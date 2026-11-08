/** Estado de cada errata según el modo de compatibilidad.
 *
 * El estado lo declara el motor (``trawlkit.compat.ERRATA``) y llega con ``GET /errata``; la app
 * no lo deduce por su cuenta, para que coincida con la API, los informes y ``docs/erratas.md``.
 */
import type { Erratum } from '../api/client';
import { msg } from '../i18n';

export type ErrataStatus = Erratum['status_corrected'];

/** Nombre del estado en el idioma activo. */
export function errataStatusLabel(status: ErrataStatus): string {
  return msg().labels.errataStatus[status];
}

/** Estado y nota de la errata en el modo ``compat``. */
export function errataStatus(
  e: Erratum,
  compat: 'excel' | 'corrected',
): { status: ErrataStatus; note: string } {
  const status = compat === 'excel' ? e.status_excel : e.status_corrected;
  if (e.note) return { status, note: e.note };
  return {
    status,
    note: compat === 'excel' ? msg().labels.errataExcel : msg().labels.errataCorrected,
  };
}
