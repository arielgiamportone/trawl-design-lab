"""Vista a escala real de la red relingada, para fabricación.

:func:`net_scale_svg` dibuja el dorso y el vientre con :func:`~trawlkit.drawing.layout.layout_net`
en modo ``"true_scale"`` (ancho = mallas · mallero · U1, alto = N · mallero · U2) a una misma
escala en x e y, sobre una cuadrícula de 1 m, con cotas de alto por panel, anchos superior e
inferior, ancho de boca y largo total, una escala gráfica y una tabla de medidas por panel. La
leyenda compara el largo relingado con el estirado de :class:`~trawlkit.dimensions.NetDimensions`.
"""

from __future__ import annotations

import math
from typing import Literal

from trawlkit.drawing import svg
from trawlkit.drawing.layout import NetLayout, PanelShape, layout_net
from trawlkit.drawing.sheet import SHEET_H, SHEET_W, fmt_es, spec_for, text_width
from trawlkit.model import DesignResult

#: Resolución de la lámina: 96 px por pulgada → mm por unidad de usuario.
MM_PER_PX: float = 25.4 / 96.0

SCALE_STYLE = """
.frame { stroke: var(--ink); stroke-width: 1.4; fill: none; }
.net-panel { stroke: var(--ink); stroke-width: 1; fill: var(--fill); fill-opacity: 0.85; }
.dim { stroke: var(--accent); stroke-width: 0.7; fill: none; }
.dim-ext { stroke: var(--accent); stroke-width: 0.5; fill: none; stroke-dasharray: 2 2; }
.bar-fill { fill: var(--ink); stroke: var(--ink); stroke-width: 0.8; }
.bar-empty { fill: var(--paper); stroke: var(--ink); stroke-width: 0.8; }
text.num { font-size: 9px; }
text.dimtxt { font-size: 9px; fill: var(--accent); }
text.letter { font-size: 14px; }
text.big { font-size: 12px; }
text.bold { font-weight: 700; }
""".strip()


class _Px:
    """Metros → px con escala uniforme ``k`` [px/m]."""

    def __init__(self, cx: float, y0: float, k: float) -> None:
        self.cx, self.y0, self.k = cx, y0, k

    def x(self, x: float) -> float:
        return self.cx + x * self.k

    def y(self, y: float) -> float:
        return self.y0 + y * self.k

    def p(self, pt: tuple[float, float]) -> tuple[float, float]:
        return (self.x(pt[0]), self.y(pt[1]))


def _hdim(x1: float, x2: float, y: float, label: str, above: bool) -> list[svg.Element]:
    """Cota horizontal con trazos de extremo y texto encima o debajo."""
    out = [
        svg.line((x1, y), (x2, y), cls="dim"),
        svg.line((x1, y - 3), (x1, y + 3), cls="dim"),
        svg.line((x2, y - 3), (x2, y + 3), cls="dim"),
    ]
    narrow = x2 - x1 < text_width(label, 9) + 4
    ty = y - 3 if above else y + 10
    if narrow:
        out.append(svg.text((x2 + 3, y + 3), label, cls="dimtxt"))
    else:
        out.append(svg.text(((x1 + x2) / 2, ty), label, cls="dimtxt mid"))
    return out


def _vdim(x: float, y1: float, y2: float, label: str, left: bool) -> list[svg.Element]:
    """Cota vertical con trazos de extremo y texto girado a un lado."""
    out = [
        svg.line((x, y1), (x, y2), cls="dim"),
        svg.line((x - 3, y1), (x + 3, y1), cls="dim"),
        svg.line((x - 3, y2), (x + 3, y2), cls="dim"),
    ]
    tx = x - 4 if left else x + 11
    out.append(svg.text((tx, (y1 + y2) / 2), label, cls="dimtxt mid", rotate=-90))
    return out


