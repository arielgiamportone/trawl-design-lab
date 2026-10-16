"""Disposición 2D de los paneles (`trawlkit.drawing.layout`)."""

from __future__ import annotations

import math
from collections.abc import Sequence
from itertools import combinations

import pytest

from trawlkit.drawing import NetLayout, PanelShape, layout_net
from trawlkit.drawing.layout import SECTION_ORDER, panel_size_m
from trawlkit.io import load_net
from trawlkit.io.schema import NetSpec, Panel
from trawlkit.netting import vertical_opening_coefficient

Point = tuple[float, float]
NETS = ("fao_a3_standard", "fao_a3_modified")
MODES = (("schematic", False), ("true_scale", False), ("true_scale", True))


@pytest.fixture(scope="module", params=NETS)
def spec(request: pytest.FixtureRequest) -> NetSpec:
    return load_net(request.param)


def _layouts(spec: NetSpec) -> list[NetLayout]:
    return [layout_net(spec, mode, stretched) for mode, stretched in MODES]  # type: ignore[arg-type]


def _signed_area(pts: Sequence[Point]) -> float:
    return 0.5 * sum(
        pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
        for i in range(len(pts))
    )


def _overlap_depth(a: Sequence[Point], b: Sequence[Point]) -> float:
    """Separating-axis test for convex polygons: penetration depth (≤ 0 → disjoint/touching)."""
    depth = math.inf
    for poly in (a, b):
        for i in range(len(poly)):
            (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % len(poly)]
            nx, ny = y0 - y1, x1 - x0
            n = math.hypot(nx, ny)
            nx, ny = nx / n, ny / n
            pa = [x * nx + y * ny for x, y in a]
            pb = [x * nx + y * ny for x, y in b]
            depth = min(depth, min(max(pa), max(pb)) - max(min(pa), min(pb)))
    return depth


def _is_convex(pts: Sequence[Point]) -> bool:
    signs = set()
    for i in range(len(pts)):
        (x0, y0), (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % len(pts)], pts[(i + 2) % len(pts)]
        cross = (x1 - x0) * (y2 - y1) - (y1 - y0) * (x2 - x1)
        if abs(cross) > 1e-12:
            signs.add(cross > 0)
    return len(signs) == 1


def test_planes_and_letters(spec: NetSpec) -> None:
    lay = layout_net(spec)
    assert lay.planes == ("upper", "lower")
    up = [b.panel_id for b in lay.bands["upper"]]
    lo = [b.panel_id for b in lay.bands["lower"]]
    if spec.id == "fao_a3_standard":
        assert up == ["A", "C", "E", "G", "H", "I"]
        assert lo == ["B", "D", "F", "G", "H", "J"]
    else:
        assert up == ["A", "C", "E", "G", "H", "I'"]
        assert lo == ["B", "D", "F", "G", "H", "I'"]
    # A, B, C, D, F de a pares (izq./der.); E, G, H, I/J/I' centrales.
    for plane in lay.planes:
        for s in lay.shapes[plane]:
            expected = "center" if s.id in {"E", "G", "H", "I", "J", "I'"} else None
            if expected:
                assert s.side == "center"
            else:
                assert s.side in ("left", "right")


def test_polygons_closed_convex_and_non_degenerate(spec: NetSpec) -> None:
    for lay in _layouts(spec):
        for plane in lay.planes:
            for s in lay.shapes[plane]:
                pts = s.points
                assert len(pts) >= 3
                assert len(set(pts)) == len(pts)  # sin vértices repetidos → se cierra solo
                assert _signed_area(pts) != 0
                assert s.area > 1e-3
                assert _is_convex(pts)
                assert s.height > 0
                assert s.width_top >= 0 and s.width_bottom > 0
                cx, cy = s.centroid
                assert s.y_top < cy < s.y_bottom


def test_no_overlap_within_a_plane(spec: NetSpec) -> None:
    for lay in _layouts(spec):
        for plane in lay.planes:
            for a, b in combinations(lay.shapes[plane], 2):
                assert _overlap_depth(a.points, b.points) <= 1e-9, (lay.mode, plane, a.id, b.id)


def test_wings_are_symmetric(spec: NetSpec) -> None:
    for lay in _layouts(spec):
        for plane in lay.planes:
            right = lay.side_chain(plane, "right")
            left = lay.side_chain(plane, "left")
            assert [s.id for s in right] == [s.id for s in left]
            assert right
            for r, lft in zip(right, left, strict=True):
                assert r.y_top == lft.y_top and r.y_bottom == lft.y_bottom
                assert r.x_top == pytest.approx((-lft.x_top[1], -lft.x_top[0]))
                assert r.x_bottom == pytest.approx((-lft.x_bottom[1], -lft.x_bottom[0]))
                assert min(r.x_top[0], r.x_bottom[0]) > 0  # no cruzan el eje
            for c in lay.central(plane):
                assert c.top_mid[0] == pytest.approx(0) and c.bottom_mid[0] == pytest.approx(0)


def test_mouth_to_codend_ordering(spec: NetSpec) -> None:
    for lay in _layouts(spec):
        for plane in lay.planes:
            bands = lay.bands[plane]
            assert bands[0].y_top == pytest.approx(0, abs=1e-12)
            for a, b in zip(bands, bands[1:], strict=False):
                assert a.y_bottom == pytest.approx(b.y_top, abs=1e-12)
            # Las alas (cadena lateral) arriba, la cadena central abajo, cada una por sección.
            sides = [s for s in lay.side_chain(plane)]
            central = list(lay.central(plane))
            assert max(s.y_bottom for s in sides) <= min(c.y_top for c in central) + 1e-12
            for chain in (sides, central):
                order = [SECTION_ORDER[s.section] for s in chain]
                assert order == sorted(order)
            assert central[-1].section.value == "codend"


