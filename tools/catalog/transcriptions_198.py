"""Transcripciones de la Fase 19.8c: redes tangoneras de langostino de INIDEP IAT 27/2019 y 75/2023.

Mismas convenciones que ``tools/catalog/transcriptions_195.py`` (filas ``(id, plane, section,
count, mesh_mm, rtex, top, bottom, depth, cut, material)``).

* **INIDEP IAT 27/2019** (Roth 2019), figs. 2 y 3 (PDF pp. 4 y 5): planos vectoriales de la red
  tangonera de la empresa Luis Solimeno e hijos S.A. («original», redibujada por el INIDEP con la
  relinga superior y la bocana del vientre corregidas) y de la red «modificada» que propone el
  INIDEP. Dorso y vientre con alas de 120 mm (7 mallas en la punta, 53 filas AB), cuerpo de 80 mm,
  copo de 60 mm en dos tramos de 100 filas; costado de 120 y 80 mm que termina en una malla. El
  plano da mallas, filas, cortes y cabos; el aparejo, el portón, la profundidad y la velocidad
  salen del texto (p. 2). Los hilos no están en el informe (salvo «Ny Tr 4 mm» en el copo de la
  fig. 2): se suponen y quedan A VERIFICAR.
* **INIDEP IAT 75/2023** (Roth y Rubio 2023), figs. 1 y 2 (PDF pp. 4 y 5): red propuesta por
  Pesquera Deseado en 2023 (dorso de 160 mm, costados de 140 mm, vientre de 80 mm) y la red
  tradicional de baja abertura de la empresa (80 mm con cuerpo trasero de 60 mm). Mallas, filas,
  cortes y cabos del plano; malleros, diámetros de hilo y aparejo del texto (pp. 2–3).

Los números entre paréntesis del plano (bocana: 78, 123, 156, 116) son el ancho de la bocana que
queda entre las alas; las filas con media malla se redondean a la malla entera. Como en ITO 043,
el tramo delantero del costado (junto a las alas o por delante de ellas) no se modela.
"""

from __future__ import annotations

from typing import Any

from tools.catalog.transcriptions_195 import rows, rtex_from_runnage

from trawlkit.catalog import LANGOSTINO_DEPTH_M

ACCESSED_198 = "2026-10-28"

# --- Hilos ---------------------------------------------------------------------------------------
#: PE Ø3 mm: el hilo «3 mm PCU» de la tabla de materiales de ITO 043/2022 (235 m/kg).
R_PE3 = rtex_from_runnage(235.0)  # 4255
#: PE Ø1,9 mm: Rtex escalado con d² del hilo de Ø1,8 mm y 500 m/kg de ITO 043/2022.
R_PE19 = round(rtex_from_runnage(500.0) * (1.9 / 1.8) ** 2)  # 2228
#: Nylon Ø3 mm del copo de ITO 043/2022 (280 m/kg).
R_NY3 = rtex_from_runnage(280.0)  # 3571
#: Nylon trenzado Ø4 mm: escalado con d² del nylon de Ø3 mm de ITO 043/2022.
R_NY4 = round(1.0e6 / 280.0 * (4.0 / 3.0) ** 2)  # 6349

