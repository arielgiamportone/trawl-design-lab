"""Fase 19.3: portones en profundidad (biblioteca de polares, elección y polar dinámica)."""

from __future__ import annotations

import re
import warnings
from pathlib import Path

import pytest

from trawlkit.api import service
from trawlkit.components import DoorItem, check, get_component, load_components
from trawlkit.door_selection import select_doors
from trawlkit.i18n import use_lang
from trawlkit.io import Door, load_doors
from trawlkit.model import DesignResult
from trawlkit.rigging import (
    PolarExtrapolationWarning,
    door_polar,
    load_door_polars,
    polar_extrapolated,
    polar_for_type,
)
from trawlkit.rigging.polars import DOOR_TYPES, get_polar
from trawlkit.sim import Scenario, simulate
from trawlkit.sim.doors import calibrate_nw, seafish_attack_angle

BIB = Path(__file__).resolve().parents[1] / "docs" / "referencias.bib"


@pytest.fixture(scope="module")
def a3() -> DesignResult:
    return service.run_case(service.build_case(net="fao_a3_standard"))


# --- Biblioteca de polares ---------------------------------------------------------------------


def test_library_loads_with_sources_and_conditions() -> None:
    lib = load_door_polars()
    sfia = [p for p in lib.polars if p.source.document == "sfia1993"]
    mell = [p for p in lib.polars if p.source.document == "mellibovsky2018"]
    assert len(sfia) == 26 and len(mell) == 4
    keys = set(re.findall(r"^@\w+\{([^,]+),", BIB.read_text("utf-8"), re.M))
    for p in lib.polars:
        assert p.source.document in keys
        assert p.source.page and p.conditions in lib.conditions
        assert len(p.usable()) >= 2, p.id
        for c in p.usable():
            assert c.cl is not None and c.cd is not None
            assert 0.3 < c.cl < 2.6 and 0.1 < c.cd < 1.3, (p.id, c)
    for p in sfia:
        assert p.max_cl is not None
        assert {"length_m", "height_m", "area_m2", "aspect_ratio"} <= set(p.model)
        # AR = H/L de la hoja (redondeo de dos cifras)
        assert p.model["height_m"] / p.model["length_m"] == pytest.approx(
            p.model["aspect_ratio"], abs=0.011
        )


def test_excel_polars_are_the_seafish_sheets() -> None:
    """Las polares del libro Excel (doors.yaml) son las hojas de Seafish 1993, número a número."""
    doors = {d.id: d for d in load_doors().doors}
    for door_id, sheet in (
        ("fao_flat_wood_a3", "sfia1993_flat_wooden"),
        ("morgere_polivalente_oval", "sfia1993_morgere_polyvalent_ovale"),
    ):
        excel = {(c.angle_deg, c.cl, c.cd) for c in doors[door_id].coefficients if c.cl}
        seafish = {(c.angle_deg, c.cl, c.cd) for c in get_polar(sheet).usable(with_max=True)}
        assert excel == seafish


def test_type_polars() -> None:
    kinds = {}
    for t in DOOR_TYPES:
        p = polar_for_type(t)
        kinds[t] = p.kind.value
        angles = [c.angle_deg for c in p.coefficients]
        assert angles == sorted(angles) and len(angles) >= 4
    assert kinds == {
        "flat": "transcribed",
        "v": "derived",
        "oval": "transcribed",
        "cambered": "derived",
        "multifoil": "derived",
        "high_aspect": "derived",
    }
    v = polar_for_type("v")
    vees = [get_polar(i) for i in v.polar_ids]
    c35 = next(c for c in v.coefficients if c.angle_deg == 35)
    mean = sum(next(q.cl for q in p.usable() if q.angle_deg == 35) for p in vees) / 3
    assert c35.cl == pytest.approx(mean, abs=1e-3)
    # alias del catálogo
    assert polar_for_type("suberkrub") is polar_for_type("high_aspect")
    assert polar_for_type("flat_wood").type == "flat"
    with pytest.raises(KeyError):
        polar_for_type("lava")

    # máximo CL por tipo: plano < V < cambado (Seafish, sección 3-14)
    def cmax(t: str) -> float:
        return max(c.cl or 0.0 for c in polar_for_type(t).coefficients)

    assert cmax("flat") < cmax("v") < cmax("cambered")


