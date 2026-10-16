"""Esquemas de entrada y salida de la API (contrato estable para el frontend)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trawlkit.io.schema import Door, NetSpec, Vessel


class DesignRequest(BaseModel):
    """Caso de diseño a calcular.

    ``net``, ``net_modified``, ``vessel`` y ``door`` aceptan el id de un preset del catálogo
    (``GET /catalog/...``) o la especificación completa en línea (para redes editadas en el
    frontend). ``class_vessels`` son ids del catálogo; si se omite, se usa el resto del catálogo
    como hace el Excel con 150 y 180 HP. ``params`` sobrescribe parámetros de ``DesignCase``
    (ver ``GET /params``).
    """

    model_config = ConfigDict(extra="forbid")

    net: str | NetSpec = "fao_a3_standard"
    net_modified: str | NetSpec | None = None
    vessel: str | Vessel | None = None
    door: str | Door | None = None
    class_vessels: list[str] | None = None
    compat: Literal["excel", "corrected"] = "corrected"
    params: dict[str, Any] = Field(default_factory=dict)


class DesignResponse(BaseModel):
    """Resultado de ``POST /design``."""

    case: dict[str, Any]
    summary: dict[str, Any]
    notes: list[str]
    result: dict[str, Any]


class CatalogItem(BaseModel):
    """Entrada resumida de un catálogo."""

    id: str
    name: str | None = None
    description: str | None = None


class ParamInfo(BaseModel):
    """Parámetro sobrescribible de ``DesignCase``."""

    name: str
    type: str
    default: Any
    comment: str = ""


class ErratumOut(BaseModel):
    """Errata del modelo Excel original."""

    key: str
    sheet: str
    cell: str
    description: str


class Health(BaseModel):
    """Estado del servicio."""

    status: str
    version: str


class OptimizeGrid(BaseModel):
    """Malla inicial de la optimización (una corrida del motor por escala)."""

    model_config = ConfigDict(extra="forbid")

    n_s: int = Field(default=13, ge=2, le=25, description="Puntos en la escala s")
    n_v: int = Field(default=11, ge=2, le=25, description="Puntos en la velocidad v")


class OptimizeRequest(BaseModel):
    """Optimización de la escala de la red ``s`` y la velocidad ``v`` (``POST /optimize``).

    ``net``, ``vessel`` y ``door`` aceptan id del catálogo o especificación en línea, como en
    ``DesignRequest``. ``objective``: ``area`` (máx. área barrida por hora), ``energy`` (mín.
    R_T/AH) o ``volume`` (máx. volumen filtrado por hora). ``margin`` es la reserva de tiro
    (F_T ≥ (1+margin)·R_T); ``s_bounds`` y ``v_bounds`` [kn] acotan la búsqueda; ``refine`` activa
    la evolución diferencial (con ``seed``) después de la malla.
    """

    model_config = ConfigDict(extra="forbid")

    net: str | NetSpec = "fao_a3_standard"
    vessel: str | Vessel | None = None
    door: str | Door | None = None
    class_vessels: list[str] | None = None
    objective: Literal["area", "energy", "volume"] = "area"
    margin: float = Field(default=0.1, ge=0.0, le=2.0)
    s_bounds: tuple[float, float] = (0.6, 1.4)
    v_bounds: tuple[float, float] = (1.5, 4.0)
    grid: OptimizeGrid = Field(default_factory=OptimizeGrid)
    refine: bool = True
    seed: int = Field(default=0, ge=0)
    propeller: Literal["fixed_pitch", "variable_pitch_nozzle"] | None = None
    door_angle: float | None = Field(default=None, gt=0.0, lt=90.0)

    @model_validator(mode="after")
    def _check_bounds(self) -> OptimizeRequest:
        s_lo, s_hi = self.s_bounds
        v_lo, v_hi = self.v_bounds
        if not 0.3 <= s_lo < s_hi <= 2.0:
            raise ValueError("s_bounds debe cumplir 0.3 ≤ s_min < s_max ≤ 2.0")
        if not 0.5 <= v_lo < v_hi <= 6.0:
            raise ValueError("v_bounds debe cumplir 0.5 ≤ v_min < v_max ≤ 6.0 kn")
        return self


class ConstraintOut(BaseModel):
    """Restricción evaluada (``lower ≤ value ≤ upper``)."""

    name: str
    value: float | None
    lower: float | None
    upper: float | None
    ok: bool
    violation: float | None
    description: str = ""


class EvaluationOut(BaseModel):
    """Diseño ``(s, v)`` evaluado."""

    s: float
    v_kn: float
    net_id: str
    vessel_id: str
    door_id: str
    propeller: str
    ah_m: float | None
    dpa_fridman_m: float | None
    av_m: float | None
    av_fridman_m: float | None
    area_rate_m2_h: float | None
    volume_rate_m3_h: float | None
    demand_kgf: float | None
    available_kgf: float | None
    thrust_margin: float | None
    energy_kgf_m_per_m2: float | None
    net_drag_kgf: float | None
    dpa_geometric_m: float | None
    headrope_m: float | None
    footrope_m: float | None
    door_area_m2: float | None
    door_required_m2: float | None
    warp_id: str | None
    constraints: list[ConstraintOut]
    feasible: bool
    penalty: float | None


class OptimizeResponse(BaseModel):
    """Resultado de ``POST /optimize`` (``OptimizationResult.to_dict()``)."""

    objective: str
    feasible: bool
    best: EvaluationOut
    grid_best: EvaluationOut | None
    pareto: list[EvaluationOut]
    grid: dict[str, Any]
    settings: dict[str, Any]
    refine: dict[str, Any] | None
    runtime_s: float
    engine_runs: int


PlanView = Literal["sheet", "scale"]
Variant = Literal["std", "mod"]
ReportFormat = Literal["html", "pdf", "xlsx"]
