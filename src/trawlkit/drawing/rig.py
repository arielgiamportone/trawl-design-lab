"""Esquema en planta de los aparejos de dos redes y de vara (Fase 19.5).

:func:`rig_plan_svg` dibuja, a partir de un :class:`~trawlkit.model.DesignResult` con tangones,
gemelo o vara, el buque, los tangones (o las pastecas), los cables, los portones, el muerto
central o las varas y las redes. Los anchos van a escala (separación de portones, puntas de los
tangones, largo de la vara); a lo largo del arrastre el dibujo es esquemático (los cables miden
cientos de metros). :func:`rig_elements` devuelve los mismos elementos para insertarlos en otra
lámina (la lámina técnica los agrega con tangones, gemelo o vara).
"""

from __future__ import annotations

from trawlkit.drawing import svg
from trawlkit.i18n import dec, t
from trawlkit.model import DesignResult

#: Tamaño del esquema suelto (unidades SVG).
PLAN_W = 640.0
PLAN_H = 420.0


def _m(x: float) -> str:
    return dec(x, 1)


def _net(cx: float, y_mouth: float, half_mouth: float, length: float) -> list[svg.Element]:
    """Red en planta: boca de ``2·half_mouth`` y copo angosto ``length`` más atrás."""
    bag = max(half_mouth * 0.18, 2.0)
    pts = [
        (cx - half_mouth, y_mouth),
        (cx + half_mouth, y_mouth),
        (cx + bag, y_mouth + 0.82 * length),
        (cx + bag, y_mouth + length),
        (cx - bag, y_mouth + length),
        (cx - bag, y_mouth + 0.82 * length),
    ]
    return [svg.polygon(pts, cls="panel")]


def _door(cx: float, cy: float) -> svg.Element:
    return svg.rect(cx - 2.5, cy - 6.0, 5.0, 12.0, cls="line")


