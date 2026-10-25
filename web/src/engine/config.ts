/** Motor sin conexión (Pyodide): versiones, direcciones y claves (Fase 13). */

/** Versión de Pyodide (Python 3.13 con numpy, pydantic y pyyaml compilados). */
export const PYODIDE_VERSION = '0.29.5';
export const PYODIDE_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
/** Archivos del intérprete (además de los paquetes del ``pyodide-lock.json``). */
export const PYODIDE_CORE = [
  'pyodide.mjs',
  'pyodide.asm.js',
  'pyodide.asm.wasm',
  'python_stdlib.zip',
  'pyodide-lock.json',
];
/** Paquetes de Pyodide que usa el motor (sus dependencias se resuelven con el lock). */
export const PY_PACKAGES = ['numpy', 'pydantic', 'pyyaml', 'micropip'];
/** Caché del navegador con todo lo necesario para calcular sin red (lo sirve el service worker). */
export const OFFLINE_CACHE = 'trawl-offline-v1';
/** Marca de «uso sin conexión preparado» en localStorage. */
export const READY_KEY = 'trawl-design-lab:offline:v1';
/** Preferencia de motor: ``auto`` (la API y, sin red, el teléfono) o ``local`` (siempre el teléfono). */
export const ENGINE_KEY = 'trawl-design-lab:engine:v1';
/** Modo de bajo consumo de datos (sin vistas 3D ni comprobaciones periódicas). */
export const LOW_DATA_KEY = 'trawl-design-lab:lowdata:v1';

/** Carpeta de la *wheel* de trawlkit publicada con la app (``py/manifest.json``, docs.yml). */
export function wheelDir(): string {
  return `${import.meta.env.BASE_URL ?? '/'}py/`;
}

export interface WheelManifest {
  wheel: string;
  /** Wheels puras extra (openpyxl y et_xmlfile, para las planillas XLSX). */
  extras?: string[];
  version: string;
  pyodide: string;
  bytes?: number;
}
