/** Modo de la interfaz: asistente guiado (por defecto) o experto (todas las pestañas). */
import { loadJson, saveJson } from './storage';

export type UiMode = 'simple' | 'expert';
export const MODE_KEY = 'trawl-design-lab:mode';

export function initialMode(): UiMode {
  return loadJson<UiMode>(MODE_KEY) === 'expert' ? 'expert' : 'simple';
}

export function saveMode(mode: UiMode): void {
  saveJson(MODE_KEY, mode);
}
