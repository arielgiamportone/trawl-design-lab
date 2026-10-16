/** Comparación de dos resúmenes (A fijado vs B en vivo). */
import type { Summary } from '../api/result';
import { label } from './labels';

export interface DiffRow {
  key: string;
  label: string;
  unit: string;
  a: number | string | null;
  b: number | string | null;
  /** B − A (sólo numéricos). */
  abs: number | null;
  /** (B − A)/|A|·100 (``null`` si A = 0 o no numérico). */
  pct: number | null;
  changed: boolean;
  /** Cambio relevante: |%| ≥ ``threshold`` o texto distinto. */
  significant: boolean;
}

const EPS = 1e-9;

export function diffSummaries(a: Summary, b: Summary, threshold = 1): DiffRow[] {
  const keys = [...Object.keys(a)];
  for (const k of Object.keys(b)) if (!keys.includes(k)) keys.push(k);
  return keys.map((key) => {
    const [name, unit] = label(key);
    const va = a[key] ?? null;
    const vb = b[key] ?? null;
    if (typeof va === 'number' && typeof vb === 'number') {
      const abs = vb - va;
      const pct = Math.abs(va) > EPS ? (abs / Math.abs(va)) * 100 : null;
      const changed = Math.abs(abs) > EPS * Math.max(1, Math.abs(va));
      const significant = changed && (pct === null ? true : Math.abs(pct) >= threshold);
      return { key, label: name, unit, a: va, b: vb, abs, pct, changed, significant };
    }
    const changed = va !== vb;
    return {
      key,
      label: name,
      unit,
      a: va,
      b: vb,
      abs: null,
      pct: null,
      changed,
      significant: changed,
    };
  });
}
