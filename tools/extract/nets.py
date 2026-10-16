"""Extrae las redes FAO A-3 (estándar y modificada) y el catálogo de buques del Excel original.

Escribe ``fao_a3_standard.yaml``, ``fao_a3_modified.yaml`` y ``vessels.yaml`` en
``src/trawlkit/data/``.
Todos los valores salen del libro (``openpyxl`` con valores cacheados); las celdas de origen
quedan registradas en ``source_cells``. Uso::

    uv run python -m tools.extract.nets
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from tools.extract.common import DATA, XLSX, cell, num, rows

from trawlkit.io.schema import NetSpec, VesselCatalogue

PANELS = "Paños de red y cortes"
DIM = "Dimensiones de la Red"
CABLES = "Cables Y Cabulleria"
FLOAT = "Flotación y Lastre"
SPECIES = "Especie Blanco"
VESSELS = "Tipo de buques"
POWER = "Potenc disponible para arrastre"

HEADER = (
    "# Generado por tools/extract/nets.py a partir de legacy/Calculos_Red_FAO_A3.xlsx\n"
    "# (hojas 'Paños de red y cortes', 'Dimensiones de la Red', 'Cables Y Cabulleria',\n"
    "# 'Flotación y Lastre', 'Especie Blanco', 'Tipo de buques', 'Potenc disponible para\n"
    "# arrastre'). No editar a mano: regenerar con `uv run python -m tools.extract.nets`.\n"
)

# Cada bloque de "compostura" de la hoja ocupa un juego de columnas. Hay dos juegos lado a lado:
# el izquierdo (A..L) y el derecho (M..X). Las claves son los conceptos de la fila de cabecera
# ("Rendimiento", "Mallero", "Lado", "Coeficiente X", "Coeficiente Y", "N° Mallas", "Ø", "Rtex").
LEFT = {
    "runnage": "A",
    "mesh": "B",
    "side": "C",
    "coef_x": "D",
    "coef_y": "F",
    "meshes": "H",
    "dia": "J",
    "rtex": "K",
}
RIGHT = {
    "runnage": "M",
    "mesh": "N",
    "side": "O",
    "coef_x": "P",
    "coef_y": "R",
    "meshes": "T",
    "dia": "V",
    "rtex": "W",
}
ALL_COLS = "A:X"


@dataclass(frozen=True)
class Block:
    """Ubicación de un panel en la hoja 'Paños de red y cortes'.

    ``rows`` son las tres filas del bloque (una por "Lado": a (T1), b (T2), h (N); el orden
    lo decide la celda ``side`` de cada fila, no se asume). ``header_row`` es la fila donde
    aparece la letra del panel sobre el dibujo (la misma que usan los COUNTIF de la hoja).
    ``cut_cells`` son las celdas con el código de corte X1 y (opcional) X2. ``summary_row`` es
    la fila de la tabla resumen N269:W291 (material en T, U1 en W). ``mirror_cols`` indica que
    el mismo panel está repetido en el otro juego de columnas (plan inferior) con los mismos
    valores: se verifica y se expresa con ``count`` + ``planes_covered``.
    """

    id: str
    name: str
    plane: str
    section: str
    cols: dict[str, str]
    rows: tuple[int, int, int]
    header_row: int
    cut_cells: tuple[str, ...]
    summary_row: int
    mirror_cols: dict[str, str] | None = None
    mirror_summary_row: int | None = None
    planes_covered: tuple[str, ...] = field(default_factory=tuple)


# Tabla de paneles (letras del plano). Filas/columnas verificadas contra el libro:
#   A  H55:H57  (cortes I63/I64)      B  T54:T56  (cortes T62/T63)
#   C  H90:H92  (cortes H97/H98)      D  T89:T91  (cortes T97/T98)
#   E  H120:H122 (corte H127)         F  T114:T116 (cortes T122/T123)
#   G  H156:H158 = T156:T158 (D1/V1)  H  H189:H191 = T189:T191 (D2/V2)
#   I  H222:H224 (cortes H229/H230)   J  T222:T224 (cortes T229/T230)
#   I' H255:H257 = T255:T257 (bolsa modificada, superior e inferior)
STANDARD_BLOCKS: tuple[Block, ...] = (
    Block(
        "A",
        "Punta de ala superior (izq. y der.)",
        "upper",
        "wing_tip",
        LEFT,
        (55, 56, 57),
        37,
        ("I63", "I64"),
        271,
    ),
    Block(
        "B",
        "Punta de ala inferior (izq. y der.)",
        "lower",
        "wing_tip",
        RIGHT,
        (54, 55, 56),
        37,
        ("T62", "T63"),
        282,
    ),
    Block(
        "C",
        "Ala superior (izq. y der.)",
        "upper",
        "wing",
        LEFT,
        (90, 91, 92),
        67,
        ("H97", "H98"),
        272,
    ),
    Block(
        "D",
        "Ala inferior (izq. y der.)",
        "lower",
        "wing",
        RIGHT,
        (89, 90, 91),
        67,
        ("T97", "T98"),
        283,
    ),
    Block("E", "Square", "upper", "square", LEFT, (120, 121, 122), 100, ("H127",), 275),
    Block(
        "F",
        "2ª sección ala inferior (izq. y der.)",
        "lower",
        "belly",
        RIGHT,
        (114, 115, 116),
        100,
        ("T122", "T123"),
        286,
    ),
    Block(
        "G",
        "Cuerpo 1: dorso D1 (superior) y vientre V1 (inferior)",
        "upper",
        "body",
        LEFT,
        (156, 157, 158),
        133,
        ("H163",),
        276,
        RIGHT,
        288,
        ("upper", "lower"),
    ),
    Block(
        "H",
        "Cuerpo 2: dorso D2 (superior) y vientre V2 (inferior)",
        "upper",
        "body",
        LEFT,
        (189, 190, 191),
        166,
        ("H196",),
        277,
        RIGHT,
        289,
        ("upper", "lower"),
    ),
    Block(
        "I",
        "Bolsa superior (estándar)",
        "upper",
        "codend",
        LEFT,
        (222, 223, 224),
        199,
        ("H229", "H230"),
        278,
    ),
    Block(
        "J",
        "Bolsa inferior (estándar)",
        "lower",
        "codend",
        RIGHT,
        (222, 223, 224),
        199,
        ("T229", "T230"),
        290,
    ),
)
MODIFIED_CODEND = Block(
    "I'",
    "Bolsa modificada para crustáceos (superior e inferior)",
    "upper",
    "codend",
    LEFT,
    (255, 256, 257),
    232,
    ("H262", "H263"),
    279,
    RIGHT,
    291,
    ("upper", "lower"),
)
STANDARD_CODENDS = {"I", "J"}

# Etiquetas "Lado" de la hoja: 'a (T1)' es el borde mayor, 'b (T2)' el menor, 'h (N)' el alto.
SIDE_KEYS = {"a": "meshes_a", "b": "meshes_b", "h": "meshes_depth"}

# Borde del panel que mira a la boca de la red ("meshes_top"); el otro mira a la bolsa
# ("meshes_bottom"). La hoja sólo distingue borde mayor/menor (T1/T2), así que la orientación se
# toma de los planos 2D (legacy/planos/fao_a3_estandar.pdf y fao_a3_modificada.pdf): A/B 3→57,
# C 57→117, D 57→97, E 412→372, F 129→143, G 372→162, H 243→113, I/J 113→113, I' 139→139.
FRONT_EDGE = {
    "A": "b",
    "B": "b",
    "C": "a",
    "D": "b",
    "E": "a",
    "F": "b",
    "G": "a",
    "H": "a",
    "I": "a",
    "J": "a",
    "I'": "a",
}


def _ref(sheet: str, ref: str) -> str:
    return f"{sheet}!{ref}"


def _text(sheet: str, ref: str) -> str | None:
    v = cell(sheet, ref)
    if v is None or (isinstance(v, str) and v.startswith("#")):
        return None
    return str(v).strip()


def _block_values(cols: dict[str, str], block_rows: tuple[int, int, int]) -> dict[str, Any]:
    """Lee las tres filas de un bloque y devuelve valores + celdas de origen."""
    values: dict[str, Any] = {}
    cells: dict[str, str] = {}
    for r in block_rows:
        side = _text(PANELS, f"{cols['side']}{r}") or ""
        key = SIDE_KEYS[side[0].lower()]
        values[key] = int(num(PANELS, f"{cols['meshes']}{r}"))
        cells[key] = _ref(PANELS, f"{cols['meshes']}{r}")
        coef_col = cols["coef_y"] if key == "meshes_depth" else cols["coef_x"]
        coef_key = "plan_coef_y" if key == "meshes_depth" else "plan_coef_x"
        coef = num(PANELS, f"{coef_col}{r}")
        if coef_key in values and values[coef_key] != coef:
            raise ValueError(f"coeficiente {coef_key} inconsistente en fila {r}")
        values[coef_key] = coef
        cells.setdefault(coef_key, _ref(PANELS, f"{coef_col}{r}"))
    r0 = block_rows[0]
    for key, col in (("mesh_mm", "mesh"), ("twine_diameter_mm", "dia"), ("rtex", "rtex")):
        values[key] = num(PANELS, f"{cols[col]}{r0}")
        cells[key] = _ref(PANELS, f"{cols[col]}{r0}")
    values["runnage_m_per_kg"] = round(num(PANELS, f"{cols['runnage']}{r0}"), 2)
    cells["runnage_m_per_kg"] = _ref(PANELS, f"{cols['runnage']}{r0}")
    values["source_cells"] = cells
    return values


def _panel(block: Block) -> dict[str, Any]:
    v = _block_values(block.cols, block.rows)
    cells = v.pop("source_cells")

    if block.mirror_cols is not None:
        mirror = _block_values(block.mirror_cols, block.rows)
        mirror.pop("source_cells")
        if mirror != v:
            raise ValueError(f"panel {block.id}: el bloque espejo no coincide ({mirror} != {v})")

    header = rows(PANELS, f"A{block.header_row}:X{block.header_row}")[0]
    count = sum(1 for x in header if isinstance(x, str) and x.strip() == block.id)
    if count == 0:
        raise ValueError(f"panel {block.id}: no aparece en la fila {block.header_row}")
    cells["count"] = _ref(PANELS, f"{block.header_row}:{block.header_row}")

    summary_mesh = num(PANELS, f"Q{block.summary_row}")
    if summary_mesh != v["mesh_mm"]:
        raise ValueError(f"panel {block.id}: mallero resumen {summary_mesh} != {v['mesh_mm']}")
    hanging = num(PANELS, f"W{block.summary_row}")
    cells["hanging_ratio"] = _ref(PANELS, f"W{block.summary_row}")
    if block.mirror_summary_row is not None:
        if num(PANELS, f"W{block.mirror_summary_row}") != hanging:
            raise ValueError(f"panel {block.id}: U1 distinto en el plan inferior")
    material = _text(PANELS, f"T{block.summary_row}") or "PA"
    cells["material"] = _ref(PANELS, f"T{block.summary_row}")

    cut_x1 = _text(PANELS, block.cut_cells[0])
    cells["cut_code"] = _ref(PANELS, block.cut_cells[0])
    cut_x2 = _text(PANELS, block.cut_cells[1]) if len(block.cut_cells) > 1 else None
    if len(block.cut_cells) > 1:
        cells["cut_code_x2"] = _ref(PANELS, block.cut_cells[1])

    front = FRONT_EDGE[block.id]
    rear = "a" if front == "b" else "b"
    cells["meshes_top"] = cells[f"meshes_{front}"]
    cells["meshes_bottom"] = cells[f"meshes_{rear}"]

    panel: dict[str, Any] = {
        "id": block.id,
        "name": block.name,
        "plane": block.plane,
        "section": block.section,
        "material": material,
        "mesh_mm": v["mesh_mm"],
        "twine_diameter_mm": v["twine_diameter_mm"],
        "rtex": v["rtex"],
        "runnage_m_per_kg": v["runnage_m_per_kg"],
        "meshes_top": v[f"meshes_{front}"],
        "meshes_bottom": v[f"meshes_{rear}"],
        "meshes_depth": v["meshes_depth"],
        "meshes_a": v["meshes_a"],
        "meshes_b": v["meshes_b"],
        "hanging_ratio": hanging,
        "count": count,
    }
    if block.planes_covered:
        panel["planes_covered"] = list(block.planes_covered)
    if cut_x1 is not None:
        panel["cut_code"] = cut_x1
    if cut_x2 is not None:
        panel["cut_code_x2"] = cut_x2
    panel["plan_coef_x"] = v["plan_coef_x"]
    panel["plan_coef_y"] = v["plan_coef_y"]
    panel["source_cells"] = cells
    return panel


def _species() -> dict[str, Any]:
    return {
        "name": _text(SPECIES, "C3"),
        # Corrige el error de tipeo de la hoja ("gragaria" → "gregaria").
        "scientific_name": _text(SPECIES, "H3").replace("gragaria", "gregaria"),
        "depth_m": num(SPECIES, "E5"),
        "bottom_type": _text(SPECIES, "E6"),
        "source_cells": {
            "name": _ref(SPECIES, "C3"),
            "scientific_name": _ref(SPECIES, "H3"),
            "depth_m": _ref(SPECIES, "E5"),
            "bottom_type": _ref(SPECIES, "E6"),
        },
    }


def _rope(cables_row: int, length_ref: str) -> dict[str, Any]:
    name = _text(CABLES, f"A{cables_row}")
    construction = _text(CABLES, f"D{cables_row}")
    length = num(DIM, length_ref)
    if num(CABLES, f"J{cables_row}") != length:
        raise ValueError(f"longitud de {name}: {CABLES}!J{cables_row} != {DIM}!{length_ref}")
    return {
        "name": f"{name} - {construction}",
        "construction": construction,
        "length_m": length,
        "diameter_mm": num(CABLES, f"I{cables_row}"),
        "weight_kg_per_m": num(CABLES, f"G{cables_row}"),
        "breaking_load_t": num(CABLES, f"H{cables_row}"),
        "source_cells": {
            "name": _ref(CABLES, f"A{cables_row}"),
            "construction": _ref(CABLES, f"D{cables_row}"),
            "length_m": _ref(DIM, length_ref),
            "diameter_mm": _ref(CABLES, f"I{cables_row}"),
            "weight_kg_per_m": _ref(CABLES, f"G{cables_row}"),
            "breaking_load_t": _ref(CABLES, f"H{cables_row}"),
        },
    }


def _floats() -> dict[str, Any]:
    count = int(num(FLOAT, "F84"))
    if int(num(FLOAT, "F91")) != count:
        raise ValueError("Flotación: F84 != F91")
    diameter = num(FLOAT, "F92")
    total = num(FLOAT, "F90")
    if num(DIM, "F63") != total:
        raise ValueError("Flotación total: F90 != Dimensiones!F63")
    # Tabla de boyas D72:F82 (diámetro, flotación unitaria, n° de boyas para la red de 150 HP).
    # F92 = LOOKUP(F91, cincuenta, D72:D82) elige la última fila cuyo n° de boyas es F91.
    each_row = None
    for i, (d, each, n) in enumerate(rows(FLOAT, "D72:F82"), start=72):
        if d == diameter and n == count:
            each_row = (i, float(each))
    if each_row is None:
        raise ValueError("Flotación: no se encontró la boya seleccionada en D72:F82")
    return {
        "count": count,
        "diameter_mm": diameter,
        "buoyancy_kgf_each": each_row[1],
        "total_buoyancy_kgf": total,
        "required_buoyancy_kgf": round(num(FLOAT, "F70"), 3),
        "source_cells": {
            "count": _ref(FLOAT, "F84"),
            "diameter_mm": _ref(FLOAT, "F92"),
            "buoyancy_kgf_each": _ref(FLOAT, f"E{each_row[0]}"),
            "total_buoyancy_kgf": _ref(FLOAT, "F90"),
            "required_buoyancy_kgf": _ref(FLOAT, "F70"),
        },
    }


COMMON_NOTES = [
    "Convención de `count`: en alas y puntas de ala (A, B, C, D, F) `count: 2` significa panel "
    "izquierdo + derecho del mismo plano (fila del dibujo: la letra aparece dos veces, p. ej. "
    'N62 = SUM(COUNTIF(37:37,"A"),COUNTIF(37:37,"B")) = 4).',
    "En G, H e I' el Excel etiqueta con la misma letra el panel del plan alto (dorso D) y el del "
    "plan bajo (vientre V), con composturas idénticas (verificado: bloques H156:K158 = T156:W158, "
    "etc.). Se expresan como un panel con `count: 2` y `planes_covered: [upper, lower]`; "
    "`plane` indica el bloque de referencia (superior).",
    "`meshes_top` es el borde del panel más cercano a la boca de la red (donde empieza el paño) y "
    "`meshes_bottom` el borde hacia la bolsa, según los planos 2D (A/B 3→57, C 57→117, D 57→97, "
    "E 412→372, F 129→143, G 372→162, H 243→113, I/J 113→113, I' 139→139). La hoja no usa esa "
    "convención: 'a (T1)' es el borde mayor y 'b (T2)' el menor; se conservan como `meshes_a` y "
    "`meshes_b` con sus celdas de origen.",
    "`hanging_ratio` es el U1 (coeficiente de abertura horizontal) de la tabla resumen "
    "N269:W291 (0.38 para mallero 80/60 mm, 0.23 para 40/30 mm), que alimenta 'Mecánica de la "
    "Red'!K56:K60. `plan_coef_x`/`plan_coef_y` (0.5 / 1) son los coeficientes X/Y 'en el plano' "
    "con los que la hoja convierte mallas a metros (columnas D/F y P/R).",
    "`cut_code` es el corte X1 (VLOOKUP sobre 'Tablas de Referencias'!A49:C88) y `cut_code_x2` "
    "el X2. En el panel F el X1 (T122) devuelve #N/A en el libro y se omite.",
    "Runnage: el libro calcula 1e6/Rtex (781.25 y 1052.63 m/kg); los planos redondean a 781 y "
    "1053 m/kg. Material PA (nylon, 'NY' en los planos).",
    "Flotación: 12 boyas de Ø200 mm para 36 kgf (promedio Fridman a 150 HP, 'Flotación y "
    "Lastre'!F70→F90). Para 180 HP el libro calcula 39.9 kgf (G70) → 13 boyas (G82). El plano "
    "impreso indica 'Flotación total=33Kg' con 12 boyas.",
    "Lastre: `ballast_kg` = 'Flotación y Lastre'!F226 ('Lastre máximo para 150 HP', 42 kg, "
    "coincide con 'Lastre total=42Kg' de los planos); el mínimo (F225) es `ballast_min_kg`. "
    "Distribución (F243:I245): reglaje 12 kg (cadena 2 m), bocana 8 kg, alas 22 kg.",
]


def _net_common() -> dict[str, Any]:
    return {
        "species": _species(),
        "headrope": _rope(3, "F45"),
        "footrope": _rope(4, "F46"),
        "floats": _floats(),
        "ballast_kg": num(FLOAT, "F226"),
        "ballast_min_kg": num(FLOAT, "F225"),
        "source_cells": {
            "ballast_kg": _ref(FLOAT, "F226"),
            "ballast_min_kg": _ref(FLOAT, "F225"),
        },
    }


def standard_net() -> dict[str, Any]:
    panels = [_panel(b) for b in STANDARD_BLOCKS]
    return {
        "id": "fao_a3_standard",
        "name": "Red de arrastre de fondo FAO A-3 (estándar, bolsa 40 mm)",
        "description": "Red de dos caras para langostilla, pesqueros de 150-180 BHP. Paneles A..J "
        "según la hoja 'Paños de red y cortes' y el plano legacy/planos/fao_a3_estandar.pdf.",
        "source": XLSX.name,
        "panels": panels,
        **_net_common(),
        "notes": list(COMMON_NOTES),
    }


def modified_net() -> dict[str, Any]:
    panels = [_panel(b) for b in STANDARD_BLOCKS if b.id not in STANDARD_CODENDS]
    panels.append(_panel(MODIFIED_CODEND))
    return {
        "id": "fao_a3_modified",
        "name": "Red de arrastre de fondo FAO A-3 modificada para crustáceos (bolsa 30 mm)",
        "description": "Igual que la estándar salvo la bolsa: los paneles I/J (40 mm, 113 mallas) "
        "se reemplazan por I' (30 mm, 139 × 300 mallas, superior e inferior). Plano "
        "legacy/planos/fao_a3_modificada.pdf.",
        "source": XLSX.name,
        "variant_of": "fao_a3_standard",
        "panels": panels,
        **_net_common(),
        "notes": [
            "Variante de fao_a3_standard: sólo cambia la bolsa (I' sustituye a I y J). Flotación y "
            "lastre se mantienen (el libro usa la misma distribución F84/F226 para ambas redes).",
            *COMMON_NOTES,
        ],
    }


# Bloques de potencia: (celda BHP, celda HP nominal, celda HP de tiro, celda vel. almirantazgo).
# El desplazamiento no tiene celda propia: está embebido en la fórmula de velocidad de
# almirantazgo, p. ej. H27 = ((C24*285)/(10^(2/3)))^(1/3) → Δ = 10 t.
POWER_BLOCKS = (("C25", "C24", "C26", "H27"), ("C37", "C36", "C38", "H38"))
_DISPLACEMENT_RE = re.compile(r"/\((\d+(?:\.\d+)?)\^\(2/3\)\)")


def _vessel(bhp_ref: str, nominal_ref: str, pull_ref: str, adm_ref: str) -> dict[str, Any]:
    bhp = num(POWER, bhp_ref)
    formula = cell(POWER, adm_ref, data_only=False)
    m = _DISPLACEMENT_RE.search(str(formula))
    if m is None:
        raise ValueError(f"{POWER}!{adm_ref}: no se pudo leer el desplazamiento de {formula!r}")
    length_txt = _text(VESSELS, "B4") or ""
    lm = re.search(r"(\d+(?:\.\d+)?)", length_txt)
    if lm is None:
        raise ValueError(f"{VESSELS}!B4: eslora ilegible {length_txt!r}")
    return {
        "id": f"fao_a3_{bhp:.0f}hp",
        "name": f"Pesquero de rada/ría {bhp:.0f} BHP (el modelo cubre hélice PF y PV+T)",
        "bhp": bhp,
        "length_m": float(lm.group(1)),
        "beam_m": num(VESSELS, "B5"),
        "depth_m": num(VESSELS, "B6"),
        "displacement_t": float(m.group(1)),
        "propeller": "fixed_pitch",
        "high_rpm": True,
        "nominal_hp": round(num(POWER, nominal_ref), 2),
        "trawl_pull_hp": round(num(POWER, pull_ref), 2),
        "vessel_class": _text(VESSELS, "A3"),
        "source_cells": {
            "bhp": _ref(POWER, bhp_ref),
            "length_m": _ref(VESSELS, "B4"),
            "beam_m": _ref(VESSELS, "B5"),
            "depth_m": _ref(VESSELS, "B6"),
            "displacement_t": _ref(POWER, adm_ref),
            "nominal_hp": _ref(POWER, nominal_ref),
            "trawl_pull_hp": _ref(POWER, pull_ref),
            "vessel_class": _ref(VESSELS, "A3"),
        },
    }


def vessel_catalogue() -> dict[str, Any]:
    return {
        "source": XLSX.name,
        "notes": [
            f"Eslora: '{_text(VESSELS, 'B4')}' ({VESSELS}!B4), se registra el máximo.",
            "Desplazamiento tomado de la fórmula de velocidad de almirantazgo "
            "('Potenc disponible para arrastre'!H27/H38). El libro no distingue buques por tipo "
            "de hélice: el mismo preset vale para PF y PV+T.",
            "nominal_hp = BHP × 1.33 (C24/C36); trawl_pull_hp = BHP × 0.33 (C26/C38).",
        ],
        "vessels": [_vessel(*refs) for refs in POWER_BLOCKS],
    }


def _source_last(obj: Any) -> Any:
    """Deja ``notes`` y ``source_cells`` al final de cada mapeo."""
    if isinstance(obj, dict):
        trailing = ("notes", "source_cells")
        out = {k: _source_last(v) for k, v in obj.items() if k not in trailing}
        out.update({k: obj[k] for k in trailing if k in obj})
        return out
    if isinstance(obj, list):
        return [_source_last(v) for v in obj]
    return obj


def _write(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = yaml.safe_dump(_source_last(data), allow_unicode=True, sort_keys=False, width=100)
    path.write_text(HEADER + body, encoding="utf-8")
    return path


def run() -> list[Path]:
    """Extrae y escribe los tres YAML; devuelve las rutas escritas."""
    outputs = [
        (DATA / "fao_a3_standard.yaml", NetSpec, standard_net()),
        (DATA / "fao_a3_modified.yaml", NetSpec, modified_net()),
        (DATA / "vessels.yaml", VesselCatalogue, vessel_catalogue()),
    ]
    written: list[Path] = []
    for path, model, raw in outputs:
        validated = model.model_validate(raw)
        written.append(_write(path, validated.model_dump(mode="json", exclude_none=True)))
    return written


if __name__ == "__main__":
    for p in run():
        print(p)
