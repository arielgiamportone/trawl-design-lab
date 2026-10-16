"""Extrae las tablas de referencia y los catálogos del Excel original a ``src/trawlkit/data/``.

Uso: ``uv run python -m tools.extract.reference``

Salidas (todas regenerables, no editar a mano):

``src/trawlkit/data/reference/*.csv`` (UTF-8, cabecera en inglés ``snake_case``):

- ``nomura_proportions.csv``  Tablas de Referencias!A16:L25 (proporciones del Dr. Nomura).
- ``cut_ratios.csv``          Tablas de Referencias!A48:F88 (razón de corte → código de corte).
- ``knot_factor_k.csv``       Tablas de Referencias!A96:Z111 (factor K de nudos, formato largo).
- ``catenary.csv``            Tablas de Referencias!A117:H171 (DPA/L → fL/L, α).
- ``useful_angles.csv``       Tablas de Referencias!A176:H216. Las cinco columnas de la hoja son
  listas independientes de distinta longitud (listas de validación), por eso se vuelca en formato
  largo ``parameter,value,source`` con un parámetro por lista.
- ``danleno_height_vs_depth.csv``  Tablas de Referencias!A202:B240. También son dos listas
  independientes (20 profundidades, 39 alturas): se conservan fila a fila, con ``depth_m`` vacío
  donde la hoja no tiene valor.
- ``depth_to_warp.csv``       Tablas de Referencias!A353:C383 (profundidad → cable filado).
- ``power_coefficients.yaml`` coeficientes empíricos de los métodos de potencia disponible.

``src/trawlkit/data/*.yaml`` (validados con ``trawlkit.io.schema``): ``doors``, ``floats``,
``ropes``, ``chains``, ``warps``, ``materials``.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

import yaml
from tools.extract.common import DATA, cell, rows

from trawlkit.io.schema import Catalogue, DoorCatalogue, PropellerType

TABLAS = "Tablas de Referencias"
POTENCIA = "Potencia Disponible Arrastre OK"
POTENCIA_FRIDMAN = "Potenc disponible para arrastre"
FLOTACION = "Flotación y Lastre"
MECANICA = "Mecánica de la Red"

REF_DIR = DATA / "reference"

HEADER = (
    "# Archivo generado por tools/extract/reference.py a partir de\n"
    "# legacy/Calculos_Red_FAO_A3.xlsx. No editar a mano; regenerar con:\n"
    "#   uv run python -m tools.extract.reference\n"
)

_DECIMAL_COMMA = re.compile(r"^-?\d+(?:,\d+)?$")


# --------------------------------------------------------------------------- helpers
def src(sheet: str, ref: str) -> str:
    return f"{sheet}!{ref}"


def to_num(value: Any) -> float | None:
    """Convierte un valor de celda a ``float`` (admite texto con coma decimal); ``None`` si no."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if _DECIMAL_COMMA.match(text):
        return float(text.replace(",", "."))
    try:
        return float(text)
    except ValueError:
        return None


def clean(value: float | None) -> float | int | None:
    """Entero cuando el valor es entero (``1.0`` → ``1``); evita ruido de coma flotante."""
    if value is None:
        return None
    rounded = round(value, 10)
    return int(rounded) if rounded == int(rounded) else rounded


def parse_range(text: Any) -> list[float] | float | None:
    """``'0,17 - 0,20'`` → ``[0.17, 0.2]``; un número suelto → ``float``."""
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    parts = [to_num(p) for p in re.split(r"\s*-\s*", str(text).strip())]
    nums = [p for p in parts if p is not None]
    if len(nums) == 1:
        return nums[0]
    return nums or None


def numbers_in(text: str) -> list[float]:
    """Todos los números (con coma o punto decimal) que aparecen en un texto."""
    return [float(m.replace(",", ".")) for m in re.findall(r"\d+(?:[.,]\d+)?", text)]


