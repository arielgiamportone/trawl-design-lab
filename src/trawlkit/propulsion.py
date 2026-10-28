"""Tiro por la hélice (Fase 19.4): *bollard pull* por diámetro y potencia, y controles de maniobra.

Los cinco métodos del libro (:mod:`trawlkit.power`) estiman el tiro sólo con el BHP y el tipo de
hélice. Cuando se conoce el **diámetro de la hélice** se puede usar la forma de Wärtsilä
(Wärtsilä Encyclopedia of Ship Technology, «Bollard pull»):

* ``T = (D·P_D)^(2/3)`` [kN] con ``D`` [m] y la potencia entregada ``P_D`` [kW];
* ``BP = T·k1·k2/9,81`` [t] con ``k1 = 0,9`` (10 % de pérdidas) y ``k2 = 1,2–1,4`` con tobera
  (sin tobera ``k2 = 1``, *derivado*: Wärtsilä da el factor como «adición» de la tobera).

Como control cruzado se da la teoría ideal de cantidad de movimiento (disco actuador, *derivado*):
hélice abierta ``T³ = 2ρA·P²`` (``T[kN] = 1,172·(D·P)^(2/3)`` con ρ = 1025 kg/m³) y tobera ideal
de relación de áreas 1 ``T³ = 4ρA·P²`` (un factor 2^(1/3) = 1,26 sobre la abierta).

El tiro a velocidad de arrastre ``v`` (*derivado*) escala el *bollard pull* con la caída del
empuje ideal del disco actuador a potencia constante, ``T_ideal(v)/T_ideal(0)`` (abierta o con
tobera ideal), y resta la resistencia del casco de Kartha y Roy Choudhury (1966),
«about 4 lbs/ton of displacement» a la velocidad de arrastre, cuando se conoce el
desplazamiento. El disco actuador es una cota ideal: el modelo da un tiro **optimista** (con los
datos medidos de Kartha, boat V, ≈ +25 %; ver ``docs/39_flota_argentina.md``).

La potencia entregada es ``P_D = 0,9·BHP`` (Kartha 1966: «max SHP = 0,9 × max BHP») en kW con
el hp métrico de :data:`trawlkit.units.HP_TO_KW`. Un tiro a punto fijo **medido**
(``Vessel.bollard_pull_t_measured``) reemplaza al de Wärtsilä como base de la curva.

Los controles del guinche siguen el *Fisherman's Workbook* (Prado y Dremière 1990, PDF p. 129):
tiro del guinche a medio tambor ≥ 80 % del *bollard pull* máximo, tiro máximo ≤ 1/3 de la rotura del
cable; la capacidad del tambor se compara con el cable filado más la reserva del libro (Cab!D12).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import numpy.typing as npt

from trawlkit.i18n import t
from trawlkit.io.schema import Vessel
from trawlkit.units import HP_TO_KW, KNOT_TO_MS

if TYPE_CHECKING:
    from trawlkit.model import DesignCase, PowerStage, WarpStage

FloatArray = npt.NDArray[np.float64]

#: Wärtsilä: k1 = 0,9 (10 % de pérdidas).
WARTSILA_K1: float = 0.9
#: Wärtsilä: rango de k2 con tobera (20-40 % de adición).
WARTSILA_K2_NOZZLE_RANGE: tuple[float, float] = (1.2, 1.4)
#: k2 con tobera usado por defecto: punto medio del rango (*derivado*: (1,2 + 1,4)/2).
WARTSILA_K2_NOZZLE: float = 1.3
#: k2 sin tobera (*derivado*: sin adición).
WARTSILA_K2_OPEN: float = 1.0
#: Gravedad con la que Wärtsilä pasa de kN a t (``BP = T·k1·k2/9,81``).
WARTSILA_G: float = 9.81
#: Kartha y Roy Choudhury (1966): potencia en el eje = 0,9·BHP.
SHAFT_OVER_BHP: float = 0.9
#: Kartha y Roy Choudhury (1966): resistencia del casco ≈ 4 lb por tonelada de desplazamiento.
KARTHA_HULL_LB_PER_T: float = 4.0
#: Libra-fuerza en kgf.
LB_TO_KG: float = 0.45359237
#: Densidad del agua de mar del disco actuador [kg/m³] (la del informe de la Fase 19.4).
RHO_ACTUATOR: float = 1025.0
#: Workbook (PDF p. 129): tiro del guinche a medio tambor ≥ 80 % del *bollard pull* máximo.
WINCH_PULL_OVER_BOLLARD: float = 0.8
#: Workbook (PDF p. 129): tiro máximo del guinche ≤ 1/3 de la rotura del cable.
WINCH_PULL_OVER_BREAKING: float = 1.0 / 3.0


# ----------------------------------------------------------------------------------------------
# Fórmulas
# ----------------------------------------------------------------------------------------------


def delivered_power_kw(
    bhp: float, shaft_fraction: float = SHAFT_OVER_BHP, hp_to_kw: float = HP_TO_KW
) -> float:
    """Potencia entregada a la hélice ``P_D = 0,9·BHP`` [kW] (Kartha y Roy Choudhury 1966)."""
    if bhp <= 0:
        raise ValueError(f"bhp must be positive, got {bhp}")
    return bhp * shaft_fraction * hp_to_kw


def wartsila_thrust_kn(diameter_m: float, power_kw: float) -> float:
    """Empuje de Wärtsilä ``T = (D·P_D)^(2/3)`` [kN], con ``D`` [m] y ``P_D`` [kW]."""
    if diameter_m <= 0 or power_kw <= 0:
        raise ValueError("diameter_m and power_kw must be positive")
    return float((diameter_m * power_kw) ** (2.0 / 3.0))


def nozzle_k2(nozzle: bool, k2: float | None = None) -> float:
    """k2 de Wärtsilä: 1 sin tobera; con tobera ``k2`` o el punto medio 1,3 del rango 1,2–1,4."""
    if not nozzle:
        return WARTSILA_K2_OPEN
    return WARTSILA_K2_NOZZLE if k2 is None else k2


def bollard_pull_wartsila_t(
    diameter_m: float,
    power_kw: float,
    nozzle: bool = False,
    *,
    k1: float = WARTSILA_K1,
    k2: float | None = None,
) -> float:
    """*Bollard pull* de Wärtsilä ``BP = (D·P_D)^(2/3)·k1·k2/9,81`` [t]."""
    return wartsila_thrust_kn(diameter_m, power_kw) * k1 * nozzle_k2(nozzle, k2) / WARTSILA_G


def momentum_thrust_kn(
    diameter_m: float,
    power_kw: float,
    v_ms: float = 0.0,
    nozzle: bool = False,
    rho: float = RHO_ACTUATOR,
) -> float:
    """Empuje ideal del disco actuador a potencia ``P`` y velocidad de avance ``v`` [kN].

    Hélice abierta: ``T = 2ρA·u·(v + u)`` y ``P = T·(v + u)``, con ``u`` la velocidad inducida en
    el disco. Tobera ideal (salida = disco): ``T = ρA·(v + w)·w`` y ``P = T·(v + w/2)``. En
    ``v = 0`` dan ``T³ = 2ρA·P²`` y ``T³ = 4ρA·P²``. *Derivado* (teoría de cantidad de
    movimiento); es una cota superior del empuje real.
    """
    if diameter_m <= 0 or power_kw <= 0:
        raise ValueError("diameter_m and power_kw must be positive")
    if v_ms < 0:
        raise ValueError(f"v_ms must be non-negative, got {v_ms}")
    area = math.pi * diameter_m**2 / 4.0
    p = power_kw * 1000.0
    if nozzle:

        def power_of(w: float) -> float:
            return rho * area * (v_ms + w) * w * (v_ms + w / 2.0)

        def thrust_of(w: float) -> float:
            return rho * area * (v_ms + w) * w

    else:

        def power_of(w: float) -> float:
            return 2.0 * rho * area * w * (v_ms + w) ** 2

        def thrust_of(w: float) -> float:
            return 2.0 * rho * area * w * (v_ms + w)

    # power_of es creciente en w ≥ 0: bisección.
    lo, hi = 0.0, 1.0
    while power_of(hi) < p:
        hi *= 2.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if power_of(mid) < p:
            lo = mid
        else:
            hi = mid
    return thrust_of(0.5 * (lo + hi)) / 1000.0


def bollard_pull_momentum_t(
    diameter_m: float, power_kw: float, nozzle: bool = False, rho: float = RHO_ACTUATOR
) -> float:
    """*Bollard pull* ideal del disco actuador [t] (sin pérdidas; control cruzado)."""
    return momentum_thrust_kn(diameter_m, power_kw, 0.0, nozzle, rho) / WARTSILA_G


def hull_resistance_kartha_kgf(displacement_t: float) -> float:
    """Resistencia del casco a la velocidad de arrastre ≈ 4 lb/t·Δ [kgf] (Kartha 1966)."""
    return KARTHA_HULL_LB_PER_T * LB_TO_KG * displacement_t


def towing_pull_kgf(
    bollard_pull_t: float,
    diameter_m: float,
    power_kw: float,
    speeds_kn: npt.ArrayLike,
    nozzle: bool = False,
    displacement_t: float | None = None,
) -> FloatArray:
    """Tiro disponible a cada velocidad [kgf] a partir del *bollard pull* ``BP`` [t].

    ``F(v) = 1000·BP·T_ideal(v)/T_ideal(0) − R_casco`` con ``T_ideal`` el empuje del disco
    actuador (abierto o con tobera ideal) a la misma potencia y ``R_casco`` = 4 lb/t·Δ (Kartha
    1966) para ``v > 0`` si se conoce el desplazamiento. *Derivado*; recortado a ≥ 0.
    """
    v = np.atleast_1d(np.asarray(speeds_kn, dtype=float))
    t0 = momentum_thrust_kn(diameter_m, power_kw, 0.0, nozzle)
    ratio = np.array([momentum_thrust_kn(diameter_m, power_kw, x * KNOT_TO_MS, nozzle) for x in v])
    out = 1000.0 * bollard_pull_t * ratio / t0
    if displacement_t is not None:
        out = out - np.where(v > 0, hull_resistance_kartha_kgf(displacement_t), 0.0)
    return np.asarray(np.maximum(out, 0.0), dtype=float)


def diameter_for_bollard_pull_m(
    bollard_pull_t: float,
    power_kw: float,
    nozzle: bool = False,
    *,
    k1: float = WARTSILA_K1,
    k2: float | None = None,
) -> float:
    """Diámetro con el que Wärtsilä da ``bollard_pull_t`` (inversa de la fórmula) [m]."""
    thrust = bollard_pull_t * WARTSILA_G / (k1 * nozzle_k2(nozzle, k2))
    return float(thrust**1.5 / power_kw)


# ----------------------------------------------------------------------------------------------
# Tiro por la hélice de un buque
# ----------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class PropellerPull:
    """Tiro por la hélice de un buque con diámetro conocido (Fase 19.4).

    ``bollard_pull_t`` es la base de la curva: el medido si el buque lo trae (``method =
    "measured"``) o el de Wärtsilä (``method = "wartsila"``). ``bollard_pull_prado_t`` es la regla
    del libro ``BHP·0,9·f/100`` (regla práctica de remolcadores de Zahalka, estimación gruesa; el
    Excel la atribuye a Prado) para comparar.
    """

    method: str
    source: str
    diameter_m: float
    delivered_kw: float
    nozzle: bool
    k1: float
    k2: float
    bollard_pull_t: float
    bollard_pull_wartsila_t: float
    bollard_pull_momentum_t: float
    bollard_pull_prado_t: float
    hull_resistance_kgf: float | None
    speeds_kn: FloatArray
    towing_kgf: FloatArray
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def kgf_per_bhp(self) -> float:
        """*Bollard pull* por BHP [kgf/BHP] (para comparar con los 10-16 kgf/BHP del Workbook)."""
        bhp = self.delivered_kw / (SHAFT_OVER_BHP * HP_TO_KW)
        return 1000.0 * self.bollard_pull_t / bhp

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "method": self.method,
            "source": self.source,
            "diameter_m": self.diameter_m,
            "delivered_kw": self.delivered_kw,
            "nozzle": self.nozzle,
            "k1": self.k1,
            "k2": self.k2,
            "bollard_pull_t": self.bollard_pull_t,
            "bollard_pull_wartsila_t": self.bollard_pull_wartsila_t,
            "bollard_pull_momentum_t": self.bollard_pull_momentum_t,
            "bollard_pull_prado_t": self.bollard_pull_prado_t,
            "hull_resistance_kgf": self.hull_resistance_kgf,
            "kgf_per_bhp": self.kgf_per_bhp,
            "speeds_kn": self.speeds_kn.tolist(),
            "towing_kgf": self.towing_kgf.tolist(),
            "notes": list(self.notes),
        }


#: Cita del método (va a la fila de la tabla de potencia y a la API).
PROPELLER_SOURCE = (
    "Wärtsilä Encyclopedia of Ship Technology, «Bollard pull»; Kartha y Roy Choudhury (1966)"
)


def propeller_pull(
    vessel: Vessel, speeds_kn: npt.ArrayLike, *, k2: float | None = None
) -> PropellerPull | None:
    """Tiro por la hélice del buque, o ``None`` si no se conoce el diámetro de la hélice."""
    from trawlkit.power import bollard_pull_t as prado_bollard_pull_t

    d = vessel.propeller_diameter_m
    if d is None:
        return None
    nozzle = vessel.has_nozzle
    pd = delivered_power_kw(vessel.bhp)
    k2v = nozzle_k2(nozzle, k2)
    bp_w = bollard_pull_wartsila_t(d, pd, nozzle, k2=k2v)
    measured = vessel.bollard_pull_t_measured
    base = bp_w if measured is None else measured
    notes: list[str] = []
    if nozzle and k2 is None:
        notes.append(
            t(
                "tobera: k2 = {k2:g}, punto medio del rango 1,2-1,4 de Wärtsilä (derivado)",
                k2=k2v,
            )
        )
    if measured is not None:
        notes.append(
            t(
                "tiro a punto fijo medido {bp:.2f} t (Wärtsilä estima {w:.2f} t)",
                bp=measured,
                w=bp_w,
            )
        )
    hull = (
        None if vessel.displacement_t is None else hull_resistance_kartha_kgf(vessel.displacement_t)
    )
    v = np.atleast_1d(np.asarray(speeds_kn, dtype=float))
    return PropellerPull(
        method="wartsila" if measured is None else "measured",
        source=PROPELLER_SOURCE,
        diameter_m=d,
        delivered_kw=pd,
        nozzle=nozzle,
        k1=WARTSILA_K1,
        k2=k2v,
        bollard_pull_t=base,
        bollard_pull_wartsila_t=bp_w,
        bollard_pull_momentum_t=bollard_pull_momentum_t(d, pd, nozzle),
        bollard_pull_prado_t=prado_bollard_pull_t(vessel.bhp, vessel.propeller),
        hull_resistance_kgf=hull,
        speeds_kn=v,
        towing_kgf=towing_pull_kgf(base, d, pd, v, nozzle, vessel.displacement_t),
        notes=tuple(notes),
    )


# ----------------------------------------------------------------------------------------------
# Controles de la maniobra (pórtico, guinche y cable)
# ----------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class WinchCheck:
    """Controles del guinche del buque frente al cable y las cargas del caso."""

    drum_capacity_m: float | None
    drum_capacity_effective_m: float | None
    drum_required_m: float
    winch_pull_t: float | None
    warp_tension_kgf: float | None
    bollard_pull_t: float
    bollard_pull_source: str
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "drum_capacity_m": self.drum_capacity_m,
            "drum_capacity_effective_m": self.drum_capacity_effective_m,
            "drum_required_m": self.drum_required_m,
            "winch_pull_t": self.winch_pull_t,
            "warp_tension_kgf": self.warp_tension_kgf,
            "bollard_pull_t": self.bollard_pull_t,
            "bollard_pull_source": self.bollard_pull_source,
            "warnings": list(self.warnings),
        }


def drum_required_m(warp_m: float, quantity_m: float) -> float:
    """Cable por tambor: la mitad del cable a comprar (Cab!D12 = 2·Ls + 0,5·Ls), nunca < ``Ls``."""
    return max(warp_m, quantity_m / 2.0)


def drum_capacity_for_diameter_m(capacity_m: float, rated_mm: float, warp_mm: float) -> float:
    """Capacidad del tambor con otro cable: ∝ 1/d² (volumen del tambor constante; *derivado*)."""
    return capacity_m * (rated_mm / warp_mm) ** 2


def winch_check(case: DesignCase, power: PowerStage, warps: WarpStage) -> WinchCheck | None:
    """Controla guinche y tambor del buque; ``None`` si el buque no trae datos del guinche."""
    from trawlkit.power import bollard_pull_t as prado_bollard_pull_t

    v = case.vessel
    if v.winch_drum_capacity_m is None and v.winch_pull_t is None:
        return None
    warnings: list[str] = []
    need = drum_required_m(warps.warp_m, warps.quantity_m)
    selected_mm = float(warps.selection.diameter_mm)
    cap = v.winch_drum_capacity_m
    cap_eff = cap
    if cap is not None and v.warp_diameter_mm is not None and selected_mm > v.warp_diameter_mm:
        cap_eff = drum_capacity_for_diameter_m(cap, v.warp_diameter_mm, selected_mm)
        warnings.append(
            t(
                "winch_warp_diameter: el cable elegido ({d:g} mm) es más grueso que el del "
                "guinche ({rated:g} mm); capacidad estimada {cap:.0f} m (∝ 1/d²)",
                d=selected_mm,
                rated=v.warp_diameter_mm,
                cap=cap_eff,
            )
        )
    if cap_eff is not None:
        if cap_eff < warps.warp_m:
            warnings.append(
                t(
                    "winch_drum_short: el tambor ({cap:.0f} m) no alcanza para el cable filado "
                    "({warp:.0f} m)",
                    cap=cap_eff,
                    warp=warps.warp_m,
                )
            )
        elif cap_eff < need:
            warnings.append(
                t(
                    "winch_drum_reserve: el tambor ({cap:.0f} m) alcanza para el cable filado "
                    "({warp:.0f} m) pero no para la reserva del libro ({need:.0f} m por tambor)",
                    cap=cap_eff,
                    warp=warps.warp_m,
                    need=need,
                )
            )
    pp = power.propeller
    if v.bollard_pull_t_measured is not None:
        bp, src = v.bollard_pull_t_measured, "measured"
    elif pp is not None:
        bp, src = pp.bollard_pull_t, pp.method
    else:
        bp, src = prado_bollard_pull_t(v.bhp, v.propeller), "prado"
    tension = None if warps.stretch is None else warps.stretch.tension_kgf
    pull = v.winch_pull_t
    if pull is not None:
        if tension is not None and pull * 1000.0 < tension:
            warnings.append(
                t(
                    "winch_pull_tension: el guinche ({pull:.2f} t) tira menos que la tensión de "
                    "cada cable a la velocidad de diseño ({tension:.0f} kgf)",
                    pull=pull,
                    tension=tension,
                )
            )
        if pull < WINCH_PULL_OVER_BOLLARD * bp:
            warnings.append(
                t(
                    "winch_pull_bollard: el guinche ({pull:.2f} t) tira menos del 80 % del tiro a "
                    "punto fijo ({bp:.2f} t; Prado y Dremière 1990)",
                    pull=pull,
                    bp=bp,
                )
            )
        mbl_t = float(warps.selection.breaking_load_t)
        if pull > WINCH_PULL_OVER_BREAKING * mbl_t:
            warnings.append(
                t(
                    "winch_pull_breaking: el tiro del guinche ({pull:.2f} t) supera 1/3 de la "
                    "rotura del cable elegido ({mbl:g} t; Prado y Dremière 1990)",
                    pull=pull,
                    mbl=mbl_t,
                )
            )
    return WinchCheck(
        drum_capacity_m=cap,
        drum_capacity_effective_m=cap_eff,
        drum_required_m=need,
        winch_pull_t=pull,
        warp_tension_kgf=tension,
        bollard_pull_t=bp,
        bollard_pull_source=src,
        warnings=tuple(warnings),
    )


__all__ = [
    "PROPELLER_SOURCE",
    "SHAFT_OVER_BHP",
    "WARTSILA_K1",
    "WARTSILA_K2_NOZZLE",
    "WARTSILA_K2_NOZZLE_RANGE",
    "PropellerPull",
    "WinchCheck",
    "bollard_pull_momentum_t",
    "bollard_pull_wartsila_t",
    "delivered_power_kw",
    "diameter_for_bollard_pull_m",
    "drum_capacity_for_diameter_m",
    "drum_required_m",
    "hull_resistance_kartha_kgf",
    "momentum_thrust_kn",
    "nozzle_k2",
    "propeller_pull",
    "towing_pull_kgf",
    "winch_check",
]
