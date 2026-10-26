import type { DesignData } from '../../api/result';
import { useT } from '../../i18n';
import { fmtFixed } from '../../lib/format';
import { toDisplay, unitLabel } from '../../lib/units';
import { impactRows } from '../../lib/impact';

interface Props {
  now: DesignData | undefined;
  base: DesignData | undefined;
  variant: 'std' | 'mod';
  speed: number;
  stale: boolean;
  hasEdits: boolean;
}

/** Indicadores en vivo de la red editada y su diferencia con la red de base. */
export function LiveImpact({ now, base, variant, speed, stale, hasEdits }: Props) {
  const T = useT().interactive.impact;
  if (!now) return <p className="empty">{T.calculating}</p>;
  const rows = impactRows(now, hasEdits ? base : now, variant, speed);
  return (
    <section
      className={`impact${stale ? ' stale' : ''}`}
      aria-label={T.label}
      aria-busy={stale}
      aria-live="polite"
    >
      {rows.map((r) => {
        const sign = r.delta !== null && r.delta > 0 ? '+' : '';
        const showDelta =
          hasEdits && r.delta !== null && Math.abs(r.delta) >= 10 ** -r.metric.digits / 2;
        const unit = unitLabel(r.metric.unit);
        const shown = (v: number | null) =>
          fmtFixed(v === null ? null : toDisplay(v, r.metric.unit), r.metric.digits);
        return (
          <div className={`impact-item ${r.tone}`} key={r.metric.key} data-impact={r.metric.key}>
            <span className="impact-label">
              {r.metric.label}
              {r.metric.key === 'rn' && T.at(fmtFixed(speed, 1))}
            </span>
            <span className="impact-value">
              {shown(r.now)} <span className="unit">{unit}</span>
            </span>
            <span className="impact-delta">
              {showDelta
                ? `${sign}${shown(r.delta)} ${unit}`
                : hasEdits
                  ? T.noChange
                  : T.baseNet}
            </span>
          </div>
        );
      })}
    </section>
  );
}
