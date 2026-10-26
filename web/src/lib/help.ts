/**
 * Ayuda contextual: explicación en lenguaje llano, unidad, rango habitual y capítulo del libro.
 * El rango es orientativo: fuera de él se avisa pero no se impide calcular. Los textos están en
 * el catálogo ``labels.help``; la unidad y el rango, en las unidades métricas del motor.
 */
import { msg } from '../i18n';
import { localized } from './labels';
import { fmtU, unitLabel } from './units';

export interface HelpEntry {
  text: string;
  /** Unidad métrica del motor (se muestra con ``unitLabel``). */
  unit?: string;
  /** Rango habitual [mín, máx] en la unidad indicada. */
  range?: [number, number];
  /** Capítulo del libro (nombre del archivo sin extensión). */
  chapter?: string;
}

const HELP_META: Record<string, Omit<HelpEntry, 'text'>> = {
  // Conceptos del asistente
  vessel: {
    chapter: '10_potencia',
  },
  propeller: {
    chapter: '10_potencia',
  },
  net: {
    chapter: '11_panos_y_cortes',
  },
  net_modified: {
    chapter: '30_caso_beagle',
  },
  door: {
    chapter: '15_portones_aparejo',
  },
  target_speed: {
    unit: 'kn',
    range: [1.5, 4],
    chapter: '19_ventana_velocidad',
  },
  catch_kg: {
    unit: 'kg',
    range: [0, 5000],
    chapter: '22_simulacion_realista',
  },
  seabed: {
    chapter: '22_simulacion_realista',
  },
  mesh_orientation: {
    chapter: '24_malla_selectividad',
  },
  l50: {
    chapter: '24_malla_selectividad',
  },
  selection_range: {
    chapter: '24_malla_selectividad',
  },
  fishselect: {
    chapter: '24_malla_selectividad',
  },
  p10_p90: {
    chapter: '25_incertidumbre_calibracion',
  },
  sensitivity: {
    chapter: '25_incertidumbre_calibracion',
  },
  calibration: {
    chapter: '25_incertidumbre_calibracion',
  },
  sensor_log: {
    chapter: '25_incertidumbre_calibracion',
  },
  // Parámetros de DesignCase
  speeds_kn: {
    unit: 'kn',
    range: [0.5, 6],
    chapter: '19_ventana_velocidad',
  },
  depth_m: {
    unit: 'm',
    range: [10, 800],
    chapter: '18_cables',
  },
  gallows_m: {
    unit: 'm',
    range: [1, 15],
    chapter: '15_portones_aparejo',
  },
  vessel_depth_m: {
    unit: 'm',
    range: [0.5, 10],
    chapter: '10_potencia',
  },
  ft_propeller: {
    chapter: '10_potencia',
  },
  door_attack_angle_deg: {
    unit: '°',
    range: [15, 45],
    chapter: '15_portones_aparejo',
  },
  bridle_angle_deg: {
    unit: '°',
    range: [2, 20],
    chapter: '15_portones_aparejo',
  },
  sweeps_m: {
    unit: 'm',
    range: [5, 200],
    chapter: '15_portones_aparejo',
  },
  dan_leno_m: {
    unit: 'm',
    range: [0.2, 3],
    chapter: '15_portones_aparejo',
  },
  float_count: {
    range: [2, 200],
    chapter: '17_flotacion_lastre',
  },
  float_diameter_mm: {
    unit: 'mm',
    range: [100, 300],
    chapter: '17_flotacion_lastre',
  },
  warp_safety_factor: {
    range: [3, 6],
    chapter: '18_cables',
  },
  warp_design_speed_kn: {
    unit: 'kn',
    range: [1.5, 5],
    chapter: '18_cables',
  },
  rob_share: {
    range: [0.05, 0.4],
    chapter: '19_ventana_velocidad',
  },
  ballast_min_speed_kn: {
    unit: 'kn',
    range: [0.5, 4],
    chapter: '17_flotacion_lastre',
  },
  ballast_max_speed_kn: {
    unit: 'kn',
    range: [1, 5],
    chapter: '17_flotacion_lastre',
  },
  flotation_max_speed_kn: {
    unit: 'kn',
    range: [1, 5],
    chapter: '17_flotacion_lastre',
  },
};

/** Ayuda de cada clave con el texto en el idioma activo. */
export const HELP: Record<string, HelpEntry> = localized(() => {
  const texts = msg().labels.help as Record<string, string>;
  const out: Record<string, HelpEntry> = {};
  for (const [k, meta] of Object.entries(HELP_META)) out[k] = { text: texts[k] ?? '', ...meta };
  return out;
});

/** Rango habitual de una clave en el sistema de unidades activo («10–800 m»), o ``null``. */
export function rangeText(key: string): string | null {
  const entry = HELP_META[key];
  if (!entry?.range) return null;
  const unit = entry.unit ?? '';
  const [lo, hi] = entry.range;
  const f = (n: number) => fmtU(n, unit, { unit: false });
  return `${f(lo)}–${f(hi)}${unit ? ` ${unitLabel(unit)}` : ''}`;
}

export type RangeCheck = { ok: true } | { ok: false; message: string };

/** ¿El valor (o todos los de una lista) cae en el rango habitual? */
export function checkRange(key: string, value: unknown): RangeCheck {
  const range = HELP_META[key]?.range;
  if (!range) return { ok: true };
  const vals = (Array.isArray(value) ? value : [value]).filter(
    (v): v is number => typeof v === 'number' && Number.isFinite(v),
  );
  const [lo, hi] = range;
  if (vals.every((v) => v >= lo && v <= hi)) return { ok: true };
  return { ok: false, message: msg().labels.outOfRange(rangeText(key) ?? '') };
}
