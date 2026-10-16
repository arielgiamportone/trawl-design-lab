"""Aberturas DPA y AV (rigging.spread) contra 'Mecánica de la Red' y 'Dimensiones de la Red'."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pytest

from tests.golden_utils import assert_close, golden
from trawlkit.compat import Compat
from trawlkit.rigging import (
    AV_IZZO_SHARES,
    AV_PRADO_SHARES,
    CATENARY_RATIO_EXCEL,
    catenary_ratio,
    dpa_fridman_m,
    dpa_fridman_table,
    dpa_from_cut_angle_m,
    dpa_geometric_m,
    dpa_geometric_working_m,
    fridman_flotation_total_kgf,
    fridman_spread,
    headrope_sag_m,
    horizontal_opening_m,
    stretched_circumference_m,
    towing_geometry,
    vertical_opening_fridman,
    vertical_opening_martini_m,
    vertical_opening_pct_m,
    vertical_opening_suzuki_m,
)

MEC = "mecanica_de_la_red"
DIM = "dimensiones_de_la_red"
FLOT = "flotacion_y_lastre"
PORT = "portones_y_aparejamiento"

#: Mallero del primer paño de dorso/vientre usado por Martini (Paños!B156 = 60 mm).
MARTINI_MESH_MM = 60.0


def g(key: str) -> Any:
    return golden(MEC, key)


def _geom() -> Any:
    return towing_geometry(g("depth_m"), g("net_length_no_bag_m"), g("bridle_length_m"), u2=g("u2"))


def _spread(compat: Compat = Compat.EXCEL) -> Any:
    return fridman_spread(
        g("door_area_m2"),
        g("door_cd"),
        g("door_cl"),
        np.array(g("speed_ms")),
        np.array(g("rn_std_kgf")),
        np.array(g("rn_mod_kgf")),
        g("warp_horizontal_shallow_m"),
        g("net_length_working_m"),
        g("bridle_length_m"),
        compat=compat,
    )


def _rigging() -> dict[str, float]:
    return {
        "crowfoot_m": g("crowfoot_m"),
        "crowfoot_extension_m": g("crowfoot_extension_m"),
        "sweeps_m": g("sweeps_m"),
        "bridle_m": g("upper_bridle_m"),
    }


def _table() -> Any:
    s = _spread()
    return dpa_fridman_table(s.dpa_std_m, s.dpa_mod_m, g("footrope_m"), **_rigging())


def _ffz() -> float:
    return fridman_flotation_total_kgf(
        golden(FLOT, "flotation_fridman_avg_150_kgf"),
        golden(FLOT, "flotation_fridman_avg_180_kgf"),
        golden(FLOT, "flotation_prado_150_kgf"),
        golden(FLOT, "flotation_prado_180_kgf"),
    )


def _av_fridman(which: str) -> Any:
    return vertical_opening_fridman(
        np.array(g(f"rn_{which}_kgf_av")),
        g("flotation_total_kgf"),
        g("headrope_sag_m"),
        g("bridle_length_m"),
        g("dan_leno_m"),
    )


CASES: list[tuple[str, str, Callable[[], Any]]] = [
    ("warp_depth_ratio", "J178", lambda: _geom().warp_depth_ratio),
    ("warp_length_m", "E177", lambda: _geom().warp_m),
    ("warp_horizontal_shallow_m", "F179", lambda: _geom().warp_horizontal_shallow_m),
    ("warp_horizontal_deep_m", "F180", lambda: _geom().warp_horizontal_deep_m),
    ("net_length_working_m", "E185", lambda: _geom().net_length_working_m),
    ("door_drag_rd_kgf", "H164:H172", lambda: _spread().door_drag_kgf),
    ("door_lift_fdy_kgf", "I164:I172", lambda: _spread().door_lift_kgf),
    ("edx_std", "L164:L172", lambda: _spread().edx_std),
    ("edx_mod", "M164:M172", lambda: _spread().edx_mod),
    ("edy_std", "N164:N172", lambda: _spread().edy_std),
    ("edy_mod", "O164:O172", lambda: _spread().edy_mod),
    ("dpa_fridman_std_m", "P164:P172", lambda: _spread().dpa_std_m),
    ("dpa_fridman_mod_m", "Q164:Q172", lambda: _spread().dpa_mod_m),
    ("yn_std_m", "I193:I201", lambda: _table().yn_std_m),
    ("yn_mod_m", "J193:J201", lambda: _table().yn_mod_m),
    ("dpa_fridman_2yn_std_m", "K193:K201", lambda: _table().dpa_std_m),
    ("dpa_fridman_2yn_mod_m", "L193:L201", lambda: _table().dpa_mod_m),
    ("door_spread_from_dpa_m", "M193:M201", lambda: _table().door_spread_from_dpa_m),
    (
        "dpa_geometric_std_m",
        "L211",
        lambda: dpa_geometric_m(g("footrope_m"), g("door_spread_m"), **_rigging()),
    ),
    (
        "dpa_geometric_working_m",
        "L225",
        lambda: dpa_geometric_working_m(
            g("door_spread_m"), g("net_length_working_m"), **_rigging()
        ),
    ),
    (
        "dpa_from_cut_angle_m",
        "L233",
        lambda: dpa_from_cut_angle_m(g("net_length_total_std_m"), g("u2"), g("cut_angle_deg")),
    ),
    (
        "av_prado_low_opening_m",
        "F245",
        lambda: vertical_opening_pct_m(g("circumference_m"), AV_PRADO_SHARES["low_opening"]),
    ),
    (
        "av_prado_high_opening_m",
        "F246",
        lambda: vertical_opening_pct_m(g("circumference_m"), AV_PRADO_SHARES["high_opening"]),
    ),
    (
        "av_prado_shellfish_m",
        "F247",
        lambda: vertical_opening_pct_m(g("circumference_m"), AV_PRADO_SHARES["shellfish"]),
    ),
    (
        "av_izzo_4_35pct_m",
        "K242",
        lambda: vertical_opening_pct_m(g("circumference_m"), AV_IZZO_SHARES[0]),
    ),
    (
        "av_izzo_5pct_m",
        "K243",
        lambda: vertical_opening_pct_m(g("circumference_m"), AV_IZZO_SHARES[1]),
    ),
    (
        "av_izzo_6pct_m",
        "K244",
        lambda: vertical_opening_pct_m(g("circumference_m"), AV_IZZO_SHARES[2]),
    ),
    (
        "av_izzo_7pct_m",
        "K245",
        lambda: vertical_opening_pct_m(g("circumference_m"), AV_IZZO_SHARES[3]),
    ),
    ("vertical_opening_m", "D255", lambda: vertical_opening_suzuki_m(g("circumference_m"))),
    ("av_martini_dv_m", "E269", lambda: stretched_circumference_m(372 + 372, MARTINI_MESH_MM)),
    (
        "av_martini_m",
        "E272",
        lambda: vertical_opening_martini_m(
            g("av_martini_dv_m"), g("av_martini_mr_meshes"), MARTINI_MESH_MM
        ),
    ),
    ("flotation_total_kgf", "O261", _ffz),
    ("headrope_sag_m", "O267", lambda: headrope_sag_m(golden(FLOT, "headrope_m"))),
    ("catenary_ratio", "O266", lambda: catenary_ratio(0.87)),
    ("alpha_fridman_std_deg", "M272:M280", lambda: _av_fridman("std").angle_deg),
    ("alpha_fridman_mod_deg", "N272:N280", lambda: _av_fridman("mod").angle_deg),
    ("av_fridman_std_m", "O272:O280", lambda: _av_fridman("std").av_m),
    ("av_fridman_mod_m", "P272:P280", lambda: _av_fridman("mod").av_m),
    ("av_fridman_avg_std_m", "O282", lambda: _av_fridman("std").av_average_m),
    ("av_fridman_avg_mod_m", "P282", lambda: _av_fridman("mod").av_average_m),
]


@pytest.mark.parametrize(("key", "cell", "compute"), CASES, ids=[f"{k}[{c}]" for k, c, _ in CASES])
def test_golden(key: str, cell: str, compute: Callable[[], Any]) -> None:
    assert_close(compute(), g(key), where=f"{MEC}:{key} ({cell})")


def test_horizontal_opening_dim_f61() -> None:
    ah = horizontal_opening_m(
        g("dpa_from_cut_angle_m"),
        g("dpa_geometric_working_m"),
        g("dpa_geometric_std_m"),
        np.array(g("dpa_fridman_2yn_std_m")),
    )
    assert_close(ah, golden(DIM, "horizontal_opening_m"), where="Dim!F61")


def test_headrope_sag_matches_portones() -> None:
    assert_close(headrope_sag_m(golden(FLOT, "headrope_m")), golden(PORT, "headrope_sag_m"))
    assert CATENARY_RATIO_EXCEL == catenary_ratio(0.87)
    # El DPA/L real de la hoja (0.45) queda fuera de la tabla (0.99…0.56): el valor fijo 0.216 es
    # el de DPA/L = 0.87, no el del modelo.
    assert catenary_ratio(g("dpa_over_l")) != CATENARY_RATIO_EXCEL


def test_dpa_fridman_corrected_uses_standard_edy() -> None:
    excel = _spread(Compat.EXCEL)
    corrected = _spread(Compat.CORRECTED)
    assert_close(corrected.dpa_mod_m, excel.dpa_mod_m)
    expected_std = dpa_fridman_m(
        g("warp_horizontal_shallow_m"),
        g("net_length_working_m"),
        corrected.edy_std,
        g("bridle_length_m"),
        corrected.edx_std,
    )
    assert_close(corrected.dpa_std_m, expected_std)
    # Edy estándar < Edy modificada (RN estándar mayor) → la DPA corregida es menor.
    assert np.all(np.asarray(corrected.dpa_std_m) < np.asarray(excel.dpa_std_m))
    assert_close(np.asarray(corrected.dpa_std_m)[0], 5.661, rtol=1e-3)


def test_dpa_geometric_rounding_direction() -> None:
    # 13.77 → ROUNDDOWN 13 ; 12.53 → ROUNDUP 13
    raw_std = g("footrope_m") * g("door_spread_m") / (sum(_rigging().values()) + g("footrope_m"))
    raw_working = (
        g("door_spread_m")
        * g("net_length_working_m")
        / (g("net_length_working_m") + sum(_rigging().values()))
    )
    assert 13.7 < raw_std < 13.8 and 12.5 < raw_working < 12.6
    assert dpa_geometric_m(g("footrope_m"), g("door_spread_m"), **_rigging()) == 13
    assert (
        dpa_geometric_working_m(g("door_spread_m"), g("net_length_working_m"), **_rigging()) == 13
    )


def test_towing_geometry_to_dict() -> None:
    d = _geom().to_dict()
    assert d["warp_m"] == 200 and d["u2"] == 0.87
    assert set(_spread().to_dict()) >= {"dpa_std_m", "dpa_mod_m", "edx_std", "edy_mod"}
