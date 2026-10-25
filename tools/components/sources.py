"""Datos de las fuentes de componentes (Fase 13), transcriptos de documentos públicos.

Dos clases de datos:

* **Tablas de referencia** (FAO *Fisherman's Workbook*, Prado y Dremière 1990): puntos por
  material y construcción. No se publican tal cual: ``build_components.py`` ajusta una ley por
  material (potencia o d²) y genera los genéricos a tamaños estándar con valores *derivados* del
  ajuste, con el error máximo del ajuste en la procedencia.
* **Fichas de fabricantes**: datos puntuales (unos pocos tamaños por línea de producto), citados.
  No se copian tablas enteras.

Cada tabla dice documento, página y unidades. Lectura del 2026-10-25.
"""

from __future__ import annotations

from typing import Any

ACCESSED = "2026-10-25"

# --- Documentos ------------------------------------------------------------------------------

DOCS: dict[str, dict[str, Any]] = {
    "prado1990": {
        "key": "prado1990",
        "title": "FAO Fisherman's Workbook (Prado y Dremière 1990)",
        "url": "https://www.fao.org/3/ah827e/ah827e.pdf",
    },
    "garware_fisheries": {
        "key": "garware_fisheries",
        "title": "Garware Technical Fibres, Fisheries brochure (redes de arrastre trenzadas y cabos)",
        "url": "https://www.garwarefibres.com/sites/default/files/brochure/solutions/"
        "Fisheries%20Brochure.pdf",
    },
    "bridon2023": {
        "key": "bridon2023",
        "title": "Bridon-Bekaert, 2023 Fishing Catalogue",
        "url": "https://www.bekaert.com/content/dam/bbrg-myrope/products/technical-sheets/"
        "2023%20Fishing%20Catalogue.pdf",
    },
    "pfeifer_6x19w": {
        "key": "pfeifer_6x19w",
        "title": "PFEIFER, ficha técnica del cable 6x19W-FC (EN 12385-4)",
        "url": "https://www.pfeifer.info/out/assets/6X19W-FC_SDB_EN_1.PDF",
    },
    "zuniga2006": {
        "key": "zuniga2006",
        "title": "Zúñiga Clavijo, Altamar y Manjarrés (FAO REBYC): Caracterización tecnológica de "
        "la flota de arrastre camaronero del mar Caribe de Colombia",
        "url": "https://www.fao.org/fileadmin/user_upload/rebyc-2015/documents/"
        "CARACTERIZACION_TECNOLOGICA_FLOTA_DE_ARRASTRE_DE_CAMARON_CARIBE_2006.pdf",
    },
    "lange1993": {
        "key": "lange1993",
        "title": "Lange, K. (1993). Design and construction of cambered V-doors. ICES C.M. "
        "1993/B:33",
        "url": "https://www.vliz.be/imisdocs/publications/ocrd/274838.pdf",
    },
    "giamportone2024": {
        "key": "giamportone2024",
        "title": "Libro Excel de cálculo de la red FAO A-3 (Giamportone)",
        "url": None,
    },
}

# --- FAO Fisherman's Workbook: hilos de red ---------------------------------------------------
# Página 18–19 del PDF («Twines»). Columnas: Rtex, diámetro [mm], A = rotura seco sin nudo
# [kgf], B = rotura mojado con nudo [kgf]. Se omiten las filas sin diámetro.

