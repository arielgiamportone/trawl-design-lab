"""Guía de construcción (Fase 15): hoja de corte, armado, montaje en relingas y cortes."""

from __future__ import annotations

import json
from functools import cache

import pytest

from trawlkit.api import service
from trawlkit.construction import (
    ConstructionGuide,
    cut_cycle,
    describe_cut,
    float_positions,
    guide,
    join_rule,
    nearest_cut_code,
)
from trawlkit.dimensions import BOSOM_HANGING, WING_HANGING
from trawlkit.model import DesignResult
from trawlkit.netcheck import check

NETS = sorted(service.net_presets())


@cache
def _result(net: str = "fao_a3_standard", modified: str | None = None) -> DesignResult:
    return service.run_case(service.build_case(net, modified))


@cache
def _guide(net: str = "fao_a3_standard") -> ConstructionGuide:
    return guide(_result(net))


# --- ciclos de corte ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("code", "cycle"),
    [
        ("AB", (0, 0, 1)),
        ("AN", (1, 0, 0)),
        ("1N2B", (1, 0, 2)),
        ("1T2B", (0, 1, 2)),
        ("3N2B", (3, 0, 2)),
    ],
)
def test_cut_cycle(code: str, cycle: tuple[int, int, int]) -> None:
    assert cut_cycle(code) == cycle


def test_cut_cycle_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        cut_cycle("XYZ")


def test_describe_cut() -> None:
    assert describe_cut("1N2B", 36) == (
        18,
        "1N2B: 1 punta y 2 malletas por ciclo; repetir 18 veces",
    )
    assert describe_cut("AB", 36)[0] == 72
    assert describe_cut("AN", 10)[1].startswith("recto")


def test_nearest_cut_code() -> None:
    assert nearest_cut_code(0.0) == "AN"
    assert nearest_cut_code(1.0) == "AB"
    assert nearest_cut_code(0.5) == "1N2B"
    assert nearest_cut_code(0.65) == "1N4B"


# --- hoja de corte ------------------------------------------------------------------------------


def test_a3_cutting_sheet_matches_the_workbook() -> None:
    g = _guide()
    by_id = {p.id: p for p in g.pieces}
    assert [p.id for p in g.pieces] == list("ABCDEFGHIJ")
    a = by_id["A"]
    assert (a.meshes_mouth, a.meshes_codend, a.meshes_depth, a.pieces) == (3, 57, 36, 2)
    assert a.paired and [s.code for s in a.sides] == ["AB", "1N2B"]
    assert by_id["D"].sides[1].code == "1N4B"
    assert [s.code for s in by_id["E"].sides] == ["1N2B"] and not by_id["E"].paired
    # Paño F: el libro no da su corte (errata panel_f_cut_na); se infiere del cambio de ancho.
    f = by_id["F"]
    assert f.sides[1].inferred and f.sides[1].code == "1N4B"
    assert sum(p.pieces for p in g.pieces) == 17


@pytest.mark.parametrize("net", NETS)
def test_stock_covers_the_finished_netting(net: str) -> None:
    g = _guide(net)
    for p in g.pieces:
        assert p.stock_weight_kg >= p.weight_kg - 1e-9
        assert 0.0 <= p.waste <= 0.6
    assert sum(s.weight_kg for s in g.stock) >= sum(s.finished_kg for s in g.stock) - 1e-9
    assert sum(s.pieces for s in g.stock) == sum(p.pieces for p in g.pieces)


def test_paired_wings_nest_without_waste() -> None:
    a = next(p for p in _guide().pieces if p.id == "A")
    assert a.stock_width == 3 + 57 and a.waste == pytest.approx(0.0, abs=1e-12)


# --- armado -------------------------------------------------------------------------------------


def test_join_rule() -> None:
    assert join_rule("A", 57, "C", 57) == ("1:1", "malla a malla")
    ratio, rule = join_rule("G", 162, "H", 243)
    assert ratio == "2:3" and "2 mallas juntas de H cada 2.0" in rule and "81 tomas" in rule
    assert "por cada malla" in join_rule("X", 10, "Y", 35)[1]


def test_a3_assembly() -> None:
    joins = _guide().joins
    assert [j.step for j in joins] == list(range(1, len(joins) + 1))
    pairs = [(j.a, j.b) for j in joins]
    assert ("E", "G") in pairs and ("C", "E") in pairs and ("F", "G") in pairs
    wing = next(j for j in joins if (j.a, j.b) == ("C", "E"))
    # 117 mallas de 80 mm ocupan 156 de 60 mm (el «117/156» de la lámina); quedan 100 de bocana.
    assert (wing.meshes_a, wing.meshes_b, wing.times) == (117, 156, 2)
    assert "100 mallas" in wing.note
    assert joins[-1].kind == "side_seam"


@pytest.mark.parametrize("net", NETS)
def test_assembly_uses_every_seam_the_validator_checks(net: str) -> None:
    spec = service.net_presets()[net]
    joins = _guide(net).joins
    ids = {p.id for p in spec.panels}
    for j in joins:
        if j.kind in ("seam", "wing_to_body", "side_panel"):
            assert j.a in ids and j.b in ids and j.meshes_a > 0 and j.meshes_b > 0
    seam_errors = {tuple(i.panels) for i in check(spec) if i.code == "seam" and i.level == "error"}
    joined = {(j.a, j.b) for j in joins}
    assert seam_errors <= joined
    # Cada paño central o de ala, salvo el primero de cada cadena, recibe una unión por su boca.
    targets = [(j.b, j.plane) for j in joins if j.kind == "seam"]
    assert len(targets) == len(set(targets))


