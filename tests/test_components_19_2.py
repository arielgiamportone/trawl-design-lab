"""Fase 19.2: más fabricantes, grilletes, cabos y cadena del catálogo y lista de precios."""

from __future__ import annotations

import dataclasses
from functools import cache

import pytest

from trawlkit import DesignCase, run
from trawlkit.components import (
    ChainItem,
    RopeItem,
    ShackleItem,
    TwineItem,
    axial_stiffness,
    check,
    get_component,
    load_components,
    parse_component,
)
from trawlkit.cost import SHACKLES_PER_SIDE, bill_of_materials, select_shackle
from trawlkit.io import load_doors, load_net, load_vessels
from trawlkit.prices import read_prices, write_prices
from trawlkit.rigging import RopeSpec, select_rope_component


@cache
def _a3() -> DesignCase:
    net = load_net("fao_a3_standard")
    vessels = {v.id: v for v in load_vessels().vessels}
    return DesignCase(net, vessels["fao_a3_150hp"], load_doors().doors[0])


# --- datos transcriptos (comprobados en la imagen de la página del catálogo) -----------------


def test_hampidjan_rows_are_the_page_values() -> None:
    magnet = get_component("twine", "hampidjan_magnet_standard_3mm")
    assert isinstance(magnet, TwineItem)
    # p. 183: 3,0 mm · 281 m/kg · 355 g/100 m · 175 kg con nudo; alargamiento 15 %.
    assert (magnet.runnage_m_per_kg, magnet.knot_breaking_load_kgf) == (281, 175)
    assert magnet.rtex == pytest.approx(3550)
    assert magnet.elongation_pct == 15 and magnet.breaking_load_kgf is None
    wire = get_component("wire", "oliveira_green_strand_6x19_poly_core_16mm")
    assert (wire.weight_kg_per_m, wire.breaking_load_t) == (0.95, 14.8)  # type: ignore[attr-defined]
    floats = get_component("float", "atlantic_floats_sa1101")
    assert floats.buoyancy_kgf == pytest.approx(8.61)  # type: ignore[attr-defined]
    assert floats.provenance["buoyancy_kgf"].kind == "derived"
    chain = get_component("chain", "hampidjan_trygg_long_link_16mm")
    assert isinstance(chain, ChainItem)
    # SWL 6,4 t con factor 5:1 → rotura 32 t (derivada).
    assert chain.breaking_load_t == pytest.approx(32.0)
    assert chain.provenance["breaking_load_t"].kind == "derived"


def test_rope_ea_is_derived_from_the_published_elongation() -> None:
    rope = get_component("rope", "hampidjan_dynice_75_duracoat_16mm")
    assert isinstance(rope, RopeItem)
    expected = 27.4 * 1000 * 9.80665 / 0.035 / 1000  # kN
    assert rope.ea_kn == pytest.approx(expected, rel=0.01)
    assert rope.provenance["ea_kn"].kind == "derived"
    ea, prov = axial_stiffness(rope)  # type: ignore[misc]
    assert ea == rope.ea_kn and prov.kind == "derived"


def test_garware_twisted_twine_is_a_draft_with_an_assumed_diameter() -> None:
    item = get_component("twine", "garware_380_d_regular_380_d_24_ply")
    assert item.status == "draft"
    assert item.provenance["diameter_mm"].kind == "assumed"
    assert "VERIFICAR" in (item.provenance["diameter_mm"].note or "")
    assert item.id not in {t.id for t in load_components("twine")}  # sólo publicados


def test_new_sources_are_cited() -> None:
    keys = {
        s.key
        for k in ("twine", "rope", "wire", "chain", "float")
        for it in load_components(k)
        for s in it.sources
    }
    assert {"hampidjan_catalogue", "gunnebo_llz"} <= keys
    shackles = load_components("shackle")
    assert {s.key for it in shackles for s in it.sources} == {"hampidjan_catalogue", "crosby_g209"}


# --- grilletes -------------------------------------------------------------------------------


