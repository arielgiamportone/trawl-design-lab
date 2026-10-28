"""API de la simulación cuasiestática: :func:`simulate`, :func:`sweep` y :class:`SimResult`."""

from __future__ import annotations

import dataclasses
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import numpy.typing as npt

from trawlkit.i18n import t
from trawlkit.io.schema import NetSpec
from trawlkit.model import DesignCase, DesignResult, run
from trawlkit.rigging import door_polar_table
from trawlkit.sim.mesh import NetModel, Rigging, build_model, interpolate_shape
from trawlkit.sim.meshstate import MeshState, mesh_state
from trawlkit.sim.scenario import Scenario
from trawlkit.sim.solver import G, Params, RelaxResult, net_mask, relax

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.int64]

KNOT_MS = 1852.0 / 3600.0

#: Coeficientes hidrodinámicos por defecto del hilo (cilindro): normal y tangencial.
DEFAULT_CN = 1.4
DEFAULT_CT = 0.08
#: Coeficiente de rozamiento red–fondo (fondo intermedio).
DEFAULT_MU = 0.5
#: Energía (A VERIFICAR): rendimiento de remolque (tiro × velocidad / potencia al freno),
#: consumo específico del motor diésel [kg/kWh] y densidad del gasoil [kg/L].
TOWING_EFFICIENCY = 0.5
SFC_KG_KWH = 0.22
DIESEL_KG_L = 0.84
KW_PER_HP = 0.7457

#: Resolución por defecto (divisiones nominales por panel).
DEFAULT_RESOLUTION = 8
#: Módulo de flexión del hilo para la rigidez de apertura de la malla [Pa] (A VERIFICAR: da
#: EI ≈ 2·10⁻³ N·m² para un hilo de 4 mm, del orden de la resistencia a la apertura medida por
#: Sala et al. 2007). Se activa sola si la red tiene paños T90 o de malla cuadrada.
DEFAULT_MESH_BENDING_PA = 1.6e8

CaseLike = DesignResult | DesignCase | NetSpec


@dataclass(frozen=True, eq=False)
class SimResult:
    """Forma de equilibrio de la red a una velocidad.

    Coordenadas en m: ``x`` hacia popa (la red avanza hacia −x), ``y`` lateral, ``z`` sobre el
    fondo. Los portones (puntos de remolque) están en ``x = 0``, ``y = ±DP/2``.
    """

    speed_kn: float
    nodes: FloatArray
    triangles: IntArray
    twine_tension_n: FloatArray
    bars: IntArray
    bar_kind: tuple[str, ...]
    bar_tension_n: FloatArray
    headrope: IntArray
    footrope: IntArray
    grid_lines: tuple[tuple[str, IntArray], ...]
    float_nodes: IntArray
    wing_tips_upper: tuple[int, int]
    wing_tips_lower: tuple[int, int]
    ah_m: float
    ah_lower_m: float
    av_m: float
    headrope_height_m: float
    footrope_height_m: float
    mouth_area_m2: float
    hydro_drag_kgf: float
    friction_kgf: float
    drag_kgf: float
    drag_jitter_kgf: float
    bridle_pull_kgf: float
    bridle_tension_kgf: dict[str, float]
    door_spread_m: float
    net_length_m: float
    converged: bool
    iterations: int
    residual: float
    force_balance: float
    runtime_s: float
    params: dict[str, float] = field(default_factory=dict)
    #: Escenario del lance (captura, fondo, portones acoplados); vacío = simulador básico.
    scenario: dict[str, Any] = field(default_factory=dict)
    #: Zona de la captura: largo, volumen, área frontal, diámetro máximo (vacío sin captura).
    catch: dict[str, float] = field(default_factory=dict)
    catch_drag_kgf: float = 0.0
    door_friction_kgf: float = 0.0
    #: Tiro total del arte en el buque (componente x de los dos cables) [kgf]; 0 = portones fijos.
    towing_pull_kgf: float = 0.0
    warp_tension_kgf: float = 0.0  # tensión de cada cable en el portón [kgf]
    door_positions_m: tuple[tuple[float, float, float], ...] = ()
    #: Operación: velocidades, cables, energía y huella (ver :func:`operation_outputs`).
    operation: dict[str, Any] = field(default_factory=dict)
    #: Ensuciamiento de cada triángulo (0–1; vacío = red limpia).
    fouling_tri: FloatArray = field(default_factory=lambda: np.zeros(0))
    #: Forma de la malla de cada triángulo (zoom por malla, selectividad).
    mesh: MeshState | None = None
    #: Ángulo de ataque y coeficientes de los portones acoplados (Fase 19.3): modo («fixed» o
    #: «dynamic»), ángulo, CL, CD, ángulos del cable y de la patente; vacío = portones fijos.
    door_attack: dict[str, Any] = field(default_factory=dict)
    #: Tangones, gemelo o vara (Fase 19.5): aparejo, redes, desplazamiento lateral de cada copia
    #: de la red simulada (para la vista 3D) y arrastre de todas las redes; vacío = una red.
    rig: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, *, geometry: bool = True) -> dict[str, Any]:
        """Representación serializable (``geometry=False`` omite nodos y conectividad)."""
        out: dict[str, Any] = {
            "speed_kn": self.speed_kn,
            "ah_m": self.ah_m,
            "ah_lower_m": self.ah_lower_m,
            "av_m": self.av_m,
            "headrope_height_m": self.headrope_height_m,
            "footrope_height_m": self.footrope_height_m,
            "mouth_area_m2": self.mouth_area_m2,
            "hydro_drag_kgf": self.hydro_drag_kgf,
            "friction_kgf": self.friction_kgf,
            "drag_kgf": self.drag_kgf,
            "drag_jitter_kgf": self.drag_jitter_kgf,
            "bridle_pull_kgf": self.bridle_pull_kgf,
            "bridle_tension_kgf": dict(self.bridle_tension_kgf),
            "door_spread_m": self.door_spread_m,
            "net_length_m": self.net_length_m,
            "converged": self.converged,
            "iterations": self.iterations,
            "residual": self.residual,
            "force_balance": self.force_balance,
            "runtime_s": self.runtime_s,
            "params": dict(self.params),
            "scenario": dict(self.scenario),
            "catch": dict(self.catch),
            "catch_drag_kgf": self.catch_drag_kgf,
            "door_friction_kgf": self.door_friction_kgf,
            "towing_pull_kgf": self.towing_pull_kgf,
            "warp_tension_kgf": self.warp_tension_kgf,
            "door_positions_m": [list(d) for d in self.door_positions_m],
            "operation": dict(self.operation),
            "door_attack": dict(self.door_attack),
        }
        if self.rig:
            out["rig"] = dict(self.rig)
        if geometry:
            out.update(
                nodes=self.nodes.tolist(),
                triangles=self.triangles.tolist(),
                twine_tension_n=self.twine_tension_n.tolist(),
                bars=self.bars.tolist(),
                bar_kind=list(self.bar_kind),
                bar_tension_n=self.bar_tension_n.tolist(),
                headrope=self.headrope.tolist(),
                footrope=self.footrope.tolist(),
                grid_lines=[[pl, idx.tolist()] for pl, idx in self.grid_lines],
                float_nodes=self.float_nodes.tolist(),
                wing_tips_upper=list(self.wing_tips_upper),
                wing_tips_lower=list(self.wing_tips_lower),
                fouling_tri=self.fouling_tri.tolist(),
            )
            if self.mesh is not None:
                out["mesh"] = self.mesh.to_dict()
        if self.mesh is not None:
            out["mesh_summary"] = self.mesh.summary()
        return out


