"""Armado con componentes del catálogo (Fase 13): portón, cable, boyas e hilo de la red.

:func:`optimise_components` busca en una grilla discreta sobre los componentes del catálogo
(:mod:`trawlkit.components`), filtrados por marca, región o «sólo genéricos»:

* **Portón**: los del rango de potencia del buque y los de superficie cercana a la requerida
  por el caso base (Port!F215), los ``max_doors`` más cercanos, más el del caso.
* **Boyas**: las que aguantan la profundidad del caso, de diámetros cercanos a 200 mm; el número
  de boyas lo da el motor para la flotación requerida (Flot!F72:F82).
* **Hilo** de los paños (salvo el copo): el del plano y los ``max_twines`` más delgados cuya
  rotura llega al 90 % de la del hilo del plano (el de igual material y diámetro más cercano).
* **Cable**: el más delgado del catálogo filtrado que cumple el diámetro y la rotura a la
  velocidad de trabajo (:class:`~trawlkit.optimize.evaluate.Evaluator`).

Cada armado se evalúa a la velocidad ``speed_kn`` (si no se da, a la mejor de la malla de
0,05 kn entre ``v_min_kn`` y ``v_max_kn``: la factible de menor R_T o de menor R_T/AH, según el
objetivo; para ``cost``, la de menor R_T/AH) con las restricciones del optimizador (tiro,
red abierta, cable, portón, velocidad) más la profundidad de las boyas y la rotura del hilo, y se
ordena por el objetivo:

* ``drag``: mínima resistencia total R_T [kgf];
* ``efficiency``: mínimo trabajo por m² barrido R_T/AH (máxima área barrida por litro);
* ``cost``: mínimo costo de la lista de materiales en ``currency`` (:mod:`trawlkit.cost`); un
  armado con menos precios faltantes va antes, porque un precio faltante no es cero.

Una corrida del motor por armado (≈ 0,1 s): con los valores por defecto son a lo sumo
5 × 4 × 4 = 80 corridas.
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import product
from typing import Any

from trawlkit.components import (
    ComponentBase,
    DoorItem,
    FloatItem,
    Price,
    TwineItem,
    get_component,
    load_components,
)
from trawlkit.cost import BillOfMaterials, bill_of_materials
from trawlkit.i18n import N_, t
from trawlkit.io import Door
from trawlkit.io.schema import Section
from trawlkit.model import DesignCase, _case_warps, component_filters, run
from trawlkit.optimize.evaluate import Constraint, Evaluation, Evaluator, Limits, _constraint

#: Objetivos del armado: nombre → descripción.
COMPONENT_OBJECTIVES = {
    "drag": N_("mínima resistencia total R_T"),
    "efficiency": N_("mínimo R_T/AH (máxima área barrida por litro)"),
    "cost": N_("mínimo costo de la lista de materiales"),
}

#: Diámetro de boya de referencia para elegir candidatas [mm] (el del libro, Flot!F70).
REFERENCE_FLOAT_MM = 200.0

#: Fracción de la rotura del hilo del plano que debe alcanzar un hilo candidato.
TWINE_STRENGTH_RATIO = 0.9


@dataclass(frozen=True)
class Assembly:
    """Un armado evaluado: componentes, evaluación, restricciones extra y lista de materiales."""

    door_id: str
    float_id: str | None
    float_count: int | None
    twine_id: str | None
    warp_id: str | None
    evaluation: Evaluation
    extra_constraints: tuple[Constraint, ...]
    bom: BillOfMaterials
    cost: float | None
    """Costo total en la moneda pedida (``None`` si no hay precios en esa moneda)."""
    currency: str | None
    feasible: bool
    penalty: float
    generic: bool
    """Todos los componentes elegidos son genéricos."""

    @property
    def constraints(self) -> tuple[Constraint, ...]:
        """Restricciones del optimizador más las del armado."""
        return (*self.evaluation.constraints, *self.extra_constraints)

    def components(self) -> dict[str, str | None]:
        """Ids de los componentes elegidos."""
        return {
            "door": self.door_id,
            "warp": self.warp_id,
            "float": self.float_id,
            "twine": self.twine_id,
        }

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        ev = self.evaluation
        return {
            "components": self.components(),
            "float_count": self.float_count,
            "speed_kn": ev.v_kn,
            "demand_kgf": ev.demand_kgf,
            "available_kgf": ev.available_kgf,
            "thrust_margin": ev.thrust_margin,
            "net_drag_kgf": ev.net_drag_kgf,
            "ah_m": ev.ah_m,
            "av_m": ev.av_m,
            "area_rate_m2_h": ev.area_rate_m2_h,
            "energy_kgf_m_per_m2": ev.energy_kgf_m_per_m2,
            "door_area_m2": ev.door_area_m2,
            "door_required_m2": ev.door_required_m2,
            "constraints": [c.to_dict() for c in self.constraints],
            "feasible": self.feasible,
            "penalty": self.penalty,
            "generic": self.generic,
            "cost": self.cost,
            "currency": self.currency,
            "missing_prices": self.bom.missing_prices,
            "bom": self.bom.to_dict(),
        }


@dataclass(frozen=True)
class ComponentOptimization:
    """Resultado de :func:`optimise_components`."""

    best: Assembly
    alternatives: tuple[Assembly, ...]
    """Siguientes armados factibles, más uno genérico si el mejor no lo es."""
    objective: str
    feasible: bool
    evaluated: int
    candidates: dict[str, list[str | None]]
    settings: dict[str, Any]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "best": self.best.to_dict(),
            "alternatives": [a.to_dict() for a in self.alternatives],
            "objective": self.objective,
            "feasible": self.feasible,
            "evaluated": self.evaluated,
            "candidates": self.candidates,
            "settings": self.settings,
            "notes": list(self.notes),
        }


def _filters(case: DesignCase) -> dict[str, Any]:
    return component_filters(case) or {}


def _door_candidates(
    case: DesignCase, required_m2: float, ids: Sequence[str] | None, n: int
) -> list[Door]:
    if ids is not None:
        out = []
        for i in ids:
            item = get_component("door", i)
            assert isinstance(item, DoorItem)
            out.append(item.to_door())
        return out
    hp = float(case.vessel.bhp)
    pool: list[tuple[float, Door]] = []
    for item in load_components("door", **_filters(case)):
        assert isinstance(item, DoorItem)
        door = item.to_door()
        area = float(door.area_m2 or 0.0)
        in_hp = item.hp_range is not None and (
            0.75 * item.hp_range[0] <= hp <= 1.25 * item.hp_range[1]
        )
        in_area = required_m2 * 0.9 <= area <= required_m2 * 2.0
        if (in_hp or in_area) and door.id != case.door.id:
            pool.append((abs(area - 1.1 * required_m2), door))
    pool.sort(key=lambda t: (t[0], t[1].id))
    return [case.door, *(d for _, d in pool[: max(n - 1, 0)])]


def _float_candidates(case: DesignCase, ids: Sequence[str] | None, n: int) -> list[str | None]:
    if ids is not None:
        return list(ids)
    # Una boya por diámetro (la de mayor flotación), para que las candidatas sean distintas.
    by_diameter: dict[float, FloatItem] = {}
    for item in load_components("float", **_filters(case)):
        assert isinstance(item, FloatItem)
        if case.depth_m is not None and item.max_depth_m is not None:
            if item.max_depth_m < case.depth_m:
                continue
        prev = by_diameter.get(item.diameter_mm)
        if prev is None or item.buoyancy_kgf > prev.buoyancy_kgf:
            by_diameter[item.diameter_mm] = item
    pool = list(by_diameter.values())
    pool.sort(key=lambda f: (abs(f.diameter_mm - REFERENCE_FLOAT_MM), f.id))
    return [None, *(f.id for f in pool[: max(n - 1, 0)])]


def _plan_twine(case: DesignCase) -> tuple[str | None, float | None]:
    """Material y diámetro del hilo del plano (primer paño que no es el copo)."""
    panels = [p for p in case.net.panels if p.section is not Section.CODEND] or case.net.panels
    p = panels[0]
    return p.material, p.twine_diameter_mm


def _reference_twine_kgf(case: DesignCase) -> float | None:
    material, diameter = _plan_twine(case)
    if material is None or diameter is None:
        return None
    same = [
        t
        for t in load_components("twine")
        if isinstance(t, TwineItem) and t.material == material and t.breaking_load_kgf
    ]
    if not same:
        return None
    ref = min(same, key=lambda t: abs(t.diameter_mm - float(diameter)))
    return float(ref.breaking_load_kgf or 0.0) * (float(diameter) / ref.diameter_mm) ** 2


def _twine_candidates(
    case: DesignCase, ids: Sequence[str] | None, n: int, ref_kgf: float | None
) -> list[str | None]:
    if ids is not None:
        return list(ids)
    if ref_kgf is None:
        return [None]
    pool = [
        t
        for t in load_components("twine", **_filters(case))
        if isinstance(t, TwineItem)
        and t.breaking_load_kgf is not None
        and t.breaking_load_kgf >= TWINE_STRENGTH_RATIO * ref_kgf
    ]
    pool.sort(key=lambda t: (t.diameter_mm, t.id))
    return [None, *(t.id for t in pool[: max(n - 1, 0)])]


def _is_generic(kind: str, item_id: str | None) -> bool:
    if item_id is None:
        return True
    try:
        item: ComponentBase = get_component(kind, item_id)
    except KeyError:
        return True  # componente del plano o del libro, no de un fabricante
    return item.brand is None or item.brand in ("Moscuzza", "Trawlex")


def _at_best_speed(ev: Evaluator, objective: str, speed_kn: float | None) -> Evaluation:
    """Evaluación a ``speed_kn`` o a la mejor velocidad de la malla (ver el docstring)."""
    if speed_kn is not None:
        return ev.at(1.0, float(speed_kn))
    lim = ev.limits
    speeds = [float(v) for v in ev.speeds if lim.v_min_kn - 1e-9 <= v <= lim.v_max_kn + 1e-9]
    evals = [ev.at(1.0, v) for v in speeds]

    def score(e: Evaluation) -> tuple[float, float, float]:
        value = e.demand_kgf if objective == "drag" else e.energy_kgf_m_per_m2
        return (0.0 if e.feasible else 1.0, e.penalty, value)

    return min(evals, key=score)


def optimise_components(
    base_case: DesignCase,
    objective: str = "drag",
    *,
    speed_kn: float | None = None,
    doors: Sequence[str] | None = None,
    floats: Sequence[str] | None = None,
    twines: Sequence[str] | None = None,
    prices: Mapping[str, Price | Mapping[str, Any]] | None = None,
    currency: str | None = None,
    limits: Limits | None = None,
    max_doors: int = 5,
    max_floats: int = 4,
    max_twines: int = 4,
    n_alternatives: int = 3,
) -> ComponentOptimization:
    """Armado recomendado del caso con componentes del catálogo (ver el docstring del módulo).

    Los filtros (``component_brands``, ``component_region``, ``generic_only``) se toman del caso.
    ``doors``/``floats``/``twines`` fijan la lista de candidatos por id (``None`` = automática).
    """
    if objective not in COMPONENT_OBJECTIVES:
        raise ValueError(
            t(
                "objetivo desconocido: {name!r} ({names})",
                name=objective,
                names=sorted(COMPONENT_OBJECTIVES),
            )
        )
    lim = limits or Limits()
    v_base = float(base_case.warp_design_speed_kn if speed_kn is None else speed_kn)
    v_base = min(max(v_base, lim.v_min_kn), lim.v_max_kn)
    # Sin filtros, todos los cables publicados del catálogo de componentes (no sólo los del libro).
    warps = _case_warps(base_case) or [w.model_dump() for w in load_components("wire")]
    base_eval = Evaluator(base_case, limits=lim, warps=warps).at(1.0, v_base)
    notes: list[str] = []

    door_list = _door_candidates(base_case, base_eval.door_required_m2, doors, max_doors)
    float_list = _float_candidates(base_case, floats, max_floats)
    ref_kgf = _reference_twine_kgf(base_case)
    twine_list = _twine_candidates(base_case, twines, max_twines, ref_kgf)
    if ref_kgf is None and twines is None:
        notes.append(t("hilo: el plano no da material y diámetro; se usa el del plano"))

    float_counts: dict[str | None, int | None] = {None: base_case.float_count}
    for fid in float_list:
        if fid is not None:
            res = run(dataclasses.replace(base_case, float_id=fid, float_count=None))
            float_counts[fid] = int(res.floats.count)

    assemblies: list[Assembly] = []
    for door, fid, tid in product(door_list, float_list, twine_list):
        case = dataclasses.replace(
            base_case, door=door, float_id=fid, float_count=float_counts[fid], twine_id=tid
        )
        try:
            evaluator = Evaluator(case, limits=lim, warps=warps)
            ev = _at_best_speed(evaluator, objective, speed_kn)
        except (KeyError, ValueError) as exc:
            notes.append(
                t(
                    "{door} / {float} / {twine}: no se puede calcular ({exc})",
                    door=door.id,
                    float=fid,
                    twine=tid,
                    exc=exc,
                )
            )
            continue
        result = evaluator.curves(1.0).result
        extra: list[Constraint] = []
        if fid is not None and case.depth_m is not None:
            item = get_component("float", fid)
            assert isinstance(item, FloatItem)
            if item.max_depth_m is not None:
                extra.append(
                    _constraint(
                        "float_depth",
                        item.max_depth_m,
                        case.depth_m,
                        None,
                        t("profundidad máxima de la boya ≥ profundidad de pesca"),
                    )
                )
        if tid is not None and ref_kgf is not None:
            tw = get_component("twine", tid)
            assert isinstance(tw, TwineItem)
            if tw.breaking_load_kgf is not None:
                extra.append(
                    _constraint(
                        "twine",
                        tw.breaking_load_kgf,
                        TWINE_STRENGTH_RATIO * ref_kgf,
                        None,
                        t(
                            "rotura del hilo ≥ {k:g}·la del hilo del plano",
                            k=TWINE_STRENGTH_RATIO,
                        ),
                    )
                )
        bom = bill_of_materials(result, prices, warp_id=ev.warp_id)
        cur = currency or next(iter(bom.totals), None)
        cost = bom.totals.get(cur) if cur else None
        feasible = ev.feasible and all(c.ok for c in extra)
        assemblies.append(
            Assembly(
                door_id=door.id,
                float_id=fid,
                float_count=float_counts[fid],
                twine_id=tid,
                warp_id=ev.warp_id,
                evaluation=ev,
                extra_constraints=tuple(extra),
                bom=bom,
                cost=cost,
                currency=cur,
                feasible=feasible,
                penalty=ev.penalty + sum(c.violation for c in extra),
                generic=all(
                    _is_generic(k, i)
                    for k, i in (
                        ("door", door.id),
                        ("float", fid),
                        ("twine", tid),
                        ("wire", ev.warp_id),
                    )
                ),
            )
        )
    if not assemblies:
        raise ValueError(t("ningún armado del catálogo se puede calcular"))

    def key(a: Assembly) -> tuple[float, ...]:
        ev = a.evaluation
        if objective == "drag":
            score = ev.demand_kgf
        elif objective == "efficiency":
            score = ev.energy_kgf_m_per_m2
        else:
            score = math.inf if a.cost is None else a.cost
            return (0.0 if a.feasible else 1.0, a.penalty, a.bom.missing_prices, score)
        return (0.0 if a.feasible else 1.0, a.penalty, score)

    ranked = sorted(assemblies, key=key)
    best = ranked[0]
    alts = [a for a in ranked[1:] if a.feasible][:n_alternatives]
    if not best.generic:
        gen = next((a for a in ranked if a.generic and a.feasible), None)
        if gen is not None and gen not in alts:
            alts.append(gen)
    if not best.feasible:
        notes.append(t("ningún armado cumple todas las restricciones; se da el de menor violación"))
    return ComponentOptimization(
        best=best,
        alternatives=tuple(alts),
        objective=objective,
        feasible=best.feasible,
        evaluated=len(assemblies),
        candidates={
            "door": [d.id for d in door_list],
            "float": list(float_list),
            "twine": list(twine_list),
        },
        settings={
            "speed_kn": speed_kn,
            "limits": lim.to_dict(),
            "filters": component_filters(base_case),
            "currency": currency,
        },
        notes=tuple(notes),
    )


__all__ = ["COMPONENT_OBJECTIVES", "Assembly", "ComponentOptimization", "optimise_components"]
