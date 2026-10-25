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
import type { CaseState } from '../state/model';

export const MODE_LABEL: Record<BatchKind, string> = {
  fleet: 'Flota de buques',
  nets: 'Redes (planos)',
  cases: 'Casos completos',
};

export const STATUS_LABEL: Record<string, string> = {
  ok: 'cumple',
  infeasible: 'no cumple',
  error: 'error',
};

export const OBJECTIVE_LABEL = {
  area: 'La mayor red que el buque remolca',
  energy: 'Menos trabajo por m² barrido',
  cost: 'Armado más barato (con precios)',
} as const;

export type Objective = keyof typeof OBJECTIVE_LABEL;

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

function cell(v: unknown): string {
  if (v === null || v === undefined) return '';
  const s = typeof v === 'number' ? String(v).replace('.', ',') : String(v);
  return /[;"\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
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
      .map(cell)
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

/** Resumen en CSV (``;``) de las filas del lote, para descargar sin volver a calcular. */
export function resultsCsv(
  result: BatchRunResponse,
  columns: { key: string; label: string }[],
): string {
  const head = ['Fila', 'Nombre', 'Estado', ...columns.map((c) => c.label)];
  const rows = (result.rows as BatchRow[]).map((r) =>
    [
      r.index + 1,
      r.name,
      STATUS_LABEL[r.status] ?? r.status,
      ...columns.map((c) => {
        const v = r.summary[c.key];
        if (typeof v === 'boolean') return v ? 'sí' : 'no';
        if (Array.isArray(v)) return v.join('; ');
        if (typeof v === 'number') return Math.round(v * 1000) / 1000;
        return v ?? (r.status === 'error' && c === columns[0] ? r.error : '');
      }),
    ]
      .map(cell)
      .join(';'),
  );
  return [head.map(cell).join(';'), ...rows].join('\n') + '\n';
}

/** Columnas de la tabla de resultados por modo. */
export const RESULT_COLUMNS: Record<BatchKind, { key: string; label: string; digits?: number }[]> =
  {
    fleet: [
      { key: 'bhp', label: 'hp', digits: 0 },
      { key: 's0', label: 'Escala por semejanza', digits: 3 },
      { key: 's', label: 'Escala', digits: 3 },
      { key: 'speed_kn', label: 'v [kn]', digits: 2 },
      { key: 'headrope_m', label: 'Lima [m]', digits: 1 },
      { key: 'demand_kgf', label: 'R_T [kgf]', digits: 0 },
      { key: 'area_rate_m2_h', label: 'Área [m²/h]', digits: 0 },
      { key: 'door', label: 'Portón' },
      { key: 'warp', label: 'Cable' },
      { key: 'cost', label: 'Costo', digits: 0 },
    ],
    cases: [
      { key: 'net_id', label: 'Red' },
      { key: 'vessel_id', label: 'Buque' },
      { key: 'headrope_m', label: 'Lima [m]', digits: 1 },
      { key: 'vertical_opening_m', label: 'AV [m]', digits: 2 },
      { key: 'horizontal_opening_m', label: 'AH [m]', digits: 1 },
      { key: 'rn_std_3kn_kgf', label: 'R_N 3 kn [kgf]', digits: 0 },
      { key: 'max_speed_kn', label: 'v máx. [kn]', digits: 2 },
      { key: 'warp_selected', label: 'Cable' },
    ],
    nets: [
      { key: 'panels', label: 'Paneles', digits: 0 },
      { key: 'errors', label: 'Errores', digits: 0 },
      { key: 'warnings', label: 'Avisos', digits: 0 },
      { key: 'headrope_m', label: 'Lima [m]', digits: 1 },
      { key: 'vertical_opening_m', label: 'AV [m]', digits: 2 },
      { key: 'rn_std_3kn_kgf', label: 'R_N 3 kn [kgf]', digits: 0 },
      { key: 'max_speed_kn', label: 'v máx. [kn]', digits: 2 },
    ],
  };

export const LAST_BATCH_KEY = 'last-batch:v1';

export interface SavedBatch {
  mode: BatchKind;
  records: FleetRecord[];
  file: BatchFile | null;
  result: BatchRunResponse | null;
  at: string;
}