# ---------------------------------------------------------------------------------------------
# Datos de entrada
# ---------------------------------------------------------------------------------------------


def _float_positions(
    count: int,
    wing_m: float,
    bosom_m: float,
    on_bosom: int | None = None,
    front: int | None = None,
    spacing_front_m: float | None = None,
    spacing_rest_m: float | None = None,
) -> tuple[float, ...]:
    """Posiciones de las boyas sobre la lima, en m desde el centro (+ = ala derecha).

    Con la distribución selectiva del motor (Flot!F103:K112): ``on_bosom`` boyas en la bocana a
    ``L_bocana/3``; en cada ala, ``front − 1`` boyas cada ``spacing_front_m`` desde la bocana y el
    resto cada ``spacing_rest_m`` a partir del primer quinto. Si los números no cierran con
    ``count`` (o no hay distribución) se reparten parejas a lo largo de la lima.
    """
    if on_bosom is not None and front is not None and spacing_front_m and spacing_rest_m:
        per_wing = (count - on_bosom) // 2
        bosom = [(-(on_bosom - 1) / 2.0 + k) * bosom_m / 3.0 for k in range(on_bosom)]
        wing = [bosom_m / 2.0 + spacing_front_m * k for k in range(1, front)]
        start = bosom_m / 2.0 + spacing_front_m * (front - 1)
        rest = per_wing - len(wing)
        wing += [start + spacing_rest_m * k for k in range(1, rest + 1)]
        if (
            2 * per_wing + on_bosom == count
            and len(wing) == per_wing
            and max(wing, default=0.0) < bosom_m / 2.0 + wing_m
        ):
            return tuple(sorted([*bosom, *wing, *(-w for w in wing)]))
    total = 2.0 * wing_m + bosom_m
    return tuple(-total / 2.0 + total * (k + 0.5) / count for k in range(count))


def _rope_pieces(spec: NetSpec, which: str) -> tuple[float, float] | None:
    """(ala, bocana) de la relinga según el plano, si la spec los trae (redes del catálogo)."""
    rope = getattr(spec, which)
    extra = (rope.model_extra or {}) if rope is not None else {}
    wing, bosom = extra.get("wing_m"), extra.get("bosom_m")
    if wing is None or bosom is None:
        return None
    return float(wing), float(bosom)


