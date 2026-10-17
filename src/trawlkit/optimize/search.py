"""Búsqueda en malla, frente de Pareto y optimización por evolución diferencial sobre ``(s, v)``."""

from __future__ import annotations

import dataclasses
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from trawlkit.compat import Compat
from trawlkit.io import Door, PropellerType
from trawlkit.model import DesignCase
from trawlkit.optimize.evaluate import (
    OBJECTIVE_ALIASES,
    OBJECTIVES,
    Evaluation,
    Evaluator,
    Limits,
)

FloatArray = NDArray[np.float64]

#: Peso de la penalización (violación relativa) frente al objetivo normalizado.
PENALTY_WEIGHT = 100.0
#: Paso con el que el optimizador redondea la escala (reutiliza corridas del motor).
S_STEP = 0.005


def _objective_key(name: str) -> str:
    key = OBJECTIVE_ALIASES.get(name, name)
    if key not in OBJECTIVES:
        valid = sorted(set(OBJECTIVE_ALIASES) | set(OBJECTIVES))
        raise ValueError(f"objetivo desconocido: {name!r} (use {valid})")
    return key


@dataclass(frozen=True)
class GridResult:
    """Matriz de evaluaciones: ``evaluations[i][j]`` es la escala ``s_values[i]`` a ``v_values[j]``.

    Las filas recorren las escalas y las columnas las velocidades.
    """

    s_values: tuple[float, ...]
    v_values: tuple[float, ...]
    evaluations: tuple[tuple[Evaluation, ...], ...]

    def flat(self) -> list[Evaluation]:
        """Todas las evaluaciones en una lista (por escala y luego por velocidad)."""
        return [e for row in self.evaluations for e in row]

    def matrix(self, attr: str) -> FloatArray:
        """Matriz ``len(s) × len(v)`` de un atributo numérico de :class:`Evaluation`."""
        return np.array(
            [[float(getattr(e, attr)) for e in row] for row in self.evaluations], dtype=float
        )

    @property
    def feasible(self) -> NDArray[np.bool_]:
        """Máscara de factibilidad ``len(s) × len(v)``."""
        return np.array([[e.feasible for e in row] for row in self.evaluations], dtype=bool)

    def to_dict(self, include_evaluations: bool = False) -> dict[str, Any]:
        """Matrices de las magnitudes principales (y, opcionalmente, cada evaluación)."""
        out: dict[str, Any] = {
            "s_values": list(self.s_values),
            "v_values": list(self.v_values),
            "feasible": self.feasible.tolist(),
        }
        for attr in (
            "area_rate_m2_h",
            "volume_rate_m3_h",
            "energy_kgf_m_per_m2",
            "ah_m",
            "av_m",
            "demand_kgf",
            "available_kgf",
            "thrust_margin",
            "penalty",
        ):
            out[attr] = self.matrix(attr).tolist()
        if include_evaluations:
            out["evaluations"] = [[e.to_dict() for e in row] for row in self.evaluations]
        return out


def _make_evaluator(
    base_case: DesignCase,
    door_id: str | Door | None,
    door_angle: float | None,
    propeller: PropellerType | str | None,
    limits: Limits | None,
    compat: Compat | str,
    s_step: float | None = None,
) -> Evaluator:
    return Evaluator(
        base_case,
        door=door_id,
        door_angle=door_angle,
        propeller=propeller,
        compat=compat,
        limits=limits,
        s_step=s_step,
    )


def _grid(ev: Evaluator, s_values: Sequence[float], v_values: Sequence[float]) -> GridResult:
    rows = []
    for s in s_values:
        c = ev.curves(float(s))  # una corrida del motor por escala, para todas las velocidades
        rows.append(tuple(ev.from_curves(c, float(v)) for v in v_values))
    return GridResult(
        s_values=tuple(float(s) for s in s_values),
        v_values=tuple(float(v) for v in v_values),
        evaluations=tuple(rows),
    )


