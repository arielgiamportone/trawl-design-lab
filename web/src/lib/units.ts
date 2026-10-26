/**
 * Unidades de la interfaz (Fase 18.3): métricas (las del motor) o imperiales.
 *
 * El motor y la API calculan siempre en métrico. Este módulo sólo convierte para mostrar
 * (``fmtU``/``toDisplay``) y para leer lo que escribe el usuario (``toCanonical``). Las magnitudes
 * se nombran por la unidad métrica del motor (``'m'``, ``'kgf'``, ``'L/h'``…): así un rótulo
 * ``['Lima', 'm']`` se convierte con ``unitLabel('m')`` y ``fmtU(v, 'm')`` sin otra tabla. Las
 * mallas (``'mesh_mm'``) siguen en mm, con la pulgada entre paréntesis en imperial, porque es la
 * convención del oficio.
 */
import { useSyncExternalStore } from 'react';
import { fmt, fmtFixed } from './format';
import { loadJson, saveJson } from './storage';

export type UnitSystem = 'metric' | 'imperial';
export const UNITS_KEY = 'trawl-design-lab:units:v1';
const EVENT = 'trawl-design-lab:units';

const LB_PER_KG = 2.204622621848776;
const FT_PER_M = 1 / 0.3048;
const IN_PER_MM = 1 / 25.4;
const GAL_PER_L = 1 / 3.785411784;

interface Conversion {
  /** Unidad imperial que se muestra. */
  unit: string;
  /** Valor imperial = valor métrico × factor. */
  factor: number;
}

/**
 * Conversiones por unidad métrica del motor. Las unidades que no figuran (kn, °, %, hp, h, s,
 * u, t/h sin masa…) se muestran igual en los dos sistemas.
 */
export const CONVERSIONS: Record<string, Conversion> = {
  m: { unit: 'ft', factor: FT_PER_M },
  km: { unit: 'nmi', factor: 1 / 1.852 },
  mm: { unit: 'in', factor: IN_PER_MM },
  cm: { unit: 'in', factor: IN_PER_MM * 10 },
  'm²': { unit: 'ft²', factor: FT_PER_M ** 2 },
  'km²': { unit: 'nmi²', factor: 1 / 1.852 ** 2 },
  'm³': { unit: 'ft³', factor: FT_PER_M ** 3 },
  'm/s': { unit: 'ft/s', factor: FT_PER_M },
  kg: { unit: 'lb', factor: LB_PER_KG },
  kgf: { unit: 'lbf', factor: LB_PER_KG },
  t: { unit: 'lbf', factor: 1000 * LB_PER_KG },
  tf: { unit: 'lbf', factor: 1000 * LB_PER_KG },
  N: { unit: 'lbf', factor: LB_PER_KG / 9.80665 },
  kN: { unit: 'lbf', factor: (1000 * LB_PER_KG) / 9.80665 },
  kW: { unit: 'hp', factor: 1 / 0.745699872 },
  L: { unit: 'gal', factor: GAL_PER_L },
  'L/h': { unit: 'gal/h', factor: GAL_PER_L },
  'kg/h': { unit: 'lb/h', factor: LB_PER_KG },
  'kg/m': { unit: 'lb/ft', factor: LB_PER_KG / FT_PER_M },
  'm/kg': { unit: 'ft/lb', factor: FT_PER_M / LB_PER_KG },
  'kg/m³': { unit: 'lb/ft³', factor: LB_PER_KG / FT_PER_M ** 3 },
  'g/m': { unit: 'lb/ft', factor: LB_PER_KG / 1000 / FT_PER_M },
  // Precios por unidad: el precio por galón es mayor que por litro; por libra, menor que por kg.
  '$/L': { unit: '$/gal', factor: 1 / GAL_PER_L },
  '$/kg': { unit: '$/lb', factor: 1 / LB_PER_KG },
  '$/m': { unit: '$/ft', factor: 1 / FT_PER_M },
  'kg/kn': { unit: 'lb/kn', factor: LB_PER_KG },
};

export function initialUnits(): UnitSystem {
  return loadJson<UnitSystem>(UNITS_KEY) === 'imperial' ? 'imperial' : 'metric';
}

let current: UnitSystem = initialUnits();

export function getUnits(): UnitSystem {
  return current;
}

export function setUnits(system: UnitSystem): void {
  saveJson(UNITS_KEY, system);
  if (system === current) return;
  current = system;
  if (typeof window !== 'undefined') window.dispatchEvent(new Event(EVENT));
}

function subscribe(cb: () => void): () => void {
  window.addEventListener(EVENT, cb);
  return () => window.removeEventListener(EVENT, cb);
}

/** Sistema de unidades activo, con re-render al cambiarlo. */
export function useUnits(): UnitSystem {
  return useSyncExternalStore(subscribe, getUnits, getUnits);
}

function conversion(unit: string, system: UnitSystem): Conversion | null {
  if (system !== 'imperial') return null;
  return CONVERSIONS[unit] ?? null;
}

/** Unidad que se muestra para una unidad del motor (``'m'`` → ``'ft'`` en imperial). */
export function unitLabel(unit: string, system: UnitSystem = current): string {
  if (unit === 'mesh_mm') return 'mm';
  return conversion(unit, system)?.unit ?? unit;
}

/** Valor a mostrar a partir del valor del motor. */
export function toDisplay(value: number, unit: string, system: UnitSystem = current): number {
  const c = conversion(unit, system);
  return c ? value * c.factor : value;
}

/** Valor del motor a partir de lo que ingresó el usuario en el sistema activo. */
export function toCanonical(value: number, unit: string, system: UnitSystem = current): number {
  const c = conversion(unit, system);
  return c ? value / c.factor : value;
}

/** Variante de ``toDisplay``/``toCanonical`` que deja pasar ``null``/``undefined``. */
export function toDisplayOpt(
  value: number | null | undefined,
  unit: string,
  system: UnitSystem = current,
): number | null {
  return value === null || value === undefined ? null : toDisplay(value, unit, system);
}

export interface FmtUOptions {
  /** Decimales fijos (máximo); por defecto, las cifras significativas de ``fmt``. */
  digits?: number;
  /** Agrega la unidad al final (por defecto ``true``). */
  unit?: boolean;
  system?: UnitSystem;
}

/**
 * Valor del motor formateado en el sistema activo, con su unidad: ``fmtU(12.5, 'm')`` →
 * «12,5 m» o «41.01 ft». Las mallas (``'mesh_mm'``) quedan en mm con la pulgada entre
 * paréntesis en imperial: «120 mm (4.72 in)».
 */
export function fmtU(
  value: number | null | undefined,
  unit: string,
  opts: FmtUOptions = {},
): string {
  const system = opts.system ?? current;
  const withUnit = opts.unit ?? true;
  const num = (v: number) => (opts.digits === undefined ? fmt(v) : fmtFixed(v, opts.digits));
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  if (unit === 'mesh_mm') {
    const mm = num(value);
    if (system !== 'imperial') return withUnit ? `${mm} mm` : mm;
    const inches = fmtFixed(value * IN_PER_MM, 2);
    return withUnit ? `${mm} mm (${inches} in)` : `${mm} (${inches})`;
  }
  const shown = num(toDisplay(value, unit, system));
  if (!withUnit || !unit) return shown;
  const u = unitLabel(unit, system);
  return u === '%' ? `${shown} %` : `${shown} ${u}`;
}
