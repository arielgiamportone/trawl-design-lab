"""Genera ``src/trawlkit/data/components/<tipo>/<fuente>.yaml`` (Fase 13).

* **Genéricos** (``generic_workbook.yaml``): ajusta una ley por material o construcción a las
  tablas del FAO *Fisherman's Workbook* (``tools/components/sources.py``) y escribe ítems a
  tamaños estándar con valores *derivados* del ajuste (el error máximo va en la procedencia).
  Boyas, cadenas y portones se transcriben (son ejemplos por tamaño o potencia).
* **Fabricantes**: datos puntuales con su fuente y su genérico equivalente.
* **Libro Excel de la A-3** (``excel_a3.yaml``): los catálogos del libro, con procedencia Excel.

Después valida cada ítem (``trawlkit.components.check``) y falla si hay errores.

    uv run python tools/components/build_components.py
"""

from __future__ import annotations

import math
import pathlib
import sys
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.components import sources as src  # noqa: E402

OUT = ROOT / "src" / "trawlkit" / "data" / "components"
DATA = ROOT / "src" / "trawlkit" / "data"
HEADER = (
    "# Generado por tools/components/build_components.py. No editar a mano: corregir las fuentes\n"
    "# (tools/components/sources.py) y regenerar.\n"
)


# --- Ajustes ---------------------------------------------------------------------------------


def power_fit(x: Sequence[float], y: Sequence[float]) -> tuple[float, float, float]:
    """``y = a·x^b`` por mínimos cuadrados en logaritmos; devuelve (a, b, error relativo máx)."""
    lx, ly = np.log(np.asarray(x, float)), np.log(np.asarray(y, float))
    b, la = np.polyfit(lx, ly, 1)
    a = math.exp(la)
    err = float(np.max(np.abs(a * np.asarray(x, float) ** b / np.asarray(y, float) - 1.0)))
    return a, float(b), err


def d2_fit(d: Sequence[float], y: Sequence[float]) -> tuple[float, float]:
    """``y = k·d²`` por mínimos cuadrados; devuelve (k, error relativo máx)."""
    dd = np.asarray(d, float) ** 2
    yy = np.asarray(y, float)
    k = float(np.sum(yy * dd) / np.sum(dd * dd))
    return k, float(np.max(np.abs(k * dd / yy - 1.0)))


def r(x: float, nd: int = 3) -> float:
    """Redondeo a ``nd`` cifras significativas."""
    if x == 0:
        return 0.0
    return float(f"{x:.{nd}g}")


def num(x: float) -> str:
    return f"{x:.3g}".replace(".", ",")


# --- Procedencia -----------------------------------------------------------------------------


def prov(doc: str, kind: str = "transcribed", page: str | None = None, note: str | None = None):
    d: dict[str, Any] = {"kind": kind, "document": doc}
    if page:
        d["page"] = page
    if note:
        d["note"] = note
    return d


def source(doc: str, page: str | None = None) -> dict[str, Any]:
    s = {k: v for k, v in src.DOCS[doc].items() if v is not None}
    s.setdefault("accessed", src.ACCESSED)
    if page:
        s["page"] = page
    return s


# --- Genéricos del Workbook ------------------------------------------------------------------

WB = "prado1990"


def twine_generics() -> list[dict[str, Any]]:
    out = []
    for key, t in src.TWINE_TABLES.items():
        rt = [p[0] for p in t["points"]]
        fits = {
            "diameter_mm": power_fit(rt, [p[1] for p in t["points"]]),
            "breaking_load_kgf": power_fit(rt, [p[2] for p in t["points"]]),
            "knot_breaking_load_kgf": power_fit(rt, [p[3] for p in t["points"]]),
        }
        page = f"Workbook, «{t['page']}»"
        for rtex in rt:
            item: dict[str, Any] = {
                "id": f"twine_{key.lower()}_r{rtex}",
                "name": f"Hilo {t['material']} {t['construction'].split(',')[0]} R{rtex} tex",
                "material": t["material"],
                "construction": t["construction"],
                "rtex": float(rtex),
                "runnage_m_per_kg": r(1e6 / rtex),
                "knotted": True,
                "regions": ["global"],
                "provenance": {
                    "rtex": prov(WB, page=page, note="tamaño de la tabla de referencia"),
                    "runnage_m_per_kg": prov(WB, "derived", page, "10⁶ / Rtex"),
                },
            }
            for f, (a, b, err) in fits.items():
                item[f] = r(a * rtex**b)
                what = {
                    "diameter_mm": "diámetro",
                    "breaking_load_kgf": "rotura seco sin nudo",
                    "knot_breaking_load_kgf": "rotura mojado con nudo",
                }[f]
                item["provenance"][f] = prov(
                    WB,
                    "derived",
                    page,
                    f"{what} = {num(a)}·Rtex^{b:.3f}, ajuste a {len(rt)} filas de la tabla "
                    f"(error máx. {100 * err:.0f} %)",
                )
            out.append(item)
    return out


ROPE_SIZES = (6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 28, 32, 36, 40)


def rope_generics() -> list[dict[str, Any]]:
    out = []
    for key, t in src.ROPE_TABLES.items():
        d = [p[0] for p in t["points"]]
        kgm = [p[1] if t.get("kg_per_m") else p[1] / 100.0 for p in t["points"]]
        mbl_t = [p[2] / 1000.0 for p in t["points"]]
        kw, ew = d2_fit(d, kgm)
        am, bm, em = power_fit(d, mbl_t)
        material = t.get("material", key)
        page = (
            "Workbook, «Synthetic fibre rope»"
            if material != "combinado"
            else ("Workbook, «Combination wire (2): steel - polypropylene»")
        )
        sizes = [s for s in ROPE_SIZES if min(d) <= s <= max(d)]
        for s in sizes:
            out.append(
                {
                    "id": f"rope_{key.lower()}_{s}mm",
                    "name": f"Cabo {material} {t['construction']} Ø{s} mm",
                    "material": material,
                    "construction": t["construction"],
                    "diameter_mm": float(s),
                    "weight_kg_per_m": r(kw * s * s),
                    "breaking_load_t": r(am * s**bm),
                    "regions": ["global"],
                    "provenance": {
                        "diameter_mm": prov(WB, page=page, note="tamaño estándar"),
                        "weight_kg_per_m": prov(
                            WB,
                            "derived",
                            page,
                            f"kg/m = {kw:.5f}·d², ajuste a {len(d)} filas (error máx. "
                            f"{100 * ew:.0f} %)",
                        ),
                        "breaking_load_t": prov(
                            WB,
                            "derived",
                            page,
                            f"rotura [t] = {num(am)}·d^{bm:.3f}, ajuste a {len(d)} filas (error "
                            f"máx. {100 * em:.0f} %)",
                        ),
                    },
                }
            )
    return out


def wire_generics() -> list[dict[str, Any]]:
    out = []
    page = "Workbook, «Galvanised steel wire rope: runnage, breaking strength»"
    for key, t in src.WIRE_TABLES.items():
        d = [p[0] for p in t["points"]]
        kw, ew = d2_fit(d, [p[1] / 100.0 for p in t["points"]])
        km, em = d2_fit(d, [p[2] / 1000.0 for p in t["points"]])
        for s in range(int(min(d)), int(max(d)) + 1, 2 if max(d) - min(d) > 8 else 1):
            out.append(
                {
                    "id": f"wire_{key}_{s}mm",
                    "name": f"Cable de acero galvanizado {t['construction']} Ø{s} mm",
                    "construction": t["construction"],
                    "core": t["core"],
                    "diameter_mm": float(s),
                    "weight_kg_per_m": r(kw * s * s),
                    "breaking_load_t": r(km * s * s),
                    "regions": ["global"],
                    "notes": [f"Uso habitual: {t['use']}."],
                    "provenance": {
                        "diameter_mm": prov(
                            WB, page=page, note="tamaño dentro del rango de la tabla"
                        ),
                        "weight_kg_per_m": prov(
                            WB,
                            "derived",
                            page,
                            f"kg/m = {kw:.5f}·d², ajuste a {len(d)} filas (error máx. "
                            f"{100 * ew:.0f} %)",
                        ),
                        "breaking_load_t": prov(
                            WB,
                            "derived",
                            page,
                            f"rotura [t] = {km:.5f}·d² (acero de 145 kgf/mm²), ajuste a {len(d)} "
                            f"filas (error máx. {100 * em:.0f} %)",
                        ),
                    },
                }
            )
    return out


