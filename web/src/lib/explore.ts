/**
 * Explorador de condiciones (``POST /simulate/explore``): variables, pedido, interpolación de
 * cuadros para la animación e indicadores del tablero.
 */
import type { DesignRequest, ExploreRequest, ExploreResponse, ScenarioIn } from '../api/client';

export type ExploreVariable = ExploreRequest['variable'];

export interface VariableDef {
  id: ExploreVariable;
  label: string;
  unit: string;
  from: number;
  to: number;
  min: number;
  max: number;
  step: number;
  digits: number;
}

export const VARIABLES: VariableDef[] = [
  {
    id: 'catch_kg',
    label: 'Captura en el copo',
    unit: 'kg',
    from: 0,
    to: 1500,
    min: 0,
    max: 20000,
    step: 50,
    digits: 0,
  },
  {
    id: 'speed_kn',
    label: 'Velocidad de arrastre',
    unit: 'kn',
    from: 2,
    to: 4,
    min: 0.5,
    max: 6,
    step: 0.1,
    digits: 1,
  },
  {
    id: 'warp_length_m',
    label: 'Cable filado',
    unit: 'm',
    from: 120,
    to: 320,
    min: 20,
    max: 3000,
    step: 10,
    digits: 0,
  },
  {
    id: 'fouling_level',
    label: 'Ensuciamiento de la red',
    unit: '× escenario',
    from: 0,
    to: 1,
    min: 0,
    max: 2,
    step: 0.1,
    digits: 1,
  },
  {
    id: 'current_kn',
    label: 'Corriente (+ a favor)',
    unit: 'kn',
    from: -0.8,
    to: 0.8,
    min: -2,
    max: 2,
    step: 0.1,
    digits: 1,
  },
  {
    id: 'mu_gear',
    label: 'Rozamiento del tren con el fondo',
    unit: 'μ',
    from: 0.3,
    to: 0.8,
    min: 0,
    max: 1.5,
    step: 0.05,
    digits: 2,
  },
];

export function variableDef(id: ExploreVariable): VariableDef {
  return VARIABLES.find((v) => v.id === id) ?? (VARIABLES[0] as VariableDef);
}

/** ``n`` valores parejos de ``from`` a ``to`` (2–10), redondeados al paso de la variable. */
export function valuesFor(def: VariableDef, from: number, to: number, n: number): number[] {
  const k = Math.max(2, Math.min(10, Math.round(n)));
  const round = (v: number) => Math.round(v / def.step) * def.step;
  return Array.from({ length: k }, (_, i) =>
    Number(round(from + ((to - from) * i) / (k - 1)).toFixed(4)),
  );
}

export interface ExploreForm {
  variable: ExploreVariable;
  from: number;
  to: number;
  steps: number;
  speed: number;
  catchKg: number;
  seabed: string | null;
  fouling: string | null;
  currentKn: number;
  warpLength: number | null;
  resolution: number;
  /** Especie para la selectividad del copo en cada estado (null = sin selectividad). */
  species?: string | null;
}

export const DEFAULT_EXPLORE: ExploreForm = {
  variable: 'catch_kg',
  from: 0,
  to: 1500,
  steps: 4,
  speed: 3,
  catchKg: 0,
  seabed: 'mixed',
  fouling: null,
  currentKn: 0,
  warpLength: null,
  resolution: 3,
};

/** Claves de la memoria de la sesión (abrir el explorador ya configurado desde otra vista). */
export const EXPLORE_FORM_KEY = 'explore:form';

/** Explorador por captura de 0 a ``catchKg`` con el fondo y la velocidad dados. */
export function catchPreset(catchKg: number, seabed: string | null, speed: number): ExploreForm {
  return {
    ...DEFAULT_EXPLORE,
    variable: 'catch_kg',
    from: 0,
    to: Math.max(100, catchKg),
    speed,
    seabed: seabed ?? DEFAULT_EXPLORE.seabed,
  };
}

export function exploreRequest(base: DesignRequest, f: ExploreForm): ExploreRequest {
  const def = variableDef(f.variable);
  const scenario: ScenarioIn = {
    catch_kg: f.catchKg,
    catch_bulk_density: 750,
    catch_body_density: 1070,
    catch_cp: 1,
    seabed: f.seabed,
    mu_gear: null,
    mu_door: null,
    coupled_doors: true,
    fouling: f.fouling,
    fouling_level: 1,
    current_kn: f.currentKn,
    warp_length_m: f.warpLength,
    haul_hours: 2,
    mesh_bending: null,
    mesh_bending_factor: 1,
  };
  if (f.variable === 'fouling_level' && !f.fouling) scenario.fouling = 'general';
  return {
    net: base.net,
    vessel: base.vessel ?? null,
    door: base.door ?? null,
    class_vessels: null,
    compat: base.compat ?? 'corrected',
    variable: f.variable,
    values: valuesFor(def, f.from, f.to, f.steps),
    speed_kn: f.speed,
    resolution: f.resolution,
    cn: null,
    ct: null,
    scenario,
    include_geometry: true,
    species: f.species ? [f.species] : [],
  };
}

// --- cuadros de la animación --------------------------------------------------------------

export interface Geometry {
  triangles: [number, number, number][];
  bars: [number, number][];
  bar_kind: string[];
  headrope: number[];
  footrope: number[];
  float_nodes: number[];
  doors: number[];
  warps: number[][];
}

export interface Frame {
  nodes: [number, number, number][];
  twine_tension_n: (number | number[])[];
  bar_tension_n: number[];
  fouling_tri: number[];
  /** Ángulo entre las dos familias de hilos de cada triángulo [°]. */
  opening_deg?: number[];
}

export function asGeometry(r: ExploreResponse): Geometry | null {
  return (r.geometry as unknown as Geometry | null) ?? null;
}

