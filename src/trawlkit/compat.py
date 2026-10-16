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
)

ERRATA_BY_KEY: dict[str, Erratum] = {e.key: e for e in ERRATA}
