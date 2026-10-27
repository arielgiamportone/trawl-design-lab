"""Elección de portones del catálogo para un caso (Fase 19.3).

:func:`select_doors` toma la superficie requerida por portón que calcula el motor para el caso
(Port!F215: la que da al portón del caso, con su CD, la resistencia asignada ROB entre 2 y 4 kn;
:func:`trawlkit.model._stage_doors`) y la lleva a cada portón del catálogo con la regla de la
superficie equivalente de Seafish/IFREMER/DIFTA (1993, App. III-9, PDF p. 123): la misma fuerza
de abertura con otro tipo de portón pide

    A₂ = A₁ · CL₁ / CL₂,

con CL₁ el del portón del caso al ángulo del caso y CL₂ el del candidato a su ángulo de trabajo
(el del caso si es del mismo tipo; si no, el centro del rango recomendado del tipo,
:data:`trawlkit.rigging.polars.ATTACK_ANGLES`). Al pasar a un portón de más CL se suma un margen
de 10 % (Seafish 1993, sección 3-16: «a safety margin of 10 % could be added to the new
otterboard area first calculated»).

Para cada candidato se revisa además:

* **Peso**: el *Fisherman's Workbook* (FAO, Prado y Dremière 1990) da el peso máximo usado por
  tipo y superficie y aclara que con un material liviano un portón puede ser hasta 50 % más
  liviano. Un portón más liviano que la mitad del peso del Workbook del mismo tipo y superficie
  se marca; sin peso publicado, se avisa (no se inventa).
* **Ángulo de ataque** recomendado para el tipo y **patas de gallo** (backstrops) de 1 a 1,5
  veces el largo del portón (Seafish 1993, sección 2.2.3).
"""

from __future__ import annotations

import warnings
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from trawlkit import rigging
from trawlkit.components import DoorItem, load_components
from trawlkit.i18n import t
from trawlkit.io import Door
from trawlkit.model import DesignCase, DesignResult, run
from trawlkit.rigging.polars import (
    ATTACK_ANGLES,
    BACKSTROP_RATIO,
    DOOR_TYPE_LABEL,
    EQUIVALENT_AREA_MARGIN,
    canonical_type,
)

#: Fracción del peso máximo del Workbook por debajo de la cual un portón se marca como liviano
#: («a lighter material which may make a board as much as 50% lighter»).
LIGHT_WEIGHT_FRACTION = 0.5

#: Tipo de los genéricos del Workbook con peso, por tipo canónico (los cambados y multiperfil no
#: tienen tabla de pesos en el Workbook).
WORKBOOK_TYPE = {"flat": "flat", "oval": "oval", "v": "v", "high_aspect": "suberkrub"}


@dataclass(frozen=True)
class DoorCandidate:
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
    weight_status: str  # ok, light, missing, no_reference
    weight_reference_kg: float | None
    attack_angle: dict[str, Any] | None
    backstrop_m: tuple[float, float] | None
    hp_ok: bool | None
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "type_label": self.type_label,
            "brand": self.brand,
            "generic": self.generic,
            "area_m2": self.area_m2,
            "length_m": self.length_m,
            "weight_air_kg": self.weight_air_kg,
            "weight_water_kg": self.weight_water_kg,
            "angle_deg": self.angle_deg,
            "cl": self.cl,
            "cd": self.cd,
            "required_m2": self.required_m2,
            "margin_applied": self.margin_applied,
            "area_margin": self.area_margin,
            "ok": self.ok,
            "weight_status": self.weight_status,
            "weight_reference_kg": self.weight_reference_kg,
            "attack_angle": self.attack_angle,
            "backstrop_m": list(self.backstrop_m) if self.backstrop_m else None,
            "hp_ok": self.hp_ok,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class DoorSelection:
    """Resultado de :func:`select_doors`."""

    required_m2: float
    """Superficie requerida por portón con el portón del caso (Port!F215) [m²]."""
    case_door: dict[str, Any]
    candidates: tuple[DoorCandidate, ...]
    """Portones que cumplen la superficie equivalente, del más justo al más holgado."""
    rejected: int
    """Cuántos portones evaluados no llegan a la superficie equivalente."""
    margin: float
    rules: tuple[dict[str, str], ...]
    notes: tuple[str, ...] = field(default=())

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "required_m2": self.required_m2,
            "case_door": self.case_door,
            "candidates": [c.to_dict() for c in self.candidates],
            "rejected": self.rejected,
            "margin": self.margin,
            "rules": [dict(r) for r in self.rules],
            "notes": list(self.notes),
        }


