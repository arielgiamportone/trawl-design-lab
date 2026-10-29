"""Caso de diseño de cada red del catálogo FAO (Fase 12).

Las redes del catálogo vienen de planos pensados para un buque, un portón y una profundidad
concretos. :func:`catalog_case` arma un :class:`~trawlkit.model.DesignCase` con esos datos en lugar
del buque de 150 hp y el portón de la FAO A-3:

* **Buque**: uno genérico con la potencia media del rango de diseño de la red (``vessel_hp``).
  Eslora, manga y puntal escalan los del buque de la A-3 (150 hp: 9,0 × 2,5 × 1,8 m) con la raíz
  cúbica de la potencia (supuesto: buques semejantes).
* **Portón**: el del plano cuando lo da (largo, alto y peso en ``design``), con la polar del
  portón plano de la A-3 (la polar es adimensional). Si no, el de la A-3 escalado por área con la
  potencia (superficie ∝ potencia, semejanza geométrica). En la pareja el portón no se usa.
* **Profundidad y patentes**: las de ``design`` (con su procedencia) o un valor por familia.
* **Separación de portones**: de la DPA de Fridman con el portón del caso
  (``door_spread_rule="fridman"``); la regla «al metro» del libro vale para la A-3.
* **Buque y portón del catálogo** (Fase 19.5): si ``design`` nombra un buque de la flota
  (``vessel_id``) o un portón del catálogo de componentes (``door_id``), se usan esos, con la
  razón en la procedencia de la red. El aparejo (``rig``) y sus parámetros (tangón, tijera,
  muerto, vara) también salen de ``design`` cuando la fuente los da.

Todo lo que no sale de la fuente queda en :attr:`CatalogCase.assumptions`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from trawlkit.i18n import t
from trawlkit.io import Door, NetSpec, Vessel, load_doors, load_fleet, load_net, load_vessels
from trawlkit.model import DEFAULT_SPEEDS_KN, DesignCase

#: Profundidad de trabajo por familia cuando la fuente no la da [m].
DEFAULT_DEPTH_M = {"bottom": 30.0, "semi_pelagic": 40.0, "pelagic": 60.0}
#: Profundidad de diseño de la flota langostinera argentina (Fase 19.7b) [m] y su rango: lances
#: comerciales a 71–87 m (Rubio et al. 2022, INIDEP IC 68/2022, p. 1) y medidos a 86–106 m (Roth,
#: Pisano y Di Leva 2024, IAT 94/2024, tabla 1); las simulaciones DynamiT de tangoneras del INIDEP
#: usan 100 m (IAT 27/2019, 85/2024 y 104/2023). Valor elegido dentro de ese rango (supuesto).
LANGOSTINO_DEPTH_M = 90.0
LANGOSTINO_DEPTH_RANGE_M: tuple[float, float] = (70.0, 110.0)


def default_depth(spec: NetSpec) -> tuple[float, str | None]:
    """Profundidad de trabajo de una red del catálogo y la nota si no la da la fuente.

    Orden: ``design.depth_m`` del plano, ``species.depth_m``, la de la flota langostinera
    (:data:`LANGOSTINO_DEPTH_M`, si la especie es el langostino) y, si no, el valor por familia
    (:data:`DEFAULT_DEPTH_M`), con una nota para las suposiciones del caso.
    """
    from trawlkit.rigging.shrimp import is_langostino

    design = (spec.model_extra or {}).get("design") or {}
    if isinstance(design, dict) and design.get("depth_m") is not None:
        return float(design["depth_m"]), None
    if spec.species is not None and spec.species.depth_m is not None:
        return float(spec.species.depth_m), None
    sp = spec.species
    if is_langostino(
        spec.target_species,
        None if sp is None else sp.name,
        None if sp is None else sp.scientific_name,
    ):
        lo, hi = LANGOSTINO_DEPTH_RANGE_M
        return LANGOSTINO_DEPTH_M, t(
            "la fuente no da profundidad: {depth:g} m de la flota langostinera ({lo:g}–{hi:g} m; "
            "INIDEP IC 68/2022, IAT 94/2024 y simulaciones DynamiT a 100 m)",
            depth=LANGOSTINO_DEPTH_M,
            lo=lo,
            hi=hi,
        )
    depth = DEFAULT_DEPTH_M.get(spec.family or "bottom", 30.0)
    note = t(
        "la fuente no da profundidad: {depth:g} m por familia ({family})",
        depth=depth,
        family=spec.family,
    )
    return depth, note


#: Buque de referencia para escalar eslora, manga y puntal (el de 150 hp de la A-3).
REFERENCE_VESSEL_ID = "fao_a3_150hp"
#: Portón de referencia (polar y proporciones): el plano de madera de la A-3.
REFERENCE_DOOR_ID = "fao_flat_wood_a3"
#: Parámetros del aparejo (Fase 19.5) que ``design`` puede traer de la fuente.
RIG_DESIGN_KEYS: tuple[str, ...] = (
    "boom_length_m",
    "boom_angle_deg",
    "outrigger_bridle_m",
    "outrigger_bridle_diameter_mm",
    "clump_weight_kg",
    "clump_frontal_area_m2",
    "beam_count",
    "beam_length_m",
    "beam_diameter_m",
    "beam_shoe_area_m2",
    "beam_shoe_height_m",
    "beam_weight_kg",
    "shrimp_bridle_m",
)


@dataclass(frozen=True)
class CatalogCase:
    """Caso de diseño de una red del catálogo y los supuestos con que se armó."""

    case: DesignCase
    assumptions: list[str] = field(default_factory=list)


def _design(spec: NetSpec) -> dict[str, Any]:
    d = (spec.model_extra or {}).get("design")
    return dict(d) if isinstance(d, dict) else {}


def design_hp(spec: NetSpec) -> float:
    """Potencia de diseño [hp]: media del rango ``vessel_hp`` de la red (150 si no lo tiene)."""
    if spec.vessel_hp is None:
        return 150.0
    lo, hi = spec.vessel_hp
    return 0.5 * (float(lo) + float(hi))


def generic_vessel(bhp: float, length_m: float | None = None) -> Vessel:
    """Buque genérico de ``bhp`` hp semejante al de 150 hp de la A-3.

    Las medidas escalan con la raíz cúbica de la potencia o, si se da la eslora del documento
    (``length_m``), con la razón de esloras.
    """
    ref = next(v for v in load_vessels().vessels if v.id == REFERENCE_VESSEL_ID)
    k = (bhp / ref.bhp) ** (1.0 / 3.0)
    if length_m is not None:
        k = length_m / float(ref.length_m or 9.0)
    return Vessel(
        id=f"generic_{bhp:g}hp",
        name=t("Buque genérico de {hp:g} hp (escalado del de 150 hp de la A-3)", hp=bhp),
        bhp=bhp,
        length_m=round(float(ref.length_m or 9.0) * k, 2),
        beam_m=round(float(ref.beam_m or 2.5) * k, 2),
        depth_m=round(float(ref.depth_m or 1.8) * k, 2),
        displacement_t=None if ref.displacement_t is None else round(ref.displacement_t * k**3, 1),
        propeller=ref.propeller,
        high_rpm=ref.high_rpm,
    )


def complete_vessel(v: Vessel) -> tuple[Vessel, list[str]]:
    """Completa manga y puntal que faltan escalando el buque de la A-3 (Fase 19.4).

    El catálogo de la flota no inventa medidas que la fuente no da; para calcular un caso se
    escalan del buque de 150 hp de la A-3 con la razón de esloras (o la raíz cúbica de la
    potencia, sin eslora), como :func:`trawlkit.catalog.generic_vessel`, y se anota.
    """
    missing = [k for k in ("length_m", "beam_m", "depth_m") if getattr(v, k) is None]
    if not missing:
        return v, []
    gen = generic_vessel(v.bhp, v.length_m)
    update = {k: getattr(gen, k) for k in missing}
    notes = [
        t("{key} = {value} m escalado del buque de la A-3", key=k, value=val)
        for k, val in update.items()
    ]
    return v.model_copy(update=update), notes


def _reference_door() -> Door:
    return next(d for d in load_doors().doors if d.id == REFERENCE_DOOR_ID)


def plan_door(length_m: float, height_m: float, weight_air_kg: float | None, name: str) -> Door:
    """Portón plano de las medidas del plano con la polar del portón plano de la A-3."""
    ref = _reference_door()
    data: dict[str, Any] = ref.model_dump()
    area = length_m * height_m
    data.update(
        id=f"plan_{length_m:g}x{height_m:g}",
        name=name,
        length_m=length_m,
        height_m=height_m,
        area_m2=area,
        aspect_ratio=height_m / length_m,
        weight_air_kg=weight_air_kg,
        weight_water_kg=None
        if weight_air_kg is None
        else weight_air_kg * float(data.get("weight_water_coefficient", 0.6)),
    )
    return Door.model_validate(data)


#: Ángulos [°] en que se repiten el CL y el CD publicados de un portón (Fase 20.2): la fuente da
#: un solo par (el del ángulo de trabajo), así que la polar es plana en todo el rango del libro.
PUBLISHED_POLAR_ANGLES_DEG: tuple[float, ...] = (20.0, 25.0, 30.0, 32.0, 35.0, 40.0, 45.0)


def door_from_params(params: dict[str, Any], name: str, door_id: str) -> tuple[Door, str]:
    """Portón con los datos que publica una fuente y la nota de cómo se armó (Fase 20.2).

    ``params`` usa las claves de ``design``: ``door_length_m`` y ``door_height_m`` (obligatorias),
    ``door_area_m2`` (si no, largo × alto), ``door_weight_air_kg`` y la polar: ``door_cl`` y
    ``door_cd`` publicados (constantes con el ángulo, :data:`PUBLISHED_POLAR_ANGLES_DEG`), una hoja
    de la biblioteca de polares (``door_polar_id``) o, si no, la del portón plano de la A-3.

    ``door_type`` (Fase 20.5) es el tipo del portón; el portón queda marcado con
    ``polar_published`` (``True`` sólo con CL y CD de la fuente). Un ``polyvalent`` sin polar
    publicada lleva en modo corregido el CL efectivo calibrado
    (:func:`trawlkit.rigging.polars.cl_effective_factor`).
    """
    from trawlkit.io.schema import DoorCoefficients
    from trawlkit.rigging.polars import get_polar

    ref = _reference_door()
    data: dict[str, Any] = ref.model_dump()
    length, height = float(params["door_length_m"]), float(params["door_height_m"])
    area = float(params.get("door_area_m2") or length * height)
    weight = params.get("door_weight_air_kg")
    published = params.get("door_cl") is not None and params.get("door_cd") is not None
    if published:
        cl, cd = float(params["door_cl"]), float(params["door_cd"])
        coefficients = [
            DoorCoefficients(angle_deg=a, cl=cl, cd=cd) for a in PUBLISHED_POLAR_ANGLES_DEG
        ]
        polar_note = t("CL = {cl:g} y CD = {cd:g} de la fuente", cl=cl, cd=cd)
    elif params.get("door_polar_id"):
        polar = get_polar(str(params["door_polar_id"]))
        coefficients = [
            DoorCoefficients(angle_deg=c.angle_deg, cl=c.cl, cd=c.cd)
            for c in polar.usable(with_max=True)
        ]
        polar_note = t("polar {polar}", polar=polar.name)
    else:
        coefficients = list(ref.coefficients)
        polar_note = t("polar del portón plano de la A-3")
    data.update(
        id=door_id,
        name=name,
        length_m=length,
        height_m=height,
        area_m2=area,
        aspect_ratio=height / length,
        weight_air_kg=None if weight is None else float(weight),
        weight_water_kg=None
        if weight is None
        else float(weight) * float(data.get("weight_water_coefficient", 0.6)),
        coefficients=[c.model_dump() for c in coefficients],
        polar_published=published,
    )
    if params.get("door_type"):
        data["type"] = str(params["door_type"])
    note = t(
        "portón de la fuente ({area:.2f} m², {length:g} × {height:g} m) con {polar}",
        area=area,
        length=length,
        height=height,
        polar=polar_note,
    )
    return Door.model_validate(data), note


def source_door(spec: NetSpec, hp: float, rig: str = "otter") -> tuple[Door, list[str]]:
    """Portón que da la fuente de la red y sus notas (Fase 19.8d).

    El del catálogo de componentes que nombra ``design.door_id``; si no, el del plano (largo,
    alto y peso en ``design``) con la polar del portón plano de la A-3; si no, el de la A-3
    escalado por área a ``hp`` caballos. Lo usan :func:`catalog_case` (con la potencia de diseño
    de la red) y la API cuando se elige un buque pero no un portón (con la de ese buque).
    """
    from trawlkit.components import DoorItem, get_component

    design = _design(spec)
    notes: list[str] = []
    door_item = None
    if design.get("door_id"):
        try:
            door_item = get_component("door", str(design["door_id"]))
        except KeyError:
            door_item = None
    if isinstance(door_item, DoorItem):
        door = door_item.to_door()
        notes.append(
            t(
                "portón {name} del catálogo de componentes ({area:.2f} m²), el que indica la red",
                name=door.name,
                area=door.area_m2 or 0.0,
            )
        )
    elif (
        "door_length_m" in design
        and "door_height_m" in design
        and (any(k in design for k in ("door_area_m2", "door_cl", "door_polar_id")))
    ):
        # Fase 20.2: superficie y polar de la fuente (CL y CD publicados u hoja de la biblioteca).
        door, note = door_from_params(
            design, t("Portón de la fuente de {net}", net=spec.id), f"source_{spec.id}"
        )
        notes.append(note)
    elif "door_length_m" in design and "door_height_m" in design:
        weight = design.get("door_weight_air_kg")
        door = plan_door(
            float(design["door_length_m"]),
            float(design["door_height_m"]),
            None if weight is None else float(weight),
            t("Portón plano del plano de {net}", net=spec.id),
        )
        notes.append(
            t(
                "portón del plano ({length:g} × {height:g} m) con la polar del "
                "portón plano de la A-3",
                length=door.length_m,
                height=door.height_m,
            )
        )
    else:
        from trawlkit.optimize.scaling import scale_door

        ref = _reference_door()
        door = scale_door(ref, float(ref.area_m2 or 1.805) * hp / 150.0)
        if rig not in ("pair", "beam"):
            notes.append(
                t(
                    "el plano no da portón: el de la A-3 escalado a {area:.2f} m² "
                    "(superficie proporcional a la potencia)",
                    area=door.area_m2,
                )
            )
    return door, notes


def source_params(spec: NetSpec) -> dict[str, Any]:
    """Patentes y parámetros del aparejo (tangón, tijera, muerto, vara) que da ``design``."""
    design = _design(spec)
    out: dict[str, Any] = {}
    if design.get("sweeps_m") is not None:
        out["sweeps_m"] = float(design["sweeps_m"])
    for key in RIG_DESIGN_KEYS:
        if design.get(key) is not None:
            out[key] = int(design[key]) if key == "beam_count" else float(design[key])
    return out


#: Cable de remolque genérico del Workbook (6x19, 9/9/1, «FC o IWRC») por diámetro: el que se
#: toma cuando la fuente da el diámetro del cable pero no el fabricante (Fase 19.9).
SOURCE_WARP_ID = "wire_6x19_991_{diameter:g}mm"


def source_warp(spec: NetSpec) -> tuple[str | None, list[str]]:
    """Cable de remolque que da la fuente de la red y sus notas (Fase 19.9).

    Con ``design.warp_diameter_mm`` (y ``design.warp_core``, el alma) se toma el cable genérico
    de ese diámetro del catálogo de componentes (:data:`SOURCE_WARP_ID`), sin atribuir
    fabricante. Si no hay uno de ese diámetro y alma, ``None`` (selección automática) con una
    nota. Lo usan :func:`catalog_case` y la API; un ``warp_id`` elegido por el usuario manda.
    """
    from trawlkit.components import WireItem, get_component

    design = _design(spec)
    if design.get("warp_diameter_mm") is None:
        return None, []
    diameter = float(design["warp_diameter_mm"])
    core = design.get("warp_core")
    try:
        item = get_component("wire", SOURCE_WARP_ID.format(diameter=diameter))
    except KeyError:
        item = None
    if not isinstance(item, WireItem) or (core and str(core) not in str(item.core or "")):
        return None, [
            t(
                "la fuente da un cable de remolque de {diameter:g} mm pero el catálogo de "
                "componentes no tiene uno genérico de ese diámetro: selección automática",
                diameter=diameter,
            )
        ]
    return item.id, [
        t(
            "cable de remolque de {diameter:g} mm de la fuente{core}: {name} del catálogo de "
            "componentes (genérico, rotura mínima {mbl:g} t)",
            diameter=diameter,
            core=t(" (alma de acero)") if core == "IWRC" else "",
            name=item.name,
            mbl=item.breaking_load_t,
        )
    ]


def catalog_case(
    net: str | NetSpec,
    speeds_kn: Sequence[float] = DEFAULT_SPEEDS_KN,
    **overrides: Any,
) -> CatalogCase:
    """Caso de diseño de la red ``net`` (id del catálogo o spec) con su buque, portón y fondo.

    ``overrides`` se pasan a :class:`~trawlkit.model.DesignCase` (p. ej. ``depth_m``,
    ``pair_wing_spread_m``, ``seabed``) y tienen prioridad sobre lo que sale de la fuente.
    """
    spec = load_net(net) if isinstance(net, str) else net
    design = _design(spec)
    notes: list[str] = []
    hp = design_hp(spec)
    length = design.get("vessel_length_m")
    fleet = {v.id: v for v in load_fleet().vessels}
    if design.get("vessel_id") in fleet:
        vessel, filled = complete_vessel(fleet[str(design["vessel_id"])])
        notes.append(
            t(
                "buque {name} de la flota ({hp:g} hp), el que indica la red",
                name=vessel.name or vessel.id,
                hp=vessel.bhp,
            )
        )
        notes.extend(filled)
    else:
        vessel = generic_vessel(hp, None if length is None else float(length))
        if spec.vessel_hp is None:
            notes.append(t("la red no da potencia de diseño: buque genérico de 150 hp"))
        rule = t("eslora del documento") if length is not None else t("raíz cúbica de la potencia")
        notes.append(
            t(
                "buque genérico de {hp:g} hp: eslora {length} m, manga {beam} m y "
                "puntal {depth} m escalados del de 150 hp de la A-3 ({rule})",
                hp=hp,
                length=vessel.length_m,
                beam=vessel.beam_m,
                depth=vessel.depth_m,
                rule=rule,
            )
        )
    rig = overrides.get("rig") or spec.rig or "otter"
    door, door_notes = source_door(spec, hp, rig)
    notes.extend(door_notes)
    depth, depth_note = default_depth(spec)
    if depth_note:
        notes.append(depth_note)
    # La regla «al metro» del libro (Port!E13) está calibrada para las pastecas de la A-3: con
    # otro buque la separación sale de la DPA de Fridman con el portón del caso.
    kwargs: dict[str, Any] = {"depth_m": float(depth), "door_spread_rule": "fridman"}
    kwargs.update(source_params(spec))
    from trawlkit.io.schema import PropellerType
    from trawlkit.power import FRIDMAN_KF

    if overrides.get("fridman_kf") is None and vessel.propeller not in FRIDMAN_KF:
        # Hélice sin KF de Fridman en el libro (PF+T, PV; p. ej. el BIP Holmberg): se calcula como
        # paso fijo, lo conservador, igual que la API (trawlkit.api.service.build_case). Fase 20.2.
        kwargs["fridman_kf"] = FRIDMAN_KF[PropellerType.FIXED_PITCH]
        notes.append(
            t(
                "hélice {prop}: el tiro se calcula como paso fijo (el libro sólo tabula PF y "
                "PV con tobera)",
                prop=vessel.propeller.value,
            )
        )
    if overrides.get("warp_id") is None:
        warp_id, warp_notes = source_warp(spec)
        if warp_id is not None:
            kwargs["warp_id"] = warp_id
        notes.extend(warp_notes)
    kwargs.update(overrides)
    case = DesignCase(
        net=spec,
        vessel=vessel,
        door=door,
        speeds_kn=tuple(float(v) for v in speeds_kn),
        assumptions=tuple(notes),
        **kwargs,
    )
    return CatalogCase(case=case, assumptions=notes)


__all__ = [
    "DEFAULT_DEPTH_M",
    "LANGOSTINO_DEPTH_M",
    "LANGOSTINO_DEPTH_RANGE_M",
    "RIG_DESIGN_KEYS",
    "SOURCE_WARP_ID",
    "CatalogCase",
    "catalog_case",
    "PUBLISHED_POLAR_ANGLES_DEG",
    "design_hp",
    "door_from_params",
    "generic_vessel",
    "plan_door",
    "source_door",
    "source_params",
    "source_warp",
]
