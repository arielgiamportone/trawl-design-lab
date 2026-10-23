import { useQuery } from '@tanstack/react-query';
import { lazy, Suspense, useId, useState } from 'react';
import { api, ApiError, type HaulRequest } from '../../api/client';
import { fmt, fmtFixed } from '../../lib/format';
import {
  CATCH_TYPES,
  DEFAULT_HAUL,
  catchSteps,
  haulRequest,
  haulRows,
  haulSummary,
  type HaulForm,
} from '../../lib/haul';
import { recall, remember } from '../../lib/memo';
import { isSimGeometry } from '../../lib/sim3d';
import { SIM_SPEEDS, speedLabel } from '../../lib/simulate';
import { useCase } from '../../state/useCase';
import { DataTable } from '../charts/ChartParts';
import { HelpTip } from '../HelpTip';
import { HaulChart } from './HaulChart';

const Net3D = lazy(() => import('../sim3d/Net3D').then((m) => ({ default: m.Net3D })));
const FORM_KEY = 'haul:form';
const REQ_KEY = 'haul:request';

/** Lance progresivo: la red con captura creciente, fondo elegido y portones acoplados. */
export function Haul() {
  const { committed, state } = useCase();
  const ids = useId();
  const [form, setFormState] = useState<HaulForm>(() => ({
    ...DEFAULT_HAUL,
    speed: state.targetSpeed,
    maxCatchKg: state.expectedCatchKg || DEFAULT_HAUL.maxCatchKg,
    seabed: state.params.seabed || DEFAULT_HAUL.seabed,
    ...(recall<HaulForm>(FORM_KEY) ?? {}),
  }));
  const setForm = (patch: Partial<HaulForm>) =>
    setFormState((f) => {
      const next = { ...f, ...patch };
      remember(FORM_KEY, next);
      return next;
    });
  const [submitted, setSubmitted] = useState<string | null>(() => recall<string>(REQ_KEY) ?? null);
  const [step3d, setStep3d] = useState<number | null>(null);
  const seabeds = useQuery({
    queryKey: ['seabeds'],
    queryFn: ({ signal }) => api.seabeds(signal),
    staleTime: Infinity,
  });
  const query = useQuery({
    queryKey: ['haul', submitted],
    queryFn: ({ signal }) => api.haul(JSON.parse(submitted as string) as HaulRequest, signal),
    enabled: submitted !== null,
    staleTime: Infinity,
    gcTime: 30 * 60_000,
    retry: false,
  });
  const run = () => {
    if (!committed) return;
    const key = JSON.stringify(haulRequest(committed, form));
    remember(REQ_KEY, key);
    setStep3d(null);
    if (key === submitted) void query.refetch();
    else setSubmitted(key);
  };

  const r = query.data;
  const rows = r ? haulRows(r) : [];
  const summary = haulSummary(rows);
  const steps = catchSteps(form.maxCatchKg, form.steps);
  const sb = seabeds.data?.find((s) => s.id === form.seabed);
  const engine = (r?.engine ?? {}) as Record<string, number>;
  const geoIdx = step3d ?? (r ? r.results.length - 1 : 0);
  const geometry = r?.results[geoIdx];

  return (
    <div className="haul">
      <p className="section-sub">
        Simula el lance mientras entra la captura: la «bola» de captura llena el copo, lo infla y lo
        frena; los portones se acomodan al equilibrio (cable hasta el buque, sustentación de su
        polar y roce con el fondo elegido).
      </p>
      <div className="opt-form haul-form" role="group" aria-label="Escenario del lance">
        <div className="field">
          <label htmlFor={`${ids}-speed`}>Velocidad [kn]</label>
          <select
            id={`${ids}-speed`}
            value={form.speed}
            onChange={(e) => setForm({ speed: Number(e.target.value) })}
          >
            {SIM_SPEEDS.map((v) => (
              <option key={v} value={v}>
                {speedLabel(v)}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor={`${ids}-catch`}>
            Captura final [kg] <HelpTip topic="catch_kg" label="Captura final" />
          </label>
          <input
            id={`${ids}-catch`}
            type="number"
            min={0}
            max={20000}
            step={50}
            value={form.maxCatchKg}
            onChange={(e) => setForm({ maxCatchKg: Math.max(0, Number(e.target.value) || 0) })}
          />
          <span className="help">Pasos: {steps.map((v) => fmt(v)).join(' · ')} kg</span>
        </div>
        <div className="field">
          <label htmlFor={`${ids}-type`}>Tipo de captura</label>
          <select
            id={`${ids}-type`}
            value={form.catchType}
            onChange={(e) => setForm({ catchType: e.target.value as HaulForm['catchType'] })}
          >
            {CATCH_TYPES.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label} ({c.bulk} kg/m³)
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor={`${ids}-seabed`}>
            Fondo <HelpTip topic="seabed" label="Tipo de fondo" />
          </label>
          <select
            id={`${ids}-seabed`}
            value={form.seabed ?? ''}
            onChange={(e) => setForm({ seabed: e.target.value || null })}
          >
            {(seabeds.data ?? []).map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
          {sb && (
            <span className="help">
              μ tren {fmtFixed(Number(sb.mu_gear.nominal), 2)} · μ portón{' '}
              {fmtFixed(Number(sb.mu_door.nominal), 2)} (estimados, con rango)
            </span>
          )}
        </div>
        <div className="field">
          <span className="label">Resolución</span>
          <div className="segmented">
            {[3, 4].map((res) => (
              <label key={res}>
                <input
                  type="radio"
                  name={`${ids}-res`}
                  checked={form.resolution === res}
                  onChange={() => setForm({ resolution: res })}
                />
                {res === 3 ? 'Rápida (3)' : 'Normal (4)'}
              </label>
            ))}
          </div>
        </div>
        <label className="check small">
          <input
            type="checkbox"
            checked={form.coupledDoors}
            onChange={(e) => setForm({ coupledDoors: e.target.checked })}
          />
          Portones acoplados (separación por equilibrio)
        </label>
      </div>
      <div className="calc-row">
        <button
          type="button"
          className="btn primary"
          onClick={run}
          disabled={!committed || query.isFetching}
        >
          Simular lance
        </button>
      </div>
      <div className="status-line" role="status" aria-live="polite">
        {query.isFetching ? (
          <>
            <span className="spinner" aria-hidden="true" /> Simulando el lance… (≈{' '}
            {fmtFixed(r?.estimated_s ?? steps.length * 3, 0)} s)
          </>
        ) : r ? (
          <span>
            {r.results.length} pasos en {fmtFixed(r.runtime_s, 1)} s.
          </span>
        ) : null}
      </div>
      {query.error && (
        <div className="alert error" role="alert">
          <span>
            <strong>
              {query.error instanceof ApiError && query.error.status
                ? `Error ${query.error.status}`
                : 'Error'}
              :
            </strong>{' '}
            {query.error.message}
          </span>
        </div>
      )}
      {rows.some((x) => !x.converged) && (
        <div className="alert warn" role="note">
          Algún paso no convergió del todo: tome esos valores con cautela.
        </div>
      )}
      {r && (
        <div className={`row-gap${query.isFetching ? ' stale' : ''}`}>
          {summary && (
            <p className="haul-summary" data-testid="haul-summary">
              {summary}
            </p>
          )}
          <div className="haul-grid">
            <HaulChart
              id="haul-dp"
              title="Separación de portones"
              unit="m"
              rows={rows}
              value={(x) => x.doorSpread}
              reference={
                engine.door_spread_m
                  ? { value: engine.door_spread_m, label: 'regla del motor' }
                  : null
              }
            />
            <HaulChart
              id="haul-pull"
              title="Tiro en el buque"
              unit="kgf"
              digits={0}
              rows={rows}
              value={(x) => x.pull ?? x.netDrag}
              reference={
                engine.demand_kgf ? { value: engine.demand_kgf, label: 'demanda del motor' } : null
              }
            />
            <HaulChart
              id="haul-ah"
              title="Abertura horizontal"
              unit="m"
              rows={rows}
              value={(x) => x.ah}
            />
            <HaulChart
              id="haul-av"
              title="Abertura vertical"
              unit="m"
              digits={2}
              rows={rows}
              value={(x) => x.av}
            />
          </div>
          <details className="table-view">
            <summary>Ver tabla del lance</summary>
            <DataTable
              caption="Lance progresivo"
              columns={[
                { key: 'catchKg', label: 'Captura [kg]' },
                { key: 'doorSpread', label: 'DP [m]' },
                { key: 'ah', label: 'AH [m]' },
                { key: 'av', label: 'AV [m]' },
                { key: 'pull', label: 'Tiro [kgf]' },
                { key: 'netDrag', label: 'Red [kgf]' },
                { key: 'catchDrag', label: 'Captura [kgf]' },
                { key: 'friction', label: 'Roce [kgf]' },
                { key: 'catchLength', label: 'Largo captura [m]' },
                { key: 'codendDiameter', label: 'Ø copo [m]' },
              ]}
              rows={rows.map((x) => ({ ...x, converged: x.converged ? 'sí' : 'no' }))}
            />
          </details>
          {isSimGeometry(geometry) && (
            <section className="sim-3d" aria-label="Forma 3D del lance">
              <div className="net3d-head">
                <h3 className="group-title">Forma 3D</h3>
                <div className="segmented" role="group" aria-label="Paso del lance en 3D">
                  {rows.map((x, i) => (
                    <button
                      key={i}
                      type="button"
                      aria-pressed={i === geoIdx}
                      onClick={() => setStep3d(i)}
                    >
                      {fmt(x.catchKg)} kg
                    </button>
                  ))}
                </div>
              </div>
              <Suspense fallback={<p className="empty">Cargando el visor 3D…</p>}>
                <Net3D geometry={geometry} />
              </Suspense>
            </section>
          )}
          <p className="help">
            Modelo de la captura: O'Neill y O'Donoghue (1997); tendencias de referencia: Priour y de
            la Prada (2015). Los rozamientos por tipo de fondo son estimaciones con rango (A
            VERIFICAR). Ver el capítulo 22 del libro.
          </p>
        </div>
      )}
      {!r && !query.isFetching && !query.error && (
        <p className="empty">
          Elija la captura final, el fondo y pulse «Simular lance». Cada paso tarda unos segundos.
        </p>
      )}
    </div>
  );
}
