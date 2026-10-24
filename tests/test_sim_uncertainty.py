"""Fase 11.4: incertidumbre (hipercubo latino), calibración y registros de sensores."""

from __future__ import annotations

import math

import numpy as np
import pytest

from trawlkit.model import run
from trawlkit.sensors import (
    example_log,
    match_column,
    parse_log,
    to_observations,
    windows,
)
from trawlkit.sim import Scenario, simulate
from trawlkit.sim.calibration import Observation, calibrate, dynamit_observations
from trawlkit.sim.uncertainty import (
    default_inputs,
    latin_hypercube,
    spearman,
    uncertainty,
)
from trawlkit.sim.validation import standard_case


@pytest.fixture(scope="module")
def result():  # type: ignore[no-untyped-def]
    return run(standard_case())


# --- muestreo y sensibilidad ----------------------------------------------------------------


def test_latin_hypercube_one_point_per_stratum() -> None:
    u = latin_hypercube(8, 3, np.random.default_rng(1))
    assert u.shape == (8, 3)
    for j in range(3):
        assert sorted(np.floor(u[:, j] * 8).astype(int).tolist()) == list(range(8))


def test_spearman() -> None:
    x = np.arange(10.0)
    assert spearman(x, x**3) == pytest.approx(1.0)
    assert spearman(x, -x) == pytest.approx(-1.0)
    assert spearman(x, np.ones(10)) == 0.0


def test_default_inputs_follow_scenario() -> None:
    names = [i.name for i in default_inputs(Scenario(seabed="rock"))]
    assert names[:3] == ["cn", "ct", "mu_gear"] and "catch_cp" not in names
    rock = {i.name: i for i in default_inputs(Scenario(seabed="rock"))}
    assert rock["mu_gear"].low < rock["mu_gear"].nominal < rock["mu_gear"].high
    with_catch = [i.name for i in default_inputs(Scenario(catch_kg=300))]
    assert "catch_bulk_density" in with_catch and "catch_cp" in with_catch
    fixed = [i.name for i in default_inputs(Scenario(coupled_doors=False))]
    assert "door_cl_factor" not in fixed


def test_door_lift_factor_closes_doors(result) -> None:  # type: ignore[no-untyped-def]
    kw = {"resolution": 2, "coarse_resolution": None}
    base = simulate(result, 3.0, scenario=Scenario(seabed="mixed"), **kw)
    weak = simulate(result, 3.0, scenario=Scenario(seabed="mixed", door_cl_factor=0.8), **kw)
    assert weak.door_spread_m < base.door_spread_m
    with pytest.raises(ValueError):
        Scenario(door_cd_factor=5)


def test_uncertainty_bands(result) -> None:  # type: ignore[no-untyped-def]
    u = uncertainty(
        result,
        3.0,
        scenario=Scenario(seabed="mixed", catch_kg=300),
        n=5,
        resolution=2,
        species=["cod"],
    )
    assert u.samples.shape == (5, len(u.inputs))
    for inp, col in zip(u.inputs, u.samples.T, strict=True):
        assert np.all((inp.low <= col) & (col <= inp.high))
    d = u.to_dict()
    keys = {o["key"] for o in d["outputs"]}
    assert {"door_spread_m", "towing_pull_kgf", "fuel_l_h", "l50_cod"} <= keys
    for o in d["outputs"]:
        assert o["p10"] <= o["p50"] <= o["p90"]
        assert set(o["sensitivity"]) == {i.name for i in u.inputs}
    with pytest.raises(ValueError):
        uncertainty(result, 3.0, n=1)


# --- calibración ------------------------------------------------------------------------------


def test_observation_validation() -> None:
    with pytest.raises(ValueError):
        Observation("wingspan", 10.0, 3.0)
    with pytest.raises(ValueError):
        Observation("ah_m", -1.0, 3.0)
    obs = dynamit_observations((2.0, 3.0), ("door_spread_m", "drag_kgf"))
    assert len(obs) == 4 and obs[0].value == pytest.approx(46.6)


