/** Simulación de forma (``POST /simulate``): velocidades, resolución y tabla de comparación. */
import type { SimulateResponse } from '../api/client';

/** Velocidades ofrecidas [kn] (las de la tabla de DynamiT). */
export const SIM_SPEEDS = [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5];
export const MAX_SIM_SPEEDS = 3;

export type SimQuality = 'fast' | 'normal';
export const SIM_RESOLUTION: Record<SimQuality, number> = { fast: 3, normal: 6 };
export const SIM_QUALITY_LABEL: Record<SimQuality, string> = {
  fast: 'Rápida',
  normal: 'Normal',
};
/** Segundos aproximados por velocidad (para el aviso de espera). */
export const SIM_SECONDS_PER_SPEED: Record<SimQuality, number> = { fast: 1, normal: 4.5 };

/** Agrega o quita una velocidad de la selección (máximo ``MAX_SIM_SPEEDS``, ordenada). */
export function toggleSpeed(sel: number[], v: number, max = MAX_SIM_SPEEDS): number[] {
  if (sel.includes(v)) return sel.filter((x) => x !== v);
  if (sel.length >= max) return sel;
  return [...sel, v].sort((a, b) => a - b);
}

/** Clave de las proyecciones en la respuesta (``f"{v:g}"`` en Python = ``String(v)``). */
export function speedKey(v: number): string {
  return String(v);
}

/** Diferencia porcentual ``(x − ref)/ref·100`` (``null`` si falta un dato). */
export function pctDiff(x: number | null | undefined, ref: number | null | undefined) {
  if (x == null || ref == null || !Number.isFinite(x) || !Number.isFinite(ref) || ref === 0)
    return null;
  return ((x - ref) / ref) * 100;
}

export type SimQuantity = 'ah_m' | 'av_m' | 'drag_kgf';

export const SIM_QUANTITIES: { key: SimQuantity; label: string; unit: string; engine: string }[] = [
  { key: 'ah_m', label: 'Abertura horizontal AH', unit: 'm', engine: 'DPA de Fridman' },
  { key: 'av_m', label: 'Abertura vertical AV', unit: 'm', engine: 'AV de Fridman' },
  { key: 'drag_kgf', label: 'Resistencia de la red', unit: 'kgf', engine: 'RN Aberdeen' },
];

export interface CompareRow {
  speed: number;
  key: SimQuantity;
  label: string;
  unit: string;
  engineName: string;
  sim: number | null;
  engine: number | null;
  /** (sim − motor)/motor [%]. */
  simVsEngine: number | null;
  dynamit: number | null;
  /** (sim − DynamiT)/DynamiT [%]. */
  simVsDynamit: number | null;
  /** (motor − DynamiT)/DynamiT [%]. */
  engineVsDynamit: number | null;
}

/** Filas de la tabla simulación / motor / DynamiT, por velocidad y magnitud. */
export function compareRows(r: SimulateResponse): CompareRow[] {
  const rows: CompareRow[] = [];
  r.results.forEach((res, i) => {
    const speed = Number(res.speed_kn);
    const eng = r.engine[i];
    const dyn = r.dynamit_comparison?.find((d) => Math.abs(d.speed_kn - speed) < 1e-9);
    for (const q of SIM_QUANTITIES) {
      const sim = typeof res[q.key] === 'number' ? (res[q.key] as number) : null;
      const engine = eng?.[q.key] ?? null;
      const dynamit = dyn?.dynamit[q.key] ?? null;
      rows.push({
        speed,
        key: q.key,
        label: q.label,
        unit: q.unit,
        engineName: q.engine,
        sim,
        engine,
        simVsEngine: pctDiff(sim, engine),
        dynamit,
        simVsDynamit: pctDiff(sim, dynamit),
        engineVsDynamit: pctDiff(engine, dynamit),
      });
    }
  });
  return rows;
}

/** Resultado convergido de cada velocidad (para avisar si alguno no convergió). */
export function unconverged(r: SimulateResponse): number[] {
  return r.results.filter((x) => x.converged === false).map((x) => Number(x.speed_kn));
}

/** Velocidad con un decimal y coma (``2,0``, ``2,5``). */
export function speedLabel(v: number): string {
  return v.toFixed(1).replace('.', ',');
}

/** Vista de la pestaña «Simulación» (memoria de la sesión). */
export const SIM_VIEW_KEY = 'simulate:view';
export type SimView = 'speeds' | 'haul' | 'explore' | 'selectivity' | 'uncertainty';
