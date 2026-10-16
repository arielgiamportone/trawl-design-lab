"""Esquemas de entrada y salida de la API (contrato estable para el frontend)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from trawlkit.io.schema import Door, NetSpec, Vessel


class DesignRequest(BaseModel):
    """Caso de diseño a calcular.

    ``net``, ``net_modified``, ``vessel`` y ``door`` aceptan el id de un preset del catálogo
    (``GET /catalog/...``) o la especificación completa en línea (para redes editadas en el
    frontend). ``class_vessels`` son ids del catálogo; si se omite, se usa el resto del catálogo
    como hace el Excel con 150 y 180 HP. ``params`` sobrescribe parámetros de ``DesignCase``
    (ver ``GET /params``).
    """

    model_config = ConfigDict(extra="forbid")

    net: str | NetSpec = "fao_a3_standard"
    net_modified: str | NetSpec | None = None
    vessel: str | Vessel | None = None
    door: str | Door | None = None
    class_vessels: list[str] | None = None
    compat: Literal["excel", "corrected"] = "corrected"
    params: dict[str, Any] = Field(default_factory=dict)


class DesignResponse(BaseModel):
    """Resultado de ``POST /design``."""

    case: dict[str, Any]
    summary: dict[str, Any]
    notes: list[str]
    result: dict[str, Any]


class CatalogItem(BaseModel):
    """Entrada resumida de un catálogo."""

    id: str
    name: str | None = None
    description: str | None = None


class ParamInfo(BaseModel):
    """Parámetro sobrescribible de ``DesignCase``."""

    name: str
    type: str
    default: Any
    comment: str = ""


class ErratumOut(BaseModel):
    """Errata del modelo Excel original."""

    key: str
    sheet: str
    cell: str
    description: str


class Health(BaseModel):
    """Estado del servicio."""

    status: str
    version: str


PlanView = Literal["sheet", "scale"]
Variant = Literal["std", "mod"]
ReportFormat = Literal["html", "pdf", "xlsx"]