def rigging_from_result(r: DesignResult, door_spread_m: float | None = None) -> Rigging:
    """Aparejo de la red estándar a partir del resultado del motor (modo del caso).

    Las relingas salen del motor (largo corregido de ala y bocana), salvo que la spec traiga los
    largos del plano (``wing_m`` y ``bosom_m`` de la relinga, redes del catálogo). La rigidez
    axial (Fase 19.1) sale del material de cada cabo y del cable de remolque elegido.
    """
    dims = r.dimensions.std
    fl = r.floats
    dist = fl.distribution
    diam = float(fl.diameter_mm)
    cat_d = list(fl.catalogue_diameters_mm)
    if diam in cat_d:
        buoy = float(fl.catalogue_buoyancy_kgf[cat_d.index(diam)])
    elif r.case.net.floats and r.case.net.floats.buoyancy_kgf_each:
        buoy = float(r.case.net.floats.buoyancy_kgf_each)
    else:
        buoy = float(fl.flotation_total_kgf) / max(fl.count, 1)
    bd = r.ballast.distribution_max
    head = _rope_pieces(r.case.net, "headrope") or (
        float(dims.headrope.wing_corrected_m),
        float(dims.headrope.bosom_corrected_m),
    )
    foot = _rope_pieces(r.case.net, "footrope") or (
        float(dims.footrope.wing_corrected_m),
        float(dims.footrope.bosom_corrected_m),
    )
    warp_core, warp_ea = _warp_stiffness(r)
    mr = r.multirig
    beam = mr is not None and mr.kind == "beam"
    if beam:
        # Vara: sin boyas (la lima va a la vara); las puntas de ala quedan fijas en la vara.
        assert mr is not None
        return dataclasses.replace(
            rigging_from_result(dataclasses.replace(r, multirig=None), door_spread_m),
            float_count=0,
            float_buoyancy_kgf=0.0,
            float_positions_m=(),
            beam_height_m=float(mr.vertical_opening_m),
        )
    upper_bridle = float(r.bridles.lengths.upper_m)
    sweeps = float(r.bridles.sweeps_m)
    op = r.spread.shrimp
    if op is not None and op.method == "tijera" and op.bridle_m is not None:
        # Fase 19.7b: con tijera el portón se une a las alas con cañas cortas (una superior y
        # una inferior), sin patentes (IAT 85/2024, IAT 111/2022).
        upper_bridle, sweeps = float(op.bridle_m), 0.0
    return Rigging(
        door_spread_m=float(r.doors.spread_m if door_spread_m is None else door_spread_m),
        upper_bridle_m=upper_bridle,
        # La cadena de reglaje se ajusta para que brida inferior + cadena = brida superior (es
        # su función). Con el redondeo del libro (17 + 1,71 = 18,71 m) la inferior quedaría
        # 0,71 m más larga que la superior —más de lo que absorbe la punta de ala— y floja.
        lower_bridle_m=upper_bridle,
        sweeps_m=sweeps,
        headrope_wing_m=head[0],
        headrope_bosom_m=head[1],
        footrope_wing_m=foot[0],
        footrope_bosom_m=foot[1],
        headrope_diameter_mm=float(fl.headrope_rope.diameter_mm),
        footrope_diameter_mm=float(r.ballast.footrope_rope.diameter_mm),
        headrope_water_kgf_m=float(fl.headrope_weight_water_kgf) / float(dims.headrope_m),
        footrope_water_kgf_m=float(r.ballast.footrope_weight_water_kgf) / float(dims.footrope_m),
        float_count=int(fl.count),
        float_buoyancy_kgf=buoy,
        float_diameter_mm=diam,
        float_cd=float(np.mean(fl.cd)),
        float_positions_m=_float_positions(
            int(fl.count),
            head[0],
            head[1],
            dist.on_bosom,
            dist.front_fifth,
            dist.spacing_front_fifth_m,
            dist.spacing_remaining_m,
        ),
        ballast_wings_kg=float(bd.wings_kg),
        ballast_bosom_kg=float(bd.bosom_kg),
        ballast_tips_kg=float(bd.adjust_kg),
        door_height_m=float(r.doors.door.height_m or 0.95),
        wire_water_kgf_m=float(r.warps.weight.water_min_kg_m),
        door_area_m2=float(r.doors.door.area_m2 or 1.8),
        door_cl=float(r.doors.polar.cl),
        door_cd=float(r.doors.polar.cd),
        door_weight_water_kgf=_door_water_kgf(r),
        warp_length_m=float(r.warps.warp_m),
        depth_m=float(r.summary()["working_depth_m"] or 40.0),
        gallows_m=float(r.case.gallows_spacing_m),
        warp_diameter_mm=float(r.warps.diameter_mm),
        vessel_bhp=float(r.case.vessel.bhp),
        door_length_m=float(r.doors.door.length_m or 1.9),
        headrope_ea_n=_rope_ea_n(fl.headrope_rope.id, float(fl.headrope_rope.diameter_mm)),
        footrope_ea_n=_rope_ea_n(
            r.ballast.footrope_rope.id, float(r.ballast.footrope_rope.diameter_mm)
        ),
        warp_core=warp_core,
        warp_ea_n=warp_ea,
        door_polar=tuple(
            (float(p.angle_deg), float(p.cl), float(p.cd))
            for p in sorted(door_polar_table(r.doors.door), key=lambda q: q.angle_deg)
        ),
        door_attack_angle_deg=float(r.case.door_attack_angle_deg),
    )


def _rope_ea_n(rope_id: str, diameter_mm: float) -> float | None:
    """EA de una relinga del motor [N] (Fase 19.1); ``None`` = supuesto por defecto (10⁶ N).

    Si el cabo está en el catálogo de componentes se usa :func:`trawlkit.components.
    axial_stiffness` (``ea_kn`` de la ficha, rotura/alargamiento o la relación del material); si
    sólo está en el catálogo del libro, la relación ``EA = k·d²`` de su material.
    """
    from trawlkit.components import RopeItem, axial_stiffness, get_component
    from trawlkit.io import load_catalogue
    from trawlkit.materials import rope_ea_n

    try:
        comp = get_component("rope", rope_id)
    except KeyError:
        comp = None
    if isinstance(comp, RopeItem):
        got = axial_stiffness(comp)
        return None if got is None else got[0] * 1000.0
    for item in load_catalogue("ropes").items:
        if item.get("id") == rope_id:
            return rope_ea_n(str(item.get("material") or ""), diameter_mm)
    return None


def _warp_stiffness(r: DesignResult) -> tuple[str, float | None]:
    """Alma del cable de remolque (``FC``/``IWRC``) y EA del cable elegido por el motor [N].

    Es la del estiramiento del motor (:class:`~trawlkit.rigging.WarpStretch`): ficha del
    componente o módulo efectivo del 6x19 sobre el área nominal.
    """
    from trawlkit.materials import wire_core

    st = r.warps.stretch
    if st is not None:
        return st.core, st.ea_n
    return wire_core(None, r.warps.selection.construction), None


def _door_water_kgf(r: DesignResult) -> float:
    door = r.doors.door
    if door.weight_water_kg:
        return float(door.weight_water_kg)
    coef = (door.model_extra or {}).get("weight_water_coefficient", 0.6)
    return float(door.weight_air_kg or 100.0) * float(coef)


