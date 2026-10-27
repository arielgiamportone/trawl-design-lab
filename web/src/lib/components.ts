/** Catálogo de componentes (Fase 13): tipos, columnas, filtros, lista de materiales y aportes. */
import { getLang, msg } from '../i18n';
import type { CaseState } from '../state/model';
import { fieldUnit, provValueText } from './catalog';
import { fmtNum, parseNumber } from './format';
import { liveRecord } from './liveRecord';
import { loadJson, saveJson } from './storage';
import { getUnits, toCanonical, toDisplay, unitLabel } from './units';

export type ComponentKind = 'twine' | 'wire' | 'rope' | 'door' | 'float' | 'chain' | 'shackle';

export const COMPONENT_KINDS: ComponentKind[] = [
  'twine',
  'wire',
  'rope',
  'door',
  'float',
  'chain',
  'shackle',
];

/** Tipos de componente en el idioma activo (objeto vivo: se lee al usarlo). */
export const COMPONENT_LABEL: Record<ComponentKind, string> = liveRecord(
  () => msg().components.kind,
);

/**
 * Regiones del catálogo (``trawlkit.components.REGIONS``) en el idioma activo. Objeto vivo con
 * la misma forma de siempre: lo importan también ``lib/params`` y el asistente.
 */
export const REGION_LABEL: Record<string, string> = liveRecord(() => msg().components.region);

export const STATUS_LABEL: Record<string, string> = liveRecord(() => msg().components.status);

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

/** Columna de la tabla de un tipo: campo, título y unidad (la métrica del motor). */
export interface Column {
  field: string;
  label: string;
  unit?: string;
}

/** Campos y unidades métricas de las columnas de cada tipo (los títulos van en ``columns``). */
const COLUMN_FIELDS: Record<ComponentKind, [string, string?][]> = {
  twine: [
    ['material'],
    ['rtex', 'tex'],
    ['diameter_mm', 'mm'],
    ['breaking_load_kgf', 'kgf'],
    ['runnage_m_per_kg', 'm/kg'],
  ],
  wire: [
    ['construction'],
    ['diameter_mm', 'mm'],
    ['weight_kg_per_m', 'kg/m'],
    ['breaking_load_t', 't'],
  ],
  rope: [
    ['material'],
    ['diameter_mm', 'mm'],
    ['weight_kg_per_m', 'kg/m'],
    ['breaking_load_t', 't'],
  ],
  door: [['type'], ['area_m2', 'm²'], ['weight_air_kg', 'kg'], ['hp_range', 'hp']],
  float: [['material'], ['diameter_mm', 'mm'], ['buoyancy_kgf', 'kgf'], ['max_depth_m', 'm']],
  chain: [
    ['link'],
    ['link_diameter_mm', 'mm'],
    ['weight_kg_per_m', 'kg/m'],
    ['breaking_load_t', 't'],
  ],
  shackle: [
    ['size'],
    ['wll_t', 't'],
    ['breaking_load_t', 't'],
    ['pin_diameter_mm', 'mm'],
    ['weight_kg', 'kg'],
  ],
};

/** Columnas de la tabla de un tipo, con los títulos en el idioma activo. */
export function columns(kind: ComponentKind): Column[] {
  const labels = msg().components.col;
  return COLUMN_FIELDS[kind].map(([field, unit]) =>
    unit
      ? { field, label: labels[field] ?? field, unit }
      : { field, label: labels[field] ?? field },
  );
}

export const DOOR_TYPE_LABEL: Record<string, string> = liveRecord(() => msg().components.doorType);

/**
 * Valor legible de una celda. Con ``unit`` (la métrica de la columna) el número se convierte al
 * sistema activo, sin la unidad (va en el título); con ``withUnit``, la unidad se deduce del
 * nombre del campo y se agrega en imperial (tablas de procedencia, sin unidad en el título).
 */
