/** Textos de «wizard». */
export const wizard = {
  /** Diagnóstico en lenguaje llano (``lib/verdict``). */
  verdict: {
    pullTitle: '¿Le alcanza la potencia?',
    pullShort: (v: string) => `No: falta ${v}`,
    pullTight: (pct: number) => `Justo: sobra ${pct} %`,
    pullYes: (pct: number) => `Sí: sobra ${pct} %`,
    pullWhy: (speed: string, available: string, demand: string) =>
      `A ${speed} el buque puede tirar unos ${available} y la red con sus portones y cables pide unos ${demand}`,
    pullFriction: (v: string) => ` (incluye ${v} de roce con el fondo)`,
    pullWhyCrit:
      'Con ese déficit el buque no llega a esa velocidad: baje la velocidad, use una red más chica o un buque más potente.',
    pullWhyWarn: 'Alcanza, pero con poco margen para corriente, fondo duro o captura en la bolsa.',
    pullWhyOk: 'Hay margen para corriente, fondo y captura.',
    pullNoData: 'Sin dato a esa velocidad',
    pullNoDataWhy:
      'La velocidad elegida queda fuera de las calculadas; ajuste la lista de velocidades en el modo experto.',
    maxTitle: 'Velocidad máxima de arrastre',
    maxNone: 'Ninguna velocidad viable',
    maxNoneWhy: 'En ninguna de las velocidades calculadas el tiro supera a la resistencia.',
    maxWhy: 'Es la velocidad a la que el tiro disponible iguala a la resistencia total',
    maxRange: (from: string, to: string) => `; se puede arrastrar entre ${from} y ${to}.`,
    maxMod: (v: string) => ` Con la red modificada: ${v}.`,
    warpTitle: 'Cable de arrastre',
    warpNone: 'No se pudo seleccionar un cable del catálogo.',
    warpOk: (v: string) =>
      `Su carga de rotura (${v}) cubre la requerida con el factor de seguridad.`,
    warpFail:
      'Su carga de rotura no cubre la requerida con el factor de seguridad: elija un cable más grueso.',
    openingTitle: 'Boca de la red',
    openingWhy: 'Ancho entre puntas de ala × altura de la boca, estimados para la red trabajando.',
    sweptTitle: 'Área barrida por hora',
    swept: (thousands: string, unit: string) => `${thousands} mil ${unit}/h`,
    sweptWhy: (width: string, speed: string) =>
      `Ancho de la boca (${width}) × distancia recorrida en una hora a ${speed}. Es un indicador del rendimiento de pesca.`,
  },
};
