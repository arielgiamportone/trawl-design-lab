import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent,
  type ReactNode,
  type WheelEvent,
} from 'react';

interface ViewT {
  x: number;
  y: number;
  k: number;
}
const IDENTITY: ViewT = { x: 0, y: 0, k: 1 };
const clampK = (k: number) => Math.min(12, Math.max(0.5, k));

interface Props {
  /** Texto SVG a mostrar (como imagen, sin scripts). */
  svg: string | null | undefined;
  /** Texto alternativo de la imagen. */
  alt: string;
  /** Etiqueta accesible del visor (instrucciones de uso). */
  label: string;
  /** Se está actualizando (la imagen se atenúa). */
  fetching?: boolean;
  /** Contenido cuando todavía no hay SVG. */
  placeholder?: ReactNode;
  testId?: string;
  /** Clases extra del escenario (p. ej. ``compact``). */
  className?: string;
}

/**
 * Visor de SVG con zoom y desplazamiento: rueda, arrastre, pellizco y teclado (+, −, 0, flechas).
 * Para volver a la vista inicial al cambiar de contenido, el padre cambia la ``key``.
 */
export function ZoomStage({ svg, alt, label, fetching, placeholder, testId, className }: Props) {
  // data: URL (sin object URLs que haya que revocar); el SVG se muestra como imagen, sin scripts.
  const url = useMemo(
    () => (svg ? `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}` : null),
    [svg],
  );
  const [t, setT] = useState<ViewT>(IDENTITY);
  const stage = useRef<HTMLDivElement>(null);
  const drag = useRef<{ x: number; y: number; tx: number; ty: number } | null>(null);
  const pointers = useRef(new Map<number, { x: number; y: number }>());
  const pinch = useRef<{ d: number; k: number } | null>(null);

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
  // evita que la rueda desplace la página mientras se hace zoom sobre el dibujo
  useEffect(() => {
    const el = stage.current;
    if (!el) return;
    const stop = (ev: globalThis.WheelEvent) => ev.preventDefault();
    el.addEventListener('wheel', stop, { passive: false });
    return () => el.removeEventListener('wheel', stop);
  }, [url]);

  const onDown = (e: PointerEvent<HTMLDivElement>) => {
    e.currentTarget.setPointerCapture?.(e.pointerId);
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

  return (
    <div
      ref={stage}
      className={`plan-stage${className ? ` ${className}` : ''}`}
      tabIndex={0}
      role="application"
      aria-roledescription="visor de dibujo"
      aria-label={label}
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
          alt={alt}
          draggable={false}
          style={{
            transform: `translate(${t.x}px, ${t.y}px) scale(${t.k})`,
            opacity: fetching ? 0.5 : 1,
          }}
          data-testid={testId}
        />
      ) : (
        (placeholder ?? null)
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
        <button
          type="button"
          className="btn small"
          onClick={() => setT(IDENTITY)}
          aria-label="Restablecer zoom"
        >
          {Math.round(t.k * 100)} %
        </button>
      </div>
    </div>
  );
}
