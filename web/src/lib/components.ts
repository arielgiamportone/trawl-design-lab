/** Catálogo de componentes (Fase 13): tipos, columnas, filtros, lista de materiales y aportes. */
import type { CaseState } from '../state/model';
import { parseNumber } from './format';
import { loadJson, saveJson } from './storage';

export type ComponentKind = 'twine' | 'wire' | 'rope' | 'door' | 'float' | 'chain';

export const COMPONENT_KINDS: ComponentKind[] = ['twine', 'wire', 'rope', 'door', 'float', 'chain'];

export const COMPONENT_LABEL: Record<ComponentKind, string> = {
  twine: 'Paño e hilo',
  wire: 'Cable de acero',
  rope: 'Cabo',
  door: 'Portón',
  float: 'Boya',
  chain: 'Cadena',
};

/** Regiones del catálogo (``trawlkit.components.REGIONS``). */
export const REGION_LABEL: Record<string, string> = {
  global: 'Todo el mundo',
  latam: 'Latinoamérica',
  europe: 'Europa',
  africa: 'África',
  south_asia: 'Asia del Sur',
  southeast_asia: 'Sudeste asiático',
  north_america: 'Norteamérica',
};

export const STATUS_LABEL: Record<string, string> = {
  published: 'publicado',
  draft: 'borrador',
  user: 'aporte, sin verificar',
};

export interface Price {
  value: number;
  currency: string;
  unit: 'kg' | 'm' | 'unit';
  date: string;
  source: string;
}

export interface ProvenanceIn {
  kind?: string;
  note?: string;
  source?: string;
  page?: string;
}

/** Un componente del catálogo (``ComponentBase`` y los campos de su tipo). */
export interface Component {
  id: string;
  kind: ComponentKind;
  name: string;
  brand?: string | null;
  product?: string | null;
  country?: string | null;
  regions?: string[];
  generic_of?: string | null;
  status?: string;
  sources?: { key: string; title: string; url?: string }[];
  provenance?: Record<string, ProvenanceIn>;
  price?: Price | null;
  notes?: string[];
  [field: string]: unknown;
}

/** Columna de la tabla de un tipo: campo, título y unidad. */
export interface Column {
  field: string;
  label: string;
  unit?: string;
}

export const COLUMNS: Record<ComponentKind, Column[]> = {
  twine: [
    { field: 'material', label: 'Material' },
    { field: 'rtex', label: 'Rtex', unit: 'tex' },
    { field: 'diameter_mm', label: 'Ø', unit: 'mm' },
    { field: 'breaking_load_kgf', label: 'Rotura', unit: 'kgf' },
    { field: 'runnage_m_per_kg', label: 'Rendimiento', unit: 'm/kg' },
  ],
  wire: [
    { field: 'construction', label: 'Construcción' },
    { field: 'diameter_mm', label: 'Ø', unit: 'mm' },
    { field: 'weight_kg_per_m', label: 'Peso', unit: 'kg/m' },
    { field: 'breaking_load_t', label: 'Rotura', unit: 't' },
  ],
  rope: [
    { field: 'material', label: 'Material' },
    { field: 'diameter_mm', label: 'Ø', unit: 'mm' },
    { field: 'weight_kg_per_m', label: 'Peso', unit: 'kg/m' },
    { field: 'breaking_load_t', label: 'Rotura', unit: 't' },
  ],
  door: [
    { field: 'type', label: 'Tipo' },
    { field: 'area_m2', label: 'Superficie', unit: 'm²' },
    { field: 'weight_air_kg', label: 'Peso', unit: 'kg' },
    { field: 'hp_range', label: 'Buque', unit: 'hp' },
  ],
  float: [
    { field: 'material', label: 'Material' },
    { field: 'diameter_mm', label: 'Ø', unit: 'mm' },
    { field: 'buoyancy_kgf', label: 'Flotación', unit: 'kgf' },
    { field: 'max_depth_m', label: 'Prof. máx.', unit: 'm' },
  ],
  chain: [
    { field: 'link', label: 'Eslabón' },
    { field: 'link_diameter_mm', label: 'Ø', unit: 'mm' },
    { field: 'weight_kg_per_m', label: 'Peso', unit: 'kg/m' },
    { field: 'breaking_load_t', label: 'Rotura', unit: 't' },
  ],
};

