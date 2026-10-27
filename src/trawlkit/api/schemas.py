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
    components: list[dict[str, Any]] = Field(
        default_factory=list,
        max_length=50,
        description="Aportes de usuario (componentes en línea, estado «user») para este cálculo",
    )


class DesignResponse(BaseModel):
    """Resultado de ``POST /design``."""

    case: dict[str, Any]
    summary: dict[str, Any]
    notes: list[str]
    result: dict[str, Any]


class CatalogSource(BaseModel):
    """Documento del que sale una red del catálogo."""

    key: str
    title: str
    url: str
    figure: str | None = None
    page: str | None = None


class CatalogCheck(BaseModel):
    """Resumen del validador de consistencia (``trawlkit.netcheck``)."""

    ok: bool
    errors: int
    warnings: int


class CatalogCoverage(BaseModel):
    """Cobertura de procedencia: fracción de valores con fuente y conteo por tipo."""

    values: int
    fraction: float
    by_kind: dict[str, int]


class CatalogItem(BaseModel):
    """Entrada resumida de un catálogo.

    Para las redes, además de id, nombre y descripción, los datos para filtrar el catálogo sin
    bajar cada especificación: familia, aparejo, potencia de diseño, estado, fuente, cantidad de
    paños, si es de 4 paneles, validador y cobertura de procedencia.
    """

    id: str
    name: str | None = None
    description: str | None = None
    family: str | None = None
    rig: str | None = None
    vessel_hp: tuple[float, float] | None = None
    status: str | None = None
    target_species: str | None = None
    source: CatalogSource | None = None
    panels: int | None = None
    four_panel: bool | None = None
    check: CatalogCheck | None = None
    coverage: CatalogCoverage | None = None


class ComponentKindOut(BaseModel):
    """Resumen de un tipo de componente del catálogo."""

    kind: str
    label: str
    items: int
    generic: int
    brands: list[str]


class ComponentCheckRequest(BaseModel):
    """Componente a validar (un aporte de usuario): sus campos según ``kind``."""

    model_config = ConfigDict(extra="allow")

    kind: Literal["twine", "wire", "rope", "door", "float", "chain"]
    id: str
    name: str


class ComponentCheckOut(BaseModel):
    """Resultado de validar un componente: el ítem normalizado y sus observaciones."""

    ok: bool
    item: dict[str, Any] | None = None
    issues: list[CheckIssue]
    generic: dict[str, Any] | None = None


class ProvenanceRow(BaseModel):
    """Un valor de la red y su procedencia (``trawlkit.provenance``)."""

    path: str
    value: Any
    provenance: dict[str, Any] | None = None


class CheckIssue(BaseModel):
    """Problema de consistencia de una red."""

    level: Literal["error", "warning"]
    code: str
    message: str
    panels: list[str]


class NetCheckOut(BaseModel):
    """Resultado completo del validador de una red."""

    ok: bool
    errors: int
    warnings: int
    issues: list[CheckIssue]


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
    """Estado del servicio.

    ``contract`` es la huella de las rutas de la API (ver ``trawlkit.api.contract``): la app la
    compara con la de su build para avisar si la API en línea es de otra versión. ``commit`` es
    el commit desplegado (``RENDER_GIT_COMMIT`` en Render; ``None`` en local).
    """

    status: str
    version: str
    contract: str | None = None
    commit: str | None = None
    #: Redes del paquete que no validan como ``NetSpec`` (vacío = todas bien).
    nets_failed: list[str] | None = None


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


class PriceIn(BaseModel):
    """Precio orientativo de un componente o de una línea de la lista de materiales."""

    model_config = ConfigDict(extra="forbid")

    value: float = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3, description="Código ISO 4217")
    unit: Literal["kg", "m", "unit"]
    date: str = Field(default="", description="AAAA-MM o AAAA-MM-DD")
    source: str = Field(default="usuario")


class BomRequest(DesignRequest):
    """Lista de materiales del caso (``POST /design/bom``).

    ``prices`` mapea id de componente o clave de línea (``netting_pa``, ``doors``, ``floats``…) a
    un precio orientativo; sin precio, se usa el del catálogo o la línea queda «sin precio».
    """

    prices: dict[str, PriceIn] = Field(default_factory=dict)


class BomLineOut(BaseModel):
    """Una línea de la lista de materiales (``trawlkit.cost.BomLine``)."""

    key: str
    label: str
    quantity: float
    unit: str
    component_id: str | None = None
    component_kind: str | None = None
    component_name: str | None = None
    unit_price: float | None = None
    currency: str | None = None
    price_source: str | None = None
    cost: float | None = None
    note: str | None = None
    optional: bool = Field(
        default=False,
        description="Cantidad supuesta: sin precio no deja incompleta la lista",
    )


class BomOut(BaseModel):
    """Lista de materiales con totales por moneda y cantidad de líneas sin precio."""

    lines: list[BomLineOut]
    totals: dict[str, float]
    missing_prices: int


