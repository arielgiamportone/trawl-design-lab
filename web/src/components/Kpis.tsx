import { useT } from '../i18n';
import { tiles } from '../lib/kpis';
import { useCase } from '../state/useCase';

const KEYS = [
  'vertical_opening_m',
  'horizontal_opening_m',
  'rn_std_3kn_kgf',
  'max_speed_kn',
  'warp_selected',
  'solid_surface_m2',
] as const;

export function Kpis() {
  const { design } = useCase();
  const d = design.data;
  const T = useT();
  if (!d) {
    return (
      <section className="kpis" aria-label={T.expert.kpisLabel} aria-busy={design.isFetching}>
        {KEYS.map((k) => T.labels.kpis[k]).map((l) => (
          <div className="card kpi" key={l}>
            <span className="kpi-label">{l}</span>
            <span className="kpi-value" aria-hidden="true">
              —
            </span>
          </div>
        ))}
      </section>
    );
  }
  const stale = design.isFetching || design.isPlaceholderData;
  return (
    <section
      className={`kpis${stale ? ' stale' : ''}`}
      aria-label={T.expert.kpisLabel}
      aria-busy={stale}
    >
      {tiles(d).map((t) => (
        <div className="card kpi" key={t.key} data-kpi={t.key}>
          <span className="kpi-label">{t.label}</span>
          <span className={`kpi-value${t.text ? ' text' : ''}`}>
            {t.value}
            {t.unit && <span className="unit">{t.unit}</span>}
          </span>
          {t.badge && (
            <span className={`badge ${t.badge.tone}`} style={{ alignSelf: 'flex-start' }}>
              {t.badge.text}
            </span>
          )}
          {t.sub && <span className="kpi-sub">{t.sub}</span>}
        </div>
      ))}
    </section>
  );
}
