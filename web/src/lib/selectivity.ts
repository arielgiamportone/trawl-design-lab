/**
 * Selectividad del copo (``POST /simulate/selectivity``): formulario, pedido, curvas y la prueba
 * de paso de un pez por una malla (la misma geometría que ``trawlkit.selectivity``).
 */
import type {
  DesignRequest,
  ScenarioIn,
  SelectivityRequest,
  SelectivityResponse,
  SpeciesOut,
} from '../api/client';
import { msg } from '../i18n';
import type { Frame, Geometry } from './explore';

export type Orientation = 'diamond' | 't90' | 'square';

const orientation = (id: Orientation) => ({
  id,
  get label() {
    return msg().selectivity.orientations[id].label;
  },
  get help() {
    return msg().selectivity.orientations[id].help;
  },
});

/** Orientaciones de la malla del copo (textos en el idioma activo). */
export const ORIENTATIONS: { id: Orientation; label: string; help: string }[] = [
  orientation('diamond'),
  orientation('t90'),
  orientation('square'),
];

export const orientationLabel = (o: string): string =>
  ORIENTATIONS.find((x) => x.id === o)?.label ?? o;

export interface SelForm {
  species: string[];
  /** Mallero del copo [mm] (null = el de la red). */
  meshMm: number | null;
  variants: Orientation[];
  catchKg: number;
  seabed: string | null;
  speed: number;
  resolution: number;
  contact: number;
}

export const DEFAULT_SEL: SelForm = {
  species: ['hake_hubbsi'],
  meshMm: null,
  variants: ['diamond', 't90'],
  catchKg: 300,
  seabed: 'mixed',
  speed: 3,
  resolution: 3,
  contact: 1,
};

/** Memoria de la sesión (abrir la vista ya configurada desde otra pestaña). */
export const SEL_FORM_KEY = 'selectivity:form';

export function selectivityRequest(base: DesignRequest, f: SelForm): SelectivityRequest {
  const scenario: ScenarioIn = {
    catch_kg: f.catchKg,
    catch_bulk_density: 750,
    catch_body_density: 1070,
    catch_cp: 1,
    seabed: f.seabed,
    mu_gear: null,
    mu_door: null,
    coupled_doors: true,
    fouling: null,
    fouling_level: 1,
    current_kn: 0,
    warp_length_m: null,
    haul_hours: 2,
    mesh_bending: true,
    mesh_bending_factor: 1,
    door_cl_factor: 1,
    door_cd_factor: 1,
  };
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
    scenario,
    species: f.species.length ? f.species : DEFAULT_SEL.species,
    variants: (f.variants.length ? f.variants : DEFAULT_SEL.variants).map((o) => ({
      orientation: o,
      mesh_mm: f.meshMm,
      hanging_ratio: null,
      label: null,
    })),
    contact: f.contact,
    zone_length_m: 3,
    lengths: null,
    include_geometry: true,
  };
}

// --- respuesta ------------------------------------------------------------------------------

export interface SelCurve {
  species: string;
  name: string;
  measure: string;
  unit: string;
  lengths: number[];
  retention: number[];
  l25: number | null;
  l50: number | null;
  l75: number | null;
  sr: number | null;
  sf: number | null;
  mesh_mm: number;
  range: '' | 'below' | 'above';
  fit_tri?: (number | null)[];
}

export interface SelVariant {
  label: string;
  orientation: Orientation;
  mesh_mm: number;
  hanging_ratio: number;
  codend_panels: {
    id: string;
    meshes_top: number;
    meshes_bottom: number;
    meshes_depth: number;
    mesh_mm: number;
    hanging_ratio: number | null;
    mesh_orientation: string;
  }[];
  result: Record<string, unknown>;
  curves: SelCurve[];
  geometry?: MeshGeometry;
  frame?: MeshFrame;
}

export interface MeshGeometry extends Geometry {
  tri_section?: string[];
  tri_orientation?: string[];
  tri_leg_mm?: number[];
  tri_twine_mm?: number[];
  tri_meshes?: number[];
}

export interface MeshFrame extends Frame {
  opening_deg?: number[];
  leg_i_mm?: number[];
  leg_j_mm?: number[];
  catch_fill?: number[];
}

export function asVariants(r: SelectivityResponse): SelVariant[] {
  return r.variants as unknown as SelVariant[];
}

/** Filas para el gráfico de retención: una por talla, una columna por variante. */
export function curveRows(
  variants: SelVariant[],
  species: string,
): { rows: Record<string, number>[]; keys: string[] } {
  const curves = variants
    .map((v) => ({ v, c: v.curves.find((c) => c.species === species) }))
    .filter((x): x is { v: SelVariant; c: SelCurve } => !!x.c);
  const first = curves[0]?.c;
  if (!first) return { rows: [], keys: [] };
  const rows = first.lengths.map((length, i) => {
    const row: Record<string, number> = { length };
    for (const { v, c } of curves) {
      const r = c.retention[i];
      if (r !== undefined) row[v.label] = r;
    }
    return row;
  });
  return { rows, keys: curves.map((x) => x.v.label) };
}

