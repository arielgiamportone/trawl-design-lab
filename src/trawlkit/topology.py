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
    for plane in (Plane.UPPER, Plane.LOWER):
        chain = _stations(panels, plane)
        if len(sides) > len(chain):
            raise ValueError(
                f"hay {len(sides)} costados y sólo {len(chain)} paños centrales en "
                f"{plane.value}: no se puede armar la red equivalente"
            )
        for side, p in zip(reversed(sides), reversed(chain), strict=False):
            if side.meshes_depth != p.meshes_depth or abs(side.mesh_mm - p.mesh_mm) > 1e-9:
                raise ValueError(
                    f"el costado {side.id} ({side.meshes_depth} mallas de {side.mesh_mm:g} mm) "
                    f"no coincide con su estación {p.id} ({p.meshes_depth} mallas de "
                    f"{p.mesh_mm:g} mm)"
                )
            top, bottom, ids = extra.get(p.id, (0, 0, []))
            # Un paño que cubre las dos caras recibe un costado por cara.
            extra[p.id] = (top + side.meshes_top, bottom + side.meshes_bottom, [*ids, side.id])
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
    return spec.model_copy(update={"panels": out, "notes": notes})
