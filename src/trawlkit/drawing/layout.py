"""Disposición 2D de los paneles de la red (plano técnico y vista a escala real).

:func:`layout_net` convierte una :class:`~trawlkit.io.schema.NetSpec` en polígonos por plano
(dorso / vientre), sin coordenadas escritas a mano: todo sale de las mallas de cada panel.

Reglas de disposición
---------------------
* **Unidades**: metros. El eje de la red es ``x = 0``; ``y`` crece desde la boca (``y = 0``, borde
  superior del panel más alto del plano) hacia la bolsa.
* **Planos**: cada panel se dibuja en los planos de ``planes_covered`` (o ``plane``). La
  multiplicidad por plano es ``count / nº de planos``: 2 → par izquierdo/derecho (puntas de ala,
  alas, 2ª sección del ala inferior); 1 → panel central sobre el eje (square, cuerpos, bolsa).
* **Orden boca → bolsa**: por ``Panel.section`` (punta de ala, ala, square, 2ª sección, cuerpo,
  extensión, bolsa) y, dentro de una sección, por el orden de la spec. La cadena lateral (pares)
  va arriba y la cadena central debajo: el primer panel central empieza donde terminan las alas.
* **Pegaduras**: los paneles centrales se apilan centrados, de modo que el borde inferior de uno y
  el superior del siguiente comparten ``y`` y punto medio (372 del square E = 372 del cuerpo G).
  Las alas se apoyan sobre el borde superior del primer panel central desde su esquina exterior
  hacia adentro (C 117 sobre las 156 mallas laterales del square; F 143 sobre G 372) y el hueco
  que queda en el centro es la bocana (100 mallas en el dorso, 86 en el vientre). Cada ala apoya
  a su vez su borde inferior en el superior del ala de abajo, alineando la esquina exterior.
* **Forma de las alas**: trapecios (o triángulos si un borde tiene 0 mallas) con ancho superior
  ``meshes_top`` y ancho inferior ``meshes_bottom``. El costado exterior continúa la pendiente del
  costado del primer panel central (la línea exterior de la red queda casi recta, como en el plano
  de 2014); el costado interior (corte AB, sobre la relinga) queda definido por los anchos.

Modos y escalas
---------------
* ``"schematic"``: ancho ∝ mallas × mallero y alto ∝ N × mallero, es decir, la red a malla
  estirada (U1 = U2 = 1) en metros. Multiplicar por el mallero mantiene la proporción entre
  secciones de 80, 60, 40 y 30 mm (117 mallas de 80 mm pegan con 156 de 60 mm). La lámina aplica
  después escalas distintas en x y en y para llenar el formato.
* ``"true_scale"``: red relingada, ancho = mallas · mallero · U1 / 1000 y alto =
  N · mallero · U2 / 1000 con U1 = ``hanging_ratio`` del panel y U2 = √(1 − U1²). Con
  ``stretched=True`` se usa U1 = U2 = 1 (largos estirados, idéntico a ``"schematic"``). Si dos
  paneles pegados tienen U1 distinto (G 0,38 → H 0,23) sus bordes relingados no miden lo mismo y
  el dibujo muestra el escalón: es lo que dice la spec.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Literal

from trawlkit.io.schema import NetSpec, Panel, Plane, Section
from trawlkit.netting import (
    SQUARE_MESH_COEFFICIENT,
    orientation_coefficients,
    stretched_length_m,
)

Point = tuple[float, float]
Mode = Literal["schematic", "true_scale"]
Side = Literal["left", "right", "center"]

#: Orden boca → bolsa de las secciones.
SECTION_ORDER: dict[Section, int] = {
    Section.WING_TIP: 0,
    Section.WING: 1,
    Section.SQUARE: 2,
    Section.BELLY: 3,
    Section.BODY: 4,
    Section.EXTENSION: 5,
    Section.CODEND: 6,
}

#: Orden de los planos en el resultado.
PLANE_ORDER: tuple[str, ...] = (Plane.UPPER.value, Plane.LOWER.value, Plane.SIDE.value)


def _extra(panel: Panel, name: str) -> object:
    return (panel.model_extra or {}).get(name)


def panel_planes(panel: Panel) -> tuple[str, ...]:
    """Planos en los que se dibuja un panel (``planes_covered`` o ``plane``)."""
    covered = _extra(panel, "planes_covered")
    if isinstance(covered, list | tuple) and covered:
        return tuple(Plane(str(p)).value for p in covered)
    return (panel.plane.value,)


def _polygon_area_centroid(points: Sequence[Point]) -> tuple[float, Point]:
    """Área con signo y centroide de un polígono simple (fórmula del cordón)."""
    a = cx = cy = 0.0
    n = len(points)
    for i in range(n):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        a += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    a *= 0.5
    if a == 0:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return 0.0, (sum(xs) / n, sum(ys) / n)
    return a, (cx / (6.0 * a), cy / (6.0 * a))


def _same(p: Point, q: Point) -> bool:
    return math.isclose(p[0], q[0], abs_tol=1e-12) and math.isclose(p[1], q[1], abs_tol=1e-12)


def _mid(p: Point, q: Point) -> Point:
    return ((p[0] + q[0]) / 2.0, (p[1] + q[1]) / 2.0)


@dataclass(frozen=True)
class PanelShape:
    """Polígono de un panel en un plano.

    ``x_top``/``x_bottom`` son las abscisas (izquierda, derecha) de los bordes superior (boca) e
    inferior (bolsa); ``points`` es el polígono cerrado en sentido horario empezando por la esquina
    superior izquierda (sin vértices repetidos: un borde de 0 mallas da un triángulo).
    """

    id: str
    plane: str
    section: Section
    side: Side
    y_top: float
    y_bottom: float
    x_top: tuple[float, float]
    x_bottom: tuple[float, float]
    meshes_top: int
    meshes_bottom: int
    meshes_depth: int
    mesh_mm: float
    hanging_ratio: float | None
    cut_code: str | None
    cut_code_x2: str | None
    panel: Panel = field(repr=False, compare=False)

    # --- geometría derivada -----------------------------------------------------------------

    @property
    def points(self) -> tuple[Point, ...]:
        """Vértices del polígono (horario, sin repetir)."""
        raw: list[Point] = [
            (self.x_top[0], self.y_top),
            (self.x_top[1], self.y_top),
            (self.x_bottom[1], self.y_bottom),
            (self.x_bottom[0], self.y_bottom),
        ]
        out: list[Point] = []
        for p in raw:
            if not out or not _same(p, out[-1]):
                out.append(p)
        if len(out) > 1 and _same(out[0], out[-1]):
            out.pop()
        return tuple(out)

    @property
    def width_top(self) -> float:
        """Ancho del borde superior [m]."""
        return self.x_top[1] - self.x_top[0]

    @property
    def width_bottom(self) -> float:
        """Ancho del borde inferior [m]."""
        return self.x_bottom[1] - self.x_bottom[0]

    @property
    def height(self) -> float:
        """Alto del panel [m]."""
        return self.y_bottom - self.y_top

    @property
    def area(self) -> float:
        """Área del polígono [m²] (positiva)."""
        return abs(_polygon_area_centroid(self.points)[0])

    @property
    def centroid(self) -> Point:
        """Centroide del polígono."""
        return _polygon_area_centroid(self.points)[1]

    @property
    def top_mid(self) -> Point:
        """Punto medio del borde superior."""
        return ((self.x_top[0] + self.x_top[1]) / 2.0, self.y_top)

    @property
    def bottom_mid(self) -> Point:
        """Punto medio del borde inferior."""
        return ((self.x_bottom[0] + self.x_bottom[1]) / 2.0, self.y_bottom)

    @property
    def left_side(self) -> tuple[Point, Point]:
        """Costado izquierdo (arriba, abajo)."""
        return (self.x_top[0], self.y_top), (self.x_bottom[0], self.y_bottom)

    @property
    def right_side(self) -> tuple[Point, Point]:
        """Costado derecho (arriba, abajo)."""
        return (self.x_top[1], self.y_top), (self.x_bottom[1], self.y_bottom)

    @property
    def left_mid(self) -> Point:
        """Punto medio del costado izquierdo."""
        return _mid(*self.left_side)

    @property
    def right_mid(self) -> Point:
        """Punto medio del costado derecho."""
        return _mid(*self.right_side)

    @property
    def outer_side(self) -> tuple[Point, Point]:
        """Costado alejado del eje (en paneles centrales, el derecho)."""
        return self.left_side if self.side == "left" else self.right_side

    @property
    def inner_side(self) -> tuple[Point, Point]:
        """Costado hacia el eje (en paneles centrales, el izquierdo)."""
        return self.right_side if self.side == "left" else self.left_side

    def x_range_at(self, y: float) -> tuple[float, float] | None:
        """Intervalo ``(x_izq, x_der)`` del panel a la altura ``y`` (``None`` si no lo corta)."""
        if y < self.y_top - 1e-12 or y > self.y_bottom + 1e-12:
            return None
        t = 0.0 if self.height == 0 else (y - self.y_top) / self.height
        t = min(1.0, max(0.0, t))
        left = self.x_top[0] + (self.x_bottom[0] - self.x_top[0]) * t
        right = self.x_top[1] + (self.x_bottom[1] - self.x_top[1]) * t
        return left, right


@dataclass(frozen=True)
class Band:
    """Franja horizontal de un plano (una fila de la tabla lateral del plano)."""

    plane: str
    y_top: float
    y_bottom: float
    panel: Panel = field(repr=False, compare=False)
    shape_ids: tuple[str, ...] = ()

    @property
    def panel_id(self) -> str:
        """Identificador del panel de la franja."""
        return self.panel.id

    @property
    def y_mid(self) -> float:
        """Ordenada media de la franja."""
        return (self.y_top + self.y_bottom) / 2.0

    @property
    def stretched_length_m(self) -> float:
        """Largo del paño a malla estirada [m] (N · mallero / 1000)."""
        return float(stretched_length_m(self.panel.meshes_depth, self.panel.mesh_mm))


@dataclass(frozen=True)
class NetLayout:
    """Paneles de la red dispuestos por plano, con sus franjas y su recuadro envolvente."""

    net_id: str
    mode: Mode
    stretched: bool
    shapes: dict[str, tuple[PanelShape, ...]]
    bands: dict[str, tuple[Band, ...]]
    bbox: tuple[float, float, float, float]

    @property
    def planes(self) -> tuple[str, ...]:
        """Planos presentes, en orden dorso → vientre → costado."""
        return tuple(p for p in PLANE_ORDER if p in self.shapes)

    def plane_bbox(self, plane: str) -> tuple[float, float, float, float]:
        """Recuadro ``(xmin, ymin, xmax, ymax)`` de un plano."""
        return _bbox(self.shapes[plane])

    def length(self, plane: str) -> float:
        """Largo dibujado del plano [m] (de la boca a la bolsa)."""
        b = self.plane_bbox(plane)
        return b[3] - b[1]

    def shape(self, plane: str, panel_id: str, side: Side | None = None) -> PanelShape:
        """Forma de un panel en un plano (``side`` elige izquierda/derecha en los pares)."""
        for s in self.shapes[plane]:
            if s.id == panel_id and (side is None or s.side == side):
                return s
        raise KeyError(f"{panel_id!r} no está en el plano {plane!r}")

    def central(self, plane: str) -> tuple[PanelShape, ...]:
        """Paneles centrales del plano (boca → bolsa)."""
        return tuple(s for s in self.shapes[plane] if s.side == "center")

    def side_chain(self, plane: str, side: Side = "right") -> tuple[PanelShape, ...]:
        """Paneles laterales de un lado (boca → bolsa)."""
        return tuple(s for s in self.shapes[plane] if s.side == side)

    def mouth_y(self, plane: str) -> float:
        """Ordenada del borde superior del primer panel central (pegadura alas-cuerpo)."""
        c = self.central(plane)
        return c[0].y_top if c else self.plane_bbox(plane)[3]

    def x_extent_at(self, plane: str, y: float) -> tuple[float, float] | None:
        """Extremos ``(xmin, xmax)`` del plano a la altura ``y``."""
        xs: list[float] = []
        for s in self.shapes[plane]:
            r = s.x_range_at(y)
            if r is not None:
                xs.extend(r)
        return (min(xs), max(xs)) if xs else None


def _bbox(shapes: Iterable[PanelShape]) -> tuple[float, float, float, float]:
    pts = [p for s in shapes for p in s.points]
    if not pts:
        return (0.0, 0.0, 0.0, 0.0)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def panel_size_m(
    panel: Panel, mode: Mode = "schematic", stretched: bool = False
) -> tuple[float, float, float]:
    """``(ancho superior, ancho inferior, alto)`` del panel en metros según el modo."""
    square = str(panel.mesh_orientation) == "square"
    if mode == "schematic" or stretched:
        # En malla cuadrada cada malla contada es un cuadrado de una pata (mL/2) de lado.
        u1 = u2 = SQUARE_MESH_COEFFICIENT if square else 1.0
    else:
        if panel.hanging_ratio is None and not square:
            raise ValueError(f"panel {panel.id}: hace falta hanging_ratio (U1) para true_scale")
        u1, u2 = orientation_coefficients(panel.mesh_orientation, panel.hanging_ratio or 0.5)
    top = float(stretched_length_m(panel.meshes_top, panel.mesh_mm, u1))
    bottom = float(stretched_length_m(panel.meshes_bottom, panel.mesh_mm, u1))
    height = float(stretched_length_m(panel.meshes_depth, panel.mesh_mm, u2))
    return top, bottom, height


def _multiplicity(panel: Panel) -> int:
    planes = panel_planes(panel)
    if panel.count % len(planes) != 0:
        raise ValueError(
            f"panel {panel.id}: count={panel.count} no se reparte entre los planos {planes}"
        )
    m = panel.count // len(planes)
    if m not in (1, 2):
        raise ValueError(f"panel {panel.id}: {m} paneles por plano (se admiten 1 o 2)")
    return m


def _shape(
    panel: Panel,
    plane: str,
    side: Side,
    y_top: float,
    y_bottom: float,
    x_top: tuple[float, float],
    x_bottom: tuple[float, float],
) -> PanelShape:
    code2 = _extra(panel, "cut_code_x2")
    return PanelShape(
        id=panel.id,
        plane=plane,
        section=panel.section,
        side=side,
        y_top=y_top,
        y_bottom=y_bottom,
        x_top=x_top,
        x_bottom=x_bottom,
        meshes_top=panel.meshes_top,
        meshes_bottom=panel.meshes_bottom,
        meshes_depth=panel.meshes_depth,
        mesh_mm=float(panel.mesh_mm),
        hanging_ratio=None if panel.hanging_ratio is None else float(panel.hanging_ratio),
        cut_code=panel.cut_code,
        cut_code_x2=None if code2 is None else str(code2),
        panel=panel,
    )


def _layout_plane(
    plane: str, panels: Sequence[Panel], mode: Mode, stretched: bool
) -> tuple[tuple[PanelShape, ...], tuple[Band, ...]]:
    def key(item: tuple[int, Panel]) -> tuple[int, int]:
        return (SECTION_ORDER[item[1].section], item[0])

    ordered = [p for _, p in sorted(enumerate(panels), key=key)]
    side_panels = [p for p in ordered if _multiplicity(p) == 2]
    central_panels = [p for p in ordered if _multiplicity(p) == 1]
    sizes = {id(p): panel_size_m(p, mode, stretched) for p in ordered}

    y_mouth = sum(sizes[id(p)][2] for p in side_panels)

    # Cadena central, centrada sobre el eje.
    central: list[PanelShape] = []
    y = y_mouth
    for p in central_panels:
        top, bottom, h = sizes[id(p)]
        central.append(
            _shape(p, plane, "center", y, y + h, (-top / 2, top / 2), (-bottom / 2, bottom / 2))
        )
        y += h

    # Cadena lateral (lado derecho), de la pegadura con el cuerpo hacia la boca.
    if central:
        first = central[0]
        outer = first.x_top[1]
        slope = (first.x_top[1] - first.x_bottom[1]) / first.height if first.height else 0.0
    else:
        outer = max((sizes[id(p)][1] for p in side_panels), default=0.0)
        slope = 0.0
    y_tops: list[float] = []
    acc = 0.0
    for p in side_panels:
        y_tops.append(acc)
        acc += sizes[id(p)][2]
    y_bottoms = [*y_tops[1:], y_mouth]
    right: list[PanelShape] = []
    for p, y0, y1 in reversed(list(zip(side_panels, y_tops, y_bottoms, strict=True))):
        top, bottom, h = sizes[id(p)]
        outer_top = outer + slope * h
        right.append(
            _shape(p, plane, "right", y0, y1, (outer_top - top, outer_top), (outer - bottom, outer))
        )
        outer = outer_top
    right.reverse()
    left = [
        _shape(
            s.panel,
            plane,
            "left",
            s.y_top,
            s.y_bottom,
            (-s.x_top[1], -s.x_top[0]),
            (-s.x_bottom[1], -s.x_bottom[0]),
        )
        for s in right
    ]

    shapes: list[PanelShape] = []
    bands: list[Band] = []
    for lft, rgt in zip(left, right, strict=True):
        shapes.extend((lft, rgt))
        bands.append(Band(plane, rgt.y_top, rgt.y_bottom, rgt.panel, (rgt.id,)))
    for c in central:
        shapes.append(c)
        bands.append(Band(plane, c.y_top, c.y_bottom, c.panel, (c.id,)))
    return tuple(shapes), tuple(bands)


def layout_net(spec: NetSpec, mode: Mode = "schematic", stretched: bool = False) -> NetLayout:
    """Dispone los paneles de ``spec`` por plano (ver reglas en el docstring del módulo).

    ``mode="schematic"`` (malla estirada, para la lámina) o ``"true_scale"`` (relingada con U1/U2
    de cada panel; ``stretched=True`` la lleva a malla estirada). Coordenadas en metros.
    """
    if mode not in ("schematic", "true_scale"):
        raise ValueError(f"modo desconocido: {mode!r} (use 'schematic' o 'true_scale')")
    by_plane: dict[str, list[Panel]] = {}
    for p in spec.panels:
        for plane in panel_planes(p):
            by_plane.setdefault(plane, []).append(p)
    shapes: dict[str, tuple[PanelShape, ...]] = {}
    bands: dict[str, tuple[Band, ...]] = {}
    for plane in PLANE_ORDER:
        if plane in by_plane:
            shapes[plane], bands[plane] = _layout_plane(plane, by_plane[plane], mode, stretched)
    return NetLayout(
        net_id=spec.id,
        mode=mode,
        stretched=stretched or mode == "schematic",
        shapes=shapes,
        bands=bands,
        bbox=_bbox(s for group in shapes.values() for s in group),
    )
