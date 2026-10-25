"""Lógica de la API independiente de HTTP: catálogos, armado del caso y serialización."""

from __future__ import annotations

import dataclasses
import inspect
import math
import os
import re
from functools import cache
from typing import Any

import yaml
from pydantic import ValidationError

from trawlkit.compat import Compat
from trawlkit.io import load_doors, load_net, load_vessels
from trawlkit.io.schema import Door, NetSpec, Vessel
from trawlkit.model import DesignCase, DesignResult, run

#: Campos de ``DesignCase`` que no se sobrescriben vía ``params`` (tienen su propio campo).
_STRUCTURAL = {"net", "net_modified", "vessel", "door", "class_vessels", "compat"}


class BadRequestError(ValueError):
    """Error de entrada del cliente (se traduce a HTTP 422)."""


class NotFoundError(KeyError):
    """Id desconocido en un catálogo (se traduce a HTTP 404)."""


# --- Guardas de costo configurables por entorno -------------------------------------------------
# Un servidor con CPU lenta (p. ej. el plan gratuito de Render) puede bajar estos límites sin tocar
# el código; los valores por defecto son los de la API local.

#: Lado máximo por defecto de la malla de ``POST /optimize`` (``OptimizeGrid`` admite hasta 25).
OPT_MAX_GRID_DEFAULT = 25


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if math.isfinite(value) and value > 0 else default


def sim_max_cost_s() -> float:
    """Costo máximo estimado de ``POST /simulate`` [s] (``TRAWLKIT_MAX_SIM_SECONDS``)."""
    return _env_float("TRAWLKIT_MAX_SIM_SECONDS", SIM_MAX_COST_S)


def opt_max_grid() -> int:
    """Lado máximo de la malla de ``POST /optimize`` (``TRAWLKIT_MAX_OPT_GRID``, 2–25)."""
    value = int(_env_float("TRAWLKIT_MAX_OPT_GRID", OPT_MAX_GRID_DEFAULT))
    return max(2, min(value, OPT_MAX_GRID_DEFAULT))


def refine_allowed() -> bool:
    """``POST /optimize`` acepta ``refine`` salvo ``TRAWLKIT_ALLOW_REFINE`` = 0/false/no/off."""
    raw = os.environ.get("TRAWLKIT_ALLOW_REFINE", "").strip().lower()
    return raw not in {"0", "false", "no", "off"}


#: Archivos de red que no validan como ``NetSpec`` (nombre → error), para diagnóstico.
NET_LOAD_ERRORS: dict[str, str] = {}


