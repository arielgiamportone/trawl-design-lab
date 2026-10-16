"""Proyecciones de la forma simulada: planta, perfil y frente, en SVG.

Usa el constructor mínimo :mod:`trawlkit.drawing.svg` y sus clases de :data:`BASE_STYLE`. Las
líneas de la grilla de paño se dibujan por plano (vientre en gris, dorso en tinta), la lima y el
burlón resaltados, las bridas y patentes en trazos, y se acotan AH (entre puntas de ala de la
lima) y AV (altura de la lima sobre el burlón en el centro).

Convención de ejes de :class:`~trawlkit.sim.core.SimResult`: ``x`` hacia popa, ``y`` lateral,
``z`` sobre el fondo. En planta y perfil la boca queda a la izquierda.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np
import numpy.typing as npt

from trawlkit.drawing import svg
from trawlkit.drawing.sheet import fmt_es
from trawlkit.sim.core import SimResult

FloatArray = npt.NDArray[np.float64]
Point = tuple[float, float]

SIM_STYLE = """
.net-up { stroke: var(--ink); stroke-width: 0.45; fill: none; stroke-opacity: 0.75; }
.net-lo { stroke: var(--muted); stroke-width: 0.45; fill: none; stroke-opacity: 0.7; }
.head { stroke: var(--accent); stroke-width: 1.8; fill: none; }
.foot { stroke: var(--ink); stroke-width: 1.8; fill: none; }
.rig { stroke: var(--muted); stroke-width: 0.8; fill: none; stroke-dasharray: 5 3; }
.seabed { stroke: var(--muted); stroke-width: 1; fill: none; }
.dim { stroke: var(--accent); stroke-width: 0.8; fill: none; }
.float { fill: var(--accent); stroke: none; }
text.dimtxt { font-size: 11px; fill: var(--accent); font-weight: 600; }
""".strip()

_W = 900.0
_H_MAX = 700.0
_TOP = 60.0
_MARGIN = 40.0
_LEGEND = 60.0


class _Frame:
    """Transformación metros → px con escala uniforme (y exageración vertical opcional).

    La escala la fija el ancho útil (``width``), con un alto máximo ``max_height``; ``height``
    es el alto del documento que resulta (título + dibujo + leyenda).
    """

    def __init__(
        self,
        u: FloatArray,
        v: FloatArray,
        *,
        width: float = _W,
        max_height: float = _H_MAX,
        top: float = _TOP,
        exaggeration: float = 1.0,
    ) -> None:
        self.ex = exaggeration
        u0, u1 = float(np.min(u)), float(np.max(u))
        v0, v1 = float(np.min(v)), float(np.max(v))
        du = max(u1 - u0, 1e-6)
        dv = max((v1 - v0) * exaggeration, 1e-6)
        avail = max_height - top - 2 * _MARGIN - _LEGEND
        self.k = min((width - 2 * _MARGIN) / du, avail / dv)
        self.u0, self.v0 = u0, v0
        self.left = (width - du * self.k) / 2.0
        self.base = top + _MARGIN + dv * self.k
        self.height = self.base + _MARGIN + 20.0 + _LEGEND

    def p(self, u: float, v: float) -> Point:
        return (
            self.left + (u - self.u0) * self.k,
            self.base - (v - self.v0) * self.ex * self.k,
        )


def _poly(pts: FloatArray, frame: _Frame, cls: str) -> svg.Element:
    return svg.polyline([frame.p(float(a), float(b)) for a, b in pts], cls=cls)


def _dim_h(p1: Point, p2: Point, y: float, label: str) -> list[svg.Element]:
    """Cota horizontal entre las abscisas de ``p1`` y ``p2``, a la altura ``y`` (px)."""
    return [
        svg.line((p1[0], p1[1]), (p1[0], y), cls="muted"),
        svg.line((p2[0], p2[1]), (p2[0], y), cls="muted"),
        svg.line((p1[0], y), (p2[0], y), cls="dim"),
        svg.line((p1[0], y - 4), (p1[0], y + 4), cls="dim"),
        svg.line((p2[0], y - 4), (p2[0], y + 4), cls="dim"),
        svg.text(((p1[0] + p2[0]) / 2.0, y + 16), label, cls="dimtxt mid"),
    ]


def _dim_v(p1: Point, p2: Point, x: float, label: str) -> list[svg.Element]:
    """Cota vertical entre las alturas de ``p1`` y ``p2`` en la abscisa ``x`` (px)."""
    return [
        svg.line((p1[0], p1[1]), (x, p1[1]), cls="muted"),
        svg.line((p2[0], p2[1]), (x, p2[1]), cls="muted"),
        svg.line((x, p1[1]), (x, p2[1]), cls="dim"),
        svg.line((x - 4, p1[1]), (x + 4, p1[1]), cls="dim"),
        svg.line((x - 4, p2[1]), (x + 4, p2[1]), cls="dim"),
        svg.text((x + 8, (p1[1] + p2[1]) / 2.0 + 4), label, cls="dimtxt"),
    ]


def _net_lines(
    r: SimResult, frame: _Frame, proj: Callable[[FloatArray], FloatArray]
) -> list[svg.Element]:
    out: list[svg.Element] = []
    for plane in ("lower", "upper"):
        cls = "net-up" if plane == "upper" else "net-lo"
        for pl, idx in r.grid_lines:
            if pl == plane:
                out.append(_poly(proj(r.nodes[idx]), frame, cls))
    return out


def _rigging(
    r: SimResult, frame: _Frame, proj: Callable[[FloatArray], FloatArray]
) -> list[svg.Element]:
    out: list[svg.Element] = []
    for (a, b), kind in zip(r.bars, r.bar_kind, strict=True):
        if kind in ("upper_bridle", "lower_bridle", "sweep"):
            out.append(_poly(proj(r.nodes[[a, b]]), frame, "rig"))
    return out


def _header(title: str, r: SimResult, extra: str = "") -> list[svg.Element]:
    sub = (
        f"v = {fmt_es(r.speed_kn, 1)} kn · AH = {fmt_es(r.ah_m, 1)} m · AV = {fmt_es(r.av_m, 2)} m"
        f" · DP = {fmt_es(r.door_spread_m, 1)} m · R = {fmt_es(r.drag_kgf, 0)} kgf{extra}"
    )
    return [
        svg.text((_MARGIN, 30), title, cls="title"),
        svg.text((_MARGIN, 48), sub, cls="muted-text"),
    ]


def plan_svg(r: SimResult, *, include_rigging: bool = False) -> str:
    """Vista en planta (desde arriba): x hacia la derecha (popa), y hacia arriba (babor)."""
    net = np.unique(r.triangles)
    pts = r.nodes[net] if not include_rigging else r.nodes
    frame = _Frame(pts[:, 0], pts[:, 1])

    def proj(p: FloatArray) -> FloatArray:
        return p[:, [0, 1]]

    els: list[svg.Element] = _header("Planta (vista superior)", r)
    if include_rigging:
        els += _rigging(r, frame, proj)
    els += _net_lines(r, frame, proj)
    els.append(_poly(proj(r.nodes[r.footrope]), frame, "foot"))
    els.append(_poly(proj(r.nodes[r.headrope]), frame, "head"))
    tr, tl = (frame.p(*r.nodes[k, [0, 1]]) for k in r.wing_tips_upper)
    x_dim = min(tr[0], tl[0]) - 22.0
    els += _dim_v(tl, tr, x_dim, f"AH = {fmt_es(r.ah_m, 2)} m")
    els.append(_legend(frame, plan=True))
    return svg.document(
        _W, frame.height, els, title_text="Red simulada: planta", extra_style=SIM_STYLE
    )


def profile_svg(r: SimResult, *, exaggeration: float = 3.0) -> str:
    """Vista de perfil (costado): x a la derecha, z arriba (escala vertical × ``exaggeration``)."""
    net = np.unique(r.triangles)
    pts = r.nodes[net]
    z = np.concatenate([pts[:, 2], [0.0]])
    frame = _Frame(
        np.concatenate([pts[:, 0], [np.min(pts[:, 0])]]),
        z,
        exaggeration=exaggeration,
    )

    def proj(p: FloatArray) -> FloatArray:
        return p[:, [0, 2]]

    els: list[svg.Element] = _header(
        "Perfil (vista lateral)", r, f" · escala vertical × {fmt_es(exaggeration, 0)}"
    )
    x0, x1 = float(np.min(pts[:, 0])) - 1.0, float(np.max(pts[:, 0])) + 1.0
    els.append(svg.line(frame.p(x0, 0.0), frame.p(x1, 0.0), cls="seabed"))
    els.append(
        svg.text(
            (frame.p(x1, 0.0)[0] - 4, frame.p(x1, 0.0)[1] + 14), "fondo", cls="small end muted-text"
        )
    )
    els += _net_lines(r, frame, proj)
    els.append(_poly(proj(r.nodes[r.footrope]), frame, "foot"))
    els.append(_poly(proj(r.nodes[r.headrope]), frame, "head"))
    hc = r.headrope[len(r.headrope) // 2]
    fc = r.footrope[len(r.footrope) // 2]
    ph = frame.p(*r.nodes[hc, [0, 2]])
    pf = frame.p(*r.nodes[fc, [0, 2]])
    els += _dim_v(ph, pf, min(ph[0], pf[0]) - 26.0, f"AV = {fmt_es(r.av_m, 2)} m")
    els.append(_legend(frame, plan=False))
    return svg.document(
        _W, frame.height, els, title_text="Red simulada: perfil", extra_style=SIM_STYLE
    )


def front_svg(r: SimResult) -> str:
    """Vista de frente (desde proa, mirando a popa): y hacia la izquierda, z hacia arriba."""
    net = np.unique(r.triangles)
    pts = r.nodes[net]
    frame = _Frame(
        -np.concatenate([pts[:, 1]]),
        np.concatenate([pts[:, 2], [0.0]]),
    )

    def proj(p: FloatArray) -> FloatArray:
        return np.stack([-p[:, 1], p[:, 2]], axis=1)

    els: list[svg.Element] = _header("Frente (vista desde proa)", r)
    y0, y1 = float(np.max(-pts[:, 1])) - 1.0, float(np.min(-pts[:, 1])) + 1.0
    els.append(svg.line(frame.p(y0, 0.0), frame.p(y1, 0.0), cls="seabed"))
    els += _net_lines(r, frame, proj)
    els.append(_poly(proj(r.nodes[r.footrope]), frame, "foot"))
    els.append(_poly(proj(r.nodes[r.headrope]), frame, "head"))
    for k in r.float_nodes:
        c = frame.p(*proj(r.nodes[[k]])[0])
        els.append(svg.circle(c, 2.5, cls="float"))
    tr, tl = (frame.p(*proj(r.nodes[[k]])[0]) for k in r.wing_tips_upper)
    els += _dim_h(tl, tr, frame.p(0.0, 0.0)[1] + 14.0, f"AH = {fmt_es(r.ah_m, 2)} m")
    hc = r.headrope[len(r.headrope) // 2]
    fc = r.footrope[len(r.footrope) // 2]
    ph = frame.p(*proj(r.nodes[[hc]])[0])
    pf = frame.p(*proj(r.nodes[[fc]])[0])
    els += _dim_v(ph, pf, ph[0] + 40.0, f"AV = {fmt_es(r.av_m, 2)} m")
    els.append(_legend(frame, plan=False))
    return svg.document(
        _W, frame.height, els, title_text="Red simulada: frente", extra_style=SIM_STYLE
    )


def _legend(frame: _Frame, *, plan: bool) -> svg.Element:
    x, y = _W - 230.0, frame.height - _LEGEND + 6.0
    items: Sequence[tuple[str, str]] = (
        ("head", "lima (relinga superior)"),
        ("foot", "burlón (relinga inferior)"),
        ("net-up", "paño del dorso"),
        ("net-lo", "paño del vientre"),
    )
    g = svg.group()
    for k, (cls, label) in enumerate(items):
        yy = y + 13.0 * k
        g.add(
            svg.line((x, yy), (x + 22, yy), cls=cls),
            svg.text((x + 28, yy + 3.5), label, cls="small"),
        )
    return g


def projections_svg(result: SimResult) -> dict[str, str]:
    """Las tres proyecciones de ``result``: ``{"plan", "profile", "front"}`` → SVG."""
    return {
        "plan": plan_svg(result),
        "profile": profile_svg(result),
        "front": front_svg(result),
    }
