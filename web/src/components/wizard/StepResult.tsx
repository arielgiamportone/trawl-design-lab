import { ApiError } from '../../api/client';
import { useT } from '../../i18n';
import { chapterUrl } from '../../lib/docs';
import { catchPreset, EXPLORE_FORM_KEY } from '../../lib/explore';
import { GUIDE_VIEW_KEY } from '../../lib/construction';
import { remember } from '../../lib/memo';
import { saveJson } from '../../lib/storage';
import { DEFAULT_SEL, SEL_FORM_KEY } from '../../lib/selectivity';
import { SIM_VIEW_KEY } from '../../lib/simulate';
import { fmtFixed } from '../../lib/format';
import { designPropeller, perfWindow } from '../../lib/series';
import { assess, overall, type Tone } from '../../lib/verdict';
import { useCase } from '../../state/useCase';
import { Downloads } from '../Downloads';

export function StepResult({ onExpert }: { onExpert: (tab?: string) => void }) {
  const { design, state, update } = useCase();
  const d = design.data;
  const T = useT().wizard.result;
  if (design.error && !d) {
    const e = design.error;
    return (
      <div className="alert error" role="alert">
        <span>
          <strong>{e instanceof ApiError && e.status ? T.errorStatus(e.status) : T.error}:</strong>{' '}
          {e.message}
        </span>
      </div>
    );
  }
  if (!d) {
    return (
      <p className="status-line" role="status">
        <span className="spinner" aria-hidden="true" /> {T.calculating}
      </p>
    );
  }
  const checks = assess(d, state.targetSpeed);
  const tone = overall(checks);
  const stale = design.isFetching || design.isPlaceholderData;
  // Si la velocidad elegida no se alcanza, se ofrece la mayor viable (redondeada hacia abajo).
  const max = perfWindow(d, designPropeller(d), 'std')?.max_speed_kn ?? null;
  const reachable = max !== null && max >= 1 ? Math.floor(max * 10) / 10 : null;
  return (
    <div className={stale ? 'stale' : undefined} aria-busy={stale}>
      <div className={`verdict-banner ${tone}`} role="status" data-overall={tone}>
        <span className="verdict-dot" aria-hidden="true" />
        {T.overall[tone]}
      </div>
      <ul className="checks">
        {checks.map((c) => {
          const url = c.chapter ? chapterUrl(c.chapter) : null;
          return (
            <li key={c.key} className={`check ${c.tone}`} data-check={c.key}>
              <span className="check-tone">{T.tone[c.tone as Tone]}</span>
              <span className="check-title">{c.title}</span>
              <span className="check-value">{c.value}</span>
              <details className="check-why">
                <summary>{T.why}</summary>
                <p>
                  {c.why}{' '}
                  {url && (
                    <a href={url} target="_blank" rel="noreferrer">
                      {T.more}
                    </a>
                  )}
                </p>
              </details>
            </li>
          );
        })}
      </ul>
      <div className="wizard-actions">
        {reachable !== null && state.targetSpeed > max! && (
          <button type="button" className="btn" onClick={() => update({ targetSpeed: reachable })}>
            {T.tryAt(fmtFixed(reachable, 1))}
          </button>
        )}
        <button type="button" className="btn primary" onClick={() => onExpert()}>
          {T.expert}
        </button>
        <button type="button" className="btn" onClick={() => onExpert('diseno')}>
          {T.adjust}
        </button>
        <button
          type="button"
          className="btn"
          onClick={() => {
            remember(SIM_VIEW_KEY, 'explore');
            remember(
              EXPLORE_FORM_KEY,
              catchPreset(
                state.expectedCatchKg,
                state.params.seabed || null,
                Math.min(5, Math.max(1, Math.round(state.targetSpeed * 2) / 2)),
              ),
            );
            onExpert('simulacion');
          }}
        >
          {T.animation}
        </button>
        <button
          type="button"
          className="btn"
          onClick={() => {
            remember(SIM_VIEW_KEY, 'selectivity');
            remember(SEL_FORM_KEY, {
              ...DEFAULT_SEL,
              catchKg: state.expectedCatchKg || DEFAULT_SEL.catchKg,
              seabed: state.params.seabed || DEFAULT_SEL.seabed,
              speed: Math.min(5, Math.max(1, Math.round(state.targetSpeed * 2) / 2)),
            });
            onExpert('simulacion');
          }}
        >
          {T.selectivity}
        </button>
        <button
          type="button"
          className="btn"
          onClick={() => {
            saveJson(GUIDE_VIEW_KEY, 'corte');
            onExpert('construccion');
          }}
        >
          {T.construction}
        </button>
        <button type="button" className="btn" onClick={() => onExpert('economia')}>
          {T.economics}
        </button>
      </div>
      <details className="accordion">
        <summary>
          <span>{T.downloads}</span>
        </summary>
        <div className="accordion-body">
          <Downloads />
        </div>
      </details>
    </div>
  );
}
