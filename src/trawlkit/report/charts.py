"""Gráficos SVG del informe, sin dependencias (sobre :mod:`trawlkit.drawing.svg`).

Cuatro gráficos de un :class:`~trawlkit.model.DesignResult`:

* :func:`towing_chart`: tiro disponible por método frente a la resistencia total, con la ventana
  viable sombreada y la velocidad máxima marcada;
* :func:`drag_methods_chart`: los 13 métodos de RN, la de diseño resaltada y el promedio;
* :func:`drag_breakdown_chart`: barras apiladas RN / RB / Rw / ROB a una velocidad;
* :func:`spread_chart`: DPA y AV de Fridman frente a la velocidad (dos paneles).

Los colores van por variables CSS (paleta categórica validada para fondo claro y oscuro, en
:data:`CHART_STYLE`); el texto usa siempre la tinta del tema, nunca el color de la serie. Cada
marca de datos lleva un ``<title>`` (tooltip nativo, sin JavaScript) y cada serie un atributo
``data-series`` con su clave.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

from trawlkit.drawing.svg import Element, document, line, polyline, rect, text
from trawlkit.report.labels import fmt
from trawlkit.report.tables import METHOD_LABELS, PULL_METHODS, VARIANT_LABELS

if TYPE_CHECKING:
    from trawlkit.model import DesignResult

#: Paleta categórica (orden fijo) para fondo claro y su versión para fondo oscuro.
PALETTE_LIGHT: tuple[str, ...] = (
    "#2a78d6",
    "#eb6834",
    "#1baf7a",
    "#eda100",
    "#e87ba4",
    "#008300",
    "#6250d6",
    "#e34948",
)
PALETTE_DARK: tuple[str, ...] = (
    "#3987e5",
    "#d95926",
    "#199e70",
    "#c98500",
    "#d55181",
    "#008300",
    "#9085e9",
    "#e66767",
)


def _vars(palette: Sequence[str]) -> str:
    return " ".join(f"--s{i}:{c};" for i, c in enumerate(palette, 1))


_SERIES_RULES = "\n".join(
    f".s{i} {{ stroke: var(--s{i}); }} .f{i} {{ fill: var(--s{i}); }}"
    for i in range(1, len(PALETTE_LIGHT) + 1)
)
_DARK = "--ink:#f0efec; --muted:#a3a29b; --grid:#2c2c2a; --axis:#4a4a46; --paper:#1a1a19; " + _vars(
    PALETTE_DARK
)

#: Estilos de los gráficos (se suman a ``BASE_STYLE`` vía ``extra_style``).
CHART_STYLE = f"""
svg.chart {{ --ink:#0b0b0b; --muted:#6f6e69; --grid:#e1e0d9; --axis:#c3c2b7; --paper:#fcfcfb;
  {_vars(PALETTE_LIGHT)}
  font-family: system-ui, -apple-system, "Segoe UI", "Helvetica Neue", Arial, "DejaVu Sans",
  sans-serif; }}
