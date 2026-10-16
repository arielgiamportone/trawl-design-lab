"""Helpers de los capítulos de caso de estudio y validación (30, 31, 32 y erratas).

Reutiliza la paleta, el estilo y las tablas HTML de ``_plots_t1`` y agrega:

* :func:`fao_case` / :func:`run_case`: el caso FAO A-3 del libro (red estándar + modificada,
  buque de diseño con el otro buque de la clase, portón FAO), con caché por (BHP, modo).
* :func:`golden_coverage`: cobertura de los valores golden por los tests del motor.
* :func:`pct`, :func:`sheet_svg`: utilidades menores.
"""

from __future__ import annotations

import ast
import html
import json
import re
from collections.abc import Sequence
from functools import cache
from pathlib import Path

from _plots_t1 import (  # noqa: F401  (re-exportados para los capítulos)
    AXIS,
    BLUE_150,
    BLUE_300,
    BLUE_450,
    BLUE_600,
    GRID,
    INK,
    INK_2,
    MUTED,
    SERIES,
    SURFACE,
    end_label,
    fmt,
    setup_style,
)
from IPython.display import HTML, SVG, display

from trawlkit import Compat, DesignCase, run
from trawlkit.io import load_doors, load_net, load_vessels
from trawlkit.model import DesignResult

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_DIR = ROOT / "tests" / "golden"
TESTS_DIR = ROOT / "tests"

#: Nombre legible de cada JSON golden (hoja del libro).
SHEET_NAMES: dict[str, str] = {
    "especie_blanco": "Especie Blanco",
    "tipo_de_buques": "Tipo de buques",
    "potenc_disponible_para_arrastre": "Potenc disponible",
    "potencia_disponible_arrastre_ok": "Potencia Disp. Arrastre OK",
    "panos_de_red_y_cortes": "Paños de red y cortes",
    "mecanica_de_la_red": "Mecánica de la Red",
    "dimensiones_de_la_red": "Dimensiones de la Red",
    "resistencia_de_la_red": "Resistencia de la RED",
    "portones_y_aparejamiento": "Portones y aparejamiento",
    "flotacion_y_lastre": "Flotación y Lastre",
    "cables_de_remolque": "Cables de Remolque",
    "cables_y_cabulleria": "Cables Y Cabulleria",
    "tablas_de_referencias": "Tablas de Referencias",
}


_NUM = re.compile(r"^[+−-]?[\d\u202f]+(,\d+)?( (%|[a-zA-Z]{1,3}))?( \(.*\))?$")


def md_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> None:
    """Tabla HTML como la de ``_plots_t1.md_table``; alinea a la derecha también ``+1,2`` y ``3 %``.

    ``**x**`` en una celda la resalta. MyST-NB no renderiza tablas en salidas ``text/markdown``.
    """

    def cell(c: object, tag: str) -> str:
        raw = str(c)
        bold = raw.startswith("**") and raw.endswith("**") and len(raw) > 4
        core = raw[2:-2] if bold else raw
        s = html.escape(core)
        if bold:
            s = f"<strong>{s}</strong>"
        align = ' style="text-align:right"' if tag == "td" and _NUM.match(core) else ""
        return f"<{tag}{align}>{s}</{tag}>"

    head = "".join(cell(h, "th") for h in headers)
    body = "".join("<tr>" + "".join(cell(c, "td") for c in r) + "</tr>" for r in rows)
    display(
        HTML(f'<table class="table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>')
    )


def fao_case(bhp: int = 150, compat: Compat = Compat.CORRECTED, **kw: object) -> DesignCase:
    """Caso FAO A-3 del libro: estándar + modificada, buque ``bhp`` y el otro de la clase."""
    vessels = {v.id: v for v in load_vessels().vessels}
    design = vessels[f"fao_a3_{bhp}hp"]
    others = tuple(v for v in vessels.values() if v.id != design.id)
    return DesignCase(
        net=load_net("fao_a3_standard"),
        net_modified=load_net("fao_a3_modified"),
        vessel=design,
        class_vessels=others,
        door=load_doors().doors[0],
        compat=compat,
        **kw,  # type: ignore[arg-type]
    )


@cache
def run_case(bhp: int = 150, compat: str = "corrected") -> DesignResult:
    """Corre :func:`fao_case` (con caché por buque y modo)."""
    return run(fao_case(bhp, Compat(compat)))