export const DOOR_TYPE_LABEL: Record<string, string> = {
  flat: 'plano',
  flat_wood: 'plano de madera',
  v: 'en V',
  oval: 'oval',
  cambered: 'cambado',
  suberkrub: 'Süberkrüb',
  shrimp: 'camaronero',
};

/** Valor legible de una celda. */
export function cellText(item: Component, field: string): string {
  const v = item[field];
  if (v === undefined || v === null || v === '') return '—';
  if (field === 'hp_range' && Array.isArray(v)) {
    const [lo, hi] = v as number[];
    return lo === hi ? `${lo}` : `${lo}–${hi}`;
  }
  if (field === 'type' && typeof v === 'string') return DOOR_TYPE_LABEL[v] ?? v;
  if (typeof v === 'number') return v.toLocaleString('es-AR', { maximumFractionDigits: 3 });
  return String(v);
}

export function isGeneric(item: Component): boolean {
  return !item.brand;
}

export interface ComponentFilters {
  text: string;
  brand: string;
  region: string;
  genericOnly: boolean;
}

export const DEFAULT_COMPONENT_FILTERS: ComponentFilters = {
  text: '',
  brand: '',
  region: '',
  genericOnly: false,
};

/** Componentes que cumplen los filtros (un genérico vale en cualquier región). */
export function filterComponents(items: Component[], f: ComponentFilters): Component[] {
  const text = f.text.trim().toLowerCase();
  return items.filter((it) => {
    if (f.genericOnly && !isGeneric(it)) return false;
    if (f.brand && (it.brand ?? '') !== f.brand && !(f.brand === '-' && !it.brand)) return false;
    if (f.region && it.brand) {
      const regs = it.regions ?? [];
      if (!regs.includes(f.region) && !regs.includes('global')) return false;
    }
    if (text) {
      const hay = [it.id, it.name, it.brand, it.product, it.material, it.construction]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      if (!hay.includes(text)) return false;
    }
    return true;
  });
}

export function brands(items: Component[]): string[] {
  return [...new Set(items.map((i) => i.brand).filter((b): b is string => !!b))].sort();
}

// -- Lista de materiales ----------------------------------------------------------------------

export interface BomLine {
  key: string;
  label: string;
  quantity: number;
  unit: string;
  component_id?: string | null;
  component_kind?: string | null;
  component_name?: string | null;
  unit_price?: number | null;
  currency?: string | null;
  price_source?: string | null;
  cost?: number | null;
  note?: string | null;
}

export interface Bom {
  lines: BomLine[];
  totals: Record<string, number>;
  missing_prices: number;
}

export const UNIT_LABEL: Record<string, string> = { kg: 'kg', m: 'm', unit: 'u.' };

