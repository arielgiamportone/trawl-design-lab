"""Extracción reproducible del Excel original a datos abiertos y valores de referencia.

Uso::

    uv run python tools/extract_excel.py            # todo
    uv run python tools/extract_excel.py nets       # sólo un bloque (nets | reference | golden)

Cada bloque vive en ``tools/extract/<bloque>.py`` y expone ``run() -> list[Path]``.
El inventario de hojas (celdas y fórmulas por hoja) se escribe en ``legacy/inventory.json``.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.extract.common import XLSX, workbook  # noqa: E402

BLOCKS = ("nets", "reference", "golden")


def inventory() -> dict[str, dict[str, int]]:
    wb = workbook(data_only=False)
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("blocks", nargs="*", choices=BLOCKS, help="bloques a extraer (default: todos)")
    args = ap.parse_args(argv)
    if not XLSX.exists():
        print(f"No se encuentra {XLSX}", file=sys.stderr)
        return 1

    inv_path = ROOT / "legacy" / "inventory.json"
    inv_path.write_text(json.dumps(inventory(), indent=2, ensure_ascii=False) + "\n", "utf-8")
    print(f"inventario: {inv_path.relative_to(ROOT)}")

    written: list[Path] = []
    for block in args.blocks or BLOCKS:
        mod = importlib.import_module(f"tools.extract.{block}")
        files = mod.run()
        written.extend(files)
        print(f"{block}: {len(files)} archivos")
    for f in written:
        print("  ", f.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
