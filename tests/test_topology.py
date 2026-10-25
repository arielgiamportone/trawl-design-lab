"""Fase 12.2: redes de 4 paneles, pelágicas y de pareja en el motor y el simulador."""

from __future__ import annotations

import dataclasses
import math

import numpy as np
import pytest

from trawlkit.catalog import catalog_case
from trawlkit.drawing.layout import layout_net
from trawlkit.drawing.scale import net_scale_svg
from trawlkit.drawing.sheet import net_sheet_svg
from trawlkit.io.loader import load_net
from trawlkit.io.schema import NetSpec, Panel
from trawlkit.model import run
from trawlkit.netcheck import check, errors
from trawlkit.netting import cut_code_ratio
from trawlkit.sim import simulate
from trawlkit.sim.scenario import Scenario
from trawlkit.topology import equivalent_two_panel, has_sides, is_a3_topology

#: Costados de la red sintética de 4 paneles: (id, mallero, alto, mallas de boca, de bolsa),
#: uno por estación del cuerpo y el copo del arrastre de fondo del Fisherman's Workbook.
SIDES = (
    ("S1", 120.0, 10, 20, 18),
    ("S2", 80.0, 50, 27, 20),
    ("S3", 60.0, 50, 27, 16),
    ("S4", 40.0, 100, 24, 20),
    ("S5", 40.0, 150, 20, 20),
)


def four_panel_net() -> NetSpec:
    """Red de 4 paneles sintética: la del Workbook con costados en el cuerpo y el copo."""
    base = load_net("fao_wb_bt2p_60hp")
    ref = next(p for p in base.panels if p.id == "G2")
    sides = [
        Panel.model_validate(
            {
                **ref.model_dump(exclude={"id", "name", "cut_code"}),
                "id": pid,
                "plane": "side",
                "section": "codend" if pid == "S5" else "body",
                "count": 2,
                "mesh_mm": mesh,
                "meshes_depth": depth,
                "meshes_top": top,
                "meshes_bottom": bottom,
            }
        )
        for pid, mesh, depth, top, bottom in SIDES
    ]
    return base.model_copy(update={"id": "synthetic_4p", "panels": [*base.panels, *sides]})


def pelagic_net() -> NetSpec:
    """La red del Workbook declarada pelágica (sin lastre)."""
    base = load_net("fao_wb_bt2p_60hp")
    return base.model_copy(update={"id": "synthetic_pelagic", "family": "pelagic"})


def _station_meshes(spec: NetSpec) -> float:
    """Circunferencia estirada de la red en la estación del copo [m]."""
    return sum(
        p.meshes_top * p.mesh_mm / 1000 * (1 if p.plane.value != "side" else p.count)
        for p in spec.panels
        if p.section.value == "codend"
    )


def test_cut_code_ratio_matches_cut_table() -> None:
    assert cut_code_ratio("AB") == 1.0
    assert cut_code_ratio("AN") == 0.0
    assert cut_code_ratio("1N2B") == pytest.approx(0.5)
    assert cut_code_ratio("1N4B") == pytest.approx(2 / 3)
    assert cut_code_ratio("3N2B") == pytest.approx(0.25)
    with pytest.raises(ValueError):
        cut_code_ratio("XYZ")


def test_a3_keeps_excel_topology_and_catalogue_does_not() -> None:
    assert is_a3_topology(load_net("fao_a3_standard"))
    assert is_a3_topology(load_net("fao_a3_modified"))
    assert not is_a3_topology(load_net("fao_wb_bt2p_60hp"))
    assert not is_a3_topology(four_panel_net())


def test_equivalent_two_panel_keeps_circumference_and_length() -> None:
    spec = four_panel_net()
    assert has_sides(spec)
    eq = equivalent_two_panel(spec)
    assert not has_sides(eq)
    assert _station_meshes(eq) == pytest.approx(_station_meshes(spec))
    lay4, lay2 = layout_net(spec), layout_net(eq)
    for plane in ("upper", "lower"):
        assert lay2.length(plane) == pytest.approx(lay4.length(plane))

    # Superficie de paño (mallas × alto) conservada.
    def area(s: NetSpec) -> float:
        return sum(
            p.count * (p.meshes_top + p.meshes_bottom) / 2 * p.meshes_depth * p.mesh_mm**2
            for p in s.panels
        )

    assert area(eq) == pytest.approx(area(spec))