export function asFrames(r: ExploreResponse): Frame[] {
  return (r.frames as unknown as Frame[] | null) ?? [];
}

/** Índice de cuadro y fracción para la posición ``t`` ∈ [0, n−1] de la línea de tiempo. */
export function frameIndex(t: number, n: number): { i: number; f: number } {
  if (n <= 1) return { i: 0, f: 0 };
  const x = Math.min(n - 1, Math.max(0, Number.isFinite(t) ? t : 0));
  const i = Math.min(n - 2, Math.floor(x));
  return { i, f: x - i };
}

const lerp = (a: number, b: number, f: number) => a + (b - a) * f;

/** Posiciones interpoladas en ``t`` (Float32Array plano, x y z por nodo). */
export function nodesAt(frames: Frame[], t: number, out?: Float32Array): Float32Array {
  const first = frames[0];
  const n = first ? first.nodes.length : 0;
  const buf = out && out.length === n * 3 ? out : new Float32Array(n * 3);
  if (!first) return buf;
  const { i, f } = frameIndex(t, frames.length);
  const a = frames[i] as Frame;
  const b = (frames[i + 1] ?? a) as Frame;
  for (let k = 0; k < n; k++) {
    const pa = a.nodes[k] as [number, number, number];
    const pb = (b.nodes[k] ?? pa) as [number, number, number];
    buf[3 * k] = lerp(pa[0], pb[0], f);
    buf[3 * k + 1] = lerp(pa[1], pb[1], f);
    buf[3 * k + 2] = lerp(pa[2], pb[2], f);
  }
  return buf;
}

/** Valor interpolado de una serie escalar por estado en ``t``. */
export function valueAt(series: (number | null)[], t: number): number | null {
  const { i, f } = frameIndex(t, series.length);
  const a = series[i];
  const b = series[i + 1] ?? a;
  if (a == null || b == null) return a ?? null;
  return lerp(a, b, f);
}

// --- indicadores ---------------------------------------------------------------------------

export interface Indicator {
  key: string;
  label: string;
  unit: string;
  digits: number;
  /** ¿Más es mejor? (para colorear el delta; null = neutro). */
  better: 'higher' | 'lower' | null;
  get: (r: Record<string, unknown>) => number | null;
}

const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);
const sel = (key: 'l50' | 'sr') => (r: Record<string, unknown>) =>
  num((r.selectivity as Record<string, unknown>[] | undefined)?.[0]?.[key]);
const meshSummary = (key: string) => (r: Record<string, unknown>) =>
  num((r.mesh_summary as Record<string, unknown> | undefined)?.[key]);
const op = (key: string) => (r: Record<string, unknown>) =>
  num((r.operation as Record<string, unknown> | undefined)?.[key]);

export const INDICATORS: Indicator[] = [
  {
    key: 'dp',
    label: 'Separación de portones',
    unit: 'm',
    digits: 1,
    better: 'higher',
    get: (r) => num(r.door_spread_m),
  },
  {
    key: 'ah',
    label: 'Abertura horizontal',
    unit: 'm',
    digits: 1,
    better: 'higher',
    get: (r) => num(r.ah_m),
  },
  {
    key: 'av',
    label: 'Abertura vertical',
    unit: 'm',
    digits: 2,
    better: 'higher',
    get: (r) => num(r.av_m),
  },
  {
    key: 'pull',
    label: 'Tiro en el buque',
    unit: 'kgf',
    digits: 0,
    better: 'lower',
    get: (r) => num(r.towing_pull_kgf),
  },
  {
    key: 'warp',
    label: 'Tensión del cable (buque)',
    unit: 'kgf',
    digits: 0,
    better: 'lower',
    get: op('warp_tension_vessel_kgf'),
  },
  {
    key: 'angle',
    label: 'Ángulo del cable',
    unit: '°',
    digits: 1,
    better: null,
    get: op('warp_angle_deg'),
  },
  {
    key: 'fuel',
    label: 'Combustible',
    unit: 'L/h',
    digits: 1,
    better: 'lower',
    get: op('fuel_l_h'),
  },
  {
    key: 'fuel_kg',
    label: 'Combustible por kg',
    unit: 'L/kg',
    digits: 3,
    better: 'lower',
    get: op('fuel_l_per_kg'),
  },
  {
    key: 'swept',
    label: 'Área barrida',
    unit: 'km²/h',
    digits: 3,
    better: 'higher',
    get: op('swept_area_km2_h'),
  },
  {
    key: 'opening',
    label: 'Apertura de malla del copo',
    unit: '°',
    digits: 0,
    better: 'higher',
    get: meshSummary('opening_deg'),
  },
  {
    key: 'l50',
    label: 'L50 del copo',
    unit: 'talla',
    digits: 1,
    better: null,
    get: sel('l50'),
  },
  {
    key: 'sr',
    label: 'Rango de selección (SR)',
    unit: 'talla',
    digits: 1,
    better: null,
    get: sel('sr'),
  },
  {
    key: 'contact',
    label: 'Área en contacto con el fondo',
    unit: 'km²/h',
    digits: 3,
    better: 'lower',
    get: op('contact_area_km2_h'),
  },
];

/** Unidad de un indicador: la de la talla de la especie para L50 y SR. */
export function unitOf(r: ExploreResponse, ind: Indicator): string {
  if (ind.unit !== 'talla') return ind.unit;
  const s = (r.results[0] as Record<string, unknown> | undefined)?.selectivity as
    { unit?: string }[] | undefined;
  return s?.[0]?.unit ?? 'cm';
}

export function series(r: ExploreResponse, ind: Indicator): (number | null)[] {
  return r.results.map((x) => ind.get(x as Record<string, unknown>));
}
