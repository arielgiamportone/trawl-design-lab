import { useQuery, useQueryClient } from '@tanstack/react-query';
import { lazy, Suspense, useEffect, useId, useState } from 'react';
import { api, ApiError, type SimulateRequest, type SimulateResponse } from '../api/client';
import { fmt, fmtFixed, fmtNum, fmtPct } from '../lib/format';
import { useT } from '../i18n';
import { toDisplayOpt, unitLabel } from '../lib/units';
import { recall, remember } from '../lib/memo';
import { Explore } from './sim/Explore';
import { Selectivity } from './sim/Selectivity';
import { Uncertainty } from './sim/Uncertainty';
import { Haul } from './sim/Haul';
import { isSimGeometry } from '../lib/sim3d';
import {
  compareRows,
  MAX_SIM_SPEEDS,
  rigParams,
  SIM_RESOLUTION,
  SIM_SECONDS_PER_SPEED,
  SIM_SPEEDS,
  SIM_VIEW_KEY,
  simQualityLabel,
  speedLabel,
  toggleSpeed,
  unconverged,
  type SimQuality,
  type SimView,
} from '../lib/simulate';
import { useCase } from '../state/useCase';
import { ZoomStage } from './ZoomStage';

// three.js (≈ 600 kB) sólo se descarga al pedir la vista 3D.
const Net3D = lazy(() => import('./sim3d/Net3D').then((m) => ({ default: m.Net3D })));

// Último pedido y selección: sobreviven al cambio de pestaña, no a la recarga de la página.
const REQ_KEY = 'simulate:request';
const SEL_KEY = 'simulate:selection';
type Sel = { speeds: number[]; quality: SimQuality; view3d?: boolean };

const VIEWS = ['plan', 'profile', 'front'] as const;

function Elapsed({ since }: { since: number }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), 500);
    return () => window.clearInterval(t);
  }, []);
  return <>{fmtFixed(Math.max(0, (now - since) / 1000), 0)} s</>;
}

function pctCell(v: number | null) {
  if (v === null) return <td className="num">—</td>;
  const big = Math.abs(v) >= 20;
  return (
    <td className={`num${big ? ' pct-big' : ''}`} data-pct={Math.round(v)}>
      {fmtPct(v, 0)}
    </td>
  );
}