def write_csv(path: Path, fieldnames: list[str], records: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for rec in records:
            writer.writerow({k: ("" if v is None else v) for k, v in rec.items()})
    return path


def write_yaml(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, width=100)
    path.write_text(HEADER + body, encoding="utf-8")
    return path


# --------------------------------------------------------------------------- tablas CSV
def nomura_proportions() -> list[dict[str, Any]]:
    cols = ["l_m", "l_b", "m_b", "a_b", "c_b", "d_b", "e_b", "f_b", "d_minus_c_b"]
    out = []
    for i, row in enumerate(rows(TABLAS, "A16:L25"), start=16):
        name = row[0]
        values = [to_num(v) for v in row[3:12]]
        rec: dict[str, Any] = {"net_type": name}
        rec.update({c: clean(v) for c, v in zip(cols, values, strict=True)})
        notes = []
        if rec["a_b"] is not None and rec["a_b"] > 5:
            notes.append(f"a/b = {rec['a_b']} en G{i} parece un error de tipeo por 1.06")
        if row[11] == "-":
            notes.append(f"L{i} = '-' en la hoja (sin dato)")
        rec["note"] = "; ".join(notes) or None
        rec["source"] = src(TABLAS, f"A{i}:L{i}")
        out.append(rec)
    return out


def cut_ratios() -> list[dict[str, Any]]:
    out = []
    formulas = rows(TABLAS, "A49:F88", data_only=False)
    for i, (row, frow) in enumerate(zip(rows(TABLAS, "A49:F88"), formulas, strict=True), 49):
        ratio, _, code, inexact, width, height = row
        if code is None:
            continue  # fila sin terminar (sin código de corte)
        raw = frow[0]
        if isinstance(raw, str) and raw.startswith("="):
            label = raw[1:]
        elif isinstance(raw, str):
            label = raw
        else:
            label = f"{int(width)}/{int(height)}" if width and height else ""
        ratio_num = to_num(ratio)
        if ratio_num is None and isinstance(ratio, str) and "/" in ratio:
            num, den = ratio.split("/", 1)  # filas 69-72: razón escrita como texto '2/1'
            ratio_num = float(num) / float(den)
        out.append(
            {
                "cut_ratio": clean(ratio_num),
                "cut_ratio_label": label,
                "cut_code": code,
                "inexact_ratio": clean(to_num(inexact)),
                "mesh_increase_width": clean(to_num(width)),
                "mesh_increase_height": clean(to_num(height)),
                "source": src(TABLAS, f"A{i}:F{i}"),
            }
        )
    return out


def knot_factor_k() -> list[dict[str, Any]]:
    letters = "BCDEFGHIJKLMNOPQRSTUVWXYZ"
    diameters = [to_num(v) for v in rows(TABLAS, "B97:Z97")[0]]
    out = []
    for i, row in enumerate(rows(TABLAS, "A98:Z111"), start=98):
        mesh = to_num(row[0])
        if mesh is None:
            continue
        for col, dia, k in zip(letters, diameters, row[1:], strict=True):
            if k is None:
                continue
            out.append(
                {
                    "mesh_mm": clean(mesh),
                    "twine_diameter_mm": clean(dia),
                    "k": clean(to_num(k)),
                    "source": src(TABLAS, f"{col}{i}"),
                }
            )
    return out


def catenary() -> list[dict[str, Any]]:
    out = []
    for i, row in enumerate(rows(TABLAS, "A119:H171"), start=119):
        dpa_l, dpa, length, fl_l, _, _, _, alpha = row
        if fl_l is None and alpha is None:
            continue
        out.append(
            {
                "dpa_l": clean(to_num(dpa_l)),
                "dpa_m": clean(to_num(dpa)),
                "l_m": clean(to_num(length)),
                "fl_l": clean(to_num(fl_l)),
                "alpha_deg": clean(to_num(alpha)),
                "source": src(TABLAS, f"A{i}:H{i}"),
            }
        )
    return out


def useful_angles() -> list[dict[str, Any]]:
    lists = {
        "sweep_angle_deg": "A",  # δ Patentes
        "dremiere_ratio": "B",  # Relación Dremière patentes
        "sweep_length_m": "C",  # Longitudes permitidas en patentes
        "useful_percentage": "F",  # Porcentajes útiles
        "nhp_hp": "H",  # NHP posibles
    }
    out = []
    for name, col in lists.items():
        for i, (value,) in enumerate(rows(TABLAS, f"{col}177:{col}216"), start=177):
            if value is None:
                continue
            out.append(
                {
                    "parameter": name,
                    "value": clean(to_num(value)),
                    "source": src(TABLAS, f"{col}{i}"),
                }
            )
    return out


def danleno_height_vs_depth() -> list[dict[str, Any]]:
    out = []
    for i, (depth, height) in enumerate(rows(TABLAS, "A202:B240"), start=202):
        if depth is None and height is None:
            continue
        out.append(
            {
                "depth_m": clean(to_num(depth)),
                "danleno_arm_height_m": clean(to_num(height)),
                "source": src(TABLAS, f"A{i}:B{i}"),
            }
        )
    return out


def depth_to_warp() -> list[dict[str, Any]]:
    out = []
    for i, (depth, warp, ratio) in enumerate(rows(TABLAS, "A354:C383"), start=354):
        if depth is None:
            continue
        out.append(
            {
                "depth_m": clean(to_num(depth)),
                "warp_length_m": clean(to_num(warp)),
                "ratio": clean(to_num(ratio)),
                "source": src(TABLAS, f"A{i}:C{i}"),
            }
        )
    return out


# --------------------------------------------------------------------------- potencia
_PROPELLERS = [
    PropellerType.FIXED_PITCH,
    PropellerType.FIXED_PITCH_NOZZLE,
    PropellerType.VARIABLE_PITCH,
    PropellerType.VARIABLE_PITCH_NOZZLE,
]


def _formula_number(sheet: str, ref: str, index: int) -> float:
    """``index``-ésimo número literal de la fórmula de una celda (p.ej. ``=0.75 *0.2*B73``)."""
    formula = str(cell(sheet, ref, data_only=False))
    body = re.sub(r"[A-Z]+\$?\d+", "", formula)  # quita referencias de celda (B73, $F$70…)
    return numbers_in(body)[index]


def power_coefficients() -> dict[str, Any]:
    # Fridman: KF embebido en el texto de E3/E4 ("…igual a 10 para hélice…"); la hoja lo lee con
    # MID(E3,38,2). B6/B7 de Tablas de Referencias repiten el valor en numérico.
    kf_pf_text = numbers_in(str(cell(POTENCIA, "E3")))[0]
    kf_pvt_text = numbers_in(str(cell(POTENCIA, "E4")))[0]
    kf_pf = to_num(cell(TABLAS, "B6"))
    kf_pvt = to_num(cell(TABLAS, "B7"))
    assert kf_pf == kf_pf_text and kf_pvt == kf_pvt_text, "KF inconsistente entre hojas"

    # Reparto energético de Fridman: los porcentajes viven en las fórmulas C24:C31
    # (=C25*0.33, =C25*0.35, …), no en celdas numéricas.
    split_rows = {
        "nominal_over_bhp": ("C24", "HP nominales = BHP + BHP·0.33"),
        "towing": ("C26", "Para tiro de red"),
        "propeller_rotation": ("C27", "Pérdida giro de hélice"),
        "wave_making": ("C28", "Pérdida por oleaje"),
        "hull_friction": ("C29", "Rozamiento"),
        "wake_turbulence": ("C30", "Estela y turbulencia"),
        "air": ("C31", "Aire"),
    }
    energy_split = {
        key: {
            "fraction": clean(_formula_number(POTENCIA_FRIDMAN, ref, 0)),
            "label": label,
            "source": src(POTENCIA_FRIDMAN, ref),
        }
        for key, (ref, label) in split_rows.items()
    }

    # Bollard pull: factores K por tipo de hélice a 150 / 180 HP (K52:L55) y porcentajes de Prado
    # embebidos en los rótulos A49/A51/A53/A55 ("BP P.FIJO = BHP * 0,9 * 1,10/ 100").
    k_rows = {p: 52 + n for n, p in enumerate(_PROPELLERS)}
    hp_150 = numbers_in(str(cell(POTENCIA, "A7")))[0]
    hp_180 = numbers_in(str(cell(POTENCIA, "A19")))[0]
    bollard_k = {
        p.value: {
            "label": str(cell(POTENCIA, f"H{r}")).strip(),
            f"k_{int(hp_150)}hp": clean(to_num(cell(POTENCIA, f"K{r}"))),
            f"k_{int(hp_180)}hp": clean(to_num(cell(POTENCIA, f"L{r}"))),
            "source": src(POTENCIA, f"H{r}:L{r}"),
        }
        for p, r in k_rows.items()
    }
    prado_rows = dict(zip(_PROPELLERS, ["A49", "A51", "A53", "A55"], strict=True))
    prado_pct = {}
    for p, ref in prado_rows.items():
        label = str(cell(POTENCIA, ref))
        nums = numbers_in(label.split("=", 1)[1])  # 0,9 ; 1,10 ; 100
        prado_pct[p.value] = {
            "label": label.strip(),
            "base_factor": clean(nums[0]),
            "propeller_factor": clean(nums[1]),
            "divisor": clean(nums[2]),
            "source": src(POTENCIA, ref),
        }

    # Prado: K por hélice/rpm en los rótulos I68:I77 y las fórmulas K68:K77 (=0.75*K*APN).
    prado_k = []
    for r in range(68, 78):
        label = str(cell(POTENCIA, f"I{r}")).strip()
        prado_k.append(
            {
                "label": label,
                "propeller": _propeller_from_label(label).value,
                "rpm": _rpm_from_label(label),
                "k": clean(_formula_number(POTENCIA, f"K{r}", 1)),
                "source": src(POTENCIA, f"I{r}:K{r}"),
            }
        )
    prado = {
        "bollard_pull_percent": prado_pct,
        "available_fraction_of_apn": clean(_formula_number(POTENCIA, "K68", 0)),
        "apn_factor_of_bollard_pull": clean(_formula_number(POTENCIA, "B73", 0)),
        "k_by_propeller_rpm": prado_k,
        "source": src(POTENCIA, "A49:L77"),
    }

    # Koyama (J164:M167) + BHP_F = 60 % BHP (A169/C169).
    koyama_rows = []
    for r in range(165, 168):
        koyama_rows.append(
            {
                "vessel_size_t": _as_list(parse_range(cell(POTENCIA, f"J{r}"))),
                "bhp": _bhp_field(cell(POTENCIA, f"K{r}")),
                "propeller_diameter_mm": clean(to_num(cell(POTENCIA, f"L{r}"))),
                "k": clean(to_num(cell(POTENCIA, f"M{r}"))),
                "source": src(POTENCIA, f"J{r}:M{r}"),
            }
        )
    koyama = {
        "bhp_fraction": clean(_formula_number(POTENCIA, "C169", 1)),
        "bhp_fraction_label": str(cell(POTENCIA, "A169")).strip(),
        "k_table": koyama_rows,
        "source": src(POTENCIA, "J164:M167"),
    }

    # Nomura (I205:L214).
    k3_classes = {
        "small": "208",
        "medium": "209",
        "large_300_1000_t": "210",
        "large_over_1000_t": "211",
    }
    nomura = {
        "k1_engine_utilisation": clean(to_num(cell(POTENCIA, "L205"))),
        "k2_sea_state": clean(to_num(cell(POTENCIA, "L206"))),
        "k3_propulsion_efficiency": {
            key: {
                "label": str(cell(POTENCIA, f"I{r}")).strip(),
                "range": _as_list(parse_range(cell(POTENCIA, f"L{r}"))),
                "source": src(POTENCIA, f"I{r}:L{r}"),
            }
            for key, r in k3_classes.items()
        },
        "k3_average": clean(to_num(cell(POTENCIA, "L212"))),
        "net_resistance_fraction": clean(to_num(cell(POTENCIA, "L213"))),
        "hp_in_kgf_m_s": clean(numbers_in(str(cell(POTENCIA, "L214")))[0]),
        "source": src(POTENCIA, "I205:L214"),
    }

    # Hamuro (A254:L265): K1, K2 y K3 por hélice/rpm. El bloque F263:L265 repite F256:L258.
    headers = [str(v).strip() for v in rows(POTENCIA, "F255:L255")[0]]
    k3_a = rows(POTENCIA, "F258:L258")[0]
    k3_b = rows(POTENCIA, "F265:L265")[0]
    assert k3_a == k3_b, "Hamuro K3 difiere entre F258:L258 y F265:L265"
    assert rows(POTENCIA, "F256:L257") == rows(POTENCIA, "F263:L264")
    hamuro_k3 = []
    for n, (label, value) in enumerate(zip(headers, k3_a, strict=True)):
        col = "FGHIJKL"[n]
        hamuro_k3.append(
            {
                "label": label,
                "propeller": _propeller_from_label(label).value,
                "rpm": "high" if ">300" in label.replace(" ", "") else "low",
                "k3": clean(to_num(value)),
                "source": src(POTENCIA, f"{col}255,{col}258,{col}265"),
            }
        )
    hamuro = {
        "k1_fraction_of_nhp": clean(to_num(cell(POTENCIA, "C254"))),
        "k2_sea_state": clean(to_num(cell(POTENCIA, "F257"))),
        "k3_by_propeller_rpm": hamuro_k3,
        "hp_in_kgf_m_s": clean(numbers_in(str(cell(POTENCIA, "C263")))[0]),
        "source": src(POTENCIA, "A253:L267"),
    }

    return {
        "description": "Coeficientes empíricos de los métodos de potencia disponible para arrastre",
        "fridman": {
            "formula": str(cell(POTENCIA, "B3")).strip(),
            "kf": {
                PropellerType.FIXED_PITCH.value: clean(kf_pf),
                PropellerType.VARIABLE_PITCH_NOZZLE.value: clean(kf_pvt),
            },
            "kf_source": [src(TABLAS, "A6:B7"), src(POTENCIA, "E3:E4")],
            "energy_split": energy_split,
            "hp_to_kw": clean(_formula_number(POTENCIA_FRIDMAN, "E25", 0)),
            "energy_split_source": src(POTENCIA_FRIDMAN, "A24:E31"),
        },
        "bollard_pull_k": {"by_propeller": bollard_k, "source": src(POTENCIA, "H51:L55")},
        "prado": prado,
        "koyama": koyama,
        "nomura": nomura,
        "hamuro": hamuro,
    }


def _as_list(value: list[float] | float | None) -> list[float] | None:
    if value is None:
        return None
    vals = value if isinstance(value, list) else [value]
    return [v for v in (clean(x) for x in vals) if v is not None]


def _bhp_field(value: Any) -> dict[str, Any] | float | None:
    if isinstance(value, str) and value.strip().startswith("<"):
        return {"max": clean(numbers_in(value)[0])}
    return clean(to_num(value))


def _rpm_from_label(label: str) -> str | None:
    text = label.lower()
    if "alta" in text:
        return "high"
    if "baja" in text:
        return "low"
    return None  # el rótulo no indica régimen de rpm


def _propeller_from_label(label: str) -> PropellerType:
    text = label.lower().replace(" ", "")
    nozzle = "tob" in text or "+t" in text
    variable = "var" in text or "pv" in text
    if variable:
        return PropellerType.VARIABLE_PITCH_NOZZLE if nozzle else PropellerType.VARIABLE_PITCH
    return PropellerType.FIXED_PITCH_NOZZLE if nozzle else PropellerType.FIXED_PITCH


# --------------------------------------------------------------------------- catálogos YAML
def _door(
    block_row: int, door_id: str, door_type: str, coef_rows: tuple[int, int]
) -> dict[str, Any]:
    r = block_row
    coefficients = []
    for i in range(coef_rows[0], coef_rows[1] + 1):
        angle, cl, cd = (to_num(cell(TABLAS, f"{c}{i}")) for c in "BCD")
        rec: dict[str, Any] = {"angle_deg": clean(angle), "cl": clean(cl), "cd": clean(cd)}
        if cl == 0 and cd == 0:
            rec["cl"] = rec["cd"] = None
            rec["note"] = f"CL = CD = 0 en la hoja (C{i}:D{i}); sin dato a este ángulo"
        rec["source"] = src(TABLAS, f"B{i}:D{i}")
        coefficients.append(rec)
    weight_air = to_num(cell(TABLAS, f"C{r + 7}"))
    coef_water = to_num(cell(TABLAS, f"C{r + 8}"))
    return {
        "id": door_id,
        "name": str(cell(TABLAS, f"B{r}")).strip(),
        "type": door_type,
        "length_m": clean(to_num(cell(TABLAS, f"C{r + 2}"))),
        "height_m": clean(to_num(cell(TABLAS, f"C{r + 3}"))),
        "area_m2": clean(to_num(cell(TABLAS, f"C{r + 4}"))),
        "aspect_ratio": clean(to_num(cell(TABLAS, f"C{r + 5}"))),
        "area_ratio": clean(to_num(cell(TABLAS, f"C{r + 6}"))),
        "weight_air_kg": clean(weight_air),
        "weight_water_coefficient": clean(coef_water),
        "weight_water_kg": clean(to_num(cell(TABLAS, f"C{r + 9}"))),
        "coefficients": coefficients,
        "source": src(TABLAS, f"A{r}:E{coef_rows[1]}"),
    }


def doors() -> dict[str, Any]:
    return {
        "doors": [
            _door(245, "fao_flat_wood_a3", "flat_wood_iron_frame", (259, 264)),
            _door(267, "morgere_polivalente_oval", "oval_polyvalent", (281, 286)),
        ]
    }


def floats() -> dict[str, Any]:
    items = []
    seen: dict[float, int] = {}
    for i, (dia, buoy) in enumerate(rows(FLOTACION, "D72:E82"), start=72):
        d = to_num(dia)
        seen[d] = seen.get(d, 0) + 1
        items.append(
            {
                "diameter_mm": clean(d),
                "buoyancy_kgf": clean(to_num(buoy)),
                "source": src(FLOTACION, f"D{i}:E{i}"),
            }
        )
    for item in items:
        if seen[item["diameter_mm"]] > 1:
            item["note"] = (
                f"la hoja lista {seen[item['diameter_mm']]} boyas de {item['diameter_mm']} mm con "
                "distinta flotación (modelos distintos); se conservan todas"
            )
    return {"kind": "floats", "source": src(FLOTACION, "D70:E82"), "items": items}


def ropes() -> dict[str, Any]:
    items = []
    for i, (brand, desc, dia, _, weight, strength) in enumerate(rows(TABLAS, "A293:F296"), 293):
        text = str(desc).strip()
        if text.upper().startswith("PP"):
            material, construction = "PP", "retorcido 3 cordones"
        else:
            material, construction = "combinado (PP + acero)", "acero 6x24+7"
        items.append(
            {
                "id": re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_"),
                "brand": str(brand).strip().title(),
                "description": text,
                "material": material,
                "construction": construction,
                "diameter_mm": clean(to_num(dia)),
                "weight_kg_per_m": clean(to_num(weight)),
                "breaking_load_t": clean(to_num(strength)),
                "source": src(TABLAS, f"A{i}:F{i}"),
            }
        )
    return {"kind": "ropes", "source": src(TABLAS, "A292:F296"), "items": items}


def chains() -> dict[str, Any]:
    items = []
    pattern = re.compile(r"(CORTO|LARGO)\s+(\d+)\s+GRADO\s*(\d+)\s+(\d+)", re.IGNORECASE)
    for i, (brand, desc, weight) in enumerate(rows(TABLAS, "A316:C317"), start=316):
        text = str(desc).strip()
        m = pattern.match(text)
        assert m, f"descripción de cadena no reconocida: {text!r}"
        link = "short" if m.group(1).upper() == "CORTO" else "long"
        items.append(
            {
                "id": f"{str(brand).lower()}_{link}_link_{m.group(2)}mm",
                "brand": str(brand).strip(),
                "description": text,
                "link": link,
                "link_diameter_mm": int(m.group(2)),
                "grade": int(m.group(3)),
                "breaking_load_t": int(m.group(4)),
                "weight_kg_per_m": clean(to_num(weight)),
                "source": src(TABLAS, f"A{i}:C{i}"),
            }
        )
    return {"kind": "chains", "source": src(TABLAS, "A314:C317"), "items": items}


def warps() -> dict[str, Any]:
    items = []
    for i, (dia, construction, _, weight, strength, ref) in enumerate(
        rows(TABLAS, "B338:G343"), start=338
    ):
        d = to_num(dia)
        items.append(
            {
                "id": f"steel_6x19_seale_{str(clean(d)).replace('.', '_')}mm",
                "material": "acero",
                "construction": str(construction).strip(),
                "diameter_mm": clean(d),
                "weight_kg_per_m": clean(to_num(weight)),
                "breaking_load_t": clean(to_num(strength)),
                "reference": str(ref).strip(),
                "source": src(TABLAS, f"B{i}:G{i}"),
            }
        )
    return {"kind": "warps", "source": src(TABLAS, "B337:G343"), "items": items}


def materials() -> dict[str, Any]:
    items = []
    coef_sea = to_num(cell(TABLAS, "G36"))
    coef_fresh = to_num(cell(TABLAS, "I36"))
    for i, row in enumerate(rows(TABLAS, "A36:I37"), start=36):
        name, density, runnage, _, rtex, dia = row[:6]
        items.append(
            {
                "id": f"{str(name).lower()}_r{int(to_num(rtex))}tex",
                "material": str(name).strip(),
                "density_kg_m3": clean(to_num(density)),
                "runnage_m_per_kg": clean(to_num(runnage)),
                "rtex": clean(to_num(rtex)),
                "diameter_mm": clean(to_num(dia)),
                "weight_in_water_coefficient_seawater": clean(coef_sea),
                "weight_in_water_coefficient_freshwater": clean(coef_fresh),
                "source": src(TABLAS, f"A{i}:I{i}"),
            }
        )
    return {
        "kind": "materials",
        "source": src(TABLAS, "A35:I37"),
        "items": items,
        "constants": {
            "seawater_density_kg_m3": clean(to_num(cell(MECANICA, "O127"))),
            "freshwater_density_kg_m3": clean(to_num(cell(MECANICA, "O128"))),
            "g_m_s2": clean(to_num(cell(MECANICA, "O129"))),
            "source": src(MECANICA, "L127:P129"),
        },
        "notes": [
            "Los coeficientes de peso en el agua (G36/I36) sólo figuran en la fila 36 de la hoja; "
            "se aplican a ambos hilos de PA."
        ],
    }


# --------------------------------------------------------------------------- run
def run() -> list[Path]:
    """Genera todos los CSV/YAML y devuelve las rutas escritas."""
    written: list[Path] = []

    tables: list[tuple[str, list[dict[str, Any]]]] = [
        ("nomura_proportions.csv", nomura_proportions()),
        ("cut_ratios.csv", cut_ratios()),
        ("knot_factor_k.csv", knot_factor_k()),
        ("catenary.csv", catenary()),
        ("useful_angles.csv", useful_angles()),
        ("danleno_height_vs_depth.csv", danleno_height_vs_depth()),
        ("depth_to_warp.csv", depth_to_warp()),
    ]
    for name, records in tables:
        written.append(write_csv(REF_DIR / name, list(records[0]), records))

    written.append(write_yaml(REF_DIR / "power_coefficients.yaml", power_coefficients()))

    doors_payload = DoorCatalogue.model_validate(doors()).model_dump(mode="json")
    written.append(write_yaml(DATA / "doors.yaml", doors_payload))

    for builder in (floats, ropes, chains, warps, materials):
        payload = Catalogue.model_validate(builder()).model_dump(mode="json")
        written.append(write_yaml(DATA / f"{payload['kind']}.yaml", payload))
    return written


if __name__ == "__main__":
    for path in run():
        print(path.relative_to(DATA.parent))
