"""Resistencia hidrodinámica de la red (hoja 'Resistencia de la RED').

Reúne las trece fórmulas empíricas de resistencia (RN, en toneladas-fuerza) que el modelo
original evalúa para las variantes estándar y modificada de la red, más el tiro disponible de
Nomura y los resúmenes (tablas en t y kgf, promedio por velocidad y promedio por método).

Convenciones:

* ``dl`` es el índice de filtración ``d/l`` (adimensional, 'Mecánica de la Red'!K15/K17);
* ``v_ms`` velocidad de arrastre en m/s, ``v_kn`` en nudos (1 kn = 0.5144 m/s en el Excel);
* las superficies ``st`` (trabajo) y ``ss`` (sólida) en m²;
* todas las funciones devuelven toneladas-fuerza y aceptan escalares o ``numpy`` arrays.

La RN de diseño que usa el resto del libro es la de Aberdeen demersal (:data:`DESIGN_METHOD`).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

from trawlkit.compat import Compat
from trawlkit.units import KNOT_TO_MS

FloatArray = NDArray[np.float64]
Speeds = float | Sequence[float] | NDArray[np.floating[Any]]

#: Método cuyo resultado usa el resto del libro como RN de diseño (columna N del resumen).
DESIGN_METHOD = "aberdeen_demersal"

#: Columnas del resumen 'Resistencia de la RED'!C302:Q310 en el orden de la hoja.
SUMMARY_COLUMNS: tuple[str, ...] = (
    "tauti_nomura_shu",
    "tauti_headrope",
    "tauti_footrope",
    "koyama_1974",
    "koyama_1984",
    "hamuro",
    "nomura_150",
    "nomura_180",
    "reid",
    "robertson",
    "maclennan",
    "aberdeen_demersal",
    "aberdeen_pelagic",
    "fridman",
    "dickson",
)

#: Columnas que son resistencia de la red (excluye Nomura I/J, que es tiro disponible).
RN_METHODS: tuple[str, ...] = tuple(c for c in SUMMARY_COLUMNS if not c.startswith("nomura"))

#: Factor m² → ft² del bloque de Dickson ('Resistencia de la RED'!F275).
DICKSON_M2_TO_FT2 = 10.76
#: NHP de referencia de Nomura (columnas I/J del resumen, celdas D130/E130).
NOMURA_NHP: tuple[float, float] = (150.0, 180.0)

_T_TO_KGF = 1000.0


def _arr(v: Speeds) -> FloatArray:
    return np.asarray(v, dtype=float)


# ----------------------------------------------------------------------------------------------
# Fórmulas por método (puras)
# ----------------------------------------------------------------------------------------------


def tauti_nomura_shu(dl: float, a_m: float, v_ms: Speeds) -> FloatArray:
    """RN de Tauti–Nomura–Shu (1974) para redes de dos caras.

    ``RN [t] = 27 · d/l · a² · v^1.45 / 1000`` con ``a`` la circunferencia estirada [m] y
    ``v`` en m/s. Celda representativa: 'Resistencia de la RED'!D11
    (``=(27*$E$4*($E$6^2)*(C11^1.45))/1000``).
    """
    v = _arr(v_ms)
    return 27.0 * dl * a_m**2 * v**1.45 / _T_TO_KGF


def tauti_rope(dl: float, rope_m: float, v_ms: Speeds) -> FloatArray:
    """RN de Tauti referida a una relinga (lima o burlón).

    ``RN [t] = 25 · d/l · L² · v² / 1000`` con ``L`` la longitud de la relinga [m] y ``v`` en
    m/s. Celdas representativas: D30 (lima, ``=(25*$E$4*$I$25^2*C30^2)/1000``) y L30
    (burlón, ``=(25*$E$4*$I$26^2*K30^2)/1000``).
    """
    v = _arr(v_ms)
    return 25.0 * dl * rope_m**2 * v**2 / _T_TO_KGF


def koyama_1974(dl: float, a_m: float, b_m: float, v_ms: Speeds) -> FloatArray:
    """RN de Koyama (1974).

    ``RN [t] = 16 · d/l · a · b · v² / 1000`` con ``a`` la circunferencia estirada [m], ``b``
    el largo total de la red con bolsa [m] y ``v`` en m/s. Celda representativa: D74
    (``=(16*$E$4*$E$68*$E$69*(C74^2))/1000``).
    """
    v = _arr(v_ms)
    return 16.0 * dl * a_m * b_m * v**2 / _T_TO_KGF


def koyama_1984(dl: float, a_m: float, l_m: float, v_kn: Speeds) -> FloatArray:
    """RN de Koyama (1984).

    ``RN [t] = 8 · d/l · a · L · v_kn² / 1000`` con ``a`` la circunferencia estirada [m], ``L``
    el largo de la red sin bolsa [m] y la velocidad **en nudos**. Celda representativa: C91
    (``=(8*$E$4*$E$6*$D$86*B91^2)/1000``).
    """
    v = _arr(v_kn)
    return 8.0 * dl * a_m * l_m * v**2 / _T_TO_KGF


def hamuro_sin_alpha(alpha_deg: float, compat: Compat = Compat.CORRECTED) -> float:
    """``|sin α|`` del método de Hamuro (celda D113).

    En modo :attr:`Compat.EXCEL` reproduce la errata ``hamuro_sin_degrees``:
    ``=ABS(SIN(DEGREES(D112)))`` (convierte grados → "grados" y evalúa el seno en radianes).
    En modo corregido es ``|sin(radians(α))|``.
    """
    if compat is Compat.EXCEL:
        return float(abs(np.sin(np.degrees(alpha_deg))))
    return float(abs(np.sin(np.radians(alpha_deg))))


def hamuro(
    dl: float,
    st_m2: float,
    alpha_deg: float,
    v_ms: Speeds,
    compat: Compat = Compat.CORRECTED,
) -> FloatArray:
    """RN de Hamuro (Tokyo University of Fisheries).

    ``RN [t] = 191 · d/l · v² · St · |sin α| / 1000`` con ``St`` la superficie de trabajo [m²],
    ``α`` el ángulo de ataque [°] y ``v`` en m/s. Celda representativa: D117
    (``=(191*$E$4*(C117^2)*$D$110*$D$113)/1000``).

    Errata ``hamuro_sin_degrees`` (D113): ver :func:`hamuro_sin_alpha`. La errata
    ``hamuro_mod_uses_std_dl`` (E117 usa ``$E$4``) se aplica en :func:`drag_table`, que es
    donde se elige el ``dl`` de cada variante.
    """
    v = _arr(v_ms)
    return 191.0 * dl * v**2 * st_m2 * hamuro_sin_alpha(alpha_deg, compat) / _T_TO_KGF


def nomura(nhp: float, v_ms: Speeds) -> FloatArray:
    """Tiro disponible según Nomura (1981) para una potencia neta ``NHP`` [HP].

    ``T [t] = (7.2 · NHP / v) / 1000`` con ``v`` en m/s. No es una resistencia de la red sino
    el tiro que el buque puede ejercer a esa velocidad. Celda representativa: D132
    (``=((7.2*150)/C132)/1000``).
    """
    v = _arr(v_ms)
    return (7.2 * nhp / v) / _T_TO_KGF


def reid(
    ss_m2: float,
    v_kn: Speeds,
    compat: Compat = Compat.CORRECTED,
    v_ref_kn: float | None = None,
) -> FloatArray:
    """RN de A. J. Reid (1977) para redes pelágicas.

    ``RN [t] = v_kn² · Ss / (54.72 · v_kn + 115.2)`` con ``Ss`` la superficie sólida [m²] y la
    velocidad en nudos. Celda representativa: C154
    (``=(($B154^2)*$F$149)/(54.72*$B$154+115.2)``).

    Errata ``reid_fixed_denominator`` (C154:C162): el denominador usa ``$B$154`` (1 kn) en
    todas las filas. En modo :attr:`Compat.EXCEL` se usa ``v_ref_kn`` en el denominador
    (por defecto la primera velocidad del vector); en modo corregido cada fila usa su propia
    velocidad.
    """
    v = _arr(v_kn)
    if compat is Compat.EXCEL:
        v_den: float | FloatArray = float(np.ravel(v)[0]) if v_ref_kn is None else v_ref_kn
    else:
        v_den = v
    return v**2 * ss_m2 / (54.72 * v_den + 115.2)


def robertson(ss_m2: float, v_kn: Speeds) -> FloatArray:
    """RN de J. H. B. Robertson (1981) para redes semipelágicas.

    ``RN [t] = v_kn² · Ss / (66.18 · v_kn + 41.5)`` con ``Ss`` la superficie sólida [m²] y la
    velocidad en nudos. Celda representativa: C174
    (``=(($B174^2)*$F$169)/((66.18*$B174)+41.5)``).
    """
    v = _arr(v_kn)
    return v**2 * ss_m2 / (66.18 * v + 41.5)


def maclennan(ss_m2: float, v_kn: Speeds) -> FloatArray:
    """RN de MacLennan (1981) para redes de fondo de polietileno.

    ``RN [t] = Ss · (61.2 + 46.6 · v_kn²) / (1 + 0.0641 · v_kn) / 9807`` (el resultado en N se
    pasa a t con g = 9.807). ``Ss`` en m², velocidad en nudos. Celda representativa: C196
    (``=($F$191*(61.2+46.6*($B196^2))/(1+(0.0641*$B196)))/9807``).
    """
    v = _arr(v_kn)
    return (ss_m2 * (61.2 + 46.6 * v**2) / (1.0 + 0.0641 * v)) / 9807.0


def aberdeen_demersal(ss_m2: float, v_kn: Speeds) -> FloatArray:
    """RN del Marine Laboratory Aberdeen para redes demersales de polietileno.

    ``RN [t] = Ss · (0.00624 + 0.00475 · v_kn²) / (1 + 0.0641 · v_kn)`` con ``Ss`` en m² y la
    velocidad en nudos. Es la **RN de diseño** que usa el resto del libro. Celda
    representativa: C214 (``=$F$209*(((0.00624+0.00475*($B214^2))/(1+0.0641*$B214)))``).
    """
    v = _arr(v_kn)
    return ss_m2 * ((0.00624 + 0.00475 * v**2) / (1.0 + 0.0641 * v))


def aberdeen_pelagic(ss_m2: float, v_kn: Speeds) -> FloatArray:
    """RN del Marine Laboratory Aberdeen para redes pelágicas de nylon.

    ``RN [t] = Ss · 0.00868 · v_kn² / (1 + 0.00475 · v_kn)`` con ``Ss`` en m² y la velocidad
    en nudos. Celda representativa: C237
    (``=$F$232*((0.00868*($B237^2))/(1+0.00475*$B237))``).
    """
    v = _arr(v_kn)
    return ss_m2 * ((0.00868 * v**2) / (1.0 + 0.00475 * v))


def fridman(dl: float, st_m2: float, alpha_deg: float, v_ms: Speeds) -> FloatArray:
    """RN de Fridman (1973).

    ``RN [t] = (1.8 + 2α · (d/l − 0.01)) · St · v² / 1000`` con ``α`` el ángulo de ataque
    **en grados** (tal como lo usa la hoja), ``St`` la superficie de trabajo [m²] y ``v`` en
    m/s. Celda representativa: D258
    (``=((1.8+(2*$F$254)*($F$250-0.01))*$F$252*($C258^2))/1000``).
    """
    v = _arr(v_ms)
    return (1.8 + (2.0 * alpha_deg) * (dl - 0.01)) * st_m2 * v**2 / _T_TO_KGF


def dickson(
    st_m2: float,
    dl: float,
    ah_m: Speeds,
    av_m: Speeds,
    m2_to_ft2: float = DICKSON_M2_TO_FT2,
) -> FloatArray:
    """RN de Dickson a partir de la abertura horizontal y vertical de la boca.

    ``RN [t] = (1/125) · St_ft² · d/l · (1 + 6.6·2 · AH · AV) / St_m²`` con ``St_ft² = St_m² ·
    10.76`` (F276 ``=F273*$F$275``), ``AH`` ('Mecánica de la Red'!P164:P172) y ``AV``
    ('Mecánica de la Red'!O272:O280) en m. No depende de la velocidad más que a través de
    ``AH``/``AV``. Celda representativa: E282
    (``=(1/125)*$F$276*($F$271*(((1+(6.6*2*$C282*$D282))/$F$273)))``).
    """
    ah = _arr(ah_m)
    av = _arr(av_m)
    st_ft2 = st_m2 * m2_to_ft2
    return (1.0 / 125.0) * st_ft2 * (dl * ((1.0 + (6.6 * 2.0 * ah * av)) / st_m2))


# ----------------------------------------------------------------------------------------------
# Tabla resumen
# ----------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class DragInputs:
    """Entradas de la hoja 'Resistencia de la RED' para ambas variantes de la red.

    Todas las longitudes en m, superficies en m², ángulo en grados. ``ah_m``/``av_m`` son las
    series de abertura horizontal/vertical de la boca (una por velocidad) que usa Dickson; si
    se omiten, la columna de Dickson queda en ``NaN``.
    """

    dl_std: float
    dl_mod: float
    circumference_m: float
    length_with_bag_std_m: float
    length_with_bag_mod_m: float
    length_without_bag_std_m: float
    length_without_bag_mod_m: float
    st_std_m2: float
    st_mod_m2: float
    ss_std_m2: float
    ss_mod_m2: float
    headrope_m: float
    footrope_m: float
    alpha_deg: float
    nhp: tuple[float, float] = NOMURA_NHP
    ah_m: tuple[float, ...] | None = None
    av_m: tuple[float, ...] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "dl_std": self.dl_std,
            "dl_mod": self.dl_mod,
            "circumference_m": self.circumference_m,
            "length_with_bag_std_m": self.length_with_bag_std_m,
            "length_with_bag_mod_m": self.length_with_bag_mod_m,
            "length_without_bag_std_m": self.length_without_bag_std_m,
            "length_without_bag_mod_m": self.length_without_bag_mod_m,
            "st_std_m2": self.st_std_m2,
            "st_mod_m2": self.st_mod_m2,
            "ss_std_m2": self.ss_std_m2,
            "ss_mod_m2": self.ss_mod_m2,
            "headrope_m": self.headrope_m,
            "footrope_m": self.footrope_m,
            "alpha_deg": self.alpha_deg,
            "nhp": list(self.nhp),
            "ah_m": None if self.ah_m is None else list(self.ah_m),
            "av_m": None if self.av_m is None else list(self.av_m),
        }


@dataclass(frozen=True)
class DragTable:
    """Resumen de resistencias por método y velocidad (A298:S326 / A394:S422).

    ``std``/``mod`` mapean cada columna de :data:`SUMMARY_COLUMNS` a un array alineado con
    ``speed_kn``. ``unit`` es ``"t"`` o ``"kgf"``.
    """

    speed_kn: FloatArray
    speed_ms: FloatArray
    std: Mapping[str, FloatArray]
    mod: Mapping[str, FloatArray]
    unit: str = "t"
    compat: Compat = Compat.CORRECTED
    columns: tuple[str, ...] = field(default=SUMMARY_COLUMNS)

    @property
    def kgf(self) -> DragTable:
        """La misma tabla en kgf (filas 398:421, ``=C302*1000``)."""
        if self.unit == "kgf":
            return self
        return DragTable(
            speed_kn=self.speed_kn,
            speed_ms=self.speed_ms,
            std={k: v * _T_TO_KGF for k, v in self.std.items()},
            mod={k: v * _T_TO_KGF for k, v in self.mod.items()},
            unit="kgf",
            compat=self.compat,
            columns=self.columns,
        )

    def variant(self, name: str) -> Mapping[str, FloatArray]:
        """Columnas de la variante ``"std"`` o ``"mod"``."""
        if name == "std":
            return self.std
        if name == "mod":
            return self.mod
        raise ValueError(f"variante desconocida: {name!r} (use 'std' o 'mod')")

    def design_rn(self, variant: str = "std") -> FloatArray:
        """RN de diseño (:data:`DESIGN_METHOD`, Aberdeen demersal) de la variante."""
        return self.variant(variant)[DESIGN_METHOD]

    def matrix(self, variant: str) -> FloatArray:
        """Matriz (velocidades × columnas) de la variante, en el orden de ``columns``."""
        cols = self.variant(variant)
        return np.column_stack([cols[c] for c in self.columns])

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable (listas de floats)."""
        return {
            "unit": self.unit,
            "compat": str(self.compat),
            "speed_kn": self.speed_kn.tolist(),
            "speed_ms": self.speed_ms.tolist(),
            "std": {k: v.tolist() for k, v in self.std.items()},
            "mod": {k: v.tolist() for k, v in self.mod.items()},
        }


