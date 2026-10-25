import { useState } from 'react';
import { CasePanel } from './components/CasePanel';
import { Header } from './components/Header';
import { OfflinePanel } from './components/OfflinePanel';
import { ProjectBar } from './components/ProjectBar';
import { Results } from './components/Results';
import { Wizard } from './components/wizard/Wizard';
import { initialMode, saveMode, type UiMode } from './lib/mode';
import { saveJson } from './lib/storage';
import { TAB_KEY } from './lib/tabs';
import { CaseProvider } from './state/CaseProvider';
import { ConnectionProvider } from './state/ConnectionProvider';

export function App() {
  const [mode, setModeState] = useState<UiMode>(initialMode);
  const setMode = (m: UiMode) => {
    setModeState(m);
    saveMode(m);
  };
  return (
    <ConnectionProvider>
      <CaseProvider>
        <a className="skip-link" href="#resultados">
          {mode === 'simple' ? 'Saltar al asistente' : 'Saltar a resultados'}
        </a>
        <Header mode={mode} onModeChange={setMode} />
        <div className="subbar">
          <ProjectBar />
        </div>
        {mode === 'simple' ? (
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
