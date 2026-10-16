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
    """Redes disponibles en ``data/*.yaml`` (sólo los archivos que validan como ``NetSpec``)."""
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


def _net(value: str | NetSpec | None) -> NetSpec | None:
    if value is None or isinstance(value, NetSpec):
        return value
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
