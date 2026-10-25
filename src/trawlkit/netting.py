"""Paños de red y cortes: largos estirados, superficies de trabajo, mallas y cortes (Prado/FAO).

Reproduce la hoja ``'Paños de red y cortes'`` del modelo original. Cada bloque de la hoja (uno
por paño) comparte las mismas fórmulas; aquí se documentan con las celdas del paño A (filas
52-64) y las del resumen de cortes (B272:K278).

Convención de nombres: ``t1``/``t2`` son los bordes del paño tal como aparecen en las celdas
``a (T1)`` / ``b (T2)`` de la hoja (``Panel.meshes_a`` / ``Panel.meshes_b``) y ``n`` el número
de mallas de alto (``h (N)``). En el bloque A (filas 55-57) las etiquetas ``b (T2)`` y
``a (T1)`` están invertidas respecto a los demás bloques (I55 es el borde de 3 mallas, I56 el
de 57); las funciones son simétricas en ``t1``/``t2`` salvo que se indique lo contrario.
"""

from __future__ import annotations

import csv
import math
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from functools import cache
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from trawlkit.compat import Compat
from trawlkit.io.loader import DATA_DIR

Number = float | npt.NDArray[np.float64]

#: Tolerancia para la búsqueda "exacta" (``VLOOKUP(...,FALSE)``) de una razón de corte real.
CUT_RATIO_TOL: float = 1e-9


def _out(a: npt.NDArray[np.float64]) -> Number:
    """Devuelve un ``float`` para entradas escalares y un array en caso contrario."""
    return float(a) if a.ndim == 0 else a


# ---------------------------------------------------------------------------------------------
# Compostura básica
# ---------------------------------------------------------------------------------------------


def runnage_m_per_kg(rtex: Number) -> Number:
    """Rendimiento del hilo [m/kg] a partir del Rtex: ``1e6 / Rtex``.

    Celda: ``'Paños de red y cortes'!A55`` (``=1000000/K55``). Rtex = g por 1000 m, de modo
    que 1e6/Rtex es la longitud de hilo por kilogramo (781.25 m/kg para R1280tex).
    """
    return _out(1_000_000.0 / np.asarray(rtex, dtype=float))


def stretched_length_m(meshes: Number, mesh_mm: Number, coef: Number = 1.0) -> Number:
    """Largo estirado de un borde o del alto del paño [m]: ``n_mallas · coef · mallero / 1000``.

    Celdas: ``'Paños de red y cortes'!I55:I57`` (``I55 =(H55*D55*$B$55)/1000``). ``coef`` es el
    coeficiente "en el plano" de la hoja: X = 0.5 para los bordes T1/T2 (columna D,
    ``Panel.plan_coef_x``) e Y = 1 para el alto N (columna F, ``Panel.plan_coef_y``).
    """
    n = np.asarray(meshes, dtype=float)
    return _out(n * np.asarray(coef, dtype=float) * np.asarray(mesh_mm, dtype=float) / 1000.0)


def vertical_opening_coefficient(u1: Number) -> Number:
    """Coeficiente de abertura vertical ``U2 = sqrt(1 - U1²)``.

    Celda: ``'Mecánica de la Red'!L56`` (``=SQRT(1-(K56^2))``); también
    ``'Paños de red y cortes'!F273``.
    """
    u = np.asarray(u1, dtype=float)
    return _out(np.sqrt(1.0 - u * u))


#: Coeficiente de abertura de la malla cuadrada a lo ancho y a lo largo: el lado del cuadrado es
#: una pata, la mitad de la malla estirada.
SQUARE_MESH_COEFFICIENT = 0.5


def orientation_coefficients(orientation: str, u1: float) -> tuple[float, float]:
    """Coeficientes "en el plano" (ancho, alto) por malla estirada según la orientación.

    Rombo y T90: ``(U1, √(1−U1²))``, con ``U1`` = ``hanging_ratio`` (la abertura a lo ancho del
    panel; en T90 la diagonal larga va a lo ancho, así que se espera un U1 mayor). Malla
    cuadrada: ``(0.5, 0.5)``, porque cada malla contada es un cuadrado de lado una pata.
    """
    if str(orientation) == "square":
        return SQUARE_MESH_COEFFICIENT, SQUARE_MESH_COEFFICIENT
    return float(u1), float(vertical_opening_coefficient(u1))


