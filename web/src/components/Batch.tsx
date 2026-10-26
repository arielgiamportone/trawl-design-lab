import { useEffect, useId, useMemo, useRef, useState } from 'react';
import {
  api,
  ApiError,
  type BatchFile,
  type BatchFormat,
  type BatchKind,
  type BatchParseResponse,
  type BatchRunRequest,
  type BatchRunResponse,
} from '../api/client';
import { preferLocal } from '../engine/offline';
import { msg, useT } from '../i18n';
import {
  chunks,
  chunkSize,
  columnValue,
  economicColumns,
  fleetCsv,
  fleetRecords,
  LAST_BATCH_KEY,
  mergeResults,
  MODE_LABEL,
  OBJECTIVE_LABEL,
  openFleetCase,
  resultColumns as columnsOf,
  resultsCsv,
  STATUS_LABEL,
  toBatchFile,
  type BatchRow,
  type FleetRecord,
  type Objective,
  type ResultColumn,
  type SavedBatch,
} from '../lib/batch';
import { loadPrices, REGION_LABEL } from '../lib/components';
import { downloadBlob } from '../lib/download';
import { loadForm, toInputs } from '../lib/economics';
import { fmt, fmtNum, parseNumber } from '../lib/format';
import { idbGet, idbSet } from '../lib/idb';
import { useCase } from '../state/useCase';

interface Issue {
  level: string;
  message: string;
  row?: number | null;
  column?: string | null;
  sheet?: string | null;
}

function errMessage(err: unknown): string {
  if (err instanceof ApiError && err.status)
    return msg().batch.errorStatus(err.status, err.message);
  return err instanceof Error ? err.message : String(err);
}

function cellText(v: unknown, c: ResultColumn): string {
  if (v === null || v === undefined || v === '') return '—';
  if (typeof v === 'boolean') return v ? msg().batch.yes : msg().batch.no;
  if (typeof v === 'number') {
    return fmtNum(columnValue(c, v), { maximumFractionDigits: c.digits ?? 2 });
  }
  return String(v);
}

/**
 * Pestaña «Lotes» (Fase 14): carga una planilla de flota, redes o casos, proyecta una red a cada
 * buque (o calcula los casos o las redes) y descarga los resultados.
 */
