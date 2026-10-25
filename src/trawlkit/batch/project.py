"""Proyección de una red probada a otro buque (Fase 14).

:func:`project_net` agranda o achica una red para un buque de otra potencia:

1. **Escala inicial por semejanza.** Con el mismo mallero, hilo y armado, la superficie de paño
   (y con ella la resistencia de la red) crece con el cuadrado de la escala lineal ``s``, y el tiro
   disponible con la potencia. Para conservar la relación entre los dos,
   ``s₀ = √(P_buque / P_diseño)``, con ``P_diseño`` la potencia media del plano
   (:func:`trawlkit.catalog.design_hp`). El portón se escala igual: superficie ∝ potencia
   (la regla con la que :func:`trawlkit.catalog.catalog_case` dimensiona el portón del plano).
2. **Refinado.** Con el evaluador del optimizador del capítulo 20
   (:class:`trawlkit.optimize.Evaluator`) se busca la **mayor escala** en ``[0,7·s₀; 1,3·s₀]``
   que cumple las restricciones de siempre (tiro con reserva, red abierta, cable y portón) a la
   velocidad del buque o, si no la da, a alguna velocidad entre 2 y 4 kn (entre las escalas
   iguales, la de más área barrida por hora); una bisección afina la escala. Con el objetivo
   ``energy`` se busca en cambio el menor trabajo por m² barrido
   (:func:`trawlkit.optimize.optimise`).
3. **Armado.** :func:`trawlkit.optimize.optimise_components` elige portón, cable, boyas e hilo
   del catálogo de componentes (filtrado por la región del puerto o «sólo genéricos») para la red
   escalada a la velocidad elegida, con la lista de materiales y su costo.
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from trawlkit.batch.fleet import FleetVessel
from trawlkit.catalog import catalog_case, design_hp
from trawlkit.io import Door, NetSpec, Vessel, load_doors, load_net, load_vessels
from trawlkit.model import DesignCase
from trawlkit.optimize import (
    Assembly,
    Evaluation,
    Limits,
    optimise,
    optimise_components,
    scale_door,
    scale_net,
)
from trawlkit.power import FRIDMAN_KF

Objective = Literal["area", "energy", "cost"]

#: Rango del refinado alrededor de la escala por semejanza.
S_RANGE = (0.7, 1.3)
#: Malla del refinado (escalas × velocidades): una corrida del motor por escala.
GRID = (9, 11)
#: Velocidades de arrastre por defecto [kn] cuando el buque no da la suya (2 a 4 kn: el arrastre
#: habitual; más lento, cualquier red «entra» pero no pesca).
V_RANGE = (2.0, 4.0)


@dataclass(frozen=True)
class Projection:
    """Red proyectada a un buque: escala, velocidad, armado, lista de materiales y avisos."""

    vessel: FleetVessel
    base_net: str
    design_hp: float
    s0: float
    evaluation: Evaluation
    net: NetSpec
    assembly: Assembly | None
    notes: tuple[str, ...] = ()
    engine_runs: int = 0
    case: DesignCase | None = field(default=None, repr=False, compare=False)
    """Caso final (red escalada con el armado elegido), para el plano y el informe."""

    @property
    def s(self) -> float:
        """Escala elegida."""
        return self.evaluation.s

    @property
    def feasible(self) -> bool:
        """Cumple las restricciones del optimizador y del armado."""
        if self.assembly is not None:
            return self.assembly.feasible
        return self.evaluation.feasible

    @property
    def failed(self) -> list[str]:
        """Descripción de las restricciones que no se cumplen."""
        cons = self.assembly.constraints if self.assembly else self.evaluation.constraints
        return [c.description for c in cons if not c.ok]

    def summary(self) -> dict[str, Any]:
        """Una fila del resumen del lote."""
        ev = self.assembly.evaluation if self.assembly else self.evaluation
        a = self.assembly
        comps = a.components() if a else {}
        return {
            "row": self.vessel.row,
            "vessel": self.vessel.vessel.name,
            "vessel_id": self.vessel.vessel.id,
            "bhp": self.vessel.vessel.bhp,
            "base_net": self.base_net,
            "design_hp": self.design_hp,
            "s0": round(self.s0, 4),
            "s": round(self.s, 4),
            "net_id": self.net.id,
            "speed_kn": round(ev.v_kn, 3),
            "feasible": self.feasible,
            "failed": self.failed,
            "demand_kgf": ev.demand_kgf,
            "available_kgf": ev.available_kgf,
            "thrust_margin": ev.thrust_margin,
            "ah_m": ev.ah_m,
            "av_m": ev.av_m,
            "area_rate_m2_h": ev.area_rate_m2_h,
            "energy_kgf_m_per_m2": ev.energy_kgf_m_per_m2,
            "headrope_m": self.evaluation.headrope_m,
            "footrope_m": self.evaluation.footrope_m,
            "door": comps.get("door"),
            "door_area_m2": ev.door_area_m2,
            "warp": comps.get("warp") or ev.warp_id,
            "float": comps.get("float"),
            "float_count": a.float_count if a else None,
            "twine": comps.get("twine"),
            "cost": a.cost if a else None,
            "currency": a.currency if a else None,
            "missing_prices": a.bom.missing_prices if a else None,
        }

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable completa."""
        return {
            "summary": self.summary(),
            "vessel": self.vessel.to_dict(),
            "net": self.net.model_dump(mode="json", exclude_none=True),
            "evaluation": self.evaluation.to_dict(),
            "assembly": None if self.assembly is None else self.assembly.to_dict(),
            "notes": list(self.notes),
            "engine_runs": self.engine_runs,
        }


