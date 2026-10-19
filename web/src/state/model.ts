/** Estado del caso de diseño y armado del ``DesignRequest``. */
import type { DesignRequest, NetSpec } from '../api/client';
import { editErrors, editedSpec, type PanelEdits } from '../lib/panels';
import { buildParams, type ParamMeta, type ParamValues } from '../lib/params';

export type Compat = 'excel' | 'corrected';

export interface CaseState {
  net: string;
  netModified: string | null;
  /** ``null`` = primer buque del catálogo (como la API). */
  vessel: string | null;
  door: string | null;
  compat: Compat;
  params: ParamValues;
  edits: { std: PanelEdits; mod: PanelEdits };
  /**
   * Red escalada desde «Optimizar» (``POST /optimize/scaled-net``): reemplaza a la red del
   * catálogo (y a la modificada, si hay) como red en línea. ``null`` = red del catálogo.
   */
  scaled: ScaledNet | null;
  /** Velocidad de arrastre prevista [kn] para el diagnóstico del modo guiado (no va a la API). */
  targetSpeed: number;
}

export interface ScaledNet {
  s: number;
  std: NetSpec;
  mod: NetSpec | null;
  /** Velocidad del diseño optimizado [kn] (informativa). */
  speed: number | null;
}

export const DEFAULT_CASE: CaseState = {
  net: 'fao_a3_standard',
  netModified: 'fao_a3_modified',
  vessel: null,
  door: null,
  compat: 'corrected',
  params: {},
  edits: { std: {}, mod: {} },
  scaled: null,
  targetSpeed: 2,
};

export const STORAGE_KEY = 'trawl-design-lab:case:v1';

/** Normaliza un estado leído de localStorage (tolera versiones viejas o datos corruptos). */
export function sanitizeCase(raw: unknown): CaseState {
  if (!raw || typeof raw !== 'object') return DEFAULT_CASE;
  const r = raw as Partial<CaseState>;
  const str = (v: unknown, d: string | null) => (typeof v === 'string' && v ? v : d);
  const obj = <T>(v: unknown, d: T): T =>
    v && typeof v === 'object' && !Array.isArray(v) ? (v as T) : d;
  const edits = obj<{ std?: PanelEdits; mod?: PanelEdits }>(r.edits, {});
  return {
    net: str(r.net, DEFAULT_CASE.net) as string,
    netModified: r.netModified === null ? null : str(r.netModified, DEFAULT_CASE.netModified),
    vessel: str(r.vessel, null),
    door: str(r.door, null),
    compat: r.compat === 'excel' ? 'excel' : 'corrected',
    params: obj<ParamValues>(r.params, {}),
    edits: { std: obj<PanelEdits>(edits.std, {}), mod: obj<PanelEdits>(edits.mod, {}) },
    scaled: sanitizeScaled(r.scaled),
    targetSpeed:
      typeof r.targetSpeed === 'number' && r.targetSpeed > 0 && r.targetSpeed <= 10
        ? r.targetSpeed
        : DEFAULT_CASE.targetSpeed,
  };
}

function isSpec(v: unknown): v is NetSpec {
  return !!v && typeof v === 'object' && Array.isArray((v as { panels?: unknown }).panels);
}

function sanitizeScaled(raw: unknown): ScaledNet | null {
  if (!raw || typeof raw !== 'object') return null;
  const r = raw as Partial<ScaledNet>;
  if (typeof r.s !== 'number' || !Number.isFinite(r.s) || !isSpec(r.std)) return null;
  return {
    s: r.s,
    std: r.std,
    mod: isSpec(r.mod) ? r.mod : null,
    speed: typeof r.speed === 'number' && Number.isFinite(r.speed) ? r.speed : null,
  };
}

export interface BuiltRequest {
  request: DesignRequest;
  /** Errores de validación (parámetros y paneles) que impiden calcular. */
  errors: Record<string, string>;
  /** Faltan datos (especificación de la red editada aún no cargada). */
  pending: boolean;
}

export function buildRequest(
  state: CaseState,
  metas: ParamMeta[],
  specs: { std?: NetSpec; mod?: NetSpec },
): BuiltRequest {
  const { params, errors: paramErrors } = buildParams(metas, state.params);
  const errors: Record<string, string> = {};
  for (const [k, v] of Object.entries(paramErrors)) errors[`param.${k}`] = v;
  for (const [k, v] of Object.entries(editErrors(state.edits.std))) errors[`std.${k}`] = v;
  if (state.netModified) {
    for (const [k, v] of Object.entries(editErrors(state.edits.mod))) errors[`mod.${k}`] = v;
  }
  let pending = false;
  // Con una red escalada, ``specs`` ya trae la escalada (ver CaseProvider) y las ediciones se
  // aplican sobre ella.
  let net: DesignRequest['net'] = state.scaled ? state.scaled.std : state.net;
  if (Object.keys(state.edits.std).length) {
    if (specs.std) net = editedSpec(specs.std, state.edits.std) ?? net;
    else pending = true;
  }
  let netModified: DesignRequest['net_modified'] =
    state.netModified && state.scaled?.mod ? state.scaled.mod : state.netModified;
  if (state.netModified && Object.keys(state.edits.mod).length) {
    if (specs.mod) netModified = editedSpec(specs.mod, state.edits.mod) ?? netModified;
    else pending = true;
  }
  const request: DesignRequest = {
    net,
    net_modified: netModified ?? null,
    vessel: state.vessel,
    door: state.door,
    compat: state.compat,
    params,
  };
  return { request, errors, pending };
}
