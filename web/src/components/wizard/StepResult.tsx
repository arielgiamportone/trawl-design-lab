import { ApiError } from '../../api/client';
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

const TONE_LABEL: Record<Tone, string> = {
  ok: 'Bien',
  warn: 'Atención',
  crit: 'Problema',
  info: 'Dato',
};

const OVERALL_TEXT: Record<Tone, string> = {
  ok: 'El diseño es viable a la velocidad elegida.',
  warn: 'El diseño es viable, pero con poco margen.',
  crit: 'El diseño no funciona así: revise los puntos marcados.',
  info: '',
};

export function StepResult({ onExpert }: { onExpert: (tab?: string) => void }) {
  const { design, state, update } = useCase();
  const d = design.data;
  if (design.error && !d) {
    const e = design.error;
    return (
      <div className="alert error" role="alert">
        <span>
          <strong>{e instanceof ApiError && e.status ? `Error ${e.status}` : 'Error'}:</strong>{' '}
          {e.message}
        </span>
      </div>
    );
  }
  if (!d) {
    return (
      <p className="status-line" role="status">
        <span className="spinner" aria-hidden="true" /> Calculando el diseño…
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
        {OVERALL_TEXT[tone]}
      </div>
      <ul className="checks">
        {checks.map((c) => {
          const url = c.chapter ? chapterUrl(c.chapter) : null;
          return (
            <li key={c.key} className={`check ${c.tone}`} data-check={c.key}>
              <span className="check-tone">{TONE_LABEL[c.tone]}</span>
              <span className="check-title">{c.title}</span>
              <span className="check-value">{c.value}</span>
              <details className="check-why">
                <summary>¿Por qué?</summary>
                <p>
                  {c.why}{' '}
                  {url && (
                    <a href={url} target="_blank" rel="noreferrer">
                      Más en el libro ↗
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
            Probar a {fmtFixed(reachable, 1)} kn (máxima viable)
          </button>
        )}
        <button type="button" className="btn primary" onClick={() => onExpert()}>
          Ver el detalle técnico (modo experto)
        </button>
        <button type="button" className="btn" onClick={() => onExpert('diseno')}>
          Ajustar la red sobre el plano
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
          Ver cómo trabaja la red (animación)
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
          ¿Qué tallas retiene el copo?
        </button>
        <button
          type="button"
          className="btn"
          onClick={() => {
            saveJson(GUIDE_VIEW_KEY, 'corte');
            onExpert('construccion');
          }}
        >
          ¿Cómo la armo? Guía para el taller
        </button>
      </div>
      <details className="accordion">
        <summary>
          <span>Descargar informe y planilla</span>
        </summary>
        <div className="accordion-body">
          <Downloads />
        </div>
      </details>
    </div>
  );
}