@media (prefers-color-scheme: dark) {{
  svg.chart.themed {{ {_DARK} }}
}}
:root[data-theme="dark"] svg.chart.themed {{ {_DARK} }}
{_SERIES_RULES}
.gridline {{ stroke: var(--grid); stroke-width: 1; fill: none; }}
.axisline {{ stroke: var(--axis); stroke-width: 1; fill: none; }}
.series {{ stroke-width: 2; fill: none; stroke-linejoin: round; stroke-linecap: round; }}
.series.bold {{ stroke-width: 2.75; }}
.series.dashed {{ stroke-dasharray: 7 4; }}
.ink {{ stroke: var(--ink); }}
.context {{ stroke: var(--muted); stroke-width: 1; fill: none; opacity: 0.6; }}
.leader {{ stroke: var(--muted); stroke-width: 0.6; fill: none; }}
.ref {{ stroke: var(--muted); stroke-width: 1; fill: none; stroke-dasharray: 3 3; }}
.window {{ fill: var(--s3); opacity: 0.12; stroke: none; }}
.marker {{ stroke: var(--ink); stroke-width: 1.25; fill: none; stroke-dasharray: 4 3; }}
.dot {{ stroke: var(--paper); stroke-width: 2; }}
.hit {{ fill: transparent; stroke: none; }}
text.tick {{ fill: var(--muted); font-size: 10px; font-variant-numeric: tabular-nums; }}
text.axis-title {{ fill: var(--muted); font-size: 10.5px; }}
text.chart-title {{ font-size: 13px; font-weight: 600; }}
text.legend {{ font-size: 10.5px; }}
text.direct {{ font-size: 10px; }}
text.direct-muted {{ font-size: 9px; fill: var(--muted); }}
""".strip()

WIDTH = 680.0
HEIGHT = 380.0


# ---------------------------------------------------------------------------------------------
# Escalas, ejes y leyenda
# ---------------------------------------------------------------------------------------------


def nice_step(span: float, target: int = 5) -> float:
    """Paso 'redondo' (1, 2, 2.5 o 5 × 10ⁿ) para dividir ``span`` en ~``target`` intervalos."""
    if span <= 0 or not math.isfinite(span):
        return 1.0
    raw = span / max(target, 1)
    mag = 10.0 ** math.floor(math.log10(raw))
    for m in (1.0, 2.0, 2.5, 5.0, 10.0):
        if raw <= m * mag:
            return m * mag
    return 10.0 * mag  # pragma: no cover


def nice_ticks(lo: float, hi: float, target: int = 5) -> list[float]:
    """Marcas redondas que cubren ``[lo, hi]`` (la primera ≤ lo y la última ≥ hi)."""
    if hi < lo:
        lo, hi = hi, lo
    if hi == lo:
        hi = lo + 1.0
    step = nice_step(hi - lo, target)
    start = math.floor(lo / step + 1e-9) * step
    stop = math.ceil(hi / step - 1e-9) * step
    n = int(round((stop - start) / step))
    return [round(start + i * step, 10) for i in range(n + 1)]


def _tick_label(v: float) -> str:
    if abs(v) >= 1000 and float(v).is_integer():
        return f"{int(v):,}".replace(",", " ")
    return f"{v:g}"


@dataclass(frozen=True)
class Plot:
    """Área de trazado: rectángulo en píxeles y dominio de datos."""

    x0: float
    y0: float
    w: float
    h: float
    xmin: float
    xmax: float
    ymin: float
    ymax: float

    def x(self, v: float) -> float:
        """Abscisa en píxeles."""
        return float(self.x0 + (v - self.xmin) / (self.xmax - self.xmin) * self.w)

    def y(self, v: float) -> float:
        """Ordenada en píxeles (crece hacia abajo)."""
        return float(self.y0 + self.h - (v - self.ymin) / (self.ymax - self.ymin) * self.h)

    def pts(self, xs: Sequence[float], ys: Sequence[float]) -> list[tuple[float, float]]:
        """Puntos en píxeles (omite pares no finitos)."""
        return [
            (self.x(float(a)), self.y(float(b)))
            for a, b in zip(xs, ys, strict=True)
            if math.isfinite(float(a)) and math.isfinite(float(b))
        ]


def axes(
    plot: Plot,
    xticks: Sequence[float],
    yticks: Sequence[float],
    xlabel: str,
    ylabel: str,
) -> list[Element]:
    """Rejilla horizontal, línea base, marcas y títulos de ejes (con unidades)."""
    out: list[Element] = []
    for t in yticks:
        y = plot.y(t)
        out.append(line((plot.x0, y), (plot.x0 + plot.w, y), cls="gridline"))
        out.append(text((plot.x0 - 6, y + 3.5), _tick_label(t), cls="tick end"))
    base = plot.y(plot.ymin)
    out.append(line((plot.x0, base), (plot.x0 + plot.w, base), cls="axisline"))
    for t in xticks:
        x = plot.x(t)
        out.append(line((x, base), (x, base + 4), cls="axisline"))
        out.append(text((x, base + 15), _tick_label(t), cls="tick mid"))
    out.append(text((plot.x0 + plot.w / 2, base + 32), xlabel, cls="axis-title mid"))
    out.append(text((plot.x0, plot.y0 - 10), ylabel, cls="axis-title"))
    return out


LegendItem = tuple[str, str, str]
"""(tipo, clases, etiqueta); tipo ∈ {"line", "swatch", "area", "marker"}."""


def legend(items: Sequence[LegendItem], x: float, y: float, max_width: float) -> list[Element]:
    """Leyenda en filas: muestra (línea o cuadro) en el color de la serie y texto en tinta."""
    out: list[Element] = []
    cx, cy = x, y
    for kind, cls, label in items:
        w = 26 + 5.6 * len(label) + 16
        if cx + w > x + max_width and cx > x:
            cx, cy = x, cy + 16
        if kind == "line":
            out.append(line((cx, cy - 3.5), (cx + 20, cy - 3.5), cls=cls))
        elif kind == "marker":
            out.append(line((cx + 10, cy - 10), (cx + 10, cy + 3), cls=cls))
        elif kind == "area":
            out.append(rect(cx, cy - 9, 20, 11, cls=cls))
        else:
            out.append(rect(cx + 4, cy - 9, 11, 11, cls=cls, rx=2))
        out.append(text((cx + 26, cy), label, cls="legend"))
        cx += w
    return out


def legend_height(items: Sequence[LegendItem], max_width: float) -> float:
    """Alto que ocupa :func:`legend` con ese ancho."""
    rows, cx = 1, 0.0
    for _, _, label in items:
        w = 26 + 5.6 * len(label) + 16
        if cx + w > max_width and cx > 0:
            rows, cx = rows + 1, 0.0
        cx += w
    return rows * 16.0


def _series(
    key: str,
    plot: Plot,
    xs: Sequence[float],
    ys: Sequence[float],
    cls: str,
    name: str,
    unit: str = "kgf",
    hit: bool = True,
) -> Element:
    """Serie de línea con ``data-series`` y blancos de hover con su ``<title>`` por punto."""
    g = Element("g", {"data-series": key, "class": "series-group"})
    pl = polyline(plot.pts(xs, ys), cls=cls)
    pl.add(Element("title", text=name))
    g.add(pl)
    if hit:
        for a, b in zip(xs, ys, strict=True):
            if not (math.isfinite(float(a)) and math.isfinite(float(b))):
                continue
            c = Element(
                "circle",
                {"cx": plot.x(float(a)), "cy": plot.y(float(b)), "r": 6.0, "class": "hit"},
            )
            c.add(Element("title", text=f"{name}: {fmt(float(b))} {unit} a {fmt(float(a))} kn"))
            g.add(c)
    return g


def _chart(title_text: str, desc: str, children: list[Element], height: float = HEIGHT) -> str:
    head = [Element("desc", text=desc)]
    return document(
        WIDTH,
        height,
        [*head, *children],
        title_text=title_text,
        extra_style=CHART_STYLE,
    ).replace('class="themed"', 'class="chart themed"', 1)


def _arr(x: Any) -> np.ndarray[Any, np.dtype[np.float64]]:
    return np.asarray(x, dtype=float)


def _spread_labels(
    ends: list[tuple[float, str, str]], top: float, bottom: float, gap: float = 10.0
) -> list[tuple[float, float, str, str]]:
    """Separa etiquetas de fin de línea: (y original, y etiqueta, texto, clase)."""
    order = sorted(ends, key=lambda e: e[0])
    ys = [max(top, min(bottom, e[0])) for e in order]
    for i in range(1, len(ys)):
        ys[i] = max(ys[i], ys[i - 1] + gap)
    overflow = ys[-1] - bottom if ys else 0.0
    if overflow > 0:
        ys = [y - overflow for y in ys]
        for i in range(len(ys) - 2, -1, -1):
            ys[i] = min(ys[i], ys[i + 1] - gap)
    return [(e[0], y, e[1], e[2]) for e, y in zip(order, ys, strict=True)]


# ---------------------------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------------------------


def towing_chart(result: DesignResult) -> str:
    """Tiro disponible por método y resistencia total (estándar/modificada) frente a la velocidad.

    Sombrea la ventana viable del propulsor de diseño con la red estándar (FT ≥ R) y marca la
    velocidad máxima remolcable.
    """
    case = result.case
    v = list(case.speeds_kn)
    curves = result.power.curves
    win = result.performance.design
    pull = [(attr, name, _arr(getattr(curves, attr))) for attr, name in PULL_METHODS]
    demand = [("std", _arr(result.warps.total.std)), ("mod", _arr(result.warps.total.mod))]
    ymax_data = max(float(np.nanmax(a)) for _, _, a in pull)
    ymax_data = max(ymax_data, *(float(np.nanmax(a)) for _, a in demand))
    yt = nice_ticks(0.0, ymax_data, 5)
    xt = nice_ticks(v[0], v[-1], 8)
    items: list[LegendItem] = [
        ("line", f"series s{i}", f"FT {name}") for i, (_, name, _) in enumerate(pull, 1)
    ]
    items += [
        ("line", "series bold ink", "R total estándar"),
        ("line", "series bold ink dashed", "R total modificada"),
        ("area", "window", "Ventana viable"),
    ]
    lw = WIDTH - 84
    lh = legend_height(items, lw)
    top = 44 + lh + 18
    plot = Plot(64, top, WIDTH - 64 - 92, HEIGHT - top - 46, xt[0], xt[-1], yt[0], yt[-1])
    out: list[Element] = [
        text((20, 24), f"Tiro disponible y resistencia total — {case.vessel.id}", "chart-title"),
        *legend(items, 64, 44, lw),
    ]
    feas = [float(s) for s in win.feasible_speeds_kn]
    if feas and win.max_speed_kn is not None:
        x0, x1 = plot.x(min(feas)), plot.x(win.max_speed_kn)
        shade = rect(x0, plot.y0, x1 - x0, plot.h, cls="window")
        shade.add(Element("title", text=f"Ventana viable hasta {fmt(win.max_speed_kn)} kn"))
        out.append(shade)
    out += axes(plot, xt, yt, "Velocidad de arrastre [kn]", "Fuerza [kgf]")
    ends: list[tuple[float, str, str]] = []
    for i, (attr, name, arr) in enumerate(pull, 1):
        out.append(_series(attr, plot, v, list(arr), f"series s{i}", f"FT {name}"))
        ends.append((plot.y(float(arr[-1])), name, "direct-muted"))
    for key, arr in demand:
        dash = " dashed" if key == "mod" else ""
        name = f"R total {VARIANT_LABELS[key]}"
        out.append(_series(f"demand_{key}", plot, v, list(arr), f"series bold ink{dash}", name))
        ends.append((plot.y(float(arr[-1])), name.replace("R total ", "R "), "direct"))
    x_end = plot.x0 + plot.w
    for y_orig, y_lab, label, cls in _spread_labels(ends, plot.y0, plot.y0 + plot.h):
        out.append(polyline([(x_end + 2, y_orig), (x_end + 10, y_lab)], cls="leader"))
        out.append(text((x_end + 12, y_lab + 3.5), label, cls))
    if win.max_speed_kn is not None:
        xm = plot.x(win.max_speed_kn)
        mk = line((xm, plot.y0), (xm, plot.y0 + plot.h), cls="marker")
        mk.add(Element("title", text=f"Velocidad máxima {fmt(win.max_speed_kn)} kn"))
        out.append(Element("g", {"data-marker": "max_speed"}, [mk]))
        out.append(text((xm + 5, plot.y0 + 12), f"v máx = {win.max_speed_kn:.2f} kn", "direct"))
    desc = (
        f"Tiro disponible (Fridman, Prado–Dremière, Koyama, Nomura, Hamuro) del buque "
        f"{case.vessel.id} y resistencia total de la red estándar y modificada entre "
        f"{v[0]:g} y {v[-1]:g} kn. Velocidad máxima remolcable: "
        f"{fmt(win.max_speed_kn)} kn."
    )
    return _chart("Tiro disponible frente a resistencia total", desc, out)


def drag_methods_chart(result: DesignResult, variant: str = "std") -> str:
    """RN de los 13 métodos frente a la velocidad: diseño resaltado, promedio a trazos."""
    from trawlkit.drag import RN_METHODS, average

    table = result.drag.table.kgf
    cols = table.variant(variant)
    v = [float(s) for s in table.speed_kn]
    avg = average(table, result.case.compat)
    avg_v = _arr(avg.std if variant == "std" else avg.mod)
    design = result.drag.design_method
    methods = [m for m in table.columns if m in RN_METHODS]
    ymax = max(float(np.nanmax(_arr(cols[m]))) for m in methods)
    yt = nice_ticks(0.0, max(ymax, float(np.nanmax(avg_v))), 5)
    xt = nice_ticks(v[0], v[-1], 8)
    others = len([m for m in methods if m != design])
    items: list[LegendItem] = [
        ("line", "series bold s1", f"RN de diseño: {METHOD_LABELS[design]}"),
        ("line", "series ink dashed", "Promedio de métodos"),
        ("line", "context", f"Otros métodos ({others})"),
    ]
    lw = WIDTH - 84
    top = 44 + legend_height(items, lw) + 18
    gutter = 150.0
    plot = Plot(64, top, WIDTH - 64 - gutter, HEIGHT - top - 46, xt[0], xt[-1], yt[0], yt[-1])
    title_v = VARIANT_LABELS[variant]
    out: list[Element] = [
        text((20, 24), f"Resistencia de la red {title_v} por método", "chart-title"),
        *legend(items, 64, 44, lw),
        *axes(plot, xt, yt, "Velocidad de arrastre [kn]", "Resistencia de la red RN [kgf]"),
    ]
    ends: list[tuple[float, str, str]] = []
    for m in methods:
        if m == design:
            continue
        arr = _arr(cols[m])
        out.append(_series(m, plot, v, list(arr), "context", METHOD_LABELS[m], hit=True))
        last = arr[np.isfinite(arr)]
        if last.size:
            ends.append((plot.y(float(last[-1])), METHOD_LABELS[m], "direct-muted"))
    out.append(_series("average", plot, v, list(avg_v), "series ink dashed", "Promedio"))
    ends.append((plot.y(float(avg_v[-1])), "Promedio", "direct"))
    d_arr = _arr(cols[design])
    out.append(_series(design, plot, v, list(d_arr), "series bold s1", METHOD_LABELS[design]))
    ends.append((plot.y(float(d_arr[-1])), f"{METHOD_LABELS[design]} (diseño)", "direct"))
    x_end = plot.x0 + plot.w
    for y_orig, y_lab, label, cls in _spread_labels(ends, plot.y0, plot.y0 + plot.h, 10.5):
        out.append(polyline([(x_end + 2, y_orig), (x_end + 12, y_lab)], cls="leader"))
        out.append(text((x_end + 14, y_lab + 3.5), label, cls))
    for a, b in zip(v, d_arr, strict=True):
        out.append(
            Element(
                "circle", {"cx": plot.x(a), "cy": plot.y(float(b)), "r": 3.5, "class": "f1 dot"}
            )
        )
    desc = (
        f"Resistencia de la red {title_v} según {len(methods)} métodos empíricos entre "
        f"{v[0]:g} y {v[-1]:g} kn; la RN de diseño es {METHOD_LABELS[design]}."
    )
    return _chart(f"Resistencia de la red {title_v} por método", desc, out)


def breakdown_values(result: DesignResult, speed_kn: float = 3.5) -> dict[str, dict[str, float]]:
    """Componentes RN, RB, Rw y ROB [kgf] a ``speed_kn`` para cada variante."""
    i = result.case.speed_index(speed_kn)
    rb = float(_arr(result.floats.drag_kgf)[i])
    rw = float(_arr(result.warps.drag_kgf)[i])
    rob = float(_arr(result.doors.forces.drag_kgf)[i])
    variants = ("std", "mod") if result.case.net_modified is not None else ("std",)
    return {
        var: {"RN": float(result.drag.rn.variant(var)[i]), "RB": rb, "Rw": rw, "ROB": rob}
        for var in variants
    }


_PART_LABELS = {
    "RN": "RN red",
    "RB": "RB boyas",
    "Rw": "Rw cables",
    "ROB": "ROB portones",
}


def drag_breakdown_chart(result: DesignResult, speed_kn: float = 3.5) -> str:
    """Barras horizontales apiladas RN / RB / Rw / ROB a ``speed_kn`` (estándar y modificada)."""
    data = breakdown_values(result, speed_kn)
    parts = list(_PART_LABELS)
    items: list[LegendItem] = [("swatch", f"f{i}", _PART_LABELS[p]) for i, p in enumerate(parts, 1)]
    totals = {k: sum(d.values()) for k, d in data.items()}
    xt = nice_ticks(0.0, max(totals.values()), 6)
    lw = WIDTH - 84
    top = 44 + legend_height(items, lw) + 22
    bar = 24.0
    band = 66.0
    height = top + band * len(data) + 64
    excel = result.case.compat.value == "excel"
    if excel:
        height += 16
    plot = Plot(110, top, WIDTH - 110 - 90, band * len(data), xt[0], xt[-1], 0.0, 1.0)
    out: list[Element] = [
        text((20, 24), f"Composición de la resistencia total a {speed_kn:g} kn", "chart-title"),
        *legend(items, 64, 44, lw),
    ]
    for t in xt:
        x = plot.x(t)
        out.append(line((x, plot.y0), (x, plot.y0 + plot.h), cls="gridline"))
        out.append(text((x, plot.y0 + plot.h + 15), _tick_label(t), cls="tick mid"))
    out.append(line((plot.x0, plot.y0), (plot.x0, plot.y0 + plot.h), cls="axisline"))
    out.append(
        text(
            (plot.x0 + plot.w / 2, plot.y0 + plot.h + 32),
            "Resistencia [kgf]",
            cls="axis-title mid",
        )
    )
    for row, (var, d) in enumerate(data.items()):
        yc = plot.y0 + band * row + band / 2
        g = Element("g", {"data-series": var, "class": "bar"})
        out.append(text((plot.x0 - 8, yc + 3.5), f"Red {VARIANT_LABELS[var]}", "legend end"))
        acc = 0.0
        for i, p in enumerate(parts, 1):
            x0, x1 = plot.x(acc), plot.x(acc + d[p])
            acc += d[p]
            w = max(x1 - x0 - 2.0, 0.6)  # 2 px de separación entre segmentos
            seg = rect(x0, yc - bar / 2, w, bar, cls=f"f{i}", rx=0)
            seg.attrs["data-part"] = p
            seg.add(Element("title", text=f"{_PART_LABELS[p]}: {fmt(round(d[p], 2))} kgf"))
            g.add(seg)
        out.append(g)
        total_txt = f"{fmt(round(totals[var], 1))} kgf"
        out.append(text((plot.x(acc) + 6, yc + 3.5), total_txt, "direct"))
        detail = " · ".join(f"{p} {fmt(round(d[p], 1))}" for p in parts)
        out.append(text((plot.x0, yc + bar / 2 + 12), f"{detail} kgf", "direct-muted"))
    if excel:
        out.append(
            text(
                (20, height - 10),
                "Modo EXCEL: el total del libro (Rem!H118) omite ROB; aquí se muestra sumado.",
                "direct-muted",
            )
        )
    desc = "; ".join(
        f"red {VARIANT_LABELS[k]}: " + ", ".join(f"{p} {fmt(round(x, 1))}" for p, x in d.items())
        for k, d in data.items()
    )
    return _chart(f"Composición de la resistencia a {speed_kn:g} kn", desc + " (kgf)", out, height)


def spread_chart(result: DesignResult) -> str:
    """DPA y AV de Fridman (estándar y modificada) frente a la velocidad, en dos paneles."""
    s = result.spread
    v = [float(x) for x in result.case.speeds_kn]
    has_mod = result.case.net_modified is not None
    variants = ("std", "mod") if has_mod else ("std",)
    dpa = {"std": _arr(s.fridman.dpa_std_m), "mod": _arr(s.fridman.dpa_mod_m)}
    av = {"std": _arr(s.vertical.fridman.std.av_m), "mod": _arr(s.vertical.fridman.mod.av_m)}
    items: list[LegendItem] = [
        ("line", f"series s{i}", f"Red {VARIANT_LABELS[k]}") for i, k in enumerate(variants, 1)
    ]
    items.append(("line", "ref", "Valor de diseño"))
    lw = WIDTH - 84
    top = 44 + legend_height(items, lw) + 34
    out: list[Element] = [
        text((20, 24), "Aberturas de la red según Fridman", "chart-title"),
        *legend(items, 64, 44, lw),
    ]
    panel_w = (WIDTH - 64 - 40 - 60) / 2
    panels: list[tuple[str, str, dict[str, Any], float, str]] = [
        ("dpa", "DPA — distancia entre puntas de alas [m]", dpa, s.horizontal_opening_m, "AH"),
        ("av", "AV — abertura vertical [m]", av, s.vertical.suzuki_m, "AV Suzuki"),
    ]
    for j, (key, ylabel, series, ref, ref_name) in enumerate(panels):
        hi = max(float(np.nanmax(series[k])) for k in variants)
        yt = nice_ticks(0.0, max(hi, ref), 5)
        xt = nice_ticks(v[0], v[-1], 4)
        x0 = 56 + j * (panel_w + 60)
        plot = Plot(x0, top, panel_w, HEIGHT - top - 46, xt[0], xt[-1], yt[0], yt[-1])
        out += axes(plot, xt, yt, "Velocidad [kn]", ylabel)
        yr = plot.y(ref)
        r = line((plot.x0, yr), (plot.x0 + plot.w, yr), cls="ref")
        r.add(Element("title", text=f"{ref_name} = {fmt(ref)} m"))
        out.append(r)
        out.append(
            text((plot.x0 + plot.w - 2, yr - 4), f"{ref_name} {ref:.2f} m", "direct-muted end")
        )
        for i, k in enumerate(variants, 1):
            name = f"{key.upper()} {VARIANT_LABELS[k]}"
            out.append(_series(f"{key}_{k}", plot, v, list(series[k]), f"series s{i}", name, "m"))
    desc = (
        f"DPA y AV de Baranov–Fridman entre {v[0]:g} y {v[-1]:g} kn. AH de diseño "
        f"{fmt(s.horizontal_opening_m)} m, AV de Suzuki {fmt(s.vertical.suzuki_m)} m."
    )
    return _chart("Aberturas de la red según Fridman", desc, out)


ChartFn = Callable[["DesignResult"], str]


def all_charts(result: DesignResult) -> dict[str, str]:
    """Todos los gráficos del informe, por clave (orden de presentación)."""
    out = {
        "remolque": towing_chart(result),
        "resistencia_std": drag_methods_chart(result, "std"),
    }
    if result.case.net_modified is not None:
        out["resistencia_mod"] = drag_methods_chart(result, "mod")
    speed = result.case.warp_design_speed_kn
    out["composicion"] = drag_breakdown_chart(result, speed)
    out["aberturas"] = spread_chart(result)
    return out


CHART_TITLES: dict[str, str] = {
    "remolque": "Tiro disponible frente a resistencia total",
    "resistencia_std": "Resistencia de la red estándar por método",
    "resistencia_mod": "Resistencia de la red modificada por método",
    "composicion": "Composición de la resistencia total",
    "aberturas": "Aberturas de la red (Fridman)",
}

__all__ = [
    "CHART_STYLE",
    "CHART_TITLES",
    "PALETTE_DARK",
    "PALETTE_LIGHT",
    "Plot",
    "all_charts",
    "axes",
    "breakdown_values",
    "drag_breakdown_chart",
    "drag_methods_chart",
    "legend",
    "nice_ticks",
    "spread_chart",
    "towing_chart",
]
