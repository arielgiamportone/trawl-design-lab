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
} from '../../lib/explore';
import { fmt, fmtFixed } from '../../lib/format';
import { recall, remember } from '../../lib/memo';
import { SIM_SPEEDS, speedLabel } from '../../lib/simulate';
import { useCase } from '../../state/useCase';
import type { AnimColor, AnimScope, NetAnimHandle } from '../sim3d/NetAnim';
import { StateChart } from './StateChart';
import { Timeline } from './Timeline';

const NetAnim = lazy(() => import('../sim3d/NetAnim').then((m) => ({ default: m.NetAnim })));
const REQ_KEY = 'explore:request';

const CHARTS = ['dp', 'pull', 'av', 'fuel', 'opening', 'l50'] as const;

/** Explorador: estados de red, portones y cables al recorrer una variable, animados. */
export function Explore() {
  const { committed, state } = useCase();
  const ids = useId();
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
    (v: number | null) => (v === null ? '—' : `${fmtFixed(v, rDef.digits)} ${rDef.unit}`),
    [rDef],
  );
  const steps = valuesFor(def, form.from, form.to, form.steps);
  const engine = (r?.engine ?? {}) as Record<string, number>;

  const savePng = () => {
    const c = anim.current?.canvas();
    if (!c) return;
    anim.current?.render();
    c.toBlob((b) => b && downloadBlob(b, `aparejo-${r?.variable}-${fmtFixed(current, 1)}.png`));
  };
  const recordVideo = async () => {
    const c = anim.current?.canvas() ?? null;
    if (!canRecord(c)) return;
    setRecording(true);
    try {
      const blob = await recordTimeline(c, Math.max(1, frames.length - 1), setT);
      downloadBlob(blob, `aparejo-${r?.variable}.webm`);
    } finally {
      setRecording(false);
    }
  };

  return (
    <div className="explore">
      <p className="section-sub">
        Elija una variable y su rango: se calculan los estados de equilibrio de la red, los portones
        y los cables, y la animación pasa de uno a otro (interpolando entre estados calculados). El
        tablero sigue al estado que se ve.
      </p>
      <div className="opt-form explore-form" role="group" aria-label="Variable y escenario">
        <div className="field explore-var">
          <label htmlFor={`${ids}-var`}>Variable a recorrer</label>
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
                {v.label} [{v.unit}]
              </option>
            ))}
          </select>
        </div>
        {(['from', 'to'] as const).map((k) => (
          <div className="field" key={k}>
            <label htmlFor={`${ids}-${k}`}>
              {k === 'from' ? 'Desde' : 'Hasta'} [{def.unit}]
            </label>
            <input
              id={`${ids}-${k}`}
              type="number"
              min={def.min}
              max={def.max}
              step={def.step}
              value={form[k]}
              onChange={(e) => setForm({ [k]: Number(e.target.value) })}
            />
          </div>
        ))}
        <div className="field">
          <label htmlFor={`${ids}-steps`}>Estados</label>
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
          <span className="help">{steps.map((v) => fmt(v)).join(' · ')}</span>
        </div>
        <fieldset className="field explore-base">
          <legend className="label">Escenario base</legend>
          <div className="explore-base-grid">
            {form.variable !== 'speed_kn' && (
              <label>
                Velocidad [kn]
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
                Captura [kg]
                <input
                  type="number"
                  min={0}
                  max={20000}
                  step={50}
                  value={form.catchKg}
                  onChange={(e) => setForm({ catchKg: Math.max(0, Number(e.target.value) || 0) })}
                />
              </label>
            )}
            {form.variable !== 'mu_gear' && (
              <label>
                Fondo
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
              Ensuciamiento
              <select
                value={form.fouling ?? ''}
                onChange={(e) => setForm({ fouling: e.target.value || null })}
              >
                <option value="">Red limpia</option>
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
                Corriente [kn, + a favor]
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
                Cable filado [m]
                <input
                  type="number"
                  min={20}
                  max={3000}
                  step={10}
                  placeholder="del motor"
                  value={form.warpLength ?? ''}
                  onChange={(e) =>
                    setForm({ warpLength: e.target.value ? Number(e.target.value) : null })
                  }
                />
              </label>
            )}
            <label>
              Selectividad de
              <select
                value={form.species ?? ''}
                onChange={(e) => setForm({ species: e.target.value || null })}
              >
                <option value="">(sin selectividad)</option>
                {(speciesQ.data ?? []).map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Resolución
              <select
                value={form.resolution}
                onChange={(e) => setForm({ resolution: Number(e.target.value) })}
              >
                <option value={2}>Muy rápida (2)</option>
                <option value={3}>Rápida (3)</option>
                <option value={4}>Normal (4)</option>
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
          Calcular estados
        </button>
      </div>
      <div className="status-line" role="status" aria-live="polite">
        {query.isFetching ? (
          <>
            <span className="spinner" aria-hidden="true" /> Calculando {steps.length} estados…
          </>
        ) : r ? (
          <span>
            {r.results.length} estados en {fmtFixed(r.runtime_s, 1)} s.
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
            <div className="segmented" role="group" aria-label="Encuadre">
              {(
                [
                  ['net', 'Red y portones'],
                  ['full', 'Con cables hasta el buque'],
                ] as [AnimScope, string][]
              ).map(([v, l]) => (
                <button
                  key={v}
                  type="button"
                  aria-pressed={scope === v}
                  onClick={() => setScope(v)}
                >
                  {l}
                </button>
              ))}
            </div>
            <div className="segmented" role="group" aria-label="Color del paño">
              {(
                [
                  ['tension', 'Tensión'],
                  ['contact', 'Contacto con el fondo'],
                  ['fouling', 'Ensuciamiento'],
                  ['opening', 'Apertura de malla'],
                ] as [AnimColor, string][]
              ).map(([v, l]) => (
                <button
                  key={v}
                  type="button"
                  aria-pressed={color === v}
                  onClick={() => setColor(v)}
                >
                  {l}
                </button>
              ))}
            </div>
            <button type="button" className="btn small" onClick={savePng}>
              Descargar PNG
            </button>
            <button
              type="button"
              className="btn small"
              onClick={() => void recordVideo()}
              disabled={recording}
            >
              {recording ? 'Grabando…' : 'Grabar video (WebM)'}
            </button>
          </div>
          <Suspense fallback={<p className="empty">Cargando el visor 3D…</p>}>
            <NetAnim
              ref={anim}
              geometry={geometry}
              frames={frames}
              t={t}
              color={color}
              scope={scope}
              label={`Aparejo animado según ${rDef.label.toLowerCase()} (${fmtVar(current)})`}
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
                  unit={unitOf(r, ind)}
                  digits={ind.digits}
                  xs={values}
                  ys={ys}
                  xLabel={(x) => fmtVar(x)}
                  cursor={current}
                  reference={
                    key === 'dp' && engine.door_spread_m
                      ? { value: engine.door_spread_m, label: 'regla del motor' }
                      : key === 'pull' && engine.demand_kgf && r.variable !== 'speed_kn'
                        ? { value: engine.demand_kgf, label: 'demanda del motor' }
                        : null
                  }
                />
              );
            })}
          </div>
          <p className="help">
            Energía: potencia = tiro × velocidad en el agua / 0,5; consumo 0,22 kg/kWh (A
            VERIFICAR). Huella según BENTHIS (Eigaard et al. 2016). Ensuciamiento y corriente:
            capítulo 23 del libro.
          </p>
        </div>
      )}
      {!r && !query.isFetching && !query.error && (
        <p className="empty">
          Elija la variable y pulse «Calcular estados». Con resolución rápida cada estado tarda unos
          segundos.
        </p>
      )}
    </div>
  );
}

function Dashboard({ r, t }: { r: ExploreResponse; t: number }) {
  return (
    <section className="explore-dash" aria-label="Estado actual" data-testid="explore-dashboard">
      {INDICATORS.map((ind) => {
        const ys = series(r, ind);
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
              {fmtFixed(now, ind.digits)} <span className="unit">{unitOf(r, ind)}</span>
            </span>
            <span className="impact-delta">
              {delta === null || Math.abs(delta) < eps
                ? 'igual al primer estado'
                : `${delta > 0 ? '+' : ''}${fmtFixed(delta, ind.digits)} vs primer estado`}
            </span>
          </div>
        );
      })}
    </section>
  );
}