export function cellText(item: Component, field: string, unit?: string, withUnit = false): string {
  const v = item[field];
  if (v === undefined || v === null || v === '') return '—';
  if (field === 'hp_range' && Array.isArray(v)) {
    const [lo, hi] = v as number[];
    return lo === hi ? `${lo}` : `${lo}–${hi}`;
  }
  if (field === 'type' && typeof v === 'string') return DOOR_TYPE_LABEL[v] ?? v;
  if (typeof v === 'number') {
    if (withUnit) return provValueText(v, fieldUnit(field));
    return fmtNum(unit ? toDisplay(v, unit) : v, { maximumFractionDigits: 3 });
  }
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

/** Unidades de cantidad de la lista de materiales (objeto vivo, en el idioma activo). */
export const UNIT_LABEL: Record<string, string> = liveRecord(() => msg().components.unit);

/**
 * Unidad métrica del motor de la cantidad de una línea (``kg``, ``m``) y la de su precio por
 * unidad (``$/kg``, ``$/m``); ``null`` para las piezas («u.»), que no se convierten.
 */
const QTY_UNIT: Record<string, { qty: string; price: string }> = {
  kg: { qty: 'kg', price: '$/kg' },
  m: { qty: 'm', price: '$/m' },
};

/** Unidad de la cantidad de una línea en el sistema activo («kg»/«lb», «m»/«ft», «u.»). */
export function bomUnitLabel(unit: string): string {
  const u = QTY_UNIT[unit];
  return u ? unitLabel(u.qty) : (UNIT_LABEL[unit] ?? unit);
}

/** Cantidad de una línea en el sistema activo. */
export function bomQuantity(line: Pick<BomLine, 'quantity' | 'unit'>): number {
  const u = QTY_UNIT[line.unit];
  return u ? toDisplay(line.quantity, u.qty) : line.quantity;
}

/** Precio por unidad de cantidad en el sistema activo (por lb, por ft) desde el del motor. */
export function priceToDisplay(value: number, unit: string): number {
  const u = QTY_UNIT[unit];
  return u ? toDisplay(value, u.price) : value;
}

/** Precio por unidad de cantidad del motor (por kg, por m) desde el que escribió el usuario. */
export function priceToCanonical(value: number, unit: string): number {
  const u = QTY_UNIT[unit];
  return u ? toCanonical(value, u.price) : value;
}

/**
 * Lista de materiales en CSV. En español, separador «;» y coma decimal (abre bien en planillas
 * en castellano); en inglés, «,» y punto decimal. Encabezados en el idioma activo y cantidades y
 * precios por unidad en el sistema de unidades activo.
 */
export function bomCsv(bom: Bom): string {
  const T = msg().components.csv;
  const es = getLang() === 'es';
  const sep = es ? ';' : ',';
  const num = (n: number | null | undefined) =>
    n === null || n === undefined ? '' : es ? String(n).replace('.', ',') : String(n);
  // En métrico, los números del motor tal cual; convertidos, con 6 decimales como mucho.
  const round = (n: number) => (getUnits() === 'imperial' ? Math.round(n * 1e6) / 1e6 : n);
  const cell = (v: unknown): string => {
    const s = v === null || v === undefined ? '' : String(v);
    return s.includes(sep) || /["\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const rows = [
    T.head,
    ...bom.lines.map((l) => [
      l.label,
      l.component_name ?? l.component_id ?? '',
      num(round(bomQuantity(l))),
      bomUnitLabel(l.unit),
      num(l.unit_price == null ? l.unit_price : round(priceToDisplay(l.unit_price, l.unit))),
      l.currency ?? '',
      l.cost === null || l.cost === undefined ? T.noPrice : num(l.cost),
      l.note ?? '',
    ]),
    ...Object.entries(bom.totals).map(([cur, v]) => [T.total, '', '', '', '', cur, num(v), '']),
  ];
  return rows.map((r) => r.map(cell).join(sep)).join('\n') + '\n';
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
      out[k] = {
        ...p,
        date: String(p.date ?? ''),
        source: String(p.source ?? msg().components.priceSource),
      };
    }
  }
  return out;
}

export function savePrices(prices: Record<string, Price>): void {
  saveJson(PRICES_KEY, prices);
}

