"""Discretización de la red en elementos triangulares de paño, relingas y bridas.

Topología
---------
Cada panel del plano relingado (:func:`trawlkit.drawing.layout_net`, modo ``"true_scale"``) se
divide en una grilla estructurada de ``(filas + 1) × (columnas + 1)`` nodos, interpolada
bilinealmente entre sus cuatro esquinas; cada celda se parte en dos triángulos. Los nodos que
representan el mismo punto físico se **unifican** (union-find):

* boca → bolsa dentro de un plano: borde inferior de un panel = borde superior del siguiente
  (A→C, C→E/F, E→G, G→H, H→I/J); las alas apoyan sobre los costados del primer panel central y
  el hueco central es la bocana (100 mallas en el dorso, 86 en el vientre);
* costuras laterales (*selvedges*): el costado exterior de cada panel del dorso con el del
  panel del vientre de la misma franja (A–B, C–D, E–F, G–G, H–H, I–J), lo que cierra el embudo;
* la bolsa se cierra atando todo su borde final en un nodo (el *codend line*).

Mecánica del paño (elemento triangular de Priour)
-------------------------------------------------
El paño de malla rómbica tiene dos familias de hilos. En coordenadas de malla ``(t, n)`` (mallas
a lo ancho y a lo alto del panel) las coordenadas de hilo son ``i = n + t`` y ``j = n − t``, en
unidades de **una pata** de largo ``a = mallero / 2``. Dentro de un triángulo la posición es
lineal en ``(i, j)``, de modo que ``∂x/∂i`` y ``∂x/∂j`` son constantes: son los vectores de una
pata de cada familia. El triángulo contiene ``A_ij`` patas de cada familia (``A_ij`` = área en
coordenadas de hilo), de modo que

* longitud total de hilo = ``2 · a · A_ij`` y, sumada sobre un panel, ``Σ d·L`` coincide con la
  superficie sólida FAO ``Ss = d · N · mallero · (T1 + T2)`` (identidad verificada en los tests);
* la tensión de cada familia es ``T = EA · max(|∂x/∂i| / a − 1, 0)`` (sólo tracción).

Orientación de la malla (``Panel.mesh_orientation``): en **T90** el paño va girado 90°, así que
la diagonal larga de la malla queda a lo ancho; el mapeo ``i = n + t``, ``j = n − t`` no cambia
(la malla sigue siendo un rombo con las diagonales sobre los ejes del panel) pero el ángulo de
reposo del nudo sí (ver :data:`DIAMOND_REST_ANGLE_DEG`). En malla **cuadrada** los hilos siguen
los ejes del panel: ``i = t``, ``j = n``, con ``t`` y ``n`` medidos en patas. En los tres casos
cada celda unidad en ``(i, j)`` es una malla: el triángulo tiene ``A_ij`` mallas.

Este es el elemento triangular de Priour (1999, "Calculation of net shapes by the finite element
method with triangular elements", *Commun. Numer. Meth. Engng.* 15:755–763; Priour 2013, *A
Finite Element Method for Netting*, Springer), que da al paño rigidez nula al corte y a la
flexión y reproduce el acoplamiento U1² + U2² ≤ 1 de la malla rómbica (el paño se angosta
cuando se alarga). Una grilla de barras a lo largo de ``t`` y ``n`` no lo haría: permitiría
abrir la malla del todo en las dos direcciones a la vez.

Relingas, bridas y patentes
---------------------------
La relinga superior (lima) y la inferior (burlón) son barras entre nodos consecutivos del borde
de la boca, con largo natural repartido según el largo relingado de cada tramo y escalado al
largo de cada pieza del motor (alas y bocana). Las bridas superior e inferior (más la cadena de
reglaje) van de cada punta de ala a un nodo de unión (dan leno), y la patente de ese nodo al
punto de remolque del portón, que se fija en ``y = ±DP/2``, ``z = alto del portón / 2``.

Detalles y valores por defecto
------------------------------
* Materiales (Fase 19.1, :func:`trawlkit.materials.material_table`): cada panel toma la densidad
  y el módulo de su hilo de ``Panel.material`` (PA si no está en la tabla). Peso sumergido del
  hilo ``g/rendimiento · (1 − ρ_agua/ρ_material)``: el PA (1140 kg/m³) y el PES pesan en el agua,
  el PE y el PP flotan. EA del hilo = ``E·π d²/4`` con ``E`` = 2 GPa para PA (supuesto, del orden
  de la fibra × el cociente hilo/fibra medido), 0,60 GPa para PE (legue2025) y el de PA escalado
  por el cociente de módulos de fibra para PES (3,27), PP (1,53) y HMPE (30,9 GPa).
* Relingas: EA de :class:`Rigging` (del cabo del motor por la relación ``EA = k·d²`` de su
  material; combinadas ``10⁶ N``, supuesto «A VERIFICAR»). Cable de remolque: 6x19 con
  ``EA = 36 700·d_mm²`` N (alma de fibra; 40 400 con alma de acero), es decir un módulo efectivo
  de 46,9 GPa (51,4) sobre el área nominal (OrcaFlex/HER). Bridas y patentes: la misma relación
  si se conoce su diámetro (``Rigging.bridle_diameter_mm``); si no, ``4·10⁶ N`` (supuesto,
  6x19 de Ø10,4 mm), con el peso sumergido del cable del motor. Las deformaciones de trabajo del
  paño y de los cables quedan por debajo del 0,5 %.
* La punta de ala (A, B) tiene un borde de boca de 3 mallas; se reduce a un punto (evita
  triángulos de relación de aspecto ~20, rígidos y lentos de relajar) y las puntas de lima y
  burlón se unen con una barra ``wing_end`` del largo estirado de esos dos bordes (6 mallas).
  La superficie sólida pierde < 0,2 %.
* La bolsa inferior J (250 mallas de alto) se cose fila a fila a la superior I (200 mallas): el
  exceso de J forma un bolsón flojo, como en la red real.
* Posición inicial: el plano relingado curvado como un embudo (dorso en arco sobre el vientre).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt

from trawlkit.drawing.layout import Band, NetLayout, PanelShape, layout_net
from trawlkit.i18n import t
from trawlkit.io.schema import NetSpec, Panel
from trawlkit.materials import (
    DEFAULT_ROPE_EA_N,
    polymer_density,
    wire_rope_ea_n,
)
from trawlkit.materials import (
    twine_modulus_pa as material_twine_modulus_pa,
)
from trawlkit.netting import orientation_coefficients
from trawlkit.topology import equivalent_two_panel

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.int64]

#: Densidad de la poliamida (PA6) [kg/m³]. Desde la Fase 19.1 cada panel usa la densidad de su
#: material (:func:`trawlkit.materials.polymer_density`); se conserva como referencia.
RHO_PA = 1140.0
#: Densidad del agua de mar del simulador [kg/m³].
RHO_SEA = 1024.0
#: EA de bridas y patentes cuando no se conoce su diámetro [N] (supuesto «A VERIFICAR»: el
#: motor no dimensiona el cable de las bridas; equivale a un 6x19 con alma de fibra de Ø10,4 mm
#: con ``EA = 36 700·d_mm²``, OrcaFlex/HER). Con el diámetro del cable de remolque (12–13 mm)
#: sería ≈ 6·10⁶ N: la AV simulada de la A-3 sube 0,3 % y la relajación tarda el doble.
DEFAULT_BRIDLE_EA_N = 4.0e6
#: Aceleración de la gravedad [m/s²].
GRAVITY = 9.80665
#: Ángulo de reposo entre las dos familias de hilos de la malla rómbica [°] (A VERIFICAR: el
#: paño usado y relajado queda entreabierto; Sala et al. 2007 miden la resistencia de la malla a
#: abrirse). En T90 el reposo es el suplemento (el nudo girado tiende a abrir la malla a lo
#: ancho) y en malla cuadrada, 90°.
DIAMOND_REST_ANGLE_DEG = 40.0


def rest_angle_rad(orientation: str, diamond_deg: float = DIAMOND_REST_ANGLE_DEG) -> float:
    """Ángulo de reposo entre ``∂x/∂i`` y ``∂x/∂j`` según la orientación de la malla [rad]."""
    o = str(orientation)
    if o == "square":
        return math.pi / 2.0
    beta = math.radians(diamond_deg)
    return math.pi - beta if o == "t90" else beta


@dataclass(frozen=True)
class Rigging:
    """Datos del aparejo que el simulador toma del motor (o de la spec, con valores por defecto).

    Largos en m, pesos en agua en kgf, flotación en kgf.
    """

    door_spread_m: float
    upper_bridle_m: float
    lower_bridle_m: float
    sweeps_m: float
    headrope_wing_m: float
    headrope_bosom_m: float
    footrope_wing_m: float
    footrope_bosom_m: float
    headrope_diameter_mm: float
    footrope_diameter_mm: float
    headrope_water_kgf_m: float
    footrope_water_kgf_m: float
    float_count: int
    float_buoyancy_kgf: float
    float_diameter_mm: float
    float_cd: float
    float_positions_m: tuple[float, ...]
    ballast_wings_kg: float
    ballast_bosom_kg: float
    ballast_tips_kg: float
    door_height_m: float = 0.95
    wire_water_kgf_m: float = 0.49  # peso sumergido de bridas y patentes (cable de acero)
    # Portones acoplados (Scenario.coupled_doors): polar al ángulo de ataque del caso, peso en el
    # agua y cable de remolque hasta el buque (valores por defecto: portón FAO A-3 a 32°).
    door_area_m2: float = 1.805
    door_cl: float = 0.93
    door_cd: float = 0.71
    door_weight_water_kgf: float = 80.6
    warp_length_m: float = 200.0
    depth_m: float = 40.0
    gallows_m: float = 2.5
    warp_diameter_mm: float = 12.0
    vessel_bhp: float = 150.0  # potencia del buque (tope de la potencia de remolque)
    door_length_m: float = 1.9
    # Rigidez axial [N] (Fase 19.1). None = valor por defecto: relingas combinadas 10⁶ N
    # (supuesto «A VERIFICAR»); bridas y patentes, cable 6x19 de ``bridle_diameter_mm`` si se
    # conoce y si no :data:`DEFAULT_BRIDLE_EA_N`; cable de remolque, 6x19 de ``warp_diameter_mm``
    # con alma ``warp_core`` (``EA = k·d²``, OrcaFlex/HER).
    headrope_ea_n: float | None = None
    footrope_ea_n: float | None = None
    bridle_ea_n: float | None = None
    bridle_diameter_mm: float | None = None
    warp_ea_n: float | None = None
    warp_core: str = "FC"
    # Polar completa del portón (ángulo [°], CL, CD) y ángulo de ataque del caso [°] (Fase 19.3):
    # la polar dinámica de los portones acoplados (``Scenario.dynamic_door_polar``) la lee para
    # recalcular CL y CD al ángulo que resulta de la geometría resuelta.
    door_polar: tuple[tuple[float, float, float], ...] = ()
    door_attack_angle_deg: float = 32.0
    #: Arrastre de vara (Fase 19.5): altura de la vara sobre el fondo [m]. Las puntas de la lima
    #: quedan fijas en los extremos de la vara (``y = ±door_spread_m/2``, ``z`` = esta altura) y
    #: las del burlón en los patines (``z = 0``); no hay bridas ni patentes. ``None`` = portones.
    beam_height_m: float | None = None

    def rope_ea(self, which: str) -> float:
        """EA de la lima (``headrope``) o del burlón (``footrope``) [N]."""
        ea = self.headrope_ea_n if which == "headrope" else self.footrope_ea_n
        return DEFAULT_ROPE_EA_N if ea is None else float(ea)

    def wire_ea(self) -> float:
        """EA de bridas y patentes [N]: dato, cable 6x19 de ``bridle_diameter_mm`` o supuesto."""
        if self.bridle_ea_n is not None:
            return float(self.bridle_ea_n)
        if self.bridle_diameter_mm is not None:
            return wire_rope_ea_n(self.bridle_diameter_mm, self.warp_core)
        return DEFAULT_BRIDLE_EA_N

    def warp_ea(self) -> float:
        """EA del cable de remolque [N] (módulo efectivo sobre el área nominal)."""
        if self.warp_ea_n is not None:
            return float(self.warp_ea_n)
        return wire_rope_ea_n(self.warp_diameter_mm, self.warp_core)


@dataclass(frozen=True)
class PanelGrid:
    """Grilla de nodos de un panel en un plano (fila 0 = boca, columna 0 = interior/izquierda)."""

    key: str
    panel_id: str
    plane: str
    side: str
    nodes: IntArray
    s_cols: FloatArray  # fracción del ancho de cada columna (0 = interior/izquierda)
    r_rows: FloatArray  # fracción del alto de cada fila (0 = boca)


@dataclass(frozen=True)
class NetModel:
    """Modelo discreto: nodos, triángulos de paño, barras (relingas, bridas, patentes)."""

    x0: FloatArray  # posiciones iniciales (n, 3)
    # Triángulos de paño
    tri: IntArray  # (nt, 3)
    tri_gi: FloatArray  # (nt, 3) coeficientes de ∂x/∂i
    tri_gj: FloatArray  # (nt, 3) coeficientes de ∂x/∂j
    tri_area: FloatArray  # (nt,) patas de cada familia en el triángulo
    tri_a: FloatArray  # (nt,) largo de pata [m]
    tri_d: FloatArray  # (nt,) diámetro del hilo [m]
    tri_ea: FloatArray  # (nt,) EA de un hilo [N]
    tri_w: FloatArray  # (nt,) peso sumergido del hilo [N/m]
    tri_panel: tuple[str, ...]  # clave de panel de cada triángulo
    # Barras (relingas, bridas, patentes)
    bar: IntArray  # (nb, 2)
    bar_l0: FloatArray
    bar_ea: FloatArray
    bar_d: FloatArray  # diámetro hidrodinámico [m] (0 = sin carga hidrodinámica)
    bar_w: FloatArray  # peso sumergido [N/m]
    bar_kind: tuple[str, ...]  # "headrope", "footrope", "upper_bridle", "lower_bridle", "sweep"
    # Cargas puntuales constantes [N] (flotación, lastre) y nodos con boyas
    point_load: FloatArray  # (n, 3)
    float_nodes: IntArray
    float_weights: FloatArray  # fracción de boya por nodo (suma = nº de boyas)
    float_buoyancy_n: float  # empuje de una boya [N]
    float_area_m2: float  # área frontal de una boya [m²]
    fixed: IntArray  # nodos fijos (puntos de remolque de los portones)
    # Nodos característicos
    headrope: IntArray  # lima, de punta derecha a punta izquierda
    footrope: IntArray  # burlón, de punta derecha a punta izquierda
    headrope_centre: int
    footrope_centre: int
    wing_tips_upper: tuple[int, int]  # (derecha, izquierda)
    wing_tips_lower: tuple[int, int]
    junctions: tuple[int, int]
    doors: tuple[int, int]
    grids: tuple[PanelGrid, ...]
    mirror: IntArray  # índice del nodo simétrico (y → −y)
    solid_surface_m2: float  # Σ d·L del paño discretizado
    #: Sección de cada triángulo (``Panel.section``: wing_tip, wing, square, belly, body,
    #: extension, codend).
    tri_section: tuple[str, ...] = ()
    #: Orientación de la malla de cada triángulo (diamond, t90, square) y ángulo de reposo entre
    #: las dos familias de hilos [rad] (rigidez de apertura de la malla, ``Params.mesh_bending``).
    tri_orientation: tuple[str, ...] = ()
    tri_rest_angle: FloatArray = field(default_factory=lambda: np.zeros(0))
    #: Anillos del copo y del cuerpo (dorso + vientre), del extremo cerrado hacia la boca.
    codend_rings: tuple[IntArray, ...] = ()
    #: Portones libres con cable hasta el buque (los puntos del buque son los nodos fijos).
    coupled_doors: bool = False
    warp_nodes: tuple[IntArray, IntArray] = (
        np.zeros(0, dtype=np.int64),
        np.zeros(0, dtype=np.int64),
    )
    door_area_m2: float = 0.0
    door_cl: float = 0.0
    door_cd: float = 0.0
    door_weight_n: float = 0.0
    door_floor_m: float = 0.0  # altura del nodo del portón sobre la zapata [m]
    warp_length_m: float = 0.0  # largo de cable filado del modelo acoplado [m]
    #: Polar del portón (filas ángulo [°], CL, CD) y ángulo de ataque del caso (Fase 19.3).
    door_polar: FloatArray = field(default_factory=lambda: np.zeros((0, 3)))
    door_angle_deg: float = 0.0
    #: Factores de la polar (escenario: calibración e incertidumbre) para la polar dinámica.
    door_cl_factor: float = 1.0
    door_cd_factor: float = 1.0
    #: Red pelágica: trabaja a media agua, sin la restricción del fondo (Fase 12).
    floor_free: bool = False
    #: Vara (Fase 19.5): las cuatro puntas de ala son nodos fijos (ver ``Rigging.beam_height_m``).
    fixed_tips: bool = False

    @property
    def n_nodes(self) -> int:
        """Cantidad de nodos."""
        return int(self.x0.shape[0])


# ---------------------------------------------------------------------------------------------
# Union-find
# ---------------------------------------------------------------------------------------------


class _UnionFind:
    def __init__(self) -> None:
        self.parent: list[int] = []

    def make(self) -> int:
        self.parent.append(len(self.parent))
        return len(self.parent) - 1

    def find(self, a: int) -> int:
        root = a
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[a] != root:
            self.parent[a], a = root, self.parent[a]
        return root

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


# ---------------------------------------------------------------------------------------------
# Construcción
# ---------------------------------------------------------------------------------------------


def _u1u2(panel: Panel) -> tuple[float, float]:
    u1 = float(panel.hanging_ratio) if panel.hanging_ratio is not None else 0.5
    return orientation_coefficients(panel.mesh_orientation, u1)


def _runnage(panel: Panel) -> float:
    if panel.runnage_m_per_kg:
        return float(panel.runnage_m_per_kg)
    if panel.rtex:
        return 1e6 / float(panel.rtex)
    d = panel.twine_diameter_mm / 1000.0
    rho = polymer_density(panel.material)
    return 1.0 / (rho * math.pi * d * d / 4.0 * 0.6)  # hilo torcido: ~60 % de relleno


def twine_weight_water_n_m(panel: Panel) -> float:
    """Peso sumergido del hilo del panel [N/m]: ``g/rendimiento · (1 − ρ_agua/ρ_material)``.

    Negativo para los hilos que flotan (PE, PP, HMPE).
    """
    return GRAVITY / _runnage(panel) * (1.0 - RHO_SEA / polymer_density(panel.material))


def twine_ea_n(panel: Panel, modulus_pa: float | None = None) -> float:
    """EA de un hilo del panel [N]: ``E·π d²/4`` con el módulo de su material (o ``modulus_pa``)."""
    e = material_twine_modulus_pa(panel.material) if modulus_pa is None else modulus_pa
    d = panel.twine_diameter_mm / 1000.0
    return e * math.pi * d * d / 4.0


@dataclass
class _PlaneTopo:
    """Nodos característicos de un plano (antes de compactar)."""

    grids: list[PanelGrid]
    outer_r: list[IntArray]
    outer_l: list[IntArray]
    mouth_r: list[IntArray]
    mouth_l: list[IntArray]
    bosom: IntArray
    collapsed: bool
    wing_end_m: float
    wing_end_ea: float
    tip_r: int
    tip_l: int
    codend_end: IntArray


def _collapses_top(panel: Panel) -> bool:
    """El borde de boca de una punta de ala casi triangular (≤ 15 % del borde opuesto)."""
    return panel.section.value == "wing_tip" and panel.meshes_top <= 0.15 * panel.meshes_bottom


_FORCE_SIGMA_SEAMS = False


def _band_rows(
    bands_u: Sequence[Band], bands_l: Sequence[Band], resolution: int
) -> tuple[dict[str, list[FloatArray]], dict[str, list[FloatArray]], bool]:
    """Filas de nodos de cada franja de dorso y vientre (fracciones del alto de la franja).

    Con la misma cantidad de franjas (la FAO A-3) cada par de franjas lleva
    :func:`_rows_for` filas parejas, y las costuras se arman franja por franja. Si las franjas
    son distintas (cielo sólo en el dorso, alas de distinto largo), se trabaja en la posición
    relativa a lo largo de la red ``σ = y / L`` de cada plano: los bordes de franja de los dos
    planos parten el largo en tramos, cada tramo lleva las mismas filas en los dos planos, y la
    costura une nodos de igual ``σ``. Devuelve también las ``σ`` de cada fila.
    """
    same = len(bands_u) == len(bands_l) and not _FORCE_SIGMA_SEAMS
    planes = {"upper": bands_u, "lower": bands_l}
    r_out: dict[str, list[FloatArray]] = {"upper": [], "lower": []}
    s_out: dict[str, list[FloatArray]] = {"upper": [], "lower": []}
    length = {pl: (b[-1].y_bottom - b[0].y_top) or 1.0 for pl, b in planes.items()}
    if same:
        for bu, bl in zip(bands_u, bands_l, strict=True):
            n = _rows_for(max(bu.y_bottom - bu.y_top, bl.y_bottom - bl.y_top), resolution)
            r = np.linspace(0.0, 1.0, n + 1)
            for pl, b in (("upper", bu), ("lower", bl)):
                r_out[pl].append(r)
                y0 = b.y_top - planes[pl][0].y_top
                s_out[pl].append((y0 + r * (b.y_bottom - b.y_top)) / length[pl])
        return r_out, s_out, True
    cuts: list[float] = []
    for pl, bs in planes.items():
        for b in bs:
            for y in (b.y_top, b.y_bottom):
                cuts.append((y - bs[0].y_top) / length[pl])
    cuts.sort()
    sigma = [0.0]
    for c in cuts:
        if c - sigma[-1] > 2e-3:
            sigma.append(c)
    sigma[-1] = 1.0
    span = max(length.values())
    k = [
        max(1, round(resolution * (b - a) * span / 9.0))
        for a, b in zip(sigma, sigma[1:], strict=False)
    ]

    def snap(v: float) -> int:
        return int(np.argmin(np.abs(np.asarray(sigma) - v)))

    # Al menos 2 filas por franja: se reparten en sus tramos (iguales en los dos planos).
    for _ in range(4):
        changed = False
        for pl, bs in planes.items():
            for b in bs:
                i0 = snap((b.y_top - bs[0].y_top) / length[pl])
                i1 = snap((b.y_bottom - bs[0].y_top) / length[pl])
                if i1 > i0 and sum(k[i0:i1]) < 2:
                    k[int(np.argmax([sigma[j + 1] - sigma[j] for j in range(i0, i1)])) + i0] += 1
                    changed = True
        if not changed:
            break
    for pl, bs in planes.items():
        for b in bs:
            i0 = snap((b.y_top - bs[0].y_top) / length[pl])
            i1 = max(snap((b.y_bottom - bs[0].y_top) / length[pl]), i0 + 1)
            pts = [sigma[i0]]
            for j in range(i0, min(i1, len(k))):
                pts.extend(np.linspace(sigma[j], sigma[j + 1], k[j] + 1)[1:].tolist())
            sv = np.asarray(pts)
            r_out[pl].append((sv - sv[0]) / max(sv[-1] - sv[0], 1e-12))
            s_out[pl].append(sv)
    return r_out, s_out, False


def _rows_for(height_m: float, resolution: int) -> int:
    return max(2, round(resolution * height_m / 9.0))


def _grid_positions(
    shape: PanelShape, s_cols: FloatArray, r_rows: FloatArray, inner_to_outer: bool
) -> tuple[FloatArray, FloatArray]:
    """Posiciones 2D del plano (x lateral, y boca→bolsa) de la grilla de un panel.

    ``r_rows`` son las fracciones del alto (0 = boca, 1 = bolsa) de cada fila de nodos.
    """
    s = np.asarray(s_cols, dtype=float)
    r = np.asarray(r_rows, dtype=float)
    if inner_to_outer and shape.side == "left":
        # col 0 = interior (x mayor) → exterior (x menor)
        xt = shape.x_top[1] - s * shape.width_top
        xb = shape.x_bottom[1] - s * shape.width_bottom
    else:
        xt = shape.x_top[0] + s * shape.width_top
        xb = shape.x_bottom[0] + s * shape.width_bottom
    xx = xt[None, :] * (1 - r[:, None]) + xb[None, :] * r[:, None]
    yy = np.broadcast_to(shape.y_top + (shape.y_bottom - shape.y_top) * r[:, None], xx.shape)
    return xx, np.array(yy)


#: Largo mínimo del tramo patente/unión hasta el punto de remolque [m] (destorcedor y grilletes).
MIN_SWEEP_M = 1.0


def build_model(
    spec: NetSpec,
    rigging: Rigging,
    *,
    resolution: int = 8,
    twine_modulus_pa: float | None = None,
    rope_ea_n: float | None = None,
    wire_ea_n: float | None = None,
    coupled_doors: bool = False,
    warp_segments: int = 10,
) -> NetModel:
    """Discretiza ``spec`` con el aparejo ``rigging`` (ver el docstring del módulo).

    ``twine_modulus_pa`` (módulo de todos los hilos), ``rope_ea_n`` (las dos relingas) y
    ``wire_ea_n`` (bridas y patentes) reemplazan, si se dan, los valores por material y del
    aparejo (:class:`Rigging`); ``None`` usa la tabla de materiales.

    ``resolution`` es la cantidad nominal de divisiones por panel: el ancho de cada ala tiene
    ``resolution // 2`` columnas, la bocana ``2·⌈resolution/6⌉`` y las filas de cada franja son
    proporcionales a su largo relingado (``resolution`` filas cada 9 m, mínimo 2).

    Con ``coupled_doors`` los portones son nodos libres y se agrega cada cable de remolque como
    ``warp_segments`` barras (peso y Morison del cable) hasta el punto del buque, que queda fijo
    a ``depth_m`` sobre el fondo, ``gallows_m/2`` del eje y a la distancia horizontal que permite
    el largo filado.
    """
    if resolution < 2:
        raise ValueError(t("resolution debe ser ≥ 2"))
    # Las redes de 4 paneles se simulan con su equivalente de 2 (trawlkit.topology).
    spec = equivalent_two_panel(spec)
    layout = layout_net(spec, mode="true_scale")
    planes = [p for p in ("upper", "lower") if p in layout.shapes]
    if planes != ["upper", "lower"]:
        raise ValueError(t("la simulación necesita una red de dos caras (planos upper y lower)"))
    n_w = max(2, resolution // 2)
    n_b = max(2, 2 * math.ceil(resolution / 6))

    uf = _UnionFind()
    pos: list[tuple[float, float, float]] = []
    tris: list[tuple[int, int, int]] = []
    tri_mc: list[tuple[tuple[float, float], ...]] = []
    tri_panel: list[str] = []
    tri_sect: list[str] = []
    tri_orient: list[str] = []
    tri_props: list[tuple[float, float, float, float]] = []  # a, d, EA, w
    grids: list[PanelGrid] = []

    bands = {pl: layout.bands[pl] for pl in planes}
    band_r, band_s, same_bands = _band_rows(bands["upper"], bands["lower"], resolution)

    def add_grid(
        shape: PanelShape, plane: str, s_cols: FloatArray, r_rows: FloatArray
    ) -> PanelGrid:
        panel = shape.panel
        xx, yy = _grid_positions(shape, s_cols, r_rows, inner_to_outer=shape.side != "center")
        u1, u2 = _u1u2(panel)
        mesh_m = panel.mesh_mm / 1000.0
        collapse = _collapses_top(panel)
        if collapse:
            # Punta de ala: el borde de boca (3 mallas) se reduce a un punto (ver build_model).
            xx[0, :] = xx[0, :].mean()
        # (t, n): mallas a lo ancho y a lo alto (rombo, T90) o patas (cuadrada).
        t = xx / (mesh_m * u1)
        n = (yy - shape.y_top) / (mesh_m * u2)
        orient = str(panel.mesh_orientation)
        ids = np.empty(xx.shape, dtype=np.int64)
        for (r_, c_), _ in np.ndenumerate(xx):
            ids[r_, c_] = uf.make()
            pos.append((float(yy[r_, c_]), float(xx[r_, c_]), 0.0))
        if collapse:
            for k in ids[0, 1:].tolist():
                uf.union(int(ids[0, 0]), int(k))
        a = mesh_m / 2.0
        d = panel.twine_diameter_mm / 1000.0
        ea = twine_ea_n(panel, twine_modulus_pa)
        w = twine_weight_water_n_m(panel)
        key = f"{plane}:{panel.id}:{shape.side}"
        n_cols = xx.shape[1] - 1
        for r_ in range(xx.shape[0] - 1):
            for c_ in range(n_cols):
                q = ((r_, c_), (r_, c_ + 1), (r_ + 1, c_ + 1), (r_ + 1, c_))
                # Diagonal espejada en la mitad izquierda de los paneles centrales, para que la
                # triangulación sea simétrica respecto del eje (y = 0).
                if shape.side == "center" and 2 * c_ < n_cols:
                    split = ((q[0], q[1], q[3]), (q[1], q[2], q[3]))
                else:
                    split = ((q[0], q[1], q[2]), (q[0], q[2], q[3]))
                for tri_q in split:
                    i0, i1, i2 = (int(ids[k]) for k in tri_q)
                    tris.append((i0, i1, i2))
                    tri_mc.append(tuple((float(t[k]), float(n[k])) for k in tri_q))
                    tri_panel.append(key)
                    tri_sect.append(panel.section.value)
                    tri_orient.append(orient)
                    tri_props.append((a, d, ea, w))
        g = PanelGrid(
            key,
            panel.id,
            plane,
            shape.side,
            ids,
            np.asarray(s_cols, float),
            np.asarray(r_rows, dtype=float),
        )
        grids.append(g)
        return g

    def union_edges(a: IntArray, b: IntArray) -> None:
        if a.shape != b.shape:
            raise ValueError("bordes de distinto largo")
        for p, q in zip(a.tolist(), b.tolist(), strict=True):
            uf.union(int(p), int(q))

    per_plane: dict[str, _PlaneTopo] = {}
    for plane in planes:
        central = list(layout.central(plane))
        right = list(layout.side_chain(plane, "right"))
        left = list(layout.side_chain(plane, "left"))
        rows_of = {id(b.panel): band_r[plane][k] for k, b in enumerate(bands[plane])}
        first = central[0]
        last_wing = right[-1]
        f_right = (last_wing.x_bottom[0] - first.x_top[0]) / first.width_top
        f_left = 1.0 - f_right
        s_central = np.concatenate(
            [
                np.linspace(0.0, f_left, n_w + 1),
                np.linspace(f_left, f_right, n_b + 1)[1:],
                np.linspace(f_right, 1.0, n_w + 1)[1:],
            ]
        )
        s_wing = np.linspace(0.0, 1.0, n_w + 1)
        cg = [add_grid(sh, plane, s_central, rows_of[id(sh.panel)]) for sh in central]
        rg = [add_grid(sh, plane, s_wing, rows_of[id(sh.panel)]) for sh in right]
        lg = [add_grid(sh, plane, s_wing, rows_of[id(sh.panel)]) for sh in left]
        for chain in (cg, rg, lg):
            for g0, g1 in zip(chain[:-1], chain[1:], strict=True):
                union_edges(g0.nodes[-1, :], g1.nodes[0, :])
        top = cg[0].nodes[0, :]
        union_edges(rg[-1].nodes[-1, :], top[n_w + n_b :])
        union_edges(lg[-1].nodes[-1, :], top[: n_w + 1][::-1])
        # Costado exterior por franja (de boca a bolsa), para las costuras laterales.
        outer_r = [g.nodes[:, -1] for g in rg] + [g.nodes[:, -1] for g in cg]
        outer_l = [g.nodes[:, -1] for g in lg] + [g.nodes[:, 0] for g in cg]
        mouth_r = [g.nodes[:, 0] for g in rg]
        mouth_l = [g.nodes[:, 0] for g in lg]
        tip_panel = right[0].panel
        per_plane[plane] = _PlaneTopo(
            grids=[*cg, *rg, *lg],
            outer_r=outer_r,
            outer_l=outer_l,
            mouth_r=mouth_r,
            mouth_l=mouth_l,
            bosom=cg[0].nodes[0, n_w : n_w + n_b + 1][::-1],  # de derecha a izquierda
            collapsed=_collapses_top(tip_panel),
            wing_end_m=tip_panel.meshes_top * tip_panel.mesh_mm / 1000.0,
            wing_end_ea=twine_ea_n(tip_panel, twine_modulus_pa) * max(2 * tip_panel.meshes_top, 1),
            tip_r=int(rg[0].nodes[0, 0]),
            tip_l=int(lg[0].nodes[0, 0]),
            codend_end=cg[-1].nodes[-1, :],
        )

    up, lo = per_plane["upper"], per_plane["lower"]
    for edges_u, edges_l in ((up.outer_r, lo.outer_r), (up.outer_l, lo.outer_l)):
        if same_bands:
            for k_band, (a_e, b_e) in enumerate(zip(edges_u, edges_l, strict=True)):
                if k_band == 0 and (up.collapsed or lo.collapsed):
                    # Las puntas de lima y burlón quedan separadas: las une la barra "wing_end".
                    a_e, b_e = a_e[1:], b_e[1:]
                union_edges(a_e, b_e)
            continue
        # Franjas distintas en dorso y vientre: las filas de ambos planos están en las mismas
        # posiciones relativas del largo (``_band_rows``); se cosen los nodos de igual posición.
        at: dict[float, list[int]] = {}
        for edges, s_list in ((edges_u, band_s["upper"]), (edges_l, band_s["lower"])):
            for e, s_e in zip(edges, s_list, strict=True):
                for node, s_node in zip(e.tolist(), s_e.tolist(), strict=True):
                    at.setdefault(round(s_node, 9), []).append(int(node))
        for s_key, nodes in at.items():
            if s_key == 0.0 and (up.collapsed or lo.collapsed):
                continue
            for k in nodes[1:]:
                uf.union(nodes[0], k)
    end = np.concatenate([up.codend_end, lo.codend_end])
    for k in end[1:].tolist():
        uf.union(int(end[0]), int(k))

    # --- compactar nodos -------------------------------------------------------------------
    n_raw = len(pos)
    roots = np.array([uf.find(k) for k in range(n_raw)], dtype=np.int64)
    uniq, remap = np.unique(roots, return_inverse=True)
    n_net = int(uniq.size)
    raw_pos = np.asarray(pos, dtype=float)
    cnt = np.bincount(remap, minlength=n_net).astype(float)
    xy = np.stack([np.bincount(remap, raw_pos[:, k], n_net) / cnt for k in range(2)], axis=1)

    def m(ids: IntArray | int) -> IntArray:
        return np.asarray(remap[np.asarray(ids)], dtype=np.int64)

    # Posición inicial: embudo elíptico. x = largo desde la punta de ala, y = lateral (con la
    # anchura relingada), z: dorso en arco elíptico sobre el vientre apoyado en el fondo.
    plane_of = np.zeros(n_net, dtype=np.int64)  # 0 vientre, 1 dorso (interior)
    for g in up.grids:
        plane_of[m(g.nodes).ravel()] = 1
    for g in lo.grids:
        plane_of[m(g.nodes).ravel()] = np.where(plane_of[m(g.nodes).ravel()] == 1, 2, 0)
    x0 = np.zeros((n_net, 3))
    x0[:, 0] = xy[:, 0]
    x0[:, 1] = xy[:, 1]
    half = _half_width_profile(layout, xy[:, 0])
    phi = np.clip(np.abs(xy[:, 1]) / np.maximum(half, 1e-6), 0.0, 1.0)
    dome = 0.45 * half * np.cos(0.5 * math.pi * phi)
    x0[:, 2] = np.where(plane_of == 1, dome, 0.0) + 0.05

    tri = m(np.asarray(tris, dtype=np.int64))
    tri_a = np.array([p[0] for p in tri_props])
    tri_d = np.array([p[1] for p in tri_props])
    tri_ea = np.array([p[2] for p in tri_props])
    tri_w = np.array([p[3] for p in tri_props])
    gi, gj, area = _twine_operators(tri_mc, np.array([o == "square" for o in tri_orient]))
    # Descartar triángulos degenerados (área nula en coordenadas de hilo).
    keep = area > 1e-9
    tri, gi, gj, area = tri[keep], gi[keep], gj[keep], area[keep]
    tri_a, tri_d, tri_ea, tri_w = tri_a[keep], tri_d[keep], tri_ea[keep], tri_w[keep]
    tri_keys = tuple(k for k, kp in zip(tri_panel, keep.tolist(), strict=True) if kp)
    tri_sections = tuple(k for k, kp in zip(tri_sect, keep.tolist(), strict=True) if kp)
    tri_orients = tuple(k for k, kp in zip(tri_orient, keep.tolist(), strict=True) if kp)
    solid = float(np.sum(2.0 * area * tri_a * tri_d))

    # --- relingas ---------------------------------------------------------------------------
    def rope_path(topo: _PlaneTopo) -> tuple[IntArray, IntArray]:
        right_part = np.concatenate(topo.mouth_r)
        left_part = np.concatenate(topo.mouth_l)
        path_raw = np.concatenate([right_part, topo.bosom, left_part[::-1]])
        p = m(path_raw)
        keep_p = np.concatenate([[True], p[1:] != p[:-1]])
        p = p[keep_p]
        # 0 = ala, 1 = bocana para cada tramo
        n_wing = int(np.unique(m(right_part)).size)
        seg_kind = np.zeros(p.size - 1, dtype=np.int64)
        seg_kind[n_wing - 1 : p.size - n_wing] = 1
        return p, seg_kind

    head, head_kind = rope_path(up)
    foot, foot_kind = rope_path(lo)

    bars: list[tuple[int, int]] = []
    l0: list[float] = []
    ea: list[float] = []
    bd: list[float] = []
    bw: list[float] = []
    kinds: list[str] = []
    for path_, kind_, wing_m, bosom_m, dmm, wkgf, name in (
        (
            head,
            head_kind,
            rigging.headrope_wing_m,
            rigging.headrope_bosom_m,
            rigging.headrope_diameter_mm,
            rigging.headrope_water_kgf_m,
            "headrope",
        ),
        (
            foot,
            foot_kind,
            rigging.footrope_wing_m,
            rigging.footrope_bosom_m,
            rigging.footrope_diameter_mm,
            rigging.footrope_water_kgf_m,
            "footrope",
        ),
    ):
        seg = np.linalg.norm(xy[path_[1:]] - xy[path_[:-1]], axis=1)
        for k_kind, target in ((0, 2.0 * wing_m), (1, bosom_m)):
            sel = kind_ == k_kind
            total = float(seg[sel].sum())
            seg[sel] = seg[sel] * (target / total if total > 0 else 1.0)
        for k in range(path_.size - 1):
            bars.append((int(path_[k]), int(path_[k + 1])))
            l0.append(float(seg[k]))
            ea.append(rigging.rope_ea(name) if rope_ea_n is None else rope_ea_n)
            bd.append(dmm / 1000.0)
            bw.append(wkgf * GRAVITY)
            kinds.append(name)

    # --- bridas, patentes, portones ---------------------------------------------------------
    tips_u = (int(m(up.tip_r)), int(m(up.tip_l)))
    tips_l = (int(m(lo.tip_r)), int(m(lo.tip_l)))
    x_list = [*x0.tolist()]
    junctions: list[int] = []
    doors: list[int] = []
    # Sin patentes (pareja: las malletas van al destorcedor) queda un tramo corto de unión, para
    # que la barra no tenga largo nulo.
    sweeps = max(rigging.sweeps_m, MIN_SWEEP_M)
    rig_len = rigging.upper_bridle_m + sweeps
    beam = rigging.beam_height_m is not None
    if beam:
        # Vara: las puntas de la lima van a los extremos de la vara y las del burlón a los patines,
        # a la altura del cuello de la boca (x medio de las cuatro puntas).
        x_tip = float(np.mean(x0[[*tips_u, *tips_l], 0]))
        for k, sgn in ((0, 1.0), (1, -1.0)):
            y = sgn * rigging.door_spread_m / 2.0
            x0[tips_u[k]] = [x_tip, y, float(rigging.beam_height_m or 0.0)]
            x0[tips_l[k]] = [x_tip, y, 0.0]
        x_list = [*x0.tolist()]
    for k, sgn in ((0, 1.0), (1, -1.0)):
        tip = 0.5 * (x0[tips_u[k]] + x0[tips_l[k]])
        door = np.array([0.0, sgn * rigging.door_spread_m / 2.0, rigging.door_height_m / 2.0])
        dy = door[1] - tip[1]
        dx = 0.0 if beam else math.sqrt(max(rig_len**2 - dy**2, 1.0))
        door[0] = tip[0] - dx
        frac = sweeps / rig_len
        junc = door + frac * (tip - door)
        junc[2] = 0.3
        junctions.append(len(x_list))
        x_list.append(junc.tolist())
        doors.append(len(x_list))
        x_list.append(door.tolist())
        if up.collapsed or lo.collapsed:
            bars.append((tips_u[k], tips_l[k]))
            l0.append(up.wing_end_m + lo.wing_end_m)
            ea.append(up.wing_end_ea)
            bd.append(0.0)
            bw.append(0.0)
            kinds.append("wing_end")
        if beam:
            continue  # sin bridas ni patentes: las puntas de ala están en la vara
        for a_, b_, ln, kind in (
            (tips_u[k], junctions[-1], rigging.upper_bridle_m, "upper_bridle"),
            (tips_l[k], junctions[-1], rigging.lower_bridle_m, "lower_bridle"),
            (junctions[-1], doors[-1], sweeps, "sweep"),
        ):
            # Cables de acero: peso sumergido (mitad a cada extremo), sin carga hidrodinámica
            # (su arrastre no es de la red).
            bars.append((a_, b_))
            l0.append(ln)
            ea.append(rigging.wire_ea() if wire_ea_n is None else wire_ea_n)
            bd.append(0.0)
            bw.append(rigging.wire_water_kgf_m * GRAVITY)
            kinds.append(kind)
    vessel_pts: list[int] = []
    warp_nodes: list[IntArray] = []
    if coupled_doors:
        # Cable de remolque: del portón al buque (pasteca), en línea recta como forma inicial.
        # EA de cable de acero 6x19: módulo efectivo 46,9 GPa (alma de fibra) o 51,4 GPa (IWRC)
        # sobre el área nominal π·d²/4 (OrcaFlex/HER; 103–113 GPa sobre el área metálica).
        warp_ea = rigging.warp_ea()
        for k, sgn in ((0, 1.0), (1, -1.0)):
            door = np.asarray(x_list[doors[k]], dtype=float)
            dz = rigging.depth_m - door[2]
            dy = sgn * rigging.gallows_m / 2.0 - door[1]
            dx = math.sqrt(max(rigging.warp_length_m**2 - dz**2 - dy**2, 1.0))
            vessel = door + np.array([-dx, dy, dz])
            wchain = [doors[k]]
            for j in range(1, warp_segments + 1):
                wchain.append(len(x_list))
                x_list.append((door + (vessel - door) * j / warp_segments).tolist())
            vessel_pts.append(wchain[-1])
            warp_nodes.append(np.asarray(wchain, dtype=np.int64))
            seg_l = rigging.warp_length_m / warp_segments
            for a_, b_ in zip(wchain[:-1], wchain[1:], strict=True):
                bars.append((a_, b_))
                l0.append(seg_l)
                ea.append(warp_ea)
                bd.append(rigging.warp_diameter_mm / 1000.0)
                bw.append(rigging.wire_water_kgf_m * GRAVITY)
                kinds.append("warp")
    x_all = np.asarray(x_list, dtype=float)
    # Trasladar para que los portones queden en x = 0.
    x_all[:, 0] -= x_all[doors[0], 0]
    n_all = x_all.shape[0]

    # Anillos del copo: filas de los paneles centrales de dorso y vientre, apareadas desde el
    # extremo cerrado (donde las franjas de ambos planos coinciden).
    def central_rows(plane: str) -> list[IntArray]:
        rows: list[IntArray] = []
        for grid in grids:
            if grid.plane != plane or grid.side != "center":
                continue
            r_nodes = [m(r) for r in grid.nodes]
            if rows and np.array_equal(rows[-1], r_nodes[0]):
                r_nodes = r_nodes[1:]
            rows.extend(r_nodes)
        return rows[::-1]

    rings = tuple(
        np.concatenate([ru, rl[::-1]])
        for ru, rl in zip(central_rows("upper"), central_rows("lower"), strict=False)
    )

    # --- cargas puntuales: lastre y boyas ---------------------------------------------------
    point = np.zeros((n_all, 3))
    steel = 1.0 - 1024.0 / 7850.0
    for tip_node in tips_l:
        point[tip_node, 2] -= 0.5 * rigging.ballast_tips_kg * steel * GRAVITY
    _distribute_on_rope(
        point, foot, foot_kind, x_all, 0, -rigging.ballast_wings_kg * steel * GRAVITY
    )
    _distribute_on_rope(
        point, foot, foot_kind, x_all, 1, -rigging.ballast_bosom_kg * steel * GRAVITY
    )
    float_nodes, float_w = _place_floats(head, x0, rigging.float_positions_m, l0[: head.size - 1])

    mirror = _mirror_index(x_all)
    return NetModel(
        x0=x_all,
        tri=tri,
        tri_gi=gi,
        tri_gj=gj,
        tri_area=area,
        tri_a=tri_a,
        tri_d=tri_d,
        tri_ea=tri_ea,
        tri_w=tri_w,
        tri_panel=tri_keys,
        tri_section=tri_sections,
        tri_orientation=tri_orients,
        tri_rest_angle=np.array([rest_angle_rad(o) for o in tri_orients]),
        bar=np.asarray(bars, dtype=np.int64),
        bar_l0=np.asarray(l0),
        bar_ea=np.asarray(ea),
        bar_d=np.asarray(bd),
        bar_w=np.asarray(bw),
        bar_kind=tuple(kinds),
        point_load=point,
        float_nodes=float_nodes,
        float_weights=float_w,
        float_buoyancy_n=rigging.float_buoyancy_kgf * GRAVITY,
        float_area_m2=math.pi * (rigging.float_diameter_mm / 1000.0) ** 2 / 4.0,
        fixed=np.asarray(
            vessel_pts
            if coupled_doors
            else ([*tips_u, *tips_l, *junctions, *doors] if beam else doors),
            dtype=np.int64,
        ),
        headrope=head,
        footrope=foot,
        headrope_centre=int(head[head.size // 2]),
        footrope_centre=int(foot[foot.size // 2]),
        wing_tips_upper=tips_u,
        wing_tips_lower=tips_l,
        junctions=(junctions[0], junctions[1]),
        doors=(doors[0], doors[1]),
        grids=tuple(
            PanelGrid(g.key, g.panel_id, g.plane, g.side, m(g.nodes), g.s_cols, g.r_rows)
            for g in grids
        ),
        mirror=mirror,
        solid_surface_m2=solid,
        codend_rings=rings,
        coupled_doors=coupled_doors,
        warp_nodes=(warp_nodes[0], warp_nodes[1])
        if coupled_doors
        else (np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)),
        door_area_m2=rigging.door_area_m2,
        door_cl=rigging.door_cl,
        door_cd=rigging.door_cd,
        door_weight_n=rigging.door_weight_water_kgf * GRAVITY,
        door_floor_m=rigging.door_height_m / 2.0,
        warp_length_m=rigging.warp_length_m if coupled_doors else 0.0,
        door_polar=np.asarray(rigging.door_polar, dtype=float).reshape(-1, 3),
        door_angle_deg=float(rigging.door_attack_angle_deg),
        floor_free=spec.family == "pelagic",
        fixed_tips=beam,
    )


def _half_width_profile(layout: NetLayout, x: FloatArray) -> FloatArray:
    """Semiancho del dorso (paneles centrales y alas) en función de la distancia a la boca."""
    ys = np.linspace(layout.bbox[1], layout.bbox[3], 200)
    w = np.array(
        [max(abs(v) for v in (layout.x_extent_at("upper", float(y)) or (0.0, 0.0))) for y in ys]
    )
    return np.asarray(np.interp(x, ys, w), dtype=float)


def _twine_operators(
    mc: Sequence[tuple[tuple[float, float], ...]],
    square: npt.NDArray[np.bool_] | None = None,
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Operadores ``∂x/∂i = Σ gi_k x_k``, ``∂x/∂j = Σ gj_k x_k`` y área en patas por triángulo.

    Rombo y T90: ``i = n + t``, ``j = n − t``; malla cuadrada (``square``): ``i = t``, ``j = n``.
    """
    tn = np.asarray(mc, dtype=float)  # (nt, 3, 2): (t, n)
    i = tn[:, :, 1] + tn[:, :, 0]
    j = tn[:, :, 1] - tn[:, :, 0]
    if square is not None and square.any():
        i[square] = tn[square, :, 0]
        j[square] = tn[square, :, 1]
    di1, di2 = i[:, 1] - i[:, 0], i[:, 2] - i[:, 0]
    dj1, dj2 = j[:, 1] - j[:, 0], j[:, 2] - j[:, 0]
    det = di1 * dj2 - di2 * dj1
    safe = np.where(np.abs(det) > 1e-12, det, 1.0)
    # x(i, j) = x0 + (x1 − x0)·α + (x2 − x0)·β con [di1 di2; dj1 dj2]·[α β]ᵀ = [i − i0, j − j0]ᵀ
    # ∂α/∂i = dj2/det, ∂β/∂i = −dj1/det, ∂α/∂j = −di2/det, ∂β/∂j = di1/det
    da_di, db_di = dj2 / safe, -dj1 / safe
    da_dj, db_dj = -di2 / safe, di1 / safe
    gi = np.stack([-(da_di + db_di), da_di, db_di], axis=1)
    gj = np.stack([-(da_dj + db_dj), da_dj, db_dj], axis=1)
    area = 0.5 * np.abs(det)
    area = np.where(np.abs(det) > 1e-12, area, 0.0)
    return gi, gj, area


