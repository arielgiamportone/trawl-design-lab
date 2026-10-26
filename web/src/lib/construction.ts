/**
 * Guía de construcción (Fase 15): progreso del taller y ayudas de presentación.
 *
 * El avance (paños cortados, uniones hechas) se guarda en el navegador por red y variante, así
 * el redero puede ir tildando en el teléfono aun sin conexión.
 */
import type { ConstructionGuide, GuideJoin } from '../api/client';
import { msg } from '../i18n';
import { loadJson, saveJson } from './storage';

export const GUIDE_VIEW_KEY = 'trawl-design-lab:guide-view';
export const EYE_KEY = 'trawl-design-lab:guide-eye';
const PROGRESS_PREFIX = 'trawl-design-lab:guide-progress:';

export type GuideView = 'corte' | 'armado' | 'montaje' | 'cortes';

export interface Progress {
  cut: string[];
  joins: number[];
}

const EMPTY: Progress = { cut: [], joins: [] };

export function progressKey(netId: string, variant: string): string {
  return `${PROGRESS_PREFIX}${netId}:${variant}`;
}

export function loadProgress(netId: string, variant: string): Progress {
  const p = loadJson<Progress>(progressKey(netId, variant));
  return p && Array.isArray(p.cut) && Array.isArray(p.joins) ? p : EMPTY;
}

export function saveProgress(netId: string, variant: string, p: Progress): void {
  saveJson(progressKey(netId, variant), p);
}

/** Alterna un elemento en una lista (tildar o destildar). */
export function toggle<T>(list: T[], item: T): T[] {
  return list.includes(item) ? list.filter((x) => x !== item) : [...list, item];
}

/** Avance del taller en 0..1: paños cortados más uniones hechas sobre el total. */
export function completion(g: ConstructionGuide, p: Progress): number {
  const ids = new Set(g.pieces.map((x) => x.id));
  const steps = new Set(g.joins.map((j) => j.step));
  const total = ids.size + steps.size;
  if (total === 0) return 0;
  const done = p.cut.filter((x) => ids.has(x)).length + p.joins.filter((s) => steps.has(s)).length;
  return done / total;
}

/** Planos del plano (layout) que toca una unión. */
export function joinPlanes(j: GuideJoin): string[] {
  if (j.kind === 'side_seam') return ['upper', 'lower'];
  if (j.kind === 'side_panel') return ['side', 'upper', 'lower'];
  return j.plane === 'vientre' ? ['lower'] : j.plane === 'costado' ? ['side'] : ['upper'];
}

/** Paneles a resaltar en el plano para una unión (las costuras laterales, toda la cara). */
export function joinPanels(j: GuideJoin): string[] | 'all' {
  return j.kind === 'side_seam' ? 'all' : [j.a, j.b];
}

/**
 * Texto de la unión para la lista y la lectura en voz alta (los bordes y la regla llegan de la
 * API ya en el idioma de la interfaz).
 */
export function joinText(j: GuideJoin): string {
  const rule = j.rule.charAt(0).toUpperCase() + j.rule.slice(1);
  return msg().construction.joinText(j.a_edge, j.a, j.meshes_a, j.b_edge, j.b, j.meshes_b, rule);
}
