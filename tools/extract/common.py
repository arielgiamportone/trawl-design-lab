"""Utilidades compartidas por los extractores."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.workbook.workbook import Workbook

ROOT = Path(__file__).resolve().parents[2]
XLSX = ROOT / "legacy" / "Calculos_Red_FAO_A3.xlsx"
DATA = ROOT / "data"
GOLDEN = ROOT / "tests" / "golden"


@lru_cache(maxsize=2)
def workbook(data_only: bool = True) -> Workbook:
    """Abre el libro una sola vez (``data_only=True`` → valores cacheados; False → fórmulas)."""
    return openpyxl.load_workbook(XLSX, data_only=data_only, read_only=False)


def cell(sheet: str, ref: str, data_only: bool = True) -> Any:
    """Valor (o fórmula) de una celda."""
    return workbook(data_only)[sheet][ref].value


def num(sheet: str, ref: str) -> float:
    """Valor numérico cacheado de una celda; falla si no es numérico."""
    v = cell(sheet, ref)
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise TypeError(f"{sheet}!{ref} no es numérico: {v!r}")
    return float(v)


def rows(sheet: str, ref: str, data_only: bool = True) -> list[list[Any]]:
    """Valores de un rango como lista de filas."""
    ws = workbook(data_only)[sheet]
    return [[c.value for c in row] for row in ws[ref]]