export function Batch({ onOpened }: { onOpened?: () => void }) {
  const { state, update, catalogs, committed } = useCase();
  const T = useT().batch;
  const ids = useId();
  const [mode, setMode] = useState<BatchKind>('fleet');
  const [file, setFile] = useState<BatchFile | null>(null);
  const [parsed, setParsed] = useState<BatchParseResponse | null>(null);
  const [records, setRecords] = useState<FleetRecord[]>([]);
  const [net, setNet] = useState<string>('fao_wb_bt2p_60hp');
  const [objective, setObjective] = useState<Objective>('area');
  const [region, setRegion] = useState('');
  const [genericOnly, setGenericOnly] = useState(false);
  const [assemble, setAssemble] = useState(true);
  const [withEconomics, setWithEconomics] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [progress, setProgress] = useState<[number, number] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BatchRunResponse | null>(null);
  const resultColumns =
    mode === 'fleet' &&
    result?.rows.some(
      (r) => (r.summary as Record<string, unknown> | undefined)?.fuel_l_trip !== undefined,
    )
      ? [...columnsOf('fleet'), ...economicColumns()]
      : columnsOf(mode);
  const [filter, setFilter] = useState<'all' | 'ok' | 'infeasible' | 'error'>('all');
  const abort = useRef<AbortController | null>(null);

  // El último lote vuelve al abrir la pestaña (IndexedDB; sin almacenamiento, no pasa nada).
  useEffect(() => {
    let alive = true;
    void idbGet<SavedBatch>(LAST_BATCH_KEY).then((saved) => {
      if (!alive || !saved) return;
      setMode(saved.mode);
      setRecords(saved.records ?? []);
      setFile(saved.file);
      setResult(saved.result);
    });
    return () => {
      alive = false;
    };
  }, []);

  const save = (patch: Partial<SavedBatch>) =>
    void idbSet(LAST_BATCH_KEY, {
      mode,
      records,
      file,
      result,
      at: new Date().toISOString(),
      ...patch,
    } satisfies SavedBatch);

  const reset = (m: BatchKind) => {
    setMode(m);
    setFile(null);
    setParsed(null);
    setRecords([]);
    setResult(null);
    setError(null);
  };

  const template = async (format: 'xlsx' | 'csv') => {
    setError(null);
    try {
      const blob = await api.batchTemplate(mode, format);
      downloadBlob(blob, T.templateFile(T.templateName[mode], format));
    } catch (err) {
      setError(errMessage(err));
    }
  };

  const load = async (f: File) => {
    setError(null);
    setResult(null);
    setBusy(T.reading);
    try {
      const bf = await toBatchFile(f);
      const p = await api.batchParse({ file: bf, mode });
      setFile(bf);
      setParsed(p);
      const recs = mode === 'fleet' ? fleetRecords(p) : [];
      setRecords(recs);
      save({ file: bf, records: recs, result: null });
    } catch (err) {
      setError(errMessage(err));
    } finally {
      setBusy(null);
    }
  };

  const options = (): Omit<BatchRunRequest, 'file'> => ({
    mode,
    net: mode === 'fleet' ? net : null,
    objective,
    margin: 0.1,
    region: region || null,
    generic_only: genericOnly,
    assemble,
    prices: loadPrices(),
    currency: null,
    detail: true,
    economics: withEconomics ? toInputs(loadForm()) : null,
  });

  const run = async () => {
    if (!file && records.length === 0) return;
    setError(null);
    setResult(null);
    const ctrl = new AbortController();
    abort.current = ctrl;
    try {
      const parts: BatchRunResponse[] = [];
      if (mode === 'fleet') {
        const est = parsed?.estimated_s ?? records.length * 2;
        const max = parsed?.max_s ?? 120;
        const size = chunkSize(est * (assemble ? 1 : 0.4), max, records.length, preferLocal());
        const groups = chunks(records, size);
        for (const [i, group] of groups.entries()) {
          setBusy(T.computingRange(i * size + 1, i * size + group.length, records.length));
          setProgress([i * size, records.length]);
          const body = {
            ...options(),
            file: { filename: 'flota.csv', content: fleetCsv(group), encoding: 'text' as const },
          };
          parts.push(await api.batchRun(body, ctrl.signal));
        }
      } else if (file) {
        setBusy(T.computing);
        parts.push(await api.batchRun({ ...options(), file }, ctrl.signal));
      }
      const merged = mergeResults(parts);
      setResult(merged);
      save({ result: merged });
    } catch (err) {
      if (!ctrl.signal.aborted) setError(errMessage(err));
    } finally {
      setBusy(null);
      setProgress(null);
      abort.current = null;
    }
  };

  const exportAs = async (format: BatchFormat) => {
    setError(null);
    const columns = resultColumns;
    if (format === 'csv' && result) {
      downloadBlob(
        new Blob([resultsCsv(result, columns)], { type: 'text/csv' }),
        T.resultsFile('csv'),
      );
      return;
    }
    const bf =
      mode === 'fleet'
        ? { filename: 'flota.csv', content: fleetCsv(records), encoding: 'text' as const }
        : file;
    if (!bf) return;
    setBusy(T.preparing(format.toUpperCase()));
    try {
      const blob = await api.batchExport({ ...options(), file: bf, detail: false }, format);
      if (format === 'html') {
        // Vista de impresión: el navegador la guarda como PDF (también sin conexión).
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank', 'noopener');
        setTimeout(() => URL.revokeObjectURL(url), 60_000);
      } else {
        downloadBlob(blob, T.resultsFile(format));
      }
    } catch (err) {
      setError(errMessage(err));
    } finally {
      setBusy(null);
    }
  };

  const open = (row: BatchRow) => {
    update((s) => openFleetCase(s, row));
    onOpened?.();
  };

  const setRecord = (i: number, patch: Partial<FleetRecord>) =>
    setRecords((rs) => rs.map((r, k) => (k === i ? { ...r, ...patch } : r)));

  const issues = (parsed?.issues ?? []) as unknown as Issue[];
  const rows = useMemo(
    () =>
      ((result?.rows ?? []) as BatchRow[]).filter((r) => filter === 'all' || r.status === filter),
    [result, filter],
  );
  const columns = resultColumns;
  const nets = catalogs.nets.filter((n) => n.status !== 'draft');
  const caseNet = state.scaled ? null : committed?.net;
  const loadedNets = (parsed?.nets ?? []) as { spec: { name: string }; ok: boolean }[];

  return (
    <div className="batch" data-testid="batch">
      <p className="section-sub">{T.intro}</p>
      <div className="segmented" role="group" aria-label={T.whatToLoad}>
        {(Object.keys(MODE_LABEL) as BatchKind[]).map((m) => (
          <button key={m} type="button" aria-pressed={mode === m} onClick={() => reset(m)}>
            {MODE_LABEL[m]}
          </button>
        ))}
      </div>
      <div className="catalog-actions">
        <span className="help">{T.templateHelp}</span>
        <button type="button" className="btn small" onClick={() => void template('xlsx')}>
          {T.templateXlsx}
        </button>
        <button type="button" className="btn small" onClick={() => void template('csv')}>
          {T.csv}
        </button>
      </div>

      <label
        className="dropzone"
        htmlFor={`${ids}-file`}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const f = e.dataTransfer.files[0];
          if (f) void load(f);
        }}
      >
        <span>{T.drop}</span>
        <input
          id={`${ids}-file`}
          type="file"
          accept=".xlsx,.xlsm,.csv,.txt"
          aria-label={T.fileAria}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void load(f);
            e.target.value = '';
          }}
        />
      </label>
      {file && (
        <p className="help">
          {T.sheet} <strong>{file.filename}</strong>
          {parsed ? T.recognized(parsed.size) : ''}
        </p>
      )}

      {issues.length > 0 && (
        <ul className="issues" data-testid="batch-issues">
          {issues.map((i, k) => (
            <li key={k} className={i.level === 'error' ? 'crit' : 'warn'}>
              <span className={`badge ${i.level === 'error' ? 'crit' : 'warn'}`}>
                {i.level === 'error' ? T.levelError : T.levelWarn}
              </span>{' '}
              {[i.sheet, i.row ? T.row(i.row) : '', i.column].filter(Boolean).join(', ')}
              {i.row || i.column || i.sheet ? ': ' : ''}
              {i.message}
            </li>
          ))}
        </ul>
      )}

      {mode === 'fleet' && records.length > 0 && (
        <div className="table-wrap">
          <table className="data" aria-label={T.fleetTable} data-testid="fleet-preview">
            <thead>
              <tr>
                <th scope="col">{T.colVessel}</th>
                <th scope="col" className="num">
                  {T.colPower}
                </th>
                <th scope="col" className="num">
                  {T.colLength}
                </th>
                <th scope="col" className="num">
                  {T.colDepth}
                </th>
                <th scope="col" className="num">
                  {T.colSpeed}
                </th>
                <th scope="col" />
              </tr>
            </thead>
            <tbody>
              {records.map((r, i) => (
                <tr key={i}>
                  <td>
                    <input
                      aria-label={T.vesselName(i + 1)}
                      value={r.name}
                      onChange={(e) => setRecord(i, { name: e.target.value })}
                    />
                  </td>
                  {(['bhp', 'length_m', 'fishing_depth_m', 'speed_kn'] as const).map((k) => (
                    <td key={k} className="num">
                      <input
                        className="price-input"
                        inputMode="decimal"
                        aria-label={T.vesselField(k, i + 1)}
                        defaultValue={r[k] == null ? '' : fmt(r[k] as number)}
                        placeholder={k === 'speed_kn' ? T.best : '—'}
                        onBlur={(e) => {
                          const n = parseNumber(e.target.value);
                          if (k === 'bhp') {
                            if (n !== null && n > 0) setRecord(i, { bhp: n });
                          } else setRecord(i, { [k]: n });
                        }}
                      />
                    </td>
                  ))}
                  <td>
                    <button
                      type="button"
                      className="btn small ghost"
                      aria-label={T.removeVessel(i + 1)}
                      onClick={() => setRecords((rs) => rs.filter((_, k) => k !== i))}
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {mode === 'nets' && loadedNets.length > 0 && (
        <ul className="contrib-list">
          {loadedNets.map((n, k) => (
            <li key={k}>
              <strong>{n.spec.name}</strong>{' '}
              <span className={`badge ${n.ok ? 'good' : 'warn'}`}>
                {n.ok ? T.closes : T.draftReview}
              </span>
            </li>
          ))}
        </ul>
      )}

      {mode === 'fleet' && (
        <div className="catalog-filters">
          <label className="inline-field">
            {T.netToProject}
            <select
              aria-label={T.netToProject}
              value={net}
              onChange={(e) => setNet(e.target.value)}
            >
              {typeof caseNet === 'string' && !nets.some((n) => n.id === caseNet) && (
                <option value={caseNet}>{T.caseNet(caseNet)}</option>
              )}
              {nets.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.name ?? n.id}
                </option>
              ))}
            </select>
          </label>
          <label className="inline-field">
            {T.objectiveLabel}
            <select
              aria-label={T.objectiveAria}
              value={objective}
              onChange={(e) => setObjective(e.target.value as Objective)}
            >
              {Object.entries(OBJECTIVE_LABEL).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
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
          <label className="check">
            <input
              type="checkbox"
              checked={assemble}
              onChange={(e) => setAssemble(e.target.checked)}
            />
            {T.assemble}
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={withEconomics}
              onChange={(e) => setWithEconomics(e.target.checked)}
            />
            {T.withEconomics}
          </label>
        </div>
      )}

      <div className="catalog-actions">
        <button
          type="button"
          className="btn primary"
          disabled={busy !== null || (mode === 'fleet' ? records.length === 0 : !file)}
          onClick={() => void run()}
        >
          {T.run}
        </button>
        {busy && (
          <span role="status" className="help">
            {busy}
          </span>
        )}
        {busy !== null && progress !== null && (
          <button type="button" className="btn small ghost" onClick={() => abort.current?.abort()}>
            {T.cancel}
          </button>
        )}
      </div>
      {progress && (
        <progress
          className="batch-progress"
          max={progress[1]}
          value={progress[0]}
          aria-label={T.progress}
        />
      )}
      {error && (
        <p className="alert crit" role="alert">
          {error}
        </p>
      )}

      {result && (
        <section className="card card-pad" aria-labelledby={`${ids}-res`}>
          <h3 className="section-title" id={`${ids}-res`}>
            <span>
              {T.results(
                result.counts.ok ?? 0,
                result.counts.infeasible ?? 0,
                result.counts.error ?? 0,
              )}
            </span>
          </h3>
          <div className="catalog-actions no-print">
            <div className="segmented" role="group" aria-label={T.filter}>
              {(['all', 'ok', 'infeasible', 'error'] as const).map((f) => (
                <button
                  key={f}
                  type="button"
                  aria-pressed={filter === f}
                  onClick={() => setFilter(f)}
                >
                  {f === 'all' ? T.all : STATUS_LABEL[f]}
                </button>
              ))}
            </div>
            <button type="button" className="btn small" onClick={() => void exportAs('xlsx')}>
              {T.downloadXlsx}
            </button>
            <button type="button" className="btn small" onClick={() => void exportAs('csv')}>
              {T.csv}
            </button>
            {mode === 'fleet' && (
              <>
                <button type="button" className="btn small" onClick={() => void exportAs('pdf')}>
                  {T.pdf}
                </button>
                <button type="button" className="btn small" onClick={() => void exportAs('html')}>
                  {T.printView}
                </button>
              </>
            )}
          </div>
          <div className="table-wrap">
            <table className="data" aria-label={T.resultsTable} data-testid="batch-results">
              <thead>
                <tr>
                  <th scope="col">{T.colName}</th>
                  <th scope="col">{T.colStatus}</th>
                  {columns.map((c) => (
                    <th key={c.key} scope="col" className={c.digits !== undefined ? 'num' : ''}>
                      {c.label}
                    </th>
                  ))}
                  {mode === 'fleet' && <th scope="col" />}
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.index} data-row={r.index}>
                    <td>{r.name}</td>
                    <td>
                      <span
                        className={`badge ${r.status === 'ok' ? 'good' : r.status === 'error' ? 'crit' : 'warn'}`}
                        title={
                          r.error ?? ((r.summary.failed as string[] | undefined) ?? []).join('; ')
                        }
                      >
                        {STATUS_LABEL[r.status]}
                      </span>
                    </td>
                    {r.status === 'error' ? (
                      <td colSpan={columns.length}>{r.error}</td>
                    ) : (
                      columns.map((c) => (
                        <td key={c.key} className={c.digits !== undefined ? 'num' : ''}>
                          {cellText(r.summary[c.key], c)}
                        </td>
                      ))
                    )}
                    {mode === 'fleet' && (
                      <td>
                        {r.detail && (
                          <button type="button" className="btn small" onClick={() => open(r)}>
                            {T.open}
                          </button>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="help">
            {T.runs(result.engine_runs, fmtNum(result.runtime_s, { maximumFractionDigits: 1 }))}
          </p>
        </section>
      )}
    </div>
  );
}
