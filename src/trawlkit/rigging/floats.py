"""Flotación de la lima: métodos de Koyama, Prado y Fridman, número y distribución de boyas.

Replica *Flotación y Lastre* E2:I6 (Koyama), E10:I17 (Prado), B22:F27 (geometría), B40:N63
(Fridman 150/180 HP), D69:G82 (número de boyas), C84:L112 (distribución) y A116:J146
(resistencia de las boyas, Hoerner).

Convenciones: fuerzas en kgf, longitudes en m, velocidades en m/s, ángulos en grados.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from trawlkit.compat import Compat
from trawlkit.excel import (
    FloatArray,
    FloatOrArray,
    as_array,
    dataclass_to_dict,
    excel_even,
    excel_int,
    excel_lookup_index,
    excel_round,
    excel_rounddown,
    ret,
)
from trawlkit.rigging.warps import kinematic_viscosity_m2_s
from trawlkit.units import RHO_SEAWATER, G

#: CD de una esfera según Hoerner (1975) (Flot!H129) y el valor que la hoja usa desde 3 kn.
FLOAT_CD_HOERNER: float = 0.47
FLOAT_CD_HIGH_SPEED: float = 0.5


def flotation_koyama_kgf(headrope_m: float) -> float:
    """Flotación según Koyama = 1.11·L − 6.81 [kgf], L = largo de la lima (Flot!F6)."""
    return 1.11 * headrope_m - 6.81


def flotation_prado_kgf(nhp_hp: float, k: float = 0.2) -> float:
    """Flotación según Prado y Dremiere = K·NHP [kgf] (Flot!F17/G17; K = 0.2 para 50–600 NHP)."""
    return k * nhp_hp


def beta_deg(vertical_opening_m: float, body_length_m: float) -> float:
    """Ángulo β = atan((AV/2)/L_cuerpo) [°] del tiro de la red sobre la lima (Flot!F23)."""
    return float(np.degrees(np.arctan((vertical_opening_m / 2.0) / body_length_m)))


@dataclass(frozen=True)
class FridmanFlotation:
    """Flotación según Fridman para una serie de velocidades (Flot!F42:M50 o F55:M63) [kgf]."""

    f1_kgf: FloatOrArray
    f2_kgf: FloatOrArray
    f1_vertical_kgf: FloatOrArray
    f2_vertical_kgf: FloatOrArray
    total_kgf: FloatOrArray

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclass_to_dict(self)


def flotation_fridman(
    ft_kgf: FloatOrArray,
    rn_kgf: FloatOrArray,
    bridle_angle_deg: float,
    beta_deg: float,
    rope_weight_water_kgf: float,
    rounddown: bool | FloatArray = True,
) -> FridmanFlotation:
    """Flotación de Fridman: F1 = 0.8·FT/4, F2 = RN/4, F = F1·sin α + F2·sin β + W_lima [kgf].

    Flot!F42 (F1), G42/H42 (F2 estándar/modificada), I42 (F1' = F1·sin α con α = ángulo de bridas,
    F22), J42/K42 (F2' = F2·sin β, F23), L42/M42 (total). ``rope_weight_water_kgf`` es el peso de la
    lima en el agua (Flot!F37).

    Redondeo: la hoja aplica ``ROUNDDOWN(…, 0)`` en L42:L50, M42 y en todo el bloque de 180 HP
    (L55:M63), pero **no** en M43:M50 (modificada, 150 HP). ``rounddown`` puede ser un booleano o
    una máscara por velocidad para reproducir esa inconsistencia.
    """
    ft = as_array(ft_kgf)
    rn = as_array(rn_kgf)
    f1 = 0.8 * ft / 4.0
    f2 = rn / 4.0
    f1v = f1 * np.sin(np.radians(bridle_angle_deg))
    f2v = f2 * np.sin(np.radians(beta_deg))
    raw = f1v + f2v + rope_weight_water_kgf
    rounded = as_array(excel_rounddown(raw))
    mask = np.broadcast_to(np.asarray(rounddown, dtype=bool), raw.shape)
    total = np.where(mask, rounded, raw)
    like = ft_kgf if np.ndim(ft_kgf) else rn_kgf
    return FridmanFlotation(
        f1_kgf=ret(f1, ft_kgf),
        f2_kgf=ret(f2, rn_kgf),
        f1_vertical_kgf=ret(f1v, ft_kgf),
        f2_vertical_kgf=ret(f2v, rn_kgf),
        total_kgf=ret(total, like),
    )


def flotation_fridman_average_kgf(
    total_std_kgf: FloatOrArray,
    total_mod_kgf: FloatOrArray,
    speeds_kn: FloatOrArray,
    max_speed_kn: float = 3.0,
) -> float:
    """Flotación de diseño = AVERAGE(L42:M46): estándar y modificada de 1 a 3 kn (Flot!N43, N55)."""
    s = as_array(speeds_kn)
    mask = s <= max_speed_kn
    values = np.concatenate([as_array(total_std_kgf)[mask], as_array(total_mod_kgf)[mask]])
    return float(np.mean(values))


def float_count(flotation_kgf: float, unit_buoyancy_kgf: FloatOrArray) -> FloatOrArray:
    """Número de boyas = ROUND(F/flotación unitaria, 0) por diámetro del catálogo (Flot!F72:G82)."""
    return excel_round(flotation_kgf / as_array(unit_buoyancy_kgf))


def float_diameter_for_count_mm(
    count: float, counts: FloatOrArray, diameters_mm: FloatOrArray
) -> float:
    """Diámetro de boya asociado al número elegido: ``LOOKUP(F91, cincuenta, D72:D82)`` (Flot!F92).

    ``cincuenta`` (F72:F82) no está ordenado; se reproduce la búsqueda binaria de ``LOOKUP``
    (12 boyas → 200 mm en el modelo).
    """
    idx = excel_lookup_index(count, list(as_array(counts)))
    return float(as_array(diameters_mm)[idx])


@dataclass(frozen=True)
class FloatDistribution:
    """Distribución de las boyas sobre la lima (Flot!F94:K112)."""

    count: int
    diameter_mm: float
    spacing_even_m: float
    per_wing_even: int
    bosom_even: int
    on_wings: int
    per_wing: int
    on_bosom: int
    front_fifth: int
    spacing_front_fifth_m: float
    wing_remaining_m: float
    remaining_per_wing: int
    spacing_remaining_m: float
    wing_free_end_m: float
    spacing_bosom_m: float

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclass_to_dict(self)


def distribute_floats(
    count: int,
    diameter_mm: float,
    headrope_m: float,
    wing_corrected_m: float,
    bosom_corrected_m: float,
    wing_share: float = 0.7,
    front_fifth_share: float = 0.6,
) -> FloatDistribution:
    """Distribución pareja y selectiva de las boyas (Flot!C84:L112).

    * pareja: ``F94 = L/n``; ``F95 = INT(L_ala/F94)``; ``F96 = n − 2·F95``;
    * selectiva: ``G103 = EVEN(n·0.7)`` en alas, ``H103 = G103/2`` por ala, ``G104 = n − G103`` en
      bocana; ``G107 = H103·0.6`` en el primer quinto, ``H110 = ROUND(L_bocana/(G107 − 1), 2)``;
      ``C111 = L_ala − L_bocana``, ``F111 = H103 − G104``, ``H111 = INT(C111/F111)``,
      ``E112 = C111 − H111·F111``, ``K112 = L_bocana/3``.

    ``wing_corrected_m`` es Dim!C143 (L ala · embando) y ``bosom_corrected_m`` Dim!G143.
    """
    spacing_even = headrope_m / count
    per_wing_even = int(excel_int(wing_corrected_m / spacing_even))
    bosom_even = count - 2 * per_wing_even
    on_wings = int(excel_even(count * wing_share))
    per_wing = on_wings // 2
    on_bosom = count - on_wings
    front_fifth = int(per_wing * front_fifth_share)
    spacing_front = float(excel_round(bosom_corrected_m / (front_fifth - 1), 2))
    remaining_m = wing_corrected_m - bosom_corrected_m
    remaining_per_wing = per_wing - on_bosom
    spacing_remaining = float(excel_int(remaining_m / remaining_per_wing))
    free_end = remaining_m - spacing_remaining * remaining_per_wing
    return FloatDistribution(
        count=count,
        diameter_mm=diameter_mm,
        spacing_even_m=spacing_even,
        per_wing_even=per_wing_even,
        bosom_even=bosom_even,
        on_wings=on_wings,
        per_wing=per_wing,
        on_bosom=on_bosom,
        front_fifth=front_fifth,
        spacing_front_fifth_m=spacing_front,
        wing_remaining_m=remaining_m,
        remaining_per_wing=remaining_per_wing,
        spacing_remaining_m=spacing_remaining,
        wing_free_end_m=free_end,
        spacing_bosom_m=bosom_corrected_m / 3.0,
    )


def float_cd(
    speed_kn: FloatOrArray,
    cd_low: float = FLOAT_CD_HOERNER,
    cd_high: float = FLOAT_CD_HIGH_SPEED,
    switch_kn: float = 3.0,
) -> FloatOrArray:
    """CD de la boya: 0.47 (Hoerner) hasta 2.5 kn y 0.5 escrito a mano desde 3 kn.

    Flot!I138:I141 = $H$129 (0.47); I142:I146 = 0.5 (valor fijo).
    """
    s = as_array(speed_kn)
    return ret(np.where(s >= switch_kn, cd_high, cd_low).astype(float), speed_kn)


def float_reynolds(
    diameter_m: float,
    v_ms: FloatOrArray,
    nu_m2_s: float | None = None,
    compat: Compat = Compat.CORRECTED,
) -> FloatOrArray:
    """Número de Reynolds de la boya (Flot!H138:H146).

    Errata ``float_reynolds``: la hoja calcula ``Re = π·D²·v/ν`` (H138) en vez de ``Re = v·D/ν``.
    :attr:`Compat.EXCEL` reproduce la fórmula errada; :attr:`Compat.CORRECTED` usa v·D/ν.
    """
    nu = kinematic_viscosity_m2_s() if nu_m2_s is None else nu_m2_s
    v = as_array(v_ms)
    if compat is Compat.EXCEL:
        return ret(np.pi * diameter_m**2 * v / nu, v_ms)
    return ret(v * diameter_m / nu, v_ms)


def float_drag_kgf(
    count: int,
    diameter_m: float,
    cd: FloatOrArray,
    v_ms: FloatOrArray,
    rho_kg_m3: float = RHO_SEAWATER,
    g_m_s2: float = G,
) -> FloatOrArray:
    """Resistencia de las boyas RB = n·½·CD·(ρ/g)·(π·D²/4)·v² [kgf] (Flot!J138:J146)."""
    v = as_array(v_ms)
    area = np.pi * diameter_m**2 / 4.0
    return ret(0.5 * count * as_array(cd) * (rho_kg_m3 / g_m_s2) * area * v**2, v_ms)
