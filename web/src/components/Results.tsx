import { lazy, Suspense, useEffect, useState } from 'react';
import { HEAVY_TABS, useLowData } from '../lib/lowdata';
import { loadJson, saveJson } from '../lib/storage';
import { TAB_EVENT, TAB_IDS, TAB_KEY } from '../lib/tabs';
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
const Catalog = lazy(() => import('./Catalog').then((m) => ({ default: m.Catalog })));
const Components = lazy(() => import('./Components').then((m) => ({ default: m.Components })));
const Construction = lazy(() =>
  import('./construction/Construction').then((m) => ({ default: m.Construction })),
);
const Economics = lazy(() =>
  import('./economics/Economics').then((m) => ({ default: m.Economics })),
);
const Batch = lazy(() => import('./Batch').then((m) => ({ default: m.Batch })));

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
  // El laboratorio guiado abre pestañas desde afuera (lib/tabs.goToTab).
  useEffect(() => {
    const on = (e: Event) => {
      const id = (e as CustomEvent<string>).detail;
      if (TAB_IDS.includes(id)) setTabState(id);
    };
    window.addEventListener(TAB_EVENT, on);
    return () => window.removeEventListener(TAB_EVENT, on);
  }, []);
  const lowData = useLowData();
  const data = design.data;
  const notes = data?.notes.length ?? 0;
  const allTabs: TabDef[] = [
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
    { id: 'catalogo', label: 'Catálogo FAO' },
    { id: 'componentes', label: 'Componentes' },
    { id: 'construccion', label: 'Construcción' },
    { id: 'economia', label: 'Economía' },
    { id: 'lotes', label: 'Lotes y flota' },
    {
      id: 'notas',
      label: <>Notas y erratas {notes > 0 && <span className="badge">{notes}</span>}</>,
    },
  ];
  const tabs = lowData ? allTabs.filter((t) => !HEAVY_TABS.includes(t.id)) : allTabs;
  const active = tabs.some((t) => t.id === tab) ? tab : 'resumen';

  return (
    <>
      <Kpis />
      <section className="card" aria-label="Detalle de resultados">
        <Tabs tabs={tabs} active={active} onChange={setTab} label="Secciones de resultados">
          {active === 'resumen' && <SummaryTable />}
          <Suspense fallback={<p className="empty">Cargando…</p>}>
            {active === 'graficos' && <Charts />}
            {active === 'comparar' && <Compare />}
            {active === 'optimizar' && <Optimize onApplied={() => setTab('resumen')} />}
            {active === 'simulacion' && <Simulate />}
            {active === 'diseno' && <InteractiveDesign />}
            {active === 'catalogo' && <Catalog />}
            {active === 'componentes' && <Components />}
            {active === 'construccion' && <Construction />}
            {active === 'economia' && <Economics />}
            {active === 'lotes' && <Batch onOpened={() => setTab('resumen')} />}
          </Suspense>
          {active === 'paneles' && <PanelEditor />}
          {active === 'plano' && <PlanViewer />}
          {active === 'descargas' && <Downloads />}
          {active === 'notas' && <NotesErrata />}
        </Tabs>
      </section>
    </>
  );
}
