import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import {
  api,
  type EconomicsCompareRequest,
  type EconomicsRequest,
  type EconomicsOut,
  type TripEconomics,
} from '../../api/client';
import { useT } from '../../i18n';
import { loadPrices } from '../../lib/components';
import {
  COST_LABELS,
  curveRows,
  ECO_VIEW_KEY,
  fieldText,
  filled,
  groups,
  loadForm,
  saveForm,
  storedText,
  toInputs,
  type EcoField,
  type EcoForm,
} from '../../lib/economics';
import { fmt, fmtFixed, parseNumber } from '../../lib/format';
import { fmtU, toDisplay, unitLabel } from '../../lib/units';
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
  const T = useT().economics;
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
      <p className="section-sub">{T.intro}</p>
      <details
        className="accordion"
        open={formOpen}
        onToggle={(e) => setFormOpen((e.target as HTMLDetailsElement).open)}
      >
        <summary>
          <span>{T.formSummary(nFilled, form.currency)}</span>
        </summary>
        <div className="accordion-body">
          <OperationForm form={form} onChange={setForm} />
          <label className="check-row">
            <input type="checkbox" checked={useBom} onChange={(e) => setUseBom(e.target.checked)} />
            {T.useBom}
          </label>
        </div>
      </details>
      {!committed && <p className="empty">{T.empty}</p>}
      {q.error && (
        <p className="alert crit" role="alert">
          {q.error.message}
        </p>
      )}
      {r && (
        <>
          <BestSummary r={r} />
          <div className="segmented no-print" role="group" aria-label={T.section}>
            {(['curva', 'comparar'] as const).map((id) => (
              <button
                key={id}
                type="button"
                aria-pressed={view === id}
                onClick={() => {
                  setView(id);
                  saveJson(ECO_VIEW_KEY, id);
                }}
              >
                {T.views[id]}
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
  const T = useT().economics;
  const set = (key: string, text: string) =>
    onChange({ ...form, values: { ...form.values, [key]: text } });
  return (
    <div className="eco-form">
      <div className="eco-row">
        <label className="inline-field">
          {T.currency}
          <input
            aria-label={T.currency}
            value={form.currency}
            maxLength={3}
            size={4}
            onChange={(e) => onChange({ ...form, currency: e.target.value.toUpperCase() })}
          />
        </label>
        <label className="inline-field">
          {T.crew}
          <select
            aria-label={T.crewAria}
            value={form.crewMode}
            onChange={(e) => onChange({ ...form, crewMode: e.target.value as EcoForm['crewMode'] })}
          >
            <option value="share">{T.crewModes.share}</option>
            <option value="wage">{T.crewModes.wage}</option>
            <option value="none">{T.crewModes.none}</option>
          </select>
        </label>
      </div>
      {groups().map((g) => (
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
              <FieldInput
                field={f}
                stored={form.values[f.key]}
                placeholder={
                  f.fallback === undefined
                    ? T.noData
                    : T.byDefault(fmt(f.percent ? f.fallback * 100 : f.fallback))
                }
                onChange={(text) => set(f.key, text)}
              />
              {f.help && <span className="help">{f.help}</span>}
            </label>
          ))}
        </fieldset>
      ))}
    </div>
  );
}

/**
 * Campo numérico del formulario. Los que se convierten (captura, precios por kg y por litro)
 * se escriben en el sistema activo y se guardan en métrico; el texto escrito se conserva aparte
 * para no reescribirlo mientras se tipea.
 */
function FieldInput({
  field,
  stored,
  placeholder,
  onChange,
}: {
  field: EcoField;
  stored: string | undefined;
  placeholder: string;
  onChange: (stored: string) => void;
}) {
  const [text, setText] = useState(() => fieldText(field, stored));
  // Si lo guardado cambia desde afuera (p. ej. se vacía), el campo lo sigue.
  const shown = storedText(field, text) === (stored ?? '') ? text : fieldText(field, stored);
  return (
    <input
      inputMode="decimal"
      aria-label={field.label}
      value={shown}
      placeholder={placeholder}
      onChange={(e) => {
        setText(e.target.value);
        onChange(storedText(field, e.target.value));
      }}
    />
  );
}

function BestSummary({ r }: { r: EconomicsOut }) {
  const T = useT().economics;
  const best: TripEconomics | undefined =
    r.trips.find((t) => t.speed_kn === r.best_margin_kn) ??
    r.trips.find((t) => t.speed_kn === r.least_fuel_kg_kn);
  const missing = Array.from(new Set(r.trips.flatMap((t) => t.missing)));
  return (
    <div data-testid="eco-summary">
      <div className="guide-summary">
        <div>
          <span className="kpi-label">{T.bestSpeed}</span>
          <strong>{r.best_margin_kn === null ? '—' : `${fmtFixed(r.best_margin_kn, 2)} kn`}</strong>
        </div>
        <div>
          <span className="kpi-label">{T.marginTrip}</span>
          <strong>{money(best?.margin, r.currency)}</strong>
        </div>
        <div>
          <span className="kpi-label">{T.costPer(unitLabel('kg'))}</span>
          <strong>
            {best?.cost_per_kg === null || best?.cost_per_kg === undefined
              ? '—'
              : `${fmtFixed(toDisplay(best.cost_per_kg, '$/kg'), 2)} ${r.currency}`}
          </strong>
        </div>
        <div>
          <span className="kpi-label">{T.fuelTrip}</span>
          <strong>{best ? fmtU(best.fuel_l, 'L', { digits: 0 }) : '—'}</strong>
        </div>
        <div>
          <span className="kpi-label">{T.marginYear}</span>
          <strong>{money(r.year.margin, r.currency)}</strong>
        </div>
        <div>
          <span className="kpi-label">{T.breakeven}</span>
          <strong>
            {best?.breakeven_price === null || best?.breakeven_price === undefined
              ? '—'
              : `${fmtFixed(toDisplay(best.breakeven_price, '$/kg'), 2)} ${r.currency}/${unitLabel('kg')}`}
          </strong>
        </div>
      </div>
      {missing.length > 0 && (
        <p className="alert warn" role="status">
          {T.missing(missing.join(', '))} {best?.revenue === null ? '' : T.missingOut}
        </p>
      )}
    </div>
  );
}

function SpeedView({ r }: { r: EconomicsOut }) {
  const T = useT().economics;
  const c = useChartColors();
  const L = unitLabel('L');
  const perKg = unitLabel('kg');
  const rows = curveRows(r.trips);
  const feasible = r.trips.filter((t) => t.feasible).map((t) => t.speed_kn);
  const hasMoney = r.trips.some((t) => t.total_cost !== null);
  const series = hasMoney
    ? [
        { key: 'revenue', name: T.revenue, color: c.s3, width: 2, unit: r.currency },
        { key: 'cost', name: T.cost, color: c.s2, width: 2, unit: r.currency },
        { key: 'margin', name: T.margin, color: c.s1, width: 3, unit: r.currency },
      ]
    : [{ key: 'fuel', name: T.fuelTrip, color: c.s2, width: 2, unit: L }];
  return (
    <>
      <ChartCard
        id="eco-curva"
        title={hasMoney ? T.chartMoney : T.fuelTrip}
        sub={T.chartSub}
        legend={series.map((s) => ({ name: s.name, color: s.color, kind: 'line' as const }))}
      >
        <SpeedLineChart
          rows={rows}
          series={series}
          yUnit={hasMoney ? r.currency : L}
          window={
            feasible.length
              ? { from: Math.min(...feasible), to: Math.max(...feasible), label: T.towable }
              : null
          }
          refX={r.best_margin_kn === null ? null : { x: r.best_margin_kn, label: T.bestMargin }}
          ariaLabel={T.chartAria}
        />
      </ChartCard>
      <div className="table-wrap">
        <table className="data" aria-label={T.table} data-testid="eco-table">
          <thead>
            <tr>
              <th scope="col" className="num">
                v [kn]
              </th>
              <th scope="col">{T.colTows}</th>
              <th scope="col" className="num">
                {T.colFuel} [{L}]
              </th>
              <th scope="col" className="num">
                {T.colCatch} [{perKg}]
              </th>
              <th scope="col" className="num">
                {T.colCost}
              </th>
              <th scope="col" className="num">
                {T.colMargin}
              </th>
              <th scope="col" className="num">
                {T.colCostPer}/{perKg}
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
                    {t.feasible ? T.yes : T.no}
                  </span>
                  {(t.warnings ?? []).length > 0 && (
                    <span className="help"> {(t.warnings ?? []).join('; ')}</span>
                  )}
                </td>
                <td className="num">{fmtFixed(toDisplay(t.fuel_l, 'L'), 0)}</td>
                <td className="num">
                  {t.catch_kg === null ? '—' : fmtFixed(toDisplay(t.catch_kg, 'kg'), 0)}
                </td>
                <td className="num">{t.total_cost === null ? '—' : fmtFixed(t.total_cost, 0)}</td>
                <td className="num">{t.margin === null ? '—' : fmtFixed(t.margin, 0)}</td>
                <td className="num">
                  {t.cost_per_kg === null ? '—' : fmtFixed(toDisplay(t.cost_per_kg, '$/kg'), 2)}
                </td>
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
  const T = useT().economics;
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
        {T.breakdownTitle(fmtFixed(best.speed_kn, 2), money(best.total_cost, r.currency))}
      </h3>
      <div className="eco-bar" role="img" aria-label={T.breakdownAria}>
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
  const T = useT().economics;
  const [alt, setAlt] = useState<string>('');
  const [gear, setGear] = useState('');
  const [request, setRequest] = useState<EconomicsCompareRequest | null>(null);
  const options = catalogs.nets.filter((n) => n.id !== committed?.net);
  const build = (): EconomicsCompareRequest | null => {
    if (!committed || !alt) return null;
    const n = parseNumber(gear);
    return {
      cases: [
        { label: T.current, case: committed },
        {
          label: options.find((o) => o.id === alt)?.name ?? alt,
          case: { ...committed, net: alt, net_modified: null },
          gear_cost: gear.trim() && n !== null ? n : null,
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
          {T.compareWith}
          <select aria-label={T.compareAria} value={alt} onChange={(e) => setAlt(e.target.value)}>
            <option value="">{T.choose}</option>
            {options.map((n) => (
              <option key={n.id} value={n.id}>
                {n.name}
              </option>
            ))}
          </select>
        </label>
        <label className="inline-field">
          {T.newCost(inputs.currency)}
          <input
            aria-label={T.newCostAria}
            inputMode="decimal"
            size={10}
            value={gear}
            onChange={(e) => setGear(e.target.value)}
          />
        </label>
        <button type="button" className="btn" disabled={!alt} onClick={() => setRequest(build())}>
          {T.compute}
        </button>
      </div>
      <p className="help">{T.compareHelp}</p>
      {q.isFetching && <p className="empty">{T.computing}</p>}
      {q.error && (
        <p className="alert crit" role="alert">
          {q.error.message}
        </p>
      )}
      {res && (
        <div className="table-wrap">
          <table className="data" aria-label={T.compareTable}>
            <thead>
              <tr>
                <th scope="col">{T.colNet}</th>
                <th scope="col" className="num">
                  v [kn]
                </th>
                <th scope="col" className="num">
                  {T.colFuelYear} [{unitLabel('L')}]
                </th>
                <th scope="col" className="num">
                  {T.colMarginYear}
                </th>
                <th scope="col" className="num">
                  {T.colSavings}
                </th>
                <th scope="col" className="num">
                  {T.colPayback}
                </th>
              </tr>
            </thead>
            <tbody>
              {res.rows.map((row) => (
                <tr key={row.label} data-compare={row.net_id}>
                  <td>{row.label}</td>
                  <td className="num">{row.trip ? fmtFixed(row.trip.speed_kn, 2) : '—'}</td>
                  <td className="num">
                    {row.annual_fuel_l === null
                      ? '—'
                      : fmtFixed(toDisplay(row.annual_fuel_l, 'L'), 0)}
                  </td>
                  <td className="num">{money(row.annual_margin, res.currency)}</td>
                  <td className="num">{money(row.savings_year, res.currency)}</td>
                  <td className="num">
                    {row.payback_years === null
                      ? '—'
                      : row.payback_years < 1
                        ? T.months(fmtFixed(row.payback_years * 12, 1))
                        : T.years(fmtFixed(row.payback_years, 1))}
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
