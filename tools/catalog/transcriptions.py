"""Transcripciones de planos de redes de documentos FAO públicos (Fase 12).

Cada red es un diccionario compacto, leído de la figura del documento. ``tools/catalog/build_nets.py``
lo convierte en ``src/trawlkit/data/nets/<id>.yaml`` con la procedencia de cada valor.

Convenciones (notación FAO de planos de red):

* ``panels``: ``(id, plane, section, count, mesh_mm, rtex, top, bottom, depth, cut)``.
  ``top``/``bottom`` = mallas del borde de boca y de bolsa; ``depth`` = alto en mallas; ``count`` =
  paños iguales en ese plano (2 para las alas); ``cut`` = corte del borde según el plano.
* ``hanging``: U1 por sección ``(valor, tipo, nota)``. Los planos FAO no dan U1: se deriva de la
  relinga y las mallas de la bocana cuando se puede, y si no se supone (tipo ``assumed``).
* Lo que el plano da como rango (boyas 9–15) se toma en el centro y se marca ``assumed``.
"""

from __future__ import annotations

from typing import Any

ACCESSED = "2026-10-25"

NETS: list[dict[str, Any]] = [
    {
        "id": "fao_wb_bt2p_60hp",
        "name": "Arrastre de fondo de 2 paneles, 50–70 hp (FAO Fisherman's Workbook)",
        "description": (
            "Red de arrastre de fondo de dos caras para buques de 50–70 hp, con alas de 120 mm, "
            "cielo en el dorso, cuerpo de 80–40 mm y copo de 40 mm. Plano de la FAO reproducido "
            "en el Fisherman's Workbook (Prado y Dremière 1990)."
        ),
        "family": "bottom",
        "rig": "otter",
        "vessel_hp": (50, 70),
        "target_species": "peces demersales y camarón (pesca costera)",
        "source": {
            "key": "prado1990",
            "title": "Fisherman's Workbook — Fishing gear and operations: 2-panel bottom trawl",
            "url": "https://www.fao.org/4/ah827e/AH827E04.htm",
            "figure": "AH827E132",
            "page": "Fishing gear and operations (cap. 4)",
        },
        "material": "PA",
        "panels": [
            # id, plane, section, count, mesh, rtex, top, bottom, depth, cut
            ("A", "upper", "wing_tip", 2, 120, 910, 3, 30, 18, "1N2B / AB"),
            ("C", "upper", "wing", 2, 120, 910, 30, 55, 50, "1N2B / AB"),
            ("E", "upper", "square", 1, 120, 910, 150, 130, 20, "1N2B"),
            ("G1", "upper", "body", 1, 120, 910, 130, 120, 10, "1N2B"),
            ("G2", "upper", "body", 1, 80, 625, 180, 130, 50, "1N2B"),
            ("G3", "upper", "body", 1, 60, 625, 174, 124, 50, "1N2B"),
            ("G4", "upper", "body", 1, 40, 625, 186, 86, 100, "1N2B"),
            ("I", "upper", "codend", 1, 40, 910, 86, 86, 150, "AN"),
            ("B", "lower", "wing_tip", 2, 120, 910, 2, 29, 18, "1N2B"),
            ("D", "lower", "wing", 2, 120, 910, 29, 53, 70, "1N4B / AB"),
            ("F", "lower", "belly", 1, 120, 910, 130, 120, 10, "1N2B"),
            ("H2", "lower", "body", 1, 80, 625, 180, 130, 50, "1N2B"),
            ("H3", "lower", "body", 1, 60, 625, 174, 124, 50, "1N2B"),
            ("H4", "lower", "body", 1, 40, 625, 186, 86, 100, "1N2B"),
            ("J", "lower", "codend", 1, 40, 910, 86, 86, 150, "AN"),
        ],
        "panel_notes": {
            "G2": "Rtex 625 escrito una vez para el grupo de 80, 60 y 40 mm.",
            "I": "El plano agrega un refuerzo/bolsa de izado de 120 mm, PA Ø3, 54 × 20 mallas.",
        },
        "hanging": {
            "default": (
                0.40,
                "derived",
                "U1 de la bocana del dorso: 1,90 m de relinga sobre 40 mallas de 120 mm "
                "(1,90 / 4,80 = 0,40); el plano no da U1 por paño, se usa en toda la red.",
            ),
        },
        "headrope": {
            "length_m": 18.90,
            "wing_m": 8.50,
            "bosom_m": 1.90,
            "diameter_mm": 12,
            "material": "PP Ø12 / combinado Ø12",
            "rope": "combinado_12_acero6x24_7",
        },
        "footrope": {
            "length_m": 23.20,
            "wing_m": 11.00,
            "bosom_m": 1.20,
            "diameter_mm": 14,
            "material": "PP Ø14 / combinado Ø12",
            "rope": "combinado_14_acero6x24_7",
        },
        "floats": {
            "count": 12,
            "diameter_mm": 130,
            "note": "el plano indica 9–15 boyas de Ø13 cm (o 3–4 de Ø20 cm); se toma 12",
        },
        "ballast_kg": {
            "value": 15.0,
            "note": "8–14 kg en el burlón más 2–3 kg en cada punta: 11 + 2 × 2 = 15 kg",
        },
        "rigging": {
            "doors": "portones de 1,30 × 0,65 m, 40–60 kg",
            "warp": "acero Ø9 mm",
            "sweeps": "20,00–30,00 m combinado Ø12–14",
            "bridles": "superior 10,00 m combinado Ø10; inferior 9,00 m combinado Ø12 + cadena de reglaje 1,00 m",
        },
        "notes": [
            "Lectura de la figura AH827E132 (450 px): números legibles; los empalmes con cambio de mallero cierran (120×120 = 180×80; 130×80 ≈ 174×60; 124×60 = 186×40).",
            "La bocana del dorso (40 mallas) y del vientre (24 mallas) cierran exactamente con las alas: 55 + 40 + 55 = 150 y 53 + 24 + 53 = 130.",
        ],
    },
    {
        "id": "bobp_wp13_pair_ho80",
        "name": "Arrastre de pareja de gran abertura, 464 mallas de 80 mm (BOBP/WP/13)",
        "description": (
            "Red de arrastre de fondo de gran abertura para dos barcos de 30–33 hp, de dos caras, "
            "con alas de 120 mm en el dorso y 80 mm en el vientre, cuerpo de 80–40 mm y copo de "
            "40 mm. Ensayada en Bangladesh (Chittagong) en 1980–81."
        ),
        "family": "bottom",
        "rig": "pair",
        "vessel_hp": (30, 33),
        "target_species": "peces demersales y semipelágicos (hasta 20 m de profundidad)",
        "source": {
            "key": "bobpwp13",
            "title": "BOBP/WP/13, apéndice 3: High opening trawl for two boats, 464 meshes of 80 mm (stretched)",
            "url": "https://www.fao.org/4/ad953e/ad953e00.pdf",
            "figure": "Apéndice 3",
            "page": "14 del PDF ([10] del documento)",
        },
        "material": "PE",
        "twine_diameter": {720: 1.25},
        "panels": [
            ("A", "upper", "wing_tip", 2, 120, 720, 4, 34, 20, "1N2B / AB"),
            ("C", "upper", "wing", 2, 120, 720, 34, 69, 60, "1N2B / AB"),
            ("E", "upper", "square", 1, 120, 720, 180, 155, 25, "1N2B"),
            ("G1", "upper", "body", 1, 120, 720, 155, 135, 20, "1N2B"),
            ("G2", "upper", "body", 1, 80, 720, 202, 152, 50, "1N2B"),
            ("G3", "upper", "body", 1, 60, 720, 203, 133, 70, "1N2B"),
            ("G4", "upper", "body", 1, 40, 720, 200, 100, 100, "1N2B"),
            ("I", "upper", "codend", 1, 40, 720, 100, 100, 200, "AN"),
            ("B", "lower", "wing_tip", 2, 80, 720, 5, 50, 30, "1N2B"),
            ("D", "lower", "wing", 2, 80, 720, 50, 93, 127, "1N2B / AB"),
            ("F", "lower", "belly", 1, 80, 720, 232, 152, 60, "1N2B"),
            ("H3", "lower", "body", 1, 60, 720, 203, 133, 70, "1N2B"),
            ("H4", "lower", "body", 1, 40, 720, 200, 100, 100, "1N2B"),
            ("J", "lower", "codend", 1, 40, 720, 100, 100, 200, "AN"),
        ],
        "overrides": {
            "B": {
                "mesh_mm": (
                    "derived",
                    "columna de mallero ilegible en las alas del vientre; 80 mm por la unión 1/1 con el cuerpo de 80 mm (93 mallas de ala sobre 232 del cuerpo)",
                )
            },
            "D": {
                "mesh_mm": (
                    "derived",
                    "columna de mallero ilegible en las alas del vientre; 80 mm por la unión 1/1 con el cuerpo de 80 mm",
                )
            },
            "G3": {
                "meshes_bottom": (
                    "transcribed",
                    "se lee 133 (no 138): 133 × 60 mm = 7,98 m empalma con 200 × 40 mm = 8,00 m",
                )
            },
        },
        "panel_notes": {
            "E": "En el plano la bocana del dorso es de 47 mallas (1,50 m de relinga) y las alas terminan en 69 mallas: 69 + 47 + 69 = 185, cinco más que las 180 del borde del cuerpo.",
            "I": "Bolsa de izado de 80 mm, PE R1760 tex (Ø2,5), 100 × 30 mallas; faldón (flapper) de 60 mm, PE R720 tex, 163/133 × 30 mallas.",
        },
        "hanging": {
            "upper": (
                0.27,
                "derived",
                "U1 de la bocana del dorso: 1,50 m de relinga sobre 47 mallas de 120 mm (0,27); el plano no da U1 por paño, se usa en todo el dorso.",
            ),
            "lower": (
                0.40,
                "derived",
                "U1 de la bocana del vientre: 1,15 m de burlón sobre 36 mallas de 80 mm (0,40); se usa en todo el vientre.",
            ),
            "default": (0.33, "assumed", "media de dorso y vientre"),
        },
        "headrope": {
            "length_m": 20.70,
            "wing_m": 9.60,
            "bosom_m": 1.50,
            "diameter_mm": 14,
            "material": "PP Ø14–16",
            "rope": "pp_14_retorcido_3_cordones",
        },
        "footrope": {
            "length_m": 26.35,
            "wing_m": 12.60,
            "bosom_m": 1.15,
            "diameter_mm": 8,
            "material": "cable de acero Ø8 forrado con PE R1760 tex",
            "rope": "combinado_12_acero6x24_7",
        },
        "floats": {
            "count": 19,
            "diameter_mm": 150,
            "note": "el plano indica 18–20 boyas plásticas de 1100 gf; se toma 19; el diámetro (150 mm) es supuesto",
        },
        "ballast_kg": {
            "value": 37.5,
            "note": "25–30 kg de plomadas en el burlón más 5 kg en cada punta: 27,5 + 2 × 5 = 37,5 kg",
        },
        "rigging": {
            "towing": "pareja de barcos de 30–33 hp; cable de remolque 100,00–150,00 m PP Ø12–14 con cadena de lastre de 40–50 kg",
            "bridles": "superior 30,00 m PP Ø14–16; inferior 29,50 m combinado Ø12 + cadena de reglaje 1,00 m (5 kg)",
        },
        "notes": [
            "Figura del apéndice 3 escaneada a 107 ppp (990 px de ancho): números legibles con ampliación.",
            "Empalmes con cambio de mallero: 135 × 120 = 202 × 80 (16,2 m); 152 × 80 ≈ 203 × 60 (12,2 m); 133 × 60 ≈ 200 × 40 (8,0 m).",
            "Las alas del dorso tienen 80 filas de 120 mm (9,6 m) y las del vientre 157 filas de 80 mm (12,6 m): el cielo de 45 filas completa el largo del dorso.",
        ],
    },
    {
        "id": "bobp_wp13_pair_ho120",
        "name": "Arrastre de pareja de gran abertura, 368 mallas de 120 mm (BOBP/WP/13)",
        "description": (
            "Red de arrastre de fondo de gran abertura para dos barcos de 30–33 hp, con alas de "
            "160 mm, cuerpo de 120–80 mm y copo de 40 mm. Ensayada en Bangladesh en 1980–81."
        ),
        "family": "bottom",
        "rig": "pair",
        "vessel_hp": (30, 33),
        "target_species": "peces demersales y semipelágicos (hasta 20 m de profundidad)",
        "source": {
            "key": "bobpwp13",
            "title": "BOBP/WP/13, apéndice 4: High opening trawl for two boats, 368 meshes of 120 mm (stretched)",
            "url": "https://www.fao.org/4/ad953e/ad953e00.pdf",
            "figure": "Apéndice 4",
            "page": "15 del PDF ([11] del documento)",
        },
        "material": "PE",
        "twine_diameter": {720: 1.25},
        "panels": [
            ("A", "upper", "wing_tip", 2, 160, 720, 8, 44, 20, "1N4B / AB"),
            ("C", "upper", "wing", 2, 160, 720, 44, 69, 50, "1N2B / AB"),
            ("E", "upper", "square", 1, 160, 720, 158, 138, 20, "1N2B"),
            ("G1", "upper", "body", 1, 120, 720, 184, 160, 24, "1N2B"),
            ("G2", "upper", "body", 1, 120, 720, 160, 60, 100, "1N2B"),
            ("G3", "upper", "body", 1, 80, 720, 90, 75, 15, "1N2B"),
            ("G4", "upper", "body", 1, 40, 720, 150, 100, 50, "1N2B"),
            ("I", "upper", "codend", 1, 40, 720, 100, 100, 250, "AN"),
            ("B", "lower", "wing_tip", 2, 160, 720, 3, 32, 20, "1N2B"),
            ("D", "lower", "wing", 2, 160, 720, 32, 67, 70, "1N2B / AB"),
            ("F", "lower", "belly", 1, 120, 720, 184, 160, 24, "1N2B"),
            ("H2", "lower", "body", 1, 120, 720, 160, 60, 100, "1N2B"),
            ("H3", "lower", "body", 1, 80, 720, 90, 75, 15, "1N2B"),
            ("H4", "lower", "body", 1, 40, 720, 150, 100, 50, "1N2B"),
            ("J", "lower", "codend", 1, 40, 720, 100, 100, 250, "AN"),
        ],
        "overrides": {
            "E": {
                "meshes_top": (
                    "derived",
                    "el plano da 138 mallas de 160 mm bajo las alas (69 + 69) y dibuja la bocana de 20 mallas como un triángulo entre las alas; para la disposición del modelo la bocana se suma al borde de boca del cielo: 138 + 20 = 158",
                )
            },
            "C": {
                "meshes_bottom": (
                    "transcribed",
                    "se lee 63 a la izquierda y 69 a la derecha; el plano es simétrico y 69 + 69 = 138 cierra con el cielo: 69",
                )
            },
            "J": {
                "meshes_depth": (
                    "assumed",
                    "el número de filas del copo del vientre está cortado en la figura; se toma el del dorso (250)",
                )
            },
        },
        "panel_notes": {
            "F": "En el plano el borde de boca del vientre se divide en 79 + 26 + 79 mallas de 120 mm bajo las alas de 67 mallas de 160 mm y la bocana.",
            "I": "Bolsa de izado de 80 mm, PE R1760 tex (Ø2,5), 100 × 30 mallas; faldón de 60 mm, PE R720 tex, 135/105 × 30 mallas.",
        },
        "hanging": {
            "default": (
                0.38,
                "derived",
                "U1 de las bocanas: 1,20 m de relinga sobre 20 mallas de 160 mm (dorso, 0,375) y 1,20 m de burlón sobre 26 mallas de 120 mm (vientre, 0,385); el plano no da U1 por paño, se usa en toda la red.",
            ),
        },
        "headrope": {
            "length_m": 23.60,
            "wing_m": 11.20,
            "bosom_m": 1.20,
            "diameter_mm": 16,
            "material": "PP Ø16",
            "rope": "pp_16_retorcido_3_cordones",
        },
        "footrope": {
            "length_m": 30.00,
            "wing_m": 14.40,
            "bosom_m": 1.20,
            "diameter_mm": 8,
            "material": "cable de acero Ø8 forrado con PE R1760 tex",
            "rope": "combinado_12_acero6x24_7",
        },
        "floats": {
            "count": 21,
            "diameter_mm": 150,
            "note": "el plano indica 20–22 boyas plásticas de 1100 gf; se toma 21; el diámetro (150 mm) es supuesto",
        },
        "ballast_kg": {
            "value": 37.5,
            "note": "25–30 kg de plomadas en el burlón más 5 kg en cada punta: 27,5 + 2 × 5 = 37,5 kg",
        },
        "rigging": {
            "towing": "pareja de barcos de 30–33 hp; cable de remolque 100,00–150,00 m PP Ø12 con cadena de lastre de 40 kg; 30,00 m PP Ø16 hasta el destorcedor",
            "bridles": "superior 30,00 m PP Ø16; inferior 29,50 m PP Ø16 + cadena de reglaje 1,00 m (5 kg)",
        },
        "notes": [
            "Figura del apéndice 4 escaneada a 107 ppp (987 px de ancho): números legibles con ampliación salvo las filas del copo del vientre.",
            "Empalmes con cambio de mallero: 138 × 160 = 184 × 120 (22,1 m); 60 × 120 = 90 × 80 (7,2 m); 75 × 80 = 150 × 40 (6,0 m).",
            "Las alas del dorso (70 filas) más el cielo (20 filas) suman lo mismo que las alas del vientre (90 filas de 160 mm).",
        ],
    },
]