def test_shackle_kind_and_validator() -> None:
    g = get_component("shackle", "crosby_g209_1_2in")
    assert isinstance(g, ShackleItem)
    assert (g.wll_t, g.weight_kg, g.pin_diameter_mm, g.body_diameter_mm) == (2.0, 0.33, 15.7, 12.7)
    assert g.breaking_load_t == pytest.approx(12.0)
    assert check(g) == []
    bad = parse_component(
        {
            "kind": "shackle",
            "id": "x",
            "name": "x",
            "size": "13 mm",
            "body_diameter_mm": 13,
            "pin_diameter_mm": 5,
            "wll_t": 20,
            "breaking_load_t": 10,
            "weight_kg": 5,
        }
    )
    codes = {(i.level, i.code) for i in check(bad)}
    assert ("error", "mbl") in codes
    assert {("warning", "weight"), ("warning", "wll"), ("warning", "pin")} <= codes


def test_select_shackle_by_working_load() -> None:
    s = select_shackle(2.5)
    assert s is not None and s.wll_t >= 2.5
    assert all(o.wll_t < 2.5 or o.wll_t >= s.wll_t for o in load_components("shackle"))
    assert select_shackle(1000.0) is None


# --- motor -----------------------------------------------------------------------------------


def test_rope_selection_rule() -> None:
    ref = RopeSpec("ref", "ref", 14.0, 0.6, 5.0)
    items = [
        {
            "id": "a",
            "material": "PP",
            "diameter_mm": 14,
            "weight_kg_per_m": 0.1,
            "breaking_load_t": 9,
        },
        {
            "id": "b",
            "material": "combinado",
            "diameter_mm": 12,
            "weight_kg_per_m": 0.4,
            "breaking_load_t": 9,
        },
        {
            "id": "c",
            "material": "combinado",
            "diameter_mm": 16,
            "weight_kg_per_m": 0.7,
            "breaking_load_t": 6,
        },
        {
            "id": "d",
            "material": "combinado",
            "diameter_mm": 18,
            "weight_kg_per_m": 0.8,
            "breaking_load_t": 8,
        },
    ]
    assert select_rope_component(items, ref, "combinado (PP + acero)").id == "c"
    weak = RopeSpec("ref", "ref", 14.0, 0.6, 50.0)
    assert select_rope_component(items, weak, "combinado").id == "b"  # el más fuerte (y menor id)
    assert select_rope_component(items, ref, "PA") is ref


def test_filters_select_headrope_and_footrope_from_the_catalogue() -> None:
    base = run(_a3())
    assert base.floats.headrope_rope.id == "combinado_12_acero6x24_7"
    r = run(dataclasses.replace(_a3(), generic_only=True))
    head = get_component("rope", r.floats.headrope_rope.id)
    foot = get_component("rope", r.ballast.footrope_rope.id)
    assert head.is_generic and foot.is_generic
    assert head.material == "combinado" and foot.material == "combinado"  # type: ignore[attr-defined]
    assert r.floats.headrope_rope.diameter_mm >= 12
    # Ningún combinado genérico llega a las 8,7 t del COMBINADO 14 del libro: el más fuerte.
    strongest = max(
        (c for c in load_components("rope", generic_only=True) if c.material == "combinado"),  # type: ignore[attr-defined]
        key=lambda c: c.breaking_load_t,  # type: ignore[attr-defined]
    )
    assert r.ballast.footrope_rope.id == strongest.id
    # Un cabo elegido en el caso manda sobre los filtros.
    r2 = run(
        dataclasses.replace(_a3(), generic_only=True, footrope_rope="pp_16_retorcido_3_cordones")
    )
    assert r2.ballast.footrope_rope.id == "pp_16_retorcido_3_cordones"


