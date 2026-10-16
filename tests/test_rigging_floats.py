"""Flotación (rigging.floats) contra 'Flotación y Lastre'."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pytest

from tests.golden_utils import SPEEDS_KN, assert_close, golden, load_sheet
from trawlkit.compat import Compat
from trawlkit.rigging import (
    beta_deg,
    distribute_floats,
    float_cd,
    float_count,
    float_diameter_for_count_mm,
    float_drag_kgf,
    float_reynolds,
    flotation_fridman,
    flotation_fridman_average_kgf,
    flotation_koyama_kgf,
    flotation_prado_kgf,
    kinematic_viscosity_m2_s,
    rope_weight_air_kg,
    rope_weight_in_water_kg,
)

FLOT = "flotacion_y_lastre"


def g(key: str) -> Any:
    return golden(FLOT, key)


def _fridman(hp: int, which: str, rounddown: Any = True) -> Any:
    return flotation_fridman(
        np.array(g(f"fridman_ft_{hp}_kgf")),
        np.array(g(f"rn_{which}_kgf")),
        g("bridle_angle_deg"),
        g("beta_deg"),
        g("headrope_weight_water_kgf"),
        rounddown=rounddown,
    )


def _catalogue_diameters() -> list[float]:
    # "float_diameter_mm" existe como valor (F92) y como serie (D72:D82): se lee la serie.
    return list(load_sheet(FLOT)["series"]["float_diameter_mm"]["values"])


#: Flot!M42 está redondeada pero M43:M50 no (solo en el bloque de 150 HP).
MOD_150_MASK = np.array([True] + [False] * 8)


def _distribution() -> Any:
    return distribute_floats(
        int(g("float_count")),
        g("float_diameter_mm"),
        g("headrope_m"),
        g("headrope_wing_corrected_m"),
        g("headrope_bosom_corrected_m"),
        wing_share=g("float_wing_share"),
        front_fifth_share=g("wing_front_fifth_share"),
    )


CASES: list[tuple[str, str, Callable[[], Any]]] = [
    ("flotation_koyama_kgf", "F6", lambda: flotation_koyama_kgf(g("headrope_m"))),
    ("flotation_prado_150_kgf", "F17", lambda: flotation_prado_kgf(150, g("prado_k"))),
    ("flotation_prado_180_kgf", "G17", lambda: flotation_prado_kgf(180, g("prado_k"))),
    ("beta_deg", "F23", lambda: beta_deg(g("vertical_opening_m"), g("body_length_m"))),
    (
        "headrope_weight_air_kg",
        "F36",
        lambda: rope_weight_air_kg(g("headrope_m"), g("headrope_kg_per_m")),
    ),
    (
        "headrope_weight_water_kgf",
        "F37",
        lambda: rope_weight_in_water_kg(g("headrope_weight_air_kg")),
    ),
    ("float_f1_150_kgf", "F42:F50", lambda: _fridman(150, "std").f1_kgf),
    ("float_f2_std_150_kgf", "G42:G50", lambda: _fridman(150, "std").f2_kgf),
    ("float_f2_mod_150_kgf", "H42:H50", lambda: _fridman(150, "mod").f2_kgf),
    ("float_f1_vertical_150_kgf", "I42:I50", lambda: _fridman(150, "std").f1_vertical_kgf),
    ("float_f2_vertical_std_150_kgf", "J42:J50", lambda: _fridman(150, "std").f2_vertical_kgf),
    ("float_f2_vertical_mod_150_kgf", "K42:K50", lambda: _fridman(150, "mod").f2_vertical_kgf),
    ("flotation_total_std_150_kgf", "L42:L50", lambda: _fridman(150, "std").total_kgf),
    (
        "flotation_total_mod_150_kgf",
        "M42:M50",
        lambda: _fridman(150, "mod", MOD_150_MASK).total_kgf,
    ),
    ("float_f1_180_kgf", "F55:F63", lambda: _fridman(180, "std").f1_kgf),
    ("float_f2_std_180_kgf", "G55:G63", lambda: _fridman(180, "std").f2_kgf),
    ("float_f2_mod_180_kgf", "H55:H63", lambda: _fridman(180, "mod").f2_kgf),
    ("float_f1_vertical_180_kgf", "I55:I63", lambda: _fridman(180, "std").f1_vertical_kgf),
    ("float_f2_vertical_std_180_kgf", "J55:J63", lambda: _fridman(180, "std").f2_vertical_kgf),
    ("float_f2_vertical_mod_180_kgf", "K55:K63", lambda: _fridman(180, "mod").f2_vertical_kgf),
    ("flotation_total_std_180_kgf", "L55:L63", lambda: _fridman(180, "std").total_kgf),
    ("flotation_total_mod_180_kgf", "M55:M63", lambda: _fridman(180, "mod").total_kgf),
    (
        "flotation_fridman_avg_150_kgf",
        "N43",
        lambda: flotation_fridman_average_kgf(
            _fridman(150, "std").total_kgf, _fridman(150, "mod", MOD_150_MASK).total_kgf, SPEEDS_KN
        ),
    ),
    (
        "flotation_fridman_avg_180_kgf",
        "N55",
        lambda: flotation_fridman_average_kgf(
            _fridman(180, "std").total_kgf, _fridman(180, "mod").total_kgf, SPEEDS_KN
        ),
    ),
    (
        "float_count_150",
        "F72:F82",
        lambda: float_count(g("flotation_design_150_kgf"), np.array(g("float_unit_buoyancy_kgf"))),
    ),
    (
        "float_count_180",
        "G72:G82",
        lambda: float_count(g("flotation_design_180_kgf"), np.array(g("float_unit_buoyancy_kgf"))),
    ),
    (
        "float_diameter_mm",
        "F92",
        lambda: float_diameter_for_count_mm(
            g("float_count_total"), np.array(g("float_count_150")), np.array(_catalogue_diameters())
        ),
    ),
    ("float_spacing_even_m", "F94", lambda: _distribution().spacing_even_m),
    ("floats_per_wing_even", "F95", lambda: _distribution().per_wing_even),
    ("floats_bosom_even", "F96", lambda: _distribution().bosom_even),
    ("floats_on_wings", "G103", lambda: _distribution().on_wings),
    ("floats_per_wing", "H103", lambda: _distribution().per_wing),
    ("floats_on_bosom", "G104", lambda: _distribution().on_bosom),
    ("floats_front_fifth", "G107", lambda: _distribution().front_fifth),
    ("float_spacing_front_fifth_m", "H110", lambda: _distribution().spacing_front_fifth_m),
    ("wing_remaining_length_m", "C111", lambda: _distribution().wing_remaining_m),
    ("floats_remaining", "F111", lambda: _distribution().remaining_per_wing),
    ("float_spacing_remaining_m", "H111", lambda: _distribution().spacing_remaining_m),
    ("wing_free_end_m", "E112", lambda: _distribution().wing_free_end_m),
    ("float_spacing_bosom_m", "K112", lambda: _distribution().spacing_bosom_m),
    ("kinematic_viscosity_avg", "H132", lambda: kinematic_viscosity_m2_s()),
    ("float_cd", "I138:I146", lambda: float_cd(np.array(SPEEDS_KN))),
    (
        "float_reynolds",
        "H138:H146",
        lambda: float_reynolds(g("float_diameter_m"), np.array(g("speed_ms")), compat=Compat.EXCEL),
    ),
    (
        "float_drag_kgf",
        "J138:J146",
        lambda: float_drag_kgf(
            int(g("float_count_total")),
            g("float_diameter_m"),
            np.array(g("float_cd")),
            np.array(g("speed_ms")),
        ),
    ),
]


@pytest.mark.parametrize(("key", "cell", "compute"), CASES, ids=[f"{k}[{c}]" for k, c, _ in CASES])
def test_golden(key: str, cell: str, compute: Callable[[], Any]) -> None:
    assert_close(compute(), g(key), where=f"{FLOT}:{key} ({cell})")


def test_float_reynolds_corrected_is_v_d_over_nu() -> None:
    v = np.array(g("speed_ms"))
    d = g("float_diameter_m")
    corrected = np.asarray(float_reynolds(d, v))
    assert_close(corrected, v * d / kinematic_viscosity_m2_s())
    excel = np.asarray(float_reynolds(d, v, compat=Compat.EXCEL))
    # π·D²·v/ν = (π·D)·(v·D/ν): el Excel sobreestima Re por el factor π·D = 0.628.
    assert_close(excel / corrected, np.pi * d)
    assert np.all(corrected > excel)


def test_flotation_total_rounding_mask() -> None:
    unrounded = _fridman(150, "mod", False).total_kgf
    masked = _fridman(150, "mod", MOD_150_MASK).total_kgf
    assert masked[0] == np.floor(unrounded[0])
    assert_close(masked[1:], unrounded[1:])
    assert_close(_fridman(150, "mod", True).total_kgf, np.floor(unrounded))


def test_float_count_rounding_matches_sheet() -> None:
    # 36.0157/3.2 = 11.25 → 11 ; 36.0157/3.0 = 12.005 → 12 ; 39.9/8.33 = 4.79 → 5
    assert float_count(g("flotation_design_150_kgf"), 3.2) == 11
    assert float_count(g("flotation_design_150_kgf"), 3.0) == 12
    assert float_count(g("flotation_design_180_kgf"), 8.33) == 5
    assert isinstance(float_count(36.0, 3.0), float)


def test_distribution_to_dict() -> None:
    d = _distribution().to_dict()
    assert d["count"] == 12 and d["diameter_mm"] == 200
    assert d["on_wings"] == 10 and d["per_wing"] == 5 and d["on_bosom"] == 2
