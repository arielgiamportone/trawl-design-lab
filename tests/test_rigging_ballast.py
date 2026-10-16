"""Lastre (rigging.ballast) contra 'Flotación y Lastre'."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pytest

from tests.golden_utils import assert_close, golden
from trawlkit.rigging import (
    adjust_chain_weight_kg,
    ballast_even_kg_m,
    ballast_fridman_kg,
    ballast_koyama_kg,
    ballast_limits,
    ballast_prado_kg,
    distribute_ballast_max,
    distribute_ballast_min,
    rope_weight_air_kg,
    rope_weight_in_water_kg,
)

FLOT = "flotacion_y_lastre"


def g(key: str) -> Any:
    return golden(FLOT, key)


def _ballast(hp: int, which: str) -> Any:
    return ballast_fridman_kg(
        np.array(g(f"float_f1_vertical_{hp}_kgf")),
        np.array(g(f"float_f2_vertical_{which}_{hp}_kgf")),
        g("footrope_weight_water_kgf"),
    )


def _limits() -> Any:
    return ballast_limits(g("ballast_mod_150_kg")[0], g("ballast_std_150_kg")[4])


def _min() -> Any:
    return distribute_ballast_min(g("ballast_min_150_kg"), g("footrope_m"))


def _max() -> Any:
    return distribute_ballast_max(
        g("ballast_max_150_kg"), g("footrope_m"), chain_m=g("adjust_chain_m")
    )


CASES: list[tuple[str, str, Callable[[], Any]]] = [
    ("ballast_koyama_kg", "G159", lambda: ballast_koyama_kg(g("headrope_m"))),
    ("ballast_prado_150_kg", "I173", lambda: ballast_prado_kg(150, g("ballast_prado_k_150"))),
    ("ballast_prado_180_kg", "I180", lambda: ballast_prado_kg(180, g("ballast_prado_k_180"))),
    (
        "footrope_weight_air_kg",
        "G188",
        lambda: rope_weight_air_kg(g("footrope_m"), g("footrope_kg_per_m")),
    ),
    (
        "footrope_weight_water_kgf",
        "G191",
        lambda: rope_weight_in_water_kg(g("footrope_weight_air_kg"), g("coef_steel") / 10),
    ),
    ("ballast_std_150_kg", "L197:L205", lambda: _ballast(150, "std")),
    ("ballast_mod_150_kg", "M197:M205", lambda: _ballast(150, "mod")),
    ("ballast_std_180_kg", "L210:L218", lambda: _ballast(180, "std")),
    ("ballast_mod_180_kg", "M210:M218", lambda: _ballast(180, "mod")),
    ("ballast_min_150_kg", "F225", lambda: _limits().min_kg),
    ("ballast_max_150_kg", "F226", lambda: _limits().max_kg),
    (
        "adjust_chain_weight_kg",
        "H224",
        lambda: adjust_chain_weight_kg(g("ballast_min_150_kg"), chain_m=g("adjust_chain_m")),
    ),
    (
        "ballast_even_kg_m",
        "E233",
        lambda: ballast_even_kg_m(
            g("ballast_min_150_kg"), g("adjust_chain_weight_kg"), g("footrope_m")
        ),
    ),
    ("ballast_min_adjust_kg", "G236", lambda: _min().adjust_kg),
    ("ballast_min_bosom_kg", "G237", lambda: _min().bosom_kg),
    ("ballast_min_wings_kg", "G238", lambda: _min().wings_kg),
    ("ballast_min_adjust_kg_m", "I236", lambda: _min().adjust_kg_m),
    ("ballast_min_bosom_kg_m", "I237", lambda: _min().bosom_kg_m),
    ("ballast_min_wings_kg_m", "I238", lambda: _min().wings_kg_m),
    ("ballast_max_adjust_kg", "G243", lambda: _max().adjust_kg),
    ("ballast_max_bosom_kg", "G244", lambda: _max().bosom_kg),
    ("ballast_max_wings_kg", "G245", lambda: _max().wings_kg),
    ("ballast_max_adjust_kg_m", "I243", lambda: _max().adjust_kg_m),
    ("ballast_max_bosom_kg_m", "I244", lambda: _max().bosom_kg_m),
    ("ballast_max_wings_kg_m", "I245", lambda: _max().wings_kg_m),
]


@pytest.mark.parametrize(("key", "cell", "compute"), CASES, ids=[f"{k}[{c}]" for k, c, _ in CASES])
def test_golden(key: str, cell: str, compute: Callable[[], Any]) -> None:
    assert_close(compute(), g(key), where=f"{FLOT}:{key} ({cell})")


def test_limits_rounding_directions() -> None:
    # mínimo = ROUNDDOWN(27.29) = 27 ; máximo = ROUNDUP(41.40) = 42
    lim = _limits()
    assert lim.min_kg == 27 and lim.max_kg == 42
    assert lim.to_dict() == {"min_kg": 27.0, "max_kg": 42.0}
    assert ballast_limits(27.0, 42.0).max_kg == 42  # ROUNDUP de un entero no lo cambia


def test_min_distribution_sums_to_more_than_total_by_rounding() -> None:
    # 5 + 7 + 15 = 27 (ROUNDDOWN + ROUNDUP + ROUNDUP) ; 0.55·27 = 14.85 → 15.
    d = _min()
    assert d.adjust_kg + d.bosom_kg + d.wings_kg == 27
    m = _max()
    assert m.adjust_kg + m.bosom_kg + m.wings_kg == 42
    assert set(m.to_dict()) == {
        "adjust_kg",
        "bosom_kg",
        "wings_kg",
        "adjust_kg_m",
        "bosom_kg_m",
        "wings_kg_m",
    }


def test_ballast_fridman_scalar() -> None:
    assert ballast_fridman_kg(23.3461, 5.8755, 1.8078) == pytest.approx(27.4138)