@dataclass(frozen=True)
class DragAverage:
    """Promedio de métodos por velocidad (columna R del resumen) para ambas variantes."""

    std: FloatArray
    mod: FloatArray
    unit: str = "t"

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {"unit": self.unit, "std": self.std.tolist(), "mod": self.mod.tolist()}


def _variant_columns(
    inputs: DragInputs,
    v_kn: FloatArray,
    v_ms: FloatArray,
    variant: str,
    compat: Compat,
) -> dict[str, FloatArray]:
    std = variant == "std"
    dl = inputs.dl_std if std else inputs.dl_mod
    st = inputs.st_std_m2 if std else inputs.st_mod_m2
    ss = inputs.ss_std_m2 if std else inputs.ss_mod_m2
    b_m = inputs.length_with_bag_std_m if std else inputs.length_with_bag_mod_m
    l_m = inputs.length_without_bag_std_m if std else inputs.length_without_bag_mod_m
    # Errata hamuro_mod_uses_std_dl: E117 usa $E$4 (d/l estándar) también para la modificada.
    dl_hamuro = inputs.dl_std if compat is Compat.EXCEL else dl
    if inputs.ah_m is None or inputs.av_m is None:
        dickson_rn = np.full_like(v_kn, np.nan)
    else:
        dickson_rn = dickson(st, dl, inputs.ah_m, inputs.av_m)
    return {
        "tauti_nomura_shu": tauti_nomura_shu(dl, inputs.circumference_m, v_ms),
        "tauti_headrope": tauti_rope(dl, inputs.headrope_m, v_ms),
        "tauti_footrope": tauti_rope(dl, inputs.footrope_m, v_ms),
        "koyama_1974": koyama_1974(dl, inputs.circumference_m, b_m, v_ms),
        "koyama_1984": koyama_1984(dl, inputs.circumference_m, l_m, v_kn),
        "hamuro": hamuro(dl_hamuro, st, inputs.alpha_deg, v_ms, compat),
        "nomura_150": nomura(inputs.nhp[0], v_ms),
        "nomura_180": nomura(inputs.nhp[1], v_ms),
        "reid": reid(ss, v_kn, compat),
        "robertson": robertson(ss, v_kn),
        "maclennan": maclennan(ss, v_kn),
        "aberdeen_demersal": aberdeen_demersal(ss, v_kn),
        "aberdeen_pelagic": aberdeen_pelagic(ss, v_kn),
        "fridman": fridman(dl, st, inputs.alpha_deg, v_ms),
        "dickson": dickson_rn,
    }


