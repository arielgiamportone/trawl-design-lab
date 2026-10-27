"""Polar dinámica de los portones acoplados (Fase 19.3).

Con los portones acoplados (``Scenario.coupled_doors``) cada portón es un nodo libre con la
sustentación y el arrastre de su polar. Hasta la Fase 19.2 el C_L y el C_D eran los del ángulo de
ataque del caso, fijos. Con ``Scenario.dynamic_door_polar`` el ángulo de ataque sale de la forma
resuelta y el C_L y el C_D se leen de la polar completa a ese ángulo (interpolación lineal).

Ángulo de ataque: método simplificado de Seafish/IFREMER/DIFTA (1993, App. III-13/14, PDF
pp. 127-128). Con el centro de presión ``t_p`` constante y la resultante hidrodinámica normal al
portón, el portón está en equilibrio cuando las rectas del cable y de la patente (brida) se
cortan sobre la línea de acción de la resultante::

    n_w + (t_w − t_p)·tan(α + β) = n_b + (t_b − t_p)·tan(α − γ),

con β y γ los ángulos del cable y de la patente con la dirección del agua en el plano horizontal
(hacia el eje de la red) y (t, n) los puntos de amarre del cable y de la patente en largos de
portón desde el borde de ataque. Los valores son los del ejemplo de Seafish para el «Reference
Vee» (t_w = 0,26, t_b = 0,85, n_b = −0,06, t_p = C_P = 0,42; :data:`SEAFISH_RIG`). El amarre del
cable ``n_w`` se calibra para que, con los ángulos de la forma de diseño del modelo (el portón a
la separación del motor y el cable recto hasta la pasteca: ``NetModel.x0``), el ángulo sea el del
caso: el aparejo de las patas de gallo se supone hecho para trabajar a ese ángulo. Así el método
aporta la *sensibilidad* del ángulo a la geometría y la corrección de +4° del App. III-11 (los
cálculos dan unos 4° más que en el mar) se cancela.

Estabilidad: el ángulo se actualiza en cada control de convergencia de la relajación con un
factor de relajación ``ω`` y un paso máximo, y se recorta al rango medido de la polar (no se
extrapola).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]

#: Amarres del cable (t_w), de la patente (t_b, n_b) y centro de presión (t_p) en largos de
#: portón: ejemplo del «Reference Vee» de Seafish 1993 (App. III-14, PDF p. 128). El ejemplo da
#: además n_w = 0,24; aquí n_w se calibra (ver el docstring del módulo).
SEAFISH_RIG: dict[str, float] = {"t_w": 0.26, "t_b": 0.85, "n_b": -0.06, "t_p": 0.42}

#: Factor de relajación y paso máximo por actualización [°] del ángulo de ataque.
DOOR_RELAX = 0.3
DOOR_MAX_STEP_DEG = 1.0


def rig_angles_deg(
    x: FloatArray, door: int, warp_next: int, sweep_next: int
) -> tuple[float, float]:
    """(β, γ): ángulos del cable y de la patente con el agua en el plano horizontal [°].

    ``warp_next`` es el primer nodo del cable desde el portón y ``sweep_next`` el otro extremo
    de la patente; ambos ángulos son positivos hacia el eje de la red (y = 0).
    """
    sgn = 1.0 if x[door, 1] >= 0 else -1.0
    dw = x[warp_next] - x[door]
    ds = x[sweep_next] - x[door]
    beta = math.degrees(math.atan2(-sgn * dw[1], -dw[0]))
    gamma = math.degrees(math.atan2(-sgn * ds[1], ds[0]))
    return beta, gamma


def _residual(alpha: float, beta: float, gamma: float, n_w: float) -> float:
    r = SEAFISH_RIG
    a = math.radians(alpha)
    y1 = n_w + (r["t_w"] - r["t_p"]) * math.tan(a + math.radians(beta))
    y2 = r["n_b"] + (r["t_b"] - r["t_p"]) * math.tan(a - math.radians(gamma))
    return y1 - y2


def calibrate_nw(alpha: float, beta: float, gamma: float) -> float:
    """Amarre del cable ``n_w`` con el que el método da ``alpha`` para (β, γ)."""
    return -_residual(alpha, beta, gamma, 0.0)


def seafish_attack_angle(beta: float, gamma: float, n_w: float) -> float:
    """Ángulo de ataque [°] del método simplificado de Seafish (bisección en 0–70°).

    El primer miembro decrece y el segundo crece con α: hay una sola raíz si cambian de signo;
    si no, se devuelve el extremo más cercano.
    """
    lo, hi = 0.0, 70.0
    flo, fhi = _residual(lo, beta, gamma, n_w), _residual(hi, beta, gamma, n_w)
    if flo * fhi > 0:
        return lo if abs(flo) < abs(fhi) else hi
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        fm = _residual(mid, beta, gamma, n_w)
        if flo * fm <= 0:
            hi = mid
        else:
            lo, flo = mid, fm
    return 0.5 * (lo + hi)


@dataclass
class DoorDynamics:
    """Estado de la polar dinámica de los portones durante la relajación."""

    polar: FloatArray  # (n, 3): ángulo, CL, CD
    n_w: float
    angle_deg: float
    angle_case_deg: float
    beta_ref_deg: float
    gamma_ref_deg: float
    cl_factor: float = 1.0
    cd_factor: float = 1.0
    beta_deg: float = 0.0
    gamma_deg: float = 0.0
    target_deg: float = 0.0
    clamped: bool = False
    updates: int = 0
    history: list[float] = field(default_factory=list)

    @property
    def range_deg(self) -> tuple[float, float]:
        """Rango medido de la polar [°]."""
        return float(self.polar[0, 0]), float(self.polar[-1, 0])

    def coefficients(self, angle: float | None = None) -> tuple[float, float]:
        """(CL, CD) a ``angle`` (o al ángulo actual), con los factores del escenario."""
        a = self.angle_deg if angle is None else angle
        cl = float(np.interp(a, self.polar[:, 0], self.polar[:, 1]))
        cd = float(np.interp(a, self.polar[:, 0], self.polar[:, 2]))
        return cl * self.cl_factor, cd * self.cd_factor

    def step(self, beta: float, gamma: float) -> float:
        """Nuevo ángulo con la geometría (β, γ): relajado, con paso máximo y recortado."""
        self.beta_deg, self.gamma_deg = beta, gamma
        target = seafish_attack_angle(beta, gamma, self.n_w)
        self.target_deg = target
        lo, hi = self.range_deg
        self.clamped = not lo <= target <= hi
        delta = DOOR_RELAX * (min(max(target, lo), hi) - self.angle_deg)
        delta = max(-DOOR_MAX_STEP_DEG, min(DOOR_MAX_STEP_DEG, delta))
        self.angle_deg = min(max(self.angle_deg + delta, lo), hi)
        self.updates += 1
        self.history.append(self.angle_deg)
        return self.angle_deg

    def to_dict(self) -> dict[str, Any]:
        """Estado final serializable."""
        cl, cd = self.coefficients()
        return {
            "mode": "dynamic",
            "angle_deg": self.angle_deg,
            "angle_case_deg": self.angle_case_deg,
            "target_deg": self.target_deg,
            "cl": cl,
            "cd": cd,
            "beta_deg": self.beta_deg,
            "gamma_deg": self.gamma_deg,
            "beta_ref_deg": self.beta_ref_deg,
            "gamma_ref_deg": self.gamma_ref_deg,
            "clamped": self.clamped,
            "polar_range_deg": list(self.range_deg),
            "updates": self.updates,
        }


__all__ = [
    "DOOR_MAX_STEP_DEG",
    "DOOR_RELAX",
    "SEAFISH_RIG",
    "DoorDynamics",
    "calibrate_nw",
    "rig_angles_deg",
    "seafish_attack_angle",
]