def _distribute_on_rope(
    load: FloatArray, path: IntArray, kind: IntArray, x: FloatArray, which: int, total_n: float
) -> None:
    """Reparte una carga vertical ``total_n`` sobre los tramos ``kind == which`` de una relinga."""
    seg = np.linalg.norm(x[path[1:], :2] - x[path[:-1], :2], axis=1) * (kind == which)
    tot = float(seg.sum())
    if tot <= 0 or total_n == 0:
        return
    per = total_n * seg / tot
    np.add.at(load[:, 2], path[:-1], 0.5 * per)
    np.add.at(load[:, 2], path[1:], 0.5 * per)


def _place_floats(
    head: IntArray, x0: FloatArray, positions: Sequence[float], l0: Sequence[float]
) -> tuple[IntArray, FloatArray]:
    """Nodos de la lima y fracciones de boya; ``positions`` en m desde el centro (+ = derecha)."""
    s = np.concatenate([[0.0], np.cumsum(np.asarray(l0, dtype=float))])
    s_mid = 0.5 * s[-1]
    nodes = np.zeros(head.size)
    for p in positions:
        target = float(np.clip(s_mid - p, 0.0, s[-1]))
        k = int(np.clip(np.searchsorted(s, target) - 1, 0, head.size - 2))
        f = (target - s[k]) / max(s[k + 1] - s[k], 1e-12)
        nodes[k] += 1.0 - f
        nodes[k + 1] += f
    sel = nodes > 0
    return head[sel], nodes[sel]


