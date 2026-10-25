import { useState } from 'react';
import { AssemblyPanel } from './comp/AssemblyPanel';
import { BillOfMaterials } from './comp/BillOfMaterials';
import { ComponentCatalog } from './comp/ComponentCatalog';
import { ContributeForm } from './comp/ContributeForm';

const VIEWS = [
  { id: 'catalogo', label: 'Catálogo' },
  { id: 'materiales', label: 'Lista de materiales' },
  { id: 'armar', label: 'Armar con el catálogo' },
  { id: 'aportar', label: 'Aportar' },
] as const;

type View = (typeof VIEWS)[number]['id'];

/** Pestaña «Componentes» (Fase 13): catálogo, lista de materiales, armado óptimo y aportes. */
export function Components() {
  const [view, setView] = useState<View>('catalogo');
  return (
    <div className="components" data-testid="components">
      <p className="section-sub">
        Paño, cables, cabos, portones, boyas y cadenas de fabricantes y sus equivalentes genéricos,
        con la fuente de cada dato. Los precios son siempre orientativos.
      </p>
      <div className="segmented no-print" role="group" aria-label="Sección de componentes">
        {VIEWS.map((v) => (
          <button
            key={v.id}
            type="button"
            aria-pressed={view === v.id}
            onClick={() => setView(v.id)}
          >
            {v.label}
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
