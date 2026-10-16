"""Pruebas lentas del simulador: refinamiento de malla y barrido completo 1–5 kn.

Se ejecutan con ``TRAWLKIT_SIM_SLOW=1 uv run pytest tests/test_sim_slow.py`` (varios minutos).
"""

from __future__ import annotations

import os

import numpy as np
import pytest

from trawlkit.compat import Compat
from trawlkit.model import DesignResult, run
from trawlkit.sim import simulate
from trawlkit.sim.validation import DYNAMIT, speed_exponent, standard_case, validate

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        os.environ.get("TRAWLKIT_SIM_SLOW") != "1",
        reason="simulación lenta: activar con TRAWLKIT_SIM_SLOW=1",
    ),
]


@pytest.fixture(scope="module")
def result() -> DesignResult:
    return run(standard_case(compat=Compat.CORRECTED))


def test_mesh_refinement(result: DesignResult) -> None:
    """Refinar la malla (10 → 12) cambia AH, AV y el arrastre menos de un 10 %.

    AH y el arrastre convergen enseguida (< 1 % entre las resoluciones 6 y 12); AV converge más
    lento: 1,72 / 1,63 / 1,48 / 1,40 m a 3 kn con resolución 6 / 8 / 10 / 12.
    """
    coarse = simulate(result, 3.0, resolution=10)
    fine = simulate(result, 3.0, resolution=12)
    for attr in ("ah_m", "av_m", "drag_kgf"):
        a, b = getattr(coarse, attr), getattr(fine, attr)
        assert abs(a - b) / b < 0.10, (attr, a, b)
    for attr in ("ah_m", "drag_kgf"):
        assert abs(getattr(coarse, attr) / getattr(fine, attr) - 1.0) < 0.02


def test_full_sweep_trends(result: DesignResult) -> None:
    v = validate(result=result)
    av = v.sim["AV"]
    ra = v.sim["RA"]
    assert np.all(np.diff(av) < 0)
    assert np.all(np.diff(ra) > 0)
    assert 1.4 < speed_exponent(v.v_kn, ra) < 2.0
    assert np.all(v.sim["residual"] < 0.05)
    assert v.v_kn.tolist() == list(DYNAMIT["v_kn"])