class ComponentOptimizeRequest(BaseModel):
    """Armado con componentes del catálogo (``POST /optimize/components``).

    ``net``, ``vessel``, ``door`` y ``params`` como en ``DesignRequest`` (los filtros van en
    ``params``: ``component_brands``, ``component_region``, ``generic_only``). ``objective``:
    ``drag`` (mín. R_T), ``efficiency`` (mín. R_T/AH) o ``cost`` (mín. costo de la lista de
    materiales). ``speed_kn`` fija la velocidad; sin ella se elige la mejor entre ``v_bounds``.
    ``doors``/``floats``/``twines`` fijan los candidatos por id.
    """

    model_config = ConfigDict(extra="forbid")

    net: str | NetSpec = "fao_a3_standard"
    vessel: str | Vessel | None = None
    door: str | Door | None = None
    class_vessels: list[str] | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    components: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    objective: Literal["drag", "efficiency", "cost"] = "drag"
    speed_kn: float | None = Field(default=None, gt=0.5, le=6.0)
    v_bounds: tuple[float, float] = (1.5, 4.0)
    margin: float = Field(default=0.1, ge=0.0, le=2.0)
    doors: list[str] | None = Field(default=None, max_length=8)
    floats: list[str] | None = Field(default=None, max_length=6)
    twines: list[str] | None = Field(default=None, max_length=6)
    prices: dict[str, PriceIn] = Field(default_factory=dict)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    max_doors: int = Field(default=5, ge=1, le=8)
    max_floats: int = Field(default=4, ge=1, le=6)
    max_twines: int = Field(default=4, ge=1, le=6)

    @model_validator(mode="after")
    def _check_bounds(self) -> ComponentOptimizeRequest:
        v_lo, v_hi = self.v_bounds
        if not 0.5 <= v_lo < v_hi <= 6.0:
            raise ValueError("v_bounds debe cumplir 0.5 ≤ v_lo < v_hi ≤ 6")
        return self


class AssemblyOut(BaseModel):
    """Un armado evaluado (``trawlkit.optimize.components.Assembly``)."""

    components: dict[str, str | None]
    float_count: int | None
    speed_kn: float
    demand_kgf: float
    available_kgf: float
    thrust_margin: float
    net_drag_kgf: float
    ah_m: float
    av_m: float
    area_rate_m2_h: float
    energy_kgf_m_per_m2: float
    door_area_m2: float
    door_required_m2: float
    constraints: list[ConstraintOut]
    feasible: bool
    penalty: float
    generic: bool
    cost: float | None
    currency: str | None
    missing_prices: int
    bom: BomOut


class ComponentOptimizeResponse(BaseModel):
    """Resultado de ``POST /optimize/components``."""

    best: AssemblyOut
    alternatives: list[AssemblyOut]
    objective: str
    feasible: bool
    evaluated: int
    candidates: dict[str, list[str | None]]
    settings: dict[str, Any]
    notes: list[str]


class DoorSelectRequest(BaseModel):
    """Elección de portones del catálogo para el caso (``POST /doors/select``, Fase 19.3).

    ``net``, ``vessel``, ``door``, ``class_vessels``, ``compat`` y ``params`` como en
    ``DesignRequest``: el caso da la superficie requerida por portón (Port!F215) y el CL del
    portón del caso. ``brands``/``region``/``generic_only`` filtran el catálogo de componentes;
    ``types`` limita los tipos (``flat``, ``v``, ``oval``, ``cambered``, ``multifoil``,
    ``high_aspect``); ``margin`` es el margen al pasar a un portón de más CL (Seafish: 10 %).
    """

    model_config = ConfigDict(extra="forbid")

    net: str | NetSpec = "fao_a3_standard"
    vessel: str | Vessel | None = None
    door: str | Door | None = None
    class_vessels: list[str] | None = None
    compat: Literal["excel", "corrected"] = "corrected"
    params: dict[str, Any] = Field(default_factory=dict)
    components: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    brands: list[str] | None = Field(default=None, max_length=20)
    region: str | None = None
    generic_only: bool = False
    types: list[str] | None = Field(default=None, max_length=8)
    margin: float = Field(default=0.1, ge=0.0, le=1.0)
    max_results: int = Field(default=20, ge=1, le=60)
    include_light: bool = True


class AttackAngleOut(BaseModel):
    """Rango de ángulo de ataque recomendado de un tipo de portón, con su fuente."""

    min_deg: float
    max_deg: float
    document: str
    page: str
    kind: str
    note: str


class DoorCandidateOut(BaseModel):
    """Un portón del catálogo evaluado para el caso."""

    id: str
    name: str
    type: str | None
    type_label: str | None
    brand: str | None
    generic: bool
    area_m2: float
    length_m: float | None
    weight_air_kg: float | None
    weight_water_kg: float | None
    angle_deg: float
    cl: float
    cd: float
    required_m2: float
    margin_applied: bool
    area_margin: float
    ok: bool
    weight_status: Literal["ok", "light", "missing", "no_reference"]
    weight_reference_kg: float | None
    attack_angle: AttackAngleOut | None
    backstrop_m: list[float] | None
    hp_ok: bool | None
    warnings: list[str]


class DoorSelectResponse(BaseModel):
    """Resultado de ``POST /doors/select``."""

    required_m2: float
    case_door: dict[str, Any]
    candidates: list[DoorCandidateOut]
    rejected: int
    margin: float
    rules: list[dict[str, str]]
    notes: list[str]


class DoorTypePolarOut(BaseModel):
    """Polar representativa de un tipo de portón (``GET /catalog/door-polars``)."""

    type: str
    label: str
    method: str
    kind: str
    polar_ids: list[str]
    documents: list[str]
    pages: list[str]
    note: str
    coefficients: list[dict[str, float]]
    attack_angle: AttackAngleOut


class BatchFile(BaseModel):
    """Planilla del lote: CSV como texto o XLSX en base64."""

    model_config = ConfigDict(extra="forbid")

    filename: str = Field(default="planilla.csv", max_length=200)
    content: str = Field(min_length=1, max_length=8_000_000)
    encoding: Literal["text", "base64"] = "text"


class BatchParseRequest(BaseModel):
    """Lectura de una planilla (``POST /batch/parse``): vista previa sin calcular."""

    model_config = ConfigDict(extra="forbid")

    file: BatchFile
    mode: Literal["fleet", "cases", "nets"] = "fleet"


