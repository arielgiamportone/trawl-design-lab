/** Modo de bajo consumo de datos: sin vistas 3D (three.js) ni comprobaciones periódicas. */
import { useSyncExternalStore } from 'react';
import { LOW_DATA_KEY } from '../engine/config';
import { loadJson, saveJson } from './storage';

/** Pestañas que se ocultan en bajo consumo (descargan three.js y simulan en el servidor). */
export const HEAVY_TABS = ['diseno', 'simulacion'];

const listeners = new Set<() => void>();

export function isLowData(): boolean {
  return loadJson<boolean>(LOW_DATA_KEY) === true;
}

export function setLowData(on: boolean): void {
  saveJson(LOW_DATA_KEY, on);
  listeners.forEach((l) => l());
}

function subscribe(l: () => void): () => void {
  listeners.add(l);
  return () => listeners.delete(l);
}

export function useLowData(): boolean {
  return useSyncExternalStore(subscribe, isLowData, () => false);
}
