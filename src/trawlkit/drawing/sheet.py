"""Lámina técnica A3 de la red (dorso y vientre), como los planos FAO A-3 de 2014.

:func:`net_sheet_svg` dibuja, a partir de un :class:`~trawlkit.model.DesignResult`:

* el plano superior (dorso) a la izquierda y el inferior (vientre) a la derecha, con
  :func:`~trawlkit.drawing.layout.layout_net` en modo esquemático (malla estirada);
* mallas en los bordes, códigos de corte en los costados, relación de pegadura entre secciones,
  letra de cada panel y las piezas de lima y burlón a lo largo de las alas;
* una tabla a cada lado con una fila por franja (material, runnage, Nº de mallas, mallero,
  Ø hilo, largo) y el largo total de cada plano;
* el cuadro de superficie sólida y peso por plano, el círculo de pesca, el esquema del aparejo
  (portón, cable, patentes, malletas, cadena, boyas, lastre) y el rótulo.

Todos los números salen del motor; texto en castellano con coma decimal (:func:`fmt_es`).
"""

from __future__ import annotations

import datetime as _dt
import math
from collections.abc import Sequence
from fractions import Fraction
from typing import Literal

from trawlkit.drawing import svg
from trawlkit.drawing.layout import NetLayout, PanelShape, Point, layout_net
from trawlkit.io.schema import NetSpec, Section
from trawlkit.model import DesignResult

#: Tamaño de la lámina (A3 apaisado a 96 dpi, unidades de usuario SVG).
SHEET_W: float = 1587.0
SHEET_H: float = 1123.0

AUTHOR = "Ariel Luján Giamportone"
INSTITUTION = "Ingeniería Pesquera · UTN Ushuaia"

#: Abreviaturas de material de los planos (PA = poliamida = nylon, "NY").
MATERIAL_ES: dict[str, str] = {"PA": "NY", "NY": "NY", "PE": "PE", "PP": "PP", "PES": "PES"}

SHEET_STYLE = """
.frame { stroke: var(--ink); stroke-width: 1.4; fill: none; }
.rope { stroke: var(--ink); stroke-width: 2.2; fill: none; stroke-linecap: round;
        stroke-linejoin: round; }
.chain { stroke: var(--ink); stroke-width: 3; fill: none; stroke-dasharray: 2.5 1.5; }
.net-panel { stroke: var(--ink); stroke-width: 0.9; fill: var(--fill); }
text.num { font-size: 9px; }
text.code { font-size: 8.5px; font-style: italic; }
text.letter { font-size: 14px; }
text.big { font-size: 12px; }
text.bold { font-weight: 700; }
text.tb-title { font-size: 14px; font-weight: 700; letter-spacing: 0.4px; }
""".strip()

Variant = Literal["std", "mod"]


# ---------------------------------------------------------------------------------------------
# Utilidades de formato y geometría
# ---------------------------------------------------------------------------------------------


def fmt_es(x: float, decimals: int = 2) -> str:
    """Número con coma decimal y sin separador de miles: ``fmt_es(28.698) == "28,70"``."""
    s = f"{float(x):.{decimals}f}"
    if s.startswith("-") and float(s) == 0.0:
        s = s[1:]
    return s.replace(".", ",")


def fmt_mm(x: float) -> str:
    """Mallero o diámetro en mm: entero si lo es (``80``), con un decimal si no (``7,5``)."""
    return fmt_es(x, 0) if float(x).is_integer() else fmt_es(x, 1)


def spec_for(result: DesignResult, variant: str) -> NetSpec:
    """Spec de la red de una variante (``"std"`` → ``case.net``, ``"mod"`` → modificada)."""
    if variant == "std":
        return result.case.net
    if variant == "mod":
        return result.case.net_modified or result.case.net
    raise ValueError(f"variante desconocida: {variant!r} (use 'std' o 'mod')")


def rope_short(description: str, diameter_mm: float) -> str:
    """Designación corta de un cabo: ``"COMBINADO 12 Acero…"`` → ``"COMB. Ø12 mm"``."""
    word = description.split()[0].upper() if description.strip() else ""
    abbrev = {"COMBINADO": "COMB."}.get(word, word)
    return f"{abbrev} Ø{fmt_mm(diameter_mm)} mm".strip()


def join_fraction(a: int, b: int) -> str:
    """Relación de pegadura ``a:b`` como fracción simple (117:156 → ``"3/4"``)."""
    lo, hi = sorted((a, b))
    f = Fraction(lo, hi).limit_denominator(8)
    return f"{f.numerator}/{f.denominator}"