class PriceParseRequest(BaseModel):
    """Lista de precios del usuario (``POST /prices/parse``): CSV como texto o XLSX en base64.

    ``currency``: moneda de las filas que no la traen.
    """

    model_config = ConfigDict(extra="forbid")

    file: BatchFile
    currency: str | None = Field(default=None, min_length=3, max_length=3)


class PriceParseResponse(BaseModel):
    """Precios leídos (clave = id de componente o de línea), filas y observaciones."""

    prices: dict[str, PriceIn]
    rows: int
    issues: list[dict[str, Any]]
    ignored: list[str]


class PriceLineIn(BaseModel):
    """Línea de la lista de materiales para la plantilla de precios."""

    model_config = ConfigDict(extra="ignore")

    key: str = Field(max_length=200)
    label: str | None = Field(default=None, max_length=300)
    unit: str | None = Field(default=None, max_length=10)
    component_id: str | None = Field(default=None, max_length=200)


class PriceExportRequest(BaseModel):
    """Lista de precios a exportar (``POST /prices/export``).

    ``lines``: líneas de la lista de materiales; las que no tienen precio salen vacías, como
    plantilla para completar.
    """

    model_config = ConfigDict(extra="forbid")

    prices: dict[str, PriceIn] = Field(default_factory=dict)
    lines: list[PriceLineIn] = Field(default_factory=list, max_length=500)


class BatchRunRequest(BatchParseRequest):
    """Lote (``POST /batch/run`` y ``/batch/export``).

    ``mode = "fleet"``: la red ``net`` (id, especificación o, si la planilla trae una sola red,
    ésa) se proyecta a cada buque. ``objective``: ``area`` (la mayor red que el buque remolca),
    ``energy`` (menor R_T/AH) o ``cost`` (armado más barato con ``prices``). ``region`` y
    ``generic_only`` filtran los componentes (cada buque puede traer los suyos en la planilla).
    """

    net: str | NetSpec | None = None
    objective: Literal["area", "energy", "cost"] = "area"
    margin: float = Field(default=0.1, ge=0.0, le=2.0)
    region: str | None = None
    generic_only: bool = False
    assemble: bool = True
    prices: dict[str, PriceIn] = Field(default_factory=dict)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    detail: bool = True
    economics: EconomicInputsIn | None = None


class BatchParseResponse(BaseModel):
    """Vista previa del lote: filas reconocidas por tipo y observaciones."""

    mode: str
    size: int
    fleet: dict[str, Any] | None
    nets: list[dict[str, Any]]
    cases: list[dict[str, Any]]
    issues: list[dict[str, Any]]
    estimated_s: float
    max_s: float


class BatchRunResponse(BaseModel):
    """Resultado del lote: una fila por buque, caso o red."""

    mode: str
    rows: list[dict[str, Any]]
    counts: dict[str, int]
    settings: dict[str, Any]
    issues: list[dict[str, Any]]
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


class ScenarioIn(BaseModel):
    """Condiciones del lance para la simulación (ver ``trawlkit.sim.scenario``).

    ``catch_kg`` captura en el copo; ``catch_bulk_density`` densidad aparente (organismos y agua
    intersticial) que fija el volumen ocupado; ``catch_body_density`` densidad de los organismos
    (peso sumergido); ``catch_cp`` coeficiente de presión de la bola de captura; ``seabed`` tipo
    de fondo (``GET /catalog/seabeds``); ``mu_gear``/``mu_door`` imponen el rozamiento del tren y
    de los portones; ``coupled_doors`` libera los portones (la separación sale del equilibrio);
    ``dynamic_door_polar`` recalcula su CL y CD al ángulo de ataque de la forma resuelta.
    """

    model_config = ConfigDict(extra="forbid")

    catch_kg: float = Field(default=0.0, ge=0.0, le=20000.0)
    catch_bulk_density: float = Field(default=750.0, ge=200.0, le=1300.0)
    catch_body_density: float = Field(default=1070.0, ge=900.0, le=2000.0)
    catch_cp: float = Field(default=1.0, ge=0.0, le=3.0)
    seabed: str | None = None
    mu_gear: float | None = Field(default=None, ge=0.0, le=1.5)
    mu_door: float | None = Field(default=None, ge=0.0, le=1.5)
    coupled_doors: bool = True
    fouling: str | None = None
    fouling_level: float = Field(default=1.0, ge=0.0, le=2.0)
    current_kn: float = Field(default=0.0, ge=-2.0, le=2.0)
    warp_length_m: float | None = Field(default=None, ge=20.0, le=3000.0)
    haul_hours: float = Field(default=2.0, ge=0.1, le=24.0)
    mesh_bending: bool | None = None
    """Rigidez de apertura de la malla (None = sólo con paños T90 o de malla cuadrada)."""
    mesh_bending_factor: float = Field(default=1.0, ge=0.0, le=20.0)
    door_cl_factor: float = Field(default=1.0, ge=0.3, le=2.0)
    """Factor sobre la sustentación de la polar del portón (calibración, incertidumbre)."""
    door_cd_factor: float = Field(default=1.0, ge=0.3, le=2.0)
    dynamic_door_polar: bool = True
    """Polar dinámica de los portones acoplados (Fase 19.3): CL y CD al ángulo de ataque que da
    la forma resuelta (método de Seafish 1993); ``false`` = CL y CD fijos al ángulo del caso."""


class FoulingOut(BaseModel):
    """Escenario de ensuciamiento: nivel 0–1 por zona (alas, cuerpo, copo)."""

    id: str
    name: str
    zones: dict[str, float]
    notes: str


