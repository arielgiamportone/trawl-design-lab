/** Lotes (Fase 14): flota editable, planilla, tramos, resultados y «abrir este caso». */
import type {
  BatchFile,
  BatchKind,
  BatchParseResponse,
  BatchRunResponse,
  Door,
  NetSpec,
  Vessel,
} from '../api/client';
import { getLang, msg } from '../i18n';
import type { CaseState } from '../state/model';
import { liveRecord } from './liveRecord';
import { toDisplay, unitLabel } from './units';

export const MODE_LABEL: Record<BatchKind, string> = liveRecord(() => msg().batch.mode);

export const STATUS_LABEL: Record<string, string> = liveRecord(() => msg().batch.status);

export type Objective = 'area' | 'energy' | 'cost';

export const OBJECTIVE_LABEL: Record<Objective, string> = liveRecord(() => msg().batch.objective);

/** Un buque de la flota, editable en la vista previa. */
export interface FleetRecord {
  name: string;
  bhp: number;
  length_m?: number | null;
  beam_m?: number | null;
  depth_m?: number | null;
  propeller?: string | null;
  fishing_depth_m?: number | null;
  speed_kn?: number | null;
  region?: string | null;
  seabed?: string | null;
  generic_only?: boolean;
}

interface ParsedVessel {
  vessel: Vessel;
  fishing_depth_m?: number | null;
  speed_kn?: number | null;
  region?: string | null;
  seabed?: string | null;
  generic_only?: boolean;
}

/** Buques de la vista previa (``POST /batch/parse``) como filas editables. */
export function fleetRecords(parsed: BatchParseResponse): FleetRecord[] {
  const vessels = ((parsed.fleet as { vessels?: ParsedVessel[] } | null)?.vessels ?? []) as
    ParsedVessel[] | [];
  return vessels.map((v) => ({
    name: v.vessel.name ?? v.vessel.id,
    bhp: v.vessel.bhp,
    length_m: v.vessel.length_m ?? null,
    beam_m: v.vessel.beam_m ?? null,
    depth_m: v.vessel.depth_m ?? null,
    propeller: v.vessel.propeller ?? null,
    fishing_depth_m: v.fishing_depth_m ?? null,
    speed_kn: v.speed_kn ?? null,
    region: v.region ?? null,
    seabed: v.seabed ?? null,
    generic_only: v.generic_only ?? false,
  }));
}

/**
 * Encabezados de la planilla de flota que se manda a la API: son entradas del motor, así que
 * quedan como los reconoce ``trawlkit.batch.columns`` (en español y en métrico) en los dos idiomas.
 */
const FLEET_HEADERS = [
  'nombre',
  'potencia [hp]',
  'eslora [m]',
  'manga [m]',
  'puntal [m]',
  'hélice',
  'profundidad [m]',
  'velocidad [kn]',
  'región',
  'fondo',
  'sólo genéricos',
];

function cell(v: unknown, sep = ';', comma = true): string {
  if (v === null || v === undefined) return '';
  const s = typeof v === 'number' && comma ? String(v).replace('.', ',') : String(v);
  return s.includes(sep) || /[;"\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/** CSV de la flota (``;`` y coma decimal), con los encabezados que reconoce la API. */
export function fleetCsv(records: FleetRecord[]): string {
  const rows = records.map((r) =>
    [
      r.name,
      r.bhp,
      r.length_m,
      r.beam_m,
      r.depth_m,
      r.propeller,
      r.fishing_depth_m,
      r.speed_kn,
      r.region,
      r.seabed,
      r.generic_only ? 'sí' : '',
    ]
      .map((v) => cell(v))
      .join(';'),
  );
  return [FLEET_HEADERS.join(';'), ...rows].join('\n') + '\n';
}

/** Archivo elegido → ``BatchFile`` (CSV como texto; XLSX en base64). */
export async function toBatchFile(file: File): Promise<BatchFile> {
  if (/\.xlsx?m?$/i.test(file.name)) {
    const bytes = new Uint8Array(await file.arrayBuffer());
    let bin = '';
    for (let i = 0; i < bytes.length; i += 0x8000) {
      bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
    }
    return { filename: file.name, content: btoa(bin), encoding: 'base64' };
  }
  return { filename: file.name, content: await file.text(), encoding: 'text' };
}

/**
 * Buques por tramo: con el motor del teléfono, 10; con el servidor, los que entran en la guarda
 * de costo con 20 % de margen.
 */
export function chunkSize(estimatedS: number, maxS: number, n: number, local: boolean): number {
  if (local) return 10;
  if (n === 0 || estimatedS <= 0) return Math.max(1, n);
  return Math.max(1, Math.min(n, Math.floor((n * 0.8 * maxS) / estimatedS)));
}

export function chunks<T>(items: T[], size: number): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < items.length; i += size) out.push(items.slice(i, i + size));
  return out;
}