def rigging_from_spec(spec: NetSpec, door_spread_m: float) -> Rigging:
    """Aparejo genérico cuando sólo hay una spec (sin corrida del motor).

    Bridas de 18 m (inferior + cadena igual a la superior), patentes de 25 m, relingas con el
    largo de la spec repartido 45/10/45 % (ala/bocana/ala), lastre de la spec repartido 50 %
    alas, 20 % bocana y 30 % puntas, boyas parejas. ``door_spread_m`` es obligatorio.
    """
    hr = spec.headrope
    fr = spec.footrope
    hl = float(hr.length_m) if hr and hr.length_m else 28.7
    fl_ = float(fr.length_m) if fr and fr.length_m else 1.16 * hl
    fs = spec.floats
    count = int(fs.count) if fs else 12
    each = (
        float(fs.buoyancy_kgf_each)
        if fs and fs.buoyancy_kgf_each
        else (float(fs.total_buoyancy_kgf) / count if fs and fs.total_buoyancy_kgf else 3.0)
    )
    ballast = float(spec.ballast_kg or 0.0)
    return Rigging(
        door_spread_m=door_spread_m,
        upper_bridle_m=18.0,
        lower_bridle_m=18.0,
        sweeps_m=25.0,
        headrope_wing_m=0.45 * hl,
        headrope_bosom_m=0.10 * hl,
        footrope_wing_m=0.45 * fl_,
        footrope_bosom_m=0.10 * fl_,
        headrope_diameter_mm=float(hr.diameter_mm) if hr and hr.diameter_mm else 12.0,
        footrope_diameter_mm=float(fr.diameter_mm) if fr and fr.diameter_mm else 14.0,
        headrope_water_kgf_m=0.087 * (float(hr.weight_kg_per_m or 0.4) if hr else 0.4),
        footrope_water_kgf_m=0.087 * (float(fr.weight_kg_per_m or 0.6) if fr else 0.6),
        float_count=count,
        float_buoyancy_kgf=each,
        float_diameter_mm=float(fs.diameter_mm) if fs else 200.0,
        float_cd=0.5,
        float_positions_m=_float_positions(count, 0.45 * hl, 0.10 * hl),
        ballast_wings_kg=0.5 * ballast,
        ballast_bosom_kg=0.2 * ballast,
        ballast_tips_kg=0.3 * ballast,
    )


def _resolve(
    case_or_spec: CaseLike, door_spread_m: float | None
) -> tuple[NetSpec, Rigging, DesignResult | None]:
    if isinstance(case_or_spec, DesignCase):
        case_or_spec = run(case_or_spec)
    if isinstance(case_or_spec, DesignResult):
        return (
            case_or_spec.case.net,
            rigging_from_result(case_or_spec, door_spread_m),
            case_or_spec,
        )
    if door_spread_m is None:
        raise ValueError(t("con una NetSpec sola hay que indicar door_spread_m"))
    return case_or_spec, rigging_from_spec(case_or_spec, door_spread_m), None


def _float_cd_at(result: DesignResult | None, rig: Rigging, speed_kn: float) -> float:
    if result is None:
        return rig.float_cd
    kn = np.asarray(result.case.speeds_kn, dtype=float)
    cd = np.asarray(result.floats.cd, dtype=float)
    if kn.size != cd.size or kn.size == 0:
        return rig.float_cd
    return float(np.interp(speed_kn, kn, cd))


# ---------------------------------------------------------------------------------------------
# Resultados
# ---------------------------------------------------------------------------------------------


def _shoelace(y: FloatArray, z: FloatArray) -> float:
    return 0.5 * abs(float(np.dot(y, np.roll(z, -1)) - np.dot(z, np.roll(y, -1))))


def _grid_lines(model: NetModel) -> tuple[tuple[str, IntArray], ...]:
    """Polilíneas de la grilla de cada panel (filas y columnas), con su plano."""
    out: list[tuple[str, IntArray]] = []
    for g in model.grids:
        out.extend((g.plane, row) for row in g.nodes)
        out.extend((g.plane, col) for col in g.nodes.T)
    return tuple(out)


