import { useQuery } from '@tanstack/react-query';
import { lazy, Suspense, useCallback, useId, useMemo, useRef, useState } from 'react';
import { api, ApiError, type ExploreRequest, type ExploreResponse } from '../../api/client';
import { downloadBlob } from '../../lib/download';
import { canRecord, recordTimeline } from '../../lib/record';
import {
  asFrames,
  asGeometry,
  DEFAULT_EXPLORE,
  EXPLORE_FORM_KEY,
  exploreRequest,
  INDICATORS,
  series,
  unitOf,
  valueAt,
  valuesFor,
  variableDef,
  VARIABLES,
  type ExploreForm,
  type Indicator,
} from '../../lib/explore';
import { fmtFixed } from '../../lib/format';
import { useT } from '../../i18n';
import { recall, remember } from '../../lib/memo';
import {
  fromInput,
  inputStep,
  inputValue,
  resolutionLabel,
  SIM_SPEEDS,
  simUnit,
  simValueOpt,
  speedLabel,
} from '../../lib/simulate';
import { fmtU, toDisplay, unitLabel } from '../../lib/units';
import { useCase } from '../../state/useCase';
import type { AnimColor, AnimScope, NetAnimHandle } from '../sim3d/NetAnim';
import { StateChart } from './StateChart';
import { Timeline } from './Timeline';

const NetAnim = lazy(() => import('../sim3d/NetAnim').then((m) => ({ default: m.NetAnim })));
const REQ_KEY = 'explore:request';

const CHARTS = ['dp', 'pull', 'av', 'fuel', 'opening', 'l50'] as const;

/** Las tallas (L50, SR) quedan en la unidad de la especie; el resto, en el sistema activo. */
const isLength = (ind: Indicator) => ind.unit === 'talla';
const indUnit = (r: ExploreResponse, ind: Indicator) =>
  isLength(ind) ? unitOf(r, ind) : simUnit(ind.unit);
const indValue = (ind: Indicator, v: number | null) =>
  isLength(ind) ? v : simValueOpt(v, ind.unit);

