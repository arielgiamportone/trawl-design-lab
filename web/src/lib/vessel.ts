/**
 * «Mi buque» (Fase 19.4): el buque del usuario como ``Vessel`` en línea para la API.
 *
 * Los valores se guardan como texto en métrico (las unidades del motor), igual que los
 * parámetros avanzados: el formulario los muestra y los lee en el sistema activo con
 * ``useUnitText`` (``lib/params``). Sólo la potencia es obligatoria; manga y puntal que falten los
 * completa el motor escalando el buque de la A-3 (y lo anota).
 */
import type { Vessel } from '../api/client';
import { msg } from '../i18n';
import { parseNumber } from './format';

export type PitchKind = 'fixed' | 'variable';

export interface MyVessel {
  name: string;
  bhp: string;
  length_m: string;
  beam_m: string;
  depth_m: string;
  pitch: PitchKind;
  nozzle: boolean;
  propeller_diameter_m: string;
  winch_drum_capacity_m: string;
  /** Región del puerto (vocabulario de componentes: ``latam``…); ``''`` = sin indicar. */
  region: string;
}

export const EMPTY_MY_VESSEL: MyVessel = {
  name: '',
  bhp: '',
  length_m: '',
  beam_m: '',
  depth_m: '',
  pitch: 'fixed',
  nozzle: false,
  propeller_diameter_m: '',
  winch_drum_capacity_m: '',
  region: '',
};

/** Campos numéricos del formulario con su unidad métrica (la del motor). */
export const MY_VESSEL_NUMBERS: readonly (readonly [NumField, string])[] = [
  ['bhp', 'hp'],
  ['length_m', 'm'],
  ['beam_m', 'm'],
  ['depth_m', 'm'],
  ['propeller_diameter_m', 'm'],
  ['winch_drum_capacity_m', 'm'],
] as const;

export type NumField =
  'bhp' | 'length_m' | 'beam_m' | 'depth_m' | 'propeller_diameter_m' | 'winch_drum_capacity_m';

/** Id con que viaja el buque del usuario a la API. */
export const MY_VESSEL_ID = 'mi_buque';

/** Hélices cuyo KF de Fridman tabula el libro (las demás piden ``fridman_kf``). */
const TABULATED = new Set(['fixed_pitch', 'variable_pitch_nozzle']);

/** Tipo de hélice del motor a partir del paso y la tobera. */
export function propellerOf(pitch: PitchKind, nozzle: boolean): Vessel['propeller'] {
  if (pitch === 'fixed') return nozzle ? 'fixed_pitch_nozzle' : 'fixed_pitch';
  return nozzle ? 'variable_pitch_nozzle' : 'variable_pitch';
}

export function sanitizeMyVessel(raw: unknown): MyVessel | null {
  if (!raw || typeof raw !== 'object') return null;
  const r = raw as Partial<Record<keyof MyVessel, unknown>>;
  const s = (v: unknown) => (typeof v === 'string' ? v : '');
  return {
    name: s(r.name),
    bhp: s(r.bhp),
    length_m: s(r.length_m),
    beam_m: s(r.beam_m),
    depth_m: s(r.depth_m),
    pitch: r.pitch === 'variable' ? 'variable' : 'fixed',
    nozzle: r.nozzle === true,
    propeller_diameter_m: s(r.propeller_diameter_m),
    winch_drum_capacity_m: s(r.winch_drum_capacity_m),
    region: s(r.region),
  };
}

/** Rangos de plausibilidad (métricos) de cada número. */
const LIMITS: Record<NumField, [number, number]> = {
  bhp: [1, 20000],
  length_m: [3, 150],
  beam_m: [1, 30],
  depth_m: [0.3, 20],
  propeller_diameter_m: [0.2, 8],
  winch_drum_capacity_m: [10, 10000],
};

/**
 * Errores del formulario por campo (vacío = sin errores). ``fridmanKf`` es el parámetro avanzado
 * del caso: sin él, una hélice sin KF de Fridman publicado (PF+T o PV) no se puede calcular.
 */
