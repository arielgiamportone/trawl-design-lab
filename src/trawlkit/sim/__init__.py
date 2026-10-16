"""Simulación cuasiestática de la forma de la red remolcada (``trawlkit.sim``).

Modelo físico de paño, relingas, bridas y patentes en equilibrio bajo el arrastre del agua, el
peso, la flotación y el contacto con el fondo (ver :mod:`trawlkit.sim.mesh` y
:mod:`trawlkit.sim.solver`), validado contra DynamiT en :mod:`trawlkit.sim.validation`.

    from trawlkit.sim import simulate, sweep
    r = simulate(design_result, 3.0)      # SimResult: AH, AV, arrastre, forma...
"""

from trawlkit.sim.core import (
    DEFAULT_CN,
    DEFAULT_CT,
    DEFAULT_MU,
    DEFAULT_RESOLUTION,
    SimResult,
    rigging_from_result,
    rigging_from_spec,
    simulate,
    sweep,
)
from trawlkit.sim.mesh import NetModel, Rigging, build_model

__all__ = [
    "DEFAULT_CN",
    "DEFAULT_CT",
    "DEFAULT_MU",
    "DEFAULT_RESOLUTION",
    "NetModel",
    "Rigging",
    "SimResult",
    "build_model",
    "rigging_from_result",
    "rigging_from_spec",
    "simulate",
    "sweep",
]
