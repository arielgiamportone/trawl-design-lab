"""Fase 19.4: buques, catálogo de la flota argentina, tiro por la hélice y controles del guinche."""

from __future__ import annotations

import dataclasses
import math
import re
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from trawlkit import propulsion as pr
from trawlkit.api import service
from trawlkit.api.app import app
from trawlkit.i18n import use_lang
from trawlkit.io import (
    DATA_DIR,
    PropellerType,
    Vessel,
    VesselType,
    load_fleet,
    load_vessels,
    vessel_files,
)
from trawlkit.io.schema import ProvenanceKind
from trawlkit.model import PROPELLER_MODEL_KEY, DesignCase, run

ROOT = Path(__file__).resolve().parents[1]
BIB_KEYS = set(
    re.findall(r"^@\w+\{([^,]+),", (ROOT / "docs" / "referencias.bib").read_text("utf-8"), re.M)
)
client = TestClient(app)

#: 1 hp (mecánico, el BHP de Kartha 1966) en kW.
HP_MECH_KW = 0.745699872


# --- esquema -------------------------------------------------------------------------------------


def test_existing_vessels_load_unchanged() -> None:
    cat = load_vessels()
    assert [v.id for v in cat.vessels] == ["fao_a3_150hp", "fao_a3_180hp"]
    v = cat.vessels[0]
    assert v.bhp == 150 and v.beam_m == 2.5 and v.propeller is PropellerType.FIXED_PITCH
    assert v.propeller_diameter_m is None and v.vessel_type is None and v.status == "published"
    assert v.sources == [] and v.provenance == {} and not v.typical
    assert (v.model_extra or {})["vessel_class"].startswith("Tipo 1")


def test_nozzle_consistent_with_propeller() -> None:
    assert Vessel(id="a", bhp=100, nozzle=True).propeller is PropellerType.FIXED_PITCH_NOZZLE
    assert Vessel(id="a", bhp=100, propeller="variable_pitch_nozzle").has_nozzle
    assert not Vessel(id="a", bhp=100, propeller="variable_pitch").has_nozzle
    ok = Vessel(id="a", bhp=100, propeller="variable_pitch_nozzle", nozzle=True)
    assert ok.has_nozzle
    with pytest.raises(ValueError, match="inconsistent"):
        Vessel(id="a", bhp=100, propeller="fixed_pitch", nozzle=True)
    with pytest.raises(ValueError):
        Vessel(id="a", bhp=100, propeller_diameter_m=-1)
    with pytest.raises(ValueError):
        Vessel(id="a", bhp=100, vessel_type="arrastrero")
    assert Vessel(id="a", bhp=100, vessel_type="tangonero").vessel_type is VesselType.TANGONERO


# --- catálogo --------------------------------------------------------------------------------


def test_fleet_catalogue_order_and_ids() -> None:
    fleet = load_fleet().vessels
    ids = [v.id for v in fleet]
    assert ids[:2] == ["fao_a3_150hp", "fao_a3_180hp"]
    assert len(ids) == len(set(ids)) >= 18
    assert vessel_files()[0] == DATA_DIR / "vessels.yaml"
    assert {"bip_holmberg", "ar_tangonero_1998", "ar_rada_ria_mdp_e1"} <= set(ids)
    # El catálogo de la API sigue el mismo orden.
    assert list(service.vessel_presets())[:2] == ids[:2]


def test_fleet_catalogue_sources_and_provenance() -> None:
    for v in load_fleet().vessels[2:]:
        assert v.sources, v.id
        assert v.region == "latam" and v.vessel_type is not None, v.id
        for s in v.sources:
            assert s.key in BIB_KEYS, (v.id, s.key)
            assert s.accessed == "2026-10-27" and s.url, (v.id, s.key)
        for name in ("bhp", "length_m"):
            assert name in v.provenance, (v.id, name)
        for name, prov in v.provenance.items():
            assert prov.document is None or prov.document in BIB_KEYS, (v.id, name)
            if prov.kind is ProvenanceKind.DERIVED:
                assert prov.note, (v.id, name)  # la fórmula
            if prov.kind is ProvenanceKind.ASSUMED:
                assert prov.note and "A VERIFICAR" in prov.note, (v.id, name)
        # Lo que no está en la fuente no se inventa: sin dato y sin procedencia.
        for name in ("beam_m", "depth_m"):
            if getattr(v, name) is None:
                assert v.provenance[name].kind is ProvenanceKind.ASSUMED, (v.id, name)
        # Ningún buque argentino tiene hélice publicada.
        assert v.propeller_diameter_m is None and v.bollard_pull_t_measured is None