@cache
def net_presets() -> dict[str, NetSpec]:
    """Redes del paquete (``data/*.yaml`` y ``data/nets/*.yaml``) que validan como ``NetSpec``.

    Las que no validan se registran en :data:`NET_LOAD_ERRORS` en lugar de descartarse en
    silencio.
    """
    from trawlkit.io.loader import net_files

    out: dict[str, NetSpec] = {}
    for path in net_files():
        with path.open(encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        if not isinstance(raw, dict) or "panels" not in raw:
            continue
        try:
            spec = NetSpec.model_validate(raw)
        except ValidationError as exc:
            NET_LOAD_ERRORS[path.stem] = str(exc)
            continue
        out[path.stem] = spec
    return out


@cache
def vessel_presets() -> dict[str, Vessel]:
    """Buques del catálogo por id."""
    return {v.id: v for v in load_vessels().vessels}


@cache
def door_presets() -> dict[str, Door]:
    """Portones del catálogo por id."""
    return {d.id: d for d in load_doors().doors}


def normalise_inline_net(spec: NetSpec) -> NetSpec:
    """Sincroniza ``meshes_a``/``meshes_b`` (T1/T2 del Excel) con los bordes editados.

    El motor usa los extras ``meshes_a`` (borde mayor) y ``meshes_b`` (borde menor) cuando están
    presentes. Una red editada en el cliente suele cambiar sólo ``meshes_top``/``meshes_bottom``;
    si esos bordes ya no coinciden con ``{meshes_a, meshes_b}``, se recalculan a partir de ellos.
    """
    panels = []
    changed = False
    for p in spec.panels:
        extra = p.model_extra or {}
        a, b = extra.get("meshes_a"), extra.get("meshes_b")
        edges = {p.meshes_top, p.meshes_bottom}
        if a is not None and b is not None and {a, b} != edges:
            data = p.model_dump()
            data["meshes_a"] = max(p.meshes_top, p.meshes_bottom)
            data["meshes_b"] = min(p.meshes_top, p.meshes_bottom)
            panels.append(type(p).model_validate(data))
            changed = True
        else:
            panels.append(p)
    return spec.model_copy(update={"panels": panels}) if changed else spec


def _net(value: str | NetSpec | None) -> NetSpec | None:
    if value is None:
        return None
    if isinstance(value, NetSpec):
        return normalise_inline_net(value)
    presets = net_presets()
    if value not in presets:
        raise NotFoundError(f"red desconocida: {value!r}")
    # load_net sólo con ids validados: nunca rutas provistas por el cliente.
    return load_net(value)


def layout_of(net: str | NetSpec, mode: str = "schematic") -> dict[str, Any]:
    """Disposición 2D de la red (``layout_net``) como datos serializables, por plano."""
    from trawlkit.drawing.layout import layout_net

    spec = _net(net)
    assert spec is not None
    lay = layout_net(spec, mode="true_scale" if mode == "true_scale" else "schematic")
    planes = []
    for plane in lay.planes:
        shapes = [
            {
                "id": s.id,
                "plane": s.plane,
                "section": str(s.section),
                "side": s.side,
                "points": [list(p) for p in s.points],
                "y_top": s.y_top,
                "y_bottom": s.y_bottom,
                "x_top": list(s.x_top),
                "x_bottom": list(s.x_bottom),
                "meshes_top": s.meshes_top,
                "meshes_bottom": s.meshes_bottom,
                "meshes_depth": s.meshes_depth,
                "mesh_mm": s.mesh_mm,
                "hanging_ratio": s.hanging_ratio,
                "mesh_orientation": str(s.panel.mesh_orientation),
                "cut_code": s.cut_code,
            }
            for s in lay.shapes[plane]
        ]
        planes.append(
            {
                "plane": plane,
                "bbox": list(lay.plane_bbox(plane)),
                "mouth_y": lay.mouth_y(plane),
                "shapes": shapes,
            }
        )
    return {"net_id": lay.net_id, "mode": lay.mode, "bbox": list(lay.bbox), "planes": planes}


def _pick(value: Any, presets: dict[str, Any], kind: str) -> Any:
    if value is None:
        return next(iter(presets.values()))
    if isinstance(value, str):
        if value not in presets:
            raise NotFoundError(f"{kind} desconocido: {value!r}")
        return presets[value]
    return value


@cache
def _field_comments() -> dict[str, str]:
    """Comentarios en línea de cada campo de ``DesignCase`` (celda del Excel)."""
    src = inspect.getsource(DesignCase)
    out: dict[str, str] = {}
    for m in re.finditer(r"^\s{4}(\w+):[^#\n]*#\s*(.+)$", src, re.MULTILINE):
        out[m.group(1)] = m.group(2).strip()
    return out


def params_info() -> list[dict[str, Any]]:
    """Parámetros sobrescribibles de ``DesignCase`` con tipo, valor por defecto y celda."""
    comments = _field_comments()
    out = []
    for f in dataclasses.fields(DesignCase):
        if f.name in _STRUCTURAL:
            continue
        default = f.default if f.default is not dataclasses.MISSING else None
        out.append(
            {
                "name": f.name,
                "type": str(f.type),
                "default": to_jsonable(default),
                "comment": comments.get(f.name, ""),
            }
        )
    return out


def _coerce_params(params: dict[str, Any]) -> dict[str, Any]:
    allowed = {p["name"] for p in params_info()}
    unknown = set(params) - allowed
    if unknown:
        raise BadRequestError(f"parámetros desconocidos: {sorted(unknown)}")
    out: dict[str, Any] = {}
    for k, v in params.items():
        values = v if isinstance(v, list) else [v]
        for item in values:
            if isinstance(item, bool) or not isinstance(item, (int, float, str)):
                raise BadRequestError(f"{k}: valor no admitido {item!r}")
            if isinstance(item, (int, float)) and (not math.isfinite(item) or item < 0):
                raise BadRequestError(f"{k}: debe ser un número finito y no negativo ({item!r})")
        out[k] = tuple(v) if isinstance(v, list) else v
    return out


def build_case(
    net: str | NetSpec = "fao_a3_standard",
    net_modified: str | NetSpec | None = None,
    vessel: str | Vessel | None = None,
    door: str | Door | None = None,
    class_vessels: list[str] | None = None,
    compat: str = "corrected",
    params: dict[str, Any] | None = None,
) -> DesignCase:
    """Arma un :class:`DesignCase` validando ids contra los catálogos."""
    vessels = vessel_presets()
    v: Vessel = _pick(vessel, vessels, "buque")
    d: Door = _pick(door, door_presets(), "portón")
    if class_vessels is None:
        others = tuple(o for o in vessels.values() if o.id != v.id)
    else:
        others = tuple(_pick(c, vessels, "buque") for c in class_vessels)
    main = _net(net)
    assert main is not None
    kwargs = _coerce_params(params or {})
    try:
        case = DesignCase(
            net=main,
            vessel=v,
            door=d,
            net_modified=_net(net_modified),
            class_vessels=others,
            compat=Compat(compat),
        )
        return dataclasses.replace(case, **kwargs) if kwargs else case
    except (TypeError, ValueError) as exc:
        raise BadRequestError(str(exc)) from exc


def run_case(case: DesignCase) -> DesignResult:
    """Corre el caso; los errores numéricos del motor se informan como entrada inválida."""
    try:
        return run(case)
    except (ValueError, ZeroDivisionError, IndexError) as exc:
        raise BadRequestError(f"el caso no se puede calcular: {exc}") from exc


def optimize_case(
    *,
    net: str | NetSpec = "fao_a3_standard",
    vessel: str | Vessel | None = None,
    door: str | Door | None = None,
    class_vessels: list[str] | None = None,
    objective: str = "area",
    margin: float = 0.1,
    s_bounds: tuple[float, float] = (0.6, 1.4),
    v_bounds: tuple[float, float] = (1.5, 4.0),
    grid: tuple[int, int] = (13, 11),
    refine: bool = True,
    seed: int = 0,
    propeller: str | None = None,
    door_angle: float | None = None,
) -> dict[str, Any]:
    """Arma el caso (modo corregido), corre :func:`trawlkit.optimize.optimise` y lo serializa."""
    from trawlkit.optimize import optimise

    limit = opt_max_grid()
    if max(grid) > limit:
        raise BadRequestError(
            f"malla de optimización demasiado grande: {grid[0]} × {grid[1]} "
            f"(máximo {limit} × {limit} en este servidor)"
        )
    if refine and not refine_allowed():
        raise BadRequestError(
            "el refinado (evolución diferencial) está desactivado en este servidor; "
            "optimice sólo con la malla (refine = false)"
        )
    case = build_case(net=net, vessel=vessel, door=door, class_vessels=class_vessels)
    try:
        result = optimise(
            case,
            objective=objective,
            bounds=(s_bounds, v_bounds),
            margin=margin,
            seed=seed,
            grid=grid,
            refine=refine,
            propeller=propeller,
            door_angle=door_angle,
        )
    except (ValueError, ZeroDivisionError, IndexError) as exc:
        raise BadRequestError(f"no se puede optimizar el caso: {exc}") from exc
    out: dict[str, Any] = to_jsonable(result.to_dict())
    return out


def to_jsonable(value: Any) -> Any:
    """Convierte a JSON estricto: NaN/inf → ``None``, tuplas → listas, recursivo."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    if hasattr(value, "item") and callable(value.item):  # escalares numpy
        return to_jsonable(value.item())
    if hasattr(value, "tolist"):
        return to_jsonable(value.tolist())
    if isinstance(value, Compat):
        return value.value
    return value


def scaled_net(net: str | NetSpec, s: float) -> NetSpec:
    """Red del caso escalada por ``s`` con :func:`trawlkit.optimize.scale_net`."""
    from trawlkit.optimize import scale_net

    spec = _net(net)
    assert spec is not None
    try:
        return scale_net(spec, s)
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc


#: Costo empírico de :func:`trawlkit.sim.simulate` por velocidad [s] según la resolución
#: (red FAO A-3, un núcleo; incluye la etapa gruesa a resolución 4 cuando corresponde).
SIM_COST_PER_SPEED_S: dict[int, float] = {
    2: 0.8,
    3: 1.0,
    4: 1.4,
    5: 2.2,
    6: 4.5,
    7: 7.0,
    8: 12.0,
    9: 20.0,
    10: 24.0,
}
#: Costo máximo estimado que acepta ``POST /simulate`` [s] por defecto
#: (``TRAWLKIT_MAX_SIM_SECONDS`` lo cambia; ver :func:`sim_max_cost_s`).
SIM_MAX_COST_S = 30.0


def _net_length_m(spec: NetSpec) -> float:
    """Largo estirado aproximado de la red: Σ mallas de alto × mallero de cada panel [m]."""
    return sum(float(p.meshes_depth) * float(p.mesh_mm) for p in spec.panels) / 1000.0


#: Con portones acoplados (cables hasta el buque) cada equilibrio cuesta más: modos lentos de
#: la catenaria y del portón.
SIM_COUPLED_FACTOR = 2.5


def estimate_sim_cost(
    n_speeds: int, resolution: int, net: NetSpec | None = None, *, coupled: bool = False
) -> float:
    """Tiempo estimado de una simulación [s]: costo por velocidad × velocidades × tamaño.

    La grilla tiene ``resolution`` filas cada 9 m de red, así que el costo crece con el largo de
    la red; se escala con (largo / largo de la FAO A-3)^1,5, como mínimo 0,5. Con portones
    acoplados se multiplica por :data:`SIM_COUPLED_FACTOR`.
    """
    per = SIM_COST_PER_SPEED_S[max(min(resolution, 10), 2)]
    if coupled:
        per *= SIM_COUPLED_FACTOR
    size = 1.0
    ref = net_presets().get("fao_a3_standard")
    if net is not None and ref is not None:
        size = max(0.5, (_net_length_m(net) / _net_length_m(ref)) ** 1.5)
    return 0.5 + per * n_speeds * size


def _is_fao_a3_standard(spec: NetSpec) -> bool:
    """La red es la FAO A-3 estándar del catálogo sin editar (la que simuló DynamiT)."""
    ref = net_presets().get("fao_a3_standard")
    return ref is not None and spec.model_dump() == load_net("fao_a3_standard").model_dump()


def _pct(x: float | None, ref: float) -> float | None:
    if x is None or not math.isfinite(x) or ref == 0:
        return None
    return (x - ref) / ref * 100.0


def simulate_case(
    *,
    net: str | NetSpec = "fao_a3_standard",
    vessel: str | Vessel | None = None,
    door: str | Door | None = None,
    class_vessels: list[str] | None = None,
    compat: str = "corrected",
    speeds_kn: list[float],
    resolution: int = 4,
    cn: float | None = None,
    ct: float | None = None,
    knot_factor: float | None = None,
    door_spread_m: float | None = None,
    include_geometry: bool = False,
    max_projections: int = 3,
    mu: float | None = None,
    scenario: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Corre el motor y :func:`trawlkit.sim.sweep`, y arma la respuesta de ``POST /simulate``.

    Las velocidades se simulan en orden creciente (cada una parte de la forma de la anterior) y
    se devuelven en el orden pedido. Las proyecciones son de las ``max_projections`` primeras
    velocidades pedidas. Si la red es la FAO A-3 estándar, ``dynamit_comparison`` compara con la
    simulación DynamiT en las velocidades de su tabla.
    """
    import time

    import numpy as np

    from trawlkit.sim import DEFAULT_CN, DEFAULT_CT, DEFAULT_MU, sweep
    from trawlkit.sim.render import projections_svg
    from trawlkit.sim.validation import DYNAMIT

    t0 = time.perf_counter()
    case = build_case(net=net, vessel=vessel, door=door, class_vessels=class_vessels, compat=compat)
    sc = make_scenario(scenario)
    coupled = bool(sc and sc.coupled_doors)
    estimate = estimate_sim_cost(len(speeds_kn), resolution, case.net, coupled=coupled)
    max_cost = sim_max_cost_s()
    if estimate > max_cost:
        raise BadRequestError(
            f"simulación demasiado costosa: ~{estimate:.0f} s estimados para "
            f"{len(speeds_kn)} velocidades a resolución {resolution} (máximo "
            f"{max_cost:.0f} s); baje la resolución o la cantidad de velocidades"
        )
    result = run_case(case)
    order = sorted(range(len(speeds_kn)), key=lambda i: speeds_kn[i])
    ordered = [float(speeds_kn[i]) for i in order]
    try:
        sims = sweep(
            result,
            ordered,
            resolution=resolution,
            cn=DEFAULT_CN if cn is None else cn,
            ct=DEFAULT_CT if ct is None else ct,
            knot_factor=0.0 if knot_factor is None else knot_factor,
            door_spread_m=door_spread_m,
            mu=DEFAULT_MU if mu is None else mu,
            scenario=sc,
        )
    except (ValueError, ZeroDivisionError, IndexError, FloatingPointError) as exc:
        raise BadRequestError(f"no se puede simular el caso: {exc}") from exc
    by_speed = dict(zip(ordered, sims, strict=True))
    sims_req = [by_speed[float(v)] for v in speeds_kn]

    # Motor a las velocidades pedidas (otra corrida con esas velocidades agregadas a la malla).
    ref = dataclasses.replace(
        case, speeds_kn=tuple(sorted({*case.speeds_kn, *(float(v) for v in speeds_kn)}))
    )
    try:
        eng = run(ref)
    except (ValueError, ZeroDivisionError, IndexError):
        eng = result
    ekn = np.asarray(eng.case.speeds_kn, dtype=float)

    def at(arr: Any, v: float) -> float | None:
        x = float(np.interp(v, ekn, np.asarray(arr, dtype=float)))
        return x if math.isfinite(x) else None

    engine_rows = [
        {
            "speed_kn": float(v),
            "ah_m": at(eng.spread.fridman.dpa_std_m, v),
            "av_m": at(eng.spread.vertical.fridman.std.av_m, v),
            "drag_kgf": at(eng.drag.rn.std, v),
            "door_spread_m": float(eng.doors.spread_m),
        }
        for v in speeds_kn
    ]

    projections = {
        f"{float(v):g}": projections_svg(r) for v, r in zip(speeds_kn, sims_req, strict=True)
    }
    projections = dict(list(projections.items())[:max_projections])

    dynamit: list[dict[str, Any]] | None = None
    if _is_fao_a3_standard(case.net):
        dynamit = []
        dv = list(DYNAMIT["v_kn"])
        for v, r, e in zip(speeds_kn, sims_req, engine_rows, strict=True):
            hit = [i for i, x in enumerate(dv) if abs(x - v) < 1e-9]
            if not hit:
                continue
            i = hit[0]
            d = {
                "ah_m": DYNAMIT["AH_m"][i],
                "av_m": DYNAMIT["AV_m"][i],
                "door_spread_m": DYNAMIT["DP_m"][i],
                "drag_kgf": DYNAMIT["RA_kg"][i],
            }
            s = {
                "ah_m": r.ah_m,
                "av_m": r.av_m,
                "door_spread_m": r.door_spread_m,
                "drag_kgf": r.drag_kgf,
            }
            en = {k: e[k] for k in ("ah_m", "av_m", "door_spread_m", "drag_kgf")}
            dynamit.append(
                {
                    "speed_kn": float(v),
                    "dynamit": d,
                    "sim": s,
                    "engine": en,
                    "sim_pct": {k: _pct(s[k], d[k]) for k in d},
                    "engine_pct": {k: _pct(en[k], d[k]) for k in d},
                }
            )
    out = {
        "results": [r.to_dict(geometry=include_geometry) for r in sims_req],
        "projections_svg": projections,
        "engine": engine_rows,
        "dynamit_comparison": dynamit,
        "settings": {
            "net_id": case.net.id,
            "vessel_id": case.vessel.id,
            "door_id": case.door.id,
            "compat": case.compat.value,
            "resolution": resolution,
            "cn": DEFAULT_CN if cn is None else cn,
            "ct": DEFAULT_CT if ct is None else ct,
            "knot_factor": 0.0 if knot_factor is None else knot_factor,
            "door_spread_m": door_spread_m,
            "mu": DEFAULT_MU if mu is None else mu,
            "scenario": None if sc is None else dataclasses.asdict(sc),
        },
        "estimated_s": estimate,
        "runtime_s": time.perf_counter() - t0,
    }
    jsonable: dict[str, Any] = to_jsonable(out)
    return jsonable


def make_scenario(data: dict[str, Any] | None) -> Any:
    """``trawlkit.sim.Scenario`` desde el cuerpo del pedido (``None`` = simulador básico)."""
    from trawlkit.sim import Scenario

    if data is None:
        return None
    try:
        return Scenario(**data)
    except (ValueError, KeyError) as exc:
        raise BadRequestError(f"escenario inválido: {exc}") from exc


def seabed_catalogue() -> list[dict[str, Any]]:
    """Catálogo de tipos de fondo (``GET /catalog/seabeds``)."""
    from trawlkit.rigging import seabeds

    return [s.to_dict() for s in seabeds()]


def haul_case(
    *,
    net: str | NetSpec = "fao_a3_standard",
    vessel: str | Vessel | None = None,
    door: str | Door | None = None,
    class_vessels: list[str] | None = None,
    compat: str = "corrected",
    speed_kn: float = 3.0,
    catches_kg: list[float],
    resolution: int = 4,
    cn: float | None = None,
    ct: float | None = None,
    scenario: dict[str, Any] | None = None,
    include_geometry: bool = False,
) -> dict[str, Any]:
    """Lance progresivo (``POST /simulate/haul``): :func:`trawlkit.sim.haul` y el motor."""
    import time

    import numpy as np

    from trawlkit.sim import DEFAULT_CN, DEFAULT_CT, haul

    t0 = time.perf_counter()
    sc = make_scenario({**(scenario or {}), "catch_kg": 0.0})
    params = {"seabed": sc.seabed} if sc.seabed else {}
    case = build_case(
        net=net,
        vessel=vessel,
        door=door,
        class_vessels=class_vessels,
        compat=compat,
        params=params,
    )
    estimate = estimate_sim_cost(len(catches_kg), resolution, case.net, coupled=sc.coupled_doors)
    max_cost = sim_max_cost_s()
    if estimate > max_cost:
        raise BadRequestError(
            f"lance demasiado costoso: ~{estimate:.0f} s estimados para {len(catches_kg)} pasos "
            f"a resolución {resolution} (máximo {max_cost:.0f} s); baje la resolución o los pasos"
        )
    result = run_case(case)
    try:
        sims = haul(
            result,
            speed_kn,
            catches_kg,
            scenario=sc,
            resolution=resolution,
            cn=DEFAULT_CN if cn is None else cn,
            ct=DEFAULT_CT if ct is None else ct,
        )
    except (ValueError, ZeroDivisionError, IndexError, FloatingPointError) as exc:
        raise BadRequestError(f"no se puede simular el lance: {exc}") from exc
    ref = dataclasses.replace(case, speeds_kn=tuple(sorted({*case.speeds_kn, float(speed_kn)})))
    try:
        eng = run(ref)
    except (ValueError, ZeroDivisionError, IndexError):
        eng = result
    ekn = np.asarray(eng.case.speeds_kn, dtype=float)
    demand = float(np.interp(speed_kn, ekn, np.asarray(eng.performance.demand.std, dtype=float)))
    out = {
        "results": [r.to_dict(geometry=include_geometry) for r in sims],
        "engine": {
            "speed_kn": float(speed_kn),
            "demand_kgf": demand,
            "door_spread_m": float(eng.doors.spread_m),
            "seabed_friction_kgf": float(eng.performance.seabed_friction_kgf),
        },
        "settings": {
            "net_id": case.net.id,
            "vessel_id": case.vessel.id,
            "door_id": case.door.id,
            "compat": case.compat.value,
            "resolution": resolution,
            "cn": DEFAULT_CN if cn is None else cn,
            "ct": DEFAULT_CT if ct is None else ct,
            "scenario": dataclasses.asdict(sc),
        },
        "estimated_s": estimate,
        "runtime_s": time.perf_counter() - t0,
    }
    jsonable: dict[str, Any] = to_jsonable(out)
    return jsonable


def fouling_catalogue() -> list[dict[str, Any]]:
    """Escenarios de ensuciamiento (``GET /catalog/fouling``)."""
    from trawlkit.sim import fouling_catalogue as cat

    return [f.to_dict() for f in cat()]


def _frame(r: Any) -> dict[str, Any]:
    """Posiciones (al cm), tensiones, ensuciamiento y apertura de malla de un estado."""
    import numpy as np

    out = {
        "nodes": np.round(r.nodes, 2).tolist(),
        "twine_tension_n": np.round(r.twine_tension_n, 1).tolist(),
        "bar_tension_n": np.round(r.bar_tension_n, 1).tolist(),
        "fouling_tri": np.round(r.fouling_tri, 3).tolist(),
    }
    if r.mesh is not None:
        out["opening_deg"] = np.round(r.mesh.opening_deg, 1).tolist()
        out["leg_i_mm"] = np.round(r.mesh.leg_i_mm, 2).tolist()
        out["leg_j_mm"] = np.round(r.mesh.leg_j_mm, 2).tolist()
        out["catch_fill"] = np.round(r.mesh.catch_fill, 3).tolist()
    return out


def _geometry(r: Any, model_warps: list[list[int]], doors: list[int]) -> dict[str, Any]:
    mesh: dict[str, Any] = {}
    if r.mesh is not None:
        mesh = {
            "tri_section": list(r.mesh.section),
            "tri_orientation": list(r.mesh.orientation),
            "tri_leg_mm": [round(float(v), 2) for v in r.mesh.leg_mm],
            "tri_twine_mm": [round(float(v), 3) for v in r.mesh.twine_mm],
            "tri_meshes": [round(float(v), 1) for v in r.mesh.meshes],
        }
    return {
        **mesh,
        "triangles": r.triangles.tolist(),
        "bars": r.bars.tolist(),
        "bar_kind": list(r.bar_kind),
        "headrope": r.headrope.tolist(),
        "footrope": r.footrope.tolist(),
        "float_nodes": r.float_nodes.tolist(),
        "wing_tips_upper": list(r.wing_tips_upper),
        "wing_tips_lower": list(r.wing_tips_lower),
        "doors": doors,
        "warps": model_warps,
    }


def explore_case(
    *,
    net: str | NetSpec = "fao_a3_standard",
    vessel: str | Vessel | None = None,
    door: str | Door | None = None,
    class_vessels: list[str] | None = None,
    compat: str = "corrected",
    variable: str,
    values: list[float],
    speed_kn: float = 3.0,
    resolution: int = 3,
    cn: float | None = None,
    ct: float | None = None,
    scenario: dict[str, Any] | None = None,
    include_geometry: bool = True,
    species: list[str] | None = None,
) -> dict[str, Any]:
    """Explorador (``POST /simulate/explore``): :func:`trawlkit.sim.explore` y el motor.

    Con ``species`` cada estado suma la selectividad del copo (L50, SR, SF) de cada especie.
    """
    import time

    import numpy as np

    from trawlkit.sim import DEFAULT_CN, DEFAULT_CT, explore
    from trawlkit.sim.core import rigging_from_result
    from trawlkit.sim.mesh import build_model

    t0 = time.perf_counter()
    sc = make_scenario(scenario or {})
    params = {"seabed": sc.seabed} if sc.seabed else {}
    case = build_case(
        net=net,
        vessel=vessel,
        door=door,
        class_vessels=class_vessels,
        compat=compat,
        params=params,
    )
    estimate = estimate_sim_cost(len(values), resolution, case.net, coupled=sc.coupled_doors)
    max_cost = sim_max_cost_s()
    if estimate > max_cost:
        raise BadRequestError(
            f"exploración demasiado costosa: ~{estimate:.0f} s estimados para {len(values)} "
            f"estados a resolución {resolution} (máximo {max_cost:.0f} s); baje la resolución "
            "o la cantidad de estados"
        )
    result = run_case(case)
    try:
        sims = explore(
            result,
            variable,
            values,
            speed_kn=speed_kn,
            scenario=sc,
            resolution=resolution,
            cn=DEFAULT_CN if cn is None else cn,
            ct=DEFAULT_CT if ct is None else ct,
        )
    except (ValueError, ZeroDivisionError, IndexError, FloatingPointError) as exc:
        raise BadRequestError(f"no se puede explorar: {exc}") from exc
    geometry = frames = None
    if include_geometry and sims:
        model = build_model(
            result.case.net,
            rigging_from_result(result),
            resolution=resolution,
            coupled_doors=sc.coupled_doors,
        )
        geometry = _geometry(
            sims[0], [w.tolist() for w in model.warp_nodes], [int(d) for d in model.doors]
        )
        frames = [_frame(r) for r in sims]
    speeds = sorted({*case.speeds_kn, float(speed_kn)})
    ref = dataclasses.replace(case, speeds_kn=tuple(speeds))
    try:
        eng = run(ref)
    except (ValueError, ZeroDivisionError, IndexError):
        eng = result
    ekn = np.asarray(eng.case.speeds_kn, dtype=float)
    demand = float(np.interp(speed_kn, ekn, np.asarray(eng.performance.demand.std, dtype=float)))
    _check_species(species or [])
    results = []
    for r in sims:
        d = r.to_dict(geometry=False)
        if species:
            d["selectivity"] = _selectivity_summary(r, species)
        results.append(d)
    out = {
        "variable": variable,
        "values": [float(v) for v in values],
        "results": results,
        "geometry": geometry,
        "frames": frames,
        "engine": {
            "speed_kn": float(speed_kn),
            "demand_kgf": demand,
            "door_spread_m": float(eng.doors.spread_m),
            "seabed_friction_kgf": float(eng.performance.seabed_friction_kgf),
        },
        "settings": {
            "net_id": case.net.id,
            "vessel_id": case.vessel.id,
            "door_id": case.door.id,
            "compat": case.compat.value,
            "resolution": resolution,
            "speed_kn": float(speed_kn),
            "cn": DEFAULT_CN if cn is None else cn,
            "ct": DEFAULT_CT if ct is None else ct,
            "scenario": dataclasses.asdict(sc),
        },
        "estimated_s": estimate,
        "runtime_s": time.perf_counter() - t0,
    }
    jsonable: dict[str, Any] = to_jsonable(out)
    return jsonable


# ---------------------------------------------------------------------------------------------
# Selectividad (Fase 11.3)
# ---------------------------------------------------------------------------------------------


def species_catalogue() -> list[dict[str, Any]]:
    """Especies con la forma de su sección transversal (``GET /catalog/species``)."""
    from trawlkit.selectivity import species_catalogue as cat

    return [s.to_dict() for s in cat()]


def _check_species(ids: list[str]) -> None:
    from trawlkit.selectivity import species

    for key in ids:
        try:
            species(key)
        except KeyError as exc:
            raise BadRequestError(str(exc)) from exc


def _selectivity_summary(r: Any, ids: list[str]) -> list[dict[str, Any]]:
    """L25, L50, L75, SR y SF por especie, sin la curva (para el explorador)."""
    from trawlkit.selectivity import selectivity

    out = []
    for c in selectivity(r, ids):
        d = c.to_dict(per_triangle=False)
        d.pop("lengths")
        d.pop("retention")
        out.append(d)
    return out


#: Variantes por defecto de ``POST /simulate/selectivity``: el copo de la red y el mismo en T90.
SELECTIVITY_DEFAULT_VARIANTS: tuple[dict[str, Any], ...] = (
    {"orientation": "diamond"},
    {"orientation": "t90"},
)


def selectivity_case(
    *,
    net: str | NetSpec = "fao_a3_standard",
    vessel: str | Vessel | None = None,
    door: str | Door | None = None,
    class_vessels: list[str] | None = None,
    compat: str = "corrected",
    speed_kn: float = 3.0,
    resolution: int = 3,
    cn: float | None = None,
    ct: float | None = None,
    scenario: dict[str, Any] | None = None,
    species: list[str] | None = None,
    variants: list[dict[str, Any]] | None = None,
    contact: float = 1.0,
    zone_length_m: float | None = 3.0,
    lengths: list[float] | None = None,
    include_geometry: bool = True,
) -> dict[str, Any]:
    """Selectividad del copo (``POST /simulate/selectivity``) para varias variantes de copo.

    Cada variante (orientación de malla, mallero, U1) es la red del pedido con el copo rehecho por
    :func:`trawlkit.selectivity.codend_variant` (mismo ancho y largo relingados); todas se simulan
    con la rigidez de apertura de la malla, para que la comparación sea pareja.
    """
    import time

    from trawlkit.selectivity import codend_variant, retention_curve, species_source
    from trawlkit.sim import DEFAULT_CN, DEFAULT_CT, simulate
    from trawlkit.sim.core import rigging_from_result
    from trawlkit.sim.mesh import build_model

    t0 = time.perf_counter()
    ids = list(species or ["hake_hubbsi"])
    _check_species(ids)
    vars_ = [dict(v) for v in (variants or SELECTIVITY_DEFAULT_VARIANTS)]
    sc = make_scenario({**(scenario or {}), "mesh_bending": True})
    params = {"seabed": sc.seabed} if sc.seabed else {}
    base = build_case(
        net=net,
        vessel=vessel,
        door=door,
        class_vessels=class_vessels,
        compat=compat,
        params=params,
    )
    estimate = estimate_sim_cost(len(vars_), resolution, base.net, coupled=sc.coupled_doors)
    max_cost = sim_max_cost_s()
    if estimate > max_cost:
        raise BadRequestError(
            f"selectividad demasiado costosa: ~{estimate:.0f} s estimados para {len(vars_)} "
            f"variantes a resolución {resolution} (máximo {max_cost:.0f} s); baje la resolución "
            "o la cantidad de variantes"
        )
    out_vars = []
    for v in vars_:
        orientation = str(v.get("orientation", "diamond"))
        mesh_mm = v.get("mesh_mm")
        hanging = v.get("hanging_ratio")
        try:
            spec = codend_variant(base.net, orientation, mesh_mm=mesh_mm, hanging_ratio=hanging)
            case = dataclasses.replace(base, net=spec)
            result = run_case(case)
            r = simulate(
                result,
                speed_kn,
                resolution=resolution,
                coarse_resolution=None,
                cn=DEFAULT_CN if cn is None else cn,
                ct=DEFAULT_CT if ct is None else ct,
                scenario=sc,
            )
        except (ValueError, ZeroDivisionError, IndexError, FloatingPointError) as exc:
            raise BadRequestError(f"no se puede simular la variante {v}: {exc}") from exc
        assert r.mesh is not None
        curves = [
            retention_curve(
                r.mesh, key, lengths, contact=contact, zone_length_m=zone_length_m
            ).to_dict()
            for key in ids
        ]
        codend = [p for p in spec.panels if p.section.value in ("codend", "extension")]
        entry: dict[str, Any] = {
            "label": v.get("label") or _variant_label(orientation, mesh_mm or codend[0].mesh_mm),
            "orientation": orientation,
            "mesh_mm": float(mesh_mm or codend[0].mesh_mm),
            "hanging_ratio": float(codend[0].hanging_ratio or 0.0),
            "codend_panels": [
                {
                    "id": p.id,
                    "meshes_top": p.meshes_top,
                    "meshes_bottom": p.meshes_bottom,
                    "meshes_depth": p.meshes_depth,
                    "mesh_mm": p.mesh_mm,
                    "hanging_ratio": p.hanging_ratio,
                    "mesh_orientation": str(p.mesh_orientation),
                }
                for p in codend
            ],
            "result": r.to_dict(geometry=False),
            "curves": curves,
        }
        if include_geometry:
            model = build_model(
                spec,
                rigging_from_result(result),
                resolution=resolution,
                coupled_doors=sc.coupled_doors,
            )
            entry["geometry"] = _geometry(
                r, [w.tolist() for w in model.warp_nodes], [int(d) for d in model.doors]
            )
            entry["frame"] = _frame(r)
        out_vars.append(entry)
    out = {
        "species": ids,
        "variants": out_vars,
        "settings": {
            "net_id": base.net.id,
            "vessel_id": base.vessel.id,
            "door_id": base.door.id,
            "compat": base.compat.value,
            "resolution": resolution,
            "speed_kn": float(speed_kn),
            "contact": contact,
            "zone_length_m": zone_length_m,
            "scenario": dataclasses.asdict(sc),
            "species_source": species_source(),
        },
        "estimated_s": estimate,
        "runtime_s": time.perf_counter() - t0,
    }
    jsonable: dict[str, Any] = to_jsonable(out)
    return jsonable


_ORIENTATION_LABEL = {"diamond": "Rombo", "t90": "T90", "square": "Cuadrada"}


def _variant_label(orientation: str, mesh_mm: float) -> str:
    return f"{_ORIENTATION_LABEL.get(orientation, orientation)} {mesh_mm:g} mm"


# ---------------------------------------------------------------------------------------------
# Incertidumbre, calibración y registros de sensores (Fase 11.4)
# ---------------------------------------------------------------------------------------------

#: Costo máximo estimado de los cálculos por lotes (incertidumbre, calibración) [s]
#: (``TRAWLKIT_MAX_BATCH_SECONDS``).
BATCH_MAX_COST_S = 120.0


def batch_max_cost_s() -> float:
    """Costo máximo estimado de ``/simulate/uncertainty`` y ``/simulate/calibrate`` [s]."""
    return _env_float("TRAWLKIT_MAX_BATCH_SECONDS", BATCH_MAX_COST_S)


#: Una muestra o evaluación con arranque en caliente cuesta una fracción de una simulación.
WARM_FACTOR = 0.5


def _guard(estimate: float, what: str) -> None:
    limit = batch_max_cost_s()
    if estimate > limit:
        raise BadRequestError(
            f"{what} demasiado costosa: ~{estimate:.0f} s estimados (máximo {limit:.0f} s); "
            "baje la resolución, las muestras o las evaluaciones"
        )


def _case_for(
    net: str | NetSpec,
    vessel: str | Vessel | None,
    door: str | Door | None,
    class_vessels: list[str] | None,
    compat: str,
    sc: Any,
) -> DesignCase:
    params = {"seabed": sc.seabed} if sc.seabed else {}
    return build_case(
        net=net,
        vessel=vessel,
        door=door,
        class_vessels=class_vessels,
        compat=compat,
        params=params,
    )


def uncertainty_case(
    *,
    net: str | NetSpec = "fao_a3_standard",
    vessel: str | Vessel | None = None,
    door: str | Door | None = None,
    class_vessels: list[str] | None = None,
    compat: str = "corrected",
    speed_kn: float = 3.0,
    resolution: int = 2,
    cn: float | None = None,
    ct: float | None = None,
    scenario: dict[str, Any] | None = None,
    samples: int = 10,
    seed: int = 0,
    inputs: list[dict[str, Any]] | None = None,
    species: list[str] | None = None,
) -> dict[str, Any]:
    """Incertidumbre (``POST /simulate/uncertainty``): :func:`trawlkit.sim.uncertainty`."""
    import time

    from trawlkit.sim import DEFAULT_CN, DEFAULT_CT
    from trawlkit.sim.uncertainty import default_inputs, uncertainty

    t0 = time.perf_counter()
    sc = make_scenario(scenario or {})
    _check_species(species or [])
    case = _case_for(net, vessel, door, class_vessels, compat, sc)
    cn_v = DEFAULT_CN if cn is None else cn
    ct_v = DEFAULT_CT if ct is None else ct
    inps = default_inputs(sc, cn_v, ct_v)
    if inputs:
        by_name = {i["name"]: i for i in inputs}
        for k, inp in enumerate(inps):
            if inp.name in by_name:
                lo, hi = float(by_name[inp.name]["low"]), float(by_name[inp.name]["high"])
                if not lo <= hi:
                    raise BadRequestError(f"rango inválido para {inp.name}")
                inps[k] = dataclasses.replace(inp, low=lo, high=hi, source="pedido")
    estimate = estimate_sim_cost(
        1 + int(WARM_FACTOR * samples), resolution, case.net, coupled=sc.coupled_doors
    )
    _guard(estimate, "incertidumbre")
    result = run_case(case)
    try:
        u = uncertainty(
            result,
            speed_kn,
            scenario=sc,
            inputs=inps,
            n=samples,
            seed=seed,
            resolution=resolution,
            cn=cn_v,
            ct=ct_v,
            species=species or [],
        )
    except (ValueError, ZeroDivisionError, IndexError, FloatingPointError) as exc:
        raise BadRequestError(f"no se puede calcular la incertidumbre: {exc}") from exc
    out = {
        "result": u.to_dict(),
        "settings": {
            "net_id": case.net.id,
            "vessel_id": case.vessel.id,
            "door_id": case.door.id,
            "compat": case.compat.value,
            "resolution": resolution,
            "speed_kn": float(speed_kn),
            "samples": samples,
            "seed": seed,
            "scenario": dataclasses.asdict(sc),
        },
        "estimated_s": estimate,
        "runtime_s": time.perf_counter() - t0,
    }
    jsonable: dict[str, Any] = to_jsonable(out)
    return jsonable


def calibrate_case(
    *,
    net: str | NetSpec = "fao_a3_standard",
    vessel: str | Vessel | None = None,
    door: str | Door | None = None,
    class_vessels: list[str] | None = None,
    compat: str = "corrected",
    resolution: int = 2,
    scenario: dict[str, Any] | None = None,
    reference: str | None = None,
    observations: list[dict[str, Any]] | None = None,
    params: list[str] | None = None,
    max_evals: int = 16,
) -> dict[str, Any]:
    """Calibración (``POST /simulate/calibrate``): :func:`trawlkit.sim.calibration.calibrate`."""
    import time

    from trawlkit.sim.calibration import Observation, calibrate, dynamit_observations

    t0 = time.perf_counter()
    sc = make_scenario(scenario or {})
    case = _case_for(net, vessel, door, class_vessels, compat, sc)
    try:
        obs = [Observation(**o) for o in (observations or [])]
    except (TypeError, ValueError) as exc:
        raise BadRequestError(f"observación inválida: {exc}") from exc
    if reference == "dynamit":
        if not _is_fao_a3_standard(case.net):
            raise BadRequestError("la referencia DynamiT es de la red FAO A-3 estándar sin editar")
        obs = dynamit_observations() + obs
    if not obs:
        raise BadRequestError("hacen falta observaciones o reference = 'dynamit'")
    states = len({(o.speed_kn, o.catch_kg) for o in obs})
    estimate = estimate_sim_cost(
        states * (1 + int(WARM_FACTOR * max_evals)), resolution, case.net, coupled=sc.coupled_doors
    )
    _guard(estimate, "calibración")
    result = run_case(case)
    try:
        c = calibrate(
            result,
            obs,
            params or ["cn", "door_cl_factor"],
            scenario=sc,
            resolution=resolution,
            max_evals=max_evals,
        )
    except (ValueError, ZeroDivisionError, IndexError, FloatingPointError) as exc:
        raise BadRequestError(f"no se puede calibrar: {exc}") from exc
    out = {
        "result": c.to_dict(),
        "settings": {
            "net_id": case.net.id,
            "vessel_id": case.vessel.id,
            "door_id": case.door.id,
            "compat": case.compat.value,
            "resolution": resolution,
            "reference": reference,
            "states": states,
            "scenario": dataclasses.asdict(sc),
        },
        "estimated_s": estimate,
        "runtime_s": time.perf_counter() - t0,
    }
    jsonable: dict[str, Any] = to_jsonable(out)
    return jsonable


def parse_sensors(
    csv: str, by: str = "speed", width: float = 0.25, min_rows: int = 5
) -> dict[str, Any]:
    """Registro de sensores a tramos y observaciones (``POST /sensors/parse``)."""
    from trawlkit.sensors import parse_log, to_observations, windows

    try:
        log = parse_log(csv)
        ws = windows(log, by=by, width=width, min_rows=min_rows)
    except ValueError as exc:
        raise BadRequestError(f"registro inválido: {exc}") from exc
    return {
        "log": log.to_dict(),
        "windows": [w.to_dict() for w in ws],
        "observations": [o.to_dict() for o in to_observations(ws)],
    }


def sensor_example() -> str:
    """CSV de ejemplo (sintético) de ``GET /sensors/example``."""
    from trawlkit.sensors import example_log

    return example_log()