def pct(new: float, ref: float) -> float:
    """Diferencia relativa ``(new - ref)/ref`` en %."""
    return (new - ref) / ref * 100.0


def pct_s(new: float, ref: float, nd: int = 1) -> str:
    """:func:`pct` formateado con signo y coma decimal."""
    p = pct(new, ref)
    s = fmt(abs(p), nd)
    if s.strip("0,") == "":
        return fmt(0.0, nd)
    return ("+" if p > 0 else "−") + s


def sfmt(x: float, nd: int = 2) -> str:
    """Número con signo explícito (+/−) y coma decimal."""
    s = fmt(abs(x), nd)
    if s.strip("0,") == "":
        return s
    return ("+" if x > 0 else "−") + s


def sheet_svg(result: DesignResult, variant: str) -> SVG:
    """Lámina A3 de la red como salida SVG de la celda (el rótulo lleva el año del libro)."""
    from trawlkit.drawing import net_sheet_svg

    return SVG(net_sheet_svg(result, variant, year=2026))


# ---------------------------------------------------------------------------------------------
# Cobertura de los golden
# ---------------------------------------------------------------------------------------------


#: Hueco de una plantilla ({hp}, {column}…): una o más palabras de la clave.
_SLOT = "[a-z0-9_]+"


def _add_pattern(patterns: list[re.Pattern[str]], rx: str) -> None:
    """Agrega la plantilla sólo si tiene texto fijo suficiente (≥ 5 letras fuera de los huecos)."""
    fixed = re.sub(r"\\.", "", rx.replace(_SLOT, ""))
    if sum(c.isalpha() for c in fixed) >= 5:
        patterns.append(re.compile(rx))


def _test_strings(path: Path) -> tuple[set[str], list[re.Pattern[str]]]:
    """Literales de texto de un test y patrones de sus f-strings y plantillas ``.format``."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    literals: set[str] = set()
    patterns: list[re.Pattern[str]] = []
    fstring_parts: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            parts = []
            for v in node.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    fstring_parts.add(id(v))
                    parts.append(re.escape(v.value))
                else:
                    parts.append(_SLOT)
            _add_pattern(patterns, "".join(parts))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in fstring_parts:
                continue
            s = node.value
            literals.add(s)
            if "{" in s and "}" in s:
                _add_pattern(patterns, re.sub(r"\\\{[^}]*\\\}", _SLOT, re.escape(s)))
    return literals, patterns


@cache
def _engine_test_index() -> tuple[frozenset[str], tuple[re.Pattern[str], ...]]:
    """Índice de textos de los tests del motor (excluye ``test_golden.py``, que valida el JSON)."""
    lits: set[str] = set()
    pats: list[re.Pattern[str]] = []
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        if path.name == "test_golden.py":
            continue
        a, b = _test_strings(path)
        lits |= a
        pats += b
    return frozenset(lits), tuple(pats)


def key_is_tested(key: str, literal_only: bool = False) -> bool:
    """Indica si algún test del motor nombra la clave (literal, f-string o plantilla ``format``)."""
    lits, pats = _engine_test_index()
    if key in lits:
        return True
    return not literal_only and any(p.fullmatch(key) for p in pats)


def golden_coverage() -> list[dict[str, object]]:
    """Por hoja: claves golden, estáticas, calculadas y cuántas de éstas usan los tests."""
    rows = []
    for slug, name in SHEET_NAMES.items():
        doc = json.loads((GOLDEN_DIR / f"{slug}.json").read_text(encoding="utf-8"))
        entries = {**doc["values"], **doc.get("series", {})}
        static = {k for k, e in entries.items() if e.get("static")}
        computed = [k for k in entries if k not in static]
        tested = [k for k in computed if key_is_tested(k)]
        literal = [k for k in computed if key_is_tested(k, literal_only=True)]
        rows.append(
            {
                "slug": slug,
                "sheet": name,
                "keys": len(entries),
                "values": len(doc["values"]),
                "series": len(doc.get("series", {})),
                "static": len(static),
                "computed": len(computed),
                "tested": len(tested),
                "tested_literal": len(literal),
                "untested_keys": [k for k in computed if k not in tested],
                "static_tested": sum(key_is_tested(k) for k in static),
            }
        )
    return rows
