/** Historial deshacer/rehacer (inmutable) con agrupado de cambios seguidos. */

export interface History<T> {
  past: T[];
  present: T;
  future: T[];
  /** Momento del último cambio registrado [ms] (para agrupar la escritura continua). */
  lastAt: number;
}

/** Cambios separados por menos de esto se agrupan en un solo paso (escribir un número). */
export const COALESCE_MS = 800;
export const MAX_HISTORY = 100;

export function initHistory<T>(present: T): History<T> {
  return { past: [], present, future: [], lastAt: -Infinity };
}

/** Registra ``next`` como estado actual. ``coalesce`` = false fuerza un paso nuevo. */
export function record<T>(h: History<T>, next: T, now: number, coalesce = true): History<T> {
  if (Object.is(next, h.present)) return h;
  if (coalesce && now - h.lastAt < COALESCE_MS && h.past.length > 0) {
    return { ...h, present: next, future: [], lastAt: now };
  }
  const past = [...h.past, h.present].slice(-MAX_HISTORY);
  return { past, present: next, future: [], lastAt: now };
}

export function undo<T>(h: History<T>): History<T> {
  const prev = h.past[h.past.length - 1];
  if (prev === undefined) return h;
  return {
    past: h.past.slice(0, -1),
    present: prev,
    future: [h.present, ...h.future],
    lastAt: -Infinity,
  };
}

export function redo<T>(h: History<T>): History<T> {
  const [next, ...rest] = h.future;
  if (next === undefined) return h;
  return { past: [...h.past, h.present], present: next, future: rest, lastAt: -Infinity };
}
