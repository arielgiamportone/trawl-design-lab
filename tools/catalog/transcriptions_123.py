"""Transcripciones de la Fase 12.3: BOBP/WP/10, BOBP/WP/20 y Schärfe (1983).

Mismas convenciones que ``tools/catalog/transcriptions.py``. Las redes pelágicas de Schärfe son de
4 paneles: :func:`four_panel` arma el dorso, el vientre y los costados a partir de las cadenas de
paños del plano (el plano da un paño de cada clase; los cuatro de cada estación tienen el mismo
alto). Las alas de los costados no se modelan: el motor y el simulador llevan las relingas por las
alas del dorso y del vientre (nota en cada red).

Los planos de Schärfe dan el alto en filas con medias mallas (79,5): se redondea a la malla entera
(:func:`rows`) y se anota.
"""

from __future__ import annotations

import math
from typing import Any

Row = tuple[float, float, int, int, float, str | None]  # mallero, Rtex, boca, bolsa, filas, corte


def rows(n: float) -> int:
    """Filas enteras de un alto con media malla (79,5 → 80)."""
    return int(math.floor(n + 0.5))


def _chain(prefix: str, plane: str, chain: list[tuple[str, Row]], count: int) -> list[tuple]:
    out = []
    for k, (section, (mesh, rtex, top, bottom, depth, cut)) in enumerate(chain, start=1):
        out.append(
            (f"{prefix}{k}", plane, section, count, mesh, rtex, top, bottom, rows(depth), cut)
        )
    return out


def four_panel(
    upper_wing: Row,
    lower_wing: Row,
    body: list[tuple[str, Row]],
    side_body: list[tuple[str, Row]] | None = None,
) -> list[tuple]:
    """Paños de una red de 4 paneles: alas y cuerpo del dorso y del vientre, cuerpo de costados.

    ``body`` es la cadena central del dorso (igual en el vientre) y ``side_body`` la de los
    costados (por defecto, la misma). Ids: ``UW``/``LW`` alas, ``U1…``, ``L1…``, ``S1…``.
    """
    out: list[tuple] = []
    for wid, plane, wing in (("UW", "upper", upper_wing), ("LW", "lower", lower_wing)):
        mesh, rtex, top, bottom, depth, cut = wing
        out.append((wid, plane, "wing", 2, mesh, rtex, top, bottom, rows(depth), cut))
    out += _chain("U", "upper", body, 1)
    out += _chain("L", "lower", body, 1)
    out += _chain("S", "side", side_body or body, 2)
    return out


def _depth_notes(chain: list[tuple[str, Row]], prefix: str) -> dict[str, dict[str, Any]]:
    """Procedencia del alto redondeado de cada paño con media malla."""
    out: dict[str, dict[str, Any]] = {}
    for k, (_, row) in enumerate(chain, start=1):
        if row[4] != int(row[4]):
            out[f"{prefix}{k}"] = {
                "meshes_depth": (
                    "derived",
                    f"el plano da {str(row[4]).replace('.', ',')} filas; se redondea a "
                    f"{rows(row[4])}",
                )
            }
    return out


