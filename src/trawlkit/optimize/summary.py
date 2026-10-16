"""Resumen en Markdown (español) de un :class:`~trawlkit.optimize.OptimizationResult`."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trawlkit.optimize.search import OptimizationResult

_OBJECTIVE_NAMES = {
    "area_rate": "máxima área barrida por hora",
    "volume_rate": "máximo volumen filtrado por hora",
    "energy": "mínimo trabajo de remolque por m² barrido",
}
_CONSTRAINT_NAMES = {
    "thrust": "Tiro (F_T ≥ (1+m)·R_T)",
    "net_open": "Red abierta (DPA Fridman)",
    "warp": "Cable de remolque",
    "door": "Portón",
    "speed": "Rango de velocidad",
}


def _ok(flag: bool) -> str:
    return "sí" if flag else "NO"


def summary_markdown(result: OptimizationResult, top: int = 5) -> str:
    """Mejor diseño, restricciones y los ``top`` primeros puntos del frente de Pareto."""
    b = result.best
    st = result.settings
    lim = st["limits"]
    lines = [
        f"## Optimización: {_OBJECTIVE_NAMES.get(result.objective, result.objective)}",
        "",
        f"Red base `{st['net_id']}`, buque `{st['vessel_id']}`, portón `{st['door_id']}`, "
        f"hélice `{st['propeller']}`, margen de tiro {lim['margin']:.0%}, "
        f"s ∈ [{st['bounds']['s'][0]:g}, {st['bounds']['s'][1]:g}], "
        f"v ∈ [{st['bounds']['v_kn'][0]:g}, {st['bounds']['v_kn'][1]:g}] kn.",
        "",
    ]
    if not result.feasible:
        worst = max(b.constraints, key=lambda c: c.violation)
        lines += [
            "**Ningún diseño factible** en el rango; se muestra el de menor violación "
            f"(restricción dominante: {_CONSTRAINT_NAMES.get(worst.name, worst.name)}).",
            "",
        ]
    lines += [
        "### Mejor diseño",
        "",
        "| Magnitud | Valor | Unidad |",
        "|---|---|---|",
        f"| Escala de la red s | {b.s:.3f} | — |",
        f"| Velocidad de arrastre | {b.v_kn:.2f} | kn |",
        f"| Relinga superior (lima) | {b.headrope_m:.2f} | m |",
        f"| Abertura horizontal AH (DPA Fridman) | {b.ah_m:.2f} | m |",
        f"| Abertura vertical AV (Fridman) | {b.av_m:.2f} | m |",
        f"| Área barrida por hora | {b.area_rate_m2_h:,.0f} | m²/h |",
        f"| Volumen filtrado por hora | {b.volume_rate_m3_h:,.0f} | m³/h |",
        f"| Resistencia total R_T | {b.demand_kgf:.0f} | kgf |",
        f"| Tiro disponible F_T | {b.available_kgf:.0f} | kgf |",
        f"| Margen F_T/R_T − 1 | {b.thrust_margin:.1%} | — |",
        f"| Trabajo por m² barrido R_T/AH | {b.energy_kgf_m_per_m2:.1f} | kgf·m/m² |",
        f"| Cable | {b.warp_id or 'ninguno del catálogo'} | — |",
        f"| Portón: requerida / disponible | {b.door_required_m2:.2f} / {b.door_area_m2:.2f} "
        "| m² |",
        "",
        "| Restricción | Cumple | Valor | Límite |",
        "|---|---|---|---|",
    ]
    for c in b.constraints:
        bound = " – ".join(
            x
            for x in (
                f"≥ {c.lower:.4g}" if c.lower is not None else "",
                f"≤ {c.upper:.4g}" if c.upper is not None else "",
            )
            if x
        )
        lines.append(
            f"| {_CONSTRAINT_NAMES.get(c.name, c.name)} | {_ok(c.ok)} | {c.value:.4g} | {bound} |"
        )
    lines += [
        "",
        f"### Frente de Pareto (área barrida/h vs R_T/AH), primeros {top}",
        "",
        "| s | v [kn] | AH [m] | Área [m²/h] | R_T/AH [kgf·m/m²] | R_T [kgf] | Margen |",
        "|---|---|---|---|---|---|---|",
    ]
    for e in result.pareto[:top]:
        lines.append(
            f"| {e.s:.3f} | {e.v_kn:.2f} | {e.ah_m:.2f} | {e.area_rate_m2_h:,.0f} | "
            f"{e.energy_kgf_m_per_m2:.1f} | {e.demand_kgf:.0f} | {e.thrust_margin:.1%} |"
        )
    if not result.pareto:
        lines.append("| — | — | — | — | — | — | — |")
    lines += [
        "",
        f"{result.engine_runs} corridas del motor, {result.runtime_s:.1f} s.",
    ]
    return "\n".join(lines)


__all__ = ["summary_markdown"]
