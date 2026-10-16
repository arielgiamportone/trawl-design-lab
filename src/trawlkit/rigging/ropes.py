"""Cabos de relingas (lima y burlón) y refuerzos: catálogo Moscuzza y peso en el agua.

Replica *Cables Y Cabulleria* A3:J5 y los pesos de *Flotación y Lastre* C29:F37 (lima) y
E182:H191 (burlón). Longitudes en m, diámetros en mm, pesos en kg.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from trawlkit.io import load_catalogue
from trawlkit.rigging._excel import dataclass_to_dict, excel_roundup

#: Fracción del peso en aire que pesa en el agua un cabo combinado (Flot!F37 = 0.087·W;
#: Flot!G191 = W·0.87/10, mismo valor).
ROPE_WATER_WEIGHT_COEF: float = 0.087


@dataclass(frozen=True)
class RopeSpec:
    """Cabo del catálogo ``data/ropes.yaml`` (Tab!A292:F296; Cab!D3:I4)."""

    id: str
    description: str
    diameter_mm: float
    weight_kg_per_m: float
    breaking_load_t: float

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclass_to_dict(self)


def select_rope(name: str) -> RopeSpec:
    """Cabo del catálogo por descripción (``"COMBINADO 12 Acero6x24+7"``) o por ``id``.

    Equivale a ``Cab!G3 = LOOKUP(resulmat, cabl, Tab!E293:E296)`` (kg/m), ``H3`` (resistencia [t])
    e ``I3`` (diámetro).
    """
    for item in load_catalogue("ropes").items:
        if name in (item.get("description"), item.get("id")):
            return RopeSpec(
                id=str(item["id"]),
                description=str(item["description"]),
                diameter_mm=float(item["diameter_mm"]),
                weight_kg_per_m=float(item["weight_kg_per_m"]),
                breaking_load_t=float(item["breaking_load_t"]),
            )
    raise KeyError(f"cabo desconocido: {name!r}")


def rope_weight_air_kg(length_m: float, weight_kg_per_m: float) -> float:
    """Peso del cabo en aire = L · kg/m [kg] (Flot!F36 = F31·F35; G188 = G184·G187)."""
    return length_m * weight_kg_per_m


def rope_weight_in_water_kg(weight_air_kg: float, coef: float = ROPE_WATER_WEIGHT_COEF) -> float:
    """Peso del cabo en el agua = coef · peso en aire [kg].

    Flot!F37 = 0.087·F36 (lima) y G191 = G188·0.87/10 (burlón): el mismo 0.087.
    """
    return weight_air_kg * coef


def wingtip_reinforcement_m(wingtip_m: float, factor: float = 4.0) -> float:
    """Refuerzo de la punta de ala = ROUNDUP(4·m_punta, 1) [m] (Cab!J5 con Dim!C155 = 2.88 m)."""
    return float(excel_roundup(factor * wingtip_m, 1))
