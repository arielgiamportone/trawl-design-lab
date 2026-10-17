"""Equilibrio de la red simulada a resolución gruesa (suite rápida de `trawlkit.sim`)."""

from __future__ import annotations

import json
import os
import time
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from trawlkit.compat import Compat
from trawlkit.model import DesignResult, run
from trawlkit.sim import SimResult, simulate, sweep
from trawlkit.sim.render import projections_svg
from trawlkit.sim.validation import markdown_table, standard_case, validate

COARSE = 4  # resolución de la suite rápida


@pytest.fixture(scope="module")
def result() -> DesignResult:
    return run(standard_case(compat=Compat.CORRECTED))


@pytest.fixture(scope="module")
def runs(result: DesignResult) -> list[SimResult]:
    return sweep(result, [2.0, 3.0, 4.0], resolution=COARSE, coarse_resolution=None)


@pytest.fixture(scope="module")
def r3(runs: list[SimResult]) -> SimResult:
    return runs[1]


def test_converged(runs: list[SimResult]) -> None:
    for r in runs:
        assert r.converged, (r.speed_kn, r.iterations, r.residual)
        assert r.residual < 0.05
        assert r.force_balance < 0.02


def test_force_balance(runs: list[SimResult]) -> None:
    """Σ F_x sobre la red = 0: el tiro de las bridas equilibra agua + rozamiento con el fondo."""
    for r in runs:
        snapshot = r.hydro_drag_kgf + r.friction_kgf
        assert r.bridle_pull_kgf == pytest.approx(snapshot, rel=0.03)
        assert r.drag_kgf == pytest.approx(snapshot, rel=0.03)


def test_symmetry(r3: SimResult) -> None:
    x = r3.nodes
    right, left = r3.wing_tips_upper
    assert x[right, 1] == pytest.approx(-x[left, 1], abs=1e-9)
    assert x[right, [0, 2]] == pytest.approx(x[left, [0, 2]], abs=1e-9)
    t = r3.bridle_tension_kgf
    for kind in ("upper_bridle", "lower_bridle", "sweep"):
        assert t[f"{kind}_right"] == pytest.approx(t[f"{kind}_left"], rel=1e-9)
    assert abs(x[r3.headrope[len(r3.headrope) // 2], 1]) < 1e-9


def test_shape_is_a_towed_bottom_trawl(r3: SimResult) -> None:
    x = r3.nodes
    assert r3.footrope_height_m == pytest.approx(0.0, abs=1e-6)  # burlón apoyado
    assert r3.headrope_height_m > 0.8  # lima levantada por las boyas
    assert np.all(x[:, 2] >= 0.0)
    assert 10.0 < r3.ah_m < 17.0
    assert r3.mouth_area_m2 > 5.0
    # Embudo: el ancho cae de la boca a la bolsa; la red se estira hacia popa (x > 0).
    net = np.unique(r3.triangles)
    xs = x[net]
    front = xs[xs[:, 0] < xs[:, 0].min() + 5.0]
    back = xs[xs[:, 0] > xs[:, 0].max() - 5.0]
    assert np.ptp(back[:, 1]) < 0.3 * np.ptp(front[:, 1])
    assert 34.0 < r3.net_length_m < 41.0  # largo estirado de dorso: 40,7 m
    # Ambas bridas trabajan (la cadena de reglaje iguala los largos).
    assert r3.bridle_tension_kgf["upper_bridle_right"] > 0.0
    assert r3.bridle_tension_kgf["lower_bridle_right"] > 0.0


def test_trends_with_speed(runs: list[SimResult]) -> None:
    av = [r.av_m for r in runs]
    drag = [r.drag_kgf for r in runs]
    assert av[0] > av[1] > av[2]
    assert drag[0] < drag[1] < drag[2]
    n = np.polyfit(np.log([r.speed_kn for r in runs]), np.log(drag), 1)[0]
    assert 1.3 < n < 2.1


def test_coarse_run_is_fast(result: DesignResult) -> None:
    t0 = time.perf_counter()
    r = simulate(result, 3.0, resolution=3, coarse_resolution=None)
    elapsed = time.perf_counter() - t0
    assert r.converged
    # Límite holgado: los runners de CI son varias veces más lentos que una máquina local.
    limit = float(os.environ.get("TRAWLKIT_SIM_TIME_LIMIT", "15.0"))
    assert elapsed < limit


def test_door_spread_override(result: DesignResult) -> None:
    r = simulate(result, 3.0, resolution=3, door_spread_m=40.0, coarse_resolution=None)
    assert r.door_spread_m == 40.0
    x = r.nodes
    doors = [k for k in range(x.shape[0]) if abs(abs(x[k, 1]) - 20.0) < 1e-9]
    assert len(doors) == 2


def test_to_dict_serialisable(r3: SimResult) -> None:
    d = r3.to_dict()
    s = json.dumps(d)
    assert '"ah_m"' in s
    assert len(d["nodes"]) == r3.nodes.shape[0]
    light = r3.to_dict(geometry=False)
    assert "nodes" not in light and light["av_m"] == r3.av_m


def test_projections_svg(r3: SimResult) -> None:
    views = projections_svg(r3)
    assert set(views) == {"plan", "profile", "front"}
    for name, svg in views.items():
        root = ET.fromstring(svg.split("\n", 1)[1])
        assert root.tag.endswith("svg"), name
        assert "AH =" in svg or "AV =" in svg
    assert "AV =" in views["profile"] and "AH =" in views["plan"]
    assert "AH =" in views["front"] and "AV =" in views["front"]


def test_validate_subset(result: DesignResult) -> None:
    v = validate(resolution=3, speeds_kn=[3.0], result=result)
    assert v.v_kn.tolist() == [3.0]
    assert set(v.errors) >= {"AH", "AV", "RA", "DP"}
    assert v.sim["DP"][0] == pytest.approx(result.doors.spread_m)
    table = markdown_table(v)
    assert "RA DynamiT" in table and "1331" in table
    assert "Rn diseño" in table


def test_simulate_from_spec_only(result: DesignResult) -> None:
    """Sin corrida del motor: aparejo genérico, DP obligatoria."""
    spec = result.case.net
    with pytest.raises(ValueError, match="door_spread_m"):
        simulate(spec, 3.0, resolution=3)
    r = simulate(spec, 3.0, resolution=3, door_spread_m=32.5, coarse_resolution=None)
    assert r.converged
    assert r.av_m > 0.5 and r.footrope_height_m == pytest.approx(0.0, abs=1e-6)