def test_catalogue_v_and_suberkrub_polars_are_measured() -> None:
    v = get_component("door", "door_v_300hp")
    s = get_component("door", "door_suberkrub_2m2")
    assert isinstance(v, DoorItem) and isinstance(s, DoorItem)
    assert v.provenance["coefficients"].document == "sfia1993"
    assert v.provenance["coefficients"].kind == "derived"
    assert s.provenance["coefficients"].document == "mellibovsky2018"
    assert [c.model_dump() for c in v.coefficients] == polar_for_type("v").coefficient_dicts()
    assert [c.model_dump() for c in s.coefficients] == polar_for_type(
        "high_aspect"
    ).coefficient_dicts()
    flat = get_component("door", "door_flat_200hp")
    assert flat.provenance["coefficients"].document == "sfia1993"
    assert flat.provenance["coefficients"].kind == "transcribed"


def test_manufacturer_doors() -> None:
    vonin = load_components("door", brands=["Vónin"])
    vonin = [d for d in vonin if d.brand == "Vónin"]
    assert {d.product for d in vonin} == {"Storm 2", "Tornado", "Twister"}
    storm = get_component("door", "door_vonin_storm2_10m2")
    assert isinstance(storm, DoorItem)
    assert storm.weight_air_kg == 4900 and storm.area_m2 == 10
    assert storm.provenance["coefficients"].kind == "assumed"
    assert storm.provenance["weight_air_kg"].kind == "transcribed"
    twister = [d for d in vonin if d.product == "Twister"]
    assert any("4.39" in n for d in twister for n in d.notes)  # dato declarado, sólo nota
    morgere = [d for d in load_components("door") if d.brand == "Morgère" and d.product]
    assert {d.product for d in morgere} == {"OvalFoil", "PolyFoil", "PFPE"}
    for d in morgere:
        assert isinstance(d, DoorItem)
        assert d.weight_air_kg is None
        codes = {i.code for i in check(d)}
        assert "weight_missing" in codes
        assert not [i for i in check(d) if i.level == "error"]
    pfpe = get_component("door", "door_morgere_pfpe01")
    assert pfpe.length_m == 1.4 and pfpe.provenance["length_m"].kind == "transcribed"


# --- Interpolación ------------------------------------------------------------------------------


def test_corrected_polar_interpolates_and_warns_when_extrapolating() -> None:
    door = load_doors().doors[0]
    p = door_polar(door, 33.5, interpolate=True)
    assert p.cl == pytest.approx(0.93 + 0.5 * (0.86 - 0.93))
    assert p.cd == pytest.approx(0.71 + 0.5 * (0.74 - 0.71))
    # modo del libro: sólo ángulos tabulados
    with pytest.raises(KeyError):
        door_polar(door, 33.5)
    # extrapolación: aviso hasta 5° fuera del rango, error más allá
    with pytest.warns(PolarExtrapolationWarning):
        low = door_polar(door, 23.0, interpolate=True)
    assert low.cl == pytest.approx(0.80 - 2 * (0.92 - 0.80) / 5)
    assert polar_extrapolated(door, 23.0) and not polar_extrapolated(door, 30.0)
    with pytest.raises(KeyError):
        door_polar(door, 15.0, interpolate=True)
    morgere = next(d for d in load_doors().doors if d.id == "morgere_polivalente_oval")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert door_polar(morgere, 28.0, interpolate=True).cl == pytest.approx(1.22 - 0.02 / 3)


def test_extrapolated_angle_is_noted_in_corrected_run() -> None:
    case = service.build_case(net="fao_a3_standard", params={"door_attack_angle_deg": 47.0})
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", PolarExtrapolationWarning)
        r = service.run_case(case)
    assert any(n.startswith("door_polar:") for n in r.notes)


# --- Elección de portones ---------------------------------------------------------------------


