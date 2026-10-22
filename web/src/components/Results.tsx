import { lazy, Suspense, useState } from 'react';
import { loadJson, saveJson } from '../lib/storage';
import { TAB_IDS, TAB_KEY } from '../lib/tabs';
import { useCase } from '../state/useCase';
import { Downloads } from './Downloads';
import { Kpis } from './Kpis';
import { NotesErrata } from './NotesErrata';
import { PanelEditor } from './PanelEditor';
import { PlanViewer } from './PlanViewer';
import { SummaryTable } from './SummaryTable';
import { Tabs, type TabDef } from './Tabs';

// Recharts sólo se descarga al abrir Gráficos o Comparar.
const Charts = lazy(() => import('./charts/Charts').then((m) => ({ default: m.Charts })));
const Compare = lazy(() => import('./Compare').then((m) => ({ default: m.Compare })));
// Optimizar y Simulación también se cargan al abrirlas.
const Optimize = lazy(() => import('./Optimize').then((m) => ({ default: m.Optimize })));
const InteractiveDesign = lazy(() =>
  import('./interactive/InteractiveDesign').then((m) => ({ default: m.InteractiveDesign })),
);
const Simulate = lazy(() => import('./Simulate').then((m) => ({ default: m.Simulate })));

export function Results() {
  const { design, pinned } = useCase();
  const [tab, setTabState] = useState<string>(() => {
    const t = loadJson<string>(TAB_KEY);
    return t && TAB_IDS.includes(t) ? t : 'resumen';
  });
  const setTab = (t: string) => {
    setTabState(t);
    saveJson(TAB_KEY, t);
  };
  const data = design.data;
  const notes = data?.notes.length ?? 0;
  const tabs: TabDef[] = [
    { id: 'resumen', label: 'Resumen' },
    { id: 'graficos', label: 'Gráficos' },
    { id: 'diseno', label: 'Diseño interactivo' },
    { id: 'paneles', label: 'Editor de paneles' },
    { id: 'plano', label: 'Plano' },
    {
      id: 'comparar',
      label: <>Comparar {pinned && <span className="badge accent">A</span>}</>,
    },
    { id: 'optimizar', label: 'Optimizar' },
    { id: 'simulacion', label: 'Simulación' },
    { id: 'descargas', label: 'Descargas' },
    {
      id: 'notas',
      label: <>Notas y erratas {notes > 0 && <span className="badge">{notes}</span>}</>,
    },
  ];

  return (
    <>
      <Kpis />
      <section className="card" aria-label="Detalle de resultados">
        <Tabs tabs={tabs} active={tab} onChange={setTab} label="Secciones de resultados">
          {tab === 'resumen' && <SummaryTable />}
          <Suspense fallback={<p className="empty">Cargando…</p>}>
            {tab === 'graficos' && <Charts />}
            {tab === 'comparar' && <Compare />}
            {tab === 'optimizar' && <Optimize onApplied={() => setTab('resumen')} />}
            {tab === 'simulacion' && <Simulate />}
            {tab === 'diseno' && <InteractiveDesign />}
          </Suspense>
          {tab === 'paneles' && <PanelEditor />}
          {tab === 'plano' && <PlanViewer />}
          {tab === 'descargas' && <Downloads />}
          {tab === 'notas' && <NotesErrata />}
        </Tabs>
      </section>
    </>
  );
}