class SeabedOut(BaseModel):
    """Tipo de fondo del catálogo, con μ nominal y rango (A VERIFICAR)."""

    id: str
    name: str
    aliases: list[str]
    mu_gear: dict[str, Any]
    mu_door: dict[str, Any]
    penetration: str
    notes: str


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
    mu: float | None = Field(default=None, ge=0.0, le=1.5, description="μ red–fondo")
    scenario: ScenarioIn | None = None
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Parámetros del caso como en DesignRequest (p. ej. el aparejo: rig, tangones, "
        "muerto o vara)",
    )

    @model_validator(mode="after")
    def _check_speeds(self) -> SimulateRequest:
        lo, hi = SIM_SPEED_RANGE
        for v in self.speeds_kn:
            if not lo <= v <= hi:
                raise ValueError(f"cada velocidad debe estar entre {lo:g} y {hi:g} kn ({v!r})")
        if len(set(self.speeds_kn)) != len(self.speeds_kn):
            raise ValueError("speeds_kn no puede repetir velocidades")
        return self


HAUL_MAX_STEPS = 8


class HaulRequest(BaseModel):
    """Lance progresivo (``POST /simulate/haul``): la captura crece a velocidad constante.

    Cada valor de ``catches_kg`` (no decreciente, 1–8 valores) es un equilibrio que parte del
    anterior; el resto del escenario se toma de ``scenario`` (su ``catch_kg`` se ignora).
    """

    model_config = ConfigDict(extra="forbid")

    net: str | NetSpec = "fao_a3_standard"
    vessel: str | Vessel | None = None
    door: str | Door | None = None
    class_vessels: list[str] | None = None
    compat: Literal["excel", "corrected"] = "corrected"
    speed_kn: float = Field(default=3.0, ge=SIM_SPEED_RANGE[0], le=SIM_SPEED_RANGE[1])
    catches_kg: list[float] = Field(
        default_factory=lambda: [0.0, 250.0, 500.0, 1000.0],
        min_length=1,
        max_length=HAUL_MAX_STEPS,
    )
    resolution: int = Field(default=4, ge=2, le=6)
    cn: float | None = Field(default=None, gt=0.0, le=3.0)
    ct: float | None = Field(default=None, ge=0.0, le=0.5)
    scenario: ScenarioIn = Field(default_factory=ScenarioIn)
    include_geometry: bool = False

    @model_validator(mode="after")
    def _check_catches(self) -> HaulRequest:
        c = self.catches_kg
        if any(v < 0 or v > 20000 for v in c):
            raise ValueError("cada captura debe estar entre 0 y 20000 kg")
        if any(b < a for a, b in zip(c, c[1:], strict=False)):
            raise ValueError("catches_kg debe ser no decreciente (la captura entra de a poco)")
        return self


EXPLORE_MAX_STEPS = 10
ExploreVariable = Literal[
    "catch_kg", "speed_kn", "warp_length_m", "fouling_level", "current_kn", "mu_gear"
]


class ExploreRequest(BaseModel):
    """Explorador (``POST /simulate/explore``): estados al recorrer una variable.

    ``values`` (2–10) son los valores de ``variable``; cada estado parte del anterior y todos
    comparten la malla, así que la forma se puede animar interpolando entre estados. El resto
    del escenario se toma de ``scenario`` y la velocidad de ``speed_kn`` (salvo que la variable
    sea la velocidad). Con ``include_geometry`` la respuesta trae la conectividad una vez
    (``geometry``) y las posiciones de cada estado (``frames``).
    """

    model_config = ConfigDict(extra="forbid")

    net: str | NetSpec = "fao_a3_standard"
    vessel: str | Vessel | None = None
    door: str | Door | None = None
    class_vessels: list[str] | None = None
    compat: Literal["excel", "corrected"] = "corrected"
    variable: ExploreVariable = "catch_kg"
    values: list[float] = Field(min_length=2, max_length=EXPLORE_MAX_STEPS)
    speed_kn: float = Field(default=3.0, ge=SIM_SPEED_RANGE[0], le=SIM_SPEED_RANGE[1])
    resolution: int = Field(default=3, ge=2, le=5)
    cn: float | None = Field(default=None, gt=0.0, le=3.0)
    ct: float | None = Field(default=None, ge=0.0, le=0.5)
    scenario: ScenarioIn = Field(default_factory=ScenarioIn)
    include_geometry: bool = True
    species: list[str] = Field(default_factory=list, max_length=8)
    """Especies (``GET /catalog/species``): cada estado suma L50, SR y SF del copo."""


class ExploreResponse(BaseModel):
    """Resultado de ``POST /simulate/explore``."""

    variable: str
    values: list[float]
    results: list[dict[str, Any]]
    """``SimResult.to_dict(geometry=False)`` por estado."""
    geometry: dict[str, Any] | None
    """Conectividad común: triángulos, barras, tipos, relingas, boyas, portones, cables."""
    frames: list[dict[str, Any]] | None
    """Por estado: posiciones de los nodos (redondeadas al cm), tensiones y ensuciamiento."""
    engine: dict[str, Any]
    settings: dict[str, Any]
    estimated_s: float
    runtime_s: float


class SpeciesOut(BaseModel):
    """Especie con la forma de su sección transversal (``trawlkit.selectivity``)."""

    id: str
    name: str
    scientific_name: str
    group: str
    measure: str
    """TL (largo total) o CL (largo del caparazón)."""
    unit: str
    length_min: float
    length_max: float
    height: float
    """Alto de la sección / talla."""
    width: float
    """Ancho de la sección / talla."""
    compression: float
    cv: float
    notes: str


class CodendVariant(BaseModel):
    """Variante de copo: orientación de la malla y, opcionalmente, mallero y U1."""

    model_config = ConfigDict(extra="forbid")

    orientation: Literal["diamond", "t90", "square"] = "diamond"
    mesh_mm: float | None = Field(default=None, gt=5.0, le=400.0)
    hanging_ratio: float | None = Field(default=None, gt=0.05, lt=1.0)
    label: str | None = Field(default=None, max_length=40)


