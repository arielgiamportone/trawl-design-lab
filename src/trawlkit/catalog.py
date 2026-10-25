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

Todo lo que no sale de la fuente queda en :attr:`CatalogCase.assumptions`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from trawlkit.io import Door, NetSpec, Vessel, load_doors, load_net, load_vessels
from trawlkit.model import DEFAULT_SPEEDS_KN, DesignCase

#: Profundidad de trabajo por familia cuando la fuente no la da [m].
DEFAULT_DEPTH_M = {"bottom": 30.0, "semi_pelagic": 40.0, "pelagic": 60.0}
#: Buque de referencia para escalar eslora, manga y puntal (el de 150 hp de la A-3).
REFERENCE_VESSEL_ID = "fao_a3_150hp"
#: Portón de referencia (polar y proporciones): el plano de madera de la A-3.
REFERENCE_DOOR_ID = "fao_flat_wood_a3"


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


def generic_vessel(bhp: float) -> Vessel:
    """Buque genérico de ``bhp`` hp semejante al de 150 hp de la A-3 (raíz cúbica)."""
    ref = next(v for v in load_vessels().vessels if v.id == REFERENCE_VESSEL_ID)
    k = (bhp / ref.bhp) ** (1.0 / 3.0)
    return Vessel(
        id=f"generic_{bhp:g}hp",
        name=f"Buque genérico de {bhp:g} hp (escalado del de 150 hp de la A-3)",
        bhp=bhp,
        length_m=round(float(ref.length_m or 9.0) * k, 2),
        beam_m=round(float(ref.beam_m or 2.5) * k, 2),
        depth_m=round(float(ref.depth_m or 1.8) * k, 2),
        displacement_t=None if ref.displacement_t is None else round(ref.displacement_t * k**3, 1),
        propeller=ref.propeller,
        high_rpm=ref.high_rpm,
    )


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
    vessel = generic_vessel(hp)
    if spec.vessel_hp is None:
        notes.append("la red no da potencia de diseño: buque genérico de 150 hp")
    notes.append(
        f"buque genérico de {hp:g} hp: eslora {vessel.length_m} m, manga {vessel.beam_m} m y "
        f"puntal {vessel.depth_m} m escalados del de 150 hp de la A-3 (raíz cúbica de la potencia)"
    )
    rig = overrides.get("rig") or spec.rig or "otter"
    if "door_length_m" in design and "door_height_m" in design:
        weight = design.get("door_weight_air_kg")
        door = plan_door(
            float(design["door_length_m"]),
            float(design["door_height_m"]),
            None if weight is None else float(weight),
            f"Portón plano del plano de {spec.id}",
        )
        notes.append(
            f"portón del plano ({door.length_m:g} × {door.height_m:g} m) con la polar del "
            "portón plano de la A-3"
        )
    else:
        from trawlkit.optimize.scaling import scale_door

        ref = _reference_door()
        door = scale_door(ref, float(ref.area_m2 or 1.805) * hp / 150.0)
        if rig != "pair":
            notes.append(
                f"el plano no da portón: el de la A-3 escalado a {door.area_m2:.2f} m² "
                "(superficie proporcional a la potencia)"
            )
    if rig == "pair":
        notes.append("arrastre de pareja: el portón del caso no se usa")
    depth = design.get("depth_m")
    if depth is None:
        depth = DEFAULT_DEPTH_M.get(spec.family or "bottom", 30.0)
        notes.append(f"la fuente no da profundidad: {depth:g} m por familia ({spec.family})")
    # La regla «al metro» del libro (Port!E13) está calibrada para las pastecas de la A-3: con
    # otro buque la separación sale de la DPA de Fridman con el portón del caso.
    kwargs: dict[str, Any] = {"depth_m": float(depth), "door_spread_rule": "fridman"}
    if design.get("sweeps_m") is not None:
        kwargs["sweeps_m"] = float(design["sweeps_m"])
    kwargs.update(overrides)
    case = DesignCase(
        net=spec,
        vessel=vessel,
        door=door,
        speeds_kn=tuple(float(v) for v in speeds_kn),
        **kwargs,
    )
    return CatalogCase(case=case, assumptions=notes)


__all__ = [
    "DEFAULT_DEPTH_M",
    "CatalogCase",
    "catalog_case",
    "design_hp",
    "generic_vessel",
    "plan_door",
]
