/** Lance progresivo (``POST /simulate/haul``): pedido, filas de los gráficos y resumen. */
import type { DesignRequest, HaulRequest, HaulResponse } from '../api/client';
import { msg } from '../i18n';
import { fmtFixed } from './format';
import { fmtU } from './units';

/** Tipos de captura: densidad aparente en el copo y de los organismos [kg/m³] (A VERIFICAR). */
export const CATCH_TYPES = [
  {
    id: 'fish',
    get label() {
      return msg().haul.catchTypes.fish;
    },
    bulk: 750,
    body: 1070,
  },
  {
    id: 'crustacean',
    get label() {
      return msg().haul.catchTypes.crustacean;
    },
    bulk: 850,
    body: 1150,
  },
  {
    id: 'mixed',
    get label() {
      return msg().haul.catchTypes.mixed;
    },
    bulk: 1000,
    body: 1300,
  },
] as const;
export type CatchType = (typeof CATCH_TYPES)[number]['id'];

export interface HaulForm {
  speed: number;
  maxCatchKg: number;
  steps: number;
  catchType: CatchType;
  seabed: string | null;
  coupledDoors: boolean;
  resolution: number;
}

export const DEFAULT_HAUL: HaulForm = {
  speed: 3,
  maxCatchKg: 1000,
  steps: 4,
  catchType: 'fish',
  seabed: 'mixed',
  coupledDoors: true,
  resolution: 4,
};

/** Capturas de cada paso: de 0 a ``max`` en ``steps`` valores parejos (redondeados a 10 kg). */
export function catchSteps(maxKg: number, steps: number): number[] {
  const n = Math.max(2, Math.min(8, Math.round(steps)));
  const max = Math.max(0, maxKg);
  return Array.from({ length: n }, (_, i) => Math.round((max * i) / (n - 1) / 10) * 10);
}

export function haulRequest(base: DesignRequest, f: HaulForm, geometry = true): HaulRequest {
  const ct = CATCH_TYPES.find((c) => c.id === f.catchType) ?? CATCH_TYPES[0];
  return {
    net: base.net,
    vessel: base.vessel ?? null,
    door: base.door ?? null,
    class_vessels: null,
    compat: base.compat ?? 'corrected',
    speed_kn: f.speed,
    catches_kg: catchSteps(f.maxCatchKg, f.steps),
    resolution: f.resolution,
    cn: null,
    ct: null,
    scenario: {
      catch_kg: 0,
      catch_bulk_density: ct.bulk,
      catch_body_density: ct.body,
      catch_cp: 1,
      seabed: f.seabed,
      mu_gear: null,
      mu_door: null,
      coupled_doors: f.coupledDoors,
      fouling: null,
      fouling_level: 1,
      current_kn: 0,
      warp_length_m: null,
      haul_hours: 2,
      mesh_bending: null,
      mesh_bending_factor: 1,
      door_cl_factor: 1,
      door_cd_factor: 1,
      dynamic_door_polar: true,
    },
    include_geometry: geometry,
  };
}

export interface HaulRow {
  catchKg: number;
  doorSpread: number | null;
  ah: number | null;
  av: number | null;
  pull: number | null;
  netDrag: number | null;
  warpTension: number | null;
  catchDrag: number | null;
  catchLength: number | null;
  codendDiameter: number | null;
  friction: number | null;
  converged: boolean;
}

const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);

export function haulRows(r: HaulResponse): HaulRow[] {
  return r.results.map((x) => {
    const catchInfo = (x.catch ?? {}) as Record<string, unknown>;
    const scen = (x.scenario ?? {}) as Record<string, unknown>;
    const fr = num(x.friction_kgf);
    const df = num(x.door_friction_kgf);
    return {
      catchKg: num(scen.catch_kg) ?? 0,
      doorSpread: num(x.door_spread_m),
      ah: num(x.ah_m),
      av: num(x.av_m),
      pull: num(x.towing_pull_kgf) || null,
      netDrag: num(x.drag_kgf),
      warpTension: num(x.warp_tension_kgf) || null,
      catchDrag: num(x.catch_drag_kgf),
      catchLength: num(catchInfo.length_m),
      codendDiameter: num(catchInfo.max_diameter_m),
      friction: fr === null ? null : fr + (df ?? 0),
      converged: x.converged !== false,
    };
  });
}

/** Frase con el efecto de la captura entre el primer y el último paso (idioma y unidades activos). */
export function haulSummary(rows: HaulRow[]): string | null {
  const a = rows[0];
  const b = rows[rows.length - 1];
  if (!a || !b || rows.length < 2 || b.catchKg === a.catchKg) return null;
  const T = msg().haul.summary;
  const parts: string[] = [];
  const diff = (x: number | null, y: number | null) => (x === null || y === null ? null : y - x);
  const pct = (x: number | null, d: number | null) =>
    x === null || d === null || x === 0
      ? ''
      : T.pct(`${d > 0 ? '+' : ''}${fmtFixed((d / x) * 100, 0)}`);
  const dDp = diff(a.doorSpread, b.doorSpread);
  if (dDp !== null)
    parts.push(T.doors(dDp < 0, fmtU(Math.abs(dDp), 'm', { digits: 1 }), pct(a.doorSpread, dDp)));
  const dPull = diff(a.pull, b.pull);
  if (dPull !== null)
    parts.push(T.pull(dPull > 0, fmtU(Math.abs(dPull), 'kgf', { digits: 0 }), pct(a.pull, dPull)));
  const dAh = diff(a.ah, b.ah);
  if (dAh !== null) parts.push(T.ah(dAh < 0, fmtU(Math.abs(dAh), 'm', { digits: 1 })));
  if (!parts.length) return null;
  const last = parts.pop() as string;
  const text = parts.length ? `${parts.join(', ')}${T.and}${last}` : last;
  return T.sentence(
    fmtU(a.catchKg, 'kg', { digits: 0, unit: false }),
    fmtU(b.catchKg, 'kg', { digits: 0 }),
    text,
  );
}

/** Marcas "redondas" (1, 2, 2,5 o 5 × 10ⁿ) que cubren [lo, hi] con unas ``count`` divisiones. */
export function niceTicks(lo: number, hi: number, count = 4): number[] {
  if (!Number.isFinite(lo) || !Number.isFinite(hi)) return [];
  if (hi - lo < 1e-9) {
    const pad = Math.abs(hi) * 0.05 || 1;
    lo -= pad;
    hi += pad;
  }
  const raw = (hi - lo) / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = ([1, 2, 2.5, 5, 10].find((m) => m * mag >= raw) ?? 10) * mag;
  const start = Math.floor(lo / step) * step;
  const end = Math.ceil(hi / step) * step;
  const out: number[] = [];
  for (let v = start; v <= end + step / 2; v += step) out.push(Number(v.toPrecision(12)));
  return out;
}
