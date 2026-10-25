"""Dimensiones de la red: relingas, largos, circunferencias y proporciones de Nomura.

Reproduce la hoja ``'Dimensiones de la Red'`` (F45:F54, D89, D97, D103, D109, C124:C132,
C140:G151, C155) y ``'Cables Y Cabulleria'!J5``. Las funciones puras reciben mallas y malleros;
:func:`compute` identifica los paneles de la spec por plano y sección (punta de ala, ala, square,
2ª sección de ala, cuerpo, bolsa) y arma la hoja completa para la red estándar o la modificada.
"""

from __future__ import annotations

import csv
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from functools import cache
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from trawlkit.compat import Compat
from trawlkit.io.loader import DATA_DIR
from trawlkit.io.schema import NetSpec, Panel, Plane, Section
from trawlkit.net import NetGeometry, analyse, group_rows, panel_planes
from trawlkit.netting import mean_cut_angle_deg

Number = float | npt.NDArray[np.float64]

#: Embando (coeficiente de armado) de las piezas de relinga en la hoja (C142/C150 y G142/G150).
WING_HANGING: float = 1.05
BOSOM_HANGING: float = 0.83

#: Etiquetas de las proporciones de Nomura en el orden de la hoja (B124:B132) y su columna en
#: ``trawlkit/data/reference/nomura_proportions.csv``.
NOMURA_LABELS: tuple[tuple[str, str], ...] = (
    ("l/m", "l_m"),
    ("l/b", "l_b"),
    ("m/b", "m_b"),
    ("a/b", "a_b"),
    ("c/b", "c_b"),
    ("d/b", "d_b"),
    ("e/b", "e_b"),
    ("f/b", "f_b"),
    ("(d-c)/b", "d_minus_c_b"),
)


def _out(a: npt.NDArray[np.float64]) -> Number:
    """Devuelve un ``float`` para entradas escalares y un array en caso contrario."""
    return float(a) if a.ndim == 0 else a


# ---------------------------------------------------------------------------------------------
# Relingas (Martini nivel 2)
# ---------------------------------------------------------------------------------------------


def headrope_wing_piece_m(wing_tip_depth: Number, wing_depth: Number, mesh_mm: Number) -> Number:
    """Pieza de ala de la lima [m]: ``(N_ala + N_punta) · mallero / 1000``.

    Martini nivel 2: largo a malla estirada del borde superior del ala (punta de ala A + ala
    C). Celda: ``'Dimensiones de la Red'!C140``
    (``{=((P!H92+P!H57)*P!B55:B57)/1000}`` = (120 + 36)·80/1000 = 12.48 m).
    """
    depth = np.asarray(wing_tip_depth, dtype=float) + np.asarray(wing_depth, dtype=float)
    return _out(depth * np.asarray(mesh_mm, dtype=float) / 1000.0)


def headrope_bosom_piece_m(
    square_top_meshes: Number,
    square_mesh_mm: Number,
    wing_bottom_meshes: Number,
    wing_mesh_mm: Number,
) -> Number:
    """Pieza de bocana de la lima [m]: ``(T_square·mL_square − 2·T_ala·mL_ala) / 2000``.

    Mitad de lo que el borde de boca del square (412 mallas de 60 mm) excede a los dos bordes de
    pegadura de las alas (117 mallas de 80 mm). Celda: ``'Dimensiones de la Red'!F140``
    (``{=(((P!H120*P!B120:B122)-((P!H91*P!B90:B92)*2))/1000)*0.5}`` = 3.0 m).
    """
    square = np.asarray(square_top_meshes, dtype=float) * np.asarray(square_mesh_mm, dtype=float)
    wings = (
        2.0 * np.asarray(wing_bottom_meshes, dtype=float) * np.asarray(wing_mesh_mm, dtype=float)
    )
    return _out((square - wings) / 1000.0 * 0.5)