def test_four_panel_net_sews_its_sides_station_by_station() -> None:
    joins = _guide("scharfe_krill_front800").joins
    sides = [j for j in joins if j.kind == "side_panel"]
    assert {j.a for j in sides} == {f"S{i}" for i in range(1, 17)}
    assert all(j.times == 2 for j in sides)


# --- montaje, boyas, lastre y cortes ------------------------------------------------------------


def test_a3_hanging_matches_the_rope_pieces() -> None:
    h = {(s.rope, s.part): s for s in _guide().hanging}
    assert h["lima", "ala"].hanging == pytest.approx(WING_HANGING)
    assert h["lima", "ala"].meshes == 36 + 120
    assert h["lima", "bocana"].meshes == 412 - 2 * 156
    assert h["lima", "bocana"].hanging == pytest.approx(BOSOM_HANGING / 2)
    assert h["burlón", "ala"].panels == ("B", "D", "F")
    assert not any(s.warning for s in h.values())


def test_hanging_warns_when_the_rope_is_longer_than_the_netting() -> None:
    h = {(s.rope, s.part): s for s in _guide("bobp_wp13_pair_ho120").hanging}
    assert h["burlón", "bocana"].hanging > 1.1 and h["burlón", "bocana"].warning
    assert any("burlón" in n.lower() for n in _guide("bobp_wp13_pair_ho120").notes)


@pytest.mark.parametrize(
    ("count", "per_wing", "front"), [(12, 5, 3), (7, 2, 1), (5, 4, 2), (24, 9, 5)]
)
def test_float_positions_are_symmetric(count: int, per_wing: int, front: int) -> None:
    pos = float_positions(count, per_wing, front, 2.5, 13.0)
    xs = [p.x_m for p in pos]
    assert len(xs) == count and xs == sorted(xs)
    assert sorted(-x for x in xs) == pytest.approx(xs)
    assert max(abs(x) for x in xs) < 2.5 / 2 + 13.0


def test_a3_floats_and_ballast() -> None:
    g = _guide()
    assert len(g.floats) == 12 and g.float_diameter_mm == 200
    zones = {b.zone: b for b in g.ballast}
    assert zones["reglaje"].kg_max == 12 and zones["alas"].kg_min == 15


def test_rope_cuts_add_the_eye_allowance() -> None:
    r = _result()
    g = guide(r, eye_allowance_m=0.3)
    cuts = {c.key: c for c in g.ropes}
    assert cuts["headrope"].length_m == pytest.approx(r.dimensions.std.headrope_m)
    for c in g.ropes:
        assert c.cut_m == pytest.approx(c.length_m + 0.3 * c.eyes)
    with pytest.raises(ValueError):
        guide(r, eye_allowance_m=-1)


def test_pair_trawl_has_no_door_rigging() -> None:
    keys = {c.key for c in _guide("bobp_wp10_pair_480x160").ropes}
    assert "headrope" in keys and "crowfoot" not in keys


def test_modified_variant() -> None:
    g = guide(_result("fao_a3_standard", "fao_a3_modified"), "mod")
    assert g.variant == "mod" and g.net_id == "fao_a3_modified"
    with pytest.raises(ValueError, match="modificada"):
        guide(_result(), "mod")


# --- salidas ------------------------------------------------------------------------------------


def test_tables_and_serialisation() -> None:
    g = _guide()
    keys = [t.key for t in g.tables()]
    assert keys[0] == "construccion_corte" and "construccion_cortes" in keys
    d = json.loads(json.dumps(service.to_jsonable(g.to_dict())))
    assert len(d["pieces"]) == 10 and d["joins"][0]["step"] == 1


def test_html_and_xlsx() -> None:
    from trawlkit.report.construction import construction_html, construction_xlsx

    page = construction_html(_guide())
    assert "Guía de construcción" in page and "Paso 11" in page and "<svg" in page
    assert construction_xlsx(_guide())[:2] == b"PK"


def test_api_routes() -> None:
    from fastapi.testclient import TestClient

    from trawlkit.api.app import app

    client = TestClient(app)
    r = client.post("/design/construction?eye_allowance_m=0.2", json={})
    assert r.status_code == 200 and r.json()["eye_allowance_m"] == 0.2
    assert client.post("/design/construction?variant=mod", json={}).status_code == 422
    r = client.post("/design/construction/export?format=html", json={"net": "fao_wb_bt2p_60hp"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")


def test_cli(tmp_path: object) -> None:
    from pathlib import Path

    from typer.testing import CliRunner

    from trawlkit.cli import app

    out = Path(str(tmp_path)) / "guia.json"
    res = CliRunner().invoke(app, ["build-guide", "fao_a3_standard", "-o", str(out)])
    assert res.exit_code == 0, res.output
    assert json.loads(out.read_text())["net_id"] == "fao_a3_standard"
    res = CliRunner().invoke(app, ["build-guide", "fao_a3_standard"])
    assert res.exit_code == 0 and "malla a malla" in res.output