def text_width(s: str, size: float) -> float:
    """Ancho aproximado de un texto en px (Helvetica/DejaVu ≈ 0,56 em por carácter)."""
    return len(s) * size * 0.56


class _Frame:
    """Transformación de metros del layout a px de la lámina (escalas x e y independientes)."""

    def __init__(self, cx: float, y0: float, sx: float, sy: float) -> None:
        self.cx, self.y0, self.sx, self.sy = cx, y0, sx, sy

    def p(self, pt: Point) -> Point:
        return (self.cx + pt[0] * self.sx, self.y0 + pt[1] * self.sy)

    def x(self, x: float) -> float:
        return self.cx + x * self.sx

    def y(self, y: float) -> float:
        return self.y0 + y * self.sy


def _unit(p: Point, q: Point) -> Point:
    dx, dy = q[0] - p[0], q[1] - p[1]
    n = math.hypot(dx, dy) or 1.0
    return (dx / n, dy / n)


def _normal_away(p: Point, q: Point, ref: Point) -> Point:
    """Devuelve la normal unitaria a ``pq`` que apunta en sentido contrario a ``ref``."""
    ux, uy = _unit(p, q)
    n = (-uy, ux)
    m = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
    if (ref[0] - m[0]) * n[0] + (ref[1] - m[1]) * n[1] > 0:
        n = (-n[0], -n[1])
    return n


def _label_along(
    p: Point, q: Point, content: str, normal: Point, offset: float, cls: str, size: float
) -> svg.Element:
    """Texto centrado sobre el segmento ``pq``, girado con él y desplazado ``offset`` px."""
    ang = math.degrees(math.atan2(q[1] - p[1], q[0] - p[0]))
    if ang > 90:
        ang -= 180
    elif ang <= -90:
        ang += 180
    m = ((p[0] + q[0]) / 2 + normal[0] * offset, (p[1] + q[1]) / 2 + normal[1] * offset)
    # Centrar en vertical: la línea base va 0,35 em "debajo" del punto, en el marco girado.
    r = math.radians(ang)
    pos = (m[0] - math.sin(r) * size * 0.35, m[1] + math.cos(r) * size * 0.35)
    return svg.text(pos, content, cls=f"{cls} mid", rotate=ang)


def _offset_polyline(points: Sequence[Point], d: float, ref: Point) -> list[Point]:
    """Polilínea paralela a ``points`` a ``d`` px, del lado opuesto a ``ref`` (inglete simple)."""
    normals = [_normal_away(points[i], points[i + 1], ref) for i in range(len(points) - 1)]
    out: list[Point] = []
    for i, pt in enumerate(points):
        if i == 0:
            n = normals[0]
            out.append((pt[0] + n[0] * d, pt[1] + n[1] * d))
        elif i == len(points) - 1:
            n = normals[-1]
            out.append((pt[0] + n[0] * d, pt[1] + n[1] * d))
        else:
            n1, n2 = normals[i - 1], normals[i]
            k = 1.0 + n1[0] * n2[0] + n1[1] * n2[1]
            k = max(k, 0.2)
            out.append((pt[0] + d * (n1[0] + n2[0]) / k, pt[1] + d * (n1[1] + n2[1]) / k))
    return out


def _arrow(p: Point, q: Point, cls: str = "line", head: float = 6.0) -> list[svg.Element]:
    """Segmento ``p→q`` con punta de flecha llena en ``q``."""
    ux, uy = _unit(p, q)
    base = (q[0] - ux * head, q[1] - uy * head)
    w = head * 0.45
    tri = [q, (base[0] - uy * w, base[1] + ux * w), (base[0] + uy * w, base[1] - ux * w)]
    return [svg.line(p, base, cls=cls), svg.polygon(tri, cls="ink-fill")]


# ---------------------------------------------------------------------------------------------
# Dibujo de un plano
# ---------------------------------------------------------------------------------------------


def _chain_above(layout: NetLayout, s: PanelShape) -> PanelShape | None:
    """Panel inmediatamente encima de ``s`` en su misma cadena (lateral o central)."""
    chain = [c for c in layout.shapes[s.plane] if c.side == s.side]
    i = chain.index(s)
    return chain[i - 1] if i > 0 else None