def test_adjoining_edges_match(spec: NetSpec) -> None:
    lay = layout_net(spec)
    for plane in lay.planes:
        central = lay.central(plane)
        for a, b in zip(central, central[1:], strict=False):
            assert a.y_bottom == b.y_top
            assert a.bottom_mid == pytest.approx(b.top_mid)
            same = math.isclose(a.meshes_bottom * a.mesh_mm, b.meshes_top * b.mesh_mm)
            assert math.isclose(a.width_bottom, b.width_top) == same
        chain = lay.side_chain(plane)
        for a, b in zip(chain, chain[1:], strict=False):
            assert a.y_bottom == b.y_top
            assert a.x_bottom[1] == pytest.approx(b.x_top[1])  # esquina exterior común
            assert a.width_bottom == pytest.approx(b.width_top, rel=0.01)  # 97·80 ≈ 129·60
        # Ala inferior sobre el borde de boca del primer panel central, desde su esquina.
        wing, first = chain[-1], central[0]
        assert wing.y_bottom == first.y_top == lay.mouth_y(plane)
        assert wing.x_bottom[1] == pytest.approx(first.x_top[1])
        assert wing.x_bottom[0] > 0

    # E (412×60) − 2·C (117×80) → bocana de 100 mallas; G (372) − 2·F (143) → 86.
    e = lay.shape("upper", "E")
    c = lay.shape("upper", "C", "right")
    assert e.meshes_bottom == lay.shape("upper", "G").meshes_top == 372
    assert round(2 * c.x_bottom[0] * 1000 / e.mesh_mm) == 100
    assert round(c.width_bottom * 1000 / e.mesh_mm) == 156
    f = lay.shape("lower", "F", "right")
    g = lay.shape("lower", "G")
    assert f.meshes_bottom == 143 and g.meshes_top == 372
    assert round(2 * f.x_bottom[0] * 1000 / g.mesh_mm) == 86


def _edges_m(p: Panel, u1: float, u2: float) -> tuple[float, float, float]:
    return (
        p.meshes_top * p.mesh_mm * u1 / 1000,
        p.meshes_bottom * p.mesh_mm * u1 / 1000,
        p.meshes_depth * p.mesh_mm * u2 / 1000,
    )


def test_true_scale_dimensions(spec: NetSpec) -> None:
    hung = layout_net(spec, "true_scale")
    stretched = layout_net(spec, "true_scale", stretched=True)
    schematic = layout_net(spec, "schematic")
    for plane in hung.planes:
        for s in hung.shapes[plane]:
            u1 = float(s.panel.hanging_ratio or 0)
            u2 = float(vertical_opening_coefficient(u1))
            top, bottom, h = _edges_m(s.panel, u1, u2)
            assert s.width_top == pytest.approx(top, rel=1e-9)
            assert s.width_bottom == pytest.approx(bottom, rel=1e-9)
            assert s.height == pytest.approx(h, rel=1e-9)
            assert panel_size_m(s.panel, "true_scale") == pytest.approx((top, bottom, h))
        for s, t in zip(stretched.shapes[plane], schematic.shapes[plane], strict=True):
            top, bottom, h = _edges_m(s.panel, 1.0, 1.0)
            assert s.width_top == pytest.approx(top, rel=1e-9)
            assert s.height == pytest.approx(h, rel=1e-9)
            assert [c for p in s.points for c in p] == pytest.approx(
                [c for p in t.points for c in p]
            )
        # Largo estirado del plano = Σ N·mallero; el vientre coincide con NetDimensions.
        assert stretched.length(plane) == pytest.approx(
            sum(b.stretched_length_m for b in stretched.bands[plane])
        )
    assert stretched.length("lower") == pytest.approx(42.68 if spec.variant_of is None else 41.68)
    assert hung.length("lower") < stretched.length("lower")


def test_extent_and_lookup_helpers() -> None:
    lay = layout_net(load_net("fao_a3_standard"))
    assert lay.x_extent_at("upper", -1.0) is None
    xmin, xmax = lay.x_extent_at("upper", 20.0) or (0.0, 0.0)
    assert xmin == pytest.approx(-xmax) and xmax > 0
    assert lay.bbox[0] == pytest.approx(-lay.bbox[2])
    with pytest.raises(KeyError):
        lay.shape("upper", "J")
    s: PanelShape = lay.shape("upper", "A", "left")
    assert s.outer_side == s.left_side and s.inner_side == s.right_side
    assert s.x_range_at(s.y_bottom + 1) is None


def test_validation() -> None:
    spec = load_net("fao_a3_standard")
    with pytest.raises(ValueError, match="modo"):
        layout_net(spec, "isometric")  # type: ignore[arg-type]
    bad = spec.model_copy(
        update={"panels": [spec.panels[0].model_copy(update={"count": 3}), *spec.panels[1:]]}
    )
    with pytest.raises(ValueError):
        layout_net(bad)
    no_u1 = spec.model_copy(
        update={
            "panels": [spec.panels[0].model_copy(update={"hanging_ratio": None}), *spec.panels[1:]]
        }
    )
    layout_net(no_u1)  # el esquema no necesita U1
    with pytest.raises(ValueError, match="hanging_ratio"):
        layout_net(no_u1, "true_scale")