def drag_table(
    inputs: DragInputs,
    speeds_kn: Speeds,
    compat: Compat = Compat.CORRECTED,
) -> DragTable:
    """Evalúa todos los métodos para ambas variantes a las velocidades dadas (en nudos).

    Reproduce el resumen 'Resistencia de la RED'!A302:Q310 (estándar) y A317:Q325
    (modificada) en toneladas-fuerza; ``.kgf`` da las filas 398:421. La velocidad en m/s se
    obtiene con el factor del libro (``C11 =PotOK!B272`` = 0.5144·kn).
    """
    v_kn = np.atleast_1d(_arr(speeds_kn))
    v_ms = v_kn * KNOT_TO_MS
    if inputs.ah_m is not None and len(inputs.ah_m) != len(v_kn):
        raise ValueError("ah_m debe tener una entrada por velocidad")
    if inputs.av_m is not None and len(inputs.av_m) != len(v_kn):
        raise ValueError("av_m debe tener una entrada por velocidad")
    return DragTable(
        speed_kn=v_kn,
        speed_ms=v_ms,
        std=_variant_columns(inputs, v_kn, v_ms, "std", compat),
        mod=_variant_columns(inputs, v_kn, v_ms, "mod", compat),
        unit="t",
        compat=compat,
    )


def average(table: DragTable, compat: Compat = Compat.CORRECTED) -> DragAverage:
    """Promedio de métodos por velocidad (columna R, filas 302:310 y 317:325).

    En modo :attr:`Compat.EXCEL` reproduce la errata ``drag_average_pollution``:
    ``R302 =AVERAGE(B302:P302)`` incluye la velocidad en m/s y excluye Dickson en la primera
    fila de la estándar, y todas las filas (``=AVERAGE(C:Q)``) incluyen las columnas de
    Nomura (tiro disponible, no RN). En modo corregido es la media de :data:`RN_METHODS`.
    """
    if compat is Compat.EXCEL:
        all_cols = list(table.columns)
        std_rows = np.column_stack([table.std[c] for c in all_cols])
        mod_rows = np.column_stack([table.mod[c] for c in all_cols])
        std_avg = std_rows.mean(axis=1)
        mod_avg = mod_rows.mean(axis=1)
        # R302 =AVERAGE(B302:P302): velocidad [m/s] + columnas C..P (sin Dickson, columna Q).
        speed = table.speed_ms[0] * (_T_TO_KGF if table.unit == "kgf" else 1.0)
        first = np.concatenate(([speed], std_rows[0, :-1]))
        std_avg[0] = first.mean()
        return DragAverage(std=std_avg, mod=mod_avg, unit=table.unit)
    rn = [c for c in table.columns if c in RN_METHODS]
    std_avg = np.column_stack([table.std[c] for c in rn]).mean(axis=1)
    mod_avg = np.column_stack([table.mod[c] for c in rn]).mean(axis=1)
    return DragAverage(std=std_avg, mod=mod_avg, unit=table.unit)