@dataclass(frozen=True)
class ProjectOptions:
    """Opciones de la proyección comunes a todo el lote."""

    objective: Objective = "area"
    margin: float = 0.1
    assemble: bool = True
    prices: dict[str, Any] = field(default_factory=dict)
    currency: str | None = None
    generic_only: bool = False
    region: str | None = None
    grid: tuple[int, int] = GRID
    max_doors: int = 3
    max_floats: int = 3
    max_twines: int = 2


def _a3_vessel() -> Vessel:
    return next(v for v in load_vessels().vessels if v.id == "fao_a3_150hp")


def _a3_door() -> Door:
    return next(d for d in load_doors().doors if d.id == "fao_flat_wood_a3")


def estimated_runs(options: ProjectOptions) -> int:
    """Corridas del motor por buque (para la guarda de costo del lote)."""
    runs = options.grid[0] + 1
    if options.assemble:
        runs += (
            options.max_floats - 1
        ) + options.max_doors * options.max_floats * options.max_twines
    return runs


def largest_scale(
    case: Any,
    s_bounds: tuple[float, float],
    speeds: Sequence[float],
    limits: Limits,
    n: int,
) -> tuple[Evaluation, int]:
    """Mayor escala factible a alguna de las velocidades ``speeds`` (malla y bisección).

    Entre las evaluaciones factibles de la mayor escala, la de más área barrida por hora. Si
    ninguna es factible, la de menor violación de restricciones.
    """
    from trawlkit.optimize import Evaluator
    from trawlkit.optimize.search import S_STEP

    lim = dataclasses.replace(
        limits,
        v_min_kn=min(limits.v_min_kn, min(speeds)),
        v_max_kn=max(limits.v_max_kn, max(speeds)),
    )
    ev = Evaluator(case, limits=lim, s_step=S_STEP)
    lo, hi = s_bounds

    def at_scale(s: float) -> list[Evaluation]:
        return [ev.at(s, v) for v in speeds]

    def pick(evals: list[Evaluation]) -> Evaluation | None:
        ok = [e for e in evals if e.feasible]
        return max(ok, key=lambda e: e.area_rate_m2_h) if ok else None

    grid = [at_scale(lo + (hi - lo) * i / (n - 1)) for i in range(n)]
    feasible = [(row[0].s, pick(row)) for row in grid if pick(row) is not None]
    if not feasible:
        return min((e for row in grid for e in row), key=lambda e: e.penalty), ev.runs
    s_ok, best = max(feasible, key=lambda t: t[0])
    assert best is not None
    above = [row[0].s for row in grid if row[0].s > s_ok]
    if above:
        a, b = s_ok, min(above)
        for _ in range(4):
            mid = ev.quantise(0.5 * (a + b))
            if mid <= a or mid >= b:
                break
            e = pick(at_scale(mid))
            if e is not None:
                a, best = mid, e
            else:
                b = mid
    return best, ev.runs