def grid_search(
    base_case: DesignCase,
    s_values: Sequence[float],
    v_values: Sequence[float],
    *,
    door_id: str | Door | None = None,
    door_angle: float | None = None,
    propeller: PropellerType | str | None = None,
    limits: Limits | None = None,
    compat: Compat | str = Compat.CORRECTED,
) -> GridResult:
    """Evalúa la malla ``s_values × v_values`` con una corrida del motor por escala."""
    if not len(s_values) or not len(v_values):
        raise ValueError("s_values y v_values no pueden estar vacíos")
    ev = _make_evaluator(base_case, door_id, door_angle, propeller, limits, compat)
    return _grid(ev, s_values, v_values)


def pareto_front(
    evaluations: Sequence[Evaluation],
    objectives: Sequence[str] = ("area_rate", "energy"),
    *,
    feasible_only: bool = True,
) -> list[Evaluation]:
    """Evaluaciones no dominadas (filtro exacto) según ``objectives``.

    ``area_rate`` y ``volume_rate`` se maximizan y ``energy`` se minimiza. Un punto domina a otro
    si no es peor en ningún objetivo y es mejor en al menos uno; de los puntos con objetivos
    idénticos se conserva el primero. El frente se devuelve ordenado por el primer objetivo, del
    mejor al peor.
    """
    keys = [_objective_key(o) for o in objectives]
    if not keys:
        raise ValueError("hace falta al menos un objetivo")
    pts = [e for e in evaluations if e.feasible or not feasible_only]
    if not pts:
        return []
    # Todo a maximizar.
    f = np.array([[OBJECTIVES[k][1] * e.objective(k) for k in keys] for e in pts], dtype=float)
    keep: list[int] = []
    for i in range(len(pts)):
        ge = np.all(f >= f[i], axis=1)
        gt = np.any(f > f[i], axis=1)
        if np.any(ge & gt):
            continue  # dominado
        if any(np.array_equal(f[i], f[j]) for j in keep):
            continue  # duplicado
        keep.append(i)
    keep.sort(key=lambda i: -f[i, 0])
    return [pts[i] for i in keep]


