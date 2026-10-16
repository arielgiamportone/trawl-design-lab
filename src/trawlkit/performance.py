"""Ventana de velocidad viable: tiro disponible (FT) frente a resistencia total.

El Excel compara, para cada velocidad de 1 a 5 nudos, el tiro disponible por propulsor
(``'Potencia Disponible Arrastre OK'!L11:O19``) con la resistencia total del sistema
(``'Cables de Remolque'!H118:I126`` = RN + RB + Rw, más ROB en modo corregido) y deja al lector
la conclusión. Aquí se formaliza: la red es remolcable a una velocidad cuando ``FT(v) >= R(v)``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class SpeedWindow:
    """Resultado de la comparación FT(v) vs R(v) sobre un vector de velocidades."""

    speeds_kn: FloatArray
    available_kgf: FloatArray
    demand_kgf: FloatArray
    margin_kgf: FloatArray = field(repr=False)
    feasible: NDArray[np.bool_] = field(repr=False)
    max_speed_kn: float | None
    """Velocidad máxima remolcable (interpolación lineal del cruce FT = R), o None si no hay cruce
    y ninguna velocidad es viable."""

    @property
    def feasible_speeds_kn(self) -> list[float]:
        """Velocidades del vector con margen no negativo."""
        return [float(v) for v in self.speeds_kn[self.feasible]]

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "speeds_kn": self.speeds_kn.tolist(),
            "available_kgf": self.available_kgf.tolist(),
            "demand_kgf": self.demand_kgf.tolist(),
            "margin_kgf": self.margin_kgf.tolist(),
            "feasible": self.feasible.tolist(),
            "feasible_speeds_kn": self.feasible_speeds_kn,
            "max_speed_kn": self.max_speed_kn,
        }


def speed_window(
    speeds_kn: Any,
    available_kgf: Any,
    demand_kgf: Any,
) -> SpeedWindow:
    """Compara tiro disponible y resistencia total sobre un vector de velocidades.

    ``max_speed_kn`` es la velocidad del primer cruce de ``FT - R`` de positivo a negativo,
    interpolada linealmente entre los dos puntos del vector; si todo el vector es viable es la
    última velocidad; si nada es viable es ``None``.
    """
    v = np.asarray(speeds_kn, dtype=float)
    ft = np.asarray(available_kgf, dtype=float)
    r = np.asarray(demand_kgf, dtype=float)
    if not (v.shape == ft.shape == r.shape):
        raise ValueError("speeds_kn, available_kgf y demand_kgf deben tener la misma forma")
    if v.ndim != 1 or v.size == 0:
        raise ValueError("se espera un vector no vacío de velocidades")
    margin = ft - r
    feasible = margin >= 0
    max_speed: float | None
    if not feasible.any():
        max_speed = None
    elif feasible.all():
        max_speed = float(v[-1])
    else:
        idx = int(np.argmax(~feasible))  # primera velocidad no viable
        if idx == 0:
            max_speed = None
        else:
            v0, v1 = v[idx - 1], v[idx]
            m0, m1 = margin[idx - 1], margin[idx]
            max_speed = float(v0 + (v1 - v0) * m0 / (m0 - m1))
    return SpeedWindow(
        speeds_kn=v,
        available_kgf=ft,
        demand_kgf=r,
        margin_kgf=margin,
        feasible=feasible,
        max_speed_kn=max_speed,
    )


def total_demand_kgf(
    net_kgf: Any,
    floats_kgf: Any = 0.0,
    warps_kgf: Any = 0.0,
    doors_kgf: Any = 0.0,
) -> FloatArray:
    """Resistencia total a remolcar: RN + RB + Rw + ROB (todas en kgf, mismas formas)."""
    out: FloatArray = (
        np.asarray(net_kgf, dtype=float)
        + np.asarray(floats_kgf, dtype=float)
        + np.asarray(warps_kgf, dtype=float)
        + np.asarray(doors_kgf, dtype=float)
    )
    return out