def test_fleet_types_are_typical_and_drafts_are_flagged() -> None:
    fleet = {v.id: v for v in load_fleet().vessels}
    types = [v for v in fleet.values() if v.typical]
    assert {v.vessel_type.value for v in types if v.vessel_type} >= {
        "rada_ria",
        "costero",
        "fresquero",
        "congelador",
        "tangonero",
    }
    assert all(any("típico" in n.lower() for n in [v.name or "", *v.notes]) for v in types)
    assert fleet["bip_oca_balda"].status == "draft" and fleet["bp_san_severo"].status == "draft"
    assert fleet["bip_holmberg"].status == "published"
    # Valores transcriptos y derivados del informe.
    assert fleet["ar_fresquero_e1"].bhp == 510.93 and fleet["ar_fresquero_e1"].length_m == 25.61
    tang = fleet["ar_tangonero_1998"]
    assert tang.bhp == pytest.approx(55974 / 59, abs=0.05)
    assert tang.provenance["bhp"].kind is ProvenanceKind.DERIVED
    holm = fleet["bip_holmberg"]
    assert holm.propeller is PropellerType.VARIABLE_PITCH and holm.propeller_blades == 4
    assert holm.winch_drum_capacity_m == 2000 and holm.warp_diameter_mm == 24
    assert holm.engine_kw == pytest.approx(2100 * 0.7355, abs=0.05)


# --- tiro por la hélice ----------------------------------------------------------------------


def test_wartsila_formula() -> None:
    # Control del informe (Kartha boat V): D = 0,897 m, P = 0,9·62,5 BHP = 41,9 kW.
    p = pr.delivered_power_kw(62.5, hp_to_kw=HP_MECH_KW)
    assert p == pytest.approx(41.9, abs=0.1)
    assert pr.wartsila_thrust_kn(0.897, p) == pytest.approx(11.2, abs=0.05)
    bp = pr.bollard_pull_wartsila_t(0.897, p)
    assert bp == pytest.approx(1.03, abs=0.01)
    assert 1000 * bp / 62.5 == pytest.approx(16.5, abs=0.1)
    # k2: 1 sin tobera; 1,3 (punto medio de 1,2-1,4) con tobera.
    assert pr.bollard_pull_wartsila_t(1.0, 100.0, True) / pr.bollard_pull_wartsila_t(
        1.0, 100.0
    ) == pytest.approx(1.3)
    assert pr.bollard_pull_wartsila_t(1.0, 100.0, True, k2=1.2) == pytest.approx(
        100.0 ** (2 / 3) * 0.9 * 1.2 / 9.81
    )
    # Inversa.
    d = pr.diameter_for_bollard_pull_m(bp, p)
    assert d == pytest.approx(0.897, rel=1e-9)


