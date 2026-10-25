"""La API sin servidor: las rutas del cálculo para el motor en el navegador (Pyodide, Fase 13).

:func:`handle` atiende un pedido ``(método, ruta, cuerpo)`` como lo haría la API FastAPI
(:mod:`trawlkit.api.app`) y devuelve ``(estado HTTP, cuerpo JSON)``, sin FastAPI ni red: la app
web lo usa desde un *Web Worker* cuando no hay conexión. Cubre los catálogos, el diseño, la
lista de materiales, el armado con componentes, el validador de aportes, la disposición 2D y la
optimización por malla. Lo demás (simulación, informes, planos SVG, incertidumbre) devuelve 503
con un mensaje que lo explica.

Usa los mismos modelos de pedido y respuesta que la API (:mod:`trawlkit.api.schemas`) y las
mismas funciones de :mod:`trawlkit.api.service`; ``tests/test_offline.py`` compara cada ruta con
la API.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any, TypeVar
from urllib.parse import parse_qs, unquote, urlsplit

from pydantic import BaseModel, TypeAdapter, ValidationError

from trawlkit import __version__
from trawlkit.api import schemas as sc
from trawlkit.api import service
from trawlkit.compat import ERRATA
from trawlkit.io.schema import Door, NetSpec, Vessel

#: Mensaje de las rutas que necesitan el servidor.
NEEDS_SERVER = (
    "Esta función necesita conexión con la API (simulación, informes y planos no corren en el "
    "teléfono). El diseño, la lista de materiales y el armado con componentes sí."
)

M = TypeVar("M", bound=BaseModel)
Query = dict[str, list[str]]
Handler = Callable[[re.Match[str], Query, Any], Any]


class _HTTPError(Exception):
    def __init__(self, status: int, detail: Any) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


def _dump(model: Any, value: Any) -> Any:
    """Serializa como ``response_model`` de FastAPI (validación y JSON con alias)."""
    adapter: TypeAdapter[Any] = TypeAdapter(model)
    return adapter.dump_python(adapter.validate_python(value), mode="json", by_alias=True)


def _body(model: type[M], body: Any) -> M:
    try:
        return model.model_validate(body if body is not None else {})
    except ValidationError as exc:
        detail = [
            {"loc": ["body", *e["loc"]], "msg": e["msg"], "type": e["type"]} for e in exc.errors()
        ]
        raise _HTTPError(422, detail) from exc


def _q(query: Query, key: str, default: str | None = None) -> str | None:
    vals = query.get(key)
    return vals[-1] if vals else default


# -- rutas GET ---------------------------------------------------------------------------------


def _health(_m: re.Match[str], _q_: Query, _b: Any) -> Any:
    service.net_presets()
    failed = sorted(service.NET_LOAD_ERRORS) or None
    return _dump(
        sc.Health,
        {"status": "ok", "version": __version__, "contract": None, "nets_failed": failed},
    )


def _nets(_m: re.Match[str], query: Query, _b: Any) -> Any:
    status = _q(query, "status", "all")
    items = service.catalog_items()
    if status != "all":
        items = [it for it in items if (it["status"] or "published") == status]
    return _dump(list[sc.CatalogItem], items)


def _net(m: re.Match[str], _q_: Query, _b: Any) -> Any:
    presets = service.net_presets()
    net_id = unquote(m["id"])
    if net_id not in presets:
        raise _HTTPError(404, f"red desconocida: {net_id!r}")
    return _dump(NetSpec, presets[net_id])


def _net_prov(m: re.Match[str], _q_: Query, _b: Any) -> Any:
    return _dump(list[sc.ProvenanceRow], service.net_provenance(unquote(m["id"])))


def _net_check(m: re.Match[str], _q_: Query, _b: Any) -> Any:
    return _dump(sc.NetCheckOut, service.net_check(unquote(m["id"])))


def _component_kinds(_m: re.Match[str], _q_: Query, _b: Any) -> Any:
    return _dump(list[sc.ComponentKindOut], service.component_kinds())


def _component_list(m: re.Match[str], query: Query, _b: Any) -> Any:
    return service.component_list(
        unquote(m["kind"]),
        brand=query.get("brand") or None,
        region=_q(query, "region"),
        generic_only=(_q(query, "generic", "false") or "").lower() in ("1", "true", "yes"),
        status=_q(query, "status", "published") or "published",
    )


def _component(m: re.Match[str], _q_: Query, _b: Any) -> Any:
    return service.component_get(unquote(m["kind"]), unquote(m["id"]))


def _vessels(_m: re.Match[str], _q_: Query, _b: Any) -> Any:
    return _dump(list[Vessel], list(service.vessel_presets().values()))


def _doors(_m: re.Match[str], _q_: Query, _b: Any) -> Any:
    return _dump(list[Door], list(service.door_presets().values()))


def _params(_m: re.Match[str], _q_: Query, _b: Any) -> Any:
    return _dump(list[sc.ParamInfo], service.params_info())


def _errata(_m: re.Match[str], _q_: Query, _b: Any) -> Any:
    return [
        {"key": e.key, "sheet": e.sheet, "cell": e.cell, "description": e.description}
        for e in ERRATA
    ]


def _seabeds(_m: re.Match[str], _q_: Query, _b: Any) -> Any:
    return _dump(list[sc.SeabedOut], service.seabed_catalogue())


# -- rutas POST --------------------------------------------------------------------------------


def _build(req: sc.DesignRequest) -> Any:
    return service.build_case(
        net=req.net,
        net_modified=req.net_modified,
        vessel=req.vessel,
        door=req.door,
        class_vessels=req.class_vessels,
        compat=req.compat,
        params=req.params,
    )


def _design(_m: re.Match[str], _q_: Query, body: Any) -> Any:
    req = _body(sc.DesignRequest, body)
    with service.user_items(req.components):
        result = service.run_case(_build(req))
    out = {
        "case": service.to_jsonable(result.case.to_dict()),
        "summary": service.to_jsonable(result.summary()),
        "notes": list(result.notes),
        "result": service.to_jsonable(result.to_dict()),
    }
    return _dump(sc.DesignResponse, out)


def _bom(_m: re.Match[str], _q_: Query, body: Any) -> Any:
    req = _body(sc.BomRequest, body)
    with service.user_items(req.components):
        out = service.design_bom(_build(req), {k: v.model_dump() for k, v in req.prices.items()})
    return _dump(sc.BomOut, out)


def _layout(_m: re.Match[str], query: Query, body: Any) -> Any:
    req = _body(sc.DesignRequest, body)
    variant = _q(query, "variant", "std")
    mode = _q(query, "mode", "schematic") or "schematic"
    if variant == "mod" and req.net_modified is None:
        raise _HTTPError(422, "variant 'mod' requiere net_modified")
    net = req.net_modified if variant == "mod" else req.net
    assert net is not None
    return _dump(sc.LayoutResponse, service.layout_of(net, mode))


def _check(_m: re.Match[str], _q_: Query, body: Any) -> Any:
    req = _body(sc.ComponentCheckRequest, body)
    return _dump(sc.ComponentCheckOut, service.component_check(req.model_dump()))


def _optimize_components(_m: re.Match[str], _q_: Query, body: Any) -> Any:
    req = _body(sc.ComponentOptimizeRequest, body)
    with service.user_items(req.components):
        case = service.build_case(
            net=req.net,
            vessel=req.vessel,
            door=req.door,
            class_vessels=req.class_vessels,
            params=req.params,
        )
        out = service.optimize_components_case(
            case,
            objective=req.objective,
            speed_kn=req.speed_kn,
            v_bounds=req.v_bounds,
            margin=req.margin,
            doors=req.doors,
            floats=req.floats,
            twines=req.twines,
            prices={k: v.model_dump() for k, v in req.prices.items()},
            currency=req.currency,
            max_doors=req.max_doors,
            max_floats=req.max_floats,
            max_twines=req.max_twines,
        )
    return _dump(sc.ComponentOptimizeResponse, out)


def _optimize(_m: re.Match[str], _q_: Query, body: Any) -> Any:
    req = _body(sc.OptimizeRequest, body)
    if req.refine:
        # La evolución diferencial usa scipy, que no se descarga en el teléfono.
        raise _HTTPError(422, "sin conexión se optimiza sólo con la malla (refine = false)")
    out = service.optimize_case(
        net=req.net,
        vessel=req.vessel,
        door=req.door,
        class_vessels=req.class_vessels,
        objective=req.objective,
        margin=req.margin,
        s_bounds=req.s_bounds,
        v_bounds=req.v_bounds,
        grid=(req.grid.n_s, req.grid.n_v),
        refine=False,
        seed=req.seed,
        propeller=req.propeller,
        door_angle=req.door_angle,
    )
    return _dump(sc.OptimizeResponse, out)


def _scaled_net(_m: re.Match[str], _q_: Query, body: Any) -> Any:
    req = _body(sc.ScaledNetRequest, body)
    return _dump(NetSpec, service.scaled_net(req.net, req.s))


_ID = r"(?P<id>[^/]+)"
_KIND = r"(?P<kind>[^/]+)"

#: (método, patrón de la ruta, función).
ROUTES: list[tuple[str, re.Pattern[str], Handler]] = [
    ("GET", re.compile(r"/health"), _health),
    ("GET", re.compile(r"/catalog/nets"), _nets),
    ("GET", re.compile(rf"/catalog/nets/{_ID}"), _net),
    ("GET", re.compile(rf"/catalog/nets/{_ID}/provenance"), _net_prov),
    ("GET", re.compile(rf"/catalog/nets/{_ID}/check"), _net_check),
    ("GET", re.compile(r"/catalog/components"), _component_kinds),
    ("GET", re.compile(rf"/catalog/components/{_KIND}"), _component_list),
    ("GET", re.compile(rf"/catalog/components/{_KIND}/{_ID}"), _component),
    ("GET", re.compile(r"/catalog/vessels"), _vessels),
    ("GET", re.compile(r"/catalog/doors"), _doors),
    ("GET", re.compile(r"/catalog/seabeds"), _seabeds),
    ("GET", re.compile(r"/params"), _params),
    ("GET", re.compile(r"/errata"), _errata),
    ("POST", re.compile(r"/design"), _design),
    ("POST", re.compile(r"/design/bom"), _bom),
    ("POST", re.compile(r"/design/layout"), _layout),
    ("POST", re.compile(r"/components/check"), _check),
    ("POST", re.compile(r"/optimize"), _optimize),
    ("POST", re.compile(r"/optimize/components"), _optimize_components),
    ("POST", re.compile(r"/optimize/scaled-net"), _scaled_net),
]


def supports(method: str, path: str) -> bool:
    """Si la ruta se puede atender sin servidor."""
    route = urlsplit(path).path
    return any(m == method.upper() and p.fullmatch(route) for m, p, _ in ROUTES)


def handle(method: str, path: str, body: Any = None) -> tuple[int, Any]:
    """Atiende un pedido como la API: ``(estado HTTP, cuerpo JSON)``.

    ``path`` puede llevar la consulta (``/catalog/components/wire?generic=true``); ``body`` es el
    cuerpo ya decodificado (o el texto JSON).
    """
    parts = urlsplit(path)
    query = parse_qs(parts.query)
    if isinstance(body, str):
        body = json.loads(body) if body else None
    for m, pattern, fn in ROUTES:
        if m != method.upper():
            continue
        match = pattern.fullmatch(parts.path)
        if match is None:
            continue
        try:
            return 200, fn(match, query, body)
        except _HTTPError as exc:
            return exc.status, {"detail": exc.detail}
        except service.NotFoundError as exc:
            return 404, {"detail": exc.args[0]}
        except service.BadRequestError as exc:
            return 422, {"detail": str(exc)}
    if any(p.fullmatch(parts.path) for _, p, _ in ROUTES):
        return 405, {"detail": "Method Not Allowed"}
    return 503, {"detail": NEEDS_SERVER}


def handle_json(method: str, path: str, body: str | None = None) -> str:
    """:func:`handle` con entrada y salida en texto JSON (lo que pasa por el *worker*)."""
    status, out = handle(method, path, body)
    return json.dumps({"status": status, "body": out}, ensure_ascii=False, allow_nan=False)


__all__ = ["NEEDS_SERVER", "ROUTES", "handle", "handle_json", "supports"]