def rig_elements(result: DesignResult, x: float, y: float, w: float, h: float) -> list[svg.Element]:
    """Elementos del esquema del aparejo en el rectángulo ``(x, y, w, h)``.

    Vacío si el caso no es de tangones, gemelo ni vara.
    """
    mr = result.multirig
    if mr is None:
        return []
    case = result.case
    out: list[svg.Element] = [svg.rect(x, y, w, h, cls="thin")]
    title = {
        "outrigger": t("Aparejo de tangones: dos redes"),
        "twin": t("Aparejo gemelo: dos redes y muerto central"),
        "beam": t("Arrastre de vara"),
    }[mr.kind]
    out.append(svg.text((x + 8, y + 14), title, cls="label"))
    cx = x + w / 2.0
    beam_m = float(case.vessel.beam_m or 5.0)
    lay = mr.layout
    half_extent = max(
        0.5 * mr.swept_width_m,
        lay.tip_offset_m + 0.5 * mr.net_spread_m if lay is not None else 0.0,
        0.5 * beam_m,
        1.0,
    )
    k = (w - 60.0) / (2.0 * half_extent)  # px por metro, a lo ancho
    y_v = y + 30.0
    v_len = min(0.16 * h, 60.0)
    hb = 0.5 * beam_m * k
    hull = [
        (cx, y_v),
        (cx + hb, y_v + 0.3 * v_len),
        (cx + hb, y_v + v_len),
        (cx - hb, y_v + v_len),
        (cx - hb, y_v + 0.3 * v_len),
    ]
    out.append(svg.polygon(hull, cls="panel"))
    y_boom = y_v + 0.55 * v_len
    y_gear = y + 0.50 * h  # portones o vara
    net_len = 0.22 * h
    labels: list[tuple[tuple[float, float], str, str]] = []
    if lay is not None:
        for sgn in (1.0, -1.0):
            tip = cx + sgn * lay.tip_offset_m * k
            out.append(svg.line((cx, y_boom), (tip, y_boom), cls="accent"))
            out.append(svg.circle((tip, y_boom), 2.0, cls="line"))
        labels.append(
            (
                (cx + lay.tip_offset_m * k + 4.0, y_v + 4.0),
                t(
                    "tangón {length} m a {angle}°",
                    length=_m(mr.boom_length_m or 0.0),
                    angle=dec(mr.boom_angle_deg or 0.0, 0),
                ),
                "small",
            )
        )
    if mr.kind == "outrigger" and lay is not None:
        half = 0.5 * mr.net_spread_m * k
        for sgn in (1.0, -1.0):
            tip = cx + sgn * lay.tip_offset_m * k
            apex = (tip, y_gear - 34.0)
            out.append(svg.line((tip, y_boom), apex, cls="line"))
            for side in (1.0, -1.0):
                door = (tip + side * half, y_gear)
                out.append(svg.line(apex, door, cls="thin"))
                out.append(_door(*door))
            out += _net(tip, y_gear + 10.0, half * 0.75, net_len)
        labels.append(
            (
                (cx + lay.tip_offset_m * k + 4.0, y_gear - 26.0),
                t("tijera {length} m", length=_m(mr.bridle_m or 0.0)),
                "small",
            )
        )
    elif mr.kind == "twin":
        half_net = 0.5 * mr.net_spread_m * k
        stern = y_v + v_len
        clump = (cx, y_gear)
        out.append(svg.rect(cx - 4.0, y_gear - 6.0, 8.0, 12.0, cls="panel"))
        for sgn in (1.0, -1.0):
            door = (cx + sgn * 2.0 * half_net, y_gear)
            out.append(svg.line((cx + sgn * hb * 0.8, stern), door, cls="line"))
            out.append(svg.line((cx + sgn * hb * 0.8, stern), clump, cls="thin"))
            out.append(_door(*door))
            out += _net(cx + sgn * half_net, y_gear + 10.0, half_net * 0.8, net_len)
        if mr.clump_weight_kg is not None:
            labels.append(
                (
                    (cx, y_gear - 10.0),
                    t("muerto {kg} kg", kg=dec(mr.clump_weight_kg, 0)),
                    "small mid",
                )
            )
    elif mr.kind == "beam":
        half = 0.5 * mr.net_spread_m * k
        stern = y_v + v_len
        if lay is not None:
            centres = [cx + sgn * lay.tip_offset_m * k for sgn in (1.0, -1.0)][: mr.n_nets]
        else:
            n = mr.n_nets
            centres = [cx + (i - (n - 1) / 2.0) * 2.0 * half * 1.1 for i in range(n)]
        for c in centres:
            start = (c, y_boom) if lay is not None else (cx, stern)
            out.append(svg.line(start, (c, y_gear - 18.0), cls="line"))
            out.append(svg.line((c, y_gear - 18.0), (c - half, y_gear), cls="thin"))
            out.append(svg.line((c, y_gear - 18.0), (c + half, y_gear), cls="thin"))
            out.append(svg.line((c - half, y_gear), (c + half, y_gear), cls="accent"))
            for side in (1.0, -1.0):
                out.append(svg.rect(c + side * half - 2.0, y_gear - 4.0, 4.0, 8.0, cls="line"))
            out += _net(c, y_gear + 6.0, half * 0.95, net_len)
        labels.append(
            (
                (centres[0], y_gear - 22.0),
                t("vara {length} m", length=_m(mr.net_spread_m)),
                "small mid",
            )
        )
    # Ancho barrido (cota) al pie.
    y_dim = y + h - 20.0
    half_sw = 0.5 * mr.swept_width_m * k
    out.append(svg.line((cx - half_sw, y_dim), (cx + half_sw, y_dim), cls="line"))
    for sgn in (1.0, -1.0):
        out.append(
            svg.line((cx + sgn * half_sw, y_dim - 4.0), (cx + sgn * half_sw, y_dim + 4.0), "line")
        )
    out.append(
        svg.text(
            (cx, y_dim - 4.0),
            t("ancho barrido {width} m", width=_m(mr.swept_width_m)),
            cls="small mid",
        )
    )
    if lay is not None and lay.gap_m < 0.0:
        out.append(
            svg.text(
                (x + 8, y + h - 4.0),
                t(
                    "las redes se superponen {gap} m: desfasarlas o alargar los tangones",
                    gap=_m(-lay.gap_m),
                ),
                cls="small muted-text",
            )
        )
    for pos, text, cls in labels:
        out.append(svg.text(pos, text, cls=cls))
    return out


def rig_plan_svg(result: DesignResult) -> str:
    """Esquema en planta (SVG) del aparejo de tangones, gemelo o vara del resultado.

    ``ValueError`` si el caso no es de tangones, gemelo ni vara.
    """
    if result.multirig is None:
        raise ValueError(t("el esquema del aparejo es para tangones, gemelo o vara"))
    children = rig_elements(result, 10.0, 10.0, PLAN_W - 20.0, PLAN_H - 20.0)
    title = t("{net} — esquema del aparejo", net=result.case.net.name)
    return svg.document(PLAN_W, PLAN_H, children, title_text=title)


__all__ = ["rig_elements", "rig_plan_svg"]
