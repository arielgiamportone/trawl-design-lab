/**
 * Diccionario «vivo» (Fase 18.3): un objeto con las mismas claves que el del catálogo de textos,
 * cuyas propiedades se leen en el idioma activo en cada acceso. Sirve para mantener importable
 * una constante de rótulos (``REGION_LABEL``…) que antes era un objeto fijo en español:
 * ``REGION_LABEL.latam`` y ``Object.entries(REGION_LABEL)`` siguen andando y cambian de idioma.
 */
export function liveRecord<K extends string>(get: () => Record<K, string>): Record<K, string> {
  const out = {} as Record<K, string>;
  for (const key of Object.keys(get()) as K[]) {
    Object.defineProperty(out, key, { enumerable: true, get: () => get()[key] });
  }
  return Object.freeze(out);
}
