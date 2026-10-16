"""API de la simulación cuasiestática: :func:`simulate`, :func:`sweep` y :class:`SimResult`."""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import numpy.typing as npt

from trawlkit.io.schema import NetSpec
from trawlkit.model import DesignCase, DesignResult, run
from trawlkit.sim.mesh import NetModel, Rigging, build_model, interpolate_shape
from trawlkit.sim.solver import G, Params, RelaxResult, relax

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.int64]

KNOT_MS = 1852.0 / 3600.0

#: Coeficientes hidrodinámicos por defecto del hilo (cilindro): normal y tangencial.
DEFAULT_CN = 1.4
DEFAULT_CT = 0.08
#: Coeficiente de rozamiento red–fondo (fondo intermedio).
DEFAULT_MU = 0.5
#: Resolución por defecto (divisiones nominales por panel).
DEFAULT_RESOLUTION = 8

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
        }
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
            )
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


def rigging_from_result(r: DesignResult, door_spread_m: float | None = None) -> Rigging:
    """Aparejo de la red estándar a partir del resultado del motor (modo del caso)."""
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
    return Rigging(
        door_spread_m=float(r.doors.spread_m if door_spread_m is None else door_spread_m),
        upper_bridle_m=float(r.bridles.lengths.upper_m),
        # La cadena de reglaje se ajusta para que brida inferior + cadena = brida superior (es
        # su función). Con el redondeo del libro (17 + 1,71 = 18,71 m) la inferior quedaría
        # 0,71 m más larga que la superior —más de lo que absorbe la punta de ala— y floja.
        lower_bridle_m=float(r.bridles.lengths.upper_m),
        sweeps_m=float(r.bridles.sweeps_m),
        headrope_wing_m=float(dims.headrope.wing_corrected_m),
        headrope_bosom_m=float(dims.headrope.bosom_corrected_m),
        footrope_wing_m=float(dims.footrope.wing_corrected_m),
        footrope_bosom_m=float(dims.footrope.bosom_corrected_m),
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
            float(dims.headrope.wing_corrected_m),
            float(dims.headrope.bosom_corrected_m),
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
    )


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
        raise ValueError("con una NetSpec sola hay que indicar door_spread_m")
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
) -> SimResult:
    x = relaxed.x
    fr = relaxed.forces
    tu, tl = model.wing_tips_upper, model.wing_tips_lower
    net_nodes = np.ones(x.shape[0], dtype=bool)
    net_nodes[[*model.junctions, *model.doors]] = False
    hydro = float(fr.hydro_x[net_nodes].sum())
    friction = float(p.mu * fr.reaction[net_nodes].sum())
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
        door_spread_m=rig.door_spread_m,
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
        },
    )


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
      interpola la forma como punto de partida (multinivel); ``None`` parte de la red relingada.
    """
    spec, rig, result = _resolve(case_or_spec, door_spread_m)
    t0 = time.perf_counter()
    mdl = model if model is not None else build_model(spec, rig, resolution=resolution)
    p = Params(
        speed_ms=speed_kn * KNOT_MS,
        cn=cn,
        ct=ct,
        mu=mu,
        float_cd=_float_cd_at(result, rig, speed_kn),
        knot_factor=knot_factor,
        knot_cd=knot_cd,
    )
    if x_init is not None and x_init.shape != mdl.x0.shape:
        x_init = None
    if x_init is None and coarse_resolution and coarse_resolution < resolution:
        coarse = build_model(spec, rig, resolution=coarse_resolution)
        rc = relax(coarse, p, tol=tol, qoi_tol=qoi_tol, max_iter=max_iter)
        x_init = interpolate_shape(coarse, rc.x, mdl)
    start = (mdl.x0 if x_init is None else x_init).copy()
    for k, sgn in zip(mdl.doors, (1.0, -1.0), strict=True):
        start[k] = [mdl.x0[k, 0], sgn * rig.door_spread_m / 2.0, mdl.x0[k, 2]]
    relaxed = relax(mdl, p, start, tol=tol, qoi_tol=qoi_tol, max_iter=max_iter)
    return _result(mdl, rig, p, speed_kn, relaxed, time.perf_counter() - t0, resolution)


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
            raise ValueError("door_spread_m debe tener un valor por velocidad")
    out: list[SimResult] = []
    prev: FloatArray | None = None
    model: NetModel | None = None
    for v, dp in zip(speeds, dps, strict=True):
        if model is None:
            spec, rig, _ = _resolve(case, dp)
            model = build_model(spec, rig, resolution=resolution)
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
        )
        prev = res.nodes
        out.append(res)
    return out
