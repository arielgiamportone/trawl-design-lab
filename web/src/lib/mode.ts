/** Modo de la interfaz: asistente guiado (por defecto), experto (todas las pestañas) o aula. */
import { loadJson, saveJson } from './storage';

export type UiMode = 'simple' | 'expert' | 'aula';
export const MODE_KEY = 'trawl-design-lab:mode';

export function initialMode(): UiMode {
  const m = loadJson<UiMode>(MODE_KEY);
  return m === 'expert' || m === 'aula' ? m : 'simple';
}

export function saveMode(mode: UiMode): void {
  saveJson(MODE_KEY, mode);
}

/** Evento con que otras partes de la app cambian de modo (el laboratorio abre el modo experto). */
export const MODE_EVENT = 'trawl-design-lab:mode';

export function goToMode(mode: UiMode): void {
  saveMode(mode);
  window.dispatchEvent(new CustomEvent<UiMode>(MODE_EVENT, { detail: mode }));
}
