/** Impacto de las ediciones: indicadores de la red editada frente a la de base. */
import type { DesignData } from '../api/result';
import { msg } from '../i18n';
import { localized } from './labels';
import { designPropeller, perfWindow } from './series';
import { interp } from './verdict';

export type Better = 'lower' | 'higher' | null;

export interface Metric {
  key: string;
  label: string;
  /** Unidad métrica del motor (se muestra con ``fmtU``/``unitLabel``). */
  unit: string;
  digits: number;
  better: Better;
  get: (d: DesignData, variant: 'std' | 'mod', speed: number) => number | null;
}

const summary = (key: string) => (d: DesignData) => {
  const v = d.summary[key];
  return typeof v === 'number' ? v : null;
};

const METRIC_DEFS: Omit<Metric, 'label'>[] = [
  {
    key: 'rn',
    unit: 'kgf',
    digits: 0,
    better: 'lower',
    get: (d, v, speed) => {
      const series = d.result.drag.rn[v];
      return series ? interp(d.case.speeds_kn, series, speed) : null;
    },
  },
  {
    key: 'max_speed',
    unit: 'kn',
    digits: 2,
    better: 'higher',
    get: (d, v) => perfWindow(d, designPropeller(d), v)?.max_speed_kn ?? null,
  },
  {
    key: 'ah',
    unit: 'm',
    digits: 2,
    better: 'higher',
    get: (d, v) => (v === 'std' ? summary('horizontal_opening_m')(d) : null),
  },
  {
    key: 'av',
    unit: 'm',
    digits: 2,
    better: 'higher',
    get: (d, v) => (v === 'std' ? summary('vertical_opening_m')(d) : null),
  },
  {
    key: 'ss',
    unit: 'm²',
    digits: 2,
    better: null,
    get: (d, v) => (v === 'std' ? summary('solid_surface_m2')(d) : null),
  },
  {
    key: 'weight',
    unit: 'kg',
    digits: 1,
    better: null,
    get: (d, v) => (v === 'std' ? summary('net_weight_kg')(d) : null),
  },
];

/** Indicadores con el rótulo en el idioma activo. */
export const METRICS: Metric[] = localized(() =>
  METRIC_DEFS.map((m) => ({
    ...m,
    label: (msg().labels.impact as Record<string, string>)[m.key] ?? m.key,
  })),
);

export interface ImpactRow {
  metric: Metric;
  now: number;
  base: number | null;
  delta: number | null;
  tone: 'good' | 'bad' | 'neutral';
}

/** Filas de impacto (se omiten los indicadores sin dato para la variante). */
export function impactRows(
  now: DesignData,
  base: DesignData | null | undefined,
  variant: 'std' | 'mod',
  speed: number,
): ImpactRow[] {
  const rows: ImpactRow[] = [];
  for (const m of METRICS) {
    const v = m.get(now, variant, speed);
    if (v === null) continue;
    const b = base ? m.get(base, variant, speed) : null;
    const delta = b === null ? null : v - b;
    const eps = 10 ** -m.digits / 2;
    let tone: ImpactRow['tone'] = 'neutral';
    if (delta !== null && Math.abs(delta) >= eps && m.better) {
      tone = (m.better === 'lower') === delta < 0 ? 'good' : 'bad';
    }
    rows.push({ metric: m, now: v, base: b, delta, tone });
  }
  return rows;
}
