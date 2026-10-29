"""Transcripciones de la Fase 20.2: redes de merluza del INIDEP y una red comercial.

Mismas convenciones que ``tools/catalog/transcriptions_198.py`` (filas ``(id, plane, section,
count, mesh_mm, rtex, top, bottom, depth, cut, material)``).

* **VA-35,5/45 diseñada** (Roth y García 2017, INIDEP IAT 101/2017, fig. 2, PDF p. 9): plano
  vectorial de cuatro caras con malleros, Ø del hilo de PE, mallas en altura, mallas de cada borde
  y cortes. El costado se dibuja en dos mitades (izquierda y derecha); aquí se suman.
* **VA-35,5/45 construida** (Bartozzetti 2018, INIDEP IAT 151/2018, fig. 1, PDF p. 2): la red tal
  como se armó y se midió en 52 lances (tabla 1, p. 5). Cambian las puntas de ala, el costado y el
  vientre (Ø4 mm); la columna de malleros del vientre no está impresa.
* **Engel 35,5 m** (IAT 101/2017, fig. 1, PDF p. 8): red de dos caras de las campañas de merluza.
  El plano no da el hilo ni el copo: se suponen y quedan A VERIFICAR.
* **Baldino «Beagle I» 46,4 m** (Roth 2019, INIDEP IAT 045/2019, figs. 2 y 3, PDF pp. 4–5): red
  comercial redibujada por el INIDEP (original, con secciones que no empalman) y la corregida; el
  plano da alturas en metros (fig. 2) y en mallas (fig. 3). Hilos del escaneo (fig. 1, p. 3).

Las mediciones de cada red (``measured``) y las simulaciones DynamiT (``simulated``) llevan la
profundidad, el cable filado, la velocidad y el portón de cada serie (``validation_doors``).
Las filas con media malla se redondean a la malla entera (``rows``).
"""

from __future__ import annotations

from typing import Any

from tools.catalog.transcriptions_195 import rows, rtex_from_runnage

ACCESSED_20 = "2026-10-28"
_URL = "https://marabiertonew.inidep.edu.ar/server/api/core/bitstreams/{}/content"

# --- Hilos ---------------------------------------------------------------------------------------
#: PE Ø3 mm: el hilo «3 mm PCU» de la tabla de materiales de ITO 043/2022 (235 m/kg).
R_PE3 = rtex_from_runnage(235.0)  # 4255
#: PE Ø4 y Ø5 mm: Rtex del de Ø3 mm escalado con d².
R_PE4 = round(R_PE3 * (4.0 / 3.0) ** 2)  # 7564
R_PE5 = round(R_PE3 * (5.0 / 3.0) ** 2)  # 11819
#: Hilo doble de PE Ø4 mm («4 D»): dos hilos de Ø4 mm.
R_PE4D = 2 * R_PE4  # 15128
#: Nylon Ø3 y Ø4 mm (copo de ITO 043/2022, 280 m/kg; Ø4 escalado con d²).
R_NY3 = rtex_from_runnage(280.0)  # 3571
R_NY4 = round(1.0e6 / 280.0 * (4.0 / 3.0) ** 2)  # 6349

_R_NOTE = {
    R_PE3: "Rtex = 10⁶ / 235 m/kg del hilo de PE de Ø3 mm («3 mm PCU») de ITO 043/2022",
    R_PE4: "Rtex = 4255 × (4/3)² (PE de Ø3 mm de ITO 043/2022 escalado con d²)",
    R_PE5: "Rtex = 4255 × (5/3)² (PE de Ø3 mm de ITO 043/2022 escalado con d²)",
    R_PE4D: "Rtex = 2 × 7564: hilo doble de PE de Ø4 mm (Ø4 escalado con d² del de Ø3 mm de ITO "
    "043/2022)",
    R_NY3: "Rtex = 10⁶ / 280 m/kg del nylon de Ø3 mm del copo de ITO 043/2022",
    R_NY4: "Rtex = 10⁶ / 280 × (4/3)² (nylon de Ø3 mm de ITO 043/2022 escalado con d²)",
}


