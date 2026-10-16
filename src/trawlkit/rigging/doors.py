"""Portones de arrastre: separación, fuerzas hidrodinámicas y superficie requerida.

Replica la hoja *Portones y aparejamiento* del modelo original (bloques B6:F13, B26:G30,
A141:H168, B184:E198, B201:F231, A235:D270, A273:H289) y la polar del portón del catálogo
(``data/doors.yaml``, *Tablas de Referencias* A245:E286).

Convenciones: fuerzas en kgf, velocidades en m/s, longitudes en m, ángulos en grados.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from trawlkit.compat import Compat
from trawlkit.io import Door, load_doors
from trawlkit.rigging._excel import FloatOrArray, as_array, dataclass_to_dict, ret
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
    """Resistencia (Rd/ROB) y fuerza de abertura (Fdy/Ry) de los dos portones [kgf]."""

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


@dataclass(frozen=True)
class RequiredArea:
    """Resumen de la superficie requerida (Port!F212/F215 y F225/F229)."""

    average_total_m2: float
    per_door_m2: float

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclass_to_dict(self)


def required_area_summary(
    areas_m2: FloatOrArray,
    speeds_kn: FloatOrArray,
    v_min_kn: float = 2.0,
    v_max_kn: float = 4.0,
) -> RequiredArea:
    """Superficie requerida promedio entre 2 y 4 nudos y por portón (Port!F212/F215).

    ``F212 = AVERAGE(E212:E216)`` (filas de 2.0 a 4.0 kn) y ``F215 = F212/2``.
    """
    a = as_array(areas_m2)
    s = as_array(speeds_kn)
    mask = (s >= v_min_kn) & (s <= v_max_kn)
    avg = float(np.mean(a[mask]))
    return RequiredArea(average_total_m2=avg, per_door_m2=avg / 2.0)


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
    """Portón del catálogo ``data/doors.yaml`` por ``id`` (p. ej. ``"fao_flat_wood_a3"``).

    Equivale a la lista desplegable Port!B117 y a los ``LOOKUP`` de Port!D120:D127.
    """
    for door in load_doors().doors:
        if door.id == door_id:
            return door
    raise KeyError(f"portón desconocido: {door_id!r}")


def door_polar(door: Door, angle_deg: float) -> DoorPolar:
    """CL, CD y CL/CD del portón al ángulo de ataque dado (Port!C132:F137; fila 134 = 32°).

    El ángulo debe existir en la polar del catálogo; ``cl_cd = CL/CD`` (Tab!E259:E264).
    """
    for coef in door.coefficients:
        if coef.angle_deg == angle_deg:
            if coef.cl is None or coef.cd is None:
                raise ValueError(f"sin coeficientes para {door.id!r} a {angle_deg}°")
            return DoorPolar(angle_deg=angle_deg, cl=coef.cl, cd=coef.cd, cl_cd=coef.cl / coef.cd)
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