def footrope_wing_piece_m(
    wing_tip_depth: Number,
    wing_depth: Number,
    wing_mesh_mm: Number,
    belly_depth: Number,
    belly_mesh_mm: Number,
) -> Number:
    """Pieza de ala del burlón [m]: ``((N_punta + N_ala)·mL_ala + N_2ª·mL_2ª) / 1000``.

    Como la lima pero añadiendo la 2ª sección del ala inferior (F). Celda:
    ``'Dimensiones de la Red'!C148``
    (``{=((P!T56+P!T91)*P!N89:N91+P!T116*P!N114:N116)/1000}`` = (156·80 + 40·60)/1000 = 14.88 m).
    """
    wing = (np.asarray(wing_tip_depth, dtype=float) + np.asarray(wing_depth, dtype=float)) * (
        np.asarray(wing_mesh_mm, dtype=float)
    )
    belly = np.asarray(belly_depth, dtype=float) * np.asarray(belly_mesh_mm, dtype=float)
    return _out((wing + belly) / 1000.0)


def footrope_bosom_piece_m(
    body_top_meshes: Number,
    body_mesh_mm: Number,
    belly_bottom_meshes: Number,
    belly_mesh_mm: Number,
) -> Number:
    """Pieza de bocana del burlón [m]: ``(T_vientre·mL_vientre − 2·T_2ª·mL_2ª) / 2000``.

    Celda: ``'Dimensiones de la Red'!F148``
    (``{=((P!T156*P!N156:N158)-((2*P!T114)*P!N114:N116))/1000*0.5}`` =
    (372·60 − 2·143·60)/2000 = 2.58 m).
    """
    body = np.asarray(body_top_meshes, dtype=float) * np.asarray(body_mesh_mm, dtype=float)
    belly = (
        2.0 * np.asarray(belly_bottom_meshes, dtype=float) * np.asarray(belly_mesh_mm, dtype=float)
    )
    return _out((body - belly) / 1000.0 * 0.5)


def corrected_piece_m(piece_m: Number, hanging: Number) -> Number:
    """Pieza de relinga corregida por el embando: ``L · embando``.

    Celdas: ``'Dimensiones de la Red'!C143`` (``=C140*C142``, 1.05) y ``G143``
    (``=F140*G142``, 0.83).
    """
    return _out(np.asarray(piece_m, dtype=float) * np.asarray(hanging, dtype=float))


def headrope_length_m(wing_corrected_m: Number, bosom_corrected_m: Number) -> Number:
    """Largo de la lima [m]: ``2·L_ala_corregido + L_bocana_corregido``.

    Celda: ``'Dimensiones de la Red'!F45`` (``=(C143*2)+G143`` = 2·13.104 + 2.49 = 28.698 m).
    """
    return _out(
        2.0 * np.asarray(wing_corrected_m, dtype=float) + np.asarray(bosom_corrected_m, dtype=float)
    )


def excel_mid_truncate(x: float, n_chars: int) -> float:
    """Imita ``MID(x, 1, n)`` aplicado a un número en Excel.

    Excel convierte el número a texto en formato General (hasta 15 cifras significativas), toma
    los ``n`` primeros caracteres y vuelve a convertirlos a número: 15.624000000000002 → "15.6"
    → 15.6; 2.1414 → "2.1" → 2.1.
    """
    return float(f"{x:.15g}"[:n_chars])


def footrope_length_m(
    wing_corrected_m: float,
    bosom_corrected_m: float,
    compat: Compat = Compat.CORRECTED,
) -> float:
    """Largo del burlón [m]: ``2·m_ala_corregido + m_bocana_corregido``.

    Celda: ``'Dimensiones de la Red'!F46`` (``=(2*MID(C151,1,4)+MID(G151,1,3))``).

    Errata ``footrope_mid_truncation`` (Dim!F46): la hoja aplica ``MID`` a los números, con lo
    que trunca 15.624 → 15.6 y 2.1414 → 2.1.

    * :attr:`Compat.EXCEL`: ``2·15.6 + 2.1 = 33.3`` m.
    * :attr:`Compat.CORRECTED`: ``2·15.624 + 2.1414 = 33.3894`` m.
    """
    if compat is Compat.EXCEL:
        return 2.0 * excel_mid_truncate(wing_corrected_m, 4) + excel_mid_truncate(
            bosom_corrected_m, 3
        )
    return 2.0 * wing_corrected_m + bosom_corrected_m


