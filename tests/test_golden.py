"""Los JSON de ``tests/golden`` tienen la estructura esperada y valores conocidos."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pytest

GOLDEN = Path(__file__).parent / "golden"
FILES = sorted(GOLDEN.glob("*.json"))
SPEED_KN = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
CELL_RE = re.compile(r"^[A-Z]{1,3}[1-9][0-9]*$")
RANGE_RE = re.compile(r"^[A-Z]{1,3}[1-9][0-9]*:[A-Z]{1,3}[1-9][0-9]*$")

EXPECTED_SHEETS = {
    "especie_blanco",
    "tipo_de_buques",
    "potenc_disponible_para_arrastre",
    "potencia_disponible_arrastre_ok",
    "panos_de_red_y_cortes",
    "cables_y_cabulleria",
    "mecanica_de_la_red",
    "dimensiones_de_la_red",
    "resistencia_de_la_red",
    "portones_y_aparejamiento",
    "flotacion_y_lastre",
    "cables_de_remolque",
    "tablas_de_referencias",
}


def load(name: str) -> dict:
    return json.loads((GOLDEN / f"{name}.json").read_text(encoding="utf-8"))


def value(name: str, key: str) -> float:
    return load(name)["values"][key]["value"]


def series(name: str, key: str) -> list:
    return load(name)["series"][key]["values"]


def _is_scalar(v: object) -> bool:
    return isinstance(v, (int, float, str)) and not isinstance(v, bool)


def test_all_sheets_present() -> None:
    assert {p.stem for p in FILES} == EXPECTED_SHEETS


@pytest.mark.parametrize("path", FILES, ids=[p.stem for p in FILES])
def test_structure(path: Path) -> None:
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert set(doc) >= {"sheet", "generated_by", "values", "series"}
    assert doc["generated_by"] == "tools/extract/golden.py"
    assert isinstance(doc["sheet"], str) and doc["sheet"]
    assert isinstance(doc["values"], dict) and isinstance(doc["series"], dict)

    for key, entry in doc["values"].items():
        assert KEY_RE.match(key), key
        assert set(entry) >= {"cell", "value", "label", "unit"}, key
        assert CELL_RE.match(entry["cell"]), key
        assert _is_scalar(entry["value"]), key
        if isinstance(entry["value"], float):
            assert math.isfinite(entry["value"]), key
        assert isinstance(entry["label"], str) and entry["label"], key
        assert isinstance(entry["unit"], str), key

    for key, entry in doc["series"].items():
        assert KEY_RE.match(key), key
        assert set(entry) >= {"x", "x_values", "cells", "values", "unit"}, key
        assert RANGE_RE.match(entry["cells"]), key
        assert isinstance(entry["x_values"], list) and isinstance(entry["values"], list), key
        assert len(entry["x_values"]) == len(entry["values"]) > 0, key
        assert any(v is not None for v in entry["values"]), key
        for v in entry["values"]:
            assert v is None or _is_scalar(v), key
        if entry["x"] == "speed_kn":
            assert entry["x_values"] == SPEED_KN, key


def test_speed_series_are_consistent() -> None:
    res = load("resistencia_de_la_red")
    assert res["series"]["speed_kn"]["values"] == SPEED_KN
    assert res["series"]["speed_ms"]["values"][0] == pytest.approx(0.5144)
    assert res["series"]["speed_ms"]["values"][-1] == pytest.approx(2.572)
    assert sum(1 for s in res["series"].values() if s["x"] == "speed_kn") >= 100


def test_static_flags() -> None:
    pot = load("potencia_disponible_arrastre_ok")
    assert pot["series"]["summary_worst_150_fridman_kgf"]["static"] is True
    assert "static" not in pot["series"]["summary_worst_150_nomura_kgf"]
    assert load("resistencia_de_la_red")["series"]["summary_dynamit_std_t"]["static"] is True


@pytest.mark.parametrize(
    ("sheet", "key", "expected"),
    [
        ("dimensiones_de_la_red", "headrope_m", 28.698),
        ("dimensiones_de_la_red", "footrope_m", 33.3),
        ("dimensiones_de_la_red", "vertical_opening_m", 1.984),
        ("dimensiones_de_la_red", "horizontal_opening_m", 13.0),
        ("dimensiones_de_la_red", "warp_length_m", 200),
        ("dimensiones_de_la_red", "warp_diameter_mm", 12),
        ("dimensiones_de_la_red", "flotation_total_kgf", 36),
        ("dimensiones_de_la_red", "fishing_circle_m", 44.64),
        ("mecanica_de_la_red", "solid_surface_std_m2", 40.895),
        ("mecanica_de_la_red", "solid_surface_mod_m2", 40.032),
        ("mecanica_de_la_red", "working_surface_std_m2", 315.57),
        ("mecanica_de_la_red", "filtration_index_std", 0.021278),
        ("mecanica_de_la_red", "filtration_index_mod", 0.019462),
        ("mecanica_de_la_red", "solidity_std", 0.1296),
        ("mecanica_de_la_red", "net_weight_air_std_kg", 28.27),
        ("mecanica_de_la_red", "net_weight_air_mod_kg", 22.95),
        ("mecanica_de_la_red", "vertical_opening_m", 1.984),
        ("mecanica_de_la_red", "dpa_geometric_std_m", 13),
        ("mecanica_de_la_red", "warp_length_m", 200),
        ("portones_y_aparejamiento", "door_spread_m", 32.5),
        ("portones_y_aparejamiento", "warp_half_divergence_deg", 4.30),
        ("portones_y_aparejamiento", "door_area_m2", 1.805),
        ("portones_y_aparejamiento", "door_angle_selected_deg", 32),
        ("portones_y_aparejamiento", "bridle_attack_angle_deg", 10.32),
        ("panos_de_red_y_cortes", "cut_angle_average_deg", 10.63),
        ("potenc_disponible_para_arrastre", "bhp_150", 150),
        ("potenc_disponible_para_arrastre", "bhp_180", 180),
        ("potenc_disponible_para_arrastre", "towing_hp_150", 49.5),
        ("flotacion_y_lastre", "flotation_design_150_kgf", 36.0157),
        ("flotacion_y_lastre", "float_count", 12),
        ("flotacion_y_lastre", "float_diameter_mm", 200),
        ("flotacion_y_lastre", "ballast_koyama_kg", 47.4),
        ("flotacion_y_lastre", "ballast_min_150_kg", 27),
        ("flotacion_y_lastre", "ballast_max_150_kg", 42),
        ("cables_de_remolque", "warp_declination_deg", 12.06),
        ("cables_de_remolque", "warp_diameter_aguila_150_mm", 11.25),
        ("cables_de_remolque", "warp_min_breaking_load_kgf", 8801.9),
        ("cables_de_remolque", "warp_length_m_sel", 200),
        ("cables_y_cabulleria", "warp_quantity_m", 500),
        ("especie_blanco", "species_depth_m", 40),
    ],
)
def test_spot_values(sheet: str, key: str, expected: float) -> None:
    assert value(sheet, key) == pytest.approx(expected, rel=1e-3)


def test_spot_series() -> None:
    aberdeen = series("resistencia_de_la_red", "aberdeen_demersal_rn_std_t")
    assert aberdeen[0] == pytest.approx(0.42236, rel=1e-4)
    assert series("resistencia_de_la_red", "summary_aberdeen_demersal_std_t") == aberdeen
    assert series("resistencia_de_la_red", "summary_aberdeen_demersal_std_kgf")[0] == pytest.approx(
        422.36, rel=1e-4
    )
    assert series("potencia_disponible_arrastre_ok", "fridman_ft_fixed_pitch_150_kgf") == [
        1395,
        1342.5,
        1290,
        1237.5,
        1185,
        1132.5,
        1080,
        1027.5,
        975,
    ]
    assert series("mecanica_de_la_red", "dpa_fridman_std_m")[0] == pytest.approx(5.78, rel=1e-3)
    assert series("cables_de_remolque", "total_drag_std_kgf")[5] == pytest.approx(2200.5, rel=1e-3)
    assert series("resistencia_de_la_red", "summary_dynamit_std_t")[0] == pytest.approx(0.3306)


def test_text_values_are_kept() -> None:
    assert value("especie_blanco", "species_common_name") == "Langostilla"
    assert value("cables_y_cabulleria", "warp_selected").startswith("CA 6X19")
    assert value("panos_de_red_y_cortes", "panel_a_cut_x1_code") == "1N2B"


def test_extractor_module_is_importable() -> None:
    from tools.extract import golden

    assert golden.slug("Resistencia de la RED") == "resistencia_de_la_red"
    assert golden.slug("Paños de red y cortes") == "panos_de_red_y_cortes"
    assert golden.is_error("#N/A") and not golden.is_error("AB")
    assert golden.clean(" 10 ") == 10.0
    assert set(golden.SHEETS) == {load(n)["sheet"] for n in EXPECTED_SHEETS}