def _result(
    model: NetModel,
    rig: Rigging,
    p: Params,
    speed_kn: float,
    relaxed: RelaxResult,
    runtime: float,
    resolution: int,
    scenario: Scenario | None = None,
    ground_kn: float | None = None,
    ff_fouling: FloatArray | None = None,
    catch_fill: FloatArray | None = None,
) -> SimResult:
    x = relaxed.x
    fr = relaxed.forces
    tu, tl = model.wing_tips_upper, model.wing_tips_lower
    net_nodes = net_mask(model)
    hydro = float(fr.hydro_x[net_nodes].sum())
    friction = float(p.mu * fr.reaction[net_nodes].sum())
    doors = list(model.doors)
    mu_door = p.mu if p.mu_door is None else p.mu_door
    door_friction = float(mu_door * fr.reaction[doors].sum()) if model.coupled_doors else 0.0
    towing = 0.0
    warp_t = 0.0
    if model.coupled_doors:
        for k, (b, kind) in enumerate(zip(model.bar, model.bar_kind, strict=True)):
            if kind != "warp":
                continue
            if int(b[1]) in model.fixed.tolist():
                d = x[b[1]] - x[b[0]]
                towing += float(fr.bar_tension[k] * -d[0] / np.linalg.norm(d))
            if int(b[0]) in doors:
                warp_t = max(warp_t, float(fr.bar_tension[k]))
    spread = (
        float(abs(x[doors[0], 1] - x[doors[1], 1])) if model.coupled_doors else rig.door_spread_m
    )
    pull = 0.0
    tension: dict[str, float] = {}
    for k, (b, kind) in enumerate(zip(model.bar, model.bar_kind, strict=True)):
        if kind in ("upper_bridle", "lower_bridle", "sweep", "wing_end"):
            side = "right" if x[b[1], 1] > 0 else "left"
            tension[f"{kind}_{side}"] = float(fr.bar_tension[k]) / G
        if kind in ("upper_bridle", "lower_bridle"):
            d = x[b[1]] - x[b[0]]
            pull += float(fr.bar_tension[k] * d[0] / np.linalg.norm(d))
    loop = np.concatenate([model.headrope, model.footrope[::-1]])
    netting = np.unique(model.tri)
    return SimResult(
        speed_kn=float(speed_kn),
        nodes=x.copy(),
        triangles=model.tri.copy(),
        twine_tension_n=fr.twine_tension.copy(),
        bars=model.bar.copy(),
        bar_kind=model.bar_kind,
        bar_tension_n=fr.bar_tension.copy(),
        headrope=model.headrope.copy(),
        footrope=model.footrope.copy(),
        grid_lines=_grid_lines(model),
        float_nodes=model.float_nodes.copy(),
        wing_tips_upper=tu,
        wing_tips_lower=tl,
        ah_m=float(np.linalg.norm(x[tu[0]] - x[tu[1]])),
        ah_lower_m=float(np.linalg.norm(x[tl[0]] - x[tl[1]])),
        av_m=float(x[model.headrope_centre, 2] - x[model.footrope_centre, 2]),
        headrope_height_m=float(x[model.headrope_centre, 2]),
        footrope_height_m=float(x[model.footrope_centre, 2]),
        mouth_area_m2=_shoelace(x[loop, 1], x[loop, 2]),
        hydro_drag_kgf=hydro / G,
        friction_kgf=friction / G,
        drag_kgf=relaxed.drag_mean / G,
        drag_jitter_kgf=relaxed.drag_std / G,
        bridle_pull_kgf=-pull / G,
        bridle_tension_kgf=tension,
        door_spread_m=spread,
        net_length_m=float(x[netting, 0].max() - x[[*tu, *tl], 0].mean()),
        converged=relaxed.converged,
        iterations=relaxed.iterations,
        residual=relaxed.residual,
        force_balance=relaxed.force_balance,
        runtime_s=runtime,
        params={
            "cn": p.cn,
            "ct": p.ct,
            "mu": p.mu,
            "float_cd": p.float_cd,
            "knot_factor": p.knot_factor,
            "resolution": float(resolution),
            "speed_ms": p.speed_ms,
            "mu_door": mu_door,
            "mesh_bending_pa": p.mesh_bending,
        },
        scenario=_scenario_dict(scenario),
        catch=dict(relaxed.catch),
        catch_drag_kgf=fr.catch_x / G,
        door_friction_kgf=door_friction / G,
        towing_pull_kgf=towing / G,
        warp_tension_kgf=warp_t / G,
        door_positions_m=tuple((float(x[k, 0]), float(x[k, 1]), float(x[k, 2])) for k in doors),
        operation=operation_outputs(
            model,
            rig,
            x,
            fr,
            scenario,
            ground_kn=speed_kn if ground_kn is None else ground_kn,
            water_kn=p.speed_ms / KNOT_MS,
            pull_kgf=towing / G if model.coupled_doors else relaxed.drag_mean / G,
            spread_m=spread,
        ),
        fouling_tri=np.zeros(0) if ff_fouling is None else ff_fouling.copy(),
        mesh=mesh_state(model, x, catch_fill),
        door_attack=_door_attack(model, x, relaxed),
    )


def _door_attack(model: NetModel, x: FloatArray, relaxed: RelaxResult) -> dict[str, Any]:
    """Ángulo de ataque de los portones acoplados (Fase 19.3; vacío con portones fijos).

    Con la polar fija se informa también el ángulo que daría la polar dinámica con la forma
    resuelta (``target_deg``), para ver cuánto se aparta del ángulo del caso.
    """
    if not model.coupled_doors:
        return {}
    if relaxed.door:
        return dict(relaxed.door)
    from trawlkit.sim.doors import calibrate_nw, rig_angles_deg, seafish_attack_angle

    nodes = (int(model.doors[0]), int(model.warp_nodes[0][1]), int(model.junctions[0]))
    b0, g0 = rig_angles_deg(model.x0, *nodes)
    beta, gamma = rig_angles_deg(x, *nodes)
    target = seafish_attack_angle(beta, gamma, calibrate_nw(model.door_angle_deg, b0, g0))
    return {
        "mode": "fixed",
        "angle_deg": model.door_angle_deg,
        "angle_case_deg": model.door_angle_deg,
        "target_deg": target,
        "cl": model.door_cl,
        "cd": model.door_cd,
        "beta_deg": beta,
        "gamma_deg": gamma,
        "beta_ref_deg": b0,
        "gamma_ref_deg": g0,
    }


