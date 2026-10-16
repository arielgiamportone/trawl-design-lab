"""Esquema de las especificaciones de entrada (pydantic v2).

Los archivos YAML de ``data/`` se validan contra estos modelos. Las unidades van en el nombre del
campo (``_m``, ``_mm``, ``_kg``, ``_kgf``) para que la spec sea legible sin consultar la doc.
Se admiten campos extra (``extra="allow"``) para no bloquear la extracción mientras el motor crece.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _Model(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class Plane(StrEnum):
    """Plano (cara) de la red al que pertenece un panel."""

    UPPER = "upper"
    LOWER = "lower"
    SIDE = "side"


class Section(StrEnum):
    """Sección estructural de la red."""

    WING_TIP = "wing_tip"
    WING = "wing"
    SQUARE = "square"
    BELLY = "belly"
    BODY = "body"
    EXTENSION = "extension"
    CODEND = "codend"


class PropellerType(StrEnum):
    """Tipo de hélice (nomenclatura del modelo original)."""

    FIXED_PITCH = "fixed_pitch"  # PF
    FIXED_PITCH_NOZZLE = "fixed_pitch_nozzle"  # PF+T
    VARIABLE_PITCH = "variable_pitch"  # PV
    VARIABLE_PITCH_NOZZLE = "variable_pitch_nozzle"  # PV+T


class Species(_Model):
    """Especie objetivo."""

    name: str
    scientific_name: str | None = None
    depth_m: float | None = None
    bottom_type: str | None = None


class Panel(_Model):
    """Panel (paño) de red, definido por su compostura y sus mallas.

    ``meshes_top`` es el número de mallas del borde del panel más cercano a la boca de la red (donde
    el panel empieza) y ``meshes_bottom`` el del borde más cercano a la bolsa, como se leen en el
    plano 2D; ``meshes_depth`` es el número de mallas de alto (N). El Excel usa en cambio T1/T2 =
    borde mayor/menor, que se conservan en los extras ``meshes_a``/``meshes_b``.
    """

    id: str
    name: str | None = None
    plane: Plane
    section: Section
    material: str = "PA"
    mesh_mm: float = Field(gt=0, description="Tamaño de malla estirada [mm]")
    twine_diameter_mm: float = Field(gt=0)
    rtex: float | None = None
    runnage_m_per_kg: float | None = None
    meshes_top: int = Field(ge=0)
    meshes_bottom: int = Field(ge=0)
    meshes_depth: int = Field(ge=1)
    hanging_ratio: float | None = Field(default=None, ge=0, le=1)
    count: int = Field(default=1, ge=1, description="Cantidad de paneles iguales")
    cut_code: str | None = None
    source_cells: dict[str, str] | None = Field(default=None, description="Procedencia en el Excel")


class Rope(_Model):
    """Cabo o relinga."""

    name: str
    length_m: float | None = None
    diameter_mm: float | None = None
    weight_kg_per_m: float | None = None
    breaking_load_t: float | None = None


class FloatSpec(_Model):
    """Flotadores de la lima."""

    count: int
    diameter_mm: float
    buoyancy_kgf_each: float | None = None
    total_buoyancy_kgf: float | None = None


class NetSpec(_Model):
    """Especificación completa de una red de arrastre."""

    id: str
    name: str
    description: str | None = None
    source: str | None = None
    variant_of: str | None = None
    species: Species | None = None
    panels: list[Panel]
    headrope: Rope | None = None
    footrope: Rope | None = None
    floats: FloatSpec | None = None
    ballast_kg: float | None = None
    notes: list[str] = Field(default_factory=list)


class Vessel(_Model):
    """Buque pesquero."""

    id: str
    name: str | None = None
    bhp: float = Field(gt=0)
    length_m: float | None = None
    beam_m: float | None = None
    depth_m: float | None = Field(default=None, description="Puntal [m]")
    displacement_t: float | None = None
    propeller: PropellerType = PropellerType.FIXED_PITCH
    high_rpm: bool = True


class DoorCoefficients(_Model):
    """Coeficientes hidrodinámicos de un portón a un ángulo de ataque."""

    angle_deg: float
    cl: float | None = None
    cd: float | None = None


class Door(_Model):
    """Portón (puerta) de arrastre."""

    id: str
    name: str
    type: str | None = None
    length_m: float | None = None
    height_m: float | None = None
    area_m2: float | None = None
    aspect_ratio: float | None = None
    weight_air_kg: float | None = None
    weight_water_kg: float | None = None
    coefficients: list[DoorCoefficients] = Field(default_factory=list)


class Catalogue(_Model):
    """Catálogo genérico (boyas, cabos, cadenas, cables, materiales)."""

    kind: str
    source: str | None = None
    items: list[dict[str, Any]]


class VesselCatalogue(_Model):
    """Catálogo de buques."""

    vessels: list[Vessel]


class DoorCatalogue(_Model):
    """Catálogo de portones."""

    doors: list[Door]