export type BatchRow = BatchRunResponse['rows'][number] & {
  index: number;
  name: string;
  status: 'ok' | 'infeasible' | 'error';
  summary: Record<string, unknown>;
  detail?: Record<string, unknown> | null;
  error?: string | null;
  notes?: string[];
};

/** Une los resultados de varios tramos (índices corridos). */
export function mergeResults(parts: BatchRunResponse[]): BatchRunResponse | null {
  if (parts.length === 0) return null;
  const rows: Record<string, unknown>[] = [];
  const counts: Record<string, number> = { ok: 0, infeasible: 0, error: 0 };
  let runtime = 0;
  let runs = 0;
  for (const p of parts) {
    for (const r of p.rows) {
      rows.push({ ...r, index: rows.length });
      const st = String((r as { status: string }).status);
      counts[st] = (counts[st] ?? 0) + 1;
    }
    runtime += p.runtime_s;
    runs += p.engine_runs;
  }
  return {
    ...parts[0]!,
    rows,
    counts,
    issues: parts.flatMap((p) => p.issues),
    runtime_s: runtime,
    engine_runs: runs,
  };
}

function paramText(v: unknown): string {
  if (typeof v === 'boolean') return v ? 'true' : 'false';
  return String(v);
}

/** Caso de una fila de la flota proyectada: red escalada, buque y portón en línea, armado. */
export function openFleetCase(state: CaseState, row: BatchRow): CaseState {
  const detail = row.detail as {
    net: NetSpec;
    summary: { s: number; speed_kn: number };
    case: { vessel: Vessel; door: Door; params: Record<string, unknown> } | null;
  } | null;
  if (!detail?.case) return state;
  const params: Record<string, string> = {};
  for (const [k, v] of Object.entries(detail.case.params)) params[k] = paramText(v);
  return {
    ...state,
    net: String(row.summary.base_net ?? state.net),
    netModified: null,
    edits: { std: {}, mod: {} },
    scaled: { s: detail.summary.s, std: detail.net, mod: null, speed: detail.summary.speed_kn },
    fromBatch: { label: row.name, vessel: detail.case.vessel, door: detail.case.door },
    params,
    targetSpeed: detail.summary.speed_kn,
  };
}

/**
 * Resumen en CSV de las filas del lote, para descargar sin volver a calcular: en español con
 * «;» y coma decimal; en inglés con «,» y punto. Encabezados en el idioma activo y magnitudes en
 * el sistema de unidades activo (las de las columnas).
 */
export function resultsCsv(result: BatchRunResponse, columns: ResultColumn[]): string {
  const T = msg().batch;
  const es = getLang() === 'es';
  const sep = es ? ';' : ',';
  const head = [...T.csvHead, ...columns.map((c) => c.label)];
  const out = (v: unknown) => cell(v, sep, es);
  const rows = (result.rows as BatchRow[]).map((r) =>
    [
      r.index + 1,
      r.name,
      STATUS_LABEL[r.status] ?? r.status,
      ...columns.map((c) => {
        const v = r.summary[c.key];
        if (typeof v === 'boolean') return v ? T.yes : T.no;
        if (Array.isArray(v)) return v.join('; ');
        if (typeof v === 'number') return Math.round(columnValue(c, v) * 1000) / 1000;
        return v ?? (r.status === 'error' && c === columns[0] ? r.error : '');
      }),
    ]
      .map(out)
      .join(sep),
  );
  return [head.map(out).join(sep), ...rows].join('\n') + '\n';
}

