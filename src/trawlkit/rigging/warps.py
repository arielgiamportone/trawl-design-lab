"""Cables de remolque: ángulos, diámetro, resistencia, peso y selección del cable.

Replica la hoja *Cables de Remolque* (D15:F33, B65:F81, A89:E112, B115:I126, B153:G175,
A178:H199, B221:D235, B241:F272), *Cables Y Cabulleria* D11:D12 y la tabla profundidad → cable
filado de *Tablas de Referencias* A353:C383 (``trawlkit/data/reference/depth_to_warp.csv``).

Convenciones: fuerzas en kgf, velocidades en m/s, longitudes en m, diámetros en mm salvo que el
sufijo diga ``_m``, ángulos en grados.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from typing import Any

import numpy as np

from trawlkit.compat import Compat
from trawlkit.excel import (
    FloatOrArray,
    as_array,
    dataclass_to_dict,
    excel_lookup_index,
    ret,
)
from trawlkit.io import DATA_DIR, load_catalogue
from trawlkit.units import RHO_SEAWATER, G

#: CD del cable según el ángulo de ataque α (Nomura y Yamazaki; Rem!A90:B94).
WARP_CD_TABLE: tuple[tuple[float, float], ...] = (
    (0.0, 0.02),
    (10.0, 0.04),
    (20.0, 0.09),
    (30.0, 0.18),
    (40.0, 0.30),
)

#: Viscosidad cinemática del agua de mar a 0 °C y 20 °C [m²/s] (Flot!H130:H131, Rem!F159:F160).
KINEMATIC_VISCOSITY_0C: float = 1.83e-6
KINEMATIC_VISCOSITY_20C: float = 1.05e-6


def kinematic_viscosity_m2_s(
    nu_cold: float = KINEMATIC_VISCOSITY_0C, nu_warm: float = KINEMATIC_VISCOSITY_20C
) -> float:
    """Viscosidad cinemática promedio ν = AVERAGE(ν₀°C, ν₂₀°C) [m²/s] (Flot!H132, Rem!F161)."""
    return (nu_cold + nu_warm) / 2.0


# ---------------------------------------------------------------------------
# Profundidad → cable filado
# ---------------------------------------------------------------------------


@cache
def _depth_to_warp_table() -> tuple[tuple[float, float, float], ...]:
    """Filas ``(profundidad, cable filado, relación)`` de ``depth_to_warp.csv``."""
    path = DATA_DIR / "reference" / "depth_to_warp.csv"
    with path.open(encoding="utf-8", newline="") as fh:
        rows = [
            (float(r["depth_m"]), float(r["warp_length_m"]), float(r["ratio"]))
            for r in csv.DictReader(fh)
        ]
    return tuple(rows)


def warp_depth_ratio(depth_m: float) -> float:
    """Relación cable filado / profundidad por ``LOOKUP`` en la tabla (Mec!J178 → 5 para 40 m).

    ``LOOKUP`` toma la fila de mayor profundidad ≤ ``depth_m`` (Tab!A354:A383 → C354:C383).
    """
    table = _depth_to_warp_table()
    idx = excel_lookup_index(depth_m, [r[0] for r in table])
    return table[idx][2]


def warp_length_for_depth(depth_m: float) -> float:
    """Cable filado recomendado por profundidad [m] (Tab!A353:B383; Mec!E177 = d · relación).

    Devuelve la columna "cable filado" de la fila de mayor profundidad ≤ ``depth_m``.
    """
    table = _depth_to_warp_table()
    idx = excel_lookup_index(depth_m, [r[0] for r in table])
    return table[idx][1]


# ---------------------------------------------------------------------------
# Geometría: ángulos y DPA por triángulos semejantes
# ---------------------------------------------------------------------------


def warp_divergence_deg(door_spread_m: float, gallows_m: float, warp_m: float) -> float:
    """Semiángulo de divergencia del cable δ2 = ½φ = asin(0.5·(Ds − pastecas)/Ls) [°].

    Rem!E25 y Port!D21 (misma fórmula).
    """
    return float(np.degrees(np.arcsin(0.5 * (door_spread_m - gallows_m) / warp_m)))


def bridle_divergence_deg(door_spread_m: float, dpa_m: float, sweeps_plus_bridle_m: float) -> float:
    """Divergencia de bridas y patentes δ3 = asin(0.5·(Ds − DPA)/(LP + Vs)) [°] (Rem!E29)."""
    return float(np.degrees(np.arcsin(0.5 * (door_spread_m - dpa_m) / sweeps_plus_bridle_m)))


def warp_declination_deg(depth_m: float, vessel_depth_m: float, warp_m: float) -> float:
    """Ángulo de declinación del cable δ1 = asin((profundidad + puntal)/Ls) [°] (Rem!E33)."""
    return float(np.degrees(np.arcsin((depth_m + vessel_depth_m) / warp_m)))


@dataclass(frozen=True)
class WarpAngles:
    """Ángulos del cable de remolque δ1, δ2, δ3 [°] (Rem!E33, E25, E29)."""

    declination_deg: float
    divergence_deg: float
    bridle_divergence_deg: float

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclass_to_dict(self)


def warp_angles_deg(
    door_spread_m: float,
    gallows_m: float,
    warp_m: float,
    dpa_m: float,
    sweeps_plus_bridle_m: float,
    depth_m: float,
    vessel_depth_m: float,
) -> WarpAngles:
    """Ángulos δ1 (declinación), δ2 (divergencia del cable) y δ3 (bridas) (Rem!C23:F33)."""
    return WarpAngles(
        declination_deg=warp_declination_deg(depth_m, vessel_depth_m, warp_m),
        divergence_deg=warp_divergence_deg(door_spread_m, gallows_m, warp_m),
        bridle_divergence_deg=bridle_divergence_deg(door_spread_m, dpa_m, sweeps_plus_bridle_m),
    )


def dpa_similar_triangles_m(door_spread_m: float, net_length_m: float, rigging_m: float) -> float:
    """DPA por triángulos semejantes = Ds·L/(L + aparejo) [m] (Rem!F17 con el burlón, F19 con LR).

    ``rigging_m`` es patentes + brida superior (Rem!F8 = 43 m). Sin redondeo.
    """
    return (door_spread_m * net_length_m) / (net_length_m + rigging_m)


# ---------------------------------------------------------------------------
# Diámetro del cable
# ---------------------------------------------------------------------------


def warp_diameter_ehp_mm(ehp_hp: float) -> float:
    """Diámetro del cable Dw = 18 + 0.0034·EHP [mm] (Rem!F73; regla para > 500 HP)."""
    return 18.0 + 0.0034 * ehp_hp


def warp_diameter_aguila_mm(nhp_hp: float) -> float:
    """Diámetro del cable según L. G. Pérez Águila: Dw = 5.6822·ln(NHP) − 17.225 [mm] (Rem!E80)."""
    return 5.6822 * float(np.log(nhp_hp)) - 17.225


# ---------------------------------------------------------------------------
# Resistencia del cable
# ---------------------------------------------------------------------------


def warp_attack_angle_deg(declination_deg: float, divergence_deg: float) -> float:
    """Ángulo de ataque del cable al flujo α = acos(cos δ1 · cos δ2) [°].

    El cable baja con la declinación δ1 en el plano vertical y abre con la divergencia δ2 en
    planta; el ángulo entre su eje y la dirección de arrastre combina ambos. Es el α que pide la
    tabla de Nomura–Yamazaki (:data:`WARP_CD_TABLE`). Errata ``warp_cd_horizontal_angle``: el
    libro usa sólo δ2 (Rem!E103 = E25 = 4.3°); para el caso FAO A-3 (δ1 = 12.06°) α = 12.80°.
    """
    c = np.cos(np.radians(declination_deg)) * np.cos(np.radians(divergence_deg))
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


def warp_cd(angle_deg: float, *, interpolate: bool = False) -> float:
    """CD del cable para el ángulo de ataque α según la tabla Nomura–Yamazaki (Rem!E106).

    * ``interpolate=False`` (libro): fila de α más cercano,
      ``E106 = INDEX(B90:B94, MATCH(MIN(ABS(α−x)), α−x, 1))`` (4.3° → 0° → 0.02).
    * ``interpolate=True`` (modo corregido, errata ``warp_cd_horizontal_angle``): interpolación
      lineal en :data:`WARP_CD_TABLE`, acotada a los extremos (0.02 por debajo de 0°, 0.30 por
      encima de 40°).
    """
    angles = np.array([a for a, _ in WARP_CD_TABLE])
    cds = np.array([c for _, c in WARP_CD_TABLE])
    if interpolate:
        return float(np.interp(angle_deg, angles, cds))
    idx = int(np.argmin(np.abs(angles - angle_deg)))
    return WARP_CD_TABLE[idx][1]


def warp_drag_kgf(
    cd: float,
    diameter_m: float,
    length_m: float,
    v_ms: FloatOrArray,
    n_warps: int = 2,
    rho_kg_m3: float = RHO_SEAWATER,
    g_m_s2: float = G,
) -> FloatOrArray:
    """Resistencia de los cables Rw = ½·CD·(ρ/g)·D·L·v²·n [kgf] (Rem!G118:G126, n = 2 cables).

    Nomura y Yamazaki, con CD de :func:`warp_cd` y D = diámetro en m (Rem!E111).
    """
    v = as_array(v_ms)
    return ret(0.5 * cd * (rho_kg_m3 / g_m_s2) * diameter_m * length_m * v**2 * n_warps, v_ms)


def total_drag_kgf(
    rn_kgf: FloatOrArray,
    rb_kgf: FloatOrArray,
    rw_kgf: FloatOrArray,
    rob_kgf: FloatOrArray = 0.0,
    compat: Compat = Compat.CORRECTED,
) -> FloatOrArray:
    """Resistencia total del arte = Rw + RB + RN (+ ROB) [kgf] (Rem!H118:I126).

    Errata ``warp_total_omits_doors``: ``H118 = G118+F118+D118`` suma cables, boyas y red pero
    omite la resistencia de los portones ROB. :attr:`Compat.EXCEL` reproduce la suma sin ROB;
    :attr:`Compat.CORRECTED` la incluye.
    """
    total = as_array(rw_kgf) + as_array(rb_kgf) + as_array(rn_kgf)
    if compat is Compat.CORRECTED:
        total = total + as_array(rob_kgf)
    like = rn_kgf if np.ndim(rn_kgf) else rw_kgf
    return ret(total, like)


def warp_cd_cylinder(
    speed_kn: FloatOrArray, cd_low: float = 1.1, cd_high: float = 1.2
) -> FloatOrArray:
    """CD del cable como cilindro en flujo cruzado: 1.1 hasta 2.5 kn y 1.2 desde 3 kn (Rem!E167).

    La hoja escribe los valores a mano por fila; se conserva el cambio en 3 nudos.
    """
    s = as_array(speed_kn)
    return ret(np.where(s >= 3.0, cd_high, cd_low).astype(float), speed_kn)


@dataclass(frozen=True)
class WarpCylinderDrag:
    """Resistencia del cable como cilindro (Rem!D167:G175)."""

    reynolds: FloatOrArray
    cd: FloatOrArray
    drag_one_kgf: FloatOrArray
    drag_two_kgf: FloatOrArray

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclass_to_dict(self)


def warp_drag_cylinder(
    diameter_m: float,
    length_m: float,
    v_ms: FloatOrArray,
    speed_kn: FloatOrArray,
    nu_m2_s: float | None = None,
    rho_kg_m3: float = RHO_SEAWATER,
    g_m_s2: float = G,
) -> WarpCylinderDrag:
    """Re = D·v/ν, CD (1.1/1.2) y Rw = ½·CD·(ρ/g)·D·L·v² [kgf] por cable y por los dos (Rem!D167).

    ``nu_m2_s`` por defecto es el promedio de :func:`kinematic_viscosity_m2_s`.
    """
    nu = kinematic_viscosity_m2_s() if nu_m2_s is None else nu_m2_s
    v = as_array(v_ms)
    cd = as_array(warp_cd_cylinder(speed_kn))
    re = diameter_m * v / nu
    one = 0.5 * cd * (rho_kg_m3 / g_m_s2) * diameter_m * length_m * v**2
    return WarpCylinderDrag(
        reynolds=ret(re, v_ms),
        cd=ret(cd, v_ms),
        drag_one_kgf=ret(one, v_ms),
        drag_two_kgf=ret(2.0 * one, v_ms),
    )


def warp_cd_maclennan(v_ms: FloatOrArray, diameter_m: float) -> FloatOrArray:
    """CD del cable según MacLennan: CD = 2.11 − 12.24·v·Dw (Dw en m) (Rem!D227:D235)."""
    return ret(2.11 - 12.24 * as_array(v_ms) * diameter_m, v_ms)


def warp_drag_share_kgf(ft_kgf: FloatOrArray, share: float) -> FloatOrArray:
    """Resistencia del cable como fracción del tiro FT [kgf] (Rem!E191:H199: 5 % y 10 %).

    Craig 4 %, Podeur 5–8 %, Hansen 5 %, Gudnasson 5–10 %, Nomura 4–10 % (Rem!D184:H184).
    """
    return ret(as_array(ft_kgf) * share, ft_kgf)


# ---------------------------------------------------------------------------
# Peso y selección del cable
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WarpWeight:
    """Peso del cable de remolque (Rem!E248:F257, E266)."""

    air_kg_m: float
    water_a_kg_m: float
    water_b_kg_m: float
    water_min_kg_m: float
    total_air_kg: float
    total_water_kg: float

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclass_to_dict(self)


def warp_weight(diameter_mm: float, length_m: float) -> WarpWeight:
    """Peso unitario y total del cable filado (Rem!B241:F257).

    * ``E248 = AVERAGE(0.00368·d², 0.00417·d²)`` [kg/m en aire];
    * ``F250 = 0.00305·d²`` y ``F252 = 0.87·E248`` [kg/m en agua];
    * ``E266 = AVERAGE(F252, F250)``; ``F256 = L·E248``; ``F257 = L·F252``.
    """
    d2 = diameter_mm**2
    air = (0.00368 * d2 + 0.00417 * d2) / 2.0
    water_a = 0.00305 * d2
    water_b = 0.87 * air
    return WarpWeight(
        air_kg_m=air,
        water_a_kg_m=water_a,
        water_b_kg_m=water_b,
        water_min_kg_m=(water_b + water_a) / 2.0,
        total_air_kg=length_m * air,
        total_water_kg=length_m * water_b,
    )


@dataclass(frozen=True)
class WarpLoads:
    """Carga de trabajo y carga mínima de rotura [kgf] (Rem!E267, E272)."""

    working_load_kgf: float
    safety_factor: float
    min_breaking_load_kgf: float

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclass_to_dict(self)


def working_load_and_breaking_load(
    total_drag_kgf: FloatOrArray,
    speeds_kn: FloatOrArray | None = None,
    design_speed_kn: float = 3.5,
    safety_factor: float = 4.0,
) -> WarpLoads:
    """Carga de trabajo = resistencia total a 3.5 kn (Rem!E267 = H123) y rotura mínima = ×4 (E272).

    Si ``total_drag_kgf`` es una serie se toma el valor en ``design_speed_kn`` de ``speeds_kn``.
    """
    if speeds_kn is None:
        working = float(as_array(total_drag_kgf))
    else:
        s = as_array(speeds_kn)
        t = as_array(total_drag_kgf)
        matches = np.flatnonzero(np.isclose(s, design_speed_kn))
        if matches.size == 0:
            raise ValueError(f"velocidad {design_speed_kn} kn no está en la serie")
        working = float(t[matches[0]])
    return WarpLoads(
        working_load_kgf=working,
        safety_factor=safety_factor,
        min_breaking_load_kgf=working * safety_factor,
    )


@dataclass(frozen=True)
class WarpSelection:
    """Cable seleccionado del catálogo ``trawlkit/data/warps.yaml`` (Cab!D11:I11)."""

    id: str
    construction: str
    diameter_mm: float
    weight_kg_per_m: float
    breaking_load_t: float
    satisfies_breaking_load: bool

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclass_to_dict(self)


def select_warp(
    min_diameter_mm: float,
    min_breaking_load_kgf: float,
    compat: Compat = Compat.CORRECTED,
    items: Sequence[dict[str, Any]] | None = None,
) -> WarpSelection:
    """Cable de acero del catálogo (6x19+1 Seale) para el diámetro y la carga de rotura requeridos.

    Errata ``warp_undersized``: ``Cab!D11 = LOOKUP(Rem!E264, diamremolque, …)`` elige por el
    diámetro mínimo (mayor Ø ≤ 12.28 mm → 12 mm, 8.55 t) e ignora la carga mínima de rotura
    Rem!E272 (8.8 t). :attr:`Compat.EXCEL` reproduce ese ``LOOKUP``; :attr:`Compat.CORRECTED`
    devuelve el menor diámetro que cumple a la vez Ø ≥ ``min_diameter_mm`` y
    rotura ≥ ``min_breaking_load_kgf`` (13 mm / 10.3 t para el modelo); si ninguno cumple,
    el más grueso del catálogo con ``satisfies_breaking_load = False``.

    ``items`` reemplaza al catálogo del libro (p. ej. los cables del catálogo de componentes
    filtrados por marca o región, Fase 13); cada ítem necesita ``id``, ``construction``,
    ``diameter_mm``, ``weight_kg_per_m`` y ``breaking_load_t``.
    """
    pool = load_catalogue("warps").items if items is None else list(items)
    if not pool:
        raise ValueError("no hay cables para elegir (revise los filtros de componentes)")
    items = sorted(pool, key=lambda it: float(it["diameter_mm"]))
    diameters = [float(it["diameter_mm"]) for it in items]
    if compat is Compat.EXCEL:
        chosen = items[excel_lookup_index(min_diameter_mm, diameters)]
    else:
        candidates = [
            it
            for it in items
            if float(it["diameter_mm"]) >= min_diameter_mm
            and float(it["breaking_load_t"]) * 1000.0 >= min_breaking_load_kgf
        ]
        # Si ninguno alcanza (artes grandes, fuera del rango del catálogo del libro), el más
        # grueso, con ``satisfies_breaking_load = False`` (nota ``warp_undersized`` del motor).
        chosen = candidates[0] if candidates else items[-1]
    return WarpSelection(
        id=str(chosen["id"]),
        construction=str(chosen["construction"]),
        diameter_mm=float(chosen["diameter_mm"]),
        weight_kg_per_m=float(chosen["weight_kg_per_m"]),
        breaking_load_t=float(chosen["breaking_load_t"]),
        satisfies_breaking_load=float(chosen["breaking_load_t"]) * 1000.0 >= min_breaking_load_kgf,
    )


def warp_quantity_m(warp_m: float, spare_fraction: float = 0.5) -> float:
    """Cable a comprar = 2·Ls + 0.5·Ls [m] (Cab!D12 = Rem!F255·2 + Rem!F255·0.5)."""
    return 2.0 * warp_m + spare_fraction * warp_m
