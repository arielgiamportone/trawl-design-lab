"""Copia la *wheel* de trawlkit a la app web para el motor sin conexión (Pyodide, Fase 13).

Deja ``<destino>/<hash>/<wheel>`` y ``<destino>/manifest.json`` con el nombre, la versión, la
versión de Pyodide (la de ``web/src/engine/config.ts``) y el tamaño. El hash del contenido en la
ruta hace que el service worker guarde en caché cada motor nuevo sin servir uno viejo.

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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "web" / "src" / "engine" / "config.ts"


def pyodide_version() -> str:
    """Versión de Pyodide que usa la app (``PYODIDE_VERSION`` de ``config.ts``)."""
    m = re.search(r"PYODIDE_VERSION = '([^']+)'", CONFIG.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit(f"no se encontró PYODIDE_VERSION en {CONFIG}")
    return m.group(1)


def bundle(wheel: Path, dest: Path) -> dict[str, object]:
    """Copia la wheel a ``dest/<hash>/`` y escribe ``dest/manifest.json``."""
    data = wheel.read_bytes()
    digest = hashlib.sha256(data).hexdigest()[:12]
    if dest.exists():
        shutil.rmtree(dest)
    (dest / digest).mkdir(parents=True)
    shutil.copyfile(wheel, dest / digest / wheel.name)
    version = wheel.name.split("-")[1]
    manifest = {
        "wheel": f"{digest}/{wheel.name}",
        "version": version,
        "pyodide": pyodide_version(),
        "bytes": len(data),
    }
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("uso: python tools/offline_bundle.py <trawlkit.whl> <destino>")
    print(json.dumps(bundle(Path(sys.argv[1]), Path(sys.argv[2]))))
