import { useQuery } from '@tanstack/react-query';
import { useId, useMemo, useState } from 'react';
import { api, ApiError, type ObservationIn, type SensorParseResponse } from '../../api/client';
import { fmtFixed } from '../../lib/format';
import { useT } from '../../i18n';
import { recall, remember } from '../../lib/memo';
import {
  fmtSim,
  fromInput,
  inputStep,
  inputValue,
  resolutionLabel,
  SIM_SPEEDS,
  simUnit,
  simValue,
  speedLabel,
} from '../../lib/simulate';
import { fmtU, getUnits, unitLabel } from '../../lib/units';
import { useChartColors } from '../../lib/theme';
import {
  asCalibration,
  asUncertainty,
  atBound,
  bandPct,
  CAL_PARAMS,
  calibrateRequest,
  DEFAULT_CAL,
  DEFAULT_UNC,
  quantityLabel,
  quantityUnit,
  relativeSpan,
  tornado,
  UNC_FORM_KEY,
  uncertaintyRequest,
  type CalForm,
  type CalParam,
  type UncForm,
  type UncOutput,
} from '../../lib/uncertainty';
import { useCase } from '../../state/useCase';
import { HelpTip } from '../HelpTip';

type Sub = 'bands' | 'calibration';
const SUB_KEY = 'uncertainty:sub';

/** Incertidumbre (bandas P10–P90 y sensibilidad) y calibración con mediciones. */
export function Uncertainty() {
  const [sub, setSubState] = useState<Sub>(() => recall<Sub>(SUB_KEY) ?? 'bands');
  const setSub = (s: Sub) => {
    remember(SUB_KEY, s);
    setSubState(s);
  };
  const T = useT().uncertainty;
  return (
    <div className="uncertainty">
      <div className="segmented" role="group" aria-label={T.subLabel}>
        <button type="button" aria-pressed={sub === 'bands'} onClick={() => setSub('bands')}>
          {T.bands}
        </button>
        <button
          type="button"
          aria-pressed={sub === 'calibration'}
          onClick={() => setSub('calibration')}
        >
          {T.calibration}
        </button>
      </div>
      {sub === 'bands' ? <Bands /> : <Calibration />}
    </div>
  );
}

function ErrorBox({ error }: { error: unknown }) {
  const S = useT().simulate;
  if (!error) return null;
  const e = error as Error;
  return (
    <div className="alert error" role="alert">
      <span>
        <strong>
          {error instanceof ApiError && error.status ? S.errorStatus(error.status) : S.error}:
        </strong>{' '}
        {e.message}
      </span>
    </div>
  );
}

// --- bandas -----------------------------------------------------------------------------------

/** Digitos de una salida según su unidad del motor. */
const outDigits = (unit: string) => (unit === 'kgf' ? 0 : unit === 'L/h' ? 1 : 2);

