"""Transcripciones de la Fase 19.6: redes del catálogo tailandés de la SEAFDEC (2016).

Mismas convenciones que ``tools/catalog/transcriptions.py`` (filas ``(id, plane, section, count,
mesh_mm, rtex, top, bottom, depth, cut[, material])``).

**SEAFDEC (2016) TD/RES/141**, *The Catalogue Bottom Trawl Net Designs of Thailand*: planos
redibujados al estilo de los catálogos de la FAO. Cada página da el tipo de arrastre, el buque
(nombre, eslora y potencia), el lugar y el año del relevamiento; el plano trae el medio dorso a la
izquierda y el medio vientre a la derecha, con el cuerpo y el copo dibujados una vez (comunes a las
dos caras), y las columnas de filas, mallero (mm) y material (PE en denier/cabos). La imagen
embebida de cada plano es de 96 ppp (563 × 777 px); se compuso sobre blanco y se amplió 2 a 8
veces para leer cada número.

Convenciones de la lectura:

* **Relingas**: el plano da el largo total arriba (flecha hacia arriba = lima, hacia abajo =
  burlón), el cabo de cada ala («2 × 9,00 PE Ø12») y el tramo de la bocana. En casi todos los
  planos lima = 2 × ala + bocana; donde no cierra se dice en la nota.
* **U1**: el plano no lo da. Se deriva por cara de la relinga de la bocana sobre el paño estirado
  de la bocana (mallas del borde de boca del primer paño menos las de las dos alas) y se usa en toda
  la cara, como en las redes del INIDEP (Fase 19.5).
* **Hilo**: el Rtex se deriva del denier como n·den/9 (sin el aumento por torsión), como en el
  plano 03 (Fase 19.5). El plano rotula el material sólo en algunas filas: un paño sin rótulo
  toma el del rótulo más cercano de su columna (se dice en la nota de procedencia).
* **Uniones**: el plano da la razón de unión entre paños (8/9, 4/5, 1/1…). Una unión 1/1 entre
  malleros distintos frunce el paño más grande; si la diferencia de largo estirado pasa del 20 %
  el validador la toma como error y la red queda en borrador.
* **Aparejo**: los planos no dan boyas, lastre, portones, tangones ni vara. El caso de diseño usa
  la eslora del documento y los valores por defecto del motor (portón de la A-3 escalado por
  potencia; tangones y vara de :mod:`trawlkit.rigging.multirig`).
"""

from __future__ import annotations

from typing import Any

from tools.catalog.transcriptions_195 import rtex_from_denier

ACCESSED_196 = "2026-10-27"

SEAFDEC_URL = "https://repository.seafdec.or.th/handle/20.500.12067/1826"

# --- Hilos (denier/cabos → Rtex ≈ n·den/9) ---------------------------------------------------
R250_6 = rtex_from_denier(250, 6)  # 166,7
R250_9 = rtex_from_denier(250, 9)  # 250
R380_6 = rtex_from_denier(380, 6)  # 253,3
R380_9 = rtex_from_denier(380, 9)  # 380
R380_12 = rtex_from_denier(380, 12)  # 506,7
R380_15 = rtex_from_denier(380, 15)  # 633,3
R380_18 = rtex_from_denier(380, 18)  # 760
R700_12 = rtex_from_denier(700, 12)  # 933,3
R700_15 = rtex_from_denier(700, 15)  # 1166,7
R700_21 = rtex_from_denier(700, 21)  # 1633,3
DENIER = {
    R250_6: "250d/6",
    R250_9: "250d/9",
    R380_6: "380d/6",
    R380_9: "380d/9",
    R380_12: "380d/12",
    R380_15: "380d/15",
    R380_18: "380d/18",
    R700_12: "700d/12",
    R700_15: "700d/15",
    R700_21: "700d/21",
}


def _dec(x: float, nd: int = 2) -> str:
    """Número con coma decimal (notas en castellano)."""
    return f"{x:.{nd}f}".replace(".", ",")


def _source(no: str, kind: str, printed_page: int) -> dict[str, Any]:
    return {
        "key": "seafdec2016thai",
        "title": f"SEAFDEC (2016) The Catalogue Bottom Trawl Net Designs of Thailand, TD/RES/141, "
        f"plano {no} ({kind})",
        "url": SEAFDEC_URL,
        "figure": f"Plano {no}",
        "page": f"{printed_page} ({printed_page + 6} del PDF)",
        "accessed": ACCESSED_196,
    }


def _u1(
    plane: str,
    rope_m: float,
    first: tuple[int, float],
    wing: tuple[int, float],
) -> tuple[float, str, str]:
    """U1 de una cara: relinga de la bocana sobre el paño estirado de la bocana.

    ``first`` = (mallas del borde de boca, mallero mm) del primer paño de la cara; ``wing`` =
    (mallas del borde de bolsa, mallero mm) del ala.
    """
    stretched = first[0] * first[1] / 1000.0 - 2 * wing[0] * wing[1] / 1000.0
    u1 = round(rope_m / stretched, 2)
    face = "dorso" if plane == "upper" else "vientre"
    rope = "lima" if plane == "upper" else "burlón"
    note = (
        f"U1 de la bocana del {face}: {rope} de {_dec(rope_m)} m sobre {first[0]} × "
        f"{first[1]:g} mm − 2 × {wing[0]} × {wing[1]:g} mm = {_dec(stretched)} m de paño "
        f"estirado ({_dec(rope_m)} / {_dec(stretched)} = {_dec(u1)}); se usa en todo el {face}"
    )
    return (u1, "derived", note)


