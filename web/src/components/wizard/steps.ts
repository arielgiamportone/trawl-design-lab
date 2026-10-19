/** Pasos del modo guiado. */
export const STEPS = [
  { id: 'buque', title: 'Buque', sub: 'Potencia disponible' },
  { id: 'red', title: 'Red', sub: 'Red y portones' },
  { id: 'operacion', title: 'Operación', sub: 'Velocidad y profundidad' },
  { id: 'resultado', title: 'Resultado', sub: 'Diagnóstico' },
] as const;
export type StepId = (typeof STEPS)[number]['id'];