class SelectivityRequest(BaseModel):
    """Selectividad del copo (``POST /simulate/selectivity``).

    Cada variante rehace el copo (y la extensión) con otra orientación de malla o mallero,
    conservando su ancho y largo relingados, y se simula con el escenario pedido. Devuelve por
    variante la curva de retención de cada especie (L25, L50, L75, SR, SF), la talla máxima de
    paso de cada triángulo (mapa) y, con ``include_geometry``, la forma para el 3D y el zoom.
    """

    model_config = ConfigDict(extra="forbid")

    net: str | NetSpec = "fao_a3_standard"
    vessel: str | Vessel | None = None
    door: str | Door | None = None
    class_vessels: list[str] | None = None
    compat: Literal["excel", "corrected"] = "corrected"
    speed_kn: float = Field(default=3.0, ge=SIM_SPEED_RANGE[0], le=SIM_SPEED_RANGE[1])
    resolution: int = Field(default=3, ge=2, le=5)
    cn: float | None = Field(default=None, gt=0.0, le=3.0)
    ct: float | None = Field(default=None, ge=0.0, le=0.5)
    scenario: ScenarioIn = Field(default_factory=lambda: ScenarioIn(catch_kg=300.0))
    species: list[str] = Field(default_factory=lambda: ["hake_hubbsi"], min_length=1, max_length=8)
    variants: list[CodendVariant] = Field(
        default_factory=lambda: [CodendVariant(), CodendVariant(orientation="t90")],
        min_length=1,
        max_length=3,
    )
    contact: float = Field(default=1.0, ge=0.0, le=1.0)
    zone_length_m: float | None = Field(default=3.0, gt=0.0, le=50.0)
    lengths: list[float] | None = Field(default=None, min_length=2, max_length=400)
    include_geometry: bool = True


class SelectivityResponse(BaseModel):
    """Resultado de ``POST /simulate/selectivity``."""

    species: list[str]
    variants: list[dict[str, Any]]
    """Por variante: ``label``, ``orientation``, ``mesh_mm``, paños del copo, ``result``
    (``SimResult.to_dict(geometry=False)``), ``curves`` (por especie) y, con geometría,
    ``geometry`` y ``frame`` (posiciones, apertura de malla y captura por triángulo)."""
    settings: dict[str, Any]
    estimated_s: float
    runtime_s: float


class UncertainIn(BaseModel):
    """Rango uniforme de una entrada incierta (reemplaza el rango por defecto)."""

    model_config = ConfigDict(extra="forbid")

    name: Literal[
        "cn",
        "ct",
        "mu_gear",
        "mu_door",
        "door_cl_factor",
        "door_cd_factor",
        "catch_bulk_density",
        "catch_cp",
    ]
    low: float
    high: float


class UncertaintyRequest(BaseModel):
    """Incertidumbre (``POST /simulate/uncertainty``): Monte Carlo con hipercubo latino.

    Muestrea las entradas inciertas (por defecto: C_N y C_T del hilo, rozamientos según el fondo,
    polar del portón ±10 % y, con captura, densidad aparente y C_p) y simula cada muestra a
    ``speed_kn`` arrancando de la forma nominal. ``inputs`` reemplaza los rangos de las entradas
    nombradas; ``species`` suma la L50 del copo.
    """

    model_config = ConfigDict(extra="forbid")

    net: str | NetSpec = "fao_a3_standard"
    vessel: str | Vessel | None = None
    door: str | Door | None = None
    class_vessels: list[str] | None = None
    compat: Literal["excel", "corrected"] = "corrected"
    speed_kn: float = Field(default=3.0, ge=SIM_SPEED_RANGE[0], le=SIM_SPEED_RANGE[1])
    resolution: int = Field(default=2, ge=2, le=4)
    cn: float | None = Field(default=None, gt=0.0, le=3.0)
    ct: float | None = Field(default=None, ge=0.0, le=0.5)
    scenario: ScenarioIn = Field(default_factory=ScenarioIn)
    samples: int = Field(default=10, ge=4, le=24)
    seed: int = Field(default=0, ge=0)
    inputs: list[UncertainIn] | None = Field(default=None, max_length=8)
    species: list[str] = Field(default_factory=list, max_length=3)


class UncertaintyResponse(BaseModel):
    """Resultado de ``POST /simulate/uncertainty``."""

    result: dict[str, Any]
    """Entradas (rangos), muestras, salidas con nominal, P10/P50/P90, valores por muestra y
    sensibilidad (correlación de rangos de Spearman por entrada), y el resultado nominal."""
    settings: dict[str, Any]
    estimated_s: float
    runtime_s: float


CalibrationQuantity = Literal[
    "door_spread_m",
    "ah_m",
    "av_m",
    "headrope_height_m",
    "drag_kgf",
    "towing_pull_kgf",
    "warp_tension_kgf",
]
CalibrationParam = Literal["cn", "ct", "door_cl_factor", "door_cd_factor", "mu_gear", "mu_door"]


DEFAULT_CALIBRATION_PARAMS: tuple[CalibrationParam, ...] = ("cn", "door_cl_factor")


class ObservationIn(BaseModel):
    """Una medición: ``quantity`` = ``value`` a ``speed_kn`` con ``catch_kg`` en el copo."""

    model_config = ConfigDict(extra="forbid")

    quantity: CalibrationQuantity
    value: float = Field(gt=0.0)
    speed_kn: float = Field(ge=0.3, le=6.0)
    catch_kg: float = Field(default=0.0, ge=0.0, le=20000.0)
    weight: float = Field(default=1.0, gt=0.0, le=10.0)
    source: str = Field(default="", max_length=60)


