import { lazy, Suspense, useEffect, useState } from 'react';
import { CasePanel } from './components/CasePanel';
import { Header } from './components/Header';
import { OfflinePanel } from './components/OfflinePanel';
import { ProjectBar } from './components/ProjectBar';
import { Results } from './components/Results';
import { Wizard } from './components/wizard/Wizard';
import { LabPanel } from './components/classroom/LabPanel';
import { useActiveLab } from './lib/lab';
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
  return (
    <ConnectionProvider>
      <CaseProvider>
        <a className="skip-link" href="#resultados">
          {mode === 'simple'
            ? 'Saltar al asistente'
            : mode === 'aula'
              ? 'Saltar al aula'
              : 'Saltar a resultados'}
        </a>
        <Header mode={mode} onModeChange={setMode} />
        <div className="subbar">
          <ProjectBar />
        </div>
        {mode === 'aula' ? (
          <main id="resultados" className="aula-layout" tabIndex={-1} aria-label="Aula UTN">
            <Suspense fallback={<p className="empty">Cargando…</p>}>
              <Classroom />
            </Suspense>
          </main>
        ) : mode === 'simple' ? (
          <main id="resultados" className="wizard-layout" tabIndex={-1} aria-label="Diseño guiado">
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
            <main id="resultados" className="results" tabIndex={-1} aria-label="Resultados">
              <Results />
            </main>
          </div>
        )}
        {lab && mode === 'expert' && <LabPanel />}
        <div className="offline-wrap">
          <OfflinePanel />
        </div>
        <footer className="footer">
          <p>
            trawl-design-lab · motor trawlkit · resultados orientativos: verifique con el plano y el
            informe antes de construir.
          </p>
          <p data-testid="footer-utn">
            Hecho en la UTN · Ingeniería Pesquera ·{' '}
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
      </CaseProvider>
    </ConnectionProvider>
  );
}