def _plane(
    layout: NetLayout, plane: str, px: _Px, side: Literal["left", "right"], title: str
) -> list[svg.Element]:
    """Un plano a escala: cuadrícula, paneles, cotas."""
    out: list[svg.Element] = []
    xmin, ymin, xmax, ymax = layout.plane_bbox(plane)
    gx0, gx1 = math.floor(xmin) - 1, math.ceil(xmax) + 1
    gy0, gy1 = math.floor(ymin) - 1, math.ceil(ymax) + 1
    for gx in range(gx0, gx1 + 1):
        out.append(svg.line((px.x(gx), px.y(gy0)), (px.x(gx), px.y(gy1)), cls="grid"))
    for gy in range(gy0, gy1 + 1):
        out.append(svg.line((px.x(gx0), px.y(gy)), (px.x(gx1), px.y(gy)), cls="grid"))
    out.append(svg.text((px.cx, px.y(gy0) - 26), title, cls="big mid bold"))

    shapes = layout.shapes[plane]
    for s in shapes:
        out.append(svg.polygon([px.p(p) for p in s.points], cls="net-panel"))
    for s in shapes:
        c = px.p(s.centroid)
        out.append(svg.text((c[0], c[1] + 5), s.id, cls="letter mid"))

    # Anchos superior e inferior (paneles centrales y alas del lado anotado).
    # Un ancho superior igual al inferior del panel de arriba (misma cadena) se acota una vez;
    # el del primer panel central es la boca, acotada aparte.
    annotated: list[PanelShape] = [t for t in shapes if t.side in ("center", side)]
    central = layout.central(plane)
    for s in annotated:
        xt = (px.x(s.x_top[0]) + 1, px.x(s.x_top[1]) - 1)
        xb = (px.x(s.x_bottom[0]) + 1, px.x(s.x_bottom[1]) - 1)
        yt, yb = px.y(s.y_top), px.y(s.y_bottom)
        chain = [t for t in annotated if t.side == s.side]
        i = chain.index(s)
        above = chain[i - 1] if i > 0 else None
        repeated = above is not None and math.isclose(above.width_bottom, s.width_top)
        if central and s is central[0]:
            repeated = True
        if repeated:
            pass
        elif xt[1] - xt[0] > 6:
            out += _hdim(xt[0], xt[1], yt + 5, f"{fmt_es(s.width_top)} m", above=False)
        else:
            out.append(svg.text((xt[1] + 4, yt - 2), f"{fmt_es(s.width_top)} m", cls="dimtxt"))
        out += _hdim(xb[0], xb[1], yb - 5, f"{fmt_es(s.width_bottom)} m", above=True)

    # Altos por panel y largo total, del lado exterior.
    bands = layout.bands[plane]
    if side == "right":  # cotas a la izquierda del plano
        x_chain, x_total, left = px.x(xmin) - 16, px.x(xmin) - 46, True
    else:
        x_chain, x_total, left = px.x(xmax) + 16, px.x(xmax) + 46, False
    for b in bands:
        out += _vdim(x_chain, px.y(b.y_top), px.y(b.y_bottom), fmt_es(b.y_bottom - b.y_top), left)
    total = layout.length(plane)
    out += _vdim(x_total, px.y(ymin), px.y(ymax), f"Largo total {fmt_es(total)} m", left)

    # Ancho de boca: borde superior del primer panel central.
    if central:
        m = central[0]
        y_cota = px.y(ymin) - 8
        xa, xb2 = px.x(m.x_top[0]), px.x(m.x_top[1])
        out.append(svg.line((xa, y_cota), (xa, px.y(m.y_top)), cls="dim-ext"))
        out.append(svg.line((xb2, y_cota), (xb2, px.y(m.y_top)), cls="dim-ext"))
        out += _hdim(xa, xb2, y_cota, f"Boca {fmt_es(m.width_top)} m", above=True)
    return out


def _scale_bar(x: float, y: float, k: float, metres: int = 5) -> list[svg.Element]:
    out: list[svg.Element] = [svg.text((x, y - 10), "Escala gráfica", cls="bold")]
    for i in range(metres):
        out.append(svg.rect(x + i * k, y, k, 6, cls="bar-fill" if i % 2 == 0 else "bar-empty"))
    for i in range(metres + 1):
        out.append(svg.text((x + i * k, y + 18), str(i), cls="num mid"))
    out.append(svg.text((x + metres * k + 8, y + 7), "m", cls="num"))
    ratio = 1000.0 / (k * MM_PER_PX)
    out.append(
        svg.text(
            (x, y + 34),
            f"1 m = {fmt_es(k, 1)} px · ≈ 1:{round(ratio):d} impreso en A3 (96 dpi)",
            cls="small",
        )
    )
    return out


