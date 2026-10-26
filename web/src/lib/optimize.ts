/** Optimización de escala y velocidad (``POST /optimize``): formulario, malla y etiquetas. */
import type { Evaluation, OptimizeRequest, OptimizeResponse } from '../api/client';
import { msg } from '../i18n';
import { fmtNum, parseNumber, toInput } from './format';

export type Objective = OptimizeRequest['objective'];

const objective = (id: Objective) => ({
  id,
  get label() {
    return msg().optimize.objectives[id].label;
  },
  get help() {
    return msg().optimize.objectives[id].help;
  },
});

/** Objetivos de la optimización (textos en el idioma activo). */
export const OBJECTIVES: { id: Objective; label: string; help: string }[] = [
  objective('area'),
  objective('volume'),
  objective('energy'),
];

/** Clave del objetivo en la respuesta (``area_rate``…) → atributo de la evaluación y sentido. */
export const OBJECTIVE_ATTR: Record<string, { attr: keyof Evaluation; sense: 1 | -1 }> = {
  area_rate: { attr: 'area_rate_m2_h', sense: 1 },
  volume_rate: { attr: 'volume_rate_m3_h', sense: 1 },
  energy: { attr: 'energy_kgf_m_per_m2', sense: -1 },
};

const OBJECTIVE_UNIT: Record<string, string> = {
  area_rate: 'm²/h',
  volume_rate: 'm³/h',
  energy: 'kgf·m/m²',
};

/** Nombre y unidad del motor (métrica) de un objetivo de la respuesta (``area_rate``…). */
export function objectiveUnit(key: string): { label: string; unit: string } {
  const labels = msg().optimize.objectiveUnits as Record<string, string>;
  return { label: labels[key] ?? key, unit: OBJECTIVE_UNIT[key] ?? '' };
}

/** Nombre de una restricción (``thrust``…) en el idioma activo. */
export function constraintLabel(name: string): string {
  return (msg().optimize.constraints as Record<string, string>)[name] ?? name;
}

/** Unidad del motor del valor y los límites de cada restricción. */
export const CONSTRAINT_UNITS: Record<string, string> = {
  thrust: 'kgf',
  net_open: 'm',
  warp: 'kgf',
  door: 'm²',
  speed: 'kn',
};

/** Valores del formulario (texto, como los escribe el usuario). */
export interface OptimizeForm {
  objective: Objective;
  margin: string;
  sMin: string;
  sMax: string;
  vMin: string;
  vMax: string;
  nS: string;
  nV: string;
  door: string;
  refine: boolean;
}

export const DEFAULT_FORM: OptimizeForm = {
  objective: 'area',
  margin: '10',
  sMin: '0,6',
  sMax: '1,4',
  vMin: '1,5',
  vMax: '4',
  nS: '9',
  nV: '11',
  door: '',
  refine: false,
};

/** Formulario por defecto con el separador decimal del idioma activo. */
export function defaultOptimizeForm(): OptimizeForm {
  return { ...DEFAULT_FORM, sMin: toInput(0.6), sMax: toInput(1.4), vMin: toInput(1.5) };
}

export interface BuiltOptimize {
  /** Campos del pedido que dependen del formulario. */
  body: Pick<
    OptimizeRequest,
    'objective' | 'margin' | 's_bounds' | 'v_bounds' | 'grid' | 'refine' | 'seed'
  > | null;
  errors: Partial<Record<keyof OptimizeForm, string>>;
}

/** Valida el formulario con los mismos límites que la API (``OptimizeRequest``). */
export function buildOptimize(f: OptimizeForm): BuiltOptimize {
  const errors: BuiltOptimize['errors'] = {};
  const T = msg().optimize.errors;
  const num = (k: keyof OptimizeForm, lo: number, hi: number, int = false): number | null => {
    const v = parseNumber(String(f[k]));
    if (v === null) {
      errors[k] = T.number;
      return null;
    }
    if (int && !Number.isInteger(v)) {
      errors[k] = T.integer;
      return null;
    }
    if (v < lo || v > hi) {
      errors[k] = T.range(fmtNum(lo), fmtNum(hi));
      return null;
    }
    return v;
  };
  const margin = num('margin', 0, 200);
  const sMin = num('sMin', 0.3, 2);
  const sMax = num('sMax', 0.3, 2);
  const vMin = num('vMin', 0.5, 6);
  const vMax = num('vMax', 0.5, 6);
  const nS = num('nS', 2, 25, true);
  const nV = num('nV', 2, 25, true);
  if (sMin !== null && sMax !== null && sMin >= sMax) errors.sMax = T.aboveMin;
  if (vMin !== null && vMax !== null && vMin >= vMax) errors.vMax = T.aboveMin;
  if (Object.keys(errors).length) return { body: null, errors };
  return {
    body: {
      objective: f.objective,
      margin: (margin as number) / 100,
      s_bounds: [sMin as number, sMax as number],
      v_bounds: [vMin as number, vMax as number],
      grid: { n_s: nS as number, n_v: nV as number },
      refine: f.refine,
      seed: 0,
    },
    errors,
  };
}

