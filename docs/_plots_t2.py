"""Utilidades de gráficos y del caso FAO A-3 para los capítulos 15–19.

Paleta categórica de referencia (validada con el validador de la skill *dataviz*: lightness band,
chroma, separación CVD ≥ 9.1 y visión normal ≥ 19.6 entre pares adyacentes, superficie clara).
Los tonos aqua, amarillo y magenta quedan por debajo de 3:1 frente a la superficie, por lo que
toda figura lleva leyenda y etiquetas directas, y los capítulos muestran además la tabla de datos.

Reglas aplicadas: colores asignados en orden fijo (nunca ciclados), líneas de 2 px, marcadores
≥ 8 px con anillo del color de la superficie, rejilla fina y recesiva, un solo eje vertical y el
texto en tinta neutra (nunca del color de la serie).
"""

from __future__ import annotations

import sys
from functools import cache
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

#: Orden fijo de la paleta categórica (slot 1 → 8).
SERIES = (
    "#2a78d6",  # 1 azul
    "#eb6834",  # 2 naranja
    "#1baf7a",  # 3 aqua
    "#eda100",  # 4 amarillo
    "#e87ba4",  # 5 magenta
    "#008300",  # 6 verde
    "#6250d6",  # 7 violeta
    "#e34948",  # 8 rojo
)
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
#: Neutro para referencias (rangos, límites) que no son una serie.
NEUTRAL = "#898781"
NEUTRAL_WASH = "#e9e8e2"
#: Estado "bueno" (zona viable); siempre acompañado de etiqueta.
GOOD = "#0ca30c"

MARKERS = ("o", "s", "D", "^", "v", "P", "X", "*")


def setup() -> None:
    """Estilo global de matplotlib para el libro (llamar una vez por capítulo)."""
    mpl.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "figure.dpi": 110,
            "savefig.dpi": 150,
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans", "Liberation Sans", "Arial"],
            "font.size": 10.5,
            "axes.edgecolor": AXIS,
            "axes.labelcolor": INK_2,
            "axes.titlecolor": INK,
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
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
            "legend.frameon": False,
            "legend.fontsize": 9,
            "legend.labelcolor": INK_2,
            "lines.linewidth": 2.0,
            "lines.solid_capstyle": "round",
            "lines.solid_joinstyle": "round",
            "lines.markersize": 7,
            "lines.markeredgewidth": 1.5,
            "lines.markeredgecolor": SURFACE,
            "axes.prop_cycle": mpl.cycler(color=list(SERIES)),
        }
    )


def color(slot: int) -> str:
    """Color de la serie en la posición ``slot`` (1–8) de la paleta."""
    return SERIES[slot - 1]


def line(ax, x, y, slot: int, label: str, marker: bool = True, **kw):
    """Línea de 2 px con marcadores anillados en el color de la superficie."""
    style = {"color": color(slot), "label": label, "lw": 2.0}
    if marker:
        style.update(marker=MARKERS[(slot - 1) % len(MARKERS)], ms=7, mec=SURFACE, mew=1.5)
    style.update(kw)
    return ax.plot(x, y, **style)[0]


def end_label(ax, x, y, text: str, dx: float = 0.06, dy: float = 0.0, **kw) -> None:
    """Etiqueta directa al final de una serie, en tinta secundaria (no del color de la serie)."""
    ax.annotate(
        text,
        xy=(x, y),
        xytext=(x + dx, y + dy),
        textcoords="data",
        color=INK_2,
        fontsize=9,
        va="center",
        ha="left",
        **kw,
    )


def legend(ax, **kw):
    """Leyenda sin marco, arriba a la izquierda por defecto."""
    opts = {"loc": "upper left"}
    opts.update(kw)
    return ax.legend(**opts)


def finish(fig) -> None:
    """Ajuste final de márgenes."""
    fig.tight_layout()


def speed_axis(ax, label: str = "Velocidad de arrastre v [kn]") -> None:
    """Eje de velocidades del libro (1–5 kn)."""
    ax.set_xlabel(label)
    ax.set_xticks([1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5])
    ax.set_xlim(0.9, 5.1)


@cache
def _vessels():
    from trawlkit.io import load_vessels

    return {v.id: v for v in load_vessels().vessels}


def fao_case(bhp: int = 150, compat=None, **overrides):
    """Caso FAO A-3 del libro: red estándar + modificada, buque ``bhp`` y el otro de la clase.

    Igual que ``tests/test_case_fao_a3.py``. ``compat`` por defecto es ``Compat.EXCEL``.
    """
    from trawlkit import Compat, DesignCase
    from trawlkit.io import load_doors, load_net

    vessels = _vessels()
    design = vessels[f"fao_a3_{bhp}hp"]
    others = tuple(v for v in vessels.values() if v.id != design.id)
    return DesignCase(
        net=load_net("fao_a3_standard"),
        net_modified=load_net("fao_a3_modified"),
        vessel=design,
        class_vessels=others,
        door=load_doors().doors[0],
        compat=Compat.EXCEL if compat is None else compat,
        **overrides,
    )


@cache
def fao_result(bhp: int = 150, compat_value: str = "excel"):
    """``run(fao_case(...))`` cacheado por buque y modo (``"excel"`` o ``"corrected"``)."""
    from trawlkit import Compat, run

    return run(fao_case(bhp, Compat(compat_value)))


__all__ = [
    "AXIS",
    "GOOD",
    "GRID",
    "INK",
    "INK_2",
    "MUTED",
    "NEUTRAL",
    "NEUTRAL_WASH",
    "SERIES",
    "SURFACE",
    "color",
    "end_label",
    "fao_case",
    "fao_result",
    "finish",
    "legend",
    "line",
    "plt",
    "setup",
    "speed_axis",
]