def opening_product(orientation: str, u1: float) -> float:
    """Producto ``U1·U2`` de la superficie de trabajo; en malla cuadrada, ``0.25`` (lado ²/mL²)."""
    cx, cy = orientation_coefficients(orientation, u1)
    return cx * cy


def panel_working_area_m2(u1: Number, t1: Number, t2: Number, n: Number, mesh_mm: Number) -> Number:
    """Superficie de trabajo del paño [m²]: ``U1·√(1−U1²)·((T1+T2)/2)·N·(mL/1000)²``.

    Método FAO (Prado): área del trapecio de mallas con las aberturas horizontal U1 y vertical
    U2 = √(1−U1²). Celda: ``'Paños de red y cortes'!A61``::

        =D55*(SQRT(1-(D55^2)))*(((H55+H56)/2)*H57)*(B55/1000)^2

    Nótese que en esa celda la hoja usa como U1 el coeficiente X "en el plano" (D55 = 0.5), no
    el U1 del resumen (W271 = 0.38) que sí emplea ``'Mecánica de la Red'!M56`` (ver
    :func:`trawlkit.net.working_surface_m2`).
    """
    u = np.asarray(u1, dtype=float)
    a = np.asarray(t1, dtype=float)
    b = np.asarray(t2, dtype=float)
    depth = np.asarray(n, dtype=float)
    m_l = np.asarray(mesh_mm, dtype=float) / 1000.0
    return _out(u * np.sqrt(1.0 - u * u) * ((a + b) / 2.0 * depth) * m_l**2)


def mesh_count(t1: Number, t2: Number, n: Number) -> Number:
    """Número de mallas del paño: ``((T1 + T2 − 1)·(N − 0.5)) + 0.5``.

    Celda: ``'Paños de red y cortes'!A64`` (``=((H55+H56-1)*(H57-0.5))+0.5``).
    """
    a = np.asarray(t1, dtype=float)
    b = np.asarray(t2, dtype=float)
    depth = np.asarray(n, dtype=float)
    return _out((a + b - 1.0) * (depth - 0.5) + 0.5)


# ---------------------------------------------------------------------------------------------
# Cortes
# ---------------------------------------------------------------------------------------------


def taper_meshes(t1: Number, t2: Number) -> Number:
    """Diferencia de mallas entre los dos bordes del paño: ``|T1 − T2|``."""
    return _out(np.abs(np.asarray(t1, dtype=float) - np.asarray(t2, dtype=float)))


def cut_meshes(t1: Number, t2: Number, n: Number) -> Number:
    """Mallas del corte X1 de un paño de ala (``Faltante / Mallas``): ``| N − |T1 − T2| |``.

    Celda: ``'Paños de red y cortes'!G63`` (``=((H56-(H55+H57))/H57)*H57`` = T1 − T2 − N = 18
    para el paño A, con T1 = 57, T2 = 3, N = 36). Los demás bloques de ala escriben la resta en
    el orden que da un resultado positivo (C: ``F97 =(H90+H92-H91)`` = T1 + N − T2 = 60;
    D: ``R97`` = T2 + N − T1 = 80; F: ``R122`` = T2 + N − T1 = 26), de ahí el valor absoluto.
    Interpretación: el borde cortado cambia |T1 − T2| mallas de ancho en N mallas de alto; N de
    ellas se resuelven con un corte AB (X2, ver :func:`cut_meshes_x2`) y el resto con el corte
    X1.
    """
    return _out(np.abs(np.asarray(n, dtype=float) - np.asarray(taper_meshes(t1, t2), dtype=float)))