@dataclass(frozen=True)
class RopePieces:
    """Piezas de una relinga (``'Dimensiones de la Red'!B140:G143`` / ``B148:G151``)."""

    wing_m: float
    bosom_m: float
    wing_hanging: float
    bosom_hanging: float
    wing_corrected_m: float
    bosom_corrected_m: float
    length_m: float

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return asdict(self)


def wingtip_reinforcement_m(
    wing_tip_depth: Number, mesh_mm: Number, hanging: Number = 1.0
) -> Number:
    """Refuerzo de la punta de ala [m]: ``N_punta · mallero / 1000 · embando``.

    Celdas: ``'Dimensiones de la Red'!C155`` (``{=(P!H57*P!B55:B57)/1000}`` = 36·80/1000 =
    2.88 m) y ``C157`` (embando = 1).
    """
    depth = np.asarray(wing_tip_depth, dtype=float)
    return _out(
        depth * np.asarray(mesh_mm, dtype=float) / 1000.0 * np.asarray(hanging, dtype=float)
    )


def wingtip_reinforcement_rope_m(reinforcement_m: float) -> float:
    """Cabo de refuerzo de puntas de ala [m]: ``ROUNDUP(4 · m_punta, 1)``.

    Cuatro puntas de ala, redondeado hacia arriba al decímetro. Celda:
    ``'Cables Y Cabulleria'!J5`` (``=ROUNDUP(4*'Dimensiones de la Red'!C155,1)`` = 11.6 m).
    """
    return math.ceil(round(4.0 * reinforcement_m * 10.0, 9)) / 10.0


# ---------------------------------------------------------------------------------------------
# Largos, circunferencias y relaciones
# ---------------------------------------------------------------------------------------------


def panel_length_m(meshes_depth: Number, mesh_mm: Number) -> Number:
    """Largo de un paño a malla estirada [m]: ``N · mallero / 1000`` (``Q·R/1000`` del resumen)."""
    return _out(np.asarray(meshes_depth, dtype=float) * np.asarray(mesh_mm, dtype=float) / 1000.0)


def body_length_no_bag_m(
    upper_lengths_m: Sequence[float],
    lower_lengths_m: Sequence[float],
    *,
    modified: bool = False,
    compat: Compat = Compat.CORRECTED,
) -> float:
    """Largo total del dorso sin la bolsa [m]: Σ largos de los paños del plan alto.

    Celda: ``'Dimensiones de la Red'!F48`` (A, C, E, G, H: 32.68 m).

    Errata ``mod_length_wrong_rows`` (Dim!G48): la columna de la red modificada suma las filas
    del plan inferior (B, D, F, G, H) en lugar de las del dorso.

    * :attr:`Compat.EXCEL` con ``modified=True``: Σ ``lower_lengths_m``.
    * :attr:`Compat.CORRECTED` (o red estándar): Σ ``upper_lengths_m``.

    En la red FAO A-3 ambos planos miden lo mismo sin bolsa (32.68 m) y la errata no cambia el
    número.
    """
    if compat is Compat.EXCEL and modified:
        return float(sum(lower_lengths_m))
    return float(sum(upper_lengths_m))


def max_circumference_m(
    upper_body_top_meshes: Number,
    upper_body_mesh_mm: Number,
    lower_body_top_meshes: Number,
    lower_body_mesh_mm: Number,
) -> Number:
    """Circunferencia máxima a malla estirada [m]: ``(T_D·mL_D + T_V·mL_V) / 1000``.

    T_D/mL_D son el borde de boca y el mallero del dorso D1, T_V/mL_V los del vientre V1.
    Celda: ``'Dimensiones de la Red'!F49``
    (``=((P!S276*P!Q276)+(P!S288*P!Q288))/1000`` = (372·60 + 372·60)/1000 = 44.64 m).
    """
    up = np.asarray(upper_body_top_meshes, dtype=float) * np.asarray(
        upper_body_mesh_mm, dtype=float
    )
    lo = np.asarray(lower_body_top_meshes, dtype=float) * np.asarray(
        lower_body_mesh_mm, dtype=float
    )
    return _out((up + lo) / 1000.0)