/** Explorador: estados de red, portones y cables al recorrer una variable, animados. */
export function Explore() {
  const { committed, state } = useCase();
  const ids = useId();
  const M = useT();
  const T = M.explore;
  const S = M.simulate;
  const [form, setFormState] = useState<ExploreForm>(
    () =>
      recall<ExploreForm>(EXPLORE_FORM_KEY) ?? {
        ...DEFAULT_EXPLORE,
        speed: state.targetSpeed,
        to: state.expectedCatchKg || DEFAULT_EXPLORE.to,
        seabed: state.params.seabed || DEFAULT_EXPLORE.seabed,
      },
  );
  const setForm = (patch: Partial<ExploreForm>) =>
    setFormState((f) => {
      const next = { ...f, ...patch };
      remember(EXPLORE_FORM_KEY, next);
      return next;
    });
  const def = variableDef(form.variable);
  const [submitted, setSubmitted] = useState<string | null>(() => recall<string>(REQ_KEY) ?? null);
  const [tRaw, setT] = useState(0);
  const [color, setColor] = useState<AnimColor>('tension');
  const [scope, setScope] = useState<AnimScope>('net');
  const [recording, setRecording] = useState(false);
  const anim = useRef<NetAnimHandle>(null);
  const seabeds = useQuery({
    queryKey: ['seabeds'],
    queryFn: ({ signal }) => api.seabeds(signal),
    staleTime: Infinity,
  });
  const speciesQ = useQuery({
    queryKey: ['species'],
    queryFn: ({ signal }) => api.species(signal),
    staleTime: Infinity,
  });
  const foulings = useQuery({
    queryKey: ['fouling'],
    queryFn: ({ signal }) => api.fouling(signal),
    staleTime: Infinity,
  });
  const query = useQuery({
    queryKey: ['explore', submitted],
    queryFn: ({ signal }) => api.explore(JSON.parse(submitted as string) as ExploreRequest, signal),
    enabled: submitted !== null,
    staleTime: Infinity,
    gcTime: 30 * 60_000,
    retry: false,
  });
  const run = () => {
    if (!committed) return;
    const key = JSON.stringify(exploreRequest(committed, form));
    remember(REQ_KEY, key);
    setT(0);
    if (key === submitted) void query.refetch();
    else setSubmitted(key);
  };

  const r = query.data;
  const geometry = r ? asGeometry(r) : null;
  const frames = useMemo(() => (r ? asFrames(r) : []), [r]);
  const t = Math.min(tRaw, Math.max(0, frames.length - 1));
  const values = r?.values ?? [];
  const rDef = r ? variableDef(r.variable as ExploreForm['variable']) : def;
  const current = valueAt(values, t);
  const fmtVar = useCallback(
    (v: number | null) => fmtU(v, rDef.unit, { digits: rDef.digits }),
    [rDef],
  );
  // Valor ya convertido al sistema activo (ejes de los gráficos).
  const fmtShownVar = (x: number) => `${fmtFixed(x, rDef.digits)} ${unitLabel(rDef.unit)}`;
  const steps = valuesFor(def, form.from, form.to, form.steps);
  const engine = (r?.engine ?? {}) as Record<string, number>;

  const savePng = () => {
    const c = anim.current?.canvas();
    if (!c) return;
    anim.current?.render();
    c.toBlob(
      (b) => b && downloadBlob(b, `${T.fileStem}-${r?.variable}-${fmtFixed(current, 1)}.png`),
    );
  };
  const recordVideo = async () => {
    const c = anim.current?.canvas() ?? null;
    if (!canRecord(c)) return;
    setRecording(true);
    try {
      const blob = await recordTimeline(c, Math.max(1, frames.length - 1), setT);
      downloadBlob(blob, `${T.fileStem}-${r?.variable}.webm`);
    } finally {
      setRecording(false);
    }
  };

  return (
    <div className="explore">
      <p className="section-sub">{T.intro}</p>
      <div className="opt-form explore-form" role="group" aria-label={T.formLabel}>
        <div className="field explore-var">
          <label htmlFor={`${ids}-var`}>{T.variable}</label>
          <select
            id={`${ids}-var`}
            value={form.variable}
            onChange={(e) => {
              const v = variableDef(e.target.value as ExploreForm['variable']);
              setForm({ variable: v.id, from: v.from, to: v.to });
            }}
          >
            {VARIABLES.map((v) => (
              <option key={v.id} value={v.id}>
                {v.label} [{unitLabel(v.unit)}]
              </option>
            ))}
          </select>
        </div>
        {(['from', 'to'] as const).map((k) => (
          <div className="field" key={k}>
            <label htmlFor={`${ids}-${k}`}>
              {k === 'from' ? T.from : T.to} [{unitLabel(def.unit)}]
            </label>
            <input
              id={`${ids}-${k}`}
              type="number"
              min={inputValue(def.min, def.unit)}
              max={inputValue(def.max, def.unit)}
              step={inputStep(def.step, def.unit)}
              value={inputValue(form[k], def.unit)}
              onChange={(e) => setForm({ [k]: fromInput(Number(e.target.value), def.unit) })}
            />
          </div>
        ))}
        <div className="field">
          <label htmlFor={`${ids}-steps`}>{T.states}</label>
          <select
            id={`${ids}-steps`}
            value={form.steps}
            onChange={(e) => setForm({ steps: Number(e.target.value) })}
          >
            {[3, 4, 5, 6, 8].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
          <span className="help">
            {steps.map((v) => fmtU(v, def.unit, { unit: false })).join(' · ')}
          </span>
        </div>
        <fieldset className="field explore-base">
          <legend className="label">{T.base}</legend>
          <div className="explore-base-grid">
            {form.variable !== 'speed_kn' && (
              <label>
                {S.speed} [kn]
                <select
                  value={form.speed}
                  onChange={(e) => setForm({ speed: Number(e.target.value) })}
                >
                  {SIM_SPEEDS.map((v) => (
                    <option key={v} value={v}>
                      {speedLabel(v)}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {form.variable !== 'catch_kg' && (
              <label>
                {T.catch} [{unitLabel('kg')}]
                <input
                  type="number"
                  min={0}
                  max={inputValue(20000, 'kg', 0)}
                  step={inputStep(50, 'kg')}
                  value={inputValue(form.catchKg, 'kg')}
                  onChange={(e) =>
                    setForm({ catchKg: Math.max(0, fromInput(Number(e.target.value) || 0, 'kg')) })
                  }
                />
              </label>
            )}
            {form.variable !== 'mu_gear' && (
              <label>
                {S.seabed}
                <select
                  value={form.seabed ?? ''}
                  onChange={(e) => setForm({ seabed: e.target.value || null })}
                >
                  {(seabeds.data ?? []).map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label>
              {T.fouling}
              <select
                value={form.fouling ?? ''}
                onChange={(e) => setForm({ fouling: e.target.value || null })}
              >
                <option value="">{T.clean}</option>
                {(foulings.data ?? [])
                  .filter((f) => f.id !== 'clean')
                  .map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.name}
                    </option>
                  ))}
              </select>
            </label>
            {form.variable !== 'current_kn' && (
              <label>
                {T.current}
                <input
                  type="number"
                  min={-2}
                  max={2}
                  step={0.1}
                  value={form.currentKn}
                  onChange={(e) => setForm({ currentKn: Number(e.target.value) || 0 })}
                />
              </label>
            )}
            {form.variable !== 'warp_length_m' && (
              <label>
                {T.warp} [{unitLabel('m')}]
                <input
                  type="number"
                  min={inputValue(20, 'm', 0)}
                  max={inputValue(3000, 'm', 0)}
                  step={inputStep(10, 'm')}
                  placeholder={T.fromEngine}
                  value={form.warpLength === null ? '' : inputValue(form.warpLength, 'm')}
                  onChange={(e) =>
                    setForm({
                      warpLength: e.target.value ? fromInput(Number(e.target.value), 'm') : null,
                    })
                  }
                />
              </label>
            )}
            <label>
              {T.selectivityOf}
              <select
                value={form.species ?? ''}
                onChange={(e) => setForm({ species: e.target.value || null })}
              >
                <option value="">{S.noSelectivity}</option>
                {(speciesQ.data ?? []).map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {S.resolution}
              <select
                value={form.resolution}
                onChange={(e) => setForm({ resolution: Number(e.target.value) })}
              >
                {[2, 3, 4].map((n) => (
                  <option key={n} value={n}>
                    {resolutionLabel(n)}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </fieldset>
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
            <span className="spinner" aria-hidden="true" /> {T.running(steps.length)}
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
      {r && geometry && frames.length > 1 && (
        <div className={`row-gap${query.isFetching ? ' stale' : ''}`}>
          <Timeline
            n={frames.length}
            t={t}
            onChange={setT}
            valueLabel={fmtVar(current)}
            variableLabel={rDef.label}
          />
          <Dashboard r={r} t={t} />
          <div className="explore-tools">
            <div className="segmented" role="group" aria-label={T.scopeLabel}>
              {(['net', 'full'] as AnimScope[]).map((v) => (
                <button
                  key={v}
                  type="button"
                  aria-pressed={scope === v}
                  onClick={() => setScope(v)}
                >
                  {T.scopes[v]}
                </button>
              ))}
            </div>
            <div className="segmented" role="group" aria-label={T.colorLabel}>
              {(['tension', 'contact', 'fouling', 'opening'] as const).map((v) => (
                <button
                  key={v}
                  type="button"
                  aria-pressed={color === v}
                  onClick={() => setColor(v)}
                >
                  {T.colors[v]}
                </button>
              ))}
            </div>
            <button type="button" className="btn small" onClick={savePng}>
              {T.png}
            </button>
            <button
              type="button"
              className="btn small"
              onClick={() => void recordVideo()}
              disabled={recording}
            >
              {recording ? T.recording : T.record}
            </button>
          </div>
          <Suspense fallback={<p className="empty">{S.loading3d}</p>}>
            <NetAnim
              ref={anim}
              geometry={geometry}
              frames={frames}
              t={t}
              color={color}
              scope={scope}
              label={T.animLabel(rDef.label.toLowerCase(), fmtVar(current))}
            />
          </Suspense>
          <div className="haul-grid">
            {CHARTS.map((key) => {
              const ind = INDICATORS.find((i) => i.key === key);
              if (!ind) return null;
              const ys = series(r, ind);
              if (ys.every((y) => y === null)) return null;
              return (
                <StateChart
                  key={key}
                  id={`explore-${key}`}
                  title={ind.label}
                  unit={indUnit(r, ind)}
                  digits={ind.digits}
                  xs={values.map((x) => toDisplay(x, rDef.unit))}
                  ys={ys.map((y) => indValue(ind, y))}
                  xLabel={fmtShownVar}
                  cursor={current === null ? null : toDisplay(current, rDef.unit)}
                  reference={
                    key === 'dp' && engine.door_spread_m
                      ? { value: toDisplay(engine.door_spread_m, 'm'), label: S.engineRule }
                      : key === 'pull' && engine.demand_kgf && r.variable !== 'speed_kn'
                        ? { value: toDisplay(engine.demand_kgf, 'kgf'), label: S.engineDemand }
                        : null
                  }
                />
              );
            })}
          </div>
          <p className="help">{T.help}</p>
        </div>
      )}
      {!r && !query.isFetching && !query.error && (
        <p className="empty">{T.empty}</p>
      )}
    </div>
  );
}

function Dashboard({ r, t }: { r: ExploreResponse; t: number }) {
  const T = useT().explore;
  return (
    <section className="explore-dash" aria-label={T.dashLabel} data-testid="explore-dashboard">
      {INDICATORS.map((ind) => {
        const ys = series(r, ind).map((y) => indValue(ind, y));
        const now = valueAt(ys, t);
        if (now === null) return null;
        const base = ys[0] ?? null;
        const delta = base === null ? null : now - base;
        const eps = 10 ** -ind.digits / 2;
        const tone =
          delta === null || Math.abs(delta) < eps || !ind.better
            ? 'neutral'
            : (ind.better === 'higher') === delta > 0
              ? 'good'
              : 'bad';
        return (
          <div className={`impact-item ${tone}`} key={ind.key} data-indicator={ind.key}>
            <span className="impact-label">{ind.label}</span>
            <span className="impact-value">
              {fmtFixed(now, ind.digits)} <span className="unit">{indUnit(r, ind)}</span>
            </span>
            <span className="impact-delta">
              {delta === null || Math.abs(delta) < eps
                ? T.same
                : T.vsFirst(`${delta > 0 ? '+' : ''}${fmtFixed(delta, ind.digits)}`)}
            </span>
          </div>
        );
      })}
    </section>
  );
}
