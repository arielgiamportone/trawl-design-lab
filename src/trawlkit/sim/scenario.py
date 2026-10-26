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
from functools import cache
from typing import Any

import yaml

from trawlkit.i18n import t
from trawlkit.io.loader import DATA_DIR
from trawlkit.rigging.seabed import Range, Seabed, seabed, seabeds

__all__ = [
    "Fouling",
    "Range",
    "Scenario",
    "Seabed",
    "fouling",
    "fouling_catalogue",
    "seabed",
    "seabeds",
]

#: Zona de la red de cada sección de panel (para el ensuciamiento).
FOULING_ZONE: dict[str, str] = {
    "wing_tip": "wings",
    "wing": "wings",
    "square": "body",
    "belly": "body",
    "body": "body",
    "extension": "codend",
    "codend": "codend",
}


@dataclass(frozen=True)
class Fouling:
    """Escenario de ensuciamiento: nivel 0–1 por zona (alas, cuerpo, copo)."""

    id: str
    name: str
    zones: dict[str, float]
    notes: str

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {"id": self.id, "name": self.name, "zones": dict(self.zones), "notes": self.notes}


@cache
def _fouling_raw() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load((DATA_DIR / "fouling.yaml").read_text(encoding="utf-8"))
    return data


def fouling_catalogue() -> tuple[Fouling, ...]:
    """Escenarios de ensuciamiento (``data/fouling.yaml``)."""
    return tuple(
        Fouling(
            id=str(it["id"]),
            name=str(it["name"]),
            zones={str(k): float(v) for k, v in it["zones"].items()},
            notes=str(it.get("notes", "")),
        )
        for it in _fouling_raw()["items"]
    )


def fouling(key: str) -> Fouling:
    """Escenario de ensuciamiento por ``id``."""
    for f in fouling_catalogue():
        if f.id == key:
            return f
    raise KeyError(t("escenario de ensuciamiento desconocido: {key!r}", key=key))


def fouling_coefficients() -> dict[str, float]:
    """Ganancias de diámetro, C_N y peso por unidad de nivel de ensuciamiento."""
    return {k: float(v) for k, v in _fouling_raw()["coefficients"].items()}


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
    #: Ensuciamiento: escenario del catálogo y factor sobre sus niveles (0 = limpio).
    fouling: str | None = None
    fouling_level: float = 1.0
    #: Corriente a lo largo del rumbo [kn] (+ a favor: el agua relativa a la red es más lenta).
    current_kn: float = 0.0
    #: Largo de cable filado [m] (None = el del motor).
    warp_length_m: float | None = None
    #: Duración del lance [h] (para combustible por kg de captura).
    haul_hours: float = 2.0
    #: Rigidez de apertura de la malla: None = sólo si hay paños T90 o de malla cuadrada.
    mesh_bending: bool | None = None
    mesh_bending_factor: float = 1.0
    #: Factores sobre la sustentación y el arrastre de la polar del portón (incertidumbre y
    #: calibración; 1 = la polar del catálogo).
    door_cl_factor: float = 1.0
    door_cd_factor: float = 1.0

    def __post_init__(self) -> None:
        """Valida rangos físicos."""
        if self.catch_kg < 0:
            raise ValueError(t("catch_kg debe ser ≥ 0"))
        if not 200.0 <= self.catch_bulk_density <= 1300.0:
            raise ValueError(t("catch_bulk_density fuera de rango (200–1300 kg/m³)"))
        if not 900.0 <= self.catch_body_density <= 2000.0:
            raise ValueError(t("catch_body_density fuera de rango (900–2000 kg/m³)"))
        if not 0.0 <= self.catch_cp <= 3.0:
            raise ValueError(t("catch_cp fuera de rango (0–3)"))
        for name in ("mu_gear", "mu_door"):
            v = getattr(self, name)
            if v is not None and not 0.0 <= v <= 1.5:
                raise ValueError(t("{name} fuera de rango (0–1,5)", name=name))
        if self.seabed is not None:
            seabed(self.seabed)  # KeyError si no existe
        if self.fouling is not None:
            fouling(self.fouling)
        if not 0.0 <= self.fouling_level <= 2.0:
            raise ValueError(t("fouling_level fuera de rango (0–2)"))
        if not -2.0 <= self.current_kn <= 2.0:
            raise ValueError(t("current_kn fuera de rango (−2 a 2 kn)"))
        if self.warp_length_m is not None and not 20.0 <= self.warp_length_m <= 3000.0:
            raise ValueError(t("warp_length_m fuera de rango (20–3000 m)"))
        if not 0.1 <= self.haul_hours <= 24.0:
            raise ValueError(t("haul_hours fuera de rango (0,1–24 h)"))
        if not 0.0 <= self.mesh_bending_factor <= 20.0:
            raise ValueError(t("mesh_bending_factor fuera de rango (0–20)"))
        for name in ("door_cl_factor", "door_cd_factor"):
            if not 0.3 <= getattr(self, name) <= 2.0:
                raise ValueError(t("{name} fuera de rango (0,3–2)", name=name))

    def fouling_zones(self) -> dict[str, float]:
        """Nivel de ensuciamiento efectivo por zona (alas, cuerpo, copo)."""
        if self.fouling is None:
            return {"wings": 0.0, "body": 0.0, "codend": 0.0}
        return {k: v * self.fouling_level for k, v in fouling(self.fouling).zones.items()}

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
