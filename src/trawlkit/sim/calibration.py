"""Calibración del simulador contra mediciones (DynamiT, ensayos o registros de sensores).

Ajusta algunos parámetros inciertos del simulador (coeficientes del hilo, polar del portón,
rozamiento) para que la simulación reproduzca observaciones: separación de portones, aberturas,
tiro o tensión del cable a una velocidad (y con una captura) dadas.

Método: mínimos cuadrados no lineales con Levenberg–Marquardt (Levenberg 1944; Marquardt 1963),
con jacobiano por diferencias finitas hacia adelante y parámetros acotados (se proyectan sobre
sus rangos). El residuo de cada observación es relativo, ``(sim − obs)/obs · peso``, así que se
mezclan magnitudes de distinta unidad. Cada evaluación simula los estados distintos (velocidad,
captura) arrancando de la última forma de cada uno, lo que la abarata.

Se informa el error cuadrático medio relativo antes y después, el error por observación y un
desvío aproximado de cada parámetro a partir de ``(JᵀJ)⁻¹`` (sólo orientativo: el modelo no es
lineal y los residuos no son independientes).
"""

from __future__ import annotations

import dataclasses
import math
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import numpy.typing as npt

from trawlkit.i18n import N_, t
from trawlkit.sim.core import DEFAULT_CN, DEFAULT_CT, CaseLike, SimResult, _resolve, simulate
from trawlkit.sim.mesh import NetModel, build_model
from trawlkit.sim.scenario import Scenario

FloatArray = npt.NDArray[np.float64]

#: Magnitudes observables: nombre → (etiqueta, unidad, función sobre el resultado).
QUANTITIES: dict[str, tuple[str, str, Callable[[SimResult], float]]] = {
    "door_spread_m": (N_("Separación de portones"), "m", lambda r: r.door_spread_m),
    "ah_m": (N_("Abertura horizontal"), "m", lambda r: r.ah_m),
    "av_m": (N_("Abertura vertical"), "m", lambda r: r.av_m),
    "headrope_height_m": (
        N_("Altura de la relinga superior"),
        "m",
        lambda r: r.headrope_height_m,
    ),
    "drag_kgf": (N_("Resistencia de la red"), "kgf", lambda r: r.drag_kgf),
    "towing_pull_kgf": (
        N_("Tiro en el buque"),
        "kgf",
        lambda r: r.towing_pull_kgf or r.drag_kgf,
    ),
    "warp_tension_kgf": (N_("Tensión del cable (portón)"), "kgf", lambda r: r.warp_tension_kgf),
}

#: Parámetros calibrables: nombre → (etiqueta, mínimo, máximo).
PARAMETERS: dict[str, tuple[str, float, float]] = {
    "cn": (N_("C_N del hilo"), 0.8, 2.0),
    "ct": (N_("C_T del hilo"), 0.01, 0.2),
    "door_cl_factor": (N_("Factor de C_L del portón"), 0.5, 1.5),
    "door_cd_factor": (N_("Factor de C_D del portón"), 0.5, 1.5),
    "mu_gear": (N_("μ tren–fondo"), 0.05, 1.2),
    "mu_door": (N_("μ portón–fondo"), 0.05, 1.2),
}


@dataclass(frozen=True)
class Observation:
    """Una medición: ``quantity`` = ``value`` a ``speed_kn`` con ``catch_kg`` en el copo."""

    quantity: str
    value: float
    speed_kn: float
    catch_kg: float = 0.0
    weight: float = 1.0
    source: str = ""

    def __post_init__(self) -> None:
        """Valida la magnitud y el valor."""
        if self.quantity not in QUANTITIES:
            raise ValueError(
                t(
                    "magnitud desconocida: {q!r} (use {names})",
                    q=self.quantity,
                    names=", ".join(QUANTITIES),
                )
            )
        if not self.value > 0:
            raise ValueError(t("el valor observado debe ser positivo"))
        if not 0.3 <= self.speed_kn <= 6.0:
            raise ValueError(t("speed_kn fuera de rango (0,3–6 kn)"))
        if self.catch_kg < 0 or self.weight <= 0:
            raise ValueError(t("catch_kg debe ser ≥ 0 y weight > 0"))

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclasses.asdict(self)


