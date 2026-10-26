import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import {
  api,
  ApiError,
  type AssemblyOut,
  type ComponentOptimizeRequest,
  type ComponentOptimizeResponse,
} from '../../api/client';
import { useT } from '../../i18n';
import { applyAssembly, loadPrices, REGION_LABEL } from '../../lib/components';
import { fmt, fmtFixed } from '../../lib/format';
import { toDisplay, unitLabel } from '../../lib/units';
import { useCase } from '../../state/useCase';

type Objective = ComponentOptimizeRequest['objective'];

const OBJECTIVES: NonNullable<Objective>[] = ['drag', 'efficiency', 'cost'];

const COMPONENT_ROW = ['door', 'warp', 'float', 'twine'];

/**
 * «Armar con el catálogo»: el optimizador elige portón, cable, boyas e hilo entre los
 * componentes que se consiguen (región, marcas o sólo genéricos) y da alternativas.
 */
export function AssemblyPanel() {
  const { committed, design, update } = useCase();
  const T = useT().components;
  const [objective, setObjective] = useState<NonNullable<Objective>>('drag');
  const [region, setRegion] = useState('');
  const [genericOnly, setGenericOnly] = useState(false);
  const run = useMutation<ComponentOptimizeResponse, Error, ComponentOptimizeRequest>({
    mutationFn: (req) => api.optimizeComponents(req),
  });

  const start = () => {
    if (!committed) return;
    const params: Record<string, unknown> = { ...committed.params };
    for (const k of ['warp_id', 'float_id', 'twine_id', 'float_count']) delete params[k];
    if (region) params.component_region = region;
    if (genericOnly) params.generic_only = true;
    const prices = loadPrices();
    run.mutate({
      net: committed.net,
      vessel: committed.vessel,
      door: committed.door,
      params,
      components: committed.components ?? [],
      objective,
      v_bounds: [1.5, 4],
      margin: 0.1,
      max_doors: 5,
      max_floats: 4,
      max_twines: 4,
      prices,
      currency: Object.values(prices)[0]?.currency ?? null,
    });
  };
  const baseDoor = design.data?.case.door as string | undefined;
  const apply = (a: AssemblyOut) => update((s) => applyAssembly(s, a, baseDoor));
  const res = run.data;

  return (
    <div className="assembly" data-testid="assembly">
      <p className="section-sub">{T.asmIntro}</p>
      <div className="catalog-filters">
        <label className="inline-field">
          {T.objectiveLabel}
          <select
            aria-label={T.objectiveAria}
            value={objective}
            onChange={(e) => setObjective(e.target.value as NonNullable<Objective>)}
          >
            {OBJECTIVES.map((k) => (
              <option key={k} value={k}>
                {T.objective[k]}
              </option>
            ))}
          </select>
        </label>
        <label className="inline-field">
          {T.port}
          <select
            aria-label={T.portAria}
            value={region}
            onChange={(e) => setRegion(e.target.value)}
          >
            <option value="">{T.anyRegion}</option>
            {Object.entries(REGION_LABEL).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={genericOnly}
            onChange={(e) => setGenericOnly(e.target.checked)}
          />
          {T.genericOnly}
        </label>
        <button
          type="button"
          className="btn primary"
          disabled={!committed || run.isPending}
          onClick={start}
        >
          {run.isPending ? T.assembling : T.assemble}
        </button>
      </div>
      {run.error && (
        <p className="alert crit" role="alert">
          {run.error instanceof ApiError && run.error.status ? T.errorStatus(run.error.status) : ''}
          {run.error.message}
        </p>
      )}
      {res && (
        <>
          <p className="help">
            {T.evaluated(res.evaluated)} {res.feasible ? T.feasible : T.infeasible}
          </p>
          {res.notes.length > 0 && (
            <ul className="issues">
              {res.notes.map((n, k) => (
                <li key={k} className="warn">
                  {n}
                </li>
              ))}
            </ul>
          )}
          <div className="assembly-grid">
            <AssemblyCard a={res.best} title={T.recommended} onApply={apply} primary />
            {res.alternatives.map((a, k) => (
              <AssemblyCard
                key={k}
                a={a}
                title={a.generic && !res.best.generic ? T.genericAlt : T.alt(k + 1)}
                onApply={apply}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function AssemblyCard({
  a,
  title,
  onApply,
  primary,
}: {
  a: AssemblyOut;
  title: string;
  onApply: (a: AssemblyOut) => void;
  primary?: boolean;
}) {
  const T = useT().components;
  const failed = a.constraints.filter((c) => !c.ok);
  return (
    <section className="card card-pad" data-testid="assembly-card">
      <h4>
        {title} {a.generic && <span className="badge good">{T.generic}</span>}{' '}
        {!a.feasible && <span className="badge crit">{T.fails}</span>}
      </h4>
      <dl className="kv">
        {COMPONENT_ROW.map((k) => (
          <div key={k}>
            <dt>{T.slot[k]}</dt>
            <dd>{a.components[k] ?? T.fromPlan}</dd>
          </div>
        ))}
        {a.float_count != null && (
          <div>
            <dt>{T.floatCount}</dt>
            <dd>{a.float_count}</dd>
          </div>
        )}
        <div>
          <dt>{T.speed}</dt>
          <dd>{fmtFixed(a.speed_kn, 2)} kn</dd>
        </div>
        <div>
          <dt>{T.drag}</dt>
          <dd>
            {fmt(Math.round(toDisplay(a.demand_kgf, 'kgf')))} {unitLabel('kgf')}
          </dd>
        </div>
        <div>
          <dt>{T.margin}</dt>
          <dd>{fmtFixed(a.thrust_margin * 100, 0)} %</dd>
        </div>
        <div>
          <dt>{T.area}</dt>
          <dd>
            {fmt(Math.round(toDisplay(a.area_rate_m2_h, 'm²')))} {unitLabel('m²')}/h
          </dd>
        </div>
        <div>
          <dt>{T.cost}</dt>
          <dd>
            {a.cost != null ? `${fmt(a.cost)} ${a.currency ?? ''}` : T.noPrices}
            {a.missing_prices > 0 && a.cost != null && T.missingPrices(a.missing_prices)}
          </dd>
        </div>
      </dl>
      {failed.length > 0 && (
        <ul className="issues">
          {failed.map((c) => (
            <li key={c.name} className="crit">
              {c.description}
            </li>
          ))}
        </ul>
      )}
      <button
        type="button"
        className={`btn${primary ? ' primary' : ''}`}
        onClick={() => onApply(a)}
      >
        {T.apply}
      </button>
    </section>
  );
}
