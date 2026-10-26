import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent,
  type WheelEvent,
} from 'react';
import type { LayoutResponse } from '../../api/client';
import { useT } from '../../i18n';
import { fmtU } from '../../lib/units';
import {
  arrangePlanes,
  dragMeshes,
  ghostPoints,
  HANDLE_FIELD,
  HANDLE_LABEL,
  handlePoint,
  pointsAttr,
  type Handle,
  type LayoutShape,
} from '../../lib/interactive';
import { PLANE_LABELS, SECTION_LABELS } from '../../lib/labels';
import type { PanelField } from '../../lib/panels';

interface Props {
  layout: LayoutResponse;
  /** Red sin ediciones, dibujada como contorno de referencia. */
  base?: LayoutResponse | null;
  showBase: boolean;
  selected: string | null;
  edited: ReadonlySet<string>;
  fetching?: boolean;
  onSelect: (id: string | null) => void;
  onCommit: (panelId: string, field: PanelField, value: number) => void;
  onNudge: (panelId: string, key: string, shift: boolean) => boolean;
}

interface Drag {
  shape: LayoutShape;
  handle: Handle;
  start: [number, number];
  value: number;
}
interface Pan {
  start: [number, number];
  view: View;
}
type View = { x: number; y: number; w: number; h: number };


/** Tirador sobre un polígono de 4 vértices (sup-izq, sup-der, inf-der, inf-izq). */
function handleOnPolygon(
  pts: [number, number][],
  side: LayoutShape['side'],
  h: Handle,
): [number, number] {
  const [tl, tr, br, bl] = pts as [
    [number, number],
    [number, number],
    [number, number],
    [number, number],
  ];
  if (h === 'depth') return [(bl[0] + br[0]) / 2, bl[1]];
  if (h === 'bottom') return side === 'left' ? bl : br;
  return side === 'left' ? tl : tr;
}

function centroid(pts: readonly (readonly [number, number])[]): [number, number] {
  const n = pts.length || 1;
  return [pts.reduce((a, p) => a + p[0], 0) / n, pts.reduce((a, p) => a + p[1], 0) / n];
}

/**
 * Plano editable de la red: los paneles son botones (clic o Enter selecciona; flechas ajustan
 * mallas) y el panel seleccionado muestra tiradores para arrastrar su alto y sus bordes. Rueda y
 * botones hacen zoom; arrastrar el fondo desplaza.
 */