/** Columna de resultados: clave del resumen, título (con la unidad activa) y decimales. */
export interface ResultColumn {
  key: string;
  label: string;
  digits?: number;
  /** Unidad métrica del motor; el valor se convierte al sistema activo para mostrarlo. */
  unit?: string;
}

/**
 * Definición de una columna: clave, decimales, unidad métrica y cómo se escribe la unidad en el
 * título («[m]» o «/kg»). ``'m²/h'`` se convierte como superficie (por hora).
 */
type ColumnDef = [key: string, digits?: number, unit?: string, style?: 'per'];

const COLUMN_DEFS: Record<BatchKind, ColumnDef[]> = {
  fleet: [
    ['bhp', 0],
    ['s0', 3],
    ['s', 3],
    ['speed_kn', 2, 'kn'],
    ['headrope_m', 1, 'm'],
    ['demand_kgf', 0, 'kgf'],
    ['area_rate_m2_h', 0, 'm²/h'],
    ['door'],
    ['warp'],
    ['cost', 0],
  ],
  cases: [
    ['net_id'],
    ['vessel_id'],
    ['headrope_m', 1, 'm'],
    ['vertical_opening_m', 2, 'm'],
    ['horizontal_opening_m', 1, 'm'],
    ['rn_std_3kn_kgf', 0, 'kgf'],
    ['max_speed_kn', 2, 'kn'],
    ['warp_selected'],
  ],
  nets: [
    ['panels', 0],
    ['errors', 0],
    ['warnings', 0],
    ['headrope_m', 1, 'm'],
    ['vertical_opening_m', 2, 'm'],
    ['rn_std_3kn_kgf', 0, 'kgf'],
    ['max_speed_kn', 2, 'kn'],
  ],
};

const ECONOMIC_DEFS: ColumnDef[] = [
  ['fuel_l_trip', 0, 'L'],
  ['catch_kg_trip', 0, 'kg'],
  ['cost_per_kg', 2, '$/kg', 'per'],
  ['margin_trip', 0],
  ['margin_year', 0],
];

/** Unidad que se muestra para una unidad del motor (con ``m²/h``, que no está en la tabla). */
function shownUnit(unit: string): string {
  return unit === 'm²/h' ? `${unitLabel('m²')}/h` : unitLabel(unit);
}

/** Valor de una columna en el sistema activo. */
export function columnValue(c: ResultColumn, v: number): number {
  if (!c.unit) return v;
  return c.unit === 'm²/h' ? toDisplay(v, 'm²') : toDisplay(v, c.unit);
}

function buildColumns(defs: ColumnDef[]): ResultColumn[] {
  const labels = msg().batch.col;
  return defs.map(([key, digits, unit, style]) => {
    const text = labels[key] ?? key;
    const col: ResultColumn = { key, label: text };
    if (digits !== undefined) col.digits = digits;
    if (unit) {
      col.unit = unit;
      // «Costo/kg» → «Cost/lb»: la unidad de un precio por unidad es la de la cantidad.
      col.label =
        style === 'per'
          ? `${text}/${shownUnit(unit).replace(/^\$\//, '')}`
          : `${text} [${shownUnit(unit)}]`;
    }
    return col;
  });
}

/** Columnas de la tabla de resultados de un modo, en el idioma y las unidades activos. */
export function resultColumns(mode: BatchKind): ResultColumn[] {
  return buildColumns(COLUMN_DEFS[mode]);
}

/** Columnas económicas de la flota (Fase 16), si se pidió la economía. */
export function economicColumns(): ResultColumn[] {
  return buildColumns(ECONOMIC_DEFS);
}

export const LAST_BATCH_KEY = 'last-batch:v1';

export interface SavedBatch {
  mode: BatchKind;
  records: FleetRecord[];
  file: BatchFile | null;
  result: BatchRunResponse | null;
  at: string;
}
