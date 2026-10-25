"""Validador de consistencia de una red (Fase 12).

Una red transcripta de un plano puede traer errores de lectura (un 6 por un 8, un borde
cambiado). Las reglas de construcción del paño permiten detectar muchos de ellos:

* **Empalmes** (``seam``): dos paños unidos borde con borde tienen el mismo largo estirado. Si
  cambia el mallero, cambia la cantidad de mallas: ``T_inf,1 · m₁ ≈ T_sup,2 · m₂``.
* **Boca** (``mouth``): las alas se apoyan sobre el primer paño del cuerpo y entre ellas queda la
  bocana. Su largo, ``T_sup · m − 2 T_ala · m_ala``, debe ser positivo.
* **Costuras laterales** (``side_seam``): el dorso y el vientre se cosen por los costados, así
  que cada franja debe tener un largo estirado parecido en las dos caras.
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
SEAM_WARN = 0.04
SEAM_ERROR = 0.10
#: Diferencia relativa de largo entre las franjas del dorso y del vientre.
SIDE_WARN = 0.15


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
