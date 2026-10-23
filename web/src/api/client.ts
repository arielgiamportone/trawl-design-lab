/** Cliente HTTP tipado para la API trawlkit (contrato en ../../openapi.json). */
import type { components } from './schema';

type S = components['schemas'];
export type CatalogItem = S['CatalogItem'];
export type NetSpec = S['NetSpec'];
export type Panel = S['Panel'];
export type Vessel = S['Vessel'];
export type Door = S['Door'];
export type ParamInfo = S['ParamInfo'];
export type Erratum = S['ErratumOut'];
export type Health = S['Health'];
export type DesignRequest = S['DesignRequest'];
export type DesignResponseRaw = S['DesignResponse'];
export type OptimizeRequest = S['OptimizeRequest'];
export type OptimizeResponse = S['OptimizeResponse'];
export type Evaluation = S['EvaluationOut'];
export type ConstraintOut = S['ConstraintOut'];
export type ScaledNetRequest = S['ScaledNetRequest'];
export type SimulateRequest = S['SimulateRequest'];
export type SimulateResponse = S['SimulateResponse'];
export type DynamitRow = S['DynamitRow'];
export type SimEngineRow = S['SimEngineRow'];
export type PlanView = 'sheet' | 'scale';
export type Variant = 'std' | 'mod';
export type ReportFormat = 'html' | 'pdf' | 'xlsx';
export type LayoutMode = 'schematic' | 'true_scale';
export type ScenarioIn = S['ScenarioIn'];
export type SeabedOut = S['SeabedOut'];
export type HaulRequest = S['HaulRequest'];
export type HaulResponse = S['HaulResponse'];
export type LayoutResponse = S['LayoutResponse'];

const DEFAULT_BASE = 'http://127.0.0.1:8000';

/** URL base de la API: ``VITE_API_URL`` o ``http://127.0.0.1:8000`` (sin barra final). */
export function apiBase(): string {
  const env = import.meta.env.VITE_API_URL as string | undefined;
  return (env && env.trim() ? env.trim() : DEFAULT_BASE).replace(/\/+$/, '');
}

/** Error HTTP de la API con el ``detail`` ya convertido a texto legible. */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;
  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

interface ValidationItem {
  loc?: (string | number)[];
  msg?: string;
}

/** Convierte el ``detail`` de FastAPI (texto o lista de errores de validación) en un mensaje. */
export function detailMessage(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: ValidationItem) => {
        const loc = (d.loc ?? []).filter((p) => p !== 'body').join('.');
        return loc ? `${loc}: ${d.msg ?? ''}` : (d.msg ?? '');
      })
      .join('; ');
  }
  if (detail == null) return '';
  return JSON.stringify(detail);
}

/**
 * Mensaje cuando la API no conoce la ruta (404 genérico de FastAPI, ``detail = "Not Found"``): la
 * API en línea es anterior a esta versión de la app. Un 404 con otro ``detail`` (p. ej. «red
 * desconocida») es un error de datos y se muestra tal cual.
 */
export const MISSING_ROUTE_MESSAGE =
  'La API en línea es anterior a esta versión de la app y todavía no tiene esta función. ' +
  'Se actualiza sola unos minutos después de cada cambio; si persiste, hay que redesplegarla ' +
  '(Render → Manual Deploy → Deploy latest commit).';

export function isMissingRoute(detail: unknown): boolean {
  return detail === undefined || detail === 'Not Found';
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(`${apiBase()}${path}`, init);
  } catch (err) {
    throw new ApiError(0, `No se pudo conectar con la API (${apiBase()}): ${String(err)}`);
  }
  if (!res.ok) {
    let detail: unknown;
    try {
      const body = (await res.json()) as { detail?: unknown };
      detail = body.detail;
    } catch {
      detail = undefined;
    }
    const msg =
      res.status === 404 && isMissingRoute(detail)
        ? MISSING_ROUTE_MESSAGE
        : detailMessage(detail) || `${res.status} ${res.statusText}`;
    throw new ApiError(res.status, msg, detail);
  }
  return res;
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await request(path, { signal });
  return (await res.json()) as T;
}

function post(path: string, body: unknown, signal?: AbortSignal): Promise<Response> {
  return request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
}

export const api = {
  health: (signal?: AbortSignal) => getJson<Health>('/health', signal),
  nets: (signal?: AbortSignal) => getJson<CatalogItem[]>('/catalog/nets', signal),
  net: (id: string, signal?: AbortSignal) =>
    getJson<NetSpec>(`/catalog/nets/${encodeURIComponent(id)}`, signal),
  vessels: (signal?: AbortSignal) => getJson<Vessel[]>('/catalog/vessels', signal),
  doors: (signal?: AbortSignal) => getJson<Door[]>('/catalog/doors', signal),
  params: (signal?: AbortSignal) => getJson<ParamInfo[]>('/params', signal),
  errata: (signal?: AbortSignal) => getJson<Erratum[]>('/errata', signal),
  async design(req: DesignRequest, signal?: AbortSignal): Promise<DesignResponseRaw> {
    const res = await post('/design', req, signal);
    return (await res.json()) as DesignResponseRaw;
  },
  async plan(
    req: DesignRequest,
    view: PlanView,
    variant: Variant,
    signal?: AbortSignal,
  ): Promise<string> {
    const res = await post(`/design/plan?view=${view}&variant=${variant}`, req, signal);
    return res.text();
  },
  async layout(
    req: DesignRequest,
    variant: Variant = 'std',
    mode: LayoutMode = 'schematic',
    signal?: AbortSignal,
  ): Promise<LayoutResponse> {
    const res = await post(`/design/layout?variant=${variant}&mode=${mode}`, req, signal);
    return (await res.json()) as LayoutResponse;
  },
  async report(req: DesignRequest, format: ReportFormat, signal?: AbortSignal): Promise<Blob> {
    const res = await post(`/design/report?format=${format}`, req, signal);
    return res.blob();
  },
  async optimize(req: OptimizeRequest, signal?: AbortSignal): Promise<OptimizeResponse> {
    const res = await post('/optimize', req, signal);
    return (await res.json()) as OptimizeResponse;
  },
  async scaledNet(req: ScaledNetRequest, signal?: AbortSignal): Promise<NetSpec> {
    const res = await post('/optimize/scaled-net', req, signal);
    return (await res.json()) as NetSpec;
  },
  seabeds: (signal?: AbortSignal) => getJson<SeabedOut[]>('/catalog/seabeds', signal),
  async haul(req: HaulRequest, signal?: AbortSignal): Promise<HaulResponse> {
    const res = await post('/simulate/haul', req, signal);
    return (await res.json()) as HaulResponse;
  },
  async simulate(req: SimulateRequest, signal?: AbortSignal): Promise<SimulateResponse> {
    const res = await post('/simulate', req, signal);
    return (await res.json()) as SimulateResponse;
  },
};
