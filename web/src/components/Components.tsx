import { useState } from 'react';
import { useT } from '../i18n';
import { AssemblyPanel } from './comp/AssemblyPanel';
import { BillOfMaterials } from './comp/BillOfMaterials';
import { ComponentCatalog } from './comp/ComponentCatalog';
import { ContributeForm } from './comp/ContributeForm';

const VIEWS = ['catalogo', 'materiales', 'armar', 'aportar'] as const;

type View = (typeof VIEWS)[number];

/** Pestaña «Componentes» (Fase 13): catálogo, lista de materiales, armado óptimo y aportes. */
export function Components() {
  const [view, setView] = useState<View>('catalogo');
  const T = useT().components;
  return (
    <div className="components" data-testid="components">
      <p className="section-sub">{T.intro}</p>
      <div className="segmented no-print" role="group" aria-label={T.section}>
        {VIEWS.map((v) => (
          <button key={v} type="button" aria-pressed={view === v} onClick={() => setView(v)}>
            {T.views[v]}
          </button>
        ))}
      </div>
      {view === 'catalogo' && <ComponentCatalog />}
      {view === 'materiales' && <BillOfMaterials />}
      {view === 'armar' && <AssemblyPanel />}
      {view === 'aportar' && <ContributeForm />}
    </div>
  );
}
