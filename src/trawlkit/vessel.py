"""Buque: reparto de la energía del motor y velocidad de Almirantazgo.

Reimplementa la hoja ``'Potenc disponible para arrastre'`` del modelo Excel. El reparto sigue a
Fridman (FAO): aproximadamente un tercio de la energía del motor se pierde antes de la hélice y,
de la que llega a la hélice (BHP), sólo un tercio se emplea en tirar de la red; el resto se gasta
en hacer girar la hélice (35 %), formación de olas (27 %), rozamiento del forro (18 %), estela y
turbulencia (17 %) y resistencia del aire (3 %).

Celdas de referencia: bloque de 150 BHP en ``C24:E31`` y de 180 BHP en ``C36:E43``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from trawlkit.io.schema import Vessel
from trawlkit.units import HP_TO_KW_EXCEL

#: Fracción del BHP que se añade para obtener los HP nominales (``C24 = C25 + C25·0.33``).
NOMINAL_OVER_BHP: float = 0.33
#: Fracción del BHP disponible para el tiro de la red (``C26 = C25·0.33``).
TOWING_FRACTION: float = 0.33
#: Pérdidas de la energía que llega a la hélice, como fracción del BHP (``C27:C31``).
LOSS_FRACTIONS: dict[str, float] = {
    "propeller_rotation": 0.35,
    "wave_making": 0.27,
    "hull_friction": 0.18,
    "wake_turbulence": 0.17,
    "air": 0.03,
}
#: Coeficiente de Almirantazgo usado en ``H27``/``H38``.
ADMIRALTY_COEFFICIENT: float = 285.0


@dataclass(frozen=True)
class PowerBudget:
    """Reparto de la potencia del motor según Fridman (``'Potenc disponible'!A24:E31``).

    Todas las potencias en HP; las propiedades ``*_kw`` aplican el factor ``hp_to_kw`` (0.745 en el
    Excel, columna E).
    """

    bhp: float
    nominal_hp: float
    towing_hp: float
    propeller_loss_hp: float
    wave_loss_hp: float
    friction_loss_hp: float
    wake_loss_hp: float
    air_loss_hp: float
    hp_to_kw: float = HP_TO_KW_EXCEL

    @property
    def bhp_kw(self) -> float:
        """BHP en kW (``E25 = C25·0.745``)."""
        return self.bhp * self.hp_to_kw

    @property
    def nominal_kw(self) -> float:
        """HP nominales en kW (``E24``)."""
        return self.nominal_hp * self.hp_to_kw

    @property
    def towing_kw(self) -> float:
        """Potencia de tiro en kW (``E26``)."""
        return self.towing_hp * self.hp_to_kw

    @property
    def propeller_loss_kw(self) -> float:
        """Pérdida por giro de hélice en kW (``E27``)."""
        return self.propeller_loss_hp * self.hp_to_kw

    @property
    def wave_loss_kw(self) -> float:
        """Pérdida por oleaje en kW (``E28``)."""
        return self.wave_loss_hp * self.hp_to_kw

    @property
    def friction_loss_kw(self) -> float:
        """Pérdida por rozamiento en kW (``E29``)."""
        return self.friction_loss_hp * self.hp_to_kw

    @property
    def wake_loss_kw(self) -> float:
        """Pérdida por estela y turbulencia en kW (``E30``)."""
        return self.wake_loss_hp * self.hp_to_kw

    @property
    def air_loss_kw(self) -> float:
        """Pérdida por resistencia del aire en kW (``E31``)."""
        return self.air_loss_hp * self.hp_to_kw

    @property
    def losses_hp(self) -> float:
        """Suma de las cinco pérdidas en HP (= BHP, ya que las fracciones suman 1.0)."""
        return (
            self.propeller_loss_hp
            + self.wave_loss_hp
            + self.friction_loss_hp
            + self.wake_loss_hp
            + self.air_loss_hp
        )

    def to_dict(self) -> dict[str, Any]:
        """Serializa campos y propiedades derivadas en un diccionario plano."""
        return {
            "bhp": self.bhp,
            "bhp_kw": self.bhp_kw,
            "nominal_hp": self.nominal_hp,
            "nominal_kw": self.nominal_kw,
            "towing_hp": self.towing_hp,
            "towing_kw": self.towing_kw,
            "propeller_loss_hp": self.propeller_loss_hp,
            "propeller_loss_kw": self.propeller_loss_kw,
            "wave_loss_hp": self.wave_loss_hp,
            "wave_loss_kw": self.wave_loss_kw,
            "friction_loss_hp": self.friction_loss_hp,
            "friction_loss_kw": self.friction_loss_kw,
            "wake_loss_hp": self.wake_loss_hp,
            "wake_loss_kw": self.wake_loss_kw,
            "air_loss_hp": self.air_loss_hp,
            "air_loss_kw": self.air_loss_kw,
            "hp_to_kw": self.hp_to_kw,
        }


def nominal_hp(bhp: float, nominal_fraction: float = NOMINAL_OVER_BHP) -> float:
    """HP nominales del motor a partir del BHP en hélice.

    ``HP_nom = BHP + BHP·0.33`` (Fridman: un tercio se pierde antes de la hélice).
    Unidades: HP. Celda ``'Potenc disponible'!C24`` (``=C25+(C25*0.33)``).
    """
    return bhp + bhp * nominal_fraction


def towing_hp(bhp: float, towing_fraction: float = TOWING_FRACTION) -> float:
    """HP disponibles para tirar de la red.

    ``HP_tiro = BHP·0.33`` (Fridman). Unidades: HP. Celda ``C26`` (``=(C25*0.33)``).
    """
    return bhp * towing_fraction


def power_budget(
    bhp: float,
    *,
    nominal_fraction: float = NOMINAL_OVER_BHP,
    towing_fraction: float = TOWING_FRACTION,
    losses: dict[str, float] | None = None,
    hp_to_kw: float = HP_TO_KW_EXCEL,
) -> PowerBudget:
    """Reparto de energía de Fridman para un motor de ``bhp`` HP en hélice.

    * ``HP_nom = BHP·(1 + 0.33)`` (``C24``);
    * ``HP_tiro = 0.33·BHP`` (``C26``);
    * pérdidas ``BHP·{0.35, 0.27, 0.18, 0.17, 0.03}`` (``C27:C31``);
    * kW = HP·0.745 (``E24:E31``).

    Unidades: HP (kW por propiedades). Autor: Fridman (FAO). Celdas ``C24:E31`` (150 BHP) y
    ``C36:E43`` (180 BHP). ``losses`` admite sobrescribir las fracciones con las mismas claves de
    :data:`LOSS_FRACTIONS`.
    """
    if bhp <= 0:
        raise ValueError(f"bhp must be positive, got {bhp}")
    frac = {**LOSS_FRACTIONS, **(losses or {})}
    return PowerBudget(
        bhp=bhp,
        nominal_hp=nominal_hp(bhp, nominal_fraction),
        towing_hp=towing_hp(bhp, towing_fraction),
        propeller_loss_hp=bhp * frac["propeller_rotation"],
        wave_loss_hp=bhp * frac["wave_making"],
        friction_loss_hp=bhp * frac["hull_friction"],
        wake_loss_hp=bhp * frac["wake_turbulence"],
        air_loss_hp=bhp * frac["air"],
        hp_to_kw=hp_to_kw,
    )


def admiralty_speed_kn(
    nominal_hp: float,
    displacement_t: float,
    admiralty_coefficient: float = ADMIRALTY_COEFFICIENT,
) -> float:
    """Velocidad según la fórmula del Almirantazgo.

    ``v = ((HP_nom · C) / Δ^(2/3))^(1/3)`` con ``C = 285`` y ``Δ`` el desplazamiento en t.
    Unidades: nudos (según el rótulo del Excel; la fórmula se aplica tal cual). Celdas
    ``'Potenc disponible'!H27`` (``=((C24*285)/(10^(2/3)))^(1/3)``, Δ = 10 t para 150 BHP) y
    ``H38`` (Δ = 12 t para 180 BHP; el desplazamiento está incrustado en la fórmula).
    """
    if displacement_t <= 0:
        raise ValueError(f"displacement_t must be positive, got {displacement_t}")
    return float(
        ((nominal_hp * admiralty_coefficient) / displacement_t ** (2.0 / 3.0)) ** (1.0 / 3.0)
    )


def vessel_power_budget(vessel: Vessel, **kwargs: Any) -> PowerBudget:
    """Reparto de energía para un :class:`~trawlkit.io.schema.Vessel` del catálogo."""
    return power_budget(vessel.bhp, **kwargs)


def vessel_admiralty_speed_kn(vessel: Vessel) -> float:
    """Velocidad de Almirantazgo de un buque del catálogo (requiere ``displacement_t``)."""
    if vessel.displacement_t is None:
        raise ValueError(f"vessel {vessel.id!r} has no displacement_t")
    return admiralty_speed_kn(nominal_hp(vessel.bhp), vessel.displacement_t)
