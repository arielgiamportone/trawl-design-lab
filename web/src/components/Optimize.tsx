import { useQuery } from '@tanstack/react-query';
import { useId, useState } from 'react';
import { api, ApiError, type Evaluation, type OptimizeRequest } from '../api/client';
import { fmtFixed, fmtPct } from '../lib/format';
import { msg, useT } from '../i18n';
import { recall, remember } from '../lib/memo';
import {
  buildOptimize,
  constraintLabel,
  CONSTRAINT_UNITS,
  defaultOptimizeForm,
  OBJECTIVES,
  objectiveUnit,
  type OptimizeForm,
} from '../lib/optimize';
import { fmtSim, simUnit, simValueOpt } from '../lib/simulate';
import { fmtU } from '../lib/units';
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
  const T = msg().optimize.tiles;
  const tile = (key: string, label: string, v: number | null, unit: string, digits?: number) => ({
    key,
    label,
    value: fmtSim(v, unit, { digits, unit: false }),
    unit: simUnit(unit),
  });
  return [
    { key: 's', label: T.s, value: fmtFixed(b.s, 3) },
    { key: 'v', label: T.v, value: fmtFixed(b.v_kn, 2), unit: 'kn' },
    tile('ah', T.ah, b.ah_m, 'm', 2),
    tile('av', T.av, b.av_m, 'm', 2),
    tile('area', T.area, b.area_rate_m2_h, 'm²/h', 0),
    tile('rt', T.rt, b.demand_kgf, 'kgf', 0),
    tile('ft', T.ft, b.available_kgf, 'kgf', 0),
    {
      key: 'margin',
      label: T.margin,
      value: b.thrust_margin === null ? '—' : fmtPct(b.thrust_margin * 100, 1),
    },
  ];
}

/** Límites de una restricción, convertidos al sistema activo y con su unidad. */
function bound(lower: number | null, upper: number | null, unit: string): string {
  const parts = [];
  if (lower !== null) parts.push(`≥ ${fmtU(lower, unit)}`);
  if (upper !== null) parts.push(`≤ ${fmtU(upper, unit)}`);
  return parts.join(msg().optimize.and) || '—';
}

