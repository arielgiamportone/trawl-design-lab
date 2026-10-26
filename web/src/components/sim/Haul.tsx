import { useQuery } from '@tanstack/react-query';
import { lazy, Suspense, useId, useState } from 'react';
import { api, ApiError, type HaulRequest } from '../../api/client';
import { fmtFixed } from '../../lib/format';
import { useT } from '../../i18n';
import { fmtU, toDisplayOpt, unitLabel } from '../../lib/units';
import {
  CATCH_TYPES,
  DEFAULT_HAUL,
  catchSteps,
  haulRequest,
  haulRows,
  haulSummary,
  type HaulForm,
} from '../../lib/haul';
import { catchPreset, EXPLORE_FORM_KEY } from '../../lib/explore';
import { recall, remember } from '../../lib/memo';
import { isSimGeometry } from '../../lib/sim3d';
import {
  fromInput,
  inputStep,
  inputValue,
  resolutionLabel,
  SIM_SPEEDS,
  speedLabel,
} from '../../lib/simulate';
import { useCase } from '../../state/useCase';
import { DataTable } from '../charts/ChartParts';
import { HelpTip } from '../HelpTip';
import { HaulChart } from './HaulChart';

const Net3D = lazy(() => import('../sim3d/Net3D').then((m) => ({ default: m.Net3D })));
const FORM_KEY = 'haul:form';

/** Columnas de la tabla del lance con su unidad del motor. */
const HAUL_COLUMNS = [
  ['catchKg', 'kg'],
  ['doorSpread', 'm'],
  ['ah', 'm'],
  ['av', 'm'],
  ['pull', 'kgf'],
  ['netDrag', 'kgf'],
  ['catchDrag', 'kgf'],
  ['friction', 'kgf'],
  ['catchLength', 'm'],
  ['codendDiameter', 'm'],
] as const;
const REQ_KEY = 'haul:request';

