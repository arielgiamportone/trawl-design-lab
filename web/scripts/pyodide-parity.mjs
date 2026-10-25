// Paridad del motor en el navegador (Pyodide) con la API: corre `trawlkit.api.offline` dentro de
// Pyodide en Node y compara las respuestas con las de CPython (tolerancia relativa 1e-9).
//
// Uso: node scripts/pyodide-parity.mjs <trawlkit.whl | manifest.json> <esperado.json>
// Con el manifiesto de web/public/py/ se instalan también las wheels extra (openpyxl).
// `esperado.json` es [{method, path, body, status, response}] (tools/offline_expected.py).
import { readFileSync } from 'node:fs';
import { basename, dirname, join } from 'node:path';
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
const files = [];
if (wheel.endsWith('.json')) {
  const m = JSON.parse(readFileSync(wheel, 'utf8'));
  for (const rel of [...(m.extras ?? []), m.wheel]) files.push(join(dirname(wheel), rel));
} else {
  files.push(wheel);
}
const installs = [];
for (const f of files) {
  const target = `/tmp/${basename(f)}`;
  py.FS.writeFile(target, readFileSync(f));
  installs.push(`await micropip.install("emfs:${target}", deps=False)`);
}
await py.runPythonAsync(
  `import micropip\n${installs.join('\n')}\nfrom trawlkit.api import offline`,
);
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
    if (c.binary !== undefined) {
      // Binarios (XLSX, CSV): se compara el contenido decodificado que da CPython.
      if (c.binary.kind === 'xlsx') {
        if (!out.binary || atob(out.binary).slice(0, 2) !== 'PK') throw new Error('no es un XLSX');
      } else if (atob(out.binary) !== atob(c.binary.data)) {
        throw new Error('el contenido difiere');
      }
    } else if (c.status === 200) compare(out.body, c.response, 'body');
    console.log(`ok   ${c.method} ${c.path} (${Date.now() - t} ms)`);
  } catch (err) {
    failed += 1;
    console.log(`FALLA ${c.method} ${c.path}: ${err.message}`);
  }
}
console.log(`peor diferencia relativa: ${worst.toExponential(2)}`);
process.exit(failed ? 1 : 0);
