"""Procedencia por valor de una red (Fase 12).

Cada valor numérico de una :class:`~trawlkit.io.schema.NetSpec` que usa el motor tiene una ruta
(``panels.C.meshes_top``, ``headrope.length_m``…). Su procedencia viene de:

* ``NetSpec.provenance[ruta]``: documento, página, figura y tipo (transcripto, derivado,
  supuesto), para las redes digitalizadas de documentos;
* ``source_cells`` del panel o de la relinga: celda del libro Excel original (tipo ``excel``),
  para la FAO A-3.

:func:`coverage` mide qué fracción de los valores presentes tiene procedencia, y
:func:`provenance_table` la lista valor por valor (para la API y la web).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from trawlkit.io.schema import NetSpec, Provenance, ProvenanceKind

#: Campos de panel que el motor usa (los que deben tener procedencia si están presentes).
PANEL_FIELDS = (
    "mesh_mm",
    "twine_diameter_mm",
    "rtex",
    "meshes_top",
    "meshes_bottom",
    "meshes_depth",
    "hanging_ratio",
    "count",
)
ROPE_FIELDS = ("length_m", "diameter_mm", "weight_kg_per_m")
FLOAT_FIELDS = ("count", "diameter_mm", "buoyancy_kgf_each", "total_buoyancy_kgf")


@dataclass(frozen=True)
class ValueProvenance:
    """Un valor de la red y su procedencia (``None`` si no la tiene)."""

    path: str
    value: Any
    provenance: Provenance | None

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "path": self.path,
            "value": self.value,
            "provenance": None if self.provenance is None else self.provenance.model_dump(),
        }


def value_paths(spec: NetSpec) -> list[tuple[str, Any]]:
    """Rutas y valores presentes (no nulos) de los campos que usa el motor."""
    out: list[tuple[str, Any]] = []
    for p in spec.panels:
        for f in PANEL_FIELDS:
            v = getattr(p, f, None)
            if v is not None:
                out.append((f"panels.{p.id}.{f}", v))
    for name in ("headrope", "footrope"):
        rope = getattr(spec, name)
        if rope is None:
            continue
        for f in ROPE_FIELDS:
            v = getattr(rope, f, None)
            if v is not None:
                out.append((f"{name}.{f}", v))
    if spec.floats is not None:
        for f in FLOAT_FIELDS:
            v = getattr(spec.floats, f, None)
            if v is not None:
                out.append((f"floats.{f}", v))
    if spec.ballast_kg is not None:
        out.append(("ballast_kg", spec.ballast_kg))
    return out


def _excel_cells(spec: NetSpec, path: str) -> str | None:
    parts = path.split(".")
    cells: dict[str, str] | None = None
    if parts[0] == "panels":
        panel = next((p for p in spec.panels if p.id == parts[1]), None)
        cells = None if panel is None else panel.source_cells
        field = parts[2]
    elif parts[0] in ("headrope", "footrope", "floats"):
        obj = getattr(spec, parts[0])
        cells = (obj.model_extra or {}).get("source_cells") if obj is not None else None
        field = parts[1]
    else:
        cells = (spec.model_extra or {}).get("source_cells")
        field = parts[0]
    if not cells:
        return None
    return cells.get(field) if isinstance(cells, dict) else None


def provenance_of(spec: NetSpec, path: str) -> Provenance | None:
    """Procedencia de un valor: la explícita o, si no, la celda del Excel."""
    if path in spec.provenance:
        return spec.provenance[path]
    cell = _excel_cells(spec, path)
    if cell:
        return Provenance(kind=ProvenanceKind.EXCEL, document="giamportone2024", note=cell)
    return None


def provenance_table(spec: NetSpec) -> list[ValueProvenance]:
    """Cada valor de la red con su procedencia."""
    return [ValueProvenance(path, v, provenance_of(spec, path)) for path, v in value_paths(spec)]


def coverage(spec: NetSpec) -> dict[str, Any]:
    """Fracción de valores con procedencia y conteo por tipo."""
    rows = provenance_table(spec)
    by_kind: dict[str, int] = {}
    for r in rows:
        k = "none" if r.provenance is None else str(r.provenance.kind)
        by_kind[k] = by_kind.get(k, 0) + 1
    n = len(rows)
    with_prov = n - by_kind.get("none", 0)
    return {
        "values": n,
        "with_provenance": with_prov,
        "fraction": with_prov / n if n else 1.0,
        "by_kind": by_kind,
        "missing": [r.path for r in rows if r.provenance is None],
    }