def _plane_elements(
    layout: NetLayout,
    plane: str,
    fr: _Frame,
    toward: Literal["left", "right"],
    rope_total: tuple[str, float],
    rope_pieces: tuple[float, float],
    rope_spec: str,
    reinforcement_m: float,
) -> list[svg.Element]:
    """Paneles, mallas, cortes, pegaduras y relingas de un plano."""
    shapes = layout.shapes[plane]
    out: list[svg.Element] = []
    labels: list[svg.Element] = []

    for s in shapes:
        out.append(svg.polygon([fr.p(p) for p in s.points], cls="net-panel", id_=None))

    central = layout.central(plane)
    first_central = central[0] if central else None
    wings_bottom = [c for c in shapes if c.side != "center" and c.y_bottom == layout.mouth_y(plane)]

    for s in shapes:
        cx, cy = fr.p(s.centroid)
        labels.append(svg.text((cx, cy + 5), s.id, cls="letter mid"))

        # --- mallas de los bordes -----------------------------------------------------------
        top_px = (fr.x(s.x_top[0]), fr.x(s.x_top[1]))
        bot_px = (fr.x(s.x_bottom[0]), fr.x(s.x_bottom[1]))
        yt, yb = fr.y(s.y_top), fr.y(s.y_bottom)
        # Pegadura con el mismo número de mallas y mallero: se escribe sólo el borde de abajo.
        t = str(s.meshes_top)
        mx = (top_px[0] + top_px[1]) / 2
        narrow = top_px[1] - top_px[0] < text_width(t, 9) + 6
        labels.append(svg.text((mx, yt - 3 if narrow else yt + 10), t, cls="num mid"))
        below_same = [
            c for c in shapes if c.side == s.side and c.y_top == s.y_bottom and c is not s
        ]
        hide_bottom = bool(
            below_same
            and below_same[0].meshes_top == s.meshes_bottom
            and below_same[0].mesh_mm == s.mesh_mm
        )
        if not hide_bottom:
            t = str(s.meshes_bottom)
            mx = (bot_px[0] + bot_px[1]) / 2
            narrow = bot_px[1] - bot_px[0] < text_width(t, 9) + 6
            labels.append(svg.text((mx, yb + 10 if narrow else yb - 3), t, cls="num mid"))

        # --- códigos de corte ---------------------------------------------------------------
        # Centrales: afuera, del lado que mira al centro de la lámina. Laterales: X1 afuera del
        # costado exterior; X2 (AB, sobre la relinga) adentro si el paño es ancho, si no afuera
        # más allá del cabo.
        mid_w = ((top_px[1] - top_px[0]) + (bot_px[1] - bot_px[0])) / 2
        roomy = mid_w > 30 and yb - yt > 30
        sides: list[tuple[tuple[Point, Point], str | None, float]] = []
        if s.side == "center":
            edge = s.right_side if toward == "right" else s.left_side
            sides.append((edge, s.cut_code, 9.0))
        else:
            sides.append((s.outer_side, s.cut_code, 9.0))
            sides.append((s.inner_side, s.cut_code_x2, -9.0 if roomy else 15.0))
        for (a, b), code, off in sides:
            if not code:
                continue
            pa, pb = fr.p(a), fr.p(b)
            n = _normal_away(pa, pb, (cx, cy))
            labels.append(_label_along(pa, pb, code, n, off, "code", 8.5))

    # --- pegaduras: relación de mallas ------------------------------------------------------
    chain_side = toward
    for s in shapes:
        if s.side not in ("center", chain_side):
            continue
        above = _chain_above(layout, s)
        if above is not None and above.meshes_bottom != s.meshes_top:
            frac = join_fraction(above.meshes_bottom, s.meshes_top)
            x_edge = s.x_top[1] if toward == "right" else s.x_top[0]
            x_px = fr.x(x_edge) + (6 if toward == "right" else -6)
            labels.append(
                svg.text(
                    (x_px, fr.y(s.y_top) + 3),
                    frac,
                    cls="num" + ("" if toward == "right" else " end"),
                )
            )
    if first_central is not None and wings_bottom:
        wing = next(w for w in wings_bottom if w.side == chain_side)
        portion = round(wing.width_bottom * 1000.0 / first_central.mesh_mm)
        x_edge = first_central.x_top[1] if toward == "right" else first_central.x_top[0]
        x_px = fr.x(x_edge) + (6 if toward == "right" else -6)
        if portion != wing.meshes_bottom:
            labels.append(
                svg.text(
                    (x_px, fr.y(first_central.y_top) + 3),
                    join_fraction(wing.meshes_bottom, portion),
                    cls="num" + ("" if toward == "right" else " end"),
                )
            )

    # --- bocana y mallas equivalentes bajo las alas -----------------------------------------
    if first_central is not None and wings_bottom:
        right_w = next(w for w in wings_bottom if w.side == "right")
        bosom_m = 2.0 * right_w.x_bottom[0]
        bosom_meshes = round(bosom_m * 1000.0 / first_central.mesh_mm)
        ym = fr.y(first_central.y_top)
        labels.append(svg.text((fr.cx, ym - 3), str(bosom_meshes), cls="num mid"))
        for w in wings_bottom:
            portion = round(w.width_bottom * 1000.0 / first_central.mesh_mm)
            if portion != w.meshes_bottom:
                mx = fr.x((w.x_bottom[0] + w.x_bottom[1]) / 2)
                labels.append(svg.text((mx, ym + 10), f"({portion})", cls="num mid"))

        # Relinga de las alas (paralela a los costados interiores) y de la bocana.
        y_rope = ym - 14
        ends: list[Point] = []
        sides_lr: tuple[Literal["left", "right"], ...] = ("left", "right")
        for side in sides_lr:
            chain = layout.side_chain(plane, side)
            pts = [fr.p(chain[0].inner_side[0])] + [fr.p(c.inner_side[1]) for c in chain]
            ref = fr.p(chain[-1].centroid)
            rope = _offset_polyline(pts, 4.0, ref)
            (x1, y1), (x2, y2) = rope[-2], rope[-1]
            if y2 != y1:  # recorta la última pieza a la altura de la relinga de bocana
                cut_t = (y_rope - y1) / (y2 - y1)
                rope[-1] = (x1 + (x2 - x1) * cut_t, y_rope)
            out.append(svg.polyline(rope, cls="rope"))
            ends.append(rope[-1])
            k = max(range(len(pts) - 1), key=lambda i: math.dist(pts[i], pts[i + 1]))
            n = _normal_away(pts[k], pts[k + 1], ref)
            txt = f"{fmt_es(rope_pieces[0])} m"
            if side == toward:
                txt += f" · {rope_spec}"
            labels.append(_label_along(pts[k], pts[k + 1], txt, n, 13.0, "num", 9))
        out.append(svg.line(ends[0], ends[1], cls="rope"))
        labels.append(svg.text((fr.cx, y_rope - 5), f"{fmt_es(rope_pieces[1])} m", cls="num mid"))

    # --- refuerzo de las puntas de ala ------------------------------------------------------
    for s in shapes:
        if s.section is not Section.WING_TIP or s.side == "center":
            continue
        a, b = (fr.p(p) for p in s.outer_side)
        n = _normal_away(a, b, fr.p(s.centroid))
        out.append(
            svg.line((a[0] + n[0] * 3, a[1] + n[1] * 3), (b[0] + n[0] * 3, b[1] + n[1] * 3), "rope")
        )
        labels.append(_label_along(a, b, f"{fmt_es(reinforcement_m)} m", n, 20.0, "num", 9))

    # --- relinga total sobre el plano -------------------------------------------------------
    name, length = rope_total
    top = fr.y(0.0)
    bar_y = top + 34
    out.append(svg.line((fr.cx - 22, bar_y), (fr.cx + 22, bar_y), cls="rope"))
    if plane == "upper":
        out.extend(_arrow((fr.cx, bar_y + 18), (fr.cx, bar_y + 3), cls="line"))
    else:
        out.extend(_arrow((fr.cx, bar_y - 22), (fr.cx, bar_y - 3), cls="line"))
    labels.append(svg.text((fr.cx, top + 8), f"{name} {fmt_es(length)} m", cls="big mid"))
    return out + labels


