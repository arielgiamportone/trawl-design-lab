// Paridad del motor en el navegador (Pyodide) con la API: corre `trawlkit.api.offline` dentro de
// Pyodide en Node y compara las respuestas con las de CPython (tolerancia relativa 1e-9).
//
// Uso: node scripts/pyodide-parity.mjs <trawlkit.whl> <esperado.json>
// `esperado.json` es [{method, path, body, status, response}] (tools/offline_expected.py).
import { readFileSync } from 'node:fs';
import { basename } from 'node:path';
import { loadPyodide } from 'pyodide';

const [wheel, expectedPath] = process.argv.slice(2);
if (!wheel || !expectedPath) {
  console.error('uso: node scripts/pyodide-parity.mjs <trawlkit.whl> <esperado.json>');
  process.exit(2);
}
const expected = JSON.parse(readFileSync(expectedPath, 'utf8'));

const t0 = Date.now();
const py = await loadPyodide();
await py.loadPackage(['numpy', 'pydantic', 'pyyaml', 'micropip']);
const target = `/tmp/${basename(wheel)}`;
py.FS.writeFile(target, readFileSync(wheel));
await py.runPythonAsync(`
import micropip
await micropip.install("emfs:${target}", deps=False)
from trawlkit.api import offline
`);
console.log(`Pyodide listo en ${((Date.now() - t0) / 1000).toFixed(1)} s`);

const RTOL = 1e-9;
let worst = 0;
function compare(a, b, path) {
  if (typeof a === 'number' && typeof b === 'number') {
    const d = Math.abs(a - b) / Math.max(Math.abs(a), Math.abs(b), 1e-12);
    worst = Math.max(worst, d);
    if (d > RTOL) throw new Error(`${path}: ${a} ≠ ${b} (rel ${d.toExponential(2)})`);
    return;
  }
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) throw new Error(`${path}: largo ${a.length} ≠ ${b.length}`);
    a.forEach((x, i) => compare(x, b[i], `${path}[${i}]`));
    return;
  }
  if (a && b && typeof a === 'object' && typeof b === 'object') {
    const ka = Object.keys(a)
      .filter((k) => k !== 'runtime_s')
      .sort();
    const kb = Object.keys(b)
      .filter((k) => k !== 'runtime_s')
      .sort();
    if (ka.join() !== kb.join()) throw new Error(`${path}: claves distintas`);
    ka.forEach((k) => compare(a[k], b[k], `${path}.${k}`));
    return;
  }
  if (a !== b) throw new Error(`${path}: ${JSON.stringify(a)} ≠ ${JSON.stringify(b)}`);
}

const handle = py.globals.get('offline').handle_json;
let failed = 0;
for (const c of expected) {
  const t = Date.now();
  const out = JSON.parse(handle(c.method, c.path, c.body == null ? null : JSON.stringify(c.body)));
  try {
    if (out.status !== c.status) throw new Error(`estado ${out.status} ≠ ${c.status}`);
    if (c.status === 200) compare(out.body, c.response, 'body');
    console.log(`ok   ${c.method} ${c.path} (${Date.now() - t} ms)`);
  } catch (err) {
    failed += 1;
    console.log(`FALLA ${c.method} ${c.path}: ${err.message}`);
  }
}
console.log(`peor diferencia relativa: ${worst.toExponential(2)}`);
process.exit(failed ? 1 : 0);