def float_generics() -> list[dict[str, Any]]:
    page = "Workbook, «Spherical floats and trawl floats» (ejemplos de catálogos de proveedores)"
    out = []
    for k, (mat, mount, dia, vol, buoy, depth) in enumerate(src.FLOAT_TABLE):
        slug = "alu" if mat == "aluminio" else "pl"
        out.append(
            {
                "id": f"float_{slug}_{int(dia)}mm_{k}",
                "name": f"Boya de {mat} Ø{int(dia)} mm, {mount}",
                "material": mat,
                "mount": mount,
                "diameter_mm": float(dia),
                "volume_l": float(vol),
                "buoyancy_kgf": float(buoy),
                "max_depth_m": float(depth),
                "regions": ["global"],
                "provenance": {
                    f: prov(WB, page=page)
                    for f in ("diameter_mm", "volume_l", "buoyancy_kgf", "max_depth_m")
                },
                "notes": [
                    "La profundidad máxima depende del fabricante; confirmarla con el proveedor."
                ],
            }
        )
    return out


def chain_generics() -> list[dict[str, Any]]:
    page = "Workbook, «Chains and thimbles»"
    out = []
    for dia, w in src.CHAIN_COMMON:
        out.append(
            {
                "id": f"chain_common_{int(dia)}mm",
                "name": f"Cadena de acero común Ø{int(dia)} mm",
                "link": "corto",
                "link_diameter_mm": float(dia),
                "weight_kg_per_m": float(w),
                "regions": ["global"],
                "provenance": {
                    "link_diameter_mm": prov(WB, page=page),
                    "weight_kg_per_m": prov(WB, page=page, note="peso aproximado"),
                },
                "notes": ["El Workbook no da la rotura de la cadena común; no usarla en tiro."],
            }
        )
    for dia, mbl, w in src.CHAIN_HIGH_TENSILE:
        out.append(
            {
                "id": f"chain_ht_{int(dia)}mm",
                "name": f"Cadena de acero de alta resistencia Ø{int(dia)} mm",
                "link": "corto",
                "link_diameter_mm": float(dia),
                "grade": "alta resistencia",
                "weight_kg_per_m": float(w),
                "breaking_load_t": float(mbl),
                "regions": ["global"],
                "provenance": {
                    "link_diameter_mm": prov(WB, page=page),
                    "weight_kg_per_m": prov(WB, page=page),
                    "breaking_load_t": prov(WB, page=page, note="ton-fuerza"),
                },
            }
        )
    return out


def _excel_door(door_id: str) -> dict[str, Any]:
    raw = yaml.safe_load((DATA / "doors.yaml").read_text(encoding="utf-8"))
    return next(d for d in raw["doors"] if d["id"] == door_id)


def _type_polar(door_type: str) -> Any:
    from trawlkit.rigging.polars import polar_for_type

    return polar_for_type(door_type)


def _polar_prov(door_type: str, kind: str | None = None, note: str | None = None) -> dict:
    """Procedencia de la polar del tipo, como dict (``kind``/``note`` la pisan)."""
    p = _type_polar(door_type).provenance()
    d = p.model_dump(mode="json", exclude_none=True)
    if kind:
        d["kind"] = kind
    if note:
        d["note"] = note + "; " + d["note"]
    return d


#: Nota de las polares del plano y del oval: son las hojas de Seafish 1993 que el libro Excel de
#: la A-3 tomó tal cual.
FLAT_POLAR_NOTE = (
    "hoja «Flat Wooden» de Seafish/IFREMER/DIFTA 1993 (App. IV-3), igual número por número a la "
    "polar del libro Excel de la A-3 (Tablas de Referencias B259:D264), que la tomó de allí"
)
OVAL_POLAR_NOTE = (
    "hoja «Morgère Polyvalent Ovale» de Seafish/IFREMER/DIFTA 1993 (App. IV-17), igual a la "
    "polar del libro Excel de la A-3 (Tablas de Referencias B281:D286)"
)


def door_generics() -> list[dict[str, Any]]:
    page = "Workbook, «Otter boards: properties of the principal types, choice depending on power»"
    out: list[dict[str, Any]] = []

    def base(
        did: str,
        name: str,
        typ: str,
        hp: tuple[float, float],
        length: float,
        height: float,
        area: float,
        weight: tuple[float, float],
        polar: list[dict[str, Any]],
        polar_prov: dict,
        wcoef: float,
        dims_prov: dict | None = None,
    ) -> dict[str, Any]:
        w = 0.5 * (weight[0] + weight[1])
        dp = dims_prov or prov(WB, page=page)
        return {
            "id": did,
            "name": name,
            "type": typ,
            "length_m": length,
            "height_m": height,
            "area_m2": area,
            "weight_air_kg": w,
            "weight_water_coefficient": wcoef,
            "hp_range": [hp[0], hp[1]],
            "coefficients": polar,
            "regions": ["global"],
            "provenance": {
                "length_m": dp,
                "height_m": dp,
                "area_m2": prov(WB, page=page),
                "weight_air_kg": prov(
                    WB,
                    page=page,
                    note=f"peso máximo usado {weight[0]:g}–{weight[1]:g} kg: valor medio; con un "
                    "material liviano puede ser hasta 50 % menor",
                ),
                "hp_range": prov(WB, page=page),
                "coefficients": polar_prov,
            },
        }

    flat = _type_polar("flat").coefficient_dicts()
    flat_prov = prov("sfia1993", page="Appendix IV-3 (PDF p. 133)", note=FLAT_POLAR_NOTE)
    for hp, length, height, area, weight in src.DOOR_FLAT:
        out.append(
            base(
                f"door_flat_{int(hp[1])}hp",
                f"Portón plano rectangular {length:g} × {height:g} m ({int(hp[0])}–{int(hp[1])} hp)"
                if hp[0] != hp[1]
                else f"Portón plano rectangular {length:g} × {height:g} m ({int(hp[0])} hp)",
                "flat",
                hp,
                length,
                height,
                area,
                weight,
                flat,
                flat_prov,
                0.6,
            )
        )
    oval = _type_polar("oval").coefficient_dicts()
    oval_prov = prov("sfia1993", page="Appendix IV-17 (PDF p. 148)", note=OVAL_POLAR_NOTE)
    for hp, length, height, area, weight in src.DOOR_OVAL:
        out.append(
            base(
                f"door_oval_{int(hp[1])}hp",
                f"Portón oval cambado {length:g} × {height:g} m ({int(hp[0])} hp)",
                "oval",
                hp,
                length,
                height,
                area,
                weight,
                oval,
                oval_prov,
                0.87,
            )
        )
    vpolar = _type_polar("v").coefficient_dicts()
    for hp, area, weight in src.DOOR_V:
        length = math.sqrt(area / 0.5)
        height = 0.5 * length
        out.append(
            base(
                f"door_v_{int(hp)}hp",
                f"Portón en V de {area:g} m² ({int(hp)} hp)",
                "v",
                (hp, hp),
                round(length, 2),
                round(height, 2),
                area,
                (weight, weight),
                vpolar,
                _polar_prov("v"),
                0.87,
                dims_prov=prov(
                    WB,
                    "assumed",
                    page,
                    "el Workbook da sólo la superficie; se supone alto/largo = 0,5",
                ),
            )
        )
    hpolar = _type_polar("high_aspect").coefficient_dicts()
    for hp, h, length, area, weight in src.DOOR_SUBERKRUB:
        out.append(
            base(
                f"door_suberkrub_{area:g}m2".replace(".", "_"),
                f"Portón pelágico Süberkrüb {area:g} m² ({int(hp[0])}–{int(hp[1])} hp)"
                if hp[0] != hp[1]
                else f"Portón pelágico Süberkrüb {area:g} m² ({int(hp[0])} hp)",
                "suberkrub",
                hp,
                length,
                h,
                area,
                weight,
                hpolar,
                _polar_prov(
                    "high_aspect",
                    note="no hay polar publicada del Süberkrüb; se usa la de un portón pelágico "
                    "cambado de alta relación de aspecto medido (H/L del Süberkrüb ≈ 2,3)",
                ),
                0.87,
            )
        )
    return out


