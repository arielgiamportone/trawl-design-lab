/// <reference lib="webworker" />
/**
 * *Worker* del motor sin conexión: carga Pyodide, instala la *wheel* de trawlkit y atiende los
 * pedidos con ``trawlkit.api.offline.handle_json`` (las mismas rutas que la API).
 */

interface InitMsg {
  id: number;
  type: 'init';
  pyodideUrl: string;
  wheelUrl: string;
  extraUrls?: string[];
  packages: string[];
}
interface RequestMsg {
  id: number;
  type: 'request';
  method: string;
  path: string;
  body: string | null;
}
type InMsg = InitMsg | RequestMsg;

/**
 * Error con código: el hilo principal lo traduce al idioma de la interfaz (``engine/offline``).
 * El *worker* no carga los catálogos de textos.
 */
class CodedError extends Error {
  constructor(
    readonly code: 'download' | 'notStarted',
    readonly arg = '',
  ) {
    super(`${code}${arg ? `: ${arg}` : ''}`);
  }
}

interface Pyodide {
  loadPackage(names: string[]): Promise<unknown>;
  runPythonAsync(code: string): Promise<unknown>;
  FS: { writeFile(path: string, data: Uint8Array): void };
  globals: {
    get(name: string): { handle_json: (m: string, p: string, b: string | null) => string };
  };
}

declare const self: DedicatedWorkerGlobalScope;

let handle: ((m: string, p: string, b: string | null) => string) | null = null;
let starting: Promise<void> | null = null;

async function init(msg: InitMsg): Promise<void> {
  // Las etapas viajan como claves; el hilo principal las traduce.
  const progress = (stage: 'python' | 'packages' | 'install') =>
    self.postMessage({ id: msg.id, type: 'progress', stage });
  progress('python');
  const mod = (await import(/* @vite-ignore */ `${msg.pyodideUrl}pyodide.mjs`)) as {
    loadPyodide: (o: { indexURL: string }) => Promise<Pyodide>;
  };
  const py = await mod.loadPyodide({ indexURL: msg.pyodideUrl });
  progress('packages');
  await py.loadPackage(msg.packages);
  progress('install');
  const names: string[] = [];
  for (const url of [...(msg.extraUrls ?? []), msg.wheelUrl]) {
    const res = await fetch(url);
    if (!res.ok) throw new CodedError('download', `${url.split('/').pop()} (${res.status})`);
    const name = url.split('/').pop() ?? 'paquete.whl';
    py.FS.writeFile(`/tmp/${name}`, new Uint8Array(await res.arrayBuffer()));
    names.push(name);
  }
  const installs = names
    .map((n) => `await micropip.install("emfs:/tmp/${n}", deps=False)`)
    .join('\n');
  await py.runPythonAsync(`import micropip\n${installs}\nfrom trawlkit.api import offline`);
  handle = py.globals.get('offline').handle_json;
}

self.onmessage = async (e: MessageEvent<InMsg>) => {
  const msg = e.data;
  try {
    if (msg.type === 'init') {
      starting ??= init(msg);
      await starting;
      self.postMessage({ id: msg.id, type: 'ready' });
      return;
    }
    if (!handle) throw new CodedError('notStarted');
    const out = handle(msg.method, msg.path, msg.body);
    self.postMessage({ id: msg.id, type: 'response', out });
  } catch (err) {
    if (msg.type === 'init') starting = null;
    const coded = err instanceof CodedError ? { code: err.code, arg: err.arg } : {};
    self.postMessage({ id: msg.id, type: 'error', message: String(err), ...coded });
  }
};
