"""Estructura de una red: detección de la topología FAO A-3 y red equivalente de 2 paneles.

El motor empírico nació para la FAO A-3 (libro Excel): dos caras, puntas de ala y alas en las dos,
cielo en el dorso, una segunda sección de ala de a pares en el vientre (``belly``) y cuerpo. Las
redes del catálogo FAO (Fase 12) tienen otras estructuras: cielo sólo en el dorso con el vientre
central, redes de pareja, redes de 4 paneles (dorso, vientre y dos costados).

* :func:`is_a3_topology` decide si la red tiene la estructura de la A-3; en ese caso el motor
  sigue la ruta del Excel, sin cambios.
* :func:`equivalent_two_panel` convierte una red de 4 paneles en una de 2: en cada estación (de
  la boca al copo, en orden), las mallas de cada costado se reparten mitad al dorso y mitad al
  vientre. Conserva la circunferencia, la superficie de paño y el largo, que es lo que usan el
  motor y el simulador; pierde las dos costuras extra de los costados.
* Si los costados no coinciden estación por estación con el dorso (planos de DynamiT en los que
  un costado de un solo mallero acompaña a paños de dos malleros, o que no llega al copo; Fase
  19.5), :func:`equivalent_two_panel` los reparte **por largo estirado**: el costado termina
  donde empieza el copo y cada paño central recibe, en su borde de boca y de bolsa, el ancho
  estirado del costado en esa posición expresado en mallas de su mallero (aproximación: conserva
  la circunferencia estirada, no la superficie exacta del costado).
"""

from __future__ import annotations

from trawlkit.io.schema import NetSpec, Panel, Plane, Section
from trawlkit.net import panel_planes


def _in(p: Panel, plane: Plane) -> bool:
    return plane in panel_planes(p)


def _paired(p: Panel) -> bool:
    """Paño de a pares (izquierda y derecha) en su plano."""
    return p.count // max(len(panel_planes(p)), 1) == 2


def is_a3_topology(spec: NetSpec) -> bool:
    """Si la red tiene la estructura de la FAO A-3 (ruta del libro Excel)."""
    ps = spec.panels
    has = {
        (Section.WING_TIP, Plane.UPPER),
        (Section.WING_TIP, Plane.LOWER),
        (Section.WING, Plane.UPPER),
        (Section.WING, Plane.LOWER),
        (Section.BODY, Plane.UPPER),
        (Section.BODY, Plane.LOWER),
        (Section.CODEND, Plane.UPPER),
    }
    for sec, plane in has:
        if not any(p.section is sec and _in(p, plane) for p in ps):
            return False
    if not any(p.section is Section.SQUARE for p in ps):
        return False
    belly = [p for p in ps if p.section is Section.BELLY and _in(p, Plane.LOWER)]
    if not belly or not all(_paired(p) for p in belly):
        return False
    return not any(Plane.SIDE in panel_planes(p) for p in ps)


def has_sides(spec: NetSpec) -> bool:
    """Si la red es de 4 paneles (con costados)."""
    return any(Plane.SIDE in panel_planes(p) for p in spec.panels)


def _stations(panels: list[Panel], plane: Plane) -> list[Panel]:
    """Paños centrales de un plano (o los costados), de la boca al copo."""
    from trawlkit.drawing.layout import SECTION_ORDER

    if plane is Plane.SIDE:
        chain = [p for p in panels if Plane.SIDE in panel_planes(p)]
    else:
        chain = [p for p in panels if _in(p, plane) and not _paired(p)]
    order = sorted(enumerate(chain), key=lambda it: (SECTION_ORDER[it[1].section], it[0]))
    return [p for _, p in order]