def net_scale_svg(result: DesignResult, variant: str = "std") -> str:
    """Vista a escala real (SVG A3) del dorso y del vientre relingados de la variante."""
    spec = spec_for(result, variant)
    dims = result.dimensions.variant(variant)
    hung = layout_net(spec, "true_scale")
    stretched = layout_net(spec, "true_scale", stretched=True)

    margin = 36.0
    top, bottom = 140.0, SHEET_H - margin - 40.0
    max_len = max(hung.length(p) for p in ("upper", "lower"))
    k = (bottom - top) / (max_len + 2.0)
    half = max(max(abs(v) for v in hung.plane_bbox(p)[::2]) for p in ("upper", "lower"))
    cx_up = margin + 120 + half * k
    cx_lo = cx_up + 2 * half * k + 210
    px_up, px_lo = _Px(cx_up, top + k, k), _Px(cx_lo, top + k, k)

    children: list[svg.Element] = [
        svg.rect(margin, margin, SHEET_W - 2 * margin, SHEET_H - 2 * margin, cls="frame"),
        svg.text((margin + 16, margin + 28), spec.name, cls="title"),
        svg.text(
            (margin + 16, margin + 46),
            "Vista a escala real — red relingada: ancho = mallas · mallero · U1, "
            "alto = N · mallero · U2 (U2 = √(1 − U1²)). Cuadrícula de 1 m.",
            cls="muted-text",
        ),
    ]
    children += _plane(hung, "upper", px_up, "right", "PLANO SUPERIOR (DORSO)")
    children += _plane(hung, "lower", px_lo, "left", "PLANO INFERIOR (VIENTRE)")

    # Leyenda.
    lx = max(cx_lo + half * k + 90, SHEET_W - margin - 420)
    ly = top + 10
    children += _scale_bar(lx, ly, k)
    ly += 70
    children.append(svg.text((lx, ly), "Largos", cls="bold"))
    rows = [
        ("Plano", "estirado", "relingado"),
        *[
            (
                "Dorso" if p == "upper" else "Vientre",
                f"{fmt_es(stretched.length(p))} m",
                f"{fmt_es(hung.length(p))} m",
            )
            for p in ("upper", "lower")
        ],
    ]
    for i, (a, b, c) in enumerate(rows):
        yy = ly + 18 + i * 15
        cls = "small bold" if i == 0 else "small"
        children += [
            svg.text((lx, yy), a, cls=cls),
            svg.text((lx + 150, yy), b, cls=cls + " end"),
            svg.text((lx + 240, yy), c, cls=cls + " end"),
        ]
    ly += 18 + len(rows) * 15 + 4
    children.append(
        svg.text(
            (lx, ly),
            f"Largo total (NetDimensions, estirado): {fmt_es(dims.total_length_m)} m",
            cls="small",
        )
    )
    ly += 13
    children.append(
        svg.text(
            (lx, ly),
            f"Ancho de boca relingado: {fmt_es(hung.central('upper')[0].width_top)} m",
            cls="small",
        )
    )

    # Tabla de medidas por panel.
    ly += 30
    children.append(svg.text((lx, ly), "Medidas relingadas por panel [m]", cls="bold"))
    heads = ("Panel", "U1", "U2", "Ancho sup.", "Ancho inf.", "Alto")
    cols = (lx, lx + 70, lx + 110, lx + 175, lx + 240, lx + 290)
    ly += 18
    for h, cx in zip(heads, cols, strict=True):
        children.append(svg.text((cx, ly), h, cls="small bold" + ("" if cx == lx else " end")))
    seen: set[str] = set()
    for plane in ("upper", "lower"):
        for s in hung.shapes[plane]:
            if s.id in seen or s.side == "left":
                continue
            seen.add(s.id)
            ly += 14
            u1 = s.hanging_ratio or 0.0
            vals = (
                s.id,
                fmt_es(u1, 2),
                fmt_es(math.sqrt(1 - u1 * u1), 3),
                fmt_es(s.width_top),
                fmt_es(s.width_bottom),
                fmt_es(s.height),
            )
            for v, cx in zip(vals, cols, strict=True):
                children.append(svg.text((cx, ly), v, cls="small" + ("" if cx == lx else " end")))

    # Pegaduras con bordes relingados distintos (U1 distinto entre paneles).
    steps: list[str] = []
    for plane in ("upper", "lower"):
        central = hung.central(plane)
        for up, down in zip(central, central[1:], strict=False):
            if not math.isclose(up.width_bottom, down.width_top, rel_tol=0.01):
                txt = f"{up.id}→{down.id}: {fmt_es(up.width_bottom)} / {fmt_es(down.width_top)} m"
                if txt not in steps:
                    steps.append(txt)
    if steps:
        ly += 28
        children.append(
            svg.text((lx, ly), "Escalones en pegaduras (U1 distinto):", cls="small bold")
        )
        for t in steps:
            ly += 13
            children.append(svg.text((lx + 8, ly), t, cls="small"))

    return svg.document(
        SHEET_W,
        SHEET_H,
        children,
        title_text=f"{spec.name} — vista a escala real",
        extra_style=SCALE_STYLE,
    )