TWINE_TABLES: dict[str, dict[str, Any]] = {
    "PA_twisted": {
        "material": "PA",
        "construction": "torcido, multifilamento continuo",
        "page": "Twines: nylon (PA), multifilament twisted or braided",
        "points": [
            (100, 0.33, 6.2, 3.6),
            (230, 0.50, 14, 9),
            (390, 0.65, 22, 14),
            (540, 0.80, 30, 18),
            (700, 0.92, 39, 22),
            (950, 1.16, 51, 28),
            (1200, 1.33, 64, 34),
            (1280, 1.37, 67, 35),
            (1690, 1.50, 91, 47),
            (2000, 1.60, 110, 56),
            (2600, 1.90, 138, 73),
            (3400, 2.20, 178, 90),
            (5000, 2.75, 260, 125),
            (8000, 3.35, 420, 190),
            (11000, 3.80, 560, 250),
        ],
    },
    "PA_braided": {
        "material": "PA",
        "construction": "trenzado, multifilamento continuo",
        "page": "Twines: nylon (PA), multifilament twisted or braided",
        "points": [
            (1350, 1.50, 82, 44),
            (1950, 1.95, 110, 60),
            (2800, 2.47, 154, 81),
            (4000, 3.10, 220, 112),
            (5000, 3.60, 270, 135),
            (7200, 4.50, 360, 178),
            (10500, 5.40, 520, 245),
            (14000, 5.93, 680, 315),
        ],
    },
    "PES_twisted": {
        "material": "PES",
        "construction": "torcido, multifilamento continuo",
        "page": "Twine: polyester (PES), polyethylene (PE), polypropylene (PP)",
        "points": [
            (370, 0.60, 21, 9.3),
            (555, 0.75, 32, 14),
            (750, 0.85, 42, 18),
            (980, 1.00, 54, 24),
            (1200, 1.10, 63, 28),
            (1500, 1.25, 78, 32),
            (1850, 1.35, 96, 40),
            (3700, 1.95, 180, 78),
        ],
    },
    "PP_twisted": {
        "material": "PP",
        "construction": "torcido, multifilamento continuo",
        "page": "Twine: polyester (PES), polyethylene (PE), polypropylene (PP)",
        "points": [
            (210, 0.60, 13, 8),
            (430, 0.90, 25, 14),
            (920, 1.34, 44, 23),
            (1920, 1.95, 92, 47),
            (2820, 2.32, 132, 70),
            (3300, 2.52, 152, 80),
            (4700, 2.94, 190, 100),
            (5640, 3.18, 254, 130),
        ],
    },
    "PE_twisted": {
        "material": "PE",
        "construction": "torcido o trenzado, filamentos gruesos",
        "page": "Twine: polyester (PES), polyethylene (PE), polypropylene (PP)",
        "points": [
            (370, 0.78, 10, 7),
            (700, 1.12, 27, 19),
            (1050, 1.42, 36, 24),
            (1410, 1.64, 49, 35),
            (2170, 2.04, 75, 54),
            (2800, 2.33, 93, 67),
            (3400, 2.56, 116, 83),
            (4440, 2.92, 135, 97),
            (5300, 3.19, 170, 125),
            (7680, 3.68, 218, 160),
            (10100, 3.96, 290, 210),
        ],
    },
}

# --- FAO Fisherman's Workbook: cabos sintéticos -----------------------------------------------
# Página «Synthetic fibre rope»: diámetro [mm], kg/100 m, R = rotura seco [kgf].

ROPE_TABLES: dict[str, dict[str, Any]] = {
    "PA": {
        "construction": "3 cordones",
        "points": [
            (6, 2.4, 750),
            (8, 4.2, 1350),
            (10, 6.5, 2080),
            (12, 9.4, 3000),
            (14, 12.8, 4100),
            (16, 16.6, 5300),
            (20, 26, 8300),
            (24, 37.5, 12000),
            (30, 58.5, 17800),
            (40, 104, 30000),
        ],
    },
    "PE": {
        "construction": "3 cordones",
        "points": [
            (6, 1.7, 400),
            (8, 3, 685),
            (10, 4.7, 1010),
            (12, 6.7, 1450),
            (14, 9.1, 1950),
            (16, 12, 2520),
            (20, 18.6, 3720),
            (24, 27, 5250),
            (30, 42, 8050),
            (40, 74.5, 14000),
        ],
    },
    "PES": {
        "construction": "3 cordones",
        "points": [
            (6, 3, 565),
            (8, 5.1, 1020),
            (10, 8.1, 1590),
            (12, 11.6, 2270),
            (14, 15.7, 3180),
            (16, 20.5, 4060),
            (20, 32, 6350),
            (24, 46, 9140),
            (30, 71.9, 13700),
            (40, 128, 23900),
        ],
    },
    "PP": {
        "construction": "3 cordones",
        "points": [
            (6, 1.7, 550),
            (8, 3, 960),
            (10, 4.5, 1425),
            (12, 6.5, 2030),
            (14, 9, 2790),
            (16, 11.5, 3500),
            (20, 18, 5370),
            (24, 26, 7600),
            (30, 40.5, 11500),
            (40, 72, 19400),
        ],
    },
    # Cabo combinado acero–polipropileno (página «Combination wire (2)»): diámetro, kg/m, R kgf.
    "combinado_3": {
        "construction": "acero + PP, 3 cordones",
        "material": "combinado",
        "kg_per_m": True,
        "points": [
            (10, 0.105, 1230),
            (12, 0.120, 1345),
            (14, 0.140, 1540),
            (16, 0.165, 2070),
            (18, 0.240, 3000),
        ],
    },
    "combinado_6": {
        "construction": "acero + PP, 6 cordones",
        "material": "combinado",
        "kg_per_m": True,
        "points": [
            (14, 0.250, 4000),
            (16, 0.275, 4400),
            (18, 0.350, 5300),
            (20, 0.430, 6400),
            (22, 0.480, 7200),
            (24, 0.520, 7800),
            (26, 0.640, 9700),
        ],
    },
}