function Bands() {
  const { committed, state } = useCase();
  const ids = useId();
  const M = useT();
  const T = M.uncertainty;
  const S = M.simulate;
  const [form, setFormState] = useState<UncForm>(
    () =>
      recall<UncForm>(UNC_FORM_KEY) ?? {
        ...DEFAULT_UNC,
        speed: state.targetSpeed,
        catchKg: state.expectedCatchKg || DEFAULT_UNC.catchKg,
        seabed: state.params.seabed || DEFAULT_UNC.seabed,
      },
  );
  const setForm = (patch: Partial<UncForm>) =>
    setFormState((f) => {
      const next = { ...f, ...patch };
      remember(UNC_FORM_KEY, next);
      return next;
    });
  const [submitted, setSubmitted] = useState<string | null>(null);
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
  const query = useQuery({
    queryKey: ['uncertainty', submitted],
    queryFn: ({ signal }) => api.uncertainty(JSON.parse(submitted as string), signal),
    enabled: submitted !== null,
    staleTime: Infinity,
    retry: false,
  });
  const run = () => {
    if (!committed) return;
    const key = JSON.stringify(uncertaintyRequest(committed, form));
    if (key === submitted) void query.refetch();
    else setSubmitted(key);
  };
  const r = query.data ? asUncertainty(query.data) : null;
  const [outKey, setOutKey] = useState<string | null>(null);
  const shown = r?.outputs.find((o) => o.key === outKey) ?? r?.outputs[0];

  return (
    <div className="row-gap">
      <p className="section-sub">{T.bandsIntro}</p>
      <div className="opt-form explore-form" role="group" aria-label={T.scenario}>
        <div className="field">
          <label htmlFor={`${ids}-speed`}>{S.speed} [kn]</label>
          <select
            id={`${ids}-speed`}
            value={form.speed}
            onChange={(e) => setForm({ speed: Number(e.target.value) })}
          >
            {SIM_SPEEDS.map((v) => (
              <option key={v} value={v}>
                {speedLabel(v)}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor={`${ids}-catch`}>
            {S.catchCodend} [{unitLabel('kg')}]
          </label>
          <input
            id={`${ids}-catch`}
            type="number"
            min={0}
            max={inputValue(20000, 'kg', 0)}
            step={inputStep(50, 'kg')}
            value={inputValue(form.catchKg, 'kg')}
            onChange={(e) =>
              setForm({ catchKg: Math.max(0, fromInput(Number(e.target.value) || 0, 'kg')) })
            }
          />
        </div>
        <div className="field">
          <label htmlFor={`${ids}-seabed`}>{S.seabed}</label>
          <select
            id={`${ids}-seabed`}
            value={form.seabed ?? ''}
            onChange={(e) => setForm({ seabed: e.target.value || null })}
          >
            {(seabeds.data ?? []).map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor={`${ids}-n`}>{T.samples}</label>
          <select
            id={`${ids}-n`}
            value={form.samples}
            onChange={(e) => setForm({ samples: Number(e.target.value) })}
          >
            {[6, 10, 16, 24].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor={`${ids}-sp`}>{T.l50Of}</label>
          <select
            id={`${ids}-sp`}
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
        </div>
        <div className="field">
          <label htmlFor={`${ids}-res`}>{S.resolution}</label>
          <select
            id={`${ids}-res`}
            value={form.resolution}
            onChange={(e) => setForm({ resolution: Number(e.target.value) })}
          >
            {[2, 3].map((n) => (
              <option key={n} value={n}>
                {resolutionLabel(n)}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="calc-row">
        <button
          type="button"
          className="btn primary"
          onClick={run}
          disabled={!committed || query.isFetching}
        >
          {T.runBands}
        </button>
      </div>
      <div className="status-line" role="status" aria-live="polite">
        {query.isFetching ? (
          <>
            <span className="spinner" aria-hidden="true" /> {T.runningBands(form.samples)}
          </>
        ) : r ? (
          <span>{T.doneBands(r.n, r.converged, fmtFixed(query.data?.runtime_s ?? 0, 1))}</span>
        ) : null}
      </div>
      <ErrorBox error={query.error} />
      {r && (
        <div className={`row-gap${query.isFetching ? ' stale' : ''}`}>
          <BandTable outputs={r.outputs} selected={shown?.key} onSelect={setOutKey} />
          {shown && <Tornado output={shown} inputs={r.inputs} />}
          <details className="accordion">
            <summary>
              <span>{T.inputRanges}</span>
            </summary>
            <div className="accordion-body table-wrap">
              <table className="data" data-testid="uncertainty-inputs">
                <thead>
                  <tr>
                    <th scope="col">{T.input}</th>
                    <th scope="col">{T.nominal}</th>
                    <th scope="col">{T.range}</th>
                    <th scope="col">{T.source}</th>
                  </tr>
                </thead>
                <tbody>
                  {r.inputs.map((i) => (
                    <tr key={i.name}>
                      <th scope="row">{i.label}</th>
                      <td className="num">{fmtFixed(simValue(i.nominal, i.unit), 3)}</td>
                      <td className="num">
                        {fmtFixed(simValue(i.low, i.unit), 3)} –{' '}
                        {fmtFixed(simValue(i.high, i.unit), 3)} {simUnit(i.unit)}
                      </td>
                      <td>{i.source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </div>
      )}
      {!r && !query.isFetching && !query.error && <p className="empty">{T.emptyBands}</p>}
    </div>
  );
}

function Strip({ o, span }: { o: UncOutput; span: number }) {
  const c = useChartColors();
  const T = useT().uncertainty;
  const ref = o.nominal ?? o.p50;
  const W = 220;
  const H = 22;
  const x = (v: number) => W / 2 + ((100 * (v - ref)) / ref / span) * (W / 2 - 4);
  return (
    <svg
      width={W}
      height={H}
      viewBox={`0 0 ${W} ${H}`}
      className="band-strip"
      role="img"
      aria-label={T.stripAria(
        o.label,
        fmtSim(o.p10, o.unit, { digits: 2, unit: false }),
        fmtSim(o.p90, o.unit, { digits: 2 }),
      )}
    >
      <line x1={4} x2={W - 4} y1={H / 2} y2={H / 2} stroke={c.grid} />
      <line x1={W / 2} x2={W / 2} y1={3} y2={H - 3} stroke={c.axis} strokeDasharray="2 2" />
      <rect
        x={x(o.p10)}
        y={H / 2 - 5}
        width={Math.max(2, x(o.p90) - x(o.p10))}
        height={10}
        rx={3}
        fill={c.s1}
        fillOpacity={0.35}
      />
      {o.values.map((v, k) =>
        v === null ? null : <circle key={k} cx={x(v)} cy={H / 2} r={1.8} fill={c.s1} />,
      )}
      <line
        x1={x(o.p50)}
        x2={x(o.p50)}
        y1={H / 2 - 7}
        y2={H / 2 + 7}
        stroke={c.text}
        strokeWidth={2}
      />
    </svg>
  );
}

function BandTable({
  outputs,
  selected,
  onSelect,
}: {
  outputs: UncOutput[];
  selected?: string;
  onSelect: (k: string) => void;
}) {
  const span = relativeSpan(outputs);
  const T = useT().uncertainty;
  const val = (o: UncOutput, v: number | null) =>
    fmtSim(v, o.unit, { digits: outDigits(o.unit), unit: false });
  return (
    <div className="table-wrap">
      <table className="data" data-testid="uncertainty-table">
        <caption>
          {T.bandCaptionA} <HelpTip topic="p10_p90" label={T.bandCaptionA} /> {T.bandCaptionB(span)}
        </caption>
        <thead>
          <tr>
            <th scope="col">{T.result}</th>
            <th scope="col">{T.nominal}</th>
            <th scope="col">P10</th>
            <th scope="col">P50</th>
            <th scope="col">P90</th>
            <th scope="col">{T.band}</th>
            <th scope="col">{T.spread}</th>
          </tr>
        </thead>
        <tbody>
          {outputs.map((o) => (
            <tr
              key={o.key}
              data-output={o.key}
              className={selected === o.key ? 'selected' : undefined}
            >
              <th scope="row">
                <button type="button" className="link-button" onClick={() => onSelect(o.key)}>
                  {o.label}
                </button>{' '}
                <span className="unit">[{simUnit(o.unit)}]</span>
              </th>
              <td className="num">{val(o, o.nominal)}</td>
              <td className="num">{val(o, o.p10)}</td>
              <td className="num">{val(o, o.p50)}</td>
              <td className="num">{val(o, o.p90)}</td>
              <td className="num">
                {bandPct(o) === null ? '—' : `± ${fmtFixed((bandPct(o) as number) / 2, 1)} %`}
              </td>
              <td>
                <Strip o={o} span={span} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Tornado({ output, inputs }: { output: UncOutput; inputs: Parameters<typeof tornado>[1] }) {
  const c = useChartColors();
  const T = useT().uncertainty;
  const rows = tornado(output, inputs);
  const LABEL = 190;
  const W = 600;
  const rowH = 26;
  const H = rows.length * rowH + 20;
  const half = (W - LABEL - 50) / 2;
  const x0 = LABEL + 25 + half;
  const x = (v: number) => x0 + v * half;
  return (
    <figure className="tornado" data-testid="tornado" style={{ margin: 0 }}>
      <figcaption>
        {T.tornadoTitle(output.label.toLowerCase())}{' '}
        <HelpTip topic="sensitivity" label={T.sensitivity} />
      </figcaption>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="tornado-svg"
        role="img"
        aria-label={T.tornadoAria(
          output.label,
          rows.map((r) => `${r.label} ${fmtFixed(r.rho, 2)}`).join(', '),
        )}
      >
        <line x1={x0} x2={x0} y1={0} y2={H - 16} stroke={c.axis} />
        {rows.map((r, k) => {
          const cy = k * rowH + rowH / 2;
          return (
            <g key={r.name}>
              <text x={LABEL} y={cy + 4} fontSize={12} fill={c.text2} textAnchor="end">
                {r.label}
              </text>
              <rect
                x={Math.min(x0, x(r.rho))}
                y={cy - (rowH - 10) / 2}
                width={Math.max(1, Math.abs(x(r.rho) - x0))}
                height={rowH - 10}
                rx={3}
                fill={r.rho >= 0 ? c.s1 : c.s2}
              />
              <text
                x={r.rho >= 0 ? x(r.rho) + 4 : x(r.rho) - 4}
                y={cy + 4}
                fontSize={11}
                fill={c.muted}
                textAnchor={r.rho >= 0 ? 'start' : 'end'}
              >
                {fmtFixed(r.rho, 2)}
              </text>
            </g>
          );
        })}
        {[-1, 0, 1].map((t) => (
          <text key={t} x={x(t)} y={H - 3} fontSize={10} fill={c.muted} textAnchor="middle">
            {t}
          </text>
        ))}
      </svg>
      <p className="help">{T.tornadoHelp}</p>
    </figure>
  );
}

// --- calibración ------------------------------------------------------------------------------

const CAL_FORM_KEY = 'calibration:form';

function Calibration() {
  const { committed } = useCase();
  const ids = useId();
  const M = useT();
  const T = M.uncertainty;
  const S = M.simulate;
  const [form, setFormState] = useState<CalForm>(
    () => recall<CalForm>(CAL_FORM_KEY) ?? DEFAULT_CAL,
  );
  const setForm = (patch: Partial<CalForm>) =>
    setFormState((f) => {
      const next = { ...f, ...patch };
      remember(CAL_FORM_KEY, next);
      return next;
    });
  const [csv, setCsv] = useState<string>('');
  const [fileName, setFileName] = useState<string | null>(null);
  const [parsed, setParsed] = useState<SensorParseResponse | null>(null);
  const [parseError, setParseError] = useState<unknown>(null);
  const [parsing, setParsing] = useState(false);
  const [submitted, setSubmitted] = useState<string | null>(null);
  const seabeds = useQuery({
    queryKey: ['seabeds'],
    queryFn: ({ signal }) => api.seabeds(signal),
    staleTime: Infinity,
  });
  const query = useQuery({
    queryKey: ['calibrate', submitted],
    queryFn: ({ signal }) => api.calibrate(JSON.parse(submitted as string), signal),
    enabled: submitted !== null,
    staleTime: Infinity,
    retry: false,
  });
  const readLog = async (text: string) => {
    setParsing(true);
    setParseError(null);
    try {
      setParsed(await api.parseSensors({ csv: text, by: form.by, width: form.width, min_rows: 5 }));
    } catch (e) {
      setParsed(null);
      setParseError(e);
    } finally {
      setParsing(false);
    }
  };
  const loadExample = async () => {
    try {
      const text = await api.sensorExample();
      setCsv(text);
      setFileName(T.exampleName);
      await readLog(text);
    } catch (e) {
      setParseError(e);
    }
  };
  const onFile = async (f: File | undefined) => {
    if (!f) return;
    const text = await f.text();
    setCsv(text);
    setFileName(f.name);
    await readLog(text);
  };
  const observations = useMemo(() => (parsed?.observations ?? []) as ObservationIn[], [parsed]);
  const canRun =
    !!committed &&
    !query.isFetching &&
    form.params.length > 0 &&
    (form.source === 'dynamit' || observations.length > 0);
  const run = () => {
    if (!committed) return;
    const key = JSON.stringify(calibrateRequest(committed, form, observations));
    if (key === submitted) void query.refetch();
    else setSubmitted(key);
  };
  const r = query.data ? asCalibration(query.data) : null;
  const toggle = (p: CalParam) =>
    setForm({
      params: form.params.includes(p)
        ? form.params.filter((x) => x !== p)
        : [...form.params, p].slice(-3),
    });

  return (
    <div className="row-gap">
      <p className="section-sub">
        {T.calIntro} <HelpTip topic="calibration" label={T.calHelpTopic} />
      </p>
      <div className="segmented" role="group" aria-label={T.sourceLabel}>
        <button
          type="button"
          aria-pressed={form.source === 'sensors'}
          onClick={() => setForm({ source: 'sensors' })}
        >
          {T.sensors}
        </button>
        <button
          type="button"
          aria-pressed={form.source === 'dynamit'}
          onClick={() => setForm({ source: 'dynamit' })}
        >
          {T.dynamit}
        </button>
      </div>
      {form.source === 'sensors' && (
        <div className="sensor-box">
          <div className="opt-form explore-form" role="group" aria-label={T.sensorLog}>
            <div className="field">
              <label htmlFor={`${ids}-file`}>
                {T.csvFile} <HelpTip topic="sensor_log" label={T.sensorLog} />
              </label>
              <input
                id={`${ids}-file`}
                type="file"
                accept=".csv,.txt,text/csv"
                onChange={(e) => void onFile(e.target.files?.[0])}
              />
              {fileName && <span className="help">{fileName}</span>}
            </div>
            <div className="field">
              <label htmlFor={`${ids}-by`}>{T.windowsBy}</label>
              <select
                id={`${ids}-by`}
                value={form.by}
                onChange={(e) => {
                  const by = e.target.value as CalForm['by'];
                  setForm({ by, width: by === 'time' ? 20 : 0.25 });
                }}
              >
                <option value="time">{T.time}</option>
                <option value="speed">{T.speed}</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor={`${ids}-width`}>{T.width(form.by === 'time' ? 'min' : 'kn')}</label>
              <input
                id={`${ids}-width`}
                type="number"
                min={form.by === 'time' ? 1 : 0.05}
                step={form.by === 'time' ? 1 : 0.05}
                value={form.width}
                onChange={(e) => setForm({ width: Math.max(0.05, Number(e.target.value) || 0) })}
              />
            </div>
            <div className="field">
              <label htmlFor={`${ids}-seabed`}>{T.haulSeabed}</label>
              <select
                id={`${ids}-seabed`}
                value={form.seabed ?? ''}
                onChange={(e) => setForm({ seabed: e.target.value || null })}
              >
                {(seabeds.data ?? []).map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="calc-row">
            <button type="button" className="btn" onClick={() => void loadExample()}>
              {T.useExample}
            </button>
            <button
              type="button"
              className="btn"
              onClick={() => void readLog(csv)}
              disabled={!csv || parsing}
            >
              {T.reread}
            </button>
          </div>
          {parsing && (
            <p className="status-line">
              <span className="spinner" aria-hidden="true" /> {T.reading}
            </p>
          )}
          <ErrorBox error={parseError} />
          {parsed && <SensorSummary parsed={parsed} />}
        </div>
      )}
      <fieldset className="field">
        <legend className="label">{T.paramsLegend}</legend>
        <div className="check-grid">
          {CAL_PARAMS.map((p) => (
            <label key={p.id} title={p.help}>
              <input
                type="checkbox"
                checked={form.params.includes(p.id)}
                onChange={() => toggle(p.id)}
              />{' '}
              {p.label}
            </label>
          ))}
        </div>
      </fieldset>
      <div className="opt-form explore-form" role="group" aria-label={T.fitLabel}>
        <div className="field">
          <label htmlFor={`${ids}-evals`}>{T.maxEvals}</label>
          <select
            id={`${ids}-evals`}
            value={form.maxEvals}
            onChange={(e) => setForm({ maxEvals: Number(e.target.value) })}
          >
            {[6, 12, 20, 30].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor={`${ids}-cres`}>{S.resolution}</label>
          <select
            id={`${ids}-cres`}
            value={form.resolution}
            onChange={(e) => setForm({ resolution: Number(e.target.value) })}
          >
            {[2, 3].map((n) => (
              <option key={n} value={n}>
                {resolutionLabel(n)}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="calc-row">
        <button type="button" className="btn primary" onClick={run} disabled={!canRun}>
          {T.calibrate}
        </button>
      </div>
      <div className="status-line" role="status" aria-live="polite">
        {query.isFetching ? (
          <>
            <span className="spinner" aria-hidden="true" /> {T.fitting(form.maxEvals)}
          </>
        ) : r ? (
          <span>{T.doneCal(r.evaluations, fmtFixed(r.runtime_s, 1))}</span>
        ) : null}
      </div>
      <ErrorBox error={query.error} />
      {r && (
        <div className={`row-gap${query.isFetching ? ' stale' : ''}`}>
          <div className="impact">
            <div
              className={`impact-item ${r.rmse_after_pct < r.rmse_before_pct ? 'good' : 'neutral'}`}
            >
              <span className="impact-label">{T.rmse}</span>
              <span className="impact-value">
                {fmtFixed(r.rmse_before_pct, 1)} → {fmtFixed(r.rmse_after_pct, 1)}{' '}
                <span className="unit">%</span>
              </span>
              <span className="impact-delta">{T.beforeAfter}</span>
            </div>
          </div>
          <div className="table-wrap">
            <table className="data" data-testid="calibration-params">
              <caption>{T.fittedParams}</caption>
              <thead>
                <tr>
                  <th scope="col">{T.param}</th>
                  <th scope="col">{T.initial}</th>
                  <th scope="col">{T.fitted}</th>
                  <th scope="col">{T.range}</th>
                </tr>
              </thead>
              <tbody>
                {r.params.map((p) => (
                  <tr key={p.name}>
                    <th scope="row">{p.label}</th>
                    <td className="num">{fmtFixed(p.initial, 3)}</td>
                    <td className="num">
                      <strong>{fmtFixed(p.fitted, 3)}</strong>
                      {p.std !== null && ` ± ${fmtFixed(p.std, 3)}`}
                      {atBound(p) && (
                        <span className="badge warn" title={T.atLimitTitle}>
                          {T.atLimit}
                        </span>
                      )}
                    </td>
                    <td className="num">
                      {fmtFixed(p.low, 2)} – {fmtFixed(p.high, 2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="table-wrap">
            <table className="data" data-testid="calibration-observations">
              <caption>{T.obsCaption}</caption>
              <thead>
                <tr>
                  <th scope="col">{T.quantity}</th>
                  <th scope="col">{T.speedCatch}</th>
                  <th scope="col">{T.measured}</th>
                  <th scope="col">{T.before}</th>
                  <th scope="col">{T.after}</th>
                </tr>
              </thead>
              <tbody>
                {r.observations.map((o, k) => (
                  <tr key={k}>
                    <th scope="row">
                      {o.label} <span className="unit">[{simUnit(o.unit)}]</span>
                    </th>
                    <td className="num">
                      {fmtFixed(o.speed_kn, 2)} kn · {fmtU(o.catch_kg, 'kg')}
                    </td>
                    <td className="num">{obs(o.value, o.unit)}</td>
                    <td className="num">
                      {obs(o.before, o.unit)}{' '}
                      <span className="unit">({signed(o.error_before_pct)} %)</span>
                    </td>
                    <td className="num">
                      {obs(o.after, o.unit)}{' '}
                      <span className="unit">({signed(o.error_after_pct)} %)</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="help">{T.calHelp}</p>
        </div>
      )}
    </div>
  );
}

const signed = (v: number) => `${v > 0 ? '+' : ''}${fmtFixed(v, 1)}`;
const obs = (v: number, unit: string) =>
  fmtSim(v, unit, { digits: unit === 'kgf' ? 0 : 2, unit: false });

function SensorSummary({ parsed }: { parsed: SensorParseResponse }) {
  const T = useT().uncertainty;
  const log = parsed.log as {
    mapping: Record<string, string>;
    ignored: string[];
    rows: number;
    warnings: string[];
  };
  const ws = parsed.windows as {
    speed_kn: number;
    catch_kg: number;
    n: number;
    values: Record<string, number>;
  }[];
  const qs = [...new Set(ws.flatMap((w) => Object.keys(w.values)))];
  return (
    <div className="row-gap" data-testid="sensor-summary">
      <p className="help">
        {T.rows(log.rows)} · {T.recognised}{' '}
        {Object.entries(log.mapping)
          .map(([h, q]) => `«${h}» → ${q}`)
          .join(' · ')}
        {log.ignored.length > 0 && T.ignored(log.ignored.join(', '))}
        {log.warnings.map((w) => ` · ${w}`)}
      </p>
      <div className="table-wrap">
        <table className="data">
          <caption>{T.windowsCaption}</caption>
          <thead>
            <tr>
              <th scope="col">{T.speed}</th>
              <th scope="col">{T.catch}</th>
              <th scope="col">{T.rowsCol}</th>
              {qs.map((q) => (
                <th scope="col" key={q}>
                  {quantityLabel(q)}
                  {getUnits() === 'imperial' && quantityUnit(q)
                    ? ` [${unitLabel(quantityUnit(q))}]`
                    : ''}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ws.map((w, k) => (
              <tr key={k}>
                <td className="num">{fmtFixed(w.speed_kn, 2)} kn</td>
                <td className="num">{fmtU(w.catch_kg, 'kg')}</td>
                <td className="num">{w.n}</td>
                {qs.map((q) => (
                  <td className="num" key={q}>
                    {fmtSim(w.values[q], quantityUnit(q), { digits: 2, unit: false })}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