def door_rebyc() -> list[dict[str, Any]]:
    page = "Tabla 5 y texto «Puertas de arrastre»"
    flat = _type_polar("flat").coefficient_dicts()
    out = []
    for label, length, height, use in src.DOOR_REBYC:
        out.append(
            {
                "id": "door_rebyc_" + label.replace("'", "ft").replace('"', "in").replace("x", "x"),
                "name": f"Puerta plana de madera {label} (flota camaronera del Caribe colombiano)",
                "type": "flat_wood",
                "product": "medida usada en la flota",
                "length_m": round(length, 3),
                "height_m": round(height, 3),
                "area_m2": round(length * height, 3),
                "hp_range": [165, 520],
                "weight_water_coefficient": 0.6,
                "coefficients": flat,
                "country": "CO",
                "regions": ["latam"],
                "notes": [f"Uso: {use}."],
                "provenance": {
                    "length_m": prov("zuniga2006", page=page, note=f"{label} (pies × pulgadas)"),
                    "height_m": prov("zuniga2006", page=page, note=f"{label} (pies × pulgadas)"),
                    "area_m2": prov("zuniga2006", "derived", page, "largo × alto"),
                    "hp_range": prov(
                        "zuniga2006", page="Tabla 1", note="potencia de la flota: 165–520 hp"
                    ),
                    "coefficients": prov(
                        "sfia1993",
                        "assumed",
                        "Appendix IV-3 (PDF p. 133)",
                        "la flota usa puertas planas de madera; se supone la polar del modelo "
                        "plano de madera de Seafish (" + FLAT_POLAR_NOTE + ")",
                    ),
                },
            }
        )
    return out


def door_noaa_ff9() -> list[dict[str, Any]]:
    """Portón de madera de la red de prueba de 16 pies (Fishery Facts 9; Fase 19.6)."""
    page = "p. 2 (tabla 1) y pp. 13–14 (fig. 12)"
    flat = _type_polar("flat").coefficient_dicts()
    out = []
    for label, length, height in src.DOOR_NOAA_FF9:
        out.append(
            {
                "id": "door_noaa_ff9_30x15in",
                "name": f"Portón plano de madera {label} de la red de prueba de 16 pies (NOAA)",
                "type": "flat_wood",
                "product": "diseño publicado (construcción casera)",
                "length_m": round(length, 3),
                "height_m": round(height, 3),
                "area_m2": round(length * height, 3),
                "weight_water_coefficient": 0.6,
                "coefficients": flat,
                "country": "US",
                "regions": ["north_america"],
                "notes": [
                    "Terciado marino de ¾ de pulgada con patín de hierro de ¼ × 2½ × 33 pulgadas; "
                    "brida de 104 eslabones de cadena de 3/16 de pulgada (patas de 15, 30, 14 y "
                    "29 eslabones).",
                    "Uso: red de prueba (try-net) de 16 pies de los camaroneros del golfo de "
                    "México y botes de 12 a 30 pies; el documento no da el peso ni la potencia.",
                ],
                "provenance": {
                    "length_m": prov("gutherz1974", page=page, note=f"{label} (pulgadas)"),
                    "height_m": prov("gutherz1974", page=page, note=f"{label} (pulgadas)"),
                    "area_m2": prov("gutherz1974", "derived", page, "largo × alto"),
                    "coefficients": prov(
                        "sfia1993",
                        "assumed",
                        "Appendix IV-3 (PDF p. 133)",
                        "portón plano de terciado; se supone la polar del modelo plano de madera "
                        "de Seafish (" + FLAT_POLAR_NOTE + ")",
                    ),
                },
            }
        )
    return out


# --- Portones de fabricante (Fase 19.3) -------------------------------------------------------


def _nearest_door(
    generics: list[dict[str, Any]], types: tuple[str, ...], area: float
) -> str | None:
    return nearest_generic(generics, lambda g: g["area_m2"], area, lambda g: g["type"] in types)


#: Coeficiente de peso en el agua de un portón de acero (1 − 1025/7850), como los genéricos en V,
#: oval y Süberkrüb.
STEEL_WATER_COEF = 0.87