def test_calibration_recovers_door_lift(result) -> None:  # type: ignore[no-untyped-def]
    truth = Scenario(seabed="mixed", door_cl_factor=0.85)
    obs = []
    for v in (2.5, 3.5):
        r = simulate(result, v, resolution=2, coarse_resolution=None, scenario=truth)
        obs.append(Observation("door_spread_m", r.door_spread_m, v))
        obs.append(Observation("warp_tension_kgf", r.warp_tension_kgf, v))
    c = calibrate(
        result,
        obs,
        ["door_cl_factor"],
        scenario=Scenario(seabed="mixed"),
        resolution=2,
        max_evals=10,
    )
    assert c.fitted[0] == pytest.approx(0.85, abs=0.02)
    assert c.rmse_after < c.rmse_before
    d = c.to_dict()
    assert d["params"][0]["name"] == "door_cl_factor"
    assert len(d["observations"]) == 4
    with pytest.raises(ValueError):
        calibrate(result, obs, ["gravity"])


# --- registros de sensores ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("header", "qty", "factor"),
    [
        ("speed_kn", "speed", 1.0),
        ("SOG (m/s)", "speed", 1.9438445),
        ("Velocidad (kn)", "speed", 1.0),
        ("Tension babor (t)", "warp_tension_port", 1000.0),
        ("warp_tension_kN", "warp_tension", 101.97162),
        ("Door spread [m]", "door_spread", 1.0),
        ("Headline height (fm)", "headrope_height", 1.8288),
        ("Profundidad", "depth", 1.0),
    ],
)
def test_match_column(header: str, qty: str, factor: float) -> None:
    m = match_column(header)
    assert m is not None and m[0] == qty and m[1] == pytest.approx(factor)


def test_match_column_unknown() -> None:
    assert match_column("salinity") is None
    assert match_column("speed (furlongs)") is None


def test_parse_english_csv_and_windows() -> None:
    rows = ["time,SOG (m/s),door_spread_m,headline_height_m,warp_tension_kN,notes"]
    for k in range(40):
        v = 1.3 if k < 20 else 1.8  # 2,5 y 3,5 kn
        rows.append(f"{k * 30},{v},{40 + k % 3},{1.2},{4.0 + 0.1 * (k % 2)},x")
    log = parse_log("\n".join(rows))
    assert log.ignored == ("notes",)
    assert log.columns["speed"][0] == pytest.approx(1.3 * 1.9438445)
    ws = windows(log, by="speed", width=0.25)
    assert [w.n for w in ws] == [20, 20]
    assert ws[0].values["door_spread_m"] == pytest.approx(41.0)
    assert ws[0].values["warp_tension_kgf"] == pytest.approx(4.05 * 101.97162, rel=1e-3)
    by_time = windows(log, by="time", width=10)
    assert len(by_time) == 2
    obs = to_observations(ws, ["door_spread_m"])
    assert len(obs) == 2 and all(o.quantity == "door_spread_m" for o in obs)


def test_parse_errors() -> None:
    with pytest.raises(ValueError):
        parse_log("solo una línea")
    with pytest.raises(ValueError):
        parse_log("a,b\n1,2")  # ninguna columna reconocida
    log = parse_log("door_spread_m\n40\n41")
    assert any("velocidad" in w for w in log.warnings)
    with pytest.raises(ValueError):
        windows(log, by="speed")


def test_example_log() -> None:
    log = parse_log(example_log())
    assert log.rows == 360 and not log.ignored
    ws = windows(log, by="time", width=20)
    assert [round(w.speed_kn, 1) for w in ws] == [2.5, 3.0, 3.5]
    assert [w.catch_kg for w in ws] == [100.0, 300.0, 500.0]
    assert all(math.isfinite(v) for w in ws for v in w.values.values())