def cut_meshes_x2(t1: Number, t2: Number, n: Number) -> Number:
    """Mallas del corte X2 de un paño de ala.

    Celda: ``'Paños de red y cortes'!G64`` (``=H56-G63-H55`` = T1 − X1 − T2 = 36 para A);
    en C, D y F la hoja escribe ``T2 + X1 − T1`` (F98, R98, R123). En ambos casos el resultado
    es N: si |T1−T2| > N, X1 = |T1−T2| − N y X2 = |T1−T2| − X1 = N; si |T1−T2| < N,
    X1 = N − |T1−T2| y X2 = |T1−T2| + X1 = N. Se reproduce la aritmética de la hoja.
    """
    d = np.asarray(taper_meshes(t1, t2), dtype=float)
    x1 = np.asarray(cut_meshes(t1, t2, n), dtype=float)
    depth = np.asarray(n, dtype=float)
    return _out(np.where(d > depth, d - x1, d + x1))


def symmetric_cut_meshes(t1: Number, t2: Number) -> Number:
    """Mallas del corte en cada costado de un paño simétrico: ``|T1 − T2| / 2``.

    Celdas: ``'Paños de red y cortes'!F127`` (square, ``=(H120-H121)/2``), ``F163`` (dorso),
    ``F196`` (dorso D2).
    """
    return _out(np.asarray(taper_meshes(t1, t2), dtype=float) / 2.0)


def cut_ratio(cut_meshes_x1: Number, n: Number) -> Number:
    """Razón de corte RC de un paño de ala: ``|X1 − N| / (2·X1)``.

    Celda: ``'Paños de red y cortes'!H63`` (``=(ABS(G63-H57))/(2*G63)`` = 18/36 = 0.5 → 1N2B).
    También G97 (C) y S122 (F). En S62 (paño B) la hoja pasa por error el coeficiente X (P55 =
    0.5) en lugar de N (T56), con lo que RC = 0.486 en vez de 0.5; ``cut_ratio(18, 0.5)`` lo
    reproduce.
    """
    x1 = np.asarray(cut_meshes_x1, dtype=float)
    depth = np.asarray(n, dtype=float)
    return _out(np.abs(x1 - depth) / (2.0 * x1))


def taper_ratio(meshes_across: Number, meshes_deep: Number) -> Number:
    """Razón de corte directa: mallas de corte a lo ancho / mallas a lo alto.

    Es la razón que indexa la tabla de cortes (1N2B = 1 malla de ancho por 2 de alto = 0.5).
    Celdas: ``'Paños de red y cortes'!G127`` (``=(H120-H121)/(2*H122)``, square), ``G163``,
    ``G196`` (dorsos), ``S97`` (paño D, ``=(T90+T91-T89)/T91`` = X1/N) y los cortes de la bolsa
    ``G229 =H224/H224``, ``G230 =H222/H223`` (= 1 → AB). El corte X2 de las alas usa
    ``((T+1)-1)/T`` = 1 (H64), equivalente a ``taper_ratio(T, T)``.
    """
    return _out(np.asarray(meshes_across, dtype=float) / np.asarray(meshes_deep, dtype=float))


@dataclass(frozen=True)
class CutRow:
    """Fila de la tabla de cortes (``'Tablas de Referencias'!A49:F88``)."""

    cut_ratio: float
    cut_code: str
    mesh_increase_width: int | None = None
    mesh_increase_height: int | None = None
    label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return asdict(self)


@cache
def load_cut_table(path: Path | str | None = None) -> tuple[CutRow, ...]:
    """Carga ``trawlkit/data/reference/cut_ratios.csv`` (``'Tablas de Referencias'!A49:C72``).

    Las filas 69-72 (razones ``2/x``) no tienen aumento de mallas en la hoja y se cargan con
    ``None``; el paño D (RC = 2/3 → ``1N4B``) sólo tiene correspondencia allí. Memorizado.
    """
    p = Path(path) if path is not None else DATA_DIR / "reference" / "cut_ratios.csv"
    rows: list[CutRow] = []
    with p.open(encoding="utf-8", newline="") as fh:
        for rec in csv.DictReader(fh):
            rows.append(
                CutRow(
                    cut_ratio=float(rec["cut_ratio"]),
                    cut_code=rec["cut_code"],
                    mesh_increase_width=_opt_int(rec.get("mesh_increase_width")),
                    mesh_increase_height=_opt_int(rec.get("mesh_increase_height")),
                    label=rec.get("cut_ratio_label") or None,
                )
            )
    return tuple(rows)