/** Lance progresivo: la red con captura creciente, fondo elegido y portones acoplados. */
export function Haul({ onAnimate }: { onAnimate?: () => void }) {
  const { committed, state } = useCase();
  const ids = useId();
  const M = useT();
  const T = M.haul;
  const S = M.simulate;
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
      <p className="section-sub">{T.intro}</p>
      <div className="opt-form haul-form" role="group" aria-label={T.formLabel}>
        <div className="field">
          <label htmlFor={`${ids}-speed`}>{S.speed} [kn]</label>
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
            {T.finalCatch} [{unitLabel('kg')}]{' '}
            <HelpTip topic="catch_kg" label={T.finalCatch} />
          </label>
          <input
            id={`${ids}-catch`}
            type="number"
            min={0}
            max={inputValue(20000, 'kg', 0)}
            step={inputStep(50, 'kg')}
            value={inputValue(form.maxCatchKg, 'kg')}
            onChange={(e) =>
              setForm({ maxCatchKg: Math.max(0, fromInput(Number(e.target.value) || 0, 'kg')) })
            }
          />
          <span className="help">
            {T.steps(
              `${steps.map((v) => fmtU(v, 'kg', { digits: 0, unit: false })).join(' · ')} ${unitLabel('kg')}`,
            )}
          </span>
        </div>
        <div className="field">
          <label htmlFor={`${ids}-type`}>{T.catchType}</label>
          <select
            id={`${ids}-type`}
            value={form.catchType}
            onChange={(e) => setForm({ catchType: e.target.value as HaulForm['catchType'] })}
          >
            {CATCH_TYPES.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label} ({fmtU(c.bulk, 'kg/m³', { digits: 1 })})
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor={`${ids}-seabed`}>
            {S.seabed} <HelpTip topic="seabed" label={T.seabedType} />
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
              {T.mu(fmtFixed(Number(sb.mu_gear.nominal), 2), fmtFixed(Number(sb.mu_door.nominal), 2))}
            </span>
          )}
        </div>
        <div className="field">
          <span className="label">{S.resolution}</span>
          <div className="segmented">
            {[3, 4].map((res) => (
              <label key={res}>
                <input
                  type="radio"
                  name={`${ids}-res`}
                  checked={form.resolution === res}
                  onChange={() => setForm({ resolution: res })}
                />
                {resolutionLabel(res)}
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
          {T.coupled}
        </label>
      </div>
      <div className="calc-row">
        <button
          type="button"
          className="btn primary"
          onClick={run}
          disabled={!committed || query.isFetching}
        >
          {T.run}
        </button>
      </div>
      <div className="status-line" role="status" aria-live="polite">
        {query.isFetching ? (
          <>
            <span className="spinner" aria-hidden="true" />{' '}
            {T.running(fmtFixed(r?.estimated_s ?? steps.length * 3, 0))}
          </>
        ) : r ? (
          <span>{T.done(r.results.length, fmtFixed(r.runtime_s, 1))}</span>
        ) : null}
      </div>
      {query.error && (
        <div className="alert error" role="alert">
          <span>
            <strong>
              {query.error instanceof ApiError && query.error.status
                ? S.errorStatus(query.error.status)
                : S.error}
              :
            </strong>{' '}
            {query.error.message}
          </span>
        </div>
      )}
      {rows.some((x) => !x.converged) && (
        <div className="alert warn" role="note">
          {T.unconverged}
        </div>
      )}
      {r && (
        <div className={`row-gap${query.isFetching ? ' stale' : ''}`}>
          {summary && (
            <p className="haul-summary" data-testid="haul-summary">
              {summary}
            </p>
          )}
          {onAnimate && (
            <button
              type="button"
              className="btn small"
              onClick={() => {
                remember(EXPLORE_FORM_KEY, {
                  ...catchPreset(form.maxCatchKg, form.seabed, form.speed),
                  resolution: form.resolution,
                });
                onAnimate();
              }}
            >
              {T.animate}
            </button>
          )}
          <div className="haul-grid">
            <HaulChart
              id="haul-dp"
              title={T.charts.dp}
              unit="m"
              rows={rows}
              value={(x) => x.doorSpread}
              reference={
                engine.door_spread_m ? { value: engine.door_spread_m, label: S.engineRule } : null
              }
            />
            <HaulChart
              id="haul-pull"
              title={T.charts.pull}
              unit="kgf"
              digits={0}
              rows={rows}
              value={(x) => x.pull ?? x.netDrag}
              reference={
                engine.demand_kgf ? { value: engine.demand_kgf, label: S.engineDemand } : null
              }
            />
            <HaulChart
              id="haul-ah"
              title={T.charts.ah}
              unit="m"
              rows={rows}
              value={(x) => x.ah}
            />
            <HaulChart
              id="haul-av"
              title={T.charts.av}
              unit="m"
              digits={2}
              rows={rows}
              value={(x) => x.av}
            />
          </div>
          <details className="table-view">
            <summary>{T.showTable}</summary>
            <DataTable
              caption={T.tableCaption}
              columns={HAUL_COLUMNS.map(([key, unit]) => ({
                key,
                label: `${T.cols[key]} [${unitLabel(unit)}]`,
              }))}
              rows={rows.map((x) => ({
                ...Object.fromEntries(
                  HAUL_COLUMNS.map(([key, unit]) => [key, toDisplayOpt(x[key], unit)]),
                ),
                converged: x.converged ? S.yes : S.no,
              }))}
            />
          </details>
          {isSimGeometry(geometry) && (
            <section className="sim-3d" aria-label={T.shape3dRegion}>
              <div className="net3d-head">
                <h3 className="group-title">{T.shape3d}</h3>
                <div className="segmented" role="group" aria-label={T.step3d}>
                  {rows.map((x, i) => (
                    <button
                      key={i}
                      type="button"
                      aria-pressed={i === geoIdx}
                      onClick={() => setStep3d(i)}
                    >
                      {fmtU(x.catchKg, 'kg', { digits: 0 })}
                    </button>
                  ))}
                </div>
              </div>
              <Suspense fallback={<p className="empty">{S.loading3d}</p>}>
                <Net3D geometry={geometry} />
              </Suspense>
            </section>
          )}
          <p className="help">{T.refs}</p>
        </div>
      )}
      {!r && !query.isFetching && !query.error && (
        <p className="empty">{T.empty}</p>
      )}
    </div>
  );
}