def vonin_doors(generics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Vónin Storm 2, Tornado y Twister: superficie y peso transcriptos, medidas supuestas."""
    out: list[dict[str, Any]] = []
    for product, d in src.VONIN_DOORS.items():
        page = f"{d['url']} («SIZES AND WEIGHTS»)"
        ar = d["aspect_ratio"]
        ar_used = ar if ar is not None else src.VONIN_DOORS["Tornado"]["aspect_ratio"]
        ar_note = (
            f"el fabricante da sólo la superficie y la relación de aspecto {ar:g} y no define la "
            "superficie; se supone superficie = largo × alto y relación = alto/largo (A VERIFICAR)"
            if ar is not None
            else f"el fabricante no da medidas ni relación de aspecto; se supone la del Tornado "
            f"({ar_used:g}) y superficie = largo × alto (A VERIFICAR)"
        )
        tp = _type_polar(d["type"])
        notes = [f"Uso: {d['use']}."]
        if d.get("claim"):
            notes.append(f"Dato del fabricante, no usado en el cálculo: {d['claim']}.")
        for area, weight in d["points"]:
            length = math.sqrt(area / ar_used)
            height = ar_used * length
            item = {
                "id": f"door_vonin_{d['slug']}_{area:g}m2".replace(".", "_"),
                "name": f"Vónin {product} {area:g} m²",
                "brand": "Vónin",
                "product": product,
                "country": "FO",
                "regions": ["europe"],
                "type": d["type"],
                "length_m": round(length, 3),
                "height_m": round(height, 3),
                "area_m2": area,
                "weight_air_kg": float(weight),
                "weight_water_coefficient": STEEL_WATER_COEF,
                "coefficients": tp.coefficient_dicts(),
                "notes": notes,
                "provenance": {
                    "area_m2": prov("vonin_doors", page=page),
                    "weight_air_kg": prov(
                        "vonin_doors",
                        page=page,
                        note="la tabla dice «WEIGHT» sin unidad ni «por portón» (Vónin no lo "
                        "dice); por portón *derivado* de la noticia del Simoon de Vónin (portones "
                        "de 7,5 m² y 3000 kg encargados como un par: ≈ 400 kg/m² por portón, "
                        "coherente con los 350–500 kg/m² del Storm)",
                    ),
                    "length_m": prov("vonin_doors", "assumed", page, ar_note),
                    "height_m": prov("vonin_doors", "assumed", page, ar_note),
                    "coefficients": tp.provenance(applied_to=f"Vónin {product}").model_dump(
                        mode="json", exclude_none=True
                    ),
                },
            }
            gen = _nearest_door(
                generics, ("suberkrub",) if d["type"] == "high_aspect" else ("v",), area
            )
            if gen:
                item["generic_of"] = gen
            out.append(item)
    return out


def morgere_doors(generics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Morgère 2025: superficie transcripta, peso «sur demande» (falta), medidas supuestas."""
    from trawlkit.rigging.polars import get_polar, polar_for_type

    out: list[dict[str, Any]] = []
    for product, d in src.MORGERE_DOORS.items():
        page = f"Catalogue 2025, {d['page']}"
        model = get_polar(d["polar"])
        ar = model.model["aspect_ratio"]
        ratio = model.model["area_ratio"]
        pts = [c.model_dump(include={"angle_deg", "cl", "cd"}) for c in model.usable(with_max=True)]
        tp = polar_for_type(d["type"])
        polar_prov = prov(
            "sfia1993",
            "assumed",
            model.source.page,
            f"Morgère no publica la polar; se usa la hoja «{model.name}» de Seafish 1993 (el "
            "mismo diseño, ensayado en 1993: A VERIFICAR que el modelo actual conserve la forma)",
        )
        for point in d["points"]:
            if len(point) == 3:
                code, length, area = point
                height = area / (length * ratio)
                dims_l = prov("morgere2025", page=page)
                dims_h = prov("morgere2025", "assumed", page, d["shape_note"])
            else:
                code, area = point
                length = math.sqrt(area / (ar * ratio))
                height = ar * length
                dims_l = dims_h = prov("morgere2025", "assumed", page, d["shape_note"])
            item = {
                "id": f"door_morgere_{code.lower().replace('.', '_')}",
                "name": f"Morgère {product} {code} ({area:g} m²)",
                "brand": "Morgère",
                "product": product,
                "country": "FR",
                "regions": ["europe"],
                "type": d["type"],
                "length_m": round(length, 3),
                "height_m": round(height, 3),
                "area_m2": area,
                "coefficients": pts,
                "notes": [
                    f"Uso: {d['use']}.",
                    "Peso «sur demande» (Morgère adapta tamaño y peso a cada barco): sin peso "
                    "publicado.",
                    f"Polar del tipo ({tp.type}) como alternativa: {tp.polar_ids[0]}.",
                ],
                "provenance": {
                    "area_m2": prov("morgere2025", page=page, note=f"modelo {code}"),
                    "length_m": dims_l,
                    "height_m": dims_h,
                    "coefficients": polar_prov,
                },
            }
            gen = _nearest_door(generics, ("oval",) if d["type"] == "oval" else ("v",), area)
            if gen:
                item["generic_of"] = gen
            out.append(item)
    return out


# --- Fabricantes -----------------------------------------------------------------------------


def nearest_generic(
    generics: list[dict[str, Any]],
    key: Callable[[dict[str, Any]], float],
    target: float,
    pred: Callable[[dict[str, Any]], bool],
) -> str | None:
    cands = [g for g in generics if pred(g)]
    if not cands:
        return None
    return min(cands, key=lambda g: abs(key(g) - target))["id"]


def garware_twine(generics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for line, t in src.GARWARE_TWINE.items():
        page = f"Garware, «{t['page']}»"
        for dia, run, bl, kbl in t["points"]:
            rtex = 1e6 / run
            out.append(
                {
                    "id": f"garware_{line.lower()}_{str(dia).replace('.', '_')}mm",
                    "name": f"Garware {line} Ø{dia:g} mm (PE trenzado para arrastre)",
                    "brand": "Garware",
                    "product": line,
                    "country": "IN",
                    "regions": ["global", "south_asia", "africa", "latam"],
                    "material": "PE",
                    "construction": "trenzado",
                    "diameter_mm": dia,
                    "runnage_m_per_kg": float(run),
                    "rtex": r(rtex),
                    "breaking_load_kgf": float(bl),
                    "knot_breaking_load_kgf": float(kbl),
                    "generic_of": nearest_generic(
                        generics, lambda g: g["rtex"], rtex, lambda g: g["material"] == "PE"
                    ),
                    "notes": [t["note"] + "."],
                    "provenance": {
                        "diameter_mm": prov("garware_fisheries", page=page, note="diámetro real"),
                        "runnage_m_per_kg": prov("garware_fisheries", page=page),
                        "breaking_load_kgf": prov("garware_fisheries", page=page),
                        "knot_breaking_load_kgf": prov(
                            "garware_fisheries",
                            page=page,
                            note="la ficha da la rotura con nudo mayor que sin nudo (ensayo "
                            "propio del fabricante)",
                        ),
                        "rtex": prov("garware_fisheries", "derived", page, "10⁶ / rendimiento"),
                    },
                }
            )
    return out


def garware_rope(generics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    page = "Garware, «Fisheries: Trawl Ropes» (X2)"
    out = []
    for dia, gm, bl in src.GARWARE_X2:
        out.append(
            {
                "id": f"garware_x2_{int(dia)}mm",
                "name": f"Garware X2 Ø{int(dia)} mm (PP/PE tipo Danline)",
                "brand": "Garware",
                "product": "X2",
                "country": "IN",
                "regions": ["global", "south_asia", "africa", "latam"],
                "material": "PP",
                "construction": "3 o 4 cordones, mezcla PP/PE",
                "diameter_mm": float(dia),
                "weight_kg_per_m": gm / 1000.0,
                "breaking_load_t": bl / 1000.0,
                "generic_of": nearest_generic(
                    generics,
                    lambda g: g["diameter_mm"],
                    dia,
                    lambda g: g["material"] == "PP",
                ),
                "notes": ["Relingas, refuerzos, tiras del copo y frente de redes pelágicas."],
                "provenance": {
                    "diameter_mm": prov("garware_fisheries", page=page),
                    "weight_kg_per_m": prov("garware_fisheries", page=page, note="g/m de la ficha"),
                    "breaking_load_t": prov("garware_fisheries", page=page, note="kgf de la ficha"),
                },
            }
        )
    return out


def bridon_wire(generics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for product, t in src.BRIDON_WIRE.items():
        page = f"Bridon-Bekaert 2023, «{product.split(' 6x')[0]}»"
        for dia, kg100, mbl in t["points"]:
            slug = product.lower().replace(" ", "_").replace("(", "").replace(")", "")
            slug = slug.replace("/", "").replace("&", "")
            out.append(
                {
                    "id": f"bridon_{slug}_{int(dia)}mm",
                    "name": f"Bridon-Bekaert {product} Ø{int(dia)} mm",
                    "brand": "Bridon-Bekaert",
                    "product": product,
                    "country": "BE",
                    "regions": ["global", "europe"],
                    "construction": t["construction"],
                    "core": t["core"],
                    "diameter_mm": float(dia),
                    "weight_kg_per_m": kg100 / 100.0,
                    "breaking_load_t": float(mbl),
                    "generic_of": nearest_generic(
                        generics,
                        lambda g: g["diameter_mm"],
                        dia,
                        lambda g, key=t["generic"]: g["id"].startswith(f"wire_{key}_"),
                    ),
                    "provenance": {
                        "diameter_mm": prov("bridon2023", page=page),
                        "weight_kg_per_m": prov("bridon2023", page=page, note="kg/100 m"),
                        "breaking_load_t": prov("bridon2023", page=page, note="carga mínima"),
                    },
                }
            )
    return out


def pfeifer_wire(generics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    page = "PFEIFER 6x19W-FC, tabla de datos"
    out = []
    for dia, kg100, kn in src.PFEIFER_6X19W:
        out.append(
            {
                "id": f"pfeifer_6x19w_fc_{int(dia)}mm",
                "name": f"PFEIFER 6x19W-FC Ø{int(dia)} mm (cable de diámetro chico)",
                "brand": "PFEIFER",
                "product": "6x19W-FC",
                "country": "DE",
                "regions": ["europe"],
                "construction": "6x19 Warrington",
                "core": "FC",
                "diameter_mm": float(dia),
                "weight_kg_per_m": kg100 / 100.0,
                "breaking_load_t": round(kn / 9.80665, 2),
                "generic_of": nearest_generic(
                    generics,
                    lambda g: g["diameter_mm"],
                    dia,
                    lambda g: g["id"].startswith("wire_6x19_1261_fc_"),
                ),
                "provenance": {
                    "diameter_mm": prov("pfeifer_6x19w", page=page),
                    "weight_kg_per_m": prov("pfeifer_6x19w", page=page, note="kg/100 m"),
                    "breaking_load_t": prov(
                        "pfeifer_6x19w", "derived", page, f"{kn:g} kN / 9,807 (EN 12385-4)"
                    ),
                },
            }
        )
    return out


# --- Fase 19.2: más fabricantes --------------------------------------------------------------

HAMP = "hampidjan_catalogue"
HAMP_REGIONS = ["global", "europe", "north_america", "latam"]
#: Aceleración de la gravedad para pasar t y kgf a N (la EA derivada va en kN).
G = 9.80665


def _slug(text: str) -> str:
    out = text.lower()
    for a, b in (("&", ""), ("(", ""), (")", ""), ("/", "_"), (" ", "_"), ("-", "_"), (".", "_")):
        out = out.replace(a, b)
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_")


def _dim(x: float) -> str:
    return f"{x:g}".replace(".", "_")


def ea_from_elongation(mbl_t: float, eps_pct: float, doc: str, page: str) -> tuple[float, Any]:
    """EA [kN] secante = rotura / alargamiento de rotura (derivada), con su procedencia."""
    from trawlkit.materials import ea_from_breaking_load_n

    ea_kn = ea_from_breaking_load_n(mbl_t * 1000.0 * G, eps_pct) / 1000.0
    return r(ea_kn), prov(
        doc,
        "derived",
        page,
        f"EA ≈ rotura / alargamiento de rotura = {num(mbl_t)} t · 9,807 / {num(eps_pct)} % "
        "(secante; cota inferior de la rigidez a la carga de trabajo)",
    )


def hampidjan_twine(generics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for product, t in src.HAMPIDJAN_TWINE.items():
        page = f"Hampidjan, «{product}», {t['page']}"
        for k, row in enumerate(t["points"]):
            if product == "Utzon":
                dia, _n, run, g100, kbl = row
                size = t["twine_no"][k]
            else:
                dia, run, g100, kbl = row
                size = None
            rtex = g100 * 10.0  # g/100 m → g/km = tex
            mat = t["material"]
            item: dict[str, Any] = {
                "id": f"hampidjan_{_slug(product)}_{_dim(dia)}mm",
                "name": f"Hampidjan {product} Ø{dia:g} mm"
                + (f" ({size})" if size else "")
                + f" ({mat} {t['construction'].split(',')[0]})",
                "brand": "Hampidjan",
                "product": product,
                "country": "IS",
                "regions": list(HAMP_REGIONS),
                "material": mat,
                "construction": t["construction"],
                "diameter_mm": float(dia),
                "runnage_m_per_kg": float(run),
                "rtex": r(rtex),
                "knot_breaking_load_kgf": float(kbl),
                "elongation_pct": float(t["elongation"]),
                "generic_of": nearest_generic(
                    generics, lambda g: g["rtex"], rtex, lambda g, m=mat: g["material"] == m
                ),
                "notes": [
                    "La ficha da sólo la rotura con nudo (no la rotura sin nudo) y no dice si el "
                    "ensayo es en seco o mojado.",
                    "Sin EA derivada: la rotura con nudo no es la rotura del hilo.",
                ],
                "provenance": {
                    "diameter_mm": prov(HAMP, page=page),
                    "runnage_m_per_kg": prov(HAMP, page=page),
                    "rtex": prov(HAMP, "derived", page, f"peso {g100:g} g/100 m × 10 = tex"),
                    "knot_breaking_load_kgf": prov(
                        HAMP, page=page, note="«Knot breaking strength»"
                    ),
                    "elongation_pct": prov(HAMP, page=page, note="cuadro «Properties»"),
                },
            }
            if size:
                item["provenance"]["diameter_mm"] = prov(
                    HAMP, page=page, note=f"número de hilo {size}"
                )
            out.append(item)
    return out


def garware_twisted(generics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Paño torcido de Garware: la ficha no da diámetro; se supone con el ajuste del Workbook."""
    out = []
    for product, t in src.GARWARE_TWISTED.items():
        page = t["page"]
        wb = src.TWINE_TABLES[t["generic"]]
        rts = [p[0] for p in wb["points"]]
        a, b, err = power_fit(rts, [p[1] for p in wb["points"]])
        for size, run, bl, kbl in t["points"]:
            rtex = 1e6 / run
            dia = r(a * rtex**b, 2)
            item: dict[str, Any] = {
                "id": f"garware_{_slug(product)}_{_slug(size)}",
                "name": f"Garware {product} {size} ({t['material']} torcido)",
                "brand": "Garware",
                "product": product,
                "country": "IN",
                "regions": ["global", "south_asia", "africa", "latam"],
                "status": "draft",
                "sources": [source("garware_fisheries"), source(WB)],
                "material": t["material"],
                "construction": f"torcido, {size}",
                "diameter_mm": dia,
                "runnage_m_per_kg": float(run),
                "rtex": r(rtex),
                "breaking_load_kgf": float(bl),
                "knot_breaking_load_kgf": float(kbl),
                "generic_of": nearest_generic(
                    generics,
                    lambda g: g["rtex"],
                    rtex,
                    lambda g, m=t["material"]: g["material"] == m,
                ),
                "notes": [
                    "Borrador: la ficha no da el diámetro; el valor es una estimación con el "
                    "ajuste del Workbook (A VERIFICAR con el fabricante antes de usarlo en la "
                    "resistencia de la red).",
                ],
                "provenance": {
                    "diameter_mm": prov(
                        WB,
                        "assumed",
                        f"Workbook, «{wb['page']}»",
                        f"la ficha de Garware no da diámetro: d = {num(a)}·Rtex^{b:.3f}, ajuste "
                        f"del Workbook a {len(rts)} filas ({t['material']} torcido, error máx. "
                        f"{100 * err:.0f} %); A VERIFICAR",
                    ),
                    "runnage_m_per_kg": prov("garware_fisheries", page=page),
                    "rtex": prov("garware_fisheries", "derived", page, "10⁶ / rendimiento"),
                    "knot_breaking_load_kgf": prov(
                        "garware_fisheries",
                        page=page,
                        note="la ficha da la rotura con nudo mayor que sin nudo (ensayo propio "
                        "del fabricante)",
                    ),
                },
            }
            if bl is not None:
                item["provenance"]["breaking_load_kgf"] = prov("garware_fisheries", page=page)
            else:
                del item["breaking_load_kgf"]
            out.append(item)
    return out


def _rope_generic(generics: list[dict[str, Any]], material: str, dia: float) -> str | None:
    return nearest_generic(
        generics, lambda g: g["diameter_mm"], dia, lambda g, m=material: g["material"] == m
    )


def hampidjan_rope(generics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for product, t in src.HAMPIDJAN_ROPE.items():
        page = f"Hampidjan, «{product}», {t['page']}"
        for row in t["points"]:
            if t.get("kg_per_100m"):
                if product == "Prima Foot rope":
                    dia, inner, kg100, mbl = row
                else:
                    dia, _l, kg100, mbl = row
                    inner = None
                kgm = kg100 / 100.0
                wprov = prov(HAMP, page=page, note="kg/100 m")
            else:
                dia, length, kg_coil, mbl = row
                inner = None
                kgm = r(kg_coil / length, 4)
                wprov = prov(
                    HAMP,
                    "derived",
                    page,
                    f"peso del rollo {num(kg_coil)} kg / {length:g} m",
                )
            ea, eaprov = ea_from_elongation(mbl, t["elongation"], HAMP, page)
            notes = [f"Nota de la ficha: {t['note']}."] if t.get("note") else []
            if t.get("elongation_note"):
                notes.append(f"Alargamiento: {t['elongation_note']}.")
            item: dict[str, Any] = {
                "id": f"hampidjan_{_slug(product)}_{int(dia)}mm",
                "name": f"Hampidjan {product} Ø{dia:g} mm ({t['material']})",
                "brand": "Hampidjan",
                "product": product,
                "country": "IS",
                "regions": list(HAMP_REGIONS),
                "material": t["material"],
                "construction": t["construction"],
                "diameter_mm": float(dia),
                "weight_kg_per_m": kgm,
                "breaking_load_t": float(mbl),
                "elongation_pct": float(t["elongation"]),
                "ea_kn": ea,
                "generic_of": _rope_generic(generics, t["material"], dia),
                "notes": notes,
                "provenance": {
                    "diameter_mm": prov(
                        HAMP,
                        page=page,
                        note=None if inner is None else f"exterior; interior {inner:g} mm",
                    ),
                    "weight_kg_per_m": wprov,
                    "breaking_load_t": prov(HAMP, page=page, note="«Breaking strength», t"),
                    "elongation_pct": prov(HAMP, page=page, note="cuadro «Properties»"),
                    "ea_kn": eaprov,
                },
            }
            out.append(item)
    page = "Hampidjan, «Combination Seine Net Rope», p. 234 (11.18)"
    for dia, kgm, kp in src.HAMPIDJAN_COMBINATION:
        out.append(
            {
                "id": f"hampidjan_combination_seine_{int(dia)}mm",
                "name": f"Randers Reb cabo combinado de cerco Ø{dia:g} mm (acero + Danline)",
                "brand": "Randers Reb",
                "product": "Combination Seine Net Rope",
                "country": "DK",
                "regions": list(HAMP_REGIONS),
                "material": "combinado",
                "construction": "4 cordones de alambre galvanizado forrados con hilo Danline",
                "diameter_mm": float(dia),
                "weight_kg_per_m": float(kgm),
                "breaking_load_t": r(kp / 1000.0),
                "generic_of": _rope_generic(generics, "combinado", dia),
                "notes": [
                    "Cabo de cerco (no de arrastre); en el catálogo de Hampidjan con los logos "
                    "de Randers Reb e Itsaskorda. La ficha no da alargamiento.",
                ],
                "provenance": {
                    "diameter_mm": prov(HAMP, page=page, note="dimensión nominal"),
                    "weight_kg_per_m": prov(HAMP, page=page, note="peso aproximado"),
                    "breaking_load_t": prov(HAMP, "derived", page, f"{kp:g} kp / 1000"),
                },
            }
        )
    return out


def garware_ropes_more(generics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for product, t in src.GARWARE_ROPES.items():
        page = f"Garware, «Fisheries: Trawl Ropes» ({product})"
        for dia, gm, bl in t["points"]:
            out.append(
                {
                    "id": f"garware_{_slug(product)}_{int(dia)}mm",
                    "name": f"Garware {product} Ø{int(dia)} mm ({t['material']})",
                    "brand": "Garware",
                    "product": product,
                    "country": "IN",
                    "regions": ["global", "south_asia", "africa", "latam"],
                    "material": t["material"],
                    "construction": t["construction"],
                    "diameter_mm": float(dia),
                    "weight_kg_per_m": gm / 1000.0,
                    "breaking_load_t": bl / 1000.0,
                    "generic_of": _rope_generic(generics, t["material"], dia),
                    "notes": ["La ficha no da alargamiento ni rigidez (sólo «bajo alargamiento»)."],
                    "provenance": {
                        "diameter_mm": prov("garware_fisheries", page=page),
                        "weight_kg_per_m": prov("garware_fisheries", page=page, note="g/m"),
                        "breaking_load_t": prov("garware_fisheries", page=page, note="kgf"),
                    },
                }
            )
    return out


def _wire_generic(generics: list[dict[str, Any]], key: str, dia: float) -> str | None:
    return nearest_generic(
        generics,
        lambda g: g["diameter_mm"],
        dia,
        lambda g, k=key: g["id"].startswith(f"wire_{k}_"),
    )


def hampidjan_wire(generics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for product, t in src.HAMPIDJAN_WIRE.items():
        page = f"Hampidjan, «{product}», {t['page']}"
        for dia, kgm, mbl in t["points"]:
            cprov = {"construction": prov(HAMP, page=page, note=t.get("construction_note"))}
            out.append(
                {
                    "id": f"{_slug(t['brand'])}_{_slug(product)}_{int(dia)}mm",
                    "name": f"{t['brand']} {product} Ø{int(dia)} mm",
                    "brand": t["brand"],
                    "product": product,
                    "country": t["country"],
                    "regions": list(HAMP_REGIONS),
                    "construction": t["construction"],
                    "core": t["core"],
                    "diameter_mm": float(dia),
                    "weight_kg_per_m": float(kgm),
                    "breaking_load_t": float(mbl),
                    "generic_of": _wire_generic(generics, t["generic"], dia),
                    "notes": [
                        "Tabla del catálogo de Hampidjan (distribuidor); la ficha no da "
                        "alargamiento ni módulo."
                    ],
                    "provenance": {
                        "diameter_mm": prov(HAMP, page=page),
                        "weight_kg_per_m": prov(HAMP, page=page, note="kg/m"),
                        "breaking_load_t": prov(HAMP, page=page, note="carga mínima de rotura, t"),
                        **(cprov if t.get("construction_note") else {}),
                    },
                }
            )
    return out


def bridon_wire_more(generics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for product, t in src.BRIDON_WIRE_MORE.items():
        page = f"Bridon-Bekaert 2023, «{t['page']}»"
        for dia, kg100, mbl in t["points"]:
            item = {
                "id": f"bridon_{_slug(product)}_{int(dia)}mm",
                "name": f"Bridon-Bekaert {product} Ø{int(dia)} mm",
                "brand": "Bridon-Bekaert",
                "product": product,
                "country": "BE",
                "regions": ["global", "europe"],
                "construction": t["construction"],
                "core": t["core"],
                "diameter_mm": float(dia),
                "weight_kg_per_m": kg100 / 100.0,
                "breaking_load_t": float(mbl),
                "generic_of": _wire_generic(generics, t["generic"], dia),
                "provenance": {
                    "diameter_mm": prov("bridon2023", page=page),
                    "weight_kg_per_m": prov("bridon2023", page=page, note="kg/100 m"),
                    "breaking_load_t": prov("bridon2023", page=page, note="carga mínima"),
                },
            }
            if t.get("note"):
                item["notes"] = [t["note"][0].upper() + t["note"][1:] + "."]
            out.append(item)
    return out


def _chain_generic(generics: list[dict[str, Any]], dia: float) -> str | None:
    """Cadena de alta resistencia genérica más cercana (sólo si difiere en ≤ 3 mm)."""
    cands = [g for g in generics if g["id"].startswith("chain_ht_")]
    best = min(cands, key=lambda g: abs(g["link_diameter_mm"] - dia))
    return best["id"] if abs(best["link_diameter_mm"] - dia) <= 3 else None


def hampidjan_chain(generics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for product, t in src.HAMPIDJAN_CHAIN.items():
        page = f"Hampidjan, «{product}», {t['page']}"
        for dia, e, h, load, kgm in t["points"]:
            if t["load"] == "swl":
                mbl = load * t["factor"]
                mprov = prov(
                    HAMP,
                    "derived",
                    page,
                    f"carga de trabajo {num(load)} t × factor {t['factor']:g}:1 de la ficha",
                )
            else:
                mbl = load
                mprov = prov(HAMP, page=page, note="«Breaking strength», t")
            item: dict[str, Any] = {
                "id": f"hampidjan_{_slug(t['brand'])}_long_link_{int(dia)}mm",
                "name": f"{t['brand']} cadena de eslabón largo Ø{int(dia)} mm",
                "brand": t["brand"],
                "product": product,
                "country": t["country"],
                "regions": list(HAMP_REGIONS),
                "link": "largo",
                "link_diameter_mm": float(dia),
                "grade": t["grade"],
                "weight_kg_per_m": float(kgm),
                "breaking_load_t": r(mbl),
                "generic_of": _chain_generic(generics, dia),
                "notes": [f"Eslabón interior {e:g} × {h:g} mm (largo × ancho)."]
                + ([f"Nota: {t['note']}."] if t.get("note") else []),
                "provenance": {
                    "link_diameter_mm": prov(HAMP, page=page),
                    "weight_kg_per_m": prov(HAMP, page=page),
                    "breaking_load_t": mprov,
                },
            }
            if t["load"] == "swl":
                item["notes"].append(f"Carga de trabajo (SWL, factor 5:1): {num(load)} t.")
            if not item["country"]:
                del item["country"]
            out.append(item)
    return out


def gunnebo_chain(generics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    page = "Gunnebo Industries Long Link Chain LLZ, tabla métrica"
    out = []
    for dia, pitch, w1, mbl, kgm in src.GUNNEBO_LLZ:
        out.append(
            {
                "id": f"gunnebo_llz_{int(dia)}mm",
                "name": f"Gunnebo LLZ grado 6 Ø{int(dia)} mm (eslabón largo, galvanizada)",
                "brand": "Gunnebo Industries",
                "product": f"LLZ-{int(dia)}-6",
                "country": "SE",
                "regions": ["global", "europe", "north_america"],
                "link": "largo",
                "link_diameter_mm": float(dia),
                "grade": "6",
                "weight_kg_per_m": float(kgm),
                "breaking_load_t": float(mbl),
                "generic_of": _chain_generic(generics, dia),
                "notes": [
                    f"Paso {pitch:g} mm, ancho exterior {w1:g} mm. Galvanizada en caliente; "
                    "factor de diseño 4:1; «no apta para izaje» (NS 9415, acuicultura y pesca)."
                ],
                "provenance": {
                    "link_diameter_mm": prov("gunnebo_llz", page=page, note="d nom."),
                    "weight_kg_per_m": prov("gunnebo_llz", page=page),
                    "breaking_load_t": prov(
                        "gunnebo_llz",
                        page=page,
                        note="la columna métrica dice «kg» pero son toneladas (columna imperial: "
                        "17 191 lb = 7,8 t para 9 mm)",
                    ),
                },
            }
        )
    return out


def hampidjan_floats(generics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    page = "Hampidjan, «Trawl float» (Atlantic Floats), p. 314 (15.2)"
    out = []
    for code, dia, w, buoy, dmax, dwork, mount in src.HAMPIDJAN_FLOAT:
        out.append(
            {
                "id": f"atlantic_floats_{code.lower()}",
                "name": f"Atlantic Floats {code} Ø{int(dia)} mm ({mount})",
                "brand": "Atlantic Floats",
                "product": code,
                "country": "DK",
                "regions": list(HAMP_REGIONS),
                "material": "plástico",
                "mount": mount,
                "diameter_mm": float(dia),
                "buoyancy_kgf": buoy / 1000.0,
                "max_depth_m": float(dmax),
                "generic_of": nearest_generic(
                    generics,
                    lambda g: g["diameter_mm"],
                    dia,
                    lambda g: g["material"] == "plástico",
                ),
                "notes": [
                    f"Peso {w:g} g; profundidad de trabajo {dwork:g} m (máxima {dmax:g} m).",
                ],
                "provenance": {
                    "diameter_mm": prov(HAMP, page=page),
                    "buoyancy_kgf": prov(HAMP, "derived", page, f"{buoy:g} g / 1000"),
                    "max_depth_m": prov(HAMP, page=page, note="«Max depth»"),
                },
            }
        )
    return out


def van_beest_shackles() -> list[dict[str, Any]]:
    page = "Hampidjan, «Shackle, safety type, Green Pin» (Van Beest), p. 275 (13.32)"
    out = []
    for code, wll, a, b, kg100 in src.HAMPIDJAN_SHACKLE:
        out.append(
            {
                "id": f"van_beest_green_pin_{code.lower()}",
                "name": f"Van Beest Green Pin {code}, grillete de seguridad {wll:g} t",
                "brand": "Van Beest",
                "product": "Green Pin safety bow shackle",
                "country": "NL",
                "regions": list(HAMP_REGIONS),
                "type": "bow",
                "size": f"{a:g} mm",
                "body_diameter_mm": float(a),
                "pin_diameter_mm": float(b),
                "wll_t": float(wll),
                "design_factor": 6.0,
                "breaking_load_t": r(6.0 * wll),
                "weight_kg": kg100 / 100.0,
                "notes": ["Perno con tuerca y chaveta (tipo de seguridad)."],
                "provenance": {
                    "body_diameter_mm": prov(HAMP, page=page, note="cota A"),
                    "pin_diameter_mm": prov(HAMP, page=page, note="cota B"),
                    "wll_t": prov(HAMP, page=page, note="WLL 6:1"),
                    "design_factor": prov(HAMP, page=page, note="«WLL 6:1»"),
                    "breaking_load_t": prov(HAMP, "derived", page, f"6 × WLL = 6 × {wll:g} t"),
                    "weight_kg": prov(HAMP, "derived", page, f"{kg100:g} kg/100 u. / 100"),
                },
            }
        )
    return out


def crosby_shackles() -> list[dict[str, Any]]:
    page = "Crosby, «G-209 / S-209 Screw Pin Anchor Shackles», p. 24"
    out = []
    for size, wll, stock, kg, pin, body in src.CROSBY_G209:
        out.append(
            {
                "id": f"crosby_g209_{_slug(size)}in",
                "name": f"Crosby G-209 {size} in, grillete de perno roscado {wll:g} t",
                "brand": "Crosby",
                "product": "G-209",
                "country": "US",
                "regions": ["global", "north_america", "latam", "europe"],
                "type": "bow",
                "size": f"{size} in",
                "body_diameter_mm": float(body),
                "pin_diameter_mm": float(pin),
                "wll_t": float(wll),
                "design_factor": 6.0,
                "breaking_load_t": r(6.0 * wll),
                "weight_kg": float(kg),
                "notes": [f"Código G-209 {stock}; galvanizado en caliente; grado 6."],
                "provenance": {
                    "body_diameter_mm": prov("crosby_g209", page=page, note="cota D"),
                    "pin_diameter_mm": prov("crosby_g209", page=page, note="cota B"),
                    "wll_t": prov("crosby_g209", page=page),
                    "design_factor": prov("crosby_g209", page=page, note="«6:1 Design Factor»"),
                    "breaking_load_t": prov(
                        "crosby_g209", "derived", page, f"6 × WLL = 6 × {wll:g} t"
                    ),
                    "weight_kg": prov("crosby_g209", page=page, note="peso de una pieza"),
                },
            }
        )
    return out


# --- Libro Excel de la A-3 -------------------------------------------------------------------


def excel_items(kind: str) -> list[dict[str, Any]]:
    def exc(cell: str) -> dict[str, Any]:
        return prov("giamportone2024", "excel", note=cell)

    out: list[dict[str, Any]] = []
    if kind == "door":
        raw = yaml.safe_load((DATA / "doors.yaml").read_text(encoding="utf-8"))
        for d in raw["doors"]:
            item = {
                "id": d["id"],
                "name": d["name"],
                "type": "flat_wood" if d["type"].startswith("flat") else "oval",
                "brand": "Morgère" if "morgere" in d["id"] else None,
                "length_m": d["length_m"],
                "height_m": d["height_m"],
                "area_m2": d["area_m2"],
                "weight_air_kg": d["weight_air_kg"],
                "weight_water_kg": d["weight_water_kg"],
                "weight_water_coefficient": d.get("weight_water_coefficient"),
                "coefficients": [
                    {k: c[k] for k in ("angle_deg", "cl", "cd")} for c in d["coefficients"]
                ],
                "regions": ["global"],
                "provenance": {
                    f: exc(d["source"])
                    for f in ("length_m", "height_m", "area_m2", "weight_air_kg", "coefficients")
                },
            }
            item["provenance"]["coefficients"] = prov(
                "giamportone2024",
                "excel",
                note=d["source"]
                + ": "
                + (FLAT_POLAR_NOTE if d["type"].startswith("flat") else OVAL_POLAR_NOTE)
                + " (fuente primaria: sfia1993)",
            )
            if item["brand"]:
                item["generic_of"] = "door_oval_100hp"
            out.append(item)
        return out
    file, rows = {
        "rope": ("ropes", None),
        "wire": ("warps", None),
        "chain": ("chains", None),
        "float": ("floats", None),
        "twine": ("materials", None),
    }[kind]
    del rows
    raw = yaml.safe_load((DATA / f"{file}.yaml").read_text(encoding="utf-8"))
    for k, it in enumerate(raw["items"]):
        cell = it.get("source", raw.get("source"))
        if kind == "rope":
            out.append(
                {
                    "id": it["id"],
                    "name": f"{it['brand']} {it['description']}",
                    "brand": it["brand"],
                    "country": "AR",
                    "regions": ["latam"],
                    "material": "combinado" if "combinado" in it["material"] else it["material"],
                    "construction": it["construction"],
                    "diameter_mm": float(it["diameter_mm"]),
                    "weight_kg_per_m": float(it["weight_kg_per_m"]),
                    "breaking_load_t": float(it["breaking_load_t"]),
                    "provenance": {
                        f: exc(cell) for f in ("diameter_mm", "weight_kg_per_m", "breaking_load_t")
                    },
                }
            )
        elif kind == "wire":
            out.append(
                {
                    "id": it["id"],
                    "name": f"Cable {it['construction']} Ø{it['diameter_mm']:g} mm",
                    "construction": it["construction"],
                    "core": "IWRC",
                    "diameter_mm": float(it["diameter_mm"]),
                    "weight_kg_per_m": float(it["weight_kg_per_m"]),
                    "breaking_load_t": float(it["breaking_load_t"]),
                    "regions": ["latam"],
                    "provenance": {
                        f: exc(cell) for f in ("diameter_mm", "weight_kg_per_m", "breaking_load_t")
                    },
                }
            )
        elif kind == "chain":
            out.append(
                {
                    "id": it["id"],
                    "name": f"{it['brand']} {it['description']}",
                    "brand": it["brand"],
                    "regions": ["latam"],
                    "link": "corto" if it["link"] == "short" else "largo",
                    "link_diameter_mm": float(it["link_diameter_mm"]),
                    "grade": str(it["grade"]),
                    "weight_kg_per_m": float(it["weight_kg_per_m"]),
                    "breaking_load_t": float(it["breaking_load_t"]),
                    "generic_of": "chain_ht_7mm"
                    if it["link_diameter_mm"] == 7
                    else "chain_ht_19mm",
                    "provenance": {
                        f: exc(cell)
                        for f in ("link_diameter_mm", "weight_kg_per_m", "breaking_load_t")
                    },
                }
            )
        elif kind == "float":
            out.append(
                {
                    "id": f"float_excel_{int(it['diameter_mm'])}mm_{k}",
                    "name": f"Boya Ø{int(it['diameter_mm'])} mm (libro Excel de la A-3)",
                    "material": "plástico",
                    "diameter_mm": float(it["diameter_mm"]),
                    "buoyancy_kgf": float(it["buoyancy_kgf"]),
                    "regions": ["latam"],
                    "notes": [it["note"]] if it.get("note") else [],
                    "provenance": {f: exc(cell) for f in ("diameter_mm", "buoyancy_kgf")},
                }
            )
        elif kind == "twine":
            out.append(
                {
                    "id": f"twine_excel_{it['id']}",
                    "name": f"Hilo PA R{it['rtex']:g} tex (libro Excel de la A-3)",
                    "material": it["material"],
                    "rtex": float(it["rtex"]),
                    "diameter_mm": float(it["diameter_mm"]),
                    "runnage_m_per_kg": float(it["runnage_m_per_kg"]),
                    "regions": ["latam"],
                    "provenance": {
                        f: exc(cell) for f in ("rtex", "diameter_mm", "runnage_m_per_kg")
                    },
                }
            )
    return out


# --- Escritura -------------------------------------------------------------------------------


def write(kind: str, name: str, docs: list[str], items: list[dict[str, Any]]) -> None:
    path = OUT / kind / f"{name}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"kind": kind, "sources": [source(d) for d in docs], "items": items}
    path.write_text(
        HEADER + yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )


def main() -> int:
    tw = twine_generics()
    ro = rope_generics()
    wi = wire_generics()
    write("twine", "generic_workbook", [WB], tw)
    write("twine", "garware", ["garware_fisheries"], garware_twine(tw) + garware_twisted(tw))
    write("twine", "hampidjan", [HAMP], hampidjan_twine(tw))
    write("twine", "excel_a3", ["giamportone2024"], excel_items("twine"))
    write("rope", "generic_workbook", [WB], ro)
    write("rope", "garware", ["garware_fisheries"], garware_rope(ro) + garware_ropes_more(ro))
    write("rope", "hampidjan", [HAMP], hampidjan_rope(ro))
    write("rope", "excel_a3", ["giamportone2024"], excel_items("rope"))
    write("wire", "generic_workbook", [WB], wi)
    write("wire", "bridon_2023", ["bridon2023"], bridon_wire(wi) + bridon_wire_more(wi))
    write("wire", "hampidjan", [HAMP], hampidjan_wire(wi))
    write("wire", "pfeifer", ["pfeifer_6x19w"], pfeifer_wire(wi))
    write("wire", "excel_a3", ["giamportone2024"], excel_items("wire"))
    fl = float_generics()
    write("float", "generic_workbook", [WB], fl)
    write("float", "hampidjan", [HAMP], hampidjan_floats(fl))
    write("float", "excel_a3", ["giamportone2024"], excel_items("float"))
    ch = chain_generics()
    write("chain", "generic_workbook", [WB], ch)
    write("chain", "hampidjan", [HAMP], hampidjan_chain(ch))
    write("chain", "gunnebo", ["gunnebo_llz"], gunnebo_chain(ch))
    write("shackle", "hampidjan", [HAMP], van_beest_shackles())
    write("shackle", "crosby", ["crosby_g209"], crosby_shackles())
    write("chain", "excel_a3", ["giamportone2024"], excel_items("chain"))
    dg = door_generics()
    write("door", "generic_workbook", [WB, "sfia1993", "mellibovsky2018"], dg)
    write("door", "rebyc_colombia", ["zuniga2006", "sfia1993"], door_rebyc())
    write("door", "noaa_ff9", ["gutherz1974", "sfia1993"], door_noaa_ff9())
    vonin_docs = ["vonin_doors", "vonin_simoon", "sfia1993", "mellibovsky2018"]
    write("door", "vonin", vonin_docs, vonin_doors(dg))
    write("door", "morgere_2025", ["morgere2025", "sfia1993"], morgere_doors(dg))
    write("door", "excel_a3", ["giamportone2024", "sfia1993"], excel_items("door"))

    from trawlkit import components as comp

    comp._load_kind.cache_clear()
    bad = 0
    for kind in comp.KINDS:
        items = comp.load_components(kind, statuses=("published", "draft", "user"))
        issues = [i for it in items for i in comp.check(it)]
        errs = [i for i in issues if i.level == "error"]
        bad += len(errs)
        print(f"{kind}: {len(items)} ítems, {len(errs)} errores, {len(issues) - len(errs)} avisos")
        for i in issues:
            print(f"   {i.level}: {i.message}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
