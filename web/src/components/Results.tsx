import { lazy, Suspense, useEffect, useState } from 'react';
import { useT } from '../i18n';
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
  const T = useT();
  const L = T.expert.tabs;
  const data = design.data;
  const notes = data?.notes.length ?? 0;
  const allTabs: TabDef[] = [
    { id: 'resumen', label: L.resumen },
    { id: 'graficos', label: L.graficos },
    { id: 'diseno', label: L.diseno },
    { id: 'paneles', label: L.paneles },
    { id: 'plano', label: L.plano },
    {
      id: 'comparar',
      label: (
        <>
          {L.comparar} {pinned && <span className="badge accent">A</span>}
        </>
      ),
    },
    { id: 'optimizar', label: L.optimizar },
    { id: 'simulacion', label: L.simulacion },
    { id: 'descargas', label: L.descargas },
    { id: 'catalogo', label: L.catalogo },
    { id: 'componentes', label: L.componentes },
    { id: 'construccion', label: L.construccion },
    { id: 'economia', label: L.economia },
    { id: 'lotes', label: L.lotes },
    {
      id: 'notas',
      label: (
        <>
          {L.notas} {notes > 0 && <span className="badge">{notes}</span>}
        </>
      ),
    },
  ];
  const tabs = lowData ? allTabs.filter((t) => !HEAVY_TABS.includes(t.id)) : allTabs;
  const active = tabs.some((t) => t.id === tab) ? tab : 'resumen';

  return (
    <>
      <Kpis />
      <section className="card" aria-label={T.expert.resultsLabel}>
        <Tabs tabs={tabs} active={active} onChange={setTab} label={T.expert.sectionsLabel}>
          {active === 'resumen' && <SummaryTable />}
          <Suspense fallback={<p className="empty">{T.common.loading}</p>}>
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
