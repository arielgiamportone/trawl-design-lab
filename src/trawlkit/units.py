"""Registro de unidades compartido (pint) y conversiones usadas en todo el motor.

Convenciones del modelo original que se conservan como constantes nombradas:

* velocidad de arrastre en nudos; internamente se trabaja en m/s (1 kn = 0.5144 m/s);
* fuerzas en kgf (el Excel usa kgf y toneladas-fuerza); internamente N;
* potencia en HP métrico (1 HP = 0.745 kW en el Excel; aquí 0.7355 kW, hp métrico exacto).
"""

from __future__ import annotations

import pint

ureg = pint.UnitRegistry()
ureg.formatter.default_format = "~P"
Q_ = ureg.Quantity

KNOT_TO_MS: float = 0.5144  # valor usado en el Excel (B272)
KGF_TO_N: float = 9.80665
RHO_SEAWATER: float = 1024.0  # kg/m³ ('Mecánica de la Red'!O127)
RHO_FRESHWATER: float = 1000.0
G: float = 9.81  # m/s² ('Mecánica de la Red'!O129)
HP_TO_KW_EXCEL: float = 0.745  # factor usado en el Excel
HP_TO_KW: float = 0.7355  # hp métrico


def knots_to_ms(v_kn: float) -> float:
    """Convierte nudos a m/s con el factor del modelo original."""
    return v_kn * KNOT_TO_MS


def ms_to_knots(v_ms: float) -> float:
    """Convierte m/s a nudos con el factor del modelo original."""
    return v_ms / KNOT_TO_MS


def kgf_to_n(f_kgf: float) -> float:
    """Convierte kgf a N."""
    return f_kgf * KGF_TO_N


def n_to_kgf(f_n: float) -> float:
    """Convierte N a kgf."""
    return f_n / KGF_TO_N