# ---------------------------------------------------------------------------------------------
# Tablas laterales
# ---------------------------------------------------------------------------------------------

_COLUMNS: tuple[tuple[str, str, float], ...] = (
    ("Material", "", 0.0),
    ("Runnage", "[m/kg]", 42.0),
    ("Nº de mallas", "", 88.0),
    ("", "", 116.0),  # rombo (malla)
    ("Mallero", "[mm]", 140.0),
    ("Ø hilo", "[mm]", 180.0),
    ("Largo", "[m]", 222.0),
)
_TABLE_W = 250.0


def _side_table(
    layout: NetLayout, plane: str, fr: _Frame, x0: float, toward: Literal["left", "right"]
) -> list[svg.Element]:
    """Tabla de franjas de un plano; ``toward`` es el lado donde está el dibujo de la red."""
    out: list[svg.Element] = []
    bands = layout.bands[plane]
    top = fr.y(bands[0].y_top)
    cols = [(name, unit, x0 + 14 + dx) for name, unit, dx in _COLUMNS]
    for name, unit, x in cols:
        if name:
            out.append(svg.text((x + 3, top - 20), name, cls="", rotate=-90))
        if unit:
            out.append(svg.text((x, top - 6), unit, cls="small mid"))
    table_l, table_r = x0, x0 + _TABLE_W

    boundaries = sorted({b.y_top for b in bands} | {b.y_bottom for b in bands})
    for y in boundaries:
        yp = fr.y(y)
        ext = layout.x_extent_at(plane, y)
        gap = 30.0
        if toward == "right":
            x_end = fr.x(ext[0]) - gap if ext else table_r
            out.append(svg.line((table_l, yp), (max(table_r, x_end), yp), cls="thin"))
        else:
            x_end = fr.x(ext[1]) + gap if ext else table_l
            out.append(svg.line((min(table_l, x_end), yp), (table_r, yp), cls="thin"))

    for b in bands:
        p = b.panel
        ym = fr.y(b.y_mid) + 3.5
        runnage = p.runnage_m_per_kg or (1e6 / p.rtex if p.rtex else float("nan"))
        values = (
            MATERIAL_ES.get(p.material.upper(), p.material),
            fmt_es(runnage, 0),
            str(p.meshes_depth),
            "",
            fmt_mm(p.mesh_mm),
            fmt_es(p.twine_diameter_mm, 2),
            fmt_es(b.stretched_length_m, 2),
        )
        for (_, _, x), v in zip(cols, values, strict=True):
            if v:
                out.append(svg.text((x, ym), v, cls="mid"))
        dx = cols[3][2]
        h = min(9.0, (fr.y(b.y_bottom) - fr.y(b.y_top)) / 2 - 3)
        out.append(
            svg.polygon(
                [(dx, ym - 3.5 - h), (dx + 5, ym - 3.5), (dx, ym - 3.5 + h), (dx - 5, ym - 3.5)],
                cls="muted",
            )
        )
    total = sum(b.stretched_length_m for b in bands)
    out.append(
        svg.text(
            ((table_l + table_r) / 2, fr.y(bands[-1].y_bottom) + 20),
            f"LARGO TOTAL {fmt_es(total)} m",
            cls="big mid",
        )
    )
    return out