def operation_outputs(
    model: NetModel,
    rig: Rigging,
    x: FloatArray,
    fr: Any,
    scenario: Scenario | None,
    *,
    ground_kn: float,
    water_kn: float,
    pull_kgf: float,
    spread_m: float,
) -> dict[str, Any]:
    """Velocidades, cables, energía y huella del equilibrio.

    * **Energía**: potencia de remolque ``P = T · v_agua / η`` (``η`` :data:`TOWING_EFFICIENCY`),
      recortada a la del buque; combustible ``P · SFC / ρ_gasoil`` [L/h]; por kg de captura con
      la duración del lance del escenario. Referencia: Parker y Tyedmers (2015).
    * **Huella** (Eigaard et al. 2016): ancho barrido = separación de portones; ancho en contacto
      con el fondo = burlón apoyado + zapatas de los dos portones; áreas por hora con la velocidad
      sobre el fondo; clase de penetración del tipo de fondo.
    * **Cables**: tensión en el portón y en el buque y ángulo con la horizontal en la pasteca.
    """
    from trawlkit.rigging import seabed as seabed_of

    out: dict[str, Any] = {"ground_speed_kn": ground_kn, "water_speed_kn": water_kn}
    power_kw = pull_kgf * G * water_kn * KNOT_MS / TOWING_EFFICIENCY / 1000.0
    max_kw = rig.vessel_bhp * KW_PER_HP
    limited = power_kw > max_kw
    used_kw = min(power_kw, max_kw)
    fuel = used_kw * SFC_KG_KWH / DIESEL_KG_L
    catch = scenario.catch_kg if scenario else 0.0
    hours = scenario.haul_hours if scenario else 2.0
    out.update(
        towing_power_kw=power_kw,
        vessel_power_kw=max_kw,
        power_limited=limited,
        fuel_l_h=fuel,
        fuel_l_per_kg=fuel * hours / catch if catch > 0 else None,
    )
    km_h = ground_kn * 1.852
    contact = x[:, 2] <= 0.02
    if model.floor_free:
        contact[:] = False  # red pelágica: no toca el fondo
    foot = model.footrope
    on_bottom = foot[contact[foot]]
    foot_width = float(np.ptp(x[on_bottom, 1])) if on_bottom.size > 1 else 0.0
    door_width = 2.0 * rig.door_length_m if model.coupled_doors else 0.0
    swept = spread_m / 1000.0 * km_h
    out.update(
        swept_width_m=spread_m,
        contact_width_m=foot_width + door_width,
        swept_area_km2_h=swept,
        contact_area_km2_h=(foot_width + door_width) / 1000.0 * km_h,
        fuel_l_per_km2=fuel / swept if swept > 0 else None,
        penetration=(
            seabed_of(scenario.seabed).penetration if scenario and scenario.seabed else None
        ),
    )
    if model.coupled_doors:
        at_door = 0.0
        at_vessel = 0.0
        angle = 0.0
        fixed = set(model.fixed.tolist())
        doors = set(model.doors)
        for k, (b, kind) in enumerate(zip(model.bar, model.bar_kind, strict=True)):
            if kind != "warp":
                continue
            t = float(fr.bar_tension[k]) / G
            if int(b[0]) in doors:
                at_door = max(at_door, t)
            if int(b[1]) in fixed:
                at_vessel = max(at_vessel, t)
                d = x[b[1]] - x[b[0]]
                angle = float(np.degrees(np.arctan2(d[2], np.hypot(d[0], d[1]))))
        out.update(
            warp_tension_door_kgf=at_door,
            warp_tension_vessel_kgf=at_vessel,
            warp_angle_deg=angle,
            warp_length_m=rig.warp_length_m,
            depth_m=rig.depth_m,
        )
    return out


def _coupled(scenario: Scenario | None, result: DesignResult | None) -> bool:
    """Si la corrida lleva portones acoplados.

    Nunca en la pareja: no hay portones; los puntos de remolque (uniones de los cables con las
    patentes) quedan fijos a la separación de la pareja. Tampoco con tangones, gemelo o vara
    (Fase 19.5): se simula una red con sus puntos de remolque fijos (portones, portón y muerto o
    extremos de la vara).
    """
    if result is not None and (result.case.is_pair or result.case.is_multi):
        return False
    return bool(scenario and scenario.coupled_doors)


def _scenario_dict(sc: Scenario | None) -> dict[str, Any]:
    if sc is None:
        return {}
    from dataclasses import asdict

    out = asdict(sc)
    out["catch_volume_m3"] = sc.catch_volume_m3
    return out


# ---------------------------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------------------------


