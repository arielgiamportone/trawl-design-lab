/** Cliente HTTP tipado para la API trawlkit (contrato en ../../openapi.json). */
import { isPrepared, localRequest, preferLocal } from '../engine/offline';
import { catalog, getLang, msg, type Lang } from '../i18n';
import type { Component } from '../lib/components';

/** Ficha de ``GET /catalog/components/{kind}/{id}``: el componente, observaciones y genérico. */
export type ComponentDetail = Component & {
  issues?: { level: 'error' | 'warning'; code: string; message: string }[];
  generic?: Component | null;
};
import type { components } from './schema';

type S = components['schemas'];
export type CatalogItem = S['CatalogItem'];
export type ProvenanceRow = S['ProvenanceRow'];
export type NetCheck = S['NetCheckOut'];
export type NetSpec = S['NetSpec'];
export type Panel = S['Panel'];
export type Vessel = S['Vessel'];
export type Door = S['Door'];
export type ParamInfo = S['ParamInfo'];
export type Erratum = S['ErratumOut'];
export type Health = S['Health'];
export type PriceParseRequest = S['PriceParseRequest'];
export type PriceParseResponse = S['PriceParseResponse'];
export type PriceExportRequest = S['PriceExportRequest'];
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
export type ExploreRequest = S['ExploreRequest'];
export type ExploreResponse = S['ExploreResponse'];
export type FoulingOut = S['FoulingOut'];
export type LayoutResponse = S['LayoutResponse'];
export type SpeciesOut = S['SpeciesOut'];
export type CodendVariant = S['CodendVariant'];
export type SelectivityRequest = S['SelectivityRequest'];
export type SelectivityResponse = S['SelectivityResponse'];
export type UncertaintyRequest = S['UncertaintyRequest'];
export type UncertaintyResponse = S['UncertaintyResponse'];
export type CalibrateRequest = S['CalibrateRequest'];
export type CalibrateResponse = S['CalibrateResponse'];
export type ObservationIn = S['ObservationIn'];
export type SensorParseRequest = S['SensorParseRequest'];
export type SensorParseResponse = S['SensorParseResponse'];
export type ComponentKindOut = S['ComponentKindOut'];
export type ComponentCheckOut = S['ComponentCheckOut'];
export type BomRequest = S['BomRequest'];
export type BomOut = S['BomOut'];
export type ConstructionGuide = S['ConstructionGuideOut'];
export type GuideJoin = S['JoinOut'];
export type GuidePiece = S['CutPieceOut'];
export type GuideFormat = 'html' | 'pdf' | 'xlsx';
export type EconomicInputs = S['EconomicInputsIn'];
export type EconomicsRequest = S['EconomicsRequest'];
export type EconomicsOut = S['EconomicsOut'];
export type TripEconomics = S['TripEconomicsOut'];
export type EconomicsCompareRequest = S['EconomicsCompareRequest'];
export type EconomicsCompareOut = S['EconomicsCompareOut'];
export type ComponentOptimizeRequest = S['ComponentOptimizeRequest'];
export type ComponentOptimizeResponse = S['ComponentOptimizeResponse'];
export type AssemblyOut = S['AssemblyOut'];
export type DoorSelectRequest = S['DoorSelectRequest'];
export type DoorSelectResponse = S['DoorSelectResponse'];
export type DoorCandidateOut = S['DoorCandidateOut'];
export type DoorTypePolar = S['DoorTypePolarOut'];
export type BatchFile = S['BatchFile'];
export type BatchParseRequest = S['BatchParseRequest'];
export type BatchParseResponse = S['BatchParseResponse'];
export type BatchRunRequest = S['BatchRunRequest'];
export type BatchRunResponse = S['BatchRunResponse'];
export type BatchFormat = 'csv' | 'xlsx' | 'pdf' | 'html';
export type BatchKind = 'fleet' | 'nets' | 'cases';
export type ExerciseSummary = S['ExerciseSummaryOut'];
export type ExerciseInstance = S['ExerciseInstanceOut'];
export type ExerciseGrade = S['GradeOut'];
export type LabSummary = S['LabSummaryOut'];
export type Lab = S['LabOut'];
export type LabStep = S['LabStepOut'];
export type LabStepResult = S['LabStepResultOut'];
export type LabCheckRequest = S['LabCheckRequest'];

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
export function missingRouteMessage(): string {
  return msg().api.missingRoute;
}

/** @deprecated Texto en español; use ``missingRouteMessage()`` (idioma activo). */
export const MISSING_ROUTE_MESSAGE = catalog('es').api.missingRoute;

export function isMissingRoute(detail: unknown): boolean {
  return detail === undefined || detail === 'Not Found';
}

/** Pedido al motor del teléfono (sin conexión): mismo contrato que la API. */
async function localFetch(path: string, init?: RequestInit): Promise<Response> {
  const body = typeof init?.body === 'string' ? init.body : null;
  return localRequest(init?.method ?? 'GET', path, body, init?.signal ?? undefined);
}

