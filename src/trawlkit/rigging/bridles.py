"""Bridas (vientos), patentes y pies de gallo (Martini / Dremiere).

Replica *Portones y aparejamiento* A33:G110: bridas a un punto (E52, E60, D44:D46), patentes de
Dremiere (C71) y de Martini (G71, C83, C87), pies de gallo (E97, G98) y ángulo de ataque de bridas
y patentes (D110). Longitudes en m, ángulos en grados.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from trawlkit.compat import Compat
from trawlkit.rigging._excel import dataclass_to_dict, excel_round, excel_roundup


@dataclass(frozen=True)
class BridleLengths:
    """Bridas a un punto (Port!E52, E60, D44, D45, D46) [m]."""

    no_triangle_m: float
    triangle_m: float
    upper_m: float
    adjust_chain_m: float
    lower_m: float

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclass_to_dict(self)


def bridle_lengths(
    vertical_opening_m: float,
    headrope_sag_m: float,
    bridle_angle_deg: float = 4.8,
    dan_leno_m: float = 0.6,
    chain_ratio: float = 0.095,
) -> BridleLengths:
    """Largo de las bridas a un punto según Martini (Port!E52, E60, D44:D46).

    * sin triángulo: ``E52 = ROUND(AV/sin α − fL, 0)``;
    * con triángulo (dan leno de altura h): ``E60 = ROUND((AV − h)/sin α, 0)``;
    * brida superior Vs: ``D44 = ROUND(E52, 0)``; cadena de reglaje ``D46 = 0.095·Vs``;
      brida inferior ``D45 = ROUNDUP(Vs − Cr, 0)``.

    ``bridle_angle_deg`` es α, el ángulo entre brida superior e inferior (Port!F39 = 4.8°). Se
    reproducen los ``ROUND``/``ROUNDUP`` de Excel.
    """
    sin_a = float(np.sin(np.radians(bridle_angle_deg)))
    no_triangle = float(excel_round(vertical_opening_m / sin_a - headrope_sag_m))
    triangle = float(excel_round((vertical_opening_m - dan_leno_m) / sin_a))
    upper = float(excel_round(no_triangle))
    chain = upper * chain_ratio
    lower = float(excel_roundup(upper - chain))
    return BridleLengths(
        no_triangle_m=no_triangle,
        triangle_m=triangle,
        upper_m=upper,
        adjust_chain_m=chain,
        lower_m=lower,
    )


def sweeps_dremiere_m(warp_m: float, ratio: float = 6.0) -> float:
    """Largo de patentes según P. Y. Dremiere = Ls / relación (Port!C71 = B69/B68, relación 6)."""
    return warp_m / ratio


def sweeps_martini_m(
    door_spread_m: float,
    dpa_m: float,
    delta_deg: float = 20.0,
    compat: Compat = Compat.CORRECTED,
) -> float:
    """Largo de patentes según Martini a partir del ángulo δ (Port!G71).

    Fórmula prevista: LP = (Ds/2 − DPA/2) / sin δ.

    Errata ``sweep_degrees_of_sine``: la celda escribe ``((E13/2)-(E78/2)/DEGREES(SIN(H65)))``:
    toma el seno de δ en grados como si fueran radianes, lo convierte con ``DEGREES`` y, por la
    precedencia, solo divide DPA/2 (16.13 m en vez de 28.5 m). En modo :attr:`Compat.EXCEL` se
    reproduce; el resultado no se usa aguas abajo en la hoja.
    """
    if compat is Compat.EXCEL:
        return door_spread_m / 2.0 - (dpa_m / 2.0) / float(np.degrees(np.sin(delta_deg)))
    return (door_spread_m - dpa_m) / (2.0 * float(np.sin(np.radians(delta_deg))))


def sweeps_length_m(
    door_spread_m: float,
    net_length_m: float,
    dpa_m: float,
    bridle_m: float,
    factor: float = 1.1,
) -> float:
    """Largo de patentes según Martini: LP = ((Ds·LR/DPA) − (Vs + LR))·1.1 [m] (Port!C83/C87).

    ``net_length_m`` es el largo de la red sin bolsa (``Largototal``, Port!E80) y ``bridle_m`` la
    brida superior (sin triángulo, Port!E79 → C83) o con triángulo (Port!E81 → C87).
    """
    return ((door_spread_m * net_length_m) / dpa_m - (bridle_m + net_length_m)) * factor


@dataclass(frozen=True)
class Crowfoot:
    """Pies de gallo (Port!E97:G99) [m]."""

    length_m: float
    upper_m: float
    extension_m: float

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclass_to_dict(self)


def crowfoot_m(door_length_m: float, extension_m: float = 0.0) -> Crowfoot:
    """Pie de gallo PG = ROUND(1.2·L_portón, 1) y superior = PG − 0.05 [m] (Port!E97, G98).

    ``extension_m`` es el alargue del pie de gallo (Port!E99, 0 en el modelo).
    """
    pg = float(excel_round(door_length_m + door_length_m * 0.2, 1))
    return Crowfoot(length_m=pg, upper_m=pg - 0.05, extension_m=extension_m)


def attack_angle_deg(
    door_spread_m: float,
    dpa_m: float,
    crowfoot_m: float,
    sweeps_m: float,
    bridle_m: float,
) -> float:
    """Ángulo de ataque de bridas y patentes δ = asin(((Ds − DPA)/2)/(PG + LP + Vs)) [°].

    Port!D110 con PG = pie de gallo, LP = patentes (C83) y Vs = brida superior (E52).
    """
    return float(
        np.degrees(np.arcsin(((door_spread_m - dpa_m) / 2.0) / (crowfoot_m + sweeps_m + bridle_m)))
    )
