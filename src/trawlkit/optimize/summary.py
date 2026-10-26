"""Resumen en Markdown (idioma activo) de un :class:`~trawlkit.optimize.OptimizationResult`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from trawlkit.i18n import N_, t

if TYPE_CHECKING:
    from trawlkit.optimize.search import OptimizationResult

_OBJECTIVE_NAMES = {
    "area_rate": N_("máxima área barrida por hora"),
    "volume_rate": N_("máximo volumen filtrado por hora"),
    "energy": N_("mínimo trabajo de remolque por m² barrido"),
}
_CONSTRAINT_NAMES = {
    "thrust": N_("Tiro (F_T ≥ (1+m)·R_T)"),
    "net_open": N_("Red abierta (DPA Fridman)"),
    "warp": N_("Cable de remolque"),
    "door": N_("Portón"),
    "speed": N_("Rango de velocidad"),
}


def _ok(flag: bool) -> str:
    return t("sí") if flag else t("NO")


def summary_markdown(result: OptimizationResult, top: int = 5) -> str:
    """Mejor diseño, restricciones y los ``top`` primeros puntos del frente de Pareto."""
    b = result.best
    st = result.settings
    lim = st["limits"]
    lines = [
        t(
            "## Optimización: {objective}",
            objective=t(_OBJECTIVE_NAMES.get(result.objective, result.objective)),
        ),
        "",
        t(
            "Red base `{net}`, buque `{vessel}`, portón `{door}`, "
            "hélice `{propeller}`, margen de tiro {margin:.0%}, "
            "s ∈ [{s0:g}, {s1:g}], v ∈ [{v0:g}, {v1:g}] kn.",
            net=st["net_id"],
            vessel=st["vessel_id"],
            door=st["door_id"],
            propeller=st["propeller"],
            margin=lim["margin"],
            s0=st["bounds"]["s"][0],
            s1=st["bounds"]["s"][1],
            v0=st["bounds"]["v_kn"][0],
            v1=st["bounds"]["v_kn"][1],
        ),
        "",
    ]
    if not result.feasible:
        worst = max(b.constraints, key=lambda c: c.violation)
        lines += [
            t(
                "**Ningún diseño factible** en el rango; se muestra el de menor violación "
                "(restricción dominante: {name}).",
                name=t(_CONSTRAINT_NAMES.get(worst.name, worst.name)),
            ),
            "",
        ]
    lines += [
        t("### Mejor diseño"),
        "",
        t("| Magnitud | Valor | Unidad |"),
        "|---|---|---|",
        t("| Escala de la red s | {x:.3f} | — |", x=b.s),
        t("| Velocidad de arrastre | {x:.2f} | kn |", x=b.v_kn),
        t("| Relinga superior (lima) | {x:.2f} | m |", x=b.headrope_m),
        t("| Abertura horizontal AH (DPA Fridman) | {x:.2f} | m |", x=b.ah_m),
        t("| Abertura vertical AV (Fridman) | {x:.2f} | m |", x=b.av_m),
        t("| Área barrida por hora | {x:,.0f} | m²/h |", x=b.area_rate_m2_h),
        t("| Volumen filtrado por hora | {x:,.0f} | m³/h |", x=b.volume_rate_m3_h),
        t("| Resistencia total R_T | {x:.0f} | kgf |", x=b.demand_kgf),
        t("| Tiro disponible F_T | {x:.0f} | kgf |", x=b.available_kgf),
        t("| Margen F_T/R_T − 1 | {x:.1%} | — |", x=b.thrust_margin),
        t("| Trabajo por m² barrido R_T/AH | {x:.1f} | kgf·m/m² |", x=b.energy_kgf_m_per_m2),
        t("| Cable | {x} | — |", x=b.warp_id or t("ninguno del catálogo")),
        t(
            "| Portón: requerida / disponible | {req:.2f} / {area:.2f} | m² |",
            req=b.door_required_m2,
            area=b.door_area_m2,
        ),
        "",
        t("| Restricción | Cumple | Valor | Límite |"),
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
        name = t(_CONSTRAINT_NAMES.get(c.name, c.name))
        lines.append(f"| {name} | {_ok(c.ok)} | {c.value:.4g} | {bound} |")
    lines += [
        "",
        t("### Frente de Pareto (área barrida/h vs R_T/AH), primeros {top}", top=top),
        "",
        t("| s | v [kn] | AH [m] | Área [m²/h] | R_T/AH [kgf·m/m²] | R_T [kgf] | Margen |"),
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
        t(
            "{runs} corridas del motor, {secs:.1f} s.",
            runs=result.engine_runs,
            secs=result.runtime_s,
        ),
    ]
    return "\n".join(lines)


__all__ = ["summary_markdown"]