@dataclass(frozen=True)
class OptimizationResult:
    """Resultado de :func:`optimise`."""

    best: Evaluation
    """Mejor diseño factible (o el de menor violación si no hay ninguno factible)."""
    grid: GridResult
    pareto: tuple[Evaluation, ...]
    """Frente de Pareto área barrida/h vs energía sobre la malla (y el punto refinado)."""
    objective: str
    settings: dict[str, Any]
    feasible: bool
    grid_best: Evaluation | None
    """Mejor punto factible de la malla antes de refinar."""
    refine: dict[str, Any] | None
    """Datos de la evolución diferencial (``None`` si no se refinó)."""
    runtime_s: float
    engine_runs: int

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable (la malla como matrices)."""
        return {
            "objective": self.objective,
            "feasible": self.feasible,
            "best": self.best.to_dict(),
            "grid_best": None if self.grid_best is None else self.grid_best.to_dict(),
            "pareto": [e.to_dict() for e in self.pareto],
            "grid": self.grid.to_dict(),
            "settings": self.settings,
            "refine": self.refine,
            "runtime_s": self.runtime_s,
            "engine_runs": self.engine_runs,
        }


def _score(e: Evaluation, key: str, scale: float) -> float:
    """Función a minimizar: −sentido·objetivo/escala + peso·violación."""
    sense = OBJECTIVES[key][1]
    return -sense * e.objective(key) / scale + PENALTY_WEIGHT * e.penalty


def _better(a: Evaluation, b: Evaluation | None, key: str) -> bool:
    """Indica si ``a`` es mejor que ``b`` (factible primero, luego violación y objetivo)."""
    if b is None:
        return True
    if a.feasible != b.feasible:
        return a.feasible
    if not a.feasible and abs(a.penalty - b.penalty) > 1e-12:
        return a.penalty < b.penalty
    sense = OBJECTIVES[key][1]
    return sense * a.objective(key) > sense * b.objective(key)


def _local_search(
    ev: Any,
    seeds: tuple[Evaluation | None, ...],
    key: str,
    s_bounds: tuple[float, float],
    v_bounds: tuple[float, float],
    s_radius: float = 0.04,
    v_radius: float = 0.3,
    v_step: float = 0.01,
) -> Evaluation | None:
    """Mejor punto factible en una vecindad fina (paso S_STEP en s, 0.01 kn en v) de ``seeds``."""
    best: Evaluation | None = None
    for seed_e in seeds:
        if seed_e is None:
            continue
        s_vals = np.arange(
            max(s_bounds[0], seed_e.s - s_radius),
            min(s_bounds[1], seed_e.s + s_radius) + 1e-9,
            S_STEP,
        )
        v_vals = np.arange(
            max(v_bounds[0], seed_e.v_kn - v_radius),
            min(v_bounds[1], seed_e.v_kn + v_radius) + 1e-9,
            v_step,
        )
        for s_i in np.round(s_vals, 6):
            for v_i in np.round(v_vals, 6):
                e = ev.at(float(s_i), float(v_i))
                if e.feasible and _better(e, best, key):
                    best = e
    return best


def optimise(
    base_case: DesignCase,
    objective: str = "area",
    bounds: tuple[tuple[float, float], tuple[float, float]] = ((0.6, 1.4), (1.5, 4.0)),
    margin: float = 0.1,
    seed: int | None = 0,
    *,
    grid: tuple[int, int] = (17, 11),
    refine: bool = True,
    door_id: str | Door | None = None,
    door_angle: float | None = None,
    propeller: PropellerType | str | None = None,
    limits: Limits | None = None,
    compat: Compat | str = Compat.CORRECTED,
    maxiter: int = 100,
    popsize: int = 20,
    pareto_objectives: Sequence[str] = ("area_rate", "energy"),
) -> OptimizationResult:
    """Optimiza la escala de la red ``s`` y la velocidad ``v`` para un objetivo.

    1. Malla ``grid = (n_s, n_v)`` sobre ``bounds = ((s_min, s_max), (v_min, v_max))``: una corrida
       del motor por escala.
    2. Si ``refine``, :func:`scipy.optimize.differential_evolution` sobre ``(s, v)`` con
       penalización de las restricciones, sembrada con el mejor punto de la malla (``x0``) y con
       ``seed`` para que sea reproducible. La escala se redondea a 0,005.
    3. ``best`` es el mejor punto factible entre la malla y el refinado.

    ``objective``: ``"area"`` (máx. área barrida por hora), ``"volume"`` (máx. volumen filtrado
    por hora) o ``"energy"`` (mín. R_T/AH). ``margin`` es la reserva de tiro (si se pasa
    ``limits`` se usa la de ``limits``). Los límites de velocidad de ``bounds`` son también los de
    la restricción de velocidad.
    """
    t0 = time.perf_counter()
    key = _objective_key(objective)
    (s_lo, s_hi), (v_lo, v_hi) = bounds
    if not 0 < s_lo < s_hi:
        raise ValueError("bounds de s: se requiere 0 < s_min < s_max")
    if not 0 < v_lo < v_hi:
        raise ValueError("bounds de v: se requiere 0 < v_min < v_max")
    n_s, n_v = grid
    if n_s < 2 or n_v < 2:
        raise ValueError("la malla necesita al menos 2 × 2 puntos")
    base_limits = limits or Limits(margin=margin)
    lim = dataclasses.replace(base_limits, v_min_kn=float(v_lo), v_max_kn=float(v_hi))
    ev = _make_evaluator(base_case, door_id, door_angle, propeller, lim, compat, S_STEP)
    s_values = np.round(np.linspace(s_lo, s_hi, n_s), 6)
    v_values = np.round(np.linspace(v_lo, v_hi, n_v), 6)
    gres = _grid(ev, [ev.quantise(float(x)) for x in s_values], [float(x) for x in v_values])
    flat = gres.flat()

    grid_best: Evaluation | None = None
    for e in flat:
        if e.feasible and _better(e, grid_best, key):
            grid_best = e
    best = grid_best
    if best is None:
        for e in flat:
            if _better(e, best, key):
                best = e
    assert best is not None
    refined: Evaluation | None = None
    refine_info: dict[str, Any] | None = None
    if refine:
        try:
            from scipy.optimize import differential_evolution
        except ImportError as exc:  # pragma: no cover - depende del entorno
            raise RuntimeError(
                'la optimización necesita scipy: pip install "trawlkit[optimize]"'
            ) from exc
        scale = abs(best.objective(key)) or 1.0

        def fun(x: NDArray[np.float64]) -> float:
            return _score(ev.at(float(x[0]), float(x[1])), key, scale)

        start = best
        x0 = np.array([np.clip(start.s, s_lo, s_hi), np.clip(start.v_kn, v_lo, v_hi)], dtype=float)
        res = differential_evolution(
            fun,
            bounds=[(s_lo, s_hi), (v_lo, v_hi)],
            x0=x0,
            seed=seed,
            maxiter=maxiter,
            popsize=popsize,
            tol=1e-9,
            mutation=(0.5, 1.0),
            recombination=0.7,
            polish=False,
            init="latinhypercube",
            updating="immediate",
            workers=1,
        )
        refined = ev.at(float(res.x[0]), float(res.x[1]))
        refine_info = {
            "method": "scipy.optimize.differential_evolution",
            "x": [refined.s, refined.v_kn],
            "fun": float(res.fun),
            "nfev": int(res.nfev),
            "nit": int(res.nit),
            "success": bool(res.success),
            "message": str(res.message),
            "seed": seed,
            "maxiter": maxiter,
            "popsize": popsize,
            "s_step": S_STEP,
            "penalty_weight": PENALTY_WEIGHT,
        }
        if _better(refined, best, key):
            best = refined
        # Refinamiento local determinista: el óptimo suele quedar en una esquina de la región
        # factible (p. ej. s mínima y la mayor velocidad remolcable), donde la penalización hace
        # que la evolución diferencial no siempre llegue. Se barre una vecindad fina alrededor de
        # los mejores puntos (malla y DE) y se conserva el mejor factible.
        local = _local_search(ev, (best, grid_best, refined), key, (s_lo, s_hi), (v_lo, v_hi))
        if local is not None and _better(local, best, key):
            best = local
        refine_info["local_search"] = None if local is None else [local.s, local.v_kn]
    pts = flat + ([refined] if refined is not None else [])
    pareto = tuple(pareto_front(pts, pareto_objectives))
    settings = {
        "objective": key,
        "bounds": {"s": [float(s_lo), float(s_hi)], "v_kn": [float(v_lo), float(v_hi)]},
        "grid": {"n_s": n_s, "n_v": n_v},
        "limits": lim.to_dict(),
        "refine": refine,
        "seed": seed,
        "compat": Compat(compat).value,
        "vessel_id": ev.case.vessel.id,
        "door_id": ev.case.door.id,
        "door_attack_angle_deg": ev.case.door_attack_angle_deg,
        "propeller": ev.case.ft_propeller.value,
        "net_id": ev.case.net.id,
        "pareto_objectives": list(pareto_objectives),
    }
    return OptimizationResult(
        best=best,
        grid=gres,
        pareto=pareto,
        objective=key,
        settings=settings,
        feasible=best.feasible,
        grid_best=grid_best,
        refine=refine_info,
        runtime_s=time.perf_counter() - t0,
        engine_runs=ev.runs,
    )


__all__ = [
    "PENALTY_WEIGHT",
    "S_STEP",
    "GridResult",
    "OptimizationResult",
    "grid_search",
    "optimise",
    "pareto_front",
]
