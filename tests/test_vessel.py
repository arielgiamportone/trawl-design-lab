"""trawlkit.vessel contra 'Potenc disponible para arrastre' (tests/golden)."""

from __future__ import annotations

import pytest

from tests.golden_utils import assert_close, golden, golden_entry
from trawlkit import vessel as ve
from trawlkit.io import load_vessels
from trawlkit.power import load_power_coefficients
from trawlkit.units import HP_TO_KW_EXCEL

SHEET = "potenc_disponible_para_arrastre"
BHPS = [150.0, 180.0]

#: Campo del PowerBudget → prefijo de la clave golden.
FIELDS = {
    "bhp": "bhp",
    "nominal_hp": "nominal_hp",
    "towing_hp": "towing_hp",
    "propeller_loss_hp": "propeller_loss_hp",
    "wave_loss_hp": "wave_loss_hp",
    "friction_loss_hp": "friction_loss_hp",
    "wake_loss_hp": "wake_loss_hp",
    "air_loss_hp": "air_loss_hp",
    "bhp_kw": "bhp_kw",
    "nominal_kw": "nominal_kw",
    "towing_kw": "towing_kw",
    "propeller_loss_kw": "propeller_loss_kw",
    "wave_loss_kw": "wave_loss_kw",
    "friction_loss_kw": "friction_loss_kw",
    "wake_loss_kw": "wake_loss_kw",
    "air_loss_kw": "air_loss_kw",
}


def _case_id(bhp: float, key: str) -> str:
    return f"{key}_{int(bhp)}[{golden_entry(SHEET, f'{key}_{int(bhp)}')['cell']}]"


@pytest.mark.parametrize(
    ("bhp", "attr", "key"),
    [(b, attr, key) for b in BHPS for attr, key in FIELDS.items()],
    ids=[_case_id(b, key) for b in BHPS for key in FIELDS.values()],
)
def test_power_budget_golden(bhp: float, attr: str, key: str) -> None:
    budget = ve.power_budget(bhp)
    assert_close(
        getattr(budget, attr), golden(SHEET, f"{key}_{int(bhp)}"), where=f"{key}_{int(bhp)}"
    )
    assert_close(budget.to_dict()[attr], golden(SHEET, f"{key}_{int(bhp)}"))


@pytest.mark.parametrize("bhp", BHPS, ids=["150", "180"])
def test_power_budget_consistency(bhp: float) -> None:
    budget = ve.power_budget(bhp)
    assert budget.hp_to_kw == HP_TO_KW_EXCEL
    # Las cinco pérdidas suman 1.0·BHP (35 + 27 + 18 + 17 + 3 = 100 %).
    assert_close(budget.losses_hp, bhp)
    assert_close(budget.nominal_hp - budget.bhp, budget.towing_hp)
    assert set(budget.to_dict()) == set(FIELDS) | {"hp_to_kw"}


def test_power_budget_matches_yaml_fractions() -> None:
    split = load_power_coefficients()["fridman"]["energy_split"]
    assert ve.NOMINAL_OVER_BHP == split["nominal_over_bhp"]["fraction"]
    assert ve.TOWING_FRACTION == split["towing"]["fraction"]
    for name, frac in ve.LOSS_FRACTIONS.items():
        assert frac == split[name]["fraction"], name
    assert HP_TO_KW_EXCEL == load_power_coefficients()["fridman"]["hp_to_kw"]


def test_power_budget_overrides() -> None:
    budget = ve.power_budget(100.0, losses={"air": 0.05}, hp_to_kw=0.7355)
    assert_close(budget.air_loss_hp, 5.0)
    assert_close(budget.wave_loss_hp, 27.0)
    assert_close(budget.air_loss_kw, 5.0 * 0.7355)
    with pytest.raises(ValueError):
        ve.power_budget(0.0)


@pytest.mark.parametrize(
    ("bhp", "displacement_t", "key"),
    [(150.0, 10.0, "admiralty_speed_150"), (180.0, 12.0, "admiralty_speed_180")],
    ids=["admiralty_speed_150[H27]", "admiralty_speed_180[H38]"],
)
def test_admiralty_speed_golden(bhp: float, displacement_t: float, key: str) -> None:
    v = ve.admiralty_speed_kn(ve.nominal_hp(bhp), displacement_t)
    assert_close(v, golden(SHEET, key), where=key)
    assert golden_entry(SHEET, key)["cell"] in {"H27", "H38"}


def test_admiralty_speed_rejects_bad_displacement() -> None:
    with pytest.raises(ValueError):
        ve.admiralty_speed_kn(199.5, 0.0)


@pytest.mark.parametrize("vessel_id", ["fao_a3_150hp", "fao_a3_180hp"])
def test_vessel_presets(vessel_id: str) -> None:
    vessel = next(v for v in load_vessels().vessels if v.id == vessel_id)
    tag = int(vessel.bhp)
    budget = ve.vessel_power_budget(vessel)
    assert_close(budget.nominal_hp, golden(SHEET, f"nominal_hp_{tag}"))
    assert_close(budget.towing_hp, golden(SHEET, f"towing_hp_{tag}"))
    # Los extras del preset (nominal_hp, trawl_pull_hp) coinciden con el reparto calculado.
    extras = vessel.model_extra or {}
    assert_close(budget.nominal_hp, extras["nominal_hp"])
    assert_close(budget.towing_hp, extras["trawl_pull_hp"])
    assert_close(ve.vessel_admiralty_speed_kn(vessel), golden(SHEET, f"admiralty_speed_{tag}"))
