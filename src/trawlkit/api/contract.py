"""Huella del contrato de la API: qué rutas expone (método y camino).

La app web calcula la misma huella desde ``web/openapi.json`` al compilarse (``vite.config.ts``)
y la compara con la que informa ``/health``: si difieren, la API en línea es de otra versión que
la app (p. ej. Render no redesplegó) y la interfaz lo avisa en lugar de mostrar un 404 suelto.
"""

from __future__ import annotations

import hashlib
from typing import Any

METHODS = ("get", "post", "put", "patch", "delete")


def routes(openapi: dict[str, Any]) -> list[str]:
    """Rutas ``"MÉTODO /camino"`` del documento OpenAPI, ordenadas."""
    out = [
        f"{method.upper()} {path}"
        for path, item in openapi.get("paths", {}).items()
        for method in item
        if method in METHODS
    ]
    return sorted(out)


def fingerprint(openapi: dict[str, Any]) -> str:
    """SHA-256 (12 hex) de las rutas unidas por saltos de línea."""
    return hashlib.sha256("\n".join(routes(openapi)).encode()).hexdigest()[:12]