def test_momentum_theory_coefficients() -> None:
    # T[kN] = 1,172·(D·P)^(2/3) abierta y 1,477 con tobera ideal (ρ = 1025).
    for d, p in ((0.9, 40.0), (2.0, 1000.0)):
        dp = (d * p) ** (2 / 3)
        assert pr.momentum_thrust_kn(d, p) / dp == pytest.approx(1.172, abs=1e-3)
        assert pr.momentum_thrust_kn(d, p, nozzle=True) / dp == pytest.approx(1.477, abs=1e-3)
    assert pr.momentum_thrust_kn(1, 50, nozzle=True) / pr.momentum_thrust_kn(1, 50) == (
        pytest.approx(2 ** (1 / 3))
    )
    # Wärtsilä (abierta) = 0,853 × ideal: la cifra de mérito implícita del informe.
    assert pr.wartsila_thrust_kn(1, 50) / pr.momentum_thrust_kn(1, 50) == pytest.approx(
        0.853, abs=1e-3
    )
    # El empuje cae con la velocidad y la ventaja de la tobera también.
    t0, t2 = pr.momentum_thrust_kn(1, 50), pr.momentum_thrust_kn(1, 50, 2.0)
    assert t2 < t0
    gain0 = pr.momentum_thrust_kn(1, 50, 0, True) / t0
    gain2 = pr.momentum_thrust_kn(1, 50, 2.0, True) / t2
    assert gain2 < gain0


def test_towing_pull_against_kartha_measurement() -> None:
    """Kartha y Roy Choudhury (1966), boat V a 356 rpm: 1192 lb de tensión a 2,49 kn.

    Potencia a RPM parcial con par constante (SHP = n/N·SHPmax). El modelo es una cota
    optimista: da ≈ 25 % más que la tensión medida (que además es 3-15 % mayor que el tiro).
    """
    ref = yaml.safe_load((DATA_DIR / "reference" / "kartha1966_trawlers.yaml").read_text("utf-8"))
    boat = next(b for b in ref["boats"] if b["id"] == "V")
    meas = ref["measurements"][0]
    n_max = boat["engine_rpm"] / boat["gear_ratio"]
    p = pr.delivered_power_kw(boat["bhp"], hp_to_kw=HP_MECH_KW) * meas["rpm"] / n_max
    d = boat["diameter_in"] * 0.0254
    bp = pr.bollard_pull_wartsila_t(d, p)
    (pull,) = pr.towing_pull_kgf(bp, d, p, [meas["speed_kn"]], False, boat["displacement_t"])
    measured = meas["warp_tension_lb"] * pr.LB_TO_KG
    assert measured == pytest.approx(540.7, abs=0.1)
    assert 1.0 < pull / measured < 1.4
    assert pull / measured == pytest.approx(1.25, abs=0.03)


def test_propeller_pull_only_with_diameter() -> None:
    v = load_vessels().vessels[0]
    assert pr.propeller_pull(v, [1.0, 2.0]) is None
    vd = v.model_copy(update={"propeller_diameter_m": 0.9})
    pp = pr.propeller_pull(vd, [0.0, 1.0, 3.0])
    assert pp is not None and pp.method == "wartsila" and not pp.nozzle
    assert pp.bollard_pull_prado_t == pytest.approx(150 * 0.9 * 1.10 / 100)
    assert pp.towing_kgf[0] == pytest.approx(1000 * pp.bollard_pull_t)
    assert pp.towing_kgf[1] > pp.towing_kgf[2] > 0
    hull = pr.hull_resistance_kartha_kgf(10.0)
    assert hull == pytest.approx(4 * 0.45359237 * 10)
    meas = vd.model_copy(update={"bollard_pull_t_measured": 1.5})
    pm = pr.propeller_pull(meas, [0.0])
    assert pm is not None and pm.method == "measured" and pm.towing_kgf[0] == pytest.approx(1500)


# --- caso de diseño --------------------------------------------------------------------------


def _case(**vessel: object) -> DesignCase:
    v = load_vessels().vessels[0].model_copy(update=vessel)
    return service.build_case(net="fao_a3_standard", net_modified="fao_a3_modified", vessel=v)


def test_existing_case_is_unchanged() -> None:
    base = run(service.build_case(net_modified="fao_a3_modified", vessel="fao_a3_150hp"))
    assert base.power.propeller is None and base.warps.winch is None
    assert set(base.performance.windows) == {
        f"{p}_{v}" for p in ("fixed_pitch", "variable_pitch_nozzle") for v in ("std", "mod")
    }
    assert not any("propeller_pull" in n or "winch_" in n for n in base.notes)
    assert "propeller_bollard_pull_t" not in base.summary()
    # La clase por defecto sigue siendo la del libro (no toda la flota).
    assert [v.id for v in base.case.vessel_class] == ["fao_a3_150hp", "fao_a3_180hp"]
    same = run(_case(propeller_blades=4, home_port="Ushuaia", vessel_type="rada_ria"))
    assert same.summary() == base.summary()


