import { lazy, Suspense, useState } from 'react';
import { loadJson, saveJson } from '../lib/storage';
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

const TAB_KEY = 'trawl-design-lab:tab';
const TAB_IDS = ['resumen', 'graficos', 'paneles', 'plano', 'comparar', 'descargas', 'notas'];

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
    { id: 'paneles', label: 'Editor de paneles' },
    { id: 'plano', label: 'Plano' },
    {
      id: 'comparar',
      label: <>Comparar {pinned && <span className="badge accent">A</span>}</>,
    },
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
          <Suspense fallback={<p className="empty">Cargando gráficos…</p>}>
            {tab === 'graficos' && <Charts />}
            {tab === 'comparar' && <Compare />}
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