/** Error de la API a partir de una respuesta no exitosa. */
async function errorOf(res: Response): Promise<ApiError> {
  let detail: unknown;
  try {
    const body = (await res.json()) as { detail?: unknown };
    detail = body.detail;
  } catch {
    detail = undefined;
  }
  const msg =
    res.status === 404 && isMissingRoute(detail)
      ? missingRouteMessage()
      : detailMessage(detail) || `${res.status} ${res.statusText}`;
  return new ApiError(res.status, msg, detail);
}

/**
 * Agrega el idioma de la interfaz al pedido (``?lang=en``) para que la API y el motor del
 * teléfono respondan los textos en ese idioma. El español es el idioma por defecto del motor.
 */
export function withLang(path: string, lang: Lang = getLang()): string {
  if (lang === 'es') return path;
  return `${path}${path.includes('?') ? '&' : '?'}lang=${lang}`;
}

async function request(rawPath: string, init?: RequestInit): Promise<Response> {
  const path = withLang(rawPath);
  let res: Response;
  if (preferLocal()) {
    res = await localFetch(path, init);
  } else {
    try {
      res = await fetch(`${apiBase()}${path}`, init);
    } catch (err) {
      if (init?.signal?.aborted || !isPrepared()) {
        throw new ApiError(0, msg().api.cannotConnect(apiBase(), String(err)));
      }
      // Sin red: el motor del teléfono atiende el pedido.
      res = await localFetch(path, init);
    }
  }
  if (!res.ok) throw await errorOf(res);
  return res;
}

/**
 * Pedido al aula (``/classroom``): sólo en línea, con el token de la sesión. Sin conexión no hay
 * motor local que lo atienda.
 */