/** Malla ``s × v`` de la respuesta (``OptimizationResult.grid.to_dict()``). */
export interface GridData {
  s_values: number[];
  v_values: number[];
  feasible: boolean[][];
  area_rate_m2_h: (number | null)[][];
  volume_rate_m3_h: (number | null)[][];
  energy_kgf_m_per_m2: (number | null)[][];
  thrust_margin: (number | null)[][];
}

export function gridData(r: OptimizeResponse): GridData {
  return r.grid as unknown as GridData;
}

export interface HeatCell {
  i: number;
  j: number;
  s: number;
  v: number;
  feasible: boolean;
  value: number | null;
  /** Posición del valor en la escala (0 peor … 1 mejor) entre las celdas factibles. */
  t: number | null;
  best: boolean;
}

const GRID_ATTR: Record<string, keyof GridData> = {
  area_rate: 'area_rate_m2_h',
  volume_rate: 'volume_rate_m3_h',
  energy: 'energy_kgf_m_per_m2',
};

/** Celdas del mapa de factibilidad coloreadas por el objetivo (sólo las factibles). */
export function heatCells(r: OptimizeResponse): {
  cells: HeatCell[];
  min: number | null;
  max: number | null;
} {
  const g = gridData(r);
  const key = GRID_ATTR[r.objective] ?? 'area_rate_m2_h';
  const sense = OBJECTIVE_ATTR[r.objective]?.sense ?? 1;
  const vals = g[key] as (number | null)[][];
  const feasibleVals: number[] = [];
  g.s_values.forEach((_, i) =>
    g.v_values.forEach((_, j) => {
      const v = vals[i]?.[j];
      if (g.feasible[i]?.[j] && typeof v === 'number') feasibleVals.push(v);
    }),
  );
  const min = feasibleVals.length ? Math.min(...feasibleVals) : null;
  const max = feasibleVals.length ? Math.max(...feasibleVals) : null;
  const cells: HeatCell[] = [];
  g.s_values.forEach((s, i) =>
    g.v_values.forEach((v, j) => {
      const feasible = !!g.feasible[i]?.[j];
      const value = vals[i]?.[j] ?? null;
      let t: number | null = null;
      if (feasible && value !== null && min !== null && max !== null) {
        const raw = max > min ? (value - min) / (max - min) : 1;
        t = sense > 0 ? raw : 1 - raw;
      }
      cells.push({ i, j, s, v, feasible, value, t, best: false });
    }),
  );
  let best: HeatCell | null = null;
  for (const c of cells) {
    if (c.t === null || c.value === null) continue;
    if (!best || sense * c.value > sense * (best.value as number)) best = c;
  }
  if (best) best.best = true;
  return { cells, min, max };
}

/** Puntos del frente de Pareto (área barrida en miles de m²/h vs R_T/AH), ordenados por área. */
export function paretoPoints(r: OptimizeResponse) {
  return r.pareto
    .filter((e) => e.area_rate_m2_h !== null && e.energy_kgf_m_per_m2 !== null)
    .map((e) => ({
      area: (e.area_rate_m2_h as number) / 1000,
      energy: e.energy_kgf_m_per_m2 as number,
      s: e.s,
      v: e.v_kn,
    }))
    .sort((a, b) => a.area - b.area);
}

/** El mejor diseño es el mismo punto que una evaluación dada (para resaltarlo). */
export function samePoint(a: { s: number; v_kn: number }, b: { s: number; v_kn: number }) {
  return Math.abs(a.s - b.s) < 1e-9 && Math.abs(a.v_kn - b.v_kn) < 1e-9;
}