class CalibrateRequest(BaseModel):
    """Calibración (``POST /simulate/calibrate``): ajusta parámetros a observaciones.

    Las observaciones vienen en ``observations`` (p. ej. de ``POST /sensors/parse``) o, con
    ``reference = "dynamit"``, de la simulación DynamiT de la red FAO A-3 estándar a 2, 3 y 4 kn.
    Levenberg–Marquardt acotado sobre los errores relativos; ``max_evals`` limita las
    evaluaciones (cada una simula todos los estados observados).
    """

    model_config = ConfigDict(extra="forbid")

    net: str | NetSpec = "fao_a3_standard"
    vessel: str | Vessel | None = None
    door: str | Door | None = None
    class_vessels: list[str] | None = None
    compat: Literal["excel", "corrected"] = "corrected"
    resolution: int = Field(default=2, ge=2, le=3)
    scenario: ScenarioIn = Field(default_factory=ScenarioIn)
    reference: Literal["dynamit"] | None = None
    observations: list[ObservationIn] = Field(default_factory=list, max_length=40)
    params: list[CalibrationParam] = Field(
        default_factory=lambda: list(DEFAULT_CALIBRATION_PARAMS), min_length=1, max_length=3
    )
    max_evals: int = Field(default=16, ge=3, le=30)


class CalibrateResponse(BaseModel):
    """Resultado de ``POST /simulate/calibrate``."""

    result: dict[str, Any]
    """Parámetros (inicial, ajustado, desvío aproximado, rango), observaciones con la simulación
    antes y después y su error, error cuadrático medio relativo antes y después e historial."""
    settings: dict[str, Any]
    estimated_s: float
    runtime_s: float


class SensorParseRequest(BaseModel):
    """Registro de sensores (``POST /sensors/parse``): CSV a tramos estacionarios.

    ``by = "speed"`` agrupa por velocidad (``width`` en kn) y ``by = "time"`` por tiempo
    (``width`` en minutos). Devuelve las columnas reconocidas, los tramos y las observaciones
    listas para ``POST /simulate/calibrate``.
    """

    model_config = ConfigDict(extra="forbid")

    csv: str = Field(min_length=3, max_length=2_000_000)
    by: Literal["speed", "time"] = "speed"
    width: float = Field(default=0.25, gt=0.0, le=120.0)
    min_rows: int = Field(default=5, ge=1, le=10_000)


class SensorParseResponse(BaseModel):
    """Resultado de ``POST /sensors/parse``."""

    log: dict[str, Any]
    """Columnas reconocidas (encabezado → magnitud), ignoradas, filas y avisos."""
    windows: list[dict[str, Any]]
    observations: list[ObservationIn]


class HaulResponse(BaseModel):
    """Resultado de ``POST /simulate/haul``."""

    results: list[dict[str, Any]]
    """``SimResult.to_dict`` por captura, en el orden pedido."""
    engine: dict[str, Any]
    """Motor empírico a la misma velocidad: demanda total, DP de la regla y rozamiento."""
    settings: dict[str, Any]
    estimated_s: float
    runtime_s: float


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
    mesh_orientation: str = "diamond"
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


# ---------------------------------------------------------------------------------------------
# Guía de construcción (Fase 15)
# ---------------------------------------------------------------------------------------------


class CutSideOut(BaseModel):
    """Corte de un costado del paño (``trawlkit.construction.CutSide``)."""

    side: str
    code: str
    cycles: int
    instruction: str
    inferred: bool = False


class CutPieceOut(BaseModel):
    """Un paño de la hoja de corte (``trawlkit.construction.CutPiece``)."""

    id: str
    name: str
    planes: str
    section: str
    pieces: int
    paired: bool
    material: str
    mesh_mm: float
    twine_mm: float
    rtex: float | None = None
    orientation: str
    meshes_mouth: int
    meshes_codend: int
    meshes_depth: int
    hanging_ratio: float | None = None
    sides: list[CutSideOut]
    start: str
    stock_width: int
    stock_depth: int
    weight_kg: float
    stock_weight_kg: float
    waste: float
    stretched_width_m: float
    stretched_length_m: float


class NettingStockOut(BaseModel):
    """Paño a comprar de una calidad (``trawlkit.construction.NettingStock``)."""

    material: str
    mesh_mm: float
    twine_mm: float
    rtex: float | None = None
    pieces: int
    width_meshes: int
    depth_meshes: int
    area_meshes: int
    weight_kg: float
    finished_kg: float


class JoinOut(BaseModel):
    """Una unión del armado (``trawlkit.construction.Join``)."""

    step: int
    plane: str
    kind: Literal["seam", "wing_to_body", "side_seam", "side_panel"]
    a: str
    a_edge: str
    b: str
    b_edge: str
    meshes_a: int
    meshes_b: int
    times: int
    ratio: str
    rule: str
    note: str = ""


class HangingOut(BaseModel):
    """Tramo de relinga con su paño (``trawlkit.construction.HangingSection``)."""

    rope: str
    part: str
    panels: list[str]
    times: int
    rope_m: float
    meshes: int
    netting_m: float
    hanging: float | None = None
    meshes_per_m: float | None = None
    schedule: str
    warning: str = ""


class FloatPositionOut(BaseModel):
    """Boya sobre la lima, a ``x_m`` del centro (+ derecha)."""

    number: int
    x_m: float
    zone: str


class BallastZoneOut(BaseModel):
    """Zona de lastre del burlón con el lastre mínimo y el máximo."""

    zone: str
    where: str
    kg_min: float
    kg_max: float
    kg_m_min: float
    kg_m_max: float