# ---------------------------------------------------------------------------------------------
# Cuadro central, aparejo y rótulo
# ---------------------------------------------------------------------------------------------


def _surface_box(result: DesignResult, variant: str, x: float, y: float) -> list[svg.Element]:
    geo = result.geometry.variant(variant)
    ss, wt = geo.solid_surface_by_plane, geo.weight_by_plane
    c1, c2, c3, w = x + 8, x + 165, x + 238, 270.0
    out: list[svg.Element] = [
        svg.text((c1, y + 22), "Sección de la red"),
        svg.text((c2, y + 10), "Superficie", cls="mid"),
        svg.text((c2, y + 22), "sólida [m²]", cls="mid"),
        svg.text((c3, y + 22), "Peso [kg]", cls="mid"),
        svg.line((x, y + 30), (x + w, y + 30), cls="thin"),
        svg.line((x + 128, y), (x + 128, y + 110), cls="thin"),
        svg.line((x + 204, y), (x + 204, y + 110), cls="thin"),
    ]
    rows = (
        ("Paneles inferiores", ss["lower"], wt["lower"]),
        ("Paneles superiores", ss["upper"], wt["upper"]),
    )
    for i, (name, a, b) in enumerate(rows):
        yy = y + 50 + i * 22
        out += [
            svg.text((c1, yy), name),
            svg.text((c2, yy), fmt_es(a), cls="mid"),
            svg.text((c3, yy), fmt_es(b), cls="mid"),
        ]
    out += [
        svg.line((x, y + 88), (x + w, y + 88), cls="thin"),
        svg.text((c1, y + 103), "Total", cls="bold"),
        svg.text((c2, y + 103), fmt_es(geo.solid_surface_m2), cls="mid bold"),
        svg.text((c3, y + 103), fmt_es(geo.weight_air_kg), cls="mid bold"),
    ]
    return out