export async function classroomRequest(
  path: string,
  token: string | null,
  init: { method?: string; body?: unknown; signal?: AbortSignal } = {},
): Promise<Response> {
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (init.body !== undefined) headers['Content-Type'] = 'application/json';
  let res: Response;
  try {
    res = await fetch(`${apiBase()}/classroom${withLang(path)}`, {
      method: init.method ?? 'GET',
      headers,
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
      signal: init.signal,
    });
  } catch (err) {
    throw new ApiError(0, msg().api.classroomOffline(apiBase(), String(err)));
  }
  if (!res.ok) throw await errorOf(res);
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
  netProvenance: (id: string, signal?: AbortSignal) =>
    getJson<ProvenanceRow[]>(`/catalog/nets/${encodeURIComponent(id)}/provenance`, signal),
  netCheck: (id: string, signal?: AbortSignal) =>
    getJson<NetCheck>(`/catalog/nets/${encodeURIComponent(id)}/check`, signal),
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
  componentKinds: (signal?: AbortSignal) =>
    getJson<ComponentKindOut[]>('/catalog/components', signal),
  components: (kind: string, signal?: AbortSignal) =>
    getJson<Component[]>(`/catalog/components/${encodeURIComponent(kind)}`, signal),
  component: (kind: string, id: string, signal?: AbortSignal) =>
    getJson<ComponentDetail>(
      `/catalog/components/${encodeURIComponent(kind)}/${encodeURIComponent(id)}`,
      signal,
    ),
  async checkComponent(item: Record<string, unknown>, signal?: AbortSignal) {
    const res = await post('/components/check', item, signal);
    return (await res.json()) as ComponentCheckOut;
  },
  async bom(req: BomRequest, signal?: AbortSignal): Promise<BomOut> {
    const res = await post('/design/bom', req, signal);
    return (await res.json()) as BomOut;
  },
  async construction(
    req: DesignRequest,
    variant: Variant,
    eyeAllowanceM: number,
    signal?: AbortSignal,
  ): Promise<ConstructionGuide> {
    const res = await post(
      `/design/construction?variant=${variant}&eye_allowance_m=${eyeAllowanceM}`,
      req,
      signal,
    );
    return (await res.json()) as ConstructionGuide;
  },
  async constructionExport(
    req: DesignRequest,
    format: GuideFormat,
    variant: Variant,
    eyeAllowanceM: number,
    signal?: AbortSignal,
  ): Promise<Blob> {
    const res = await post(
      `/design/construction/export?format=${format}&variant=${variant}&eye_allowance_m=${eyeAllowanceM}`,
      req,
      signal,
    );
    return res.blob();
  },
  async economics(req: EconomicsRequest, signal?: AbortSignal): Promise<EconomicsOut> {
    const res = await post('/economics', req, signal);
    return (await res.json()) as EconomicsOut;
  },
  async economicsCompare(
    req: EconomicsCompareRequest,
    signal?: AbortSignal,
  ): Promise<EconomicsCompareOut> {
    const res = await post('/economics/compare', req, signal);
    return (await res.json()) as EconomicsCompareOut;
  },
  async optimizeComponents(
    req: ComponentOptimizeRequest,
    signal?: AbortSignal,
  ): Promise<ComponentOptimizeResponse> {
    const res = await post('/optimize/components', req, signal);
    return (await res.json()) as ComponentOptimizeResponse;
  },
  async selectDoors(req: DoorSelectRequest, signal?: AbortSignal): Promise<DoorSelectResponse> {
    const res = await post('/doors/select', req, signal);
    return (await res.json()) as DoorSelectResponse;
  },
  async batchParse(req: BatchParseRequest, signal?: AbortSignal): Promise<BatchParseResponse> {
    const res = await post('/batch/parse', req, signal);
    return (await res.json()) as BatchParseResponse;
  },
  async batchRun(req: BatchRunRequest, signal?: AbortSignal): Promise<BatchRunResponse> {
    const res = await post('/batch/run', req, signal);
    return (await res.json()) as BatchRunResponse;
  },
  async batchExport(req: BatchRunRequest, format: BatchFormat, signal?: AbortSignal) {
    const res = await post(`/batch/export?format=${format}`, req, signal);
    return res.blob();
  },
  async pricesParse(req: PriceParseRequest, signal?: AbortSignal): Promise<PriceParseResponse> {
    const res = await post('/prices/parse', req, signal);
    return (await res.json()) as PriceParseResponse;
  },
  async pricesExport(req: PriceExportRequest, format: 'csv' | 'xlsx', signal?: AbortSignal) {
    const res = await post(`/prices/export?format=${format}`, req, signal);
    return res.blob();
  },
  async batchTemplate(kind: BatchKind, format: 'xlsx' | 'csv', signal?: AbortSignal) {
    const res = await request(`/batch/template?kind=${kind}&format=${format}`, { signal });
    return res.blob();
  },
  seabeds: (signal?: AbortSignal) => getJson<SeabedOut[]>('/catalog/seabeds', signal),
  fouling: (signal?: AbortSignal) => getJson<FoulingOut[]>('/catalog/fouling', signal),
  async explore(req: ExploreRequest, signal?: AbortSignal): Promise<ExploreResponse> {
    const res = await post('/simulate/explore', req, signal);
    return (await res.json()) as ExploreResponse;
  },
  species: (signal?: AbortSignal) => getJson<SpeciesOut[]>('/catalog/species', signal),
  async selectivity(req: SelectivityRequest, signal?: AbortSignal): Promise<SelectivityResponse> {
    const res = await post('/simulate/selectivity', req, signal);
    return (await res.json()) as SelectivityResponse;
  },
  async uncertainty(req: UncertaintyRequest, signal?: AbortSignal): Promise<UncertaintyResponse> {
    const res = await post('/simulate/uncertainty', req, signal);
    return (await res.json()) as UncertaintyResponse;
  },
  async calibrate(req: CalibrateRequest, signal?: AbortSignal): Promise<CalibrateResponse> {
    const res = await post('/simulate/calibrate', req, signal);
    return (await res.json()) as CalibrateResponse;
  },
  async parseSensors(req: SensorParseRequest, signal?: AbortSignal): Promise<SensorParseResponse> {
    const res = await post('/sensors/parse', req, signal);
    return (await res.json()) as SensorParseResponse;
  },
  async sensorExample(signal?: AbortSignal): Promise<string> {
    const res = await request('/sensors/example', { signal });
    return res.text();
  },
  async haul(req: HaulRequest, signal?: AbortSignal): Promise<HaulResponse> {
    const res = await post('/simulate/haul', req, signal);
    return (await res.json()) as HaulResponse;
  },
  async simulate(req: SimulateRequest, signal?: AbortSignal): Promise<SimulateResponse> {
    const res = await post('/simulate', req, signal);
    return (await res.json()) as SimulateResponse;
  },
  exercises: (signal?: AbortSignal) => getJson<ExerciseSummary[]>('/teaching/exercises', signal),
  exercise: (id: string, seed: number, signal?: AbortSignal) =>
    getJson<ExerciseInstance>(`/teaching/exercises/${encodeURIComponent(id)}?seed=${seed}`, signal),
  async grade(
    id: string,
    seed: number,
    answers: Record<string, string>,
    signal?: AbortSignal,
  ): Promise<ExerciseGrade> {
    const res = await post('/teaching/grade', { id, seed, answers }, signal);
    return (await res.json()) as ExerciseGrade;
  },
  labs: (signal?: AbortSignal) => getJson<LabSummary[]>('/teaching/labs', signal),
  lab: (id: string, signal?: AbortSignal) =>
    getJson<Lab>(`/teaching/labs/${encodeURIComponent(id)}`, signal),
  async labCheck(req: LabCheckRequest, signal?: AbortSignal): Promise<LabStepResult> {
    const res = await post('/teaching/labs/check', req, signal);
    return (await res.json()) as LabStepResult;
  },
};