def fishing_circle_m(
    upper_body_top_meshes: Number, lower_body_top_meshes: Number, mesh_mm: Number
) -> Number:
    """Circunferencia de pesca FC [m]: ``(T_dorso + T_vientre) · mallero / 1000``.

    Celda: ``'Dimensiones de la Red'!D97`` (``=((P!S276+P!S288)*P!Q288)/1000`` = 44.64 m). Es
    la misma magnitud que :func:`max_circumference_m` escrita con el mallero del vientre.
    """
    total = np.asarray(upper_body_top_meshes, dtype=float) + np.asarray(
        lower_body_top_meshes, dtype=float
    )
    return _out(total * np.asarray(mesh_mm, dtype=float) / 1000.0)


def length_factor(
    headrope_m: Number, footrope_m: Number, square_depth_meshes: Number, square_mesh_mm: Number
) -> Number:
    """Factor largo FL de Fujiishi: ``(Lima + 2·(N_square·mL_square/1000)) / Burlón``.

    Dr. Akio Fujiishi (Shimonoseki University of Fisheries). Celda:
    ``'Dimensiones de la Red'!D89`` (``=(F83+(2*((F85*F86)/1000)))/F84`` =
    (28.698 + 2·2.4)/33.3 = 1.00595).
    """
    square = np.asarray(square_depth_meshes, dtype=float) * np.asarray(square_mesh_mm, dtype=float)
    return _out(
        (np.asarray(headrope_m, dtype=float) + 2.0 * square / 1000.0)
        / np.asarray(footrope_m, dtype=float)
    )


def fc_body_ratio(fishing_circle: Number, body_length: Number) -> Number:
    """Relación circunferencia de pesca / largo del cuerpo.

    Celda: ``'Dimensiones de la Red'!D109`` (``=D97/D103`` = 44.64/17.8 = 2.508).
    """
    return _out(np.asarray(fishing_circle, dtype=float) / np.asarray(body_length, dtype=float))


def nomura_ratios(
    headrope_m: float,
    footrope_m: float,
    total_length_m: float,
    circumference_m: float,
    upper_wing_m: float,
    lower_wing_m: float,
    back_m: float,
    bag_m: float,
) -> dict[str, float]:
    """Proporciones elementales de Nomura de la red (``'Dimensiones de la Red'!C124:C132``).

    ``l`` lima, ``m`` burlón, ``b`` largo total con bolsa (F47), ``a`` circunferencia máxima
    (F49), ``c`` ala superior (F50), ``d`` ala inferior (F51), ``e`` dorso (F52), ``f`` bolsa
    (F53). Devuelve ``{"l/m", "l/b", "m/b", "a/b", "c/b", "d/b", "e/b", "f/b", "(d-c)/b"}``.
    """
    b = total_length_m
    return {
        "l/m": headrope_m / footrope_m,
        "l/b": headrope_m / b,
        "m/b": footrope_m / b,
        "a/b": circumference_m / b,
        "c/b": upper_wing_m / b,
        "d/b": lower_wing_m / b,
        "e/b": back_m / b,
        "f/b": bag_m / b,
        "(d-c)/b": (lower_wing_m - upper_wing_m) / b,
    }


@cache
def load_nomura_reference(
    path: Path | str | None = None, net_type: str = "Red de Fondo, 2 caras"
) -> dict[str, float]:
    """Proporciones de referencia de Nomura para un tipo de red.

    Lee ``trawlkit/data/reference/nomura_proportions.csv`` (``'Tablas de Referencias'!A16:L25``) y
    devuelve la primera fila de ``net_type`` con las claves de :func:`nomura_ratios`
    (``'Dimensiones de la Red'!E124:E132`` = fila 16, red de fondo de 2 caras).
    """
    p = Path(path) if path is not None else DATA_DIR / "reference" / "nomura_proportions.csv"
    with p.open(encoding="utf-8", newline="") as fh:
        for rec in csv.DictReader(fh):
            if rec["net_type"] == net_type:
                return {label: float(rec[col]) for label, col in NOMURA_LABELS if rec[col]}
    raise KeyError(f"tipo de red sin proporciones de Nomura: {net_type!r}")


