"""Fase 13: catálogo de componentes (paño, cables, cabos, portones, boyas, cadenas)."""

from __future__ import annotations

from collections import Counter

import pytest

from trawlkit.components import (
    KINDS,
    ComponentBase,
    DoorItem,
    WireItem,
    check,
    generic_for,
    get_component,
    load_components,
    parse_component,
)
from trawlkit.io import load_catalogue, load_doors
from trawlkit.rigging import door_polar

#: Campos que usa el motor y que deben tener procedencia, por tipo.
ENGINE_FIELDS: dict[str, tuple[str, ...]] = {
    "twine": ("diameter_mm",),
    "wire": ("diameter_mm", "weight_kg_per_m", "breaking_load_t"),
    "rope": ("diameter_mm", "weight_kg_per_m", "breaking_load_t"),
    "door": ("length_m", "height_m", "area_m2", "coefficients"),
    "float": ("diameter_mm", "buoyancy_kgf"),
    "chain": ("link_diameter_mm", "weight_kg_per_m"),
}

#: Máximo de ítems por línea de producto de un fabricante (datos puntuales, no tablas enteras).
MAX_PER_PRODUCT = 10


@pytest.mark.parametrize("kind", KINDS)
def test_catalogue_is_loaded_unique_and_consistent(kind: str) -> None:
    items = load_components(kind)
    assert len(items) >= 10
    ids = [i.id for i in items]
    assert len(ids) == len(set(ids))
    for it in items:
        assert [i for i in check(it) if i.level == "error"] == [], it.id
        assert it.sources, it.id
        for f in ENGINE_FIELDS[kind]:
            assert f in it.provenance, f"{it.id}: {f} sin procedencia"
            if it.provenance[f].kind != "transcribed":
                assert it.provenance[f].note, f"{it.id}: {f} sin nota"


@pytest.mark.parametrize("kind", KINDS)
def test_every_kind_has_generics_and_brands_point_to_one(kind: str) -> None:
    items = load_components(kind)
    assert any(i.is_generic for i in items)
    for it in items:
        if not it.is_generic and it.generic_of is not None:
            g = generic_for(it)
            assert g is not None and g.is_generic and g.kind == kind


def test_manufacturer_data_is_spot_data_not_whole_tables() -> None:
    lines: Counter[tuple[str, str]] = Counter()
    for kind in KINDS:
        for it in load_components(kind):
            if it.brand and it.brand not in ("Moscuzza", "Trawlex", "Morgère"):
                lines[(it.brand, it.product or "")] += 1
    assert lines and max(lines.values()) <= MAX_PER_PRODUCT, lines


def test_filters_brand_region_generic() -> None:
    all_wire = load_components("wire")
    generic = load_components("wire", generic_only=True)
    assert generic and all(w.is_generic for w in generic)
    assert len(generic) < len(all_wire)
    bridon = load_components("wire", brands=["Bridon-Bekaert"])
    assert {w.brand for w in bridon} == {None, "Bridon-Bekaert"}
    latam = load_components("rope", region="latam")
    assert any(r.brand == "Moscuzza" for r in latam)
    europe = load_components("wire", region="latam")
    assert not any(w.brand == "PFEIFER" for w in europe)


def test_generic_values_follow_the_workbook() -> None:
    # Cable 6x19 (12/6/1) de 12 mm: Workbook 48,4 kg/100 m y 6420 kgf.
    w = get_component("wire", "wire_6x19_1261_fc_12mm")
    assert isinstance(w, WireItem)
    assert w.weight_kg_per_m == pytest.approx(0.484, rel=0.05)
    assert w.breaking_load_t == pytest.approx(6.42, rel=0.08)
    # Hilo PA R1280 tex: Workbook 1,37 mm, 67 kgf (el libro Excel de la A-3 usa 1,37 mm).
    t = get_component("twine", "twine_pa_twisted_r1280")
    assert t.diameter_mm == pytest.approx(1.37, rel=0.08)  # type: ignore[attr-defined]


def test_excel_a3_components_match_the_old_catalogues() -> None:
    warps = {w["id"]: w for w in load_catalogue("warps").items}
    for wid, raw in warps.items():
        it = get_component("wire", wid)
        assert it.weight_kg_per_m == raw["weight_kg_per_m"]  # type: ignore[attr-defined]
        assert it.provenance["breaking_load_t"].kind == "excel"
    ropes = {r["id"] for r in load_catalogue("ropes").items}
    assert ropes <= {r.id for r in load_components("rope")}
    doors = {d.id for d in load_doors().doors}
    assert doors <= {d.id for d in load_components("door")}


def test_generic_doors_work_with_the_engine_polar() -> None:
    flat = get_component("door", "door_flat_200hp")
    assert isinstance(flat, DoorItem)
    assert flat.hp_range == (200, 200)
    door = flat.to_door()
    polar = door_polar(door, 32.0)
    assert 0.8 < polar.cl < 1.0
    v = get_component("door", "door_v_200hp")
    assert isinstance(v, DoorItem)
    assert door_polar(v.to_door(), 32.0).cl < polar.cl
    rebyc = [d for d in load_components("door", region="latam") if d.country == "CO"]
    assert len(rebyc) == 4


def test_check_flags_implausible_user_item() -> None:
    bad = parse_component(
        {
            "kind": "wire",
            "id": "user_wire",
            "name": "aporte",
            "status": "user",
            "construction": "6x19",
            "diameter_mm": 10,
            "weight_kg_per_m": 2.0,
            "breaking_load_t": 50,
        }
    )
    codes = {i.code for i in check(bad)}
    assert {"weight", "mbl"} <= codes
    # Un aporte entra sólo si se pide y pasa los mismos filtros.
    assert bad.id not in {w.id for w in load_components("wire", extra=[bad])}
    got = load_components("wire", extra=[bad], statuses=("published", "user"))
    assert bad.id in {w.id for w in got}


def test_unknown_kind_and_id() -> None:
    with pytest.raises(KeyError):
        load_components("bobbin")
    with pytest.raises(KeyError):
        get_component("wire", "no_such_wire")
    assert isinstance(load_components("float")[0], ComponentBase)


def test_user_components_context_is_scoped() -> None:
    from trawlkit.components import user_components

    data = {
        "kind": "float",
        "id": "user_float_x",
        "name": "boya del puerto",
        "material": "plástico",
        "diameter_mm": 200,
        "buoyancy_kgf": 3.5,
    }
    with user_components([data]) as items:
        assert items[0].status == "user" and not items[0].is_generic
        assert get_component("float", "user_float_x").name == "boya del puerto"
        assert "user_float_x" in {f.id for f in load_components("float")}
        assert "user_float_x" not in {f.id for f in load_components("float", generic_only=True)}
    with pytest.raises(KeyError):
        get_component("float", "user_float_x")
