import { useEffect, useId, useRef, useState } from 'react';
import { useT } from '../../i18n';
import { loadJson, saveJson } from '../../lib/storage';
import { useCase } from '../../state/useCase';
import { StepNet } from './StepNet';
import { StepOperation } from './StepOperation';
import { StepResult } from './StepResult';
import { StepVessel } from './StepVessel';
import { STEPS } from './steps';

const STEP_KEY = 'trawl-design-lab:wizard-step';

/** Modo guiado: el mismo caso de diseño, en cuatro pasos y con diagnóstico en lenguaje llano. */
export function Wizard({ onExpert }: { onExpert: (tab?: string) => void }) {
  const { catalogs, errors } = useCase();
  const T = useT().wizard;
  const [step, setStepState] = useState<number>(() => {
    const s = loadJson<number>(STEP_KEY);
    return typeof s === 'number' && s >= 0 && s < STEPS.length ? s : 0;
  });
  const headingRef = useRef<HTMLHeadingElement>(null);
  const first = useRef(true);
  const ids = useId();
  const setStep = (s: number) => {
    setStepState(s);
    saveJson(STEP_KEY, s);
  };
  // Al cambiar de paso, el foco va al título (lectores de pantalla y teclado).
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    headingRef.current?.focus();
  }, [step]);

  const current = (STEPS[step] ?? STEPS[0])!;
  const nErrors = Object.keys(errors).length;
  const last = step === STEPS.length - 1;

  return (
    <div className="wizard">
      <nav aria-label={T.stepsLabel}>
        <ol className="stepper">
          {STEPS.map((s, i) => (
            <li key={s.id} className={i === step ? 'current' : i < step ? 'done' : ''}>
              <button
                type="button"
                onClick={() => setStep(i)}
                aria-current={i === step ? 'step' : undefined}
              >
                <span className="step-num" aria-hidden="true">
                  {i < step ? '✓' : i + 1}
                </span>
                <span className="step-text">
                  <span className="step-title">{s.title}</span>
                  <span className="step-sub">{s.sub}</span>
                </span>
              </button>
            </li>
          ))}
        </ol>
      </nav>

      <section className="card card-pad wizard-body" aria-labelledby={`${ids}-h`}>
        <h2 id={`${ids}-h`} className="wizard-title" tabIndex={-1} ref={headingRef}>
          {T.stepHeading(step + 1, STEPS.length, current.title)}
        </h2>
        {catalogs.error && (
          <div className="alert error" role="alert">
            <span>
              <strong>{T.catalogError}</strong> {catalogs.error.message}
            </span>
          </div>
        )}
        {current.id === 'buque' && <StepVessel onBatch={() => onExpert('lotes')} />}
        {current.id === 'red' && <StepNet />}
        {current.id === 'operacion' && <StepOperation />}
        {current.id === 'resultado' && <StepResult onExpert={onExpert} />}

        <div className="wizard-nav">
          <button
            type="button"
            className="btn"
            onClick={() => setStep(step - 1)}
            disabled={step === 0}
          >
            {T.prev}
          </button>
          {nErrors > 0 && !last && (
            <span className="help" role="status">
              {T.toFix(nErrors)}
            </span>
          )}
          {!last ? (
            <button
              type="button"
              className="btn primary"
              onClick={() => setStep(step + 1)}
              disabled={nErrors > 0}
            >
              {step === STEPS.length - 2 ? T.seeResult : T.next}
            </button>
          ) : (
            <button type="button" className="btn" onClick={() => setStep(0)}>
              {T.restart}
            </button>
          )}
        </div>
      </section>
    </div>
  );
}