# --- FAO Fisherman's Workbook: cables de acero galvanizado ------------------------------------
# Página 25 «Galvanised steel wire rope: runnage, breaking strength». Diámetro [mm], kg/100 m,
# R [kgf] (acero de 145 kgf/mm²).

WIRE_TABLES: dict[str, dict[str, Any]] = {
    "6x7_fc": {
        "construction": "6x7 (6/1)",
        "core": "FC",
        "use": "cables de remolque de arrastreros chicos, buques costeros",
        "points": [
            (8, 22.2, 3080),
            (10, 34.7, 4820),
            (12, 50.0, 6940),
            (14, 68.0, 9440),
            (16, 88.8, 12300),
        ],
    },
    "6x12_fc": {
        "construction": "6x12 (12/fibra)",
        "core": "FC",
        "use": "malletas y cables de arrastreros chicos",
        "points": [
            (6, 9.9, 1100),
            (8, 15.6, 1940),
            (10, 24.3, 3020),
            (12, 35.0, 4350),
            (14, 47.7, 5930),
            (16, 62.3, 7740),
        ],
    },
    "6x19_1261_fc": {
        "construction": "6x19 (12/6/1)",
        "core": "FC",
        "use": "patentes y cables de arrastreros",
        "points": [
            (8, 21.5, 2850),
            (10, 33.6, 4460),
            (12, 48.4, 6420),
            (14, 65.8, 8730),
            (16, 86.0, 11400),
            (18, 109, 14400),
            (20, 134, 17800),
            (22, 163, 21600),
            (24, 193, 25700),
        ],
    },
    "6x19_991": {
        "construction": "6x19 (9/9/1)",
        "core": "FC o IWRC",
        "use": "cables de remolque de arrastreros",
        "points": [
            (16, 92.6, 12300),
            (18, 117, 15500),
            (20, 145, 19200),
            (22, 175, 23200),
            (24, 208, 27600),
            (26, 245, 32400),
        ],
    },
    "6x24_fc": {
        "construction": "6x24 (15/9/fibra)",
        "core": "FC",
        "use": "malletas, estrobos de portón, maniobra",
        "points": [
            (8, 19.8, 2600),
            (10, 30.9, 4060),
            (12, 44.5, 5850),
            (14, 60.6, 7960),
            (16, 79.1, 10400),
            (18, 100, 13200),
            (20, 124, 16200),
            (22, 150, 19700),
            (24, 178, 23400),
            (26, 209, 27500),
        ],
    },
}

# --- FAO Fisherman's Workbook: boyas («Spherical floats and trawl floats», ejemplos) ----------
# Material y montaje, diámetro [mm], volumen [l], flotación [kgf], profundidad máxima [m].

FLOAT_TABLE: list[tuple[str, str, float, float, float, float]] = [
    ("plástico", "agujero central", 200, 4, 2.9, 1500),
    ("plástico", "agujero central", 280, 11, 8.5, 600),
    ("plástico", "agujero lateral", 75, 0.2, 0.1, 400),
    ("plástico", "agujero lateral", 100, 0.5, 0.3, 500),
    ("plástico", "agujero lateral", 125, 1, 0.8, 400),
    ("plástico", "agujero lateral", 160, 2, 1.4, 400),
    ("plástico", "agujero lateral", 200, 4, 3.6, 400),
    ("plástico", "con orejas", 203, 4.4, 2.8, 1800),
    ("plástico", "con oreja roscada", 280, 11.25, 9, 500),
    ("aluminio", "con orejas", 152, 1.8, 1.3, 1190),
    ("aluminio", "con orejas", 191, 3.6, 2.7, 820),
    ("aluminio", "con orejas", 254, 8.6, 6.4, 1000),
]