def test_selection_a3_gives_the_a3_door(a3: DesignResult) -> None:
    sel = select_doors(a3)
    assert sel.required_m2 == pytest.approx(a3.doors.required_area.per_door_m2)
    ids = [c.id for c in sel.candidates]
    assert "fao_flat_wood_a3" in ids
    flats = [c for c in sel.candidates if c.type and c.type.startswith("flat")]
    assert flats[0].id == "fao_flat_wood_a3"  # el plano más justo es el de la A-3
    a3_door = next(c for c in sel.candidates if c.id == "fao_flat_wood_a3")
    assert a3_door.required_m2 == pytest.approx(sel.required_m2)  # mismo tipo, sin margen
    assert not a3_door.margin_applied and a3_door.weight_status == "ok"
    assert a3_door.backstrop_m == pytest.approx((1.9, 2.85))
    for c in sel.candidates:
        assert c.ok and c.area_m2 >= c.required_m2 * (1 - 1e-9)
        assert c.type != "suberkrub"  # red de fondo: sin pelágicos
        if c.margin_applied:  # Seafish: +10 % al pasar a más CL
            assert c.cl > a3.doors.polar.cl
            assert c.required_m2 == pytest.approx(sel.required_m2 * 0.93 / c.cl * 1.1)
    ordered = [c.area_margin for c in sel.candidates]
    assert ordered == sorted(ordered)


def test_selection_filters_weight_and_language(a3: DesignResult) -> None:
    sel = select_doors(a3, types=["oval"], generic_only=True)
    assert sel.candidates and all(c.type == "oval" for c in sel.candidates)
    for c in sel.candidates:
        assert c.angle_deg == 35.0 and c.attack_angle is not None
        assert c.attack_angle["document"] == "prado1990"
    mor = select_doors(a3, brands=["Morgère"], types=["multifoil"])
    assert all(c.weight_status == "missing" for c in mor.candidates)
    with use_lang("en"):
        en = select_doors(a3, brands=["Morgère"], types=["multifoil"]).candidates[0]
    assert "ask the manufacturer" in en.warnings[0]


def test_select_route(a3: DesignResult) -> None:
    from fastapi.testclient import TestClient

    from trawlkit.api.app import app

    client = TestClient(app)
    r = client.post("/doors/select", json={"max_results": 3})
    assert r.status_code == 200
    body = r.json()
    assert len(body["candidates"]) == 3
    assert body["required_m2"] == pytest.approx(a3.doors.required_area.per_door_m2)
    r = client.get("/catalog/door-polars?lang=en")
    assert r.status_code == 200 and len(r.json()) == 6
    assert r.json()[0]["label"] == "Flat rectangular"


# --- Polar dinámica en la simulación acoplada --------------------------------------------------


def test_seafish_simplified_angle_example() -> None:
    """Ejemplo del Reference Vee (App. III-14/15): la tabla de Y₂ y el cruce hacia 36°."""
    # con n_w = 0,24 el cruce está entre 35 y 40° (tabla del App. III-15)
    a = seafish_attack_angle(6.0, 18.0, 0.24)
    assert 35.0 < a < 40.0
    nw = calibrate_nw(32.0, 4.0, 12.0)
    assert seafish_attack_angle(4.0, 12.0, nw) == pytest.approx(32.0, abs=1e-6)
    # cable más abierto → menos ángulo; patente más abierta → más ángulo
    assert seafish_attack_angle(6.0, 12.0, nw) < 32.0 < seafish_attack_angle(4.0, 16.0, nw)


def test_coupled_dynamic_polar_converges(a3: DesignResult) -> None:
    fixed = simulate(a3, 3.0, resolution=3, scenario=Scenario(dynamic_door_polar=False))
    dyn = simulate(a3, 3.0, resolution=3, scenario=Scenario())
    assert fixed.converged and dyn.converged
    assert fixed.door_attack["mode"] == "fixed" and dyn.door_attack["mode"] == "dynamic"
    d = dyn.door_attack
    assert d["angle_deg"] == pytest.approx(d["target_deg"], abs=0.2)
    assert not d["clamped"] and 32.0 < d["angle_deg"] < 40.0
    # flat: más allá de 32° baja el CL → menos separación de portones
    assert d["cl"] < 0.93 and dyn.door_spread_m < fixed.door_spread_m
    assert fixed.door_attack["target_deg"] == pytest.approx(d["angle_deg"], abs=1.5)


def test_basic_simulator_has_no_door_attack(a3: DesignResult) -> None:
    door = Door.model_validate(load_doors().doors[0].model_dump())
    assert door.id == "fao_flat_wood_a3"
    assert simulate(a3, 3.0, resolution=2).door_attack == {}