function CompareTable({ r }: { r: SimulateResponse }) {
  const T = useT().simulate.table;
  const { design } = useCase();
  const rows = compareRows(r, typeof design.data?.summary.opening_method === 'string');
  const hasDyn = rows.some((x) => x.dynamit !== null);
  return (
    <div className="table-wrap">
      <table className="data" data-testid="sim-table">
        <caption className="sr-only">{T.caption(hasDyn)}</caption>
        <thead>
          <tr>
            <th scope="col">v [kn]</th>
            <th scope="col">{T.quantity}</th>
            <th scope="col" className="num">
              {T.sim}
            </th>
            <th scope="col" className="num">
              {T.engine}
            </th>
            <th scope="col" className="num">
              {T.simVsEngine}
            </th>
            {hasDyn && (
              <>
                <th scope="col" className="num">
                  DynamiT
                </th>
                <th scope="col" className="num">
                  {T.simVsDynamit}
                </th>
                <th scope="col" className="num col-abs">
                  {T.engineVsDynamit}
                </th>
              </>
            )}
          </tr>
        </thead>
        <tbody>
          {rows.map((x, i) => (
            <tr key={`${x.speed}-${x.key}`} data-row={`${x.speed}-${x.key}`}>
              <td className="num">{i % 3 === 0 ? speedLabel(x.speed) : ''}</td>
              <th scope="row">
                {x.label} [{unitLabel(x.unit)}]
                <span className="cell-note">{T.engineNote(x.engineName)}</span>
              </th>
              <td className="num">{fmt(rounded(x.sim, x.unit))}</td>
              <td className="num">{fmt(rounded(x.engine, x.unit))}</td>
              {pctCell(x.simVsEngine)}
              {hasDyn && (
                <>
                  <td className="num">{fmt(toDisplayOpt(x.dynamit, x.unit))}</td>
                  {pctCell(x.simVsDynamit)}
                  <td className="num col-abs">
                    {x.engineVsDynamit === null ? '—' : fmtPct(x.engineVsDynamit, 0)}
                  </td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Valor en el sistema de unidades activo: fuerzas al entero, longitudes a dos decimales. */
function rounded(v: number | null, unit: string): number | null {
  const d = toDisplayOpt(v, unit);
  if (d === null) return null;
  return unit === 'kgf' ? Math.round(d) : Math.round(d * 100) / 100;
}

/** Pestaña «Simulación»: barrido de velocidades o lance progresivo con escenario. */
export function Simulate() {
  const [view, setViewState] = useState<SimView>(() => recall<SimView>(SIM_VIEW_KEY) ?? 'speeds');
  const setView = (v: SimView) => {
    remember(SIM_VIEW_KEY, v);
    setViewState(v);
  };
  const T = useT().simulate;
  const views: SimView[] = ['speeds', 'haul', 'explore', 'selectivity', 'uncertainty'];
  return (
    <div>
      <div className="panel-toolbar">
        <h2 className="section-title">
          {T.title} <span className="badge warn">{T.experimental}</span>
        </h2>
        <div className="segmented" role="group" aria-label={T.viewsLabel}>
          {views.map((v) => (
            <button key={v} type="button" aria-pressed={view === v} onClick={() => setView(v)}>
              {T.views[v]}
            </button>
          ))}
        </div>
      </div>
      {view === 'speeds' ? (
        <SpeedSweep />
      ) : view === 'haul' ? (
        <Haul onAnimate={() => setView('explore')} />
      ) : view === 'explore' ? (
        <Explore />
      ) : view === 'selectivity' ? (
        <Selectivity />
      ) : (
        <Uncertainty />
      )}
    </div>
  );
}

function SpeedSweep() {
  const { state, committed, catalogs } = useCase();
  const T = useT().simulate;
  const ids = useId();
  const [speeds, setSpeedsState] = useState<number[]>(() => recall<Sel>(SEL_KEY)?.speeds ?? [3]);
  const [quality, setQualityState] = useState<SimQuality>(
    () => recall<Sel>(SEL_KEY)?.quality ?? 'fast',
  );
  const [view3d, setView3dState] = useState<boolean>(() => recall<Sel>(SEL_KEY)?.view3d ?? true);
  const [speed3d, setSpeed3d] = useState(0);
  const setSel = (s: number[], q: SimQuality, v3 = view3d) => {
    remember<Sel>(SEL_KEY, { speeds: s, quality: q, view3d: v3 });
    setSpeedsState(s);
    setQualityState(q);
    setView3dState(v3);
  };
  const [submitted, setSubmitted] = useState<string | null>(() => recall<string>(REQ_KEY) ?? null);
  const [startedAt, setStartedAt] = useState<number>(() => Date.now());

  const query = useQuery({
    queryKey: ['simulate', submitted],
    queryFn: ({ signal }) =>
      api.simulate(JSON.parse(submitted as string) as SimulateRequest, signal),
    enabled: submitted !== null,
    staleTime: Infinity,
    gcTime: 30 * 60_000,
    retry: false,
  });
  const r = query.data;
  const busy = query.isFetching;
  const err = query.error;
  const qc = useQueryClient();
  // Corta la simulación: en el servidor se abandona el pedido; en el teléfono se detiene el motor.
  const cancel = () => {
    void qc.cancelQueries({ queryKey: ['simulate', submitted] });
    setSubmitted(null);
  };

  const run = () => {
    if (!speeds.length || !committed) return;
    const req: SimulateRequest = {
      net: committed.net,
      vessel: committed.vessel ?? null,
      door: committed.door ?? null,
      class_vessels: null,
      compat: committed.compat,
      speeds_kn: speeds,
      resolution: SIM_RESOLUTION[quality],
      cn: null,
      ct: null,
      knot_factor: null,
      door_spread_m: null,
      include_geometry: view3d,
    };
    const rp = rigParams(committed.params);
    if (rp) req.params = rp;
    const key = JSON.stringify(req);
    remember(REQ_KEY, key);
    setStartedAt(Date.now());
    if (key === submitted) void query.refetch();
    else setSubmitted(key);
  };

  const estimate = Math.max(1, Math.round(SIM_SECONDS_PER_SPEED[quality] * speeds.length));
  const bad = r ? unconverged(r) : [];
  const netLabel = state.scaled
    ? T.scaledNet(fmtFixed(state.scaled.s, 3))
    : (catalogs.nets.find((n) => n.id === state.net)?.name ?? state.net);

  return (
    <div>
      <p className="section-sub" style={{ marginBottom: 12 }}>
        {T.intro(netLabel)}
      </p>
      <div className="opt-form" role="group" aria-label={T.formLabel}>
        <fieldset className="field sim-speeds">
          <legend className="label">{T.speedsLegend(MAX_SIM_SPEEDS, speeds.length)}</legend>
          <div className="chip-group">
            {SIM_SPEEDS.map((v) => {
              const on = speeds.includes(v);
              const full = !on && speeds.length >= MAX_SIM_SPEEDS;
              return (
                <button
                  key={v}
                  type="button"
                  className="chip"
                  aria-pressed={on}
                  disabled={full}
                  onClick={() => setSel(toggleSpeed(speeds, v), quality)}
                >
                  {speedLabel(v)}
                </button>
              );
            })}
          </div>
        </fieldset>
        <fieldset className="field sim-quality">
          <legend className="label">{T.resolution}</legend>
          <div className="segmented">
            {(['fast', 'normal'] as const).map((q) => (
              <label key={q}>
                <input
                  type="radio"
                  name={`${ids}-quality`}
                  value={q}
                  checked={quality === q}
                  onChange={() => setSel(speeds, q)}
                />
                {simQualityLabel(q)} ({SIM_RESOLUTION[q]})
              </label>
            ))}
          </div>
          <span className="help">{T.estimate(estimate)}</span>
        </fieldset>
        <label className="check small">
          <input
            type="checkbox"
            checked={view3d}
            onChange={(e) => setSel(speeds, quality, e.target.checked)}
          />
          {T.view3d}
        </label>
      </div>
      <div className="calc-row">
        <button
          type="button"
          className="btn primary"
          onClick={run}
          disabled={!speeds.length || busy || !committed}
        >
          {T.run}
        </button>
        {busy && (
          <button type="button" className="btn ghost" onClick={cancel}>
            {T.cancel}
          </button>
        )}
      </div>
      <div className="status-line" role="status" aria-live="polite">
        {busy ? (
          <>
            <span className="spinner" aria-hidden="true" /> {T.running}{' '}
            <Elapsed since={startedAt} /> {T.runningOf(estimate)}
          </>
        ) : r ? (
          <span>
            {T.done(r.results.length, fmtFixed(r.runtime_s, 1), String(r.settings.resolution))}
          </span>
        ) : null}
      </div>
      {err && (
        <div className="alert error" role="alert">
          <span>
            <strong>
              {err instanceof ApiError && err.status ? T.errorStatus(err.status) : T.error}:
            </strong>{' '}
            {err.message}
          </span>
        </div>
      )}
      {bad.length > 0 && (
        <div className="alert warn" role="note">
          {T.unconverged(bad.map((v) => fmtFixed(v, 1)).join(', '))}
        </div>
      )}

      {r && (
        <div className={`row-gap${busy ? ' stale' : ''}`} style={{ marginTop: 16 }}>
          {r.results.some(isSimGeometry) && (
            <section className="sim-3d" aria-label={T.view3dRegion}>
              <div className="net3d-head">
                <h3 className="group-title">{T.view3d}</h3>
                {r.results.length > 1 && (
                  <div className="segmented" role="group" aria-label={T.speed3d}>
                    {r.results.map((x, i) => (
                      <button
                        key={i}
                        type="button"
                        aria-pressed={i === Math.min(speed3d, r.results.length - 1)}
                        onClick={() => setSpeed3d(i)}
                      >
                        {speedLabel(Number(x.speed_kn))} kn
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <Suspense fallback={<p className="empty">{T.loading3d}</p>}>
                {(() => {
                  const g = r.results[Math.min(speed3d, r.results.length - 1)];
                  return isSimGeometry(g) ? <Net3D geometry={g} /> : null;
                })()}
              </Suspense>
            </section>
          )}
          {Object.entries(r.projections_svg).map(([k, p]) => {
            const kv = fmtNum(Number(k));
            return (
              <section key={k} className="sim-speed" aria-label={T.projAria(kv)}>
                <h3 className="group-title">{T.at(speedLabel(Number(k)))}</h3>
                <div className="sim-views" data-speed={k}>
                  {VIEWS.map((view) => (
                    <figure key={view} className="sim-view" style={{ margin: 0 }}>
                      <figcaption>{T.projections[view]}</figcaption>
                      <ZoomStage
                        key={`${submitted}-${k}-${view}`}
                        svg={p[view]}
                        alt={T.projAlt(T.projections[view], kv)}
                        label={T.projLabel(T.projections[view], kv)}
                        className="compact"
                        testId="sim-svg"
                      />
                    </figure>
                  ))}
                </div>
              </section>
            );
          })}
          {Object.keys(r.projections_svg).length < r.results.length && (
            <p className="help">{T.firstThree}</p>
          )}
          <section aria-labelledby={`${ids}-cmp`}>
            <h3 className="group-title" id={`${ids}-cmp`}>
              {T.compareTitle(!!r.dynamit_comparison?.length)}
            </h3>
            <CompareTable r={r} />
            <div className="alert info sim-note" role="note">
              <span>
                <strong>{T.dragNote.title}</strong> {T.dragNote.a}
                <sub>N</sub>
                {T.dragNote.b(fmt(Number(r.settings.cn)))}
                <sub>T</sub>
                {T.dragNote.c(fmt(Number(r.settings.ct)))}
                <sub>N</sub>
                {T.dragNote.d}
                <sub>T</sub>
                {T.dragNote.e}
              </span>
            </div>
          </section>
        </div>
      )}
      {!r && !busy && !err && <p className="empty">{T.empty}</p>}
    </div>
  );
}
