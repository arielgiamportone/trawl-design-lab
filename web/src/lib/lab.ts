/**
 * Laboratorio en curso (Fase 17): qué laboratorio, en qué paso y lo hecho en cada paso. Vive en
 * localStorage para seguir después de recargar y lo comparten el panel del laboratorio (sobre el
 * modo experto) y el aula.
 */
import { useSyncExternalStore } from 'react';
import type { DesignRequest, LabStepResult } from '../api/client';
import { DEFAULT_CASE, type CaseState } from '../state/model';
import { loadJson, removeKey, saveJson } from './storage';

export interface LabStepState {
  answers: Record<string, string>;
  /** Caso del alumno cuando comprobó el paso (se entrega con él). */
  design?: DesignRequest;
  result?: LabStepResult;
}

export interface ActiveLab {
  labId: string;
  /** Práctica libre o un ítem de una tarea del aula. */
  source: { kind: 'practice' } | { kind: 'assignment'; assignmentId: number; item: number };
  step: number;
  steps: Record<string, LabStepState>;
  startedAt: string;
}

export const LAB_KEY = 'trawl-design-lab:lab:v1';
const EVENT = 'trawl-design-lab:lab';

export function loadLab(): ActiveLab | null {
  const l = loadJson<ActiveLab>(LAB_KEY);
  return l && typeof l.labId === 'string' && l.source ? l : null;
}

export function saveLab(l: ActiveLab | null): void {
  if (l) saveJson(LAB_KEY, l);
  else removeKey(LAB_KEY);
  window.dispatchEvent(new Event(EVENT));
}

export function startLab(labId: string, source: ActiveLab['source']): ActiveLab {
  const l: ActiveLab = { labId, source, step: 0, steps: {}, startedAt: new Date().toISOString() };
  saveLab(l);
  return l;
}

function subscribe(cb: () => void): () => void {
  window.addEventListener(EVENT, cb);
  window.addEventListener('storage', cb);
  return () => {
    window.removeEventListener(EVENT, cb);
    window.removeEventListener('storage', cb);
  };
}

let cachedRaw: string | null = null;
let cached: ActiveLab | null = null;
function snapshot(): ActiveLab | null {
  let raw: string | null;
  try {
    raw = window.localStorage.getItem(LAB_KEY);
  } catch {
    raw = null;
  }
  if (raw !== cachedRaw) {
    cachedRaw = raw;
    cached = loadLab();
  }
  return cached;
}

/** Laboratorio en curso, reactivo. */
export function useActiveLab(): ActiveLab | null {
  return useSyncExternalStore(subscribe, snapshot, () => null);
}

/** Pasos para entregar: los que tienen un caso comprobado. */
export function labSubmission(
  l: ActiveLab,
): Record<string, { design: DesignRequest; answers: Record<string, string> }> {
  const out: Record<string, { design: DesignRequest; answers: Record<string, string> }> = {};
  for (const [id, st] of Object.entries(l.steps)) {
    if (st.design) out[id] = { design: st.design, answers: st.answers };
  }
  return out;
}

/** Caso de partida de un laboratorio (un ``DesignRequest`` con ids del catálogo) como estado. */
export function caseFromStart(start: Record<string, unknown>): CaseState {
  const params: Record<string, string> = {};
  for (const [k, v] of Object.entries((start.params as Record<string, unknown>) ?? {})) {
    params[k] = String(v);
  }
  return {
    ...DEFAULT_CASE,
    net: typeof start.net === 'string' ? start.net : DEFAULT_CASE.net,
    netModified: typeof start.net_modified === 'string' ? start.net_modified : null,
    vessel: typeof start.vessel === 'string' ? start.vessel : null,
    door: typeof start.door === 'string' ? start.door : null,
    params,
  };
}