function csvCell(v: unknown): string {
  const s = v === null || v === undefined ? '' : String(v);
  return /[";\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/**
 * Lista de materiales en CSV (separador «;», coma decimal: abre bien en planillas en castellano).
 */
export function bomCsv(bom: Bom): string {
  const num = (n: number | null | undefined) =>
    n === null || n === undefined ? '' : String(n).replace('.', ',');
  const rows = [
    ['Ítem', 'Componente', 'Cantidad', 'Unidad', 'Precio unitario', 'Moneda', 'Costo', 'Nota'],
    ...bom.lines.map((l) => [
      l.label,
      l.component_name ?? l.component_id ?? '',
      num(l.quantity),
      UNIT_LABEL[l.unit] ?? l.unit,
      num(l.unit_price),
      l.currency ?? '',
      l.cost === null || l.cost === undefined ? 'sin precio' : num(l.cost),
      l.note ?? '',
    ]),
    ...Object.entries(bom.totals).map(([cur, v]) => ['Total', '', '', '', '', cur, num(v), '']),
  ];
  return rows.map((r) => r.map(csvCell).join(';')).join('\n') + '\n';
}

/** Clave con la que se guarda el precio de una línea: el componente, o la línea si no hay. */
export function priceKey(line: BomLine): string {
  return line.component_id ?? line.key;
}

// -- Precios del usuario ----------------------------------------------------------------------

export const PRICES_KEY = 'trawl-design-lab:prices:v1';

export function loadPrices(): Record<string, Price> {
  const raw = loadJson<Record<string, Price>>(PRICES_KEY);
  if (!raw || typeof raw !== 'object') return {};
  const out: Record<string, Price> = {};
  for (const [k, p] of Object.entries(raw)) {
    if (p && typeof p.value === 'number' && p.value >= 0 && typeof p.currency === 'string') {
      out[k] = { ...p, date: String(p.date ?? ''), source: String(p.source ?? 'usuario') };
    }
  }
  return out;
}

export function savePrices(prices: Record<string, Price>): void {
  saveJson(PRICES_KEY, prices);
}

// -- Aportes de usuarios ----------------------------------------------------------------------

/** Campos del formulario de aporte por tipo (además de nombre, marca, país y fuente). */
export const CONTRIB_FIELDS: Record<
  ComponentKind,
  { field: string; label: string; num: boolean }[]
> = {
  twine: [
    { field: 'material', label: 'Material (PA, PE, PP, PES, UHMWPE)', num: false },
    { field: 'diameter_mm', label: 'Diámetro [mm]', num: true },
    { field: 'rtex', label: 'Rtex [tex]', num: true },
    { field: 'breaking_load_kgf', label: 'Rotura [kgf]', num: true },
  ],
  wire: [
    { field: 'construction', label: 'Construcción (6x19, 6x24…)', num: false },
    { field: 'diameter_mm', label: 'Diámetro [mm]', num: true },
    { field: 'weight_kg_per_m', label: 'Peso [kg/m]', num: true },
    { field: 'breaking_load_t', label: 'Rotura [t]', num: true },
  ],
  rope: [
    { field: 'material', label: 'Material (PP, PE, PA, combinado…)', num: false },
    { field: 'diameter_mm', label: 'Diámetro [mm]', num: true },
    { field: 'weight_kg_per_m', label: 'Peso [kg/m]', num: true },
    { field: 'breaking_load_t', label: 'Rotura [t]', num: true },
  ],
  door: [
    { field: 'type', label: 'Tipo (flat, v, oval, suberkrub…)', num: false },
    { field: 'length_m', label: 'Largo [m]', num: true },
    { field: 'height_m', label: 'Alto [m]', num: true },
    { field: 'weight_air_kg', label: 'Peso en aire [kg]', num: true },
  ],
  float: [
    { field: 'material', label: 'Material', num: false },
    { field: 'diameter_mm', label: 'Diámetro [mm]', num: true },
    { field: 'buoyancy_kgf', label: 'Flotación [kgf]', num: true },
    { field: 'max_depth_m', label: 'Profundidad máxima [m]', num: true },
  ],
  chain: [
    { field: 'link', label: 'Eslabón (corto, largo)', num: false },
    { field: 'link_diameter_mm', label: 'Diámetro del eslabón [mm]', num: true },
    { field: 'weight_kg_per_m', label: 'Peso [kg/m]', num: true },
    { field: 'breaking_load_t', label: 'Rotura [t]', num: true },
  ],
};

/** Normaliza los aportes leídos de un proyecto o de localStorage (descarta los inválidos). */
export function sanitizeContributions(raw: unknown): Component[] {
  if (!Array.isArray(raw)) return [];
  return (raw as Component[])
    .filter(
      (c) =>
        !!c &&
        typeof c.id === 'string' &&
        typeof c.name === 'string' &&
        COMPONENT_KINDS.includes(c.kind),
    )
    .map((c) => ({ ...c, status: 'user' }));
}

/** Armado del componente del formulario de aportes (los números aceptan coma decimal). */
export function draftComponent(
  kind: ComponentKind,
  values: Record<string, string>,
): Record<string, unknown> {
  const out: Record<string, unknown> = {
    kind,
    id: contributionId(kind, values.name ?? ''),
    name: (values.name ?? '').trim(),
    status: 'user',
  };
  if (values.brand?.trim()) out.brand = values.brand.trim();
  if (values.country?.trim()) out.country = values.country.trim().toUpperCase();
  if (values.source?.trim()) out.notes = [`Fuente: ${values.source.trim()}`];
  for (const f of CONTRIB_FIELDS[kind]) {
    const t = (values[f.field] ?? '').trim();
    if (!t) continue;
    out[f.field] = f.num ? (parseNumber(t) ?? t) : t;
  }
  if (kind === 'door' && typeof out.length_m === 'number' && typeof out.height_m === 'number') {
    out.area_m2 = Math.round(out.length_m * out.height_m * 1000) / 1000;
  }
  return out;
}

/** Id de un aporte a partir del nombre: «user_<tipo>_<nombre>». */
export function contributionId(kind: ComponentKind, name: string): string {
  const slug = name
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '')
    .slice(0, 40);
  return `user_${kind}_${slug || 'aporte'}`;
}

export const REPO_URL = 'https://github.com/arielgiamportone/trawl-design-lab';

/** Enlace a un *issue* nuevo con la plantilla de componentes y el aporte en JSON. */
export function issueUrl(item: Component): string {
  const body = [
    `Tipo: ${COMPONENT_LABEL[item.kind]}`,
    `Fuente: ${String(item.notes?.[0] ?? '')}`,
    '',
    '```json',
    JSON.stringify(item, null, 2),
    '```',
  ].join('\n');
  const q = new URLSearchParams({
    template: 'componente.yml',
    title: `Componente: ${item.name}`,
    labels: 'componente',
    datos: body,
  });
  return `${REPO_URL}/issues/new?${q.toString()}`;
}

// -- Aplicar al caso --------------------------------------------------------------------------

/** Parámetro del caso que fija un componente de cada tipo (el portón va en ``door``). */
export const CASE_PARAM: Partial<Record<ComponentKind, string>> = {
  wire: 'warp_id',
  float: 'float_id',
  twine: 'twine_id',
  chain: 'chain_id',
};

export type RopeRole = 'headrope_rope' | 'footrope_rope';

/** Estado del caso con el componente elegido (los cabos van a la lima o al burlón). */
export function applyComponent(
  state: CaseState,
  item: Component,
  role: RopeRole = 'headrope_rope',
): CaseState {
  if (item.kind === 'door') return { ...state, door: item.id };
  const param = item.kind === 'rope' ? role : CASE_PARAM[item.kind];
  if (!param) return state;
  const params = { ...state.params, [param]: item.id };
  // Con una boya del catálogo, el número sale de la flotación requerida.
  if (item.kind === 'float') delete params.float_count;
  return { ...state, params };
}

/** ¿El componente es el que usa el caso? */
export function inCase(state: CaseState, item: Component): boolean {
  if (item.kind === 'door') return state.door === item.id;
  if (item.kind === 'rope') {
    return state.params.headrope_rope === item.id || state.params.footrope_rope === item.id;
  }
  const param = CASE_PARAM[item.kind];
  return !!param && state.params[param] === item.id;
}

/**
 * Componentes de un armado del optimizador (``AssemblyOut.components``) aplicados al caso.
 * ``baseDoor`` es el portón del caso calculado: si el armado lo conserva (p. ej. el portón del
 * plano de una red del catálogo FAO), no se fija ``door``.
 */
export function applyAssembly(
  state: CaseState,
  assembly: { components: Record<string, string | null>; float_count: number | null },
  baseDoor?: string,
): CaseState {
  const c = assembly.components;
  const params = { ...state.params };
  const slots: [string, string][] = [
    ['warp', 'warp_id'],
    ['float', 'float_id'],
    ['twine', 'twine_id'],
  ];
  for (const [key, param] of slots) {
    const id = c[key];
    if (id) params[param] = id;
    else delete params[param];
  }
  if (c.float && assembly.float_count) params.float_count = String(assembly.float_count);
  const door = !c.door || c.door === baseDoor ? state.door : c.door;
  return { ...state, door, params };
}
