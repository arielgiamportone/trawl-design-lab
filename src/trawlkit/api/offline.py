"""La API sin servidor: las rutas del cálculo para el motor en el navegador (Pyodide, Fase 13).

:func:`handle` atiende un pedido ``(método, ruta, cuerpo)`` como lo haría la API FastAPI
(:mod:`trawlkit.api.app`) y devuelve ``(estado HTTP, cuerpo JSON)``, sin FastAPI ni red: la app
web lo usa desde un *Web Worker* cuando no hay conexión. Cubre los catálogos, el diseño, la
lista de materiales, el armado con componentes, el validador de aportes, la disposición 2D, la
optimización por malla, los lotes (Fase 14), la guía de construcción (Fase 15; sus PDF, no), la
economía de la operación (Fase 16) y el banco de ejercicios y los laboratorios (Fase 17).
Lo demás (simulación, informes, planos SVG, incertidumbre) devuelve 503 con un mensaje que
lo explica.

Usa los mismos modelos de pedido y respuesta que la API (:mod:`trawlkit.api.schemas`) y las
mismas funciones de :mod:`trawlkit.api.service`; ``tests/test_offline.py`` compara cada ruta con
la API.
"""

from __future__ import annotations

import base64
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
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
    "teléfono). El diseño, la lista de materiales, el armado con componentes y la guía de "
    "construcción sí."
)

M = TypeVar("M", bound=BaseModel)
Query = dict[str, list[str]]
Handler = Callable[[re.Match[str], Query, Any], Any]


@dataclass(frozen=True)
class Binary:
    """Respuesta que no es JSON (planillas, CSV, HTML): contenido, tipo MIME y nombre."""

    data: bytes
    media: str
    filename: str


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


def _guide_args(query: Query) -> tuple[str, float]:
    variant = _q(query, "variant", "std") or "std"
    try:
        eye = float(_q(query, "eye_allowance_m", "0.5") or 0.5)
    except ValueError as exc:
        raise _HTTPError(422, "eye_allowance_m debe ser un número") from exc
    return variant, eye


def _construction(_m: re.Match[str], query: Query, body: Any) -> Any:
    req = _body(sc.DesignRequest, body)
    variant, eye = _guide_args(query)
    with service.user_items(req.components):
        out = service.construction_guide(_build(req), variant, eye)
    return _dump(sc.ConstructionGuideOut, out)


def _construction_export(_m: re.Match[str], query: Query, body: Any) -> Any:
    req = _body(sc.DesignRequest, body)
    variant, eye = _guide_args(query)
    fmt = _q(query, "format", "pdf") or "pdf"
    if fmt == "pdf":
        raise _HTTPError(503, "el PDF de la guía necesita conexión: use format=html e imprímalo")
    with service.user_items(req.components):
        data, media, name = service.construction_export(_build(req), variant, eye, fmt)
    return Binary(data, media, name)


def _economics(_m: re.Match[str], _q_: Query, body: Any) -> Any:
    req = _body(sc.EconomicsRequest, body)
    with service.user_items(req.components):
        out = service.economics_case(_build(req), req.model_dump(mode="json"))
    return _dump(sc.EconomicsOut, out)


def _economics_compare(_m: re.Match[str], _q_: Query, body: Any) -> Any:
    req = _body(sc.EconomicsCompareRequest, body)
    cases = []
    for c in req.cases:
        with service.user_items(c.case.components):
            cases.append((c.label, _build(c.case), c.gear_cost))
    return _dump(
        sc.EconomicsCompareOut, service.economics_compare(cases, req.model_dump(mode="json"))
    )


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


def _batch_parse(_m: re.Match[str], _q_: Query, body: Any) -> Any:
    req = _body(sc.BatchParseRequest, body)
    return _dump(sc.BatchParseResponse, service.batch_parse(req.file.model_dump(), req.mode))


def _batch_run(_m: re.Match[str], _q_: Query, body: Any) -> Any:
    req = _body(sc.BatchRunRequest, body)
    return _dump(sc.BatchRunResponse, service.batch_run(req.model_dump(mode="json")))


def _batch_export(_m: re.Match[str], query: Query, body: Any) -> Any:
    req = _body(sc.BatchRunRequest, body)
    fmt = _q(query, "format", "xlsx") or "xlsx"
    if fmt == "pdf":
        # WeasyPrint sólo corre en el servidor; sin conexión, el informe HTML se imprime.
        raise _HTTPError(503, "el PDF del lote necesita conexión: use format=html e imprímalo")
    data, media, name = service.batch_export(req.model_dump(mode="json"), fmt)
    return Binary(data, media, name)