export function myVesselErrors(mv: MyVessel, fridmanKf = ''): Record<string, string> {
  const M = msg().vessel.errors;
  const out: Record<string, string> = {};
  for (const [k] of MY_VESSEL_NUMBERS) {
    const text = mv[k].trim();
    if (!text) {
      if (k === 'bhp') out[k] = M.required;
      continue;
    }
    const n = parseNumber(text);
    if (n === null) out[k] = M.notNumber;
    else if (n <= 0) out[k] = M.positive;
    else {
      const [lo, hi] = LIMITS[k];
      if (n < lo || n > hi) out[k] = M.range(lo, hi);
    }
  }
  const len = parseNumber(mv.length_m);
  const beam = parseNumber(mv.beam_m);
  if (!out.beam_m && len !== null && beam !== null && beam >= len) out.beam_m = M.beamVsLength;
  if (!TABULATED.has(propellerOf(mv.pitch, mv.nozzle)) && !fridmanKf.trim()) {
    out.propeller = M.noKf;
  }
  return out;
}

/** ``Vessel`` en línea para ``DesignRequest.vessel`` (en métrico, sólo los datos cargados). */
export function myVesselToApi(mv: MyVessel): Vessel {
  const num = (text: string) => parseNumber(text) ?? undefined;
  const bhp = num(mv.bhp) ?? 0;
  const v: Vessel = {
    id: MY_VESSEL_ID,
    name: mv.name.trim() || msg().vessel.defaultName(bhp),
    bhp,
    propeller: propellerOf(mv.pitch, mv.nozzle),
    nozzle: mv.nozzle,
    // Valores por defecto del esquema (``Vessel`` los declara obligatorios en la respuesta).
    high_rpm: true,
    typical: false,
    status: 'published',
  };
  for (const [k] of MY_VESSEL_NUMBERS) {
    if (k === 'bhp') continue;
    const n = num(mv[k]);
    if (n !== undefined) (v as Record<string, unknown>)[k] = n;
  }
  if (mv.region) v.region = mv.region;
  return v;
}

/** Arranca «Mi buque» con los datos de un buque del catálogo (texto métrico). */
export function myVesselFrom(v: Vessel | undefined): MyVessel {
  if (!v) return EMPTY_MY_VESSEL;
  const txt = (n: number | null | undefined) => (n === null || n === undefined ? '' : String(n));
  const prop = v.propeller ?? 'fixed_pitch';
  return {
    ...EMPTY_MY_VESSEL,
    bhp: txt(v.bhp),
    length_m: txt(v.length_m),
    beam_m: txt(v.beam_m),
    depth_m: txt(v.depth_m),
    pitch: prop.startsWith('variable') ? 'variable' : 'fixed',
    nozzle: prop.endsWith('nozzle'),
    propeller_diameter_m: txt(v.propeller_diameter_m),
    winch_drum_capacity_m: txt(v.winch_drum_capacity_m),
    region: v.region ?? '',
  };
}

/** Tipos de buque presentes en el catálogo, en orden de aparición. */
export function vesselTypes(vessels: Vessel[]): string[] {
  const out: string[] = [];
  for (const v of vessels)
    if (v.vessel_type && !out.includes(v.vessel_type)) out.push(v.vessel_type);
  return out;
}

/** Regiones presentes en el catálogo. */
export function vesselRegions(vessels: Vessel[]): string[] {
  const out: string[] = [];
  for (const v of vessels) if (v.region && !out.includes(v.region)) out.push(v.region);
  return out;
}

/** Filtro del catálogo por tipo y región (``''`` = todos; ``book`` = buques del libro). */
export function filterVessels(vessels: Vessel[], type: string, region: string): Vessel[] {
  return vessels.filter(
    (v) =>
      (!type || (type === 'book' ? !v.vessel_type : v.vessel_type === type)) &&
      (!region || v.region === region),
  );
}
