import { useQueryClient } from '@tanstack/react-query';
import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { CasePanel } from './components/CasePanel';
import { Header } from './components/Header';
import { OfflinePanel } from './components/OfflinePanel';
import { ProjectBar } from './components/ProjectBar';
import { Results } from './components/Results';
import { Wizard } from './components/wizard/Wizard';
import { LabPanel } from './components/classroom/LabPanel';
import { useLang, useT } from './i18n';
import { useActiveLab } from './lib/lab';
import { useUnits } from './lib/units';
import { initialMode, MODE_EVENT, saveMode, type UiMode } from './lib/mode';
import { saveJson } from './lib/storage';
import { TAB_KEY } from './lib/tabs';
import { CaseProvider } from './state/CaseProvider';
import { ConnectionProvider } from './state/ConnectionProvider';

// El aula se descarga al abrirla.
const Classroom = lazy(() =>
  import('./components/classroom/Classroom').then((m) => ({ default: m.Classroom })),
);

export function App() {
  const [mode, setModeState] = useState<UiMode>(initialMode);
  const setMode = (m: UiMode) => {
    setModeState(m);
    saveMode(m);
  };
  // El aula y el laboratorio cambian de modo desde adentro (lib/mode.goToMode).
  useEffect(() => {
    const on = (e: Event) => setModeState((e as CustomEvent<UiMode>).detail);
    window.addEventListener(MODE_EVENT, on);
    return () => window.removeEventListener(MODE_EVENT, on);
  }, []);
  const lab = useActiveLab();
  const T = useT();
  const lang = useLang();
  const units = useUnits();
  // Al cambiar de idioma, la API vuelve a responder los textos del motor en el idioma nuevo.
  const qc = useQueryClient();
  const firstLang = useRef(lang);
  useEffect(() => {
    if (lang === firstLang.current) return;
    firstLang.current = lang;
    void qc.invalidateQueries();
  }, [lang, qc]);
  return (
    <ConnectionProvider>
      <CaseProvider>
        {/* Idioma y unidades vuelven a montar la interfaz (el caso y la conexión se conservan). */}
        <Shell key={`${lang}:${units}`} mode={mode} setMode={setMode} lab={!!lab} T={T} />
      </CaseProvider>
    </ConnectionProvider>
  );
}

interface ShellProps {
  mode: UiMode;
  setMode: (m: UiMode) => void;
  lab: boolean;
  T: ReturnType<typeof useT>;
}

function Shell({ mode, setMode, lab, T }: ShellProps) {
  return (
    <>
      <a className="skip-link" href="#resultados">
        {T.app.skip[mode]}
      </a>
      <Header mode={mode} onModeChange={setMode} />
      <div className="subbar">
        <ProjectBar />
      </div>
      {mode === 'aula' ? (
        <main id="resultados" className="aula-layout" tabIndex={-1} aria-label={T.app.main.aula}>
          <Suspense fallback={<p className="empty">{T.common.loading}</p>}>
            <Classroom />
          </Suspense>
        </main>
      ) : mode === 'simple' ? (
        <main
          id="resultados"
          className="wizard-layout"
          tabIndex={-1}
          aria-label={T.app.main.simple}
        >
          <Wizard
            onExpert={(tab) => {
              if (tab) saveJson(TAB_KEY, tab);
              setMode('expert');
            }}
          />
        </main>
      ) : (
        <div className="layout">
          <CasePanel />
          <main id="resultados" className="results" tabIndex={-1} aria-label={T.app.main.expert}>
            <Results />
          </main>
        </div>
      )}
      {lab && mode === 'expert' && <LabPanel />}
      <div className="offline-wrap">
        <OfflinePanel />
      </div>
      <footer className="footer">
        <p>{T.app.footer}</p>
        <p data-testid="footer-utn">
          {T.app.footerUtn} ·{' '}
          <a href="https://www.frtdf.utn.edu.ar/" target="_blank" rel="noreferrer">
            FRTDF
          </a>{' '}
          ·{' '}
          <a href="https://www.frch.utn.edu.ar/" target="_blank" rel="noreferrer">
            FRCh
          </a>{' '}
          ·{' '}
          <a href="https://mdp.utn.edu.ar/" target="_blank" rel="noreferrer">
            FRMDP
          </a>
        </p>
      </footer>
    </>
  );
}