_R_NOTE = {
    R_PE3: "Rtex = 10⁶ / 235 m/kg del hilo de PE de Ø3 mm («3 mm PCU») de ITO 043/2022",
    R_PE19: "Rtex = 2000 × (1,9/1,8)² (hilo de PE de Ø1,8 mm y 500 m/kg de ITO 043/2022 escalado "
    "con d²)",
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


# =================================================================================================
# IAT 27/2019: red Solimeno
# =================================================================================================
_IAT027 = {
    "key": "roth2019iat027",
    "url": "https://marabiertonew.inidep.edu.ar/server/api/core/bitstreams/"
    "0593c738-7dbd-44d4-907e-8cb4ff9bcee9/content",
    "accessed": ACCESSED_198,
}
_SOURCE_027_2 = {
    **_IAT027,
    "title": "INIDEP IAT 27/19 (Roth 2019), fig. 2: plano digital de la red tangonera original de "
    "Luis Solimeno e hijos S.A.",
    "figure": "Figura 2",
    "page": "4",
}
_SOURCE_027_3 = {
    **_IAT027,
    "title": "INIDEP IAT 27/19 (Roth 2019), fig. 3: red tangonera modificada por el INIDEP",
    "figure": "Figura 3",
    "page": "5",
}

_TWINE_027_NOTE = "IAT 27/2019 no da los hilos de la red: se supone {what}. A VERIFICAR"
_D027_120 = ("assumed", _TWINE_027_NOTE.format(what="PE de Ø3 mm (cuerpo de ITO 043/2022)"))
_D027_80 = (
    "assumed",
    _TWINE_027_NOTE.format(what="PE de Ø1,9 mm (malla de 80 mm de IAT 75/2023, misma flota)"),
)
_D027_CODEND = (
    "assumed",
    "el plano rotula «Ny Tr 4 mm» (nylon trenzado de Ø4 mm) sólo en el segundo tramo del copo "
    "(fig. 2); se supone el mismo hilo en el primero. A VERIFICAR",
)
_D027_CODEND_T = ("transcribed", "«Ny Tr 4 mm»: nylon trenzado de Ø4 mm (fig. 2)")

_DESIGN_027: dict[str, tuple[Any, str, str | None]] = {
    "vessel_id": (
        "ar_tangonero_1998",
        "assumed",
        "IAT 27/2019 no nombra el buque de la empresa Luis Solimeno: tangonero típico de la flota "
        "argentina (media de 1998)",
    ),
    "door_length_m": (
        4.20,
        "transcribed",
        "«portones rectangulares planos, para arrastre de fondo, construidos en hierro y madera "
        "de 4,20 x 1,30 m» (p. 2)",
    ),
    "door_height_m": (1.30, "transcribed", "4,20 × 1,30 m (p. 2)"),
    "door_weight_air_kg": (450.0, "transcribed", "«un peso en el aire de 450 kg» (p. 2)"),
    "depth_m": (100.0, "transcribed", "«Profundidad de pesca: 100 m» (p. 2)"),
    "outrigger_bridle_m": (
        55.0,
        "transcribed",
        "«Una tijera de cable de acero combinado de 26 mm de diámetro y 55 m de longitud» (p. 2)",
    ),
    "outrigger_bridle_diameter_mm": (26.0, "transcribed", "tijera de 26 mm (p. 2)"),
    "shrimp_bridle_m": (
        4.0,
        "transcribed",
        "«Un par de bridas de cable de acero combinado, la superior de 18 mm de diámetro y la "
        "inferior de 22 mm de diámetro, y 4 m de longitud por banda» (p. 2); son los tramos de 4 m "
        "que el plano suma a las relingas",
    ),
    "speed_kn": (4.0, "transcribed", "«Velocidad de arrastre: 4 Ns» (p. 2)"),
}

_RIGGING_027 = {
    "doors": "rectangulares planos de hierro y madera, 4,20 × 1,30 m, 450 kg en el aire",
    "bridle": "tijera de 55 m de cable de acero combinado de 26 mm; bridas de 4 m por banda "
    "(superior Ø18 mm, inferior Ø22 mm)",
    "warp": "350 m de cable de acero de 22 mm",
    "floats": "5 flotadores de 200 mm",
    "ballast": "140 kg de cadena de hierro",
    "seabed": "fango",
}
_RIG_NOTE_027 = (
    "Aparejo y condiciones de la simulación (p. 2): 5 flotadores de 200 mm; 140 kg de cadena; "
    "bridas de cable combinado de 4 m por banda (superior Ø18 mm, inferior Ø22 mm); portones "
    "planos de hierro y madera de 4,20 × 1,30 m y 450 kg; tijera de 55 m de Ø26 mm; 350 m de cable "
    "de Ø22 mm; relinga superior Ø18 mm e inferior Ø22 mm de cable combinado; 4 nudos; 100 m; "
    "fango."
)
_ROPES_027 = (
    "Las relingas del plano suman las bridas de 4 m: la lima publicada ({rs} m) es "
    "2 × ({pieces_s}) "
    "+ {bs} m y el burlón ({ri} m) 2 × ({pieces_i}) + {bi} m. El motor toma esos totales (como "
    "ITO 043 e IAT 75); los tramos verticales (bridas de 4 m{legs}) no van sobre el paño y los "
    "tramos sobre el ala son más largos que su borde estirado (53 filas AB de 120 mm = 6,36 m): "
    "A VERIFICAR."
)
_FLOATS_027 = {
    "count": 5,
    "diameter_mm": 200,
    "kind": "transcribed",
}
_BALLAST_027 = {
    "value": 140.0,
    "kind": "transcribed",
    "note": "«Peso de 140 kg integrado por cadena de hierro» (p. 2)",
}
_SIDE_NOTE_027 = (
    "Tramo del costado junto a U1: las últimas 25,5 filas del tramo de 91,5 filas (el plano traza "
    "la línea a 66 filas, a la altura del pie de las alas). Lo de adelante (68 mallas de 120 mm, "
    "{rows} + 66 filas AN, por delante y junto a las alas) no se modela, como en ITO 043."
)
_HUNG_SIDE_027 = (
    0.66,
    "assumed",
    "el plano no da U1 del costado: promedio del dorso y del vientre",
)


def _iat027_panels(
    u_bosom: int,
    u1_bottom: int,
    u2: tuple[int, int, str],
    l_bosom: int,
    l1_rows: float,
    l2: tuple[int, int, str],
    codend_r: float,
) -> list[tuple[Any, ...]]:
    """Paños de la red Solimeno (figs. 2 y 3: mismas alas, costados y copo)."""
    u_top = 2 * 86 + u_bosom
    l_top = 2 * 80 + l_bosom
    return [
        ("UW1", "upper", "wing", 2, 120, R_PE3, 7, 60, 53, "AN / AB", "PE"),
        ("UW2", "upper", "wing", 2, 120, R_PE3, 60, 86, 13, "AN / 1T2B", "PE"),
        ("U1", "upper", "body", 1, 120, R_PE3, u_top, u1_bottom, rows(25.5), "1N4B", "PE"),
        ("U2", "upper", "body", 1, 80, R_PE19, u2[0], u2[1], 200, u2[2], "PE"),
        ("UC1", "upper", "codend", 1, 60, codend_r, 100, 100, 100, "AN", "PA"),
        ("UC2", "upper", "codend", 1, 60, codend_r, 100, 100, 100, "AN", "PA"),
        ("LW1", "lower", "wing", 2, 120, R_PE3, 7, 60, 53, "AN / AB", "PE"),
        ("LW2", "lower", "wing", 2, 120, R_PE3, 60, 80, 13, None, "PE"),
        ("L1", "lower", "body", 1, 120, R_PE3, l_top, l_top, rows(l1_rows), "AN", "PE"),
        ("L2", "lower", "body", 1, 80, R_PE19, l2[0], l2[1], 200, l2[2], "PE"),
        ("LC1", "lower", "codend", 1, 60, codend_r, 100, 100, 100, "AN", "PA"),
        ("LC2", "lower", "codend", 1, 60, codend_r, 100, 100, 100, "AN", "PA"),
        ("S1", "side", "body", 2, 120, R_PE3, 68, 68, rows(25.5), "AN", "PE"),
        ("S2", "side", "body", 2, 80, R_PE19, 101, 1, 200, "1N2B / AN", "PE"),
    ]


def _iat027_twine(panels: list[tuple[Any, ...]], codend_t: bool) -> dict[str, Any]:
    diam: dict[str, tuple[str, str]] = {}
    for row in panels:
        pid, mesh = row[0], row[4]
        if row[2] == "codend":
            diam[pid] = _D027_CODEND_T if (codend_t and pid.endswith("2")) else _D027_CODEND
        else:
            diam[pid] = _D027_120 if mesh == 120 else _D027_80
    return _twine(panels, diam)


_PANEL_NOTES_027 = {
    "LW2": "El plano no rotula el corte del costado interior (20 mallas en 13 filas).",
    "S2": "Termina en una malla al llegar al copo; no hay cabo de cierre (aft_rope_m).",
}

IAT027_2_PANELS = _iat027_panels(88, 226, (340, 140, "1N2B"), 66, 10, (340, 140, "1N2B"), R_NY4)
IAT027_3_PANELS = _iat027_panels(90, 228, (343, 75, "1N4B"), 68, 6.5, (343, 75, "1N4B"), R_NY4)

IAT027_2: dict[str, Any] = {
    "id": "inidep_iat027_tangonera_solimeno",
    "name": "Red tangonera de Luis Solimeno e hijos S.A., original (IAT 27/2019, fig. 2)",
    "description": (
        "Red tangonera de langostino de dos paños y costados, presentada por la empresa Luis "
        "Solimeno e hijos S.A. y redibujada por el INIDEP con la relinga superior (37,8 m) y la "
        "bocana del vientre corregidas: alas y cielo de 120 mm, cuerpo de 80 mm y copo de 60 mm "
        "de nylon trenzado. El INIDEP señala un exceso de paño al final del cuerpo (Roth 2019)."
    ),
    "family": "bottom",
    "rig": "outrigger",
    "vessel_hp": (948.7, 948.7),
    "target_species": "langostino patagónico (Pleoticus muelleri)",
    "species": {"name": "Langostino", "scientific_name": "Pleoticus muelleri"},
    "source": _SOURCE_027_2,
    "material": "PE",
    "twine_diameter": {R_PE3: 3.0, R_PE19: 1.9, R_NY4: 4.0},
    "panels": IAT027_2_PANELS,
    "panel_notes": {
        **_PANEL_NOTES_027,
        "S1": _SIDE_NOTE_027.format(rows="49,5"),
        "U2": "Borde de bolsa de 140 mallas de 80 mm (11,20 m) sobre el copo de 100 mallas de "
        "60 mm (6,00 m): el «exceso de material en la parte final del cuerpo» que señala el "
        "INIDEP (p. 5).",
    },
    "overrides": _merge(
        _iat027_twine(IAT027_2_PANELS, True),
        _half_rows(U1="25,5 filas redondeadas a 26", S1="25,5 filas (91,5 − 66) redondeadas a 26"),
    ),
    "hanging": {
        "upper": (
            0.57,
            "derived",
            "U1 de la bocana del dorso: 6 m de relinga sobre 88 mallas de 120 mm = 10,56 m "
            "(6 / 10,56 = 0,57); se usa en todo el dorso",
        ),
        "lower": (
            0.76,
            "derived",
            "U1 de la bocana del vientre: 6 m sobre 66 × 0,12 = 7,92 m (0,76). El INIDEP propone "
            "5 m para que las mallas trabajen al 63 % (p. 5); se usa en todo el vientre",
        ),
        "side": _HUNG_SIDE_027,
    },
    "headrope": {
        "length_m": 37.8,
        "wing_m": 15.9,
        "bosom_m": 6.0,
        "diameter_mm": 18,
        "material": "cable de acero combinado Ø18 mm (p. 2)",
        "rope": "rope_combinado_6_18mm",
        "pieces_note": "alas = 4 + 10,3 + 1,6 m (brida de 4 m incluida); bocana = 6 m (fig. 2)",
    },
    "footrope": {
        "length_m": 46.6,
        "wing_m": 20.3,
        "bosom_m": 6.0,
        "diameter_mm": 22,
        "material": "cable de acero combinado Ø22 mm (p. 2)",
        "rope": "rope_combinado_6_22mm",
        "pieces_note": "alas = 4 + 13,3 + 3 m (brida de 4 m incluida); bocana = 6 m (fig. 2)",
    },
    "floats": _FLOATS_027,
    "ballast_kg": _BALLAST_027,
    "design": _DESIGN_027,
    "simulated": [
        {
            "speed_kn": 4.0,
            "vertical_opening_m": 1.1,
            "horizontal_opening_m": 17.5,
            "drag_kgf": 5853.1,
            "note": "resultados de DynamiT del INIDEP para la red original (p. 6, «resistencia al "
            "avance»): modelo, no mediciones; el informe no da la separación de portones",
        }
    ],
    "rigging": _RIGGING_027,
    "notes": [
        "BORRADOR: el cuerpo termina en 140 mallas de 80 mm (11,20 m) por cara y el copo tiene "
        "100 mallas de 60 mm (6,00 m): el empalme no cierra (46 %). El costado termina en una "
        "malla, sin cabo de cierre, así que tampoco cierra por la circunferencia (22,4 m frente a "
        "12,0 m). Es el «exceso de material en la parte final del cuerpo» que el INIDEP corrige en "
        "la red modificada (fig. 3), no un error de lectura.",
        "El plano corrige la relinga superior del plano original de la empresa (39,40 m, que no "
        "es la suma de sus tramos) a 37,8 m y la bocana del vientre (66 mallas en lugar de 100); "
        "el "
        "INIDEP recomienda además 5 m en lugar de 6 m en el centro del burlón (pp. 1 y 5).",
        _ROPES_027.format(
            rs="37,8",
            pieces_s="4 + 10,3 + 1,6",
            bs="6",
            ri="46,6",
            pieces_i="4 + 13,3 + 3",
            bi="6",
            legs="",
        ),
        _RIG_NOTE_027,
        "Hilos: el informe sólo da «Ny Tr 4 mm» en el copo; el resto de los hilos son supuestos "
        "(A VERIFICAR).",
    ],
    "status": "draft",
}

IAT027_3: dict[str, Any] = {
    **IAT027_2,
    "id": "inidep_iat027_tangonera_modificada",
    "name": "Red tangonera modificada por el INIDEP para Luis Solimeno (IAT 27/2019, fig. 3)",
    "description": (
        "Red tangonera de langostino que el INIDEP propone a la empresa Luis Solimeno e hijos "
        "S.A.: las mismas alas de 120 mm, cuerpo de 80 mm que cierra en 75 mallas sobre el copo "
        "de 100 mallas de 60 mm, lima de 39,4 m y burlón de 45,0 m con 5 m de bocana (Roth 2019)."
    ),
    "source": _SOURCE_027_3,
    "panels": IAT027_3_PANELS,
    "panel_notes": {**_PANEL_NOTES_027, "S1": _SIDE_NOTE_027.format(rows="31,5")},
    "overrides": _merge(
        _iat027_twine(IAT027_3_PANELS, False),
        _half_rows(
            U1="25,5 filas redondeadas a 26",
            S1="25,5 filas (91,5 − 66) redondeadas a 26",
            L1="6,5 filas redondeadas a 7",
        ),
    ),
    "hanging": {
        "upper": (
            0.56,
            "derived",
            "U1 de la bocana del dorso: 6 m sobre 90 × 0,12 = 10,80 m (0,56); se usa en todo el "
            "dorso",
        ),
        "lower": (
            0.61,
            "derived",
            "U1 de la bocana del vientre: 5 m sobre 68 × 0,12 = 8,16 m (0,61); se usa en todo el "
            "vientre",
        ),
        "side": (
            0.59,
            "assumed",
            "el plano no da U1 del costado: promedio del dorso (0,56) y del vientre (0,61)",
        ),
    },
    "headrope": {
        "length_m": 39.4,
        "wing_m": 16.7,
        "bosom_m": 6.0,
        "diameter_mm": 18,
        "material": "cable de acero combinado Ø18 mm (p. 2)",
        "rope": "rope_combinado_6_18mm",
        "pieces_note": "alas = 4 + 3,7 + 7 + 2 m (brida de 4 m incluida); bocana = 6 m (fig. 3)",
    },
    "footrope": {
        "length_m": 45.0,
        "wing_m": 20.0,
        "bosom_m": 5.0,
        "diameter_mm": 22,
        "material": "cable de acero combinado Ø22 mm (p. 2)",
        "rope": "rope_combinado_6_22mm",
        "pieces_note": "alas = 4 + 3,7 + 3,3 + 7 + 2 m (brida de 4 m incluida); bocana = 5 m "
        "(fig. 3)",
    },
    "simulated": [
        {
            "speed_kn": 4.0,
            "vertical_opening_m": 1.5,
            "horizontal_opening_m": 17.9,
            "drag_kgf": 5350.7,
            "note": "resultados de DynamiT del INIDEP para la red modificada (p. 6, «resistencia "
            "al avance»): modelo, no mediciones; el informe no da la separación de portones",
        }
    ],
    "notes": [
        "El cuerpo cierra en 75 mallas de 80 mm (6,00 m) sobre el copo de 100 mallas de 60 mm "
        "(6,00 m) en cada cara; el costado termina en una malla. Es la corrección del «exceso de "
        "material» de la red original (fig. 2).",
        _ROPES_027.format(
            rs="39,4",
            pieces_s="4 + 3,7 + 7 + 2",
            bs="6",
            ri="45,0",
            pieces_i="4 + 3,7 + 3,3 + 7 + 2",
            bi="5",
            legs=" y tramos de 3,7 m en la lima y de 3,7 + 3,3 m en el burlón",
        ),
        _RIG_NOTE_027,
        "Hilos: el informe no los da (la fig. 3 no rotula el copo); se suponen los de la fig. 2 "
        "(A VERIFICAR).",
    ],
    "status": "published",
}

# =================================================================================================
# IAT 75/2023: redes de Pesquera Deseado
# =================================================================================================
_IAT075 = {
    "key": "roth2023iat075",
    "url": "https://marabiertonew.inidep.edu.ar/server/api/core/bitstreams/"
    "d3517485-a2a7-4f70-9674-b6e22ffd433f/content",
    "accessed": ACCESSED_198,
}
_SOURCE_075_1 = {
    **_IAT075,
    "title": "INIDEP IAT 75/23 (Roth y Rubio 2023), fig. 1: red tangonera propuesta por Pesquera "
    "Deseado en 2023",
    "figure": "Figura 1",
    "page": "3",
}
_SOURCE_075_2 = {
    **_IAT075,
    "title": "INIDEP IAT 75/23 (Roth y Rubio 2023), fig. 2: red tradicional de baja abertura "
    "vertical de Pesquera Deseado",
    "figure": "Figura 2",
    "page": "4",
}

_DESIGN_075: dict[str, tuple[Any, str, str | None]] = {
    "vessel_id": (
        "ar_tangonero_1998",
        "assumed",
        "IAT 75/2023 no nombra el buque: tangonero típico de la flota argentina (media de 1998)",
    ),
    "door_length_m": (
        2.86,
        "assumed",
        "IAT 75/2023 da el área (4,08 m², transcrita, p. 2) pero no las medidas: proporción "
        "alto/largo 0,5 del portón plano genérico del catálogo, √(4,08/0,5) = 2,86 m (como ITO "
        "043/2022); alto ≤ 1,50 m por la Res. CFP 7/2018, art. 4. A VERIFICAR",
    ),
    "door_height_m": (1.43, "assumed", "0,5 × 2,86 m (ver door_length_m). A VERIFICAR"),
    "door_weight_air_kg": (
        530.0,
        "transcribed",
        "«portones rectangulares planos de madera con refuerzos de acero de 4,08 m2 de área y "
        "530 kg de peso cada uno» (p. 2; ITO 043/2022 da 540 kg)",
    ),
    "depth_m": (
        LANGOSTINO_DEPTH_M,
        "assumed",
        "IAT 75/2023 no da la profundidad de las simulaciones: la de la flota langostinera "
        "(trawlkit.catalog.LANGOSTINO_DEPTH_M; 70–110 m)",
    ),
    "outrigger_bridle_m": (
        70.0,
        "transcribed",
        "«tijera de 70 m de longitud confeccionada en cable de acero de 22 mm» (p. 2)",
    ),
    "outrigger_bridle_diameter_mm": (22.0, "transcribed", "cable de acero de 22 mm (p. 2)"),
    "speed_kn": (
        3.5,
        "transcribed",
        "una de las cinco velocidades simuladas (4; 3,5; 3; 2,8 y 2,5 nudos, p. 2), la de ITO 043",
    ),
}
_RIGGING_075 = {
    "doors": "rectangulares planos de madera con refuerzos de acero, 4,08 m² y 530 kg cada uno",
    "bridle": "tijera de 70 m de cable de acero de 22 mm",
    "warp": "acero de 24 mm con alma de acero",
}
_RIG_NOTE_075 = (
    "Aparejo de las simulaciones (p. 2): tijera de 70 m de cable de acero de 22 mm, cable de "
    "arrastre de acero de 24 mm con alma de acero, portones rectangulares planos de madera con "
    "refuerzos de acero de 4,08 m² y 530 kg; 4; 3,5; 3; 2,8 y 2,5 nudos. El informe no da las "
    "cañas, la profundidad ni el fondo."
)
_ROPE_KIND_075 = {
    "diameter_mm": (
        "assumed",
        "el plano no da el material ni el diámetro de las relingas: los de ITO 043/2022 (misma "
        "empresa y aparejo). A VERIFICAR",
    ),
}
_SIDE_NOTE_075 = (
    "Tramo trasero del costado; el tramo delantero junto a las alas ({front}) no se modela, como "
    "en ITO 043."
)
_LOWER_26 = (
    "El vientre termina en «26» mallas de 80 mm (2,08 m) según el plano, sobre el copo de 70 "
    "mallas de 60 mm (4,20 m); el corte 1N4B del paño daría {cut} mallas ({cut_m} m). Se "
    "transcribe como se lee: A VERIFICAR."
)
_SIM_075 = (
    "resultados de DynamiT del INIDEP (tabla 1, p. 5): modelo, no mediciones; «tensión» en kg; "
    "el informe no da la separación de portones"
)


def _sim(
    av: tuple[float, ...], ah: tuple[float, ...], ten: tuple[float, ...], note: str
) -> list[dict[str, Any]]:
    return [
        {
            "speed_kn": v,
            "vertical_opening_m": a,
            "horizontal_opening_m": h,
            "warp_tension_kgf": t,
            "note": note,
        }
        for v, a, h, t in zip((4.0, 3.5, 3.0, 2.8, 2.5), av, ah, ten, strict=True)
    ]


_D3 = ("transcribed", "«hilo de polietileno de 3 mm de diámetro» (p. 2)")
_D19 = ("transcribed", "«hilo de polietileno de 1,9 mm de diámetro» (p. 2)")
_D_NY = (
    "assumed",
    "«60 mm, de nylon, en el copo, de las mismas dimensiones que el de las redes utilizadas "
    "habitualmente» (p. 2): nylon de Ø3 mm del copo de ITO 043/2022. A VERIFICAR",
)

# --- Fig. 1: red propuesta (2023) -------------------------------------------------------------
IAT075_1_PANELS = [
    ("UW1", "upper", "wing", 2, 160, R_PE3, 1, 40, 38, "AN / AB", "PE"),
    ("UW2", "upper", "wing", 2, 160, R_PE3, 40, 65, rows(13.5), "AN / 1T2B", "PE"),
    ("U1", "upper", "body", 1, 160, R_PE3, 208, 26, rows(136.5), "1N4B", "PE"),
    ("UC", "upper", "codend", 1, 60, R_NY3, 70, 70, 300, "AN", "PA"),
    ("LW1", "lower", "wing", 2, 80, R_PE19, 1, 75, 68, "AN / AB", "PE"),
    ("LW2", "lower", "wing", 2, 80, R_PE19, 75, 126, rows(25.5), "AN / 1T2B", "PE"),
    ("L1", "lower", "body", 1, 80, R_PE19, 375, 26, 247, "1N4B", "PE"),
    ("LC", "lower", "codend", 1, 60, R_NY3, 70, 70, 300, "AN", "PA"),
    ("S1", "side", "body", 2, 140, R_PE3, 35, 13, rows(155.5), "6N2B / AN", "PE"),
]
_D075_1 = {
    "UW1": _D3,
    "UW2": _D3,
    "U1": _D3,
    "UC": _D_NY,
    "LW1": _D19,
    "LW2": _D19,
    "L1": _D19,
    "LC": _D_NY,
    "S1": _D3,
}

IAT075_1: dict[str, Any] = {
    "id": "inidep_iat075_tangonera_propuesta",
    "name": "Red tangonera propuesta por Pesquera Deseado en 2023 (IAT 75/2023, fig. 1)",
    "description": (
        "Red tangonera de langostino de Pesquera Deseado SAU evaluada en DynamiT por el INIDEP: "
        "dorso de 160 mm y costados de 140 mm en PE de 3 mm, vientre de 80 mm en PE de 1,9 mm y "
        "copo de 60 mm de nylon; lima de 34,84 m y burlón de 36,9 m (Roth y Rubio 2023)."
    ),
    "family": "bottom",
    "rig": "outrigger",
    "vessel_hp": (948.7, 948.7),
    "target_species": "langostino patagónico (Pleoticus muelleri)",
    "species": {"name": "Langostino", "scientific_name": "Pleoticus muelleri"},
    "source": _SOURCE_075_1,
    "material": "PE",
    "twine_diameter": {R_PE3: 3.0, R_PE19: 1.9, R_NY3: 3.0},
    "panels": IAT075_1_PANELS,
    "panel_notes": {
        "U1": "El texto describe un sector de malla cuadrada en la parte delantera del dorso; el "
        "plano no lo dimensiona y no se modela (A VERIFICAR).",
        "L1": _LOWER_26.format(cut=46, cut_m="3,68"),
        "S1": _SIDE_NOTE_075.format(front="35 mallas, 19,5 + 39,5 filas AN")
        + " Filas: 14,5 + 141 = 155,5 desde el comienzo del corte; termina en 13 mallas sin "
        "cabo de cierre.",
    },
    "overrides": _merge(
        _twine(IAT075_1_PANELS, _D075_1),
        _half_rows(
            UW2="13,5 filas redondeadas a 14",
            U1="136,5 filas redondeadas a 137",
            LW2="25,5 filas redondeadas a 26",
            S1="14,5 + 141 = 155,5 filas redondeadas a 156",
        ),
        {
            "UW1": {
                "mesh_mm": ("transcribed", "160 mm en todo el dorso (p. 2 y columna del plano)")
            },
            "S1": {"mesh_mm": ("transcribed", "140 mm en los costados (p. 2)")},
        },
    ),
    "hanging": {
        "upper": (
            0.76,
            "derived",
            "U1 de la bocana del dorso: 9,54 m sobre (78) mallas de 160 mm = 12,48 m (0,76); se "
            "usa en todo el dorso",
        ),
        "lower": (
            0.76,
            "derived",
            "U1 de la bocana del vientre: 7,5 m sobre (123) mallas de 80 mm = 9,84 m (0,76); se "
            "usa en todo el vientre",
        ),
        "side": (
            0.76,
            "assumed",
            "el plano no da U1 del costado: el del dorso y del vientre (0,76)",
        ),
    },
    "headrope": {
        "length_m": 34.84,
        "wing_m": 12.65,
        "bosom_m": 9.54,
        "diameter_mm": 22,
        "material": "relinga del plano (material no publicado; combinado Ø22 mm supuesto)",
        "rope": "rope_combinado_6_22mm",
        "pieces_note": "alas = 3,25 + 6,15 + 3,25 m; bocana = 9,54 m (fig. 1)",
        "pieces": _ROPE_KIND_075,
    },
    "footrope": {
        "length_m": 36.9,
        "wing_m": 14.7,
        "bosom_m": 7.5,
        "diameter_mm": 24,
        "material": "relinga del plano (material no publicado; cable mixto Ø24 mm supuesto)",
        "rope": "rope_combinado_6_24mm",
        "pieces_note": "alas = 3,25 + 2,75 + 5,45 + 3,25 m; bocana = 7,5 m (fig. 1)",
        "pieces": _ROPE_KIND_075,
    },
    "floats": {
        "count": 2,
        "diameter_mm": 200,
        "kind": "assumed",
        "note": "el plano no da la flotación de la red; el informe recomienda «colocar dos "
        "flotadores adicionales de 200 mm» (3 kg de flotación, «sobre la relinga superior, en la "
        "unión de la base de las alas con el square», pp. 1 y 7) y la simula así: se modela esa "
        "variante («PROPUESTA + 2 FL»). A VERIFICAR",
    },
    "design": _DESIGN_075,
    "simulated": _sim(
        (1.1, 1.1, 1.2, 1.2, 1.3),
        (13.9, 13.7, 13.3, 13.2, 12.8),
        (5217.2, 4221.3, 3351.6, 3051.7, 2617.1),
        _SIM_075 + " (red propuesta con los dos flotadores de 200 mm, la variante del catálogo)",
    )
    + _sim(
        (0.9, 0.9, 0.9, 0.9, 0.9),
        (13.9, 13.7, 13.4, 13.2, 12.9),
        (5205.6, 4211.8, 3349.8, 3042.3, 2611.3),
        _SIM_075 + " (red propuesta sin los dos flotadores agregados)",
    ),
    "rigging": _RIGGING_075,
    "notes": [
        "BORRADOR: "
        + _LOWER_26.format(cut=46, cut_m="3,68")
        + " El dorso cierra (26 × 160 mm = 4,16 m frente a 4,20 m). Los costados terminan en 13 "
        "mallas de 140 mm sin cabo de cierre: el plano no dice cómo se unen al copo.",
        "Flotación: se modela la variante con los dos flotadores de 200 mm que recomienda el "
        "informe (DynamiT: AV de 1,1–1,3 m y AH de 12,8–13,9 m, tabla 1, p. 5); sin ellos la AV "
        "de DynamiT queda en 0,9 m a todas las velocidades. Sin flotación publicada el motor "
        "tomaría la del libro (52 boyas), que no corresponde a esta red.",
        "Relingas: 2 × (3,25 + 6,15 + 3,25) + 9,54 = 34,84 m y 2 × (3,25 + 2,75 + 5,45 + 3,25) + "
        "7,5 = 36,9 m; los tramos verticales de 3,25 m (y 2,75 m en el burlón) van por delante de "
        "la punta del ala.",
        _RIG_NOTE_075,
    ],
    "status": "draft",
}

# --- Fig. 2: red tradicional ------------------------------------------------------------------
IAT075_2_PANELS = [
    ("UW1", "upper", "wing", 2, 80, R_PE19, 1, 77, 77, "AN / AB", "PE"),
    ("UW2", "upper", "wing", 2, 80, R_PE19, 77, 128, rows(25.5), "AN / 1T2B", "PE"),
    ("U1", "upper", "body", 1, 80, R_PE19, 412, 321, rows(68.5), "1N4B", "PE"),
    ("U2", "upper", "body", 1, 60, R_PE19, 428, 66, 272, "1N4B", "PE"),
    ("UC", "upper", "codend", 1, 60, R_NY3, 70, 70, 300, "AN", "PA"),
    ("LW1", "lower", "wing", 2, 80, R_PE19, 1, 83, rows(85.5), "AN / AB", "PE"),
    ("LW2", "lower", "wing", 2, 80, R_PE19, 83, 117, rows(25.5), "1N4B / 1T2B", "PE"),
    ("L1", "lower", "body", 1, 60, R_PE19, 428, 26, 272, "1N4B", "PE"),
    ("LC", "lower", "codend", 1, 60, R_NY3, 70, 70, 300, "AN", "PA"),
    ("S1", "side", "body", 2, 80, R_PE19, 62, 53, rows(68.5), "6N2B / AN", "PE"),
    ("S2", "side", "body", 2, 60, R_PE19, 70, 25, 272, "5N2B / AN", "PE"),
]
_D_TRAD = (
    "assumed",
    "IAT 75/2023 no da el hilo de la red tradicional («polietileno de 80 mm en el cuerpo», "
    "p. 2): PE de Ø1,9 mm, el de la malla de 80 mm de la red propuesta. A VERIFICAR",
)
_D075_2 = {r[0]: (_D_NY if r[2] == "codend" else _D_TRAD) for r in IAT075_2_PANELS}

IAT075_2: dict[str, Any] = {
    **IAT075_1,
    "id": "inidep_iat075_tangonera_tradicional",
    # El informe no da la flotación de la red tradicional: la del libro, como ITO 043.
    "floats": None,
    "name": "Red tangonera tradicional de Pesquera Deseado (IAT 75/2023, fig. 2)",
    "description": (
        "Red tangonera de langostino de baja abertura vertical que usa Pesquera Deseado SAU (red "
        "de control de IAT 75/2023): alas y cuerpo delantero de 80 mm, cuerpo trasero de 60 mm de "
        "PE y copo de 60 mm de nylon; lima de 34,84 m y burlón de 41,34 m (Roth y Rubio 2023)."
    ),
    "source": _SOURCE_075_2,
    "twine_diameter": {R_PE19: 1.9, R_NY3: 3.0},
    "panels": IAT075_2_PANELS,
    "panel_notes": {
        "LW1": "68 filas con el costado exterior recto (AN) y 17,5 filas más en las que el borde "
        "exterior se corta hacia adentro (sin rótulo); 83 mallas en la línea de puntos.",
        "LW2": "Ala de 83 mallas en la línea de puntos y 66 + 51 = 117 al pie; el corte exterior "
        "(83 − 66 = 17 mallas en 25,5 filas: 1N4B) no está rotulado y se deriva.",
        "L1": _LOWER_26.format(cut=66, cut_m="3,96").replace("80 mm (2,08 m)", "60 mm (1,56 m)")
        + " Las alas (117 mallas de 80 mm = 156 de 60 mm) y la bocana (116 de 60 mm) apoyan "
        "sobre las 428 mallas de 60 mm del cuerpo: el plano rotula «156 (116) 156».",
        "U2": "El texto dice «80 mm en el cuerpo», pero el plano da 60 mm en el cuerpo trasero "
        "(321 × 80 mm = 428 × 60 mm = 25,68 m).",
        "S1": _SIDE_NOTE_075.format(front="62 mallas de 80 mm, 34 + 68,5 filas AN"),
    },
    "overrides": _merge(
        _twine(IAT075_2_PANELS, _D075_2),
        _half_rows(
            UW2="25,5 filas redondeadas a 26",
            U1="68,5 filas redondeadas a 69",
            LW1="68 + 17,5 = 85,5 filas redondeadas a 86",
            LW2="25,5 filas redondeadas a 26",
            S1="68,5 filas redondeadas a 69",
        ),
        {
            "LW1": {"meshes_bottom": ("transcribed", "«83» en la línea de puntos del vientre")},
            "LW2": {
                "meshes_bottom": ("derived", "66 + 51 mallas (rótulos del pie del ala)"),
                "cut_code": (
                    "derived",
                    "1T2B rotulado en el borde de la relinga; 1N4B del borde exterior derivado "
                    "de 83 → 66 mallas en 25,5 filas",
                ),
            },
        },
    ),
    "hanging": {
        "upper": (
            0.76,
            "derived",
            "U1 de la bocana del dorso: 9,54 m sobre (156) mallas de 80 mm = 12,48 m (0,76); se "
            "usa en todo el dorso",
        ),
        "lower": (
            0.76,
            "derived",
            "U1 de la bocana del vientre: 5,28 m sobre (116) mallas de 60 mm = 6,96 m (0,76); se "
            "usa en todo el vientre",
        ),
        "side": (
            0.76,
            "assumed",
            "el plano no da U1 del costado: el del dorso y del vientre (0,76)",
        ),
    },
    "footrope": {
        "length_m": 41.34,
        "wing_m": 18.03,
        "bosom_m": 5.28,
        "diameter_mm": 24,
        "material": "relinga del plano (material no publicado; cable mixto Ø24 mm supuesto)",
        "rope": "rope_combinado_6_24mm",
        "pieces_note": "alas = 3,25 + 2,75 + 8,78 + 3,25 m; bocana = 5,28 m (fig. 2)",
        "pieces": _ROPE_KIND_075,
    },
    "simulated": _sim(
        (1.0, 1.1, 1.1, 1.2, 1.3),
        (13.5, 13.3, 13.0, 12.8, 12.5),
        (5015.0, 4054.3, 3229.9, 2932.7, 2523.0),
        _SIM_075 + " (red convencional)",
    ),
    "notes": [
        "BORRADOR: "
        + _LOWER_26.format(cut=66, cut_m="3,96").replace("80 mm (2,08 m)", "60 mm (1,56 m)")
        + " El dorso cierra (66 × 60 mm = 3,96 m frente a 4,20 m, 6 %). Los costados terminan "
        "en 25 mallas de 60 mm sin cabo de cierre. Además, los costados modelados (69 filas de "
        "80 mm y 272 de 60 mm: 21,84 m estirados, como el cuerpo del dorso) son un 25 % más "
        "largos que el cuerpo del vientre (sólo las 272 filas de 60 mm, 16,32 m; el vientre no "
        "tiene el tramo de 68,5 filas de 80 mm del dorso): el motor los reparte por largo con la "
        "tolerancia de 30 % de trawlkit.topology.SIDE_LENGTH_TOL (Fase 19.8c).",
        "La fig. 2 de ITO 043/2022 lleva el mismo título («red tradicional de baja abertura "
        "vertical»), pero no se comparó número por número con esta. Lima 2 × (3,25 + 6,15 + "
        "3,25) + 9,54 = 34,84 m; burlón 2 × (3,25 + 2,75 + 8,78 + 3,25) + 5,28 = 41,34 m.",
        _RIG_NOTE_075,
    ],
    "status": "draft",
}

NETS_198: list[dict[str, Any]] = [IAT027_2, IAT027_3, IAT075_1, IAT075_2]
