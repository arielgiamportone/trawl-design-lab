/**
 * Economía de la operación (Fase 16): campos del formulario, conversión al pedido de la API y
 * memoria en el navegador. Los precios empiezan en blanco: la app no inventa precios.
 */
import type { EconomicInputs, TripEconomics } from '../api/client';
import { msg } from '../i18n';
import { parseNumber, toInput } from './format';
import { liveRecord } from './liveRecord';
import { loadJson, saveJson } from './storage';
import { getUnits, toCanonical, toDisplay, unitLabel } from './units';

export const ECO_KEY = 'trawl-design-lab:economics';
export const ECO_VIEW_KEY = 'trawl-design-lab:economics-view';

export type FieldKind = 'money' | 'number' | 'int' | 'fraction';

export interface EcoField {
  key: keyof EconomicInputs & string;
  label: string;
  /** Unidad que se muestra (en el idioma y el sistema de unidades activos). */
  unit?: string;
  kind: FieldKind;
  /** Valor que usa el motor si se deja en blanco (constantes de ingeniería, A VERIFICAR). */
  fallback?: number;
  help?: string;
  /**
   * Unidad métrica del motor con la que se convierte lo escrito (``'kg/h'``, ``'$/kg'``,
   * ``'$/L'``): en imperial se escribe por lb o por galón y la API recibe por kg o por litro.
   */
  conv?: string;
  /** Se escribe en % y viaja como fracción. */
  percent?: boolean;
}

export interface EcoGroup {
  id: string;
  title: string;
  fields: EcoField[];
}

/** Definición de un campo: lo que no depende del idioma. */
interface FieldDef {
  key: keyof EconomicInputs & string;
  kind: FieldKind;
  /** Unidad fija (no se traduce ni se convierte). */
  unit?: string;
  /** Precio por unidad de cantidad: ``'kg'`` o ``'L'`` («por kg», «por L» / «per lb»…). */
  per?: 'kg' | 'L';
  conv?: string;
  percent?: boolean;
  fallback?: number;
}

const GROUP_DEFS: { id: string; fields: FieldDef[] }[] = [
  {
    id: 'captura',
    fields: [
      { key: 'catch_kg_h', kind: 'number', conv: 'kg/h' },
      { key: 'reference_speed_kn', unit: 'kn', kind: 'number', fallback: 3 },
      { key: 'price_kg', kind: 'money', per: 'kg', conv: '$/kg' },
    ],
  },
  {
    id: 'marea',
    fields: [
      { key: 'hauls_per_trip', kind: 'int', fallback: 4 },
      { key: 'haul_hours', unit: 'h', kind: 'number', fallback: 2 },
      { key: 'handling_hours', unit: 'h', kind: 'number', fallback: 0.5 },
      { key: 'steaming_hours', unit: 'h', kind: 'number', fallback: 4 },
      { key: 'trip_days', kind: 'number', fallback: 1 },
      { key: 'trips_per_year', kind: 'number', fallback: 150 },
    ],
  },
  {
    id: 'combustible',
    fields: [
      { key: 'fuel_price_l', kind: 'money', per: 'L', conv: '$/L' },
      { key: 'lube_price_l', kind: 'money', per: 'L', conv: '$/L' },
      { key: 'lube_ratio', unit: 'L/L', kind: 'number', fallback: 0.01 },
      { key: 'sfc_kg_kwh', unit: 'kg/kWh', kind: 'number', fallback: 0.22 },
      { key: 'steaming_load', unit: '0–1', kind: 'fraction', fallback: 0.8 },
    ],
  },
  {
    id: 'tripulacion',
    fields: [
      { key: 'crew_share', unit: '%', kind: 'fraction', percent: true },
      { key: 'crew_size', kind: 'int' },
      { key: 'wage_day', kind: 'money' },
    ],
  },
  {
    id: 'aparejo',
    fields: [
      { key: 'gear_cost', kind: 'money' },
      { key: 'gear_life_hours', kind: 'number', fallback: 2000 },
      { key: 'gear_repair_year', kind: 'fraction', percent: true, fallback: 0.1 },
      { key: 'trip_costs', kind: 'money' },
      { key: 'annual_costs', kind: 'money' },
    ],
  },
];

