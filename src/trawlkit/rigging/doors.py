"""Portones de arrastre: separación, fuerzas hidrodinámicas y superficie requerida.

Replica la hoja *Portones y aparejamiento* del modelo original (bloques B6:F13, B26:G30,
A141:H168, B184:E198, B201:F231, A235:D270, A273:H289) y la polar del portón del catálogo
(``trawlkit/data/doors.yaml``, *Tablas de Referencias* A245:E286).

Convenciones: fuerzas en kgf, velocidades en m/s, longitudes en m, ángulos en grados.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any

import numpy as np

from trawlkit.compat import Compat
from trawlkit.excel import FloatOrArray, as_array, dataclass_to_dict, ret
from trawlkit.i18n import t
from trawlkit.io import Door, load_doors
from trawlkit.units import RHO_SEAWATER, G

#: Fracciones de FT que Fridman asigna a la resistencia de los portones (Port!E146:H146).
ROB_SHARES: tuple[float, ...] = (0.15, 0.20, 0.25, 0.30)


def door_spread_m(gallows_m: float, spread_per_m: float, warp_m: float) -> float:
    """Distancia entre portones Ds = (D7 − D6)·Ls + D6 [m] (Port!E13).

    Regla práctica "al metro": ``spread_per_m`` es la separación obtenida con 1 m de cable
    (Port!D7 = 2.65 m), ``gallows_m`` la distancia entre pastecas (Port!D6) y ``warp_m`` el cable
    filado (Port!D9).
    """
    return (spread_per_m - gallows_m) * warp_m + gallows_m


def door_spread_corrected_m(
    warp_m: float, half_divergence_deg: float, factor: float = 1.15
) -> float:
    """Distancia entre portones corregida = factor·2·Ls·sin(½φ) [m] (Port!F30).

    ``half_divergence_deg`` es ½φ (Port!D21, ver :func:`trawlkit.rigging.warps.warp_divergence_deg`)
    y ``factor`` el coeficiente de corrección Port!D28 (1.15).
    """
    return float(factor * (2.0 * warp_m * np.sin(np.radians(half_divergence_deg))))


def door_drag_share_kgf(ft_kgf: FloatOrArray, share: float) -> FloatOrArray:
    """Resistencia de los portones ROB como fracción del tiro disponible FT [kgf] (Port!E146:H168).

    Fridman: ROB = 15–30 % de FT. ``share`` es la fracción (0.15, 0.20, 0.25 o 0.30).
    """
    return ret(as_array(ft_kgf) * share, ft_kgf)


@dataclass(frozen=True)
class DoorForces:
    """Resistencia (Rd/ROB) y fuerza de abertura (Fdy/Ry) de UN portón [kgf] (Port!D190:E198)."""

    drag_kgf: FloatOrArray
    lift_kgf: FloatOrArray

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclass_to_dict(self)


def door_forces_kgf(
    area_m2: float,
    cd: float,
    cl: float,
    v_ms: FloatOrArray,
    rho_kg_m3: float = RHO_SEAWATER,
    g_m_s2: float = G,
) -> DoorForces:
    """Fuerzas hidrodinámicas del portón: F = ½·(ρ/g)·C·S·v² [kgf] (Port!D190/E190, Mec!H164/I164).

    ``drag_kgf`` usa CD (ROB, Tx) y ``lift_kgf`` usa CL (fuerza de abertura Ry). ``area_m2`` es la
    superficie proyectada del portón (Port!D122 = 1.805 m²) y ``v_ms`` la velocidad de arrastre.
    """
    v = as_array(v_ms)
    q = 0.5 * (rho_kg_m3 / g_m_s2) * area_m2 * v**2
    return DoorForces(drag_kgf=ret(q * cd, v_ms), lift_kgf=ret(q * cl, v_ms))


def required_area_m2(
    rob_kgf: FloatOrArray,
    cd: float,
    v_ms: FloatOrArray,
    rho_kg_m3: float = RHO_SEAWATER,
    g_m_s2: float = G,
) -> FloatOrArray:
    """Superficie total de portones necesaria S = 2·ROB/((ρ/g)·CD·v²) [m²] (Port!E210:E218).

    Inversa de :func:`door_forces_kgf` para la resistencia ROB asignada (Port!D210 = 20 % de FT).
    """
    rob = as_array(rob_kgf)
    v = as_array(v_ms)
    return ret(2.0 * rob / ((rho_kg_m3 / g_m_s2) * cd * v**2), v_ms if np.ndim(v_ms) else rob_kgf)


#: Exponente b de las tablas reales de superficie de portón contra potencia, S ∝ hp^b (Fase 20.1b).
#: Ajuste por mínimos cuadrados en log–log: tabla de portones planos del *Workbook* (Prado y
#: Dremière 1990, «Otter boards … choice depending on power», 50–800 hp) → 0,646; tabla de los
#: Fishbuster de Net Systems (2014, catálogo pp. C.10–C.11, «Estimated Range hp», 250–5500 hp,
#: punto medio geométrico de cada rango) → 0,656. Se toma el valor central 0,65. Fuentes:
#: ``prado1990`` y ``netsystems_fishbuster`` en ``docs/referencias.bib``.
DOOR_AREA_POWER_EXPONENT: float = 0.65

#: Potencia de diseño del libro [BHP]: el mayor de los dos buques de la clase A-3 (150 y 180 HP,
#: bloques Port!E146:H168 y E160:F229). Hasta esta potencia la regla del libro no se toca.
DOOR_AREA_DESIGN_POWER_HP: float = 180.0


#: Tabla de los portones Fishbuster de Net Systems (2014, catálogo pp. C.10–C.11; portón en V,
#: «Lift-to-drag ratio in excess of 2 to 1»): superficie por portón [m²] y «Estimated Range hp»
#: (mínimo, máximo; «6000 UP» → sin máximo). Referencia ``netsystems_fishbuster``; es la única
#: tabla pública de portones indexada por potencia (comparación de la Fase 20.1b).
FISHBUSTER_AREA_HP: tuple[tuple[float, float, float], ...] = (
    (1.5, 250, 300),
    (2.0, 300, 400),
    (3.0, 300, 500),
    (3.5, 400, 650),
    (4.0, 600, 800),
    (4.5, 700, 900),
    (5.0, 900, 1200),
    (5.5, 1000, 1300),
    (6.0, 1400, 1800),
    (6.5, 1600, 2200),
    (7.0, 1800, 2200),
    (7.5, 1800, 2200),
    (8.5, 2250, 3200),
    (10.0, 2800, 4000),
    (11.0, 3000, 4500),
    (12.5, 4000, 5500),
    (14.0, 6000, float("inf")),
    (15.0, 6000, float("inf")),
)


def fishbuster_area_range_m2(hp: float, band: float = 0.05) -> tuple[float, float] | None:
    """Rango de superficie por portón de la tabla Fishbuster para la potencia ``hp`` [m²].

    Toma las filas cuyo «Estimated Range hp» se cruza con ``hp·(1 ± band)`` (los rangos del
    catálogo están redondeados a 50–100 hp); si ninguna lo hace (un hueco de la tabla, p. ej.
    1311 hp entre 1000–1300 y 1400–1800), las dos filas vecinas. ``None`` por debajo de la tabla
    (< 250 hp).
    """
    lo_hp, hi_hp = hp * (1.0 - band), hp * (1.0 + band)
    if hi_hp < FISHBUSTER_AREA_HP[0][1]:
        return None
    rows = [a for a, lo, hi in FISHBUSTER_AREA_HP if lo <= hi_hp and hi >= lo_hp]
    if not rows:
        below = max(a for a, _, hi in FISHBUSTER_AREA_HP if hi < lo_hp)
        above = min(a for a, lo, _ in FISHBUSTER_AREA_HP if lo > hi_hp)
        rows = [below, above]
    return min(rows), max(rows)


def door_area_power_factor(
    bhp: float,
    compat: Compat = Compat.CORRECTED,
    *,
    exponent: float = DOOR_AREA_POWER_EXPONENT,
    design_power_hp: float = DOOR_AREA_DESIGN_POWER_HP,
) -> float:
    """Factor de la superficie requerida por encima de la potencia de diseño del libro (Fase 20.1b).

    ``min(1, (design_power_hp/bhp)^(1 − exponent))``: la regla del libro (Port!F212/F215) es
    lineal en la potencia (``S ∝ FT ∝ BHP``), las tablas reales crecen como ``hp^0,65``; por
    encima de 180 HP el factor lleva el crecimiento de la regla al de las tablas (errata
    ``door_area_power_extrapolation``). ``bhp`` es la potencia al freno del buque, la misma que
    alimenta el tiro de Fridman ``FT = KF·BHP`` de la regla (PotOK!L11:O19). En
    :attr:`Compat.EXCEL` (y para ``bhp ≤ 180``) el factor es exactamente 1.
    """
    if compat is Compat.EXCEL or not bhp > design_power_hp:
        return 1.0
    return float((design_power_hp / bhp) ** (1.0 - exponent))


@dataclass(frozen=True)
class RequiredArea:
    """Resumen de la superficie requerida (Port!F212/F215 y F225/F229).

    ``average_total_m2`` y ``per_door_m2`` son los valores de diseño (con el factor de potencia de
    la Fase 20.1b aplicado); ``book_per_door_m2`` es Port!F215 tal cual lo da la regla del libro y
    ``power_factor`` el factor aplicado (1 hasta 180 HP y en modo EXCEL).
    """

    average_total_m2: float
    per_door_m2: float
    book_per_door_m2: float
    power_factor: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclass_to_dict(self)


def required_area_summary(
    areas_m2: FloatOrArray,
    speeds_kn: FloatOrArray,
    v_min_kn: float = 2.0,
    v_max_kn: float = 4.0,
    *,
    bhp: float | None = None,
    compat: Compat = Compat.CORRECTED,
) -> RequiredArea:
    """Superficie requerida promedio entre 2 y 4 nudos y por portón (Port!F212/F215).

    ``F212 = AVERAGE(E212:E216)`` (filas de 2.0 a 4.0 kn) y ``F215 = F212/2``. Con ``bhp`` se
    aplica :func:`door_area_power_factor` (Fase 20.1b). Es la única función que da la superficie
    requerida: la usan la etapa de portones del motor, la selección de portones, el optimizador,
    el informe y la API.
    """
    a = as_array(areas_m2)
    s = as_array(speeds_kn)
    mask = (s >= v_min_kn) & (s <= v_max_kn)
    book = float(np.mean(a[mask]))
    factor = 1.0 if bhp is None else door_area_power_factor(bhp, compat)
    avg = book * factor
    return RequiredArea(
        average_total_m2=avg,
        per_door_m2=avg / 2.0,
        book_per_door_m2=book / 2.0,
        power_factor=factor,
    )


def required_area_overall_m2(per_door_150_m2: float, per_door_180_m2: float) -> float:
    """Superficie requerida por portón promediando 150 y 180 HP (Port!F220).

    ``F220 = AVERAGE(F215, F229)``.
    """
    return (per_door_150_m2 + per_door_180_m2) / 2.0


def door_force_kgf(
    cd: float,
    area_m2: float,
    angle_deg: float,
    v_ms: FloatOrArray,
    rho_kg_m3: float = RHO_SEAWATER,
    g_m_s2: float = G,
    compat: Compat = Compat.CORRECTED,
) -> FloatOrArray:
    """Fuerza Pφ sobre el portón según el ángulo de bisagra/ataque [kgf] (Port!D252:D260).

    Pφ = ½·CD·(ρ/g)·v²·S·(2·sin φ)/(1 + sin² φ).

    Errata ``door_force_mixed_angles``: la celda escribe ``SIN(RADIANS($E$240))`` en el numerador
    pero ``SIN($E$240)`` (φ en grados interpretado como radianes) en el denominador. En modo
    :attr:`Compat.EXCEL` se reproduce esa mezcla; en :attr:`Compat.CORRECTED` ambos senos usan
    radianes.
    """
    v = as_array(v_ms)
    phi = np.radians(angle_deg)
    sin_num = np.sin(phi)
    sin_den = np.sin(angle_deg) if compat is Compat.EXCEL else sin_num
    ratio = (2.0 * sin_num) / (1.0 + sin_den**2)
    return ret(0.5 * cd * (rho_kg_m3 / g_m_s2) * v**2 * area_m2 * ratio, v_ms)


@dataclass(frozen=True)
class CentreOfPressure:
    """Centro de presión y brazos hA/hB del portón [m] (Port!C266, C269, C270)."""

    d_m: float
    ha_m: float
    hb_m: float

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclass_to_dict(self)


def centre_of_pressure_m(length_m: float, angle_deg: float) -> CentreOfPressure:
    """Centro de presión d = ¾·cos φ/(4 + π·sin φ)·L y brazos hA = 0.8·L/4, hB = L/4 [m].

    Port!C266, C269 y C270 con L = largo del portón (Port!E243) y φ el ángulo de ataque (E240).
    """
    phi = np.radians(angle_deg)
    d = 0.75 * (np.cos(phi) / (4.0 + np.pi * np.sin(phi))) * length_m
    return CentreOfPressure(d_m=float(d), ha_m=0.8 * length_m / 4.0, hb_m=length_m / 4.0)


@dataclass(frozen=True)
class MomentBalance:
    """Momentos de la fuerza del portón y de la patente (Port!G281:H289)."""

    door_moment_kgf_cm: FloatOrArray
    sweep_moment_kgf_m: FloatOrArray

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclass_to_dict(self)


def moment_balance(
    door_force_kgf: FloatOrArray,
    rn_kgf: FloatOrArray,
    centre_of_pressure_m: float,
    sweep_lever_m: float = 3.0,
) -> MomentBalance:
    """Equilibrio de momentos: Pφ·(d·100) [kgf·cm] y ½·RN·d_patente [kgf·m] (Port!G281/H281).

    ``G281 = F281*($C$266*100)`` convierte el centro de presión a cm; ``H281 = 0.5*D281*$E$277``
    queda en kgf·m aunque la cabecera de la hoja diga kgf·cm (se conserva tal cual).
    """
    p = as_array(door_force_kgf)
    rn = as_array(rn_kgf)
    return MomentBalance(
        door_moment_kgf_cm=ret(p * (centre_of_pressure_m * 100.0), door_force_kgf),
        sweep_moment_kgf_m=ret(0.5 * rn * sweep_lever_m, rn_kgf),
    )


@dataclass(frozen=True)
class DoorPolar:
    """Coeficientes del portón a un ángulo de ataque (Port!C132:F137)."""

    angle_deg: float
    cl: float
    cd: float
    cl_cd: float

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclass_to_dict(self)


def select_door(door_id: str) -> Door:
    """Portón del catálogo ``trawlkit/data/doors.yaml`` por ``id`` (p. ej. ``"fao_flat_wood_a3"``).

    Equivale a la lista desplegable Port!B117 y a los ``LOOKUP`` de Port!D120:D127.
    """
    for door in load_doors().doors:
        if door.id == door_id:
            return door
    raise KeyError(f"portón desconocido: {door_id!r}")


#: Extrapolación máxima fuera del rango de la polar en modo corregido [°] (Fase 19.3).
MAX_EXTRAPOLATION_DEG = 5.0


class PolarExtrapolationWarning(UserWarning):
    """El ángulo de ataque cae fuera de los ángulos medidos de la polar y se extrapola."""


def _usable_points(door: Door) -> list[tuple[float, float, float]]:
    return sorted(
        (c.angle_deg, c.cl, c.cd)
        for c in door.coefficients
        if c.cl is not None and c.cd is not None
    )


def polar_extrapolated(door: Door, angle_deg: float) -> bool:
    """Si ``angle_deg`` cae fuera de los ángulos con coeficientes de la polar del portón."""
    pts = _usable_points(door)
    return bool(pts) and not pts[0][0] <= angle_deg <= pts[-1][0]


def door_polar(door: Door, angle_deg: float, *, interpolate: bool = False) -> DoorPolar:
    """CL, CD y CL/CD del portón al ángulo de ataque dado (Port!C132:F137; fila 134 = 32°).

    Por defecto el ángulo debe existir en la polar del catálogo, como el ``LOOKUP`` del libro;
    ``cl_cd = CL/CD`` (Tab!E259:E264). Con ``interpolate`` (modo corregido y portones del
    catálogo de componentes, cuya polar no siempre tiene 32°) se interpola linealmente entre los
    dos ángulos vecinos con coeficientes; hasta :data:`MAX_EXTRAPOLATION_DEG` fuera del rango
    medido se extrapola con el tramo extremo y se avisa (:class:`PolarExtrapolationWarning`);
    más allá es ``KeyError``.
    """
    for coef in door.coefficients:
        if coef.angle_deg == angle_deg:
            if coef.cl is None or coef.cd is None:
                if interpolate:
                    break
                raise ValueError(f"sin coeficientes para {door.id!r} a {angle_deg}°")
            return DoorPolar(angle_deg=angle_deg, cl=coef.cl, cd=coef.cd, cl_cd=coef.cl / coef.cd)
    if interpolate:
        pts = _usable_points(door)
        for (a0, l0, d0), (a1, l1, d1) in zip(pts, pts[1:], strict=False):
            if a0 <= angle_deg <= a1:
                f = (angle_deg - a0) / (a1 - a0)
                cl, cd = l0 + f * (l1 - l0), d0 + f * (d1 - d0)
                return DoorPolar(angle_deg=angle_deg, cl=cl, cd=cd, cl_cd=cl / cd)
        if len(pts) >= 2:
            lo, hi = pts[0][0], pts[-1][0]
            below = lo - MAX_EXTRAPOLATION_DEG <= angle_deg < lo
            above = hi < angle_deg <= hi + MAX_EXTRAPOLATION_DEG
            if below or above:
                (a0, l0, d0), (a1, l1, d1) = pts[:2] if below else pts[-2:]
                f = (angle_deg - a0) / (a1 - a0)
                cl = max(l0 + f * (l1 - l0), 0.0)
                cd = max(d0 + f * (d1 - d0), 1e-3)
                warnings.warn(
                    t(
                        "ángulo de ataque {angle:g}° fuera de la polar medida de {door} "
                        "({lo:g}–{hi:g}°): CL y CD extrapolados",
                        angle=angle_deg,
                        door=door.id,
                        lo=lo,
                        hi=hi,
                    ),
                    PolarExtrapolationWarning,
                    stacklevel=2,
                )
                return DoorPolar(angle_deg=angle_deg, cl=cl, cd=cd, cl_cd=cl / cd)
    raise KeyError(f"ángulo {angle_deg}° no está en la polar de {door.id!r}")


def door_polar_table(door: Door) -> list[DoorPolar]:
    """Polar completa del portón (ángulos con CL y CD definidos), en el orden del catálogo."""
    return [
        DoorPolar(c.angle_deg, c.cl, c.cd, c.cl / c.cd)
        for c in door.coefficients
        if c.cl is not None and c.cd is not None
    ]


def door_weight_water_kg(weight_air_kg: float, coefficient: float) -> float:
    """Peso del portón en el agua = peso en aire · coeficiente (Port!D127 = D125·D126, 0.597)."""
    return weight_air_kg * coefficient