export function NetCanvas({
  layout,
  base,
  showBase,
  selected,
  edited,
  fetching,
  onSelect,
  onCommit,
  onNudge,
}: Props) {
  const T = useT().interactive;
  const svgRef = useRef<SVGSVGElement>(null);
  const planes = layout.planes;
  const span = useMemo(() => {
    const widths = planes.map((p) => p.bbox[2] - p.bbox[0]);
    return Math.max(1, ...widths);
  }, [planes]);
  const gap = span * 0.12;
  const { offsets, bbox } = useMemo(() => arrangePlanes(planes, gap), [planes, gap]);
  const pad = Math.max(bbox[2] - bbox[0], bbox[3] - bbox[1]) * 0.06;
  const home: View = useMemo(
    () => ({
      x: bbox[0] - pad,
      y: bbox[1] - pad * 2,
      w: bbox[2] - bbox[0] + 2 * pad,
      h: bbox[3] - bbox[1] + 3 * pad,
    }),
    [bbox, pad],
  );
  const [view, setView] = useState<View>(home);
  const homeKey = `${layout.net_id}:${planes.map((p) => p.plane).join(',')}`;
  const lastHome = useRef(homeKey);
  useEffect(() => {
    if (lastHome.current !== homeKey) {
      lastHome.current = homeKey;
      setView(home);
    }
  }, [homeKey, home]);

  const [drag, setDrag] = useState<Drag | null>(null);
  const pan = useRef<Pan | null>(null);
  const u = view.w / 100; // unidad de dibujo proporcional al zoom (tiradores y textos)

  const toMeters = (clientX: number, clientY: number): [number, number] => {
    const svg = svgRef.current;
    const ctm = svg?.getScreenCTM();
    if (!svg || !ctm) return [0, 0];
    const p = new DOMPoint(clientX, clientY).matrixTransform(ctm.inverse());
    return [p.x, p.y];
  };

  const zoom = (factor: number, cx = view.x + view.w / 2, cy = view.y + view.h / 2) =>
    setView((v) => {
      const w = Math.min(home.w * 4, Math.max(home.w / 12, v.w / factor));
      const f = w / v.w;
      return { x: cx - (cx - v.x) * f, y: cy - (cy - v.y) * f, w, h: v.h * f };
    });

  const onWheel = (e: WheelEvent<SVGSVGElement>) => {
    const [mx, my] = toMeters(e.clientX, e.clientY);
    zoom(Math.exp(-e.deltaY * 0.0015), mx, my);
  };
  useEffect(() => {
    const el = svgRef.current;
    if (!el) return;
    const stop = (ev: globalThis.WheelEvent) => ev.preventDefault();
    el.addEventListener('wheel', stop, { passive: false });
    return () => el.removeEventListener('wheel', stop);
  }, []);

  // Un solo manejador para todos los tiradores: el tirador se identifica por sus data-*.
  const onHandleDown = (e: PointerEvent<SVGCircleElement>) => {
    e.stopPropagation();
    const { panel, side, handle: h, plane } = e.currentTarget.dataset;
    const shape = planes
      .find((p) => p.plane === plane)
      ?.shapes.find((x) => x.id === panel && x.side === side);
    if (!shape || !h) return;
    const handle = h as Handle;
    svgRef.current?.setPointerCapture?.(e.pointerId);
    const value = dragMeshes(shape, handle, 0, 0);
    setDrag({ shape, handle, start: toMeters(e.clientX, e.clientY), value });
  };
  const onDown = (e: PointerEvent<SVGSVGElement>) => {
    if (drag) return;
    svgRef.current?.setPointerCapture?.(e.pointerId);
    pan.current = { start: [e.clientX, e.clientY], view };
  };
  const onMove = (e: PointerEvent<SVGSVGElement>) => {
    if (drag) {
      const [mx, my] = toMeters(e.clientX, e.clientY);
      const value = dragMeshes(drag.shape, drag.handle, mx - drag.start[0], my - drag.start[1]);
      if (value !== drag.value) setDrag({ ...drag, value });
      return;
    }
    const p = pan.current;
    const el = svgRef.current;
    if (!p || !el) return;
    const k = p.view.w / (el.clientWidth || 1);
    setView({
      ...p.view,
      x: p.view.x - (e.clientX - p.start[0]) * k,
      y: p.view.y - (e.clientY - p.start[1]) * k,
    });
  };
  const onUp = () => {
    if (drag) {
      const start = dragMeshes(drag.shape, drag.handle, 0, 0);
      if (drag.value !== start) onCommit(drag.shape.id, HANDLE_FIELD[drag.handle], drag.value);
      setDrag(null);
    }
    pan.current = null;
  };
  const onSvgKey = (e: KeyboardEvent<SVGSVGElement>) => {
    if (e.key === 'Escape') {
      if (drag) setDrag(null);
      else onSelect(null);
    } else if (e.key === '+' || e.key === '=') zoom(1.25);
    else if (e.key === '-') zoom(0.8);
    else if (e.key === '0') setView(home);
  };
  const onPanelKey = (e: KeyboardEvent<SVGPolygonElement>, id: string) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onSelect(id === selected ? null : id);
    } else if (e.key.startsWith('Arrow')) {
      if (id !== selected) onSelect(id);
      if (onNudge(id, e.key, e.shiftKey)) e.preventDefault();
    }
  };

  const fontSize = Math.max(u * 1.6, 0.05);
  return (
    <div className={`net-canvas${fetching ? ' fetching' : ''}`}>
      <svg
        ref={svgRef}
        viewBox={`${view.x} ${view.y} ${view.w} ${view.h}`}
        preserveAspectRatio="xMidYMid meet"
        role="group"
        aria-label={T.canvasLabel}
        tabIndex={-1}
        onPointerDown={onDown}
        onPointerMove={onMove}
        onPointerUp={onUp}
        onPointerCancel={onUp}
        onWheel={onWheel}
        onKeyDown={onSvgKey}
        data-testid="net-canvas"
      >
        {planes.map((plane) => {
          const dx = offsets[plane.plane] ?? 0;
          const [x0, y0, x1] = plane.bbox;
          return (
            <g key={plane.plane} data-plane={plane.plane}>
              <text
                x={x0 + dx + (x1 - x0) / 2}
                y={y0 - pad * 0.8}
                fontSize={fontSize * 1.3}
                textAnchor="middle"
                className="nc-plane-label"
              >
                {T.planeTitle(PLANE_LABELS[plane.plane] ?? plane.plane)}
              </text>
              {plane.shapes.map((s) => {
                const isSel = s.id === selected;
                const isDragged =
                  drag && drag.shape.id === s.id ? ghostPoints(s, drag.handle, drag.value) : null;
                const pts = isDragged ?? (s.points as [number, number][]);
                const [cx, cy] = centroid(pts);
                const label = T.panelLabel(
                  s.id,
                  `${SECTION_LABELS[s.section] ?? s.section}, ${PLANE_LABELS[s.plane] ?? s.plane}, ${T.sides[s.side]}`,
                  s.meshes_top,
                  s.meshes_bottom,
                  s.meshes_depth,
                  fmtU(s.mesh_mm, 'mesh_mm'),
                );
                return (
                  <g key={`${s.id}-${s.side}`}>
                    <polygon
                      points={pointsAttr(pts, dx)}
                      className={`nc-panel${isSel ? ' selected' : ''}${edited.has(s.id) ? ' edited' : ''}`}
                      role="button"
                      tabIndex={s.side === 'left' ? -1 : 0}
                      aria-label={label}
                      aria-pressed={isSel}
                      data-panel={s.id}
                      data-side={s.side}
                      onPointerDown={(e) => e.stopPropagation()}
                      onClick={() => onSelect(isSel ? null : s.id)}
                      onKeyDown={(e) => onPanelKey(e, s.id)}
                    />
                    <text
                      x={cx + dx}
                      y={cy}
                      fontSize={fontSize}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      className="nc-panel-id"
                      aria-hidden="true"
                    >
                      {s.id}
                    </text>
                  </g>
                );
              })}
              {showBase &&
                base?.planes
                  .find((b) => b.plane === plane.plane)
                  ?.shapes.map((s) => (
                    <polygon
                      key={`base-${s.id}-${s.side}`}
                      points={pointsAttr(s.points as [number, number][], dx)}
                      className="nc-base"
                      aria-hidden="true"
                    />
                  ))}
              {plane.shapes
                .filter((s) => s.id === selected)
                .flatMap((s) =>
                  (['depth', 'bottom', 'top'] as Handle[])
                    .filter((h) => h !== 'top' || s.meshes_top > 0 || s.side !== 'center')
                    .map((h) => {
                      const pts =
                        drag && drag.shape.id === s.id
                          ? ghostPoints(s, drag.handle, drag.value)
                          : (s.points as [number, number][]);
                      const shown =
                        drag && drag.shape.id === s.id
                          ? handleOnPolygon(pts, s.side, h)
                          : handlePoint(s, h);
                      return (
                        <circle
                          key={`h-${s.id}-${s.side}-${h}`}
                          cx={shown[0] + dx}
                          cy={shown[1]}
                          r={u * 1.1}
                          className={`nc-handle ${h}`}
                          data-handle={h}
                          data-side={s.side}
                          data-panel={s.id}
                          data-plane={plane.plane}
                          aria-label={T.dragHandle(HANDLE_LABEL[h], s.id)}
                          onPointerDown={onHandleDown}
                        />
                      );
                    }),
                )}
            </g>
          );
        })}
      </svg>
      {drag && (
        <div className="nc-drag-tip" role="status">
          {T.dragTipHead(drag.shape.id, HANDLE_LABEL[drag.handle])} <strong>{drag.value}</strong>{' '}
          {T.dragTipTail(dragMeshes(drag.shape, drag.handle, 0, 0))}
        </div>
      )}
      <div className="plan-zoom">
        <button type="button" className="btn small" onClick={() => zoom(1.25)} aria-label={T.zoomIn}>
          +
        </button>
        <button type="button" className="btn small" onClick={() => zoom(0.8)} aria-label={T.zoomOut}>
          −
        </button>
        <button
          type="button"
          className="btn small"
          onClick={() => setView(home)}
          aria-label={T.fullView}
        >
          {Math.round((home.w / view.w) * 100)} %
        </button>
      </div>
    </div>
  );
}
