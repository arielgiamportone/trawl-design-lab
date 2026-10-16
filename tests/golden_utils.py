"""Acceso a los valores de referencia del Excel (tests/golden/*.json) para los tests del motor.

Uso::

    from tests.golden_utils import SPEEDS_KN, assert_close, golden, golden_series

    assert_close(net.solid_surface_m2, golden("mecanica_de_la_red", "solid_surface_std_m2"))
    x, y = golden_series("resistencia_de_la_red", "aberdeen_demersal_rn_std_t")
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

import numpy as np
from numpy.testing import assert_allclose

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"

#: Vector de velocidades del modelo original (nudos).
SPEEDS_KN: list[float] = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]

#: Tolerancia relativa por defecto en modo Compat.EXCEL.
RTOL_EXACT = 1e-6
#: Tolerancia cuando el Excel usa entradas truncadas por MID() u otros redondeos de texto.
RTOL_TRUNCATED = 1e-3


@cache
def load_sheet(sheet_slug: str) -> dict[str, Any]:
    """Carga el JSON de una hoja (p. ej. ``"resistencia_de_la_red"``)."""
    path = GOLDEN_DIR / f"{sheet_slug}.json"
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)  # type: ignore[no-any-return]


def golden_entry(sheet_slug: str, key: str) -> dict[str, Any]:
    """Entrada completa (``cell``, ``value`` o ``values``, ``label``, ``unit``, flags)."""
    sheet = load_sheet(sheet_slug)
    if key in sheet["values"]:
        return sheet["values"][key]  # type: ignore[no-any-return]
    if key in sheet.get("series", {}):
        return sheet["series"][key]  # type: ignore[no-any-return]
    raise KeyError(f"{sheet_slug}: clave golden desconocida {key!r}")


def golden(sheet_slug: str, key: str) -> Any:
    """Valor escalar (``values``) o lista de valores (``series``) de una clave."""
    entry = golden_entry(sheet_slug, key)
    return entry["value"] if "value" in entry else entry["values"]


def golden_series(sheet_slug: str, key: str) -> tuple[list[float], list[float]]:
    """``(x_values, values)`` de una serie."""
    entry = golden_entry(sheet_slug, key)
    return list(entry["x_values"]), list(entry["values"])


def is_static(sheet_slug: str, key: str) -> bool:
    """True si el Excel tiene ese valor pegado a mano (no es una fórmula)."""
    return bool(golden_entry(sheet_slug, key).get("static", False))


def assert_close(
    actual: Any,
    expected: Any,
    rtol: float = RTOL_EXACT,
    atol: float = 0.0,
    where: str = "",
) -> None:
    """``assert_allclose`` con mensaje legible; acepta escalares, listas y arrays."""
    a = np.asarray(actual, dtype=float)
    e = np.asarray(expected, dtype=float)
    assert_allclose(a, e, rtol=rtol, atol=atol, err_msg=where or "", verbose=True)
