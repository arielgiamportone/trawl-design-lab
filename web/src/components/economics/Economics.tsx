import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import {
  api,
  type EconomicsCompareRequest,
  type EconomicsRequest,
  type EconomicsOut,
  type TripEconomics,
} from '../../api/client';
import { loadPrices } from '../../lib/components';
import {
  COST_LABELS,
  curveRows,
  ECO_VIEW_KEY,
  filled,
  GROUPS,
  loadForm,
  saveForm,
  toInputs,
  type EcoForm,
} from '../../lib/economics';
import { fmt, fmtFixed } from '../../lib/format';
import { loadJson, saveJson } from '../../lib/storage';
import { useChartColors } from '../../lib/theme';
import { useCase } from '../../state/useCase';
import { ChartCard, Legend } from '../charts/ChartParts';
import { SpeedLineChart } from '../charts/SpeedLineChart';

type View = 'curva' | 'comparar';

/** Rango de velocidades y reserva de tiro de la curva (los del optimizador). */
const RANGE = { v_min_kn: 1.5, v_max_kn: 4.0, margin: 0.1 };

function money(v: number | null | undefined, cur: string): string {
  return v === null || v === undefined ? '—' : `${fmtFixed(v, 0)} ${cur}`;
}

/**
 * Pestaña «Economía» (Fase 16): costo, ingreso y margen de una marea a cada velocidad, con los
 * datos de la operación que carga el usuario; comparación con otras redes y ahorro.
 */
