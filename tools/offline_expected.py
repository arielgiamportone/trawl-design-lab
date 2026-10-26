"""Respuestas de referencia (CPython) para la prueba de paridad de Pyodide.

Escribe ``[{method, path, body, status, response}]`` con lo que devuelve
:func:`trawlkit.api.offline.handle` en CPython; ``web/scripts/pyodide-parity.mjs`` corre los
mismos pedidos dentro de Pyodide y compara.

Uso: ``uv run python tools/offline_expected.py salida.json``
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

from trawlkit.api import offline

_FLEET = "nombre;potencia\nA;60\nB;150\n"
_NET = "fao_wb_bt2p_60hp"

CASES: list[tuple[str, str, dict[str, object] | None]] = [
    ("GET", "/health", None),
    ("GET", "/catalog/components/wire?generic=true", None),
    ("POST", "/design", {}),
    ("POST", "/design", {"compat": "excel"}),
    ("POST", "/design", {"net": "fao_wb_bt2p_60hp", "params": {"generic_only": True}}),
    (
        "POST",
        "/design/bom",
        {"prices": {"doors": {"value": 450, "currency": "USD", "unit": "unit"}}},
    ),
    (
        "POST",
        "/optimize/components",
        {"net": "fao_wb_bt2p_60hp", "max_doors": 2, "max_floats": 2, "max_twines": 2},
    ),
    ("POST", "/optimize", {"grid": {"n_s": 3, "n_v": 3}, "refine": False}),
    (
        "POST",
        "/batch/run",
        {"file": {"filename": "f.csv", "content": _FLEET}, "net": _NET, "assemble": False},
    ),
    (
        "POST",
        "/batch/export?format=csv",
        {"file": {"filename": "f.csv", "content": _FLEET}, "net": _NET, "assemble": False},
    ),
    (
        "POST",
        "/batch/export?format=xlsx",
        {"file": {"filename": "f.csv", "content": _FLEET}, "net": _NET, "assemble": False},
    ),
    ("GET", "/batch/template?kind=fleet&format=xlsx", None),
    ("POST", "/design/construction", {"net": _NET}),
    ("POST", "/design/construction/export?format=xlsx", {"net": _NET}),
]


def main(out: str) -> None:
    """Escribe las respuestas de referencia en ``out``."""
    rows = []
    for method, path, body in CASES:
        status, response = offline.handle(method, path, None if body is None else json.dumps(body))
        row: dict[str, object] = {"method": method, "path": path, "body": body, "status": status}
        if isinstance(response, offline.Binary):
            kind = "xlsx" if response.media.startswith("application/vnd") else "text"
            row["binary"] = {"kind": kind, "data": base64.b64encode(response.data).decode()}
        else:
            row["response"] = response
        rows.append(row)
    Path(out).write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    print(f"{len(rows)} pedidos de referencia en {out}")


if __name__ == "__main__":
    main(sys.argv[1])