def method_average(
    table: DragTable,
    variant: str = "mod",
    compat: Compat = Compat.CORRECTED,
) -> dict[str, float]:
    """Promedio sobre velocidades de cada columna (fila 326, ``C326 =AVERAGE(C317:C325)``).

    Devuelve un diccionario columna → media, más ``"average"`` (R326, media de la columna de
    promedios calculada con :func:`average` en el mismo ``compat``). La hoja solo tiene esta
    fila para la variante modificada; ``variant`` permite calcularla también para la
    estándar.
    """
    cols = table.variant(variant)
    out = {c: float(np.mean(cols[c])) for c in table.columns}
    avg = average(table, compat)
    out["average"] = float(np.mean(avg.std if variant == "std" else avg.mod))
    return out


__all__ = [
    "DESIGN_METHOD",
    "DICKSON_M2_TO_FT2",
    "NOMURA_NHP",
    "RN_METHODS",
    "SUMMARY_COLUMNS",
    "DragAverage",
    "DragInputs",
    "DragTable",
    "aberdeen_demersal",
    "aberdeen_pelagic",
    "average",
    "dickson",
    "drag_table",
    "fridman",
    "hamuro",
    "hamuro_sin_alpha",
    "koyama_1974",
    "koyama_1984",
    "maclennan",
    "method_average",
    "nomura",
    "reid",
    "robertson",
    "tauti_nomura_shu",
    "tauti_rope",
]