def _merge(*dicts: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for d in dicts:
        for k, v in d.items():
            out.setdefault(k, {}).update(v)
    return out


def _twine(
    panels: list[tuple[Any, ...]], diameter: dict[str, tuple[str, str]]
) -> dict[str, dict[str, tuple[str, str]]]:
    """Procedencia del hilo de cada paño: ``diameter[pid] = (kind, nota del Ø)``."""
    out: dict[str, dict[str, tuple[str, str]]] = {}
    for row in panels:
        pid, rtex = row[0], row[5]
        d_kind, d_note = diameter[pid]
        r_kind = "assumed" if d_kind == "assumed" else "derived"
        out[pid] = {
            "twine_diameter_mm": (d_kind, d_note),
            "rtex": (r_kind, _R_NOTE[rtex] + ("" if r_kind == "derived" else ". A VERIFICAR")),
        }
    return out


def _half_rows(**notes: str) -> dict[str, dict[str, tuple[str, str]]]:
    return {pid: {"meshes_depth": ("derived", note)} for pid, note in notes.items()}


def _kind(pids: list[str], field: str, kind: str, note: str) -> dict[str, Any]:
    return {pid: {field: (kind, note)} for pid in pids}


# =================================================================================================
# Fuentes
# =================================================================================================
_IAT101 = {
    "key": "roth2017angelescu",
    "url": _URL.format("c4ca20ad-6497-4eba-8fbb-72b565bed12f"),
    "accessed": ACCESSED_20,
}
_IAT151 = {
    "key": "bartozzetti2018iat151",
    "url": _URL.format("95f5dd8e-1983-4b46-a704-e570c0ae738b"),
    "accessed": ACCESSED_20,
}
_IAT045 = {
    "key": "roth2019iat045",
    "url": _URL.format("d956d3a6-4d30-4eb2-9fa0-de33d3f3d743"),
    "accessed": ACCESSED_20,
}


def _src(key: str, title: str, url: str, page: str | None = None) -> dict[str, Any]:
    return {"key": key, "title": title, "url": url, "accessed": ACCESSED_20, "page": page}


SRC_IAT026 = _src(
    "roth2025iat026",
    "INIDEP IAT 026/25 (Roth y Rubio 2025): portones SPF, simulación DynamiT de la VA-35/45 a "
    "400 m",
    _URL.format("e97fb316-932c-47df-b33a-555c14ee26bc"),
    "3, 8",
)
SRC_IC029 = _src(
    "cabreira2018ic029",
    "INIDEP IC 029/2018 (Cabreira et al. 2018, VA-10/18): portones Morgère SPF08 con la VA-35,5/45",
    _URL.format("5a0b7861-44a1-4070-b18a-5a927add7760"),
    "4–5",
)
SRC_IC012 = _src(
    "roth2021ic012",
    "INIDEP IC 012/2021 (Roth 2021, VA-02/21): datos de puente de 40 lances con la VA-35/45",
    _URL.format("b93fefeb-ab3f-4d46-8c83-30857c6ef25a"),
    "3, 13–52",
)
SRC_IC016 = _src(
    "rubio2024calibracion",
    "INIDEP IC 016/24 (Rubio et al. 2024, VA-05/2024): lances 17–28 con la red Engel",
    _URL.format("e2f4cb3c-a0ef-4c8f-abde-e37ccfe506cb"),
    "11–13, 23, Anexo I (PDF pp. 32–33)",
)
SRC_EH0612 = _src(
    "tringali2012eh0612",
    "INIDEP, campaña EH 06/12 (Tringali et al. 2012): red Engel y portones del BIP Holmberg",
    _URL.format("84042f69-aa0c-4417-8ce0-578443812725"),
    "6",
)
SRC_IC004 = _src(
    "pappi2024ic004",
    "INIDEP IC 004/24 (Pappi et al. 2024, EH-2024/01): características de la red Engel",
    _URL.format("dc0d3fa2-a685-49e3-af8c-99ca566db44d"),
    "2–3",
)
SRC_IC041 = _src(
    "alvarezcolombo2025ic041",
    "INIDEP IC 041/25 (Álvarez Colombo et al. 2025, VA-2025/06): geometría media de la red Engel",
    _URL.format("9eece631-b43f-42b6-99b0-35b86e47508e"),
    "5–7",
)
SRC_IT66 = _src(
    "casarsa2007inftec66",
    "Casarsa y Madirolas (2007), INIDEP Inf. Téc. 66: red Engel con sonar de red (Oca Balda)",
    _URL.format("61ee3c64-300a-46a1-9c3b-2c7ba5284ea6"),
    "7 (tablas 1 y 2)",
)

# =================================================================================================
# Portones de cada serie (claves de design; ver trawlkit.catalog.door_from_params)
# =================================================================================================
_AR05 = (
    "la fuente da la superficie pero no las medidas: proporción alto/largo 0,5 del portón plano "
    "genérico (como ITO 043/2022). A VERIFICAR"
)
#: Polar de un polivalente: la hoja «Morgère Polyvalent Ovale» de Seafish (1993).
_POLY_NOTE = (
    "el INIDEP no publica la polar de sus portones polivalentes: hoja «Morgère Polyvalent Ovale» "
    "de Seafish/IFREMER/DIFTA (1993), el mismo tipo. A VERIFICAR"
)
VALIDATION_DOORS: dict[str, dict[str, Any]] = {
    "spf08_iat101": {
        "label": "Morgère SPF08, 4,5 m², 1200 kg, CL 1,00 / CD 0,58 (IAT 101/17)",
        "door_area_m2": 4.5,
        "door_length_m": 3.0,
        "door_height_m": 1.5,
        "door_weight_air_kg": 1200.0,
        "door_cl": 1.00,
        "door_cd": 0.58,
        "note": "«Portones: Super v Morgere (modelo SPF08) de 4,5 m2 y 1200 kg de peso (CL = 1,00; "
        "CD = 0,58)» (IAT 101/2017, p. 4). Largo y alto: " + _AR05,
    },
    "spf08_1000": {
        "label": "Morgère SPF08, 4,68 m², 1000 kg (IC 029/18, IC 012/21)",
        "door_area_m2": 4.68,
        "door_length_m": 3.06,
        "door_height_m": 1.53,
        "door_weight_air_kg": 1000.0,
        "door_cl": 1.00,
        "door_cd": 0.58,
        "note": "«modelo SPF08, con un peso individual de 1000 kg y un área total de 4.68 m2» "
        "(IC 029/2018, p. 4; IC 012/2021, p. 3). CL y CD: los del SPF08 de IAT 101/2017 (supuesto, "
        "A VERIFICAR). Largo y alto: " + _AR05,
    },
    "spf085_ic016": {
        "label": "Morgère SPF 08,5, 4,8 m², 1200 kg, CL 0,92 / CD 0,40 (IC 016/24)",
        "door_area_m2": 4.8,
        "door_length_m": 3.10,
        "door_height_m": 1.55,
        "door_weight_air_kg": 1200.0,
        "door_cl": 0.92,
        "door_cd": 0.40,
        "note": "«Morgère SPF 08,5 de 1200 kg de peso y 4,8 m2 de área» (IC 016/24, p. 2). CL y "
        "CD: «Con el menor ángulo de ataque de los portones utilizado en la campaña VA-2024/05 […] "
        "CD = 0,4 y CL = 0,92» (IAT 026/25, p. 3); los enganches cambiaron entre lances (IC "
        "016/24, pp. 11–13). Largo y alto: " + _AR05,
    },
    "spf085_iat026": {
        "label": "Morgère SPF 08,5, 4,9 m², 1200 kg, CL 0,92 / CD 0,40 (IAT 026/25)",
        "door_area_m2": 4.9,
        "door_length_m": 3.13,
        "door_height_m": 1.57,
        "door_weight_air_kg": 1200.0,
        "door_cl": 0.92,
        "door_cd": 0.40,
        "note": "«portones hidrodinámicos Morgère SPF 08,5 de 1200 kg de peso y 4,9 m2 de área» y "
        "«CD = 0,4 y CL = 0,92» (IAT 026/25, pp. 2–3; IC 016/24 da 4,8 m²). Largo y alto: " + _AR05,
    },
    "polivalente_1200": {
        "label": "polivalente, 5,58 m², 1200 kg (EH 06/12), polar Morgère Polyvalent Ovale",
        "door_area_m2": 5.58,
        "door_length_m": 3.20,
        "door_height_m": 2.18,
        "door_weight_air_kg": 1200.0,
        "door_polar_id": "sfia1993_morgere_polyvalent_ovale",
        "note": "«portones polivalentes de 1200 kg y 5,58 m2 de superficie» (EH 06/12, p. 6; las "
        "demás fuentes dan sólo «polivalentes de 1200 kg»). Polar: "
        + _POLY_NOTE
        + ". Largo y alto: L·H·0,80 = 5,58 m² con H/L = 0,68 (proporciones de la hoja de Seafish), "
        "supuesto",
    },
    "polivalente_1260": {
        "label": "polivalente, 1260 kg (Inf. Téc. 66), 5,58 m² supuestos",
        "door_area_m2": 5.58,
        "door_length_m": 3.20,
        "door_height_m": 2.18,
        "door_weight_air_kg": 1260.0,
        "door_polar_id": "sfia1993_morgere_polyvalent_ovale",
        "note": "«Polivalentes 1.260 kg» (Inf. Téc. 66, tabla 1); superficie: la de los "
        "polivalentes de 1200 kg de EH 06/12 (supuesto). Polar: " + _POLY_NOTE,
    },
    "mercury_2300": {
        "label": "Polar Mercury 2,0r de 2300 kg (7,5 m² por la tabla de Polar)",
        "door_id": "door_polar_mercury20r_7_5m2",
        "note": "«portones con toberas modelo Mercury de 2300 kg de peso en el aire» (IAT 045/19, "
        "p. 2); la superficie no se publica: el tamaño de 2300 kg de la tabla «Size & Weight» de "
        "Polar es el de 7,5 m² (derivado, A VERIFICAR)",
    },
}


def _door_design(key: str, doc: str) -> dict[str, tuple[Any, str, str, str]]:
    """Claves de ``design`` del portón ``key`` de :data:`VALIDATION_DOORS` con su procedencia."""
    d = VALIDATION_DOORS[key]
    note = d["note"]
    out: dict[str, tuple[Any, str, str, str]] = {}
    for k in ("door_area_m2", "door_weight_air_kg", "door_cl", "door_cd"):
        if k in d:
            out[k] = (d[k], "transcribed", note, doc)
    for k in ("door_length_m", "door_height_m", "door_polar_id"):
        if k in d:
            out[k] = (d[k], "assumed", note, doc)
    return out


# =================================================================================================
# VA-35,5/45 diseñada (IAT 101/2017, fig. 2)
# =================================================================================================
_SOURCE_101_2 = {
    **_IAT101,
    "title": "INIDEP IAT 101/17 (Roth y García 2017), fig. 2: plano definitivo de la red "
    "VA-35,5/45 diseñada para el BIP Víctor Angelescu",
    "figure": "Figura 2",
    "page": "9",
}
VA_DESIGN_PANELS = [
    ("UW1", "upper", "wing", 2, 300, R_PE3, 2, 20, rows(35.5), "1N2B / AB", "PE"),
    ("UW2", "upper", "wing", 2, 300, R_PE3, 20, 45, 10, "1N2B / 1T1B", "PE"),
    ("U1", "upper", "body", 1, 300, R_PE3, 122, 102, 20, "1N2B", "PE"),
    ("U2", "upper", "body", 1, 200, R_PE3, 154, 128, 26, "1N2B", "PE"),
    ("U3", "upper", "body", 1, 160, R_PE3, 160, 126, 34, "1N2B", "PE"),
    ("U4", "upper", "body", 1, 140, R_PE3, 144, 108, 36, "1N2B", "PE"),
    ("U5", "upper", "body", 1, 120, R_PE3, 126, 79, 47, "1N2B", "PE"),
    ("UC", "upper", "codend", 1, 110, R_PE5, 86, 86, 200, "AN", "PE"),
    ("LW1", "lower", "wing", 2, 300, R_PE3, 2, 26, 60, "1N3B / AB", "PE"),
    ("LW2", "lower", "wing", 2, 200, R_PE3, 39, 54, 10, "1N2B / 1T2B", "PE"),
    ("L1", "lower", "body", 1, 200, R_PE3, 154, 128, 26, "1N2B", "PE"),
    ("L2", "lower", "body", 1, 160, R_PE3, 160, 126, 34, "1N2B", "PE"),
    ("L3", "lower", "body", 1, 140, R_PE3, 144, 108, 36, "1N2B", "PE"),
    ("L4", "lower", "body", 1, 120, R_PE3, 126, 79, 47, "1N2B", "PE"),
    ("LC", "lower", "codend", 1, 110, R_PE5, 86, 86, 200, "AN", "PE"),
    ("S1", "side", "body", 2, 300, R_PE3, 38, 33, 20, None, "PE"),
    ("S2", "side", "body", 2, 200, R_PE3, 52, 44, 26, "2N1B / 5N2B", "PE"),
    ("S3", "side", "body", 2, 160, R_PE3, 55, 37, 34, "2N1B / 1N1B", "PE"),
    ("S4", "side", "body", 2, 140, R_PE3, 42, 23, 36, "2N1B / 1N1B", "PE"),
    ("S5", "side", "body", 2, 120, R_PE3, 26, 2, 47, "2N1B / 1N1B", "PE"),
]
_D3_101 = ("transcribed", "columna «Material PE (Ø mm)»: 3 (fig. 2)")
_D5_101 = ("transcribed", "columna «Material PE (Ø mm)»: 5 en el copo (fig. 2)")
_SIDE_HALVES = (
    "El plano dibuja el costado en dos mitades: se suman las mallas de las dos ({left} + {right})."
)
_SIDE_101 = {
    "S2": ("22 + 30", "17 + 27"),
    "S3": ("21 + 34", "14 + 23"),
    "S4": ("16 + 26", "9 + 14"),
    "S5": ("10 + 16", "1 + 1"),
}
#: El tramo del costado junto a las alas no se modela (como en ITO 043/2022).
_SIDE_FRONT = (
    " El tramo delantero del costado, junto a las alas ({front}), no se modela: su alto iguala "
    "el de las alas del dorso ({wing}), como en ITO 043/2022."
)
_CUT_SIDE_101 = (
    "derived",
    "la mitad derecha rotula su corte (5N2B o 1N1B); el de la mitad izquierda se rotula «2N1B» "
    "una vez en todo el costado",
)

VA_DESIGN: dict[str, Any] = {
    "id": "inidep_iat101_va355_disenada",
    "name": "Red de fondo VA-35,5/45 del INIDEP, diseñada (IAT 101/2017, fig. 2)",
    "description": (
        "Red de arrastre de fondo de cuatro caras diseñada por el INIDEP para las campañas de "
        "merluza del BIP Víctor Angelescu: alas y cielo de 300 mm, cuerpo de 200 a 120 mm en PE de "
        "3 mm y copo de 110 mm en PE de 5 mm; lima de 35,5 m y burlón de 45,0 m (Roth y García "
        "2017). DynamiT: DP 89,2 m, AH 23,0 m y AV 3,7 m a 4 nudos, 100 m y 500 m de cable."
    ),
    "family": "bottom",
    "rig": "otter",
    "vessel_hp": (2855.2, 2855.2),
    "target_species": "merluza común (Merluccius hubbsi)",
    "species": {"name": "Merluza", "scientific_name": "Merluccius hubbsi"},
    "source": _SOURCE_101_2,
    "material": "PE",
    "twine_diameter": {R_PE3: 3.0, R_PE5: 5.0},
    "panels": VA_DESIGN_PANELS,
    "panel_notes": {
        **{
            pid: _SIDE_HALVES.format(left=f"boca {a}", right=f"bolsa {b}")
            for pid, (a, b) in _SIDE_101.items()
        },
        "S1": _SIDE_HALVES.format(left="boca 18 + 20", right="bolsa 13 + 20")
        + " El corte de la mitad izquierda (18 → 13 mallas en 20 filas) no está rotulado."
        + _SIDE_FRONT.format(
            front="300 mm, 1 + 3 → 18 + 20 mallas en 25,5 filas y 20 filas rectas",
            wing="35,5 + 10 filas",
        ),
        "UW2": "Pie del ala: 20 → 45 mallas en 10 filas; el borde de la relinga se corta 1T1B y "
        "lleva los 4,75 m de lima.",
        "LW2": "El ala inferior cambia de 300 a 200 mm en la línea de 26/39 mallas (7,80 m en las "
        "dos).",
    },
    "overrides": _merge(
        _twine(
            VA_DESIGN_PANELS,
            {r[0]: (_D5_101 if r[2] == "codend" else _D3_101) for r in VA_DESIGN_PANELS},
        ),
        _half_rows(UW1="35,5 filas redondeadas a 36"),
        _kind(["S2", "S3", "S4", "S5"], "cut_code", *_CUT_SIDE_101),
    ),
    "hanging": {
        "upper": (
            0.42,
            "derived",
            "U1 de la bocana del dorso: 4 m de lima sobre 122 − 2 × 45 = 32 mallas de 300 mm "
            "(9,60 m): 4 / 9,60 = 0,42; se usa en todo el dorso",
        ),
        "lower": (
            0.43,
            "derived",
            "U1 de la bocana del vientre: 4 m sobre 154 − 2 × 54 = 46 mallas de 200 mm (9,20 m): "
            "0,43; se usa en todo el vientre",
        ),
        "side": (0.43, "assumed", "el plano no da U1 del costado: el del vientre"),
    },
    "headrope": {
        "length_m": 35.5,
        "wing_m": 15.75,
        "bosom_m": 4.0,
        "material": "lima del plano (material y diámetro no publicados: los del motor)",
        "pieces": {
            "wing_m": ("transcribed", "11 + 4,75 m por ala (fig. 2; «hA = 15,75 m», p. 3)"),
            "bosom_m": ("transcribed", "«un centro de 4 m» (p. 3) y 4 m en la fig. 2"),
        },
    },
    "footrope": {
        "length_m": 45.0,
        "wing_m": 20.5,
        "bosom_m": 4.0,
        "material": "burlón del plano (material y diámetro no publicados: los del motor)",
        "pieces": {
            "wing_m": ("transcribed", "18 + 2,5 m por ala (fig. 2)"),
            "bosom_m": ("transcribed", "centro de 4 m (fig. 2)"),
        },
    },
    "floats": {
        "count": 90,
        "diameter_mm": 200,
        "kind": "assumed",
        "note": "IAT 101/2017 no da la flotación: la de la red construida, «una flotación de 90 "
        "boyas de 200 m[m] de diámetro» (IAT 151/2018, p. 2). A VERIFICAR",
    },
    "ballast_kg": {
        "value": 380.0,
        "kind": "assumed",
        "note": "IAT 101/2017 no da el lastre: el de la red construida, «un peso de 380 kg de "
        "cadena de alta resistencia» (IAT 151/2018, p. 2). A VERIFICAR",
    },
    "design": {
        "vessel_id": (
            "bipo_victor_angelescu",
            "transcribed",
            "«red de arrastre de fondo destinada al BIP Dr. Víctor Angelescu» (título, p. 1); "
            "«dos motores eléctricos de 1050 kW» (p. 4)",
        ),
        "depth_m": (100.0, "transcribed", "«Profundidad de pesca: 100 m» (simulación, p. 4)"),
        "sweeps_m": (50.0, "transcribed", "«Patentes: 50 m» (simulación, p. 4)"),
        "bridle_upper_m": (50.0, "transcribed", "«Bridas: 50 m» (simulación, p. 4)"),
        "speed_kn": (4.0, "transcribed", "«Velocidad de arrastre: 4 nudos» (p. 4)"),
        "warp_m": (500.0, "transcribed", "«Cable de arrastre: 500 m» (p. 4)"),
        **{k: v[:3] for k, v in _door_design("spf08_iat101", "roth2017angelescu").items()},
    },
    "validation_doors": {"spf08_iat101": VALIDATION_DOORS["spf08_iat101"]},
    "simulated": [
        {
            "speed_kn": 4.0,
            "depth_m": 100.0,
            "warp_m": 500.0,
            "sweeps_m": 50.0,
            "door": "spf08_iat101",
            "door_spread_m": 89.2,
            "horizontal_opening_m": 23.0,
            "vertical_opening_m": 3.7,
            "drag_kgf": 6243.47,
            "source": "roth2017angelescu",
            "note": "resultados de DynamiT del INIDEP (p. 6): «Resistencia total al avance (kg) "
            "6.243,47 / Abertura vertical (m) 3,7 / Abertura horizontal (m) 23,0 / Distancia entre "
            "portones (m) 89,2»; modelo, no mediciones",
        }
    ],
    "rigging": {
        "doors": "Morgère SPF08 de 4,5 m² y 1200 kg (CL 1,00; CD 0,58)",
        "bridle": "bridas de 50 m",
        "sweeps": "patentes de 50 m (simulación); 100 m en la red construida (IAT 151/2018)",
        "warp": "500 m (simulación)",
    },
    "notes": [
        "Aparejo de la simulación DynamiT (p. 4): 4 nudos, 100 m, 500 m de cable, portones Morgère "
        "SPF08 de 4,5 m² y 1200 kg (CL 1,00; CD 0,58), bridas de 50 m y patentes de 50 m. Buque: "
        "BIP Víctor Angelescu, dos motores eléctricos de 1050 kW.",
        "Los empalmes cierran por largo estirado (102 × 300 = 154 × 200 mm, etc.): diseño por "
        "proporciones de Martini (2006), p. 3.",
        "Relingas: el plano no da material ni diámetro; el motor usa los cabos del libro.",
        "Flotación y lastre: los de la red construida (IAT 151/2018), A VERIFICAR.",
    ],
    "status": "published",
}

# =================================================================================================
# VA-35,5/45 construida (IAT 151/2018, fig. 1) y sus mediciones
# =================================================================================================
_SOURCE_151_1 = {
    **_IAT151,
    "title": "INIDEP IAT 151/18 (Bartozzetti 2018), fig. 1: plano de la red VA-35,5/45 utilizada "
    "en el BIP Víctor Angelescu",
    "figure": "Figura 1",
    "page": "2",
}
VA_BUILT_PANELS = [
    ("UW1", "upper", "wing", 2, 300, R_PE3, 12, 32, rows(35.5), "1N2B / AB", "PE"),
    ("UW2", "upper", "wing", 2, 300, R_PE3, 32, 47, 10, "1N2B / 1T2B", "PE"),
    ("U1", "upper", "body", 1, 300, R_PE3, 126, 106, 20, "1N2B", "PE"),
    ("U2", "upper", "body", 1, 200, R_PE3, 159, 133, 26, "1N2B", "PE"),
    ("U3", "upper", "body", 1, 160, R_PE3, 166, 132, 34, "1N2B", "PE"),
    ("U4", "upper", "body", 1, 140, R_PE3, 151, 115, 36, "1N2B", "PE"),
    ("U5", "upper", "body", 1, 120, R_PE3, 134, 79, 47, "1N2B", "PE"),
    ("UC", "upper", "codend", 1, 110, R_PE4D, 86, 86, 200, "AN", "PE"),
    ("LW1", "lower", "wing", 2, 300, R_PE4, 9, 31, rows(55.5), "1N3B / AB", "PE"),
    ("LW2", "lower", "wing", 2, 300, R_PE4, 31, 40, 10, "1N2B / 1T4B", "PE"),
    ("L1", "lower", "body", 1, 200, R_PE4, 154, 128, 26, "1N2B", "PE"),
    ("L2", "lower", "body", 1, 160, R_PE4, 160, 126, 34, "1N2B", "PE"),
    ("L3", "lower", "body", 1, 140, R_PE4, 144, 108, 36, "1N2B", "PE"),
    ("L4", "lower", "body", 1, 120, R_PE4, 126, 79, 47, "1N2B", "PE"),
    ("LC", "lower", "codend", 1, 110, R_PE4D, 86, 86, 200, "AN", "PE"),
    ("S1", "side", "body", 2, 300, R_PE3, 46, 41, 20, None, "PE"),
    ("S2", "side", "body", 2, 200, R_PE3, 61, 53, 26, "5N2B", "PE"),
    ("S3", "side", "body", 2, 160, R_PE3, 66, 47, 34, "1N1B / 2N1B", "PE"),
    ("S4", "side", "body", 2, 140, R_PE3, 54, 35, 36, "1N1B / 2N1B", "PE"),
    ("S5", "side", "body", 2, 120, R_PE3, 41, 2, 47, "1N1B / 2N1B", "PE"),
]
_D3_151 = ("transcribed", "columna «Material PE (Ø mm)»: 3 (fig. 1)")
_D4_151 = ("transcribed", "columna «Material PE (Ø mm)» del vientre: 4 (fig. 1)")
_D4D_151 = (
    "transcribed",
    "«4D» en el copo (fig. 1): hilo doble de Ø4 mm; el motor toma Ø4 mm y el Rtex de los dos hilos",
)
_MESH_LOWER_151 = (
    "assumed",
    "la fig. 1 no imprime la columna de malleros del vientre: 300 mm en las alas (55,5 + 10 = 65,5 "
    "filas, como las 65,5 filas de 300 mm del dorso y del costado, y 31 mallas a los dos lados de "
    "la línea de 55,5 filas) y 200–110 mm en el cuerpo como el dorso y la fig. 2 de IAT 101/2017. "
    "A VERIFICAR",
)
_CUT_SIDE_151 = (
    "derived",
    "la fig. 1 rotula 1N1B en un borde; el otro borde (2N1B) es el de la fig. 2 de IAT 101/2017 y "
    "da el cambio de ancho del paño",
)


def _va151_hauls() -> list[dict[str, Any]]:
    """IAT 151/2018, tabla 1 (p. 5): lance, profundidad, cable filado, DP y AV."""
    table = [
        (1, 90, 400, 99, 3.5),
        (2, 93, 450, 101, 3.5),
        (3, 92, 450, 95, 3.5),
        (4, 90, 430, 100, 3.4),
        (5, 81, 350, 93, 3.4),
        (6, 80, 350, 95, 3.8),
        (7, 68, 320, 97, 3.8),
        (8, 79, 350, 98, 3.6),
        (9, 78, 350, 95, 3.4),
        (10, 90, 350, 95, 3.3),
        (11, 84, 380, 94, 3.4),
        (12, 78, 350, 93, 3.6),
        (13, 82, 350, 95, 3.6),
        (14, 62, 300, 90, 3.3),
        (15, 85, 380, 98, 3.4),
        (16, 79, 350, 94, 3.4),
        (17, 82, 380, 97, 3.7),
        (18, 60, 250, 87, 3.8),
        (19, 35, 180, 79, 4.9),
        (20, 85, 380, 103, 3.4),
        (21, 83, 380, 101, 3.9),
        (22, 73, 350, 97, 3.3),
        (23, 40, 250, 89, 4.2),
        (24, 39, 250, 91, 3.7),
        (25, 70, 350, 101, 3.6),
        (26, 78, 350, 97, 3.9),
        (27, 79, 350, 101, 3.7),
        (28, 55, 250, 88, 3.8),
        (29, 27, 200, 80, 4.0),
        (30, 27, 200, 78, 4.3),
        (31, 50, 250, 89, 3.7),
        (32, 79, 380, 102, 3.5),
        (33, 85, 380, 101, 3.7),
        (34, 82, 380, 95, 3.8),
        (35, 76, 350, 96, 3.7),
        (36, 53, 250, 88, 4.1),
        (37, 28, 180, 75, 4.1),
        (38, 26, 200, 81, 3.7),
        (39, 42, 250, 89, 3.8),
        (40, 57, 300, 93, 3.9),
        (41, 74, 350, 97, 3.1),
        (42, 60, 300, 93, 3.5),
        (43, 52, 250, 91, 3.8),
        (44, 30, 200, 81, 4.0),
        (45, 32, 200, 86, 3.8),
        (46, 50, 250, 93, 3.6),
        (47, 30, 200, 82, 4.3),
        (48, 27, 180, 79, 4.3),
        (49, 38, 200, 91, 3.9),
        (51, 68, 330, 102, 3.5),
        (52, 51, 250, 94, 3.4),
        (54, 28, 180, 76, 3.9),
    ]
    return [
        {
            "series": "iat151",
            "source": "bartozzetti2018iat151",
            "haul": n,
            "depth_m": float(d),
            "warp_m": float(w),
            "speed_kn": 3.8,
            "door": "polivalente_1200",
            "door_spread_m": float(dp),
            "vertical_opening_m": av,
            "note": "tabla 1 (p. 5), Simrad TV-80; velocidad: la media de la campaña («a una "
            "velocidad de 3,8 Ns», p. 1), la tabla no la da por lance",
        }
        for n, d, w, dp, av in table
    ]


def _ic029_hauls() -> list[dict[str, Any]]:
    """IC 029/2018, tabla 1 (p. 5): portones SPF08 de 1000 kg y 4,68 m²."""
    return [
        {
            "series": "ic029",
            "source": "cabreira2018ic029",
            "haul": n,
            "depth_m": float(d),
            "warp_m": float(w),
            "speed_kn": v,
            "door": "spf08_1000",
            "door_spread_m": float(dp),
            "vertical_opening_m": av,
            "note": "tabla 1 (p. 5), sensores Simrad PX / TV80",
        }
        for n, d, w, dp, av, v in (
            (5, 120, 500, 129, 2.73, 3.9),
            (6, 140, 600, 142, 2.65, 4.0),
            (7, 317, 930, 158, 2.45, 4.0),
        )
    ]


def _ic012_hauls() -> list[dict[str, Any]]:
    """IC 012/2021, anexo II (PDF pp. 13–52): datos de puente de los 40 lances."""
    # lance, prof. inicial, prof. final, velocidad, AV, DP, cable filado
    table = [
        (1, 82, 81, 4.1, 4.2, 90, 300),
        (2, 81, 85, 4.0, 4.2, 88, 300),
        (3, 68, 67, 4.03, 3.3, 78.1, 240),
        (4, 63, 64, 3.84, 2.9, 82.1, 300),
        (5, 68, 68, 3.97, 2.8, 80.8, 240),
        (6, 64, 71, 4.02, 3.6, 75.6, 250),
        (7, 106, 108, 3.84, 3.8, 102.4, 360),
        (8, 108, 109, 4.02, 3.7, 89.7, 363),
        (9, 126, 131, 3.93, 2.8, 89.6, 400),
        (10, 133, 128, 3.86, 2.7, 78.5, 435),
        (11, 125, 129, 3.85, 2.3, 93.6, 400),
        (12, 130, 133, 3.9, 3.1, 91.6, 413),
        (13, 135, 132, 4.0, 2.3, 96.7, 420),
        (14, 133, 137, 4.0, 2.8, 90.3, 420),
        (15, 135, 133, 3.69, 3.3, 90.1, 440),
        (16, 134, 132, 3.87, 2.9, 92.7, 420),
        (17, 145, 149, 3.91, 2.9, 98.4, 445),
        (18, 131, 135, 3.8, 2.8, 93.8, 400),
        (19, 129, 134, 3.9, 3.1, 91, 400),
        (20, 129, 131, 3.98, 3.1, 87.2, 400),
        (21, 131, 135, 3.86, 3.1, 87.7, 400),
        (22, 146, 142, 3.97, 2.7, 94.8, 450),
        (23, 139, 142, 4.03, 3.4, 98, 456),
        (24, 131, 133, 3.91, 3.2, 88.8, 400),
        (25, 151, 144, 3.67, 3.3, 93.3, 470),
        (26, 147, 141, 3.97, 2.8, 96.5, 461),
        (27, 152, 161, 3.94, 2.9, 97.9, 450),
        (28, 140, 141, 3.87, 3.1, 86.6, 430),
        (29, 141, 154, 4.07, 2.7, 97, 445),
        (30, 148, 148, 3.9, 2.7, 102.6, 451),
        (31, 108, 108, 3.91, 3.0, 81.9, 340),
        (32, 129, 119, 4.09, 2.8, 99, 407),
        (33, 107, 106, 3.8, 3.2, 84.7, 330),
        (34, 104, 105, 3.8, 3.3, 89.2, 330),
        (35, 107, 108, 3.93, 3.3, 86.3, 330),
        (36, 103, 103, 3.87, 2.8, 94.3, 330),
        (37, 118, 119, 3.7, 2.9, 92.6, 365),
        (38, 104, 104, 4.04, 3.6, 84.9, 320),
        (39, 89, 90, 3.92, 3.7, 79.7, 280),
        (40, 83, 83, 3.82, 3.1, 76.3, 263),
    ]
    return [
        {
            "series": "ic012",
            "source": "roth2021ic012",
            "haul": n,
            "depth_m": round(0.5 * (d0 + d1), 1),
            "warp_m": float(w),
            "speed_kn": v,
            "door": "spf08_1000",
            "door_spread_m": float(dp),
            "vertical_opening_m": av,
            "note": "anexo II: «Vel Arrastre», «Prof INI»/«Prof FIn» (se usa la media), «Abertura "
            "Vert», «Dist e/Port» y «Cable Filado»; los lances llevan dispositivos de selectividad "
            "(malla cuadrada, T90, grilla), que pueden cambiar algo la resistencia",
        }
        for n, d0, d1, v, av, dp, w in table
    ]


VA_BUILT: dict[str, Any] = {
    **VA_DESIGN,
    "id": "inidep_iat151_va355_construida",
    "name": "Red de fondo VA-35,5/45 del INIDEP, construida (IAT 151/2018, fig. 1)",
    "description": (
        "La red VA-35,5/45 tal como se construyó y se midió a bordo del BIP Víctor Angelescu en "
        "2018: alas de 300 mm, dorso y costados en PE de 3 mm, vientre en PE de 4 mm y copo de "
        "110 mm en hilo doble de 4 mm; 90 boyas de 200 mm y 380 kg de cadena (Bartozzetti 2018). "
        "Lleva 95 lances medidos con tres juegos de portones y una simulación DynamiT a 400 m."
    ),
    "source": _SOURCE_151_1,
    "extra_sources": [
        {
            **_IAT101,
            "title": "INIDEP IAT 101/17 (Roth y García 2017): diseño de la red",
            "page": "4",
        },
        SRC_IAT026,
        SRC_IC029,
        SRC_IC012,
        SRC_EH0612,
    ],
    "twine_diameter": {R_PE3: 3.0, R_PE4: 4.0, R_PE4D: 4.0},
    "panels": VA_BUILT_PANELS,
    "panel_notes": {
        "S1": "El corte de 46 → 41 mallas en 20 filas no está rotulado."
        + _SIDE_FRONT.format(
            front="dos cuñas de 6 → 23 mallas de 300 mm en 25,5 filas y 46 mallas en 20 filas",
            wing="35,5 + 10 filas",
        ),
        "S5": "La fig. 1 da 41 → 2 mallas en 47 filas (la fig. 2 de IAT 101/2017, 26 → 2): el "
        "corte 1N1B/2N1B daría 25 mallas. Se transcribe como se lee: A VERIFICAR.",
        "U5": "La fig. 1 da 134 → 79 mallas en 47 filas (55 mallas; 1N2B daría 47). Se transcribe "
        "como se lee: A VERIFICAR.",
        "LW2": "Mismo mallero arriba y abajo de la línea de 55,5 filas (31 / 31 mallas); 31 → 40 "
        "mallas en 10 filas con el borde de la relinga en 1T4B.",
        "UC": "Copo de 110 mm en hilo doble de PE de 4 mm («4D»).",
    },
    "overrides": _merge(
        _twine(
            VA_BUILT_PANELS,
            {
                r[0]: (_D4D_151 if r[2] == "codend" else _D4_151 if r[1] == "lower" else _D3_151)
                for r in VA_BUILT_PANELS
            },
        ),
        _half_rows(
            UW1="35,5 filas redondeadas a 36",
            LW1="55,5 filas redondeadas a 56",
        ),
        _kind(["LW1", "LW2", "L1", "L2", "L3", "L4", "LC"], "mesh_mm", *_MESH_LOWER_151),
        _kind(["S3", "S4", "S5"], "cut_code", *_CUT_SIDE_151),
    ),
    "hanging": {
        "upper": (
            0.42,
            "derived",
            "U1 de la bocana del dorso: 4 m de lima sobre 126 − 2 × 47 = 32 mallas de 300 mm (el "
            "plano rotula «32»; 9,60 m): 0,42; se usa en todo el dorso",
        ),
        "lower": (
            0.59,
            "derived",
            "U1 de la bocana del vientre: 4 m sobre 154 × 0,20 − 2 × 40 × 0,30 = 6,80 m (con alas "
            "de 300 mm, supuestas): 0,59; se usa en todo el vientre. A VERIFICAR",
        ),
        "side": (0.50, "assumed", "el plano no da U1 del costado: promedio del dorso y el vientre"),
    },
    "headrope": {
        **VA_DESIGN["headrope"],
        "pieces": {
            "wing_m": ("transcribed", "11 + 4,75 m por ala (fig. 1)"),
            "bosom_m": ("transcribed", "centro de 4 m (fig. 1)"),
        },
    },
    "footrope": {
        **VA_DESIGN["footrope"],
        "wing_m": 20.5,
        "pieces": {
            "wing_m": ("transcribed", "17 + 3,5 m por ala (fig. 1)"),
            "bosom_m": ("transcribed", "centro de 4 m (fig. 1)"),
        },
    },
    "floats": {
        "count": 90,
        "diameter_mm": 200,
        "kind": "transcribed",
        "note": "«una flotación de 90 boyas de 200 m[m] de diámetro» (p. 2); a partir del lance 1 "
        "se agregaron 10 (100 en total, p. 3)",
    },
    "ballast_kg": {
        "value": 380.0,
        "kind": "transcribed",
        "note": "«un peso de 380 kg de cadena de alta resistencia» (p. 2)",
    },
    "design": {
        "vessel_id": (
            "bipo_victor_angelescu",
            "transcribed",
            "«redes de arrastre de fondo para ser utilizadas en el BIP Víctor Angelescu» (título)",
        ),
        "depth_m": (
            62.7,
            "derived",
            "media de las profundidades de los 52 lances de la tabla 1 (26–93 m, p. 5)",
        ),
        "sweeps_m": (
            100.0,
            "transcribed",
            "«Patentes de 100 m de longitud en cable de acero de 20 mm de diámetro» (p. 3)",
        ),
        "bridle_upper_m": (
            50.0,
            "transcribed",
            "«Bridas superiores de 50 m en cable de acero de 18 mm de diámetro» (p. 3); en el "
            "lance 6 se alargó a 50,7 m (p. 4)",
        ),
        "bridle_lower_m": (
            48.5,
            "transcribed",
            "«Bridas inferiores de 48,5 m en cable de acero de 20 mm de diámetro y 1,5 m de "
            "cadena de reglaje» (p. 3)",
        ),
        "speed_kn": (3.8, "transcribed", "«a una velocidad de 3,8 Ns» (media, p. 1)"),
        "door_weight_air_kg": (
            1200.0,
            "transcribed",
            "«Portones polivalentes (Morgère) de 1200 kg c/u» (p. 3)",
        ),
        **{
            k: (v[0], "assumed", v[2], v[3])
            for k, v in _door_design("polivalente_1200", "tringali2012eh0612").items()
            if k != "door_weight_air_kg"
        },
    },
    "validation_doors": {
        k: VALIDATION_DOORS[k] for k in ("polivalente_1200", "spf08_1000", "spf085_iat026")
    },
    "measured": _va151_hauls() + _ic029_hauls() + _ic012_hauls(),
    "simulated": [
        {
            "speed_kn": 4.0,
            "depth_m": 400.0,
            "warp_m": 1200.0,
            "sweeps_m": 100.0,
            "door": "spf085_iat026",
            "door_spread_m": 162.3,
            "horizontal_opening_m": 28.4,
            "vertical_opening_m": 2.4,
            "drag_kgf": 9175.828,
            "source": "roth2025iat026",
            "note": "DynamiT del INIDEP, tabla 1 (p. 8), portones de 1200 kg: «1200 2,4 28,4 "
            "162,3 9175,828 105»; 4 nudos, 400 m y 1200 m de cable (p. 6). Las patentes de 100 m "
            "son las de la red (IAT 151/2018), el informe no las repite (supuesto)",
        }
    ],
    "rigging": {
        "doors": "polivalentes Morgère de 1200 kg (IAT 151/2018); SPF08 de 1000 kg y 4,68 m² "
        "desde agosto de 2018 (IC 029/2018, IC 012/2021)",
        "bridle": "superiores de 50 m (Ø18 mm) e inferiores de 48,5 m (Ø20 mm) con 1,5 m de "
        "cadena de reglaje",
        "sweeps": "100 m de cable de acero de 20 mm",
    },
    "notes": [
        "Red construida (fig. 1): cambian respecto de la diseñada las puntas de ala (12 y 9 "
        "mallas), el costado (dos cuñas de 6 mallas), el vientre (alas de 55,5 + 10 filas, Ø4 mm) "
        "y el copo (hilo doble de 4 mm). La columna de malleros del vientre no está impresa: se "
        "suponen los del dorso (A VERIFICAR).",
        "Mediciones: 52 lances de la tabla 1 de IAT 151/2018 (polivalentes de 1200 kg, 26–93 m), "
        "3 de IC 029/2018 y 40 de IC 012/2021 (SPF08 de 1000 kg y 4,68 m², 63–161 m). La "
        "superficie y la polar de los polivalentes no se publican: 5,58 m² (EH 06/12) y la hoja "
        "Morgère Polyvalent Ovale de Seafish, A VERIFICAR.",
        "Relingas: el plano no da material ni diámetro; el motor usa los cabos del libro.",
    ],
    "status": "published",
}

# =================================================================================================
# Engel 35,5 m (IAT 101/2017, fig. 1)
# =================================================================================================
_SOURCE_101_1 = {
    **_IAT101,
    "title": "INIDEP IAT 101/17 (Roth y García 2017), fig. 1: plano de la red Engel de 35,5 m de "
    "relinga superior",
    "figure": "Figura 1",
    "page": "8",
}
ENGEL_PANELS = [
    ("UW1", "upper", "wing", 2, 200, R_NY3, 4, 75, 45, "1N2B / AB", "PA"),
    ("UW2", "upper", "wing", 2, 200, R_NY3, 75, 88, 25, "1N2B", "PA"),
    ("U1", "upper", "body", 1, 200, R_NY3, 254, 254, 2, "AN", "PA"),
    ("U2", "upper", "body", 1, 200, R_NY3, 254, 194, 45, "1N3B", "PA"),
    ("U3", "upper", "body", 1, 160, R_NY3, 194, 160, 25, "1N4B", "PA"),
    ("U4", "upper", "body", 1, 120, R_NY3, 160, 110, 50, "1N2B", "PA"),
    ("U5", "upper", "body", 1, 110, R_NY3, 110, 76, 50, "2N2B", "PA"),
    ("UC", "upper", "codend", 1, 103, R_NY4, 81, 81, 214, "AN", "PA"),
    ("LW1", "lower", "wing", 2, 200, R_NY3, 1, 30, 15, "AB / AB", "PA"),
    ("LW2", "lower", "wing", 2, 200, R_NY3, 35, 39, 20, "1N7B / AB", "PA"),
    ("L1", "lower", "body", 1, 200, R_NY3, 169, 169, 2, "AN", "PA"),
    ("L2", "lower", "body", 1, 160, R_NY3, 169, 144, 25, "1N2B", "PA"),
    ("L3", "lower", "body", 1, 120, R_NY3, 144, 110, 50, "1N1B", "PA"),
    ("L4", "lower", "body", 1, 110, R_NY3, 110, 76, 50, "2N2B", "PA"),
    ("LC", "lower", "codend", 1, 103, R_NY4, 81, 81, 214, "AN", "PA"),
]
_D_ENGEL = (
    "assumed",
    "el plano no da el hilo; IC 016/24 dice sólo «confeccionada en hilo de Nylon» (p. 23): nylon "
    "de Ø3 mm (copo de ITO 043/2022). A VERIFICAR",
)
_D_ENGEL_C = (
    "assumed",
    "el plano no dibuja el copo: nylon de Ø4 mm supuesto. A VERIFICAR",
)
_CODEND_ENGEL = {
    "mesh_mm": (
        "transcribed",
        "«Tamaño de malla en la bolsa (mm): 103» (IC 004/24, p. 3; IC 041/25: «Luz de malla en el "
        "copo: 103 mm»); el plano no dibuja el copo",
    ),
    "meshes_top": (
        "derived",
        "76 mallas de 110 mm del final del cuerpo (8,36 m) en mallas de 103 mm: 81 (empalme por "
        "largo estirado). A VERIFICAR",
    ),
    "meshes_bottom": ("derived", "copo recto de 81 mallas. A VERIFICAR"),
    "meshes_depth": (
        "derived",
        "«Longitud de la bolsa (m): 22» (IC 004/24, p. 3) / 0,103 m = 213,6 → 214 filas. A "
        "VERIFICAR",
    ),
    "cut_code": ("assumed", "copo recto (AN)"),
}

ENGEL: dict[str, Any] = {
    "id": "inidep_iat101_engel355",
    "name": "Red Engel de 35,5 m de las campañas de merluza del INIDEP (IAT 101/2017, fig. 1)",
    "description": (
        "Red de arrastre de fondo de dos caras usada en las campañas de evaluación de merluza del "
        "INIDEP desde 1993 (BIP Holmberg, Oca Balda y Angelescu): alas y cuerpo delantero de "
        "200 mm, 160, 120 y 110 mm hacia atrás; lima de 35,5 m (Roth y García 2017, fig. 1). El "
        "plano no da el hilo ni el copo (supuestos) y empalma malla a malla al cambiar de mallero."
    ),
    "family": "bottom",
    "rig": "otter",
    "vessel_hp": (2100.0, 2100.0),
    "target_species": "merluza común (Merluccius hubbsi)",
    "species": {"name": "Merluza", "scientific_name": "Merluccius hubbsi"},
    "source": _SOURCE_101_1,
    "extra_sources": [SRC_EH0612, SRC_IC004, SRC_IC016, SRC_IC041, SRC_IT66],
    "material": "PA",
    "twine_diameter": {R_NY3: 3.0, R_NY4: 4.0},
    "panels": ENGEL_PANELS,
    "panel_notes": {
        "UW2": "Pieza 881 A (45 + 25 filas): el borde de la relinga lleva la lima de 14,60 m y "
        "termina en «1T2B X 8» junto al centro de 6,30 m.",
        "U1": "«2 dobles»: dos filas de mallas dobles al pie de la pieza 881 A («8 mallas "
        "dobles» a cada lado del centro).",
        "LW1": "Triángulo de la pieza 888 (15 filas AB/AB, de la punta a 30 mallas). La pieza "
        "718 M (paralelogramo de 30 mallas y 15 + 44 + 15 filas en AB, con cabos de nylon de 18, "
        "20 y 24 mm y 11,30 m de burlón) va por delante del ala y no se modela. A VERIFICAR.",
        "LW2": "30 mallas sobre la línea y 35 debajo (14 %, como se lee).",
        "L4": "«110 Doble»: hilo doble.",
        "UC": "El plano termina en 76 mallas de 110 mm: el copo se supone (ver procedencia).",
        "LC": "Copo supuesto, como el del dorso.",
    },
    "overrides": _merge(
        _twine(
            ENGEL_PANELS,
            {r[0]: (_D_ENGEL_C if r[2] == "codend" else _D_ENGEL) for r in ENGEL_PANELS},
        ),
        {"UC": _CODEND_ENGEL, "LC": _CODEND_ENGEL},
        {"LW1": {"meshes_top": ("derived", "punta del triángulo (0 mallas) tomada como 1")}},
    ),
    "hanging": {
        "upper": (
            0.40,
            "derived",
            "U1 de la bocana del dorso: 6,30 m de lima sobre 254 − 2 × 88 = 78 mallas de 200 mm "
            "(15,60 m): 0,40; se usa en todo el dorso",
        ),
        "lower": (
            0.40,
            "assumed",
            "el plano no da el centro del burlón: el U1 del dorso. A VERIFICAR",
        ),
    },
    "headrope": {
        "length_m": 35.5,
        "wing_m": 14.6,
        "bosom_m": 6.3,
        "diameter_mm": 16,
        "material": "«Cable plastificado 16 mm» (fig. 1)",
        "rope": "rope_combinado_6_16mm",
        "pieces": {
            "wing_m": ("transcribed", "«14,60 m» por ala (fig. 1)"),
            "bosom_m": ("transcribed", "«6,30 m» entre los grilletes de acople (fig. 1)"),
            "diameter_mm": (
                "transcribed",
                "«Cable plastificado 16 mm» (fig. 1); el motor toma el combinado de 16 mm",
            ),
        },
    },
    "footrope": {
        "length_m": 41.5,
        "wing_m": 17.11,
        "bosom_m": 7.28,
        "material": "«Relinga 41,50 m» (fig. 1); material no publicado",
        "pieces": {
            "bosom_m": (
                "assumed",
                "el plano no da el centro del burlón: 91 mallas de 200 mm de la bocana del vientre "
                "× U1 0,40 (supuesto) = 7,28 m. A VERIFICAR",
            ),
            "wing_m": ("derived", "(41,50 − 7,28) / 2 = 17,11 m por ala. A VERIFICAR"),
        },
    },
    "floats": {
        "count": 77,
        "diameter_mm": 200,
        "kind": "transcribed",
        "document": "rubio2024calibracion",
        "note": "«77 boyas de 200 mm y 3 kg de flotación y 240 kg de peso» (IC 016/24, p. 23)",
    },
    "ballast_kg": {
        "value": 240.0,
        "kind": "transcribed",
        "document": "rubio2024calibracion",
        "note": "«77 boyas de 200 mm y 3 kg de flotación y 240 kg de peso» (IC 016/24, p. 23)",
    },
    "design": {
        "vessel_id": (
            "bip_holmberg",
            "transcribed",
            "BIP «Dr. E. L. Holmberg», «Potencia (HP): 2100» (EH 06/12, pp. 5–6)",
            "tringali2012eh0612",
        ),
        "depth_m": (
            100.0,
            "assumed",
            "profundidad típica de las campañas de merluza: los lances de IC 041/25 van de 64 a "
            "158 m (p. 5). A VERIFICAR",
            "alvarezcolombo2025ic041",
        ),
        "sweeps_m": (
            100.0,
            "transcribed",
            "«Largo de patentes: 100 m» (IC 041/25, p. 5)",
            "alvarezcolombo2025ic041",
        ),
        "bridle_upper_m": (
            50.0,
            "transcribed",
            "«Largo de brida superior: 50 m» (IC 041/25, p. 5)",
            "alvarezcolombo2025ic041",
        ),
        "bridle_lower_m": (
            48.5,
            "transcribed",
            "«Largo de brida inferior: 48,5 m» (IC 041/25, p. 5)",
            "alvarezcolombo2025ic041",
        ),
        "speed_kn": (
            4.0,
            "transcribed",
            "«La velocidad y duración de los arrastres fue de 4 nudos» (IC 041/25, p. 5)",
            "alvarezcolombo2025ic041",
        ),
        **_door_design("polivalente_1200", "tringali2012eh0612"),
    },
    "validation_doors": {
        k: VALIDATION_DOORS[k] for k in ("polivalente_1200", "polivalente_1260", "spf085_ic016")
    },
    "measured": [
        {
            "series": "ic016",
            "source": "rubio2024calibracion",
            "haul": n,
            "depth_m": d,
            "warp_m": float(w),
            "speed_kn": v,
            "door": "spf085_ic016",
            "wing_spread_m": ah,
            "door_spread_m": float(dp),
            "vertical_opening_m": av,
            "note": "anexo I (PDF pp. 32–33), BIPO Angelescu; AH de los sensores de puntas de ala; "
            "enganches del portón cambiados entre lances (pp. 11–13)",
        }
        for n, d, v, w, ah, av, dp in (
            (17, 22.55, 4.0, 104, None, 4.96, 57),
            (18, 24.5, 4.1, 106, 15.95, 4.95, 57),
            (19, 20.8, 4.22, 110, 17.0, 4.0, 64),
            (20, 21.2, 3.97, 160, 18.5, 4.3, 76),
            (21, 21.95, 4.06, 149, 18.9, 4.0, 79),
            (22, 24.5, 3.91, 145, 19.86, 4.0, 93),
            (23, 22.17, 4.0, 157, 19.0, 4.0, 91),
            (25, 106.0, 3.6, 351, None, 4.57, 120),
            (26, 108.0, 3.9, 352, 23.04, 4.29, 125),
            (27, 117.0, 3.8, 370, 23.19, 4.45, 124),
            (28, 105.0, 3.9, 403, 23.8, 4.23, 128),
        )
    ]
    + [
        {
            "series": "it66",
            "source": "casarsa2007inftec66",
            "haul": n,
            "depth_m": float(d),
            "warp_m": None,
            "speed_kn": v,
            "door": "polivalente_1260",
            "wing_spread_m": ah,
            "door_spread_m": float(dp),
            "vertical_opening_m": av,
            "note": "tabla 2 (BIP Oca Balda, 2000): AH del sonar de red Simrad FS-903; el informe "
            "no da el cable filado (el motor usa el de su tabla por profundidad)",
        }
        for n, av, ah, dp, v, d in (
            (1, 6.5, 17.0, 97, 3.2, 55),
            (3, 6.5, 18.5, 106, 3.7, 64),
            (4, 7.2, 18.3, 101, 3.5, 70),
            (5, 7.2, 17.5, 104, 3.9, 62),
            (6, 5.6, 17.0, 105, 3.8, 74),
            (8, 6.0, 18.2, 109, 3.6, 80),
            (9, 6.0, 17.5, 114, 4.0, 79),
            (10, 5.8, 17.0, 107, 3.7, 86),
        )
    ]
    + [
        {
            "series": "ic041",
            "source": "alvarezcolombo2025ic041",
            "haul": "media",
            "depth_m": 111.0,
            "warp_m": None,
            "speed_kn": 4.0,
            "door": "polivalente_1200",
            "wing_spread_m": None,
            "door_spread_m": 101.2,
            "vertical_opening_m": 4.4,
            "note": "«Los promedios de la geometría de la red fueron de 101,2 m para la distancia "
            "entre portones, estimándose la distancia entre alas en 20,18 m, y 4,4 m para la "
            "abertura vertical» (p. 7; la AH es estimada, no medida); lances de 64 a 158 m (se usa "
            "el centro, 111 m) a 4 nudos; BIPO Angelescu, Simrad TV80",
        },
    ],
    "rigging": {
        "doors": "polivalentes de 1200 kg y 5,58 m² (EH 06/12)",
        "bridle": "superior de 50 m e inferior de 48,5 m",
        "sweeps": "100 m",
    },
    "notes": [
        "BORRADOR: al cambiar de mallero el plano conserva la cantidad de mallas (194 de 200 mm "
        "sobre 194 de 160 mm, 160 de 160 mm sobre 160 de 120 mm, 169 de 200 mm sobre 169 de "
        "160 mm, 144 de 160 mm sobre 144 de 120 mm): empalmes malla a malla que no cierran por "
        "largo estirado (20–25 %). El plano no da el hilo (supuesto nylon de Ø3 mm) ni el copo "
        "(supuesto de 103 mm, 22 m), y la pieza 718 M del ala inferior no se modela.",
        "Burlón: el plano da 41,50 m; EH 06/12, IC 004/24 e IC 041/25 dicen 50 m; IC 019/13, "
        "35,3/40,0 m; Inf. Téc. 66, 40,3 m. Se usa el del plano (A VERIFICAR).",
        "Mediciones: IC 016/24 (Angelescu, SPF 08,5 de 4,8 m², lances 17–28 a 21–117 m con AH "
        "de los sensores de ala), Inf. Téc. 66 (Oca Balda, polivalentes de 1260 kg, sonar de red) "
        "e IC 041/25 (media de la campaña). EH 06/12: DP entre 100 y 115 m y AV de unos 4,5 m a "
        "4 nudos, sin profundidad por lance.",
    ],
    "status": "draft",
}

# =================================================================================================
# Baldino «Beagle I» 46,4 m (IAT 045/2019, figs. 2 y 3)
# =================================================================================================
_SOURCE_045_3 = {
    **_IAT045,
    "title": "INIDEP IAT 045/19 (Roth 2019), fig. 3: plano de la red modificada de 46,4 m de la "
    "empresa Nietos de Antonio Baldino S.A. (pesquero Beagle I)",
    "figure": "Figura 3",
    "page": "5",
}
_SOURCE_045_2 = {
    **_IAT045,
    "title": "INIDEP IAT 045/19 (Roth 2019), fig. 2: plano digital de la red original de 46,4 m "
    "presentada por Nietos de Antonio Baldino S.A.",
    "figure": "Figura 2",
    "page": "4",
}
BALDINO_MOD_PANELS = [
    ("UW1", "upper", "wing", 2, 300, R_PE3, 3, 24, 30, None, "PE"),
    ("UW2", "upper", "wing", 2, 300, R_PE3, 24, 63, 26, None, "PE"),
    ("U1", "upper", "body", 1, 200, R_PE3, 277, 245, 24, None, "PE"),
    ("U2", "upper", "body", 1, 200, R_PE3, 243, 191, 26, None, "PE"),
    ("U3", "upper", "body", 1, 160, R_PE3, 239, 164, rows(62.5), None, "PE"),
    ("U4", "upper", "body", 1, 140, R_PE3, 188, 86, 85, None, "PE"),
    ("U5", "upper", "body", 1, 120, R_PE3, 100, 100, 59, "AN", "PE"),
    ("UC", "upper", "codend", 1, 120, R_PE4D, 100, 100, 167, "AN", "PE"),
    ("LW1", "lower", "wing", 2, 200, R_PE4, 40, 40, 46, None, "PE"),
    ("LW2", "lower", "wing", 2, 200, R_PE4, 40, 60, 20, None, "PE"),
    ("L1", "lower", "body", 1, 200, R_PE4, 185, 185, 24, "AN", "PE"),
    ("L2", "lower", "body", 1, 160, R_PE4, 231, 166, rows(62.5), None, "PE"),
    ("L3", "lower", "body", 1, 140, R_PE4, 188, 86, 85, None, "PE"),
    ("L4", "lower", "body", 1, 120, R_PE4, 100, 100, 59, "AN", "PE"),
    ("LC", "lower", "codend", 1, 120, R_PE4D, 100, 100, 167, "AN", "PE"),
    ("S1", "side", "body", 2, 200, R_PE3, 30, 30, 24, "AN", "PE"),
    ("S2", "side", "body", 2, 200, R_PE3, 45, 45, 26, "AN", "PE"),
    ("S3", "side", "body", 2, 160, R_PE3, 56, 31, rows(62.5), None, "PE"),
    ("S4", "side", "body", 2, 140, R_PE3, 35, 12, 85, None, "PE"),
    ("S5", "side", "body", 2, 120, R_PE3, 14, 3, 59, None, "PE"),
]
_D_BALDINO = {
    "upper": (
        "assumed",
        "rótulo manuscrito «3» del dorso en el escaneo del plano de la empresa (fig. 1, p. 3), "
        "leído como PE de Ø3 mm (las redes del INIDEP del mismo puerto); el informe no da el hilo. "
        "A VERIFICAR",
    ),
    "side": (
        "assumed",
        "rótulo manuscrito «3» del costado en el escaneo (fig. 1, p. 3), leído como PE de Ø3 mm. A "
        "VERIFICAR",
    ),
    "lower": (
        "assumed",
        "rótulo manuscrito «4» del vientre en el escaneo (fig. 1, p. 3), leído como PE de Ø4 mm. A "
        "VERIFICAR",
    ),
    "codend": (
        "assumed",
        "«# 4D 120 20 MTS» en el escaneo (fig. 1, p. 3): hilo doble de Ø4 mm en el copo de 120 "
        "mm. A VERIFICAR",
    ),
}


def _baldino_twine(panels: list[tuple[Any, ...]]) -> dict[str, Any]:
    return _twine(
        panels, {r[0]: _D_BALDINO["codend" if r[2] == "codend" else r[1]] for r in panels}
    )


_DESIGN_045: dict[str, tuple[Any, ...]] = {
    "vessel_id": (
        "ar_congelador_e1",
        "assumed",
        "IAT 045/2019 no da el buque ni su potencia («buque pesquero Beagle I», p. 2): congelador "
        "arrastrero típico de la flota, estrato I. A VERIFICAR",
    ),
    "depth_m": (130.0, "transcribed", "«Profundidad de pesca: 130 m» (p. 2)"),
    "speed_kn": (4.0, "transcribed", "«Velocidad de arrastre: 4 Ns» (p. 2)"),
    "warp_m": (
        600.0,
        "transcribed",
        "«Cable de arrastre de acero de 24 mm de diámetro y 600 m de longitud» (p. 2)",
    ),
    "warp_diameter_mm": (24.0, "transcribed", "cable de arrastre de acero de 24 mm (p. 2)"),
    "bridle_upper_m": (
        45.0,
        "transcribed",
        "«Un par de bridas de cable de acero, la superior de 18 mm de diámetro y la inferior de "
        "22 mm de diámetro y 45 m de longitud por banda» (p. 2)",
    ),
    "door_id": (
        "door_polar_mercury20r_7_5m2",
        "derived",
        VALIDATION_DOORS["mercury_2300"]["note"],
    ),
}
_SIM_045 = (
    "resultados de DynamiT del INIDEP (p. 6): AV, AH, «Resistencia al avance (kg)», volumen "
    "filtrado y DP; 4 nudos, 130 m y 600 m de cable (p. 2); modelo, no mediciones"
)
_ROPES_045 = {
    "headrope": {
        "length_m": 46.4,
        "wing_m": 20.8,
        "bosom_m": 6.0,
        "diameter_mm": 14,
        "material": "«Relinga superior de cable de acero de 14 mm de diámetro» (p. 2)",
        "rope": "rope_combinado_6_14mm",
        "pieces": {
            "wing_m": ("transcribed", "11,10 + 9,70 m por ala (figs. 2 y 3)"),
            "bosom_m": ("transcribed", "centro de 6 m (figs. 2 y 3)"),
            "diameter_mm": (
                "transcribed",
                "cable de acero de 14 mm (p. 2); el motor toma el combinado de 14 mm",
            ),
        },
    },
    "footrope": {
        "length_m": 55.7,
        "wing_m": 24.85,
        "bosom_m": 6.0,
        "diameter_mm": 18,
        "material": "«Relinga inferior de cable de acero combinado de 18 mm de diámetro con doble "
        "forro» (p. 2)",
        "rope": "rope_combinado_6_18mm",
        "pieces": {
            "wing_m": ("transcribed", "11,10 + 13,75 m por ala (figs. 2 y 3)"),
            "bosom_m": ("transcribed", "centro de 6 m (figs. 2 y 3)"),
            "diameter_mm": ("transcribed", "combinado de 18 mm con doble forro (p. 2)"),
        },
    },
}

BALDINO_MOD: dict[str, Any] = {
    "id": "inidep_iat045_baldino_modificada",
    "name": "Red de fondo de 46,4 m de Baldino (Beagle I), modificada por el INIDEP (IAT 045/2019, "
    "fig. 3)",
    "description": (
        "Red de arrastre de fondo comercial de 46,4 m de lima del pesquero Beagle I (Nietos de "
        "Antonio Baldino S.A.), redibujada por el INIDEP con las secciones empalmadas: alas de 300 "
        "mm, cuerpo de 200 a 120 mm, copo de 120 mm; portones Mercury de 2300 kg. DynamiT a 4 "
        "nudos, 130 m y 600 m de cable: DP 194,9 m, AH 27,4 m, AV 3,3 m (Roth 2019)."
    ),
    "family": "bottom",
    "rig": "otter",
    "vessel_hp": (1435.0, 1435.0),
    "target_species": "merluza común (Merluccius hubbsi)",
    "species": {"name": "Merluza", "scientific_name": "Merluccius hubbsi"},
    "source": _SOURCE_045_3,
    "material": "PE",
    "twine_diameter": {R_PE3: 3.0, R_PE4: 4.0, R_PE4D: 4.0},
    "panels": BALDINO_MOD_PANELS,
    "panel_notes": {
        "UW1": "Triángulo de 30 filas de 300 mm de la punta («3» mallas) a «54» mallas, que "
        "incluyen el ala (24) y el frente del costado (30, no se modela). Los cortes de la fig. 3 "
        "no están rotulados.",
        "S1": "El costado sigue en 30 mallas de 200 mm (6,00 m) bajo las 30 de 300 mm (9,00 m) y "
        "pasa a 45 mallas de 200 mm (9,00 m) en la sección siguiente: así se lee la fig. 3."
        + _SIDE_FRONT.format(front="30 mallas de 300 mm en 26 filas", wing="26 filas de UW2"),
        "S5": "Termina en 3 mallas al llegar al copo.",
    },
    "overrides": _merge(
        _baldino_twine(BALDINO_MOD_PANELS),
        _half_rows(
            U3="62,5 filas redondeadas a 63",
            L2="62,5 filas redondeadas a 63",
            S3="62,5 filas redondeadas a 63",
        ),
        {"UW1": {"meshes_bottom": ("derived", "54 − 30 mallas del frente del costado")}},
    ),
    "hanging": {
        "upper": (
            0.34,
            "derived",
            "U1 de la bocana del dorso: 6 m de lima sobre 277 × 0,20 − 2 × 63 × 0,30 = 17,60 m: "
            "0,34; se usa en todo el dorso",
        ),
        "lower": (
            0.46,
            "derived",
            "U1 de la bocana del vientre: 6 m sobre 185 × 0,20 − 2 × 60 × 0,20 = 13,00 m: 0,46; "
            "se usa en todo el vientre",
        ),
        "side": (0.40, "assumed", "el plano no da U1 del costado: promedio del dorso y el vientre"),
    },
    **_ROPES_045,
    "floats": {
        "count": 88,
        "diameter_mm": 200,
        "kind": "assumed",
        "note": "«Flotacion = 88 de LOT. 200 %» en el escaneo (fig. 1, p. 3): 88 boyas; el "
        "diámetro no se lee (200 mm supuestos). A VERIFICAR",
    },
    "ballast_kg": {
        "value": 172.9,
        "kind": "assumed",
        "note": "escaneo (fig. 1, p. 3): «BOCA = 110 kg. (61 est C/A.) PUNTO = 21,5 kg. MEDIO = "
        "23,4 kg. PUNTO = 18 kg.»: suma 110 + 21,5 + 23,4 + 18 = 172,9 kg; no se sabe si los "
        "tramos son por lado (235,8 kg) y hay un «270 kg cadena» manuscrito. A VERIFICAR",
    },
    "design": _DESIGN_045,
    "simulated": [
        {
            "speed_kn": 4.0,
            "depth_m": 130.0,
            "warp_m": 600.0,
            "door_spread_m": dp,
            "horizontal_opening_m": ah,
            "vertical_opening_m": av,
            "drag_kgf": r,
            "variant": var,
            "source": "roth2019iat045",
            "note": _SIM_045 + note,
        }
        for var, av, ah, r, dp, note in (
            (
                "modificada",
                3.3,
                27.4,
                13536.8,
                194.9,
                ": «Modificada 3,3 27,4 13.536,8 179,8 194,9»",
            ),
            (
                "bridas +5 m",
                3.4,
                27.2,
                13552.7,
                195.8,
                " (bridas 5 m más largas; no es el caso del catálogo)",
            ),
        )
    ]
    + [
        {
            "speed_kn": 4.0,
            "depth_m": 130.0,
            "warp_m": 550.0,
            "door_spread_m": 186.2,
            "horizontal_opening_m": 26.5,
            "vertical_opening_m": 3.5,
            "drag_kgf": 13382.0,
            "variant": "malleta −5 m, cable −50 m",
            "source": "roth2019iat045",
            "note": _SIM_045 + " (malleta 5 m más corta y 50 m menos de cable; no es el caso del "
            "catálogo)",
        }
    ],
    "rigging": {
        "doors": "Mercury (Polar) con toberas, 2300 kg en el aire",
        "bridle": "superior de Ø18 mm e inferior de Ø22 mm, 45 m por banda",
        "warp": "600 m de acero de 24 mm",
        "seabed": "arena",
    },
    "notes": [
        "BORRADOR: el costado pasa de 30 mallas de 300 mm (9,00 m) a 30 de 200 mm (6,00 m) y "
        "luego a 45 de 200 mm (9,00 m), como se lee la fig. 3: el empalme S1/S2 no cierra (33 %). "
        "Los cortes no están rotulados.",
        "Aparejo de la simulación (p. 2): bridas de 45 m (superior Ø18 mm, inferior Ø22 mm), "
        "portones Mercury de 2300 kg, 600 m de cable de 24 mm, lima de acero de 14 mm, burlón "
        "combinado de 18 mm con doble forro, 4 nudos, 130 m, arena. El informe no da el largo de "
        "las malletas (el motor usa sus 25 m), la superficie del portón ni el buque.",
        "Lima: 2 × (11,10 + 9,70) + 6 = 47,6 m en el plano frente a «LIMA 46,4 MTS» del título y "
        "del escaneo; se usa 46,4 m. Burlón: 2 × (11,10 + 13,75) + 6 = 55,7 m («BURLÓN 55,7 MTS»).",
        "Hilos y flotación del escaneo manuscrito de la empresa (fig. 1), A VERIFICAR.",
    ],
    "status": "draft",
}

BALDINO_ORIG_PANELS = [
    ("UW1", "upper", "wing", 2, 300, R_PE3, 3, 25, 30, None, "PE"),
    ("UW2", "upper", "wing", 2, 300, R_PE3, 25, 63, 26, None, "PE"),
    ("U1", "upper", "body", 1, 200, R_PE3, 277, 245, 24, None, "PE"),
    ("U2", "upper", "body", 1, 200, R_PE3, 234, 203, 25, None, "PE"),
    ("U3", "upper", "body", 1, 160, R_PE3, 250, 190, rows(62.5), None, "PE"),
    ("U4", "upper", "body", 1, 140, R_PE3, 214, 134, rows(85.7), None, "PE"),
    ("U5", "upper", "body", 1, 120, R_PE3, 100, 100, rows(53.3), "AN", "PE"),
    ("UC", "upper", "codend", 1, 120, R_PE4D, 100, 100, rows(166.7), "AN", "PE"),
    ("LW1", "lower", "wing", 2, 200, R_PE4, 40, 40, 39, None, "PE"),
    ("LW2", "lower", "wing", 2, 200, R_PE4, 40, 60, 24, None, "PE"),
    ("L1", "lower", "body", 1, 200, R_PE4, 185, 185, 25, "AN", "PE"),
    ("L2", "lower", "body", 1, 160, R_PE4, 184, 135, rows(62.5), None, "PE"),
    ("L3", "lower", "body", 1, 140, R_PE4, 187, 102, rows(85.7), None, "PE"),
    ("L4", "lower", "body", 1, 120, R_PE4, 100, 100, rows(53.3), "AN", "PE"),
    ("LC", "lower", "codend", 1, 120, R_PE4D, 100, 100, rows(166.7), "AN", "PE"),
    ("S1", "side", "body", 2, 200, R_PE3, 46, 46, 24, "AN", "PE"),
    ("S2", "side", "body", 2, 200, R_PE3, 46, 46, 25, "AN", "PE"),
    ("S3", "side", "body", 2, 140, R_PE3, 60, 40, rows(71.4), None, "PE"),
    ("S4", "side", "body", 2, 140, R_PE3, 45, 11, rows(85.7), None, "PE"),
    ("S5", "side", "body", 2, 120, R_PE3, 11, 5, rows(53.3), None, "PE"),
]
_ROWS_045_2 = {
    "UW1": "9,0 m / 0,30 m = 30 filas (la fig. 2 da alturas en metros)",
    "UW2": "7,8 m / 0,30 m = 26 filas",
    "U1": "4,8 m / 0,20 m = 24 filas",
    "U2": "5,0 m / 0,20 m = 25 filas",
    "U3": "10,0 m / 0,16 m = 62,5 → 63 filas",
    "U4": "12,0 m / 0,14 m = 85,7 → 86 filas",
    "U5": "6,4 m / 0,12 m = 53,3 → 53 filas",
    "UC": "20,0 m / 0,12 m = 166,7 → 167 filas",
    "LW1": "7,8 m / 0,20 m = 39 filas",
    "LW2": "4,8 m / 0,20 m = 24 filas",
    "L1": "5,0 m / 0,20 m = 25 filas",
    "L2": "10,0 m / 0,16 m = 62,5 → 63 filas",
    "L3": "12,0 m / 0,14 m = 85,7 → 86 filas",
    "L4": "6,4 m / 0,12 m = 53,3 → 53 filas",
    "LC": "20,0 m / 0,12 m = 166,7 → 167 filas",
    "S1": "4,8 m / 0,20 m = 24 filas",
    "S2": "5,0 m / 0,20 m = 25 filas",
    "S3": "10,0 m / 0,14 m = 71,4 → 71 filas (malla de 140 mm en la franja de 160 mm)",
    "S4": "12,0 m / 0,14 m = 85,7 → 86 filas",
    "S5": "6,4 m / 0,12 m = 53,3 → 53 filas",
}

BALDINO_ORIG: dict[str, Any] = {
    **BALDINO_MOD,
    "id": "inidep_iat045_baldino_original",
    "name": "Red de fondo de 46,4 m de Baldino (Beagle I), original (IAT 045/2019, fig. 2)",
    "description": (
        "Red de arrastre de fondo comercial de 46,4 m de lima del pesquero Beagle I tal como la "
        "presentó la empresa, redibujada por el INIDEP: «secciones que no coinciden con las "
        "siguientes en diversas partes del cuerpo» (Roth 2019, p. 5). DynamiT a 4 nudos, 130 m "
        "y 600 m de cable: DP 189,1 m, AH 27,1 m, AV 3,2 m y 13 875,6 kg."
    ),
    "source": _SOURCE_045_2,
    "panels": BALDINO_ORIG_PANELS,
    "panel_notes": {
        "UW1": "Triángulo de 9,0 m de 300 mm con «66» mallas al pie: ala (25) y frente del "
        "costado (no se modela). La punta (3 mallas) es la de la fig. 3.",
        "S1": "Primer tramo modelado del costado."
        + _SIDE_FRONT.format(front="46 mallas de 200 mm en 7,8 m", wing="7,8 m de UW2"),
        "S3": "El costado usa malla de 140 mm (◊140) en la franja de 160 mm del cuerpo.",
        "S5": "La fig. 2 no rotula el ancho de arriba: 11 mallas, las del pie del tramo anterior "
        "(A VERIFICAR); termina en 5.",
    },
    "overrides": _merge(
        _baldino_twine(BALDINO_ORIG_PANELS),
        {pid: {"meshes_depth": ("derived", note)} for pid, note in _ROWS_045_2.items()},
        {
            "UW1": {
                "meshes_top": ("assumed", "la fig. 2 no rotula la punta: 3 mallas de la fig. 3"),
                "meshes_bottom": ("derived", "«25» al pie del ala (fig. 2)"),
            },
            "S5": {"meshes_top": ("assumed", "11 mallas del tramo anterior. A VERIFICAR")},
        },
    ),
    "simulated": [
        {
            "speed_kn": 4.0,
            "depth_m": 130.0,
            "warp_m": 600.0,
            "door_spread_m": 189.1,
            "horizontal_opening_m": 27.1,
            "vertical_opening_m": 3.2,
            "drag_kgf": 13875.6,
            "variant": "original",
            "source": "roth2019iat045",
            "note": _SIM_045 + ": «Original 3,2 27,1 13.875,6 166,2 189,1»",
        }
    ],
    "notes": [
        "BORRADOR: secciones que no empalman (lo que señala el INIDEP, p. 5): dorso 245 → 234 "
        "mallas de 200 mm, 134 de 140 mm (18,76 m) sobre 100 de 120 mm (12,00 m); vientre 185 de "
        "200 mm sobre 184 de 160 mm. La fig. 2 da alturas en metros: las filas se derivan.",
        *BALDINO_MOD["notes"][1:],
    ],
    "status": "draft",
}

NETS_20: list[dict[str, Any]] = [VA_DESIGN, VA_BUILT, ENGEL, BALDINO_ORIG, BALDINO_MOD]