def _rtex_overrides(
    panels: list[tuple[Any, ...]], inherited: dict[str, str] | None = None
) -> dict[str, dict[str, tuple[str, str]]]:
    """Procedencia del Rtex de cada paño (derivado del denier) y, si el plano no rotula el
    material en esa fila, de dónde se tomó el rótulo."""
    out: dict[str, dict[str, tuple[str, str]]] = {}
    for row in panels:
        pid, rtex = row[0], row[5]
        note = f"Rtex ≈ n·den/9 de PE {DENIER[rtex]} (sin el aumento por torsión; A VERIFICAR)"
        if inherited and pid in inherited:
            note += f"; {inherited[pid]}"
        out[pid] = {"rtex": ("derived", note)}
    return out


def _merge(*dicts: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for d in dicts:
        for k, v in d.items():
            out.setdefault(k, {}).update(v)
    return out


def _lower(panels: list[tuple[Any, ...]], start: int) -> list[tuple[Any, ...]]:
    """Paños del cuerpo y el copo del vientre: los del dorso desde ``start`` (comunes)."""
    out = []
    for row in panels[start:]:
        pid = "L" + row[0][1:]
        out.append((pid, "lower", *row[2:]))
    return out


def _rope(
    total: float,
    wing: float,
    bosom: float,
    diameter: float,
    material: str,
    rope: str,
    pieces: dict[str, tuple[str, str | None]] | None = None,
) -> dict[str, Any]:
    return {
        "length_m": total,
        "wing_m": wing,
        "bosom_m": bosom,
        "diameter_mm": diameter,
        "material": material,
        "rope": rope,
        "pieces": pieces
        or {
            "wing_m": ("transcribed", None),
            "bosom_m": ("transcribed", None),
        },
    }


_SHARED_NOTE = "Paño del cuerpo dibujado una vez en el plano, común al dorso y al vientre."
_RIG_NOTE = (
    "El plano no da boyas, lastre, portones ni tangones: el caso usa la eslora del documento y "
    "los valores por defecto del motor (portón de la A-3 escalado por potencia, tangones de "
    "24 pies a 20° de Knake et al. 1958 y tijera de 70 m del INIDEP), que no son los de la "
    "flota tailandesa."
)
_SHRIMP = "camarón (shrimp)"


def _shared_notes(panels: list[tuple[Any, ...]], start: int) -> dict[str, str]:
    return {row[0]: _SHARED_NOTE for row in panels[start:]}


# --- Plano 31: «Otter with Boom», 14 m, 75 hp (Laem Ngob, Trat, 1986) ---------------------------
_P31_U = [
    ("UW", "upper", "wing", 2, 38, R380_9, 50, 133, 250, "1N4B / AB"),
    ("U1", "upper", "square", 1, 38, R380_9, 420, 380, 30, "1N4B"),
    ("U2", "upper", "body", 1, 38, R380_9, 380, 320, 60, "1N2B"),
    ("U3", "upper", "body", 1, 32, R380_9, 360, 240, 120, "1N2B"),
    ("U4", "upper", "body", 1, 25, R250_9, 270, 120, 150, "1N2B"),
    ("UC", "upper", "codend", 1, 20, R250_9, 150, 150, 200, None),
]
_P31_L = [("LW", "lower", "wing", 2, 38, R380_9, 50, 143, 280, "1N4B / AB"), *_lower(_P31_U, 2)]
_P31 = _P31_U + _P31_L
_P31_INH = {
    p: "el plano rotula «PE 380d/9» en las alas; el cuerpo de 38 y 32 mm no lleva rótulo"
    for p in ("U1", "U2", "U3", "L2", "L3")
} | {p: "el copo no lleva rótulo: se toma el «PE 250d/9» del cuerpo de 25 mm" for p in ("UC", "LC")}

SEAFDEC_31: dict[str, Any] = {
    "id": "seafdec_31_outrigger_shrimp",
    "name": "Arrastre camaronero con tangón, 14 m y 75 hp (SEAFDEC 2016, n.º 31)",
    "description": (
        "Red camaronera de dos caras para tangones («otter with boom») de un buque de 14 m y "
        "75 hp (Laem Ngob, Trat, Tailandia, 1986): alas y cielo de 38 mm, cuerpo de 38, 32 y "
        "25 mm y copo de 20 mm, PE; lima de 21,00 m y burlón de 22,40 m."
    ),
    "family": "bottom",
    "rig": "outrigger",
    "vessel_hp": (75, 75),
    "target_species": _SHRIMP,
    "source": _source("31", "Bottom, Otter with Boom; Shrimp", 44),
    "material": "PE",
    "panels": _P31,
    "panel_notes": {
        **_shared_notes(_P31_U, 2),
        "U2": f"{_SHARED_NOTE} Unión 8/9 con el paño de 32 mm (320 → 360 mallas).",
        "U3": f"{_SHARED_NOTE} Unión 8/9 con el paño de 25 mm (240 → 270 mallas).",
        "U4": f"{_SHARED_NOTE} Unión 4/5 con el copo (120 → 150 mallas).",
    },
    "overrides": _merge(
        _rtex_overrides(_P31, _P31_INH),
        {"U1": {"mesh_mm": ("transcribed", "mallero rotulado una vez para el ala y el cielo")}},
    ),
    "hanging": {
        "upper": _u1("upper", 2.00, (420, 38), (133, 38)),
        "lower": _u1("lower", 1.20, (380, 38), (143, 38)),
    },
    "headrope": _rope(
        21.00,
        9.50,
        2.00,
        22,
        "PE Ø22 mm",
        "rope_pe_22mm",
        {
            "wing_m": (
                "derived",
                "(21,00 − 2,00) / 2: el rótulo del ala dice 10,00 m, que con la bocana de 2,00 m "
                "daría 22,00 m y no los 21,00 m del total",
            ),
            "bosom_m": ("transcribed", None),
        },
    ),
    "footrope": _rope(
        22.40,
        10.60,
        1.20,
        24,
        "PE Ø24 mm",
        "rope_pe_24mm",
        {
            "wing_m": (
                "derived",
                "(22,40 − 1,20) / 2: el rótulo del ala dice 11,20 m, que con la bocana de 1,20 m "
                "daría 23,60 m y no los 22,40 m del total",
            ),
            "bosom_m": ("transcribed", None),
        },
    ),
    "design": {"vessel_length_m": (14.0, "transcribed", "Loa 14,00 m")},
    "notes": [
        "Los rótulos de las alas (10,00 m de lima y 11,20 m de burlón, sin «2 ×») más los de la "
        "bocana (2,00 y 1,20 m) no suman los totales del plano (21,00 y 22,40 m): se toman los "
        "totales y la bocana, y el ala se deriva.",
        "Uniones del cuerpo con su razón en el plano: 8/9 (320 × 38 mm con 360 × 32 mm, 5 %), "
        "8/9 (240 × 32 mm con 270 × 25 mm, 12 %) y 4/5 (120 × 25 mm con 150 × 20 mm).",
        _RIG_NOTE,
    ],
}

# --- Plano 33: «Otter boom», 20 m, 90 hp (Khanohm, Nakhon Si Thammarat, 1986) -------------------
_P33_U = [
    ("UW", "upper", "wing", 2, 45, R250_9, 90, 156, 200, "1N4B / AB"),
    ("U1", "upper", "square", 1, 45, R250_9, 446, 380, 50, "1N4B"),
    ("U2", "upper", "body", 1, 40, R250_9, 428, 300, 192, "2N2B"),
    ("U3", "upper", "body", 1, 30, R250_9, 350, 200, 150, "1N2B"),
    ("U4", "upper", "body", 1, 25, R250_6, 250, 150, 100, "1N2B"),
    ("UC", "upper", "codend", 1, 20, R250_6, 180, 180, 150, None),
]
_P33_L = [("LW", "lower", "wing", 2, 45, R250_9, 90, 173, 250, "1N4B / AB"), *_lower(_P33_U, 2)]
_P33 = _P33_U + _P33_L
_P33_INH = (
    {
        p: "el cuerpo de 30 mm no lleva rótulo: se toma el «PE 250d/9» de arriba"
        for p in ("U3", "L3")
    }
    | {
        p: "el copo no lleva rótulo: se toma el «PE 250d/6» del cuerpo de 25 mm"
        for p in ("UC", "LC")
    }
    | {"LW": "el ala del vientre no lleva rótulo: se toma el «PE 250d/9» del ala del dorso"}
)

SEAFDEC_33: dict[str, Any] = {
    "id": "seafdec_33_outrigger_shrimp",
    "name": "Arrastre camaronero con tangón, 20 m y 90 hp (SEAFDEC 2016, n.º 33)",
    "description": (
        "Red camaronera de dos caras para tangones («otter boom») de un buque de 20 m y 90 hp "
        "(Khanohm, Nakhon Si Thammarat, Tailandia, 1986): alas y cielo de 45 mm, cuerpo de 40, "
        "30 y 25 mm y copo de 20 mm, PE; lima de 20,00 m y burlón de 23,00 m."
    ),
    "family": "bottom",
    "rig": "outrigger",
    "vessel_hp": (90, 90),
    "target_species": _SHRIMP,
    "source": _source("33", "Bottom, Otter boom; Shrimp", 46),
    "material": "PE",
    "panels": _P33,
    "panel_notes": {
        **_shared_notes(_P33_U, 2),
        "U1": "El cielo de 380 mallas de 45 mm se une 8/9 al cuerpo de 428 mallas de 40 mm.",
        "U2": f"{_SHARED_NOTE} Unión 6/7 con el paño de 30 mm (300 → 350 mallas).",
        "U3": f"{_SHARED_NOTE} Unión 4/5 con el paño de 25 mm (200 → 250 mallas).",
        "U4": f"{_SHARED_NOTE} Unión 5/6 con el copo (150 → 180 mallas).",
    },
    "overrides": _merge(
        _rtex_overrides(_P33, _P33_INH),
        {"U1": {"mesh_mm": ("transcribed", "mallero rotulado una vez para el ala y el cielo")}},
    ),
    "hanging": {
        "upper": _u1("upper", 2.00, (446, 45), (156, 45)),
        "lower": _u1("lower", 0.50, (428, 40), (173, 45)),
    },
    "headrope": _rope(20.00, 9.00, 2.00, 12, "2 × 9,00 PE Ø12 mm + bocana 2,00", "rope_pe_12mm"),
    "footrope": _rope(23.00, 11.25, 0.50, 14, "2 × 11,25 PE Ø14 mm + bocana 0,50", "rope_pe_14mm"),
    "design": {"vessel_length_m": (20.0, "transcribed", "Loa 20,00 m")},
    "notes": [
        "Lima = 2 × 9,00 + 2,00 = 20,00 m y burlón = 2 × 11,25 + 0,50 = 23,00 m, como el total "
        "del plano.",
        "Uniones del cuerpo con su razón en el plano: 8/9 (380 × 45 mm con 428 × 40 mm), 6/7 "
        "(300 × 40 mm con 350 × 30 mm, 12 %), 4/5 (200 × 30 mm con 250 × 25 mm) y 5/6 "
        "(150 × 25 mm con 180 × 20 mm).",
        _RIG_NOTE,
    ],
}

# --- Plano 35: «Otter with boom», 15 m, 112 hp (Kanhom, Surat Thani, 1986) ----------------------
_P35_U = [
    ("UW", "upper", "wing", 2, 51, R380_18, 70, 195, 250, "1N2B / AB"),
    ("U1", "upper", "square", 1, 51, R380_18, 475, 455, 20, None),
    ("U2", "upper", "body", 1, 51, R380_18, 455, 455, 50, None),
    ("U3", "upper", "body", 1, 51, R380_18, 455, 389, 100, "2N2B"),
    ("U4", "upper", "body", 1, 45, R380_18, 389, 295, 140, "2N2B"),
    ("U5", "upper", "body", 1, 38, R380_9, 295, 125, 170, "1N2B"),
    ("UC", "upper", "codend", 1, 25, R250_6, 125, 125, 200, None),
]
_P35_L = [("LW", "lower", "wing", 2, 51, R380_18, 70, 205, 270, "1N2B / AB"), *_lower(_P35_U, 2)]
_P35 = _P35_U + _P35_L
_P35_INH = {
    p: "sin rótulo en esa fila: se toma el «PE 380d/18» de arriba"
    for p in ("U1", "U3", "U4", "L3", "L4", "LW")
}

SEAFDEC_35: dict[str, Any] = {
    "id": "seafdec_35_outrigger_shrimp",
    "name": "Arrastre camaronero con tangón, 15 m y 112 hp (SEAFDEC 2016, n.º 35)",
    "description": (
        "Red camaronera de dos caras para tangones («otter with boom») de un buque de 15 m y "
        "112 hp (Kanhom, Surat Thani, Tailandia, 1986): alas, cielo y primer cuerpo de 51 mm, "
        "cuerpo de 45 y 38 mm y copo de 25 mm, PE; lima de 26,90 m y burlón de 28,20 m. El "
        "plano 36 (11 m, 150 hp) es el mismo."
    ),
    "family": "bottom",
    "rig": "outrigger",
    "vessel_hp": (112, 112),
    "target_species": _SHRIMP,
    "source": _source("35", "Bottom, Otter with boom; Shrimp", 48),
    "material": "PE",
    "panels": _P35,
    "panel_notes": {
        **_shared_notes(_P35_U, 2),
        "U1": "El plano no rotula el corte del cielo (475 → 455 mallas en 20 filas).",
        "U4": f"{_SHARED_NOTE} Unión 1/1 con el paño de 51 mm (389 mallas): frunce un 12 %.",
        "U5": f"{_SHARED_NOTE} Unión 1/1 con el paño de 45 mm (295 mallas): frunce un 16 %.",
        "UC": "El copo de 125 mallas de 25 mm se une 1/1 al cuerpo de 125 mallas de 38 mm.",
    },
    "overrides": _merge(
        _rtex_overrides(_P35, _P35_INH),
        {
            p: {"mesh_mm": ("transcribed", "mallero rotulado una vez para los paños de 51 mm")}
            for p in ("U1", "U3", "L3")
        },
    ),
    "hanging": {
        "upper": _u1("upper", 1.40, (475, 51), (195, 51)),
        "lower": _u1("lower", 0.70, (455, 51), (205, 51)),
    },
    "headrope": _rope(26.90, 12.75, 1.40, 8, "2 × 12,75 PE Ø8 mm + bocana 1,40", "rope_pe_8mm"),
    "footrope": _rope(28.20, 13.75, 0.70, 8, "2 × 13,75 PE Ø8 mm + bocana 0,70", "rope_pe_8mm"),
    "design": {"vessel_length_m": (15.0, "transcribed", "Loa 15,00 m")},
    "notes": [
        "BORRADOR: el plano une 1/1 el cuerpo de 125 mallas de 38 mm al copo de 125 mallas de "
        "25 mm (34 % de diferencia de largo estirado) y los paños de 51, 45 y 38 mm también 1/1 "
        "(12 y 16 %).",
        "Lima = 2 × 12,75 + 1,40 = 26,90 m y burlón = 2 × 13,75 + 0,70 = 28,20 m, como el total "
        "del plano.",
        _RIG_NOTE,
    ],
    "status": "draft",
}

# --- Plano 38: «Otter boom», 13,5 m, 100 hp (Klong Yai, Trat, 1986) -----------------------------
_P38_U = [
    ("UW", "upper", "wing", 2, 38, R380_6, 75, 175, 250, "1N2B / AB"),
    ("U1", "upper", "square", 1, 38, R380_6, 490, 430, 50, "1N3B"),
    ("U2", "upper", "body", 1, 40, R250_9, 430, 360, 70, "1N2B"),
    ("U3", "upper", "body", 1, 30, R250_9, 480, 330, 150, "1N2B"),
    ("U4", "upper", "body", 1, 25, R250_6, 330, 270, 180, "5N2B"),
    ("UC", "upper", "codend", 1, 25, R250_6, 270, 270, 240, None),
]
_P38_L = [("LW", "lower", "wing", 2, 38, R380_6, 75, 195, 300, "1N2B / AB"), *_lower(_P38_U, 2)]
_P38 = _P38_U + _P38_L
_P38_INH = (
    {"U1": "sin rótulo en esa fila: se toma el «PE 380d/6» del ala"}
    | {
        p: "el cuerpo de 30 mm no lleva rótulo: se toma el «PE 250d/9» de arriba"
        for p in ("U3", "L3")
    }
    | {
        p: "el copo no lleva rótulo: se toma el «PE 250d/6» del cuerpo de 25 mm"
        for p in ("UC", "LC")
    }
)

SEAFDEC_38: dict[str, Any] = {
    "id": "seafdec_38_outrigger_shrimp",
    "name": "Arrastre camaronero con tangón, 13,5 m y 100 hp (SEAFDEC 2016, n.º 38)",
    "description": (
        "Red camaronera de dos caras para tangones («otter boom») de un buque de 13,5 m y 100 hp "
        "(Klong Yai, Trat, Tailandia, 1986): alas y cielo de 38 mm, cuerpo de 40, 30 y 25 mm y "
        "copo de 25 mm, PE; lima de 21,00 m y burlón de 23,30 m."
    ),
    "family": "bottom",
    "rig": "outrigger",
    "vessel_hp": (100, 100),
    "target_species": _SHRIMP,
    "source": _source("38", "Bottom, Otter boom; Shrimp", 51),
    "material": "PE",
    "panels": _P38,
    "panel_notes": {
        **_shared_notes(_P38_U, 2),
        "UW": "El corte del costado exterior se lee 1N2B (ampliado 5 veces), pero el ensanche "
        "75 → 175 en 250 filas con el costado AB pide 1N3B; se conserva lo leído y el validador "
        "lo avisa. Lo mismo en el ala del vientre (75 → 195 en 300 filas).",
        "U2": f"{_SHARED_NOTE} El cielo de 430 mallas de 38 mm se une 1/1 a este paño de 40 mm; "
        "unión 3/4 con el paño de 30 mm (360 → 480 mallas).",
        "U3": f"{_SHARED_NOTE} Unión 1/1 con el paño de 25 mm (330 mallas): frunce un 17 %.",
    },
    "overrides": _merge(
        _rtex_overrides(_P38, _P38_INH),
        {"U1": {"mesh_mm": ("transcribed", "mallero rotulado una vez para el ala y el cielo")}},
    ),
    "hanging": {
        "upper": _u1("upper", 2.00, (490, 38), (175, 38)),
        "lower": _u1("lower", 0.50, (430, 40), (195, 38)),
    },
    "headrope": _rope(21.00, 9.50, 2.00, 10, "2 × 9,50 PE Ø10 mm + bocana 2,00", "rope_pe_10mm"),
    "footrope": _rope(23.30, 11.40, 0.50, 10, "2 × 11,40 PE Ø10 mm + bocana 0,50", "rope_pe_10mm"),
    "design": {"vessel_length_m": (13.5, "transcribed", "Loa 13,50 m")},
    "notes": [
        "Lima = 2 × 9,50 + 2,00 = 21,00 m y burlón = 2 × 11,40 + 0,50 = 23,30 m, como el total "
        "del plano.",
        "Uniones con su razón en el plano: 1/1 (430 × 38 mm con 430 × 40 mm, 5 %), 3/4 "
        "(360 × 40 mm con 480 × 30 mm) y 1/1 (330 × 30 mm con 330 × 25 mm, 17 %).",
        _RIG_NOTE,
    ],
}

# --- Plano 39: «Otter with boom», 16 m, 150 hp (Surat Thani, 1986) ------------------------------
_P39_U = [
    ("UW", "upper", "wing", 2, 51, R380_18, 70, 205, 270, "1N2B / AB"),
    ("U1", "upper", "square", 1, 51, R380_18, 488, 468, 20, None),
    ("U2", "upper", "body", 1, 51, R380_18, 468, 468, 50, None),
    ("U3", "upper", "body", 1, 51, R380_18, 468, 402, 100, "2N2B"),
    ("U4", "upper", "body", 1, 45, R380_18, 402, 302, 150, "2N2B"),
    ("U5", "upper", "body", 1, 38, R380_9, 302, 125, 175, "2N2B"),
    ("UC", "upper", "codend", 1, 32, R380_9, 150, 150, 200, None),
]
_P39_L = [("LW", "lower", "wing", 2, 51, R380_18, 70, 215, 290, "1N2B / AB"), *_lower(_P39_U, 2)]
_P39 = _P39_U + _P39_L
_P39_INH = {
    p: "sin rótulo en esa fila: se toma el «PE 380d/18» de arriba"
    for p in ("U1", "U3", "U4", "L3", "L4", "LW")
} | {p: "el copo no lleva rótulo: se toma el «PE 380d/9» del cuerpo de 38 mm" for p in ("UC", "LC")}

SEAFDEC_39: dict[str, Any] = {
    "id": "seafdec_39_outrigger_shrimp",
    "name": "Arrastre camaronero con tangón, 16 m y 150 hp (SEAFDEC 2016, n.º 39)",
    "description": (
        "Red camaronera de dos caras para tangones («otter with boom») de un buque de 16 m y "
        "150 hp (Surat Thani, Tailandia, 1986): alas, cielo y primer cuerpo de 51 mm, cuerpo de "
        "45 y 38 mm y copo de 32 mm, PE; lima de 28,70 m y burlón de 29,70 m."
    ),
    "family": "bottom",
    "rig": "outrigger",
    "vessel_hp": (150, 150),
    "target_species": _SHRIMP,
    "source": _source("39", "Bottom, Otter with boom; Shrimp", 52),
    "material": "PE",
    "panels": _P39,
    "panel_notes": {
        **_shared_notes(_P39_U, 2),
        "U1": "El plano no rotula el corte del cielo (488 → 468 mallas en 20 filas).",
        "U4": f"{_SHARED_NOTE} Unión 1/1 con el paño de 51 mm (402 mallas): frunce un 12 %.",
        "U5": f"{_SHARED_NOTE} Unión 1/1 con el paño de 45 mm (302 mallas): frunce un 16 %. El "
        "corte se lee 2N2B (ampliado 5 veces), pero 302 → 125 en 175 filas pide 1N2B; se "
        "conserva lo leído y el validador lo avisa. Unión 5/6 con el copo (125 → 150 mallas).",
    },
    "overrides": _merge(
        _rtex_overrides(_P39, _P39_INH),
        {
            p: {"mesh_mm": ("transcribed", "mallero rotulado una vez para los paños de 51 mm")}
            for p in ("U1", "U3", "L3")
        },
    ),
    "hanging": {
        "upper": _u1("upper", 1.30, (488, 51), (205, 51)),
        "lower": _u1("lower", 0.30, (468, 51), (215, 51)),
    },
    "headrope": _rope(28.70, 13.70, 1.30, 10, "2 × 13,70 PE Ø10 mm + bocana 1,30", "rope_pe_10mm"),
    "footrope": _rope(
        29.70,
        14.70,
        0.30,
        10,
        "2 × 14,70 PE Ø10 mm + bocana",
        "rope_pe_10mm",
        {
            "wing_m": ("transcribed", None),
            "bosom_m": (
                "derived",
                "29,70 − 2 × 14,70: el rótulo de la bocana está tapado por la línea del ala "
                "(se adivina «0,30»)",
            ),
        },
    ),
    "design": {"vessel_length_m": (16.0, "transcribed", "Loa 16,00 m")},
    "notes": [
        "Lima = 2 × 13,70 + 1,30 = 28,70 m, como el total del plano; la bocana del burlón "
        "(0,30 m) sale del total.",
        "Uniones con su razón en el plano: 1/1 (402 × 51 mm con 402 × 45 mm, 12 %), 1/1 "
        "(302 × 45 mm con 302 × 38 mm, 16 %) y 5/6 (125 × 38 mm con 150 × 32 mm).",
        _RIG_NOTE,
    ],
}

# --- Plano 30: arrastre de vara para camarón, 11 m, 165 hp (Khao Sammuk, Chon Buri, 1986) -------
_P30_U = [
    ("UW", "upper", "wing", 2, 40, R250_9, 60, 109, 220, "1N7B / AB"),
    ("U1", "upper", "square", 1, 40, R250_9, 358, 280, 50, "1N7B"),
    ("U2", "upper", "body", 1, 30, R250_9, 350, 250, 150, "2N2B"),
    ("U3", "upper", "body", 1, 25, R250_9, 300, 200, 150, "2N2B"),
    ("UC", "upper", "codend", 1, 20, R250_6, 200, 200, 200, None),
]
_P30_L = [("LW", "lower", "wing", 2, 40, R250_9, 60, 120, 270, "1N7B / AB"), *_lower(_P30_U, 2)]
_P30 = _P30_U + _P30_L
_P30_INH = {
    p: "sin rótulo en esa fila: se toma el «PE 250d/9» de las alas"
    for p in ("U1", "U2", "U3", "L2", "L3")
}

SEAFDEC_30: dict[str, Any] = {
    "id": "seafdec_30_beam_shrimp",
    "name": "Arrastre de vara para camarón, 11 m y 165 hp (SEAFDEC 2016, n.º 30)",
    "description": (
        "Red de vara de dos caras para camarón de un buque de 11 m y 165 hp (Khao Sammuk, Chon "
        "Buri, Tailandia, 1986): alas y cielo de 40 mm, cuerpo de 30 y 25 mm y copo de 20 mm, "
        "PE; lima de 19,60 m y burlón de 22,10 m."
    ),
    "family": "bottom",
    "rig": "beam",
    "vessel_hp": (165, 165),
    "target_species": _SHRIMP,
    "source": _source("30", "Bottom, Beam trawl; Shrimp", 43),
    "material": "PE",
    "panels": _P30,
    "panel_notes": {
        **_shared_notes(_P30_U, 2),
        "U1": "El cielo de 280 mallas de 40 mm se une 4/5 al cuerpo de 350 mallas de 30 mm.",
        "U2": f"{_SHARED_NOTE} Unión 5/6 con el paño de 25 mm (250 → 300 mallas).",
        "UC": "El copo de 200 mallas de 20 mm se une 1/1 al cuerpo de 200 mallas de 25 mm "
        "(frunce un 20 %).",
    },
    "overrides": _merge(
        _rtex_overrides(_P30, _P30_INH),
        {"U1": {"mesh_mm": ("transcribed", "mallero rotulado una vez para el ala y el cielo")}},
    ),
    "hanging": {
        "upper": _u1("upper", 2.00, (358, 40), (109, 40)),
        "lower": _u1("lower", 0.50, (350, 30), (120, 40)),
    },
    "headrope": _rope(19.60, 8.80, 2.00, 10, "2 × 8,80 PE Ø10 mm + bocana 2,00", "rope_pe_10mm"),
    "footrope": _rope(22.10, 10.80, 0.50, 10, "2 × 10,80 PE Ø10 mm + bocana 0,50", "rope_pe_10mm"),
    "design": {
        "vessel_length_m": (11.0, "transcribed", "Loa 11,00 m"),
        "beam_count": (
            2,
            "assumed",
            "el plano no da el aparejo; dos varas por buque (Eigaard et al. 2016)",
        ),
    },
    "notes": [
        "Lima = 2 × 8,80 + 2,00 = 19,60 m y burlón = 2 × 10,80 + 0,50 = 22,10 m, como el total "
        "del plano.",
        "Uniones con su razón en el plano: 4/5 (280 × 40 mm con 350 × 30 mm, 6 %), 5/6 "
        "(250 × 30 mm con 300 × 25 mm) y 1/1 (200 × 25 mm con 200 × 20 mm, 20 %).",
        "El plano no da la vara, los patines, las cadenas ni el lastre: el caso usa los valores "
        "por defecto del motor para la vara (Eigaard et al. 2016 y C056/20).",
    ],
}

# --- Plano 21: arrastre de fondo para peces, 24 m, 250 hp (Paknam Chumphon, 1986) ---------------
_P21_U = [
    ("UT", "upper", "wing_tip", 2, 160, R700_15, 1, 60, 30, "AB / AB"),
    ("UW", "upper", "wing", 2, 160, R700_15, 60, 88, 55, "1N2B / AB"),
    ("U1", "upper", "square", 1, 160, R700_15, 200, 180, 20, None),
    ("U2", "upper", "body", 1, 120, R700_15, 240, 200, 40, "1N2B"),
    ("U3", "upper", "body", 1, 80, R700_12, 250, 200, 50, "1N2B"),
    ("U4", "upper", "body", 1, 60, R700_12, 250, 200, 50, "1N2B"),
    ("U5", "upper", "body", 1, 38, R700_12, 300, 200, 150, "2N2B"),
    ("UC", "upper", "codend", 1, 19, R380_12, 250, 250, 250, None),
]
_P21_L = [
    ("LT", "lower", "wing_tip", 2, 160, R700_15, 1, 60, 30, "AB / AB"),
    ("LW", "lower", "wing", 2, 160, R700_15, 60, 81, 75, "1N5B / AB"),
    *_lower(_P21_U, 3),
]
_P21 = _P21_U + _P21_L
_P21_INH = {
    p: "sin rótulo en esa fila: se toma el «PE 700d/15» de las alas"
    for p in ("UT", "U1", "U2", "LT", "L2")
} | {
    p: "el cuerpo de 60 y 38 mm no lleva rótulo: se toma el «PE 700d/12» de arriba"
    for p in (
        "U4",
        "U5",
        "L4",
        "L5",
    )
}
_TIP_MESH = (
    "assumed",
    "el plano no rotula el mallero de la punta de ala (sólo sus filas): se toma el del ala",
)
_TIP_TOP = (
    "assumed",
    "el plano dibuja la punta de ala como un vértice (0 mallas); el simulador necesita un borde "
    "de boca, así que se toma 1 malla",
)
_TIPS = {
    "UT": {"mesh_mm": _TIP_MESH, "meshes_top": _TIP_TOP},
    "LT": {"mesh_mm": _TIP_MESH, "meshes_top": _TIP_TOP},
}

SEAFDEC_21: dict[str, Any] = {
    "id": "seafdec_21_otter_fish",
    "name": "Arrastre de fondo para peces, 24 m y 250 hp (SEAFDEC 2016, n.º 21)",
    "description": (
        "Red de arrastre de fondo de dos caras con portones para peces de un buque de 24 m y "
        "250 hp (Paknam Chumphon, Tailandia, 1986): puntas de ala, alas y cielo de 160 mm, "
        "cuerpo de 120, 80, 60 y 38 mm y copo de 19 mm, PE; lima de 29,20 m y burlón de "
        "33,60 m."
    ),
    "family": "bottom",
    "rig": "otter",
    "vessel_hp": (250, 250),
    "target_species": "peces demersales (fishes)",
    "source": _source("21", "Bottom, Otter; Fishes", 34),
    "material": "PE",
    "panels": _P21,
    "panel_notes": {
        **_shared_notes(_P21_U, 3),
        "UT": "Punta de ala triangular: el plano la dibuja desde un vértice (0 mallas; se toma 1) "
        "hasta 60 mallas en 30 filas, con los dos costados en malletas (AB).",
        "U1": "El plano no rotula el corte del cielo (200 → 180 mallas en 20 filas). El cielo y "
        "las alas del vientre se unen 3/4 al cuerpo de 240 mallas de 120 mm.",
        "U2": f"{_SHARED_NOTE} Unión 4/5 con el paño de 80 mm (200 → 250 mallas).",
        "U3": f"{_SHARED_NOTE} Unión 4/5 con el paño de 60 mm (200 → 250 mallas).",
        "U4": f"{_SHARED_NOTE} Unión 2/3 con el paño de 38 mm (200 → 300 mallas).",
        "U5": f"{_SHARED_NOTE} Unión 4/5 con el copo de 19 mm (200 → 250 mallas).",
    },
    "overrides": _merge(
        _rtex_overrides(_P21, _P21_INH),
        _TIPS,
        {"U1": {"mesh_mm": ("transcribed", "mallero rotulado una vez para el ala y el cielo")}},
    ),
    "hanging": {
        "upper": _u1("upper", 2.00, (200, 160), (88, 160)),
        "lower": _u1("lower", 1.00, (240, 120), (81, 160)),
    },
    "headrope": _rope(
        29.20, 13.60, 2.00, 17, "13,60 PE Ø17 mm en cada ala + bocana 2,00", "rope_pe_18mm"
    ),
    "footrope": _rope(
        33.60, 16.30, 1.00, 25, "16,30 PE Ø25 mm en cada ala + bocana 1,00", "rope_pe_24mm"
    ),
    "design": {"vessel_length_m": (24.0, "transcribed", "Loa 24,00 m")},
    "notes": [
        "BORRADOR: el plano une 4/5 el cuerpo de 200 mallas de 38 mm al copo de 250 mallas de "
        "19 mm (7,60 m contra 4,75 m de largo estirado, 38 %); el resto de las uniones da su "
        "razón y cierra (3/4, 4/5, 4/5 y 2/3, hasta 17 %).",
        "Lima = 2 × 13,60 + 2,00 = 29,20 m y burlón = 2 × 16,30 + 1,00 = 33,60 m, como el total "
        "del plano.",
        "Los cabos del plano son PE de Ø17 y Ø25 mm; el motor toma del catálogo de componentes "
        "los PE de 18 y 24 mm (los más cercanos) para el peso y la resistencia.",
        "El plano no da boyas, lastre ni portones: el caso usa el portón de la A-3 escalado por "
        "potencia.",
    ],
    "status": "draft",
}

# --- Plano 22: arrastre de fondo para peces, 20 m, 365 hp (Klong, Samut Songkhram, 1986) --------
_P22_U = [
    ("UT", "upper", "wing_tip", 2, 180, R700_21, 1, 70, 35, "AB / AB"),
    ("UW", "upper", "wing", 2, 180, R700_21, 70, 85, 75, "1N8B / AB"),
    ("U1", "upper", "square", 1, 180, R700_21, 243, 211, 20, "1N8B"),
    ("U2", "upper", "body", 1, 160, R700_21, 241, 220, 21, "1N2B"),
    ("U3", "upper", "body", 1, 120, R700_21, 275, 240, 35, "1N2B"),
    ("U4", "upper", "body", 1, 80, R700_12, 300, 250, 50, "1N2B"),
    ("U5", "upper", "body", 1, 60, R700_12, 250, 200, 50, "1N2B"),
    ("U6", "upper", "body", 1, 38, R700_12, 300, 200, 150, "2N2B"),
    ("UC", "upper", "codend", 1, 19, R380_15, 300, 300, 250, None),
]
_P22_L = [
    ("LT", "lower", "wing_tip", 2, 180, R700_21, 1, 70, 30, "AB / AB"),
    ("LW", "lower", "wing", 2, 180, R700_21, 70, 89, 95, "1N8B / AB"),
    *_lower(_P22_U, 3),
]
_P22 = _P22_U + _P22_L
_P22_INH = {
    p: "sin rótulo en esa fila: se toma el «PE 700d/21» de las alas"
    for p in ("UT", "U1", "U2", "U3", "LT", "L2", "L3")
} | {
    p: "sin rótulo en esa fila: se toma el «PE 700d/12» de arriba" for p in ("U5", "U6", "L5", "L6")
}

SEAFDEC_22: dict[str, Any] = {
    "id": "seafdec_22_otter_fish",
    "name": "Arrastre de fondo para peces, 20 m y 365 hp (SEAFDEC 2016, n.º 22)",
    "description": (
        "Red de arrastre de fondo de dos caras con portones para peces de un buque de 20 m y "
        "365 hp (Klong, Samut Songkhram, Tailandia, 1986): puntas de ala, alas y cielo de "
        "180 mm, cuerpo de 160, 120, 80, 60 y 38 mm y copo de 19 mm, PE; lima de 46,10 m y "
        "burlón de 49,80 m."
    ),
    "family": "bottom",
    "rig": "otter",
    "vessel_hp": (365, 365),
    "target_species": "peces demersales (fishes)",
    "source": _source("22", "Bottom, Otter; Fishes", 35),
    "material": "PE",
    "panels": _P22,
    "panel_notes": {
        **_shared_notes(_P22_U, 3),
        "UT": "Punta de ala triangular desde un vértice (0 mallas; se toma 1) hasta 70 mallas en "
        "35 filas, con los dos costados en malletas (AB).",
        "LT": "Punta de ala del vientre: 0 (se toma 1) → 70 mallas en 30 filas con los dos "
        "costados AB (darían 60 mallas); se conserva lo leído y el validador lo avisa.",
        "U1": "El cielo de 211 mallas de 180 mm se une 7/8 al cuerpo de 241 mallas de 160 mm.",
        "U2": f"{_SHARED_NOTE} Unión 4/5 con el paño de 120 mm (220 → 275 mallas).",
        "U3": f"{_SHARED_NOTE} Unión 4/5 con el paño de 80 mm (240 → 300 mallas).",
        "U4": f"{_SHARED_NOTE} Unión 1/1 con el paño de 60 mm (250 mallas): frunce un 25 %.",
        "U5": f"{_SHARED_NOTE} Unión 2/3 con el paño de 38 mm (200 → 300 mallas).",
        "U6": f"{_SHARED_NOTE} Unión 2/3 con el copo de 19 mm (200 → 300 mallas).",
    },
    "overrides": _merge(
        _rtex_overrides(_P22, _P22_INH),
        _TIPS,
        {"U1": {"mesh_mm": ("transcribed", "mallero rotulado una vez para el ala y el cielo")}},
    ),
    "hanging": {
        "upper": _u1("upper", 6.50, (243, 180), (85, 180)),
        "lower": _u1("lower", 3.00, (241, 160), (89, 180)),
    },
    "headrope": _rope(
        46.10,
        19.80,
        6.50,
        20,
        "19,80 combinado Ø20 mm en cada ala + bocana 6,50",
        "rope_combinado_6_20mm",
    ),
    "footrope": _rope(
        49.80,
        23.40,
        3.00,
        32,
        "23,40 combinado Ø32 mm en cada ala + bocana 3,00",
        "rope_combinado_6_24mm",
    ),
    "design": {"vessel_length_m": (20.0, "transcribed", "Loa 20,00 m")},
    "notes": [
        "BORRADOR: dos uniones no cierran en largo estirado: 1/1 entre el paño de 80 mm y el de "
        "60 mm (250 mallas, 25 %) y 2/3 entre el cuerpo de 38 mm y el copo de 19 mm (7,60 m "
        "contra 5,70 m, 25 %).",
        "Lima = 2 × 19,80 + 6,50 = 46,10 m y burlón = 2 × 23,40 + 3,00 = 49,80 m, como el total "
        "del plano.",
        "El burlón es un combinado de Ø32 mm; el catálogo de componentes llega a 24 mm y el "
        "motor toma ese para el peso y la resistencia.",
        "El plano no da boyas, lastre ni portones: el caso usa el portón de la A-3 escalado por "
        "potencia.",
    ],
    "status": "draft",
}

NETS_196: list[dict[str, Any]] = [
    SEAFDEC_31,
    SEAFDEC_33,
    SEAFDEC_35,
    SEAFDEC_38,
    SEAFDEC_39,
    SEAFDEC_30,
    SEAFDEC_21,
    SEAFDEC_22,
]
