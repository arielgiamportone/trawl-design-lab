"""Aberturas de la red: DPA (distancia entre puntas de alas) y AV (abertura vertical).

Replica de *Mecánica de la Red*: fuerzas del portón y DPA de Fridman (B162:Q172), datos de
maniobra (B175:F186), tabla 2·Yn (B191:M201), DPA geométrica (L211, L225), DPA por ángulo de corte
(L233), AV por porcentaje (F245:F247, K242:K245), Suzuki (D255), Martini (E269:E272) y
Baranov–Fridman (J250:P282); y *Dimensiones de la Red*!F61 (abertura horizontal promedio).

Convenciones: longitudes en m, fuerzas en kgf, velocidades en m/s, ángulos en grados.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import cache
from typing import Any

import numpy as np

from trawlkit.compat import Compat
from trawlkit.excel import (
    FloatOrArray,
    as_array,
    dataclass_to_dict,
    excel_round,
    excel_rounddown,
    excel_roundup,
    ret,
)
from trawlkit.i18n import N_
from trawlkit.io import DATA_DIR
from trawlkit.io.schema import Provenance, ProvenanceKind
from trawlkit.rigging.doors import door_forces_kgf
from trawlkit.rigging.warps import warp_depth_ratio
from trawlkit.units import RHO_SEAWATER, G

#: Porcentajes de la circunferencia máxima según Prado y Dremiere (Mec!H245:H247).
AV_PRADO_SHARES: dict[str, float] = {
    "low_opening": 0.055,
    "high_opening": 0.065,
    "shellfish": 0.065,
}
#: Porcentajes de la circunferencia máxima según A. Izzo, INIDEP (Mec!J242:K245).
AV_IZZO_SHARES: tuple[float, ...] = (0.0435, 0.05, 0.06, 0.07)

#: Relación flecha/largo de la catenaria usada por la hoja (Mec!O266, valor fijo).
CATENARY_RATIO_EXCEL: float = 0.216

#: Corrección del exponente del cable en la DPA de Fridman (Fase 20.5, sólo modo corregido):
#: ``DPA_cal = DPA · (Ls / Ls_tabla)^Δn`` con ``Ls_tabla`` el cable que el libro tabula para la
#: profundidad (Mec!E177). Ajuste por mínimos cuadrados en logaritmos, con un nivel por serie, a
#: los 103 lances con cable publicado de IAT 151/18, IC 012/21 e IC 016/24
#: (:func:`trawlkit.fieldcheck.warp_exponent_fit`); errata ``fridman_dp_warp_saturation``.
DP_WARP_EXPONENT_CORRECTION: float = 0.10

#: Procedencia de :data:`DP_WARP_EXPONENT_CORRECTION`.
DP_WARP_EXPONENT_PROVENANCE = Provenance(
    kind=ProvenanceKind.CALIBRATED,
    document="bartozzetti2018iat151",
    page="IAT 151/2018, tabla 1; IC 012/2021, anexo; IC 016/2024, anexo I",
    note=N_(
        "Δn ajustado por mínimos cuadrados en log(DP medida / DP del motor) contra "
        "log(cable / cable de la tabla), con un nivel por serie, a IAT 151/18 "
        "(bartozzetti2018iat151), IC 012/21 (roth2021ic012) e IC 016/24 "
        "(rubio2024calibracion); validación cruzada dejando una serie afuera"
    ),
)


# ---------------------------------------------------------------------------
# Datos de maniobra
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TowingGeometry:
    """Datos de maniobra (Mec!E176:E186)."""

    depth_m: float
    warp_depth_ratio: float
    warp_m: float
    warp_horizontal_shallow_m: float
    warp_horizontal_deep_m: float
    net_length_m: float
    u2: float
    net_length_working_m: float
    bridle_m: float

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclass_to_dict(self)


def towing_geometry(
    depth_m: float,
    net_length_m: float,
    bridle_m: float,
    u2: float = 0.87,
    shallow_factor: float = 0.95,
    deep_factor: float = 0.85,
    warp_m: float | None = None,
) -> TowingGeometry:
    """Cable filado y proyecciones para la DPA de Fridman (Mec!B175:F186).

    * ``E177 = d · LOOKUP(d, Tab!A354:A383, Tab!C354:C383)`` (Ls);
    * ``F179 = 0.95·Ls`` (Lsh, poca profundidad) y ``F180 = 0.85·Ls`` (mayor profundidad);
    * ``E185 = LR·U2`` (largo de red trabajando) con LR = largo sin bolsa (``Largototal``);
    * ``E186`` = brida superior Lnc (Dim!F68).

    ``warp_m`` (Fase 20.2) reemplaza el cable de la tabla por uno medido (el cable filado de un
    lance publicado); la relación cable/profundidad pasa a ser ``warp_m / depth_m``. Los métodos
    no cambian.
    """
    if warp_m is None:
        ratio = warp_depth_ratio(depth_m)
        warp = depth_m * ratio
    else:
        warp = float(warp_m)
        ratio = warp / depth_m
    return TowingGeometry(
        depth_m=depth_m,
        warp_depth_ratio=ratio,
        warp_m=warp,
        warp_horizontal_shallow_m=shallow_factor * warp,
        warp_horizontal_deep_m=warp * deep_factor,
        net_length_m=net_length_m,
        u2=u2,
        net_length_working_m=net_length_m * u2,
        bridle_m=bridle_m,
    )


def table_warp_m(depth_m: float) -> float:
    """Cable que el libro tabula para la profundidad, ``d · LOOKUP(d)`` [m] (Mec!E177)."""
    return depth_m * warp_depth_ratio(depth_m)


def dp_warp_factor(
    warp_m: float,
    depth_m: float,
    compat: Compat = Compat.CORRECTED,
    exponent: float = DP_WARP_EXPONENT_CORRECTION,
) -> float:
    """Factor de cable de la DPA de Fridman ``(Ls / Ls_tabla)^Δn`` (Fase 20.5).

    En la DPA de Fridman (:func:`dpa_fridman_m`) el cable horizontal Lsh está arriba y abajo de
    la fracción y la DPA se satura con el cable; en el mar sigue creciendo (errata
    ``fridman_dp_warp_saturation``). Vale 1 en modo :attr:`Compat.EXCEL` y con el cable de la
    tabla del libro (:func:`table_warp_m`), es decir, en todo caso de diseño; sólo actúa con un
    cable distinto (``DesignCase.measured_warp_m``).
    """
    if compat is Compat.EXCEL:
        return 1.0
    return float((warp_m / table_warp_m(depth_m)) ** exponent)


# ---------------------------------------------------------------------------
# Fridman: fuerzas del portón, Edx/Edy y DPA
# ---------------------------------------------------------------------------


def expansion_coefficients(
    door_drag_kgf: FloatOrArray, door_lift_kgf: FloatOrArray, rn_kgf: FloatOrArray
) -> tuple[FloatOrArray, FloatOrArray]:
    """Coeficientes de Fridman Edx = Rd/(RN/2) y Edy = Fdy/(RN/2) (Mec!L164:O172)."""
    half_rn = 0.5 * as_array(rn_kgf)
    return (
        ret(as_array(door_drag_kgf) / half_rn, rn_kgf),
        ret(as_array(door_lift_kgf) / half_rn, rn_kgf),
    )


def dpa_fridman_m(
    warp_horizontal_m: float,
    net_length_working_m: float,
    edy: FloatOrArray,
    bridle_m: float,
    edx: FloatOrArray,
) -> FloatOrArray:
    """DPA de Fridman = 2·Lsh·LRw·Edy / (Lsh + Lnc·(1 + Edx)) [m] (Mec!P164/Q164).

    ``warp_horizontal_m`` = Lsh (Mec!F179), ``net_length_working_m`` = LR·U2 (E185),
    ``bridle_m`` = Lnc (E186).
    """
    e_y = as_array(edy)
    e_x = as_array(edx)
    num = 2.0 * warp_horizontal_m * net_length_working_m * e_y
    den = warp_horizontal_m + bridle_m * (1.0 + e_x)
    return ret(num / den, edy)


@dataclass(frozen=True)
class FridmanSpread:
    """Fuerzas del portón, Edx/Edy y DPA de Fridman, red estándar y modificada (Mec!H164:Q172)."""

    door_drag_kgf: FloatOrArray
    door_lift_kgf: FloatOrArray
    edx_std: FloatOrArray
    edx_mod: FloatOrArray
    edy_std: FloatOrArray
    edy_mod: FloatOrArray
    dpa_std_m: FloatOrArray
    dpa_mod_m: FloatOrArray

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclass_to_dict(self)


def fridman_spread(
    door_area_m2: float,
    door_cd: float,
    door_cl: float,
    v_ms: FloatOrArray,
    rn_std_kgf: FloatOrArray,
    rn_mod_kgf: FloatOrArray,
    warp_horizontal_m: float,
    net_length_working_m: float,
    bridle_m: float,
    rho_kg_m3: float = RHO_SEAWATER,
    g_m_s2: float = G,
    compat: Compat = Compat.CORRECTED,
    warp_factor: float = 1.0,
) -> FridmanSpread:
    """Bloque completo "Fuerzas del portón y DPA Fridman" (Mec!B162:Q172).

    Rd y Fdy con :func:`trawlkit.rigging.doors.door_forces_kgf`; Edx/Edy con
    :func:`expansion_coefficients`; DPA con :func:`dpa_fridman_m`.

    Errata ``dpa_std_uses_mod_edy``: ``P164 = 2*($F$179*$E$185*$O164)/(...)`` usa ``$O164``
    (Edy de la red **modificada**) en la columna estándar. :attr:`Compat.EXCEL` reproduce el
    cruce; :attr:`Compat.CORRECTED` usa Edy estándar (``$N164``).

    ``warp_factor`` (Fase 20.5, :func:`dp_warp_factor`) multiplica las dos DPA; vale 1 en el
    libro.
    """
    forces = door_forces_kgf(door_area_m2, door_cd, door_cl, v_ms, rho_kg_m3, g_m_s2)
    edx_std, edy_std = expansion_coefficients(forces.drag_kgf, forces.lift_kgf, rn_std_kgf)
    edx_mod, edy_mod = expansion_coefficients(forces.drag_kgf, forces.lift_kgf, rn_mod_kgf)
    edy_for_std = edy_mod if compat is Compat.EXCEL else edy_std
    return FridmanSpread(
        door_drag_kgf=forces.drag_kgf,
        door_lift_kgf=forces.lift_kgf,
        edx_std=edx_std,
        edx_mod=edx_mod,
        edy_std=edy_std,
        edy_mod=edy_mod,
        dpa_std_m=_scaled(
            dpa_fridman_m(warp_horizontal_m, net_length_working_m, edy_for_std, bridle_m, edx_std),
            warp_factor,
        ),
        dpa_mod_m=_scaled(
            dpa_fridman_m(warp_horizontal_m, net_length_working_m, edy_mod, bridle_m, edx_mod),
            warp_factor,
        ),
    )


def _scaled(value: FloatOrArray, factor: float) -> FloatOrArray:
    return value if factor == 1.0 else ret(as_array(value) * factor, value)


@dataclass(frozen=True)
class FridmanDpaTable:
    """Tabla Yn / 2·Yn / distancia entre portones (Mec!I193:M201)."""

    yn_std_m: FloatOrArray
    yn_mod_m: FloatOrArray
    dpa_std_m: FloatOrArray
    dpa_mod_m: FloatOrArray
    door_spread_from_dpa_m: FloatOrArray

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclass_to_dict(self)


def door_spread_from_dpa_m(
    dpa_m: FloatOrArray,
    footrope_m: float,
    crowfoot_m: float,
    crowfoot_extension_m: float,
    sweeps_m: float,
    bridle_m: float,
) -> FloatOrArray:
    """Distancia entre portones desde la DPA = DPA·(PG + APG + LP + Vs + m)/m [m] (Mec!M193).

    ``m`` es el largo del burlón (Mec!E209).
    """
    rigging = crowfoot_m + crowfoot_extension_m + sweeps_m + bridle_m + footrope_m
    return ret(as_array(dpa_m) * rigging / footrope_m, dpa_m)


def dpa_fridman_table(
    dpa_std_m: FloatOrArray,
    dpa_mod_m: FloatOrArray,
    footrope_m: float,
    crowfoot_m: float,
    crowfoot_extension_m: float,
    sweeps_m: float,
    bridle_m: float,
) -> FridmanDpaTable:
    """Yn = DPA/2 (I193/J193), 2·Yn (K193/L193) y Ds desde la DPA modificada (M193).

    ``M193 = (L193*($E$211+$E$212+$E$213+$E$214+$E$209))/$E$209`` usa la columna modificada.
    """
    yn_std = as_array(dpa_std_m) / 2.0
    yn_mod = as_array(dpa_mod_m) / 2.0
    return FridmanDpaTable(
        yn_std_m=ret(yn_std, dpa_std_m),
        yn_mod_m=ret(yn_mod, dpa_mod_m),
        dpa_std_m=ret(2.0 * yn_std, dpa_std_m),
        dpa_mod_m=ret(2.0 * yn_mod, dpa_mod_m),
        door_spread_from_dpa_m=door_spread_from_dpa_m(
            2.0 * yn_mod, footrope_m, crowfoot_m, crowfoot_extension_m, sweeps_m, bridle_m
        ),
    )


# ---------------------------------------------------------------------------
# DPA geométrica y por ángulo de corte
# ---------------------------------------------------------------------------


def dpa_geometric_m(
    footrope_m: float,
    door_spread_m: float,
    crowfoot_m: float,
    crowfoot_extension_m: float,
    sweeps_m: float,
    bridle_m: float,
) -> float:
    """DPA geométrica = ROUNDDOWN(burlón·Ds/(PG + APG + LP + Vs + burlón), 0) [m] (Mec!L211)."""
    rigging = crowfoot_m + crowfoot_extension_m + sweeps_m + bridle_m + footrope_m
    return float(excel_rounddown((footrope_m * door_spread_m) / rigging))


def dpa_geometric_working_m(
    door_spread_m: float,
    net_length_working_m: float,
    crowfoot_m: float,
    crowfoot_extension_m: float,
    sweeps_m: float,
    bridle_m: float,
) -> float:
    """DPA con LR trabajando = ROUNDUP(Ds·LRw/(LRw + PG + APG + LP + Vs), 0) [m] (Mec!L225)."""
    rigging = crowfoot_m + crowfoot_extension_m + sweeps_m + bridle_m
    return float(
        excel_roundup((door_spread_m * net_length_working_m) / (net_length_working_m + rigging))
    )


def dpa_from_cut_angle_m(net_length_total_m: float, u2: float, cut_angle_deg: float) -> float:
    """DPA por ángulo de corte = 2·b·U2·tan α [m] (Mec!L233; Prado).

    ``net_length_total_m`` es el largo total del vientre incluida la bolsa (Dim!F47) y
    ``cut_angle_deg`` el ángulo promedio de los cortes (Paños!K278).
    """
    return 2.0 * net_length_total_m * u2 * float(np.tan(np.radians(cut_angle_deg)))


def horizontal_opening_m(
    dpa_cut_angle_m: float,
    dpa_working_m: float,
    dpa_geometric_m: float,
    dpa_fridman_std_m: FloatOrArray,
) -> float:
    """Abertura horizontal AH = AVERAGE(L233, L225, L211, AVERAGE(K193:K201)) [m] (Dim!F61).

    El promedio de la serie de Fridman (2·Yn estándar, 1–5 kn) cuenta como un solo término.
    """
    fridman_avg = float(np.mean(as_array(dpa_fridman_std_m)))
    return (dpa_cut_angle_m + dpa_working_m + dpa_geometric_m + fridman_avg) / 4.0


# ---------------------------------------------------------------------------
# Abertura vertical
# ---------------------------------------------------------------------------


def stretched_circumference_m(meshes: float, mesh_mm: float) -> float:
    """Circunferencia a malla estirada = mallas · mallero / 1000 [m] (Dim!F49, Mec!E269)."""
    return meshes * mesh_mm / 1000.0


def vertical_opening_pct_m(circumference_m: float, share: float) -> float:
    """AV como porcentaje de la circunferencia máxima a malla estirada [m].

    Prado y Dremiere: 5.5 % (poca AV), 6.5 % (mucha AV y marisquera) (Mec!F245:F247);
    A. Izzo (INIDEP): 4.35, 5, 6 y 7 % (Mec!K242:K245).
    """
    return circumference_m * share


def vertical_opening_suzuki_m(circumference_m: float) -> float:
    """AV según N. Suzuki (JICA 1982) = 4/90 · a [m] (Mec!D255)."""
    return (4.0 / 90.0) * circumference_m


def vertical_opening_martini_m(
    dv_m: float, mr_meshes: float, mesh_mm: float, factor: float = 0.05
) -> float:
    """AV según Martini nivel 2 = (DV − MR·mallero/1000)·0.05 [m] (Mec!E272).

    ``dv_m`` es la circunferencia estirada del primer paño de dorso + vientre (E269) y
    ``mr_meshes`` las mallas relingadas en los bordes de unión (E270 = 3·4 = 12).
    """
    return (dv_m - (mr_meshes * mesh_mm) / 1000.0) * factor


def fridman_flotation_total_kgf(*flotations_kgf: float) -> float:
    """Flotación total Ffz = promedio de los métodos (Mec!O261 = AVERAGE(Flot!N43,N55,F17,G17))."""
    return float(np.mean(flotations_kgf))


@cache
def _catenary_table() -> tuple[tuple[float, float], ...]:
    """Pares ``(DPA/L, fL/L)`` de ``trawlkit/data/reference/catenary.csv`` (Tab!A119:D162)."""
    path = DATA_DIR / "reference" / "catenary.csv"
    with path.open(encoding="utf-8", newline="") as fh:
        rows = [(float(r["dpa_l"]), float(r["fl_l"])) for r in csv.DictReader(fh)]
    return tuple(rows)


def catenary_ratio(dpa_over_l: float) -> float:
    """Relación flecha/largo fL/L de la catenaria para el DPA/L más cercano (Tab!A116:D162).

    La hoja redondea DPA/L a 2 decimales (Mec!P265 = ROUND(O265, 2)) pero escribe 0.216 a mano
    en O266, que es el valor tabulado para DPA/L = 0.87 (no para 0.45): ver
    :data:`CATENARY_RATIO_EXCEL`.
    """
    key = float(excel_round(dpa_over_l, 2))
    table = _catenary_table()
    idx = int(np.argmin([abs(r[0] - key) for r in table]))
    return table[idx][1]


def headrope_sag_m(headrope_m: float, ratio: float = CATENARY_RATIO_EXCEL) -> float:
    """Flecha de la lima fL = (fL/L)·L [m] (Mec!O267 = O266·O260, O266 = 0.216)."""
    return ratio * headrope_m


@dataclass(frozen=True)
class FridmanVerticalOpening:
    """AV según Baranov–Fridman (Mec!M272:O282)."""

    angle_deg: FloatOrArray
    av_m: FloatOrArray
    av_average_m: float

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclass_to_dict(self)


def vertical_opening_fridman(
    rn_kgf: FloatOrArray,
    flotation_kgf: float,
    headrope_sag_m: float,
    bridle_m: float,
    dan_leno_m: float,
) -> FridmanVerticalOpening:
    """AV = dan leno + (fL + Vs)·sin α, con α = atan(2·Ffz/RN) [m] (Mec!M272, O272, O282).

    ``O282 = AVERAGE(O272:O280)`` promedia las nueve velocidades (1–5 kn).
    """
    rn = as_array(rn_kgf)
    alpha = np.degrees(np.arctan((2.0 * flotation_kgf) / rn))
    av = dan_leno_m + (headrope_sag_m + bridle_m) * np.sin(np.radians(alpha))
    return FridmanVerticalOpening(
        angle_deg=ret(alpha, rn_kgf),
        av_m=ret(av, rn_kgf),
        av_average_m=float(np.mean(av)),
    )
