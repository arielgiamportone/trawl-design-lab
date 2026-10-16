"""Portones (rigging.doors) contra 'Portones y aparejamiento'."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pytest

from tests.golden_utils import SPEEDS_KN, assert_close, golden
from trawlkit.compat import Compat
from trawlkit.rigging import (
    ROB_SHARES,
    centre_of_pressure_m,
    door_drag_share_kgf,
    door_force_kgf,
    door_forces_kgf,
    door_polar,
    door_polar_table,
    door_spread_corrected_m,
    door_spread_m,
    door_weight_water_kg,
    moment_balance,
    required_area_m2,
    required_area_overall_m2,
    required_area_summary,
    select_door,
    warp_divergence_deg,
)

PORT = "portones_y_aparejamiento"


def g(key: str) -> Any:
    return golden(PORT, key)


def _forces() -> Any:
    return door_forces_kgf(g("rob_area_m2"), g("rob_cd"), g("rob_cl"), np.array(g("speed_ms")))


def _required_150() -> Any:
    return required_area_summary(
        required_area_m2(
            np.array(g("rob_20pct_input_150_kgf")), g("rob_cd"), np.array(g("speed_ms"))
        ),
        SPEEDS_KN,
    )


def _required_180() -> Any:
    return required_area_summary(
        required_area_m2(
            np.array(g("rob_20pct_input_180_kgf")), g("rob_cd"), np.array(g("speed_ms"))
        ),
        SPEEDS_KN,
    )


def _door_force_excel() -> Any:
    return door_force_kgf(
        g("rob_cd"),
        g("door_area_m2"),
        g("force_angle_deg"),
        np.array(g("speed_ms")),
        compat=Compat.EXCEL,
    )


def _moments() -> Any:
    cp = centre_of_pressure_m(g("door_length_m"), g("force_angle_deg"))
    return moment_balance(
        _door_force_excel(), np.array(g("rn_std_kgf")), cp.d_m, g("sweep_lever_m")
    )


CASES: list[tuple[str, str, Callable[[], Any]]] = [
    (
        "door_spread_m",
        "E13",
        lambda: door_spread_m(g("gallows_spacing_m"), g("spread_per_metre_m"), g("warp_length_m")),
    ),
    (
        "warp_half_divergence_deg",
        "D21",
        lambda: warp_divergence_deg(g("door_spread_m"), g("gallows_spacing_m"), g("warp_length_m")),
    ),
    (
        "door_spread_corrected_m",
        "F30",
        lambda: door_spread_corrected_m(
            g("warp_length_m"), g("warp_half_divergence_deg"), g("spread_correction_factor")
        ),
    ),
    ("rob_kgf", "D190:D198", lambda: _forces().drag_kgf),
    ("door_spreading_force_kgf", "E190:E198", lambda: _forces().lift_kgf),
    (
        "required_door_area_150_m2",
        "E210:E218",
        lambda: required_area_m2(
            np.array(g("rob_20pct_input_150_kgf")), g("rob_cd"), np.array(g("speed_ms"))
        ),
    ),
    (
        "required_door_area_180_m2",
        "E223:E231",
        lambda: required_area_m2(
            np.array(g("rob_20pct_input_180_kgf")), g("rob_cd"), np.array(g("speed_ms"))
        ),
    ),
    ("required_door_area_avg_150_m2", "F212", lambda: _required_150().average_total_m2),
    ("required_door_area_each_150_m2", "F215", lambda: _required_150().per_door_m2),
    ("required_door_area_avg_180_m2", "F225", lambda: _required_180().average_total_m2),
    ("required_door_area_each_180_m2", "F229", lambda: _required_180().per_door_m2),
    (
        "required_door_area_overall_m2",
        "F220",
        lambda: required_area_overall_m2(_required_150().per_door_m2, _required_180().per_door_m2),
    ),
    ("door_force_kgf", "D252:D260", _door_force_excel),
    (
        "centre_of_pressure_m",
        "C266",
        lambda: centre_of_pressure_m(g("door_length_m"), g("force_angle_deg")).d_m,
    ),
    ("ha_m", "C269", lambda: centre_of_pressure_m(g("door_length_m"), g("force_angle_deg")).ha_m),
    ("hb_m", "C270", lambda: centre_of_pressure_m(g("door_length_m"), g("force_angle_deg")).hb_m),
    ("door_moment_kgf_cm", "G281:G289", lambda: _moments().door_moment_kgf_cm),
    ("sweep_moment_kgf_cm", "H281:H289", lambda: _moments().sweep_moment_kgf_m),
    (
        "door_weight_water_kg",
        "D127",
        lambda: door_weight_water_kg(g("door_weight_air_kg"), g("door_weight_coef")),
    ),
    ("door_cl_selected", "D134", lambda: door_polar(select_door("fao_flat_wood_a3"), 32).cl),
    ("door_cd_selected", "E134", lambda: door_polar(select_door("fao_flat_wood_a3"), 32).cd),
    ("door_cl_cd_selected", "F134", lambda: door_polar(select_door("fao_flat_wood_a3"), 32).cl_cd),
    (
        "door_polar_cl",
        "D132:D137",
        lambda: [p.cl for p in door_polar_table(select_door("fao_flat_wood_a3"))],
    ),
    (
        "door_polar_cd",
        "E132:E137",
        lambda: [p.cd for p in door_polar_table(select_door("fao_flat_wood_a3"))],
    ),
    (
        "door_polar_cl_cd",
        "F132:F137",
        lambda: [p.cl_cd for p in door_polar_table(select_door("fao_flat_wood_a3"))],
    ),
    (
        "door_polar_angle_deg",
        "C132:C137",
        lambda: [p.angle_deg for p in door_polar_table(select_door("fao_flat_wood_a3"))],
    ),
]

for hp in (150, 180):
    for share in ROB_SHARES:
        pct = int(round(share * 100))
        CASES.append(
            (
                f"rob_{pct}pct_{hp}_kgf",
                f"{'EFGH'[ROB_SHARES.index(share)]}{146 if hp == 150 else 160}",
                (
                    lambda hp=hp, share=share: door_drag_share_kgf(
                        np.array(g(f"fridman_ft_fixed_{hp}_kgf")), share
                    )
                ),
            )
        )


@pytest.mark.parametrize(("key", "cell", "compute"), CASES, ids=[f"{k}[{c}]" for k, c, _ in CASES])
def test_golden(key: str, cell: str, compute: Callable[[], Any]) -> None:
    assert_close(compute(), g(key), where=f"{PORT}:{key} ({cell})")


def test_select_door_catalogue_matches_sheet() -> None:
    door = select_door("fao_flat_wood_a3")
    assert door.name == g("door_name")
    assert door.length_m == g("door_length_m")
    assert door.height_m == g("door_height_m")
    assert_close(door.area_m2, g("door_area_m2"))
    assert door.aspect_ratio == g("door_aspect_ratio")
    assert door.weight_air_kg == g("door_weight_air_kg")
    assert_close(door.weight_water_kg, g("door_weight_water_kg"))
    with pytest.raises(KeyError):
        select_door("nope")
    with pytest.raises(KeyError):
        door_polar(door, 33)


def test_door_polar_missing_coefficients() -> None:
    morgere = select_door("morgere_polivalente_oval")
    with pytest.raises(ValueError):
        door_polar(morgere, 25)
    assert [p.angle_deg for p in door_polar_table(morgere)] == [27, 30, 35, 40, 45]


def test_door_force_corrected_uses_radians_in_both_sines() -> None:
    v = np.array(g("speed_ms"))
    excel = np.asarray(_door_force_excel())
    corrected = np.asarray(
        door_force_kgf(
            g("rob_cd"), g("door_area_m2"), g("force_angle_deg"), v, compat=Compat.CORRECTED
        )
    )
    phi = np.radians(g("force_angle_deg"))
    expected = (
        0.5
        * g("rob_cd")
        * (1024 / 9.81)
        * v**2
        * g("door_area_m2")
        * (2 * np.sin(phi))
        / (1 + np.sin(phi) ** 2)
    )
    assert_close(corrected, expected)
    # sin(32 rad)² = 0.304 > sin(32°)² = 0.281 → el Excel subestima la fuerza.
    assert np.all(corrected > excel)
    assert_close(corrected[0] / excel[0], (1 + np.sin(32.0) ** 2) / (1 + np.sin(phi) ** 2))


def test_scalar_inputs_return_floats() -> None:
    f = door_forces_kgf(1.805, 0.71, 0.93, 0.5144)
    assert isinstance(f.drag_kgf, float) and isinstance(f.lift_kgf, float)
    assert isinstance(door_drag_share_kgf(1395.0, 0.2), float)
    assert isinstance(door_force_kgf(0.71, 1.805, 32, 0.5144), float)
    d = f.to_dict()
    assert set(d) == {"drag_kgf", "lift_kgf"}
