import type { DesignData } from '../../api/result';
import { fmtFixed } from '../../lib/format';
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
  if (!now) return <p className="empty">Calculando…</p>;
  const rows = impactRows(now, hasEdits ? base : now, variant, speed);
  return (
    <section
      className={`impact${stale ? ' stale' : ''}`}
      aria-label="Impacto de los cambios"
      aria-busy={stale}
      aria-live="polite"
    >
      {rows.map((r) => {
        const sign = r.delta !== null && r.delta > 0 ? '+' : '';
        const showDelta =
          hasEdits && r.delta !== null && Math.abs(r.delta) >= 10 ** -r.metric.digits / 2;
        return (
          <div className={`impact-item ${r.tone}`} key={r.metric.key} data-impact={r.metric.key}>
            <span className="impact-label">
              {r.metric.label}
              {r.metric.key === 'rn' && ` a ${fmtFixed(speed, 1)} kn`}
            </span>
            <span className="impact-value">
              {fmtFixed(r.now, r.metric.digits)} <span className="unit">{r.metric.unit}</span>
            </span>
            <span className="impact-delta">
              {showDelta
                ? `${sign}${fmtFixed(r.delta, r.metric.digits)} ${r.metric.unit}`
                : hasEdits
                  ? 'sin cambio'
                  : 'red de base'}
            </span>
          </div>
        );
      })}
    </section>
  );
}
