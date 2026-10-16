import { tiles } from '../lib/kpis';
import { useCase } from '../state/useCase';

export function Kpis() {
  const { design } = useCase();
  const d = design.data;
  if (!d) {
    return (
      <section className="kpis" aria-label="Indicadores clave" aria-busy={design.isFetching}>
        {[
          'Abertura vertical',
          'Abertura horizontal',
          'RN a 3 kn',
          'Vel. máx. remolcable',
          'Cable seleccionado',
          'Superficie sólida',
        ].map((l) => (
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
      aria-label="Indicadores clave"
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