def _opt_int(text: str | None) -> int | None:
    """Entero de una celda CSV vacía o numérica (``"1"``, ``"1.0"``, ``""`` → ``None``)."""
    if text is None or text.strip() == "":
        return None
    return int(float(text))


def cut_code(
    ratio: float,
    table: Sequence[CutRow] | None = None,
    compat: Compat = Compat.CORRECTED,
) -> str | None:
    """Código de corte (``AB``, ``1N2B``, …) para una razón de corte.

    Celda: ``'Paños de red y cortes'!I63``
    (``=VLOOKUP(H63,'Tablas de Referencias'!$A$49:$C$88,3,FALSE)``): búsqueda exacta en la
    primera fila de la tabla cuya razón coincide con ``ratio`` (tolerancia
    :data:`CUT_RATIO_TOL`, ya que la hoja compara reales).

    Errata ``panel_f_cut_na`` (P!T122): la razón del paño F (0.2692…) no figura en la tabla y
    la celda devuelve ``#N/A``.

    * :attr:`Compat.EXCEL`: sin coincidencia exacta devuelve ``None`` (el ``#N/A``).
    * :attr:`Compat.CORRECTED`: sin coincidencia exacta devuelve el código de la razón más
      cercana (lo que intentaba la fórmula matricial ``MATCH(MIN(ABS(tabla-RC)),…)`` de T122),
      ``3N2B`` (1/4) para el paño F.
    """
    rows = tuple(table) if table is not None else load_cut_table()
    for row in rows:
        if abs(row.cut_ratio - ratio) <= CUT_RATIO_TOL:
            return row.cut_code
    if compat is Compat.EXCEL:
        return None
    nearest = min(rows, key=lambda r: abs(r.cut_ratio - ratio))
    return nearest.cut_code


def cut_steps(code: str, table: Sequence[CutRow] | None = None) -> tuple[int, int]:
    """Mallas de aumento o disminución ``(en ancho, en alto)`` de un código de corte.

    Celdas: ``'Paños de red y cortes'!H273`` e ``I273``
    (``VLOOKUP($G$273,'Tablas de Referencias'!$C$49:$F$88,3/4,FALSE)``: columnas E y F de la
    tabla). Se toma la primera fila con ese código que tenga ambas columnas.
    """
    rows = tuple(table) if table is not None else load_cut_table()
    for row in rows:
        if (
            row.cut_code == code
            and row.mesh_increase_width is not None
            and row.mesh_increase_height is not None
        ):
            return row.mesh_increase_width, row.mesh_increase_height
    raise KeyError(f"código de corte sin filas de aumento en la tabla: {code!r}")


_CUT_TOKEN = re.compile(r"(\d*)([NTB])")


def cut_code_ratio(code: str) -> float:
    """Razón de corte de un código FAO (``AB``, ``AN``, ``1N2B``, ``1T2B``…), sin la tabla.

    En un ciclo de corte cada punta (N) baja una malla sin cambiar el ancho, cada malleta (B)
    avanza media malla a lo ancho y media a lo alto, y cada transversal (T) avanza una malla a
    lo ancho: razón = (T + B/2)/(N + B/2) mallas de ancho por malla de alto. Da los valores de la
    tabla de cortes (1N2B = 1/2, 1N1B = 1/3, 1N4B = 2/3, AB = 1, AN = 0). ``ValueError`` si el
    código no se entiende.
    """
    c = code.strip().upper().replace(" ", "")
    counts = {"N": 0.0, "T": 0.0, "B": 0.0}
    if c in ("AB", "AN", "AT"):
        counts[c[1]] = 1.0
    else:
        pos = 0
        for m in _CUT_TOKEN.finditer(c):
            if m.start() != pos:
                break
            counts[m.group(2)] += float(m.group(1) or 1)
            pos = m.end()
        if pos != len(c) or pos == 0:
            raise ValueError(f"código de corte no reconocido: {code!r}")
    deep = counts["N"] + counts["B"] / 2.0
    across = counts["T"] + counts["B"] / 2.0
    if deep == 0.0:
        raise ValueError(f"código de corte sin avance en alto: {code!r}")
    return across / deep


