/** Derivación de series para gráficos y KPI a partir de ``DesignData``. */
import type { DesignData, PerformanceWindow, Series } from '../api/result';
import { DRAG_METHODS, PULL_METHODS } from './labels';

export const at = (s: Series | undefined, i: number): number | null => {
  const v = s?.[i];
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
};

export function hasModified(d: DesignData): boolean {
  return d.case.net_modified !== null && d.case.net_modified !== undefined;
}

/** Hélice de los tiros disponibles en ``performance.windows`` (``fixed_pitch``…). */
export function windowPropellers(d: DesignData): string[] {
  const out: string[] = [];
  for (const k of Object.keys(d.result.performance.windows)) {
    const p = k.replace(/_(std|mod)$/, '');
    if (!out.includes(p)) out.push(p);
  }
  return out;
}

export function designPropeller(d: DesignData): string {
  return d.result.performance.design_key.replace(/_(std|mod)$/, '');
}

export function perfWindow(
  d: DesignData,
  propeller: string,
  variant: 'std' | 'mod',
): PerformanceWindow | undefined {
  return d.result.performance.windows[`${propeller}_${variant}`];
}

export interface PullRow {
  speed: number;
  available: number | null;
  demandStd: number | null;
  demandMod: number | null;
  [method: string]: number | null;
}

/** Filas del gráfico «tiro disponible vs resistencia total». */
export function pullRows(d: DesignData, propeller: string): PullRow[] {
  const speeds = d.case.speeds_kn;
  const curves = d.result.power.curves;
  const wStd = perfWindow(d, propeller, 'std');
  const wMod = perfWindow(d, propeller, 'mod');
  return speeds.map((speed, i) => {
    const row: PullRow = {
      speed,
      available: at(wStd?.available_kgf, i),
      demandStd: at(wStd?.demand_kgf ?? d.result.performance.demand.std, i),
      demandMod: hasModified(d) ? at(wMod?.demand_kgf ?? d.result.performance.demand.mod, i) : null,
    };
    for (const [k] of PULL_METHODS) {
      if (k === 'fridman_kgf') continue;
      row[k] = at(curves[k], i);
    }
    return row;
  });
}

/** Ventana factible [min, max] de velocidades para la red estándar. */
export function feasibleWindow(
  w: PerformanceWindow | undefined,
): { from: number; to: number } | null {
  if (!w || w.max_speed_kn === null || !w.feasible.some(Boolean)) return null;
  const first = w.speeds_kn[w.feasible.indexOf(true)];
  if (first === undefined) return null;
  return { from: first, to: w.max_speed_kn };
}

export interface DragRow {
  speed: number;
  [method: string]: number | null;
}

/** RN por método [kgf] (la tabla del motor viene en toneladas). */
export function dragRows(d: DesignData, variant: 'std' | 'mod'): DragRow[] {
  const table = d.result.drag.table;
  const factor = table.unit === 't' ? 1000 : 1;
  const cols = table[variant];
  return d.case.speeds_kn.map((speed, i) => {
    const row: DragRow = { speed };
    for (const [k] of DRAG_METHODS) {
      const v = at(cols[k], i);
      row[k] = v === null ? null : v * factor;
    }
    return row;
  });
}

export interface CompositionRow {
  variant: string;
  rn: number;
  floats: number;
  warps: number;
  doors: number;
  total: number;
}

/** Composición de la resistencia total a la velocidad de índice ``i``. */
export function composition(d: DesignData, i: number): CompositionRow[] {
  const r = d.result;
  const floats = at(r.floats.drag_kgf, i) ?? 0;
  const warps = at(r.warps.drag_kgf, i) ?? 0;
  const doors = at(r.doors.forces.drag_kgf, i) ?? 0;
  const mk = (variant: string, rn: number): CompositionRow => ({
    variant,
    rn,
    floats,
    warps,
    doors,
    total: rn + floats + warps + doors,
  });
  const rows = [mk('Estándar', at(r.drag.rn.std, i) ?? 0)];
  if (hasModified(d)) rows.push(mk('Modificada', at(r.drag.rn.mod, i) ?? 0));
  return rows;
}

export interface SpreadRow {
  speed: number;
  dpaStd: number | null;
  dpaMod: number | null;
  avStd: number | null;
  avMod: number | null;
}

export function spreadRows(d: DesignData): SpreadRow[] {
  const s = d.result.spread;
  const mod = hasModified(d);
  return d.case.speeds_kn.map((speed, i) => ({
    speed,
    dpaStd: at(s.fridman.dpa_std_m, i),
    dpaMod: mod ? at(s.fridman.dpa_mod_m, i) : null,
    avStd: at(s.vertical.fridman.std.av_m, i),
    avMod: mod ? at(s.vertical.fridman.mod.av_m, i) : null,
  }));
}

/** ¿El cable seleccionado cumple la rotura mínima requerida? (``null`` = sin dato). */
export function warpMeetsBreakingLoad(d: DesignData): boolean | null {
  const sel = d.result.warps?.selection;
  if (sel && typeof sel.satisfies_breaking_load === 'boolean') return sel.satisfies_breaking_load;
  const bt = d.summary.warp_breaking_load_t;
  const req = d.summary.warp_min_breaking_load_kgf;
  if (typeof bt === 'number' && typeof req === 'number') return bt * 1000 >= req;
  return null;
}

/** Índice de la velocidad más cercana a ``kn`` en ``speeds``. */
export function nearestIndex(speeds: number[], kn: number): number {
  let best = 0;
  speeds.forEach((s, i) => {
    if (Math.abs(s - kn) < Math.abs((speeds[best] ?? Infinity) - kn)) best = i;
  });
  return best;
}