# --- FAO Fisherman's Workbook: cadenas («Chains and thimbles») -------------------------------
# Cadena común: diámetro [mm], peso aproximado [kg/m].
CHAIN_COMMON: list[tuple[float, float]] = [
    (5, 0.5),
    (6, 0.75),
    (7, 1.0),
    (8, 1.35),
    (9, 1.9),
    (10, 2.25),
    (11, 2.7),
    (13, 3.8),
    (14, 4.4),
    (16, 5.8),
    (18, 7.3),
    (20, 9.0),
]
# Acero de alta resistencia: diámetro [mm], rotura [t], peso [kg/m].
CHAIN_HIGH_TENSILE: list[tuple[float, float, float]] = [
    (7, 6.158, 1.090),
    (10, 12.570, 2.207),
    (13, 21.240, 3.720),
    (16, 32.175, 5.640),
    (19, 45.370, 7.140),
]

# --- FAO Fisherman's Workbook: portones por potencia («Otter boards: properties of the principal
# types, choice depending on the trawler's power»). Potencia [hp], L [m], h [m], superficie [m²],
# peso [kg] (máximo usado; el texto aclara que un material liviano lo baja hasta 50 %).

DOOR_FLAT: list[tuple[tuple[float, float], float, float, float, tuple[float, float]]] = [
    ((50, 75), 1.30, 0.65, 0.85, (45, 45)),
    ((100, 100), 1.50, 0.75, 1.12, (100, 120)),
    ((200, 200), 2.00, 1.00, 2.00, (190, 220)),
    ((300, 300), 2.20, 1.10, 2.42, (300, 320)),
    ((400, 400), 2.40, 1.20, 2.88, (400, 420)),
    ((500, 500), 2.50, 1.25, 3.12, (500, 520)),
    ((600, 600), 2.60, 1.30, 3.38, (600, 620)),
    ((700, 800), 2.80, 1.40, 3.92, (800, 900)),
]
DOOR_OVAL: list[tuple[tuple[float, float], float, float, float, tuple[float, float]]] = [
    ((100, 100), 1.40, 0.85, 0.93, (100, 120)),
    ((200, 200), 1.75, 1.05, 1.45, (190, 220)),
    ((300, 300), 1.90, 1.10, 1.65, (300, 320)),
    ((400, 400), 2.20, 1.25, 2.15, (400, 420)),
    ((500, 500), 2.40, 1.40, 2.65, (500, 520)),
    ((600, 600), 2.60, 1.50, 3.05, (600, 620)),
    ((700, 800), 2.90, 1.60, 3.65, (800, 900)),
]
# V: potencia, superficie, peso (el Workbook no da medidas).
DOOR_V: list[tuple[float, float, float]] = [
    (100, 1.40, 240),
    (200, 2.10, 400),
    (300, 2.50, 580),
    (400, 2.90, 720),
    (500, 3.30, 890),
    (600, 3.60, 1000),
    (700, 3.90, 1100),
    (800, 4.20, 1200),
]
# Süberkrüb (pelágico): potencia, alto H [m], largo L [m], superficie [m²], peso [kg].
DOOR_SUBERKRUB: list[tuple[tuple[float, float], float, float, float, tuple[float, float]]] = [
    ((150, 200), 1.88, 0.80, 1.50, (90, 100)),
    ((150, 200), 2.05, 0.87, 1.80, (110, 120)),
    ((250, 250), 2.12, 0.94, 2.00, (150, 160)),
    ((300, 350), 2.28, 0.97, 2.20, (170, 180)),
    ((300, 350), 2.32, 1.03, 2.40, (220, 240)),
    ((400, 400), 2.42, 1.07, 2.60, (240, 260)),
    ((450, 450), 2.51, 1.12, 2.80, (260, 280)),
    ((500, 500), 2.68, 1.14, 3.00, (280, 300)),
    ((600, 600), 2.86, 1.22, 3.50, (320, 350)),
    ((700, 800), 3.00, 1.33, 4.00, (400, 430)),
]

# Coeficiente de sustentación máximo por tipo (Lange 1993, que cita a Lange 1976, Ward y
# Strickland/Seafish y SFIA-IFREMER-DIFTA): plano rectangular 0,95; V plano 0,70–0,85.
CL_MAX = {"flat": 0.95, "v": 0.775}

