/**
 * Memoria de la sesión (en el módulo, no en localStorage): conserva el último pedido y los
 * controles de las pestañas pesadas (Optimizar, Simulación) al cambiar de pestaña, sin repetir
 * el cálculo al recargar la página.
 */
const store = new Map<string, unknown>();

export function recall<T>(key: string): T | undefined {
  return store.get(key) as T | undefined;
}

export function remember<T>(key: string, value: T): void {
  store.set(key, value);
}

/** Sólo para pruebas. */
export function forgetAll(): void {
  store.clear();
}
