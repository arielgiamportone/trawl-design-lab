"""Lastre del burlón: métodos de Koyama, Prado y Fridman, y distribución sobre el burlón.

Replica *Flotación y Lastre* D153:H159 (Koyama), F162:I180 (Prado), A193:M218 (Fridman) y
B221:I245 (distribución). Pesos en kg (la hoja los trata como kgf), longitudes en m.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from trawlkit.excel import (
    FloatOrArray,
    as_array,
    dataclass_to_dict,
    excel_rounddown,
    excel_roundup,
    ret,
)


def ballast_koyama_kg(headrope_m: float) -> float:
    """Lastre según Koyama = 1.81·L − 4.54 [kg], L = largo de la lima (Flot!G159)."""
    return 1.81 * headrope_m - 4.54


def ballast_prado_kg(nhp_hp: float, k: float = 0.28) -> float:
    """Lastre según Prado y Dremiere = K·NHP [kg] (Flot!I173/I180; K = 0.28 para 50–100 NHP)."""
    return k * nhp_hp


def ballast_fridman_kg(
    f1_vertical_kgf: FloatOrArray,
    f2_vertical_kgf: FloatOrArray,
    footrope_weight_water_kgf: float,
) -> FloatOrArray:
    """Lastre según Fridman = F1' + F2' − W_burlón [kg] (Flot!L197/M197).

    ``f1_vertical_kgf`` y ``f2_vertical_kgf`` son las componentes verticales del bloque de
    flotación (Flot!I42, J42/K42); ``footrope_weight_water_kgf`` es Flot!G191.
    """
    total = as_array(f1_vertical_kgf) + as_array(f2_vertical_kgf) - footrope_weight_water_kgf
    like = f1_vertical_kgf if hasattr(f1_vertical_kgf, "__len__") else f2_vertical_kgf
    return ret(total, like)


@dataclass(frozen=True)
class BallastLimits:
    """Lastre mínimo y máximo (Flot!F225, F226) [kg]."""

    min_kg: float
    max_kg: float

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclass_to_dict(self)


def ballast_limits(ballast_mod_1kn_kg: float, ballast_std_3kn_kg: float) -> BallastLimits:
    """Mínimo = ROUNDDOWN(lastre modificada a 1 kn), máximo = ROUNDUP(estándar a 3 kn).

    Flot!F225 = ROUNDDOWN(M197, 0) y F226 = ROUNDUP(L201, 0).
    """
    return BallastLimits(
        min_kg=float(excel_rounddown(ballast_mod_1kn_kg)),
        max_kg=float(excel_roundup(ballast_std_3kn_kg)),
    )


def adjust_chain_weight_kg(ballast_kg: float, share: float = 0.2, chain_m: float = 2.0) -> float:
    """Peso de la cadena de reglaje = ROUNDUP(lastre·0.2, 0)·L_cadena [kg] (Flot!H224)."""
    return float(excel_roundup(ballast_kg * share)) * chain_m


def ballast_even_kg_m(ballast_kg: float, chain_weight_kg: float, footrope_m: float) -> float:
    """Distribución pareja = (lastre − peso de reglaje)/burlón [kg/m] (Flot!E233)."""
    return (ballast_kg - chain_weight_kg) / footrope_m


@dataclass(frozen=True)
class BallastDistribution:
    """Distribución selectiva del lastre (Flot!G236:I238 o G243:I245)."""

    adjust_kg: float
    bosom_kg: float
    wings_kg: float
    adjust_kg_m: float
    bosom_kg_m: float
    wings_kg_m: float

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclass_to_dict(self)


def distribute_ballast_min(
    ballast_kg: float,
    footrope_m: float,
    adjust_share: float = 0.2,
    bosom_share: float = 0.25,
    adjust_m: float = 1.0,
    bosom_m: float = 2.5,
) -> BallastDistribution:
    """Distribución selectiva del lastre mínimo (Flot!F236:I238).

    ``G236 = ROUNDDOWN(0.2·F225)`` (reglaje), ``G237 = ROUNDUP(0.25·F225)`` (bocana),
    ``G238 = ROUNDUP((1 − 0.25 − 0.2)·F225)`` (alas); kg/m sobre 1 m, 2.5 m y burlón − 2.5 m.
    """
    wings_share = 1.0 - bosom_share - adjust_share
    adjust = float(excel_rounddown(adjust_share * ballast_kg))
    bosom = float(excel_roundup(bosom_share * ballast_kg))
    wings = float(excel_roundup(wings_share * ballast_kg))
    wings_m = footrope_m - bosom_m
    return BallastDistribution(
        adjust_kg=adjust,
        bosom_kg=bosom,
        wings_kg=wings,
        adjust_kg_m=adjust / adjust_m,
        bosom_kg_m=bosom / bosom_m,
        wings_kg_m=wings / wings_m,
    )


def distribute_ballast_max(
    ballast_kg: float,
    footrope_m: float,
    adjust_share: float = 0.3,
    bosom_share: float = 0.2,
    chain_m: float = 2.0,
    bosom_m: float = 2.5,
) -> BallastDistribution:
    """Distribución selectiva del lastre máximo (Flot!F243:I245).

    ``G243 = ROUNDDOWN(0.3·F226)`` (reglaje), ``G244 = ROUNDDOWN(0.2·F226)`` (bocana),
    ``G245 = F226 − G243 − G244`` (alas); kg/m sobre la cadena (F224 = 2 m), 2.5 m y
    burlón − 2.5 m − cadena.
    """
    adjust = float(excel_rounddown(adjust_share * ballast_kg))
    bosom = float(excel_rounddown(bosom_share * ballast_kg))
    wings = ballast_kg - adjust - bosom
    wings_m = footrope_m - bosom_m - chain_m
    return BallastDistribution(
        adjust_kg=adjust,
        bosom_kg=bosom,
        wings_kg=wings,
        adjust_kg_m=adjust / chain_m,
        bosom_kg_m=bosom / bosom_m,
        wings_kg_m=wings / wings_m,
    )


@dataclass(frozen=True)
class BallastChain:
    """Lastre con una cadena del catálogo de componentes (Fase 19.2; no está en el libro).

    El libro da el lastre en kg (Flot!F225:F226, plomos o cadena) y la cadena de reglaje en kg
    (Flot!H224). Con una cadena elegida (``DesignCase.chain_id``), esos kg se pasan a metros con
    su peso por metro en aire, y se da el peso en el agua de esos metros:
    ``W_agua = L · kg/m · (1 − ρ_mar/ρ_acero)``.
    """

    id: str
    name: str
    weight_kg_per_m: float
    water_coefficient: float
    min_m: float
    max_m: float
    adjust_m: float
    water_weight_min_kgf: float
    water_weight_max_kgf: float
    breaking_load_t: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclass_to_dict(self)


def ballast_chain(
    chain_id: str,
    name: str,
    weight_kg_per_m: float,
    min_kg: float,
    max_kg: float,
    adjust_kg: float,
    water_coefficient: float,
    breaking_load_t: float | None = None,
) -> BallastChain:
    """Metros de cadena para el lastre mínimo, el máximo y el reglaje: kg / (kg/m) [m].

    ``water_coefficient`` = 1 − ρ_mar/ρ_acero (:func:`trawlkit.materials.
    weight_in_water_coefficient` con la densidad del acero de la tabla de materiales).
    """
    if weight_kg_per_m <= 0:
        raise ValueError("el peso por metro de la cadena debe ser > 0")
    lmin = min_kg / weight_kg_per_m
    lmax = max_kg / weight_kg_per_m
    return BallastChain(
        id=chain_id,
        name=name,
        weight_kg_per_m=weight_kg_per_m,
        water_coefficient=water_coefficient,
        min_m=lmin,
        max_m=lmax,
        adjust_m=adjust_kg / weight_kg_per_m,
        water_weight_min_kgf=lmin * weight_kg_per_m * water_coefficient,
        water_weight_max_kgf=lmax * weight_kg_per_m * water_coefficient,
        breaking_load_t=breaking_load_t,
    )