/** L50 con su unidad, o el rango cuando la curva no cruza el 50 % dentro de las tallas. */
export function l50Text(c: SelCurve, fmt: (v: number) => string): string {
  if (c.l50 !== null) return `${fmt(c.l50)} ${c.unit}`;
  const lo = c.lengths[0];
  const hi = c.lengths[c.lengths.length - 1];
  if (c.range === 'below' && lo !== undefined) return `< ${fmt(lo)} ${c.unit}`;
  if (c.range === 'above' && hi !== undefined) return `> ${fmt(hi)} ${c.unit}`;
  return '—';
}

// --- malla y prueba de paso -----------------------------------------------------------------

/** Área de la malla respecto de la abierta en cuadrado (patas nominales): ``sen β``. */
export function openFraction(openingDeg: number): number {
  return Math.max(0, Math.sin((openingDeg * Math.PI) / 180));
}

export interface MeshShape {
  openingDeg: number;
  legIMm: number;
  legJMm: number;
  twineMm: number;
}

/** Luz entre hilos de cada par de lados [mm] (alturas del paralelogramo menos el hilo). */
export function clearOpenings(m: MeshShape): { clearI: number; clearJ: number } {
  const sb = Math.sin((m.openingDeg * Math.PI) / 180);
  return { clearI: m.legJMm * sb - m.twineMm, clearJ: m.legIMm * sb - m.twineMm };
}

const THETAS = Array.from({ length: 91 }, (_, k) => (Math.PI * k) / 90);

/**
 * Talla máxima que pasa por la malla y el giro de la elipse con el que pasa. Elipse de semiejes
 * ``c·h·L/2`` y ``c·w·L/2`` dentro del paralelogramo de lados ``e_i`` (eje x) y ``e_j``.
 */
export function maxPassing(
  m: MeshShape,
  sp: Pick<SpeciesOut, 'height' | 'width' | 'compression' | 'unit'>,
): { length: number; theta: number } {
  const { clearI, clearJ } = clearOpenings(m);
  if (clearI <= 0 || clearJ <= 0) return { length: 0, theta: 0 };
  const perUnit = sp.unit === 'cm' ? 10 : 1;
  const a = (sp.compression * sp.height * perUnit) / 2;
  const b = (sp.compression * sp.width * perUnit) / 2;
  const beta = (m.openingDeg * Math.PI) / 180;
  const normals: [number, number, number][] = [
    [0, 1, clearI / 2],
    [Math.sin(beta), -Math.cos(beta), clearJ / 2],
  ];
  let best = { length: 0, theta: 0 };
  for (const th of THETAS) {
    const cu = Math.cos(th);
    const su = Math.sin(th);
    let lim = Infinity;
    for (const [nx, ny, h] of normals) {
      const nu = nx * cu + ny * su;
      const nv = -nx * su + ny * cu;
      const sigma = Math.hypot(a * nu, b * nv);
      lim = Math.min(lim, h / Math.max(sigma, 1e-12));
    }
    if (lim > best.length) best = { length: lim, theta: th };
  }
  return best;
}

/** Nudos de un parche de ``n × n`` mallas en el plano local [mm]: ``e_i`` sobre x. */
export function patchKnots(m: MeshShape, n: number): [number, number][][] {
  const beta = (m.openingDeg * Math.PI) / 180;
  const e1: [number, number] = [m.legIMm, 0];
  const e2: [number, number] = [m.legJMm * Math.cos(beta), m.legJMm * Math.sin(beta)];
  return Array.from({ length: n + 1 }, (_, a) =>
    Array.from({ length: n + 1 }, (_, b): [number, number] => [
      a * e1[0] + b * e2[0],
      a * e1[1] + b * e2[1],
    ]),
  );
}

/** Forma de la malla del triángulo ``k`` de una variante (null si faltan datos). */
export function meshAt(
  geometry: MeshGeometry | undefined,
  frame: MeshFrame | undefined,
  k: number,
): (MeshShape & { section: string; orientation: string; meshes: number }) | null {
  const deg = frame?.opening_deg?.[k];
  const li = frame?.leg_i_mm?.[k];
  const lj = frame?.leg_j_mm?.[k];
  const d = geometry?.tri_twine_mm?.[k];
  if (deg === undefined || li === undefined || lj === undefined || d === undefined) return null;
  return {
    openingDeg: deg,
    legIMm: li,
    legJMm: lj,
    twineMm: d,
    section: geometry?.tri_section?.[k] ?? '',
    orientation: geometry?.tri_orientation?.[k] ?? 'diamond',
    meshes: geometry?.tri_meshes?.[k] ?? 0,
  };
}

/** Primer triángulo del copo más abierto en la franja de escape (para abrir el zoom). */
export function defaultTriangle(v: SelVariant): number | null {
  const fit = v.curves[0]?.fit_tri ?? [];
  let best: number | null = null;
  let bestV = -1;
  fit.forEach((x, k) => {
    if (x !== null && x > bestV) {
      bestV = x;
      best = k;
    }
  });
  return best;
}
