"""Extrae datos de entrada, tablas de referencia y valores de referencia del Excel original.

Uso: ``uv run python tools/extract_excel.py [--xlsx legacy/Calculos_Red_FAO_A3.xlsx]``

Fase 1 del plan. Por ahora sólo inventaría hojas y cuenta fórmulas; la extracción
estructurada (paneles, buques, portones, tablas, golden values) se agrega en la Fase 1.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]


def inventory(xlsx: Path) -> dict[str, dict[str, int]]:
    wb = openpyxl.load_workbook(xlsx, data_only=False)
    out: dict[str, dict[str, int]] = {}
    for ws in wb.worksheets:
        cells = formulas = 0
        for row in ws.iter_rows():
            for c in row:
                if c.value is None:
                    continue
                cells += 1
                if isinstance(c.value, str) and c.value.startswith("="):
                    formulas += 1
        out[ws.title] = {"cells": cells, "formulas": formulas}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", type=Path, default=ROOT / "legacy" / "Calculos_Red_FAO_A3.xlsx")
    ap.add_argument("--out", type=Path, default=ROOT / "legacy" / "inventory.json")
    args = ap.parse_args()
    inv = inventory(args.xlsx)
    args.out.write_text(json.dumps(inv, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{len(inv)} hojas → {args.out}")


if __name__ == "__main__":
    main()
