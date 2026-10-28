"""Datos de las fuentes de componentes (Fase 13), transcriptos de documentos públicos.

Dos clases de datos:

* **Tablas de referencia** (FAO *Fisherman's Workbook*, Prado y Dremière 1990): puntos por
  material y construcción. No se publican tal cual: ``build_components.py`` ajusta una ley por
  material (potencia o d²) y genera los genéricos a tamaños estándar con valores *derivados* del
  ajuste, con el error máximo del ajuste en la procedencia.
* **Fichas de fabricantes**: datos puntuales (unos pocos tamaños por línea de producto), citados.
  No se copian tablas enteras.

Cada tabla dice documento, página y unidades. Lectura del 2026-10-25; las fuentes de la Fase 19.2
(Hampidjan, Crosby, Gunnebo y las líneas nuevas de Garware y Bridon-Bekaert), del 2026-10-27.
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
        # Releído el 2026-10-27 (Fase 19.2): se cargaron más líneas y se comprobaron las de antes.
        "accessed": "2026-10-27",
        "title": "Garware Technical Fibres, Fisheries brochure (redes de arrastre trenzadas y cabos)",
        "url": "https://www.garwarefibres.com/sites/default/files/brochure/solutions/"
        "Fisheries%20Brochure.pdf",
    },
    "bridon2023": {
        "key": "bridon2023",
        "accessed": "2026-10-27",
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
    "hampidjan_catalogue": {
        "key": "hampidjan_catalogue",
        "title": "Hampiðjan hf., Hampidjan Fishing Catalogue (visor iPaper, 437 págs., versión "
        "2023-10-11)",
        "url": "https://viewer.ipaper.io/hampidjan/hampidjan-fishing-catalouge/",
        "accessed": "2026-10-27",
    },
    "crosby_g209": {
        "key": "crosby_g209",
        "title": "The Crosby Group, G-209 / S-209 Screw Pin Anchor Shackles (Crosby General "
        "Catalog, p. 24)",
        "url": "https://www.thecrosbygroup.com/wp-content/uploads/catalog/2022/en/24.pdf",
        "accessed": "2026-10-27",
    },
    "gunnebo_llz": {
        "key": "gunnebo_llz",
        "title": "Gunnebo Industries / Kito Crosby, Long Link Chain LLZ, Grade 6, hot-dip "
        "galvanized (datos del producto)",
        "url": "https://kitocrosby.com/product/gunnebo-industries-long-link-chain-llz-grade-6/",
        "accessed": "2026-10-27",
    },
    "sfia1993": {
        "key": "sfia1993",
        "title": "Sea Fish Industry Authority, IFREMER y DIFTA (1993, rev. 1995). Otterboard "
        "Performance and Behaviour (contrato CEE FAR TE 1 214)",
        "url": "https://www.seafish.org/media/1peahnrq/otterboard_performance_and_behaviour.pdf",
        "accessed": "2026-10-27",
    },
    "mellibovsky2018": {
        "key": "mellibovsky2018",
        "title": "Mellibovsky, Prat-Farran, Notti y Sala (2018). Otterboard hydrodynamic "
        "performance testing in flume tank and wind tunnel facilities. Ocean Eng. 149:238–244",
        "url": "https://hdl.handle.net/2117/116734",
        "accessed": "2026-10-27",
    },
    "gutherz1974": {
        "key": "gutherz1974",
        "title": "Gutherz, Serra y Klima (1974). Design and Materials Used in Construction of a "
        "16-Foot Shrimp Trawl. NOAA/NMFS Fishery Facts 9",
        "url": "https://spo.nmfs.noaa.gov/sites/default/files/legacy-pdfs/fishfact09.pdf",
        "accessed": "2026-10-27",
    },
    "vonin_doors": {
        "key": "vonin_doors",
        "title": "Vónin P/F, portones Storm 2, Tornado y Twister: tamaños y pesos (páginas de "
        "producto)",
        "url": "https://www.vonin.com/fishing/trawl-doors/",
        "accessed": "2026-10-27",
    },
    "vonin_simoon": {
        "key": "vonin_simoon",
        "title": "Vónin P/F, Test of Vónin Simoon trawl doors (noticia)",
        "url": "https://www.vonin.com/test-of-vonin-simoon-trawl-doors/",
        "accessed": "2026-10-28",
    },
    "morgere2025": {
        "key": "morgere2025",
        "title": "Morgère S.A., Catalogue 2025: Imaginer la pêche de demain",
        "url": "https://www.morgere.com/wp-content/uploads/2025/06/"
        "catalogue-morgere-2025-filiere-peche-fr.pdf",
        "accessed": "2026-10-27",
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

# Polares de los genéricos (Fase 19.3): las da la biblioteca de polares medidas
# (``trawlkit/data/door_polars.yaml``, :func:`trawlkit.rigging.polars.polar_for_type`). Hasta la
# Fase 19.2 la polar en V era la del plano con CL × 0,775/0,93 (CL máximo de Lange 1993) y la del
# Süberkrüb, la del oval: ninguna de las dos era medida.

# --- Portones de la flota camaronera del Caribe colombiano (Zúñiga et al., FAO REBYC) -------
# Planos rectangulares de madera, medidos en pies × pulgadas; uso y potencia de la flota.
DOOR_REBYC: list[tuple[str, float, float, str]] = [
    ("6'x28\"", 6 * 0.3048, 28 * 0.0254, "barcos del golfo de Morrosquillo (una red por banda)"),
    ("8'x36\"", 8 * 0.3048, 36 * 0.0254, "el más usado (43 %) con redes de 37' de relinga"),
    ("9'x36\"", 9 * 0.3048, 36 * 0.0254, "37,7 % de la flota; redes japonesas de 42'"),
    ("10'x40\"", 10 * 0.3048, 40 * 0.0254, "buque de 520 hp con red de 52'"),
]

#: Portón de la red de prueba (*try-net*) de 16 pies del golfo de México (Gutherz, Serra y Klima
#: 1974, NOAA Fishery Facts 9, p. 2 y pp. 13–14, fig. 12): 30 × 15 pulgadas de terciado marino
#: de ¾ de pulgada con patín de hierro de ¼ × 2½ × 33 pulgadas; el documento no da el peso.
#: (nombre, largo [m], alto [m]) (Fase 19.6).
DOOR_NOAA_FF9: list[tuple[str, float, float]] = [
    ('30"x15"', 30 * 0.0254, 15 * 0.0254),
]

# --- Portones de fabricante (Fase 19.3) ------------------------------------------------------
# Ningún fabricante publica la polar CL/CD: los portones usan la polar de su tipo
# (``polar_for_type``) con procedencia «supuesta». Se cargan todos los tamaños que publica cada
# línea (Fase 19.8a; hasta la 19.3 se tomaban a lo sumo 10). Relectura del 2026-10-28.

#: Vónin (páginas de producto, «SIZES AND WEIGHTS»): superficie [m²] → peso [kg]. La columna dice
#: sólo «WEIGHT», sin unidad ni «por portón». Fase 19.8b: se toma por portón, *derivado* de la
#: noticia de Vónin sobre el Simoon (vonin_simoon): «these 7.5 square metre, 3000kg doors»,
#: encargados como «a pair» → ≈ 400 kg/m² por portón, coherente con los 350–500 kg/m² de la tabla
#: del Storm (por par serían 175–250 kg/m² por portón, la mitad). Vónin no lo dice en ningún texto.
#: Vónin tampoco define la superficie ni da largo o alto: superficie = largo × alto y relación de
#: aspecto = alto/largo son supuestos. Storm 2: portón de fondo de cuatro perfiles,
#: «ASPECT RATIO 1,2 (STANDARD)»; Tornado: pelágico de cinco perfiles, «ASPECT RATIO 3,0
#: (STANDARD)», ángulo de ataque de 21 a 48°; Twister: pelágico regulable (no da la relación de
#: aspecto; dice «With a CL value of 4.39» y «The CL/CD ratio varies between 3.16 and 3.60»).
VONIN_DOORS: dict[str, dict[str, Any]] = {
    "Storm 2": {
        "slug": "storm2",
        "url": "https://www.vonin.com/product/vonin-storm/",
        "type": "multifoil",
        "aspect_ratio": 1.2,
        "use": "fondo, cuatro perfiles",
        # 14 tamaños publicados (3–16 m²), todos.
        "points": [
            (3.0, 1050),
            (4.0, 1450),
            (5.0, 2100),
            (6.0, 2850),
            (7.0, 3375),
            (8.0, 3900),
            (9.0, 4400),
            (10.0, 4900),
            (11.0, 5450),
            (12.0, 5950),
            (13.0, 6450),
            (14.0, 7000),
            (15.0, 7500),
            (16.0, 7800),
        ],
    },
    "Tornado": {
        "slug": "tornado",
        "url": "https://www.vonin.com/product/vonin-tornado/",
        "type": "high_aspect",
        "aspect_ratio": 3.0,
        "use": "pelágico, cinco perfiles; ángulo de ataque de 21 a 48° según el fabricante",
        # 11 tamaños publicados (3–13 m²), todos.
        "points": [
            (3.0, 1050),
            (4.0, 1450),
            (5.0, 1850),
            (6.0, 2200),
            (7.0, 2600),
            (8.0, 3000),
            (9.0, 3400),
            (10.0, 3800),
            (11.0, 4200),
            (12.0, 4600),
            (13.0, 5000),
        ],
    },
    "Twister": {
        "slug": "twister",
        "url": "https://www.vonin.com/product/vonin-twister/",
        "type": "high_aspect",
        "aspect_ratio": None,
        "use": "pelágico regulable desde el puente (persianas)",
        "claim": "el fabricante declara «a CL value of 4.39» y CL/CD de 3,16 a 3,60 según las "
        "persianas y el ángulo de ataque; no publica la polar",
        # 8 tamaños publicados (6–13 m²), todos.
        "points": [
            (6.0, 2100),
            (7.0, 2475),
            (8.0, 2850),
            (9.0, 3250),
            (10.0, 3650),
            (11.0, 3975),
            (12.0, 4300),
            (13.0, 4700),
        ],
    },
}

#: Morgère, catálogo 2025: «Les panneaux Morgère ne sont pas standardisés : leur taille et leur
#: poids sont adaptés à chaque type de bateau» (p. 9); pesos «SUR DEMANDE / PERSONNALISABLE».
#: Se cargan los modelos con hoja de Seafish 1993 del mismo diseño (para medidas y polar); de los
#: demás (Proto NG, V Champion, Champion, Osprey, Exocet) no hay medidas ni polar publicadas.
#: ``points``: (modelo, superficie [m²]) o (modelo, largo [m], superficie [m²]) para el PFPE.
MORGERE_DOORS: dict[str, dict[str, Any]] = {
    "OvalFoil": {
        "slug": "ovalfoil",
        "page": "p. 25",
        "type": "oval",
        "polar": "sfia1993_morgere_polyvalent_ovale",
        "shape_note": "«forme emblématique du Polyvalent»: proporciones del modelo Morgère "
        "Polyvalent Ovale de Seafish 1993 (AR 0,68, relación de superficie 0,80)",
        "use": "fondo, fondos duros",
        # 21 tamaños (OF0–OF20), todos.
        "points": [
            ("OF0", 0.59),
            ("OF01", 1.06),
            ("OF02", 1.34),
            ("OF03", 1.74),
            ("OF04", 2.18),
            ("OF05", 2.59),
            ("OF06", 3.08),
            ("OF07", 3.6),
            ("OF08", 4.19),
            ("OF09", 4.79),
            ("OF10", 5.1),
            ("OF11", 5.51),
            ("OF12", 5.82),
            ("OF13", 6.62),
            ("OF14", 6.96),
            ("OF15", 7.82),
            ("OF16", 8.57),
            ("OF17", 9.64),
            ("OF18", 10.96),
            ("OF19", 11.97),
            ("OF20", 13.44),
        ],
    },
    "PolyFoil": {
        "slug": "polyfoil",
        "page": "p. 27",
        "type": "multifoil",
        "polar": "sfia1993_morgere_polyfoil",
        "shape_note": "proporciones del modelo Morgère Polyfoil de Seafish 1993 (AR 0,61, "
        "relación de superficie 0,94)",
        "use": "fondo, aguas profundas; «premier panneau multi-foils»",
        # 19 tamaños (PF0–PF18), todos.
        "points": [
            ("PF0", 0.67),
            ("PF01", 1.2),
            ("PF02", 1.52),
            ("PF03", 1.88),
            ("PF04", 2.28),
            ("PF05", 2.72),
            ("PF06", 3.19),
            ("PF07", 3.71),
            ("PF08", 4.26),
            ("PF09", 4.68),
            ("PF10", 5.13),
            ("PF11", 5.45),
            ("PF12", 5.78),
            ("PF13", 6.56),
            ("PF14", 6.98),
            ("PF15", 7.66),
            ("PF16", 8.55),
            ("PF17", 9.64),
            ("PF18", 10.96),
        ],
    },
    "PFPE": {
        "slug": "pfpe",
        "page": "p. 23",
        "type": "multifoil",
        "polar": "sfia1993_morgere_polyfoil",
        "shape_note": "«PolyFoil à crevettes» de material «longue vie» en un marco de acero: el "
        "catálogo da el largo; el alto sale de la relación de superficie del modelo Morgère Polyfoil de Seafish "
        "1993 (0,94)",
        "use": "fondo, langostino y camarón",
        # 17 tamaños (PFPE01–PFPE12) con largo, todos.
        "points": [
            ("PFPE01", 1.40, 1.20),
            ("PFPE02", 1.60, 1.52),
            ("PFPE02.5", 1.70, 1.70),
            ("PFPE03", 1.80, 1.88),
            ("PFPE03.2", 1.85, 1.98),
            ("PFPE03.5", 1.90, 2.08),
            ("PFPE05.5", 2.30, 2.95),
            ("PFPE06", 2.40, 3.19),
            ("PFPE06.2", 2.45, 3.25),
            ("PFPE06.5", 2.5, 3.44),
            ("PFPE07", 2.6, 3.71),
            ("PFPE07.5", 2.7, 3.98),
            ("PFPE08", 2.8, 4.26),
            ("PFPE09", 2.9, 4.68),
            ("PFPE10", 3.0, 5.13),
            ("PFPE11", 3.1, 5.45),
            ("PFPE12", 3.2, 5.78),
        ],
    },
}

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

# --- Fase 19.2: más fabricantes --------------------------------------------------------------
# Lectura del 2026-10-27. El catálogo de Hampidjan es un visor de páginas (iPaper) sin PDF; su
# capa de texto desordena columnas, así que cada fila de abajo se leyó en la imagen de la página
# (``Pages/<n>/Zoom.jpg`` del visor), no en el texto. «p.» es el número de página del visor; la
# sección del catálogo (p. ej. 10.1) va entre paréntesis.

#: Hampidjan, paño (sección 10): diámetro [mm], rendimiento [m/kg], peso [g/100 m], rotura con
#: nudo [kg]. La ficha no da la rotura sin nudo ni si el ensayo es en seco o mojado.
#: ``elongation``: alargamiento [%] del cuadro «Properties» (en Primanet el texto aclara «de
#: rotura»).
HAMPIDJAN_TWINE: dict[str, dict[str, Any]] = {
    "Magnet Standard": {
        "page": "p. 183 (10.1)",
        "material": "PE",
        "construction": "trenzado de 16 hilos con alma",
        "elongation": 15.0,
        "points": [
            (1.8, 675, 148, 82),
            (3.0, 281, 355, 175),
            (4.0, 200, 500, 250),
            (5.0, 128, 782, 390),
            (6.0, 96, 1040, 525),
            (8.0, 37, 2728, 1120),
        ],
    },
    "Magnet Compact Green": {
        "page": "p. 187 (10.5)",
        "material": "PE",
        "construction": "trenzado compacto de 16 hilos con alma",
        "elongation": 15.0,
        "points": [
            (1.2, 777, 129, 80),
            (2.5, 375, 267, 162),
            (3.0, 258, 387, 223),
            (4.0, 149, 669, 362),
            (5.0, 111, 898, 481),
            (6.0, 53, 1886, 1012),
        ],
    },
    "Magnet Grey": {
        "page": "p. 188 (10.6)",
        "material": "PE",
        "construction": "trenzado de 16 hilos con alma (alta rotura con nudo)",
        "elongation": 15.0,
        "points": [
            (1.0, 974, 103, 59),
            (1.8, 526, 190, 124),
            (2.4, 299, 335, 207),
            (3.1, 186, 535, 350),
            (5.0, 72, 1380, 743),
            (7.2, 33, 3030, 1551),
        ],
    },
    "Advant": {
        "page": "p. 189 (10.7)",
        "material": "HMPE",
        "construction": "trenzado de 16 hilos, Dyneema SK62 con alma de PE",
        "elongation": 9.0,
        "points": [
            (1.1, 925, 108, 116),
            (1.5, 693, 144, 131),
            (2.0, 435, 230, 209),
            (2.5, 245, 407, 370),
        ],
    },
    "Utzon": {
        "page": "p. 191 (10.9)",
        "material": "PA",
        "construction": "torcido de 3 cabos, 210 den",
        "elongation": 28.0,
        # diámetro, número de hilo (210/n), rendimiento, peso, rotura con nudo.
        "points": [
            (0.9, 210 / 18, 2150, 46, 28),
            (1.4, 210 / 36, 1054, 95, 59),
            (2.0, 210 / 72, 509, 196, 117),
            (3.0, 210 / 144, 245, 408, 201),
            (4.4, 210 / 384, 96, 1042, 629),
            (9.0, 210 / 1728, 25, 4000, 2300),
        ],
        "twine_no": ["210/18", "210/36", "210/72", "210/144", "210/384", "210/1728"],
    },
    "Primanet Braid": {
        "page": "p. 192 (10.10)",
        "material": "HMPE",
        "construction": "trenzado de 16 hilos",
        "elongation": 4.0,
        "points": [
            (1.1, 1190, 84, 135),
            (1.7, 685, 146, 220),
            (2.5, 316, 316, 425),
            (3.5, 158, 632, 753),
            (4.5, 105, 948, 1125),
            (5.5, 65, 1543, 1790),
        ],
    },
    "Primanet Twist": {
        "page": "p. 193 (10.11)",
        "material": "HMPE",
        "construction": "torcido de 3 cabos",
        "elongation": 4.8,
        "points": [
            (0.9, 1705, 59, 101),
            (1.1, 1111, 90, 136),
            (1.4, 824, 121, 178),
            (1.8, 549, 182, 254),
            (2.1, 407, 246, 342),
        ],
    },
}

#: Hampidjan, cabos de fibra: diámetro [mm], largo del rollo [m], peso del rollo [kg] (o
#: ``kg_per_100m``), rotura [t]. ``elongation`` [%] del cuadro «Properties».
HAMPIDJAN_ROPE: dict[str, dict[str, Any]] = {
    "Nylex": {
        "page": "p. 104 (6.2)",
        "material": "PA",
        "construction": "trenzado de 12 cabos (red pelágica)",
        "elongation": 36.0,
        "points": [
            (6, 1500, 42.6, 1.3),
            (10, 470, 36.0, 3.5),
            (12, 310, 35.8, 4.4),
            (16, 160, 31.4, 7.6),
            (24, 300, 119.1, 16.1),
            (32, 500, 355.7, 26.1),
        ],
    },
    "Kraft rope": {
        "page": "p. 112 (6.10)",
        "material": "PP",
        "construction": "torcido de 3 cordones, Polysteel (mezcla PP/PE)",
        "elongation": 22.0,
        "points": [
            (8, 220, 6.6, 1.3),
            (12, 220, 14.5, 2.6),
            (16, 220, 25.5, 4.9),
            (20, 220, 39.5, 6.5),
            (24, 220, 57.0, 8.6),
            (32, 220, 100.0, 15.3),
        ],
    },
    "Danline": {
        "page": "p. 125 (6.23)",
        "material": "PP",
        "construction": "torcido de 3 cordones, Danline",
        "elongation": 25.0,
        "note": "filas de rollos de 220 m (las de 55 m repiten el peso del rollo de 220 m; la de "
        "22 mm no trae peso ni rotura)",
        "points": [
            (8, 220, 6.6, 1.2),
            (12, 220, 14.5, 2.7),
            (16, 220, 25.5, 4.7),
            (20, 220, 39.3, 6.9),
            (24, 220, 57.0, 9.9),
            (32, 220, 101.2, 16.8),
        ],
    },
    "DynIce 75 Duracoat": {
        "page": "p. 132 (7.2)",
        "material": "HMPE",
        "construction": "trenzado de 12 cabos, Dyneema SK75 impregnado",
        "elongation": 3.5,
        "elongation_note": "3,5 % «después de pretensar» (cabo trabajado; la curva del cabo nuevo "
        "llega a la rotura cerca del 5,5 %)",
        "kg_per_100m": True,
        "note": "rotura según ISO 2307; el empalme puede bajarla hasta 10 %",
        "points": [
            (4, None, 1.10, 2.0),
            (8, None, 3.80, 6.7),
            (12, None, 9.30, 16.4),
            (16, None, 16.0, 27.4),
            (24, None, 35.6, 57.8),
            (36, None, 67.2, 102.9),
        ],
    },
    "Prima Foot rope": {
        "page": "p. 179 (9.15)",
        "material": "HMPE",
        "construction": "12 cabos de HMPE con forro trenzado de PA/PE (burlón)",
        "elongation": 3.5,
        "elongation_note": "3,5 % «después de pretensar»",
        "kg_per_100m": True,
        "note": "diámetro exterior (la ficha da interior/exterior); rotura según ISO 2307",
        # diámetro exterior [mm], diámetro interior [mm], kg/100 m, rotura [t].
        "points": [
            (43, 22, 68.8, 46.1),
            (51, 30, 90.5, 91.8),
            (61, 40, 129.0, 138.8),
            (67, 46, 154.5, 179.1),
            (75, 54, 190.0, 216.0),
        ],
    },
}

#: Hampidjan, cabo combinado para redes de cerco (p. 234, 11.18; Randers Reb / Itsaskorda):
#: cuatro cordones de alambre galvanizado forrados con hilo Danline. Diámetro nominal [mm],
#: peso aproximado [kg/m], rotura [kp = kgf]. La ficha no da alargamiento.
HAMPIDJAN_COMBINATION: list[tuple[float, float, float]] = [
    (18, 0.36, 5950),
    (20, 0.40, 6400),
    (24, 0.55, 7800),
    (28, 0.71, 9800),
    (32, 0.88, 12200),
    (38, 1.42, 18500),
]

#: Hampidjan, cables de arrastre (sección 11): diámetro [mm], kg/m, carga mínima de rotura [t].
#: La ficha no da alargamiento ni módulo.
HAMPIDJAN_WIRE: dict[str, dict[str, Any]] = {
    "Randers Trawl Wire": {
        "brand": "Randers Reb",
        "country": "DK",
        "page": "p. 217 (11.1)",
        "construction": "6x25 Seale compactado",
        "construction_note": "la ficha imprime «6X255E + IWRC»; se lee 6x25SE (Seale)",
        "core": "IWRC",
        "generic": "6x19_991",
        "points": [
            (14, 0.90, 15.4),
            (18, 1.52, 25.9),
            (22, 2.12, 36.1),
            (26, 2.83, 47.8),
            (30, 3.87, 66.0),
            (36, 5.37, 91.0),
        ],
    },
    "Super Atlantic 6xK26SW-CWR": {
        "brand": "Oliveira",
        "country": "PT",
        "page": "p. 218 (11.2)",
        "construction": "6xK26SW compactado",
        "core": "IWRC",
        "generic": "6x19_991",
        "points": [
            (16, 1.15, 17.1),
            (20, 1.79, 27.2),
            (24, 2.57, 39.7),
            (28, 3.55, 56.2),
            (32, 4.60, 73.6),
            (36, 5.80, 93.1),
        ],
    },
    "6xK26SW-CF": {
        "brand": "Oliveira",
        "country": "PT",
        "page": "p. 219 (11.3)",
        "construction": "6xK26SW compactado",
        "core": "FC",
        "generic": "6x19_991",
        "points": [
            (20, 1.60, 26.1),
            (22, 1.92, 31.3),
            (24, 2.29, 37.2),
            (26, 2.68, 43.7),
            (30, 3.61, 58.7),
            (36, 5.20, 84.6),
        ],
    },
    "Green Strand 6x19 Poly Core": {
        "brand": "Oliveira",
        "country": "PT",
        "page": "p. 222 (11.6)",
        "construction": "6x19",
        "core": "FC",
        "generic": "6x19_1261_fc",
        "points": [
            (12, 0.51, 7.8),
            (14, 0.69, 10.7),
            (16, 0.95, 14.8),
            (18, 1.20, 18.6),
            (20, 1.47, 22.8),
            (24, 2.04, 31.6),
        ],
    },
    "Green Strand 6x19 IWRC": {
        "brand": "Oliveira",
        "country": "PT",
        "page": "p. 222 (11.6)",
        "construction": "6x19",
        "core": "IWRC",
        "generic": "6x19_991",
        "points": [
            (18, 1.36, 20.1),
            (20, 1.68, 24.8),
            (22, 1.94, 28.8),
            (24, 2.32, 34.4),
            (26, 2.82, 43.0),
            (32, 4.20, 64.9),
        ],
    },
}

#: Hampidjan, cadena de eslabón largo (sección 12): diámetro [mm], largo interior E [mm],
#: ancho interior H [mm], carga [t], peso [kg/m]. ``load``: «swl» (carga de trabajo con factor
#: ``factor``) o «mbl» (rotura).
HAMPIDJAN_CHAIN: dict[str, dict[str, Any]] = {
    "Trygg GR80 long link": {
        "brand": "Trygg",
        "country": "NO",
        "page": "p. 240 (12.5)",
        "grade": "80",
        "load": "swl",
        "factor": 5.0,
        "points": [
            (9, 57, 16, 2.0, 1.4),
            (13, 81, 22, 4.2, 2.7),
            (16, 100, 26, 6.4, 4.8),
            (19, 100, 28, 9.0, 6.5),
            (22, 120, 32, 12.1, 8.5),
            (28, 150, 39, 19.7, 14.0),
        ],
    },
    "Trawlex long link": {
        "brand": "Trawlex",
        "country": None,
        "page": "p. 242 (12.7)",
        "grade": "Trawlex",
        "load": "mbl",
        "note": "se omite la fila de 13 mm (peso impreso «28», errata evidente); 16 y 19 mm son "
        "«profile chain»",
        "points": [
            (9, 53, 15, 12.5, 1.4),
            (11, 63, 18, 18.5, 2.0),
            (16, 100, 24.5, 40.0, 4.3),
            (19, 100, 25, 57.0, 6.3),
            (22, 120, 35.5, 70.0, 8.7),
            (28, 150, 46, 105.0, 14.4),
        ],
    },
}

#: Hampidjan, grilletes de seguridad Green Pin de Van Beest (p. 275, 13.32): código, WLL [t]
#: (factor 6:1), A = diámetro del cuerpo [mm], B = diámetro del perno [mm], peso [kg/100 u.].
HAMPIDJAN_SHACKLE: list[tuple[str, float, float, float, float]] = [
    ("FH08GPS", 0.75, 8, 10, 10),
    ("FH12GPS", 2.00, 13, 16, 34),
    ("FH16GPS", 3.25, 16, 19, 63),
    ("FH19GPS", 4.75, 19, 22, 95),
    ("FH25GPS", 8.50, 25, 28, 230),
    ("FH32GPS", 12.00, 32, 35, 440),
    ("FH38GPS", 17.00, 38, 42, 750),
    ("FH50GPS", 35.00, 50, 57, 1892),
]

#: Hampidjan, boyas de arrastre de Atlantic Floats (p. 314, 15.2): código, diámetro [mm], peso
#: [g], flotación [g], profundidad máxima [m], profundidad de trabajo [m], montaje.
HAMPIDJAN_FLOAT: list[tuple[str, float, float, float, float, float, str]] = [
    ("SA1084", 200, 1300, 2685, 1150, 1050, "agujero central"),
    ("SA1087", 200, 1760, 2110, 2400, 2000, "agujero central"),
    ("SA1095", 242, 2433, 4280, 1300, 1100, "agujero central"),
    ("SA1096", 242, 2822, 3900, 2500, 2000, "agujero central"),
    ("SA1101", 280, 2490, 8610, 700, 600, "agujero central"),
    ("SA1103", 280, 3730, 6950, 2000, 1500, "agujero central"),
    ("SA2080", 200, 1500, 1700, 1850, 1700, "con orejas"),
]

#: Garware, paño torcido (págs. «Fisheries: Twisted Nets»): construcción, rendimiento [m/kg],
#: rotura [kgf] (``None`` si la ficha no la da), rotura con nudo [kgf]. La ficha NO da diámetro.
GARWARE_TWISTED: dict[str, dict[str, Any]] = {
    "380 D Regular": {
        "material": "PE",
        "generic": "PE_twisted",
        "page": "Garware, «Fisheries: Twisted Nets» (380 D Regular)",
        "points": [
            ("380 D/6 PLY", 3450, 9.6, 16),
            ("380 D/12 PLY", 1688, 18.8, 30),
            ("380 D/24 PLY", 845, 36.0, 54),
            ("380 D/48 PLY", 432, 68.5, 110),
            ("380 D/90 PLY", 225, 135.0, 178),
            ("380 D/180 PLY", 110, 234.0, 347),
        ],
    },
    "500 D Regular": {
        "material": "PE",
        "generic": "PE_twisted",
        "page": "Garware, «Fisheries: Twisted Nets» (500 D Regular)",
        "points": [
            ("500 D/2X3", 2700, 15.30, 20),
            ("500 D/4X3", 1350, 28.80, 39),
            ("500 D/6X3", 900, 43.20, 54.7),
            ("500 D/10X3", 558, 69.30, 86),
            ("500 D/20X3", 265, 135.00, 190),
            ("500 D/50X3", 105, 300.00, 370),
        ],
    },
    "Sapphire Twisted 380D": {
        "material": "PE",
        "generic": "PE_twisted",
        "page": "Garware, «Fisheries: Twisted Nets» (Sapphire Twisted 380D)",
        "points": [
            ("380 D/3X3", 2400, 18.8, 26),
            ("380 D/4X3", 1775, 25, 34),
            ("380 D/6X3", 1125, 38, 51),
            ("380 D/8X3", 845, 44, 64),
            ("380 D/10X3", 675, 55, 84),
            ("380 D/14X3", 482, 75, 110),
        ],
    },
    "Nylon Twisted": {
        "material": "PA",
        "generic": "PA_twisted",
        "page": "Garware, «Fisheries: Twisted Nets» (Nylon Twisted)",
        "points": [
            ("210 D/4X3", 3386, 18.0, 22.1),
            ("210 D/8X3", 1626, 38.0, 41),
            ("210 D/16X3", 790, 77.0, 82.3),
            ("210 D/24X3", 527, 115.0, 117),
            ("210 D/48X3", 260, 212.0, 216),
            ("210 D/128X3", 82, 511.0, 549),
        ],
    },
}

#: Garware, cabos (págs. «Fisheries: Trawl Ropes»): diámetro [mm], g/m, rotura [kgf].
GARWARE_ROPES: dict[str, dict[str, Any]] = {
    "Maxima": {
        "material": "PP",
        "construction": "3 cordones, mezcla de polímeros (equivalente a Danline/Polysteel)",
        "points": [
            (6, 16.8, 750),
            (8, 30.0, 1350),
            (12, 65.9, 3000),
            (16, 115.9, 4800),
            (20, 181.8, 7600),
            (24, 259.1, 10500),
        ],
    },
    "PP": {
        "material": "PP",
        "construction": "3 cordones, cinta Parapro o monofilamento de PP",
        "points": [
            (6, 16.8, 600),
            (8, 30.0, 1060),
            (12, 65.9, 2210),
            (16, 115.9, 3770),
            (20, 181.8, 5800),
            (24, 259.1, 8130),
        ],
    },
    "PE": {
        "material": "PE",
        "construction": "3 o 4 cordones, PE de alta densidad",
        "points": [
            (6, 18.0, 400),
            (8, 33.0, 700),
            (12, 72.0, 1540),
            (16, 128.0, 2800),
            (20, 200.0, 4300),
            (24, 295.0, 6100),
        ],
    },
    "Maxibraid": {
        "material": "PA",
        "construction": "trenzado de 12 cabos, nylon impregnado",
        "points": [
            (6, 33.2, 1400),
            (8, 55, 2400),
            (10, 67, 3000),
            (12, 86, 3700),
            (16, 159, 6800),
            (20, 258, 10800),
        ],
    },
}

#: Bridon-Bekaert 2023: construcciones que no estaban (diámetro [mm], kg/100 m, MBL [t]).
BRIDON_WIRE_MORE: dict[str, dict[str, Any]] = {
    "Dyform Starfish 6x26 Poly Core": {
        "construction": "6x26 (10/5&5/5/1) compactado",
        "core": "fibra sintética",
        "generic": "6x19_991",
        "page": "Dyform Starfish",
        "points": [
            (20, 159.7, 26.7),
            (24, 224.8, 38.5),
            (28, 317.4, 52.4),
            (32, 408.8, 68.4),
            (36, 514.5, 86.6),
            (44, 768.5, 129.3),
        ],
    },
    "Dyform 6x26 Poly Core": {
        "construction": "6x26 (10/5&5/5/1) compactado",
        "core": "fibra sintética",
        "generic": "6x19_991",
        "page": "Dyform",
        "note": "de 20 a 44 mm, los mismos valores que Dyform Starfish; se cargan los tamaños "
        "que Starfish no tiene",
        "points": [(16, 103.3, 17.1), (18, 129.1, 21.6)],
    },
    "Dyform 6x26 IWRC": {
        "construction": "6x26 (10/5&5/5/1) compactado",
        "core": "IWRC",
        "generic": "6x19_991",
        "page": "Dyform",
        "note": "de 20 a 44 mm, los mismos valores que Dyform Starfish IWRC",
        "points": [(16, 115.5, 19.1), (18, 145.3, 24.1)],
    },
    "SeaBeam 6x26 Poly Core": {
        "construction": "6x26 (10/5&5/5/1)",
        "core": "fibra sintética",
        "generic": "6x19_991",
        "page": "Seabeam (arrastre a la vara)",
        "points": [(22, 174.4, 25.7), (26, 240.6, 35.8), (32, 362.6, 54.3)],
    },
    "SeaBeam 6x26 IWRC": {
        "construction": "6x26 (10/5&5/5/1)",
        "core": "IWRC",
        "generic": "6x19_991",
        "page": "Seabeam (arrastre a la vara)",
        "points": [(22, 199.4, 27.6), (26, 276.2, 38.6), (32, 415.0, 58.5)],
    },
    "6x7": {
        "construction": "6x7",
        "core": "FC",
        "generic": "6x7_fc",
        "page": "6x7 (arrastre a la vara)",
        "points": [(10, 33.30, 5.32), (12, 48.10, 7.65), (14, 65.40, 10.42)],
    },
}

#: Gunnebo Industries LLZ grado 6 galvanizada (NS 9415; factor 4:1; «no para izaje»): diámetro
#: [mm], paso P [mm], ancho exterior w1 [mm], rotura mínima [t], peso [kg/m]. La columna métrica
#: dice «kg» pero los valores son toneladas (la columna imperial: 17 191 lb = 7,8 t).
GUNNEBO_LLZ: list[tuple[float, float, float, float, float]] = [
    (9, 53, 14.3, 7.8, 1.4),
    (13, 80, 21.1, 16.3, 2.9),
    (16, 100, 27, 24.7, 4.6),
    (19, 99, 28.5, 34.8, 6.5),
    (22, 120, 36, 46.6, 8.7),
    (25, 140, 37, 60.0, 12.0),
    (32, 170, 44, 98.3, 19.0),
]

#: Crosby G-209 (grillete de perno roscado, galvanizado; factor 6:1): tamaño nominal [in],
#: WLL [t], código G-209, peso [kg], B = diámetro del perno [mm], D = diámetro del cuerpo [mm].
CROSBY_G209: list[tuple[str, float, str, float, float, float]] = [
    ("3/8", 1.0, "1018419", 0.14, 11.2, 9.7),
    ("1/2", 2.0, "1018455", 0.33, 15.7, 12.7),
    ("5/8", 3.25, "1018473", 0.62, 19.1, 15.7),
    ("3/4", 4.75, "1018491", 1.07, 22.4, 19.1),
    ("7/8", 6.5, "1018516", 1.64, 25.4, 22.4),
    ("1", 8.5, "1018534", 2.28, 28.4, 25.4),
    ("1-1/4", 12.0, "1018570", 4.31, 35.1, 32.8),
    ("1-1/2", 17.0, "1018614", 7.80, 41.4, 38.9),
    ("2", 35.0, "1018650", 20.4, 57.2, 52.8),
    ("2-1/2", 55.0, "1018678", 38.9, 69.9, 69.1),
]
