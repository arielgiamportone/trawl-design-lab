"""Bridas, patentes y pies de gallo (rigging.bridles) contra 'Portones y aparejamiento'."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pytest

from tests.golden_utils import assert_close, golden
from trawlkit.compat import Compat
from trawlkit.rigging import (
    attack_angle_deg,
    bridle_lengths,
    crowfoot_m,
    sweeps_dremiere_m,
    sweeps_length_m,
    sweeps_martini_m,
)

PORT = "portones_y_aparejamiento"


def g(key: str) -> Any:
    return golden(PORT, key)


def _bridles() -> Any:
    return bridle_lengths(
        g("vertical_opening_std_m"),
        g("headrope_sag_m"),
        g("bridle_angle_deg"),
        g("dan_leno_height_m"),
    )


CASES: list[tuple[str, str, Callable[[], Any]]] = [
    ("bridle_length_no_triangle_std_m", "E52", lambda: _bridles().no_triangle_m),
    ("bridle_length_no_triangle_mod_m", "F52", lambda: _bridles().no_triangle_m),
    ("bridle_length_triangle_std_m", "E60", lambda: _bridles().triangle_m),
    ("bridle_length_triangle_mod_m", "F60", lambda: _bridles().triangle_m),
    ("upper_bridle_std_m", "D44", lambda: _bridles().upper_m),
    ("upper_bridle_mod_m", "E44", lambda: _bridles().upper_m),
    ("adjust_chain_std_m", "D46", lambda: _bridles().adjust_chain_m),
    ("adjust_chain_mod_m", "E46", lambda: _bridles().adjust_chain_m),
    ("lower_bridle_std_m", "D45", lambda: _bridles().lower_m),
    ("lower_bridle_mod_m", "E45", lambda: _bridles().lower_m),
    (
        "sweeps_dremiere_m",
        "C71",
        lambda: sweeps_dremiere_m(g("warp_length_m"), g("dremiere_ratio")),
    ),
    (
        "sweeps_martini_m",
        "G71",
        lambda: sweeps_martini_m(
            g("door_spread_m"),
            g("sweeps_dpa_m"),
            g("sweeps_martini_delta_deg"),
            compat=Compat.EXCEL,
        ),
    ),
    (
        "sweeps_no_triangle_m",
        "C83",
        lambda: sweeps_length_m(
            g("door_spread_m"), g("sweeps_net_length_m"), g("sweeps_dpa_m"), g("sweeps_bridle_m")
        ),
    ),
    (
        "sweeps_triangle_m",
        "C87",
        lambda: sweeps_length_m(
            g("door_spread_m"),
            g("sweeps_net_length_m"),
            g("sweeps_dpa_m"),
            g("sweeps_bridle_triangle_m"),
        ),
    ),
    ("crowfoot_m", "E97", lambda: crowfoot_m(g("door_length_for_crowfoot_m")).length_m),
    ("crowfoot_upper_m", "G98", lambda: crowfoot_m(g("door_length_for_crowfoot_m")).upper_m),
    (
        "crowfoot_extension_m",
        "E99",
        lambda: crowfoot_m(g("door_length_for_crowfoot_m")).extension_m,
    ),
    (
        "bridle_attack_angle_deg",
        "D110",
        lambda: attack_angle_deg(
            g("door_spread_m"),
            g("sweeps_dpa_m"),
            g("crowfoot_m"),
            g("sweeps_no_triangle_m"),
            g("bridle_length_no_triangle_std_m"),
        ),
    ),
]


@pytest.mark.parametrize(("key", "cell", "compute"), CASES, ids=[f"{k}[{c}]" for k, c, _ in CASES])
def test_golden(key: str, cell: str, compute: Callable[[], Any]) -> None:
    assert_close(compute(), g(key), where=f"{PORT}:{key} ({cell})")


def test_bridle_rounding_is_excel_round_half_away() -> None:
    # AV/sin α − fL = 17.51 → 18; (AV − h)/sin α = 16.54 → 17; 18 − 1.71 = 16.29 → ROUNDUP 17.
    b = _bridles()
    raw = g("vertical_opening_std_m") / np.sin(np.radians(4.8)) - g("headrope_sag_m")
    assert 17.4 < raw < 17.6
    assert b.upper_m == 18 and b.lower_m == 17 and b.triangle_m == 17
    assert b.to_dict()["adjust_chain_m"] == pytest.approx(18 * 0.095)


def test_sweeps_martini_corrected_uses_sine_of_degrees() -> None:
    ds, dpa, delta = g("door_spread_m"), g("sweeps_dpa_m"), g("sweeps_martini_delta_deg")
    corrected = sweeps_martini_m(ds, dpa, delta)
    assert_close(corrected, (ds - dpa) / (2 * np.sin(np.radians(delta))))
    # 28.5 m en vez de los 16.1 m del Excel (DEGREES(SIN(20)) y precedencia).
    assert corrected > sweeps_martini_m(ds, dpa, delta, compat=Compat.EXCEL)
    assert 28 < corrected < 29


def test_crowfoot_rounds_to_one_decimal() -> None:
    assert crowfoot_m(1.9).length_m == pytest.approx(2.3)  # 2.28 → 2.3
    assert crowfoot_m(1.4).length_m == pytest.approx(1.7)  # 1.68 → 1.7
