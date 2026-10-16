"""Comprobaciones de los catálogos y tablas de referencia extraídos del Excel."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
import yaml

from trawlkit.io import DATA_DIR, load_catalogue, load_doors

REF_DIR = DATA_DIR / "reference"


def read_csv(name: str) -> list[dict[str, str]]:
    with (REF_DIR / name).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_doors_catalogue() -> None:
    doors = load_doors().doors
    assert [d.id for d in doors] == ["fao_flat_wood_a3", "morgere_polivalente_oval"]
    fao = doors[0]
    assert fao.length_m == 1.9 and fao.height_m == 0.95
    assert fao.area_m2 == pytest.approx(1.805)
    assert fao.aspect_ratio == 0.5
    assert fao.weight_air_kg == 135
    assert fao.weight_water_kg == pytest.approx(135 * 0.597)
    at_32 = next(c for c in fao.coefficients if c.angle_deg == 32)
    assert at_32.cl == pytest.approx(0.93)
    assert at_32.cd == pytest.approx(0.71)
    morgere = doors[1]
    at_25 = next(c for c in morgere.coefficients if c.angle_deg == 25)
    assert at_25.cl is None and at_25.cd is None


def test_floats_catalogue() -> None:
    cat = load_catalogue("floats")
    assert cat.kind == "floats"
    d200 = [it for it in cat.items if it["diameter_mm"] == 200]
    assert d200 and all("note" in it for it in d200)
    assert {it["buoyancy_kgf"] for it in d200} == {3.2, 3, 3.1}
    assert cat.items[0] == {
        "diameter_mm": 100,
        "buoyancy_kgf": 0.3,
        "source": "Flotación y Lastre!D72:E72",
    }


def test_warps_catalogue() -> None:
    cat = load_catalogue("warps")
    w12 = next(it for it in cat.items if it["diameter_mm"] == 12)
    assert w12["breaking_load_t"] == pytest.approx(8.55, abs=1e-6)
    assert w12["weight_kg_per_m"] == pytest.approx(0.531)


def test_ropes_and_chains() -> None:
    ropes = load_catalogue("ropes")
    assert len(ropes.items) == 4
    pp14 = next(it for it in ropes.items if it["id"] == "pp_14_retorcido_3_cordones")
    assert pp14["weight_kg_per_m"] == pytest.approx(27.5 / 220)
    chains = load_catalogue("chains")
    assert [it["link_diameter_mm"] for it in chains.items] == [7, 19]
    assert all(it["grade"] == 80 for it in chains.items)


def test_materials_catalogue() -> None:
    cat = load_catalogue("materials")
    pa = next(it for it in cat.items if it["material"] == "PA")
    assert pa["density_kg_m3"] == 1140
    extra = cat.model_dump()
    assert extra["constants"]["seawater_density_kg_m3"] == 1024
    assert extra["constants"]["g_m_s2"] == 9.81


def test_every_item_has_source() -> None:
    for kind in ("floats", "ropes", "chains", "warps", "materials"):
        cat = load_catalogue(kind)
        assert cat.source
        assert all(it.get("source") for it in cat.items), kind
    for door in load_doors().doors:
        assert door.model_dump()["source"].startswith("Tablas de Referencias!")


def test_depth_to_warp() -> None:
    table = read_csv("depth_to_warp.csv")
    assert len(table) == 30
    row = next(r for r in table if float(r["depth_m"]) == 40)
    assert float(row["warp_length_m"]) == 200
    assert float(row["ratio"]) == 5


def test_reference_tables_shape() -> None:
    nomura = read_csv("nomura_proportions.csv")
    assert len(nomura) == 10
    assert nomura[0]["net_type"] == "Red de Fondo, 2 caras"
    assert float(nomura[2]["a_b"]) == 10.6 and nomura[2]["note"]

    cuts = read_csv("cut_ratios.csv")
    assert [r["cut_code"] for r in cuts[:4]] == ["AB", "1N2B", "1N1B", "3N2B"]
    assert all(r["mesh_increase_width"] == "1" for r in cuts if r["mesh_increase_width"])
    # Filas 69-72 (razones 2/x): código sin aumento de mallas; el paño D usa 2/3 → 1N4B.
    assert len(cuts) == 24
    assert any(r["cut_code"] == "1N4B" and abs(float(r["cut_ratio"]) - 2 / 3) < 1e-9 for r in cuts)

    knots = read_csv("knot_factor_k.csv")
    k = next(r for r in knots if float(r["mesh_mm"]) == 40 and float(r["twine_diameter_mm"]) == 1)
    assert float(k["k"]) == pytest.approx(1.38)

    catenary = read_csv("catenary.csv")
    assert float(catenary[0]["dpa_l"]) == 0.99 and float(catenary[0]["alpha_deg"]) == 76.1
    assert all(r["fl_l"] for r in catenary)

    angles = read_csv("useful_angles.csv")
    params = {r["parameter"] for r in angles}
    assert params == {
        "sweep_angle_deg",
        "dremiere_ratio",
        "sweep_length_m",
        "useful_percentage",
        "nhp_hp",
    }

    danleno = read_csv("danleno_height_vs_depth.csv")
    assert danleno[0] == {
        "depth_m": "10",
        "danleno_arm_height_m": "0.1",
        "source": "Tablas de Referencias!A202:B202",
    }


def test_power_coefficients() -> None:
    raw = yaml.safe_load((REF_DIR / "power_coefficients.yaml").read_text(encoding="utf-8"))
    assert raw["fridman"]["kf"] == {"fixed_pitch": 10, "variable_pitch_nozzle": 15}
    assert raw["fridman"]["energy_split"]["towing"]["fraction"] == 0.33
    assert raw["bollard_pull_k"]["by_propeller"]["fixed_pitch"]["k_150hp"] == 11.23
    assert raw["nomura"]["k1_engine_utilisation"] == 0.85
    assert raw["nomura"]["k3_propulsion_efficiency"]["small"]["range"] == [0.17, 0.2]
    assert raw["hamuro"]["k1_fraction_of_nhp"] == 0.825
    assert raw["koyama"]["k_table"][0]["k"] == 0.15
    assert {k["k"] for k in raw["prado"]["k_by_propeller_rpm"]} == {0.2, 0.25, 0.28, 0.3}


def test_generated_files_exist() -> None:
    expected = [
        "nomura_proportions.csv",
        "cut_ratios.csv",
        "knot_factor_k.csv",
        "catenary.csv",
        "useful_angles.csv",
        "danleno_height_vs_depth.csv",
        "depth_to_warp.csv",
        "power_coefficients.yaml",
    ]
    assert all((REF_DIR / name).is_file() for name in expected)
    assert all(Path(DATA_DIR / f"{k}.yaml").is_file() for k in ("doors", "floats", "ropes"))