# ---------------------------------------------------------------------------------------------
# Resultado y cálculo desde la spec
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class NetDimensions:
    """Dimensiones de la red (``'Dimensiones de la Red'``)."""

    net_id: str
    compat: Compat
    headrope: RopePieces
    footrope: RopePieces
    headrope_m: float
    footrope_m: float
    total_length_m: float
    body_length_no_bag_m: float
    max_circumference_m: float
    upper_wing_m: float
    lower_wing_m: float
    back_belly_m: float
    bag_m: float
    square_m: float
    length_factor: float
    fishing_circle_m: float
    body_length_m: float
    fc_body_ratio: float
    nomura_ratios: dict[str, float]
    nomura_reference: dict[str, float]
    wingtip_reinforcement_m: float
    wingtip_hanging: float
    wingtip_reinforcement_rope_m: float
    cut_angle_deg: float
    filtration_index: float
    solid_surface_m2: float
    working_surface_m2: float
    net_weight_kg: float

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        d = asdict(self)
        d["compat"] = self.compat.value
        return d


def _find(panels: Sequence[Panel], section: Section, plane: Plane | None = None) -> Panel:
    for p in panels:
        if p.section is section and (plane is None or plane in panel_planes(p)):
            return p
    raise ValueError(f"la spec no tiene un panel {section.value} en el plano {plane}")


def _length(p: Panel) -> float:
    return float(panel_length_m(p.meshes_depth, p.mesh_mm))


