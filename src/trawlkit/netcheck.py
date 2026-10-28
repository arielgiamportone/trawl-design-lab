"""Validador de consistencia de una red (Fase 12).

Una red transcripta de un plano puede traer errores de lectura (un 6 por un 8, un borde
cambiado). Las reglas de construcción del paño permiten detectar muchos de ellos:

* **Empalmes** (``seam``): dos paños unidos borde con borde tienen el mismo largo estirado. Si
  cambia el mallero, cambia la cantidad de mallas: ``T_inf,1 · m₁ ≈ T_sup,2 · m₂``.
* **Boca** (``mouth``): las alas se apoyan sobre el primer paño del cuerpo y entre ellas queda la
  bocana. Su largo, ``T_sup · m − 2 T_ala · m_ala``, debe ser positivo.
* **Costuras laterales** (``side_seam``): el dorso y el vientre se cosen por los costados, así
  que cada franja debe tener un largo estirado parecido en las dos caras.
* **Cortes** (``cut``): el corte declarado del costado (``cut_code``, y ``cut_code_x2`` en las
  alas) debe dar el cambio de ancho del paño, ``|T_sup − T_inf|``, en sus ``N`` mallas de alto.
  Un paño central se corta igual en los dos costados (``2·r·N``); uno de ala tiene un costado
  con cada corte, en el mismo sentido o en sentidos opuestos (``(r₁ ± r₂)·N``); si el plano sólo
  da un corte, el otro costado puede ser recto, en malletas o igual.
* **Costados** (``side``): en una red de 4 paneles, cada estación del costado (contada desde el
  copo) se cose a la del dorso: mismo alto en mallas y mismo mallero. Es un error, porque el
  motor y el simulador no pueden armar la red equivalente de 2 paneles.
* **Unión al copo por la circunferencia** (``codend_join``, Fase 19.7c): en las tangoneras del
  INIDEP los costados terminan antes del copo, fruncidos en un cabo corto que cierra en las
  costuras (``aft_rope_m`` del costado: cabo N de 0,50 m en ITO 043/2022, fig. 5), y el copo de
  dos caras se une al dorso y al vientre alrededor de la boca. Entonces se compara la suma de los
  bordes de bolsa del dorso y del vientre con la de las bocas del copo (no cara por cara); si
  cierra, la diferencia por cara queda como aviso.
* **Datos** (``data``): campos que el motor necesita (U1, rendimiento del hilo).

Cada problema es un :class:`Issue` con nivel ``error`` (la red no cierra) o ``warning`` (hay que
revisar la lectura). Las tolerancias cubren los redondeos habituales de los planos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from trawlkit.i18n import N_, t
from trawlkit.io.schema import NetSpec, Panel

Level = Literal["error", "warning"]

#: Diferencia relativa de largo estirado en un empalme: aviso y error.
#: Los planos reales cosen paños con distinto armado (fruncido) hasta ≈ 18 % (BOBP/WP/10, Schärfe
#: 1983); por encima del 20 % es casi seguro un error de lectura (un 2 por un 3, 243 por 343).
SEAM_WARN = 0.04
SEAM_ERROR = 0.20
#: Diferencia relativa de largo entre las franjas del dorso y del vientre.
SIDE_WARN = 0.15
#: Diferencia admitida entre el cambio de ancho del paño y el que da su corte [mallas]: la mayor
#: entre esta cantidad y CUT_REL del cambio (los planos redondean al ciclo de corte).
CUT_ABS = 2.0
CUT_REL = 0.10


@dataclass(frozen=True)
class Issue:
    """Problema de consistencia de una red."""

    level: Level
    code: str
    message: str
    panels: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "level": self.level,
            "code": self.code,
            "message": self.message,
            "panels": list(self.panels),
        }


#: Nombre de cada plano en los mensajes.
_PLANE_LABEL = {"upper": N_("dorso"), "lower": N_("vientre"), "side": N_("costado")}


def _m(panel: Panel) -> float:
    return panel.mesh_mm / 1000.0


def _rel(a: float, b: float) -> float:
    return abs(a - b) / max(abs(a), abs(b), 1e-9)


def _seam(prev: Panel, nxt: Panel, where: str) -> Issue | None:
    a = prev.meshes_bottom * _m(prev)
    b = nxt.meshes_top * _m(nxt)
    d = _rel(a, b)
    if d <= SEAM_WARN:
        return None
    level: Level = "error" if d > SEAM_ERROR else "warning"
    return Issue(
        level,
        "seam",
        t(
            "{where}: el borde de bolsa de {prev} ({prev_n} × {prev_mm:g} mm = "
            "{a:.2f} m) no empalma con el borde de boca de {nxt} ({nxt_n} × "
            "{nxt_mm:g} mm = {b:.2f} m): {pct:.0f} % de diferencia",
            where=where,
            prev=prev.id,
            prev_n=prev.meshes_bottom,
            prev_mm=prev.mesh_mm,
            a=a,
            nxt=nxt.id,
            nxt_n=nxt.meshes_top,
            nxt_mm=nxt.mesh_mm,
            b=b,
            pct=100 * d,
        ),
        (prev.id, nxt.id),
    )


def _cut_issue(panel: Panel, paired: bool) -> Issue | None:
    """Corte declarado frente al cambio de ancho del paño (ver el docstring del módulo)."""
    from trawlkit.netting import cut_code_ratio

    code = panel.cut_code
    if not code:
        return None
    code2 = (panel.model_extra or {}).get("cut_code_x2")
    try:
        r1 = cut_code_ratio(code)
        r2 = None if code2 is None else cut_code_ratio(str(code2))
    except ValueError as exc:
        return Issue("warning", "cut", f"panel {panel.id}: {exc}", (panel.id,))
    n = panel.meshes_depth
    taper = abs(panel.meshes_top - panel.meshes_bottom)
    if not paired:
        expected = [2.0 * r1 * n] if r2 is None else [(r1 + r2) * n]
    else:
        others = [r2] if r2 is not None else [0.0, 1.0, r1]
        expected = [abs(r1 + sign * r) * n for r in others for sign in (1.0, -1.0)]
    best = min(expected, key=lambda e: abs(e - taper))
    if abs(best - taper) <= max(CUT_ABS, CUT_REL * taper):
        return None
    cut = code if code2 is None else f"{code} / {code2}"
    return Issue(
        "warning",
        "cut",
        t(
            "panel {id}: el corte {cut} en {n} mallas de alto da un cambio de ancho de "
            "{best:.0f} mallas, pero el paño pasa de {top} a {bottom} ({taper} mallas)",
            id=panel.id,
            cut=cut,
            n=n,
            best=best,
            top=panel.meshes_top,
            bottom=panel.meshes_bottom,
            taper=taper,
        ),
        (panel.id,),
    )


def _codend_join(lay: Any) -> tuple[float, float, tuple[str, ...], float] | None:
    """Unión al copo por la circunferencia (ver el docstring del módulo) o ``None``.

    Sólo con costados que terminan en un cabo antes del copo (``aft_rope_m``) y un copo en el
    dorso y en el vientre. Devuelve ``(bordes de bolsa, bocas del copo, paños, cabo)`` en metros.
    """
    if "side" not in lay.planes or "upper" not in lay.planes or "lower" not in lay.planes:
        return None
    sides = [s.panel for s in lay.central("side")]
    ropes = [(p.model_extra or {}).get("aft_rope_m") for p in sides]
    if not sides or any(r is None for r in ropes):
        return None
    body_m = codend_m = 0.0
    ids: list[str] = []
    for plane in ("upper", "lower"):
        central = [s.panel for s in lay.central(plane)]
        idx = next((i for i, p in enumerate(central) if p.section.value == "codend"), None)
        if idx is None or idx == 0:
            return None
        prev, cod = central[idx - 1], central[idx]
        body_m += prev.meshes_bottom * _m(prev)
        codend_m += cod.meshes_top * _m(cod)
        ids += [prev.id, cod.id]
    return body_m, codend_m, tuple(ids), float(ropes[-1] or 0.0)


def check(spec: NetSpec) -> list[Issue]:
    """Problemas de consistencia de ``spec`` (lista vacía si la red cierra)."""
    from trawlkit.drawing.layout import layout_net

    issues: list[Issue] = []
    for p in spec.panels:
        if p.hanging_ratio is None and str(p.mesh_orientation) != "square":
            issues.append(
                Issue("error", "data", t("panel {id}: falta U1 (hanging_ratio)", id=p.id), (p.id,))
            )
        if p.rtex is None and p.runnage_m_per_kg is None:
            issues.append(
                Issue(
                    "warning",
                    "data",
                    t(
                        "panel {id}: sin Rtex ni rendimiento; el peso del hilo se estima del "
                        "diámetro",
                        id=p.id,
                    ),
                    (p.id,),
                )
            )
    from trawlkit.net import panel_planes
    from trawlkit.provenance import provenance_of

    for p in spec.panels:
        prov = provenance_of(spec, f"panels.{p.id}.cut_code")
        if prov is not None and prov.kind == "excel":
            # Los cortes del libro Excel salen de sus propias fórmulas (la bolsa recta queda
            # «AB»), no de un plano: no se contrastan.
            continue
        paired = p.count // max(len(panel_planes(p)), 1) == 2 and "side" not in panel_planes(p)
        if (i := _cut_issue(p, paired)) is not None:
            issues.append(i)
    try:
        lay = layout_net(spec, mode="schematic")
    except (ValueError, KeyError) as exc:
        issues.append(Issue("error", "structure", t("no se puede disponer la red: {exc}", exc=exc)))
        return issues
    join = _codend_join(lay)
    join_ok = join is not None and _rel(join[0], join[1]) <= SEAM_WARN
    if join is not None and join_ok:
        issues.append(
            Issue(
                "warning",
                "codend_join",
                t(
                    "copo unido por la circunferencia: bordes de bolsa del dorso y del vientre "
                    "{a:.2f} m frente a {b:.2f} m de las bocas del copo ({pct:.0f} %); los "
                    "costados terminan antes del copo en un cabo de {rope:.2f} m y la "
                    "diferencia cara por cara se reparte en las costuras",
                    a=join[0],
                    b=join[1],
                    pct=100 * _rel(join[0], join[1]),
                    rope=join[3],
                ),
                join[2],
            )
        )
    for plane in lay.planes:
        central = [s.panel for s in lay.central(plane)]
        wings = [s.panel for s in lay.side_chain(plane, "right")]
        label = t(_PLANE_LABEL.get(plane, plane))
        for a, b in zip(central, central[1:], strict=False):
            if join_ok and b.section.value == "codend" and a.section.value != "codend":
                continue  # unión al copo por la circunferencia (codend_join)
            if (i := _seam(a, b, label)) is not None:
                issues.append(i)
        for a, b in zip(wings, wings[1:], strict=False):
            if (i := _seam(a, b, t("{plane}, ala", plane=label))) is not None:
                issues.append(i)
        if central and wings:
            first, wing = central[0], wings[-1]
            bosom = first.meshes_top * _m(first) - 2 * wing.meshes_bottom * _m(wing)
            if bosom <= 0:
                issues.append(
                    Issue(
                        "error",
                        "mouth",
                        t(
                            "{plane}: las alas ({wing}, {wing_n} mallas) son más "
                            "anchas que el borde de boca de {first} ({first_n} mallas): "
                            "no queda bocana",
                            plane=label,
                            wing=wing.id,
                            wing_n=wing.meshes_bottom,
                            first=first.id,
                            first_n=first.meshes_top,
                        ),
                        (first.id, wing.id),
                    )
                )
        if not central:
            issues.append(
                Issue("error", "structure", t("{plane}: no hay paños centrales", plane=label))
            )
    # Costados (redes de 4 paneles): estación por estación con el dorso, desde el copo. Si no
    # coinciden pero se pueden repartir por largo estirado (Fase 19.5) es un aviso.
    by_length = False
    if "side" in lay.planes and "upper" in lay.planes:
        sides = [s.panel for s in lay.central("side")]
        body = [s.panel for s in lay.central("upper")]
        from trawlkit.topology import equivalent_two_panel, side_stations_match

        if not side_stations_match(sides, body):
            try:
                equivalent_two_panel(spec)
                by_length = True
            except ValueError:
                by_length = False
        if by_length:
            issues.append(
                Issue(
                    "warning",
                    "side",
                    t(
                        "los costados no coinciden estación por estación con el dorso: la red "
                        "equivalente de 2 paneles los reparte por largo estirado (aproximación)"
                    ),
                    tuple(p.id for p in sides),
                )
            )
        elif len(sides) > len(body):
            issues.append(
                Issue(
                    "error",
                    "side",
                    t(
                        "el costado tiene {sides} estaciones y el dorso sólo {body}",
                        sides=len(sides),
                        body=len(body),
                    ),
                    tuple(p.id for p in sides),
                )
            )
        for s_, b in zip(reversed(sides), reversed(body), strict=False):
            if by_length:
                break
            if s_.meshes_depth != b.meshes_depth or abs(s_.mesh_mm - b.mesh_mm) > 1e-9:
                issues.append(
                    Issue(
                        "error",
                        "side",
                        t(
                            "costado {side} ({side_n} mallas de {side_mm:g} mm) no "
                            "cose con el dorso {top} ({top_n} mallas de {top_mm:g} mm)",
                            side=s_.id,
                            side_n=s_.meshes_depth,
                            side_mm=s_.mesh_mm,
                            top=b.id,
                            top_n=b.meshes_depth,
                            top_mm=b.mesh_mm,
                        ),
                        (s_.id, b.id),
                    )
                )
    # Costuras laterales: largo estirado de cada franja en el dorso y el vientre.
    if "upper" in lay.planes and "lower" in lay.planes:
        bu, bl = lay.bands["upper"], lay.bands["lower"]
        # Con distinta cantidad de franjas (cielo sólo en el dorso) las costuras se arman por
        # posición a lo largo (``trawlkit.sim.mesh._band_rows``): no se comparan franja a franja.
        if len(bu) == len(bl):
            for u, lo in zip(bu, bl, strict=True):
                la, lb = u.stretched_length_m, lo.stretched_length_m
                if _rel(la, lb) > SIDE_WARN:
                    issues.append(
                        Issue(
                            "warning",
                            "side_seam",
                            t(
                                "franja {up}/{low}: dorso {la:.2f} m y vientre "
                                "{lb:.2f} m de largo estirado ({pct:.0f} %)",
                                up=u.panel.id,
                                low=lo.panel.id,
                                la=la,
                                lb=lb,
                                pct=100 * _rel(la, lb),
                            ),
                            (u.panel.id, lo.panel.id),
                        )
                    )
    return issues


def errors(spec: NetSpec) -> list[Issue]:
    """Sólo los errores."""
    return [i for i in check(spec) if i.level == "error"]


def summary(spec: NetSpec) -> dict[str, Any]:
    """Resumen serializable: ¿cierra?, cantidades y problemas."""
    issues = check(spec)
    return {
        "ok": not any(i.level == "error" for i in issues),
        "errors": sum(i.level == "error" for i in issues),
        "warnings": sum(i.level == "warning" for i in issues),
        "issues": [i.to_dict() for i in issues],
    }