class RopeCutOut(BaseModel):
    """Corte de un cabo, cable o cadena."""

    key: str
    label: str
    material: str
    pieces: int
    length_m: float
    eyes: int
    cut_m: float


class ConstructionGuideOut(BaseModel):
    """Resultado de ``POST /design/construction``: la guía de construcción para el taller."""

    net_id: str
    net_name: str
    variant: Literal["std", "mod"]
    eye_allowance_m: float
    pieces: list[CutPieceOut]
    stock: list[NettingStockOut]
    joins: list[JoinOut]
    hanging: list[HangingOut]
    floats: list[FloatPositionOut]
    float_diameter_mm: float
    ballast: list[BallastZoneOut]
    ropes: list[RopeCutOut]
    notes: list[str]


GuideFormat = Literal["html", "pdf", "xlsx"]


# ---------------------------------------------------------------------------------------------
# Economía de la operación (Fase 16)
# ---------------------------------------------------------------------------------------------


class SpeciesPriceIn(BaseModel):
    """Especie de la captura: fracción del peso y precio en playa por kg."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=60)
    share: float = Field(gt=0.0, le=1.0)
    price: float | None = Field(default=None, ge=0.0)


class EconomicInputsIn(BaseModel):
    """Datos de la operación (``trawlkit.economics.EconomicInputs``).

    Los precios y montos en ``null`` son «sin dato»: las magnitudes que los necesitan salen en
    ``null`` y se listan en ``missing``. No hay precios por defecto.
    """

    model_config = ConfigDict(extra="forbid")

    currency: str = Field(default="USD", min_length=3, max_length=3)
    fuel_price_l: float | None = Field(default=None, ge=0.0)
    lube_price_l: float | None = Field(default=None, ge=0.0)
    lube_ratio: float = Field(default=0.01, ge=0.0, le=0.2)
    sfc_kg_kwh: float = Field(default=0.22, gt=0.1, le=0.5)
    towing_efficiency: float = Field(default=0.5, gt=0.05, le=1.0)
    steaming_load: float = Field(default=0.8, ge=0.0, le=1.0)
    idle_load: float = Field(default=0.2, ge=0.0, le=1.0)
    steaming_hours: float = Field(default=4.0, ge=0.0, le=500.0)
    hauls_per_trip: int = Field(default=4, ge=1, le=200)
    haul_hours: float = Field(default=2.0, gt=0.0, le=24.0)
    handling_hours: float = Field(default=0.5, ge=0.0, le=12.0)
    trip_days: float = Field(default=1.0, ge=0.0, le=120.0)
    trips_per_year: float = Field(default=150.0, gt=0.0, le=366.0)
    catch_kg_h: float | None = Field(default=None, ge=0.0)
    reference_speed_kn: float = Field(default=3.0, gt=0.0, le=8.0)
    price_kg: float | None = Field(default=None, ge=0.0)
    species: list[SpeciesPriceIn] = Field(default_factory=list, max_length=20)
    crew_mode: Literal["share", "wage", "none"] = "share"
    crew_share: float | None = Field(default=None, ge=0.0, le=1.0)
    share_after_costs: bool = True
    crew_size: int | None = Field(default=None, ge=1, le=200)
    wage_day: float | None = Field(default=None, ge=0.0)
    gear_cost: float | None = Field(default=None, ge=0.0)
    gear_life_hours: float = Field(default=2000.0, gt=0.0)
    gear_repair_year: float = Field(default=0.1, ge=0.0, le=2.0)
    trip_costs: float | None = Field(default=None, ge=0.0)
    annual_costs: float | None = Field(default=None, ge=0.0)


class EconomicsRequest(DesignRequest):
    """Curva económica del caso (``POST /economics``).

    ``economics``: datos de la operación; ``prices``: precios de componentes para sacar el costo
    del armado de la lista de materiales si ``economics.gear_cost`` falta; ``v_min_kn`` y
    ``v_max_kn``: rango de velocidades (paso 0,25 kn).
    """

    economics: EconomicInputsIn = Field(default_factory=EconomicInputsIn)
    prices: dict[str, PriceIn] = Field(default_factory=dict)
    v_min_kn: float = Field(default=1.5, ge=0.5, le=6.0)
    v_max_kn: float = Field(default=4.0, ge=0.5, le=6.0)
    margin: float = Field(default=0.1, ge=0.0, le=2.0)


class TripEconomicsOut(BaseModel):
    """Una marea a una velocidad (``trawlkit.economics.TripEconomics``)."""

    speed_kn: float
    feasible: bool
    towing_power_kw: float
    power_limited: bool
    fuel_l_tow: float
    fuel_l_steam: float
    fuel_l_handling: float
    fuel_l: float
    fuel_l_h_tow: float
    area_rate_m2_h: float
    catch_kg: float | None
    fuel_l_per_kg: float | None
    revenue: float | None
    costs: dict[str, float | None]
    total_cost: float | None
    margin: float | None
    cost_per_kg: float | None
    margin_per_sea_hour: float | None
    breakeven_price: float | None
    missing: list[str]
    warnings: list[str] = Field(default_factory=list)
    complete: bool = False


class EconomicsOut(BaseModel):
    """Resultado de ``POST /economics``: curva por velocidad, las mejores y el año."""

    net_id: str
    vessel_id: str
    currency: str
    gear_cost: float | None
    gear_cost_source: str
    trips: list[TripEconomicsOut]
    best_margin_kn: float | None
    best_cost_kg_kn: float | None
    least_fuel_kg_kn: float | None
    year: dict[str, float | None]
    inputs: dict[str, Any]
    notes: list[str]


class CompareCaseIn(BaseModel):
    """Un caso de la comparación: rótulo, caso y costo de su armado (opcional)."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=80)
    case: DesignRequest
    gear_cost: float | None = Field(default=None, ge=0.0)


