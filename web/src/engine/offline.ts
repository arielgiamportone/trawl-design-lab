/**
 * Motor sin conexión en el teléfono (Pyodide en un *Web Worker*, Fase 13).
 *
 * «Preparar uso sin conexión» descarga una sola vez el intérprete, numpy, pydantic, pyyaml y la
 * *wheel* de trawlkit (≈ 15 MB) y los guarda en la caché del navegador; desde entonces, si no hay
 * red (o si el usuario lo elige), el cliente de la API atiende los pedidos con el motor local:
 * las mismas rutas y respuestas que la API (``trawlkit.api.offline``).
 */
import { msg as messages } from '../i18n';
import { APP_CONTRACT } from '../lib/connection';
import { loadJson, removeKey, saveJson } from '../lib/storage';
import {
  ENGINE_KEY,
  OFFLINE_CACHE,
  PY_PACKAGES,
  PYODIDE_CORE,
  PYODIDE_URL,
  PYODIDE_VERSION,
  READY_KEY,
  wheelDir,
  type WheelManifest,
} from './config';

export type EnginePref = 'auto' | 'local';

export interface ReadyInfo {
  version: string;
  pyodide: string;
  at: string;
  bytes: number;
}

export function readyInfo(): ReadyInfo | null {
  const r = loadJson<ReadyInfo>(READY_KEY);
  return r && typeof r.version === 'string' ? r : null;
}

export function isPrepared(): boolean {
  return readyInfo() !== null;
}

export function enginePref(): EnginePref {
  return loadJson<EnginePref>(ENGINE_KEY) === 'local' ? 'local' : 'auto';
}

export function setEnginePref(p: EnginePref): void {
  saveJson(ENGINE_KEY, p);
}

/** ¿Hay que usar el motor local sin intentar la red? */
export function preferLocal(): boolean {
  if (!isPrepared()) return false;
  const offline = typeof navigator !== 'undefined' && navigator.onLine === false;
  return offline || enginePref() === 'local';
}

interface Pending {
  resolve: (v: unknown) => void;
  reject: (e: Error) => void;
  onProgress?: (stage: string) => void;
}

let worker: Worker | null = null;
let seq = 0;
const pending = new Map<number, Pending>();
let readyPromise: Promise<void> | null = null;

function getWorker(): Worker {
  if (worker) return worker;
  worker = new Worker(new URL('./pyodide.worker.ts', import.meta.url), { type: 'module' });
  worker.onmessage = (e: MessageEvent) => {
    const m = e.data as {
      id: number;
      type: string;
      stage?: string;
      out?: string;
      message?: string;
      code?: 'download' | 'notStarted';
      arg?: string;
    };
    const p = pending.get(m.id);
    if (!p) return;
    const O = messages().api.offline;
    if (m.type === 'progress') {
      const stage = m.stage ?? '';
      return p.onProgress?.(O.stages[stage as keyof typeof O.stages] ?? stage);
    }
    pending.delete(m.id);
    if (m.type === 'error') {
      if (m.code === 'download') p.reject(new Error(O.downloadFailed(m.arg ?? '')));
      else if (m.code === 'notStarted') p.reject(new Error(O.notStarted));
      else p.reject(new Error(m.message));
    } else p.resolve(m.out);
  };
  return worker;
}

function send(
  msg: Record<string, unknown>,
  onProgress?: (s: string) => void,
  signal?: AbortSignal,
): Promise<unknown> {
  const id = ++seq;
  return new Promise((resolve, reject) => {
    if (signal?.aborted) return reject(new DOMException('cancelado', 'AbortError'));
    pending.set(id, { resolve, reject, onProgress });
    getWorker().postMessage({ id, ...msg });
    signal?.addEventListener('abort', () => stopWorker(), { once: true });
  });
}

/**
 * Corta un cálculo del motor local (una simulación larga): termina el *worker* y rechaza lo que
 * esperaba. El próximo pedido vuelve a cargar el motor desde la caché.
 */
export function stopWorker(): void {
  if (!worker) return;
  worker.terminate();
  worker = null;
  readyPromise = null;
  for (const p of pending.values()) p.reject(new DOMException('cancelado', 'AbortError'));
  pending.clear();
}

async function manifest(): Promise<WheelManifest> {
  const res = await fetch(`${wheelDir()}manifest.json`, { cache: 'no-cache' }).catch(() => null);
  if (!res?.ok) throw new Error(messages().api.offline.noEngine);
  return (await res.json()) as WheelManifest;
}

