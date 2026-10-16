/** Tratamiento de cada errata según el modo de compatibilidad (espejo de ``report.tables``). */

export type ErrataStatus = 'reproducida' | 'corregida' | 'documentada';

/** Erratas cuyo tratamiento no depende del modo (``ERRATA_FIXED_TREATMENT``). */
export const ERRATA_FIXED_TREATMENT: Record<string, readonly [ErrataStatus, string]> = {
  nomura_column_links_hamuro: [
    'documentada',
    'Sin conmutador: Nomura se calcula de verdad; el enlace del libro sólo se documenta.',
  ],
  nomura_ratio_typo: ['reproducida', 'Tabla de referencia copiada tal cual en ambos modos.'],
  panel_f_cut_na: ['corregida', 'El código de corte se calcula en ambos modos.'],
  panel_b_cut_uses_plan_coef: ['corregida', 'La razón de corte usa N en ambos modos.'],
  panel_b_cut_code_lookup_a: ['corregida', 'Cada paño busca con su propia razón.'],
  net_weight_ignores_panel_count: [
    'reproducida',
    'Peso por fila del libro en ambos modos (documentado).',
  ],
  catenary_ratio_hardcoded: [
    'reproducida',
    'fL/L = 0.216 en ambos modos; el valor de tabla se anota en las notas.',
  ],
};

export function errataStatus(
  key: string,
  compat: 'excel' | 'corrected',
): { status: ErrataStatus; note: string } {
  const fixed = ERRATA_FIXED_TREATMENT[key];
  if (fixed) return { status: fixed[0], note: fixed[1] };
  return compat === 'excel'
    ? { status: 'reproducida', note: 'Modo «reproducir Excel»: se replica el valor del libro.' }
    : { status: 'corregida', note: 'Modo «corregido»: se aplica la fórmula correcta.' };
}