class EconomicsCompareRequest(BaseModel):
    """Comparación económica (``POST /economics/compare``); el primer caso es la base."""

    model_config = ConfigDict(extra="forbid")

    cases: list[CompareCaseIn] = Field(min_length=2, max_length=6)
    economics: EconomicInputsIn = Field(default_factory=EconomicInputsIn)
    prices: dict[str, PriceIn] = Field(default_factory=dict)
    speed_kn: float | None = Field(default=None, ge=0.5, le=6.0)
    v_min_kn: float = Field(default=1.5, ge=0.5, le=6.0)
    v_max_kn: float = Field(default=4.0, ge=0.5, le=6.0)
    margin: float = Field(default=0.1, ge=0.0, le=2.0)


class ComparisonOut(BaseModel):
    """Un caso comparado: su marea, el año y el ahorro y el repago frente a la base."""

    label: str
    net_id: str
    vessel_id: str
    gear_cost: float | None
    trip: TripEconomicsOut | None
    annual_margin: float | None
    annual_fuel_l: float | None
    savings_year: float | None
    fuel_savings_l_year: float | None
    payback_years: float | None


class EconomicsCompareOut(BaseModel):
    """Resultado de ``POST /economics/compare``."""

    currency: str
    rows: list[ComparisonOut]


# --- Fase 17: banco de ejercicios y laboratorios ----------------------------------------------

TeachingLevel = Literal["basico", "intermedio", "avanzado"]


class ExerciseSummaryOut(BaseModel):
    """Ejercicio del banco (sin datos ni respuestas)."""

    id: str
    chapter: str
    topic: str
    level: TeachingLevel
    title: str
    answers: int


class ExerciseDataOut(BaseModel):
    """Un dato del enunciado."""

    key: str
    label: str
    value: float | str
    unit: str
    text: str


class ExerciseFieldOut(BaseModel):
    """Un campo a responder."""

    key: str
    label: str
    unit: str
    kind: Literal["number", "code", "choice"]
    options: list[str] | None


class ExerciseInstanceOut(BaseModel):
    """Un ejercicio con sus datos para una semilla, sin las respuestas."""

    id: str
    seed: int
    chapter: str
    topic: str
    level: TeachingLevel
    title: str
    statement: str
    data: list[ExerciseDataOut]
    answers: list[ExerciseFieldOut]
    hints: list[str]
    refs: list[str]


class GradeRequest(BaseModel):
    """Respuestas a corregir (``POST /teaching/grade``), por clave; números con coma o punto."""

    model_config = ConfigDict(extra="forbid")

    id: str
    seed: int = Field(default=0, ge=0, le=2**31 - 1)
    answers: dict[str, str | float] = Field(default_factory=dict)


class AnswerGradeOut(BaseModel):
    """Corrección de una respuesta."""

    key: str
    ok: bool
    given: str | None
    expected: float | str | None
    expected_text: str | None
    error_rel: float | None
    message: str


class GradeOut(BaseModel):
    """Corrección de un ejercicio: puntaje (0 a 1), por respuesta y explicación."""

    id: str
    seed: int
    score: float
    answers: list[AnswerGradeOut]
    explanation: str | None


class LabSummaryOut(BaseModel):
    """Laboratorio guiado (sin los pasos)."""

    id: str
    chapter: str
    topic: str
    level: TeachingLevel
    title: str
    summary: str
    steps: int


class LabCheckOut(BaseModel):
    """Comprobación de un paso, sin la respuesta."""

    label: str
    fact: str
    op: str


class LabQuestionOut(BaseModel):
    """Pregunta de un paso (sin la respuesta correcta)."""

    id: str
    kind: Literal["number", "choice", "text"]
    prompt: str
    unit: str
    options: list[str] | None = Field(description="Textos de las opciones en el idioma activo")
    option_ids: list[str] | None = Field(
        default=None, description="Ids estables de las opciones (se puede responder con el id)"
    )


class LabTargetOut(BaseModel):
    """Dónde se hace el paso en la app."""

    mode: Literal["expert", "simple"]
    tab: str | None
    hint: str | None


class LabStepOut(BaseModel):
    """Un paso del laboratorio."""

    id: str
    title: str
    instruction: str
    target: LabTargetOut
    checks: list[LabCheckOut]
    questions: list[LabQuestionOut]


class LabOut(LabSummaryOut):
    """Laboratorio completo: caso de partida y pasos."""

    start: dict[str, Any]
    step_list: list[LabStepOut]
    closing: str


class LabCheckRequest(BaseModel):
    """Comprobar un paso sobre el caso del alumno (``POST /teaching/labs/check``)."""

    model_config = ConfigDict(extra="forbid")

    lab_id: str
    step_id: str
    design: DesignRequest
    answers: dict[str, str | float] = Field(default_factory=dict)


class LabCheckResultOut(BaseModel):
    """Resultado de una comprobación."""

    label: str
    ok: bool
    fact: str
    value: Any
    target: Any


class LabQuestionResultOut(BaseModel):
    """Corrección de una pregunta (``ok`` nulo en las abiertas)."""

    id: str
    ok: bool | None
    given: str | None
    expected_text: str | None
    message: str


class LabStepResultOut(BaseModel):
    """Estado del paso: hecho o no, comprobaciones, preguntas y los valores del caso."""

    lab_id: str
    step_id: str
    done: bool
    checks: list[LabCheckResultOut]
    questions: list[LabQuestionResultOut]
    values: dict[str, Any]


BatchRunRequest.model_rebuild()
