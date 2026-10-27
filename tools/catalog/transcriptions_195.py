"""Transcripciones de la Fase 19.5: redes tangoneras del INIDEP y una red de vara de la SEAFDEC.

Mismas convenciones que ``tools/catalog/transcriptions.py`` (filas ``(id, plane, section, count,
mesh_mm, rtex, top, bottom, depth, cut[, material])``).

* **INIDEP ITO 043/2022** (Roth y Rubio 2022), figs. 4 y 5: planos exportados de DynamiT de la red
  tangonera de la empresa Pesquera Deseado con hilos más gruesos (simulación 2) y de la red
  propuesta por el INIDEP (simulación 3). Cada plano trae tres paños (#1 dorso, LOW vientre, SIDE
  costado) con filas, mallas, cortes, lado de malla, Ø del hilo y rendimiento (m/kg), y la tabla
  de cabos. Los planos de DynamiT dan el lado de malla (``Mesh side``): el mallero es el doble.
  El Rtex se deriva del rendimiento (Rtex = 10⁶ / rendimiento en m/kg). Las filas con media malla
  (69,5; 63,5; 150,857; 100,5) se redondean a la malla entera. El tramo delantero del costado
  (malla de 160 mm, junto a las alas) no se modela: el motor lleva las relingas por las alas del
  dorso y del vientre (como en las redes de 4 paneles de Schärfe). Los rótulos de corte se
  transcriben como se leen en la imagen (1613 px); el validador avisa cuando no dan el cambio de
  ancho del paño.
* **SEAFDEC (2016) TD/RES/141**, plano n.º 03 (p. 16): arrastre de vara para camarón de un buque
  de 17 m y 235 hp (Chumphon, 1986). Plano vectorial: medio dorso a la izquierda y medio vientre a
  la derecha, cuerpo y copo comunes a las dos caras. El hilo va en denier (380d/15 = 15 cabos de
  380 denier); el Rtex se deriva como n·den/9 (sin el aumento por torsión).
"""

from __future__ import annotations

from typing import Any

ACCESSED_195 = "2026-10-27"


def rows(n: float) -> int:
    """Filas enteras de un alto con fracción de malla (69,5 → 70)."""
    import math

    return int(math.floor(n + 0.5))


def rtex_from_runnage(runnage_m_kg: float) -> float:
    """Rtex [g/km] de un hilo de rendimiento ``runnage_m_kg`` [m/kg]."""
    return round(1.0e6 / runnage_m_kg)


def rtex_from_denier(denier: float, plies: int) -> float:
    """Rtex aproximado de ``plies`` cabos de ``denier`` (n·den/9, sin el aumento por torsión)."""
    return round(denier * plies / 9.0, 1)


# --- Materiales de los planos DynamiT (tabla «Description», figs. 4 y 5) ---------------------
#: (rendimiento m/kg, Ø mm) de cada hilo del plano.
INIDEP_TWINES: dict[str, tuple[float, float]] = {
    "Santy-160 mm": (500.0, 1.8),
    "NY": (280.0, 3.0),
    "140 PEPE": (500.0, 1.8),
    "140 3 mm PCU": (235.0, 3.0),
    "160 3 mm PCU": (235.0, 3.0),
    "DY 3 120 mm": (150.0, 3.0),
}
R_SANTY = rtex_from_runnage(500.0)  # 2000
R_PCU = rtex_from_runnage(235.0)  # 4255
R_DY = rtex_from_runnage(150.0)  # 6667
R_NY = rtex_from_runnage(280.0)  # 3571

_INIDEP_SOURCE_5 = {
    "key": "roth2022ito043",
    "title": "INIDEP ITO 043/22 (Roth y Rubio 2022), fig. 5: red tangonera propuesta por el "
    "INIDEP (simulación DynamiT 3)",
    "url": "https://fisheryprogress.org/sites/default/files/documents_actions/"
    "ITO_043_2022_LIB_Roth_Pesquera_Deseado.pdf",
    "figure": "Figura 5",
    "page": "9",
    "accessed": ACCESSED_195,
}
_INIDEP_SOURCE_4 = {
    **_INIDEP_SOURCE_5,
    "title": "INIDEP ITO 043/22 (Roth y Rubio 2022), fig. 4: red tangonera de Pesquera Deseado "
    "con hilos de 3 mm (simulación DynamiT 2)",
    "figure": "Figura 4",
    "page": "8",
}