def compute(
    spec: NetSpec,
    geometry: NetGeometry | None = None,
    compat: Compat = Compat.CORRECTED,
    *,
    modified: bool | None = None,
    wing_hanging: float = WING_HANGING,
    bosom_hanging: float = BOSOM_HANGING,
) -> NetDimensions:
    """Calcula la hoja ``'Dimensiones de la Red'`` para una spec.

    Identifica los paneles por plano y sección: punta de ala superior/inferior (A/B), ala
    superior/inferior (C/D), square (E), 2ª sección del ala inferior (F, ``belly``), cuerpo
    (G, H, en orden) y bolsa superior/inferior (I/J, o I' si cubre ambos planos). Los bordes se
    toman en la convención boca→bolsa de la spec (``meshes_top``/``meshes_bottom``).

    ``geometry`` (``net.analyse``) aporta los ecos F56:F59 (d/l, Ss, St, peso); si no se pasa se
    calcula con el mismo ``compat``. ``modified`` indica la columna G de la hoja (por defecto,
    ``spec.variant_of is not None``) y sólo interviene en la errata ``mod_length_wrong_rows``.

    Erratas: ``footrope_mid_truncation`` (F46; también arrastra D89 y C124:C126, que usan el
    nombre ``Burlon``) y ``mod_length_wrong_rows`` (G48).
    """
    from trawlkit.topology import is_a3_topology

    geo = geometry if geometry is not None else analyse(spec, compat)
    # La ruta del libro (constantes de la A-3) sólo para la estructura de la A-3 sin largos de
    # relinga del plano; una red del catálogo con esa estructura usa los largos de su plano.
    plan_ropes = _rope_from_spec(spec, "headrope") is not None
    if not is_a3_topology(spec) or plan_ropes:
        return compute_generic(spec, geo, compat, wing_hanging=wing_hanging)
    panels = spec.panels
    is_mod = (spec.variant_of is not None) if modified is None else modified

    a = _find(panels, Section.WING_TIP, Plane.UPPER)
    b = _find(panels, Section.WING_TIP, Plane.LOWER)
    c = _find(panels, Section.WING, Plane.UPPER)
    d = _find(panels, Section.WING, Plane.LOWER)
    e = _find(panels, Section.SQUARE)
    f = _find(panels, Section.BELLY, Plane.LOWER)
    g_up = _find(panels, Section.BODY, Plane.UPPER)
    g_lo = _find(panels, Section.BODY, Plane.LOWER)
    bag_up = _find(panels, Section.CODEND, Plane.UPPER)

    # Relingas (Martini nivel 2).
    h_wing = float(headrope_wing_piece_m(a.meshes_depth, c.meshes_depth, a.mesh_mm))
    h_bosom = float(headrope_bosom_piece_m(e.meshes_top, e.mesh_mm, c.meshes_bottom, c.mesh_mm))
    h_wing_c = float(corrected_piece_m(h_wing, wing_hanging))
    h_bosom_c = float(corrected_piece_m(h_bosom, bosom_hanging))
    headrope = RopePieces(
        h_wing,
        h_bosom,
        wing_hanging,
        bosom_hanging,
        h_wing_c,
        h_bosom_c,
        float(headrope_length_m(h_wing_c, h_bosom_c)),
    )
    f_wing = float(
        footrope_wing_piece_m(b.meshes_depth, d.meshes_depth, d.mesh_mm, f.meshes_depth, f.mesh_mm)
    )
    f_bosom = float(
        footrope_bosom_piece_m(g_lo.meshes_top, g_lo.mesh_mm, f.meshes_bottom, f.mesh_mm)
    )
    f_wing_c = float(corrected_piece_m(f_wing, wing_hanging))
    f_bosom_c = float(corrected_piece_m(f_bosom, bosom_hanging))
    footrope = RopePieces(
        f_wing,
        f_bosom,
        wing_hanging,
        bosom_hanging,
        f_wing_c,
        f_bosom_c,
        footrope_length_m(f_wing_c, f_bosom_c, compat),
    )

    # Largos por plan (resumen N269:W291 de 'Paños').
    upper = [p for p in panels if Plane.UPPER in panel_planes(p)]
    lower = [p for p in panels if Plane.LOWER in panel_planes(p)]
    total_length = sum(_length(p) for p in lower)
    no_bag = body_length_no_bag_m(
        [_length(p) for p in upper if p.section is not Section.CODEND],
        [_length(p) for p in lower if p.section is not Section.CODEND],
        modified=is_mod,
        compat=compat,
    )
    upper_wing = _length(a) + _length(c)
    lower_wing = _length(b) + _length(d) + _length(f)
    back = _length(g_up)
    bag = _length(bag_up)
    circumference = float(
        max_circumference_m(g_up.meshes_top, g_up.mesh_mm, g_lo.meshes_top, g_lo.mesh_mm)
    )
    body_length = sum(_length(p) for p in upper if p.section is Section.BODY)
    fc = float(fishing_circle_m(g_up.meshes_top, g_lo.meshes_top, g_lo.mesh_mm))

    # Ángulo de ataque de los cortes (P!K278): filas del plan alto, sin bolsa.
    rows = [
        r for r in group_rows(spec) if Plane.UPPER in r.planes and r.section is not Section.CODEND
    ]
    by_id = {p.id: p for p in panels}
    codes_u1 = [
        (by_id[r.panel_ids[0]].cut_code, r.u1)
        for r in rows
        if by_id[r.panel_ids[0]].cut_code is not None
    ]
    cut_angle = (
        mean_cut_angle_deg(
            [str(code) for code, _ in codes_u1], [u for _, u in codes_u1], compat=compat
        )
        if codes_u1
        else math.nan
    )

    reinforcement = float(wingtip_reinforcement_m(a.meshes_depth, a.mesh_mm, 1.0))
    return NetDimensions(
        net_id=spec.id,
        compat=compat,
        headrope=headrope,
        footrope=footrope,
        headrope_m=headrope.length_m,
        footrope_m=footrope.length_m,
        total_length_m=total_length,
        body_length_no_bag_m=no_bag,
        max_circumference_m=circumference,
        upper_wing_m=upper_wing,
        lower_wing_m=lower_wing,
        back_belly_m=back,
        bag_m=bag,
        square_m=lower_wing - upper_wing,
        length_factor=float(
            length_factor(headrope.length_m, footrope.length_m, e.meshes_depth, e.mesh_mm)
        ),
        fishing_circle_m=fc,
        body_length_m=body_length,
        fc_body_ratio=float(fc_body_ratio(fc, body_length)),
        nomura_ratios=nomura_ratios(
            headrope.length_m,
            footrope.length_m,
            total_length,
            circumference,
            upper_wing,
            lower_wing,
            back,
            bag,
        ),
        nomura_reference=load_nomura_reference(),
        wingtip_reinforcement_m=reinforcement,
        wingtip_hanging=1.0,
        wingtip_reinforcement_rope_m=wingtip_reinforcement_rope_m(reinforcement),
        cut_angle_deg=cut_angle,
        filtration_index=geo.filtration_index,
        solid_surface_m2=geo.solid_surface_m2,
        working_surface_m2=geo.working_surface_m2,
        net_weight_kg=geo.weight_air_kg,
    )


