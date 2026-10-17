import { useQuery } from '@tanstack/react-query';
import { useEffect, useId, useState } from 'react';
import { api, ApiError, type SimulateRequest, type SimulateResponse } from '../api/client';
import { fmt, fmtFixed, fmtPct } from '../lib/format';
import { recall, remember } from '../lib/memo';
import {
  compareRows,
  MAX_SIM_SPEEDS,
  SIM_QUALITY_LABEL,
  SIM_RESOLUTION,
  SIM_SECONDS_PER_SPEED,
  SIM_SPEEDS,
  speedLabel,
  toggleSpeed,
  unconverged,
  type SimQuality,
} from '../lib/simulate';
import { useCase } from '../state/useCase';
import { ZoomStage } from './ZoomStage';

// Último pedido y selección: sobreviven al cambio de pestaña, no a la recarga de la página.
const REQ_KEY = 'simulate:request';
const SEL_KEY = 'simulate:selection';
type Sel = { speeds: number[]; quality: SimQuality };

const VIEWS: { key: 'plan' | 'profile' | 'front'; label: string }[] = [
  { key: 'plan', label: 'Planta' },
  { key: 'profile', label: 'Perfil' },
  { key: 'front', label: 'Frente' },
];

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
  const rows = compareRows(r);
  const hasDyn = rows.some((x) => x.dynamit !== null);
  return (
    <div className="table-wrap">
      <table className="data" data-testid="sim-table">
        <caption className="sr-only">
          Simulación frente al motor empírico{hasDyn ? ' y a DynamiT' : ''}
        </caption>
        <thead>
          <tr>
            <th scope="col">v [kn]</th>
            <th scope="col">Magnitud</th>
            <th scope="col" className="num">
              Simulación
            </th>
            <th scope="col" className="num">
              Motor
            </th>
            <th scope="col" className="num">
              Δ sim/motor
            </th>
            {hasDyn && (
              <>
                <th scope="col" className="num">
                  DynamiT
                </th>
                <th scope="col" className="num">
                  Δ sim/DynamiT
                </th>
                <th scope="col" className="num col-abs">
                  Δ motor/DynamiT
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
                {x.label} [{x.unit}]<span className="cell-note"> motor: {x.engineName}</span>
              </th>
              <td className="num">{fmt(x.unit === 'kgf' ? roundOrNull(x.sim) : round2(x.sim))}</td>
              <td className="num">
                {fmt(x.unit === 'kgf' ? roundOrNull(x.engine) : round2(x.engine))}
              </td>
              {pctCell(x.simVsEngine)}
              {hasDyn && (
                <>
                  <td className="num">{fmt(x.dynamit)}</td>
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

const roundOrNull = (v: number | null) => (v === null ? null : Math.round(v));
const round2 = (v: number | null) => (v === null ? null : Math.round(v * 100) / 100);

export function Simulate() {
  const { state, committed, catalogs } = useCase();
  const ids = useId();
  const [speeds, setSpeedsState] = useState<number[]>(() => recall<Sel>(SEL_KEY)?.speeds ?? [3]);
  const [quality, setQualityState] = useState<SimQuality>(
    () => recall<Sel>(SEL_KEY)?.quality ?? 'fast',
  );
  const setSel = (s: number[], q: SimQuality) => {
    remember<Sel>(SEL_KEY, { speeds: s, quality: q });
    setSpeedsState(s);
    setQualityState(q);
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
      include_geometry: false,
    };
    const key = JSON.stringify(req);
    remember(REQ_KEY, key);
    setStartedAt(Date.now());
    if (key === submitted) void query.refetch();
    else setSubmitted(key);
  };

  const estimate = Math.max(1, Math.round(SIM_SECONDS_PER_SPEED[quality] * speeds.length));
  const bad = r ? unconverged(r) : [];
  const netLabel = state.scaled
    ? `red escalada s = ${fmtFixed(state.scaled.s, 3)}`
    : (catalogs.nets.find((n) => n.id === state.net)?.name ?? state.net);

  return (
    <div>
      <h2 className="section-title">
        Simulación de la forma <span className="badge warn">experimental</span>
      </h2>
      <p className="section-sub" style={{ marginBottom: 12 }}>
        Busca la forma de equilibrio de la red ({netLabel}) remolcada a cada velocidad: paño de
        hilos con arrastre de Morison, relingas, boyas, lastre, bridas, patentes y contacto con el
        fondo, con el aparejo del caso actual.
      </p>
      <div className="opt-form" role="group" aria-label="Parámetros de la simulación">
        <fieldset className="field sim-speeds">
          <legend className="label">
            Velocidades [kn] (hasta {MAX_SIM_SPEEDS}, {speeds.length} elegidas)
          </legend>
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
          <legend className="label">Resolución</legend>
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
                {SIM_QUALITY_LABEL[q]} ({SIM_RESOLUTION[q]})
              </label>
            ))}
          </div>
          <span className="help">≈ {estimate} s en el servidor</span>
        </fieldset>
      </div>
      <div className="calc-row">
        <button
          type="button"
          className="btn primary"
          onClick={run}
          disabled={!speeds.length || busy || !committed}
        >
          Simular
        </button>
      </div>
      <div className="status-line" role="status" aria-live="polite">
        {busy ? (
          <>
            <span className="spinner" aria-hidden="true" /> Simulando… <Elapsed since={startedAt} />{' '}
            de ≈ {estimate} s
          </>
        ) : r ? (
          <span>
            {r.results.length}{' '}
            {r.results.length === 1 ? 'velocidad simulada' : 'velocidades simuladas'} en{' '}
            {fmtFixed(r.runtime_s, 1)} s (resolución {String(r.settings.resolution)}).
          </span>
        ) : null}
      </div>
      {err && (
        <div className="alert error" role="alert">
          <span>
            <strong>
              {err instanceof ApiError && err.status ? `Error ${err.status}` : 'Error'}:
            </strong>{' '}
            {err.message}
          </span>
        </div>
      )}
      {bad.length > 0 && (
        <div className="alert warn" role="note">
          La simulación no convergió del todo a {bad.map((v) => fmtFixed(v, 1)).join(', ')} kn: tome
          esos valores con cautela.
        </div>
      )}

      {r && (
        <div className={`row-gap${busy ? ' stale' : ''}`} style={{ marginTop: 16 }}>
          {Object.entries(r.projections_svg).map(([k, p]) => (
            <section
              key={k}
              className="sim-speed"
              aria-label={`Proyecciones a ${k.replace('.', ',')} kn`}
            >
              <h3 className="group-title">A {speedLabel(Number(k))} kn</h3>
              <div className="sim-views" data-speed={k}>
                {VIEWS.map((view) => (
                  <figure key={view.key} className="sim-view" style={{ margin: 0 }}>
                    <figcaption>{view.label}</figcaption>
                    <ZoomStage
                      key={`${submitted}-${k}-${view.key}`}
                      svg={p[view.key]}
                      alt={`${view.label} de la red simulada a ${k.replace('.', ',')} kn`}
                      label={`${view.label} de la red a ${k.replace('.', ',')} kn. Arrastre para desplazar, rueda o teclas + y − para acercar, 0 para restablecer.`}
                      className="compact"
                      testId="sim-svg"
                    />
                  </figure>
                ))}
              </div>
            </section>
          ))}
          {Object.keys(r.projections_svg).length < r.results.length && (
            <p className="help">Se dibujan las tres primeras velocidades.</p>
          )}
          <section aria-labelledby={`${ids}-cmp`}>
            <h3 className="group-title" id={`${ids}-cmp`}>
              Simulación, motor empírico{r.dynamit_comparison?.length ? ' y DynamiT' : ''}
            </h3>
            <CompareTable r={r} />
            <div className="alert info sim-note" role="note">
              <span>
                <strong>Sobre la resistencia.</strong> El arrastre simulado es sólo el de los hilos
                (Morison con C<sub>N</sub> = {fmt(Number(r.settings.cn))} y C<sub>T</sub> ={' '}
                {fmt(Number(r.settings.ct))}) más el rozamiento con el fondo: en la red FAO A-3
                queda ≈ 50 % por debajo de la RA de DynamiT entre 2 y 4 kn, y la RN empírica del
                motor (Aberdeen) ≈ 20 % por encima. Las aberturas, en cambio, coinciden: AH dentro
                del 3 % y AV dentro del 10–20 %. La brecha de resistencia apunta a lo que el modelo
                no tiene —nudos, vibración y ondulación del paño, sombra hidrodinámica entre hilos y
                coeficientes del hilo calibrados en flujo uniforme— y no se cierra con C<sub>N</sub>
                /C<sub>T</sub> dentro de los rangos de la literatura (ver el capítulo 21 del libro).
                Use la simulación para la forma y las aberturas, y el motor para la resistencia de
                diseño.
              </span>
            </div>
          </section>
        </div>
      )}
      {!r && !busy && !err && (
        <p className="empty">
          Elija hasta tres velocidades y pulse «Simular». La versión rápida tarda alrededor de un
          segundo por velocidad.
        </p>
      )}
    </div>
  );
}