def test_case_with_propeller_diameter() -> None:
    r = run(_case(propeller_diameter_m=0.9))
    pp = r.power.propeller
    assert pp is not None
    assert f"{PROPELLER_MODEL_KEY}_std" in r.performance.windows
    assert r.performance.design_key == "fixed_pitch_std"
    s = r.summary()
    assert s["propeller_bollard_pull_t"] == pytest.approx(pp.bollard_pull_t)
    assert any(n.startswith("propeller_pull:") and "A VERIFICAR" in n for n in r.notes)
    base = run(_case())
    # El resto del diseño no cambia (el tiro por la hélice no reemplaza a Fridman).
    assert s["max_speed_kn"] == base.summary()["max_speed_kn"]
    assert s["float_count"] == base.summary()["float_count"]


def test_gallows_fields_drive_geometry() -> None:
    base = _case()
    assert base.gallows_spacing_m == 2.5 and base.hull_depth_m == 1.8
    c = _case(gallows_spacing_m=3.2, gallows_height_m=3.0)
    assert c.gallows_spacing_m == 3.2 and c.hull_depth_m == 3.0
    ra, rb = run(base), run(c)
    assert rb.warps.angles.divergence_deg != ra.warps.angles.divergence_deg
    assert rb.warps.angles.declination_deg > ra.warps.angles.declination_deg
    # gallows_m / vessel_depth_m del caso siguen mandando.
    d = dataclasses.replace(c, gallows_m=2.0, vessel_depth_m=1.0)
    assert d.gallows_spacing_m == 2.0 and d.hull_depth_m == 1.0


def test_winch_checks() -> None:
    r = run(_case(winch_drum_capacity_m=230.0, winch_pull_t=5.0))
    w = r.warps.winch
    assert w is not None
    assert w.drum_required_m == pytest.approx(max(r.warps.warp_m, r.warps.quantity_m / 2))
    assert any(n.startswith("winch_drum_reserve") for n in r.notes)
    assert any(n.startswith("winch_pull_breaking") for n in r.notes)  # 5 t > 10,3/3 t
    short = run(_case(winch_drum_capacity_m=150.0, winch_pull_t=1.0))
    keys = {n.split(":")[0] for n in short.notes}
    assert {"winch_drum_short", "winch_pull_tension", "winch_pull_bollard"} <= keys
    ok = run(_case(winch_drum_capacity_m=400.0, winch_pull_t=2.0))
    assert ok.warps.winch is not None and ok.warps.winch.warnings == ()
    # Cable más grueso que el del guinche: capacidad ∝ 1/d².
    thick = run(_case(winch_drum_capacity_m=400.0, warp_diameter_mm=10.0))
    sel = thick.warps.selection.diameter_mm
    assert thick.warps.winch is not None
    assert thick.warps.winch.drum_capacity_effective_m == pytest.approx(400 * (10 / sel) ** 2)
    assert any(n.startswith("winch_warp_diameter") for n in thick.notes)
    with use_lang("en"):
        en = run(_case(winch_drum_capacity_m=150.0))
    assert any("cannot hold the warp paid out" in n for n in en.notes)


def test_untabulated_fridman_kf_message() -> None:
    # Desde la API (Fase 19.7a): sin KF tabulado se calcula como paso fijo y se anota.
    case = _case(propeller=PropellerType.VARIABLE_PITCH)
    assert case.fridman_kf == 10.0
    assert any("paso fijo" in a for a in case.assumptions)
    # El motor directo sigue pidiendo el KF explícito, con un mensaje claro.
    with pytest.raises(service.BadRequestError, match="no se halló una fuente publicada"):
        service.run_case(dataclasses.replace(case, fridman_kf=None))
    ok = service.run_case(dataclasses.replace(case, fridman_kf=12.0))
    assert ok.power.curves.fridman_kgf[0] == pytest.approx(150 * (12.0 - 0.7))


