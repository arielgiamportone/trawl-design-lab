"""Fase 13.2: el motor con componentes del catálogo, la lista de materiales y el armado óptimo."""

from __future__ import annotations

import dataclasses
from functools import cache

import pytest

from trawlkit import DesignCase, run
from trawlkit.catalog import catalog_case
from trawlkit.components import TwineItem, WireItem, get_component, load_components
from trawlkit.cost import bill_of_materials
from trawlkit.io import Section, load_doors, load_net, load_vessels
from trawlkit.model import DesignResult
from trawlkit.optimize import optimise_components


@cache
def _a3() -> DesignCase:
    net = load_net("fao_a3_standard")
    vessels = {v.id: v for v in load_vessels().vessels}
    return DesignCase(net, vessels["fao_a3_150hp"], load_doors().doors[0])


@cache
def _a3_result() -> DesignResult:
    return run(_a3())


@cache
def _wb60() -> DesignCase:
    return catalog_case(load_net("fao_wb_bt2p_60hp")).case


def test_without_component_fields_the_a3_result_is_unchanged() -> None:
    case = _a3()
    assert case.warp_id is None and case.float_id is None and case.twine_id is None
    r = _a3_result()
    assert r.warps.selection.id == "steel_6x19_seale_13mm"
    assert r.floats.count == 12


def test_twine_from_the_catalogue_replaces_all_panels_but_the_codend() -> None:
    twine = get_component("twine", "twine_pe_twisted_r1410")
    assert isinstance(twine, TwineItem)
    case = dataclasses.replace(_a3(), twine_id=twine.id)
    for p in case.net.panels:
        if p.section is Section.CODEND:
            assert p.material == "PA"
        else:
            assert (p.material, p.twine_diameter_mm) == ("PE", twine.diameter_mm)
    assert any(twine.id in n for n in case.net.notes)
    run(case)
    with pytest.raises(ValueError, match="no_such"):
        dataclasses.replace(_a3(), twine_id="no_such_twine")


def test_component_warp_float_and_filters() -> None:
    r = run(dataclasses.replace(_a3(), warp_id="wire_6x24_fc_16mm"))
    assert r.warps.selection.id == "wire_6x24_fc_16mm"
    r = run(dataclasses.replace(_a3(), generic_only=True))
    wire = get_component("wire", r.warps.selection.id)
    assert isinstance(wire, WireItem) and wire.brand is None
    # Con una boya del catálogo, el número sale de la flotación requerida.
    r = run(dataclasses.replace(_a3(), float_id="float_pl_280mm_8"))
    assert r.floats.diameter_mm == 280
    assert r.floats.count < 12
    assert any("float_pl_280mm_8" in n for n in r.notes)


def test_bill_of_materials_lines_and_missing_prices() -> None:
    r = _a3_result()
    bom = bill_of_materials(r)
    keys = [ln.key for ln in bom.lines]
    assert keys[:2] == ["netting_pa", "headrope"]
    assert {"bridles", "sweeps", "warps", "floats", "doors", "ballast"} <= set(keys)
    # Los grilletes (cantidad supuesta) son opcionales: sin precio no cuentan como faltantes.
    assert bom.totals == {} and bom.missing_prices == len(bom.lines) - 1
    by_key = {ln.key: ln for ln in bom.lines}
    assert by_key["warps"].quantity == pytest.approx(r.warps.quantity_m)
    assert by_key["netting_pa"].quantity == pytest.approx(
        sum(row.weight_air_kg for row in r.geometry.std.rows), rel=1e-3
    )
    priced = bill_of_materials(
        r,
        {
            "steel_6x19_seale_13mm": {
                "value": 2.0,
                "currency": "USD",
                "unit": "m",
                "date": "2026-10",
                "source": "t",
            },
            "doors": {
                "value": 500,
                "currency": "USD",
                "unit": "unit",
                "date": "2026-10",
                "source": "t",
            },
            # Unidad equivocada: no se usa (un precio por kg no vale para boyas por unidad).
            "floats": {
                "value": 3,
                "currency": "USD",
                "unit": "kg",
                "date": "2026-10",
                "source": "t",
            },
        },
    )
    lines = {ln.key: ln for ln in priced.lines}
    assert lines["doors"].cost == 1000.0
    assert lines["warps"].cost == pytest.approx(2.0 * r.warps.quantity_m, abs=0.01)
    assert lines["floats"].cost is None
    expected = sum(ln.cost or 0.0 for ln in priced.lines)
    assert priced.totals["USD"] == pytest.approx(expected, abs=0.02)
    # Con precio: malletas, patentes, cable y portones; los grilletes son opcionales.
    assert priced.missing_prices == len(priced.lines) - 5


def test_bill_of_materials_with_chain_in_metres() -> None:
    r = run(dataclasses.replace(_a3(), chain_id=load_components("chain")[0].id))
    line = next(ln for ln in bill_of_materials(r).lines if ln.key == "chain")
    assert line.unit == "m" and line.quantity > 0


def test_component_optimiser_on_the_workbook_60hp_net() -> None:
    res = optimise_components(_wb60(), "drag")
    assert res.feasible and res.evaluated >= 20
    best = res.best
    for c in best.constraints:
        assert c.ok, c
    assert best.warp_id is not None
    assert best.evaluation.door_required_m2 <= best.evaluation.door_area_m2
    # El armado de menor resistencia no tiene más R_T que ninguna alternativa.
    assert all(best.evaluation.demand_kgf <= a.evaluation.demand_kgf for a in res.alternatives)
    assert 1 <= len(res.alternatives) <= 4
    eff = optimise_components(_wb60(), "efficiency")
    assert eff.best.evaluation.energy_kgf_m_per_m2 <= best.evaluation.energy_kgf_m_per_m2 + 1e-9


def test_generic_only_is_not_more_expensive_than_branded() -> None:
    generic = "twine_pe_twisted_r1410"
    branded = "garware_sng_2_1mm"
    prices = {
        generic: {"value": 6.0, "currency": "USD", "unit": "kg", "date": "2026-10", "source": "t"},
        branded: {"value": 9.0, "currency": "USD", "unit": "kg", "date": "2026-10", "source": "t"},
    }
    kw = {"speed_kn": 2.3, "doors": ["door_flat_75hp"], "floats": ["float_pl_200mm_6"]}
    gen = optimise_components(_wb60(), "cost", twines=[generic], prices=prices, **kw)
    brand = optimise_components(_wb60(), "cost", twines=[branded], prices=prices, **kw)
    assert gen.best.cost is not None and brand.best.cost is not None
    assert gen.best.cost <= brand.best.cost
    assert gen.best.bom.missing_prices == brand.best.bom.missing_prices > 0
    with pytest.raises(ValueError, match="objetivo"):
        optimise_components(_wb60(), "speed")
