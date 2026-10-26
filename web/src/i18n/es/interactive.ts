/** Textos de «interactive». */
export const interactive = {
  title: 'Diseño interactivo',
  sub: 'Toque un panel y arrastre sus tiradores (alto y bordes) o use las flechas; el caso se recalcula al soltar. Ctrl+Z deshace.',
  outline: 'Contorno original',
  loading: 'Cargando el plano…',
  edited: (n: number) =>
    n === 0
      ? 'Sin cambios respecto de la red de base.'
      : `${n} ${n === 1 ? 'valor editado' : 'valores editados'} (paneles resaltados). La línea discontinua es la red original.`,
  stretched: 'El plano está a malla estirada: ancho = mallas × mallero; alto = N × mallero.',
  canvasLabel:
    'Plano editable de la red. Tab recorre los paneles; Enter selecciona; flechas ajustan mallas (Mayúsculas ×10); +/− zoom; 0 vista completa; Esc deselecciona.',
  planeTitle: (plane: string) => `Plano ${plane}`,
  sides: { left: 'izquierda', right: 'derecha', center: 'centro' },
  panelLabel: (
    id: string,
    where: string,
    top: number,
    bottom: number,
    depth: number,
    mesh: string,
  ) => `Panel ${id} (${where}): ${top} → ${bottom} mallas, N ${depth}, mallero ${mesh}`,
  dragHandle: (handle: string, id: string) => `Arrastrar ${handle} del panel ${id}`,
  dragTipHead: (id: string, handle: string) => `Panel ${id} · ${handle}:`,
  dragTipTail: (before: number) => `mallas (antes ${before}) · Esc cancela`,
  zoomIn: 'Acercar',
  zoomOut: 'Alejar',
  fullView: 'Vista completa',
  inspector: {
    panel: (id: string) => `Panel ${id}`,
    close: 'Cerrar el panel',
    plane: (plane: string) => `plano ${plane}`,
    minus: (field: string) => `Restar 1 a ${field}`,
    plus: (field: string) => `Sumar 1 a ${field}`,
    orientation: 'Orientación de la malla',
    squareHelp: 'En malla cuadrada las mallas cuentan cuadrados de una pata (mallero / 2) de lado.',
    reset: 'Restablecer este panel',
  },
  impact: {
    calculating: 'Calculando…',
    label: 'Impacto de los cambios',
    at: (speed: string) => ` a ${speed} kn`,
    noChange: 'sin cambio',
    baseNet: 'red de base',
  },
};