def dynamit_observations(
    speeds_kn: Sequence[float] = (2.0, 3.0, 4.0),
    quantities: Sequence[str] = ("door_spread_m", "ah_m", "av_m", "drag_kgf"),
) -> list[Observation]:
    """Observaciones de la simulación DynamiT de la red FAO A-3 estándar (red vacía)."""
    from trawlkit.sim.validation import DYNAMIT

    col = {"door_spread_m": "DP_m", "ah_m": "AH_m", "av_m": "AV_m", "drag_kgf": "RA_kg"}
    out = []
    for v in speeds_kn:
        if v not in DYNAMIT["v_kn"]:
            raise ValueError(t("DynamiT no tiene {v} kn", v=v))
        k = DYNAMIT["v_kn"].index(v)
        for q in quantities:
            out.append(Observation(q, float(DYNAMIT[col[q]][k]), float(v), source="DynamiT"))
    return out


@dataclass(frozen=True, eq=False)
class CalibrationResult:
    """Resultado de :func:`calibrate`."""

    params: tuple[str, ...]
    initial: FloatArray
    fitted: FloatArray
    std: FloatArray  # desvío aproximado (NaN si el jacobiano es singular)
    observations: tuple[Observation, ...]
    before: FloatArray  # simulación con los parámetros iniciales, por observación
    after: FloatArray
    rmse_before: float  # error cuadrático medio relativo [%]
    rmse_after: float
    evaluations: int
    history: list[dict[str, Any]] = field(default_factory=list)
    runtime_s: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "params": [
                {
                    "name": p,
                    "label": t(PARAMETERS[p][0]),
                    "initial": float(self.initial[i]),
                    "fitted": float(self.fitted[i]),
                    "std": None if not math.isfinite(self.std[i]) else float(self.std[i]),
                    "low": PARAMETERS[p][1],
                    "high": PARAMETERS[p][2],
                }
                for i, p in enumerate(self.params)
            ],
            "observations": [
                {
                    **o.to_dict(),
                    "label": t(QUANTITIES[o.quantity][0]),
                    "unit": QUANTITIES[o.quantity][1],
                    "before": float(self.before[k]),
                    "after": float(self.after[k]),
                    "error_before_pct": float(100 * (self.before[k] / o.value - 1)),
                    "error_after_pct": float(100 * (self.after[k] / o.value - 1)),
                }
                for k, o in enumerate(self.observations)
            ],
            "rmse_before_pct": self.rmse_before,
            "rmse_after_pct": self.rmse_after,
            "evaluations": self.evaluations,
            "history": self.history,
            "runtime_s": self.runtime_s,
        }


def _initial(name: str, scenario: Scenario, cn: float, ct: float) -> float:
    if name == "cn":
        return cn
    if name == "ct":
        return ct
    if name in ("door_cl_factor", "door_cd_factor"):
        return float(getattr(scenario, name))
    mu_g, mu_d = scenario.friction(0.5)
    return mu_g if name == "mu_gear" else mu_d


