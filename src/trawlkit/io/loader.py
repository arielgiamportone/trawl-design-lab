"""Carga de especificaciones YAML desde ``trawlkit/data/`` o desde rutas arbitrarias."""

from __future__ import annotations

from functools import cache
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


#: Carpeta del catálogo de la flota (Fase 19.4); los buques del libro siguen en ``vessels.yaml``.
VESSELS_DIR = DATA_DIR / "vessels"


def vessel_files() -> list[Path]:
    """Archivos de buques: ``vessels.yaml`` (los dos de la A-3) y luego ``vessels/*.yaml``."""
    return [DATA_DIR / "vessels.yaml", *sorted(VESSELS_DIR.glob("*.yaml"))]


def load_vessels(path: Path | str | None = None) -> VesselCatalogue:
    """Carga el catálogo de buques del libro (``vessels.yaml``: la clase de la A-3).

    Es la «clase» de buques del libro (150 y 180 BHP): sin ``path`` no incluye la flota de
    ``vessels/``, que se carga con :func:`load_fleet`.
    """
    return load_yaml(path or DATA_DIR / "vessels.yaml", VesselCatalogue)


def load_fleet() -> VesselCatalogue:
    """Catálogo completo: los buques del libro primero y después los de ``vessels/*.yaml``.

    El orden es estable (archivo por archivo, en el orden de cada archivo); un id repetido es un
    error.
    """
    vessels = []
    seen: set[str] = set()
    for path in vessel_files():
        for v in load_yaml(path, VesselCatalogue).vessels:
            if v.id in seen:
                raise ValueError(f"{path}: duplicated vessel id {v.id!r}")
            seen.add(v.id)
            vessels.append(v)
    return VesselCatalogue(vessels=vessels)


def load_doors(path: Path | str | None = None) -> DoorCatalogue:
    """Carga el catálogo de portones."""
    return load_yaml(path or DATA_DIR / "doors.yaml", DoorCatalogue)


def load_catalogue(kind: str, path: Path | str | None = None) -> Catalogue:
    """Carga un catálogo genérico (``floats``, ``ropes``, ``chains``, ``warps``, ``materials``).

    Los catálogos del paquete se leen una sola vez por proceso (el motor los consulta en cada
    corrida y la tabla de materiales es grande); no hay que modificar el objeto devuelto.
    """
    if path is None:
        return _packaged_catalogue(kind)
    return load_yaml(path, Catalogue)


@cache
def _packaged_catalogue(kind: str) -> Catalogue:
    return load_yaml(DATA_DIR / f"{kind}.yaml", Catalogue)
