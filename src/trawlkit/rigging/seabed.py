"""Catálogo de tipos de fondo (``data/seabed.yaml``): rozamiento del tren y de los portones.

Lo usan el motor empírico (término opcional de rozamiento en la demanda, ``DesignCase.seabed``)
y el simulador (:mod:`trawlkit.sim.scenario`). Los coeficientes son estimaciones con rango
("A VERIFICAR"): no hay una tabla publicada por sedimento para artes de arrastre.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from typing import Any

import yaml

from trawlkit.io.loader import DATA_DIR


@dataclass(frozen=True)
class Range:
    """Valor nominal y rango [mín, máx]."""

    nominal: float
    low: float
    high: float


@dataclass(frozen=True)
class Seabed:
    """Tipo de fondo del catálogo."""

    id: str
    name: str
    aliases: tuple[str, ...]
    mu_gear: Range
    mu_door: Range
    penetration: str
    notes: str

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "id": self.id,
            "name": self.name,
            "aliases": list(self.aliases),
            "mu_gear": {
                "nominal": self.mu_gear.nominal,
                "range": [self.mu_gear.low, self.mu_gear.high],
            },
            "mu_door": {
                "nominal": self.mu_door.nominal,
                "range": [self.mu_door.low, self.mu_door.high],
            },
            "penetration": self.penetration,
            "notes": self.notes,
        }


def _range(d: dict[str, Any]) -> Range:
    lo, hi = (float(v) for v in d["range"])
    nominal = float(d["nominal"])
    if not lo <= nominal <= hi:
        raise ValueError(f"nominal {nominal} fuera de [{lo}, {hi}]")
    return Range(nominal, lo, hi)


@cache
def seabeds() -> tuple[Seabed, ...]:
    """Catálogo de tipos de fondo (``data/seabed.yaml``)."""
    raw = yaml.safe_load((DATA_DIR / "seabed.yaml").read_text(encoding="utf-8"))
    return tuple(
        Seabed(
            id=str(it["id"]),
            name=str(it["name"]),
            aliases=tuple(str(a) for a in it.get("aliases", ())),
            mu_gear=_range(it["mu_gear"]),
            mu_door=_range(it["mu_door"]),
            penetration=str(it["penetration"]),
            notes=str(it.get("notes", "")),
        )
        for it in raw["items"]
    )


def seabed(key: str) -> Seabed:
    """Tipo de fondo por ``id`` o por alias en castellano (``"Intermedio"`` → ``mixed``)."""
    k = key.strip().lower()
    for s in seabeds():
        if k == s.id or k == s.name.lower() or k in s.aliases:
            return s
    raise KeyError(f"tipo de fondo desconocido: {key!r}")