def equivalent_two_panel(spec: NetSpec) -> NetSpec:
    """Red de 2 paneles equivalente a una de 4 (ver el docstring del módulo).

    Los costados se emparejan por estaciones contadas desde el copo con los paños centrales del
    dorso y del vientre (el k-ésimo costado desde el copo con el k-ésimo paño central de cada
    cara): en el plano de una red de 4 paneles los cuatro paños de cada estación tienen el mismo
    alto y el mismo mallero. Cada plano recibe un costado entero (la mitad de cada uno de los dos)
    en sus bordes de boca y de bolsa. Si no hay costados devuelve la misma spec; ``ValueError``
    si un costado no tiene estación en el dorso o en el vientre, o no coincide en alto o mallero.
    """
    if not has_sides(spec):
        return spec
    panels = list(spec.panels)
    sides = _stations(panels, Plane.SIDE)
    extra: dict[str, tuple[int, int, list[str]]] = {}
    by_length = False
    for plane in (Plane.UPPER, Plane.LOWER):
        chain = _stations(panels, plane)
        if side_stations_match(sides, chain):
            for side, p in zip(reversed(sides), reversed(chain), strict=False):
                top, bottom, ids = extra.get(p.id, (0, 0, []))
                # Un paño que cubre las dos caras recibe un costado por cara.
                extra[p.id] = (
                    top + side.meshes_top,
                    bottom + side.meshes_bottom,
                    [*ids, side.id],
                )
            continue
        by_length = True
        for pid, (top, bottom, ids) in _sides_by_length(sides, chain, plane).items():
            t0, b0, ids0 = extra.get(pid, (0, 0, []))
            extra[pid] = (t0 + top, b0 + bottom, [*ids0, *ids])
    out: list[Panel] = []
    for p in panels:
        if Plane.SIDE in panel_planes(p):
            continue
        if p.id in extra:
            top, bottom, ids = extra[p.id]
            p = p.model_copy(
                update={
                    "meshes_top": p.meshes_top + top,
                    "meshes_bottom": p.meshes_bottom + bottom,
                    "name": f"{p.name or p.id} + costado {', '.join(sorted(set(ids)))}",
                }
            )
        out.append(p)
    notes = [
        *spec.notes,
        "Red de 4 paneles calculada como su equivalente de 2 paneles: las mallas de los costados "
        "se suman al dorso y al vientre de cada estación (misma circunferencia, superficie y "
        "largo; sin las costuras de los costados).",
    ]
    if by_length:
        notes.append(
            "Los costados no coinciden estación por estación con el dorso y el vientre: se "
            "reparten por largo estirado (el costado termina donde empieza el copo; su ancho "
            "estirado pasa a mallas del paño central de cada tramo)."
        )
    return spec.model_copy(update={"panels": out, "notes": notes})


#: Diferencia admitida entre el largo estirado de los costados y el del cuerpo (sin copo) para
#: repartirlos por largo (los costados pueden empezar junto a las alas).
SIDE_LENGTH_TOL = 0.25


def side_stations_match(sides: list[Panel], chain: list[Panel]) -> bool:
    """Si los costados se cosen estación por estación (mismo alto y mallero desde el copo)."""
    if len(sides) > len(chain):
        return False
    return all(
        s.meshes_depth == p.meshes_depth and abs(s.mesh_mm - p.mesh_mm) <= 1e-9
        for s, p in zip(reversed(sides), reversed(chain), strict=False)
    )


def _sides_by_length(
    sides: list[Panel], chain: list[Panel], plane: Plane
) -> dict[str, tuple[int, int, list[str]]]:
    """Mallas de costado para cada paño central del cuerpo, por largo estirado (ver el módulo).

    ``ValueError`` si el largo de los costados difiere del cuerpo (sin copo) en más de
    :data:`SIDE_LENGTH_TOL`.
    """
    body = [p for p in chain if p.section is not Section.CODEND]
    l_body = sum(p.meshes_depth * p.mesh_mm for p in body)
    l_side = sum(s.meshes_depth * s.mesh_mm for s in sides)
    if not body or not l_side or abs(l_body - l_side) > SIDE_LENGTH_TOL * l_side:
        raise ValueError(
            f"los costados ({l_side / 1000:.2f} m estirados) no se pueden repartir sobre el "
            f"cuerpo de {plane.value} ({l_body / 1000:.2f} m): no se puede armar la red "
            "equivalente"
        )
    start = l_body - l_side  # posición del comienzo de los costados desde la boca [mm]
    spans: list[tuple[float, float, Panel]] = []
    x = start
    for s in sides:
        length = s.meshes_depth * s.mesh_mm
        spans.append((x, x + length, s))
        x += length

    def width_mm(pos: float) -> tuple[float, str | None]:
        for a, b, s in spans:
            if a - 1e-6 <= pos <= b + 1e-6:
                f = 0.0 if b <= a else min(max((pos - a) / (b - a), 0.0), 1.0)
                meshes = s.meshes_top + f * (s.meshes_bottom - s.meshes_top)
                return meshes * s.mesh_mm, s.id
        return 0.0, None

    out: dict[str, tuple[int, int, list[str]]] = {}
    pos = 0.0
    for p in body:
        end = pos + p.meshes_depth * p.mesh_mm
        w_top, id_top = width_mm(pos)
        w_bot, id_bot = width_mm(end)
        ids = sorted({i for i in (id_top, id_bot) if i is not None})
        if ids:
            out[p.id] = (
                int(round(w_top / p.mesh_mm)),
                int(round(w_bot / p.mesh_mm)),
                ids,
            )
        pos = end
    return out
