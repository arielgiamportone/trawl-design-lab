import { useQuery } from '@tanstack/react-query';
import { useId, useState } from 'react';
import { api, ApiError, type Evaluation, type OptimizeRequest } from '../api/client';
import { fmt, fmtFixed, fmtPct } from '../lib/format';
import { recall, remember } from '../lib/memo';
import {
  buildOptimize,
  CONSTRAINT_LABELS,
  DEFAULT_FORM,
  OBJECTIVES,
  OBJECTIVE_UNITS,
  type OptimizeForm,
} from '../lib/optimize';
import { useChartColors } from '../lib/theme';
import { useCase } from '../state/useCase';
import { ChartCard, DataTable } from './charts/ChartParts';
import { Heatmap } from './opt/Heatmap';
import { ParetoChart } from './opt/ParetoChart';

// Último pedido y formulario: sobreviven al cambio de pestaña, no a la recarga de la página.
const REQ_KEY = 'optimize:request';
const FORM_KEY = 'optimize:form';

interface Tile {
  key: string;
  label: string;
  value: string;
  unit?: string;
}

function bestTiles(b: Evaluation): Tile[] {
  return [
    { key: 's', label: 'Escala de la red s', value: fmtFixed(b.s, 3) },
    { key: 'v', label: 'Velocidad', value: fmtFixed(b.v_kn, 2), unit: 'kn' },
    { key: 'ah', label: 'Abertura horizontal AH', value: fmtFixed(b.ah_m, 2), unit: 'm' },
    { key: 'av', label: 'Abertura vertical AV', value: fmtFixed(b.av_m, 2), unit: 'm' },
    {
      key: 'area',
      label: 'Área barrida por hora',
      value: fmt(b.area_rate_m2_h === null ? null : Math.round(b.area_rate_m2_h)),
      unit: 'm²/h',
    },
    {
      key: 'rt',
      label: 'Resistencia total R_T',
      value: fmt(b.demand_kgf === null ? null : Math.round(b.demand_kgf)),
      unit: 'kgf',
    },
    {
      key: 'ft',
      label: 'Tiro disponible F_T',
      value: fmt(b.available_kgf === null ? null : Math.round(b.available_kgf)),
      unit: 'kgf',
    },
    {
      key: 'margin',
      label: 'Margen F_T/R_T − 1',
      value: b.thrust_margin === null ? '—' : fmtPct(b.thrust_margin * 100, 1),
    },
  ];
}

function bound(lower: number | null, upper: number | null): string {
  const parts = [];
  if (lower !== null) parts.push(`≥ ${fmt(lower)}`);
  if (upper !== null) parts.push(`≤ ${fmt(upper)}`);
  return parts.join(' y ') || '—';
}