# --- Portones de la flota camaronera del Caribe colombiano (Zúñiga et al., FAO REBYC) -------
# Planos rectangulares de madera, medidos en pies × pulgadas; uso y potencia de la flota.
DOOR_REBYC: list[tuple[str, float, float, str]] = [
    ("6'x28\"", 6 * 0.3048, 28 * 0.0254, "barcos del golfo de Morrosquillo (una red por banda)"),
    ("8'x36\"", 8 * 0.3048, 36 * 0.0254, "el más usado (43 %) con redes de 37' de relinga"),
    ("9'x36\"", 9 * 0.3048, 36 * 0.0254, "37,7 % de la flota; redes japonesas de 42'"),
    ("10'x40\"", 10 * 0.3048, 40 * 0.0254, "buque de 520 hp con red de 52'"),
]

# --- Fabricantes: datos puntuales ------------------------------------------------------------

#: Garware: paño trenzado de PE para redes de arrastre (diámetro real [mm], rendimiento [m/kg],
#: rotura [kgf], rotura con nudo [kgf]). Se toman 6 tamaños por línea.
GARWARE_TWINE: dict[str, dict[str, Any]] = {
    "Sapphire": {
        "note": "red compacta: 25–30 % menos diámetro que el PE estándar",
        "page": "Fisheries: Braided Trawl Nets (Sapphire)",
        "points": [
            (1.2, 775, 59, 80),
            (2.1, 340, 115, 150),
            (3.1, 190, 220, 299),
            (4.2, 101, 355, 520),
            (5.0, 75, 544, 732),
            (6.0, 59, 700, 975),
        ],
    },
    "SNG": {
        "note": "hasta 20 % menos diámetro que Sapphire",
        "page": "Fisheries: Braided Trawl Nets (SNG)",
        "points": [
            (1.2, 840, 62, 75),
            (2.1, 350, 140, 185),
            (3.1, 190, 260, 315),
            (4.2, 110, 420, 515),
            (5.0, 80, 590, 745),
            (6.0, 61, 730, 940),
        ],
    },
}
#: Garware X2: cabo de PP/PE (equivalente a Danline/Polysteel), diámetro [mm], g/m, rotura [kgf].
GARWARE_X2: list[tuple[float, float, float]] = [
    (6, 16.8, 863),
    (8, 30.0, 1553),
    (10, 45.5, 2358),
    (12, 65.9, 3450),
    (14, 90.9, 4800),
    (16, 115.9, 5516),
    (20, 181.8, 8740),
    (24, 259.1, 12200),
]

#: Bridon-Bekaert: cables de arrastre (diámetro [mm], kg/100 m, MBL [t]).
BRIDON_WIRE: dict[str, dict[str, Any]] = {
    "Marblue 6x19 (9/9/1) Poly Core": {
        "construction": "6x19 (9/9/1)",
        "core": "fibra sintética",
        "generic": "6x19_991",
        "points": [
            (14, 70.3, 10.4),
            (16, 90.9, 14.9),
            (18, 116.8, 18.8),
            (20, 144.2, 23.2),
            (24, 205.4, 33.5),
        ],
    },
    "Marblue 6x19 (9/9/1) IWRC": {
        "construction": "6x19 (9/9/1)",
        "core": "IWRC",
        "generic": "6x19_991",
        "points": [
            (14, 82.7, 12.6),
            (16, 102, 16.1),
            (18, 128.9, 20.3),
            (20, 164.6, 25.1),
            (24, 235.4, 36.1),
        ],
    },
    "Dyform Starfish 6x26 IWRC": {
        "construction": "6x26 (10/5&5/5/1) compactado",
        "core": "IWRC",
        "generic": "6x19_991",
        "points": [(20, 183, 29.8), (22, 216.6, 36.0), (24, 254.7, 42.9), (26, 307.2, 50.3)],
    },
}

#: PFEIFER 6x19W-FC (EN 12385-4): cable de tamaño chico (diámetro [mm], kg/100 m, MBL [kN]).
PFEIFER_6X19W: list[tuple[float, float, float]] = [
    (6, 12.9, 21),
    (8, 23, 37.4),
    (10, 35.9, 58.4),
    (12, 51.7, 84.1),
    (14, 70.4, 114),
    (16, 91.9, 150),
]