def _twine_overrides(panels: list[tuple[Any, ...]], names: dict[str, str]) -> dict[str, Any]:
    """Procedencia derivada del Rtex (del rendimiento) y del Ø del hilo (de la tabla)."""
    out: dict[str, Any] = {}
    for row in panels:
        pid = row[0]
        twine = names[pid]
        runnage, diameter = INIDEP_TWINES[twine]
        out[pid] = {
            "rtex": (
                "derived",
                f"Rtex = 10⁶ / {runnage:g} m/kg (rendimiento del hilo «{twine}» en la tabla de "
                "materiales del plano)",
            ),
            "twine_diameter_mm": (
                "transcribed",
                f"Ø {diameter:g} mm del hilo «{twine}» en la tabla de materiales del plano",
            ),
            "mesh_mm": (
                "derived",
                "mallero = 2 × lado de malla («Mesh side») del plano de DynamiT",
            ),
        }
    return out


def _merge(*dicts: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for d in dicts:
        for k, v in d.items():
            out.setdefault(k, {}).update(v)
    return out


_ROPES_5 = (
    "Cabos del plano: A combinado 22 mm 11,00 m; B combinado 22 mm 3,75 m; E combinado 22 mm "
    "6,00 m (lima: 2 × (11,00 + 3,75) + 6,00 = 35,5 m); O cable mixto 24 mm 10,00 m; P 3,75 m; "
    "S 5,00 m (burlón: 2 × (10,00 + 3,75) + 5,00 = 32,5 m); J cable mixto 24 mm 3,15 m (borde "
    "delantero del costado); costuras de 2 y 3 mm."
)
_RIG_NOTE = (
    "Aparejo de las tres simulaciones (pp. 1 y 5): tijera de 70 m de cable de acero de 22 mm, "
    "cable de arrastre de acero de 24 mm con alma de acero, portones rectangulares planos de madera "
    "con refuerzos de acero de 540 kg cada uno, 3,5 nudos; tangones del B/P «Atlántico 1»."
)

_DESIGN_INIDEP: dict[str, tuple[Any, str, str | None]] = {
    "vessel_id": (
        "ar_tangonero_1998",
        "assumed",
        "B/P «Atlántico 1» (tangonero): el informe no da eslora ni potencia; se usa el "
        "tangonero típico de la flota argentina (media de 1998)",
    ),
    "door_id": (
        "door_flat_500hp",
        "assumed",
        "portones rectangulares planos de madera de 540 kg (pp. 1 y 5) sin medidas publicadas: "
        "se toma el portón plano genérico del catálogo de peso más cercano (510 kg, 2,5 × 1,25 m; "
        "alto ≤ 1,5 m de la Res. CFP 7/2018). A VERIFICAR",
    ),
    "door_weight_air_kg": (540.0, "transcribed", "portones de madera de 540 kg cada uno"),
    "outrigger_bridle_m": (70.0, "transcribed", "tijera de 70 m (pp. 1 y 5)"),
    "outrigger_bridle_diameter_mm": (22.0, "transcribed", "cable de acero de 22 mm"),
    "speed_kn": (3.5, "transcribed", "velocidad de las simulaciones (p. 5)"),
}

# --- Fig. 5: red propuesta por el INIDEP (simulación 3) ---------------------------------------
INIDEP_5_PANELS = [
    # id, plane, section, count, mesh, rtex, top, bottom, depth, cut, material
    ("UW1", "upper", "wing", 2, 160, R_SANTY, 4, 52, rows(69.5), "10N9B / AB", "PE"),
    ("UW2", "upper", "wing", 2, 160, R_SANTY, 52, 76, 14, "5N4B / 1T2B", "PE"),
    ("U1", "upper", "square", 1, 140, R_PCU, 235, 214, 15, "3N4B", "PE"),
    ("U2", "upper", "body", 1, 140, R_PCU, 214, 135, 59, "19N7B", "PE"),
    ("U3", "upper", "body", 1, 120, R_DY, 157, 40, 88, "1N4B", "HMPE"),
    ("UC", "upper", "codend", 1, 60, R_NY, 100, 100, 217, "AN", "PA"),
    ("LW1", "lower", "wing", 2, 140, R_SANTY, 1, 50, 73, "1N1B / AB", "PE"),
    ("LW2", "lower", "wing", 2, 140, R_SANTY, 50, 77, 16, "1N1B / 1T2B", "PE"),
    ("L2", "lower", "body", 1, 140, R_PCU, 210, 131, 59, "1N4B", "PE"),
    ("L3", "lower", "body", 1, 120, R_DY, 153, 61, 88, "5N1B", "HMPE"),
    ("LC", "lower", "codend", 1, 60, R_NY, 100, 100, 217, "AN", "PA"),
    ("S1", "side", "body", 2, 140, R_PCU, 39, 17, rows(150.857), "3N1B / AN", "PE"),
]
_TWINE_5 = {
    "UW1": "Santy-160 mm",
    "UW2": "Santy-160 mm",
    "U1": "140 3 mm PCU",
    "U2": "140 3 mm PCU",
    "U3": "DY 3 120 mm",
    "UC": "NY",
    "LW1": "140 PEPE",
    "LW2": "140 PEPE",
    "L2": "140 3 mm PCU",
    "L3": "DY 3 120 mm",
    "LC": "NY",
    "S1": "140 3 mm PCU",
}

INIDEP_5: dict[str, Any] = {
    "id": "inidep_ito043_tangonera_inidep",
    "name": "Red tangonera de langostino propuesta por el INIDEP (ITO 043/2022, fig. 5)",
    "description": (
        "Red de arrastre de fondo de baja abertura para tangones (langostino patagónico), de "
        "tres paños (dorso, vientre y costados): alas de 160 mm en el dorso y 140 mm en el "
        "vientre, cielo y cuerpo de 140 mm, cuerpo trasero de 120 mm de Dyneema y copo de 60 mm "
        "de nylon; lima de 35,5 m y burlón de 32,5 m. Plano de DynamiT del INIDEP (Roth y Rubio "
        "2022)."
    ),
    "family": "bottom",
    "rig": "outrigger",
    "vessel_hp": (948.7, 948.7),
    "target_species": "langostino patagónico (Pleoticus muelleri)",
    "species": {"name": "Langostino", "scientific_name": "Pleoticus muelleri"},
    "source": _INIDEP_SOURCE_5,
    "material": "PE",
    "twine_diameter": {R_SANTY: 1.8, R_PCU: 3.0, R_DY: 3.0, R_NY: 3.0},
    "panels": INIDEP_5_PANELS,
    "panel_notes": {
        "UW1": "Rótulo de corte «10N9B-:AB» (el guion final no se interpreta).",
        "U2": "El rótulo se lee «19N7B», pero el paño pasa de 214 a 135 mallas en 59 filas, "
        "como el vientre con 1N4B (el validador lo avisa).",
        "U3": "Rótulo «1N4B-» (el guion final no se interpreta).",
        "L3": "Rótulo «5N1B-»; el paño pasa de 153 a 61 mallas en 88 filas (el validador lo "
        "avisa).",
        "S1": "Tramo trasero del costado (140 mm, 150,857 filas); el tramo delantero de 160 mm "
        "(20 filas AN:1T6B de 2 a 29 mallas y 63,5 filas AN de 34 mallas, junto a las alas) no "
        "se modela.",
    },
    "overrides": _merge(
        _twine_overrides(INIDEP_5_PANELS, _TWINE_5),
        {
            "UW1": {"meshes_depth": ("derived", "69,5 filas redondeadas a 70")},
            "S1": {"meshes_depth": ("derived", "150,857 filas redondeadas a 151")},
        },
    ),
    "hanging": {
        "upper": (
            0.70,
            "derived",
            "U1 de la bocana del dorso: lima E de 6,00 m sobre 235 × 140 − 2 × 76 × 160 = 8,58 m "
            "de paño estirado (6,00 / 8,58 = 0,70); se usa en todo el dorso",
        ),
        "lower": (
            0.64,
            "derived",
            "U1 de la bocana del vientre: burlón S de 5,00 m sobre 210 × 140 − 2 × 77 × 140 = "
            "7,84 m (5,00 / 7,84 = 0,64); se usa en todo el vientre",
        ),
        "side": (
            0.67,
            "assumed",
            "el plano no da U1 del costado: promedio del dorso (0,70) y del vientre (0,64)",
        ),
    },
    "headrope": {
        "length_m": 35.5,
        "wing_m": 14.75,
        "bosom_m": 6.00,
        "diameter_mm": 22,
        "material": "combinado Ø22 mm (A + B en cada ala, E en la bocana)",
        "rope": "rope_combinado_6_22mm",
        "pieces_note": "alas = A + B = 11,00 + 3,75 m; bocana = E = 6,00 m",
    },
    "footrope": {
        "length_m": 32.5,
        "wing_m": 13.75,
        "bosom_m": 5.00,
        "diameter_mm": 24,
        "material": "cable mixto Ø24 mm (O + P en cada ala, S en la bocana)",
        "rope": "rope_combinado_6_24mm",
        "pieces_note": "alas = O + P = 10,00 + 3,75 m; bocana = S = 5,00 m",
    },
    "design": _DESIGN_INIDEP,
    "measured": [
        {
            "speed_kn": 3.5,
            "vertical_opening_m": 1.3,
            "horizontal_opening_m": 14.0,
            "door_spread_m": 16.2,
            "warp_tension_kgf": 3777.2,
            "note": "resultados de la simulación DynamiT 3 del INIDEP (p. 6): modelo, no "
            "mediciones",
        }
    ],
    "rigging": {
        "doors": "rectangulares planos de madera con refuerzos de acero, 540 kg cada uno",
        "bridle": "tijera de 70 m de cable de acero de 22 mm",
        "warp": "acero de 24 mm con alma de acero",
    },
    "notes": [
        _ROPES_5,
        _RIG_NOTE,
        "Paños del plano: #1 28,80 m² y 62,26 kg; LOW 25,95 m² y 57,76 kg; SIDE 9,92 m² y "
        "17,18 kg; total 64,68 m² y 137,21 kg.",
        "La boca del cuerpo trasero de Dyneema (40 mallas de 120 mm en el dorso, 61 en el "
        "vientre) se une a un copo de 100 mallas de 60 mm en cada cara, como dibuja el plano.",
        "El cabo del burlón es un cable mixto de 24 mm; el motor toma el combinado de 24 mm del "
        "catálogo de componentes para el peso y la resistencia.",
    ],
    "status": "draft",
}

# --- Fig. 4: red de la empresa con hilos de 3 mm (simulación 2) -------------------------------
INIDEP_4_PANELS = [
    ("UW1", "upper", "wing", 2, 160, R_SANTY, 4, 52, rows(69.5), "10N9B / AB", "PE"),
    ("UW2", "upper", "wing", 2, 160, R_SANTY, 52, 76, 14, "5N4B / 1T2B", "PE"),
    ("U1", "upper", "body", 1, 160, R_PCU, 236, 30, 132, "1N4B", "PE"),
    ("UC", "upper", "codend", 1, 60, R_NY, 100, 100, 217, "AN", "PA"),
    ("LW1", "lower", "wing", 2, 140, R_SANTY, 1, 50, 73, "1N1B / AB", "PE"),
    ("LW2", "lower", "wing", 2, 140, R_SANTY, 50, 77, 16, "1N1B / 1T2B", "PE"),
    ("L1", "lower", "body", 1, 140, R_PCU, 210, 76, rows(100.5), "1N4B", "PE"),
    ("L2", "lower", "body", 1, 140, R_PCU, 76, 53, 34, "1N1B", "PE"),
    ("LC", "lower", "codend", 1, 60, R_NY, 100, 100, 217, "AN", "PA"),
    ("S1", "side", "body", 2, 160, R_PCU, 34, 15, 132, "3N1B / AN", "PE"),
]
_TWINE_4 = {
    "UW1": "Santy-160 mm",
    "UW2": "Santy-160 mm",
    "U1": "160 3 mm PCU",
    "UC": "NY",
    "LW1": "140 PEPE",
    "LW2": "140 PEPE",
    "L1": "140 3 mm PCU",
    "L2": "140 3 mm PCU",
    "LC": "NY",
    "S1": "160 3 mm PCU",
}

INIDEP_4: dict[str, Any] = {
    "id": "inidep_ito043_tangonera_empresa",
    "name": "Red tangonera de Pesquera Deseado con hilo de 3 mm (ITO 043/2022, fig. 4)",
    "description": (
        "Red tangonera de langostino propuesta por la empresa Pesquera Deseado SAU con el cuerpo "
        "en hilo de 3 mm (simulación DynamiT 2 del INIDEP): dorso de 160 mm, vientre de 140 mm, "
        "copo de 60 mm de nylon; lima de 35,5 m y burlón de 32,5 m."
    ),
    "family": "bottom",
    "rig": "outrigger",
    "vessel_hp": (948.7, 948.7),
    "target_species": "langostino patagónico (Pleoticus muelleri)",
    "species": {"name": "Langostino", "scientific_name": "Pleoticus muelleri"},
    "source": _INIDEP_SOURCE_4,
    "material": "PE",
    "twine_diameter": {R_SANTY: 1.8, R_PCU: 3.0, R_NY: 3.0},
    "panels": INIDEP_4_PANELS,
    "panel_notes": {
        "UW1": "El rótulo de corte está sobreimpreso; se toma el de la fig. 5 («10N9B / AB»).",
        "U1": "236 mallas de boca (el rótulo se superpone a la letra G de la bocana).",
        "S1": "Tramo trasero del costado (160 mm, 132 filas); el tramo delantero junto a las "
        "alas (20 filas AN:1T6B y 63,5 filas AN, 160 mm) no se modela.",
    },
    "overrides": _merge(
        _twine_overrides(INIDEP_4_PANELS, _TWINE_4),
        {
            "UW1": {
                "meshes_depth": ("derived", "69,5 filas redondeadas a 70"),
                "cut_code": ("assumed", "rótulo sobreimpreso; se toma el de la fig. 5"),
            },
            "L1": {"meshes_depth": ("derived", "100,5 filas redondeadas a 101")},
        },
    ),
    "hanging": {
        "upper": (
            0.45,
            "derived",
            "U1 de la bocana del dorso: lima G de 6,00 m sobre 236 × 160 − 2 × 76 × 160 = 13,44 m "
            "de paño estirado (6,00 / 13,44 = 0,45); se usa en todo el dorso",
        ),
        "lower": (
            0.64,
            "derived",
            "U1 de la bocana del vientre: burlón R de 5,00 m sobre 210 × 140 − 2 × 77 × 140 = "
            "7,84 m (5,00 / 7,84 = 0,64); se usa en todo el vientre",
        ),
        "side": (
            0.55,
            "assumed",
            "el plano no da U1 del costado: promedio del dorso (0,45) y del vientre (0,64)",
        ),
    },
    "headrope": {
        "length_m": 35.5,
        "wing_m": 14.75,
        "bosom_m": 6.00,
        "diameter_mm": 22,
        "material": "combinado Ø22 mm (A + B en cada ala, G en la bocana)",
        "rope": "rope_combinado_6_22mm",
        "pieces_note": "alas = A + B = 11,00 + 3,75 m; bocana = G = 6,00 m",
    },
    "footrope": {
        "length_m": 32.5,
        "wing_m": 13.75,
        "bosom_m": 5.00,
        "diameter_mm": 24,
        "material": "cable mixto Ø24 mm (M + N en cada ala, R en la bocana)",
        "rope": "rope_combinado_6_24mm",
        "pieces_note": "alas = M + N = 10,00 + 3,75 m; bocana = R = 5,00 m",
    },
    "design": _DESIGN_INIDEP,
    "measured": [
        {
            "speed_kn": 3.5,
            "vertical_opening_m": 1.5,
            "horizontal_opening_m": 14.0,
            "door_spread_m": 16.2,
            "warp_tension_kgf": 3559.6,
            "note": "resultados de la simulación DynamiT 2 del INIDEP (p. 6): modelo, no "
            "mediciones",
        }
    ],
    "rigging": INIDEP_5["rigging"],
    "notes": [
        "Cabos del plano: A combinado 22 mm 11,00 m; B 3,75 m; G 6,00 m (lima 35,5 m); M cable "
        "mixto 24 mm 10,00 m; N 3,75 m; R 5,00 m (burlón 32,5 m); H cable mixto 24 mm 3,15 m.",
        _RIG_NOTE,
        "Paños del plano: #1 26,04 m² y 48,61 kg; LOW 24,64 m² y 47,07 kg; SIDE 9,04 m² y "
        "15,15 kg; total 59,72 m² y 110,82 kg.",
        "El cabo del burlón es un cable mixto de 24 mm; el motor toma el combinado de 24 mm del "
        "catálogo de componentes para el peso y la resistencia.",
    ],
    "status": "draft",
}

# --- SEAFDEC (2016), plano n.º 03: arrastre de vara para camarón ----------------------------
R_380_15 = rtex_from_denier(380, 15)  # 633,3
R_380_12 = rtex_from_denier(380, 12)  # 506,7
SEAFDEC_03_PANELS = [
    ("UW", "upper", "wing", 2, 57, R_380_15, 20, 55, 52, "2N2B / AB"),
    ("U1", "upper", "square", 1, 57, R_380_15, 140, 140, 17, None),
    ("U2", "upper", "body", 1, 51, R_380_15, 140, 140, 20, None),
    ("U3", "upper", "body", 1, 51, R_380_12, 140, 50, 90, None),
    ("UC", "upper", "codend", 1, 32, R_380_12, 50, 50, 100, "AN"),
    ("LW", "lower", "wing", 2, 57, R_380_15, 10, 56, 69, "2N2B / AB"),
    ("L2", "lower", "body", 1, 51, R_380_15, 140, 140, 20, None),
    ("L3", "lower", "body", 1, 51, R_380_12, 140, 50, 90, None),
    ("LC", "lower", "codend", 1, 32, R_380_12, 50, 50, 100, "AN"),
]
_DEN = {R_380_15: "380d/15", R_380_12: "380d/12"}

SEAFDEC_03: dict[str, Any] = {
    "id": "seafdec_03_beam_shrimp",
    "name": "Arrastre de vara para camarón, 17 m y 235 hp (SEAFDEC 2016, n.º 03)",
    "description": (
        "Red de vara de dos caras para camarón de un buque de 17 m y 235 hp (Chumphon, "
        "Tailandia, 1986): alas de 57 mm, cielo de 57 mm, cuerpo de 51 mm y copo de 32 mm, PE; "
        "lima de 6,90 m y burlón de 8,70 m."
    ),
    "family": "bottom",
    "rig": "beam",
    "vessel_hp": (235, 235),
    "target_species": "camarón (shrimp)",
    "source": {
        "key": "seafdec2016thai",
        "title": "SEAFDEC (2016) The Catalogue Bottom Trawl Net Designs of Thailand, TD/RES/141, "
        "plano 03 (Bottom, beam trawl; shrimp)",
        "url": "https://repository.seafdec.or.th/handle/20.500.12067/1826",
        "figure": "Plano 03",
        "page": "16 (22 del PDF)",
        "accessed": ACCESSED_195,
    },
    "material": "PE",
    "panels": SEAFDEC_03_PANELS,
    "panel_notes": {
        "U2": "El plano dibuja el cuerpo y el copo una vez, comunes a las dos caras.",
        "U3": "El plano no da el corte del cuerpo (140 → 50 mallas en 90 filas: 1N2B).",
        "LW": "Junto a la relinga del ala del vientre el plano dibuja una tira de 120 mm (PE "
        "700d/12) de una malla de ancho, que no se modela.",
        "UC": "El copo de 50 mallas de 32 mm se une 1/1 al cuerpo de 50 mallas de 51 mm.",
    },
    "overrides": {
        row[0]: {
            "rtex": (
                "derived",
                f"Rtex ≈ n·den/9 de PE {_DEN[row[5]]} (sin el aumento por torsión; A VERIFICAR)",
            )
        }
        for row in SEAFDEC_03_PANELS
    },
    "hanging": {
        "default": (
            0.50,
            "assumed",
            "el plano no da U1 ni el largo de la relinga de la bocana; 0,5 supuesto",
        ),
    },
    "headrope": {
        "length_m": 6.90,
        "wing_m": 3.02,
        "bosom_m": 0.86,
        "diameter_mm": 6,
        "material": "2 × PP Ø6 mm S+Z",
        "rope": "rope_pp_6mm",
        "pieces_note": "bocana con U1 = 0,5: 140 − 2 × 55 = 30 mallas de 57 mm (0,86 m); alas = "
        "(6,90 − 0,86) / 2",
    },
    "footrope": {
        "length_m": 8.70,
        "wing_m": 3.95,
        "bosom_m": 0.80,
        "diameter_mm": 6,
        "material": "2 × PP Ø6 mm S+Z",
        "rope": "rope_pp_6mm",
        "pieces_note": "bocana con U1 = 0,5: 140 − 2 × 56 = 28 mallas de 57 mm (0,80 m); alas = "
        "(8,70 − 0,80) / 2",
    },
    "design": {
        "vessel_length_m": (17.0, "transcribed", "Loa 17,00 m"),
        "beam_count": (
            2,
            "assumed",
            "el plano no da el aparejo; dos varas por buque (Eigaard et al. 2016)",
        ),
    },
    "notes": [
        "El hilo va en denier: 380d/15 en alas, cielo y primer cuerpo; 380d/12 en el cuerpo "
        "trasero y el copo.",
        "El plano no da la vara, los patines, las cadenas ni el lastre: el caso usa los valores "
        "por defecto del motor para la vara (Eigaard et al. 2016 y C056/20).",
    ],
    "status": "draft",
}

NETS_195: list[dict[str, Any]] = [INIDEP_5, INIDEP_4, SEAFDEC_03]
