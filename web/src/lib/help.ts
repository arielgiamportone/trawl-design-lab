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
  catch_kg: {
    text: 'Captura acumulada en el copo. Ocupa el extremo del copo, lo infla y agrega resistencia; los portones se cierran un poco y el tiro sube.',
    unit: 'kg',
    range: [0, 5000],
    chapter: '22_simulacion_realista',
  },
  seabed: {
    text: 'Tipo de fondo: fija el rozamiento del tren de fondo y de las zapatas de los portones. Los valores son estimaciones con rango (no hay una tabla publicada por sedimento).',
    chapter: '22_simulacion_realista',
  },
  mesh_orientation: {
    text: 'Orientación de la malla del paño. Rombo: la malla clásica, que la tensión a lo largo cierra. T90: el mismo paño girado 90°, que se mantiene más abierto. Cuadrada: hilos a lo largo y a lo ancho; la malla no se cierra.',
    chapter: '24_malla_selectividad',
  },
  l50: {
    text: 'Talla de retención al 50 %: los peces de esa talla tienen la mitad de chance de quedar en el copo. Sube con el mallero y con mallas más abiertas.',
    chapter: '24_malla_selectividad',
  },
  selection_range: {
    text: 'Rango de selección SR = L75 − L25: cuán gradual es el paso de escapar a quedar retenido. Un SR chico es una selección más nítida.',
    chapter: '24_malla_selectividad',
  },
  fishselect: {
    text: 'Modelo geométrico de escape (tipo FISHSELECT): un pez pasa si la sección más resistente de su cuerpo entra en la luz de la malla deformada, girándola a su favor.',
    chapter: '24_malla_selectividad',
  },
  p10_p90: {
    text: 'Banda de incertidumbre: el 80 % de las muestras cae entre P10 y P90; P50 es la mediana. Se obtiene variando dentro de sus rangos los datos que no se conocen con precisión.',
    chapter: '25_incertidumbre_calibracion',
  },
  sensitivity: {
    text: 'Correlación de rangos entre cada dato incierto y el resultado: cerca de ±1, ese dato explica casi toda la variación; cerca de 0, casi no influye.',
    chapter: '25_incertidumbre_calibracion',
  },
  calibration: {
    text: 'Ajusta parámetros del simulador (coeficientes del hilo, polar del portón, rozamientos) para reproducir mediciones. Si un parámetro queda en el límite de su rango, la diferencia es del modelo, no del parámetro.',
    chapter: '25_incertidumbre_calibracion',
  },
  sensor_log: {
    text: 'CSV exportado por los sensores del arte: velocidad, separación de portones, altura de la relinga, tensiones de los cables, captura. Se reconocen nombres en español o inglés y la unidad entre paréntesis o como sufijo; el separador puede ser coma, punto y coma o tabulador.',
    chapter: '25_incertidumbre_calibracion',
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