def _merge(*dicts: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for d in dicts:
        for k, v in d.items():
            out.setdefault(k, {}).update(v)
    return out


# --- Schärfe 1983: red de krill (ap. 5) y popa común a los aps. 7 y 8 ---------------------------

#: Popa de la red de krill desde la estación de 369 mallas de 120 mm (ap. 5).
KRILL_AFT: list[tuple[str, Row]] = [
    ("body", (120, 1210, 369, 350, 19.5, None)),
    ("body", (80, 910, 525, 425, 99.5, "1N2B")),
    ("body", (60, 760, 566, 466, 99.5, "1N2B")),
    ("body", (31, 610, 900, 600, 299.5, "1N2B")),
    ("body", (22, 760, 845, 445, 599.5, None)),
    ("body", (22, 910, 445, 245, 199.5, "1N2B")),
    # Copo de 9 mm en tramos de 4,0 m (444 filas) y uno final de 10,0 m (1111 filas).
    ("codend", (9, 340, 625, 525, 444, None)),
    ("codend", (9, 340, 525, 450, 444, None)),
    ("codend", (9, 340, 450, 375, 444, None)),
    ("codend", (9, 340, 375, 300, 444, None)),
    ("codend", (9, 340, 300, 240, 444, None)),
    ("codend", (9, 340, 240, 240, 1111, "AN")),
]

KRILL_BODY: list[tuple[str, Row]] = [
    ("body", (200, 1820, 355, 338, 19.5, None)),
    ("body", (170, 1210, 336, 317, 19.5, None)),
    *KRILL_AFT,
]

#: Frente de 800 mm (ap. 7) desde la estación de 152 mallas de 400 mm, común a dorso y costados.
FRONT_800_AFT: list[tuple[str, Row]] = [
    ("body", (400, 2220, 152, 127, 24.5, "1N2B")),
    ("body", (200, 1820, 253, 228, 24.5, "1N2B")),
    ("body", (120, 1210, 377, 369, 9.5, None)),
    *KRILL_AFT,
]

SCHARFE_SOURCE = {
    "key": "scharfe1983",
    "url": "https://www.fao.org/4/x6567e/x6567e00.htm",
}

SCHARFE_COMMON: dict[str, Any] = {
    "family": "pelagic",
    "rig": "otter",
    "vessel_hp": (1000, 1500),
    "target_species": "peces linterna (Benthosema pterotum), capa D1 de 100–150 m",
    "material": "PA",
    "hanging": {
        "default": (
            0.50,
            "derived",
            "el documento calcula la boca con la mitad del largo de paño de las relingas (U1 = "
            "0,5); con eso la red de krill da los 256 m² de boca que informa",
        ),
    },
    "design": {
        "depth_m": (125.0, "transcribed", "capa D1 entre 100 y 150 m: valor medio"),
        "sweeps_m": (
            80.0,
            "assumed",
            "malletas de 100 m; el motor calcula la superior con su regla y el resto va como patente",
        ),
        "door_length_m": (4.3, "transcribed", "portones SÜBERKRÜB de 4,3 × 1,9 m = 8,2 m²"),
        "door_height_m": (1.9, "transcribed", None),
        "door_weight_air_kg": (1350.0, "transcribed", "1,35 t cada uno"),
        "vessel_length_m": (45.0, "transcribed", "B/I Dr. Fridtjof Nansen, 45 m y 1500 hp"),
    },
    "rigging": {
        "doors": "SÜBERKRÜB cambados de 4,3 × 1,9 m (8,2 m²), 1,35 t",
        "bridles": "100 m (las inferiores 94 m más 6 m de cadena de peso delantero)",
        "front_weights": "cadena de 230 a 520 kg por lado según el lance",
    },
}

SIDE_WING_NOTE = (
    "Los costados del plano tienen alas como el dorso y el vientre; en el modelo los costados "
    "empiezan en la primera estación del cuerpo (las relingas van por las alas del dorso y del "
    "vientre)."
)


def _scharfe(
    net_id: str,
    name: str,
    description: str,
    figure: str,
    title: str,
    panels: list[tuple],
    overrides: dict[str, dict[str, Any]],
    *,
    status: str = "published",
    notes: list[str] | None = None,
    measured: list[dict[str, Any]] | None = None,
    floats: dict[str, Any] | None = None,
    ballast: dict[str, Any] | None = None,
    panel_notes: dict[str, str] | None = None,
) -> dict[str, Any]:
    net: dict[str, Any] = {
        "id": net_id,
        "name": name,
        "description": description,
        **SCHARFE_COMMON,
        "status": status,
        "source": {
            **SCHARFE_SOURCE,
            "title": f"Schärfe 1983 (FI:DP/GLO/82/001), {title}",
            "figure": figure,
            "page": figure,
        },
        "panels": panels,
        "overrides": overrides,
        "notes": [SIDE_WING_NOTE, *(notes or [])],
    }
    if measured:
        net["measured"] = measured
    if floats:
        net["floats"] = floats
    if ballast:
        net["ballast_kg"] = ballast
    if panel_notes:
        net["panel_notes"] = panel_notes
    return net


KRILL_WING: Row = (200, 1820, 25, 105, 79.5, "AB")

SCHARFE_NETS: list[dict[str, Any]] = [
    _scharfe(
        "scharfe_krill_1420x200",
        "Arrastre pelágico de krill de 4 paneles, 1420 × 200 mm (Schärfe 1983)",
        "Red pelágica de 4 paños iguales con 1420 mallas de 200 mm de circunferencia (284 m), "
        "cuerpo de 170–22 mm y copo de 9 mm. Red de krill modificada que el B/I Dr. Fridtjof "
        "Nansen usó para peces linterna en el golfo de Omán (1983).",
        "Apéndice 5 (x6567e06.gif)",
        "apéndice 5: Krill trawl, 1420 × 200 = 284 m circumference",
        four_panel(KRILL_WING, KRILL_WING, KRILL_BODY),
        _merge(
            _depth_notes([("wing", KRILL_WING)], "UW"),
            _depth_notes([("wing", KRILL_WING)], "LW"),
            *(_depth_notes(KRILL_BODY, p) for p in ("U", "L", "S")),
        ),
        notes=[
            "Cuatro paños iguales: 4 × 355 = 1420 mallas de 200 mm, la circunferencia que da el "
            "título del apéndice.",
            "Las franjas de 170 y 120 mm se angostan respecto de la de 200 mm (empalmes de 16 y "
            "18 %): es el plano, no un error de lectura.",
            "El documento estima la boca en 256 m² (16 × 16 m).",
        ],
    ),
    _scharfe(
        "scharfe_harstad_1436x200",
        "Arrastre pelágico Harstad de 4 paneles, 1436 × 200 mm (Schärfe 1983)",
        "Red pelágica noruega de 4 paños iguales con 1436 mallas de 200 mm de circunferencia "
        "(287 m) y cuerpo de 190–60 mm; se usó a bordo para muestreo biológico.",
        "Apéndice 6 (x6567e07.gif)",
        "apéndice 6: Harstad trawl, 1436 × 200 = 287 m circumference",
        four_panel(
            (200, 2430, 50, 130, 79.5, "AB"),
            (200, 2430, 50, 130, 79.5, "AB"),
            HARSTAD_BODY := [
                ("body", (200, 1520, 359, 310, 49.5, "1N2B")),
                ("body", (190, 1370, 310, 260, 49.5, "1N2B")),
                ("body", (140, 1370, 260, 202, 59.5, "1N2B")),
                ("body", (120, 1370, 202, 143, 59.5, "1N2B")),
                ("body", (80, 1370, 214, 115, 99.5, "1N2B")),
                ("body", (60, 1370, 155, 96, 99.5, None)),
                ("codend", (40, 910, 144, 144, 125, "AN")),
            ],
        ),
        _merge(
            *(_depth_notes(HARSTAD_BODY, p) for p in ("U", "L", "S")),
            _depth_notes([("wing", (200, 2430, 50, 130, 79.5, "AB"))], "UW"),
            _depth_notes([("wing", (200, 2430, 50, 130, 79.5, "AB"))], "LW"),
            *(
                {
                    f"{p}7": {
                        k: (
                            "assumed",
                            "el plano no dibuja el copo (sólo indica un forro de 4,6 mm sin nudo, "
                            "PA R380 tex): se modela un copo de 40 mm de 5 m que empalma con el "
                            "borde de 96 mallas de 60 mm",
                        )
                        for k in ("mesh_mm", "rtex", "meshes_top", "meshes_bottom", "meshes_depth")
                    }
                }
                for p in ("U", "L", "S")
            ),
        ),
        status="draft",
        notes=[
            "Cuatro paños iguales: 4 × 359 = 1436 mallas de 200 mm.",
            "BORRADOR: el plano cose 260 mallas de 190 mm con 260 de 140 mm (26 % de diferencia "
            "de largo); el validador lo marca como error. Puede ser un fruncido del plano o una "
            "lectura del mallero; queda para revisar con el original.",
        ],
    ),
    _scharfe(
        "scharfe_krill_front800",
        "Arrastre pelágico de krill con frente de 800 mm, 422 × 800 (Schärfe 1983)",
        "Red de krill con un frente agrandado de 800 mm (422 mallas, 338 m de circunferencia), "
        "dorso y vientre distintos de los costados en la primera estación; popa de la red de krill.",
        "Apéndice 7 (x6567e08.gif)",
        "apéndice 7: Krill trawl with 800 mm meshsize front part, 422 × 800 = 338 m",
        four_panel(
            (800, 3370, 16, 40, 25.5, "AB"),
            (800, 3370, 10, 40, 31.0, "AB"),
            F8 := [("body", (800, 3370, 110, 76, 24.5, "1N4B")), *FRONT_800_AFT],
            F8S := [("body", (800, 3370, 101, 76, 24.5, "1N2B")), *FRONT_800_AFT],
        ),
        _merge(
            *(_depth_notes(F8, p) for p in ("U", "L")),
            _depth_notes(F8S, "S"),
            _depth_notes([("wing", (800, 3370, 16, 40, 25.5, "AB"))], "UW"),
            {
                "UW": {
                    "meshes_top": (
                        "transcribed",
                        "el plano dibuja la mitad izquierda del paño con un ala de 16 → 40 mallas "
                        "en 25,5 filas y la derecha con 10 → 40 en 31 filas; se toma la izquierda "
                        "para el dorso y la derecha para el vientre",
                    )
                },
                "LW": {
                    "meshes_top": (
                        "transcribed",
                        "mitad derecha del plano (ver la nota del ala del dorso)",
                    )
                },
            },
        ),
        notes=[
            "Circunferencia: 2 × 110 (dorso y vientre) + 2 × 101 (costados) = 422 mallas de "
            "800 mm, como el título del apéndice.",
            "Empalmes del frente: 76 × 800 = 152 × 400; 127 × 400 ≈ 253 × 200; 228 × 200 ≈ 377 × "
            "120; sigue la red de krill desde la estación de 369 mallas de 120 mm.",
        ],
        measured=[
            {
                "speed_kn": 2.7,
                "warp_m": 900.0,
                "height_m": 21.0,
                "width_m": 33.0,
                "front_weight_kg": 520.0,
                "note": "2,5–2,9 kn, 900 m de cable, pesos delanteros de 520 kg: 20–22 m de alto "
                "y 30–36 m de ancho a 320–340 m",
            },
            {
                "speed_kn": 2.0,
                "warp_m": 300.0,
                "height_m": 33.0,
                "width_m": 25.0,
                "front_weight_kg": 230.0,
                "note": "≈ 2 kn, 300 m de cable, pesos de 230 kg: 33 m de alto y 25 m de ancho",
            },
        ],
        floats={
            "count": 24,
            "diameter_mm": 280,
            "kind": "transcribed",
        },
        ballast={
            "value": 560.0,
            "kind": "transcribed",
            "note": "100 kg de lastre en el burlón más 2 × 230 kg de pesos delanteros (el "
            "aparejo más usado); los pesos van en las malletas inferiores, el motor los reparte en "
            "el burlón",
        },
    ),
    _scharfe(
        "scharfe_krill_front1600",
        "Arrastre pelágico de krill con frente de 1600 mm, 252 × 1600 (Schärfe 1983)",
        "Red de krill con un frente de 1600 mm (252 mallas, 403 m de circunferencia) seguido de "
        "parte del frente de 800 mm y la popa de la red de krill.",
        "Apéndice 8 (x6567e09.gif)",
        "apéndice 8: Krill trawl with 1600 mm meshsize front part, 252 × 1600 = 403 m",
        four_panel(
            (1600, 8860, 9, 24, 14.5, "AB"),
            (1600, 8860, 6, 24, 18, "AB"),
            F16 := [
                ("body", (1600, 8860, 66, 46, 14.5, "1N4B")),
                ("body", (800, 3370, 92, 76, 12, "1N4B")),
                *FRONT_800_AFT,
            ],
            F16S := [
                ("body", (1600, 8860, 60, 44, 14.5, "1N3B")),
                ("body", (800, 3370, 88, 76, 12, "1N2B")),
                *FRONT_800_AFT,
            ],
        ),
        _merge(
            *(_depth_notes(F16, p) for p in ("U", "L")),
            _depth_notes(F16S, "S"),
            _depth_notes([("wing", (1600, 8860, 9, 24, 14.5, "AB"))], "UW"),
            {
                "LW": {
                    "meshes_depth": (
                        "derived",
                        "el plano no da las filas del ala de la mitad derecha; 18 filas es lo que "
                        "pide el corte AB para ir de 6 a 24 mallas",
                    ),
                    "meshes_top": (
                        "transcribed",
                        "mitad derecha del plano (ala de 6 → 24 mallas); la izquierda (9 → 24) va "
                        "al dorso",
                    ),
                },
                **{
                    f"{p}1": {
                        "rtex": (
                            "transcribed",
                            "se lee 8860 en el cuerpo de 1600 mm (8565 en el ala, ilegible); se "
                            "usa 8860",
                        )
                    }
                    for p in ("U", "L", "S")
                },
            },
        ),
        status="draft",
        notes=[
            "Circunferencia: 2 × 66 (dorso y vientre) + 2 × 60 (costados) = 252 mallas de "
            "1600 mm, como el título del apéndice; 46 × 1600 = 92 × 800 empalma con el frente de "
            "800 mm.",
            "BORRADOR: el alto del ala del vientre no se lee y el Rtex del ala es dudoso.",
        ],
        measured=[
            {
                "speed_kn": 2.1,
                "warp_m": 250.0,
                "height_m": 26.0,
                "width_m": 30.0,
                "front_weight_kg": 230.0,
                "note": "≈ 2,1 kn, 250 m de cable, pesos de 230 kg: 26 m de alto y 30 m de ancho "
                "(≈ 780 m²)",
            }
        ],
        floats={"count": 24, "diameter_mm": 280, "kind": "transcribed"},
        ballast={
            "value": 560.0,
            "kind": "transcribed",
            "note": "100 kg en el burlón más 2 × 230 kg de pesos delanteros",
        },
    ),
]


# --- BOBP/WP/10 (Pajot et al. 1982, Tamil Nadu, Palk Bay) --------------------------------------

WP10_SOURCE = {"key": "bobpwp10", "url": "https://www.fao.org/4/ad950e/ad950e00.pdf"}
WP10_COMMON: dict[str, Any] = {
    "family": "bottom",
    "vessel_hp": (65, 65),
    "target_species": "peces de fondo y semipelágicos, Palk Bay (menos de 30–40 m)",
    "material": "PE",
    "twine_diameter": {720: 1.25, 570: 1.00},
}
WP10_DEPTH = (
    30.0,
    "assumed",
    "el documento sitúa la pesca en Palk Bay, a menos de 30–40 m; se toma 30 m",
)


def _rope(length: float, wing: float, bosom: float, rope: str, material: str) -> dict[str, Any]:
    return {
        "length_m": length,
        "wing_m": wing,
        "bosom_m": bosom,
        "diameter_mm": 14,
        "material": material,
        "rope": rope,
    }


BOBP_NETS: list[dict[str, Any]] = [
    {
        "id": "bobp_wp10_ho360x160",
        "name": "Arrastre de fondo de gran abertura, 360 mallas de 160 mm (BOBP/WP/10)",
        "description": (
            "Red de arrastre de fondo de gran abertura para un barco de 65 hp, de dos caras, con "
            "alas de 200 mm, cuerpo de 160–40 mm y copo de 25 mm. Ensayada en Palk Bay (Tamil "
            "Nadu) en 1980."
        ),
        **WP10_COMMON,
        "rig": "otter",
        "source": {
            **WP10_SOURCE,
            "title": "BOBP/WP/10, apéndice 3: One boat high opening bottom trawl, 360 meshes of 160 mm",
            "figure": "Apéndice 3",
            "page": "17 del PDF ([13] del documento)",
        },
        "panels": [
            ("A", "upper", "wing_tip", 2, 200, 720, 10, 35, 15, "1N4B / AB"),
            ("C", "upper", "wing", 2, 200, 720, 35, 60, 45, "1N2B / AB"),
            ("E", "upper", "square", 1, 200, 720, 140, 125, 15, "1N2B"),
            ("G1", "upper", "body", 1, 160, 720, 180, 140, 40, "1N2B"),
            ("G2", "upper", "body", 1, 120, 720, 180, 140, 40, "1N2B"),
            ("G3", "upper", "body", 1, 80, 720, 210, 150, 60, "1N2B"),
            ("G4", "upper", "body", 1, 40, 570, 260, 65, 195, "1N2B"),
            ("I", "upper", "codend", 1, 25, 720, 120, 120, 200, "AN"),
            ("B", "lower", "wing_tip", 2, 200, 720, 6, 30, 15, "1N3B / AB"),
            ("D", "lower", "wing", 2, 200, 720, 30, 60, 60, "1N2B / AB"),
            ("F", "lower", "belly", 1, 160, 720, 180, 140, 40, "1N2B"),
            ("H2", "lower", "body", 1, 120, 720, 180, 140, 40, "1N2B"),
            ("H3", "lower", "body", 1, 80, 720, 210, 150, 60, "1N2B"),
            ("H4", "lower", "body", 1, 40, 570, 260, 65, 195, "1N2B"),
            ("J", "lower", "codend", 1, 25, 720, 120, 120, 200, "AN"),
        ],
        "overrides": {
            "C": {
                "meshes_depth": (
                    "derived",
                    "la cifra está borrosa (45 u 85); con 45 filas el dorso (15 + 45 + 15) llega "
                    "a la estación del cuerpo de 160 mm con el mismo largo que el vientre (15 + 60)",
                )
            },
            "G3": {
                "meshes_bottom": (
                    "transcribed",
                    "se lee 160 en el dorso y 150 en el vientre; el corte 1N2B en 60 filas da 150",
                )
            },
        },
        "panel_notes": {
            "E": "El cielo cose 125 mallas de 200 mm con 180 de 160 mm (14 %): fruncido del plano.",
            "G4": "Paños de 40 mm en PE R570 tex (Ø1,00); el resto en PE R720 tex (Ø1,25).",
            "I": "Bolsa de izado de 100 mm, PE R1760 tex (Ø2,5), 50 × 40 mallas.",
        },
        "hanging": {
            "upper": (
                0.50,
                "derived",
                "U1 de la bocana del dorso: 2,00 m de relinga sobre 20 mallas de 200 mm (0,50); "
                "se usa en todo el dorso",
            ),
            "lower": (
                0.33,
                "derived",
                "U1 de la bocana del vientre: 2,00 m de burlón sobre 30 mallas de 200 mm (0,33); "
                "se usa en todo el vientre",
            ),
            "default": (0.42, "assumed", "media de dorso y vientre"),
        },
        "headrope": _rope(
            25.60, 11.80, 2.00, "combinado_14_acero6x24_7", "combinado Ø14 + PE Ø20 en las alas"
        ),
        "footrope": _rope(31.60, 14.80, 2.00, "combinado_14_acero6x24_7", "combinado Ø14"),
        "design": {
            "depth_m": WP10_DEPTH,
            "door_length_m": (1.30, "transcribed", "portón del apéndice 4: 1300 × 650 mm"),
            "door_height_m": (0.65, "transcribed", None),
            "door_weight_air_kg": (50.0, "transcribed", None),
        },
        "rigging": {"doors": "portón plano de madera y hierro de 1,30 × 0,65 m, 50 kg (ap. 4)"},
        "notes": [
            "Figura del apéndice 3 rasterizada a 300 ppp: números legibles salvo el alto del ala "
            "del dorso.",
            "Empalmes: 140 × 160 = 22,4 m ≈ 180 × 120 = 21,6 m; 140 × 120 = 210 × 80 = 16,8 m; "
            "los cambios a 40 y 25 mm frunce ≈ 13 % (como en el plano).",
        ],
    },
    {
        "id": "bobp_wp10_pair_480x160",
        "name": "Arrastre de pareja de gran abertura, 480 mallas de 160 mm (BOBP/WP/10)",
        "description": (
            "Red de arrastre de fondo de gran abertura para dos barcos de 65 hp, con alas de "
            "200 mm, cuerpo de 160–40 mm y copo de 25 mm. Ensayada en Palk Bay en 1980."
        ),
        **WP10_COMMON,
        "rig": "pair",
        "source": {
            **WP10_SOURCE,
            "title": "BOBP/WP/10, apéndice 5: Two boat high opening bottom trawl, 480 meshes of 160 mm",
            "figure": "Apéndice 5",
            "page": "19 del PDF ([15] del documento)",
        },
        "panels": [
            ("A", "upper", "wing_tip", 2, 200, 720, 10, 45, 20, "1N6B / AB"),
            ("C", "upper", "wing", 2, 200, 720, 45, 78, 45, "3N2B / AB"),
            ("E", "upper", "square", 1, 200, 720, 180, 165, 15, "1N2B"),
            ("G1", "upper", "body", 1, 160, 720, 240, 180, 45, "1N4B"),
            ("G2", "upper", "body", 1, 120, 720, 240, 190, 50, "1N2B"),
            ("G3", "upper", "body", 1, 80, 720, 280, 180, 75, "1N4B"),
            ("G4", "upper", "body", 1, 40, 720, 360, 100, 260, "1N2B"),
            ("I", "upper", "codend", 1, 25, 720, 160, 160, 200, "AN"),
            ("B", "lower", "wing_tip", 2, 200, 720, 10, 40, 20, "1N2B / AB"),
            ("D", "lower", "wing", 2, 200, 720, 40, 80, 60, "1N1B / AB"),
            ("F", "lower", "belly", 1, 160, 720, 240, 180, 45, "1N4B"),
            ("H2", "lower", "body", 1, 120, 720, 240, 190, 50, "1N2B"),
            ("H3", "lower", "body", 1, 80, 720, 280, 180, 75, "1N4B"),
            ("H4", "lower", "body", 1, 40, 720, 360, 100, 260, "1N2B"),
            ("J", "lower", "codend", 1, 25, 720, 160, 160, 200, "AN"),
        ],
        "panel_notes": {
            "E": "El cielo cose 165 mallas de 200 mm con 240 de 160 mm (14 %): fruncido del plano.",
            "I": "Bolsa de izado de 100 mm, PE R1760 tex (Ø2,5), 50 × 40 mallas.",
        },
        "overrides": {
            "I": {
                "rtex": (
                    "assumed",
                    "la columna de material da PE R720 tex una sola vez para toda la red",
                )
            },
            "J": {
                "rtex": (
                    "assumed",
                    "la columna de material da PE R720 tex una sola vez para toda la red",
                )
            },
        },
        "hanging": {
            "upper": (
                0.45,
                "derived",
                "U1 de la bocana del dorso: 2,15 m de relinga sobre 24 mallas de 200 mm (0,45)",
            ),
            "lower": (
                0.36,
                "derived",
                "U1 de la bocana del vientre: 2,15 m de burlón sobre 30 mallas de 200 mm (0,36)",
            ),
            "default": (0.40, "assumed", "media de dorso y vientre"),
        },
        "headrope": _rope(
            27.75, 12.80, 2.15, "combinado_14_acero6x24_7", "combinado Ø14 + PE Ø20 en las alas"
        ),
        "footrope": _rope(33.75, 15.80, 2.15, "combinado_14_acero6x24_7", "combinado Ø14"),
        "design": {
            "depth_m": WP10_DEPTH,
            "sweeps_m": (
                0.0,
                "assumed",
                "el plano no da el aparejo de la pareja; malletas directo al cable",
            ),
        },
        "notes": [
            "Empalmes: 180 × 160 = 240 × 120 = 28,8 m; 190 × 120 ≈ 280 × 80 = 22,4 m; "
            "180 × 80 = 360 × 40 = 14,4 m; 100 × 40 = 160 × 25 = 4,0 m.",
            "El dorso (20 + 45 + 15 filas de 200 mm) y el vientre (20 + 60) llegan juntos a la "
            "estación de 240 mallas de 160 mm.",
        ],
    },
    {
        "id": "bobp_wp10_pair_680x60",
        "name": "Arrastre de pareja de gran abertura, 680 mallas de 60 mm (BOBP/WP/10)",
        "description": (
            "Red de arrastre de fondo de gran abertura para dos barcos de 65 hp, con alas de "
            "120 mm, cuerpo de 80–40 mm y copo de 32 y 25 mm. Ensayada en Palk Bay en 1980."
        ),
        **WP10_COMMON,
        "rig": "pair",
        "source": {
            **WP10_SOURCE,
            "title": "BOBP/WP/10, apéndice 6: Two boat high opening bottom trawl, 680 meshes of 60 mm",
            "figure": "Apéndice 6",
            "page": "20 del PDF ([16] del documento)",
        },
        "panels": [
            ("A", "upper", "wing_tip", 2, 120, 720, 4, 40, 24, "1N2B / AB"),
            ("C", "upper", "wing", 2, 120, 720, 40, 85, 90, "1N2B / AB"),
            ("E", "upper", "square", 1, 80, 720, 312, 272, 40, "1N2B"),
            ("G1", "upper", "body", 1, 60, 720, 340, 140, 200, "1N2B"),
            ("G2", "upper", "body", 1, 40, 720, 186, 60, 126, "1N2B"),
            ("I1", "upper", "codend", 1, 32, 720, 80, 80, 100, "AN"),
            ("I2", "upper", "codend", 1, 25, 720, 112, 112, 100, "AN"),
            ("B", "lower", "wing_tip", 2, 120, 720, 4, 40, 24, "1N2B / AB"),
            ("D", "lower", "wing", 2, 120, 720, 40, 70, 90, "1N4B / AB"),
            ("D2", "lower", "belly", 2, 80, 720, 86, 106, 40, "1N2B / AB"),
            ("F", "lower", "body", 1, 60, 720, 340, 140, 200, "1N2B"),
            ("H", "lower", "body", 1, 40, 720, 186, 60, 126, "1N2B"),
            ("J1", "lower", "codend", 1, 32, 720, 80, 80, 100, "AN"),
            ("J2", "lower", "codend", 1, 25, 720, 112, 112, 100, "AN"),
        ],
        "panel_notes": {
            "D2": "El vientre cose 70 mallas de 120 mm del ala con 86 de 80 mm (18 %): fruncido "
            "del plano.",
            "I1": "Copo en dos tramos: 32 mm y 25 mm; bolsa de izado de 100 mm, PE R1760 tex.",
        },
        "hanging": {
            "upper": (
                0.33,
                "derived",
                "U1 de la bocana del dorso: 1,60 m de relinga sobre 60 mallas de 80 mm (0,33)",
            ),
            "lower": (
                0.32,
                "derived",
                "U1 de la bocana del vientre: 1,50 m de burlón sobre 58 mallas de 80 mm (0,32)",
            ),
            "default": (0.33, "assumed", "media de dorso y vientre"),
        },
        "headrope": _rope(
            29.00, 13.70, 1.60, "combinado_14_acero6x24_7", "combinado Ø14 + PE Ø20 en las alas"
        ),
        "footrope": _rope(35.30, 16.90, 1.50, "combinado_14_acero6x24_7", "combinado Ø14"),
        "design": {
            "depth_m": WP10_DEPTH,
            "sweeps_m": (
                0.0,
                "assumed",
                "el plano no da el aparejo de la pareja; malletas directo al cable",
            ),
        },
        "notes": [
            "El vientre tiene una segunda sección de ala de 80 mm (D2, de a pares) bajo las alas "
            "de 120 mm, frente al cielo del dorso: es la estructura de la FAO A-3.",
            "El borde de boca del cielo (312 mallas de 80 mm) suma las alas del dorso (85 de 120 "
            "mm) y la bocana (60 de 80 mm): 2 × 10,2 + 4,8 = 25,2 m.",
        ],
    },
    {
        "id": "bobp_wp20_fish_shrimp",
        "name": "Arrastre de gran abertura pescado/camarón, un barco (BOBP/WP/20)",
        "description": (
            "Red de arrastre de fondo de gran abertura para pescado y camarón, para un barco de "
            "65–75 hp, con alas de 80 mm, cuerpo de 60–40 mm y copo de 30 mm (Tamil Nadu, "
            "1980–81)."
        ),
        "family": "bottom",
        "rig": "otter",
        "status": "draft",
        "vessel_hp": (65, 75),
        "target_species": "pescado y camarón (Palk Bay, golfo de Mannar)",
        "material": "PE",
        "twine_diameter": {720: 1.25},
        "source": {
            "key": "bobpwp20",
            "url": "https://www.fao.org/4/ad960e/ad960e00.pdf",
            "title": "BOBP/WP/20, apéndice 1: One-boat high-opening fish-cum-shrimp trawl",
            "figure": "Apéndice 1",
            "page": "24 del PDF ([19] del documento)",
        },
        "panels": [
            ("A", "upper", "wing_tip", 2, 80, 720, 14, 30, 32, "1N2B / AB"),
            ("C", "upper", "wing", 2, 80, 720, 30, 110, 190, "1N3B / AB"),
            ("E", "upper", "square", 1, 80, 720, 272, 262, 30, None),
            ("G1", "upper", "body", 1, 60, 720, 350, 200, 180, None),
            ("G2", "upper", "body", 1, 40, 720, 300, 180, 120, "1N2B"),
            ("G3", "upper", "body", 1, 30, 720, 240, 120, 120, "1N2B"),
            ("I", "upper", "codend", 1, 30, 720, 120, 120, 200, "AN"),
            ("B", "lower", "wing_tip", 2, 80, 720, 14, 32, 32, "1N2B / AB"),
            ("D", "lower", "wing", 2, 80, 720, 32, 100, 190, "1N3B / AB"),
            ("F", "lower", "belly", 1, 60, 720, 350, 200, 180, None),
            ("H2", "lower", "body", 1, 40, 720, 300, 180, 120, "1N2B"),
            ("H3", "lower", "body", 1, 30, 720, 240, 120, 120, "1N2B"),
            ("J", "lower", "codend", 1, 30, 720, 120, 120, 200, "AN"),
        ],
        "overrides": {
            "G3": {
                "mesh_mm": ("derived", "mallero sin rótulo; 30 mm empalma con 180 × 40 mm"),
            },
            "H3": {
                "mesh_mm": ("derived", "mallero sin rótulo; 30 mm empalma con 180 × 40 mm"),
            },
            **{
                pid: {
                    f: (
                        "assumed",
                        "el escaneo (107 ppp) no deja leer esta cifra; valor elegido para que "
                        "cierren el corte y los empalmes",
                    )
                    for f in ("meshes_top", "meshes_bottom")
                }
                for pid in ("A", "B", "E", "G1", "F")
            },
        },
        "hanging": {
            "default": (
                0.35,
                "assumed",
                "el plano no se lee lo suficiente para derivar U1 de las bocanas",
            ),
        },
        "headrope": _rope(26.70, 12.20, 2.30, "pp_14_retorcido_3_cordones", "PP Ø14"),
        "footrope": _rope(31.20, 14.60, 2.00, "pp_16_retorcido_3_cordones", "PP Ø16"),
        "floats": {
            "count": 13,
            "diameter_mm": 200,
            "note": "el plano da 32,5 kgf de flotación total; 13 boyas de 2,5 kgf (Ø200 supuesto)",
        },
        "ballast_kg": {"value": 45.2, "kind": "transcribed", "note": "lastre total del plano"},
        "design": {
            "depth_m": (30.0, "assumed", "el documento no da la profundidad; 30 m como WP/10"),
            "sweeps_m": (25.0, "transcribed", "patentes de 20,00–30,00 m PP Ø16: valor medio"),
            "door_length_m": (1.40, "transcribed", "portón plano de 1,40 × 0,70 m"),
            "door_height_m": (0.70, "transcribed", None),
            "door_weight_air_kg": (52.5, "transcribed", "50–55 kg: valor medio"),
        },
        "panel_notes": {
            "G3": "Mallero sin rótulo en el plano; 30 mm es el que empalma 180 × 40 = 240 × 30 "
            "(7,2 m) y el del copo.",
        },
        "notes": [
            "BORRADOR: la figura del documento es un escaneo de 107 ppp (611 × 875 px); se leen "
            "los malleros, las filas, las relingas y el aparejo, pero varias cifras de mallas de "
            "los bordes son ilegibles y van como supuestas.",
            "El dorso tiene 30 filas de cielo que el vientre no compensa en el largo de las alas: "
            "las estaciones del cuerpo no coinciden (lectura dudosa de las filas de las alas).",
        ],
    },
    {
        "id": "bobp_wp20_ho",
        "name": "Arrastre de fondo de gran abertura, un barco (BOBP/WP/20)",
        "description": (
            "Red de arrastre de fondo de gran abertura para un barco de 65–75 hp, con alas de "
            "200 mm, cuerpo de 160–40 mm y copo de 30 mm (Tamil Nadu, 1980–81)."
        ),
        "family": "bottom",
        "rig": "otter",
        "vessel_hp": (65, 75),
        "target_species": "peces de fondo y semipelágicos (Palk Bay, golfo de Mannar, Coromandel)",
        "material": "PE",
        "twine_diameter": {720: 1.25},
        "source": {
            "key": "bobpwp20",
            "url": "https://www.fao.org/4/ad960e/ad960e00.pdf",
            "title": "BOBP/WP/20, apéndice 2: One-boat high-opening bottom trawl",
            "figure": "Apéndice 2",
            "page": "25 del PDF ([20] del documento)",
        },
        "panels": [
            ("A", "upper", "wing_tip", 2, 200, 720, 3, 38, 22, "1N3B / AB"),
            ("C", "upper", "wing", 2, 200, 720, 38, 56, 35, "1N2B / AB"),
            ("E", "upper", "square", 1, 200, 720, 142, 127, 15, "1N2B"),
            ("G1", "upper", "body", 1, 160, 720, 160, 130, 30, "1N2B"),
            ("G2", "upper", "body", 1, 120, 720, 173, 133, 40, "1N2B"),
            ("G3", "upper", "body", 1, 80, 720, 200, 150, 50, "1N2B"),
            ("G4", "upper", "body", 1, 40, 720, 300, 100, 200, "1N2B"),
            ("I", "upper", "codend", 1, 30, 720, 133, 133, 250, "AN"),
            ("B", "lower", "wing_tip", 2, 200, 720, 3, 25, 22, "AB"),
            ("D", "lower", "wing", 2, 200, 720, 25, 50, 50, "1N2B / AB"),
            ("F", "lower", "belly", 1, 160, 720, 160, 130, 30, "1N2B"),
            ("H2", "lower", "body", 1, 120, 720, 173, 133, 40, "1N2B"),
            ("H3", "lower", "body", 1, 80, 720, 200, 150, 50, "1N2B"),
            ("H4", "lower", "body", 1, 40, 720, 300, 100, 200, "1N2B"),
            ("J", "lower", "codend", 1, 30, 720, 133, 133, 250, "AN"),
        ],
        "overrides": {
            "A": {
                "cut_code": (
                    "derived",
                    "el corte exterior de la punta de ala no se lee; 1N3B es el que da 3 → 38 "
                    "mallas en 22 filas con el costado AB",
                )
            },
            "B": {
                "cut_code": (
                    "derived",
                    "el corte exterior no se lee; 3 → 25 mallas en 22 filas es un costado AB y el "
                    "otro recto",
                )
            },
            "F": {
                "meshes_top": (
                    "transcribed",
                    "62 + 36 + 62 = 160: las alas de 50 mallas de 200 mm se cosen 4/5 a 62 de 160",
                )
            },
        },
        "hanging": {
            "upper": (
                0.43,
                "derived",
                "U1 de la bocana del dorso: 2,60 m de relinga sobre 30 mallas de 200 mm (0,43)",
            ),
            "lower": (
                0.32,
                "derived",
                "U1 de la bocana del vientre: 2,30 m de burlón sobre 36 mallas de 200 mm (0,32)",
            ),
            "default": (0.38, "assumed", "media de dorso y vientre"),
        },
        "headrope": _rope(25.40, 11.40, 2.60, "pp_14_retorcido_3_cordones", "PP Ø14"),
        "footrope": _rope(31.10, 14.40, 2.30, "pp_14_retorcido_3_cordones", "PP Ø14"),
        "floats": {
            "count": 13,
            "diameter_mm": 200,
            "note": "el plano da 32,5 kgf de flotación total; 13 boyas de 2,5 kgf (Ø200 supuesto)",
        },
        "ballast_kg": {"value": 40.8, "kind": "transcribed", "note": "lastre total del plano"},
        "design": {
            "depth_m": (30.0, "assumed", "el documento no da la profundidad; 30 m como WP/10"),
            "sweeps_m": (25.0, "transcribed", "patentes de 20,00–30,00 m PP Ø16: valor medio"),
            "door_length_m": (1.40, "transcribed", "portón plano de 1,40 × 0,70 m"),
            "door_height_m": (0.70, "transcribed", None),
            "door_weight_air_kg": (57.5, "transcribed", "55–60 kg: valor medio"),
        },
        "rigging": {
            "doors": "portón plano de 1,40 × 0,70 m, 55–60 kg",
            "sweeps": "20,00–30,00 m PP Ø16",
            "bridles": "superior 20,00 m PP Ø16; inferior 19,50 m PP Ø14",
        },
        "notes": [
            "Escaneo de 107 ppp: se leyó ampliando la imagen embebida del PDF.",
            "Todos los empalmes del cuerpo cierran: 127 × 200 ≈ 160 × 160; 130 × 160 ≈ 173 × 120; "
            "133 × 120 ≈ 200 × 80; 150 × 80 = 300 × 40; 100 × 40 ≈ 133 × 30.",
        ],
    },
    {
        "id": "bobp_wp20_pair_ho",
        "name": "Arrastre de pareja de gran abertura (BOBP/WP/20)",
        "description": (
            "Red de arrastre de fondo de gran abertura para dos barcos de 65–75 hp, con alas de "
            "200 mm, cuerpo de 160–40 mm y copo de 25 mm (Tamil Nadu, 1980–81)."
        ),
        "family": "bottom",
        "rig": "pair",
        "vessel_hp": (65, 75),
        "target_species": "peces de fondo y semipelágicos",
        "material": "PE",
        "twine_diameter": {720: 1.25},
        "source": {
            "key": "bobpwp20",
            "url": "https://www.fao.org/4/ad960e/ad960e00.pdf",
            "title": "BOBP/WP/20, apéndice 3: Two-boat high-opening bottom trawl",
            "figure": "Apéndice 3",
            "page": "26 del PDF ([21] del documento)",
        },
        "panels": [
            ("A", "upper", "wing_tip", 2, 200, 720, 10, 45, 20, "1N6B / AB"),
            ("C", "upper", "wing", 2, 200, 720, 45, 78, 45, "3N2B / AB"),
            ("E", "upper", "square", 1, 200, 720, 180, 165, 15, "1N2B"),
            ("G1", "upper", "body", 1, 160, 720, 240, 180, 60, "1N2B"),
            ("G2", "upper", "body", 1, 120, 720, 240, 186, 54, "1N2B"),
            ("G3", "upper", "body", 1, 80, 720, 280, 180, 100, "1N2B"),
            ("G4", "upper", "body", 1, 40, 720, 360, 100, 260, "1N2B"),
            ("I", "upper", "codend", 1, 25, 720, 160, 160, 300, "AN"),
            ("B", "lower", "wing_tip", 2, 200, 720, 10, 40, 20, "1N2B / AB"),
            ("D", "lower", "wing", 2, 200, 720, 40, 80, 60, "1N1B / AB"),
            ("F", "lower", "belly", 1, 160, 720, 240, 180, 60, "1N2B"),
            ("H2", "lower", "body", 1, 120, 720, 240, 186, 54, "1N2B"),
            ("H3", "lower", "body", 1, 80, 720, 280, 180, 100, "1N2B"),
            ("H4", "lower", "body", 1, 40, 720, 360, 100, 260, "1N2B"),
            ("J", "lower", "codend", 1, 25, 720, 160, 160, 300, "AN"),
        ],
        "overrides": {
            pid: {
                "cut_code": (
                    "derived",
                    "el corte de las alas no se lee en el escaneo; se toma el del apéndice 5 de "
                    "BOBP/WP/10 (mismas alas: 10 → 45 → 78 mallas del dorso, 10 → 40 → 80 del "
                    "vientre), que cierra con las mallas",
                )
            }
            for pid in ("A", "C", "B", "D")
        },
        "panel_notes": {
            "E": "El cielo cose 165 mallas de 200 mm con 240 de 160 mm (14 %), como en BOBP/WP/10.",
        },
        "hanging": {
            "upper": (
                0.46,
                "derived",
                "U1 de la bocana del dorso: 2,20 m de relinga sobre 24 mallas de 200 mm (0,46)",
            ),
            "lower": (
                0.38,
                "derived",
                "U1 de la bocana del vientre: 2,30 m de burlón sobre 30 mallas de 200 mm (0,38)",
            ),
            "default": (0.42, "assumed", "media de dorso y vientre"),
        },
        "headrope": _rope(28.20, 13.00, 2.20, "pp_16_retorcido_3_cordones", "PP Ø16"),
        "footrope": _rope(34.30, 16.00, 2.30, "pp_16_retorcido_3_cordones", "PP Ø16"),
        "floats": {
            "count": 15,
            "diameter_mm": 200,
            "note": "el plano da 37,5 kgf de flotación total; 15 boyas de 2,5 kgf (Ø200 supuesto)",
        },
        "design": {
            "depth_m": (30.0, "assumed", "el documento no da la profundidad; 30 m como WP/10"),
            "sweeps_m": (
                0.0,
                "assumed",
                "en la pareja las malletas van directo al cable; no hay patentes",
            ),
        },
        "notes": [
            "Escaneo de 107 ppp: se leyó ampliando la imagen embebida del PDF.",
            "Variante del apéndice 5 de BOBP/WP/10 con más filas en el cuerpo (60, 54, 100) y copo "
            "de 300 filas de 25 mm.",
        ],
    },
]

NETS_123: list[dict[str, Any]] = [*BOBP_NETS, *SCHARFE_NETS]
