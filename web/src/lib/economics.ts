/**
 * Economía de la operación (Fase 16): campos del formulario, conversión al pedido de la API y
 * memoria en el navegador. Los precios empiezan en blanco: la app no inventa precios.
 */
import type { EconomicInputs, TripEconomics } from '../api/client';
import { parseNumber } from './format';
import { loadJson, saveJson } from './storage';

export const ECO_KEY = 'trawl-design-lab:economics';
export const ECO_VIEW_KEY = 'trawl-design-lab:economics-view';

export type FieldKind = 'money' | 'number' | 'int' | 'fraction';

export interface EcoField {
  key: keyof EconomicInputs & string;
  label: string;
  unit?: string;
  kind: FieldKind;
  /** Valor que usa el motor si se deja en blanco (constantes de ingeniería, A VERIFICAR). */
  fallback?: number;
  help?: string;
}

export interface EcoGroup {
  id: string;
  title: string;
  fields: EcoField[];
}

export const GROUPS: EcoGroup[] = [
  {
    id: 'captura',
    title: 'Captura e ingreso',
    fields: [
      {
        key: 'catch_kg_h',
        label: 'Captura por hora de arrastre',
        unit: 'kg/h',
        kind: 'number',
        help: 'A la velocidad de referencia; a otras velocidades escala con el área barrida.',
      },
      {
        key: 'reference_speed_kn',
        label: 'Velocidad de referencia',
        unit: 'kn',
        kind: 'number',
        fallback: 3,
      },
      { key: 'price_kg', label: 'Precio en playa', unit: 'por kg', kind: 'money' },
    ],
  },
  {
    id: 'marea',
    title: 'Marea',
    fields: [
      { key: 'hauls_per_trip', label: 'Lances por marea', kind: 'int', fallback: 4 },
      { key: 'haul_hours', label: 'Duración del lance', unit: 'h', kind: 'number', fallback: 2 },
      {
        key: 'handling_hours',
        label: 'Calado y virado por lance',
        unit: 'h',
        kind: 'number',
        fallback: 0.5,
      },
      {
        key: 'steaming_hours',
        label: 'Navegación ida y vuelta',
        unit: 'h',
        kind: 'number',
        fallback: 4,
      },
      { key: 'trip_days', label: 'Días por marea', kind: 'number', fallback: 1 },
      { key: 'trips_per_year', label: 'Mareas por año', kind: 'number', fallback: 150 },
    ],
  },
  {
    id: 'combustible',
    title: 'Combustible',
    fields: [
      { key: 'fuel_price_l', label: 'Precio del gasoil', unit: 'por L', kind: 'money' },
      { key: 'lube_price_l', label: 'Precio del lubricante', unit: 'por L', kind: 'money' },
      {
        key: 'lube_ratio',
        label: 'Lubricante por litro de gasoil',
        unit: 'L/L',
        kind: 'number',
        fallback: 0.01,
      },
      {
        key: 'sfc_kg_kwh',
        label: 'Consumo específico del motor',
        unit: 'kg/kWh',
        kind: 'number',
        fallback: 0.22,
      },
      {
        key: 'steaming_load',
        label: 'Carga del motor navegando',
        unit: '0–1',
        kind: 'fraction',
        fallback: 0.8,
      },
    ],
  },
  {
    id: 'tripulacion',
    title: 'Tripulación',
    fields: [
      {
        key: 'crew_share',
        label: 'Parte de la tripulación',
        unit: '%',
        kind: 'fraction',
        help: 'Del ingreso, después de descontar gasoil, lubricante y gastos de la marea.',
      },
      { key: 'crew_size', label: 'Tripulantes (a jornal)', kind: 'int' },
      { key: 'wage_day', label: 'Jornal por día', kind: 'money' },
    ],
  },
  {
    id: 'aparejo',
    title: 'Red, aparejo y otros gastos',
    fields: [
      { key: 'gear_cost', label: 'Costo de la red y el aparejo', kind: 'money' },
      {
        key: 'gear_life_hours',
        label: 'Vida útil',
        unit: 'h de arrastre',
        kind: 'number',
        fallback: 2000,
      },
      {
        key: 'gear_repair_year',
        label: 'Reparación por año',
        unit: '% del costo',
        kind: 'fraction',
        fallback: 0.1,
      },
      {
        key: 'trip_costs',
        label: 'Hielo, víveres, carnada y puerto',
        unit: 'por marea',
        kind: 'money',
      },
      { key: 'annual_costs', label: 'Permisos, seguro y fijos', unit: 'por año', kind: 'money' },
    ],
  },
];

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

const FIELDS = GROUPS.flatMap((g) => g.fields);

/** Valor del campo: los porcentajes se escriben en % y viajan como fracción. */
function value(field: EcoField, text: string | undefined): number | null {
  const n = parseNumber(text ?? '');
  if (n === null || n < 0) return null;
  if (field.kind === 'fraction')
    return field.unit === '%' || field.unit === '% del costo' ? n / 100 : n;
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

export const COST_LABELS: Record<string, string> = {
  fuel: 'Combustible',
  lube: 'Lubricante',
  crew: 'Tripulación',
  gear: 'Red y aparejo',
  trip: 'Gastos de la marea',
  annual: 'Fijos anuales',
};

/** Filas para el gráfico por velocidad (montos en miles si son grandes). */
export function curveRows(trips: TripEconomics[]): Record<string, number | null>[] {
  return trips.map((t) => ({
    speed: t.speed_kn,
    revenue: t.revenue ?? null,
    cost: t.total_cost ?? null,
    margin: t.margin ?? null,
    costKg: t.cost_per_kg ?? null,
    fuel: t.fuel_l,
  }));
}
