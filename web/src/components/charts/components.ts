/** Componentes de la resistencia total (orden fijo de color validado). */
import { msg } from '../../i18n';
import { localized } from '../../lib/labels';

const DEFS = [
  { key: 'rn', color: 's7' },
  { key: 'floats', color: 's3' },
  { key: 'warps', color: 's4' },
  { key: 'doors', color: 's5' },
] as const;

type Def = (typeof DEFS)[number];

/** Componentes con el nombre en el idioma activo (se leen en cada acceso). */
export const COMPONENTS: readonly (Def & { name: string })[] = localized(() =>
  DEFS.map((d) => ({ ...d, name: msg().charts.components[d.key] })),
);
