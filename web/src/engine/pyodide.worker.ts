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
  const progress = (stage: string) => self.postMessage({ id: msg.id, type: 'progress', stage });
  progress('Cargando el intérprete de Python…');
  const mod = (await import(/* @vite-ignore */ `${msg.pyodideUrl}pyodide.mjs`)) as {
    loadPyodide: (o: { indexURL: string }) => Promise<Pyodide>;
  };
  const py = await mod.loadPyodide({ indexURL: msg.pyodideUrl });
  progress('Cargando numpy y pydantic…');
  await py.loadPackage(msg.packages);
  progress('Instalando el motor trawlkit…');
  const res = await fetch(msg.wheelUrl);
  if (!res.ok) throw new Error(`no se pudo descargar el motor (${res.status})`);
  const name = msg.wheelUrl.split('/').pop() ?? 'trawlkit.whl';
  py.FS.writeFile(`/tmp/${name}`, new Uint8Array(await res.arrayBuffer()));
  await py.runPythonAsync(
    `import micropip\nawait micropip.install("emfs:/tmp/${name}", deps=False)\n` +
      'from trawlkit.api import offline',
  );
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
    if (!handle) throw new Error('el motor sin conexión no está iniciado');
    const out = handle(msg.method, msg.path, msg.body);
    self.postMessage({ id: msg.id, type: 'response', out });
  } catch (err) {
    if (msg.type === 'init') starting = null;
    self.postMessage({ id: msg.id, type: 'error', message: String(err) });
  }
};
