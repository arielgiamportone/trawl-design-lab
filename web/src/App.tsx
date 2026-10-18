import { CasePanel } from './components/CasePanel';
import { Header } from './components/Header';
import { Results } from './components/Results';
import { CaseProvider } from './state/CaseProvider';
import { ConnectionProvider } from './state/ConnectionProvider';

export function App() {
  return (
    <ConnectionProvider>
      <CaseProvider>
        <a className="skip-link" href="#resultados">
          Saltar a resultados
        </a>
        <Header />
        <div className="layout">
          <CasePanel />
          <main id="resultados" className="results" tabIndex={-1} aria-label="Resultados">
            <Results />
          </main>
        </div>
        <footer className="footer">
          trawl-design-lab · motor trawlkit · resultados orientativos: verifique con el plano y el
          informe antes de construir.
        </footer>
      </CaseProvider>
    </ConnectionProvider>
  );
}
