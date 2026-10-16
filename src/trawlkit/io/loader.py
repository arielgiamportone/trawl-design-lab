"""Carga de especificaciones YAML desde ``data/`` o desde rutas arbitrarias."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel

from trawlkit.io.schema import Catalogue, DoorCatalogue, NetSpec, VesselCatalogue

#: Carpeta ``data/`` del repositorio (cuando se trabaja desde el checkout).
DATA_DIR = Path(__file__).resolve().parents[3] / "data"

T = TypeVar("T", bound=BaseModel)


def load_yaml(path: Path | str, model: type[T]) -> T:
    """Lee un YAML y lo valida contra ``model``."""
    with Path(path).open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return model.model_validate(raw)


def load_net(name_or_path: str | Path) -> NetSpec:
    """Carga una red por nombre de preset (``fao_a3_standard``) o por ruta."""
    p = Path(name_or_path)
    if not p.exists():
        p = DATA_DIR / f"{name_or_path}.yaml"
    return load_yaml(p, NetSpec)


def load_vessels(path: Path | str | None = None) -> VesselCatalogue:
    """Carga el catálogo de buques."""
    return load_yaml(path or DATA_DIR / "vessels.yaml", VesselCatalogue)


def load_doors(path: Path | str | None = None) -> DoorCatalogue:
    """Carga el catálogo de portones."""
    return load_yaml(path or DATA_DIR / "doors.yaml", DoorCatalogue)


def load_catalogue(kind: str, path: Path | str | None = None) -> Catalogue:
    """Carga un catálogo genérico (``floats``, ``ropes``, ``chains``, ``warps``, ``materials``)."""
    return load_yaml(path or DATA_DIR / f"{kind}.yaml", Catalogue)
