/** Etiquetas en español de ``DesignResult.summary()`` (espejo de ``trawlkit.report.labels``). */

export const SUMMARY_LABELS: Record<string, readonly [string, string]> = {
  net_id: ['Red', ''],
  vessel_id: ['Buque', ''],
  door_id: ['Portón', ''],
  compat: ['Modo de compatibilidad', ''],
  headrope_m: ['Lima', 'm'],
  footrope_m: ['Burlón', 'm'],
  cut_angle_deg: ['Ángulo de ataque de los cortes (α)', '°'],
  filtration_index: ['Índice de filtración (d/l)', ''],
  solid_surface_m2: ['Superficie sólida (Ss)', 'm²'],
  working_surface_m2: ['Superficie de trabajo (St)', 'm²'],
  net_weight_kg: ['Peso de la red', 'kg'],
  vertical_opening_m: ['Abertura vertical (AV)', 'm'],
  horizontal_opening_m: ['Abertura horizontal (AH)', 'm'],
  working_depth_m: ['Profundidad de trabajo', 'm'],
  flotation_total_kgf: ['Flotación total', 'kgf'],
  dan_leno_m: ['Dan leno', 'm'],
  sweeps_m: ['Patentes', 'm'],
  crowfoot_m: ['Pies de gallo', 'm'],
  crowfoot_extension_m: ['Alargue de pies de gallo', 'm'],
  upper_bridle_m: ['Brida superior', 'm'],
  lower_bridle_m: ['Brida inferior', 'm'],
  warp_diameter_mm: ['Ø cable de remolque', 'mm'],
  warp_length_m: ['Cable filado', 'm'],
  float_count: ['Boyas', 'u'],
  float_diameter_mm: ['Ø boya', 'mm'],
  ballast_min_kg: ['Lastre mínimo', 'kg'],
  ballast_max_kg: ['Lastre máximo', 'kg'],
  warp_selected: ['Cable seleccionado', ''],
  warp_breaking_load_t: ['Rotura del cable seleccionado', 't'],
  warp_min_breaking_load_kgf: ['Rotura mínima requerida', 'kgf'],
  warp_quantity_m: ['Cable a comprar', 'm'],
  max_speed_kn: ['Velocidad máxima remolcable', 'kn'],
};

/** Etiqueta y unidad de una clave del resumen (con las claves dinámicas ``rn_std_*``/``rob_*``). */
export function label(key: string): readonly [string, string] {
  const known = SUMMARY_LABELS[key];
  if (known) return known;
  if (key.startsWith('rn_std_')) return [`RN estándar a ${speedOf(key.slice(7))}`, 'kgf'];
  if (key.startsWith('rob_')) return [`ROB a ${speedOf(key.slice(4))}`, 'kgf'];
  return [key, ''];
}

function speedOf(rest: string): string {
  // "3_5kn_kgf" → "3,5 kn" (Python: key[7:-4] → "3_5kn" → "3.5kn"; aquí con coma decimal)
  const s = rest.replace(/_kgf$/, '').replace(/kn$/, '');
  return `${s.replace('_', ',')} kn`;
}

/** Métodos de resistencia de la red (``drag.table``), en el orden de la hoja. */
export const DRAG_METHODS: readonly (readonly [string, string])[] = [
  ['tauti_nomura_shu', 'Tauti–Nomura–Shu (1974)'],
  ['tauti_headrope', 'Tauti (lima)'],
  ['tauti_footrope', 'Tauti (burlón)'],
  ['koyama_1974', 'Koyama (1974)'],
  ['koyama_1984', 'Koyama (1984)'],
  ['hamuro', 'Hamuro'],
  ['reid', 'Reid (1977)'],
  ['robertson', 'Robertson (1981)'],
  ['maclennan', 'MacLennan (1981)'],
  ['aberdeen_demersal', 'Aberdeen demersal'],
  ['aberdeen_pelagic', 'Aberdeen pelágica'],
  ['fridman', 'Fridman (1973)'],
  ['dickson', 'Dickson'],
];

export function dragMethodLabel(key: string): string {
  return DRAG_METHODS.find(([k]) => k === key)?.[1] ?? key;
}

/** Métodos de tiro disponible (``power.curves``). */
export const PULL_METHODS = [
  ['fridman_kgf', 'Fridman'],
  ['prado_kgf', 'Prado–Dremière'],
  ['koyama_kgf', 'Koyama'],
  ['nomura_kgf', 'Nomura'],
  ['hamuro_kgf', 'Hamuro'],
  ['average_kgf', 'Promedio'],
] as const;

export const PROPELLER_LABELS: Record<string, string> = {
  fixed_pitch: 'Paso fijo (PF)',
  fixed_pitch_nozzle: 'Paso fijo con tobera (PF+T)',
  variable_pitch: 'Paso variable (PV)',
  variable_pitch_nozzle: 'Paso variable con tobera (PV+T)',
};

export const PLANE_LABELS: Record<string, string> = {
  upper: 'superior',
  lower: 'inferior',
  side: 'lateral',
};

export const SECTION_LABELS: Record<string, string> = {
  wing_tip: 'punta de ala',
  wing: 'ala',
  square: 'square',
  belly: 'vientre',
  body: 'cuerpo',
  extension: 'extensión',
  codend: 'bolsa',
};

export const VARIANT_LABELS = { std: 'estándar', mod: 'modificada' } as const;

/** Tipos de fondo (``data/seabed.yaml``) para el parámetro ``seabed`` del motor. */
export const SEABED_LABELS: Record<string, string> = {
  mud: 'Fango',
  sand: 'Arena',
  mixed: 'Intermedio (mixto)',
  gravel: 'Grava y conchilla',
  rock: 'Roca o piedra',
};
