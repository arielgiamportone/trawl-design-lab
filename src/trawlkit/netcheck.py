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
* **Datos** (``data``): campos que el motor necesita (U1, rendimiento del hilo).

Cada problema es un :class:`Issue` con nivel ``error`` (la red no cierra) o ``warning`` (hay que
revisar la lectura). Las tolerancias cubren los redondeos habituales de los planos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

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
        f"{where}: el borde de bolsa de {prev.id} ({prev.meshes_bottom} × {prev.mesh_mm:g} mm = "
        f"{a:.2f} m) no empalma con el borde de boca de {nxt.id} ({nxt.meshes_top} × "
        f"{nxt.mesh_mm:g} mm = {b:.2f} m): {100 * d:.0f} % de diferencia",
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
        f"panel {panel.id}: el corte {cut} en {n} mallas de alto da un cambio de ancho de "
        f"{best:.0f} mallas, pero el paño pasa de {panel.meshes_top} a {panel.meshes_bottom} "
        f"({taper} mallas)",
        (panel.id,),
    )


def check(spec: NetSpec) -> list[Issue]:
    """Problemas de consistencia de ``spec`` (lista vacía si la red cierra)."""
    from trawlkit.drawing.layout import layout_net

    issues: list[Issue] = []
    for p in spec.panels:
        if p.hanging_ratio is None and str(p.mesh_orientation) != "square":
            issues.append(
                Issue("error", "data", f"panel {p.id}: falta U1 (hanging_ratio)", (p.id,))
            )
        if p.rtex is None and p.runnage_m_per_kg is None:
            issues.append(
                Issue(
                    "warning",
                    "data",
                    f"panel {p.id}: sin Rtex ni rendimiento; el peso del hilo se estima del "
                    "diámetro",
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
        issues.append(Issue("error", "structure", f"no se puede disponer la red: {exc}"))
        return issues
    for plane in lay.planes:
        central = [s.panel for s in lay.central(plane)]
        wings = [s.panel for s in lay.side_chain(plane, "right")]
        label = {"upper": "dorso", "lower": "vientre", "side": "costado"}.get(plane, plane)
        for a, b in zip(central, central[1:], strict=False):
            if (i := _seam(a, b, label)) is not None:
                issues.append(i)
        for a, b in zip(wings, wings[1:], strict=False):
            if (i := _seam(a, b, f"{label}, ala")) is not None:
                issues.append(i)
        if central and wings:
            first, wing = central[0], wings[-1]
            bosom = first.meshes_top * _m(first) - 2 * wing.meshes_bottom * _m(wing)
            if bosom <= 0:
                issues.append(
                    Issue(
                        "error",
                        "mouth",
                        f"{label}: las alas ({wing.id}, {wing.meshes_bottom} mallas) son más "
                        f"anchas que el borde de boca de {first.id} ({first.meshes_top} mallas): "
                        "no queda bocana",
                        (first.id, wing.id),
                    )
                )
        if not central:
            issues.append(Issue("error", "structure", f"{label}: no hay paños centrales"))
    # Costados (redes de 4 paneles): estación por estación con el dorso, desde el copo.
    if "side" in lay.planes and "upper" in lay.planes:
        sides = [s.panel for s in lay.central("side")]
        body = [s.panel for s in lay.central("upper")]
        if len(sides) > len(body):
            issues.append(
                Issue(
                    "error",
                    "side",
                    f"el costado tiene {len(sides)} estaciones y el dorso sólo {len(body)}",
                    tuple(p.id for p in sides),
                )
            )
        for s_, b in zip(reversed(sides), reversed(body), strict=False):
            if s_.meshes_depth != b.meshes_depth or abs(s_.mesh_mm - b.mesh_mm) > 1e-9:
                issues.append(
                    Issue(
                        "error",
                        "side",
                        f"costado {s_.id} ({s_.meshes_depth} mallas de {s_.mesh_mm:g} mm) no "
                        f"cose con el dorso {b.id} ({b.meshes_depth} mallas de {b.mesh_mm:g} mm)",
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
                            f"franja {u.panel.id}/{lo.panel.id}: dorso {la:.2f} m y vientre "
                            f"{lb:.2f} m de largo estirado ({100 * _rel(la, lb):.0f} %)",
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
