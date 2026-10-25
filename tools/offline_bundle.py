"""Copia la *wheel* de trawlkit a la app web para el motor sin conexión (Pyodide, Fase 13).

Deja ``<destino>/<hash>/<wheel>`` y ``<destino>/manifest.json`` con el nombre, la versión, la
versión de Pyodide (la de ``web/src/engine/config.ts``) y el tamaño. El hash del contenido en la
ruta hace que el service worker guarde en caché cada motor nuevo sin servir uno viejo.

Además descarga de PyPI las *wheels* puras que Pyodide no trae y el motor usa sin conexión
(:data:`EXTRAS`: openpyxl para leer y escribir planillas XLSX, Fase 14), verifica su sha256 y
las lista en ``extras``.

Uso (docs.yml y CI)::

    uv build --wheel -o dist
    uv run python tools/offline_bundle.py dist/trawlkit-*.whl web/public/py
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "web" / "src" / "engine" / "config.ts"

#: Wheels puras de PyPI que el motor sin conexión instala con micropip (versiones de uv.lock).
EXTRAS = (("openpyxl", "3.1.5"), ("et-xmlfile", "2.0.0"))


def fetch_wheel(name: str, version: str, dest: Path) -> Path:
    """Descarga la wheel ``py3-none-any`` de ``name==version`` de PyPI y verifica su sha256."""
    with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/{version}/json", timeout=60) as r:
        info = json.load(r)
    wheel = next(
        (
            u
            for u in info["urls"]
            if u["filename"].endswith("-py3-none-any.whl")
            or u["filename"].endswith("-py2.py3-none-any.whl")
        ),
        None,
    )
    if wheel is None:
        raise SystemExit(f"{name}=={version} no tiene wheel pura en PyPI")
    with urllib.request.urlopen(wheel["url"], timeout=120) as r:
        data = r.read()
    if hashlib.sha256(data).hexdigest() != wheel["digests"]["sha256"]:
        raise SystemExit(f"sha256 distinto para {wheel['filename']}")
    out = dest / wheel["filename"]
    out.write_bytes(data)
    return out


def pyodide_version() -> str:
    """Versión de Pyodide que usa la app (``PYODIDE_VERSION`` de ``config.ts``)."""
    m = re.search(r"PYODIDE_VERSION = '([^']+)'", CONFIG.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit(f"no se encontró PYODIDE_VERSION en {CONFIG}")
    return m.group(1)


def bundle(
    wheel: Path, dest: Path, extras: tuple[tuple[str, str], ...] = EXTRAS
) -> dict[str, object]:
    """Copia la wheel (y las de :data:`EXTRAS`) a ``dest/<hash>/`` y escribe el manifiesto."""
    data = wheel.read_bytes()
    digest = hashlib.sha256(data).hexdigest()[:12]
    if dest.exists():
        shutil.rmtree(dest)
    (dest / digest).mkdir(parents=True)
    shutil.copyfile(wheel, dest / digest / wheel.name)
    version = wheel.name.split("-")[1]
    extra_paths = [f"{digest}/{fetch_wheel(name, ver, dest / digest).name}" for name, ver in extras]
    total = len(data) + sum((dest / p).stat().st_size for p in extra_paths)
    manifest = {
        "wheel": f"{digest}/{wheel.name}",
        "extras": extra_paths,
        "version": version,
        "pyodide": pyodide_version(),
        "bytes": total,
    }
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("uso: python tools/offline_bundle.py <trawlkit.whl> <destino>")
    print(json.dumps(bundle(Path(sys.argv[1]), Path(sys.argv[2]))))
