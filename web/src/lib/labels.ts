/**
 * Etiquetas de ``DesignResult.summary()`` (espejo de ``trawlkit.report.labels``) y de los
 * métodos, hélices, planos, secciones y fondos. Los textos viven en el catálogo ``labels`` del
 * idioma activo; las unidades son las métricas del motor (quien muestra usa ``fmtU``/``unitLabel``).
 *
 * Las constantes exportadas (``SUMMARY_LABELS``, ``PROPELLER_LABELS``…) se leen en el momento de
 * uso con el idioma vigente (objetos «vivos»), así que se pueden seguir usando como antes.
 */
import { msg } from '../i18n';
import { fmt } from './format';

/**
 * Objeto o lista que se lee de nuevo en cada acceso (``get()``): mantiene la forma de las viejas
 * constantes (``X[key]``, ``Object.entries(X)``, ``X.map``…) pero en el idioma activo.
 */
export function localized<T extends object>(get: () => T): T {
  const isArray = Array.isArray(get());
  const target = (isArray ? [] : {}) as T;
  return new Proxy(target, {
    get: (_t, k) => {
      const v = get();
      const r: unknown = Reflect.get(v, k);
      return typeof r === 'function' ? (r as (...a: unknown[]) => unknown).bind(v) : r;
    },
    has: (_t, k) => Reflect.has(get(), k),
    ownKeys: () => Reflect.ownKeys(get()),
    getOwnPropertyDescriptor: (_t, k) => {
      const d = Reflect.getOwnPropertyDescriptor(get(), k);
      if (!d) return undefined;
      // ``length`` de una lista no es configurable en el destino: se informa tal cual.
      return isArray && k === 'length' ? d : { ...d, configurable: true };
    },
  });
}

/** Unidad métrica (del motor) de cada clave del resumen. */
export const SUMMARY_UNITS: Record<string, string> = {
  net_id: '',
  vessel_id: '',
  door_id: '',
  compat: '',
  headrope_m: 'm',
  footrope_m: 'm',
  cut_angle_deg: '°',
  filtration_index: '',
  solid_surface_m2: 'm²',
  working_surface_m2: 'm²',
  net_weight_kg: 'kg',
  vertical_opening_m: 'm',
  horizontal_opening_m: 'm',
  working_depth_m: 'm',
  flotation_total_kgf: 'kgf',
  dan_leno_m: 'm',
  sweeps_m: 'm',
  crowfoot_m: 'm',
  crowfoot_extension_m: 'm',
  upper_bridle_m: 'm',
  lower_bridle_m: 'm',
  warp_diameter_mm: 'mm',
  warp_length_m: 'm',
  float_count: 'u',
  float_diameter_mm: 'mm',
  ballast_min_kg: 'kg',
  ballast_max_kg: 'kg',
  warp_selected: '',
  warp_breaking_load_t: 't',
  warp_min_breaking_load_kgf: 'kgf',
  warp_quantity_m: 'm',
  warp_tension_kgf: 'kgf',
  warp_stretch_m: 'm',
  warp_safety_factor: '',
  max_speed_kn: 'kn',
  rig: '',
  n_nets: 'u',
  net_spread_m: 'm',
  door_spread_total_m: 'm',
  swept_width_m: 'm',
  beam_length_m: 'm',
  boom_tip_offset_m: 'm',
  nets_gap_m: 'm',
  clump_weight_kg: 'kg',
  opening_method: '',
  door_spread_m: 'm',
  cfp_av_limit_m: 'm',
};

/** Etiqueta (idioma activo) y unidad métrica de cada clave fija del resumen. */
export const SUMMARY_LABELS: Record<string, readonly [string, string]> = localized(() => {
  const names = msg().labels.summary as Record<string, string>;
  const out: Record<string, readonly [string, string]> = {};
  for (const [k, unit] of Object.entries(SUMMARY_UNITS)) out[k] = [names[k] ?? k, unit];
  return out;
});

/**
 * Etiqueta (idioma activo) y unidad métrica de una clave del resumen (con las claves dinámicas
 * ``rn_std_*``/``rob_*``). La unidad es la del motor: para mostrarla use ``unitLabel``/``fmtU``.
 */
export function label(key: string): readonly [string, string] {
  const L = msg().labels;
  const name = (L.summary as Record<string, string>)[key];
  if (name !== undefined) return [name, SUMMARY_UNITS[key] ?? ''];
  if (key.startsWith('rn_std_')) return [L.rnStd(speedOf(key.slice(7))), 'kgf'];
  if (key.startsWith('rob_')) return [L.rob(speedOf(key.slice(4))), 'kgf'];
  if (key.startsWith('net_total_')) return [L.netTotal(speedOf(key.slice(10))), 'kgf'];
  if (key.startsWith('total_drag_')) return [L.totalDrag(speedOf(key.slice(11))), 'kgf'];
  return [key, ''];
}

function speedOf(rest: string): string {
  // "3_5kn_kgf" → "3,5 kn" (Python: key[7:-4] → "3_5kn" → "3.5kn"; aquí con el separador del idioma)
  const s = rest.replace(/_kgf$/, '').replace(/kn$/, '');
  const n = Number(s.replace('_', '.'));
  return `${Number.isFinite(n) ? fmt(n) : s} kn`;
}

const DRAG_KEYS = [
  'tauti_nomura_shu',
  'tauti_headrope',
  'tauti_footrope',
  'koyama_1974',
  'koyama_1984',
  'hamuro',
  'reid',
  'robertson',
  'maclennan',
  'aberdeen_demersal',
  'aberdeen_pelagic',
  'fridman',
  'dickson',
] as const;

/** Métodos de resistencia de la red (``drag.table``), en el orden de la hoja. */
export const DRAG_METHODS: readonly (readonly [string, string])[] = localized(() =>
  DRAG_KEYS.map((k) => [k, msg().labels.dragMethods[k]] as const),
);

export function dragMethodLabel(key: string): string {
  return (msg().labels.dragMethods as Record<string, string>)[key] ?? key;
}

const PULL_KEYS = [
  'fridman_kgf',
  'prado_kgf',
  'koyama_kgf',
  'nomura_kgf',
  'hamuro_kgf',
  'average_kgf',
] as const;

/** Métodos de tiro disponible (``power.curves``). */
export const PULL_METHODS: readonly (readonly [(typeof PULL_KEYS)[number], string])[] = localized(
  () => PULL_KEYS.map((k) => [k, msg().labels.pullMethods[k]] as const),
);

export const PROPELLER_LABELS: Record<string, string> = localized(() => msg().labels.propellers);

export const PLANE_LABELS: Record<string, string> = localized(() => msg().labels.planes);

export const SECTION_LABELS: Record<string, string> = localized(() => msg().labels.sections);

export const VARIANT_LABELS: { readonly std: string; readonly mod: string } = localized(
  () => msg().labels.variants,
);

/** Tipos de fondo (``data/seabed.yaml``) para el parámetro ``seabed`` del motor. */
export const SEABED_LABELS: Record<string, string> = localized(() => msg().labels.seabeds);
