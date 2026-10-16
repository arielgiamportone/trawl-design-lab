"""Optimización del diseño: escala de la red y velocidad de arrastre (Fase 6).

Variables: factor de escala ``s`` de la red (mismo mallero y materiales, ``s`` veces más mallas
por borde) y velocidad de arrastre ``v``. Objetivos: área barrida por hora, volumen filtrado por
hora o trabajo de remolque por m² barrido. Restricciones: reserva de tiro, red abierta, cable,
portón y rango de velocidad. Ver ``docs/20_optimizacion.md``.

Uso::

    from trawlkit.optimize import optimise
    res = optimise(case, objective="area", margin=0.1, seed=0)
    res.best.s, res.best.v_kn, res.best.area_rate_m2_h
"""

from trawlkit.optimize.evaluate import (
    OBJECTIVE_ALIASES,
    OBJECTIVES,
    Constraint,
    Curves,
    Evaluation,
    Evaluator,
    Limits,
    evaluate,
    speed_grid,
)
from trawlkit.optimize.scaling import scale_count, scale_door, scale_net
from trawlkit.optimize.search import (
    GridResult,
    OptimizationResult,
    grid_search,
    optimise,
    pareto_front,
)
from trawlkit.optimize.summary import summary_markdown

__all__ = [
    "OBJECTIVES",
    "OBJECTIVE_ALIASES",
    "Constraint",
    "Curves",
    "Evaluation",
    "Evaluator",
    "GridResult",
    "Limits",
    "OptimizationResult",
    "evaluate",
    "grid_search",
    "optimise",
    "pareto_front",
    "scale_count",
    "scale_door",
    "scale_net",
    "speed_grid",
    "summary_markdown",
]