/** Inicia el motor (una vez por sesión); la primera vez tarda unos segundos. */
export function startEngine(onProgress?: (stage: string) => void): Promise<void> {
  readyPromise ??= (async () => {
    const m = await manifest();
    await send(
      {
        type: 'init',
        pyodideUrl: PYODIDE_URL,
        wheelUrl: `${wheelDir()}${m.wheel}`,
        extraUrls: (m.extras ?? []).map((e) => `${wheelDir()}${e}`),
        packages: PY_PACKAGES,
      },
      onProgress,
    );
  })().catch((err: unknown) => {
    readyPromise = null;
    throw err;
  });
  return readyPromise;
}

/** Archivos de los paquetes (y sus dependencias) según el ``pyodide-lock.json``. */
export function packageFiles(
  lock: { packages: Record<string, { file_name: string; depends?: string[] }> },
  names: string[],
): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  const visit = (n: string) => {
    const key = n.toLowerCase();
    if (seen.has(key)) return;
    seen.add(key);
    const p = lock.packages[key];
    if (!p) return;
    out.push(p.file_name);
    for (const d of p.depends ?? []) visit(d);
  };
  names.forEach(visit);
  return out;
}

/**
 * Descarga y guarda en caché todo lo necesario, inicia el motor y prueba un diseño.
 * ``onProgress`` recibe la etapa y los bytes descargados.
 */
export async function prepareOffline(
  onProgress: (stage: string, bytes: number) => void,
): Promise<ReadyInfo> {
  let bytes = 0;
  const m = await manifest();
  const O = messages().api.offline;
  onProgress(O.searching, 0);
  const lockRes = await fetch(`${PYODIDE_URL}pyodide-lock.json`);
  if (!lockRes.ok) throw new Error(O.lockFailed(lockRes.status));
  const lock = (await lockRes.json()) as Parameters<typeof packageFiles>[0];
  const urls = [
    ...PYODIDE_CORE.map((f) => `${PYODIDE_URL}${f}`),
    ...packageFiles(lock, PY_PACKAGES).map((f) => `${PYODIDE_URL}${f}`),
    `${wheelDir()}manifest.json`,
    ...(m.extras ?? []).map((e) => `${wheelDir()}${e}`),
    `${wheelDir()}${m.wheel}`,
  ];
  const cache = typeof caches !== 'undefined' ? await caches.open(OFFLINE_CACHE) : null;
  for (const [i, url] of urls.entries()) {
    onProgress(O.downloading(i + 1, urls.length), bytes);
    const hit = await cache?.match(url);
    if (hit) {
      bytes += Number(hit.headers.get('content-length') ?? 0);
      continue;
    }
    const res = await fetch(url);
    if (!res.ok) throw new Error(O.fileFailed(`${url.split('/').pop()} (${res.status})`));
    const blob = await res.clone().blob();
    bytes += blob.size;
    await cache?.put(url, res);
  }
  await startEngine((stage) => onProgress(stage, bytes));
  onProgress(O.testing, bytes);
  const test = await localRequest('POST', '/design', '{}');
  if (!test.ok) throw new Error(O.testFailed);
  const info: ReadyInfo = {
    version: m.version,
    pyodide: PYODIDE_VERSION,
    at: new Date().toISOString(),
    bytes,
  };
  saveJson(READY_KEY, info);
  return info;
}

/** Olvida el motor sin conexión y libera la caché. */
export async function forgetOffline(): Promise<void> {
  removeKey(READY_KEY);
  setEnginePref('auto');
  if (typeof caches !== 'undefined') await caches.delete(OFFLINE_CACHE);
}

/** Atiende un pedido con el motor local como si fuera la API (``Response`` con JSON). */
export async function localRequest(
  method: string,
  path: string,
  body: string | null,
  signal?: AbortSignal,
): Promise<Response> {
  await startEngine();
  const raw = (await send({ type: 'request', method, path, body }, undefined, signal)) as string;
  const parsed = JSON.parse(raw) as {
    status: number;
    body?: unknown;
    binary?: string;
    media?: string;
    filename?: string;
  };
  const { status, body: out } = parsed;
  if (parsed.binary !== undefined) {
    // Planillas, CSV e informes: el motor los devuelve en base64.
    const bytes = Uint8Array.from(atob(parsed.binary), (c) => c.charCodeAt(0));
    return new Response(bytes, {
      status,
      headers: {
        'Content-Type': parsed.media ?? 'application/octet-stream',
        'Content-Disposition': `attachment; filename="${parsed.filename ?? 'archivo'}"`,
        'X-Trawlkit-Engine': 'local',
      },
    });
  }
  const payload =
    // El motor local es de la misma compilación que la app: su contrato es el de la app.
    path === '/health' && out && typeof out === 'object'
      ? { ...out, contract: APP_CONTRACT || null, offline: true }
      : out;
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json', 'X-Trawlkit-Engine': 'local' },
  });
}