/** Normaliza una lista de precios leída de un proyecto (descarta los precios inválidos). */
export function sanitizePrices(raw: unknown): Record<string, Price> {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {};
  const out: Record<string, Price> = {};
  for (const [k, p] of Object.entries(raw as Record<string, Partial<Price>>)) {
    if (
      p &&
      typeof p.value === 'number' &&
      p.value >= 0 &&
      typeof p.currency === 'string' &&
      (p.unit === 'kg' || p.unit === 'm' || p.unit === 'unit')
    ) {
      out[k] = {
        value: p.value,
        currency: p.currency,
        unit: p.unit,
        date: String(p.date ?? ''),
        source: String(p.source ?? msg().components.priceSource),
      };
    }
  }
  return out;
}

/**
 * Precios importados sobre los que ya había: los de la planilla reemplazan a los de la misma
 * clave y el resto se conserva.
 */
export function mergePrices(
  current: Record<string, Price>,
  imported: Record<string, Price>,
): Record<string, Price> {
  return { ...current, ...sanitizePrices(imported) };
}

/** Líneas de la lista de materiales para la plantilla de precios (``POST /prices/export``). */
export function priceLines(bom: Bom | undefined): {
  key: string;
  label: string;
  unit: string;
  component_id?: string | null;
}[] {
  return (bom?.lines ?? []).map((l) => ({
    key: l.key,
    label: l.component_name ? `${l.label}: ${l.component_name}` : l.label,
    unit: l.unit,
    component_id: l.component_id ?? null,
  }));
}

// -- Aportes de usuarios ----------------------------------------------------------------------

export interface ContribField {
  field: string;
  /** Rótulo en el idioma activo, con la unidad del sistema activo entre corchetes. */
  label: string;
  num: boolean;
  /** Unidad métrica del motor (lo escrito se convierte a ella antes de validar). */
  unit?: string;
}

/** Campos y unidades métricas del formulario de aporte por tipo. */
const CONTRIB_UNITS: Record<ComponentKind, [string, string?][]> = {
  twine: [['material'], ['diameter_mm', 'mm'], ['rtex', 'tex'], ['breaking_load_kgf', 'kgf']],
  wire: [
    ['construction'],
    ['diameter_mm', 'mm'],
    ['weight_kg_per_m', 'kg/m'],
    ['breaking_load_t', 't'],
  ],
  rope: [
    ['material'],
    ['diameter_mm', 'mm'],
    ['weight_kg_per_m', 'kg/m'],
    ['breaking_load_t', 't'],
  ],
  door: [['type'], ['length_m', 'm'], ['height_m', 'm'], ['weight_air_kg', 'kg']],
  float: [['material'], ['diameter_mm', 'mm'], ['buoyancy_kgf', 'kgf'], ['max_depth_m', 'm']],
  chain: [
    ['link'],
    ['link_diameter_mm', 'mm'],
    ['weight_kg_per_m', 'kg/m'],
    ['breaking_load_t', 't'],
  ],
  shackle: [['size'], ['body_diameter_mm', 'mm'], ['wll_t', 't'], ['weight_kg', 'kg']],
};

/** Campos del formulario de aporte por tipo (además de nombre, marca, país y fuente). */
export function contribFields(kind: ComponentKind): ContribField[] {
  const labels = msg().components.contrib[kind] ?? {};
  return CONTRIB_UNITS[kind].map(([field, unit]) => {
    const text = labels[field] ?? field;
    return unit
      ? { field, label: `${text} [${unitLabel(unit)}]`, num: true, unit }
      : { field, label: text, num: false };
  });
}

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
  if (values.source?.trim()) out.notes = [msg().components.sourceNote(values.source.trim())];
  for (const f of contribFields(kind)) {
    const t = (values[f.field] ?? '').trim();
    if (!t) continue;
    if (!f.num) {
      out[f.field] = t;
      continue;
    }
    // Lo escrito está en el sistema activo; el motor recibe siempre métrico.
    const n = parseNumber(t);
    out[f.field] = n === null ? t : f.unit ? Number(toCanonical(n, f.unit).toPrecision(10)) : n;
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
  const T = msg().components.issue;
  const body = [
    T.kind(COMPONENT_LABEL[item.kind]),
    T.source(String(item.notes?.[0] ?? '')),
    '',
    '```json',
    JSON.stringify(item, null, 2),
    '```',
  ].join('\n');
  const q = new URLSearchParams({
    template: 'componente.yml',
    title: T.title(item.name),
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