def test_chain_from_the_catalogue_in_the_ballast_stage() -> None:
    base = run(_a3())
    assert base.ballast.chain is None
    r = run(dataclasses.replace(_a3(), chain_id="gunnebo_llz_9mm"))
    bc = r.ballast.chain
    assert bc is not None and bc.weight_kg_per_m == 1.4
    assert bc.max_m == pytest.approx(r.ballast.limits.max_kg / 1.4)
    assert bc.min_m == pytest.approx(r.ballast.limits.min_kg / 1.4)
    assert bc.water_weight_max_kgf == pytest.approx(r.ballast.limits.max_kg * (1 - 1024 / 7800))
    # El lastre (kg) no cambia: la cadena sólo lo pasa a metros.
    assert r.ballast.limits == base.ballast.limits
    assert "chain" in r.ballast.to_dict()


def test_bill_of_materials_has_shackles_and_chain_metres() -> None:
    r = run(dataclasses.replace(_a3(), chain_id="gunnebo_llz_9mm"))
    lines = {ln.key: ln for ln in bill_of_materials(r).lines}
    sh = lines["shackles"]
    assert sh.quantity == 2 * SHACKLES_PER_SIDE["otter"] and sh.unit == "unit"
    item = get_component("shackle", sh.component_id or "")
    assert item.wll_t * 1000 >= r.warps.loads.working_load_kgf  # type: ignore[attr-defined]
    assert lines["chain"].quantity == pytest.approx(r.ballast.chain.max_m, abs=1e-3)  # type: ignore[union-attr]
    priced = bill_of_materials(
        r,
        {
            sh.component_id: {
                "value": 10,
                "currency": "USD",
                "unit": "unit",
                "date": "2026-10",
                "source": "t",
            }
        },
    )
    assert {ln.key: ln for ln in priced.lines}["shackles"].cost == pytest.approx(10.0 * sh.quantity)


# --- lista de precios ------------------------------------------------------------------------


def test_price_list_round_trip_csv_and_xlsx() -> None:
    prices = {
        "crosby_g209_5_8in": {
            "value": 12.5,
            "currency": "USD",
            "unit": "unit",
            "date": "2026-10",
            "source": "Ferretería del puerto",
        },
        "netting_pa": {
            "value": 7.25,
            "currency": "ARS",
            "unit": "kg",
            "date": "2026-09-01",
            "source": "x",
        },
    }
    lines = [{"key": "floats", "label": "Boyas", "unit": "unit"}]
    for fmt, name in (("csv", "p.csv"), ("xlsx", "p.xlsx")):
        data = write_prices(prices, fmt, lines)
        back = read_prices(data if fmt == "xlsx" else data.decode("utf-8"), name)
        assert back.prices == prices, fmt
        assert back.rows == 3 and not back.issues


def test_price_list_reader_reports_bad_rows() -> None:
    text = (
        "Componente,Price (USD),Currency,Unit,Date,Source\n"
        "doors,800,USD,u,,\n"
        "floats,abc,USD,unit,2026-10,\n"
        "warps,2.5,,m,2026-10,\n"
        "chain,1.2,USD,ton,2026-10,\n"
        "doors,900,EUR,unit,2026-10,y\n"
    )
    out = read_prices(text, "p.csv", currency="USD")
    assert out.prices["doors"]["value"] == 900 and out.prices["doors"]["currency"] == "EUR"
    assert out.prices["warps"]["currency"] == "USD"
    assert "floats" not in out.prices and "chain" not in out.prices
    codes = {(i.code, i.row) for i in out.issues}
    assert {("value", 2), ("unit", 4), ("duplicate", 5)} <= codes
    missing = read_prices("a;b\n1;2\n", "p.csv")
    assert missing.issues[0].code == "columns" and not missing.prices


def test_grilletes_sin_precio_no_dejan_incompleta_la_lista() -> None:
    from trawlkit.api.service import build_case
    from trawlkit.cost import bill_of_materials
    from trawlkit.model import run

    bom = bill_of_materials(run(build_case()), {})
    shackles = next(ln for ln in bom.lines if ln.key == "shackles")
    assert shackles.optional and shackles.cost is None
    assert bom.missing_prices == sum(ln.cost is None for ln in bom.lines) - 1
