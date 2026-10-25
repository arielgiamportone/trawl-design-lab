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
    de los portones; ``coupled_doors`` libera los portones (la separación sale del equilibrio).
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