def cut_angle_deg(
    code: str,
    u1: float,
    u2: float | None = None,
    table: Sequence[CutRow] | None = None,
) -> float:
    """Ángulo de ataque horizontal del corte [°]: ``θ = atan((a·U1) / (d·U2))``.

    Prado: ``a`` y ``d`` son las mallas de aumento en ancho y en alto del código de corte
    (:func:`cut_steps`), U1 el coeficiente de abertura horizontal y U2 = √(1−U1²) el vertical
    (si no se pasa se calcula). Celdas: ``'Paños de red y cortes'!J273``
    (``=(H273*E273)/(I273*F273)``) y ``K273`` (``=DEGREES(ATAN(J273))``).
    """
    width, height = cut_steps(code, table)
    v2 = float(vertical_opening_coefficient(u1)) if u2 is None else u2
    tan_theta = (width * u1) / (height * v2)
    return math.degrees(math.atan(tan_theta))


def mean_cut_angle_deg(
    cut_codes: Sequence[str],
    u1: Sequence[float],
    u2: Sequence[float] | None = None,
    table: Sequence[CutRow] | None = None,
    compat: Compat = Compat.CORRECTED,
) -> float:
    """Promedio de los ángulos de ataque de los cortes de los paños del plan alto [°].

    Celda: ``'Paños de red y cortes'!K278`` (``=AVERAGE(K273:K277)``) sobre los paños A, C, E,
    G y H con sus U1 (``'Mecánica de la Red'!K56:K60``).

    Errata ``cut_ratio_first_panel`` (P!H274:I277): las filas 2 a 5 buscan las mallas de
    aumento con ``$G$273`` (el código del primer paño) en lugar de su propio G27x.

    * :attr:`Compat.EXCEL`: todos los paños usan ``cut_codes[0]`` (sólo cambia U1/U2).
    * :attr:`Compat.CORRECTED`: cada paño usa su propio código.

    En la red FAO A-3 todos los cortes son 1N2B, por lo que ambos modos coinciden (10.634°).
    """
    if len(cut_codes) != len(u1):
        raise ValueError("cut_codes y u1 deben tener la misma longitud")
    v2 = [float(vertical_opening_coefficient(u)) for u in u1] if u2 is None else list(u2)
    angles = []
    for i, (code, u, v) in enumerate(zip(cut_codes, u1, v2, strict=True)):
        use = cut_codes[0] if (compat is Compat.EXCEL and i > 0) else code
        angles.append(cut_angle_deg(use, u, v, table))
    return float(np.mean(angles))


# ---------------------------------------------------------------------------------------------
# Pegadura de la bolsa modificada
# ---------------------------------------------------------------------------------------------


def join_ratio(next_edge_m: Number, previous_edge_m: Number) -> Number:
    """Relación de pegadura entre un paño y el siguiente: ``borde siguiente / borde anterior``.

    Celda: ``'Paños de red y cortes'!J240`` (``=I256/I190``: borde T2 estirado de la bolsa I'
    sobre el borde T2 del paño H, 2.085/2.26 = 0.9226).
    """
    return _out(np.asarray(next_edge_m, dtype=float) / np.asarray(previous_edge_m, dtype=float))


def join_offset_m(previous_edge_m: Number, next_edge_m: Number) -> Number:
    """Media diferencia de anchos en la pegadura [m]: ``(borde anterior − borde siguiente)/2``.

    Celda: ``'Paños de red y cortes'!B243`` (``=(I189-I255)/2``: (4.86 − 2.085)/2 = 1.3875 m).
    """
    prev = np.asarray(previous_edge_m, dtype=float)
    nxt = np.asarray(next_edge_m, dtype=float)
    return _out((prev - nxt) / 2.0)
