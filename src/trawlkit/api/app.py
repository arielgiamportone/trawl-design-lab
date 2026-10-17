"""Aplicación FastAPI: catálogos, cálculo de casos, planos e informes."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from trawlkit import __version__
from trawlkit.api import service
from trawlkit.api.schemas import (
    CatalogItem,
    DesignRequest,
    DesignResponse,
    ErratumOut,
    Health,
    OptimizeRequest,
    OptimizeResponse,
    ParamInfo,
    PlanView,
    ReportFormat,
    ScaledNetRequest,
    SimulateRequest,
    SimulateResponse,
    Variant,
)
from trawlkit.compat import ERRATA
from trawlkit.io.schema import Door, NetSpec, Vessel
from trawlkit.model import DesignResult

app = FastAPI(
    title="trawlkit API",
    version=__version__,
    description="Diseño y dimensionamiento de redes de arrastre (motor trawlkit).",
)

_origins = [o.strip() for o in os.environ.get("TRAWLKIT_CORS_ORIGINS", "*").split(",") if o]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(service.BadRequestError)
async def _bad_request(_: Request, exc: service.BadRequestError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(service.NotFoundError)
async def _not_found(_: Request, exc: service.NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.args[0]})


@app.get("/health", response_model=Health)
def health() -> Health:
    """Comprobación de vida."""
    return Health(status="ok", version=__version__)


@app.get("/catalog/nets", response_model=list[CatalogItem])
def list_nets() -> list[CatalogItem]:
    """Redes predefinidas."""
    return [
        CatalogItem(id=k, name=v.name, description=v.description)
        for k, v in service.net_presets().items()
    ]


@app.get("/catalog/nets/{net_id}", response_model=NetSpec)
def get_net(net_id: str) -> NetSpec:
    """Especificación completa de una red predefinida (paneles, relingas, boyas)."""
    presets = service.net_presets()
    if net_id not in presets:
        raise HTTPException(404, f"red desconocida: {net_id!r}")
    return presets[net_id]


@app.get("/catalog/vessels", response_model=list[Vessel])
def list_vessels() -> list[Vessel]:
    """Buques del catálogo."""
    return list(service.vessel_presets().values())


@app.get("/catalog/doors", response_model=list[Door])
def list_doors() -> list[Door]:
    """Portones del catálogo con su polar CL/CD."""
    return list(service.door_presets().values())


@app.get("/params", response_model=list[ParamInfo])
def list_params() -> list[dict[str, Any]]:
    """Parámetros de diseño sobrescribibles en ``DesignRequest.params``."""
    return service.params_info()


@app.get("/errata", response_model=list[ErratumOut])
def list_errata() -> list[ErratumOut]:
    """Erratas del libro Excel original."""
    return [
        ErratumOut(key=e.key, sheet=e.sheet, cell=e.cell, description=e.description) for e in ERRATA
    ]


def _run(req: DesignRequest) -> DesignResult:
    case = service.build_case(
        net=req.net,
        net_modified=req.net_modified,
        vessel=req.vessel,
        door=req.door,
        class_vessels=req.class_vessels,
        compat=req.compat,
        params=req.params,
    )
    return service.run_case(case)


@app.post("/design", response_model=DesignResponse)
def design(req: DesignRequest) -> dict[str, Any]:
    """Calcula un caso de diseño completo."""
    result = _run(req)
    return {
        "case": service.to_jsonable(result.case.to_dict()),
        "summary": service.to_jsonable(result.summary()),
        "notes": list(result.notes),
        "result": service.to_jsonable(result.to_dict()),
    }


@app.post(
    "/design/plan", response_class=Response, responses={200: {"content": {"image/svg+xml": {}}}}
)
def design_plan(req: DesignRequest, view: PlanView = "sheet", variant: Variant = "std") -> Response:
    """Plano SVG del caso: lámina técnica (``sheet``) o escala real (``scale``)."""
    from trawlkit.drawing import net_scale_svg, net_sheet_svg

    if variant == "mod" and req.net_modified is None:
        raise HTTPException(422, "variant 'mod' requiere net_modified")
    result = _run(req)
    svg = (net_sheet_svg if view == "sheet" else net_scale_svg)(result, variant)
    return Response(svg, media_type="image/svg+xml")


@app.post("/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest) -> dict[str, Any]:
    """Optimiza la escala de la red y la velocidad de arrastre (malla + evolución diferencial)."""
    return service.optimize_case(
        net=req.net,
        vessel=req.vessel,
        door=req.door,
        class_vessels=req.class_vessels,
        objective=req.objective,
        margin=req.margin,
        s_bounds=req.s_bounds,
        v_bounds=req.v_bounds,
        grid=(req.grid.n_s, req.grid.n_v),
        refine=req.refine,
        seed=req.seed,
        propeller=req.propeller,
        door_angle=req.door_angle,
    )


@app.post("/optimize/scaled-net", response_model=NetSpec)
def optimize_scaled_net(req: ScaledNetRequest) -> NetSpec:
    """Red escalada por ``s`` (mismas mallas y materiales), para usar el diseño optimizado."""
    return service.scaled_net(req.net, req.s)


@app.post("/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest) -> dict[str, Any]:
    """Simula la forma de equilibrio de la red a varias velocidades (experimental)."""
    return service.simulate_case(
        net=req.net,
        vessel=req.vessel,
        door=req.door,
        class_vessels=req.class_vessels,
        compat=req.compat,
        speeds_kn=req.speeds_kn,
        resolution=req.resolution,
        cn=req.cn,
        ct=req.ct,
        knot_factor=req.knot_factor,
        door_spread_m=req.door_spread_m,
        include_geometry=req.include_geometry,
    )


_MEDIA = {
    "html": "text/html; charset=utf-8",
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


@app.post(
    "/design/report",
    response_class=Response,
    responses={200: {"content": {m: {} for m in _MEDIA.values()}}},
)
def design_report(req: DesignRequest, format: ReportFormat = "html") -> Response:  # noqa: A002
    """Informe del caso en HTML, PDF o XLSX."""
    from trawlkit.report.build import build_report

    result = _run(req)
    with tempfile.TemporaryDirectory() as tmp:
        try:
            paths = build_report(result, tmp, (format,))
        except RuntimeError as exc:  # extra 'report' no instalado
            raise HTTPException(501, str(exc)) from exc
        path = next(p for p in paths if p.suffix == f".{format}")
        content = Path(path).read_bytes()
    headers = {"Content-Disposition": f'attachment; filename="informe.{format}"'}
    if format == "html":
        headers = {}
    return Response(content, media_type=_MEDIA[format], headers=headers)