# ---------------------------------------------------------------------------------------------
# Ruta genérica (redes del catálogo FAO, Fase 12)
# ---------------------------------------------------------------------------------------------


def _rope_from_spec(spec: NetSpec, which: str) -> tuple[float, float, float] | None:
    """(ala, bocana, total) de la relinga si la spec trae los largos del plano."""
    rope = getattr(spec, which)
    extra = (rope.model_extra or {}) if rope is not None else {}
    wing, bosom = extra.get("wing_m"), extra.get("bosom_m")
    if wing is None or bosom is None:
        return None
    total = float(rope.length_m) if rope is not None and rope.length_m else 2 * wing + bosom
    return float(wing), float(bosom), total


def _taper_angle_deg(p: Panel) -> float:
    """Ángulo del costado de un paño central respecto del eje, con su armado [°].

    Del corte que dan las mallas: el paño pierde ``(T_boca − T_bolsa)/2`` mallas por costado
    en ``N`` mallas de alto; con U1 a lo ancho y U2 a lo alto, ``tan θ = ΔT·U1 / (2·N·U2)``.
    """
    u1 = float(p.hanging_ratio or 0.5)
    u2 = math.sqrt(max(1.0 - u1 * u1, 1e-9))
    return math.degrees(
        math.atan(abs(p.meshes_top - p.meshes_bottom) * u1 / (2.0 * p.meshes_depth * u2))
    )


