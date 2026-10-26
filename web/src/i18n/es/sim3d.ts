/** Vistas 3D de la red simulada (forma y animación). */
export const sim3d = {
  views: { iso: 'Perspectiva', plan: 'Planta', profile: 'Perfil', front: 'Frente' },
  viewsLabel: 'Vista 3D',
  colorLabel: 'Color del paño',
  tension: 'Tensión',
  contact: 'Contacto con el fondo',
  png: 'Descargar PNG',
  pngName: (v: string) => `red-3d-${v}kn.png`,
  canvasAria: (v: string, ah: string, av: string) =>
    `Forma 3D de la red a ${v} kn: abertura horizontal ${ah} y vertical ${av}; color = tensión del hilo.`,
  noWebgl:
    'Este navegador no tiene WebGL: use las proyecciones de planta, perfil y frente de abajo.',
  stageAria: 'Visor 3D: arrastre para girar, rueda para acercar, flechas para desplazar.',
  twineTension: (unit: string) => `Tensión del hilo [${unit}]`,
  onSeabed: 'Paño apoyado en el fondo',
  contactShare: (pct: string) => `${pct} % del paño`,
  legend:
    'Línea llena: lima y burlón · discontinua: bridas, patentes y cables · puntos: boyas · grilla: fondo.',
  // Animación
  noWebglAnim: 'Este navegador no tiene WebGL: la animación 3D no está disponible.',
  animStageAria:
    'Visor 3D animado: arrastre para girar, rueda para acercar, flechas para desplazar.',
  openingLegend: 'Apertura de la malla (área / malla abierta en cuadrado)',
  valuePerTriangle: 'Valor por triángulo',
  fouled: 'Paño ensuciado (más intenso = más nivel)',
  pickHint: 'Haga clic sobre el paño para ver sus mallas de cerca (zoom por malla).',
  animLegend:
    'Placas: portones · flechas rojas: tiro de los cables en el buque (largo ∝ tensión) · puntos: boyas · grilla: fondo.',
};
