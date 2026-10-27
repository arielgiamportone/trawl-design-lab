/**
 * Forma (parcial) de ``DesignResponse.result``. El contrato OpenAPI lo declara como objeto libre;
 * estas interfaces describen sólo los campos que usa la interfaz (ver ``trawlkit.model``).
 */
import type { DesignResponseRaw } from './client';

export type Series = (number | null)[];
/** ``mod`` es ``null`` cuando el caso no trae red modificada (``case.net_modified``). */
export type StdMod<T> = { std: T; mod: T | null };

export interface PerformanceWindow {
  speeds_kn: number[];
  available_kgf: Series;
  demand_kgf: Series;
  margin_kgf: Series;
  feasible: boolean[];
  feasible_speeds_kn: number[];
  max_speed_kn: number | null;
}

export interface DesignResult {
  power: {
    curves: {
      speeds_kn: number[];
      fridman_kgf: Series;
      prado_kgf: Series;
      koyama_kgf: Series;
      nomura_kgf: Series;
      hamuro_kgf: Series;
      average_kgf: Series;
    };
    ft_propeller: string;
    /** Tiro por la hélice (Fase 19.4): sólo si el buque trae el diámetro de la hélice. */
    propeller?: {
      method: string;
      source: string;
      diameter_m: number;
      bollard_pull_t: number;
      towing_kgf: Series;
    } | null;
  };
  drag: {
    table: {
      unit: string;
      speed_kn: number[];
      std: Record<string, Series>;
      mod: Record<string, Series>;
    };
    design_method: string;
    rn: StdMod<Series>;
  };
  doors: { forces: { drag_kgf: Series; lift_kgf: Series }; rig_drag_kgf: Series };
  /** Tangones, gemelo o vara (Fase 19.5): todo el aparejo; ausente con portones o pareja. */
  multirig?: {
    kind: string;
    n_nets: number;
    warp_drag_kgf: Series;
    doors_drag_kgf: Series;
    bridle_drag_kgf: Series | null;
    clump_drag_kgf: Series | null;
    beam: { total_kgf: Series } | null;
  };
  floats: { drag_kgf: Series };
  warps: {
    drag_kgf: Series;
    total: StdMod<Series>;
    loads: { working_load_kgf: number; safety_factor: number; min_breaking_load_kgf: number };
    selection: {
      id: string;
      construction?: string;
      diameter_mm: number;
      breaking_load_t: number;
      satisfies_breaking_load: boolean;
    } | null;
  };
  spread: {
    fridman: { dpa_std_m: Series; dpa_mod_m: Series };
    vertical: { fridman: StdMod<{ av_m: Series; av_average_m: number | null }> };
  };
  performance: {
    windows: Record<string, PerformanceWindow>;
    demand: StdMod<Series>;
    design_key: string;
  };
}

export type Summary = Record<string, number | string | null>;

export interface DesignCaseOut {
  net: string;
  net_modified: string | null;
  vessel: string;
  door: string;
  speeds_kn: number[];
  compat: 'excel' | 'corrected';
  [key: string]: unknown;
}

export interface DesignData {
  case: DesignCaseOut;
  summary: Summary;
  notes: string[];
  result: DesignResult;
}

/** Adapta la respuesta cruda (objetos libres en el contrato) a los tipos de la interfaz. */
export function asDesignData(raw: DesignResponseRaw): DesignData {
  return raw as unknown as DesignData;
}
