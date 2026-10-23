"""Escenario de la simulación: catálogo de fondos, captura en el copo y portones acoplados."""

from __future__ import annotations

import pytest

from trawlkit.api import service
from trawlkit.model import DesignResult
from trawlkit.rigging import seabed, seabeds
from trawlkit.sim import Scenario, haul, simulate
from trawlkit.sim.validation import DYNAMIT


@pytest.fixture(scope="module")
def result() -> DesignResult:
    return service.run_case(service.build_case(net="fao_a3_standard"))


@pytest.fixture(scope="module")
def mud_haul(result: DesignResult) -> list:
    return haul(result, 3.0, [0.0, 400.0, 1000.0], scenario=Scenario(seabed="mud"))


def test_seabed_catalogue() -> None:
    ids = [s.id for s in seabeds()]
    assert ids == ["mud", "sand", "mixed", "gravel", "rock"]
    for s in seabeds():
        for r in (s.mu_gear, s.mu_door):
            assert 0.0 < r.low <= r.nominal <= r.high <= 1.0
    # el "Intermedio" de la especie del Excel y alias en castellano
    assert seabed("Intermedio").id == "mixed"
    assert seabed("fango").id == "mud"
    assert seabed("ROCA").id == "rock"
    with pytest.raises(KeyError):
        seabed("lava")
    # rozamiento creciente de fango a roca
    mus = [seabed(k).mu_gear.nominal for k in ("mud", "sand", "gravel", "rock")]
    assert mus == sorted(mus)


def test_scenario_validation_and_friction() -> None:
    sc = Scenario(catch_kg=600, seabed="arena")
    assert sc.catch_volume_m3 == pytest.approx(600 / 750)
    assert sc.friction(0.5) == (0.55, 0.50)
    assert Scenario(mu_gear=0.3).friction(0.5) == (0.3, 0.3)
    assert 0 < sc.catch_weight_water_n() < 600 * 9.81 * 0.1
    for bad in (
        {"catch_kg": -1},
        {"catch_bulk_density": 100},
        {"catch_cp": 5},
        {"mu_door": 2},
        {"seabed": "lava"},
    ):
        with pytest.raises((ValueError, KeyError)):
            Scenario(**bad)  # type: ignore[arg-type]


def test_basic_simulator_unchanged(result: DesignResult) -> None:
    basic = simulate(result, 3.0, resolution=3)
    assert basic.door_spread_m == pytest.approx(result.doors.spread_m)
    assert basic.scenario == {} and basic.catch == {} and basic.towing_pull_kgf == 0.0


def test_coupled_doors_reach_dynamit_spread(mud_haul: list) -> None:
    empty = mud_haul[0]
    assert empty.converged
    dyn = DYNAMIT["DP_m"][DYNAMIT["v_kn"].index(3.0)]
    # El motor empírico da 32,5 m; el equilibrio acoplado se acerca a DynamiT (51,4 m).
    assert empty.door_spread_m == pytest.approx(dyn, rel=0.15)
    # Portones apoyados en el fondo (centro a media altura de la zapata) y cable con catenaria.
    for x, _y, z in empty.door_positions_m:
        assert z == pytest.approx(0.475, abs=0.05)
        assert abs(x) < 5.0
    assert empty.towing_pull_kgf > empty.drag_kgf  # el tiro incluye portones y cables
    assert empty.warp_tension_kgf > 0.4 * empty.towing_pull_kgf
    assert empty.force_balance < 0.02


def test_catch_trends_follow_priour_de_la_prada(mud_haul: list) -> None:
    dp = [r.door_spread_m for r in mud_haul]
    pull = [r.towing_pull_kgf for r in mud_haul]
    ah = [r.ah_m for r in mud_haul]
    # Con la captura la separación de portones baja y el tiro y la tensión suben
    # (Priour y de la Prada 2015: −1,06 m/h de DP y +76 kg/h de tensión con la captura).
    assert dp[0] > dp[1] > dp[2]
    assert ah[0] > ah[2]
    assert pull[0] < pull[1] < pull[2]
    assert 1.0 < dp[0] - dp[2] < 10.0
    full = mud_haul[2]
    assert full.catch["volume_m3"] == pytest.approx(1000 / 750, rel=0.01)
    assert full.catch["overflow"] == 0.0
    assert full.catch["length_m"] > mud_haul[1].catch["length_m"] > 0
    # La resultante de la presión ≈ ½ρ C_p v² × área frontal de la captura.
    v = 3.0 * 1852 / 3600
    expected = 0.5 * 1024 * 1.0 * v * v * full.catch["front_area_m2"] / 9.80665
    assert full.catch_drag_kgf == pytest.approx(expected, rel=0.35)


def test_rougher_seabed_more_friction(result: DesignResult, mud_haul: list) -> None:
    rock = simulate(result, 3.0, resolution=4, scenario=Scenario(seabed="rock"))
    mud = mud_haul[0]
    assert rock.friction_kgf > 1.5 * mud.friction_kgf
    assert rock.door_friction_kgf > mud.door_friction_kgf
    assert rock.towing_pull_kgf > mud.towing_pull_kgf


def test_engine_seabed_friction_in_demand() -> None:
    base = service.run_case(service.build_case(net="fao_a3_standard"))
    mud = service.run_case(service.build_case(net="fao_a3_standard", params={"seabed": "mud"}))
    rock = service.run_case(service.build_case(net="fao_a3_standard", params={"seabed": "rock"}))
    f_mud = mud.summary()["seabed_friction_kgf"]
    f_rock = rock.summary()["seabed_friction_kgf"]
    assert isinstance(f_mud, float) and isinstance(f_rock, float)
    assert 0 < f_mud < f_rock
    assert "seabed_friction_kgf" not in base.summary()
    d0 = base.performance.demand.std
    assert mud.performance.demand.std - d0 == pytest.approx(f_mud)
    assert rock.summary()["max_speed_kn"] < base.summary()["max_speed_kn"]  # type: ignore[operator]
    with pytest.raises(ValueError):
        service.run_case(service.build_case(net="fao_a3_standard", params={"seabed": "lava"}))
