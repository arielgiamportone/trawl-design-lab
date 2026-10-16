import { useQuery } from '@tanstack/react-query';
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent,
  type WheelEvent,
} from 'react';
import { api, type PlanView, type Variant } from '../api/client';
import { downloadBlob } from '../lib/download';
import { useCase } from '../state/useCase';

interface ViewT {
  x: number;
  y: number;
  k: number;
}
const IDENTITY: ViewT = { x: 0, y: 0, k: 1 };
const clampK = (k: number) => Math.min(12, Math.max(0.5, k));

export function PlanViewer() {
  const { committed, state } = useCase();
  const [view, setView] = useState<PlanView>('sheet');
  const [variantSel, setVariant] = useState<Variant>('std');
  const variant: Variant = committed?.net_modified ? variantSel : 'std';
  const plan = useQuery({
    queryKey: ['plan', view, variant, committed],
    queryFn: ({ signal }) => api.plan(committed!, view, variant, signal),
    enabled: committed !== null,
    staleTime: 5 * 60_000,
    retry: false,
  });

  // data: URL (sin object URLs que haya que revocar); el SVG se muestra como imagen, sin scripts.
  const url = useMemo(
    () => (plan.data ? `data:image/svg+xml;charset=utf-8,${encodeURIComponent(plan.data)}` : null),
    [plan.data],
  );

  const [t, setT] = useState<ViewT>(IDENTITY);
  const stage = useRef<HTMLDivElement>(null);
  const drag = useRef<{ x: number; y: number; tx: number; ty: number } | null>(null);
  const pointers = useRef(new Map<number, { x: number; y: number }>());
  const pinch = useRef<{ d: number; k: number } | null>(null);

  const chooseView = (v: PlanView) => {
    setView(v);
    setT(IDENTITY);
  };
  const chooseVariant = (v: Variant) => {
    setVariant(v);
    setT(IDENTITY);
  };

  const zoomAt = (factor: number, cx: number, cy: number) =>
    setT((p) => {
      const k = clampK(p.k * factor);
      const f = k / p.k;
      return { k, x: cx - (cx - p.x) * f, y: cy - (cy - p.y) * f };
    });
  const zoomCenter = (factor: number) => {
    const r = stage.current?.getBoundingClientRect();
    zoomAt(factor, (r?.width ?? 0) / 2, (r?.height ?? 0) / 2);
  };

  const onWheel = (e: WheelEvent<HTMLDivElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    zoomAt(Math.exp(-e.deltaY * 0.0015), e.clientX - r.left, e.clientY - r.top);
  };
  // evita que la rueda desplace la página mientras se hace zoom sobre el plano
  useEffect(() => {
    const el = stage.current;
    if (!el) return;
    const stop = (ev: globalThis.WheelEvent) => ev.preventDefault();
    el.addEventListener('wheel', stop, { passive: false });
    return () => el.removeEventListener('wheel', stop);
  }, [url]);

  const onDown = (e: PointerEvent<HTMLDivElement>) => {
    e.currentTarget.setPointerCapture(e.pointerId);
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.current.size === 2) {
      const [a, b] = [...pointers.current.values()];
      if (a && b) pinch.current = { d: Math.hypot(a.x - b.x, a.y - b.y), k: t.k };
      drag.current = null;
    } else {
      drag.current = { x: e.clientX, y: e.clientY, tx: t.x, ty: t.y };
    }
  };
  const onMove = (e: PointerEvent<HTMLDivElement>) => {
    if (!pointers.current.has(e.pointerId)) return;
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pinch.current && pointers.current.size === 2) {
      const [a, b] = [...pointers.current.values()];
      if (!a || !b) return;
      const r = e.currentTarget.getBoundingClientRect();
      const d = Math.hypot(a.x - b.x, a.y - b.y);
      const target = clampK((pinch.current.k * d) / pinch.current.d);
      zoomAt(target / t.k, (a.x + b.x) / 2 - r.left, (a.y + b.y) / 2 - r.top);
      return;
    }
    const s = drag.current;
    if (s) setT((p) => ({ ...p, x: s.tx + e.clientX - s.x, y: s.ty + e.clientY - s.y }));
  };
  const onUp = (e: PointerEvent<HTMLDivElement>) => {
    pointers.current.delete(e.pointerId);
    if (pointers.current.size < 2) pinch.current = null;
    drag.current = null;
  };
  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    const step = 40;
    if (e.key === '+' || e.key === '=') zoomCenter(1.25);
    else if (e.key === '-') zoomCenter(0.8);
    else if (e.key === '0') setT(IDENTITY);
    else if (e.key === 'ArrowLeft') setT((p) => ({ ...p, x: p.x + step }));
    else if (e.key === 'ArrowRight') setT((p) => ({ ...p, x: p.x - step }));
    else if (e.key === 'ArrowUp') setT((p) => ({ ...p, y: p.y + step }));
    else if (e.key === 'ArrowDown') setT((p) => ({ ...p, y: p.y - step }));
    else return;
    e.preventDefault();
  };

  const download = () => {
    if (!plan.data) return;
    const name = `plano-${state.net}-${variant}-${view === 'sheet' ? 'lamina' : 'escala'}.svg`;
    downloadBlob(new Blob([plan.data], { type: 'image/svg+xml' }), name);
  };

  return (
    <div>
      <div className="plan-toolbar">
        <div className="segmented" role="group" aria-label="Tipo de plano">
          <button type="button" aria-pressed={view === 'sheet'} onClick={() => chooseView('sheet')}>
            Lámina técnica
          </button>
          <button type="button" aria-pressed={view === 'scale'} onClick={() => chooseView('scale')}>
            Escala real
          </button>
        </div>
        {committed?.net_modified && (
          <div className="segmented" role="group" aria-label="Variante de red">
            <button
              type="button"
              aria-pressed={variant === 'std'}
              onClick={() => chooseVariant('std')}
            >
              Estándar
            </button>
            <button
              type="button"
              aria-pressed={variant === 'mod'}
              onClick={() => chooseVariant('mod')}
            >
              Modificada
            </button>
          </div>
        )}
        <span style={{ flex: 1 }} />
        <button type="button" className="btn small" onClick={download} disabled={!plan.data}>
          Descargar SVG
        </button>
      </div>
      {plan.isError && (
        <div className="alert error" role="alert">
          No se pudo generar el plano: {plan.error.message}
        </div>
      )}
      <div
        ref={stage}
        className="plan-stage"
        tabIndex={0}
        role="application"
        aria-roledescription="visor de plano"
        aria-label="Plano de la red. Arrastre para desplazar, rueda o teclas + y − para acercar, 0 para restablecer."
        onWheel={onWheel}
        onPointerDown={onDown}
        onPointerMove={onMove}
        onPointerUp={onUp}
        onPointerCancel={onUp}
        onKeyDown={onKey}
        onDoubleClick={() => setT(IDENTITY)}
      >
        {url ? (
          <img
            src={url}
            alt={`Plano de la red (${view === 'sheet' ? 'lámina técnica' : 'escala real'}, ${variant === 'std' ? 'estándar' : 'modificada'})`}
            draggable={false}
            style={{
              transform: `translate(${t.x}px, ${t.y}px) scale(${t.k})`,
              opacity: plan.isFetching ? 0.5 : 1,
            }}
            data-testid="plan-image"
          />
        ) : (
          <p className="empty">{plan.isFetching ? 'Generando plano…' : 'Sin plano todavía.'}</p>
        )}
        <div className="plan-zoom">
          <button
            type="button"
            className="btn small"
            onClick={() => zoomCenter(1.25)}
            aria-label="Acercar"
          >
            +
          </button>
          <button
            type="button"
            className="btn small"
            onClick={() => zoomCenter(0.8)}
            aria-label="Alejar"
          >
            −
          </button>
          <button type="button" className="btn small" onClick={() => setT(IDENTITY)}>
            {Math.round(t.k * 100)} %
          </button>
        </div>
      </div>
      <p className="help" style={{ marginTop: 8 }}>
        Arrastre para desplazar; rueda del ratón o pellizco para acercar; doble clic o «0» para
        restablecer.
      </p>
    </div>
  );
}
