"""Mecánica de la red: índice de filtración, superficies sólida y de trabajo, solidez y pesos.

Reproduce la hoja ``'Mecánica de la Red'`` (filas 6-17, 29-40, 56-67, 75-79 y 98-113). La hoja
trabaja con **filas de paño** (una por letra: ``A+B``, ``C``, ``E``, ``G``, ``H``, ``D``, ``F``,
``I``, ``J`` y ``I'`` para la bolsa modificada) y no con los paneles individuales de la spec;
:func:`group_rows` construye esas filas a partir de ``NetSpec.panels`` agrupando los paneles de
compostura idéntica (A y B) y conservando el orden de la hoja. Varias magnitudes (Σd/Σl, pesos)
se suman por fila sin multiplicar por la cantidad de paneles, tal como hace el Excel.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import numpy.typing as npt

from trawlkit.compat import ERRATA_BY_KEY, Compat
from trawlkit.i18n import t
from trawlkit.io.loader import load_catalogue
from trawlkit.io.schema import NetSpec, Panel, Plane, Section
from trawlkit.materials import (
    EXCEL_PI,
    Material,
    find_material,
    materials_from_catalogue,
    twine_density_kg_m3,
)
from trawlkit.netting import opening_product, vertical_opening_coefficient

Number = float | npt.NDArray[np.float64]

#: Densidad del agua usada por las fórmulas de peso en agua (``'Mecánica de la Red'!P98``:
#: ``=O98*(1-(1025/F98))``). Difiere del ρ_mar = 1024 de ``trawlkit.units.RHO_SEAWATER``
#: (O127); se conserva como constante propia para reproducir la hoja.
RHO_WATER_WEIGHT_KG_M3: float = 1025.0

#: Mallas en T y en N del paño de referencia con el que la hoja pesa el hilo (P!C3:C4, O3:O4…).
REFERENCE_T_MESHES: int = 500
REFERENCE_N_MESHES: int = 100

#: Clave propuesta (no registrada aún en :data:`trawlkit.compat.ERRATA`) para la referencia
#: equivocada de ``'Mecánica de la Red'!K36`` (``='Paños de red y cortes'!H224``: el alto N de
#: la bolsa en vez de su borde menor H223) que arrastra K37 (``=K36``) y, por tanto, N36:N37,
#: M63:M64 y O105:P106 de la red estándar.
ERRATUM_CODEND_MINOR_SIDE = ERRATA_BY_KEY["codend_minor_side_uses_depth"].key


def _out(a: npt.NDArray[np.float64]) -> Number:
    """Devuelve un ``float`` para entradas escalares y un array en caso contrario."""
    return float(a) if a.ndim == 0 else a


# ---------------------------------------------------------------------------------------------
# Fórmulas por fila
# ---------------------------------------------------------------------------------------------


def filtration_per_row(twine_mm: Number, mesh_mm: Number, count: Number = 1) -> Number:
    """Índice de filtración de una fila de paños: ``(Ø hilo / mallero) · nº paneles``.

    Celda: ``'Mecánica de la Red'!K6`` (``=(I6/J6)*H6``). Es informativo: el índice global
    (:func:`filtration_index`) no promedia estas celdas sino que divide Σd / Σl.
    """
    d = np.asarray(twine_mm, dtype=float)
    m_l = np.asarray(mesh_mm, dtype=float)
    return _out(d / m_l * np.asarray(count, dtype=float))


@dataclass(frozen=True)
class FiltrationIndex:
    """Índice de filtración d/l de la red (``'Mecánica de la Red'!H15:K15`` / ``H17:K17``)."""

    sum_twine_mm: float
    sum_mesh_mm: float
    sum_panels: float
    value: float

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return asdict(self)


def filtration_index(
    twine_mm: Sequence[float],
    mesh_mm: Sequence[float],
    counts: Sequence[float] | None = None,
    *,
    mod_codend_index: int | None = None,
    compat: Compat = Compat.CORRECTED,
) -> FiltrationIndex:
    """Índice de filtración de la red (FAO): ``Σ Ø hilo / Σ mallero`` sobre las filas de paño.

    Celdas: ``'Mecánica de la Red'!I15 =SUM(I6:I14)``, ``J15 =SUM(J6:J14)``, ``K15 =I15/J15``.
    Las sumas son por fila (sin ponderar por la cantidad de paneles, que sólo se acumula en
    H15 = ``sum_panels``).

    Errata ``filtration_double_count`` (Mec!J17): para la red modificada
    ``J17 =SUM(J16,J6:J12,J16)`` suma dos veces el mallero de la bolsa I' (30 mm → Σl = 520 en
    vez de 490).

    * :attr:`Compat.EXCEL` con ``mod_codend_index`` apuntando a la fila de la bolsa modificada
      reproduce el doble conteo (d/l = 0.019462).
    * :attr:`Compat.CORRECTED` suma cada fila una vez (d/l = 0.020653).
    """
    d = np.asarray(twine_mm, dtype=float)
    m_l = np.asarray(mesh_mm, dtype=float)
    n = np.ones_like(d) if counts is None else np.asarray(counts, dtype=float)
    sum_d = float(d.sum())
    sum_l = float(m_l.sum())
    if compat is Compat.EXCEL and mod_codend_index is not None:
        sum_l += float(m_l[mod_codend_index])
    return FiltrationIndex(sum_d, sum_l, float(n.sum()), sum_d / sum_l)


def panel_length_m(n: Number, mesh_mm: Number) -> Number:
    """Largo del paño a malla estirada [m]: ``N · mallero / 1000``.

    Celda: ``'Mecánica de la Red'!M29`` (``=(I29*L29)/1000``).
    """
    return _out(np.asarray(n, dtype=float) * np.asarray(mesh_mm, dtype=float) / 1000.0)


def solid_surface_m2(
    twine_mm: Number, mesh_mm: Number, t1: Number, t2: Number, n: Number, count: Number = 1
) -> Number:
    """Superficie sólida ocupada por el hilo [m²]: ``L · d · (T1 + T2) / 1000 · nº paneles``.

    FAO: largo del paño L = N·mL/1000 [m] por el diámetro del hilo d [mm] por el número de
    mallas de ambos bordes, pasado a metros. Celda: ``'Mecánica de la Red'!N29``
    (``=((M29*H29*(J29+K29))/1000)*F29``).
    """
    length = np.asarray(panel_length_m(n, mesh_mm), dtype=float)
    d = np.asarray(twine_mm, dtype=float)
    edges = np.asarray(t1, dtype=float) + np.asarray(t2, dtype=float)
    return _out(length * d * edges / 1000.0 * np.asarray(count, dtype=float))


def working_surface_m2(
    u1: Number,
    mesh_mm: Number,
    t1: Number,
    t2: Number,
    n: Number,
    count: Number = 1,
    opening: Number | None = None,
) -> Number:
    """Superficie de trabajo (razón de armadura) [m²]: ``0.5·U1·U2·mL²·(T1+T2)·N·nº paneles``.

    FAO: U2 = √(1−U1²) y mL en metros. Celda: ``'Mecánica de la Red'!M56``
    (``=(0.5*K56*L56*((G56)^2)*(H56+I56)*J56)*D56``). Coincide con
    :func:`trawlkit.netting.panel_working_area_m2` por panel, usando el U1 real del paño (W271).
    ``opening`` reemplaza el producto ``U1·U2`` (malla cuadrada: 0.25, ver
    :func:`trawlkit.netting.opening_product`).
    """
    u = np.asarray(u1, dtype=float)
    uu = (
        u * np.asarray(vertical_opening_coefficient(u), dtype=float)
        if opening is None
        else np.asarray(opening, dtype=float)
    )
    m_l = np.asarray(mesh_mm, dtype=float) / 1000.0
    edges = np.asarray(t1, dtype=float) + np.asarray(t2, dtype=float)
    depth = np.asarray(n, dtype=float)
    return _out(0.5 * uu * m_l**2 * edges * depth * np.asarray(count, dtype=float))


def solidity(solid_surface: Number, working_surface: Number) -> Number:
    """Coeficiente de solidez ``Ss / St`` (L. G. Pérez Águila, 2010).

    Celda: ``'Mecánica de la Red'!E75`` (``=N38/M65``).
    """
    return _out(np.asarray(solid_surface, dtype=float) / np.asarray(working_surface, dtype=float))


def filtering_coefficient(solidity_coef: Number) -> Number:
    """Coeficiente de filtrado ``1 − solidez``.

    Celda: ``'Mecánica de la Red'!M78`` (``=N$75-E75`` con N75 = 1).
    """
    return _out(1.0 - np.asarray(solidity_coef, dtype=float))


def reference_twine_weight_kg(
    mesh_mm: Number,
    twine_mm: Number,
    density_kg_m3: Number,
    t_meshes: int = REFERENCE_T_MESHES,
    n_meshes: int = REFERENCE_N_MESHES,
    pi: float = EXCEL_PI,
) -> Number:
    """Peso del hilo de un paño de referencia de ``T × N`` mallas (SN, método A) [kg].

    ``SN = (T · mL[m] · 2N) · π · (d[m]/2)² · ρ``: longitud total de hilo (T mallas de mL por
    2N lados) por la sección del hilo por la densidad aparente. Celda:
    ``'Mecánica de la Red'!N98``::

        =(((L98*(H98/1000))*(2*M98))*3.1416*(((G98/2)/1000)^2))*F98

    con L98 = 500 (T), M98 = 100 (N), H98 = mallero, G98 = Ø hilo y F98 = densidad (P!L55). La
    hoja usa π = 3.1416 (:data:`trawlkit.materials.EXCEL_PI`); con la densidad corregida
    (``1/(A·runnage)``) y ``pi=math.pi`` el resultado es exactamente ``longitud / runnage``.
    """
    length_m = np.asarray(t_meshes, dtype=float) * (np.asarray(mesh_mm, dtype=float) / 1000.0)
    length_m = length_m * (2.0 * np.asarray(n_meshes, dtype=float))
    radius_m = (np.asarray(twine_mm, dtype=float) / 2.0) / 1000.0
    return _out(length_m * pi * radius_m**2 * np.asarray(density_kg_m3, dtype=float))


def panel_weight_air_kg(
    t1: Number,
    t2: Number,
    n: Number,
    reference_weight_kg: Number,
    t_meshes: int = REFERENCE_T_MESHES,
    n_meshes: int = REFERENCE_N_MESHES,
) -> Number:
    """Peso en aire del paño (método B) [kg]: ``((T1+T2)/2 / T) · (N / N_ref) · SN``.

    Escala el peso del paño de referencia por la relación de mallas en ancho (promedio de los
    bordes sobre T = 500) y en alto (N sobre 100). Celda: ``'Mecánica de la Red'!O98``
    (``=(((I98+J98)/2)/L98)*(K98/M98)*N98``). No multiplica por la cantidad de paneles.
    """
    edges = (np.asarray(t1, dtype=float) + np.asarray(t2, dtype=float)) / 2.0
    ratio_t = edges / float(t_meshes)
    ratio_n = np.asarray(n, dtype=float) / float(n_meshes)
    return _out(ratio_t * ratio_n * np.asarray(reference_weight_kg, dtype=float))


def weight_in_water_kg(
    weight_air_kg: Number,
    density_kg_m3: Number,
    rho_water: float = RHO_WATER_WEIGHT_KG_M3,
) -> Number:
    """Peso en agua [kg]: ``W_aire · (1 − ρ_agua / ρ)``.

    Celda: ``'Mecánica de la Red'!P98`` (``=O98*(1-(1025/F98))``). La hoja usa como ρ la
    "densidad" de P!L55 (≈1152, errata ``twine_density_units``), que casualmente da un
    coeficiente ≈0.11 próximo al 0.10 tabulado para PA (1140 kg/m³) en agua de mar. En modo
    corregido :func:`analyse` pasa la densidad del polímero del catálogo de materiales.
    """
    w = np.asarray(weight_air_kg, dtype=float)
    rho = np.asarray(density_kg_m3, dtype=float)
    return _out(w * (1.0 - rho_water / rho))


# ---------------------------------------------------------------------------------------------
# Filas de paño y agregados por plan
# ---------------------------------------------------------------------------------------------


def _extra(panel: Panel, name: str, default: Any = None) -> Any:
    """Campo extra (no declarado en el esquema) de un panel."""
    extra = panel.model_extra or {}
    return extra.get(name, default)


def panel_planes(panel: Panel) -> tuple[Plane, ...]:
    """Planos cubiertos por un panel (``planes_covered`` o, en su defecto, ``plane``)."""
    covered = _extra(panel, "planes_covered")
    if covered:
        return tuple(Plane(p) for p in covered)
    return (panel.plane,)


def panel_edges(panel: Panel) -> tuple[int, int]:
    """Bordes ``(T1, T2)`` del panel en la convención de la hoja (``meshes_a``/``meshes_b``).

    Si la spec no trae los extras se usan ``meshes_top``/``meshes_bottom`` (las fórmulas de
    esta hoja son simétricas en T1/T2).
    """
    a = _extra(panel, "meshes_a")
    b = _extra(panel, "meshes_b")
    if a is None or b is None:
        return panel.meshes_top, panel.meshes_bottom
    return int(a), int(b)


@dataclass(frozen=True)
class NettingRow:
    """Fila de paño de ``'Mecánica de la Red'`` (C29:L37): paneles de compostura idéntica."""

    id: str
    panel_ids: tuple[str, ...]
    section: Section
    planes: tuple[Plane, ...]
    count: int
    material: str
    mesh_mm: float
    twine_mm: float
    rtex: float | None
    runnage_m_per_kg: float
    t1: int
    t2: int
    n: int
    u1: float
    orientation: str = "diamond"

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        d = asdict(self)
        d["section"] = self.section.value
        d["planes"] = [p.value for p in self.planes]
        return d


def _row_key(panel: Panel) -> tuple[Any, ...]:
    t1, t2 = panel_edges(panel)
    return (
        panel.section,
        panel.mesh_mm,
        panel.twine_diameter_mm,
        t1,
        t2,
        panel.meshes_depth,
        str(panel.mesh_orientation),
    )


def _runnage(panel: Panel) -> float:
    """Rendimiento [m/kg]: ``1e6/Rtex`` (P!A55) si hay Rtex; si no, el valor de la spec.

    Se prefiere el Rtex porque la spec guarda el rendimiento redondeado (1052.63 frente a
    1052.6315…), lo que desvía los pesos ~1.5e-6 respecto del Excel.
    """
    if panel.rtex is not None:
        return 1_000_000.0 / float(panel.rtex)
    if panel.runnage_m_per_kg is None:
        raise ValueError(t("panel {id}: hace falta rtex o runnage_m_per_kg", id=panel.id))
    return float(panel.runnage_m_per_kg)


def group_rows(spec: NetSpec) -> tuple[NettingRow, ...]:
    """Construye las filas de paño de la hoja a partir de los paneles de la spec.

    Se agrupan los paneles consecutivos con la misma sección y compostura (mallero, Ø hilo,
    T1, T2, N): en la red FAO A-3 sólo A y B (puntas de ala) → fila ``A+B`` con 4 paneles
    (``F29 =SUM(COUNTIF(37:37,"A"),COUNTIF(37:37,"B"))``). Las filas se devuelven en el orden
    de la hoja: primero las que incluyen el plan alto (A+B, C, E, G, H), luego las exclusivas
    del plan bajo (D, F) y por último las bolsas (I, J o I'). El U1 de la fila es el
    ``hanging_ratio`` del primer panel (``K56 ='Paños de red y cortes'!W271``).
    """
    groups: list[list[Panel]] = []
    for panel in spec.panels:
        if groups and _row_key(groups[-1][0]) == _row_key(panel):
            groups[-1].append(panel)
        else:
            groups.append([panel])

    rows: list[NettingRow] = []
    for group in groups:
        first = group[0]
        planes: list[Plane] = []
        for p in group:
            for pl in panel_planes(p):
                if pl not in planes:
                    planes.append(pl)
        if first.hanging_ratio is None:
            raise ValueError(t("panel {id}: hace falta hanging_ratio (U1)", id=first.id))
        t1, t2 = panel_edges(first)
        rows.append(
            NettingRow(
                id="+".join(p.id for p in group),
                panel_ids=tuple(p.id for p in group),
                section=first.section,
                planes=tuple(planes),
                count=sum(p.count for p in group),
                material=first.material,
                mesh_mm=float(first.mesh_mm),
                twine_mm=float(first.twine_diameter_mm),
                rtex=None if first.rtex is None else float(first.rtex),
                runnage_m_per_kg=_runnage(first),
                t1=t1,
                t2=t2,
                n=first.meshes_depth,
                u1=float(first.hanging_ratio),
                orientation=str(first.mesh_orientation),
            )
        )

    def order(row: NettingRow) -> int:
        if row.section is Section.CODEND:
            return 2
        return 0 if Plane.UPPER in row.planes else 1

    return tuple(sorted(rows, key=order))


def apply_excel_codend_quirk(rows: Sequence[NettingRow]) -> tuple[NettingRow, ...]:
    """Reproduce la referencia errónea de ``'Mecánica de la Red'!K36`` (bolsa estándar).

    K36 (``lado menor`` de la bolsa superior I) apunta a ``P!H224`` (N = 200) en lugar de
    ``P!H223`` (T2 = 113), y K37 (bolsa inferior J) copia K36. Con ello N36, N37, M63, M64,
    O105 y O106 usan (T1 + N_I) en vez de (T1 + T2). Sólo afecta a las bolsas de un solo plano
    (I y J); la bolsa modificada I' (J39:K39) está bien referenciada. Clave propuesta:
    :data:`ERRATUM_CODEND_MINOR_SIDE`.
    """
    codends = [r for r in rows if r.section is Section.CODEND and len(r.planes) == 1]
    if not codends:
        return tuple(rows)
    depth_first = codends[0].n
    out: list[NettingRow] = []
    for r in rows:
        if r in codends:
            out.append(
                NettingRow(
                    **{**asdict(r), "section": r.section, "planes": r.planes, "t2": depth_first}
                )
            )
        else:
            out.append(r)
    return tuple(out)


def split_by_plane(rows: Sequence[NettingRow], values: Sequence[float]) -> dict[str, float]:
    """Reparte una magnitud por fila entre los planos alto y bajo.

    Regla de la hoja (``O30:O37`` e ``I110:I113``): las filas que cubren ambos planos (A+B,
    G, H, I') aportan la mitad a cada uno; las de un solo plano aportan todo a su plano.
    Devuelve ``{"upper": …, "lower": …}``.
    """
    totals = {Plane.UPPER.value: 0.0, Plane.LOWER.value: 0.0}
    for row, v in zip(rows, values, strict=True):
        share = float(v) / len(row.planes)
        for plane in row.planes:
            if plane.value in totals:
                totals[plane.value] += share
    return totals


# ---------------------------------------------------------------------------------------------
# Resultado
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class RowGeometry:
    """Resultados de ``'Mecánica de la Red'`` para una fila de paño.

    ``solid_surface_m2`` y ``working_surface_m2`` incluyen la cantidad de paneles de la fila.
    ``weight_air_kg``/``weight_water_kg`` son de un panel en :attr:`Compat.EXCEL` (O98, P98) y de
    toda la fila en :attr:`Compat.CORRECTED` (errata ``net_weight_ignores_panel_count``).
    """

    row: NettingRow
    u2: float
    length_m: float
    filtration: float
    solid_surface_m2: float
    working_surface_m2: float
    twine_density_kg_m3: float
    reference_twine_weight_kg: float
    weight_air_kg: float
    weight_water_kg: float

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        d = asdict(self)
        d["row"] = self.row.to_dict()
        return d


@dataclass(frozen=True)
class NetGeometry:
    """Geometría mecánica de la red (``'Mecánica de la Red'``), estándar o modificada."""

    net_id: str
    compat: Compat
    rows: tuple[RowGeometry, ...]
    filtration: FiltrationIndex
    solid_surface_m2: float
    working_surface_m2: float
    solidity: float
    filtering_coefficient: float
    solid_surface_by_plane: dict[str, float]
    weight_air_kg: float
    weight_water_kg: float
    weight_by_plane: dict[str, float]
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def filtration_index(self) -> float:
        """Índice de filtración d/l (``K15`` / ``K17``)."""
        return self.filtration.value

    def row(self, row_id: str) -> RowGeometry:
        """Fila por identificador (``"A+B"``, ``"C"``, …)."""
        for r in self.rows:
            if r.row.id == row_id:
                return r
        raise KeyError(row_id)

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "net_id": self.net_id,
            "compat": self.compat.value,
            "rows": [r.to_dict() for r in self.rows],
            "filtration": self.filtration.to_dict(),
            "filtration_index": self.filtration_index,
            "solid_surface_m2": self.solid_surface_m2,
            "working_surface_m2": self.working_surface_m2,
            "solidity": self.solidity,
            "filtering_coefficient": self.filtering_coefficient,
            "solid_surface_by_plane": dict(self.solid_surface_by_plane),
            "weight_air_kg": self.weight_air_kg,
            "weight_water_kg": self.weight_water_kg,
            "weight_by_plane": dict(self.weight_by_plane),
            "notes": list(self.notes),
        }


def analyse(
    spec: NetSpec,
    compat: Compat = Compat.CORRECTED,
    materials: Sequence[Material] | None = None,
) -> NetGeometry:
    """Calcula la hoja ``'Mecánica de la Red'`` completa para una spec.

    Reproduce, para la red estándar (``fao_a3_standard``) y la modificada (``fao_a3_modified``):
    K15/K17 (d/l), N38/N40 (Ss), O30:O37 (Ss por plan), M65/M67 (St), E75:E76 (solidez),
    M78:M79 (filtrado), O107:P109 (peso en aire/agua) e I110:I113 (peso por plan).

    Erratas reproducidas en :attr:`Compat.EXCEL` y corregidas en :attr:`Compat.CORRECTED`:

    * ``twine_density_units`` (P!L55): densidad usada en SN (N98) y en el peso en agua (P98).
      En modo corregido SN = longitud de hilo / runnage y el peso en agua usa la densidad del
      polímero del catálogo ``materials`` (``load_catalogue("materials")`` si no se pasa).
    * ``filtration_double_count`` (Mec!J17): mallero de la bolsa I' sumado dos veces.
    * :data:`ERRATUM_CODEND_MINOR_SIDE` (Mec!K36, propuesta): lado menor de las bolsas I/J
      sustituido por el alto N de I. Afecta Ss, St y pesos de la red estándar.

    * ``net_weight_ignores_panel_count`` (Mec!O107, O109): el libro suma el peso de un panel
      por fila (O107 = ΣO98:O106) aunque la fila agrupe varios paneles iguales (alas izquierda y
      derecha, planos alto y bajo). En modo corregido el peso de cada fila (en aire y en agua) se
      multiplica por su cantidad de paneles ``count``, igual que Ss y St; de ahí salen los totales
      ``weight_air_kg``/``weight_water_kg`` y el reparto por plano (I110:I113).

    Además, como la hoja, Σd/Σl no pondera por paneles.
    """
    rows = group_rows(spec)
    notes: list[str] = []
    if compat is Compat.EXCEL:
        rows = apply_excel_codend_quirk(rows)
        notes.append(
            t(
                "{code}: bolsas I/J con T2 := N (Mec!K36:K37)",
                code=ERRATUM_CODEND_MINOR_SIDE,
            )
        )

    mats: Sequence[Material] | None = materials
    if compat is Compat.CORRECTED and mats is None:
        mats = materials_from_catalogue(load_catalogue("materials"))

    pi = EXCEL_PI if compat is Compat.EXCEL else math.pi
    geoms: list[RowGeometry] = []
    for r in rows:
        u2 = float(vertical_opening_coefficient(r.u1))
        density = float(twine_density_kg_m3(r.twine_mm, r.mesh_mm, r.runnage_m_per_kg, compat))
        sn = float(reference_twine_weight_kg(r.mesh_mm, r.twine_mm, density, pi=pi))
        w_air = float(panel_weight_air_kg(r.t1, r.t2, r.n, sn))
        if compat is Compat.CORRECTED:
            w_air *= r.count  # errata net_weight_ignores_panel_count (O107 = ΣO98:O106)
        if compat is Compat.EXCEL:
            rho_buoyancy = density
        else:
            assert mats is not None
            rho_buoyancy = find_material(tuple(mats), r.material, rtex=r.rtex).density_kg_m3
        geoms.append(
            RowGeometry(
                row=r,
                u2=u2,
                length_m=float(panel_length_m(r.n, r.mesh_mm)),
                filtration=float(filtration_per_row(r.twine_mm, r.mesh_mm, r.count)),
                solid_surface_m2=float(
                    solid_surface_m2(r.twine_mm, r.mesh_mm, r.t1, r.t2, r.n, r.count)
                ),
                working_surface_m2=float(
                    working_surface_m2(
                        r.u1,
                        r.mesh_mm,
                        r.t1,
                        r.t2,
                        r.n,
                        r.count,
                        opening=opening_product(r.orientation, r.u1)
                        if r.orientation == "square"
                        else None,
                    )
                ),
                twine_density_kg_m3=density,
                reference_twine_weight_kg=sn,
                weight_air_kg=w_air,
                weight_water_kg=float(weight_in_water_kg(w_air, rho_buoyancy)),
            )
        )

    mod_codend = [
        i for i, r in enumerate(rows) if r.section is Section.CODEND and len(r.planes) > 1
    ]
    filt = filtration_index(
        [r.twine_mm for r in rows],
        [r.mesh_mm for r in rows],
        [r.count for r in rows],
        mod_codend_index=mod_codend[0] if mod_codend else None,
        compat=compat,
    )
    ss = sum(g.solid_surface_m2 for g in geoms)
    st = sum(g.working_surface_m2 for g in geoms)
    sol = float(solidity(ss, st))
    return NetGeometry(
        net_id=spec.id,
        compat=compat,
        rows=tuple(geoms),
        filtration=filt,
        solid_surface_m2=ss,
        working_surface_m2=st,
        solidity=sol,
        filtering_coefficient=float(filtering_coefficient(sol)),
        solid_surface_by_plane=split_by_plane(rows, [g.solid_surface_m2 for g in geoms]),
        weight_air_kg=sum(g.weight_air_kg for g in geoms),
        weight_water_kg=sum(g.weight_water_kg for g in geoms),
        weight_by_plane=split_by_plane(rows, [g.weight_air_kg for g in geoms]),
        notes=tuple(notes),
    )
