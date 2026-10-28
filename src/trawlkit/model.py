"""Caso de diseño completo: encadena los módulos del motor en el orden del libro Excel.

:class:`DesignCase` reúne la red (estándar y, opcionalmente, modificada), el buque, el portón y
todos los parámetros que el libro ``Calculos_Red_FAO_A3.xlsx`` tiene escritos a mano (cada campo
cita su celda). :func:`run` ejecuta las etapas en el orden en que el libro las resuelve y devuelve
un :class:`DesignResult` con un dataclass por etapa.

Orden de las etapas (cada una es un helper privado ``_stage_*``)::

    geometry     Mecánica de la Red       d/l, Ss, St, pesos (estándar y modificada)
    dimensions   Dimensiones de la Red    relingas, largos, circunferencias, ángulo de corte
    power        Potencia disponible      reparto de energía, curvas de tiro, FT Fridman (L11:O19)
    drag         Resistencia de la RED    13 métodos; Aberdeen demersal = RN de diseño (Dickson NaN)
    rigging      Mec!B175:F186, Port!A33  cable filado Ls, LR·U2, flecha de la lima, bridas, pies
    doors        Portones y aparej.       Ds, polar, ROB, fuerzas, superficie requerida, Pφ
    floats       Flotación y Lastre       Koyama, Prado, Fridman por buque de la clase → Ffz (O261)
    spread       Mec!B162:P282, Dim!F61   DPA Fridman/geométrica/por corte, AH, AV (%, Suzuki,
                                          Martini, Fridman)
    drag         Res!C282:F290            columna de Dickson con AH = P164:P172 y AV = O272:O280
    bridles      Port!A63:E110            patentes (Dremiere, Martini), ángulo de ataque δ
    ballast      Flot!D153:I245           Koyama, Prado, Fridman, límites, distribución
    warps        Cables de Remolque       ángulos, diámetro, CD, Rw, total, peso, cargas, selección
    performance                           FT por propulsor frente a la resistencia total

El libro es circular en un punto (Dickson usa la DPA y la AV de Fridman, que usan la RN de
Aberdeen): como Dickson no alimenta la columna de Aberdeen, se calcula la tabla de resistencia dos
veces, la segunda sólo para rellenar Dickson. La AV de Fridman promedia la flotación de **todos**
los buques de la clase (``Mec!O261 = AVERAGE(Flot!N43, N55, F17, G17)``), por lo que la etapa de
flotación va antes que la de aberturas aunque en el libro figure después.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field, fields, is_dataclass, replace
from enum import Enum
from typing import Any, Generic, TypeVar

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel

from trawlkit import dimensions as dimensions_mod
from trawlkit import drag as drag_mod
from trawlkit import net as net_mod
from trawlkit import power as power_mod
from trawlkit import propulsion, rigging
from trawlkit.compat import Compat
from trawlkit.dimensions import NetDimensions
from trawlkit.drag import DragAverage, DragInputs, DragTable
from trawlkit.excel import excel_round
from trawlkit.i18n import N_, t
from trawlkit.io import Door, NetSpec, PropellerType, Vessel, load_catalogue
from trawlkit.net import NetGeometry
from trawlkit.performance import SpeedWindow, speed_window
from trawlkit.power import FridmanSummary, PowerCurves
from trawlkit.propulsion import PropellerPull, WinchCheck
from trawlkit.rigging import (
    BallastChain,
    BallastDistribution,
    BallastLimits,
    BridleLengths,
    CentreOfPressure,
    Crowfoot,
    DoorForces,
    DoorPolar,
    FloatDistribution,
    FridmanDpaTable,
    FridmanFlotation,
    FridmanSpread,
    FridmanVerticalOpening,
    MomentBalance,
    RequiredArea,
    RopeSpec,
    TowingGeometry,
    WarpAngles,
    WarpCylinderDrag,
    WarpLoads,
    WarpSelection,
    WarpStretch,
    WarpWeight,
    multirig,
    shrimp,
)
from trawlkit.rigging.shrimp import ShrimpOpening, TijeraBalance
from trawlkit.units import KNOT_TO_MS
from trawlkit.vessel import PowerBudget, power_budget

FloatArray = NDArray[np.float64]
T = TypeVar("T")

#: Vector de velocidades del libro (``'Potencia Disponible Arrastre OK'!B10:B18``) [kn].
DEFAULT_SPEEDS_KN: tuple[float, ...] = (1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0)
#: Cabos de relinga del libro (``'Cables Y Cabulleria'!D3:D4``) cuando la spec no los nombra.
DEFAULT_HEADROPE_ROPE = "COMBINADO 12 Acero6x24+7"
DEFAULT_FOOTROPE_ROPE = "COMBINADO 14 Acero6x24+7"
#: Diámetro de boya por defecto cuando ni el caso ni la spec fijan la cantidad (Flot!F92).
DEFAULT_FLOAT_DIAMETER_MM = 200.0


# ---------------------------------------------------------------------------------------------
# Serialización
# ---------------------------------------------------------------------------------------------


#: ``False`` mientras se serializa un resultado sin red modificada: cada :class:`Pair` escribe
#: ``"mod": None`` en lugar de repetir la columna estándar (ver :meth:`DesignResult.to_dict`).
_SERIALISE_MOD: ContextVar[bool] = ContextVar("_SERIALISE_MOD", default=True)


@contextmanager
def _serialising_mod(include_mod: bool) -> Iterator[None]:
    """Fija, dentro del bloque, si los :class:`Pair` serializan su variante modificada."""
    token = _SERIALISE_MOD.set(include_mod)
    try:
        yield
    finally:
        _SERIALISE_MOD.reset(token)


def _serialise(value: Any) -> Any:
    """Convierte arrays, enums, dataclasses y modelos pydantic a tipos serializables en JSON."""
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(k): _serialise(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_serialise(v) for v in value]
    if is_dataclass(value) and not isinstance(value, type):
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            return _serialise(to_dict())
        return {f.name: _serialise(getattr(value, f.name)) for f in fields(value)}
    return value


def _arr(x: Any) -> FloatArray:
    return np.asarray(x, dtype=float)


@dataclass(frozen=True)
class Pair(Generic[T]):
    """Columnas estándar (``F``) y modificada (``G``) del libro para un mismo resultado."""

    std: T
    mod: T

    def variant(self, name: str) -> T:
        """Valor de la variante ``"std"`` o ``"mod"``."""
        if name == "std":
            return self.std
        if name == "mod":
            return self.mod
        raise ValueError(t("variante desconocida: {name!r} (use 'std' o 'mod')", name=name))

    def to_dict(self, include_mod: bool | None = None) -> dict[str, Any]:
        """Representación serializable ``{"std": …, "mod": …}``.

        Con ``include_mod=False`` (o, si se omite, dentro de :meth:`DesignResult.to_dict` de un
        caso sin ``net_modified``) la variante modificada se escribe como ``None``: en ese caso
        el motor la calcula con la misma red estándar y no es un resultado propio.
        """
        if include_mod is None:
            include_mod = _SERIALISE_MOD.get()
        return {"std": _serialise(self.std), "mod": _serialise(self.mod) if include_mod else None}


# ---------------------------------------------------------------------------------------------
# Caso de diseño
# ---------------------------------------------------------------------------------------------


#: Portones por arte de arrastre simple (la hoja calcula fuerzas por portón).
DOORS_PER_RIG = 2


@dataclass(frozen=True)
class DesignCase:
    """Entradas de un caso de diseño: red, buque, portón y los parámetros fijos del libro.

    Cada parámetro numérico cita la celda del libro donde está escrito a mano. ``net_modified``
    es la columna ``G`` del libro (red modificada); si se omite se usa la misma red en ambas
    columnas y se anota en ``DesignResult.notes``. ``class_vessels`` son los otros buques de la
    clase (el libro calcula 150 y 180 BHP lado a lado): su flotación entra en el promedio Ffz
    de ``Mec!O261`` y el mayor BHP dimensiona el cable de remolque (``Rem!E110 = E81``).
    """

    net: NetSpec
    vessel: Vessel
    door: Door
    net_modified: NetSpec | None = None
    class_vessels: tuple[Vessel, ...] = ()
    speeds_kn: tuple[float, ...] = DEFAULT_SPEEDS_KN
    compat: Compat = Compat.CORRECTED

    # --- entradas de hoja ---------------------------------------------------------------
    depth_m: float | None = None  # Especie Blanco!E5 (None → net.species.depth_m)
    gallows_m: float | None = None  # Port!D6 = Tipo de buques!B5 (None → vessel.beam_m)
    vessel_depth_m: float | None = None  # Rem!E33 usa Tipo de buques!B6 (None → vessel.depth_m)
    ft_propeller: PropellerType = (
        PropellerType.FIXED_PITCH
    )  # PotOK!L11: FT PF → ROB, Flot!E42, Rem!C191

    # --- potencia -----------------------------------------------------------------------
    fridman_kf: float | None = None  # PotOK!D10/F10 (None → según hélice del buque)
    koyama_k: float | None = None  # PotOK!C170 = M165 (None → power.koyama_k(bhp))
    nomura_k3: float = power_mod.NOMURA_K3_EXCEL  # PotOK!E216 = MID(L208,1,4) = 0.17
    nomura_nhp: tuple[float, float] = drag_mod.NOMURA_NHP  # Res!D130:E130 (150 / 180)

    # --- portones -----------------------------------------------------------------------
    spread_per_m: float = 2.65  # Port!D7 (apertura por metro de cable)
    #: Separación de portones: "excel" (regla al metro de Port!E13, calibrada para la A-3 con
    #: pastecas a 2,5 m) o "fridman" (de la DPA de Fridman con el portón del caso; Fase 12).
    door_spread_rule: str = "excel"
    spread_correction_factor: float = 1.15  # Port!D28
    door_attack_angle_deg: float = 32.0  # Port!C134 (fila seleccionada de la polar)
    rob_share: float = 0.20  # Port!D210 = F146 (ROB = 20 % de FT)
    required_area_speed_range_kn: tuple[float, float] = (2.0, 4.0)  # Port!F212 = AVERAGE(E212:E216)
    sweep_lever_m: float = 3.0  # Port!E277

    # --- bridas, patentes y pies de gallo -------------------------------------------------
    bridle_angle_deg: float = 4.8  # Port!F39
    dan_leno_m: float = 0.6  # Dim!F64 = Port!F56 = Mec!O262
    bridle_chain_ratio: float = 0.095  # Port!D46
    sweeps_m: float = 25.0  # Dim!F65 = Mec!E213 (patentes de diseño)
    crowfoot_extension_m: float = 0.0  # Port!E99
    dremiere_ratio: float = 6.0  # Port!B68
    sweeps_martini_delta_deg: float = 20.0  # Port!H65
    sweeps_factor: float = 1.1  # Port!C83

    # --- aberturas ----------------------------------------------------------------------
    working_u2: float = 0.87  # Mec!E184 (U2 de la red trabajando; E183 = U1 = 0.5)
    warp_shallow_factor: float = 0.95  # Mec!F179 (Lsh = 0.95·Ls)
    warp_deep_factor: float = 0.85  # Mec!F180
    catenary_ratio: float = rigging.CATENARY_RATIO_EXCEL  # Mec!O266 (0.216, fijo)
    martini_mr_meshes: float = 12.0  # Mec!E270 = 3·4
    martini_factor: float = 0.05  # Mec!E272
    martini_mesh_mm: float | None = None  # Mec!E272 usa P!B156 (None → mallero del cuerpo)

    # --- flotación y lastre ---------------------------------------------------------------
    prado_flotation_k: float = 0.2  # Flot!I14
    prado_ballast_k: float = 0.28  # Flot!G168 / G176
    flotation_max_speed_kn: float = 3.0  # Flot!N43 = AVERAGE(L42:M46): 1–3 kn
    float_count: int | None = None  # Flot!F84 (12, elegido a mano; None → spec o catálogo)
    float_diameter_mm: float | None = None  # Flot!F92 (None → LOOKUP sobre el catálogo)
    float_wing_share: float = 0.7  # Flot!F103
    float_front_fifth_share: float = 0.6  # Flot!G106
    headrope_rope: str | None = None  # Cab!D3 (None → spec o COMBINADO 12)
    footrope_rope: str | None = None  # Cab!D4 (None → spec o COMBINADO 14)

    # --- componentes del catálogo (Fase 13; None = los del libro) --------------------------
    warp_id: str | None = None  # cable del catálogo de componentes (None → selección automática)
    float_id: str | None = None  # boya del catálogo de componentes
    twine_id: str | None = None  # hilo de todos los paños salvo el copo
    chain_id: str | None = None  # cadena de lastre y reglaje (lista de materiales)
    component_brands: tuple[str, ...] | None = None  # marcas para la selección automática
    component_region: str | None = None  # región del puerto para la selección automática
    generic_only: bool = False  # sólo componentes genéricos en la selección automática
    ballast_min_speed_kn: float = 1.0  # Flot!F225 = ROUNDDOWN(M197): modificada a 1 kn
    ballast_max_speed_kn: float = 3.0  # Flot!F226 = ROUNDUP(L201): estándar a 3 kn
    adjust_chain_m: float = 2.0  # Flot!F224

    # --- cables de remolque ---------------------------------------------------------------
    warp_nhp_hp: float | None = None  # Rem!E78 "180 HP" (None → mayor BHP de la clase)
    warp_safety_factor: float = 4.0  # Rem!D271
    warp_design_speed_kn: float = 3.5  # Rem!E267 = H123 (resistencia total a 3.5 kn)
    warp_spare_fraction: float = 0.5  # Cab!D12 = 2·Ls + 0.5·Ls
    warp_drag_shares: tuple[float, ...] = (0.05, 0.10)  # Rem!E191:H199

    # --- aparejo (Fase 12) ----------------------------------------------------------------
    rig: str | None = None  # otter, pair, outrigger, twin o beam (None → net.rig o "otter")
    pair_wing_spread_m: float | None = None  # pareja: separación de puntas de ala (None → ½ lima)
    # --- tangones, gemelo y vara (Fase 19.5; None = valor de la fuente) ------------------
    boom_length_m: float | None = None  # tangón (None → 24 pies, Knake et al. 1958)
    boom_angle_deg: float | None = None  # tangón (None → 20°, Knake et al. 1958; vara: 30°)
    boom_heel_offset_m: float = 0.0  # pie del tangón desde la crujía (FL 470: al pie del palo)
    outrigger_bridle_m: float | None = None  # tijera de cada red (None → 70 m, INIDEP 043/2022)
    outrigger_bridle_diameter_mm: float | None = None  # tijera (None → 22 mm, INIDEP 043/2022)
    clump_weight_kg: float | None = None  # muerto del gemelo (None → 1,5 portones, Seafish)
    clump_frontal_area_m2: float | None = None  # muerto (None → trineo de Bullis y Floyd 1972)
    beam_count: int | None = None  # varas por buque (None → 2, Eigaard et al. 2016)
    beam_length_m: float | None = None  # largo de cada vara (None → Eigaard et al. 2016 por kW)
    beam_diameter_m: float | None = None  # diámetro de la vara (None → C056/20, tabla 2)
    beam_shoe_area_m2: float | None = None  # área frontal de un patín (None → C056/20, tabla 2)
    beam_shoe_height_m: float | None = None  # alto del patín (None → C056/20, tabla 2)
    beam_ticklers: bool | None = None  # cadenas espantadoras (None → sí, salvo crustáceos)
    beam_weight_kg: float | None = None  # vara y patines en aire (None → sin rozamiento)
    # --- aberturas de redes camaroneras (Fase 19.7b) -------------------------------------
    opening_method: str = "auto"  # auto (tangones o gemelo → shrimp), book o shrimp
    shrimp_bridle_m: float | None = None  # cañas portón–ala (None → 3 m, INIDEP IAT 85/2024)

    # --- fondo ----------------------------------------------------------------------------
    seabed: str | None = None  # tipo de fondo (data/seabed.yaml); None = sin rozamiento extra

    # --- informe --------------------------------------------------------------------------
    report_speeds_kn: tuple[float, ...] = (2.0, 3.0, 3.5)  # velocidades de la RN en summary()
    #: Supuestos con que se armó el caso (``trawlkit.catalog.catalog_case``); van a las notas.
    assumptions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Normaliza y valida las entradas."""
        speeds = tuple(float(v) for v in self.speeds_kn)
        if not speeds or any(v <= 0 for v in speeds) or any(np.diff(speeds) <= 0):
            raise ValueError(t("speeds_kn debe ser un vector no vacío, positivo y creciente"))
        object.__setattr__(self, "speeds_kn", speeds)
        object.__setattr__(self, "class_vessels", tuple(self.class_vessels))
        object.__setattr__(self, "compat", Compat(self.compat))
        object.__setattr__(self, "ft_propeller", PropellerType(self.ft_propeller))
        if self.component_brands is not None:
            object.__setattr__(self, "component_brands", tuple(self.component_brands))
        if self.twine_id is not None:
            from trawlkit.components import TwineItem, apply_twine, get_component

            try:
                twine = get_component("twine", self.twine_id)
            except KeyError as exc:
                raise ValueError(str(exc)) from exc
            assert isinstance(twine, TwineItem)
            object.__setattr__(self, "net", apply_twine(self.net, twine))
            if self.net_modified is not None:
                object.__setattr__(self, "net_modified", apply_twine(self.net_modified, twine))
        if self.working_depth_m <= 0:
            raise ValueError(
                t("hace falta la profundidad de trabajo (depth_m o net.species.depth_m)")
            )
        if self.gallows_spacing_m <= 0:
            raise ValueError(
                t("hace falta la distancia entre pastecas (gallows_m o vessel.beam_m)")
            )
        if self.hull_depth_m <= 0:
            raise ValueError(t("hace falta el puntal (vessel_depth_m o vessel.depth_m)"))
        if not 0.0 < self.rob_share < 1.0:
            raise ValueError(t("rob_share debe estar entre 0 y 1"))
        if self.door_spread_rule not in ("excel", "fridman"):
            raise ValueError(t("door_spread_rule debe ser 'excel' o 'fridman'"))
        if self.opening_method not in shrimp.OPENING_METHODS:
            raise ValueError(
                t(
                    "opening_method debe ser uno de {methods}, no {method!r}",
                    methods=", ".join(shrimp.OPENING_METHODS),
                    method=self.opening_method,
                )
            )
        if self.rig_kind not in multirig.RIGS:
            raise ValueError(
                t(
                    "rig debe ser uno de {rigs}, no {rig!r}",
                    rigs=", ".join(multirig.RIGS),
                    rig=self.rig_kind,
                )
            )
        for name in (
            "boom_length_m",
            "outrigger_bridle_m",
            "outrigger_bridle_diameter_mm",
            "clump_frontal_area_m2",
            "beam_length_m",
            "beam_diameter_m",
            "beam_shoe_area_m2",
            "beam_shoe_height_m",
            "shrimp_bridle_m",
        ):
            value = getattr(self, name)
            if value is not None and value <= 0:
                raise ValueError(t("{name} debe ser positivo", name=name))
        for name in ("clump_weight_kg", "beam_weight_kg"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(t("{name} no puede ser negativo", name=name))
        if self.boom_angle_deg is not None and not 0.0 <= self.boom_angle_deg < 90.0:
            raise ValueError(t("boom_angle_deg debe estar entre 0 y 90°"))
        if self.beam_count is not None and self.beam_count not in (1, 2):
            raise ValueError(t("beam_count debe ser 1 o 2"))
        if self.pair_wing_spread_m is not None and self.pair_wing_spread_m <= 0:
            raise ValueError(t("pair_wing_spread_m debe ser positivo"))
        if self.door.area_m2 is None or self.door.length_m is None:
            raise ValueError(t("el portón {door!r} necesita area_m2 y length_m", door=self.door.id))
        try:
            rigging.door_polar(
                self.door,
                self.door_attack_angle_deg,
                interpolate=self.compat is Compat.CORRECTED,
            )
        except KeyError as exc:
            raise ValueError(str(exc)) from exc
        if self.ft_propeller not in power_mod.FRIDMAN_KF:
            raise ValueError(
                t(
                    "ft_propeller {prop!r} no tiene KF de Fridman tabulado",
                    prop=self.ft_propeller.value,
                )
            )
        if self.warp_design_speed_kn not in speeds:
            raise ValueError(t("warp_design_speed_kn debe pertenecer a speeds_kn"))
        for v in (self.ballast_min_speed_kn, self.ballast_max_speed_kn):
            if v not in speeds:
                raise ValueError(t("ballast_min/max_speed_kn deben pertenecer a speeds_kn"))
        if self.seabed is not None:
            try:
                rigging.seabed(self.seabed)
            except KeyError as exc:
                raise ValueError(str(exc)) from exc

    # --- derivados ------------------------------------------------------------------------

    @property
    def rig_kind(self) -> str:
        """Aparejo: ``otter`` (portones) o ``pair`` (pareja de buques, sin portones)."""
        return str(self.rig or self.net.rig or "otter")

    @property
    def is_pair(self) -> bool:
        """Si el aparejo es de pareja."""
        return self.rig_kind == "pair"

    @property
    def is_beam(self) -> bool:
        """Si el arte es de vara (Fase 19.5): sin portones, la vara fija la abertura."""
        return self.rig_kind == "beam"

    @property
    def is_multi(self) -> bool:
        """Si el aparejo es de tangones, gemelo o vara (:class:`RigStage`, Fase 19.5)."""
        return self.rig_kind in multirig.MULTI_RIGS

    @property
    def n_nets(self) -> int:
        """Redes que remolca el buque: 2 con tangones o gemelo, una por vara, 1 si no."""
        if self.rig_kind in ("outrigger", "twin"):
            return 2
        if self.is_beam:
            return int(self.beam_count or multirig.BEAMS_PER_VESSEL)
        return 1

    @property
    def species_texts(self) -> tuple[str | None, ...]:
        """Especie objetivo, nombre y nombre científico de la red (para reconocer camaroneras)."""
        sp = self.net.species
        return (
            self.net.target_species,
            None if sp is None else sp.name,
            None if sp is None else sp.scientific_name,
        )

    @property
    def uses_shrimp_opening(self) -> bool:
        """Si las aberturas salen del método camaronero (Fase 19.7b, :mod:`~.rigging.shrimp`).

        ``auto``: con tangones o gemelo. Con portones (aunque la red sea de crustáceos, como la
        langostilla de la A-3) sigue el promedio del libro salvo ``opening_method="shrimp"``.
        Nunca en la pareja ni en la vara (no hay portones).
        """
        if self.opening_method == "book" or self.is_pair or self.is_beam:
            return False
        return self.opening_method == "shrimp" or self.rig_kind in ("outrigger", "twin")

    @property
    def shrimp_bridle(self) -> float:
        """Cañas portón–ala del método camaronero [m] (el caso o 3 m, INIDEP IAT 85/2024)."""
        if self.shrimp_bridle_m is not None:
            return float(self.shrimp_bridle_m)
        return shrimp.SHRIMP_BRIDLE_M

    @property
    def power_kw(self) -> float:
        """Potencia del motor [kW] (``engine_kw`` del buque o BHP·0,7457)."""
        return float(self.vessel.engine_kw or self.vessel.bhp * 0.7457)

    @property
    def beam_metier(self) -> str:
        """Métier de la vara de Eigaard et al. (2016): ``CRU`` (crustáceos) o ``DMF``."""
        sp = self.net.species
        crust = multirig.is_crustacean(
            self.net.target_species,
            None if sp is None else sp.name,
            None if sp is None else sp.scientific_name,
        )
        return "CRU" if crust else "DMF"

    @property
    def beam_class(self) -> str:
        """Clase de buque de C056/20 por la potencia: ``small`` (≤ 221 kW) o ``large``."""
        return multirig.beam_class(self.power_kw)

    @property
    def beam_length(self) -> float:
        """Largo de cada vara [m]: el del caso o el ancho total de Eigaard et al. / varas."""
        if self.beam_length_m is not None:
            return float(self.beam_length_m)
        total = multirig.beam_width_total_m(self.power_kw, self.beam_metier)
        return total / self.n_nets

    @property
    def boom_length(self) -> float | None:
        """Largo del tangón [m]: el del caso, 24 pies (FL 470) con tangones; sin dato en la vara."""
        if self.boom_length_m is not None:
            return float(self.boom_length_m)
        return multirig.BOOM_LENGTH_M if self.rig_kind == "outrigger" else None

    @property
    def boom_angle(self) -> float:
        """Ángulo del tangón [°]: el del caso, 20° (FL 470) o 30° en la vara (Verhoest y Maton)."""
        if self.boom_angle_deg is not None:
            return float(self.boom_angle_deg)
        return multirig.BEAM_BOOM_ANGLE_DEG if self.is_beam else multirig.BOOM_ANGLE_DEG

    @property
    def working_depth_m(self) -> float:
        """Profundidad de trabajo (Especie Blanco!E5)."""
        if self.depth_m is not None:
            return float(self.depth_m)
        if self.net.species is not None and self.net.species.depth_m is not None:
            return float(self.net.species.depth_m)
        return 0.0

    @property
    def gallows_spacing_m(self) -> float:
        """Distancia entre pastecas (Port!D6): ``gallows_m``, la del buque o, si no, su manga."""
        if self.gallows_m is not None:
            return float(self.gallows_m)
        if self.vessel.gallows_spacing_m is not None:  # Fase 19.4
            return float(self.vessel.gallows_spacing_m)
        return float(self.vessel.beam_m or 0.0)

    @property
    def hull_depth_m(self) -> float:
        """Altura de las pastecas sobre el agua (Tipo de buques!B6: el libro usa el puntal).

        ``vessel_depth_m``, la altura de las pastecas del buque (Fase 19.4) o, si no, su puntal.
        """
        if self.vessel_depth_m is not None:
            return float(self.vessel_depth_m)
        if self.vessel.gallows_height_m is not None:
            return float(self.vessel.gallows_height_m)
        return float(self.vessel.depth_m or 0.0)

    @property
    def vessel_class(self) -> tuple[Vessel, ...]:
        """Buques de la clase (el de diseño y ``class_vessels``), sin repetir, por BHP creciente."""
        seen: dict[str, Vessel] = {}
        for v in (self.vessel, *self.class_vessels):
            seen.setdefault(v.id, v)
        return tuple(sorted(seen.values(), key=lambda v: (v.bhp, v.id)))

    @property
    def warp_sizing_nhp_hp(self) -> float:
        """NHP con el que Águila dimensiona el cable (Rem!E80:E81; el libro usa 180 HP)."""
        if self.warp_nhp_hp is not None:
            return float(self.warp_nhp_hp)
        return max(v.bhp for v in self.vessel_class)

    @property
    def speeds(self) -> FloatArray:
        """Velocidades en nudos como array."""
        return _arr(self.speeds_kn)

    @property
    def speeds_ms(self) -> FloatArray:
        """Velocidades en m/s (``0.5144·kn``, PotOK!B272)."""
        return self.speeds * KNOT_TO_MS

    def speed_index(self, speed_kn: float) -> int:
        """Posición de una velocidad en ``speeds_kn``."""
        matches = np.flatnonzero(np.isclose(self.speeds, speed_kn))
        if matches.size == 0:
            raise ValueError(t("velocidad {v} kn no está en speeds_kn", v=speed_kn))
        return int(matches[0])

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable (las specs y catálogos se citan por ``id``)."""
        out: dict[str, Any] = {}
        for f in fields(self):
            v = getattr(self, f.name)
            if f.name in {"net", "net_modified"}:
                out[f.name] = None if v is None else v.id
            elif f.name in {"vessel", "door"}:
                out[f.name] = v.id
            elif f.name == "class_vessels":
                out[f.name] = [x.id for x in v]
            else:
                out[f.name] = _serialise(v)
        return out


# ---------------------------------------------------------------------------------------------
# Resultados por etapa
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class PowerStage:
    """Potencia: reparto de energía, curvas de tiro y resumen de Fridman (PotOK!L11:O19)."""

    budget: PowerBudget
    curves: PowerCurves
    fridman: FridmanSummary
    class_fridman: dict[str, FridmanSummary]
    ft_propeller: PropellerType
    ft_kgf: FloatArray
    koyama_ehp_hp: float
    #: Tiro por la hélice (Wärtsilä; Fase 19.4), sólo si el buque trae el diámetro de la hélice.
    propeller: PropellerPull | None = None

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {f.name: _serialise(getattr(self, f.name)) for f in fields(self)}


@dataclass(frozen=True)
class DragStage:
    """Resistencia de la red: tabla de métodos y RN de diseño (Aberdeen demersal) en kgf."""

    inputs: DragInputs
    table: DragTable
    average: DragAverage
    design_method: str
    rn: Pair[FloatArray]

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {f.name: _serialise(getattr(self, f.name)) for f in fields(self)}


@dataclass(frozen=True)
class RiggingGeometry:
    """Datos de maniobra (Mec!B175:F186), flecha de la lima, bridas y pies de gallo."""

    towing: TowingGeometry
    vertical_opening_m: float
    headrope_sag_m: float
    catenary_ratio: float
    bridles: BridleLengths
    crowfoot: Crowfoot

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {f.name: _serialise(getattr(self, f.name)) for f in fields(self)}


@dataclass(frozen=True)
class DoorStage:
    """Portones (hoja 'Portones y aparejamiento')."""

    door: Door
    polar: DoorPolar
    spread_m: float
    half_divergence_deg: float
    spread_corrected_m: float
    rob_share: float
    rob_share_kgf: FloatArray
    rob_shares_kgf: dict[str, FloatArray]
    forces: DoorForces
    """Fuerzas de UN portón (Port!D190:E198)."""
    rig_drag_kgf: FloatArray
    """Resistencia de los dos portones del arte: ``DOORS_PER_RIG · forces.drag_kgf``."""
    required_area_m2: FloatArray
    required_area: RequiredArea
    required_area_class: dict[str, RequiredArea]
    required_area_per_door_class_m2: float
    force_kgf: FloatArray
    centre_of_pressure: CentreOfPressure
    moments: MomentBalance
    #: Equilibrio portón–tijera–red a la velocidad de diseño (método camaronero con tangones,
    #: Fase 19.7b) y la separación que daba la regla del libro; ``None`` en los demás casos.
    tijera: TijeraBalance | None = None
    book_spread_m: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable (sin los campos de la Fase 19.7b cuando no aplican)."""
        return {
            f.name: _serialise(getattr(self, f.name))
            for f in fields(self)
            if not (f.name in ("tijera", "book_spread_m") and getattr(self, f.name) is None)
        }


@dataclass(frozen=True)
class VerticalOpening:
    """Abertura vertical por los distintos métodos (Mec!J242:P282)."""

    suzuki_m: float
    prado_m: dict[str, float]
    izzo_m: tuple[float, ...]
    martini_dv_m: float
    martini_m: float
    flotation_total_kgf: float
    fridman: Pair[FridmanVerticalOpening]

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {f.name: _serialise(getattr(self, f.name)) for f in fields(self)}


@dataclass(frozen=True)
class SpreadStage:
    """Aberturas: DPA (Fridman, geométrica, por corte), AH y AV."""

    fridman: FridmanSpread
    table: FridmanDpaTable
    dpa_geometric_m: float
    dpa_working_m: float
    dpa_cut_angle_m: float
    horizontal_opening_m: float
    dpa_over_headrope: float
    catenary_ratio_table: float
    vertical: VerticalOpening
    #: Aberturas por el método camaronero (Fase 19.7b); ``None`` con el promedio del libro.
    shrimp: ShrimpOpening | None = None

    @property
    def vertical_opening_m(self) -> float:
        """AV informada: la del método camaronero o la de Suzuki (Dim!F60)."""
        if self.shrimp is not None:
            return self.shrimp.vertical_opening_m
        return float(self.vertical.suzuki_m)

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable (sin ``shrimp`` cuando no aplica)."""
        return {
            f.name: _serialise(getattr(self, f.name))
            for f in fields(self)
            if not (f.name == "shrimp" and self.shrimp is None)
        }


@dataclass(frozen=True)
class BridleStage:
    """Bridas, patentes y pies de gallo (Port!A33:E110)."""

    lengths: BridleLengths
    crowfoot: Crowfoot
    sweeps_m: float
    sweeps_plus_bridle_m: float
    sweeps_dremiere_m: float
    sweeps_martini_m: float
    sweeps_no_triangle_m: float
    sweeps_triangle_m: float
    attack_angle_deg: float

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {f.name: _serialise(getattr(self, f.name)) for f in fields(self)}


@dataclass(frozen=True)
class FloatStage:
    """Flotación de la lima (Flot!E2:J146)."""

    koyama_kgf: float
    prado_kgf: float
    headrope_rope: RopeSpec
    headrope_weight_air_kg: float
    headrope_weight_water_kgf: float
    beta_deg: float
    fridman: Pair[FridmanFlotation]
    fridman_average_kgf: float
    class_fridman_average_kgf: dict[str, float]
    class_prado_kgf: dict[str, float]
    flotation_total_kgf: float
    flotation_rounded_kgf: float
    catalogue_diameters_mm: tuple[float, ...]
    catalogue_buoyancy_kgf: tuple[float, ...]
    catalogue_counts: FloatArray
    count: int
    diameter_mm: float
    distribution: FloatDistribution
    cd: FloatArray
    reynolds: FloatArray
    drag_kgf: FloatArray

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {f.name: _serialise(getattr(self, f.name)) for f in fields(self)}


@dataclass(frozen=True)
class BallastStage:
    """Lastre del burlón (Flot!D153:I245)."""

    koyama_kg: float
    prado_kg: float
    footrope_rope: RopeSpec
    footrope_weight_air_kg: float
    footrope_weight_water_kgf: float
    fridman: Pair[FloatArray]
    limits: BallastLimits
    adjust_chain_weight_kg: float
    even_kg_m: float
    distribution_min: BallastDistribution
    distribution_max: BallastDistribution
    #: Lastre en metros de la cadena del caso (``chain_id``; Fase 19.2; no está en el libro).
    chain: BallastChain | None = None

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {f.name: _serialise(getattr(self, f.name)) for f in fields(self)}


@dataclass(frozen=True)
class WarpStage:
    """Cables de remolque (hoja 'Cables de Remolque' y Cab!D11:D12)."""

    warp_m: float
    sweeps_plus_bridle_m: float
    dpa_a_m: float
    dpa_b_m: float
    angles: WarpAngles
    diameter_ehp_mm: float
    diameter_aguila_mm: float
    sizing_nhp_hp: float
    diameter_mm: float
    cd_angle_deg: float
    cd: float
    drag_kgf: FloatArray
    total: Pair[FloatArray]
    cylinder: WarpCylinderDrag
    shares_kgf: dict[str, FloatArray]
    cd_maclennan: FloatArray
    weight: WarpWeight
    loads: WarpLoads
    selection: WarpSelection
    quantity_m: float
    #: Tensión, rigidez y estiramiento elástico del cable elegido a la velocidad de diseño
    #: (Fase 19.1; no está en el libro).
    stretch: WarpStretch | None = None
    #: Guinche y tambor del buque frente al cable (Fase 19.4; sólo si el buque trae esos datos).
    winch: WinchCheck | None = None

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {f.name: _serialise(getattr(self, f.name)) for f in fields(self)}


@dataclass(frozen=True)
class PerformanceStage:
    """Ventanas de velocidad FT(v) ≥ R(v) por propulsor y variante."""

    windows: dict[str, SpeedWindow]
    demand: Pair[FloatArray]
    design_key: str
    #: Rozamiento con el fondo del tren (burlón + lastre) y de los dos portones [kgf], incluido
    #: en ``demand`` cuando el caso indica ``seabed`` (0 si no).
    seabed_friction_kgf: float = 0.0

    @property
    def design(self) -> SpeedWindow:
        """Ventana del propulsor de FT (``ft_propeller``) con la red estándar."""
        return self.windows[self.design_key]

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {f.name: _serialise(getattr(self, f.name)) for f in fields(self)}


@dataclass(frozen=True)
class RigStage:
    """Tangones, gemelo o vara (Fase 19.5): planta del aparejo y resistencia de todo el arte.

    Las etapas del libro calculan **una** red con su par de portones (``doors.spread_m`` es la
    separación de los puntos de remolque de esa red: sus dos portones con tangones, portón y muerto
    en el gemelo, los extremos de la vara en la vara). Esta etapa suma las redes, los portones, los
    cables, la tijera, el muerto o los componentes de la vara (todo en kgf):

    * ``per_net``: una red con su parte del aparejo (RN + boyas + portones + un cable + tijera o
      medio muerto; en la vara RN + vara, patines, tren, cadenas y un cable);
    * ``warp_load``: lo que remolca cada grupo de cables (una red por cable con tangones y varas;
      todo el arte en el gemelo, como el libro con sus dos cables);
    * ``demand``: ``n_nets·per_net`` más el rozamiento con el fondo, frente al tiro del buque.
    """

    kind: str
    n_nets: int
    n_doors: int
    n_warps: int
    net_spread_m: float
    door_spread_total_m: float
    swept_width_m: float
    vertical_opening_m: float
    per_net: Pair[FloatArray]
    warp_load: Pair[FloatArray]
    warp_drag_kgf: FloatArray
    doors_drag_kgf: FloatArray
    friction_kgf: float
    demand: Pair[FloatArray]
    layout: multirig.OutriggerLayout | None = None
    boom_length_m: float | None = None
    boom_angle_deg: float | None = None
    bridle_m: float | None = None
    bridle_diameter_mm: float | None = None
    bridle_drag_kgf: FloatArray | None = None
    clump_weight_kg: float | None = None
    clump_frontal_area_m2: float | None = None
    clump_drag_kgf: FloatArray | None = None
    beam: multirig.BeamDrag | None = None
    watson_door_area_m2: tuple[float, float] | None = None
    watson_spread_m: tuple[float, float] | None = None
    #: Valores por defecto usados y su fuente (también van a las notas de la corrida).
    sources: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {f.name: _serialise(getattr(self, f.name)) for f in fields(self)}


@dataclass(frozen=True)
class DesignResult:
    """Resultado de :func:`run`: un dataclass por etapa más las notas de la corrida."""

    case: DesignCase
    geometry: Pair[NetGeometry]
    dimensions: Pair[NetDimensions]
    power: PowerStage
    drag: DragStage
    rigging: RiggingGeometry
    doors: DoorStage
    spread: SpreadStage
    bridles: BridleStage
    floats: FloatStage
    ballast: BallastStage
    warps: WarpStage
    performance: PerformanceStage
    notes: list[str] = field(default_factory=list)
    #: Tangones, gemelo o vara (Fase 19.5); ``None`` con portones o pareja.
    multirig: RigStage | None = None

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable en JSON (arrays → listas).

        Si el caso no trae red modificada (``case.net_modified is None``) cada :class:`Pair`
        se serializa como ``{"std": …, "mod": None}``: la columna modificada sería una copia
        fantasma de la estándar. :meth:`summary` no cambia (sólo usa la estándar). ``multirig``
        sólo aparece con tangones, gemelo o vara.
        """
        with _serialising_mod(self.case.net_modified is not None):
            return {
                f.name: _serialise(getattr(self, f.name))
                for f in fields(self)
                if not (f.name == "multirig" and self.multirig is None)
            }

    def summary(self) -> dict[str, float | str | None]:
        """Resumen 'Dimensiones de la Red'!F45:F71 más RN, ROB, boyas, lastre, cable y velocidad."""
        dims = self.dimensions.std
        case = self.case
        out: dict[str, float | str | None] = {
            "net_id": case.net.id,
            "vessel_id": case.vessel.id,
            "door_id": case.door.id,
            "compat": case.compat.value,
            "headrope_m": dims.headrope_m,  # F45
            "footrope_m": dims.footrope_m,  # F46
            "cut_angle_deg": dims.cut_angle_deg,  # F55
            "filtration_index": dims.filtration_index,  # F56
            "solid_surface_m2": dims.solid_surface_m2,  # F57
            "working_surface_m2": dims.working_surface_m2,  # F58
            "net_weight_kg": dims.net_weight_kg,  # F59
            "vertical_opening_m": self.spread.vertical_opening_m,  # F60 (Suzuki o Fase 19.7b)
            "horizontal_opening_m": self.spread.horizontal_opening_m,  # F61
            "working_depth_m": case.working_depth_m,  # F62
            "flotation_total_kgf": self.floats.flotation_rounded_kgf,  # F63
            "dan_leno_m": case.dan_leno_m,  # F64
            "sweeps_m": case.sweeps_m,  # F65
            "crowfoot_m": self.bridles.crowfoot.length_m,  # F66
            "crowfoot_extension_m": self.bridles.crowfoot.extension_m,  # F67
            "upper_bridle_m": self.bridles.lengths.upper_m,  # F68
            "lower_bridle_m": self.bridles.lengths.lower_m,  # F69
            "warp_diameter_mm": self.warps.selection.diameter_mm,  # F70
            "warp_length_m": self.warps.warp_m,  # F71
        }
        for v in case.report_speeds_kn:
            i = case.speed_index(v)
            tag = f"{v:g}".replace(".", "_")
            out[f"rn_std_{tag}kn_kgf"] = float(self.drag.rn.std[i])
            out[f"rob_{tag}kn_kgf"] = float(_arr(self.doors.forces.drag_kgf)[i])
        out.update(
            {
                "float_count": self.floats.count,
                "float_diameter_mm": self.floats.diameter_mm,
                "ballast_min_kg": self.ballast.limits.min_kg,
                "ballast_max_kg": self.ballast.limits.max_kg,
                "warp_selected": self.warps.selection.id,
                "warp_breaking_load_t": self.warps.selection.breaking_load_t,
                "warp_min_breaking_load_kgf": self.warps.loads.min_breaking_load_kgf,
                "warp_quantity_m": self.warps.quantity_m,
                "max_speed_kn": self.performance.design.max_speed_kn,
            }
        )
        st = self.warps.stretch
        if st is not None and case.compat is Compat.CORRECTED:
            # Fase 19.1 (fuera del libro: sólo en modo corregido).
            out["warp_tension_kgf"] = st.tension_kgf
            out["warp_stretch_m"] = st.stretch_m
            out["warp_safety_factor"] = st.safety_factor
        if case.seabed is not None:
            out["seabed"] = case.seabed
            out["seabed_friction_kgf"] = self.performance.seabed_friction_kgf
        pp = self.power.propeller
        if pp is not None:  # Fase 19.4: sólo con diámetro de hélice
            out["propeller_bollard_pull_t"] = pp.bollard_pull_t
            out["propeller_max_speed_kn"] = self.performance.windows[
                f"{PROPELLER_MODEL_KEY}_std"
            ].max_speed_kn
        if self.warps.winch is not None:
            out["winch_drum_required_m"] = self.warps.winch.drum_required_m
        op = self.spread.shrimp
        if op is not None:  # Fase 19.7b: método camaronero de aberturas
            out["opening_method"] = op.method
            out["door_spread_m"] = op.door_spread_m
        mr = self.multirig
        if mr is not None:  # Fase 19.5: tangones, gemelo o vara
            out["rig"] = mr.kind
            out["n_nets"] = mr.n_nets
            out["net_spread_m"] = mr.net_spread_m
            out["door_spread_total_m"] = mr.door_spread_total_m
            out["swept_width_m"] = mr.swept_width_m
            if mr.kind == "beam":
                out["vertical_opening_m"] = mr.vertical_opening_m
                out["beam_length_m"] = mr.net_spread_m
            if mr.layout is not None:
                out["boom_tip_offset_m"] = mr.layout.tip_offset_m
                out["nets_gap_m"] = mr.layout.gap_m
            if mr.clump_weight_kg is not None:
                out["clump_weight_kg"] = mr.clump_weight_kg
            for v in case.report_speeds_kn:
                i = case.speed_index(v)
                tag = f"{v:g}".replace(".", "_")
                out[f"net_total_{tag}kn_kgf"] = float(mr.per_net.std[i])
                out[f"total_drag_{tag}kn_kgf"] = float(mr.demand.std[i])
        return out


# ---------------------------------------------------------------------------------------------
# Etapas
# ---------------------------------------------------------------------------------------------


def _ft_of(summary: FridmanSummary, propeller: PropellerType) -> FloatArray:
    """Columna de FT de Fridman del propulsor (PotOK!L/N paso fijo, M/O paso variable + tobera)."""
    if propeller is PropellerType.FIXED_PITCH:
        return summary.ft_fixed_pitch_kgf
    return summary.ft_variable_pitch_nozzle_kgf


def _stage_geometry(case: DesignCase) -> Pair[NetGeometry]:
    """'Mecánica de la Red' para las columnas estándar y modificada."""
    std = net_mod.analyse(case.net, case.compat)
    mod = net_mod.analyse(case.net_modified, case.compat) if case.net_modified else std
    return Pair(std, mod)


def _stage_dimensions(case: DesignCase, geometry: Pair[NetGeometry]) -> Pair[NetDimensions]:
    """'Dimensiones de la Red' (columna F con la estándar, G con la modificada)."""
    std = dimensions_mod.compute(case.net, geometry.std, case.compat, modified=False)
    mod_spec = case.net_modified if case.net_modified is not None else case.net
    mod = dimensions_mod.compute(mod_spec, geometry.mod, case.compat, modified=True)
    return Pair(std, mod)


def _stage_power(case: DesignCase) -> PowerStage:
    """'Potenc disponible' y 'Potencia Disponible Arrastre OK' para el buque y su clase."""
    v = case.vessel
    curves = power_mod.power_curves(
        v,
        case.speeds,
        kf=case.fridman_kf,
        koyama_k_value=case.koyama_k,
        nomura_k3=case.nomura_k3,
    )
    class_fridman = {cv.id: power_mod.summary(cv, case.speeds) for cv in case.vessel_class}
    fridman = class_fridman[v.id]
    k = power_mod.koyama_k(v.bhp) if case.koyama_k is None else case.koyama_k
    return PowerStage(
        budget=power_budget(v.bhp),
        curves=curves,
        fridman=fridman,
        class_fridman=class_fridman,
        ft_propeller=case.ft_propeller,
        ft_kgf=_ft_of(fridman, case.ft_propeller),
        koyama_ehp_hp=power_mod.koyama_ehp_hp(power_mod.koyama_bhp_f_hp(v.bhp), k),  # PotOK!C171
        propeller=propulsion.propeller_pull(v, case.speeds),
    )


def _stage_drag(
    case: DesignCase,
    geometry: Pair[NetGeometry],
    dimensions: Pair[NetDimensions],
    ah_m: FloatArray | None = None,
    av_m: FloatArray | None = None,
) -> DragStage:
    """'Resistencia de la RED'. Sin ``ah_m``/``av_m`` la columna de Dickson queda en NaN."""
    d_std, d_mod = dimensions.std, dimensions.mod
    inputs = DragInputs(
        dl_std=geometry.std.filtration_index,  # E4 = Mec!K15
        dl_mod=geometry.mod.filtration_index,  # E5 = Mec!K17
        circumference_m=d_std.fishing_circle_m,  # E6 = Dim!D97
        length_with_bag_std_m=d_std.total_length_m,  # E69 = Dim!F47
        length_with_bag_mod_m=d_mod.total_length_m,  # E70 = Dim!G47
        length_without_bag_std_m=d_std.body_length_no_bag_m,  # D86 = Largototal
        length_without_bag_mod_m=d_mod.body_length_no_bag_m,  # D87 = Dim!G48
        st_std_m2=geometry.std.working_surface_m2,  # D110 = Dim!F58
        st_mod_m2=geometry.mod.working_surface_m2,  # D111 = Dim!G58
        ss_std_m2=geometry.std.solid_surface_m2,  # F149 = Dim!F57
        ss_mod_m2=geometry.mod.solid_surface_m2,  # F150 = Dim!G57
        headrope_m=d_std.headrope_m,  # I25 = Lima
        footrope_m=d_std.footrope_m,  # I26 = Burlon
        alpha_deg=d_std.cut_angle_deg,  # D112 = Dim!G55 (= F55)
        nhp=case.nomura_nhp,
        ah_m=None if ah_m is None else tuple(float(x) for x in ah_m),
        av_m=None if av_m is None else tuple(float(x) for x in av_m),
    )
    table = drag_mod.drag_table(inputs, case.speeds, case.compat)
    kgf = table.kgf
    return DragStage(
        inputs=inputs,
        table=table,
        average=drag_mod.average(table, case.compat),
        design_method=drag_mod.DESIGN_METHOD,
        rn=Pair(_arr(kgf.design_rn("std")), _arr(kgf.design_rn("mod"))),
    )


def _stage_rigging(case: DesignCase, dimensions: Pair[NetDimensions]) -> RiggingGeometry:
    """Cable filado, red trabajando, flecha de la lima, bridas a un punto y pies de gallo.

    Mec!E176:E186 necesita la brida superior (Dim!F68 = Port!D44), que sólo depende de la AV de
    Suzuki (Mec!D255) y de la flecha de la lima (Mec!O267 = 0.216·Lima).
    """
    dims = dimensions.std
    av = rigging.vertical_opening_suzuki_m(dims.max_circumference_m)  # Mec!D255 → Dim!F60
    sag = rigging.headrope_sag_m(dims.headrope_m, case.catenary_ratio)  # Mec!O267
    bridles = rigging.bridle_lengths(
        av, sag, case.bridle_angle_deg, case.dan_leno_m, case.bridle_chain_ratio
    )
    towing = rigging.towing_geometry(
        case.working_depth_m,
        dims.body_length_no_bag_m,  # Mec!E182 = Res!D86 = Largototal
        bridles.upper_m,  # Mec!E186 = Dim!F68
        u2=case.working_u2,
        shallow_factor=case.warp_shallow_factor,
        deep_factor=case.warp_deep_factor,
    )
    assert case.door.length_m is not None
    # En la pareja y en la vara no hay portón: el cable se une a las patentes (o a la vara) sin
    # pie de gallo.
    door_length = 0.0 if case.is_pair or case.is_beam else case.door.length_m
    crowfoot = rigging.crowfoot_m(door_length, case.crowfoot_extension_m)  # Port!E97:E99
    return RiggingGeometry(
        towing=towing,
        vertical_opening_m=av,
        headrope_sag_m=sag,
        catenary_ratio=case.catenary_ratio,
        bridles=bridles,
        crowfoot=crowfoot,
    )


def pair_wing_spread_m(case: DesignCase) -> float:
    """Separación de puntas de ala de la pareja [m]: la del caso o la mitad de la lima.

    Los documentos de la FAO y la BOBP no miden la separación de la pareja: el patrón ajusta la
    distancia entre los buques. Por defecto se supone que las puntas de ala trabajan separadas la
    mitad de la lima (regla habitual de aparejamiento; supuesto documentado, ``notes``).
    """
    if case.pair_wing_spread_m is not None:
        return float(case.pair_wing_spread_m)
    head = case.net.headrope.length_m if case.net.headrope is not None else None
    if head is None:
        head = dimensions_mod.compute(case.net, compat=case.compat).headrope_m
    return 0.5 * float(head)


def pair_towing_spread_m(case: DesignCase, rig: RiggingGeometry) -> float:
    """Separación de los puntos de remolque de la pareja [m] (unión cable-patente).

    Invierte la regla de triángulos semejantes de Mec!L225 (DPA = Ds·LRw/(LRw + aparejo)) para
    que la abertura de puntas de ala sea :func:`pair_wing_spread_m`.
    """
    lrw = rig.towing.net_length_working_m
    rigging_m = rig.crowfoot.length_m + rig.crowfoot.extension_m + case.sweeps_m
    rigging_m += rig.bridles.upper_m
    return pair_wing_spread_m(case) * (lrw + rigging_m) / lrw


def fridman_door_spread_m(
    case: DesignCase, drag: DragStage, rig: RiggingGeometry, polar: DoorPolar
) -> float:
    """Separación de portones de la DPA de Fridman con el portón del caso [m].

    La DPA de Fridman (Mec!P164, :func:`~trawlkit.rigging.fridman_spread`) sale de la
    sustentación y la resistencia del portón frente a la de la red; se promedia en el rango de
    velocidades de la superficie requerida (2–4 kn) y se lleva a los portones con la regla de
    triángulos semejantes de Mec!L225 (Ds = DPA·(LRw + aparejo)/LRw).
    """
    door = case.door
    assert door.area_m2 is not None
    fr = rigging.fridman_spread(
        door.area_m2,
        polar.cd,
        polar.cl,
        case.speeds_ms,
        drag.rn.std,
        drag.rn.mod,
        rig.towing.warp_horizontal_shallow_m,
        rig.towing.net_length_working_m,
        rig.towing.bridle_m,
        compat=case.compat,
    )
    lo, hi = case.required_area_speed_range_kn
    v = np.asarray(case.speeds)
    dpa = float(np.mean(_arr(fr.dpa_std_m)[(v >= lo) & (v <= hi)]))
    lrw = rig.towing.net_length_working_m
    rigging_m = rig.crowfoot.length_m + rig.crowfoot.extension_m + case.sweeps_m
    rigging_m += rig.bridles.upper_m
    return dpa * (lrw + rigging_m) / lrw


def _stage_doors(
    case: DesignCase, power: PowerStage, drag: DragStage, rig: RiggingGeometry
) -> DoorStage:
    """'Portones y aparejamiento': separación, polar, ROB, fuerzas, superficie, Pφ y momentos."""
    door = case.door
    assert door.area_m2 is not None and door.length_m is not None
    polar = rigging.door_polar(
        door, case.door_attack_angle_deg, interpolate=case.compat is Compat.CORRECTED
    )  # Port!C134:F134
    warp_m = rig.towing.warp_m  # Port!D9 = Mec!E177
    if case.is_pair:
        spread = pair_towing_spread_m(case, rig)
    elif case.is_beam:
        spread = case.beam_length  # la vara fija la separación de las puntas de ala
    elif case.door_spread_rule == "fridman":
        spread = fridman_door_spread_m(case, drag, rig, polar)
    else:
        spread = rigging.door_spread_m(case.gallows_spacing_m, case.spread_per_m, warp_m)  # E13
    tijera: TijeraBalance | None = None
    book_spread: float | None = None
    if case.uses_shrimp_opening and case.rig_kind == "outrigger":
        # Fase 19.7b: con tijera la separación no depende del cable filado (Roth 2016).
        tijera = tijera_spread(case, drag, rig, polar)
        if tijera.converged:
            book_spread, spread = spread, tijera.spread_m
    half_div = rigging.warp_divergence_deg(spread, case.gallows_spacing_m, warp_m)  # D21
    corrected = rigging.door_spread_corrected_m(
        warp_m, half_div, case.spread_correction_factor
    )  # F30
    shares = {
        f"{int(round(s * 100))}pct": _arr(rigging.door_drag_share_kgf(power.ft_kgf, s))
        for s in rigging.ROB_SHARES
    }  # E146:H146 (150 HP) / E160:H160 (180 HP)
    rob_share = _arr(rigging.door_drag_share_kgf(power.ft_kgf, case.rob_share))  # D210 = F146
    v_ms = case.speeds_ms
    forces = rigging.door_forces_kgf(door.area_m2, polar.cd, polar.cl, v_ms)  # D190:E198
    lo, hi = case.required_area_speed_range_kn

    def required(ft: FloatArray) -> tuple[FloatArray, RequiredArea]:
        rob = _arr(rigging.door_drag_share_kgf(ft, case.rob_share))
        areas = _arr(rigging.required_area_m2(rob, polar.cd, v_ms))  # E210:E218
        return areas, rigging.required_area_summary(areas, case.speeds, lo, hi)  # F212, F215

    areas, req = required(power.ft_kgf)
    req_class = {
        vid: required(_ft_of(s, case.ft_propeller))[1] for vid, s in power.class_fridman.items()
    }
    per_door_class = float(np.mean([r.per_door_m2 for r in req_class.values()]))  # F220
    force = _arr(
        rigging.door_force_kgf(
            polar.cd, door.area_m2, case.door_attack_angle_deg, v_ms, compat=case.compat
        )
    )  # D252:D260
    cop = rigging.centre_of_pressure_m(door.length_m, case.door_attack_angle_deg)  # C266:C270
    moments = rigging.moment_balance(force, drag.rn.std, cop.d_m, case.sweep_lever_m)  # G281:H289
    if case.is_pair or case.is_beam:
        # Pareja o vara: no hay portones; sus fuerzas, su arrastre y su superficie requerida son
        # nulos.
        zero = 0.0 * v_ms
        forces = rigging.door_forces_kgf(door.area_m2, 0.0, 0.0, v_ms)
        areas, force = zero, zero
        req = rigging.required_area_summary(zero, case.speeds, lo, hi)
        req_class = {vid: req for vid in req_class}
        per_door_class = 0.0
        moments = rigging.moment_balance(zero, drag.rn.std, cop.d_m, case.sweep_lever_m)
    return DoorStage(
        door=door,
        polar=polar,
        spread_m=spread,
        half_divergence_deg=half_div,
        spread_corrected_m=corrected,
        rob_share=case.rob_share,
        rob_share_kgf=rob_share,
        rob_shares_kgf=shares,
        forces=forces,
        rig_drag_kgf=DOORS_PER_RIG * _arr(forces.drag_kgf),
        required_area_m2=areas,
        required_area=req,
        required_area_class=req_class,
        required_area_per_door_class_m2=per_door_class,
        force_kgf=force,
        centre_of_pressure=cop,
        moments=moments,
        tijera=tijera,
        book_spread_m=book_spread,
    )


def tijera_spread(
    case: DesignCase, drag: DragStage, rig: RiggingGeometry, polar: DoorPolar
) -> TijeraBalance:
    """Equilibrio portón–tijera–red a la velocidad de diseño (Fase 19.7b).

    :func:`~trawlkit.rigging.shrimp.tijera_balance` con la sustentación y la resistencia de un
    portón del caso (polar al ángulo de ataque), la RN de diseño de la red (Aberdeen), la rama de
    la tijera ``outrigger_bridle_m`` (70 m, ITO 043/2022) y L_R = cañas + pie de gallo + 0,90 ×
    largo estirado sin bolsa (punta de ala → copo). La velocidad es la de diseño del cable
    (``warp_design_speed_kn``, 3,5 nudos como las simulaciones DynamiT del INIDEP).
    """
    door = case.door
    assert door.area_m2 is not None
    i = case.speed_index(case.warp_design_speed_kn)
    forces = rigging.door_forces_kgf(door.area_m2, polar.cd, polar.cl, case.speeds_ms)
    leg = case.outrigger_bridle_m or multirig.OUTRIGGER_BRIDLE_M
    net_leg = shrimp.net_leg_m(
        case.shrimp_bridle,
        rig.crowfoot.length_m + rig.crowfoot.extension_m,
        rig.towing.net_length_m,
    )
    return shrimp.tijera_balance(
        float(_arr(forces.lift_kgf)[i]),
        float(_arr(forces.drag_kgf)[i]),
        float(drag.rn.std[i]),
        float(leg),
        net_leg,
    )


def _rope(case: DesignCase, which: str) -> RopeSpec:
    """Cabo de la lima o del burlón: campo del caso, ``construction`` de la spec o el del libro.

    Con filtros de componentes (:func:`component_filters`) y sin cabo elegido en el caso, el de
    la spec o el del libro es sólo la referencia: se elige del catálogo de componentes filtrado
    (:func:`trawlkit.rigging.select_rope_component`, Fase 19.2), como los cables y las boyas.
    """
    chosen = case.headrope_rope if which == "headrope" else case.footrope_rope
    explicit = chosen is not None
    if chosen is None:
        spec_rope = case.net.headrope if which == "headrope" else case.net.footrope
        extra = (spec_rope.model_extra or {}) if spec_rope is not None else {}
        chosen = extra.get("construction")
    if chosen is None:
        chosen = DEFAULT_HEADROPE_ROPE if which == "headrope" else DEFAULT_FOOTROPE_ROPE
    ref = rigging.select_rope(str(chosen))
    flt = component_filters(case)
    if explicit or flt is None:
        return ref
    from trawlkit.components import RopeItem, get_component, load_components

    try:
        ref_item = get_component("rope", ref.id)
    except KeyError:
        return ref
    assert isinstance(ref_item, RopeItem)
    items = [r.model_dump() for r in load_components("rope", **flt)]
    return rigging.select_rope_component(items, ref, ref_item.material)


def component_filters(case: DesignCase) -> dict[str, Any] | None:
    """Filtros de la selección automática de componentes, o ``None`` si se usan los del libro."""
    if case.component_brands is None and case.component_region is None and not case.generic_only:
        return None
    return {
        "brands": case.component_brands,
        "region": case.component_region,
        "generic_only": case.generic_only,
    }


def _case_floats(case: DesignCase) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Boyas para elegir: la del caso, las del catálogo de componentes filtrado o las del libro."""
    from trawlkit.components import FloatItem, get_component, load_components

    if case.float_id is not None:
        item = get_component("float", case.float_id)
        assert isinstance(item, FloatItem)
        return (item.diameter_mm,), (item.buoyancy_kgf,)
    flt = component_filters(case)
    if flt is not None:
        items = [f for f in load_components("float", **flt) if isinstance(f, FloatItem)]
        if items:
            return (
                tuple(f.diameter_mm for f in items),
                tuple(f.buoyancy_kgf for f in items),
            )
    return _float_catalogue()


def _case_warps(case: DesignCase) -> list[dict[str, Any]] | None:
    """Cables para elegir: el del caso o los del catálogo de componentes filtrado (None = libro)."""
    from trawlkit.components import get_component, load_components

    if case.warp_id is not None:
        return [get_component("wire", case.warp_id).model_dump()]
    flt = component_filters(case)
    if flt is None:
        return None
    return [w.model_dump() for w in load_components("wire", **flt)]


def _float_catalogue() -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Diámetros y flotaciones unitarias del catálogo de boyas (Flot!D72:E82)."""
    items = load_catalogue("floats").items
    return (
        tuple(float(it["diameter_mm"]) for it in items),
        tuple(float(it["buoyancy_kgf"]) for it in items),
    )


def _stage_floats(
    case: DesignCase,
    dimensions: Pair[NetDimensions],
    power: PowerStage,
    drag: DragStage,
    rig: RiggingGeometry,
    notes: list[str],
) -> FloatStage:
    """'Flotación y Lastre' E2:J146: Koyama, Prado, Fridman por buque de la clase, boyas y RB."""
    dims = dimensions.std
    v = case.vessel
    koyama = rigging.flotation_koyama_kgf(dims.headrope_m)  # F6
    rope = _rope(case, "headrope")  # Cab!D3
    rope_air = rigging.rope_weight_air_kg(dims.headrope_m, rope.weight_kg_per_m)  # F36
    rope_water = rigging.rope_weight_in_water_kg(rope_air)  # F37
    beta = rigging.beta_deg(rig.vertical_opening_m, dims.body_length_m)  # F23
    first_block = case.vessel_class[0]
    # Flot!M43:M50 (modificada, primer bloque de la hoja) sin ROUNDDOWN; L42:L50, M42 y el bloque
    # de 180 HP sí (errata flotation_rounding_inconsistent). En modo corregido todo se redondea.
    mod_mask: FloatArray = np.ones(len(case.speeds_kn), dtype=bool)
    if case.compat is Compat.EXCEL:
        mod_mask = np.array([True] + [False] * (len(case.speeds_kn) - 1))

    def fridman_for(cv: Vessel) -> Pair[FridmanFlotation]:
        ft = _ft_of(power.class_fridman[cv.id], case.ft_propeller)  # E42 = PotOK!L11
        rounddown_mod: bool | FloatArray = (
            mod_mask if (case.compat is Compat.EXCEL and cv.id == first_block.id) else True
        )
        return Pair(
            rigging.flotation_fridman(
                ft, drag.rn.std, case.bridle_angle_deg, beta, rope_water, rounddown=True
            ),
            rigging.flotation_fridman(
                ft, drag.rn.mod, case.bridle_angle_deg, beta, rope_water, rounddown=rounddown_mod
            ),
        )

    class_fridman = {cv.id: fridman_for(cv) for cv in case.vessel_class}
    class_avg = {
        vid: rigging.flotation_fridman_average_kgf(
            _arr(p.std.total_kgf), _arr(p.mod.total_kgf), case.speeds, case.flotation_max_speed_kn
        )
        for vid, p in class_fridman.items()
    }  # N43 / N55
    class_prado = {
        cv.id: rigging.flotation_prado_kgf(cv.bhp, case.prado_flotation_k)
        for cv in case.vessel_class
    }  # F17 / G17
    ffz = rigging.fridman_flotation_total_kgf(*class_avg.values(), *class_prado.values())  # O261
    if case.compat is Compat.EXCEL and first_block.id != v.id:
        notes.append(
            t(
                "flotation_rounding_inconsistent: la máscara de Flot!M43:M50 se aplica al primer "
                "bloque de la hoja ({first}), no al buque de diseño ({vessel})",
                first=first_block.id,
                vessel=v.id,
            )
        )

    design = class_avg[v.id]  # F70 = N43
    diameters, buoyancies = _case_floats(case)
    counts = _arr(rigging.float_count(design, _arr(buoyancies)))  # F72:F82
    count = case.float_count
    if count is None and case.float_id is not None:
        count = int(counts[0])
        notes.append(
            t(
                "float_count = {count} boyas {id} (catálogo de componentes)",
                count=count,
                id=case.float_id,
            )
        )
    if count is None and case.net.floats is not None:
        count = int(case.net.floats.count)
        notes.append(t("float_count tomado de la spec ({count} boyas)", count=count))
    if count is None:
        target = (
            DEFAULT_FLOAT_DIAMETER_MM if case.float_diameter_mm is None else case.float_diameter_mm
        )
        idx = [i for i, d in enumerate(diameters) if d == target]
        if not idx:
            raise ValueError(
                t("no hay boyas de {target} mm en el catálogo; fije float_count", target=target)
            )
        count = int(counts[idx[-1]])
        notes.append(
            t(
                "float_count = {count} boyas de {target:g} mm del catálogo (Flot!F72:F82)",
                count=count,
                target=target,
            )
        )
    spec_floats = case.net.floats
    if case.float_diameter_mm is not None:
        diameter = float(case.float_diameter_mm)
    elif case.float_id is not None:
        diameter = float(diameters[0])
    elif (
        case.float_count is None
        and spec_floats is not None
        and spec_floats.diameter_mm is not None
        and case.compat is not Compat.EXCEL
    ):
        # La spec trae el diámetro de sus boyas: se usa ése, no el del catálogo (Fase 19.8).
        diameter = float(spec_floats.diameter_mm)
        notes.append(t("float_diameter_mm tomado de la spec ({d:g} mm)", d=diameter))
    elif case.compat is Compat.EXCEL:
        diameter = rigging.float_diameter_for_count_mm(count, counts, _arr(diameters))  # F92
    else:
        # float_lookup_unsorted: en vez del LOOKUP sobre un vector desordenado se toma la boya
        # del catálogo cuyo número requerido es el más cercano al elegido.
        diameter = float(diameters[int(np.argmin(np.abs(counts - count)))])
    distribution = rigging.distribute_floats(
        count,
        diameter,
        dims.headrope_m,
        dims.headrope.wing_corrected_m,
        dims.headrope.bosom_corrected_m,
        case.float_wing_share,
        case.float_front_fifth_share,
    )
    cd = _arr(rigging.float_cd(case.speeds))  # I138:I146
    d_m = diameter / 1000.0  # H128
    reynolds = _arr(rigging.float_reynolds(d_m, case.speeds_ms, compat=case.compat))  # H138
    rb = _arr(rigging.float_drag_kgf(count, d_m, cd, case.speeds_ms))  # J138:J146
    return FloatStage(
        koyama_kgf=koyama,
        prado_kgf=class_prado[v.id],
        headrope_rope=rope,
        headrope_weight_air_kg=rope_air,
        headrope_weight_water_kgf=rope_water,
        beta_deg=beta,
        fridman=class_fridman[v.id],
        fridman_average_kgf=design,
        class_fridman_average_kgf=class_avg,
        class_prado_kgf=class_prado,
        flotation_total_kgf=ffz,
        flotation_rounded_kgf=float(excel_round(design)),  # F90 = ROUND(F70, 0)
        catalogue_diameters_mm=diameters,
        catalogue_buoyancy_kgf=buoyancies,
        catalogue_counts=counts,
        count=count,
        diameter_mm=diameter,
        distribution=distribution,
        cd=cd,
        reynolds=reynolds,
        drag_kgf=rb,
    )


def _stage_spread(
    case: DesignCase,
    dimensions: Pair[NetDimensions],
    drag: DragStage,
    rig: RiggingGeometry,
    doors: DoorStage,
    floats: FloatStage,
    notes: list[str],
) -> SpreadStage:
    """Mec!B162:P282 y Dim!F61: DPA de Fridman, geométrica y por corte, AH y AV."""
    d_std, d_mod = dimensions.std, dimensions.mod
    assert case.door.area_m2 is not None
    fridman = rigging.fridman_spread(
        case.door.area_m2,
        doors.polar.cd,
        doors.polar.cl,
        case.speeds_ms,
        drag.rn.std,
        drag.rn.mod,
        rig.towing.warp_horizontal_shallow_m,  # F179
        rig.towing.net_length_working_m,  # E185
        rig.towing.bridle_m,  # E186
        compat=case.compat,
    )
    parts = {
        "crowfoot_m": rig.crowfoot.length_m,  # E211
        "crowfoot_extension_m": rig.crowfoot.extension_m,  # E212
        "sweeps_m": case.sweeps_m,  # E213
        "bridle_m": rig.bridles.upper_m,  # E214
    }
    table = rigging.dpa_fridman_table(
        fridman.dpa_std_m, fridman.dpa_mod_m, d_std.footrope_m, **parts
    )
    geometric = rigging.dpa_geometric_m(d_std.footrope_m, doors.spread_m, **parts)  # L211
    working = rigging.dpa_geometric_working_m(
        doors.spread_m, rig.towing.net_length_working_m, **parts
    )  # L225
    cut = rigging.dpa_from_cut_angle_m(
        d_std.total_length_m, case.working_u2, d_std.cut_angle_deg
    )  # L233
    ah = rigging.horizontal_opening_m(cut, working, geometric, _arr(table.dpa_std_m))  # Dim!F61
    if case.is_pair or case.is_beam:
        # Sin portones no hay DPA de Fridman: la abertura la fija la separación de la pareja o el
        # largo de la vara.
        ah = pair_wing_spread_m(case) if case.is_pair else case.beam_length
        const = ah + 0.0 * case.speeds_ms
        fridman = replace(fridman, dpa_std_m=const, dpa_mod_m=const)
    shrimp_opening: ShrimpOpening | None = None
    if case.uses_shrimp_opening:
        book_ah = ah
        if doors.book_spread_m is not None:
            # AH del promedio del libro con la separación que daba su regla (para comparar).
            book_ah = rigging.horizontal_opening_m(
                cut,
                rigging.dpa_geometric_working_m(
                    doors.book_spread_m, rig.towing.net_length_working_m, **parts
                ),
                rigging.dpa_geometric_m(d_std.footrope_m, doors.book_spread_m, **parts),
                _arr(table.dpa_std_m),
            )
        shrimp_opening = shrimp_opening_of(case, d_std, rig, doors, book_ah)
        ah = shrimp_opening.horizontal_opening_m
    dpa_over_l = working / d_std.headrope_m  # O265 = O264/O260, O264 = L225
    ratio_table = rigging.catenary_ratio(dpa_over_l)
    if ratio_table != case.catenary_ratio:
        notes.append(
            t(
                "catenary_ratio_hardcoded: fL/L = {fixed} (Mec!O266) frente a "
                "{table} de la tabla para DPA/L = {ratio:.2f}; se conserva el valor fijo",
                fixed=case.catenary_ratio,
                table=ratio_table,
                ratio=dpa_over_l,
            )
        )
    circ = d_std.max_circumference_m  # F243
    body = next(
        p
        for p in (case.net_modified or case.net).panels
        if p.section.value == "body" and p.plane.value == "upper"
    )
    mesh = float(case.martini_mesh_mm if case.martini_mesh_mm is not None else body.mesh_mm)
    dv = rigging.stretched_circumference_m(2 * body.meshes_top, mesh)  # E269
    av_fridman = Pair(
        rigging.vertical_opening_fridman(
            drag.rn.std,
            floats.flotation_total_kgf,
            rig.headrope_sag_m,
            rig.bridles.upper_m,
            case.dan_leno_m,
        ),
        rigging.vertical_opening_fridman(
            drag.rn.mod,
            floats.flotation_total_kgf,
            rig.headrope_sag_m,
            rig.bridles.upper_m,
            case.dan_leno_m,
        ),
    )  # M272:P282
    vertical = VerticalOpening(
        suzuki_m=rig.vertical_opening_m,  # D255
        prado_m={
            k: rigging.vertical_opening_pct_m(circ, s) for k, s in rigging.AV_PRADO_SHARES.items()
        },
        izzo_m=tuple(rigging.vertical_opening_pct_m(circ, s) for s in rigging.AV_IZZO_SHARES),
        martini_dv_m=dv,
        martini_m=rigging.vertical_opening_martini_m(
            dv, case.martini_mr_meshes, mesh, case.martini_factor
        ),
        flotation_total_kgf=floats.flotation_total_kgf,
        fridman=av_fridman,
    )
    del d_mod
    return SpreadStage(
        fridman=fridman,
        table=table,
        dpa_geometric_m=geometric,
        dpa_working_m=working,
        dpa_cut_angle_m=cut,
        horizontal_opening_m=ah,
        dpa_over_headrope=dpa_over_l,
        catenary_ratio_table=ratio_table,
        vertical=vertical,
        shrimp=shrimp_opening,
    )


def shrimp_opening_of(
    case: DesignCase,
    dims: NetDimensions,
    rig: RiggingGeometry,
    doors: DoorStage,
    book_ah_m: float,
) -> ShrimpOpening:
    """Aberturas por el método camaronero (Fase 19.7b, :mod:`trawlkit.rigging.shrimp`).

    Con tijera (tangones) y el equilibrio resuelto: AH = DP·LRw/(LRw + pie de gallo + cañas);
    si no (gemelo, portones, o sin solución del equilibrio): AH = k·lima con k por familia y la
    DP del libro. AV = 0,04·lima en los dos casos.
    """
    head = float(dims.headrope_m)
    k = shrimp.headrope_k(*case.species_texts, case.net.name)
    dp = float(doors.spread_m)
    tij = doors.tijera
    lrw = float(rig.towing.net_length_working_m)
    crowfoot = rig.crowfoot.length_m + rig.crowfoot.extension_m
    if tij is not None and tij.converged:
        method = "tijera"
        ah = shrimp.wing_spread_m(dp, lrw, crowfoot + case.shrimp_bridle)
    else:
        method = "headrope_k"
        ah = k.k * head
    leg = case.outrigger_bridle_m or multirig.OUTRIGGER_BRIDLE_M
    return ShrimpOpening(
        method=method,
        door_spread_m=dp,
        horizontal_opening_m=float(ah),
        vertical_opening_m=shrimp.vertical_opening_m(head),
        headrope_m=head,
        ah_over_dp=float(ah / dp) if dp > 0 else float("nan"),
        ah_over_headrope=float(ah / head),
        k=k,
        book_door_spread_m=float(doors.book_spread_m if doors.book_spread_m is not None else dp),
        book_horizontal_opening_m=float(book_ah_m),
        bridle_m=case.shrimp_bridle if tij is not None else None,
        leg_m=float(leg) if tij is not None else None,
        net_leg_m=(
            shrimp.net_leg_m(case.shrimp_bridle, crowfoot, rig.towing.net_length_m)
            if tij is not None
            else None
        ),
        body_stretched_m=float(rig.towing.net_length_m),
        speed_kn=case.warp_design_speed_kn if tij is not None else None,
        balance=tij,
    )


def _stage_bridles(
    case: DesignCase,
    dimensions: Pair[NetDimensions],
    rig: RiggingGeometry,
    doors: DoorStage,
    spread: SpreadStage,
) -> BridleStage:
    """Port!A63:E110: patentes de Dremiere y Martini y ángulo de ataque de bridas y patentes."""
    dims = dimensions.std
    dpa = spread.dpa_geometric_m  # Port!E78 = E104 = Mec!L211
    no_triangle = rigging.sweeps_length_m(
        doors.spread_m,
        dims.body_length_no_bag_m,
        dpa,
        rig.bridles.no_triangle_m,
        case.sweeps_factor,
    )  # C83
    triangle = rigging.sweeps_length_m(
        doors.spread_m, dims.body_length_no_bag_m, dpa, rig.bridles.triangle_m, case.sweeps_factor
    )  # C87
    return BridleStage(
        lengths=rig.bridles,
        crowfoot=rig.crowfoot,
        sweeps_m=case.sweeps_m,
        sweeps_plus_bridle_m=case.sweeps_m + rig.bridles.upper_m,  # Rem!F8
        sweeps_dremiere_m=rigging.sweeps_dremiere_m(rig.towing.warp_m, case.dremiere_ratio),  # C71
        sweeps_martini_m=rigging.sweeps_martini_m(
            doors.spread_m, dpa, case.sweeps_martini_delta_deg, compat=case.compat
        ),  # G71
        sweeps_no_triangle_m=no_triangle,
        sweeps_triangle_m=triangle,
        attack_angle_deg=rigging.attack_angle_deg(
            doors.spread_m, dpa, rig.crowfoot.length_m, no_triangle, rig.bridles.no_triangle_m
        ),  # D110
    )


def _stage_ballast(
    case: DesignCase, dimensions: Pair[NetDimensions], floats: FloatStage
) -> BallastStage:
    """Flot!D153:I245: Koyama, Prado, Fridman, límites y distribución del lastre."""
    dims = dimensions.std
    rope = _rope(case, "footrope")  # Cab!D4
    rope_air = rigging.rope_weight_air_kg(dims.footrope_m, rope.weight_kg_per_m)  # G188
    rope_water = rigging.rope_weight_in_water_kg(rope_air)  # G191
    f = floats.fridman
    fridman = Pair(
        _arr(
            rigging.ballast_fridman_kg(
                _arr(f.std.f1_vertical_kgf), _arr(f.std.f2_vertical_kgf), rope_water
            )
        ),
        _arr(
            rigging.ballast_fridman_kg(
                _arr(f.mod.f1_vertical_kgf), _arr(f.mod.f2_vertical_kgf), rope_water
            )
        ),
    )  # L197:M205
    limits = rigging.ballast_limits(
        float(fridman.mod[case.speed_index(case.ballast_min_speed_kn)]),
        float(fridman.std[case.speed_index(case.ballast_max_speed_kn)]),
    )  # F225:F226
    chain = rigging.adjust_chain_weight_kg(limits.min_kg, chain_m=case.adjust_chain_m)  # H224
    return BallastStage(
        koyama_kg=rigging.ballast_koyama_kg(dims.headrope_m),  # G159
        prado_kg=rigging.ballast_prado_kg(case.vessel.bhp, case.prado_ballast_k),  # I173
        footrope_rope=rope,
        footrope_weight_air_kg=rope_air,
        footrope_weight_water_kgf=rope_water,
        fridman=fridman,
        limits=limits,
        adjust_chain_weight_kg=chain,
        even_kg_m=rigging.ballast_even_kg_m(limits.min_kg, chain, dims.footrope_m),  # E233
        distribution_min=rigging.distribute_ballast_min(limits.min_kg, dims.footrope_m),
        distribution_max=rigging.distribute_ballast_max(
            limits.max_kg, dims.footrope_m, chain_m=case.adjust_chain_m
        ),
        chain=_ballast_chain(case, limits, chain),
    )


def _ballast_chain(
    case: DesignCase, limits: BallastLimits, adjust_kg: float
) -> BallastChain | None:
    """Lastre en metros de la cadena ``chain_id`` del catálogo de componentes (Fase 19.2)."""
    if case.chain_id is None:
        return None
    from trawlkit.components import DENSITY_KG_M3, ChainItem, get_component
    from trawlkit.materials import weight_in_water_coefficient

    item = get_component("chain", case.chain_id)
    assert isinstance(item, ChainItem)
    return rigging.ballast_chain(
        item.id,
        item.name,
        item.weight_kg_per_m,
        limits.min_kg,
        limits.max_kg,
        adjust_kg,
        float(weight_in_water_coefficient(DENSITY_KG_M3["steel"])),
        item.breaking_load_t,
    )


def _stage_warps(
    case: DesignCase,
    dimensions: Pair[NetDimensions],
    power: PowerStage,
    drag: DragStage,
    rig: RiggingGeometry,
    doors: DoorStage,
    bridles: BridleStage,
    floats: FloatStage,
) -> WarpStage:
    """'Cables de Remolque' y Cab!D11:D12.

    CD del cable (Rem!E103:E106), errata ``warp_cd_horizontal_angle``: en :attr:`Compat.EXCEL` el
    ángulo de ataque es la divergencia en planta δ2 (E103 = E25) y el CD la fila más cercana de la
    tabla Nomura–Yamazaki (4.3° → 0.02). En :attr:`Compat.CORRECTED` el ángulo es el del cable con
    el flujo, acos(cos δ1 · cos δ2), y el CD se interpola linealmente en la tabla.
    """
    dims = dimensions.std
    warp_m = rig.towing.warp_m  # F9 = Port!D9
    rigging_m = bridles.sweeps_plus_bridle_m  # F8 = Dim!F65 + Dim!F68
    dpa_a = rigging.dpa_similar_triangles_m(doors.spread_m, dims.footrope_m, rigging_m)  # F17
    dpa_b = rigging.dpa_similar_triangles_m(
        doors.spread_m, dims.body_length_no_bag_m, rigging_m
    )  # F19
    angles = rigging.warp_angles_deg(
        doors.spread_m,
        case.gallows_spacing_m,
        warp_m,
        dpa_a,
        rigging_m,
        case.working_depth_m,  # E105 = Especie!E5
        case.hull_depth_m,  # Buques!B6
    )
    d_ehp = rigging.warp_diameter_ehp_mm(power.koyama_ehp_hp)  # F73 (E70 = PotOK!C171)
    d_aguila = rigging.warp_diameter_aguila_mm(case.vessel.bhp)  # E80
    sizing = case.warp_sizing_nhp_hp
    diameter = rigging.warp_diameter_aguila_mm(sizing)  # E110 = E81 (180 HP)
    d_m = diameter / 1000.0  # E111
    if case.compat is Compat.EXCEL:
        # Errata warp_cd_horizontal_angle: α = E103 = E25 (δ2) y fila más cercana (E106).
        cd_angle = angles.divergence_deg
        cd = rigging.warp_cd(cd_angle)
    else:
        cd_angle = rigging.warp_attack_angle_deg(angles.declination_deg, angles.divergence_deg)
        cd = rigging.warp_cd(cd_angle, interpolate=True)
    v_ms = case.speeds_ms
    rw = _arr(rigging.warp_drag_kgf(cd, d_m, warp_m, v_ms))  # G118:G126
    rob = doors.rig_drag_kgf  # par de portones (Port!D190 es por portón)
    total = Pair(
        _arr(rigging.total_drag_kgf(drag.rn.std, floats.drag_kgf, rw, rob, case.compat)),  # H118
        _arr(rigging.total_drag_kgf(drag.rn.mod, floats.drag_kgf, rw, rob, case.compat)),  # I118
    )
    cylinder = rigging.warp_drag_cylinder(d_m, warp_m, v_ms, case.speeds)  # D167:G175
    shares: dict[str, FloatArray] = {}
    for prop in (PropellerType.FIXED_PITCH, PropellerType.VARIABLE_PITCH_NOZZLE):
        ft = _ft_of(power.fridman, prop)
        for s in case.warp_drag_shares:
            shares[f"{prop.value}_{int(round(s * 100))}pct"] = _arr(
                rigging.warp_drag_share_kgf(ft, s)
            )
    weight = rigging.warp_weight(diameter, warp_m)  # B241:F257 (F246 = E110, F255 = Ls)
    loads = rigging.working_load_and_breaking_load(
        total.std, case.speeds, case.warp_design_speed_kn, case.warp_safety_factor
    )  # E267, E272
    selection = rigging.select_warp(
        diameter, loads.min_breaking_load_kgf, case.compat, items=_case_warps(case)
    )  # Cab!D11
    return WarpStage(
        warp_m=warp_m,
        sweeps_plus_bridle_m=rigging_m,
        dpa_a_m=dpa_a,
        dpa_b_m=dpa_b,
        angles=angles,
        diameter_ehp_mm=d_ehp,
        diameter_aguila_mm=d_aguila,
        sizing_nhp_hp=sizing,
        diameter_mm=diameter,
        cd_angle_deg=cd_angle,
        cd=cd,
        drag_kgf=rw,
        total=total,
        cylinder=cylinder,
        shares_kgf=shares,
        cd_maclennan=_arr(rigging.warp_cd_maclennan(v_ms, d_m)),  # D227:D235
        weight=weight,
        loads=loads,
        selection=selection,
        quantity_m=rigging.warp_quantity_m(warp_m, case.warp_spare_fraction),  # Cab!D12
        stretch=_warp_stretch(angles, loads, selection, warp_m),
    )


def _warp_stretch(
    angles: WarpAngles,
    loads: WarpLoads,
    selection: WarpSelection,
    warp_m: float,
    n_warps: int = 2,
) -> WarpStretch:
    """Estiramiento elástico del cable elegido (Fase 19.1): ΔL = T·L/EA a la velocidad de diseño.

    EA del componente del catálogo si el cable está en él (:func:`trawlkit.components.
    axial_stiffness`: ``ea_kn`` de la ficha o el módulo efectivo según el alma); si no, el del
    6x19 con alma de fibra sobre el área nominal (:func:`trawlkit.materials.wire_rope_ea_n`).
    El ángulo del cable es siempre acos(cos δ1 · cos δ2), también en modo EXCEL (no es una celda
    del libro).
    """
    from trawlkit.components import WireItem, axial_stiffness, get_component
    from trawlkit.materials import wire_core, wire_rope_ea_n

    try:
        comp = get_component("wire", selection.id)
    except KeyError:
        comp = None
    got = axial_stiffness(comp) if isinstance(comp, WireItem) else None
    if isinstance(comp, WireItem) and got is not None:
        core = wire_core(comp.core, comp.construction)
        ea_n, kind = got[0] * 1000.0, got[1].kind.value
    else:
        core = wire_core(None, selection.construction)
        ea_n, kind = wire_rope_ea_n(selection.diameter_mm, core), "derived"
    alpha = rigging.warp_attack_angle_deg(angles.declination_deg, angles.divergence_deg)
    return rigging.warp_stretch(loads, selection, warp_m, alpha, ea_n, kind, core, n_warps)


def _friction_parts(case: DesignCase, ballast: BallastStage) -> tuple[float, float, float]:
    """(tren de una red, un portón, μ de las zapatas) del rozamiento con el fondo [kgf].

    Tren: μ del tren por el peso en el agua de burlón y lastre (máximo, acero); portón: μ de las
    zapatas por su peso en el agua. Ceros si el caso no indica ``seabed`` o la red es pelágica.
    """
    if case.seabed is None or case.net.family == "pelagic":
        return 0.0, 0.0, 0.0
    sb = rigging.seabed(case.seabed)
    dist = ballast.distribution_max
    steel = 1.0 - 1024.0 / 7850.0
    ballast_water = (dist.wings_kg + dist.bosom_kg + dist.adjust_kg) * steel
    gear = sb.mu_gear.nominal * (ballast.footrope_weight_water_kgf + ballast_water)
    door = case.door
    door_water = door.weight_water_kg or (door.weight_air_kg or 0.0) * 0.6
    return float(gear), float(sb.mu_door.nominal * door_water), float(sb.mu_door.nominal)


def seabed_friction_kgf(case: DesignCase, ballast: BallastStage) -> float:
    """Rozamiento con el fondo [kgf] del tren de fondo y de los dos portones.

    Es μ del tren por el peso en el agua de burlón y lastre (máximo, acero) más μ de las zapatas
    por el peso en el agua de los dos portones; 0 si el caso no indica ``seabed``. Es una cota
    simple (todo el peso apoyado): el simulador con portones acoplados reparte la reacción con la
    sustentación de las boyas y los cables. Con tangones, gemelo o vara el rozamiento de todo el
    arte está en :class:`RigStage` (``friction_kgf``).
    """
    gear, door_one, _ = _friction_parts(case, ballast)
    doors = 0 if case.is_pair else DOORS_PER_RIG
    return float(gear + doors * door_one)


def _stage_rig(
    case: DesignCase,
    dimensions: Pair[NetDimensions],
    geometry: Pair[NetGeometry],
    drag: DragStage,
    doors: DoorStage,
    spread: SpreadStage,
    floats: FloatStage,
    ballast: BallastStage,
    warps: WarpStage,
) -> RigStage:
    """Tangones, gemelo o vara (Fase 19.5): ver :class:`RigStage`.

    Las etapas del libro dan una red con su par de portones y dos cables; acá se cuentan las
    piezas que tiene de verdad cada aparejo:

    * **tangones**: dos portones y un cable por red, más la tijera (dos ramas por red);
    * **gemelo**: un portón por red, el muerto central (medio por red) y un cable por red;
    * **vara**: sin portones ni boyas (la lima va a la vara); vara, patines, tren y cadenas
      espantadoras por vara (C056/20) y un cable por vara.
    """
    kind = case.rig_kind
    n = case.n_nets
    v_ms = case.speeds_ms
    zero = 0.0 * v_ms
    rn = drag.rn
    rb = _arr(floats.drag_kgf)
    door_one = _arr(doors.forces.drag_kgf)
    rw_one = _arr(warps.drag_kgf) / 2.0  # la etapa del libro cuenta dos cables
    gear, door_friction, mu_door = _friction_parts(case, ballast)
    dims = dimensions.std
    sources: list[str] = []
    layout: multirig.OutriggerLayout | None = None
    bridle: tuple[float, float, FloatArray] | None = None
    clump_w: float | None = None
    clump_a: float | None = None
    clump_d: FloatArray | None = None
    beam_drag: multirig.BeamDrag | None = None
    watson_area: tuple[float, float] | None = None
    watson_spread: tuple[float, float] | None = None
    vertical = float(spread.vertical_opening_m)  # Suzuki o método camaronero (Fase 19.7b)
    boom_l = case.boom_length
    if kind in ("outrigger", "twin"):
        watson_area = multirig.watson_door_area_m2(dims.headrope_m)
        watson_spread = multirig.watson_spread_m(dims.headrope_m)
    if kind == "outrigger":
        n_doors, n_warps = 2 * n, n
        bridle_m = case.outrigger_bridle_m or multirig.OUTRIGGER_BRIDLE_M
        bridle_d = case.outrigger_bridle_diameter_mm or multirig.OUTRIGGER_BRIDLE_DIAMETER_MM
        if case.outrigger_bridle_m is None:
            sources.append(t("tijera de {m:g} m (INIDEP, Roth y Rubio 2022)", m=bridle_m))
        if case.outrigger_bridle_diameter_mm is None:
            sources.append(t("cable de la tijera de {d:g} mm (Roth y Rubio 2022)", d=bridle_d))
        # Dos ramas de tijera por red, con el CD del cable de remolque.
        bridle_kgf = _arr(rigging.warp_drag_kgf(warps.cd, bridle_d / 1000.0, bridle_m, v_ms, 2))
        bridle = (bridle_m, bridle_d, bridle_kgf)
        per_extra = 2.0 * door_one + rw_one + bridle_kgf
        assert boom_l is not None
        if case.boom_length_m is None:
            sources.append(t("tangón de 24 pies (7,32 m; Knake et al. 1958, FL 470)"))
        if case.boom_angle_deg is None:
            sources.append(t("tangón a 20° de la horizontal (FL 470)"))
        layout = multirig.outrigger_layout(
            doors.spread_m, boom_l, case.boom_angle, case.boom_heel_offset_m
        )
        net_spread = doors.spread_m
        door_total = layout.swept_width_m
        swept = layout.swept_width_m
        friction = n * gear + n_doors * door_friction
    elif kind == "twin":
        n_doors, n_warps = 2, 2
        clump_w = case.clump_weight_kg
        if clump_w is None and case.door.weight_air_kg:
            clump_w = multirig.clump_weight_kg(float(case.door.weight_air_kg))
            sources.append(
                t(
                    "muerto de {kg:.0f} kg = 1,5 × el portón (Seafish, regla práctica)",
                    kg=clump_w,
                )
            )
        clump_a = case.clump_frontal_area_m2 or multirig.SLED_FRONTAL_M2
        if case.clump_frontal_area_m2 is None:
            sources.append(
                t(
                    "área frontal del muerto {a:.3f} m² del trineo de Bullis y Floyd (1972): "
                    "32 × 8 pulgadas (supuesto)",
                    a=clump_a,
                )
            )
        clump_d = multirig.drag_kgf(multirig.CD_SLED, clump_a, v_ms)
        per_extra = door_one + rw_one + 0.5 * clump_d
        net_spread = doors.spread_m
        door_total = 2.0 * doors.spread_m
        swept = door_total
        clump_friction = 0.0 if clump_w is None else mu_door * multirig.steel_in_water(clump_w)
        friction = n * gear + n_doors * door_friction + clump_friction
    else:  # vara
        n_doors, n_warps = 0, n
        cls = case.beam_class
        data = multirig.BEAM_CLASSES[cls]
        metier = case.beam_metier
        ticklers = case.beam_ticklers if case.beam_ticklers is not None else metier == "DMF"
        if case.beam_length_m is None:
            sources.append(
                t(
                    "vara de {m:.2f} m: ancho total de Eigaard et al. (2016, TBB_{metier}) para "
                    "{kw:.0f} kW repartido en {n} varas",
                    m=case.beam_length,
                    metier=metier,
                    kw=case.power_kw,
                    n=n,
                )
            )
        if case.beam_count is None:
            sources.append(t("dos varas por buque (Eigaard et al. 2016)"))
        if case.beam_ticklers is None:
            sources.append(
                t("cadenas espantadoras: sí (peces)")
                if ticklers
                else t("cadenas espantadoras: no (crustáceos; Eigaard et al. 2016)")
            )
        if (
            case.beam_diameter_m is None
            or case.beam_shoe_area_m2 is None
            or case.beam_shoe_height_m is None
        ):
            sources.append(
                t(
                    "vara, patines y cadenas de buques {cls} de C056/20 (Rijnsdorp et al. 2020, "
                    "tablas 2, 8 y 9)",
                    cls=t("chicos (≤ 221 kW)") if cls == "small" else t("grandes (> 221 kW)"),
                )
            )
        beam = multirig.beam_drag(
            v_ms,
            length_m=case.beam_length,
            diameter_m=case.beam_diameter_m or data.beam_diameter_m,
            shoe_area_m2=case.beam_shoe_area_m2 or data.shoe_area_m2,
            shoe_height_m=case.beam_shoe_height_m or data.shoe_height_m,
            cls=cls,
            ticklers=ticklers,
            metier=metier,
            twine_area_m2=float(geometry.std.solid_surface_m2),
        )
        beam_drag = beam
        rb = zero  # la lima va a la vara: sin boyas
        per_extra = beam.total_kgf + rw_one
        net_spread = case.beam_length
        door_total = 0.0
        swept = n * case.beam_length
        vertical = beam.shoe_height_m
        if boom_l is not None and n == 2:
            layout = multirig.outrigger_layout(
                net_spread, boom_l, case.boom_angle, case.boom_heel_offset_m
            )
        foot_friction = gear
        if case.seabed is not None and case.net.family != "pelagic":
            sb = rigging.seabed(case.seabed)
            foot_friction = sb.mu_gear.nominal * ballast.footrope_weight_water_kgf
        beam_friction = (
            0.0
            if case.beam_weight_kg is None
            else mu_door * multirig.steel_in_water(case.beam_weight_kg)
        )
        friction = n * (foot_friction + beam_friction)
    per_net = Pair(rn.std + rb + per_extra, rn.mod + rb + per_extra)
    system = Pair(n * per_net.std, n * per_net.mod)
    demand = Pair(system.std + friction, system.mod + friction)
    warp_load = system if kind == "twin" else per_net
    return RigStage(
        kind=kind,
        n_nets=n,
        n_doors=n_doors,
        n_warps=n_warps,
        net_spread_m=float(net_spread),
        door_spread_total_m=float(door_total),
        swept_width_m=float(swept),
        vertical_opening_m=float(vertical),
        per_net=per_net,
        warp_load=warp_load,
        warp_drag_kgf=n_warps * rw_one,
        doors_drag_kgf=n_doors * door_one,
        friction_kgf=float(friction),
        demand=demand,
        layout=layout,
        boom_length_m=boom_l,
        boom_angle_deg=case.boom_angle if boom_l is not None else None,
        bridle_m=None if bridle is None else bridle[0],
        bridle_diameter_mm=None if bridle is None else bridle[1],
        bridle_drag_kgf=None if bridle is None else n * bridle[2],
        clump_weight_kg=clump_w,
        clump_frontal_area_m2=clump_a,
        clump_drag_kgf=clump_d,
        beam=beam_drag,
        watson_door_area_m2=watson_area,
        watson_spread_m=watson_spread,
        sources=tuple(sources),
    )


def _rig_warps(case: DesignCase, warps: WarpStage, mr: RigStage) -> WarpStage:
    """Cables de un aparejo de tangones, gemelo o vara (Fase 19.5).

    El libro dimensiona cada cable con la resistencia de todo lo que remolca el par de cables
    (Rem!E267). Con tangones o varas cada cable remolca una red; en el gemelo, los dos cables
    remolcan todo el arte. La cantidad a comprar es un largo filado por cable más la reserva.
    """
    loads = rigging.working_load_and_breaking_load(
        mr.warp_load.std, case.speeds, case.warp_design_speed_kn, case.warp_safety_factor
    )
    selection = rigging.select_warp(
        warps.diameter_mm, loads.min_breaking_load_kgf, case.compat, items=_case_warps(case)
    )
    per_group = 2 if mr.kind == "twin" else 1
    return replace(
        warps,
        loads=loads,
        selection=selection,
        quantity_m=mr.n_warps * warps.warp_m + case.warp_spare_fraction * warps.warp_m,
        stretch=_warp_stretch(warps.angles, loads, selection, warps.warp_m, per_group),
    )


def _rig_notes(case: DesignCase, result: RigStage, doors: DoorStage) -> list[str]:
    """Notas de la corrida con tangones, gemelo o vara (Fase 19.5)."""
    label = {
        "outrigger": t("tangones"),
        "twin": t("gemelo"),
        "beam": t("vara"),
    }[result.kind]
    out = [
        t(
            "multirig: aparejo de {label} con {n} redes; ancho barrido {swept:.1f} m; la "
            "resistencia total suma las redes, {doors} portones y {warps} cables",
            label=label,
            n=result.n_nets,
            swept=result.swept_width_m,
            doors=result.n_doors,
            warps=result.n_warps,
        )
    ]
    out.extend(f"multirig: {s}" for s in result.sources)
    lay = result.layout
    if lay is not None and lay.overlap:
        out.append(
            t(
                "multirig_overlap: con tangones de {length:.2f} m a {angle:g}° las redes de "
                "{spread:.1f} m de DP se superponen {gap:.1f} m; hace falta un tangón de al "
                "menos {need:.2f} m o redes desfasadas (FL 470: una red 25 brazas más a popa)",
                length=result.boom_length_m or 0.0,
                angle=result.boom_angle_deg or 0.0,
                spread=lay.net_spread_m,
                gap=-lay.gap_m,
                need=multirig.boom_length_without_overlap_m(
                    lay.net_spread_m, result.boom_angle_deg or 0.0, case.boom_heel_offset_m
                ),
            )
        )
    if result.watson_door_area_m2 is not None and case.door.area_m2 is not None:
        lo, hi = result.watson_door_area_m2
        if not lo <= case.door.area_m2 <= hi:
            out.append(
                t(
                    "watson_door_area: portón de {area:.2f} m² fuera del rango de Watson et al. "
                    "(1984) para esta relinga: {lo:.2f}–{hi:.2f} m² (70–80 pulg²/pie, abertura "
                    "70–75 % de la relinga)",
                    area=case.door.area_m2,
                    lo=lo,
                    hi=hi,
                )
            )
    if result.kind == "twin":
        out.append(
            t(
                "twin_clump: cada portón abre una red contra el muerto central (sin "
                "sustentación); la separación por red es portón–muerto ({spread:.1f} m)",
                spread=doors.spread_m,
            )
        )
        if result.clump_weight_kg is None:
            out.append(
                t(
                    "twin_clump_weight: el portón no trae peso; indique clump_weight_kg para el "
                    "rozamiento del muerto"
                )
            )
    if result.kind == "outrigger":
        out.append(
            t(
                "outrigger_warp: un cable por red desde la punta del tangón con tijera a los dos "
                "portones (FL 470); la geometría de cada red se calcula como un arrastre con "
                "portones del libro"
            )
        )
    if result.kind == "beam":
        beam = result.beam
        assert beam is not None
        out.append(
            t(
                "beam_trawl: vara de {length:.2f} m (abertura horizontal) y patines de "
                "{height:.2f} m (abertura vertical); sin portones ni boyas; la red se calcula con "
                "la RN de diseño (Aberdeen), de la misma forma que la ec. 10 de C056/20",
                length=result.net_spread_m,
                height=result.vertical_opening_m,
            )
        )
        if case.beam_weight_kg is None and case.seabed is not None:
            out.append(
                t(
                    "beam_weight: sin peso de la vara y los patines (beam_weight_kg) no se "
                    "calcula su rozamiento con el fondo"
                )
            )
    return out


def _shrimp_notes(case: DesignCase, spread: SpreadStage) -> list[str]:
    """Notas del método camaronero de aberturas (Fase 19.7b): método, fuentes y rangos."""
    op = spread.shrimp
    if op is None:
        return []
    out: list[str] = []
    tij = op.balance
    if op.method == "tijera":
        assert tij is not None and op.net_leg_m is not None and op.leg_m is not None
        out.append(
            t(
                "shrimp_opening: método camaronero con tijera; DP {dp:.1f} m del equilibrio "
                "portón–tijera–red a {v:g} nudos (Roth 2016, IAT 72/2016, ecs. 13–17, con la "
                "proyección corregida de la ec. 12): rama L_C {lc:g} m, L_R {lr:.1f} m = cañas "
                "{b:g} m + pie de gallo + 0,90 × {body:.2f} m de red estirada sin copo; "
                "α = {alpha:.1f}°, β = {beta:.1f}°; la regla del libro daba {book:.1f} m",
                dp=op.door_spread_m,
                v=op.speed_kn or 0.0,
                lc=op.leg_m,
                lr=op.net_leg_m,
                b=op.bridle_m or 0.0,
                body=op.body_stretched_m or 0.0,
                alpha=tij.alpha_deg,
                beta=tij.beta_deg,
                book=op.book_door_spread_m,
            )
        )
        out.append(
            t(
                "shrimp_opening: AH {ah:.1f} m = DP × LRw/(LRw + pie de gallo + cañas) "
                "(triángulos semejantes de Mec!L225 con cañas cortas, no patentes); "
                "AH/DP = {r:.2f}: {verdict} de 0,72–0,88 de DynamiT (INIDEP)",
                ah=op.horizontal_opening_m,
                r=op.ah_over_dp,
                verdict=t("dentro") if op.ah_over_dp_in_range else t("fuera"),
            )
        )
        if case.shrimp_bridle_m is None:
            out.append(
                t(
                    "shrimp_opening: cañas de {b:g} m supuestas (IAT 85/2024 e ITO 61/2022; "
                    "rango 2,5–4 m en los aparejos del INIDEP); cambiar con shrimp_bridle_m",
                    b=case.shrimp_bridle,
                )
            )
    else:
        if tij is not None and not tij.converged:
            out.append(
                t(
                    "shrimp_opening: el equilibrio portón–tijera–red no tiene solución (la "
                    "sustentación del portón supera lo que equilibra la red); se usa el respaldo "
                    "AH = k·lima y la DP del libro"
                )
            )
        out.append(
            t(
                "shrimp_opening: método camaronero sin tijera; AH {ah:.1f} m = {k:.2f} × lima "
                "({fam}: {lo:.2f}–{hi:.2f}, {src}); DP {dp:.1f} m de la regla del libro",
                ah=op.horizontal_opening_m,
                k=op.k.k,
                fam=t(_SHRIMP_FAMILY[op.k.key]),
                lo=op.k.low,
                hi=op.k.high,
                src=op.k.source,
                dp=op.door_spread_m,
            )
        )
    out.append(
        t(
            "shrimp_opening: AH/lima = {r:.2f}, {verdict} de {lo:.2f}–{hi:.2f} ({fam}); "
            "DynamiT del INIDEP da 0,36–0,50 en tangoneras argentinas y la separación de "
            "portones medida con sensores es 0,74–0,77 × lima (IAT 94/2024); el INIDEP considera "
            "que su AH simulada queda «muy por debajo» del ≈ 70 % recomendado (IAT 85/2024): "
            "DynamiT puede subestimar",
            r=op.ah_over_headrope,
            verdict=t("dentro") if op.k.low <= op.ah_over_headrope <= op.k.high else t("fuera"),
            lo=op.k.low,
            hi=op.k.high,
            fam=t(_SHRIMP_FAMILY[op.k.key]),
        )
    )
    out.append(
        t(
            "shrimp_opening: AV {av:.2f} m = 0,04 × lima (0,03–0,07 en redes de baja abertura "
            "con pocas boyas); sin corrección por boyas (Watson et al. 1984, tabla 3: 10–20 "
            "boyas multiplican la AV por 1,75–2,9)",
            av=op.vertical_opening_m,
        )
    )
    out.append(
        t(
            "shrimp_opening: se omiten la DPA por ángulo de corte ({cut:.1f} m) y la serie de "
            "Fridman del promedio del libro (AH del libro {book:.1f} m); opening_method='book' "
            "vuelve al promedio",
            cut=spread.dpa_cut_angle_m,
            book=op.book_horizontal_opening_m,
        )
    )
    return out


#: Nombre de cada familia de k (AH = k·lima) en las notas.
_SHRIMP_FAMILY = {
    "inidep_dynamit": N_("tangonera argentina, DynamiT"),
    "us_conventional": N_("camaronera convencional de EE. UU., medida"),
    "tongue": N_("red de lengüeta, medida"),
}


def _cfp_checks(case: DesignCase, result: DesignResult) -> list[str]:
    """Límites de la Res. CFP 7/2018 para la flota langostinera con tangones (Fase 19.5).

    Art. 3 c: tangoneros nuevos de hasta 40 m de eslora y 2000 hp; art. 4: portones y abertura
    vertical de la boca de la red de hasta 150 cm. Sólo con tangones y un buque tangonero o una
    red de langostino.
    """
    if case.rig_kind != "outrigger":
        return []
    sp = case.net.species
    texts = (
        case.net.target_species,
        None if sp is None else sp.name,
        None if sp is None else sp.scientific_name,
    )
    hay = " ".join(x for x in texts if x).lower()
    tangonero = case.vessel.vessel_type is not None and case.vessel.vessel_type.value == (
        "tangonero"
    )
    if not (tangonero or "langostino" in hay or "pleoticus" in hay):
        return []
    out: list[str] = []
    limit = 1.5
    h = case.door.height_m
    if h is not None:
        ok = h <= limit
        out.append(
            t(
                "cfp_res7_2018: alto del portón {h:.2f} m: {verdict} (máximo 1,50 m, art. 4)",
                h=h,
                verdict=t("dentro del límite") if ok else t("por encima del límite"),
            )
        )
    av = float(result.spread.vertical_opening_m)
    verdict = t("dentro del límite") if av <= limit else t("por encima del límite")
    if result.spread.shrimp is not None:
        out.append(
            t(
                "cfp_res7_2018: abertura vertical {av:.2f} m (método camaronero, 0,04 × lima): "
                "{verdict} (máximo 1,50 m, art. 4)",
                av=av,
                verdict=verdict,
            )
        )
    else:
        out.append(
            t(
                "cfp_res7_2018: abertura vertical {av:.2f} m (Suzuki): {verdict} (máximo 1,50 m, "
                "art. 4)",
                av=av,
                verdict=verdict,
            )
        )
    loa = case.vessel.loa_m or case.vessel.length_m
    if loa is not None and loa > 40.0:
        out.append(t("cfp_res7_2018: eslora {loa:.1f} m mayor que 40 m (art. 3 c)", loa=float(loa)))
    if case.vessel.bhp > 2000.0:
        out.append(
            t(
                "cfp_res7_2018: potencia {hp:.0f} hp mayor que 2000 hp (art. 3 c)",
                hp=case.vessel.bhp,
            )
        )
    return out


#: Clave de las ventanas de velocidad con el tiro por la hélice (Fase 19.4).
PROPELLER_MODEL_KEY = "propeller_model"


def _stage_performance(
    case: DesignCase,
    power: PowerStage,
    warps: WarpStage,
    ballast: BallastStage,
    multi: RigStage | None = None,
) -> PerformanceStage:
    """FT de Fridman por propulsor frente a la resistencia total (con ROB en modo corregido).

    Con ``case.seabed`` la demanda suma el rozamiento con el fondo (:func:`seabed_friction_kgf`).
    Con tangones, gemelo o vara la demanda es la de todo el arte (:class:`RigStage`).
    """
    if multi is not None:
        friction = multi.friction_kgf
        demand = multi.demand
    else:
        friction = seabed_friction_kgf(case, ballast)
        demand = (
            warps.total
            if friction == 0.0
            else Pair(warps.total.std + friction, warps.total.mod + friction)
        )
    windows: dict[str, SpeedWindow] = {}
    for prop in (PropellerType.FIXED_PITCH, PropellerType.VARIABLE_PITCH_NOZZLE):
        ft = _ft_of(power.fridman, prop)
        if case.is_pair:
            ft = 2.0 * ft  # dos buques tiran de la misma red
        for variant in ("std", "mod"):
            windows[f"{prop.value}_{variant}"] = speed_window(
                case.speeds, ft, demand.variant(variant)
            )
    if power.propeller is not None:
        # Fase 19.4: ventana con el tiro por la hélice (no cambia el propulsor de diseño).
        ft = power.propeller.towing_kgf * (2.0 if case.is_pair else 1.0)
        for variant in ("std", "mod"):
            windows[f"{PROPELLER_MODEL_KEY}_{variant}"] = speed_window(
                case.speeds, ft, demand.variant(variant)
            )
    return PerformanceStage(
        windows=windows,
        demand=demand,
        design_key=f"{case.ft_propeller.value}_std",
        seabed_friction_kgf=friction,
    )


# ---------------------------------------------------------------------------------------------
# Corrida completa
# ---------------------------------------------------------------------------------------------


def _propeller_notes(
    case: DesignCase, power: PowerStage, performance: PerformanceStage
) -> list[str]:
    """Notas del tiro por la hélice (Fase 19.4)."""
    pp = power.propeller
    if pp is None:
        return []
    win = performance.windows[f"{PROPELLER_MODEL_KEY}_std"]
    vmax = win.max_speed_kn
    out = [
        t(
            "propeller_pull: tiro a punto fijo {bp:.2f} t por la hélice de {d:g} m "
            "({method}; Wärtsilä {w:.2f} t, ideal {ideal:.2f} t) frente a {prado:.2f} t de "
            "BHP·0,9·f/100 (regla de remolcadores de Zahalka, estimación gruesa); "
            "velocidad máxima con ese tiro: {vmax}",
            bp=pp.bollard_pull_t,
            d=pp.diameter_m,
            method=pp.method,
            w=pp.bollard_pull_wartsila_t,
            ideal=pp.bollard_pull_momentum_t,
            prado=pp.bollard_pull_prado_t,
            vmax=t("ninguna") if vmax is None else f"{vmax:.2f} kn",
        )
    ]
    out.extend(f"propeller_pull: {n}" for n in pp.notes)
    return out


def run(case: DesignCase) -> DesignResult:
    """Ejecuta el caso completo en el orden del libro y devuelve :class:`DesignResult`."""
    notes: list[str] = []
    if case.net_modified is None:
        notes.append(
            t(
                "net_modified no indicado: la columna modificada (G) usa la misma red que la "
                "estándar"
            )
        )
    if case.compat is Compat.EXCEL:
        notes.append(
            t("Compat.EXCEL: se reproducen las erratas registradas en trawlkit.compat.ERRATA")
        )
    notes.extend(f"catalog: {a}" for a in case.assumptions)
    geometry = _stage_geometry(case)
    notes.extend(f"geometry/{v}: {n}" for v in ("std", "mod") for n in geometry.variant(v).notes)
    dimensions = _stage_dimensions(case, geometry)
    power = _stage_power(case)
    drag = _stage_drag(case, geometry, dimensions)  # Aberdeen demersal; Dickson en NaN
    rig = _stage_rigging(case, dimensions)
    doors = _stage_doors(case, power, drag, rig)
    floats = _stage_floats(case, dimensions, power, drag, rig, notes)
    spread = _stage_spread(case, dimensions, drag, rig, doors, floats, notes)
    notes.extend(_shrimp_notes(case, spread))
    drag = _stage_drag(
        case,
        geometry,
        dimensions,
        ah_m=_arr(spread.fridman.dpa_std_m),  # Res!C282 = Mec!P164
        av_m=_arr(spread.vertical.fridman.std.av_m),  # Res!D282 = Mec!O272
    )
    bridles = _stage_bridles(case, dimensions, rig, doors, spread)
    ballast = _stage_ballast(case, dimensions, floats)
    warps = _stage_warps(case, dimensions, power, drag, rig, doors, bridles, floats)
    multi: RigStage | None = None
    if case.is_multi:  # Fase 19.5: tangones, gemelo o vara
        multi = _stage_rig(case, dimensions, geometry, drag, doors, spread, floats, ballast, warps)
        warps = _rig_warps(case, warps, multi)
        notes.extend(_rig_notes(case, multi, doors))
    performance = _stage_performance(case, power, warps, ballast, multi)
    winch = propulsion.winch_check(case, power, warps)  # Fase 19.4
    if winch is not None:
        warps = replace(warps, winch=winch)
        notes.extend(winch.warnings)
    notes.extend(_propeller_notes(case, power, performance))
    if (
        case.compat is Compat.CORRECTED
        and not case.is_pair
        and not case.is_beam
        and rigging.polar_extrapolated(case.door, case.door_attack_angle_deg)
    ):
        notes.append(
            t(
                "door_polar: el ángulo de ataque {angle:g}° cae fuera de los ángulos medidos de "
                "la polar de {door}; CL = {cl:.3f} y CD = {cd:.3f} son extrapolados",
                angle=case.door_attack_angle_deg,
                door=case.door.id,
                cl=doors.polar.cl,
                cd=doors.polar.cd,
            )
        )
    if case.compat is Compat.CORRECTED:
        notes.append(
            t(
                "warp_total_omits_doors: la resistencia total incluye ROB de los dos portones "
                "(Rem!H118 + 2·D190)"
            )
        )
        notes.append(
            t(
                "warp_cd_horizontal_angle: CD del cable {cd:.4f} con α = acos(cos δ1·cos δ2) = "
                "{angle:.2f}° interpolado (Rem!E106 usa δ2 → 0.02)",
                cd=warps.cd,
                angle=warps.cd_angle_deg,
            )
        )
    if case.net.family == "pelagic":
        notes.append(
            t(
                "pelagic_not_applicable: red pelágica; el lastre de Koyama, el rozamiento del "
                "burlón con el fondo y los ratios de Nomura están pensados para redes de fondo y "
                "no se aplican (el rozamiento con el fondo vale 0)"
            )
        )
    if case.is_pair:
        notes.append(
            t(
                "pair_trawl: arrastre de pareja sin portones; puntas de ala a {wings:.1f} m",
                wings=pair_wing_spread_m(case),
            )
            + (
                t(" (supuesto: ½ lima; cambiar con pair_wing_spread_m)")
                if case.pair_wing_spread_m is None
                else ""
            )
            + t(
                ", puntos de remolque a {tow:.1f} m; el tiro disponible es el de dos buques",
                tow=doors.spread_m,
            )
        )
    if case.door_spread_rule == "fridman" and not case.is_pair and not case.is_beam:
        notes.append(
            t(
                "door_spread_fridman: separación de portones {spread:.1f} m de la DPA de "
                "Fridman con el portón del caso (la regla al metro de Port!E13 vale para la A-3)",
                spread=doors.spread_m,
            )
        )
    if not warps.selection.satisfies_breaking_load:
        notes.append(
            t(
                "warp_undersized: cable de {d:g} mm ({mbl} t) por debajo de la rotura mínima "
                "{need:.2f} t",
                d=warps.selection.diameter_mm,
                mbl=warps.selection.breaking_load_t,
                need=warps.loads.min_breaking_load_kgf / 1000,
            )
        )
    result = DesignResult(
        case=case,
        geometry=geometry,
        dimensions=dimensions,
        power=power,
        drag=drag,
        rigging=rig,
        doors=doors,
        spread=spread,
        bridles=bridles,
        floats=floats,
        ballast=ballast,
        warps=warps,
        performance=performance,
        notes=notes,
        multirig=multi,
    )
    notes.extend(_cfp_checks(case, result))
    return result


__all__ = [
    "DEFAULT_SPEEDS_KN",
    "BallastStage",
    "BridleStage",
    "DesignCase",
    "DesignResult",
    "DoorStage",
    "DragStage",
    "FloatStage",
    "Pair",
    "PerformanceStage",
    "PowerStage",
    "RigStage",
    "RiggingGeometry",
    "SpreadStage",
    "VerticalOpening",
    "WarpStage",
    "run",
]