def simulate(
    case_or_spec: CaseLike,
    speed_kn: float,
    *,
    resolution: int = DEFAULT_RESOLUTION,
    cn: float = DEFAULT_CN,
    ct: float = DEFAULT_CT,
    mu: float = DEFAULT_MU,
    door_spread_m: float | None = None,
    knot_factor: float = 0.0,
    knot_cd: float = 1.0,
    tol: float = 1e-2,
    qoi_tol: float = 3e-3,
    max_iter: int = 40_000,
    coarse_resolution: int | None = 4,
    x_init: FloatArray | None = None,
    model: NetModel | None = None,
    scenario: Scenario | None = None,
) -> SimResult:
    """Forma de equilibrio de la red remolcada a ``speed_kn`` nudos.

    ``case_or_spec`` puede ser un :class:`~trawlkit.model.DesignResult` (se usan sus bridas,
    patentes, relingas, boyas, lastre y separación de portones ``doors.spread_m``), un
    :class:`~trawlkit.model.DesignCase` (se corre el motor) o una
    :class:`~trawlkit.io.schema.NetSpec` (aparejo genérico; ``door_spread_m`` obligatorio).

    * ``resolution``: divisiones nominales por panel (ver :func:`~trawlkit.sim.mesh.build_model`);
    * ``cn``/``ct``: coeficientes de Morison normal y tangencial del hilo; ``mu``: rozamiento
      con el fondo; ``door_spread_m``: distancia entre portones (si no, la del motor);
    * ``knot_factor``/``knot_cd``: arrastre opcional de los nudos (diámetro ``knot_factor·d``;
      0 = sin nudos, el modelo por defecto);
    * ``tol``/``qoi_tol``/``max_iter``: criterio de parada de :func:`~trawlkit.sim.solver.relax`;
    * ``coarse_resolution``: si no se da ``x_init``, se resuelve primero a esa resolución y se
      interpola la forma como punto de partida (multinivel); ``None`` parte de la red relingada;
    * ``scenario``: captura en el copo, tipo de fondo y portones acoplados (ver
      :mod:`trawlkit.sim.scenario`); ``None`` = simulador básico (red vacía, portones fijos).
    """
    spec, rig, result = _resolve(case_or_spec, door_spread_m)
    t0 = time.perf_counter()
    coupled = _coupled(scenario, result)
    if scenario is not None and scenario.warp_length_m is not None:
        rig = dataclasses.replace(rig, warp_length_m=float(scenario.warp_length_m))
    if model is not None and model.coupled_doors != coupled:
        model = None
    if model is not None and coupled and abs(model.warp_length_m - rig.warp_length_m) > 1e-9:
        model = None
    mdl = (
        model
        if model is not None
        else build_model(spec, rig, resolution=resolution, coupled_doors=coupled)
    )
    if scenario is not None and (scenario.door_cl_factor != 1.0 or scenario.door_cd_factor != 1.0):
        mdl = dataclasses.replace(
            mdl,
            door_cl=mdl.door_cl * scenario.door_cl_factor,
            door_cd=mdl.door_cd * scenario.door_cd_factor,
            door_cl_factor=scenario.door_cl_factor,
            door_cd_factor=scenario.door_cd_factor,
        )
    mu_door: float | None = None
    catch_v = catch_w = 0.0
    catch_cp = 1.0
    current = 0.0
    fouling_zones: tuple[tuple[str, float], ...] = ()
    gains = (1.5, 0.3, 2.0)
    if scenario is not None:
        mu, mu_door = scenario.friction(mu)
        catch_v = scenario.catch_volume_m3
        catch_w = scenario.catch_weight_water_n()
        catch_cp = scenario.catch_cp
        current = scenario.current_kn
        if scenario.fouling is not None:
            from trawlkit.sim.scenario import fouling_coefficients

            fouling_zones = tuple(sorted(scenario.fouling_zones().items()))
            c = fouling_coefficients()
            gains = (c["diameter_gain"], c["cn_gain"], c["weight_gain"])
    water_kn = speed_kn - current
    if water_kn < 0.2:
        raise ValueError(
            t(
                "velocidad relativa al agua muy baja ({v:.2f} kn): la corriente a favor "
                "no puede igualar a la velocidad de arrastre",
                v=water_kn,
            )
        )
    p = Params(
        speed_ms=water_kn * KNOT_MS,
        cn=cn,
        ct=ct,
        mu=mu,
        float_cd=_float_cd_at(result, rig, speed_kn),
        knot_factor=knot_factor,
        knot_cd=knot_cd,
        mu_door=mu_door,
        catch_volume_m3=catch_v,
        catch_weight_n=catch_w,
        catch_cp=catch_cp,
        fouling=fouling_zones,
        fouling_gains=gains,
        mesh_bending=_mesh_bending(mdl, scenario),
        door_dynamic=bool(coupled and scenario is not None and scenario.dynamic_door_polar),
    )
    if x_init is not None and x_init.shape != mdl.x0.shape:
        x_init = None
    if x_init is None and coarse_resolution and coarse_resolution < resolution:
        coarse = build_model(spec, rig, resolution=coarse_resolution, coupled_doors=coupled)
        rc = relax(coarse, p, tol=tol, qoi_tol=qoi_tol, max_iter=max_iter)
        x_init = interpolate_shape(coarse, rc.x, mdl)
    start = (mdl.x0 if x_init is None else x_init).copy()
    if mdl.fixed_tips:
        start[mdl.fixed] = mdl.x0[mdl.fixed]  # vara: puntas de ala en la vara y los patines
    elif not coupled:
        for k, sgn in zip(mdl.doors, (1.0, -1.0), strict=True):
            start[k] = [mdl.x0[k, 0], sgn * rig.door_spread_m / 2.0, mdl.x0[k, 2]]
    else:
        # Los puntos del buque son fijos: vienen del modelo (el largo de cable puede cambiar).
        start[mdl.fixed] = mdl.x0[mdl.fixed]
    relaxed = relax(mdl, p, start, tol=tol, qoi_tol=qoi_tol, max_iter=max_iter)
    foul = None
    fill = None
    if fouling_zones or catch_v > 0:
        from trawlkit.sim.solver import ForceField

        ff = ForceField(mdl, p)
        if fouling_zones:
            foul = ff.foul
        if ff.has_catch:
            ff.update_catch(relaxed.x)
            fill = np.zeros(mdl.tri.shape[0])
            fill[ff.catch_tri] = ff.catch_w
    out = _result(
        mdl,
        rig,
        p,
        speed_kn,
        relaxed,
        time.perf_counter() - t0,
        resolution,
        scenario,
        ground_kn=speed_kn,
        ff_fouling=foul,
        catch_fill=fill,
    )
    info = rig_info(result, out)
    return dataclasses.replace(out, rig=info) if info else out


def rig_info(result: DesignResult | None, sim: SimResult) -> dict[str, Any]:
    """Tangones, gemelo o vara (Fase 19.5): copias de la red simulada y arrastre del aparejo.

    Se simula **una** red con sus puntos de remolque fijos y se replica en la vista 3D:

    * tangones: cada red centrada detrás de la punta de su tangón (``±y`` de la punta);
    * gemelo: las dos redes a cada lado del muerto central, que queda en la crujía: los puntos
      de remolque de la red simulada son el portón y el muerto (simplificación: la red es
      simétrica respecto de su eje; el muerto va en el fondo y sin sustentación);
    * vara: una vara por tangón (``±y`` de la punta si hay tangones; si no, lado a lado).

    ``drag_kgf`` es el arrastre de todas las redes (sin portones, cables ni vara).
    """
    if result is None or result.multirig is None:
        return {}
    mr = result.multirig
    n = mr.n_nets
    if n == 1:
        offsets: list[float] = [0.0]
    elif mr.layout is not None:
        offsets = [mr.layout.tip_offset_m, -mr.layout.tip_offset_m]
    else:
        offsets = [0.5 * mr.net_spread_m, -0.5 * mr.net_spread_m]
    return {
        "kind": mr.kind,
        "n_nets": n,
        "offsets_m": offsets,
        "drag_kgf": n * sim.drag_kgf,
        "swept_width_m": mr.swept_width_m,
    }


def _mesh_bending(model: NetModel, scenario: Scenario | None) -> float:
    """Módulo de flexión de la malla de la corrida (0 = sin rigidez de apertura)."""
    flag = None if scenario is None else scenario.mesh_bending
    if flag is None:
        flag = any(o != "diamond" for o in model.tri_orientation)
    if not flag:
        return 0.0
    factor = 1.0 if scenario is None else scenario.mesh_bending_factor
    return DEFAULT_MESH_BENDING_PA * factor