def _batch_template(_m: re.Match[str], query: Query, _b: Any) -> Any:
    kind = _q(query, "kind", "fleet") or "fleet"
    fmt = _q(query, "format", "xlsx") or "xlsx"
    if kind not in ("fleet", "nets", "cases") or fmt not in ("xlsx", "csv"):
        raise _HTTPError(422, "kind: fleet, nets o cases; format: xlsx o csv")
    data, media, name = service.batch_template(kind, fmt)
    return Binary(data, media, name)


def _teaching_exercises(_m: re.Match[str], query: Query, _b: Any) -> Any:
    level = _q(query, "level")
    if level is not None and level not in ("basico", "intermedio", "avanzado"):
        raise _HTTPError(422, "level: basico, intermedio o avanzado")
    out = service.teaching_exercises(_q(query, "chapter"), level, _q(query, "topic"))
    return _dump(list[sc.ExerciseSummaryOut], out)


def _teaching_exercise(m: re.Match[str], query: Query, _b: Any) -> Any:
    raw = _q(query, "seed", "0") or "0"
    try:
        seed = int(raw)
    except ValueError:
        raise _HTTPError(422, "seed: entero") from None
    if not 0 <= seed <= 2**31 - 1:
        raise _HTTPError(422, "seed: entre 0 y 2³¹ − 1")
    return _dump(sc.ExerciseInstanceOut, service.teaching_exercise(unquote(m["id"]), seed))


def _teaching_grade(_m: re.Match[str], _q_: Query, body: Any) -> Any:
    req = _body(sc.GradeRequest, body)
    return _dump(sc.GradeOut, service.teaching_grade(req.id, req.seed, dict(req.answers)))


def _teaching_labs(_m: re.Match[str], query: Query, _b: Any) -> Any:
    level = _q(query, "level")
    if level is not None and level not in ("basico", "intermedio", "avanzado"):
        raise _HTTPError(422, "level: basico, intermedio o avanzado")
    return _dump(list[sc.LabSummaryOut], service.teaching_labs(_q(query, "chapter"), level))


def _teaching_lab(m: re.Match[str], _q_: Query, _b: Any) -> Any:
    return _dump(sc.LabOut, service.teaching_lab(unquote(m["id"])))


def _teaching_lab_check(_m: re.Match[str], _q_: Query, body: Any) -> Any:
    req = _body(sc.LabCheckRequest, body)
    out = service.teaching_lab_check(
        req.lab_id, req.step_id, req.design.model_dump(mode="json"), dict(req.answers)
    )
    return _dump(sc.LabStepResultOut, out)


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
    ("POST", re.compile(r"/design/construction"), _construction),
    ("POST", re.compile(r"/design/construction/export"), _construction_export),
    ("POST", re.compile(r"/components/check"), _check),
    ("POST", re.compile(r"/economics"), _economics),
    ("POST", re.compile(r"/economics/compare"), _economics_compare),
    ("POST", re.compile(r"/optimize"), _optimize),
    ("POST", re.compile(r"/optimize/components"), _optimize_components),
    ("POST", re.compile(r"/optimize/scaled-net"), _scaled_net),
    ("POST", re.compile(r"/batch/parse"), _batch_parse),
    ("POST", re.compile(r"/batch/run"), _batch_run),
    ("POST", re.compile(r"/batch/export"), _batch_export),
    ("GET", re.compile(r"/batch/template"), _batch_template),
    ("GET", re.compile(r"/teaching/exercises"), _teaching_exercises),
    ("GET", re.compile(rf"/teaching/exercises/{_ID}"), _teaching_exercise),
    ("POST", re.compile(r"/teaching/grade"), _teaching_grade),
    ("GET", re.compile(r"/teaching/labs"), _teaching_labs),
    ("GET", re.compile(rf"/teaching/labs/{_ID}"), _teaching_lab),
    ("POST", re.compile(r"/teaching/labs/check"), _teaching_lab_check),
]


def supports(method: str, path: str) -> bool:
    """Si la ruta se puede atender sin servidor."""
    route = urlsplit(path).path
    return any(m == method.upper() and p.fullmatch(route) for m, p, _ in ROUTES)


def handle(method: str, path: str, body: Any = None) -> tuple[int, Any]:
    """Atiende un pedido como la API: ``(estado HTTP, cuerpo JSON o :class:`Binary`)``.

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
    """:func:`handle` con entrada y salida en texto JSON (lo que pasa por el *worker*).

    Una respuesta binaria va en base64: ``{"status", "binary", "media", "filename"}``.
    """
    status, out = handle(method, path, body)
    if isinstance(out, Binary):
        payload: dict[str, Any] = {
            "status": status,
            "binary": base64.b64encode(out.data).decode("ascii"),
            "media": out.media,
            "filename": out.filename,
        }
        return json.dumps(payload)
    return json.dumps({"status": status, "body": out}, ensure_ascii=False, allow_nan=False)


__all__ = ["NEEDS_SERVER", "ROUTES", "Binary", "handle", "handle_json", "supports"]