def _mirror_index(x: FloatArray) -> IntArray:
    """Índice del nodo espejo (y → −y): vecino más cercano en la geometría inicial."""
    mirrored = x * np.array([1.0, -1.0, 1.0])
    out = np.empty(x.shape[0], dtype=np.int64)
    for k in range(x.shape[0]):
        out[k] = int(np.argmin(np.sum((x - mirrored[k]) ** 2, axis=1)))
    return out


def interpolate_shape(coarse: NetModel, x_coarse: FloatArray, fine: NetModel) -> FloatArray:
    """Posiciones de ``fine`` interpoladas (bilineal por panel) de una solución de ``coarse``.

    Sirve de punto de partida para la relajación a la resolución fina (multinivel).
    """
    x = fine.x0.copy()
    by_key = {g.key: g for g in coarse.grids}
    for g in fine.grids:
        gc = by_key[g.key]
        xc = x_coarse[gc.nodes]  # (Rc+1, Cc+1, 3)
        ri = np.clip(np.searchsorted(gc.r_rows, g.r_rows, side="right") - 1, 0, gc.r_rows.size - 2)
        ci = np.clip(np.searchsorted(gc.s_cols, g.s_cols, side="right") - 1, 0, gc.s_cols.size - 2)
        fr = (g.r_rows - gc.r_rows[ri]) / (gc.r_rows[ri + 1] - gc.r_rows[ri])
        fc = (g.s_cols - gc.s_cols[ci]) / np.maximum(gc.s_cols[ci + 1] - gc.s_cols[ci], 1e-12)
        r0, c0 = ri[:, None], ci[None, :]
        a, b = fr[:, None, None], fc[None, :, None]
        val = (
            (1 - a) * (1 - b) * xc[r0, c0]
            + (1 - a) * b * xc[r0, c0 + 1]
            + a * (1 - b) * xc[r0 + 1, c0]
            + a * b * xc[r0 + 1, c0 + 1]
        )
        x[g.nodes] = val
    for kc, kf in zip(
        (*coarse.junctions, *coarse.doors), (*fine.junctions, *fine.doors), strict=True
    ):
        x[kf] = x_coarse[kc]
    return x