def _fishing_circle(result: DesignResult, variant: str, x: float, y: float) -> list[svg.Element]:
    fc = result.dimensions.variant(variant).fishing_circle_m
    r = 9.0
    a0, a1 = math.radians(-60), math.radians(250)
    p0 = (x + r * math.cos(a0), y + r * math.sin(a0))
    p1 = (x + r * math.cos(a1), y + r * math.sin(a1))
    out: list[svg.Element] = [
        svg.path(f"M {p0[0]:.2f} {p0[1]:.2f} A {r} {r} 0 1 1 {p1[0]:.2f} {p1[1]:.2f}")
    ]
    out.append(
        svg.polygon(
            [(p0[0] - 4, p0[1] - 3), (p0[0] + 4, p0[1] - 4), (p0[0] + 1, p0[1] + 4)], cls="ink-fill"
        )
    )
    out.append(svg.text((x + 16, y - 2), f"{fmt_es(fc)} m", cls="big"))
    out.append(svg.text((x + 16, y + 10), "Círculo de pesca", cls="small muted-text"))
    return out


def _rigging(result: DesignResult, x0: float, y0: float, x_max: float) -> list[svg.Element]:
    """Esquema del aparejo en planta (cable, portón, patentes, malletas, red) en ``[x0, x_max]``."""
    door = result.doors.door
    polar = result.doors.polar
    warp = result.warps.selection
    br = result.bridles
    fl = result.floats
    bal = result.ballast
    dist = bal.distribution_max
    out: list[svg.Element] = []

    info = [
        f"Tipo de portón: {door.name}",
        "Dimensiones: "
        + f"{fmt_es(door.length_m or 0)} m × {fmt_es(door.height_m or 0)} m = "
        + f"{fmt_es(door.area_m2 or 0)} m²",
        f"Peso: {fmt_es(door.weight_air_kg or 0, 0)} kg",
        f"CD: {fmt_es(polar.cd)}    CL: {fmt_es(polar.cl)}",
        f"Ángulo de ataque: {fmt_es(polar.angle_deg, 0)}°",
    ]
    for i, t in enumerate(info):
        out.append(svg.text((x0 + 70, y0 + i * 13), t))

    ya = y0 + 112  # eje del aparejo
    door_x = x0 + 96
    x_sw1 = x0 + 400  # unión patentes-malletas
    x_net = x0 + 640  # puntas de ala
    x_bag = x_max - 50
    x_end = x_bag - 30
    y_up, y_lo = ya - 20, ya + 20

    # Cable de remolque.
    out.append(svg.line((x0 + 50, ya - 34), (door_x, ya - 4), cls="line"))
    out.append(svg.text((x0, ya - 4), "Cable de acero", cls="small"))
    out.append(svg.text((x0, ya + 8), f"Ø {fmt_mm(warp.diameter_mm)} mm", cls="small"))
    out.append(svg.text((x0, ya + 20), f"{fmt_es(result.warps.warp_m, 0)} m", cls="small"))
    # Portón.
    out.append(svg.rect(door_x, ya - 8, 34, 16, cls="line"))
    out.append(svg.line((door_x + 6, ya - 3), (door_x + 6, ya + 3), cls="thin"))
    out.append(svg.line((door_x + 28, ya - 3), (door_x + 28, ya + 3), cls="thin"))
    # Pie de gallo + patentes.
    x_sw0 = door_x + 34
    out.append(svg.polyline([(x_sw0, ya - 6), (x_sw0 + 22, ya), (x_sw0, ya + 6)], cls="thin"))
    out.append(svg.line((x_sw0 + 22, ya), (x_sw1, ya), cls="line"))
    out.append(svg.circle((x_sw1, ya), 2.2, cls="line"))
    out.append(
        svg.text(((x_sw0 + x_sw1) / 2, ya - 5), f"Patentes {fmt_es(br.sweeps_m)} m", cls="mid")
    )
    out.append(
        svg.text((x_sw0 + 2, ya + 16), f"Pie de gallo {fmt_es(br.crowfoot.length_m)} m", cls="tiny")
    )
    # Malletas superior e inferior; cadena de reglaje al final de la inferior.
    out.append(svg.line((x_sw1, ya), (x_net, y_up), cls="line"))
    chain_x = x_net - 36
    chain_y = ya + (y_lo - ya) * (chain_x - x_sw1) / (x_net - x_sw1)
    out.append(svg.line((x_sw1, ya), (chain_x, chain_y), cls="line"))
    out.append(svg.line((chain_x, chain_y), (x_net, y_lo), cls="chain"))
    out.append(
        svg.text(
            ((x_sw1 + x_net) / 2, y_up - 6),
            f"Malleta superior {fmt_es(br.lengths.upper_m)} m",
            cls="small mid",
        )
    )
    out.append(
        svg.text(
            ((x_sw1 + x_net) / 2 - 30, y_lo + 12),
            f"Malleta inferior {fmt_es(br.lengths.lower_m)} m",
            cls="small mid",
        )
    )
    chain_txt = (
        f"Cadena de reglaje {fmt_es(result.case.adjust_chain_m)} m · {fmt_es(dist.adjust_kg, 0)} kg"
    )
    out.extend(_arrow((chain_x - 30, y_lo + 34), (chain_x + 12, chain_y + 5)))
    out.append(svg.text((chain_x - 30, y_lo + 45), chain_txt, cls="small mid"))

    # Red de perfil: lima con boyas, burlón con lastre, bolsa.
    out.append(svg.polyline([(x_net, y_up), (x_end, y_up + 8), (x_bag, ya - 5)], cls="line"))
    out.append(svg.polyline([(x_net, y_lo), (x_end, y_lo - 8), (x_bag, ya + 5)], cls="line"))
    out.append(
        svg.polyline([(x_net + 50, y_up + 1), (x_end - 30, ya), (x_net + 50, y_lo - 1)], cls="thin")
    )
    out.append(svg.rect(x_bag, ya - 5, 40, 10, cls="line"))
    n_floats = max(1, min(fl.count, 40))
    span = x_end - x_net - 70
    for i in range(n_floats):
        fx = x_net + 25 + i * span / max(1, n_floats - 1)
        fy = y_up + 8 * (fx - x_net) / (x_end - x_net)
        out.append(svg.circle((fx, fy - 4), 3.2, cls="line"))
    for i in range(10):
        bx = x_net + 25 + i * span / 9
        by = y_lo - 8 * (bx - x_net) / (x_end - x_net)
        out.append(svg.path(f"M {bx - 4:.2f} {by:.2f} A 4 4 0 0 0 {bx + 4:.2f} {by:.2f}"))
    xm = (x_net + x_end) / 2
    out += [
        svg.text((xm, y_up - 24), f"{fl.count} boyas de Ø {fmt_mm(fl.diameter_mm)} mm", cls="mid"),
        svg.text(
            (xm, y_up - 13),
            f"Flotación total = {fmt_es(fl.flotation_rounded_kgf, 0)} kgf",
            cls="mid",
        ),
        svg.text((xm, y_lo + 22), f"Lastre total = {fmt_es(bal.limits.max_kg, 0)} kg", cls="mid"),
        svg.text(
            (xm, y_lo + 34),
            f"alas {fmt_es(dist.wings_kg, 0)} kg · bocana {fmt_es(dist.bosom_kg, 0)} kg · "
            f"reglaje {fmt_es(dist.adjust_kg, 0)} kg",
            cls="small mid muted-text",
        ),
    ]
    return out


