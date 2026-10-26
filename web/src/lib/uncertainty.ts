/**
 * Incertidumbre (``POST /simulate/uncertainty``) y calibración (``POST /simulate/calibrate``,
 * ``POST /sensors/parse``): formularios, pedidos y lectura de las respuestas.
 */
import type {
  CalibrateRequest,
  CalibrateResponse,
  DesignRequest,
  ObservationIn,
  UncertaintyRequest,
  UncertaintyResponse,
} from '../api/client';
import { msg } from '../i18n';
import { scenarioIn } from './scenario';

// --- incertidumbre --------------------------------------------------------------------------

export interface UncForm {
  speed: number;
  catchKg: number;
  seabed: string | null;
  samples: number;
  resolution: number;
  species: string | null;
}

export const DEFAULT_UNC: UncForm = {
  speed: 3,
  catchKg: 300,
  seabed: 'mixed',
  samples: 10,
  resolution: 2,
  species: null,
};

export const UNC_FORM_KEY = 'uncertainty:form';

export function uncertaintyRequest(base: DesignRequest, f: UncForm): UncertaintyRequest {
  return {
    net: base.net,
    vessel: base.vessel ?? null,
    door: base.door ?? null,
    class_vessels: null,
    compat: base.compat ?? 'corrected',
    speed_kn: f.speed,
    resolution: f.resolution,
    cn: null,
    ct: null,
    scenario: scenarioIn({ catch_kg: f.catchKg, seabed: f.seabed }),
    samples: f.samples,
    seed: 0,
    inputs: null,
    species: f.species ? [f.species] : [],
  };
}

export interface UncInput {
  name: string;
  label: string;
  low: number;
  high: number;
  nominal: number;
  unit: string;
  source: string;
}

export interface UncOutput {
  key: string;
  label: string;
  unit: string;
  nominal: number | null;
  p10: number;
  p50: number;
  p90: number;
  values: (number | null)[];
  sensitivity: Record<string, number>;
}

export interface UncResult {
  speed_kn: number;
  n: number;
  inputs: UncInput[];
  samples: number[][];
  outputs: UncOutput[];
  converged: number;
  runtime_s: number;
}

export function asUncertainty(r: UncertaintyResponse): UncResult {
  return r.result as unknown as UncResult;
}

/** Ancho de la banda P10–P90 relativo a la mediana [%]. */
export function bandPct(o: UncOutput): number | null {
  if (!o.p50) return null;
  return (100 * (o.p90 - o.p10)) / Math.abs(o.p50);
}

/** Entradas ordenadas por el peso de su correlación con la salida (tornado). */
export function tornado(
  o: UncOutput,
  inputs: UncInput[],
): { name: string; label: string; rho: number }[] {
  return inputs
    .map((i) => ({ name: i.name, label: i.label, rho: o.sensitivity[i.name] ?? 0 }))
    .sort((a, b) => Math.abs(b.rho) - Math.abs(a.rho));
}

/** Escala común (± % respecto del nominal) para dibujar todas las bandas juntas. */
export function relativeSpan(outputs: UncOutput[]): number {
  let m = 5;
  for (const o of outputs) {
    const ref = o.nominal ?? o.p50;
    if (!ref) continue;
    for (const v of [o.p10, o.p90, ...o.values]) {
      if (v === null || v === undefined) continue;
      m = Math.max(m, Math.abs((100 * (v - ref)) / ref));
    }
  }
  return Math.ceil(m / 5) * 5;
}

// --- calibración ----------------------------------------------------------------------------

export type CalParam = NonNullable<CalibrateRequest['params']>[number];

const calParam = (id: CalParam) => ({
  id,
  get label() {
    return msg().uncertainty.calParams[id].label;
  },
  get help() {
    return msg().uncertainty.calParams[id].help;
  },
});

/** Parámetros calibrables (textos en el idioma activo). */
export const CAL_PARAMS: { id: CalParam; label: string; help: string }[] = [
  calParam('cn'),
  calParam('ct'),
  calParam('door_cl_factor'),
  calParam('door_cd_factor'),
  calParam('mu_gear'),
  calParam('mu_door'),
];

const QUANTITY_UNITS: Record<string, string> = {
  door_spread_m: 'm',
  ah_m: 'm',
  av_m: 'm',
  headrope_height_m: 'm',
  drag_kgf: 'kgf',
  towing_pull_kgf: 'kgf',
  warp_tension_kgf: 'kgf',
};

/** Nombre de una magnitud medida (``door_spread_m`` → «Separación de portones»). */
export function quantityLabel(key: string): string {
  return (msg().uncertainty.quantities as Record<string, string>)[key] ?? key;
}

/** Unidad del motor de una magnitud medida (por la clave o su sufijo). */
export function quantityUnit(key: string): string {
  return QUANTITY_UNITS[key] ?? (key.endsWith('_kgf') ? 'kgf' : key.endsWith('_m') ? 'm' : '');
}

export interface CalForm {
  source: 'dynamit' | 'sensors';
  params: CalParam[];
  resolution: number;
  maxEvals: number;
  seabed: string | null;
  by: 'speed' | 'time';
  width: number;
}

export const DEFAULT_CAL: CalForm = {
  source: 'sensors',
  params: ['door_cl_factor'],
  resolution: 2,
  maxEvals: 12,
  seabed: 'mixed',
  by: 'time',
  width: 20,
};

export function calibrateRequest(
  base: DesignRequest,
  f: CalForm,
  observations: ObservationIn[],
): CalibrateRequest {
  return {
    net: base.net,
    vessel: base.vessel ?? null,
    door: base.door ?? null,
    class_vessels: null,
    compat: base.compat ?? 'corrected',
    resolution: f.resolution,
    scenario: scenarioIn({ seabed: f.source === 'dynamit' ? null : f.seabed }),
    reference: f.source === 'dynamit' ? 'dynamit' : null,
    observations: f.source === 'dynamit' ? [] : observations,
    params: f.params.length ? f.params : DEFAULT_CAL.params,
    max_evals: f.maxEvals,
  };
}

export interface CalParamOut {
  name: string;
  label: string;
  initial: number;
  fitted: number;
  std: number | null;
  low: number;
  high: number;
}

export interface CalObsOut {
  quantity: string;
  label: string;
  unit: string;
  value: number;
  speed_kn: number;
  catch_kg: number;
  before: number;
  after: number;
  error_before_pct: number;
  error_after_pct: number;
  source: string;
}

export interface CalResult {
  params: CalParamOut[];
  observations: CalObsOut[];
  rmse_before_pct: number;
  rmse_after_pct: number;
  evaluations: number;
  runtime_s: number;
}

export function asCalibration(r: CalibrateResponse): CalResult {
  return r.result as unknown as CalResult;
}

/** ¿El parámetro quedó en un borde de su rango? (el ajuste quiere ir más allá). */
export function atBound(p: CalParamOut): boolean {
  const tol = 1e-6 * Math.max(1, Math.abs(p.high - p.low));
  return Math.abs(p.fitted - p.low) < tol || Math.abs(p.fitted - p.high) < tol;
}
