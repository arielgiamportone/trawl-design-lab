/** Tratamiento de cada errata según el modo de compatibilidad (espejo de ``report.tables``). */
import { msg } from '../i18n';
import { localized } from './labels';

export type ErrataStatus = 'reproducida' | 'corregida' | 'documentada';

/** Erratas cuyo tratamiento no depende del modo (``ERRATA_FIXED_TREATMENT``). */
const FIXED_STATUS: Record<string, ErrataStatus> = {
  nomura_column_links_hamuro: 'documentada',
  nomura_ratio_typo: 'reproducida',
  panel_f_cut_na: 'corregida',
  panel_b_cut_uses_plan_coef: 'corregida',
  panel_b_cut_code_lookup_a: 'corregida',
  net_weight_ignores_panel_count: 'reproducida',
  catenary_ratio_hardcoded: 'reproducida',
};

/** Estado fijo y nota (idioma activo) de las erratas cuyo tratamiento no depende del modo. */
export const ERRATA_FIXED_TREATMENT: Record<string, readonly [ErrataStatus, string]> = localized(
  () => {
    const notes = msg().labels.errataFixed as Record<string, string>;
    const out: Record<string, readonly [ErrataStatus, string]> = {};
    for (const [k, st] of Object.entries(FIXED_STATUS)) out[k] = [st, notes[k] ?? ''];
    return out;
  },
);

/** Nombre del estado en el idioma activo (el valor interno sigue en español). */
export function errataStatusLabel(status: ErrataStatus): string {
  return msg().labels.errataStatus[status];
}

export function errataStatus(
  key: string,
  compat: 'excel' | 'corrected',
): { status: ErrataStatus; note: string } {
  const fixed = ERRATA_FIXED_TREATMENT[key];
  if (fixed) return { status: fixed[0], note: fixed[1] };
  return compat === 'excel'
    ? { status: 'reproducida', note: msg().labels.errataExcel }
    : { status: 'corregida', note: msg().labels.errataCorrected };
}
