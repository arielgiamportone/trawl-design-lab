import { useState } from 'react';
import { CasePanel } from './components/CasePanel';
import { Header } from './components/Header';
import { ProjectBar } from './components/ProjectBar';
import { Results } from './components/Results';
import { Wizard } from './components/wizard/Wizard';
import { initialMode, saveMode, type UiMode } from './lib/mode';
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
            <Wizard onExpert={() => setMode('expert')} />
          </main>
        ) : (
          <div className="layout">
            <CasePanel />
            <main id="resultados" className="results" tabIndex={-1} aria-label="Resultados">
              <Results />
            </main>
          </div>
        )}
        <footer className="footer">
          trawl-design-lab · motor trawlkit · resultados orientativos: verifique con el plano y el
          informe antes de construir.
        </footer>
      </CaseProvider>
    </ConnectionProvider>
  );
}
