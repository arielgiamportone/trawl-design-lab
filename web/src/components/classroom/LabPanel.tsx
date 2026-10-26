import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { api, type Lab, type LabStep } from '../../api/client';
import { classroom, pct } from '../../lib/classroom';
import { labSubmission, saveLab, useActiveLab, type ActiveLab } from '../../lib/lab';
import { goToMode } from '../../lib/mode';
import { goToTab } from '../../lib/tabs';
import { useCase } from '../../state/useCase';

const TAB_NAMES: Record<string, string> = {
  resumen: 'Resumen',
  graficos: 'Gráficos',
  diseno: 'Diseño interactivo',
  paneles: 'Editor de paneles',
  plano: 'Plano',
  comparar: 'Comparar',
  optimizar: 'Optimizar',
  simulacion: 'Simulación',
  descargas: 'Descargas',
  catalogo: 'Catálogo FAO',
  componentes: 'Componentes',
  construccion: 'Construcción',
  economia: 'Economía',
  lotes: 'Lotes y flota',
  notas: 'Notas y erratas',
};

/**
 * Panel del laboratorio en curso, sobre el modo experto: el paso, dónde hacerlo, la comprobación
 * con el caso abierto y las preguntas. Desde una tarea del aula, entrega los pasos comprobados.
 */
export function LabPanel() {
  const active = useActiveLab();
  const q = useQuery({
    queryKey: ['teaching', 'lab', active?.labId],
    queryFn: ({ signal }) => api.lab(active!.labId, signal),
    enabled: !!active,
    staleTime: Infinity,
  });
  const [collapsed, setCollapsed] = useState(false);
  if (!active) return null;
  const lab = q.data;
  return (
    <aside
      className={`lab-panel card${collapsed ? ' collapsed' : ''}`}
      aria-label="Laboratorio guiado"
      data-testid="lab-panel"
    >
      <header className="lab-head">
        <strong>{lab ? lab.title : 'Laboratorio'}</strong>
        <button
          type="button"
          className="btn ghost small"
          aria-expanded={!collapsed}
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? 'Abrir' : 'Achicar'}
        </button>
      </header>
      {q.error && (
        <p className="alert error" role="alert">
          {q.error.message}
        </p>
      )}
      {lab && !collapsed && <LabBody lab={lab} active={active} />}
    </aside>
  );
}

