/** Simulación de la forma: barrido de velocidades y textos comunes a las vistas de simulación. */
export const simulate = {
  quality: { fast: 'Rápida', normal: 'Normal' },
  resolutions: { veryFast: 'Muy rápida', fast: 'Rápida', normal: 'Normal' },
  quantities: {
    ah_m: { label: 'Abertura horizontal AH', engine: 'DPA de Fridman' },
    av_m: { label: 'Abertura vertical AV', engine: 'AV de Fridman' },
    drag_kgf: { label: 'Resistencia de la red', engine: 'RN Aberdeen' },
  },
  /** Aberturas del motor con el método camaronero (Fase 19.7b), en lugar de las de Fridman. */
  shrimpEngine: 'método camaronero, a la velocidad de diseño',
  // Textos compartidos por las vistas de simulación
  speed: 'Velocidad',
  resolution: 'Resolución',
  seabed: 'Fondo',
  catchCodend: 'Captura en el copo',
  noSelectivity: '(sin selectividad)',
  error: 'Error',
  errorStatus: (status: number) => `Error ${status}`,
  loading3d: 'Cargando el visor 3D…',
  engineRule: 'regla del motor',
  engineDemand: 'demanda del motor',
  yes: 'sí',
  no: 'no',
  // Pestaña
  title: 'Simulación de la forma',
  experimental: 'experimental',
  viewsLabel: 'Tipo de simulación',
  views: {
    speeds: 'Barrido de velocidad',
    haul: 'Lance progresivo (captura y fondo)',
    explore: 'Explorador animado',
    selectivity: 'Mallas y selectividad',
    uncertainty: 'Incertidumbre y calibración',
  },
  // Barrido de velocidad
  projections: { plan: 'Planta', profile: 'Perfil', front: 'Frente' },
  table: {
    caption: (dynamit: boolean) =>
      `Simulación frente al motor empírico${dynamit ? ' y a DynamiT' : ''}`,
    quantity: 'Magnitud',
    sim: 'Simulación',
    engine: 'Motor',
    simVsEngine: 'Δ sim/motor',
    simVsDynamit: 'Δ sim/DynamiT',
    engineVsDynamit: 'Δ motor/DynamiT',
    engineNote: (name: string) => ` motor: ${name}`,
  },
  scaledNet: (s: string) => `red escalada s = ${s}`,
  intro: (net: string) =>
    `Busca la forma de equilibrio de la red (${net}) remolcada a cada velocidad: paño de hilos con arrastre de Morison, relingas, boyas, lastre, bridas, patentes y contacto con el fondo, con el aparejo del caso actual.`,
  formLabel: 'Parámetros de la simulación',
  speedsLegend: (max: number, n: number) => `Velocidades [kn] (hasta ${max}, ${n} elegidas)`,
  estimate: (s: number) => `≈ ${s} s en el servidor`,
  view3d: 'Vista 3D',
  run: 'Simular',
  cancel: 'Cancelar',
  running: 'Simulando…',
  runningOf: (s: number) => `de ≈ ${s} s`,
  done: (n: number, secs: string, res: string) =>
    `${n} ${n === 1 ? 'velocidad simulada' : 'velocidades simuladas'} en ${secs} s (resolución ${res}).`,
  unconverged: (speeds: string) =>
    `La simulación no convergió del todo a ${speeds} kn: tome esos valores con cautela.`,
  view3dRegion: 'Vista 3D de la forma simulada',
  speed3d: 'Velocidad de la vista 3D',
  projAria: (v: string) => `Proyecciones a ${v} kn`,
  at: (v: string) => `A ${v} kn`,
  projAlt: (view: string, v: string) => `${view} de la red simulada a ${v} kn`,
  projLabel: (view: string, v: string) =>
    `${view} de la red a ${v} kn. Arrastre para desplazar, rueda o teclas + y − para acercar, 0 para restablecer.`,
  firstThree: 'Se dibujan las tres primeras velocidades.',
  compareTitle: (dynamit: boolean) => `Simulación, motor empírico${dynamit ? ' y DynamiT' : ''}`,
  dragNote: {
    title: 'Sobre la resistencia.',
    a: 'El arrastre simulado es sólo el de los hilos (Morison con C',
    b: (cn: string) => ` = ${cn} y C`,
    c: (ct: string) =>
      ` = ${ct}) más el rozamiento con el fondo: en la red FAO A-3 queda ≈ 50 % por debajo de la RA de DynamiT entre 2 y 4 kn, y la RN empírica del motor (Aberdeen) ≈ 20 % por encima. Las aberturas, en cambio, coinciden: AH dentro del 3 % y AV dentro del 10–20 %. La brecha de resistencia apunta a lo que el modelo no tiene —nudos, vibración y ondulación del paño, sombra hidrodinámica entre hilos y coeficientes del hilo calibrados en flujo uniforme— y no se cierra con C`,
    d: '/C',
    e: ' dentro de los rangos de la literatura (ver el capítulo 21 del libro). Use la simulación para la forma y las aberturas, y el motor para la resistencia de diseño.',
  },
  empty:
    'Elija hasta tres velocidades y pulse «Simular». La versión rápida tarda alrededor de un segundo por velocidad.',
};
