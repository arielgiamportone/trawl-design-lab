"""Compara la huella de rutas de la API en línea con la de ``web/openapi.json``.

Uso: ``python tools/check_api_contract.py URL_API [--wait SEGUNDOS]``. Consulta ``URL/health``
(despierta la API si duerme) hasta que la huella coincida o se agote la espera, y lo informa con
anotaciones de GitHub Actions (``::notice``/``::warning``). Siempre termina con código 0: un
despliegue lento o una API dormida no deben hacer fallar la publicación del libro.

Sólo usa la biblioteca estándar, con el mismo algoritmo que ``trawlkit.api.contract``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METHODS = ("get", "post", "put", "patch", "delete")


def fingerprint(openapi: dict) -> str:  # type: ignore[type-arg]
    routes = sorted(
        f"{m.upper()} {path}"
        for path, item in openapi.get("paths", {}).items()
        for m in item
        if m in METHODS
    )
    return hashlib.sha256("\n".join(routes).encode()).hexdigest()[:12]


def fetch_health(base: str, timeout: float = 60.0) -> dict | None:  # type: ignore[type-arg]
    try:
        with urllib.request.urlopen(f"{base.rstrip('/')}/health", timeout=timeout) as r:
            data: dict = json.load(r)  # type: ignore[type-arg]
            return data
    except Exception:  # noqa: BLE001 — cualquier fallo de red cuenta como "sin respuesta"
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("--wait", type=float, default=0.0, help="segundos máximos de espera")
    ap.add_argument("--every", type=float, default=30.0)
    args = ap.parse_args()
    expected = fingerprint(json.loads((ROOT / "web" / "openapi.json").read_text("utf-8")))
    deadline = time.monotonic() + args.wait
    last: dict | None = None  # type: ignore[type-arg]
    while True:
        last = fetch_health(args.base)
        if last and last.get("contract") == expected:
            print(
                f"::notice title=API al día::{args.base} sirve el contrato {expected} "
                f"(v{last.get('version')}, commit {last.get('commit')})"
            )
            return 0
        if time.monotonic() >= deadline:
            break
        time.sleep(args.every)
    if last is None:
        print(f"::warning title=API sin respuesta::{args.base}/health no respondió")
    else:
        print(
            f"::warning title=API desactualizada::{args.base} sirve el contrato "
            f"{last.get('contract')} (commit {last.get('commit')}) y la app espera {expected}. "
            "Si no se actualiza sola, en Render: Manual Deploy → Deploy latest commit "
            "(ver docs/despliegue.md)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
