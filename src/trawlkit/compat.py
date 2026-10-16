"""Modo de compatibilidad con el modelo Excel original.

El modelo Excel contiene varias erratas de cálculo (ver ``docs/erratas.md``). Cada función del
motor que se ve afectada acepta un parámetro ``compat``:

* :attr:`Compat.EXCEL` reproduce exactamente el número del Excel, errata incluida. Se usa para
  validar la migración contra los valores de referencia (``tests/golden``).
* :attr:`Compat.CORRECTED` aplica la fórmula correcta. Es el modo por defecto para uso real.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Compat(StrEnum):
    """Modo de compatibilidad del motor de cálculo."""

    EXCEL = "excel"
    CORRECTED = "corrected"


@dataclass(frozen=True)
class Erratum:
    """Errata documentada del modelo Excel original."""

    key: str
    sheet: str
    cell: str
    description: str


#: Registro de erratas conocidas. Cada función que las replica en modo EXCEL referencia su ``key``.
ERRATA: tuple[Erratum, ...] = (
    Erratum(
        "cut_ratio_first_panel",
        "Paños de red y cortes",
        "H274:I277",
        "Todos los paneles usan la razón de corte del primero ($G$273).",
    ),
    Erratum(
        "twine_density_units",
        "Paños de red y cortes",
        "L55",
        "Densidad del hilo dimensionalmente incorrecta (A[mm²]·runnage).",
    ),
    Erratum(
        "filtration_double_count",
        "Mecánica de la Red",
        "J17",
        "SUM(J16,J6:J12,J16) cuenta J16 dos veces.",
    ),
    Erratum(
        "hamuro_sin_degrees",
        "Resistencia de la RED",
        "D113",
        "SIN(DEGREES(x)) en lugar de SIN(RADIANS(x)).",
    ),
    Erratum(
        "hamuro_mod_uses_std_dl",
        "Resistencia de la RED",
        "E117",
        "La variante modificada usa el índice de filtración de la estándar.",
    ),
    Erratum(
        "reid_fixed_denominator",
        "Resistencia de la RED",
        "C154:C162",
        "Denominador fijo $B$154 (1 nudo) para todas las velocidades.",
    ),
    Erratum(
        "drag_average_pollution",
        "Resistencia de la RED",
        "R302:R310",
        "El promedio incluye la columna de velocidad y el tiro de Nomura.",
    ),
    Erratum(
        "door_force_mixed_angles",
        "Portones y aparejamiento",
        "D252",
        "Mezcla SIN(RADIANS(x)) y SIN(x) con x en grados.",
    ),
    Erratum(
        "float_reynolds",
        "Flotación y Lastre",
        "H138",
        "Reynolds calculado como π·D²·v/ν en lugar de v·D/ν.",
    ),
    Erratum(
        "warp_total_omits_doors",
        "Cables de Remolque",
        "H118",
        "La resistencia total omite la de los portones (ROB).",
    ),
    Erratum(
        "warp_cd_horizontal_angle",
        "Cables de Remolque",
        "E103:E106",
        "El CD del cable se toma con la divergencia en planta δ2 = 4.3° (→ 0.02) en vez del ángulo "
        "de ataque del cable al flujo, y por la fila más cercana de la tabla, sin interpolar.",
    ),
    Erratum(
        "warp_undersized",
        "Cables de Remolque",
        "E267:E272",
        "Cable de 12 mm (8.55 t) seleccionado con carga mínima requerida de 8.8 t.",
    ),
    Erratum(
        "mod_length_wrong_rows",
        "Dimensiones de la Red",
        "G48",
        "Largo de la red modificada suma filas del plano inferior en vez de la bolsa.",
    ),
    Erratum(
        "footrope_mid_truncation",
        "Dimensiones de la Red",
        "F46",
        "MID() sobre números trunca el burlón a 33.3 m (el valor completo es 33.389 m).",
    ),
    Erratum(
        "dpa_std_uses_mod_edy",
        "Mecánica de la Red",
        "P164",
        "La DPA de Fridman de la red estándar usa el coeficiente Edy de la modificada.",
    ),
    Erratum(
        "nomura_column_links_hamuro",
        "Potencia Disponible Arrastre OK",
        "G319,G342,G362",
        "La columna 'Nomura' de los resúmenes enlaza a los resultados de Hamuro.",
    ),
    Erratum(
        "sweep_degrees_of_sine",
        "Portones y aparejamiento",
        "G71",
        "DEGREES(SIN(20)) con el ángulo en grados y error de precedencia.",
    ),
    Erratum(
        "nomura_ratio_typo",
        "Tablas de Referencias",
        "G18,G21",
        "Proporción 10.6 donde el resto de la tabla sugiere 1.06.",
    ),
    Erratum(
        "panel_f_cut_na",
        "Paños de red y cortes",
        "T122",
        "VLOOKUP/MATCH de la razón de corte del panel F devuelve #N/A.",
    ),
    Erratum(
        "codend_minor_side_uses_depth",
        "Mecánica de la Red",
        "K36:K37",
        "Lado menor de las bolsas I/J = Paños!H224 (N = 200) en vez de H223 (T2 = 113); "
        "infla Ss de 38.75 a 40.90 m² y St de 308.6 a 315.6 m².",
    ),
    Erratum(
        "panel_b_cut_uses_plan_coef",
        "Paños de red y cortes",
        "S62",
        "La razón de corte del paño B usa P55 (coeficiente de plano 0.5) en vez de T56 (N).",
    ),
    Erratum(
        "panel_b_cut_code_lookup_a",
        "Paños de red y cortes",
        "T62",
        "El código de corte del paño B se busca con la razón del paño A (H63).",
    ),
    Erratum(
        "net_weight_ignores_panel_count",
        "Mecánica de la Red",
        "O107,O109",
        "El peso total suma las filas sin multiplicar por la cantidad de paneles iguales.",
    ),
    Erratum(
        "catenary_ratio_hardcoded",
        "Mecánica de la Red",
        "O266",
        "fL/L = 0.216 fijo (corresponde a DPA/L = 0.87); el DPA/L del modelo (0.45) queda fuera "
        "de la tabla de catenaria.",
    ),
    Erratum(
        "float_lookup_unsorted",
        "Flotación y Lastre",
        "F92",
        "LOOKUP del diámetro de boya sobre el vector 'cincuenta' sin ordenar.",
    ),
    Erratum(
        "flotation_rounding_inconsistent",
        "Flotación y Lastre",
        "M43:M50",
        "ROUNDDOWN sólo en M42 y en el bloque de 180 HP; el resto de la columna sin redondear.",
    ),
)

ERRATA_BY_KEY: dict[str, Erratum] = {e.key: e for e in ERRATA}