def _title_block(
    result: DesignResult, variant: str, spec: NetSpec, year: int, x: float, y: float, w: float
) -> list[svg.Element]:
    case = result.case
    base = case.net.name.split(" (")[0].upper()
    codend = [p for p in spec.panels if p.section is Section.CODEND]
    mesh = f" · MALLA {fmt_mm(codend[0].mesh_mm)} mm" if codend else ""
    sub = (
        "CON BOLSA ESTÁNDAR PARA PEQUEÑOS PECES"
        if variant == "std"
        else "CON BOLSA MODIFICADA PARA CRUSTÁCEOS"
    ) + mesh
    bhps = sorted({float(v.bhp) for v in case.vessel_class})
    power = (
        f"PARA {fmt_es(bhps[0], 0)}HP"
        if len(bhps) == 1
        else f"PARA {fmt_es(bhps[0], 0)}HP A {fmt_es(bhps[-1], 0)}HP"
    )
    compat = "corregido" if case.compat.value == "corrected" else "Excel 2014"
    h1, h2, h3 = 70.0, 32.0, 34.0
    xm = x + w - 110
    out: list[svg.Element] = [
        svg.rect(x, y, w, h1 + h2 + h3, cls="frame"),
        svg.line((x, y + h1), (x + w, y + h1), cls="line"),
        svg.line((x, y + h1 + h2), (x + w, y + h1 + h2), cls="line"),
        svg.line((xm, y + h1), (xm, y + h1 + h2 + h3), cls="line"),
        svg.text((x + w / 2, y + 20), base, cls="tb-title mid"),
        svg.text((x + w / 2, y + 36), sub, cls="small mid"),
        svg.text((x + w / 2, y + 56), power, cls="big mid bold"),
        svg.text((x + 10, y + h1 + 21), AUTHOR, cls="big"),
        svg.text((xm + 55, y + h1 + 13), "AÑO", cls="small mid"),
        svg.text((xm + 55, y + h1 + 26), str(year), cls="mid"),
        svg.text((x + 10, y + h1 + h2 + 22), INSTITUTION, cls="big"),
        svg.text((xm + 55, y + h1 + h2 + 14), "Modo de cálculo", cls="tiny mid"),
        svg.text((xm + 55, y + h1 + h2 + 27), compat, cls="small mid"),
    ]
    return out


