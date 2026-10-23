"""Explorador de condiciones: ensuciamiento, corriente, cable, energía y huella."""

from __future__ import annotations

import pytest

from trawlkit.api import service
from trawlkit.model import DesignResult
from trawlkit.sim import Scenario, explore, fouling, fouling_catalogue, haul, simulate


@pytest.fixture(scope="module")
def result() -> DesignResult:
    return service.run_case(service.build_case(net="fao_a3_standard"))


BASE = Scenario(seabed="mixed")


def test_fouling_catalogue_and_validation() -> None:
    ids = [f.id for f in fouling_catalogue()]
    assert ids == ["clean", "algae_wings", "jellyfish_codend", "general"]
    assert fouling("clean").zones == {"wings": 0.0, "body": 0.0, "codend": 0.0}
    sc = Scenario(fouling="jellyfish_codend", fouling_level=0.5)
    assert sc.fouling_zones()["codend"] == pytest.approx(0.5)
    for bad in (
        {"fouling": "barnacles"},
        {"fouling_level": 3},
        {"current_kn": 5},
        {"warp_length_m": 5},
        {"haul_hours": 0},
    ):
        with pytest.raises((ValueError, KeyError)):
            Scenario(**bad)  # type: ignore[arg-type]


def test_fouling_raises_pull_and_closes_doors(result: DesignResult) -> None:
    runs = explore(
        result,
        "fouling_level",
        [0.0, 0.5, 1.0],
        scenario=Scenario(seabed="mixed", fouling="general"),
        resolution=3,
    )
    pull = [r.towing_pull_kgf for r in runs]
    dp = [r.door_spread_m for r in runs]
    assert pull[0] < pull[1] < pull[2]
    assert dp[0] > dp[2]
    assert 1.1 < pull[2] / pull[0] < 2.0
    assert runs[0].fouling_tri.max() == 0.0 and runs[2].fouling_tri.max() == pytest.approx(0.5)
    # sólo el escenario «medusas en el copo» ensucia el copo y no las alas
    jelly = simulate(
        result, 3.0, resolution=3, scenario=Scenario(seabed="mixed", fouling="jellyfish_codend")
    )
    assert jelly.fouling_tri.max() == pytest.approx(1.0)
    assert jelly.towing_pull_kgf > runs[0].towing_pull_kgf


def test_current_is_relative_water_speed(result: DesignResult) -> None:
    against = simulate(
        result, 3.0, resolution=3, scenario=Scenario(seabed="mixed", current_kn=-0.5)
    )
    faster = simulate(result, 3.5, resolution=3, scenario=BASE)
    assert against.towing_pull_kgf == pytest.approx(faster.towing_pull_kgf, rel=0.02)
    assert against.operation["water_speed_kn"] == pytest.approx(3.5)
    assert against.operation["ground_speed_kn"] == pytest.approx(3.0)
    # la huella usa la velocidad sobre el fondo
    assert against.operation["swept_area_km2_h"] < faster.operation["swept_area_km2_h"]
    with pytest.raises(ValueError, match="relativa"):
        simulate(result, 1.0, resolution=3, scenario=Scenario(current_kn=1.0))


def test_warp_length_spread_and_angle(result: DesignResult) -> None:
    runs = explore(result, "warp_length_m", [150.0, 200.0, 300.0], scenario=BASE, resolution=3)
    dp = [r.door_spread_m for r in runs]
    ang = [r.operation["warp_angle_deg"] for r in runs]
    assert dp[0] < dp[1] < dp[2]
    assert ang[0] > ang[1] > ang[2]
    assert [r.operation["warp_length_m"] for r in runs] == [150.0, 200.0, 300.0]


def test_energy_and_footprint(result: DesignResult) -> None:
    runs = explore(result, "speed_kn", [2.0, 3.0], scenario=Scenario(seabed="mud", catch_kg=600))
    slow, fast = (r.operation for r in runs)
    assert fast["fuel_l_h"] > slow["fuel_l_h"] > 0
    assert fast["towing_power_kw"] < fast["vessel_power_kw"]
    assert fast["power_limited"] is False
    assert fast["fuel_l_per_kg"] == pytest.approx(fast["fuel_l_h"] * 2.0 / 600)
    assert fast["swept_area_km2_h"] > slow["swept_area_km2_h"] > fast["contact_area_km2_h"] * 0
    assert 0 < fast["contact_area_km2_h"] < fast["swept_area_km2_h"]
    assert fast["penetration"] == "alta"
    assert fast["warp_tension_vessel_kgf"] >= fast["warp_tension_door_kgf"] * 0.9


def test_explore_matches_simulate_and_haul(result: DesignResult) -> None:
    a = explore(result, "catch_kg", [0.0, 500.0], scenario=BASE, resolution=3)
    b = haul(result, 3.0, [0.0, 500.0], scenario=BASE, resolution=3)
    assert [r.door_spread_m for r in a] == pytest.approx([r.door_spread_m for r in b])
    single = simulate(result, 3.0, resolution=3, scenario=Scenario(seabed="mixed", catch_kg=500))
    assert a[1].door_spread_m == pytest.approx(single.door_spread_m, rel=0.02)
    assert all(r.nodes.shape == a[0].nodes.shape for r in a)  # misma malla: se puede animar
    with pytest.raises(ValueError, match="variable"):
        explore(result, "colour", [1.0])
