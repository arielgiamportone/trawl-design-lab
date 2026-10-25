"""Carga de especificaciones YAML desde ``trawlkit/data/`` o desde rutas arbitrarias."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel

from trawlkit.io.schema import Catalogue, DoorCatalogue, NetSpec, VesselCatalogue


def _data_dir() -> Path:
    """Carpeta de datos empaquetada ``trawlkit/data`` (``src/trawlkit/data`` en el checkout).

    Se resuelve con :func:`importlib.resources.files`, de modo que funciona igual desde el
    checkout (instalación editable) que desde una rueda instalada.
    """
    return Path(str(files("trawlkit") / "data"))


#: Carpeta de datos del paquete: presets de red, buques, catálogos y ``reference/*.csv``.
DATA_DIR: Path = _data_dir()

T = TypeVar("T", bound=BaseModel)


def load_yaml(path: Path | str, model: type[T]) -> T:
    """Lee un YAML y lo valida contra ``model``."""
    with Path(path).open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return model.model_validate(raw)


#: Carpeta del catálogo de redes digitalizadas (Fase 12); la FAO A-3 sigue en ``DATA_DIR``.
NETS_DIR = DATA_DIR / "nets"


def net_files() -> list[Path]:
    """Archivos de redes: los de ``DATA_DIR`` con paneles y los de ``DATA_DIR/nets``."""
    return sorted(DATA_DIR.glob("*.yaml")) + sorted(NETS_DIR.glob("*.yaml"))


def load_net(name_or_path: str | Path) -> NetSpec:
    """Carga una red por nombre de preset (``fao_a3_standard``, ``bobp_wp13_ho80``) o por ruta."""
    p = Path(name_or_path)
    if not p.exists():
        p = DATA_DIR / f"{name_or_path}.yaml"
        if not p.exists():
            p = NETS_DIR / f"{name_or_path}.yaml"
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
