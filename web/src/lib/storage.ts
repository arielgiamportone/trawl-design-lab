/** Acceso a localStorage tolerante a fallos (modo privado, cuotas, previsualizaciones). */

export function loadJson<T>(key: string): T | null {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

export function saveJson(key: string, value: unknown): void {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* almacenamiento no disponible: se ignora */
  }
}

export function removeKey(key: string): void {
  try {
    window.localStorage.removeItem(key);
  } catch {
    /* ignorado */
  }
}