def _rules() -> tuple[dict[str, str], ...]:
    return (
        {
            "rule": t("superficie equivalente A₂ = A₁·CL₁/CL₂"),
            "document": "sfia1993",
            "page": "Appendix III-9 (PDF p. 123)",
        },
        {
            "rule": t("margen de 10 % al pasar a un portón de más CL"),
            "document": "sfia1993",
            "page": "Section 3-16 (PDF p. 61)",
        },
        {
            "rule": t(
                "peso: el Workbook da el máximo usado; con material liviano, hasta 50 % menos"
            ),
            "document": "prado1990",
            "page": "Workbook, «Otter boards: properties of the principal types» (PDF p. 97)",
        },
        {
            "rule": t("patas de gallo de 1 a 1,5 veces el largo del portón"),
            "document": "sfia1993",
            "page": "Section 2-14, §2.2.3 (PDF p. 37)",
        },
        {
            "rule": t("ángulo de ataque recomendado por tipo"),
            "document": "prado1990",
            "page": "Workbook, «Otter boards: proportions, angles of attack» (PDF p. 95)",
        },
    )


def _workbook_weights() -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Peso máximo del Workbook en función de la superficie, por tipo canónico."""
    out: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    gens = [
        g
        for g in load_components("door", generic_only=True)
        if isinstance(g, DoorItem) and g.weight_air_kg and g.hp_range is not None
    ]
    for key, wb_type in WORKBOOK_TYPE.items():
        pts = sorted(
            {(g.area_m2, float(g.weight_air_kg or 0.0)) for g in gens if g.type == wb_type}
        )
        if len(pts) >= 2:
            out[key] = (np.array([p[0] for p in pts]), np.array([p[1] for p in pts]))
    return out


def _suits_family(door_type: str | None, net_family: str | None) -> bool:
    """Si el tipo de portón sirve para la red: pelágicos para pelágica, de fondo para fondo.

    El Workbook pone al Süberkrüb entre los portones de media agua («Midwater, Suberkrub») y
    Seafish (1993, §2.2.1) advierte que una relación de aspecto alta lo vuelve inestable a las
    velocidades bajas del arrastre de fondo. La red semipelágica acepta los dos.
    """
    if net_family == "pelagic":
        return door_type == "high_aspect"
    if net_family == "bottom":
        return door_type != "high_aspect"
    return True


def _family(door_type: str | None) -> str | None:
    return canonical_type(door_type) or (door_type.lower() if door_type else None)


def _evaluate(
    item_id: str,
    name: str,
    brand: str | None,
    generic: bool,
    door: Door,
    hp_range: tuple[float, float] | None,
    *,
    case: DesignCase,
    a1: float,
    cl1: float,
    margin: float,
    weights: dict[str, tuple[np.ndarray, np.ndarray]],
) -> DoorCandidate | None:
    typ = canonical_type(door.type)
    same = _family(door.type) == _family(case.door.type)
    rng = ATTACK_ANGLES.get(typ) if typ else None
    angle = case.door_attack_angle_deg if same or rng is None else rng.design_deg
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", rigging.PolarExtrapolationWarning)
            polar = rigging.door_polar(door, angle, interpolate=True)
    except KeyError:
        return None
    if polar.cl <= 0 or door.area_m2 is None:
        return None
    higher = polar.cl > cl1 * (1.0 + 1e-9)
    req = a1 * cl1 / polar.cl * ((1.0 + margin) if higher else 1.0)
    area = float(door.area_m2)
    warn: list[str] = []
    if rigging.polar_extrapolated(door, angle):
        warn.append(t("CL extrapolado fuera de la polar medida"))
    w_air = door.weight_air_kg
    coef = (door.model_extra or {}).get("weight_water_coefficient")
    w_water = door.weight_water_kg or (
        float(w_air) * float(coef) if w_air and coef is not None else None
    )
    ref = None
    if w_air is None and w_water is None:
        status = "missing"
        warn.append(t("sin peso publicado: pedir el peso al fabricante"))
    elif typ in weights:
        a, w = weights[typ]
        ref = float(np.interp(area, a, w))
        if w_air is not None and w_air < LIGHT_WEIGHT_FRACTION * ref:
            status = "light"
            warn.append(
                t(
                    "peso {w:.0f} kg: menos de la mitad del máximo del Workbook para el tipo y la "
                    "superficie ({ref:.0f} kg); puede no apoyar bien en el fondo",
                    w=w_air,
                    ref=ref,
                )
            )
        else:
            status = "ok"
    else:
        status = "no_reference"
    hp = float(case.vessel.bhp)
    hp_ok = None if hp_range is None else bool(0.75 * hp_range[0] <= hp <= 1.25 * hp_range[1])
    if hp_ok is False:
        warn.append(
            t(
                "rango de potencia del catálogo {lo:g}–{hi:g} hp (buque de {hp:g} hp)",
                lo=hp_range[0] if hp_range else 0,
                hi=hp_range[1] if hp_range else 0,
                hp=hp,
            )
        )
    length = door.length_m
    return DoorCandidate(
        id=item_id,
        name=name,
        type=door.type,
        type_label=t(DOOR_TYPE_LABEL[typ]) if typ else None,
        brand=brand,
        generic=generic,
        area_m2=area,
        length_m=length,
        weight_air_kg=w_air,
        weight_water_kg=w_water,
        angle_deg=float(angle),
        cl=float(polar.cl),
        cd=float(polar.cd),
        required_m2=float(req),
        margin_applied=higher,
        area_margin=float(area / req - 1.0),
        ok=area >= req * (1.0 - 1e-9),
        weight_status=status,
        weight_reference_kg=ref,
        attack_angle=rng.to_dict() if rng else None,
        backstrop_m=(BACKSTROP_RATIO[0] * length, BACKSTROP_RATIO[1] * length) if length else None,
        hp_ok=hp_ok,
        warnings=tuple(warn),
    )


def select_doors(
    case_or_result: DesignCase | DesignResult,
    *,
    brands: Iterable[str] | None = None,
    region: str | None = None,
    generic_only: bool = False,
    types: Sequence[str] | None = None,
    margin: float = EQUIVALENT_AREA_MARGIN,
    max_results: int = 20,
    include_light: bool = True,
) -> DoorSelection:
    """Portones del catálogo que alcanzan la superficie equivalente del caso (ver el módulo).

    ``brands``/``region``/``generic_only`` filtran el catálogo de componentes como
    :func:`~trawlkit.components.load_components`; ``types`` limita los tipos canónicos
    (``flat``, ``v``, ``oval``, ``cambered``, ``multifoil``, ``high_aspect``); ``margin`` es el
    margen al pasar a un portón de más CL (10 % por defecto); ``include_light`` deja en la lista
    los portones marcados como livianos.
    """
    result = case_or_result if isinstance(case_or_result, DesignResult) else run(case_or_result)
    case = result.case
    if case.is_pair:
        raise ValueError(t("el aparejo en pareja no lleva portones"))
    a1 = float(result.doors.required_area.per_door_m2)
    cl1 = float(result.doors.polar.cl)
    weights = _workbook_weights()
    want = {canonical_type(x) or x for x in types} if types else None
    notes: list[str] = []
    seen: set[str] = set()
    evaluated: list[DoorCandidate] = []
    pool: list[tuple[str, str, str | None, bool, Door, tuple[float, float] | None]] = [
        (case.door.id, case.door.name, None, True, case.door, None)
    ]
    for item in load_components("door", brands=brands, region=region, generic_only=generic_only):
        assert isinstance(item, DoorItem)
        pool.append(
            (item.id, item.name, item.brand, item.is_generic, item.to_door(), item.hp_range)
        )
    family = case.net.family or "bottom"  # sin familia: red de fondo, como la A-3
    skipped = 0
    for item_id, name, brand, generic, door, hp_range in pool:
        if item_id in seen:
            continue
        seen.add(item_id)
        typ = canonical_type(door.type)
        if want is not None and typ not in want:
            continue
        if item_id != case.door.id and not _suits_family(typ, family):
            skipped += 1
            continue
        cand = _evaluate(
            item_id,
            name,
            brand,
            generic,
            door,
            hp_range,
            case=case,
            a1=a1,
            cl1=cl1,
            margin=margin,
            weights=weights,
        )
        if cand is not None:
            evaluated.append(cand)
    if skipped:
        notes.append(
            t(
                "{n} portones de otro tipo de pesca descartados: los pelágicos de alta relación "
                "de aspecto (Süberkrüb) son inestables a las velocidades bajas del arrastre de "
                "fondo (Seafish 1993, §2.2.1) y una red pelágica no lleva portones de fondo",
                n=skipped,
            )
        )
    ok = [c for c in evaluated if c.ok and (include_light or c.weight_status != "light")]
    ok.sort(key=lambda c: (c.area_margin, c.id))
    if not ok:
        notes.append(t("ningún portón del catálogo filtrado alcanza la superficie equivalente"))
    notes.append(
        t(
            "superficie requerida por portón {a:.2f} m² con {door} (CL {cl:.2f} a {angle:g}°)",
            a=a1,
            door=case.door.id,
            cl=cl1,
            angle=case.door_attack_angle_deg,
        )
    )
    return DoorSelection(
        required_m2=a1,
        case_door={
            "id": case.door.id,
            "type": case.door.type,
            "area_m2": case.door.area_m2,
            "angle_deg": case.door_attack_angle_deg,
            "cl": cl1,
            "cd": float(result.doors.polar.cd),
            "required_area_m2": a1,
            "ok": bool((case.door.area_m2 or 0.0) >= a1),
        },
        candidates=tuple(ok[:max_results]),
        rejected=len(evaluated) - len(ok),
        margin=margin,
        rules=_rules(),
        notes=tuple(notes),
    )


__all__ = ["DoorCandidate", "DoorSelection", "select_doors"]
