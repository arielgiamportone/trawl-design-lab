"""Cables de remolque (rigging.warps) contra 'Cables de Remolque' y 'Cables Y Cabulleria'."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pytest

from tests.golden_utils import SPEEDS_KN, assert_close, golden
from trawlkit.compat import Compat
from trawlkit.rigging import (
    dpa_similar_triangles_m,
    kinematic_viscosity_m2_s,
    select_warp,
    total_drag_kgf,
    warp_angles_deg,
    warp_cd,
    warp_cd_cylinder,
    warp_cd_maclennan,
    warp_depth_ratio,
    warp_diameter_aguila_mm,
    warp_diameter_ehp_mm,
    warp_drag_cylinder,
    warp_drag_kgf,
    warp_drag_share_kgf,
    warp_length_for_depth,
    warp_quantity_m,
    warp_weight,
    working_load_and_breaking_load,
)

REM = "cables_de_remolque"
CAB = "cables_y_cabulleria"
PORT = "portones_y_aparejamiento"
BUQ = "tipo_de_buques"


def g(key: str) -> Any:
    return golden(REM, key)


def _angles() -> Any:
    return warp_angles_deg(
        g("door_spread_m"),
        g("gallows_spacing_m"),
        g("warp_length_m"),
        g("dpa_a_m"),
        g("sweeps_plus_bridle_m"),
        g("effective_depth_m"),
        golden(BUQ, "vessel_depth_m"),
    )


def _total(which: str) -> Any:
    return total_drag_kgf(
        np.array(g(f"rn_{which}_kgf")),
        np.array(g("float_drag_kgf")),
        np.array(g("warp_drag_2_kgf")),
        compat=Compat.EXCEL,
    )


def _cylinder() -> Any:
    return warp_drag_cylinder(
        g("warp_diameter_m"), g("warp_length_used_m"), np.array(g("speed_ms")), np.array(SPEEDS_KN)
    )


def _weight() -> Any:
    return warp_weight(g("warp_min_diameter_mm"), g("warp_length_m_sel"))


def _loads() -> Any:
    return working_load_and_breaking_load(_total("std"), SPEEDS_KN)


CASES: list[tuple[str, str, Callable[[], Any]]] = [
    (
        "dpa_a_m",
        "F17",
        lambda: dpa_similar_triangles_m(
            g("door_spread_m"), g("footrope_m"), g("sweeps_plus_bridle_m")
        ),
    ),
    (
        "dpa_b_m",
        "F19",
        lambda: dpa_similar_triangles_m(
            g("door_spread_m"), g("net_length_no_bag_m"), g("sweeps_plus_bridle_m")
        ),
    ),
    ("warp_divergence_deg", "E25", lambda: _angles().divergence_deg),
    ("bridle_divergence_deg", "E29", lambda: _angles().bridle_divergence_deg),
    ("warp_declination_deg", "E33", lambda: _angles().declination_deg),
    ("warp_diameter_ehp_150_mm", "F73", lambda: warp_diameter_ehp_mm(g("ehp_150_hp"))),
    ("warp_diameter_ehp_180_mm", "F74", lambda: warp_diameter_ehp_mm(g("ehp_180_hp"))),
    ("warp_diameter_aguila_150_mm", "E80", lambda: warp_diameter_aguila_mm(150)),
    ("warp_diameter_aguila_180_mm", "E81", lambda: warp_diameter_aguila_mm(180)),
    ("warp_cd", "E106", lambda: warp_cd(g("warp_attack_angle_deg"))),
    (
        "warp_drag_2_kgf",
        "G118:G126",
        lambda: warp_drag_kgf(
            g("warp_cd"), g("warp_diameter_m"), g("warp_length_used_m"), np.array(g("speed_ms"))
        ),
    ),
    ("total_drag_std_kgf", "H118:H126", lambda: _total("std")),
    ("total_drag_mod_kgf", "I118:I126", lambda: _total("mod")),
    ("kinematic_viscosity_avg", "F161", lambda: kinematic_viscosity_m2_s()),
    ("warp_reynolds", "D167:D175", lambda: _cylinder().reynolds),
    ("warp_cd_cylinder", "E167:E175", lambda: _cylinder().cd),
    ("warp_drag_cylinder_kgf", "F167:F175", lambda: _cylinder().drag_one_kgf),
    ("warp_drag_cylinder_2_kgf", "G167:G175", lambda: _cylinder().drag_two_kgf),
    (
        "warp_drag_5pct_fixed_kgf",
        "E191:E199",
        lambda: warp_drag_share_kgf(np.array(g("fridman_ft_fixed_150_kgf")), 0.05),
    ),
    (
        "warp_drag_5pct_variable_kgf",
        "F191:F199",
        lambda: warp_drag_share_kgf(np.array(g("fridman_ft_variable_nozzle_150_kgf")), 0.05),
    ),
    (
        "warp_drag_10pct_fixed_kgf",
        "G191:G199",
        lambda: warp_drag_share_kgf(np.array(g("fridman_ft_fixed_150_kgf")), 0.10),
    ),
    (
        "warp_drag_10pct_variable_kgf",
        "H191:H199",
        lambda: warp_drag_share_kgf(np.array(g("fridman_ft_variable_nozzle_150_kgf")), 0.10),
    ),
    (
        "warp_cd_maclennan",
        "D227:D235",
        lambda: warp_cd_maclennan(np.array(g("speed_ms")), g("warp_diameter_m")),
    ),
    ("warp_weight_air_kg_m", "E248", lambda: _weight().air_kg_m),
    ("warp_weight_water_a_kg_m", "F250", lambda: _weight().water_a_kg_m),
    ("warp_weight_water_b_kg_m", "F252", lambda: _weight().water_b_kg_m),
    ("warp_total_weight_air_kg", "F256", lambda: _weight().total_air_kg),
    ("warp_total_weight_water_kg", "F257", lambda: _weight().total_water_kg),
    ("warp_min_weight_air_kg_m", "E265", lambda: _weight().air_kg_m),
    ("warp_min_weight_water_kg_m", "E266", lambda: _weight().water_min_kg_m),
    ("warp_working_load_kgf", "E267", lambda: _loads().working_load_kgf),
    ("warp_safety_factor", "D271", lambda: _loads().safety_factor),
    ("warp_min_breaking_load_kgf", "E272", lambda: _loads().min_breaking_load_kgf),
]


@pytest.mark.parametrize(("key", "cell", "compute"), CASES, ids=[f"{k}[{c}]" for k, c, _ in CASES])
def test_golden(key: str, cell: str, compute: Callable[[], Any]) -> None:
    assert_close(compute(), g(key), where=f"{REM}:{key} ({cell})")


def _select_excel() -> Any:
    return select_warp(
        g("warp_min_diameter_mm"), g("warp_min_breaking_load_kgf"), compat=Compat.EXCEL
    )


CAB_CASES: list[tuple[str, str, Callable[[], Any]]] = [
    ("warp_selected", "D11", lambda: _select_excel().construction),
    ("warp_diameter_mm", "G11", lambda: _select_excel().diameter_mm),
    ("warp_kg_per_m", "H11", lambda: _select_excel().weight_kg_per_m),
    ("warp_strength_t", "I11", lambda: _select_excel().breaking_load_t),
    ("warp_quantity_m", "D12", lambda: warp_quantity_m(g("warp_length_m_sel"))),
]


@pytest.mark.parametrize(
    ("key", "cell", "compute"), CAB_CASES, ids=[f"{k}[{c}]" for k, c, _ in CAB_CASES]
)
def test_golden_cabulleria(key: str, cell: str, compute: Callable[[], Any]) -> None:
    expected = golden(CAB, key)
    actual = compute()
    if isinstance(expected, str):
        assert actual == expected, f"{CAB}:{key} ({cell})"
    else:
        assert_close(actual, expected, where=f"{CAB}:{key} ({cell})")


def test_select_warp_excel_is_undersized_and_corrected_fixes_it() -> None:
    excel = _select_excel()
    assert excel.diameter_mm == 12 and excel.breaking_load_t == 8.55
    assert not excel.satisfies_breaking_load  # 8.55 t < 8.80 t requeridas
    corrected = select_warp(g("warp_min_diameter_mm"), g("warp_min_breaking_load_kgf"))
    assert corrected.diameter_mm == 13 and corrected.breaking_load_t == 10.3
    assert corrected.satisfies_breaking_load
    assert corrected.to_dict()["id"] == "steel_6x19_seale_13mm"
    # Ninguno alcanza: el más grueso del catálogo, marcado como insuficiente.
    huge = select_warp(12.0, 1e6)
    assert not huge.satisfies_breaking_load
    assert huge.diameter_mm >= corrected.diameter_mm


def test_total_drag_corrected_includes_doors() -> None:
    rob = np.array(golden(PORT, "rob_kgf"))
    excel = np.asarray(_total("std"))
    corrected = np.asarray(
        total_drag_kgf(
            np.array(g("rn_std_kgf")),
            np.array(g("float_drag_kgf")),
            np.array(g("warp_drag_2_kgf")),
            rob,
        )
    )
    assert_close(corrected, excel + rob)
    assert np.all(corrected > excel)
    # Con ROB la carga de trabajo a 3.5 kn sube de 2200 a 2417 kgf (rotura mínima 9.67 t).
    loads = working_load_and_breaking_load(corrected, SPEEDS_KN)
    assert_close(loads.working_load_kgf, 2200.483713451298 + rob[5])
    assert loads.min_breaking_load_kgf > g("warp_min_breaking_load_kgf")


def test_warp_table_lookup() -> None:
    assert warp_depth_ratio(40) == 5
    assert warp_length_for_depth(40) == 200
    assert warp_length_for_depth(20) == 120
    assert warp_length_for_depth(50) == 200  # LOOKUP: mayor profundidad ≤ 50 → 40 m
    assert warp_length_for_depth(600) == 1875
    with pytest.raises(ValueError):
        warp_length_for_depth(10)


def test_warp_cd_nearest_angle() -> None:
    assert warp_cd(4.3) == 0.02
    assert warp_cd(6.0) == 0.04
    assert warp_cd(35.0) == 0.18  # empate 30°/40° → se toma el primero de la tabla
    assert warp_cd(24.9) == 0.09


def test_warp_cd_cylinder_switch_at_3_kn() -> None:
    assert_close(warp_cd_cylinder(np.array([2.5, 3.0])), [1.1, 1.2])
    assert isinstance(warp_cd_cylinder(2.0), float)


def test_working_load_requires_design_speed() -> None:
    with pytest.raises(ValueError):
        working_load_and_breaking_load(np.array([1.0, 2.0]), [1.0, 2.0])
    assert working_load_and_breaking_load(2200.0).min_breaking_load_kgf == pytest.approx(8800.0)
