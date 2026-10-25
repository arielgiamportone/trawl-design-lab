import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import {
  api,
  ApiError,
  type AssemblyOut,
  type ComponentOptimizeRequest,
  type ComponentOptimizeResponse,
} from '../../api/client';
import { applyAssembly, loadPrices, REGION_LABEL } from '../../lib/components';
import { fmt, fmtFixed } from '../../lib/format';
import { useCase } from '../../state/useCase';

type Objective = ComponentOptimizeRequest['objective'];

const OBJECTIVE_LABEL: Record<NonNullable<Objective>, string> = {
  drag: 'Menor resistencia (menos combustible por hora)',
  efficiency: 'Más área barrida por litro',
  cost: 'Menor costo de armado',
};

const COMPONENT_ROW: [string, string][] = [
  ['door', 'Portón'],
  ['warp', 'Cable'],
  ['float', 'Boyas'],
  ['twine', 'Hilo del paño'],
];

/**
 * «Armar con el catálogo»: el optimizador elige portón, cable, boyas e hilo entre los
 * componentes que se consiguen (región, marcas o sólo genéricos) y da alternativas.
 */
export function AssemblyPanel() {
  const { committed, design, update } = useCase();
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
      <p className="section-sub">
        Elige portón, cable, boyas e hilo entre los componentes del catálogo que cumplen el tiro del
        buque, la apertura de la red, la rotura del cable y la profundidad, y propone alternativas
        genéricas. Para ordenar por costo, cargue precios en la lista de materiales.
      </p>
      <div className="catalog-filters">
        <label className="inline-field">
          Objetivo
          <select
            aria-label="Objetivo del armado"
            value={objective}
            onChange={(e) => setObjective(e.target.value as NonNullable<Objective>)}
          >
            {Object.entries(OBJECTIVE_LABEL).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </label>
        <label className="inline-field">
          ¿Qué se consigue en su puerto?
          <select
            aria-label="Región del puerto"
            value={region}
            onChange={(e) => setRegion(e.target.value)}
          >
            <option value="">Cualquier región</option>
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
          Sólo genéricos
        </label>
        <button
          type="button"
          className="btn primary"
          disabled={!committed || run.isPending}
          onClick={start}
        >
          {run.isPending ? 'Armando…' : 'Armar con el catálogo'}
        </button>
      </div>
      {run.error && (
        <p className="alert crit" role="alert">
          {run.error instanceof ApiError && run.error.status ? `Error ${run.error.status}: ` : ''}
          {run.error.message}
        </p>
      )}
      {res && (
        <>
          <p className="help">
            {res.evaluated} armados evaluados.{' '}
            {res.feasible
              ? 'El recomendado cumple todas las restricciones.'
              : 'Ninguno cumple todo: se muestra el de menor violación.'}
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
            <AssemblyCard a={res.best} title="Recomendado" onApply={apply} primary />
            {res.alternatives.map((a, k) => (
              <AssemblyCard
                key={k}
                a={a}
                title={
                  a.generic && !res.best.generic ? 'Alternativa genérica' : `Alternativa ${k + 1}`
                }
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
  const failed = a.constraints.filter((c) => !c.ok);
  return (
    <section className="card card-pad" data-testid="assembly-card">
      <h4>
        {title} {a.generic && <span className="badge good">genérico</span>}{' '}
        {!a.feasible && <span className="badge crit">no cumple</span>}
      </h4>
      <dl className="kv">
        {COMPONENT_ROW.map(([k, label]) => (
          <div key={k}>
            <dt>{label}</dt>
            <dd>{a.components[k] ?? 'el del plano'}</dd>
          </div>
        ))}
        {a.float_count != null && (
          <div>
            <dt>Número de boyas</dt>
            <dd>{a.float_count}</dd>
          </div>
        )}
        <div>
          <dt>Velocidad</dt>
          <dd>{fmtFixed(a.speed_kn, 2)} kn</dd>
        </div>
        <div>
          <dt>Resistencia total</dt>
          <dd>{fmt(Math.round(a.demand_kgf))} kgf</dd>
        </div>
        <div>
          <dt>Reserva de tiro</dt>
          <dd>{fmtFixed(a.thrust_margin * 100, 0)} %</dd>
        </div>
        <div>
          <dt>Área barrida</dt>
          <dd>{fmt(Math.round(a.area_rate_m2_h))} m²/h</dd>
        </div>
        <div>
          <dt>Costo orientativo</dt>
          <dd>
            {a.cost != null ? `${fmt(a.cost)} ${a.currency ?? ''}` : 'sin precios'}
            {a.missing_prices > 0 && a.cost != null && ` (${a.missing_prices} sin precio)`}
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
        Aplicar al caso
      </button>
    </section>
  );
}
