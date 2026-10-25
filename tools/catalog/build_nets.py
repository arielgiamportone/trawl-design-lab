"""Genera ``src/trawlkit/data/nets/<id>.yaml`` a partir de ``tools/catalog/transcriptions.py``.

Cada valor sale con su procedencia: los leídos en la figura como ``transcribed`` (documento, página
y figura), el diámetro del hilo como ``derived`` (de su Rtex) y lo que el plano no da como
``assumed`` (con la razón). Después valida cada red (``trawlkit.netcheck``) e informa la cobertura
de procedencia.

    uv run python tools/catalog/build_nets.py
"""

from __future__ import annotations

import math
import pathlib
import sys
from typing import Any

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.catalog.transcriptions import ACCESSED, NETS  # noqa: E402

from trawlkit.io.schema import NetSpec  # noqa: E402
from trawlkit.netcheck import check  # noqa: E402
from trawlkit.provenance import coverage  # noqa: E402

OUT = ROOT / "src" / "trawlkit" / "data" / "nets"

#: Densidad del polímero [kg/m³] para derivar el diámetro del hilo de su Rtex.
DENSITY = {"PA": 1140.0, "PE": 950.0, "PP": 910.0, "PES": 1380.0}
#: d [mm] = K · √Rtex para PA, de la tabla del libro de la FAO A-3 (1,37 mm ↔ R1280 tex,
#: 1,16 mm ↔ R950 tex: K ≈ 0,038); para otros polímeros se escala con √(ρ_PA/ρ).
K_PA = 0.038

HEADER = (
    "# Generado por tools/catalog/build_nets.py desde tools/catalog/transcriptions.py.\n"
    "# No editar a mano: corregir la transcripción y regenerar.\n"
)


def diameter_mm(rtex: float, material: str) -> float:
    """Diámetro aproximado del hilo de red a partir de su Rtex [mm]."""
    k = K_PA * math.sqrt(DENSITY["PA"] / DENSITY.get(material, DENSITY["PA"]))
    return round(k * math.sqrt(rtex), 2)


def build(t: dict[str, Any]) -> dict[str, Any]:
    """Diccionario de la ``NetSpec`` con procedencia por valor."""
    src = t["source"]
    base = {
        "kind": "transcribed",
        "document": src["key"],
        "page": src.get("page"),
        "figure": src.get("figure"),
    }
    prov: dict[str, dict[str, Any]] = {}

    def mark(path: str, kind: str = "transcribed", note: str | None = None) -> None:
        d = dict(base, kind=kind)
        if note:
            d["note"] = note
        prov[path] = {k: v for k, v in d.items() if v is not None}

    material = t.get("material", "PA")
    hanging = t.get("hanging", {})
    panels = []
    for row in t["panels"]:
        pid, plane, section, count, mesh, rtex, top, bottom, depth, cut = row[:10]
        mat = row[10] if len(row) > 10 else material
        h = hanging.get(pid) or hanging.get(section) or hanging.get(plane) or hanging["default"]
        d_given = t.get("twine_diameter", {}).get(rtex)
        panel = {
            "id": pid,
            "plane": plane,
            "section": section,
            "material": mat,
            "mesh_mm": float(mesh),
            "twine_diameter_mm": float(d_given) if d_given else diameter_mm(rtex, mat),
            "rtex": float(rtex),
            "meshes_top": int(top),
            "meshes_bottom": int(bottom),
            "meshes_depth": int(depth),
            "hanging_ratio": float(h[0]),
            "count": int(count),
            "fao_cut": cut,
        }
        if pid in t.get("panel_notes", {}):
            panel["note"] = t["panel_notes"][pid]
        panels.append(panel)
        for f in ("mesh_mm", "rtex", "meshes_top", "meshes_bottom", "meshes_depth"):
            mark(f"panels.{pid}.{f}")
        mark(
            f"panels.{pid}.count",
            note="dos paños iguales (alas izquierda y derecha)" if count == 2 else None,
        )
        if d_given:
            mark(f"panels.{pid}.twine_diameter_mm")
        else:
            mark(
                f"panels.{pid}.twine_diameter_mm",
                "derived",
                f"d = K·√Rtex con K = {K_PA} para PA (tabla de la FAO A-3), escalado por "
                f"√(ρ_PA/ρ_{mat}); Rtex {rtex:g}",
            )
        for f, (kind, note) in t.get("overrides", {}).get(pid, {}).items():
            mark(f"panels.{pid}.{f}", kind, note)
        mark(f"panels.{pid}.hanging_ratio", h[1], h[2])

    spec: dict[str, Any] = {
        "id": t["id"],
        "name": t["name"],
        "description": t["description"],
        "source": f"{src['title']} ({src['url']})",
        "family": t["family"],
        "rig": t["rig"],
        "vessel_hp": list(t["vessel_hp"]),
        "target_species": t.get("target_species"),
        "status": t.get("status", "published"),
        "sources": [
            {
                "key": src["key"],
                "title": src["title"],
                "url": src["url"],
                "accessed": ACCESSED,
                "figure": src.get("figure"),
                "page": src.get("page"),
            }
        ],
        "panels": panels,
    }
    for name in ("headrope", "footrope"):
        r = t.get(name)
        if not r:
            continue
        spec[name] = {
            "name": "lima" if name == "headrope" else "burlón",
            "length_m": r["length_m"],
            "diameter_mm": r.get("diameter_mm"),
            "wing_m": r.get("wing_m"),
            "bosom_m": r.get("bosom_m"),
            "description": r.get("material"),
            # Cabo del catálogo de cabos más parecido (el motor toma de ahí peso y resistencia).
            "construction": r.get("rope"),
        }
        mark(f"{name}.length_m")
        if r.get("diameter_mm") is not None:
            mark(f"{name}.diameter_mm")
    if f := t.get("floats"):
        spec["floats"] = {"count": f["count"], "diameter_mm": f["diameter_mm"]}
        for k in ("count", "diameter_mm"):
            mark(
                f"floats.{k}",
                f.get("kind", "assumed" if f.get("note") else "transcribed"),
                f.get("note"),
            )
    if b := t.get("ballast_kg"):
        spec["ballast_kg"] = b["value"]
        mark("ballast_kg", b.get("kind", "derived"), b.get("note"))
    if t.get("rigging"):
        spec["rigging"] = t["rigging"]
    spec["notes"] = list(t.get("notes", []))
    spec["provenance"] = prov
    return spec


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    failed = 0
    for t in NETS:
        data = build(t)
        spec = NetSpec.model_validate(data)
        issues = check(spec)
        cov = coverage(spec)
        path = OUT / f"{t['id']}.yaml"
        path.write_text(
            HEADER + yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100),
            encoding="utf-8",
        )
        errs = [i for i in issues if i.level == "error"]
        failed += bool(errs)
        print(
            f"{t['id']}: {len(spec.panels)} paños, procedencia {cov['with_provenance']}/"
            f"{cov['values']}, {len(errs)} errores, {len(issues) - len(errs)} avisos"
        )
        for i in issues:
            print(f"   {i.level}: {i.message}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
