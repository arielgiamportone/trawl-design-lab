/**
 * Ayuda contextual: explicación en lenguaje llano, unidad, rango habitual y capítulo del libro.
 * El rango es orientativo: fuera de él se avisa pero no se impide calcular.
 */

export interface HelpEntry {
  text: string;
  unit?: string;
  /** Rango habitual [mín, máx] en la unidad indicada. */
  range?: [number, number];
  /** Capítulo del libro (nombre del archivo sin extensión). */
  chapter?: string;
}

export const HELP: Record<string, HelpEntry> = {
  // Conceptos del asistente
  vessel: {
    text: 'El buque fija la potencia disponible para arrastrar: de ella sale el tiro (fuerza) que puede hacer a cada velocidad.',
    chapter: '10_potencia',
  },
  propeller: {
    text: 'Una hélice de paso fijo pierde tiro al ir despacio; una de paso variable con tobera aprovecha mejor la potencia al arrastrar.',
    chapter: '10_potencia',
  },
  net: {
    text: 'La red define la resistencia al avance (cuánto «frena») y la boca que barre el fondo. Redes más grandes pescan más área pero piden más tiro.',
    chapter: '11_panos_y_cortes',
  },
  net_modified: {
    text: 'Una segunda red que se calcula a la par para compararla con la principal (por ejemplo, otra bolsa).',
    chapter: '30_caso_beagle',
  },
  door: {
    text: 'Los portones abren la red hacia los lados. Su tamaño debe acompañar a la red y al buque.',
    chapter: '15_portones_aparejo',
  },
  target_speed: {
    text: 'Velocidad a la que piensa arrastrar. Con ella se evalúa si el tiro alcanza y cuánta área se barre por hora.',
    unit: 'kn',
    range: [1.5, 4],
    chapter: '19_ventana_velocidad',
  },
  // Parámetros de DesignCase
  speeds_kn: {
    text: 'Velocidades en las que se calculan las curvas de tiro y resistencia.',
    unit: 'kn',
    range: [0.5, 6],
    chapter: '19_ventana_velocidad',
  },
  depth_m: {
    text: 'Profundidad del fondo de pesca. Determina el largo de cable a filar y su resistencia.',
    unit: 'm',
    range: [10, 800],
    chapter: '18_cables',
  },
  gallows_m: {
    text: 'Separación entre las pastecas de popa por donde salen los cables.',
    unit: 'm',
    range: [1, 15],
    chapter: '15_portones_aparejo',
  },
  vessel_depth_m: {
    text: 'Puntal del buque.',
    unit: 'm',
    range: [0.5, 10],
    chapter: '10_potencia',
  },
  ft_propeller: {
    text: 'Tipo de hélice con que se calcula el tiro de Fridman.',
    chapter: '10_potencia',
  },
  door_attack_angle_deg: {
    text: 'Ángulo del portón respecto de la dirección de avance; define su sustentación (apertura) y resistencia.',
    unit: '°',
    range: [15, 45],
    chapter: '15_portones_aparejo',
  },
  bridle_angle_deg: {
    text: 'Ángulo de las bridas respecto de la línea de arrastre.',
    unit: '°',
    range: [2, 20],
    chapter: '15_portones_aparejo',
  },
  sweeps_m: {
    text: 'Largo de las patentes (cabos entre portones y red). Más largas arrean más peces pero agregan resistencia.',
    unit: 'm',
    range: [5, 200],
    chapter: '15_portones_aparejo',
  },
  dan_leno_m: {
    text: 'Largo del dan leno.',
    unit: 'm',
    range: [0.2, 3],
    chapter: '15_portones_aparejo',
  },
  float_count: {
    text: 'Cantidad de boyas en la lima (vacío = la calcula el motor).',
    range: [2, 200],
    chapter: '17_flotacion_lastre',
  },
  float_diameter_mm: {
    text: 'Diámetro de las boyas (vacío = automático).',
    unit: 'mm',
    range: [100, 300],
    chapter: '17_flotacion_lastre',
  },
  warp_safety_factor: {
    text: 'Factor de seguridad del cable de arrastre sobre la carga de trabajo.',
    range: [3, 6],
    chapter: '18_cables',
  },
  warp_design_speed_kn: {
    text: 'Velocidad con la que se dimensiona el cable.',
    unit: 'kn',
    range: [1.5, 5],
    chapter: '18_cables',
  },
  rob_share: {
    text: 'Fracción del tiro que absorben los cables y el aparejo (resistencia de otros elementos).',
    range: [0.05, 0.4],
    chapter: '19_ventana_velocidad',
  },
  ballast_min_speed_kn: {
    text: 'Velocidad del lastre mínimo.',
    unit: 'kn',
    range: [0.5, 4],
    chapter: '17_flotacion_lastre',
  },
  ballast_max_speed_kn: {
    text: 'Velocidad del lastre máximo.',
    unit: 'kn',
    range: [1, 5],
    chapter: '17_flotacion_lastre',
  },
  flotation_max_speed_kn: {
    text: 'Velocidad máxima para la que se dimensiona la flotación.',
    unit: 'kn',
    range: [1, 5],
    chapter: '17_flotacion_lastre',
  },
};

export type RangeCheck = { ok: true } | { ok: false; message: string };

/** ¿El valor (o todos los de una lista) cae en el rango habitual? */
export function checkRange(key: string, value: unknown): RangeCheck {
  const range = HELP[key]?.range;
  if (!range) return { ok: true };
  const vals = (Array.isArray(value) ? value : [value]).filter(
    (v): v is number => typeof v === 'number' && Number.isFinite(v),
  );
  const [lo, hi] = range;
  if (vals.every((v) => v >= lo && v <= hi)) return { ok: true };
  const unit = HELP[key]?.unit ? ` ${HELP[key]?.unit}` : '';
  const f = (n: number) => n.toLocaleString('es-AR');
  return {
    ok: false,
    message: `Fuera del rango habitual (${f(lo)}–${f(hi)}${unit}). Se calcula igual; revise el dato.`,
  };
}
