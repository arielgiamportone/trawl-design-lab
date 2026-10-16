"""Cabos (rigging.ropes) contra 'Cables Y Cabulleria' y 'Flotación y Lastre'."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from tests.golden_utils import assert_close, golden
from trawlkit.rigging import (
    ROPE_WATER_WEIGHT_COEF,
    rope_weight_air_kg,
    rope_weight_in_water_kg,
    select_rope,
    wingtip_reinforcement_m,
)

CAB = "cables_y_cabulleria"
FLOT = "flotacion_y_lastre"
DIM = "dimensiones_de_la_red"


def g(key: str) -> Any:
    return golden(CAB, key)


CASES: list[tuple[str, str, Callable[[], Any]]] = [
    ("headrope_rope_kg_per_m", "G3", lambda: select_rope(g("headrope_rope")).weight_kg_per_m),
    ("headrope_rope_strength_t", "H3", lambda: select_rope(g("headrope_rope")).breaking_load_t),
    ("headrope_rope_diameter_mm", "I3", lambda: select_rope(g("headrope_rope")).diameter_mm),
    ("footrope_rope_kg_per_m", "G4", lambda: select_rope(g("footrope_rope")).weight_kg_per_m),
    ("footrope_rope_strength_t", "H4", lambda: select_rope(g("footrope_rope")).breaking_load_t),
    ("footrope_rope_diameter_mm", "I4", lambda: select_rope(g("footrope_rope")).diameter_mm),
    (
        "wingtip_reinforcement_m",
        "J5",
        lambda: wingtip_reinforcement_m(golden(DIM, "wingtip_reinforcement_m")),
    ),
]


@pytest.mark.parametrize(("key", "cell", "compute"), CASES, ids=[f"{k}[{c}]" for k, c, _ in CASES])
def test_golden(key: str, cell: str, compute: Callable[[], Any]) -> None:
    assert_close(compute(), g(key), where=f"{CAB}:{key} ({cell})")


def test_select_rope_by_id_and_description() -> None:
    by_desc = select_rope("COMBINADO 12 Acero6x24+7")
    by_id = select_rope("combinado_12_acero6x24_7")
    assert by_desc == by_id
    assert by_desc.to_dict()["diameter_mm"] == 12
    with pytest.raises(KeyError):
        select_rope("PP 99")


def test_rope_weights_match_flotacion_sheet() -> None:
    air = rope_weight_air_kg(golden(FLOT, "headrope_m"), golden(FLOT, "headrope_kg_per_m"))
    assert_close(air, golden(FLOT, "headrope_weight_air_kg"), where="Flot!F36")
    assert_close(
        rope_weight_in_water_kg(air), golden(FLOT, "headrope_weight_water_kgf"), where="F37"
    )
    foot_air = rope_weight_air_kg(golden(FLOT, "footrope_m"), golden(FLOT, "footrope_kg_per_m"))
    assert_close(foot_air, golden(FLOT, "footrope_weight_air_kg"), where="Flot!G188")
    # G191 = G188·0.87/10: el mismo coeficiente 0.087 que la lima.
    assert_close(golden(FLOT, "coef_steel") / 10, ROPE_WATER_WEIGHT_COEF)
    assert_close(
        rope_weight_in_water_kg(foot_air), golden(FLOT, "footrope_weight_water_kgf"), where="G191"
    )


def test_wingtip_reinforcement_roundup_one_decimal() -> None:
    assert wingtip_reinforcement_m(2.88) == pytest.approx(11.6)  # 11.52 → 11.6
    assert wingtip_reinforcement_m(2.9) == pytest.approx(11.6)  # 11.6 exacto se conserva
    assert wingtip_reinforcement_m(2.9001) == pytest.approx(11.7)
