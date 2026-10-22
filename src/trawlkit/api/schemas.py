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


class ScaledNetRequest(BaseModel):
    """Red escalada geométricamente por ``s`` (``POST /optimize/scaled-net``).

    ``net`` es el id de un preset o una especificación en línea; el resultado es la
    ``NetSpec`` de :func:`trawlkit.optimize.scale_net` (mismo mallero e hilo, ``s`` veces más
    mallas por borde), lista para usar como red en línea de ``POST /design``.
    """

    model_config = ConfigDict(extra="forbid")

    net: str | NetSpec = "fao_a3_standard"
    s: float = Field(ge=0.3, le=2.0, description="Factor de escala de la red")


#: Límites de ``SimulateRequest``.
SIM_MAX_SPEEDS = 9
SIM_SPEED_RANGE = (0.5, 6.0)
SIM_RESOLUTION_RANGE = (2, 10)


class SimulateRequest(BaseModel):
    """Simulación cuasiestática de la forma de la red (``POST /simulate``).

    ``net``, ``vessel``, ``door`` y ``class_vessels`` como en ``DesignRequest``: el motor corre
    el caso para obtener el aparejo (bridas, patentes, relingas, boyas, lastre y separación de
    portones) y :func:`trawlkit.sim.sweep` busca la forma de equilibrio a cada velocidad de
    ``speeds_kn`` (1–9 valores entre 0,5 y 6 kn). ``resolution`` son las divisiones nominales por
    panel (2–10; 4 por defecto, rápido). ``cn``/``ct`` son los coeficientes de Morison del hilo,
    ``knot_factor`` el diámetro relativo de los nudos (0 = sin nudos) y ``door_spread_m`` impone la
    separación de portones (si no, la del motor). ``include_geometry`` agrega nodos y conectividad
    a cada resultado (pesado). Se rechazan los pedidos cuyo costo estimado supera ~30 s.
    """

    model_config = ConfigDict(extra="forbid")

    net: str | NetSpec = "fao_a3_standard"
    vessel: str | Vessel | None = None
    door: str | Door | None = None
    class_vessels: list[str] | None = None
    compat: Literal["excel", "corrected"] = "corrected"
    speeds_kn: list[float] = Field(
        default_factory=lambda: [3.0], min_length=1, max_length=SIM_MAX_SPEEDS
    )
    resolution: int = Field(default=4, ge=SIM_RESOLUTION_RANGE[0], le=SIM_RESOLUTION_RANGE[1])
    cn: float | None = Field(default=None, gt=0.0, le=3.0, description="C_N del hilo")
    ct: float | None = Field(default=None, ge=0.0, le=0.5, description="C_T del hilo")
    knot_factor: float | None = Field(default=None, ge=0.0, le=10.0)
    door_spread_m: float | None = Field(default=None, gt=5.0, le=200.0)
    include_geometry: bool = False

    @model_validator(mode="after")
    def _check_speeds(self) -> SimulateRequest:
        lo, hi = SIM_SPEED_RANGE
        for v in self.speeds_kn:
            if not lo <= v <= hi:
                raise ValueError(f"cada velocidad debe estar entre {lo:g} y {hi:g} kn ({v!r})")
        if len(set(self.speeds_kn)) != len(self.speeds_kn):
            raise ValueError("speeds_kn no puede repetir velocidades")
        return self


class SimProjections(BaseModel):
    """Proyecciones SVG de la forma simulada a una velocidad."""

    plan: str
    profile: str
    front: str


class SimEngineRow(BaseModel):
    """Magnitudes empíricas del motor a una velocidad (comparables con la simulación)."""

    speed_kn: float
    ah_m: float | None
    """DPA de Fridman (red estándar) [m]."""
    av_m: float | None
    """AV de Fridman (red estándar) [m]."""
    drag_kgf: float | None
    """RN de diseño (Aberdeen) [kgf]."""
    door_spread_m: float | None


class DynamitRow(BaseModel):
    """Comparación con DynamiT (red FAO A-3 estándar) a una velocidad de la tabla de DynamiT."""

    speed_kn: float
    dynamit: dict[str, float]
    sim: dict[str, float | None]
    engine: dict[str, float | None]
    sim_pct: dict[str, float | None]
    engine_pct: dict[str, float | None]


class SimulateResponse(BaseModel):
    """Resultado de ``POST /simulate``."""

    results: list[dict[str, Any]]
    """``SimResult.to_dict(geometry=include_geometry)`` por velocidad, en el orden pedido."""
    projections_svg: dict[str, SimProjections]
    """Planta, perfil y frente de las primeras 3 velocidades (clave: velocidad, ``f"{v:g}"``)."""
    engine: list[SimEngineRow]
    dynamit_comparison: list[DynamitRow] | None
    """Sólo para la red ``fao_a3_standard`` y las velocidades de la tabla de DynamiT."""
    settings: dict[str, Any]
    estimated_s: float
    runtime_s: float


class LayoutShape(BaseModel):
    """Polígono de un panel en un plano (``trawlkit.drawing.layout.PanelShape``), en metros.

    ``y`` crece desde la boca hacia la bolsa; ``x = 0`` es el eje de la red. ``points`` va en
    sentido horario desde la esquina superior izquierda (un borde de 0 mallas da un triángulo).
    """

    id: str
    plane: str
    section: str
    side: Literal["left", "right", "center"]
    points: list[tuple[float, float]]
    y_top: float
    y_bottom: float
    x_top: tuple[float, float]
    x_bottom: tuple[float, float]
    meshes_top: int
    meshes_bottom: int
    meshes_depth: int
    mesh_mm: float
    hanging_ratio: float | None
    cut_code: str | None


class LayoutPlane(BaseModel):
    """Paneles de un plano (dorso, vientre o costado) y su recuadro ``(xmin, ymin, xmax, ymax)``."""

    plane: str
    bbox: tuple[float, float, float, float]
    mouth_y: float
    shapes: list[LayoutShape]


class LayoutResponse(BaseModel):
    """Resultado de ``POST /design/layout``: la disposición 2D de la red, por plano."""

    net_id: str
    mode: Literal["schematic", "true_scale"]
    bbox: tuple[float, float, float, float]
    planes: list[LayoutPlane]


LayoutMode = Literal["schematic", "true_scale"]
PlanView = Literal["sheet", "scale"]
Variant = Literal["std", "mod"]
ReportFormat = Literal["html", "pdf", "xlsx"]
