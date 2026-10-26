/** Simulación de forma (``POST /simulate``): velocidades, resolución y tabla de comparación. */
import type { SimulateResponse } from '../api/client';
import { msg } from '../i18n';
import { fmt, fmtFixed, fmtNum } from './format';
import {
  CONVERSIONS,
  fmtU,
  getUnits,
  toCanonical,
  toDisplay,
  unitLabel,
  type FmtUOptions,
} from './units';

/** Velocidades ofrecidas [kn] (las de la tabla de DynamiT). */
export const SIM_SPEEDS = [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5];
export const MAX_SIM_SPEEDS = 3;

export type SimQuality = 'fast' | 'normal';
export const SIM_RESOLUTION: Record<SimQuality, number> = { fast: 3, normal: 6 };
/** Nombre de la calidad en el idioma activo («Rápida», «Normal»). */
export function simQualityLabel(q: SimQuality): string {
  return msg().simulate.quality[q];
}
/** Nombre de una resolución del simulador con su número («Rápida (3)»). */
export function resolutionLabel(n: number): string {
  const r = msg().simulate.resolutions;
  const name = n <= 2 ? r.veryFast : n === 3 ? r.fast : r.normal;
  return `${name} (${n})`;
}
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

const quantity = (key: SimQuantity, unit: string) => ({
  key,
  unit,
  get label() {
    return msg().simulate.quantities[key].label;
  },
  get engine() {
    return msg().simulate.quantities[key].engine;
  },
});

/** Magnitudes comparadas (los textos se leen en el idioma activo al usarlos). */
export const SIM_QUANTITIES: { key: SimQuantity; label: string; unit: string; engine: string }[] = [
  quantity('ah_m', 'm'),
  quantity('av_m', 'm'),
  quantity('drag_kgf', 'kgf'),
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

/** Velocidad con un decimal en el formato del idioma (``2,0`` / ``2.0``). */
export function speedLabel(v: number): string {
  return fmtNum(v, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

/** Vista de la pestaña «Simulación» (memoria de la sesión). */
export const SIM_VIEW_KEY = 'simulate:view';
export type SimView = 'speeds' | 'haul' | 'explore' | 'selectivity' | 'uncertainty';

// --- unidades compuestas de la simulación y la optimización ---------------------------------

const C = (u: string) => (CONVERSIONS[u] as { factor: number }).factor;

/**
 * Unidades del motor que ``lib/units`` no conoce (tasas y cocientes): unidad imperial y factor
 * (valor imperial = métrico × factor).
 */
const EXTRA: Record<string, { unit: string; factor: number }> = {
  'm²/h': { unit: 'ft²/h', factor: C('m²') },
  'm³/h': { unit: 'ft³/h', factor: C('m³') },
  'km²/h': { unit: 'nmi²/h', factor: C('km²') },
  // kgf·m/m² = kgf/m → lbf·ft/ft² = lbf/ft
  'kgf·m/m²': { unit: 'lbf·ft/ft²', factor: C('kg/m') },
  'L/kg': { unit: 'gal/lb', factor: C('L') / C('kg') },
};

const extra = (unit: string) => (getUnits() === 'imperial' ? (EXTRA[unit] ?? null) : null);

/** ``unitLabel`` con las unidades compuestas de la simulación. */
export function simUnit(unit: string): string {
  return extra(unit)?.unit ?? unitLabel(unit);
}

/** ``toDisplay`` con las unidades compuestas de la simulación. */
export function simValue(value: number, unit: string): number {
  const e = extra(unit);
  return e ? value * e.factor : toDisplay(value, unit);
}

/** ``simValue`` que deja pasar ``null``. */
export function simValueOpt(value: number | null | undefined, unit: string): number | null {
  return value === null || value === undefined ? null : simValue(value, unit);
}

/** ``fmtU`` con las unidades compuestas de la simulación. */
export function fmtSim(
  value: number | null | undefined,
  unit: string,
  opts: Omit<FmtUOptions, 'system'> = {},
): string {
  const e = extra(unit);
  if (!e) return fmtU(value, unit, opts);
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  const v = value * e.factor;
  const shown = opts.digits === undefined ? fmt(v) : fmtFixed(v, opts.digits);
  return opts.unit === false ? shown : `${shown} ${e.unit}`;
}

// --- campos numéricos en el sistema de unidades activo --------------------------------------

/** Valor a mostrar en un ``<input type="number">`` (convertido y redondeado a ``digits``). */
export function inputValue(value: number, unit: string, digits = 2): number {
  return Number(toDisplay(value, unit).toFixed(digits));
}

/** Valor del motor a partir de lo escrito en un campo en el sistema activo. */
export function fromInput(value: number, unit: string): number {
  return toCanonical(value, unit);
}

/** Paso de un campo: el métrico, o libre cuando la unidad se convierte (no hay paso «redondo»). */
export function inputStep(step: number, unit: string): number | 'any' {
  return getUnits() === 'imperial' && CONVERSIONS[unit] ? 'any' : step;
}