# ---------------------------------------------------------------------------------------------
# Lámina
# ---------------------------------------------------------------------------------------------


def net_sheet_svg(result: DesignResult, variant: str = "std", *, year: int | None = None) -> str:
    """Lámina técnica A3 (SVG) de la red ``variant`` (``"std"`` o ``"mod"``) del resultado.

    ``year`` va al rótulo (por defecto, el año actual).
    """
    spec = spec_for(result, variant)
    dims = result.dimensions.variant(variant)
    layout = layout_net(spec, "schematic")
    year = _dt.date.today().year if year is None else int(year)

    margin = 36.0
    y_top, y_bot = 178.0, 770.0
    max_len = max(layout.length(p) for p in ("upper", "lower"))
    half = max(
        max(abs(layout.plane_bbox(p)[0]), abs(layout.plane_bbox(p)[2])) for p in ("upper", "lower")
    )
    sy = (y_bot - y_top) / max_len
    sx = 150.0 / half
    fr_up = _Frame(548.0, y_top, sx, sy)
    fr_lo = _Frame(1040.0, y_top, sx, sy)

    head_rope = rope_short(
        result.floats.headrope_rope.description, result.floats.headrope_rope.diameter_mm
    )
    foot_rope = rope_short(
        result.ballast.footrope_rope.description, result.ballast.footrope_rope.diameter_mm
    )
    children: list[svg.Element] = [
        svg.rect(margin, margin, SHEET_W - 2 * margin, SHEET_H - 2 * margin, cls="frame")
    ]

    children.append(svg.text((fr_up.cx, 62), "PLANO SUPERIOR (DORSO)", cls="big mid bold"))
    children.append(svg.text((fr_lo.cx, 62), "PLANO INFERIOR (VIENTRE)", cls="big mid bold"))
    children += _plane_elements(
        layout,
        "upper",
        fr_up,
        "right",
        ("Lima", dims.headrope_m),
        (dims.headrope.wing_corrected_m, dims.headrope.bosom_corrected_m),
        head_rope,
        dims.wingtip_reinforcement_m,
    )
    children += _plane_elements(
        layout,
        "lower",
        fr_lo,
        "left",
        ("Burlón", dims.footrope_m),
        (dims.footrope.wing_corrected_m, dims.footrope.bosom_corrected_m),
        foot_rope,
        dims.wingtip_reinforcement_m,
    )
    children += _side_table(layout, "upper", fr_up, 64.0, "right")
    children += _side_table(layout, "lower", fr_lo, SHEET_W - 64.0 - _TABLE_W, "left")

    # Cabo de refuerzo que une las puntas de ala del dorso y del vientre.
    a = layout.side_chain("upper", "right")[0]
    b = layout.side_chain("lower", "left")[0]
    pa = fr_up.p((a.x_top[1], 0.0))
    pb = fr_lo.p((b.x_top[0], 0.0))
    ytop = y_top - 40
    tip_a, tip_b = (pa[0] + 8, pa[1] - 6), (pb[0] - 8, pb[1] - 6)
    mid_l, mid_r = (pa[0] + 50, ytop), (pb[0] - 50, ytop)
    children.append(svg.line(mid_l, mid_r, cls="line"))
    children += _arrow(mid_l, tip_a)
    children += _arrow(mid_r, tip_b)
    children.append(
        svg.text(
            ((pa[0] + pb[0]) / 2, ytop - 5),
            f"Refuerzo de puntas de ala {fmt_es(dims.wingtip_reinforcement_rope_m, 1)} m",
            cls="small mid",
        )
    )

    children += _fishing_circle(result, variant, 760.0, 580.0)
    children += _surface_box(result, variant, 660.0, 640.0)
    children += _rigging(result, 56.0, 858.0, SHEET_W - margin - 350.0 - 20.0)
    tb_w = 350.0
    children += _title_block(
        result, variant, spec, year, SHEET_W - margin - tb_w, SHEET_H - margin - 136.0, tb_w
    )

    title = f"{spec.name} — lámina técnica"
    return svg.document(SHEET_W, SHEET_H, children, title_text=title, extra_style=SHEET_STYLE)
