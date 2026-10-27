"""Guía de construcción: del diseño calculado al taller de redes (Fase 15).

A partir de un :class:`~trawlkit.model.DesignResult` arma lo que necesita el redero:

* **Hoja de corte** (:func:`cutting_sheet`): por paño, cantidad de piezas, mallero, hilo, mallas
  en la boca, en la bolsa y en alto, el corte de cada costado con su ciclo explicado («1N2B: 1
  punta y 2 malletas, repetir 18 veces»), el rectángulo de paño del que sale y su desperdicio.
  :func:`netting_to_buy` suma esos rectángulos por paño (material, mallero e hilo).
* **Armado** (:func:`assembly`): la secuencia de uniones, borde con borde, con la cantidad de
  mallas de cada lado y la regla de toma cuando difieren («tomar 2 mallas juntas de H cada 2
  mallas»). Sale de las mismas reglas que el plano (:func:`trawlkit.drawing.layout.layout_net`) y
  el validador (:func:`trawlkit.netcheck.check`): paños centrales de la boca a la bolsa, alas de
  la punta al cuerpo, alas sobre el primer paño central (lo que sobra es la bocana) y costuras
  laterales (o costados de las redes de 4 paneles, estación por estación desde el copo).
* **Montaje en relingas** (:func:`hanging`): por tramo de lima y burlón, el largo de cabo, las
  mallas que se arman, el coeficiente de armado ``E = cabo / paño estirado`` y las mallas por
  metro, con una pauta práctica («≈ 6 mallas cada 50 cm»).
* **Aparejo** (:func:`rigging_layout`): posición sugerida de cada boya sobre la lima, zonas de
  lastre del burlón con kg y kg/m, y la lista de cortes de cabos, cables y cadenas con un
  sobrante por gaza (:data:`EYE_ALLOWANCE_M`, ajustable).

Las reglas prácticas (sobrante por gaza, reparto de las boyas, borde por el que se empieza a
cortar) son supuestos de taller y se dicen en :attr:`ConstructionGuide.notes`.
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from typing import TYPE_CHECKING, Any, Literal

from trawlkit.i18n import N_, dec, t
from trawlkit.io.schema import NetSpec, Panel
from trawlkit.net import panel_edges, panel_planes, panel_weight_air_kg

if TYPE_CHECKING:
    from trawlkit.dimensions import NetDimensions
    from trawlkit.model import DesignResult
    from trawlkit.net import NetGeometry
    from trawlkit.report.tables import Table

Variant = Literal["std", "mod"]

#: Sobrante de cabo o cable por gaza o empalme [m] (A VERIFICAR: regla de taller; depende del
#: diámetro y del tipo de empalme).
EYE_ALLOWANCE_M = 0.5

#: Tramo de la pauta de armado sobre la relinga [m].
SCHEDULE_STEP_M = 0.5

#: Nombre de cada plano y de cada sección en los textos de taller (se traducen con ``t``).
PLANE_NAMES: dict[str, str] = {"upper": N_("dorso"), "lower": N_("vientre"), "side": N_("costado")}
SECTION_NAMES: dict[str, str] = {
    "wing_tip": N_("punta de ala"),
    "wing": N_("ala"),
    "square": "square",
    "belly": N_("vientre (2ª sección de ala)"),
    "body": N_("cuerpo"),
    "extension": N_("extensión"),
    "codend": N_("bolsa"),
}

_TOKEN = re.compile(r"(\d*)([NTB])")


# ---------------------------------------------------------------------------------------------
# Ciclos de corte
# ---------------------------------------------------------------------------------------------


def cut_cycle(code: str) -> tuple[int, int, int]:
    """Puntas, transversales y malletas ``(N, T, B)`` de un ciclo de corte FAO.

    ``AB`` es un ciclo de una malleta, ``AN`` de una punta y ``AT`` de una transversal.
    ``ValueError`` si el código no se entiende.
    """
    c = code.strip().upper().replace(" ", "")
    if c in ("AB", "AN", "AT"):
        return (int(c == "AN"), int(c == "AT"), int(c == "AB"))
    counts = {"N": 0, "T": 0, "B": 0}
    pos = 0
    for m in _TOKEN.finditer(c):
        if m.start() != pos:
            break
        counts[m.group(2)] += int(m.group(1) or 1)
        pos = m.end()
    if pos != len(c) or pos == 0:
        raise ValueError(t("código de corte no reconocido: {code!r}", code=code))
    return counts["N"], counts["T"], counts["B"]


def _plural(n: int, one: str, many: str) -> str:
    """``one`` o ``many`` (textos con ``{n}``, ya marcados con ``N_``) en el idioma activo."""
    return t(one if n == 1 else many, n=n)


def cut_ratio_of(code: str) -> float:
    """Mallas de ancho que gana o pierde el costado por malla de alto (``AB`` = 1, ``AN`` = 0)."""
    n, tv, b = cut_cycle(code)
    deep = n + b / 2.0
    if deep == 0:
        return math.inf
    return (tv + b / 2.0) / deep


def nearest_cut_code(ratio: float) -> str:
    """Código de corte para una razón (mallas de ancho por malla de alto) del costado."""
    from trawlkit.netting import cut_code

    if ratio < 0.025:
        return "AN"
    if abs(ratio - 1.0) < 0.02:
        return "AB"
    code = cut_code(ratio)
    return code or "AB"


@dataclass(frozen=True)
class CutSide:
    """Corte de un costado del paño."""

    side: str
    code: str
    cycles: int
    instruction: str
    inferred: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return asdict(self)


def describe_cut(code: str, depth: int) -> tuple[int, str]:
    """Ciclos y texto de taller de un corte a lo largo de ``depth`` mallas de alto."""
    n, tv, b = cut_cycle(code)
    deep = n + b / 2.0
    c = code.strip().upper()
    if c == "AN":
        points = _plural(depth, N_("{n} punta"), N_("{n} puntas"))
        return depth, t("recto, todo puntas (AN): {points}", points=points)
    if c == "AT":
        return depth, t("todo transversales (AT)")
    if c == "AB":
        bars = 2 * depth
        return bars, t("todo malletas (AB): {bars} malletas seguidas", bars=bars)
    cycles = max(1, round(depth / deep)) if deep > 0 else depth
    parts = []
    if n:
        parts.append(_plural(n, N_("{n} punta"), N_("{n} puntas")))
    if tv:
        parts.append(_plural(tv, N_("{n} transversal"), N_("{n} transversales")))
    if b:
        parts.append(_plural(b, N_("{n} malleta"), N_("{n} malletas")))
    return cycles, t(
        "{code}: {parts} por ciclo; repetir {cycles} veces",
        code=c,
        parts=t(" y ").join(parts),
        cycles=cycles,
    )


# ---------------------------------------------------------------------------------------------
# Hoja de corte
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class CutPiece:
    """Un paño de la hoja de corte.

    ``stock_width`` × ``stock_depth`` es el rectángulo de paño del que sale una pieza o, si la
    pieza va de a pares (``paired``, las alas), el par encastrado. ``stock_weight_kg`` es el peso
    de ese rectángulo por pieza y ``waste`` la fracción que se pierde al cortar.
    """

    id: str
    name: str
    planes: str
    section: str
    pieces: int
    paired: bool
    material: str
    mesh_mm: float
    twine_mm: float
    rtex: float | None
    orientation: str
    meshes_mouth: int
    meshes_codend: int
    meshes_depth: int
    hanging_ratio: float | None
    sides: tuple[CutSide, ...]
    start: str
    stock_width: int
    stock_depth: int
    weight_kg: float
    stock_weight_kg: float
    waste: float
    stretched_width_m: float
    stretched_length_m: float

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        d = asdict(self)
        d["sides"] = [s.to_dict() for s in self.sides]
        return d


def _paired_ids(spec: NetSpec) -> set[str]:
    """Paños que van de a pares, izquierda y derecha (las cadenas de ala del plano)."""
    from trawlkit.drawing.layout import layout_net

    lay = layout_net(spec, mode="schematic")
    return {s.id for plane in lay.planes for s in lay.side_chain(plane, "right")}


def _planes_label(panel: Panel) -> str:
    return t(" y ").join(
        t(PLANE_NAMES.get(str(p.value), str(p.value))) for p in panel_planes(panel)
    )


def _cut_sides(panel: Panel, paired: bool) -> tuple[CutSide, ...]:
    depth = panel.meshes_depth
    taper = abs(panel.meshes_top - panel.meshes_bottom)
    code2 = (panel.model_extra or {}).get("cut_code_x2")
    code1 = panel.cut_code
    sides: list[tuple[str, str, bool]] = []
    if not paired:
        if code1:
            sides = [(t("ambos costados"), code1, False)]
        else:
            sides = [(t("ambos costados"), nearest_cut_code(taper / 2.0 / depth), True)]
    else:
        # Un costado de ala cambia r·N mallas de ancho; los dos juntos dan |T_boca − T_bolsa|,
        # sumando o restando (``netcheck``). Al costado que falta se le da lo que queda.
        def rest(code: str) -> float:
            try:
                return abs(taper - cut_ratio_of(code) * depth) / depth
            except ValueError:
                return 0.0

        if code1 and code2:
            c1, c2, inferred1, inferred2 = code1, str(code2), False, False
        elif code1:
            c1, inferred1 = code1, False
            c2, inferred2 = nearest_cut_code(rest(code1)), True
        elif code2:
            c2, inferred2 = str(code2), False
            c1, inferred1 = nearest_cut_code(rest(c2)), True
        else:
            c1, c2, inferred1, inferred2 = nearest_cut_code(taper / depth), "AN", True, True
        sides = [
            (t("costado de la relinga"), c2, inferred2),
            (t("costado interior"), c1, inferred1),
        ]
    out = []
    for side, code, inferred in sides:
        try:
            cycles, text = describe_cut(code, depth)
        except ValueError:
            cycles, text = 0, t("{code}: ciclo no reconocido, cortar según el plano", code=code)
        out.append(CutSide(side, code, cycles, text, inferred))
    return tuple(out)


def _reference_weights(geometry: NetGeometry) -> dict[str, float]:
    """Peso del paño de referencia de cada panel (``SN`` de su fila)."""
    out: dict[str, float] = {}
    for rg in geometry.rows:
        for pid in rg.row.panel_ids:
            out[pid] = rg.reference_twine_weight_kg
    return out


def cutting_sheet(spec: NetSpec, geometry: NetGeometry) -> tuple[CutPiece, ...]:
    """Hoja de corte de ``spec``: un :class:`CutPiece` por paño, en el orden de la spec."""
    paired = _paired_ids(spec)
    ref = _reference_weights(geometry)
    out: list[CutPiece] = []
    for p in spec.panels:
        t1, t2 = panel_edges(p)
        is_pair = p.id in paired
        # Las piezas de ala se cortan de a pares encastradas (una el reflejo de la otra): el par
        # sale de un rectángulo de (T_boca + T_bolsa) × N mallas; el resto, de max(T) × N.
        wide = p.meshes_top + p.meshes_bottom if is_pair else max(p.meshes_top, p.meshes_bottom)
        sn = ref.get(p.id)
        weight = float(panel_weight_air_kg(t1, t2, p.meshes_depth, sn)) if sn else 0.0
        stock = float(panel_weight_air_kg(wide, wide, p.meshes_depth, sn)) if sn else 0.0
        if is_pair:
            stock /= 2.0
        if p.meshes_top == p.meshes_bottom:
            start = t("lados rectos: cortar a la medida")
        elif p.meshes_top > p.meshes_bottom:
            start = t(
                "empezar por el borde de boca ({n} mallas) y bajar hacia la bolsa", n=p.meshes_top
            )
        else:
            start = t(
                "empezar por el borde de bolsa ({n} mallas) y subir hacia la boca",
                n=p.meshes_bottom,
            )
        m = p.mesh_mm / 1000.0
        out.append(
            CutPiece(
                id=p.id,
                name=p.name or p.id,
                planes=_planes_label(p),
                section=t(SECTION_NAMES.get(str(p.section.value), str(p.section.value))),
                pieces=p.count,
                paired=p.id in paired,
                material=p.material,
                mesh_mm=float(p.mesh_mm),
                twine_mm=float(p.twine_diameter_mm),
                rtex=None if p.rtex is None else float(p.rtex),
                orientation=str(p.mesh_orientation),
                meshes_mouth=p.meshes_top,
                meshes_codend=p.meshes_bottom,
                meshes_depth=p.meshes_depth,
                hanging_ratio=None if p.hanging_ratio is None else float(p.hanging_ratio),
                sides=_cut_sides(p, p.id in paired),
                start=start,
                stock_width=wide,
                stock_depth=p.meshes_depth,
                weight_kg=weight,
                stock_weight_kg=stock,
                waste=0.0 if stock <= 0 else 1.0 - weight / stock,
                stretched_width_m=wide * m,
                stretched_length_m=p.meshes_depth * m,
            )
        )
    return tuple(out)


@dataclass(frozen=True)
class NettingStock:
    """Paño a comprar de una misma calidad (material, mallero, hilo)."""

    material: str
    mesh_mm: float
    twine_mm: float
    rtex: float | None
    pieces: int
    width_meshes: int
    depth_meshes: int
    area_meshes: int
    weight_kg: float
    finished_kg: float

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return asdict(self)


def netting_to_buy(pieces: tuple[CutPiece, ...]) -> tuple[NettingStock, ...]:
    """Rectángulos de paño de la hoja de corte sumados por calidad.

    Se propone una tira del ancho del paño más ancho de esa calidad y el alto necesario para
    juntar el área de todos los rectángulos (``ceil(área / ancho)``).
    """
    groups: dict[tuple[str, float, float, float | None], list[CutPiece]] = {}
    for c in pieces:
        groups.setdefault((c.material, c.mesh_mm, c.twine_mm, c.rtex), []).append(c)
    out = []
    for (material, mesh, twine, rtex), items in groups.items():
        width = max(c.stock_width for c in items)
        area = sum(
            c.stock_width * c.stock_depth * c.pieces // (2 if c.paired else 1) for c in items
        )
        out.append(
            NettingStock(
                material=material,
                mesh_mm=mesh,
                twine_mm=twine,
                rtex=rtex,
                pieces=sum(c.pieces for c in items),
                width_meshes=width,
                depth_meshes=math.ceil(area / width) if width else 0,
                area_meshes=area,
                weight_kg=sum(c.stock_weight_kg * c.pieces for c in items),
                finished_kg=sum(c.weight_kg * c.pieces for c in items),
            )
        )
    return tuple(sorted(out, key=lambda s: (-s.mesh_mm, s.twine_mm)))


# ---------------------------------------------------------------------------------------------
# Armado
# ---------------------------------------------------------------------------------------------

JoinKind = Literal["seam", "wing_to_body", "side_seam", "side_panel"]


@dataclass(frozen=True)
class Join:
    """Una unión del armado: el borde de un paño con el de otro."""

    step: int
    plane: str
    kind: JoinKind
    a: str
    a_edge: str
    b: str
    b_edge: str
    meshes_a: int
    meshes_b: int
    times: int
    ratio: str
    rule: str
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return asdict(self)


def join_rule(a: str, na: int, b: str, nb: int) -> tuple[str, str]:
    """Relación ``a:b`` simplificada y regla de toma para unir ``na`` mallas con ``nb``."""
    if na <= 0 or nb <= 0:
        return "—", t("sin mallas para unir")
    frac = Fraction(na, nb).limit_denominator(8)
    ratio = f"{frac.numerator}:{frac.denominator}"
    if na == nb:
        return "1:1", t("malla a malla")
    big, n_big, n_small = (a, na, nb) if na > nb else (b, nb, na)
    extra = n_big - n_small
    if extra <= n_small:
        every = n_small / extra
        return ratio, t(
            "malla a malla, tomando 2 mallas juntas de {big} cada {every} mallas "
            "({extra} tomas en total)",
            big=big,
            every=dec(every),
            extra=extra,
        )
    per = n_big / n_small
    return ratio, t(
        "tomar {per} mallas de {big} por cada malla del otro paño", per=dec(per), big=big
    )


def _m(p: Panel) -> float:
    return p.mesh_mm / 1000.0


def wing_meshes_on_body(wing: Panel, body: Panel) -> int:
    """Mallas del borde de boca del primer paño central que ocupa el ala (mismo largo estirado)."""
    return round(wing.meshes_bottom * _m(wing) / _m(body))


def assembly(spec: NetSpec) -> tuple[Join, ...]:
    """Secuencia de uniones de ``spec`` (ver el docstring del módulo)."""
    from trawlkit.drawing.layout import layout_net

    lay = layout_net(spec, mode="schematic")
    joins: list[Join] = []

    def add(**kw: Any) -> None:
        ratio, rule = join_rule(kw["a"], kw["meshes_a"], kw["b"], kw["meshes_b"])
        joins.append(Join(step=len(joins) + 1, ratio=ratio, rule=rule, **kw))

    for plane in lay.planes:
        name = t(PLANE_NAMES.get(plane, plane))
        central = [s.panel for s in lay.central(plane)]
        wings = [s.panel for s in lay.side_chain(plane, "right")]
        for a, b in zip(central, central[1:], strict=False):
            add(
                plane=name,
                kind="seam",
                a=a.id,
                a_edge=t("borde de bolsa"),
                b=b.id,
                b_edge=t("borde de boca"),
                meshes_a=a.meshes_bottom,
                meshes_b=b.meshes_top,
                times=1,
            )
        for a, b in zip(wings, wings[1:], strict=False):
            add(
                plane=name,
                kind="seam",
                a=a.id,
                a_edge=t("borde de bolsa"),
                b=b.id,
                b_edge=t("borde de boca"),
                meshes_a=a.meshes_bottom,
                meshes_b=b.meshes_top,
                times=2,
                note=t("una vez en cada ala (izquierda y derecha)"),
            )
        if wings and central:
            wing, body = wings[-1], central[0]
            on_body = wing_meshes_on_body(wing, body)
            bosom = body.meshes_top - 2 * on_body
            add(
                plane=name,
                kind="wing_to_body",
                a=wing.id,
                a_edge=t("borde de bolsa"),
                b=body.id,
                b_edge=t("borde de boca, desde cada esquina"),
                meshes_a=wing.meshes_bottom,
                meshes_b=on_body,
                times=2,
                note=t(
                    "una ala en cada esquina de {body}; quedan libres {bosom} mallas en el "
                    "centro: la bocana, que se arma directamente en la relinga",
                    body=body.id,
                    bosom=bosom,
                ),
            )
    if "side" in lay.planes:
        side_panels = [sh.panel for sh in lay.central("side")][::-1]
        for face in ("upper", "lower"):
            if face not in lay.planes:
                continue
            face_panels = [sh.panel for sh in lay.central(face)][::-1]
            for sp, fp in zip(side_panels, face_panels, strict=False):
                add(
                    plane=t("costado"),
                    kind="side_panel",
                    a=sp.id,
                    a_edge=t("costado hacia el {face}", face=t(PLANE_NAMES[face])),
                    b=fp.id,
                    b_edge=t("costado"),
                    meshes_a=sp.meshes_depth,
                    meshes_b=fp.meshes_depth,
                    times=2,
                    note=t("a cada lado de la red, desde el copo hacia la boca"),
                )
    elif "upper" in lay.planes and "lower" in lay.planes:

        def edge(plane: str) -> tuple[int, float]:
            chain = [s.panel for s in lay.side_chain(plane, "right")] + [
                s.panel for s in lay.central(plane)
            ]
            return (
                sum(p.meshes_depth for p in chain),
                sum(p.meshes_depth * _m(p) for p in chain),
            )

        nu, lu = edge("upper")
        nl, ll = edge("lower")
        add(
            plane=t("dorso y vientre"),
            kind="side_seam",
            a=t("dorso"),
            a_edge=t("costado"),
            b=t("vientre"),
            b_edge=t("costado"),
            meshes_a=nu,
            meshes_b=nl,
            times=2,
            note=t(
                "costura lateral a cada lado, de la bolsa hacia la punta de ala: dorso "
                "{upper} m y vientre {lower} m estirados; se suele reforzar con "
                "un cabo de costado",
                upper=dec(lu, 2),
                lower=dec(ll, 2),
            ),
        )
    return tuple(joins)


# ---------------------------------------------------------------------------------------------
# Montaje en relingas
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class HangingSection:
    """Tramo de una relinga con el paño que se arma en él."""

    rope: str
    part: str
    panels: tuple[str, ...]
    times: int
    rope_m: float
    meshes: int
    netting_m: float
    hanging: float
    meshes_per_m: float
    schedule: str
    warning: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return asdict(self)


#: Coeficiente de armado por encima del cual el paño no alcanza a cubrir el cabo (en las alas el
#: libro arma a 1,05 sobre el costado cortado).
MAX_HANGING = 1.1


def _section(
    rope: str, part: str, panels: list[Panel], times: int, rope_m: float, meshes: int, mesh: float
) -> HangingSection:
    netting = meshes * mesh
    per_m = meshes / rope_m if rope_m > 0 else math.nan
    step = per_m * SCHEDULE_STEP_M
    e = rope_m / netting if netting > 0 else math.nan
    warning = (
        t(
            "el cabo es más largo que el paño estirado: el paño no se arma directo en él (va a "
            "una relinga de armado o línea de pesca, y el cabo se une con colgantes o cadenas); "
            "revisar el plano"
        )
        if e > MAX_HANGING
        else ""
    )
    return HangingSection(
        rope=rope,
        part=part,
        panels=tuple(p.id for p in panels),
        times=times,
        rope_m=rope_m,
        meshes=meshes,
        netting_m=netting,
        hanging=e,
        meshes_per_m=per_m,
        schedule=t("≈ {step} mallas cada {cm:.0f} cm", step=dec(step), cm=100 * SCHEDULE_STEP_M),
        warning=warning,
    )


def hanging(spec: NetSpec, dims: NetDimensions) -> tuple[HangingSection, ...]:
    """Tramos de lima (dorso) y burlón (vientre): alas y bocana.

    En las alas el paño se arma por su costado: las mallas son las del alto de la cadena de ala
    (la misma cuenta que la pieza de ala de la hoja, ``(N_punta + N_ala)·mallero``). En la bocana
    son las mallas libres del borde de boca del primer paño central. Las redes con costados se
    arman sobre su red equivalente de 2 paneles (:func:`trawlkit.topology.equivalent_two_panel`),
    como hace el motor con las relingas: la boca de cada cara incluye su parte de los costados.
    """
    from trawlkit.drawing.layout import layout_net
    from trawlkit.topology import equivalent_two_panel

    lay = layout_net(equivalent_two_panel(spec), mode="schematic")
    out: list[HangingSection] = []
    for plane, rope_name, pieces in (
        ("upper", t("lima"), dims.headrope),
        ("lower", t("burlón"), dims.footrope),
    ):
        if plane not in lay.planes:
            continue
        wings = [s.panel for s in lay.side_chain(plane, "right")]
        central = [s.panel for s in lay.central(plane)]
        if wings:
            meshes = sum(p.meshes_depth for p in wings)
            mesh = sum(p.meshes_depth * _m(p) for p in wings) / meshes
            out.append(
                _section(rope_name, t("ala"), wings, 2, pieces.wing_corrected_m, meshes, mesh)
            )
        if central:
            body = central[0]
            free = body.meshes_top - (2 * wing_meshes_on_body(wings[-1], body) if wings else 0)
            out.append(
                _section(
                    rope_name, t("bocana"), [body], 1, pieces.bosom_corrected_m, free, _m(body)
                )
            )
    return tuple(out)


# ---------------------------------------------------------------------------------------------
# Aparejo: boyas, lastre y cortes
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class FloatPosition:
    """Boya sobre la lima: distancia al centro (+ derecha, − izquierda) y zona."""

    number: int
    x_m: float
    zone: str

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return asdict(self)


def float_positions(
    count: int, per_wing: int, front: int, bosom_m: float, wing_m: float
) -> tuple[FloatPosition, ...]:
    """Posición sugerida de las boyas sobre la lima.

    Las de la bocana se reparten parejas en ella; en cada ala, ``front`` boyas en el primer
    quinto del ala (junto a la bocana, donde la lima necesita más empuje) y el resto parejas
    hasta la punta. Si la regla no cierra (``2·per_wing > count``) se reparten todas parejas.
    """
    on_bosom = count - 2 * per_wing
    if on_bosom < 0 or per_wing < 0:
        per_wing, on_bosom, front = 0, count, 0
    front = max(0, min(front, per_wing))
    half = bosom_m / 2.0
    xs: list[tuple[float, str]] = []
    bosom, first_fifth, wing = t("bocana"), t("ala, primer quinto"), t("ala")
    for k in range(on_bosom):
        xs.append((-half + (k + 0.5) * bosom_m / on_bosom, bosom))
    zone1 = wing_m / 5.0
    rest = per_wing - front
    for sign in (-1.0, 1.0):
        for k in range(front):
            xs.append((sign * (half + (k + 0.5) * zone1 / front), first_fifth))
        for k in range(rest):
            xs.append((sign * (half + zone1 + (k + 0.5) * (wing_m - zone1) / rest), wing))
    xs.sort()
    return tuple(FloatPosition(i + 1, round(x, 3), z) for i, (x, z) in enumerate(xs))


@dataclass(frozen=True)
class BallastZone:
    """Zona de lastre del burlón, para el lastre mínimo y el máximo."""

    zone: str
    where: str
    kg_min: float
    kg_max: float
    kg_m_min: float
    kg_m_max: float

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return asdict(self)


@dataclass(frozen=True)
class RopeCut:
    """Corte de un cabo, cable o cadena."""

    key: str
    label: str
    material: str
    pieces: int
    length_m: float
    eyes: int
    cut_m: float

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return asdict(self)


def rope_cuts(result: DesignResult, dims: NetDimensions, eye_m: float) -> tuple[RopeCut, ...]:
    """Lista de cortes: relingas, refuerzos, bridas, patentes, pies de gallo, cadenas, cables."""
    hr = result.floats.headrope_rope.description
    fr = result.ballast.footrope_rope.description
    b = result.bridles
    items = [
        ("headrope", t("Lima (relinga superior)"), hr, 1, dims.headrope_m, 2),
        ("footrope", t("Burlón (relinga inferior)"), fr, 1, dims.footrope_m, 2),
    ]
    if dims.wingtip_reinforcement_m > 0:
        items.append(
            (
                "wingtip",
                t("Refuerzo de punta de ala"),
                hr,
                4,
                dims.wingtip_reinforcement_m,
                2,
            )
        )
    # Sin bridas ni patentes en la pareja y en la vara (Fase 19.5: las puntas de ala van a la vara).
    if result.case.rig_kind not in ("pair", "beam"):
        items += [
            (
                "bridle_upper",
                t("Malleta superior (brida)"),
                t("cable de bridas"),
                2,
                b.lengths.upper_m,
                2,
            ),
            (
                "bridle_lower",
                t("Malleta inferior (brida)"),
                t("cable de bridas"),
                2,
                b.lengths.lower_m,
                2,
            ),
            ("sweeps", t("Patentes"), t("cable de patentes"), 2, b.sweeps_m, 2),
            ("crowfoot", t("Pie de gallo"), t("cadena o cable"), 4, b.crowfoot.length_m, 2),
            (
                "bridle_chain",
                t("Cadena de reglaje de bridas"),
                t("cadena"),
                2,
                b.lengths.adjust_chain_m,
                0,
            ),
        ]
    items += [
        (
            "ballast_chain",
            t("Cadena de reglaje del burlón"),
            t("cadena"),
            1,
            result.case.adjust_chain_m,
            0,
        ),
        (
            "warp",
            t("Cable de remolque (por banda)"),
            t("cable de remolque"),
            2,
            result.warps.warp_m,
            1,
        ),
    ]
    return tuple(
        RopeCut(key, label, mat, n, length, eyes, length + eyes * eye_m)
        for key, label, mat, n, length, eyes in items
        if length and length > 0
    )


# ---------------------------------------------------------------------------------------------
# Guía completa
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ConstructionGuide:
    """Guía de construcción de una variante de la red."""

    net_id: str
    net_name: str
    variant: str
    eye_allowance_m: float
    pieces: tuple[CutPiece, ...]
    stock: tuple[NettingStock, ...]
    joins: tuple[Join, ...]
    hanging: tuple[HangingSection, ...]
    floats: tuple[FloatPosition, ...]
    float_diameter_mm: float
    ballast: tuple[BallastZone, ...]
    ropes: tuple[RopeCut, ...]
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "net_id": self.net_id,
            "net_name": self.net_name,
            "variant": self.variant,
            "eye_allowance_m": self.eye_allowance_m,
            "pieces": [p.to_dict() for p in self.pieces],
            "stock": [s.to_dict() for s in self.stock],
            "joins": [j.to_dict() for j in self.joins],
            "hanging": [h.to_dict() for h in self.hanging],
            "floats": [f.to_dict() for f in self.floats],
            "float_diameter_mm": self.float_diameter_mm,
            "ballast": [b.to_dict() for b in self.ballast],
            "ropes": [r.to_dict() for r in self.ropes],
            "notes": list(self.notes),
        }

    def tables(self) -> list[Table]:
        """Tablas de la guía (hoja de corte, paño, armado, montaje, boyas, lastre, cortes)."""
        from trawlkit.report.construction import guide_tables

        return guide_tables(self)


def _ballast_zones(result: DesignResult) -> tuple[BallastZone, ...]:
    lo = result.ballast.distribution_min
    hi = result.ballast.distribution_max
    return (
        BallastZone(
            t("reglaje"),
            t("cadena en el centro del burlón"),
            lo.adjust_kg,
            hi.adjust_kg,
            lo.adjust_kg_m,
            hi.adjust_kg_m,
        ),
        BallastZone(
            t("bocana"),
            t("{w} m centrales del burlón", w=dec(2.5)),
            lo.bosom_kg,
            hi.bosom_kg,
            lo.bosom_kg_m,
            hi.bosom_kg_m,
        ),
        BallastZone(
            t("alas"),
            t("resto del burlón, parejo en las dos alas"),
            lo.wings_kg,
            hi.wings_kg,
            lo.wings_kg_m,
            hi.wings_kg_m,
        ),
    )


def guide(
    result: DesignResult, variant: Variant = "std", eye_allowance_m: float = EYE_ALLOWANCE_M
) -> ConstructionGuide:
    """Guía de construcción de la red estándar (``std``) o de la modificada (``mod``)."""
    if variant == "mod":
        if result.case.net_modified is None:
            raise ValueError(t("el caso no tiene red modificada"))
        spec, geometry, dims = (
            result.case.net_modified,
            result.geometry.mod,
            result.dimensions.mod,
        )
    else:
        spec, geometry, dims = result.case.net, result.geometry.std, result.dimensions.std
    if eye_allowance_m < 0:
        raise ValueError(t("el sobrante por gaza no puede ser negativo"))
    pieces = cutting_sheet(spec, geometry)
    fd = result.floats.distribution
    floats = float_positions(
        fd.count,
        fd.per_wing,
        fd.front_fifth,
        dims.headrope.bosom_corrected_m,
        dims.headrope.wing_corrected_m,
    )
    notes = [
        t("Mallas a malla estirada; los largos de cabo incluyen el armado (embando) del motor."),
        t(
            "Sobrante por gaza o empalme: {eye} m (A VERIFICAR según el cabo y el empalme).",
            eye=dec(eye_allowance_m, 2),
        ),
        t(
            "La posición de las boyas sigue la regla selectiva del libro (70 % en las alas, 60 % "
            "de ellas en el primer quinto); ajustar en la prueba de mar."
        ),
        t(
            "Los cortes marcados como inferidos no vienen del plano: salen del cambio de ancho "
            "del paño."
        ),
    ]
    if any(s.inferred for p in pieces for s in p.sides):
        notes.append(t("Hay cortes inferidos: verificarlos contra el plano antes de cortar."))
    sections = hanging(spec, dims)
    for h in sections:
        if h.warning:
            notes.append(f"{h.rope.capitalize()}, {h.part}: {h.warning}.")
    return ConstructionGuide(
        net_id=spec.id,
        net_name=spec.name,
        variant=variant,
        eye_allowance_m=eye_allowance_m,
        pieces=pieces,
        stock=netting_to_buy(pieces),
        joins=assembly(spec),
        hanging=sections,
        floats=floats,
        float_diameter_mm=fd.diameter_mm,
        ballast=_ballast_zones(result),
        ropes=rope_cuts(result, dims, eye_allowance_m),
        notes=tuple(notes),
    )


__all__ = [
    "EYE_ALLOWANCE_M",
    "BallastZone",
    "ConstructionGuide",
    "CutPiece",
    "CutSide",
    "FloatPosition",
    "HangingSection",
    "Join",
    "NettingStock",
    "RopeCut",
    "assembly",
    "cut_cycle",
    "cutting_sheet",
    "describe_cut",
    "float_positions",
    "guide",
    "hanging",
    "join_rule",
    "nearest_cut_code",
    "netting_to_buy",
    "rope_cuts",
    "wing_meshes_on_body",
]
