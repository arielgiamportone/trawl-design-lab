/** Pasos del modo guiado. */
import { msg } from '../../i18n';
import { localized } from '../../lib/labels';

const STEP_IDS = ['buque', 'red', 'operacion', 'resultado'] as const;
export type StepId = (typeof STEP_IDS)[number];

export interface StepDef {
  id: StepId;
  title: string;
  sub: string;
}

/** Pasos con título y subtítulo en el idioma activo (se leen en cada acceso). */
export const STEPS: readonly StepDef[] = localized(() =>
  STEP_IDS.map((id) => ({ id, ...msg().wizard.steps[id] })),
);