def project_net(
    net: str | NetSpec, fv: FleetVessel, options: ProjectOptions | None = None
) -> Projection:
    """Proyecta la red ``net`` al buque ``fv`` (ver el docstring del módulo)."""
    opt = options or ProjectOptions()
    spec = load_net(net) if isinstance(net, str) else net
    vessel = fv.vessel
    notes: list[str] = list(fv.notes)
    p_design = design_hp(spec)
    s0 = math.sqrt(vessel.bhp / p_design)
    notes.append(
        f"escala por semejanza s₀ = √({vessel.bhp:g} / {p_design:g}) = {s0:.3f} "
        "(superficie de paño ∝ potencia)"
    )
    overrides: dict[str, Any] = {}
    if fv.fishing_depth_m is not None:
        overrides["depth_m"] = float(fv.fishing_depth_m)
    if fv.seabed:
        overrides["seabed"] = fv.seabed
    if spec.vessel_hp is None:
        # Red sin potencia de diseño (la A-3 del libro): el caso del libro, 150 hp y su portón.
        base = DesignCase(spec, _a3_vessel(), _a3_door(), **overrides)
        notes.append("red sin potencia de diseño: caso base del libro (buque y portón de la A-3)")
    else:
        base = catalog_case(spec, **overrides).case
        notes += [f"caso base: {a}" for a in base.assumptions]
    prop = vessel.propeller if vessel.propeller in FRIDMAN_KF else base.ft_propeller
    region = fv.region or opt.region
    generic = fv.generic_only or opt.generic_only
    changes: dict[str, Any] = {
        "vessel": vessel,
        "class_vessels": (),
        "ft_propeller": prop,
        "component_region": region,
        "generic_only": generic,
    }
    if not base.is_pair and base.door.area_m2 and abs(vessel.bhp - p_design) > 1e-9:
        changes["door"] = scale_door(base.door, float(base.door.area_m2) * vessel.bhp / p_design)
    case = dataclasses.replace(base, **changes)

    runs = 0
    if fv.speed_kn is not None:
        speeds = [float(fv.speed_kn)]
        v_bounds = (max(0.5, speeds[0] - 0.05), speeds[0] + 0.05)
    else:
        speeds = [V_RANGE[0] + 0.25 * i for i in range(int((V_RANGE[1] - V_RANGE[0]) / 0.25) + 1)]
        v_bounds = V_RANGE
    grid = opt.grid
    s_bounds = (S_RANGE[0] * s0, S_RANGE[1] * s0)
    lim = Limits(margin=opt.margin, v_min_kn=V_RANGE[0], v_max_kn=V_RANGE[1])
    if opt.objective == "energy":
        res = optimise(
            case,
            objective="energy",
            bounds=(s_bounds, v_bounds),
            refine=False,
            grid=grid,
            limits=lim,
        )
        best = res.best
        runs += res.engine_runs
    else:
        best, used = largest_scale(case, s_bounds, speeds, lim, opt.grid[0])
        runs += used
    if best.feasible and best.s >= s_bounds[1] - 0.01:
        notes.append(
            "la escala llegó al tope del rango (1,3·s₀): el buque podría con una red mayor"
        )
    if not best.feasible:
        notes.append("ninguna escala de la malla cumple todas las restricciones")
    scaled = scale_net(spec, best.s)
    scaled = scaled.model_copy(update={"name": f"{spec.name} × {best.s:.2f} para {vessel.name}"})
    assembly: Assembly | None = None
    final = dataclasses.replace(case, net=scaled)
    if opt.assemble:
        final = dataclasses.replace(final, float_count=None)
        comp_obj = {"area": "drag", "energy": "efficiency", "cost": "cost"}[opt.objective]
        try:
            ca = optimise_components(
                final,
                comp_obj,
                speed_kn=best.v_kn,
                prices=opt.prices,
                currency=opt.currency,
                limits=Limits(margin=opt.margin),
                max_doors=opt.max_doors,
                max_floats=opt.max_floats,
                max_twines=opt.max_twines,
                n_alternatives=0,
            )
            assembly = ca.best
            runs += ca.evaluated
            final = _with_assembly(final, assembly, ca)
            notes += list(ca.notes)
        except ValueError as exc:
            notes.append(f"armado con componentes: {exc}")
    return Projection(
        vessel=fv,
        base_net=spec.id,
        design_hp=p_design,
        s0=s0,
        evaluation=best,
        net=scaled,
        assembly=assembly,
        notes=tuple(notes),
        engine_runs=runs,
        case=final,
    )


def _with_assembly(case: DesignCase, a: Assembly, opt_result: Any) -> DesignCase:
    """Caso con los componentes del armado (portón, cable, boyas, hilo)."""
    from trawlkit.components import DoorItem, get_component

    changes: dict[str, Any] = {
        "warp_id": a.warp_id,
        "float_id": a.float_id,
        "float_count": a.float_count,
        "twine_id": a.twine_id,
        "warp_design_speed_kn": a.evaluation.v_kn,
        "speeds_kn": tuple(sorted({*case.speeds_kn, round(a.evaluation.v_kn, 6)})),
    }
    if a.door_id != case.door.id:
        item = get_component("door", a.door_id)
        assert isinstance(item, DoorItem)
        changes["door"] = item.to_door()
    return dataclasses.replace(case, **changes)


__all__ = [
    "GRID",
    "S_RANGE",
    "V_RANGE",
    "ProjectOptions",
    "Projection",
    "estimated_runs",
    "project_net",
]
