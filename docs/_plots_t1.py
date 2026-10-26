"""Estilo común de las figuras de los capítulos 10-14 (paleta validada y helpers de matplotlib).

Paleta categórica en orden fijo (nunca ciclada): el método de diseño o la serie principal ocupa
siempre la ranura 1 (azul). Validada con el validador de la guía de visualización (modo claro,
superficie ``#fcfcfb``): separación CVD y visión normal OK en pares adyacentes; las ranuras 3-5
quedan por debajo de 3:1 de contraste, por lo que las series llevan etiqueta directa o tabla.
"""

from __future__ import annotations

from _lang import LANG

import html
from collections.abc import Sequence

import matplotlib as mpl
import matplotlib.pyplot as plt
from IPython.display import HTML, display

#: Ranuras categóricas (modo claro), en orden fijo.
SERIES: tuple[str, ...] = (
    "#2a78d6",  # 1 azul
    "#eb6834",  # 2 naranja
    "#1baf7a",  # 3 aqua
    "#eda100",  # 4 amarillo
    "#e87ba4",  # 5 magenta
    "#008300",  # 6 verde
)

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
#: Rampa secuencial azul (pasos 150, 300, 450, 600) para rellenos.
BLUE_150 = "#b7d3f6"
BLUE_300 = "#6da7ec"
BLUE_450 = "#2a78d6"
BLUE_600 = "#184f95"


def setup_style() -> None:
    """Aplica el estilo de figura (superficie clara, grilla tenue, líneas de 2 px)."""
    mpl.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "figure.dpi": 110,
            "savefig.dpi": 150,
            "font.family": "sans-serif",
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.labelsize": 10,
            "axes.labelcolor": INK_2,
            "axes.edgecolor": AXIS,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "grid.linestyle": "-",
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "xtick.labelcolor": INK_2,
            "ytick.labelcolor": INK_2,
            "xtick.major.size": 0,
            "ytick.major.size": 0,
            "lines.linewidth": 2.0,
            "lines.solid_capstyle": "round",
            "lines.solid_joinstyle": "round",
            "lines.markersize": 6,
            "legend.frameon": False,
            "legend.fontsize": 9,
            "text.color": INK,
            "axes.prop_cycle": mpl.cycler(color=list(SERIES)),
        }
    )


def end_label(
    ax: plt.Axes, x: float, y: float, text: str, color: str = INK_2, dy: float = 0.0, **kw: object
) -> None:
    """Etiqueta directa al final de una línea (texto en tinta, no en el color de la serie)."""
    ax.annotate(
        text,
        xy=(x, y),
        xytext=(6, dy),
        textcoords="offset points",
        va="center",
        ha="left",
        fontsize=8.5,
        color=color,
        **kw,
    )


def fmt(x: float, nd: int = 2) -> str:
    """Número con el separador decimal del libro (coma en español, punto en inglés)."""
    s = f"{x:,.{nd}f}".replace(",", "\u202f")
    return s if LANG == "en" else s.replace(".", ",")


def md_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> None:
    """Muestra una tabla en la salida de la celda (HTML; ``**x**`` en una celda la resalta).

    MyST-NB renderiza las salidas ``text/markdown`` como CommonMark sin tablas, por eso se emite
    HTML. Usar símbolos Unicode (U₁, Sₛ, θ) en lugar de LaTeX dentro de las celdas.
    """

    def cell(c: object, tag: str) -> str:
        s = html.escape(str(c))
        if s.startswith("**") and s.endswith("**") and len(s) > 4:
            s = f"<strong>{s[2:-2]}</strong>"
        elif s.startswith("*") and s.endswith("*") and len(s) > 2:
            s = f"<em>{s[1:-1]}</em>"
        align = "" if tag == "th" else ' style="text-align:right"' if _numeric(s) else ""
        return f"<{tag}{align}>{s}</{tag}>"

    head = "".join(cell(h, "th") for h in headers)
    body = "".join("<tr>" + "".join(cell(c, "td") for c in r) + "</tr>" for r in rows)
    display(
        HTML(f'<table class="table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>')
    )


def _numeric(s: str) -> bool:
    t = s.replace("\u202f", "").replace(",", "").replace(".", "").replace("−", "").replace("-", "")
    return t.isdigit()