export function Optimize({ onApplied }: { onApplied?: () => void }) {
  const { state, catalogs, committed, update } = useCase();
  const ids = useId();
  const c = useChartColors();
  const T = useT().optimize;
  const S = useT().simulate;
  const [form, setFormState] = useState<OptimizeForm>(
    () => recall<OptimizeForm>(FORM_KEY) ?? defaultOptimizeForm(),
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

  const unit = r ? objectiveUnit(r.objective) : undefined;
  const grid = r?.grid as { s_values?: number[]; v_values?: number[] } | undefined;

  return (
    <div>
      <h2 className="section-title">{T.title}</h2>
      <p className="section-sub" style={{ marginBottom: 12 }}>
        {T.intro}
      </p>
      <div className="opt-form" role="group" aria-label={T.formLabel}>
        <fieldset className="field opt-objective">
          <legend className="label">{T.objective}</legend>
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
        {field('margin', T.margin, 'F_T ≥ (1 + m)·R_T')}
        {field('sMin', T.sMin)}
        {field('sMax', T.sMax)}
        {field('vMin', T.vMin)}
        {field('vMax', T.vMax)}
        {field('nS', T.nS, T.nSHelp, 'numeric')}
        {field('nV', T.nV, undefined, 'numeric')}
        <div className="field">
          <label htmlFor={`${ids}-door`}>{T.door}</label>
          <select
            id={`${ids}-door`}
            value={doorValue}
            onChange={(e) => setForm({ door: e.target.value })}
          >
            {catalogs.doors.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
                {d.area_m2 != null ? ` · ${fmtU(d.area_m2, 'm²', { digits: 2 })}` : ''}
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
            {T.refine}
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
          {T.run}
        </button>
      </div>
      <div className="status-line" role="status" aria-live="polite">
        {busy ? (
          <>
            <span className="spinner" aria-hidden="true" /> {T.running}
          </>
        ) : r ? (
          <span>{T.done(r.engine_runs, fmtFixed(r.runtime_s, 1))}</span>
        ) : null}
      </div>
      {err && (
        <div className="alert error" role="alert">
          <span>
            <strong>
              {err instanceof ApiError && err.status ? S.errorStatus(err.status) : S.error}:
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
                  {T.best}{' '}
                  {r.feasible ? (
                    <span className="badge good">{T.feasible}</span>
                  ) : (
                    <span className="badge crit">{T.noneFeasible}</span>
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
                    return fmtSim(v, unit?.unit ?? '', {
                      digits: r.objective === 'energy' ? undefined : 0,
                    });
                  })()}
                  {T.bestSub(r.best.vessel_id, r.best.door_id, r.best.warp_id ?? T.noWarp)}
                </p>
              </div>
              <button
                type="button"
                className="btn primary small"
                onClick={() => void apply()}
                disabled={applying}
              >
                {applying ? T.applying : T.apply}
              </button>
            </div>
            {!r.feasible && (
              <div className="alert warn" role="note">
                {T.infeasibleNote}
              </div>
            )}
            {applyError && (
              <div className="alert error" role="alert">
                {T.applyError(applyError)}
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
                <caption className="sr-only">{T.constraintsCaption}</caption>
                <thead>
                  <tr>
                    <th scope="col">{T.constraint}</th>
                    <th scope="col" className="num">
                      {T.value}
                    </th>
                    <th scope="col" className="num">
                      {T.limit}
                    </th>
                    <th scope="col">{T.ok}</th>
                  </tr>
                </thead>
                <tbody>
                  {r.best.constraints.map((k) => (
                    <tr key={k.name} data-constraint={k.name}>
                      <th scope="row" title={k.description}>
                        {constraintLabel(k.name)}
                      </th>
                      <td className="num">{fmtU(k.value, CONSTRAINT_UNITS[k.name] ?? '')}</td>
                      <td className="num">
                        {bound(k.lower, k.upper, CONSTRAINT_UNITS[k.name] ?? '')}
                      </td>
                      <td>
                        <span className={`badge ${k.ok ? 'good' : 'crit'}`}>
                          {k.ok ? T.okBadge : T.noBadge}
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
              title={T.mapTitle}
              sub={T.mapSub(
                r.best.net_id.replace(/_s[\d.]+$/, ''),
                grid?.s_values?.length ?? 0,
                grid?.v_values?.length ?? 0,
              )}
              note={T.mapNote}
            >
              <Heatmap r={r} />
            </ChartCard>
            <ChartCard
              id="opt-pareto"
              title={T.paretoTitle}
              sub={T.paretoSub}
              legend={[
                { name: T.paretoFront, color: c.s1, kind: 'line' },
                { name: T.best, color: c.s2, kind: 'rect' },
              ]}
              table={
                <DataTable
                  caption={T.paretoCaption}
                  columns={[
                    { key: 's', label: 's' },
                    { key: 'v', label: 'v [kn]' },
                    { key: 'area', label: `${T.area} [${simUnit('m²/h')}]` },
                    { key: 'energy', label: `R_T/AH [${simUnit('kgf·m/m²')}]` },
                  ]}
                  rows={r.pareto.map((e) => {
                    const area = simValueOpt(e.area_rate_m2_h, 'm²/h');
                    return {
                      s: e.s,
                      v: e.v_kn,
                      area: area === null ? null : Math.round(area),
                      energy: simValueOpt(e.energy_kgf_m_per_m2, 'kgf·m/m²'),
                    };
                  })}
                />
              }
            >
              <ParetoChart r={r} />
            </ChartCard>
          </div>
        </div>
      )}
      {!r && !busy && !err && (
        <p className="empty">{T.empty}</p>
      )}
    </div>
  );
}