def calibrate(
    case: CaseLike,
    observations: Sequence[Observation],
    params: Sequence[str] = ("cn", "door_cl_factor"),
    *,
    scenario: Scenario | None = None,
    initial: dict[str, float] | None = None,
    resolution: int = 3,
    cn: float = DEFAULT_CN,
    ct: float = DEFAULT_CT,
    max_evals: int = 30,
    rel_step: float = 0.04,
    tol: float = 1e-3,
) -> CalibrationResult:
    """Ajusta ``params`` para reproducir ``observations`` (ver el docstring del módulo).

    ``max_evals`` limita las evaluaciones del modelo (cada una simula todos los estados
    observados). El ajuste se detiene cuando el error deja de bajar más de ``tol`` (relativo).
    """
    t0 = time.perf_counter()
    if not observations:
        raise ValueError(t("hacen falta observaciones"))
    names = tuple(params)
    if not names:
        raise ValueError(t("hay que elegir al menos un parámetro"))
    for p in names:
        if p not in PARAMETERS:
            raise ValueError(
                t(
                    "parámetro desconocido: {p!r} (use {names})",
                    p=p,
                    names=", ".join(PARAMETERS),
                )
            )
    if len(set(names)) != len(names):
        raise ValueError(t("parámetros repetidos"))
    obs = tuple(observations)
    sc = scenario or Scenario()
    spec, rig, result = _resolve(case, None)
    base_case = result if result is not None else case
    model: NetModel | None = build_model(
        spec, rig, resolution=resolution, coupled_doors=sc.coupled_doors
    )
    if sc.warp_length_m is not None and sc.coupled_doors:
        model = None
    states = sorted({(o.speed_kn, o.catch_kg) for o in obs})
    lo = np.array([PARAMETERS[p][1] for p in names])
    hi = np.array([PARAMETERS[p][2] for p in names])
    x0 = np.array([(initial or {}).get(p, _initial(p, sc, cn, ct)) for p in names], dtype=float)
    x0 = np.clip(x0, lo, hi)
    shapes: dict[tuple[float, float], FloatArray] = {}
    values = np.array([o.value for o in obs])
    weights = np.array([o.weight for o in obs])
    n_eval = 0

    def simulate_all(x: FloatArray) -> FloatArray:
        nonlocal n_eval
        n_eval += 1
        cn_x, ct_x = cn, ct
        changes: dict[str, Any] = {}
        for name, v in zip(names, x, strict=True):
            if name == "cn":
                cn_x = float(v)
            elif name == "ct":
                ct_x = float(v)
            else:
                changes[name] = float(v)
        sims: dict[tuple[float, float], SimResult] = {}
        for st in states:
            sc_st = dataclasses.replace(sc, catch_kg=st[1], **changes)
            prev = shapes.get(st)
            r = simulate(
                base_case,
                st[0],
                resolution=resolution,
                cn=cn_x,
                ct=ct_x,
                scenario=sc_st,
                model=model,
                x_init=prev,
                coarse_resolution=None,
            )
            shapes[st] = r.nodes
            sims[st] = r
        return np.array(
            [QUANTITIES[o.quantity][2](sims[(o.speed_kn, o.catch_kg)]) for o in obs], dtype=float
        )

    def residual(sim: FloatArray) -> FloatArray:
        return np.asarray((sim / values - 1.0) * weights, dtype=float)

    def rmse(sim: FloatArray) -> float:
        return float(100 * np.sqrt(np.mean((sim / values - 1.0) ** 2)))

    x = x0.copy()
    sim0 = simulate_all(x)
    before = sim0.copy()
    r = residual(sim0)
    cost = float(r @ r)
    lam = 1e-2
    history = [{"x": x.tolist(), "rmse_pct": rmse(sim0), "lambda": lam}]
    jac = np.zeros((len(obs), len(names)))
    best_sim = sim0
    while n_eval + len(names) + 1 <= max_evals:
        # Jacobiano por diferencias hacia adelante (hacia adentro del rango en el borde).
        for j in range(len(names)):
            h = rel_step * max(abs(x[j]), 0.05)
            if x[j] + h > hi[j]:
                h = -h
            xj = x.copy()
            xj[j] += h
            jac[:, j] = (residual(simulate_all(xj)) - r) / h
        jtj = jac.T @ jac
        g = jac.T @ r
        improved = False
        while n_eval < max_evals:
            step = np.linalg.solve(jtj + lam * np.diag(np.maximum(np.diag(jtj), 1e-12)), -g)
            x_new = np.clip(x + step, lo, hi)
            sim_new = simulate_all(x_new)
            r_new = residual(sim_new)
            cost_new = float(r_new @ r_new)
            if cost_new < cost:
                rel = (cost - cost_new) / max(cost, 1e-15)
                x, r, cost, best_sim = x_new, r_new, cost_new, sim_new
                lam = max(lam / 3.0, 1e-6)
                improved = True
                history.append({"x": x.tolist(), "rmse_pct": rmse(sim_new), "lambda": lam})
                break
            lam *= 4.0
            if lam > 1e4:
                break
        if not improved or rel < tol:
            break
    std = np.full(len(names), np.nan)
    try:
        dof = max(len(obs) - len(names), 1)
        cov = np.linalg.inv(jac.T @ jac) * (cost / dof)
        std = np.sqrt(np.maximum(np.diag(cov), 0.0))
    except np.linalg.LinAlgError:
        pass
    return CalibrationResult(
        params=names,
        initial=x0,
        fitted=x,
        std=std,
        observations=obs,
        before=before,
        after=best_sim,
        rmse_before=rmse(before),
        rmse_after=rmse(best_sim),
        evaluations=n_eval,
        history=history,
        runtime_s=time.perf_counter() - t0,
    )
