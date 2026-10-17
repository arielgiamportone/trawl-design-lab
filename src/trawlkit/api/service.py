"""Lógica de la API independiente de HTTP: catálogos, armado del caso y serialización."""

from __future__ import annotations

import dataclasses
import inspect
import math
import re
from functools import cache
from typing import Any

import yaml
from pydantic import ValidationError

from trawlkit.compat import Compat
from trawlkit.io import DATA_DIR, load_doors, load_net, load_vessels
from trawlkit.io.schema import Door, NetSpec, Vessel
from trawlkit.model import DesignCase, DesignResult, run

#: Campos de ``DesignCase`` que no se sobrescriben vía ``params`` (tienen su propio campo).
_STRUCTURAL = {"net", "net_modified", "vessel", "door", "class_vessels", "compat"}


class BadRequestError(ValueError):
    """Error de entrada del cliente (se traduce a HTTP 422)."""


class NotFoundError(KeyError):
    """Id desconocido en un catálogo (se traduce a HTTP 404)."""


@cache
def net_presets() -> dict[str, NetSpec]:
    """Redes de ``trawlkit/data/*.yaml`` (sólo los archivos que validan como ``NetSpec``)."""
    out: dict[str, NetSpec] = {}
    for path in sorted(DATA_DIR.glob("*.yaml")):
        with path.open(encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        if not isinstance(raw, dict) or "panels" not in raw:
            continue
        try:
            spec = NetSpec.model_validate(raw)
        except ValidationError:
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
#: Costo máximo estimado que acepta ``POST /simulate`` [s].
SIM_MAX_COST_S = 30.0


def _net_length_m(spec: NetSpec) -> float:
    """Largo estirado aproximado de la red: Σ mallas de alto × mallero de cada panel [m]."""
    return sum(float(p.meshes_depth) * float(p.mesh_mm) for p in spec.panels) / 1000.0


def estimate_sim_cost(n_speeds: int, resolution: int, net: NetSpec | None = None) -> float:
    """Tiempo estimado de una simulación [s]: costo por velocidad × velocidades × tamaño.

    La grilla tiene ``resolution`` filas cada 9 m de red, así que el costo crece con el largo de
    la red; se escala con (largo / largo de la FAO A-3)^1,5, como mínimo 0,5.
    """
    per = SIM_COST_PER_SPEED_S[max(min(resolution, 10), 2)]
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
) -> dict[str, Any]:
    """Corre el motor y :func:`trawlkit.sim.sweep`, y arma la respuesta de ``POST /simulate``.

    Las velocidades se simulan en orden creciente (cada una parte de la forma de la anterior) y
    se devuelven en el orden pedido. Las proyecciones son de las ``max_projections`` primeras
    velocidades pedidas. Si la red es la FAO A-3 estándar, ``dynamit_comparison`` compara con la
    simulación DynamiT en las velocidades de su tabla.
    """
    import time

    import numpy as np

    from trawlkit.sim import DEFAULT_CN, DEFAULT_CT, sweep
    from trawlkit.sim.render import projections_svg
    from trawlkit.sim.validation import DYNAMIT

    t0 = time.perf_counter()
    case = build_case(net=net, vessel=vessel, door=door, class_vessels=class_vessels, compat=compat)
    estimate = estimate_sim_cost(len(speeds_kn), resolution, case.net)
    if estimate > SIM_MAX_COST_S:
        raise BadRequestError(
            f"simulación demasiado costosa: ~{estimate:.0f} s estimados para "
            f"{len(speeds_kn)} velocidades a resolución {resolution} (máximo "
            f"{SIM_MAX_COST_S:.0f} s); baje la resolución o la cantidad de velocidades"
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
        },
        "estimated_s": estimate,
        "runtime_s": time.perf_counter() - t0,
    }
    jsonable: dict[str, Any] = to_jsonable(out)
    return jsonable
