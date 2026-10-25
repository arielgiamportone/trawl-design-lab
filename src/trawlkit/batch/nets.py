"""Redes (planos) desde una planilla de paneles, y de vuelta a planilla (Fase 14).

Hoja de paneles (:data:`~trawlkit.batch.columns.PANELS`): un panel por fila, con la red a la que
pertenece (columna ``red``; si falta, el nombre de la hoja). Hoja ``red`` opcional
(:data:`~trawlkit.batch.columns.NETS`): relingas, boyas, potencia de diseño, profundidad.

Cada red pasa por el validador de consistencia (:func:`trawlkit.netcheck.check`, Fase 12): una
red con errores queda como borrador, visible pero marcada.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from trawlkit.batch.columns import NETS, PANELS
from trawlkit.batch.sheets import RowIssue, Sheet, norm, parse_sheet
from trawlkit.io import NetSpec
from trawlkit.netcheck import Issue, check

#: Columnas de un panel que se copian tal cual a :class:`~trawlkit.io.schema.Panel`.
_PANEL_FIELDS = (
    "plane",
    "section",
    "material",
    "mesh_mm",
    "twine_diameter_mm",
    "rtex",
    "meshes_top",
    "meshes_bottom",
    "meshes_depth",
    "hanging_ratio",
    "count",
    "cut_code",
    "cut_code_x2",
    "runnage_m_per_kg",
    "meshes_a",
    "meshes_b",
)

_PLANE_NAMES = {
    "superior": "upper",
    "inferior": "lower",
    "lateral": "side",
    "upper": "upper",
    "lower": "lower",
    "side": "side",
    "dorso": "upper",
    "vientre": "lower",
}


@dataclass
class LoadedNet:
    """Red leída de una planilla, con su validación."""

    spec: NetSpec
    check: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Sin errores del validador."""
        return not any(i.level == "error" for i in self.check)

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "spec": self.spec.model_dump(mode="json", exclude_none=True),
            "ok": self.ok,
            "check": [i.to_dict() for i in self.check],
        }


def _sheet_kind(sheet: Sheet) -> str:
    n = norm(sheet.name)
    return "nets" if n in ("red", "redes", "net", "nets") else "panels"


def read_nets(sheets: list[Sheet]) -> tuple[list[LoadedNet], list[RowIssue]]:
    """Redes de las hojas de paneles (y la hoja ``red``, si la hay)."""
    issues: list[RowIssue] = []
    meta: dict[str, dict[str, Any]] = {}
    for sh in sheets:
        if _sheet_kind(sh) == "nets":
            p = parse_sheet(sh, NETS)
            issues += p.issues
            for rec in p.records:
                if rec.get("net"):
                    meta[norm(rec["net"])] = rec
    groups: dict[str, tuple[str, list[dict[str, Any]], str]] = {}
    for sh in sheets:
        if _sheet_kind(sh) != "panels":
            continue
        p = parse_sheet(sh, PANELS)
        issues += p.issues
        bad = {i.row for i in p.issues if i.level == "error" and i.row is not None}
        for rec in p.records:
            if rec["_row"] in bad:
                continue
            name = str(rec.get("net") or sh.name)
            key = norm(name) or "red"
            groups.setdefault(key, (name, [], sh.name))[1].append(rec)
    out: list[LoadedNet] = []
    for key, (name, rows, sheet_name) in groups.items():
        try:
            spec = _spec(key, name, rows, meta.get(key, {}))
        except ValidationError as exc:
            for e in exc.errors():
                issues.append(
                    RowIssue(
                        "error",
                        "bad_net",
                        f"{name}: {'.'.join(str(x) for x in e['loc'])}: {e['msg']}",
                        sheet=sheet_name,
                    )
                )
            continue
        out.append(LoadedNet(spec=spec, check=check(spec)))
    for ln in out:
        if not ln.ok:
            ln.spec = ln.spec.model_copy(update={"status": "draft"})
    return out, issues


def _spec(key: str, name: str, rows: list[dict[str, Any]], meta: dict[str, Any]) -> NetSpec:
    panels = []
    for r in rows:
        p: dict[str, Any] = {"id": str(r["panel"])}
        for f in _PANEL_FIELDS:
            if r.get(f) is not None:
                p[f] = r[f]
        if r.get("planes_covered"):
            parts = [norm(x) for x in re.split(r"[+,;/ ]+", str(r["planes_covered"])) if x]
            p["planes_covered"] = [_PLANE_NAMES.get(x, x) for x in parts]
        panels.append(p)
    data: dict[str, Any] = {
        "id": f"user_{key}",
        "name": name,
        "description": meta.get("description"),
        "source": "planilla del usuario",
        "panels": panels,
        "notes": ["Red cargada desde una planilla del usuario (sin verificar)."],
    }
    if meta.get("family"):
        data["family"] = meta["family"]
    if meta.get("rig"):
        data["rig"] = meta["rig"]
    hps = [float(meta[k]) for k in ("hp_min", "hp_max") if meta.get(k) is not None]
    if hps:
        data["vessel_hp"] = (hps[0], hps[-1])
    if meta.get("headrope_m") is not None:
        data["headrope"] = {"name": "Lima", "length_m": meta["headrope_m"]}
    if meta.get("footrope_m") is not None:
        data["footrope"] = {"name": "Burlón", "length_m": meta["footrope_m"]}
    if meta.get("float_count") is not None:
        data["floats"] = {
            "count": meta["float_count"],
            "diameter_mm": meta.get("float_diameter_mm") or 200.0,
        }
    if meta.get("species") or meta.get("depth_m") is not None:
        data["species"] = {"name": meta.get("species") or "—", "depth_m": meta.get("depth_m")}
    if meta.get("depth_m") is not None:
        data["design"] = {"depth_m": meta["depth_m"]}
    return NetSpec.model_validate(data)


#: Encabezados de la hoja de paneles al exportar (en el orden de la plantilla).
PANEL_HEADERS = (
    ("net", "red"),
    ("panel", "panel"),
    ("plane", "cara"),
    ("section", "sección"),
    ("material", "material"),
    ("mesh_mm", "mallero [mm]"),
    ("twine_diameter_mm", "hilo [mm]"),
    ("rtex", "rtex"),
    ("meshes_top", "mallas boca"),
    ("meshes_bottom", "mallas bolsa"),
    ("meshes_depth", "mallas alto"),
    ("hanging_ratio", "U1"),
    ("count", "cantidad"),
    ("cut_code", "corte"),
    ("cut_code_x2", "corte 2"),
    ("runnage_m_per_kg", "rendimiento"),
    ("planes_covered", "caras cubiertas"),
    ("meshes_a", "T1"),
    ("meshes_b", "T2"),
)


def net_rows(spec: NetSpec) -> list[list[Any]]:
    """Filas de la hoja de paneles de ``spec`` (encabezados de :data:`PANEL_HEADERS`)."""
    rows = []
    for p in spec.panels:
        d = p.model_dump(mode="json")
        extra = p.model_extra or {}
        vals: list[Any] = []
        for key, _ in PANEL_HEADERS:
            if key == "net":
                vals.append(spec.name)
            elif key == "panel":
                vals.append(p.id)
            elif key in ("meshes_a", "meshes_b", "cut_code_x2"):
                vals.append(extra.get(key, ""))
            elif key == "planes_covered":
                vals.append("+".join(extra.get(key) or []))
            else:
                v = d.get(key)
                vals.append("" if v is None else v)
        rows.append(vals)
    return rows


__all__ = ["PANEL_HEADERS", "LoadedNet", "net_rows", "read_nets"]