/** Grupos y campos del formulario, con rótulos y unidades en el idioma y el sistema activos. */
export function groups(): EcoGroup[] {
  const T = msg().economics;
  return GROUP_DEFS.map((g) => ({
    id: g.id,
    title: T.groups[g.id] ?? g.id,
    fields: g.fields.map((d) => {
      const text = T.fields[d.key];
      const unit = d.per
        ? T.per(unitLabel(d.per))
        : d.conv
          ? unitLabel(d.conv)
          : (text?.unit ?? d.unit);
      const f: EcoField = { key: d.key, label: text?.label ?? d.key, kind: d.kind };
      if (unit) f.unit = unit;
      if (d.fallback !== undefined) f.fallback = d.fallback;
      if (text?.help) f.help = text.help;
      if (d.conv) f.conv = d.conv;
      if (d.percent) f.percent = true;
      return f;
    }),
  }));
}

/**
 * Texto del campo a partir de lo guardado. Lo guardado está siempre en métrico (por kg, por
 * litro): en métrico se muestra tal cual se escribió; en imperial, convertido.
 */
export function fieldText(field: Pick<EcoField, 'conv'>, stored: string | undefined): string {
  const text = stored ?? '';
  if (!field.conv || getUnits() !== 'imperial') return text;
  const n = parseNumber(text);
  if (n === null) return text;
  return toInput(Number(toDisplay(n, field.conv).toPrecision(6)));
}

/** Lo que se guarda a partir de lo escrito: en imperial, convertido a métrico. */
export function storedText(field: Pick<EcoField, 'conv'>, text: string): string {
  if (!field.conv || getUnits() !== 'imperial') return text;
  const n = parseNumber(text);
  if (n === null) return text;
  return String(Number(toCanonical(n, field.conv).toPrecision(10)));
}

export interface EcoForm {
  currency: string;
  crewMode: 'share' | 'wage' | 'none';
  values: Record<string, string>;
}

export const EMPTY_FORM: EcoForm = { currency: 'USD', crewMode: 'share', values: {} };

export function loadForm(): EcoForm {
  const f = loadJson<EcoForm>(ECO_KEY);
  return f && typeof f.values === 'object' ? { ...EMPTY_FORM, ...f } : EMPTY_FORM;
}

export function saveForm(f: EcoForm): void {
  saveJson(ECO_KEY, f);
}

const FIELDS = GROUP_DEFS.flatMap((g) => g.fields);

/**
 * Valor del campo (lo guardado, en métrico): los porcentajes se escriben en % y viajan como
 * fracción.
 */
function value(field: FieldDef, text: string | undefined): number | null {
  const n = parseNumber(text ?? '');
  if (n === null || n < 0) return null;
  if (field.kind === 'fraction') return field.percent ? n / 100 : n;
  if (field.kind === 'int') return Math.round(n);
  return n;
}

/** Pedido ``economics`` de la API: sólo los campos con valor (el resto, el motor decide). */
export function toInputs(f: EcoForm): EconomicInputs {
  const out: Record<string, unknown> = {
    currency: (f.currency || 'USD').toUpperCase().slice(0, 3).padEnd(3, 'X'),
    crew_mode: f.crewMode,
  };
  for (const field of FIELDS) {
    const v = value(field, f.values[field.key]);
    if (v !== null) out[field.key] = v;
  }
  return out as EconomicInputs;
}

/** Cantidad de rubros cargados (para el resumen del formulario). */
export function filled(f: EcoForm): number {
  return FIELDS.filter((field) => value(field, f.values[field.key]) !== null).length;
}

/** Rubros del costo en el idioma activo (objeto vivo: se lee al usarlo). */
export const COST_LABELS: Record<string, string> = liveRecord(() => msg().economics.costs);

/**
 * Filas para el gráfico por velocidad (montos en miles si son grandes); el gasoil y el costo por
 * kg, en el sistema de unidades activo (galones, por lb).
 */
export function curveRows(trips: TripEconomics[]): Record<string, number | null>[] {
  return trips.map((t) => ({
    speed: t.speed_kn,
    revenue: t.revenue ?? null,
    cost: t.total_cost ?? null,
    margin: t.margin ?? null,
    costKg: t.cost_per_kg == null ? null : toDisplay(t.cost_per_kg, '$/kg'),
    fuel: toDisplay(t.fuel_l, 'L'),
  }));
}