def test_side_layout_aligned_with_upper_stations() -> None:
    spec = four_panel_net()
    lay = layout_net(spec, "true_scale")
    sides = lay.central("side")
    upper = lay.central("upper")
    assert [s.id for s in sides] == ["S1", "S2", "S3", "S4", "S5"]
    # Contadas desde el copo, las estaciones del costado y del dorso terminan a la misma altura
    # a malla estirada (mismo alto y mallero).
    lay_s = layout_net(spec, "schematic")
    pairs = zip(reversed(lay_s.central("side")), reversed(lay_s.central("upper")), strict=False)
    for s, u in pairs:
        assert s.height == pytest.approx(u.height)
    assert sides[-1].y_bottom == pytest.approx(upper[-1].y_bottom)
    assert sides[0].y_top == pytest.approx(upper[1].y_top, abs=0.3)


def test_four_panel_net_checks_runs_and_draws() -> None:
    spec = four_panel_net()
    assert errors(spec) == []
    bad = spec.model_copy(
        update={
            "panels": [
                p.model_copy(update={"meshes_depth": 60}) if p.id == "S2" else p
                for p in spec.panels
            ]
        }
    )
    assert any(i.code == "side" and i.level == "error" for i in check(bad))
    result = run(catalog_case(spec).case)
    s = result.summary()
    assert not [k for k, v in s.items() if isinstance(v, float) and math.isnan(v)]
    # La circunferencia crece con los costados.
    base = run(catalog_case("fao_wb_bt2p_60hp").case)
    assert result.dimensions.std.max_circumference_m > base.dimensions.std.max_circumference_m
    sheet = net_sheet_svg(result)
    assert "COSTADOS" in sheet and ">S3<" in sheet
    assert "COSTADOS" in net_scale_svg(result)
    sim = simulate(result, 2.5, resolution=2, coarse_resolution=None)
    assert sim.converged


def test_pelagic_net_does_not_touch_the_bottom() -> None:
    cc = catalog_case(pelagic_net(), seabed="sand")
    result = run(cc.case)
    assert result.performance.seabed_friction_kgf == 0.0
    assert any(n.startswith("pelagic_not_applicable") for n in result.notes)
    sim = simulate(result, 2.5, resolution=2, coarse_resolution=None)
    assert sim.converged
    # Sin fondo: el burlón lastrado baja por debajo del nivel de los puntos de remolque, sin
    # reacción ni rozamiento.
    assert float(np.min(sim.nodes[:, 2])) < 0.0
    assert sim.friction_kgf == 0.0
    assert sim.operation.get("contact_width_m", 0.0) == 0.0


def test_pair_trawl_has_no_doors_and_two_vessels() -> None:
    cc = catalog_case("bobp_wp13_pair_ho80")
    assert cc.case.is_pair
    r = run(cc.case)
    assert float(np.max(r.doors.rig_drag_kgf)) == 0.0
    head = float(r.case.net.headrope.length_m)  # type: ignore[union-attr]
    assert r.spread.horizontal_opening_m == pytest.approx(0.5 * head)
    assert any(n.startswith("pair_trawl") for n in r.notes)
    # El tiro disponible es el de dos buques: la misma red con un solo buque y portones queda
    # con una ventana de velocidad menor.
    otter = run(dataclasses.replace(cc.case, rig="otter"))
    assert r.summary()["max_speed_kn"] > otter.summary()["max_speed_kn"]
    wide = run(dataclasses.replace(cc.case, pair_wing_spread_m=14.0))
    assert wide.spread.horizontal_opening_m == pytest.approx(14.0)
    assert wide.doors.spread_m > r.doors.spread_m
    # En el simulador, los puntos de remolque quedan fijos aunque se pidan portones acoplados.
    sc = Scenario(coupled_doors=True)
    sim = simulate(r, 2.5, resolution=2, coarse_resolution=None, scenario=sc)
    assert sim.converged
    assert sim.door_spread_m == pytest.approx(r.doors.spread_m)