export function Economics() {
  const { committed } = useCase();
  const [form, setFormState] = useState<EcoForm>(() => loadForm());
  const [useBom, setUseBom] = useState(false);
  const [view, setView] = useState<View>(() => loadJson<View>(ECO_VIEW_KEY) ?? 'curva');
  const setForm = (f: EcoForm) => {
    setFormState(f);
    saveForm(f);
  };
  const inputs = useMemo(() => toInputs(form), [form]);
  const prices = useMemo(() => (useBom ? loadPrices() : {}), [useBom]);
  const q = useQuery({
    queryKey: ['economics', committed, inputs, prices],
    queryFn: ({ signal }) =>
      api.economics(
        { ...committed!, economics: inputs, prices, ...RANGE } as EconomicsRequest,
        signal,
      ),
    enabled: committed !== null,
    placeholderData: (prev) => prev,
  });
  const r = q.data;
  const nFilled = filled(form);
  // Abierto de entrada sólo si no hay datos; después manda el usuario.
  const [formOpen, setFormOpen] = useState(() => filled(loadForm()) === 0);

  return (
    <div className="economics" data-testid="economics">
      <p className="section-sub">
        Cuánto cuesta y cuánto deja una marea con esta red, a cada velocidad. Cargue los precios de
        su puerto: la app no inventa precios, y lo que falte queda fuera del cálculo y se avisa. Los
        datos quedan guardados en este navegador.
      </p>
      <details
        className="accordion"
        open={formOpen}
        onToggle={(e) => setFormOpen((e.target as HTMLDetailsElement).open)}
      >
        <summary>
          <span>
            Datos de la operación ({nFilled} cargados · {form.currency})
          </span>
        </summary>
        <div className="accordion-body">
          <OperationForm form={form} onChange={setForm} />
          <label className="check-row">
            <input type="checkbox" checked={useBom} onChange={(e) => setUseBom(e.target.checked)} />
            Si falta el costo de la red y el aparejo, tomarlo de la lista de materiales (precios
            cargados en «Componentes»)
          </label>
        </div>
      </details>
      {!committed && <p className="empty">Complete el caso para ver la economía.</p>}
      {q.error && (
        <p className="alert crit" role="alert">
          {q.error.message}
        </p>
      )}
      {r && (
        <>
          <BestSummary r={r} />
          <div className="segmented no-print" role="group" aria-label="Sección de la economía">
            {(
              [
                ['curva', 'Por velocidad'],
                ['comparar', 'Comparar redes'],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                aria-pressed={view === id}
                onClick={() => {
                  setView(id);
                  saveJson(ECO_VIEW_KEY, id);
                }}
              >
                {label}
              </button>
            ))}
          </div>
          {view === 'curva' && <SpeedView r={r} />}
          {view === 'comparar' && <CompareView inputs={inputs} prices={prices} />}
          <ul className="help">
            {r.notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function OperationForm({ form, onChange }: { form: EcoForm; onChange: (f: EcoForm) => void }) {
  const set = (key: string, text: string) =>
    onChange({ ...form, values: { ...form.values, [key]: text } });
  return (
    <div className="eco-form">
      <div className="eco-row">
        <label className="inline-field">
          Moneda
          <input
            aria-label="Moneda"
            value={form.currency}
            maxLength={3}
            size={4}
            onChange={(e) => onChange({ ...form, currency: e.target.value.toUpperCase() })}
          />
        </label>
        <label className="inline-field">
          Tripulación
          <select
            aria-label="Pago de la tripulación"
            value={form.crewMode}
            onChange={(e) => onChange({ ...form, crewMode: e.target.value as EcoForm['crewMode'] })}
          >
            <option value="share">a la parte</option>
            <option value="wage">a jornal</option>
            <option value="none">no se cuenta</option>
          </select>
        </label>
      </div>
      {GROUPS.map((g) => (
        <fieldset key={g.id} className="eco-group">
          <legend>{g.title}</legend>
          {g.fields.map((f) => (
            <label key={f.key} className="eco-field">
              <span>
                {f.label}
                {f.unit ? (
                  <span className="unit">
                    {' '}
                    [{f.kind === 'money' ? `${form.currency} ${f.unit}` : f.unit}]
                  </span>
                ) : null}
                {f.kind === 'money' && !f.unit ? (
                  <span className="unit"> [{form.currency}]</span>
                ) : null}
              </span>
              <input
                inputMode="decimal"
                aria-label={f.label}
                value={form.values[f.key] ?? ''}
                placeholder={
                  f.fallback === undefined
                    ? 'sin dato'
                    : `${fmt(f.unit?.startsWith('%') ? f.fallback * 100 : f.fallback)} (por defecto)`
                }
                onChange={(e) => set(f.key, e.target.value)}
              />
              {f.help && <span className="help">{f.help}</span>}
            </label>
          ))}
        </fieldset>
      ))}
    </div>
  );
}

function BestSummary({ r }: { r: EconomicsOut }) {
  const best: TripEconomics | undefined =
    r.trips.find((t) => t.speed_kn === r.best_margin_kn) ??
    r.trips.find((t) => t.speed_kn === r.least_fuel_kg_kn);
  const missing = Array.from(new Set(r.trips.flatMap((t) => t.missing)));
  return (
    <div data-testid="eco-summary">
      <div className="guide-summary">
        <div>
          <span className="kpi-label">Velocidad de mayor margen</span>
          <strong>{r.best_margin_kn === null ? '—' : `${fmtFixed(r.best_margin_kn, 2)} kn`}</strong>
        </div>
        <div>
          <span className="kpi-label">Margen por marea</span>
          <strong>{money(best?.margin, r.currency)}</strong>
        </div>
        <div>
          <span className="kpi-label">Costo por kg</span>
          <strong>
            {best?.cost_per_kg === null || best?.cost_per_kg === undefined
              ? '—'
              : `${fmtFixed(best.cost_per_kg, 2)} ${r.currency}`}
          </strong>
        </div>
        <div>
          <span className="kpi-label">Gasoil por marea</span>
          <strong>{best ? `${fmtFixed(best.fuel_l, 0)} L` : '—'}</strong>
        </div>
        <div>
          <span className="kpi-label">Margen por año</span>
          <strong>{money(r.year.margin, r.currency)}</strong>
        </div>
        <div>
          <span className="kpi-label">Precio de equilibrio</span>
          <strong>
            {best?.breakeven_price === null || best?.breakeven_price === undefined
              ? '—'
              : `${fmtFixed(best.breakeven_price, 2)} ${r.currency}/kg`}
          </strong>
        </div>
      </div>
      {missing.length > 0 && (
        <p className="alert warn" role="status">
          Faltan datos: {missing.join(', ')}.{' '}
          {best?.revenue === null ? '' : 'Lo que falta queda fuera del costo.'}
        </p>
      )}
    </div>
  );
}

function SpeedView({ r }: { r: EconomicsOut }) {
  const c = useChartColors();
  const rows = curveRows(r.trips);
  const feasible = r.trips.filter((t) => t.feasible).map((t) => t.speed_kn);
  const hasMoney = r.trips.some((t) => t.total_cost !== null);
  const series = hasMoney
    ? [
        { key: 'revenue', name: 'Ingreso', color: c.s3, width: 2, unit: r.currency },
        { key: 'cost', name: 'Costo', color: c.s2, width: 2, unit: r.currency },
        { key: 'margin', name: 'Margen', color: c.s1, width: 3, unit: r.currency },
      ]
    : [{ key: 'fuel', name: 'Gasoil por marea', color: c.s2, width: 2, unit: 'L' }];
  return (
    <>
      <ChartCard
        id="eco-curva"
        title={hasMoney ? 'Ingreso, costo y margen por marea' : 'Gasoil por marea'}
        sub="Según la velocidad de arrastre; la franja marca donde el buque remolca con reserva."
        legend={series.map((s) => ({ name: s.name, color: s.color, kind: 'line' as const }))}
      >
        <SpeedLineChart
          rows={rows}
          series={series}
          yUnit={hasMoney ? r.currency : 'L'}
          window={
            feasible.length
              ? { from: Math.min(...feasible), to: Math.max(...feasible), label: 'remolcable' }
              : null
          }
          refX={r.best_margin_kn === null ? null : { x: r.best_margin_kn, label: 'mayor margen' }}
          ariaLabel="Ingreso, costo y margen de la marea según la velocidad"
        />
      </ChartCard>
      <div className="table-wrap">
        <table className="data" aria-label="Economía por velocidad" data-testid="eco-table">
          <thead>
            <tr>
              <th scope="col" className="num">
                v [kn]
              </th>
              <th scope="col">Remolca</th>
              <th scope="col" className="num">
                Gasoil [L]
              </th>
              <th scope="col" className="num">
                Captura [kg]
              </th>
              <th scope="col" className="num">
                Costo
              </th>
              <th scope="col" className="num">
                Margen
              </th>
              <th scope="col" className="num">
                Costo/kg
              </th>
            </tr>
          </thead>
          <tbody>
            {r.trips.map((t) => (
              <tr
                key={t.speed_kn}
                data-speed={t.speed_kn}
                className={t.speed_kn === r.best_margin_kn ? 'row-best' : undefined}
              >
                <td className="num">{fmtFixed(t.speed_kn, 2)}</td>
                <td>
                  <span className={`badge ${t.feasible ? 'good' : 'crit'}`}>
                    {t.feasible ? 'sí' : 'no'}
                  </span>
                  {(t.warnings ?? []).length > 0 && (
                    <span className="help"> {(t.warnings ?? []).join('; ')}</span>
                  )}
                </td>
                <td className="num">{fmtFixed(t.fuel_l, 0)}</td>
                <td className="num">{t.catch_kg === null ? '—' : fmtFixed(t.catch_kg, 0)}</td>
                <td className="num">{t.total_cost === null ? '—' : fmtFixed(t.total_cost, 0)}</td>
                <td className="num">{t.margin === null ? '—' : fmtFixed(t.margin, 0)}</td>
                <td className="num">{t.cost_per_kg === null ? '—' : fmtFixed(t.cost_per_kg, 2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <CostBreakdown r={r} />
    </>
  );
}

function CostBreakdown({ r }: { r: EconomicsOut }) {
  const c = useChartColors();
  const best =
    r.trips.find((t) => t.speed_kn === r.best_margin_kn) ??
    r.trips.find((t) => t.speed_kn === r.least_fuel_kg_kn);
  if (!best || best.total_cost === null) return null;
  const items = Object.entries(best.costs).filter(([, v]) => v !== null) as [string, number][];
  const total = items.reduce((a, [, v]) => a + v, 0) || 1;
  const colors = [c.s2, c.s4, c.s1, c.s7, c.s5, c.s3];
  return (
    <div className="eco-breakdown" data-testid="eco-breakdown">
      <h3 className="subhead">
        Costo de la marea a {fmtFixed(best.speed_kn, 2)} kn: {money(best.total_cost, r.currency)}
      </h3>
      <div className="eco-bar" role="img" aria-label="Reparto del costo de la marea">
        {items.map(([k, v], i) => (
          <span
            key={k}
            style={{ width: `${(100 * v) / total}%`, background: colors[i % colors.length] }}
            title={`${COST_LABELS[k] ?? k}: ${fmtFixed(v, 0)}`}
          />
        ))}
      </div>
      <Legend
        items={items.map(([k, v], i) => ({
          name: `${COST_LABELS[k] ?? k} ${fmtFixed((100 * v) / total, 0)} %`,
          color: colors[i % colors.length]!,
          kind: 'rect' as const,
        }))}
      />
    </div>
  );
}

function CompareView({
  inputs,
  prices,
}: {
  inputs: ReturnType<typeof toInputs>;
  prices: Record<string, unknown>;
}) {
  const { committed, catalogs } = useCase();
  const [alt, setAlt] = useState<string>('');
  const [gear, setGear] = useState('');
  const [request, setRequest] = useState<EconomicsCompareRequest | null>(null);
  const options = catalogs.nets.filter((n) => n.id !== committed?.net);
  const build = (): EconomicsCompareRequest | null => {
    if (!committed || !alt) return null;
    const n = Number(gear.replace(',', '.'));
    return {
      cases: [
        { label: 'Red actual', case: committed },
        {
          label: options.find((o) => o.id === alt)?.name ?? alt,
          case: { ...committed, net: alt, net_modified: null },
          gear_cost: gear.trim() && Number.isFinite(n) ? n : null,
        },
      ],
      economics: inputs,
      prices: prices as EconomicsCompareRequest['prices'],
      speed_kn: null,
      ...RANGE,
    };
  };
  const q = useQuery({
    queryKey: ['economics-compare', request],
    queryFn: ({ signal }) => api.economicsCompare(request!, signal),
    enabled: request !== null,
  });
  const res = q.data;
  return (
    <div data-testid="eco-compare">
      <div className="catalog-actions">
        <label className="inline-field">
          Comparar con
          <select aria-label="Red a comparar" value={alt} onChange={(e) => setAlt(e.target.value)}>
            <option value="">elija una red del catálogo…</option>
            {options.map((n) => (
              <option key={n.id} value={n.id}>
                {n.name}
              </option>
            ))}
          </select>
        </label>
        <label className="inline-field">
          Costo de la red nueva [{inputs.currency}]
          <input
            aria-label="Costo de la red nueva"
            inputMode="decimal"
            size={10}
            value={gear}
            onChange={(e) => setGear(e.target.value)}
          />
        </label>
        <button type="button" className="btn" disabled={!alt} onClick={() => setRequest(build())}>
          Calcular
        </button>
      </div>
      <p className="help">
        Mismo buque, portón y datos de operación; cada red trabaja a su velocidad de mayor margen.
        El ahorro es la diferencia de margen por año; el repago, el costo de la red nueva sobre ese
        ahorro.
      </p>
      {q.isFetching && <p className="empty">Calculando…</p>}
      {q.error && (
        <p className="alert crit" role="alert">
          {q.error.message}
        </p>
      )}
      {res && (
        <div className="table-wrap">
          <table className="data" aria-label="Comparación económica">
            <thead>
              <tr>
                <th scope="col">Red</th>
                <th scope="col" className="num">
                  v [kn]
                </th>
                <th scope="col" className="num">
                  Gasoil por año [L]
                </th>
                <th scope="col" className="num">
                  Margen por año
                </th>
                <th scope="col" className="num">
                  Ahorro por año
                </th>
                <th scope="col" className="num">
                  Repago
                </th>
              </tr>
            </thead>
            <tbody>
              {res.rows.map((row) => (
                <tr key={row.label} data-compare={row.net_id}>
                  <td>{row.label}</td>
                  <td className="num">{row.trip ? fmtFixed(row.trip.speed_kn, 2) : '—'}</td>
                  <td className="num">
                    {row.annual_fuel_l === null ? '—' : fmtFixed(row.annual_fuel_l, 0)}
                  </td>
                  <td className="num">{money(row.annual_margin, res.currency)}</td>
                  <td className="num">{money(row.savings_year, res.currency)}</td>
                  <td className="num">
                    {row.payback_years === null
                      ? '—'
                      : row.payback_years < 1
                        ? `${fmtFixed(row.payback_years * 12, 1)} meses`
                        : `${fmtFixed(row.payback_years, 1)} años`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