def compute_generic(
    spec: NetSpec,
    geometry: NetGeometry,
    compat: Compat = Compat.CORRECTED,
    *,
    wing_hanging: float = WING_HANGING,
) -> NetDimensions:
    """Dimensiones de una red que no tiene la estructura de la FAO A-3.

    Se calculan a partir de las cadenas de paños del plano (``drawing.layout``), sobre la red
    equivalente de 2 paneles si tiene costados (:func:`trawlkit.topology.equivalent_two_panel`):

    * **Relingas**: los largos del plano si la spec los trae (``wing_m`` y ``bosom_m`` de la
      relinga); si no, el alto estirado de la cadena de alas × ``wing_hanging`` y la bocana
      (borde de boca del primer paño central menos las dos alas) × U1.
    * **Círculo de pesca**: mallas del borde de boca del primer paño central de cada cara ×
      mallero. **Circunferencia máxima**: la mayor suma dorso + vientre de las estaciones del
      cuerpo, emparejadas desde el copo.
    * **Ángulo de corte**: promedio del ángulo del costado de los paños centrales del dorso sin
      el copo, con su armado (:func:`_taper_angle_deg`).
    * **Proporciones de Nomura**: sólo para redes de fondo; si no, quedan vacías.

    No aplica ninguna errata del libro Excel.
    """
    from trawlkit.drawing.layout import layout_net
    from trawlkit.topology import equivalent_two_panel

    eq = equivalent_two_panel(spec)
    lay = layout_net(eq, mode="schematic")
    planes: list[str] = [pl for pl in ("upper", "lower") if pl in lay.planes]
    if not planes:
        raise ValueError("la red no tiene dorso ni vientre")
    central: dict[str, list[Panel]] = {pl: [s.panel for s in lay.central(pl)] for pl in planes}
    wings: dict[str, list[Panel]] = {
        pl: [s.panel for s in lay.side_chain(pl, "right")] for pl in planes
    }

    def wing_depth_m(pl: str) -> float:
        return float(sum(_length(p) for p in wings.get(pl, [])))

    def bosom_m(pl: str) -> float:
        cs, ws = central.get(pl, []), wings.get(pl, [])
        if not cs:
            return 0.0
        first = cs[0]
        gap = first.meshes_top * first.mesh_mm
        if ws:
            gap -= 2 * ws[-1].meshes_bottom * ws[-1].mesh_mm
        return max(gap, 0.0) / 1000.0 * float(first.hanging_ratio or 0.5)

    def rope(which: str, pl: str) -> RopePieces:
        given = _rope_from_spec(spec, which)
        if given is not None:
            w, b, total = given
            return RopePieces(w, b, 1.0, 1.0, w, b, total)
        w = wing_depth_m(pl)
        b = bosom_m(pl)
        wc = w * wing_hanging
        return RopePieces(w, b, wing_hanging, 1.0, wc, b, 2 * wc + b)

    headrope = rope("headrope", "upper" if "upper" in planes else planes[0])
    footrope = rope("footrope", "lower" if "lower" in planes else planes[-1])

    def plane_panels(pl: str) -> list[Panel]:
        return [p for p in eq.panels if Plane(pl) in panel_planes(p)]

    lengths = {pl: [s for s in lay.bands[pl]] for pl in planes}
    total_length = max(sum(_length(b.panel) for b in lengths[pl]) for pl in planes)
    upper = plane_panels("upper") if "upper" in planes else []
    upper_no_bag = [
        b.panel for b in lay.bands.get("upper", ()) if b.panel.section is not Section.CODEND
    ]
    no_bag = sum(_length(p) for p in upper_no_bag)
    upper_wing = wing_depth_m("upper") if "upper" in planes else 0.0
    lower_wing = wing_depth_m("lower") if "lower" in planes else 0.0
    body_up = [p for p in central.get("upper", []) if p.section is Section.BODY]
    back = _length(body_up[0]) if body_up else 0.0
    bag = sum(_length(p) for p in central.get("upper", []) if p.section is Section.CODEND)
    square = sum(_length(p) for p in eq.panels if p.section is Section.SQUARE)
    fc = sum(
        central[pl][0].meshes_top * central[pl][0].mesh_mm / 1000.0
        for pl in planes
        if central.get(pl)
    )
    # Estaciones del cuerpo emparejadas desde el copo (dorso y vientre).
    up_c = list(reversed(central.get("upper", [])))
    lo_c = list(reversed(central.get("lower", [])))
    stations = [
        (a.meshes_top * a.mesh_mm + b.meshes_top * b.mesh_mm) / 1000.0
        for a, b in zip(up_c, lo_c, strict=False)
    ]
    circumference = max([*stations, fc]) if stations else fc
    body_length = sum(_length(p) for p in upper if p.section is Section.BODY)
    tapers = [
        _taper_angle_deg(p)
        for p in central.get("upper", [])
        if p.section is not Section.CODEND and p.meshes_top != p.meshes_bottom
    ]
    cut_angle = float(np.mean(tapers)) if tapers else 0.0
    sq = next((p for p in eq.panels if p.section is Section.SQUARE), None)
    bottom_net = spec.family in (None, "bottom")
    ratios = (
        nomura_ratios(
            headrope.length_m,
            footrope.length_m,
            total_length,
            circumference,
            upper_wing,
            lower_wing,
            back,
            bag,
        )
        if bottom_net
        else {}
    )
    tip = next((p for p in eq.panels if p.section is Section.WING_TIP), None)
    reinforcement = (
        float(wingtip_reinforcement_m(tip.meshes_depth, tip.mesh_mm, 1.0)) if tip else 0.0
    )
    return NetDimensions(
        net_id=spec.id,
        compat=compat,
        headrope=headrope,
        footrope=footrope,
        headrope_m=headrope.length_m,
        footrope_m=footrope.length_m,
        total_length_m=total_length,
        body_length_no_bag_m=no_bag,
        max_circumference_m=circumference,
        upper_wing_m=upper_wing,
        lower_wing_m=lower_wing,
        back_belly_m=back,
        bag_m=bag,
        square_m=square,
        length_factor=float(
            length_factor(
                headrope.length_m,
                footrope.length_m,
                sq.meshes_depth if sq else 0,
                sq.mesh_mm if sq else 0.0,
            )
        ),
        fishing_circle_m=fc,
        body_length_m=body_length,
        fc_body_ratio=float(fc_body_ratio(fc, body_length)) if body_length else math.nan,
        nomura_ratios=ratios,
        nomura_reference=load_nomura_reference() if bottom_net else {},
        wingtip_reinforcement_m=reinforcement,
        wingtip_hanging=1.0,
        wingtip_reinforcement_rope_m=wingtip_reinforcement_rope_m(reinforcement)
        if reinforcement
        else 0.0,
        cut_angle_deg=cut_angle,
        filtration_index=geometry.filtration_index,
        solid_surface_m2=geometry.solid_surface_m2,
        working_surface_m2=geometry.working_surface_m2,
        net_weight_kg=geometry.weight_air_kg,
    )
