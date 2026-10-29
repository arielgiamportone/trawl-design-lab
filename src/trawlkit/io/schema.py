"""Esquema de las especificaciones de entrada (pydantic v2).

Los archivos YAML de ``trawlkit/data/`` se validan contra estos modelos. Las unidades van en el
nombre del campo (``_m``, ``_mm``, ``_kg``, ``_kgf``) para que la spec sea legible sin consultar la
doc. Se admiten campos extra (``extra="allow"``) para no bloquear la extracción mientras el motor
crece.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class MeshOrientation(StrEnum):
    """Orientación de la malla del paño.

    ``diamond`` es la malla rómbica clásica (la diagonal larga de la malla estirada a lo largo de
    la red); ``t90`` es el mismo paño girado 90° (la diagonal larga queda a lo ancho); ``square``
    es la malla cuadrada, con los hilos a lo largo y a lo ancho de la red (paño cortado en barras).
    En malla cuadrada ``meshes_top``/``meshes_bottom``/``meshes_depth`` cuentan cuadrados de lado
    una pata (``mesh_mm / 2``).
    """

    DIAMOND = "diamond"
    T90 = "t90"
    SQUARE = "square"


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
    mesh_orientation: MeshOrientation = Field(
        default=MeshOrientation.DIAMOND,
        description="Orientación de la malla (rombo, T90, cuadrada)",
    )
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


class ProvenanceKind(StrEnum):
    """Cómo se obtuvo un valor de una spec."""

    EXCEL = "excel"  # celda del libro Excel original (``source_cells``)
    TRANSCRIBED = "transcribed"  # leído en una figura o tabla de un documento
    DERIVED = "derived"  # calculado a partir de valores transcriptos (fórmula en ``note``)
    ASSUMED = "assumed"  # el documento no lo da y el motor lo necesita (razón en ``note``)
    CALIBRATED = "calibrated"  # ajustado a mediciones publicadas (ajuste y series en ``note``)


class Provenance(_Model):
    """Procedencia de un valor: documento (clave bibliográfica), página, figura y tipo."""

    kind: ProvenanceKind = ProvenanceKind.TRANSCRIBED
    document: str | None = Field(default=None, description="Clave de docs/referencias.bib")
    page: str | None = None
    figure: str | None = None
    note: str | None = None


class SourceDocument(_Model):
    """Documento fuente de una spec digitalizada."""

    key: str = Field(description="Clave de docs/referencias.bib")
    title: str
    url: str | None = None
    accessed: str | None = Field(default=None, description="Fecha de consulta (AAAA-MM-DD)")
    figure: str | None = None
    page: str | None = None


NetFamily = Literal["bottom", "semi_pelagic", "pelagic"]
NetRig = Literal["otter", "pair", "outrigger", "twin", "beam"]


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
    # --- catálogo (Fase 12) -------------------------------------------------------------
    family: NetFamily | None = None
    rig: NetRig | None = None
    vessel_hp: tuple[float, float] | None = Field(
        default=None, description="Potencia del buque de diseño [hp] (mín, máx)"
    )
    target_species: str | None = None
    status: Literal["published", "draft"] = "published"
    sources: list[SourceDocument] = Field(default_factory=list)
    #: Procedencia por valor, por ruta de campo (``panels.C.meshes_top``, ``headrope.length_m``).
    provenance: dict[str, Provenance] = Field(default_factory=dict)


class VesselType(StrEnum):
    """Tipo de buque (estratos de la flota argentina; FAO 2005, Bertolotti et al. 2001)."""

    RADA_RIA = "rada_ria"  # flota de rada o ría (costera menor)
    COSTERO = "costero"  # flota costera (con bodega refrigerada o aislada)
    FRESQUERO = "fresquero"  # arrastrero fresquero de altura
    CONGELADOR = "congelador"  # arrastrero procesador congelador
    TANGONERO = "tangonero"  # langostinero con tangones
    INVESTIGACION = "investigacion"  # buque de investigación pesquera
    OTRO = "otro"


#: Hélices con tobera (``nozzle``) según :class:`PropellerType`.
NOZZLE_PROPELLERS: frozenset[PropellerType] = frozenset(
    {PropellerType.FIXED_PITCH_NOZZLE, PropellerType.VARIABLE_PITCH_NOZZLE}
)


class Vessel(_Model):
    """Buque pesquero.

    Los campos del libro (``bhp``, ``length_m``, ``beam_m``, ``depth_m``, ``displacement_t``,
    ``propeller``, ``high_rpm``) alimentan el motor desde la Fase 1. Los demás (Fase 19.4) son
    opcionales: datos de la hélice para el modelo de tiro por diámetro
    (:mod:`trawlkit.propulsion`), de la maniobra (pórtico, guinche y cable) para los controles del
    caso y de procedencia para el catálogo de la flota (``data/vessels/*.yaml``). ``length_m`` es
    la eslora que usa el motor (la total cuando se conoce; ``loa_m`` la repite y ``lpp_m`` es la
    eslora entre perpendiculares).
    """

    id: str
    name: str | None = None
    bhp: float = Field(gt=0)
    length_m: float | None = None
    beam_m: float | None = None
    depth_m: float | None = Field(default=None, description="Puntal [m]")
    displacement_t: float | None = None
    propeller: PropellerType = PropellerType.FIXED_PITCH
    high_rpm: bool = True
    # --- casco (Fase 19.4) --------------------------------------------------------------
    loa_m: float | None = Field(default=None, gt=0, description="Eslora total [m]")
    lpp_m: float | None = Field(default=None, gt=0, description="Eslora entre perpendiculares [m]")
    draft_m: float | None = Field(default=None, gt=0, description="Calado [m]")
    gross_tonnage: float | None = Field(
        default=None, gt=0, description="Arqueo bruto (TRB del registro o GT)"
    )
    # --- motor y hélice -----------------------------------------------------------------
    engine_kw: float | None = Field(default=None, gt=0, description="Potencia del motor [kW]")
    engine_rpm: float | None = Field(default=None, gt=0, description="RPM nominales del motor")
    gear_ratio: float | None = Field(default=None, gt=0, description="Reducción (motor:hélice)")
    propeller_diameter_m: float | None = Field(
        default=None, gt=0, description="Diámetro de la hélice [m]"
    )
    propeller_pitch_ratio: float | None = Field(default=None, gt=0, description="Paso/diámetro")
    propeller_blades: int | None = Field(default=None, ge=2, description="Número de palas")
    nozzle: bool | None = Field(
        default=None, description="Hélice con tobera (debe coincidir con ``propeller``)"
    )
    bollard_pull_t_measured: float | None = Field(
        default=None, gt=0, description="Tiro a punto fijo medido [t]"
    )
    sfc_g_kwh: float | None = Field(
        default=None, gt=0, description="Consumo específico de combustible [g/kWh]"
    )
    # --- maniobra -----------------------------------------------------------------------
    gallows_height_m: float | None = Field(
        default=None, gt=0, description="Altura de las pastecas sobre el agua [m]"
    )
    gallows_spacing_m: float | None = Field(
        default=None, gt=0, description="Distancia entre pastecas (pórticos) [m]"
    )
    winch_pull_t: float | None = Field(
        default=None, gt=0, description="Tiro del guinche a medio tambor [t]"
    )
    winch_drum_capacity_m: float | None = Field(
        default=None, gt=0, description="Capacidad de cable de cada tambor [m]"
    )
    warp_diameter_mm: float | None = Field(
        default=None, gt=0, description="Diámetro del cable para el que vale la capacidad [mm]"
    )
    # --- catálogo -----------------------------------------------------------------------
    vessel_type: VesselType | None = None
    #: Preset de tipo de buque (valores medios publicados de un estrato), no un casco real.
    typical: bool = False
    region: str | None = Field(default=None, description="Región (vocabulario de componentes)")
    home_port: str | None = None
    status: Literal["published", "draft"] = "published"
    sources: list[SourceDocument] = Field(default_factory=list)
    #: Procedencia por campo (``bhp``, ``length_m``…), como en :class:`NetSpec`.
    provenance: dict[str, Provenance] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _nozzle_matches_propeller(self) -> Vessel:
        """``nozzle`` y ``propeller`` deben decir lo mismo.

        Si sólo se da ``nozzle`` (``propeller`` por defecto) se completa la hélice: paso fijo con
        o sin tobera.
        """
        if self.nozzle is None:
            return self
        has = self.propeller in NOZZLE_PROPELLERS
        if self.nozzle == has:
            return self
        if "propeller" not in self.model_fields_set:
            self.propeller = (
                PropellerType.FIXED_PITCH_NOZZLE if self.nozzle else PropellerType.FIXED_PITCH
            )
            return self
        raise ValueError(
            f"nozzle={self.nozzle} is inconsistent with propeller={self.propeller.value!r}"
        )

    @property
    def has_nozzle(self) -> bool:
        """Si la hélice tiene tobera (``nozzle`` o, si falta, el tipo de hélice)."""
        return self.propeller in NOZZLE_PROPELLERS if self.nozzle is None else self.nozzle


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
    source: str | None = None
    notes: list[str] = Field(default_factory=list)


class DoorCatalogue(_Model):
    """Catálogo de portones."""

    doors: list[Door]