function LabBody({ lab, active }: { lab: Lab; active: ActiveLab }) {
  const { committed, design, dirty } = useCase();
  const n = lab.step_list.length;
  const idx = Math.min(active.step, n);
  const step = lab.step_list[idx];
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState<string | null>(null);

  const update = (next: Partial<ActiveLab>) => saveLab({ ...active, ...next });
  const go = (i: number) => {
    update({ step: i });
    const t = lab.step_list[i]?.target.tab;
    if (t) goToTab(t);
  };

  const check = async (s: LabStep) => {
    if (!committed) return;
    setBusy(true);
    setError(null);
    const answers = active.steps[s.id]?.answers ?? {};
    try {
      const result = await api.labCheck({
        lab_id: lab.id,
        step_id: s.id,
        design: committed,
        answers,
      });
      update({ steps: { ...active.steps, [s.id]: { answers, design: committed, result } } });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const leave = () => {
    saveLab(null);
    if (active.source.kind === 'assignment') goToMode('aula');
  };

  const submit = async () => {
    if (active.source.kind !== 'assignment') return;
    setBusy(true);
    setError(null);
    try {
      const r = await classroom.submit(active.source.assignmentId, active.source.item, {
        steps: labSubmission(active),
      });
      setSent(r.score === null ? r.message || 'Entrega recibida' : `Entregado: ${pct(r.score)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const done = lab.step_list.filter((s) => active.steps[s.id]?.result?.done).length;

  if (!step) {
    return (
      <div className="lab-body">
        <p>
          <strong>Fin del laboratorio.</strong> {done} de {n} pasos cumplidos.
        </p>
        {lab.closing && <p className="help">{lab.closing}</p>}
        {active.source.kind === 'assignment' && (
          <button
            type="button"
            className="btn primary"
            disabled={busy}
            onClick={() => void submit()}
          >
            Entregar al docente
          </button>
        )}
        {sent && (
          <p className="alert good" role="status">
            {sent}
          </p>
        )}
        {error && (
          <p className="alert error" role="alert">
            {error}
          </p>
        )}
        <div className="calc-row">
          <button type="button" className="btn small" onClick={() => go(n - 1)}>
            ← Volver
          </button>
          <button type="button" className="btn ghost small" onClick={leave}>
            Salir del laboratorio
          </button>
        </div>
      </div>
    );
  }

  const st = active.steps[step.id] ?? { answers: {} };
  const res = st.result;
  const setAnswer = (qid: string, v: string) =>
    update({
      steps: { ...active.steps, [step.id]: { ...st, answers: { ...st.answers, [qid]: v } } },
    });
  const qres = new Map((res?.questions ?? []).map((x) => [x.id, x]));

  return (
    <div className="lab-body">
      <p className="lab-progress">
        Paso {idx + 1} de {n} · {done} cumplidos
      </p>
      <h4>{step.title}</h4>
      <p>{step.instruction}</p>
      {step.target.tab && (
        <p className="help">
          <button type="button" className="btn small" onClick={() => goToTab(step.target.tab!)}>
            Ir a «{TAB_NAMES[step.target.tab] ?? step.target.tab}»
          </button>{' '}
          {step.target.hint}
        </p>
      )}
      {step.checks.length > 0 && (
        <ul className="lab-checks">
          {step.checks.map((c, i) => {
            const r = res?.checks[i];
            return (
              <li key={c.label} className={r ? (r.ok ? 'ok' : 'bad') : ''}>
                {r ? (r.ok ? '✓' : '✗') : '○'} {c.label}
              </li>
            );
          })}
        </ul>
      )}
      {step.questions.map((qq) => {
        const r = qres.get(qq.id);
        const fid = `lab-${step.id}-${qq.id}`;
        return (
          <div
            className={`field${r ? (r.ok === false ? ' bad' : r.ok ? ' ok' : '') : ''}`}
            key={qq.id}
          >
            <label htmlFor={fid}>
              {qq.prompt}
              {qq.unit && <span className="unit"> [{qq.unit}]</span>}
            </label>
            {qq.kind === 'choice' ? (
              <select
                id={fid}
                value={st.answers[qq.id] ?? ''}
                onChange={(e) => setAnswer(qq.id, e.target.value)}
              >
                <option value="">Elegir…</option>
                {(qq.options ?? []).map((o) => (
                  <option key={o}>{o}</option>
                ))}
              </select>
            ) : qq.kind === 'text' ? (
              <textarea
                id={fid}
                rows={3}
                value={st.answers[qq.id] ?? ''}
                onChange={(e) => setAnswer(qq.id, e.target.value)}
              />
            ) : (
              <input
                id={fid}
                inputMode="decimal"
                autoComplete="off"
                value={st.answers[qq.id] ?? ''}
                onChange={(e) => setAnswer(qq.id, e.target.value)}
              />
            )}
            {r && (
              <span className="aula-mark">
                {r.ok === null ? r.message : r.ok ? '✓ correcta' : `✗ ${r.message}`}
                {r.ok === false && r.expected_text ? ` · su caso da ${r.expected_text}` : ''}
              </span>
            )}
          </div>
        );
      })}
      {error && (
        <p className="alert error" role="alert">
          {error}
        </p>
      )}
      {res && (
        <p className={`alert ${res.done ? 'good' : 'warn'}`} role="status">
          {res.done ? 'Paso cumplido.' : 'Todavía falta algo: revise las marcas.'}
        </p>
      )}
      <div className="calc-row">
        <button
          type="button"
          className="btn primary"
          disabled={busy || !committed || dirty || design.isFetching}
          onClick={() => void check(step)}
        >
          {busy ? 'Comprobando…' : 'Comprobar con mi caso'}
        </button>
      </div>
      <div className="calc-row">
        <button
          type="button"
          className="btn small"
          disabled={idx === 0}
          onClick={() => go(idx - 1)}
        >
          ← Anterior
        </button>
        <button type="button" className="btn small" onClick={() => go(idx + 1)}>
          {idx + 1 < n ? 'Siguiente →' : 'Terminar'}
        </button>
        <button type="button" className="btn ghost small" onClick={leave}>
          Salir
        </button>
      </div>
    </div>
  );
}
