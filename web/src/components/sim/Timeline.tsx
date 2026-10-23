import { useEffect, useId, useRef, useState } from 'react';
import { useMediaQuery } from '../../lib/theme';

interface Props {
  /** Cantidad de estados (la posición va de 0 a n − 1). */
  n: number;
  t: number;
  onChange: (t: number) => void;
  /** Texto del valor de la variable en la posición ``t``. */
  valueLabel: string;
  /** Etiqueta de la variable («Captura en el copo»). */
  variableLabel: string;
}

const SPEEDS = [0.5, 1, 2] as const;
/** Duración de un tramo entre dos estados a velocidad 1× [s]. */
const SEGMENT_S = 1.2;

/**
 * Línea de tiempo de la animación: reproducir/pausa, velocidad y deslizador. Con «reducir
 * movimiento» del sistema no hay reproducción automática (sólo el deslizador y los botones).
 */
export function Timeline({ n, t, onChange, valueLabel, variableLabel }: Props) {
  const reduced = useMediaQuery('(prefers-reduced-motion: reduce)');
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>(1);
  const tRef = useRef(t);
  useEffect(() => {
    tRef.current = t;
  }, [t]);
  const ids = useId();
  const max = Math.max(0, n - 1);

  useEffect(() => {
    if (!playing || reduced) return;
    let raf = 0;
    let last = performance.now();
    const step = (now: number) => {
      const dt = (now - last) / 1000;
      last = now;
      let next = tRef.current + (dt * speed) / SEGMENT_S;
      if (next >= max) {
        next = max;
        setPlaying(false);
      }
      onChange(next);
      if (next < max) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [playing, reduced, speed, max, onChange]);

  const toggle = () => {
    if (!playing && tRef.current >= max) onChange(0);
    setPlaying((p) => !p);
  };
  const stepTo = (d: number) => {
    setPlaying(false);
    onChange(Math.min(max, Math.max(0, Math.round(tRef.current) + d)));
  };

  return (
    <div className="timeline" role="group" aria-label="Línea de tiempo de la animación">
      <button
        type="button"
        className="btn small"
        onClick={() => stepTo(-1)}
        aria-label="Estado anterior"
      >
        ⏮
      </button>
      {!reduced && (
        <button
          type="button"
          className="btn small primary timeline-play"
          onClick={toggle}
          aria-pressed={playing}
        >
          {playing ? '⏸ Pausa' : '▶ Reproducir'}
        </button>
      )}
      <button
        type="button"
        className="btn small"
        onClick={() => stepTo(1)}
        aria-label="Estado siguiente"
      >
        ⏭
      </button>
      <label htmlFor={`${ids}-t`} className="sr-only">
        {variableLabel}
      </label>
      <input
        id={`${ids}-t`}
        type="range"
        min={0}
        max={max}
        step={0.01}
        value={t}
        aria-valuetext={`${variableLabel}: ${valueLabel}`}
        onChange={(e) => {
          setPlaying(false);
          onChange(Number(e.target.value));
        }}
      />
      <span className="timeline-value" aria-live="off">
        {variableLabel}: <strong>{valueLabel}</strong>
      </span>
      {!reduced && (
        <div className="segmented" role="group" aria-label="Velocidad de reproducción">
          {SPEEDS.map((s) => (
            <button key={s} type="button" aria-pressed={speed === s} onClick={() => setSpeed(s)}>
              {String(s).replace('.', ',')}×
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
