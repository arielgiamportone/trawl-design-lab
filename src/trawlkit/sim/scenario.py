"""Escenario de operación de la simulación: captura en el copo, tipo de fondo y portones.

El simulador básico (:func:`trawlkit.sim.simulate`) resuelve la red limpia, vacía, con un
rozamiento único con el fondo y los portones fijos a la separación del motor. Un
:class:`Scenario` agrega las condiciones reales del lance:

* **Captura** (``catch_kg``): ocupa el extremo del copo con un volumen
  ``V = catch_kg / ρ_aparente`` (organismos más agua intersticial). Los hilos de esa zona dejan
  de filtrar (el flujo queda bloqueado por la captura) y reciben la presión de la "bola" de
  captura ``p = ½ ρ C_p U²`` normal al paño, más el peso sumergido de la captura. Es el modelo de
  O'Neill y O'Donoghue (1997, *Proc. R. Soc. A* 453:1631) para la forma del copo cargado, usado
  también por Priour (2014) y Herrmann (2005, PRESEMO).
* **Fondo** (``seabed``): tipo de sedimento del catálogo ``data/seabed.yaml``, con rozamientos
  distintos para el tren de fondo y el paño (``mu_gear``) y para las zapatas de los portones
  (``mu_door``).
* **Portones acoplados** (``coupled_doors``): los portones dejan de ser puntos fijos. Cada uno
  es un nodo libre con la sustentación y el arrastre de su polar (C_L, C_D al ángulo de ataque
  del caso), su peso en el agua, el rozamiento con el fondo y el cable de remolque discretizado
  hasta el buque. La separación entre portones sale del equilibrio y cambia con la captura y con
  el fondo, como observaron Priour y de la Prada (2015, *Ocean Eng.* 94:94).
"""

from __future__ import annotations

from dataclasses import dataclass

from trawlkit.rigging.seabed import Range, Seabed, seabed, seabeds

__all__ = ["Range", "Scenario", "Seabed", "seabed", "seabeds"]

#: Densidad aparente por defecto de la captura en el copo [kg/m³] (A VERIFICAR: peces y agua
#: intersticial; ~0,6–0,75 del volumen ocupado por organismos de ~1070 kg/m³).
DEFAULT_CATCH_BULK_DENSITY = 750.0
#: Densidad de los organismos [kg/m³] (peces óseos ~1050–1080; crustáceos ~1100–1200).
DEFAULT_CATCH_BODY_DENSITY = 1070.0
#: Coeficiente de presión de la bola de captura (O'Neill y O'Donoghue 1997: ~1; A VERIFICAR).
DEFAULT_CATCH_CP = 1.0


@dataclass(frozen=True)
class Scenario:
    """Condiciones del lance (ver el docstring del módulo).

    Todo es opcional: el valor por defecto reproduce el simulador básico, salvo ``coupled_doors``.
    """

    catch_kg: float = 0.0
    catch_bulk_density: float = DEFAULT_CATCH_BULK_DENSITY
    catch_body_density: float = DEFAULT_CATCH_BODY_DENSITY
    catch_cp: float = DEFAULT_CATCH_CP
    seabed: str | None = None
    mu_gear: float | None = None
    mu_door: float | None = None
    coupled_doors: bool = True

    def __post_init__(self) -> None:
        """Valida rangos físicos."""
        if self.catch_kg < 0:
            raise ValueError("catch_kg debe ser ≥ 0")
        if not 200.0 <= self.catch_bulk_density <= 1300.0:
            raise ValueError("catch_bulk_density fuera de rango (200–1300 kg/m³)")
        if not 900.0 <= self.catch_body_density <= 2000.0:
            raise ValueError("catch_body_density fuera de rango (900–2000 kg/m³)")
        if not 0.0 <= self.catch_cp <= 3.0:
            raise ValueError("catch_cp fuera de rango (0–3)")
        for name in ("mu_gear", "mu_door"):
            v = getattr(self, name)
            if v is not None and not 0.0 <= v <= 1.5:
                raise ValueError(f"{name} fuera de rango (0–1,5)")
        if self.seabed is not None:
            seabed(self.seabed)  # KeyError si no existe

    @property
    def catch_volume_m3(self) -> float:
        """Volumen que ocupa la captura en el copo [m³]."""
        return self.catch_kg / self.catch_bulk_density

    def catch_weight_water_n(self, rho_water: float = 1024.0, g: float = 9.80665) -> float:
        """Peso sumergido de la captura [N] (organismos, sin el agua intersticial)."""
        return self.catch_kg * g * (1.0 - rho_water / self.catch_body_density)

    def friction(self, default_mu: float) -> tuple[float, float]:
        """(μ del tren y del paño, μ de los portones) del escenario."""
        sb = seabed(self.seabed) if self.seabed else None
        gear = (
            self.mu_gear if self.mu_gear is not None else (sb.mu_gear.nominal if sb else default_mu)
        )
        door = self.mu_door if self.mu_door is not None else (sb.mu_door.nominal if sb else gear)
        return gear, door