def sweep(
    case: CaseLike,
    speeds_kn: Sequence[float],
    *,
    resolution: int = DEFAULT_RESOLUTION,
    cn: float = DEFAULT_CN,
    ct: float = DEFAULT_CT,
    mu: float = DEFAULT_MU,
    door_spread_m: float | Sequence[float] | None = None,
    knot_factor: float = 0.0,
    knot_cd: float = 1.0,
    tol: float = 1e-2,
    qoi_tol: float = 3e-3,
    max_iter: int = 40_000,
    coarse_resolution: int | None = 4,
    scenario: Scenario | None = None,
) -> list[SimResult]:
    """:func:`simulate` a varias velocidades; cada una parte de la forma de la anterior.

    ``door_spread_m`` puede ser un valor único o uno por velocidad (p. ej. la DP de DynamiT).
    """
    if isinstance(case, DesignCase):
        case = run(case)
    speeds = [float(v) for v in speeds_kn]
    if door_spread_m is None or isinstance(door_spread_m, int | float):
        dps: list[float | None] = [None if door_spread_m is None else float(door_spread_m)] * len(
            speeds
        )
    else:
        dps = [float(d) for d in door_spread_m]
        if len(dps) != len(speeds):
            raise ValueError(t("door_spread_m debe tener un valor por velocidad"))
    out: list[SimResult] = []
    prev: FloatArray | None = None
    model: NetModel | None = None
    for v, dp in zip(speeds, dps, strict=True):
        if model is None:
            spec, rig, res0 = _resolve(case, dp)
            model = build_model(
                spec, rig, resolution=resolution, coupled_doors=_coupled(scenario, res0)
            )
        res = simulate(
            case,
            v,
            resolution=resolution,
            cn=cn,
            ct=ct,
            mu=mu,
            door_spread_m=dp,
            knot_factor=knot_factor,
            knot_cd=knot_cd,
            tol=tol,
            qoi_tol=qoi_tol,
            max_iter=max_iter,
            coarse_resolution=coarse_resolution,
            x_init=prev,
            model=model,
            scenario=scenario,
        )
        prev = res.nodes
        out.append(res)
    return out


#: Variables que :func:`explore` puede recorrer.
EXPLORE_VARIABLES = (
    "catch_kg",
    "speed_kn",
    "warp_length_m",
    "fouling_level",
    "current_kn",
    "mu_gear",
)


def explore(
    case: CaseLike,
    variable: str,
    values: Sequence[float],
    *,
    speed_kn: float = 3.0,
    scenario: Scenario | None = None,
    resolution: int = 4,
    cn: float = DEFAULT_CN,
    ct: float = DEFAULT_CT,
    mu: float = DEFAULT_MU,
    tol: float = 1e-2,
    qoi_tol: float = 3e-3,
    max_iter: int = 40_000,
) -> list[SimResult]:
    """Estados de equilibrio al recorrer ``variable`` por ``values`` (arranque en caliente).

    ``variable`` es una de :data:`EXPLORE_VARIABLES`: ``speed_kn`` cambia la velocidad de arrastre
    y las demás el campo homónimo del escenario. Todos los estados comparten la malla (mismos
    nodos), así que la forma puede interpolarse entre ellos para animarla.
    """
    if variable not in EXPLORE_VARIABLES:
        raise ValueError(
            t(
                "variable desconocida: {v!r} (use {names})",
                v=variable,
                names=", ".join(EXPLORE_VARIABLES),
            )
        )
    if isinstance(case, DesignCase):
        case = run(case)
    base = scenario or Scenario()
    spec, rig, res0 = _resolve(case, None)
    model: NetModel | None = None
    out: list[SimResult] = []
    prev: FloatArray | None = None
    for value in values:
        v = float(value)
        changes: dict[str, Any] = {} if variable == "speed_kn" else {variable: v}
        sc = dataclasses.replace(base, **changes)
        speed = v if variable == "speed_kn" else speed_kn
        coupled = _coupled(sc, res0)
        if model is None or (variable == "warp_length_m" and coupled):
            rig_v = (
                dataclasses.replace(rig, warp_length_m=sc.warp_length_m)
                if sc.warp_length_m is not None
                else rig
            )
            model = build_model(spec, rig_v, resolution=resolution, coupled_doors=coupled)
        res = simulate(
            case,
            speed,
            resolution=resolution,
            cn=cn,
            ct=ct,
            mu=mu,
            tol=tol,
            qoi_tol=qoi_tol,
            max_iter=max_iter,
            coarse_resolution=None,
            x_init=prev,
            model=model,
            scenario=sc,
        )
        prev = res.nodes
        out.append(res)
    return out


def haul(
    case: CaseLike,
    speed_kn: float,
    catches_kg: Sequence[float],
    *,
    scenario: Scenario | None = None,
    resolution: int = 4,
    cn: float = DEFAULT_CN,
    ct: float = DEFAULT_CT,
    mu: float = DEFAULT_MU,
    tol: float = 1e-2,
    qoi_tol: float = 3e-3,
    max_iter: int = 40_000,
) -> list[SimResult]:
    """Lance progresivo: equilibrios sucesivos a ``speed_kn`` con la captura creciendo.

    Cada paso parte de la forma del anterior (la captura entra de a poco, como en el lance). El
    resto del escenario (fondo, densidades, portones acoplados) se toma de ``scenario``.
    """
    return explore(
        case,
        "catch_kg",
        catches_kg,
        speed_kn=speed_kn,
        scenario=scenario,
        resolution=resolution,
        cn=cn,
        ct=ct,
        mu=mu,
        tol=tol,
        qoi_tol=qoi_tol,
        max_iter=max_iter,
    )