export function Optimize({ onApplied }: { onApplied?: () => void }) {
  const { state, catalogs, committed, update } = useCase();
  const ids = useId();
  const c = useChartColors();
  const [form, setFormState] = useState<OptimizeForm>(
    () => recall<OptimizeForm>(FORM_KEY) ?? { ...DEFAULT_FORM },
  );
  const setForm = (patch: Partial<OptimizeForm>) =>
    setFormState((f) => {
      const next = { ...f, ...patch };
      remember(FORM_KEY, next);
      return next;
    });
  const [submitted, setSubmitted] = useState<string | null>(() => recall<string>(REQ_KEY) ?? null);
  const [applying, setApplying] = useState(false);
  const [applyError, setApplyError] = useState<string | null>(null);
  const built = buildOptimize(form);
  const doorValue = form.door || state.door || catalogs.doors[0]?.id || '';
  // Con una red ya escalada se optimiza la del catálogo (la escala es siempre absoluta).
  const baseNet: OptimizeRequest['net'] = state.scaled ? state.net : (committed?.net ?? state.net);

  const query = useQuery({
    queryKey: ['optimize', submitted],
    queryFn: ({ signal }) =>
      api.optimize(JSON.parse(submitted as string) as OptimizeRequest, signal),
    enabled: submitted !== null,
    staleTime: Infinity,
    gcTime: 30 * 60_000,
    retry: false,
  });
  const r = query.data;

  const run = () => {
    if (!built.body) return;
    const req: OptimizeRequest = {
      net: baseNet,
      vessel: state.vessel,
      door: doorValue || null,
      class_vessels: null,
      propeller: null,
      door_angle: null,
      ...built.body,
    };
    const key = JSON.stringify(req);
    remember(REQ_KEY, key);
    if (key === submitted) void query.refetch();
    else setSubmitted(key);
  };

  const apply = async () => {
    if (!r) return;
    const req = JSON.parse(submitted as string) as OptimizeRequest;
    setApplying(true);
    setApplyError(null);
    try {
      const s = r.best.s;
      const std = await api.scaledNet({ net: req.net, s });
      const modBase = state.netModified
        ? state.scaled
          ? state.netModified
          : (committed?.net_modified ?? state.netModified)
        : null;
      const mod = modBase ? await api.scaledNet({ net: modBase, s }) : null;
      update((st) => ({
        ...st,
        door: typeof req.door === 'string' ? req.door : st.door,
        edits: { std: {}, mod: {} },
        scaled: { s, std, mod, speed: r.best.v_kn },
      }));
      onApplied?.();
    } catch (e) {
      setApplyError((e as Error).message);
    } finally {
      setApplying(false);
    }
  };

  const err = query.error;
  const busy = query.isFetching;
  const field = (
    k: keyof OptimizeForm,
    label: string,
    help?: string,
    inputMode: 'decimal' | 'numeric' = 'decimal',
  ) => (
    <div className="field">
      <label htmlFor={`${ids}-${k}`}>{label}</label>
      <input
        id={`${ids}-${k}`}
        type="text"
        inputMode={inputMode}
        value={String(form[k])}
        aria-invalid={built.errors[k] ? true : undefined}
        aria-describedby={built.errors[k] ? `${ids}-${k}-err` : undefined}
        onChange={(e) => setForm({ [k]: e.target.value })}
      />
      {built.errors[k] ? (
        <span className="field-error" id={`${ids}-${k}-err`}>
          {built.errors[k]}
        </span>
      ) : (
        help && <span className="help">{help}</span>
      )}
    </div>
  );

  const unit = r ? OBJECTIVE_UNITS[r.objective] : undefined;
  const grid = r?.grid as { s_values?: number[]; v_values?: number[] } | undefined;

  return (
    <div>
      <h2 className="section-title">Optimizar escala y velocidad</h2>
      <p className="section-sub" style={{ marginBottom: 12 }}>
        Busca la escala de la red (mismo mallero, s veces más mallas por borde) y la velocidad que
        mejor cumplen el objetivo con el buque y el portón elegidos, respetando tiro, apertura,
        cable y portón.
      </p>
      <div className="opt-form" role="group" aria-label="Parámetros de la optimización">
        <fieldset className="field opt-objective">
          <legend className="label">Objetivo</legend>
          <div className="segmented">
            {OBJECTIVES.map((o) => (
              <label key={o.id} title={o.help}>
                <input
                  type="radio"
                  name={`${ids}-objective`}
                  value={o.id}
                  checked={form.objective === o.id}
                  onChange={() => setForm({ objective: o.id })}
                />
                {o.label}
              </label>
            ))}
          </div>
          <span className="help">{OBJECTIVES.find((o) => o.id === form.objective)?.help}</span>
        </fieldset>
        {field('margin', 'Reserva de tiro [%]', 'F_T ≥ (1 + m)·R_T')}
        {field('sMin', 'Escala mínima')}
        {field('sMax', 'Escala máxima')}
        {field('vMin', 'Velocidad mínima [kn]')}
        {field('vMax', 'Velocidad máxima [kn]')}
        {field('nS', 'Puntos en s', 'Malla: una corrida del motor por escala', 'numeric')}
        {field('nV', 'Puntos en v', undefined, 'numeric')}
        <div className="field">
          <label htmlFor={`${ids}-door`}>Portón</label>
          <select
            id={`${ids}-door`}
            value={doorValue}
            onChange={(e) => setForm({ door: e.target.value })}
          >
            {catalogs.doors.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
                {d.area_m2 != null ? ` · ${fmtFixed(d.area_m2, 2)} m²` : ''}
              </option>
            ))}
          </select>
        </div>
        <div className="field opt-refine">
          <label className="toggle-line">
            <input
              type="checkbox"
              checked={form.refine}
              onChange={(e) => setForm({ refine: e.target.checked })}
            />
            Refinar con evolución diferencial (más lento)
          </label>
        </div>
      </div>
      <div className="calc-row">
        <button
          type="button"
          className="btn primary"
          onClick={run}
          disabled={!built.body || busy || catalogs.loading}
        >
          Optimizar
        </button>
      </div>
      <div className="status-line" role="status" aria-live="polite">
        {busy ? (
          <>
            <span className="spinner" aria-hidden="true" /> Optimizando… (unos segundos)
          </>
        ) : r ? (
          <span>
            {r.engine_runs} corridas del motor en {fmtFixed(r.runtime_s, 1)} s.
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

      {r && (
        <div className={`row-gap${busy ? ' stale' : ''}`} style={{ marginTop: 16 }}>
          <section className="opt-best" aria-labelledby={`${ids}-best`} data-testid="opt-best">
            <div className="chart-head">
              <div>
                <h3 id={`${ids}-best`}>
                  Mejor diseño{' '}
                  {r.feasible ? (
                    <span className="badge good">Factible</span>
                  ) : (
                    <span className="badge crit">Ningún diseño factible</span>
                  )}
                </h3>
                <p className="chart-sub">
                  {unit?.label}:{' '}
                  {(() => {
                    const v =
                      r.objective === 'volume_rate'
                        ? r.best.volume_rate_m3_h
                        : r.objective === 'energy'
                          ? r.best.energy_kgf_m_per_m2
                          : r.best.area_rate_m2_h;
                    return v === null ? '—' : fmt(r.objective === 'energy' ? v : Math.round(v));
                  })()}{' '}
                  {unit?.unit} · buque {r.best.vessel_id} · portón {r.best.door_id} · cable{' '}
                  {r.best.warp_id ?? 'ninguno del catálogo'}
                </p>
              </div>
              <button
                type="button"
                className="btn primary small"
                onClick={() => void apply()}
                disabled={applying}
              >
                {applying ? 'Aplicando…' : 'Usar este diseño'}
              </button>
            </div>
            {!r.feasible && (
              <div className="alert warn" role="note">
                Ninguna combinación cumple todas las restricciones; se muestra la de menor
                violación.
              </div>
            )}
            {applyError && (
              <div className="alert error" role="alert">
                No se pudo aplicar el diseño: {applyError}
              </div>
            )}
            <div className="opt-tiles">
              {bestTiles(r.best).map((t) => (
                <div className="opt-tile" key={t.key} data-tile={t.key}>
                  <span className="kpi-label">{t.label}</span>
                  <span className="kpi-value">
                    {t.value}
                    {t.unit && <span className="unit">{t.unit}</span>}
                  </span>
                </div>
              ))}
            </div>
            <div className="table-wrap">
              <table className="data" data-testid="opt-constraints">
                <caption className="sr-only">Restricciones del mejor diseño</caption>
                <thead>
                  <tr>
                    <th scope="col">Restricción</th>
                    <th scope="col" className="num">
                      Valor
                    </th>
                    <th scope="col" className="num">
                      Límite
                    </th>
                    <th scope="col">Cumple</th>
                  </tr>
                </thead>
                <tbody>
                  {r.best.constraints.map((k) => (
                    <tr key={k.name} data-constraint={k.name}>
                      <th scope="row" title={k.description}>
                        {CONSTRAINT_LABELS[k.name] ?? k.name}
                      </th>
                      <td className="num">{fmt(k.value)}</td>
                      <td className="num">{bound(k.lower, k.upper)}</td>
                      <td>
                        <span className={`badge ${k.ok ? 'good' : 'crit'}`}>
                          {k.ok ? 'OK' : 'NO'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <div className="charts-grid">
            <ChartCard
              id="opt-mapa"
              title="Región factible en escala × velocidad"
              sub={`${r.best.net_id.replace(/_s[\d.]+$/, '')} · malla ${grid?.s_values?.length ?? 0} × ${grid?.v_values?.length ?? 0}`}
              note="Cada celda es una corrida del motor interpolada a esa velocidad. Pase el puntero para ver el valor."
            >
              <Heatmap r={r} />
            </ChartCard>
            <ChartCard
              id="opt-pareto"
              title="Frente de Pareto"
              sub="Área barrida por hora frente al trabajo de remolque por m² barrido"
              legend={[
                { name: 'Frente de Pareto (factibles no dominados)', color: c.s1, kind: 'line' },
                { name: 'Mejor diseño', color: c.s2, kind: 'rect' },
              ]}
              table={
                <DataTable
                  caption="Puntos del frente de Pareto"
                  columns={[
                    { key: 's', label: 's' },
                    { key: 'v', label: 'v [kn]' },
                    { key: 'area', label: 'Área [m²/h]' },
                    { key: 'energy', label: 'R_T/AH [kgf·m/m²]' },
                  ]}
                  rows={r.pareto.map((e) => ({
                    s: e.s,
                    v: e.v_kn,
                    area: e.area_rate_m2_h === null ? null : Math.round(e.area_rate_m2_h),
                    energy: e.energy_kgf_m_per_m2,
                  }))}
                />
              }
            >
              <ParetoChart r={r} />
            </ChartCard>
          </div>
        </div>
      )}
      {!r && !busy && !err && (
        <p className="empty">
          Elija el objetivo y los rangos y pulse «Optimizar». Se usa el caso actual (red, buque y
          portón) en modo corregido.
        </p>
      )}
    </div>
  );
}