# --- API -------------------------------------------------------------------------------------


def test_catalog_vessels_filters() -> None:
    all_ = client.get("/catalog/vessels").json()
    assert [v["id"] for v in all_][:2] == ["fao_a3_150hp", "fao_a3_180hp"]
    tang = client.get("/catalog/vessels", params={"type": "tangonero"}).json()
    assert {v["id"] for v in tang} == {"ar_tangonero_1998", "bp_san_severo"}
    assert client.get("/catalog/vessels", params={"region": "europe"}).json() == []
    drafts = client.get("/catalog/vessels", params={"status": "draft"}).json()
    assert {v["id"] for v in drafts} == {"bip_oca_balda", "bp_san_severo"}
    en = client.get("/catalog/vessels", params={"type": "investigacion", "lang": "en"}).json()
    names = {v["id"]: v["name"] for v in en}
    assert names["bip_holmberg"].startswith("RV ")
    notes = {v["id"]: " ".join(v["notes"]) for v in en}
    assert "NOT FOUND" in notes["bip_holmberg"]
    assert not any("NO ENCONTRADO" in n or "Provisorio" in n for n in notes.values())


def test_design_inline_vessel_with_propeller() -> None:
    vessel = {
        "id": "mi_buque",
        "name": "Mi buque",
        "bhp": 180,
        "length_m": 11,
        "beam_m": 3.4,
        "depth_m": 1.9,
        "propeller": "fixed_pitch_nozzle",
        "nozzle": True,
        "propeller_diameter_m": 0.95,
        "winch_drum_capacity_m": 300,
        "region": "latam",
    }
    r = client.post("/design", json={"net": "fao_a3_standard", "vessel": vessel})
    # PF+T: el KF de Fridman no está tabulado; se calcula como paso fijo (Fase 19.7a).
    assert r.status_code == 200, r.text
    assert r.json()["result"]["power"]["curves"]["fridman_kgf"][0] == pytest.approx(
        180 * (10.0 - 0.7)
    )
    body = {"net": "fao_a3_standard", "vessel": vessel, "params": {"fridman_kf": 12}}
    r = client.post("/design", json=body)
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["summary"]["vessel_id"] == "mi_buque"
    prop = out["result"]["power"]["propeller"]
    assert prop["nozzle"] is True and prop["k2"] == 1.3 and prop["diameter_m"] == 0.95
    assert out["result"]["warps"]["winch"]["drum_capacity_m"] == 300
    assert "propeller_model_std" in out["result"]["performance"]["windows"]


def test_design_catalogue_vessel_without_beam_is_completed() -> None:
    r = client.post("/design", json={"net": "fao_a3_standard", "vessel": "ar_fresquero_e1"})
    assert r.status_code == 200, r.text
    notes = " ".join(r.json()["notes"])
    assert "beam_m = " in notes and "escalado del buque de la A-3" in notes
    case = service.build_case(vessel="ar_fresquero_e1")
    k = 25.61 / 9.0
    assert case.vessel.beam_m == pytest.approx(round(2.5 * k, 2))
    assert case.vessel.length_m == 25.61  # el dato de la fuente no se toca
    assert [v.id for v in case.class_vessels] == ["fao_a3_150hp", "fao_a3_180hp"]


def test_power_table_has_propeller_row() -> None:
    from trawlkit.report.tables import power_table

    r = run(_case(propeller_diameter_m=0.9))
    tab = power_table(r)
    assert tab.columns[-1].key == "propeller_kgf" and "Wärtsilä" in tab.note
    pp = r.power.propeller
    assert pp is not None
    assert math.isclose(float(tab.column("propeller_kgf")[0] or 0), pp.towing_kgf[0])
    assert power_table(run(_case())).note == ""
