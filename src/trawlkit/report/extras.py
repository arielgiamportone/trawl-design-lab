"""Secciones opcionales del informe: optimización (Fase 6) y simulación de forma (Fase 7).

:func:`trawlkit.report.build.build_report` las agrega cuando recibe ``optimization`` (un
:class:`~trawlkit.optimize.OptimizationResult`) y/o ``simulation`` (una lista de
:class:`~trawlkit.sim.SimResult`):

* tablas neutrales (:class:`~trawlkit.report.tables.Table`) que van al HTML y al XLSX:
  mejor diseño, restricciones, frente de Pareto y malla ``s × v``; comparación de la simulación
  con el motor empírico (y con DynamiT para la red FAO A-3 estándar);
* gráficos SVG con el estilo de :mod:`trawlkit.report.charts`: mapa de factibilidad ``s × v`` y
  frente de Pareto;
* las proyecciones de la forma simulada (:func:`trawlkit.sim.render.projections_svg`).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import TYPE_CHECKING

import numpy as np

from trawlkit.drawing.svg import Element, text
from trawlkit.i18n import N_, t
from trawlkit.report.charts import (
    HEIGHT,
    WIDTH,
    LegendItem,
    Plot,
    _chart,
    _series,
    axes,
    legend,
    legend_height,
    nice_ticks,
)
from trawlkit.report.labels import fmt
from trawlkit.report.tables import Cell, Column, Table

if TYPE_CHECKING:
    from trawlkit.model import DesignResult
    from trawlkit.optimize import Evaluation, OptimizationResult
    from trawlkit.sim import SimResult

OBJECTIVE_LABELS: dict[str, tuple[str, str, str]] = {
    "area_rate": (N_("máxima área barrida por hora"), "area_rate_m2_h", "m²/h"),
    "volume_rate": (N_("máximo volumen filtrado por hora"), "volume_rate_m3_h", "m³/h"),
    "energy": (N_("mínimo trabajo de remolque por m² barrido"), "energy_kgf_m_per_m2", "kgf·m/m²"),
}
CONSTRAINT_LABELS: dict[str, str] = {
    "thrust": N_("Tiro: F_T ≥ (1 + m)·R_T"),
    "net_open": N_("Red abierta (DPA de Fridman)"),
    "warp": N_("Cable de remolque"),
    "door": N_("Portón (superficie requerida)"),
    "speed": N_("Rango de velocidad"),
}

#: Rampa secuencial (un tono) del mapa de factibilidad: claro → oscuro = peor → mejor.
_RAMP = ((214, 230, 249), (28, 92, 171))
_HATCH_ID = "opt-hatch"


# ---------------------------------------------------------------------------------------------
# Optimización: tablas
# ---------------------------------------------------------------------------------------------


def _kv(name: str, value: Cell, unit: str = "") -> tuple[Cell, ...]:
    return (name, value, unit)


def optimization_best_table(opt: OptimizationResult) -> Table:
    """Mejor diseño de la optimización (magnitud, valor, unidad)."""
    b = opt.best
    st = opt.settings
    label = t(OBJECTIVE_LABELS.get(opt.objective, (opt.objective, "", ""))[0])
    rows = (
        _kv(t("Objetivo"), label),
        _kv(t("Factible"), t("sí") if opt.feasible else t("no (menor violación)")),
        _kv(t("Red base"), str(st.get("net_id", ""))),
        _kv(t("Buque"), b.vessel_id),
        _kv(t("Portón"), b.door_id),
        _kv(t("Hélice"), b.propeller),
        _kv(t("Escala de la red s"), float(b.s)),
        _kv(t("Velocidad de arrastre"), float(b.v_kn), "kn"),
        _kv(t("Relinga superior (lima)"), float(b.headrope_m), "m"),
        _kv(t("Abertura horizontal AH"), float(b.ah_m), "m"),
        _kv(t("Abertura vertical AV"), float(b.av_m), "m"),
        _kv(t("Área barrida por hora"), float(b.area_rate_m2_h), "m²/h"),
        _kv(t("Volumen filtrado por hora"), float(b.volume_rate_m3_h), "m³/h"),
        _kv(t("Resistencia total R_T"), float(b.demand_kgf), "kgf"),
        _kv(t("Tiro disponible F_T"), float(b.available_kgf), "kgf"),
        _kv(t("Margen F_T/R_T − 1"), float(b.thrust_margin) * 100.0, "%"),
        _kv(t("Trabajo por m² barrido R_T/AH"), float(b.energy_kgf_m_per_m2), "kgf·m/m²"),
        _kv(t("Cable"), b.warp_id or t("ninguno del catálogo")),
        _kv(t("Corridas del motor"), int(opt.engine_runs)),
    )
    return Table(
        key="optimizacion",
        title=t("Optimización: mejor diseño"),
        columns=(
            Column("name", t("Magnitud")),
            Column("value", t("Valor")),
            Column("unit", t("Unidad")),
        ),
        rows=rows,
        note=(
            t(
                "Escala s ∈ [{s0}, {s1}], velocidad v ∈ [{v0}, {v1}] kn, reserva de tiro "
                "{margin}, malla {n_s} × {n_v}",
                s0=f"{st['bounds']['s'][0]:g}",
                s1=f"{st['bounds']['s'][1]:g}",
                v0=f"{st['bounds']['v_kn'][0]:g}",
                v1=f"{st['bounds']['v_kn'][1]:g}",
                margin=f"{st['limits']['margin']:.0%}",
                n_s=st["grid"]["n_s"],
                n_v=st["grid"]["n_v"],
            )
            + (t(", refinado por evolución diferencial.") if opt.refine else ".")
        ),
    )


def optimization_constraints_table(opt: OptimizationResult) -> Table:
    """Restricciones del mejor diseño."""
    rows = tuple(
        (
            t(CONSTRAINT_LABELS.get(c.name, c.name)),
            float(c.value),
            None if c.lower is None else float(c.lower),
            None if c.upper is None else float(c.upper),
            "OK" if c.ok else "NO",
        )
        for c in opt.best.constraints
    )
    return Table(
        key="optimizacion_restricciones",
        title=t("Optimización: restricciones del mejor diseño"),
        columns=(
            Column("name", t("Restricción")),
            Column("value", t("Valor")),
            Column("lower", t("Mínimo")),
            Column("upper", t("Máximo")),
            Column("ok", t("Cumple")),
        ),
        rows=rows,
    )


def _eval_row(e: Evaluation) -> tuple[Cell, ...]:
    return (
        float(e.s),
        float(e.v_kn),
        float(e.ah_m),
        float(e.av_m),
        float(e.area_rate_m2_h),
        float(e.volume_rate_m3_h),
        float(e.energy_kgf_m_per_m2),
        float(e.demand_kgf),
        float(e.thrust_margin) * 100.0,
    )


def _eval_columns() -> tuple[Column, ...]:
    return (
        Column("s", "s"),
        Column("v_kn", t("Velocidad"), "kn"),
        Column("ah_m", "AH", "m"),
        Column("av_m", "AV", "m"),
        Column("area", t("Área barrida"), "m²/h"),
        Column("volume", t("Volumen"), "m³/h"),
        Column("energy", "R_T/AH", "kgf·m/m²"),
        Column("rt", "R_T", "kgf"),
        Column("margin", t("Margen"), "%"),
    )


def optimization_pareto_table(opt: OptimizationResult) -> Table:
    """Frente de Pareto (área barrida por hora vs R_T/AH)."""
    return Table(
        key="optimizacion_pareto",
        title=t("Optimización: frente de Pareto (área barrida vs trabajo por m²)"),
        columns=_eval_columns(),
        rows=tuple(_eval_row(e) for e in opt.pareto),
    )


def optimization_grid_table(opt: OptimizationResult) -> Table:
    """Malla ``s × v`` completa con factibilidad (para el XLSX)."""
    rows = tuple(
        (*_eval_row(e), t("sí") if e.feasible else t("no"), float(e.penalty))
        for e in opt.grid.flat()
    )
    return Table(
        key="optimizacion_malla",
        title=t("Optimización: malla escala × velocidad"),
        columns=(
            *_eval_columns(),
            Column("feasible", t("Factible")),
            Column("penalty", t("Violación")),
        ),
        rows=rows,
    )


def optimization_tables(opt: OptimizationResult) -> list[Table]:
    """Tablas de la optimización (orden de presentación)."""
    return [
        optimization_best_table(opt),
        optimization_constraints_table(opt),
        optimization_pareto_table(opt),
        optimization_grid_table(opt),
    ]


# ---------------------------------------------------------------------------------------------
# Optimización: gráficos
# ---------------------------------------------------------------------------------------------


def _ramp(t: float) -> str:
    lo, hi = _RAMP
    c = [round(a + (b - a) * t) for a, b in zip(lo, hi, strict=True)]
    return f"rgb({c[0]},{c[1]},{c[2]})"


def feasibility_chart(opt: OptimizationResult) -> str:
    """Mapa ``s × v``: celdas factibles coloreadas por el objetivo, no factibles rayadas."""
    g = opt.grid
    key = opt.objective
    label, attr, unit = OBJECTIVE_LABELS.get(key, (key, "area_rate_m2_h", ""))
    label = t(label)
    sense = -1.0 if key == "energy" else 1.0
    vals = g.matrix(attr)
    feas = g.feasible
    ok = vals[feas]
    lo = float(np.min(ok)) if ok.size else 0.0
    hi = float(np.max(ok)) if ok.size else 1.0
    s_vals, v_vals = list(g.s_values), list(g.v_values)
    n_s, n_v = len(s_vals), len(v_vals)
    items: list[LegendItem] = [
        ("swatch", "ramp-hi", t("{label} (más oscuro = mejor)", label=label)),
        ("swatch", "hatch", t("no factible")),
        ("swatch", "best-cell", t("mejor diseño")),
    ]
    lw = WIDTH - 84
    top = 44 + legend_height(items, lw) + 24
    x0, w = 64.0, WIDTH - 64.0 - 24.0
    h = HEIGHT - top - 50
    cw, ch = w / n_v, h / n_s
    pattern = Element(
        "pattern",
        {
            "id": _HATCH_ID,
            "width": 6,
            "height": 6,
            "patternUnits": "userSpaceOnUse",
            "patternTransform": "rotate(45)",
        },
    ).add(
        Element("rect", {"width": 6, "height": 6, "fill": "#eeeeea"}),
        Element(
            "line", {"x1": 0, "y1": 0, "x2": 0, "y2": 6, "stroke": "#bdbbb3", "stroke-width": 2}
        ),
    )
    out: list[Element] = [
        Element("defs").add(pattern),
        text((20, 24), t("Región factible en escala × velocidad"), "chart-title"),
    ]
    # Leyenda con muestras propias (rampa, rayado y mejor punto).
    lx, ly = 64.0, 44.0
    out.append(
        Element(
            "rect",
            {"x": lx + 4, "y": ly - 9, "width": 11, "height": 11, "fill": _ramp(1.0), "rx": 2},
        )
    )
    out.append(text((lx + 26, ly), items[0][2], cls="legend"))
    lx2 = lx + 26 + 5.6 * len(items[0][2]) + 16
    out.append(
        Element(
            "rect",
            {"x": lx2 + 4, "y": ly - 9, "width": 11, "height": 11, "fill": f"url(#{_HATCH_ID})"},
        )
    )
    out.append(text((lx2 + 26, ly), items[1][2], cls="legend"))
    lx3 = lx2 + 26 + 5.6 * len(items[1][2]) + 16
    out.append(
        Element(
            "rect",
            {
                "x": lx3 + 4,
                "y": ly - 9,
                "width": 11,
                "height": 11,
                "fill": "none",
                "stroke": "currentColor",
                "class": "ink",
                "stroke-width": 2,
            },
        )
    )
    out.append(text((lx3 + 26, ly), items[2][2], cls="legend"))
    best = opt.best
    for i, s in enumerate(s_vals):
        for j, v in enumerate(v_vals):
            x = x0 + j * cw
            y = top + (n_s - 1 - i) * ch
            value = float(vals[i, j])
            if feas[i, j] and math.isfinite(value):
                frac = (value - lo) / (hi - lo) if hi > lo else 1.0
                fill = _ramp(frac if sense > 0 else 1.0 - frac)
                tip = f"s = {s:.3f}, v = {v:.2f} kn: {fmt(value)} {unit}"
            else:
                fill = f"url(#{_HATCH_ID})"
                tip = f"s = {s:.3f}, v = {v:.2f} kn: {t('no factible')}"
            cell = Element(
                "rect",
                {"x": x + 0.5, "y": y + 0.5, "width": cw - 1, "height": ch - 1, "fill": fill},
            )
            cell.add(Element("title", text=tip))
            out.append(cell)
    # Mejor diseño: la celda más cercana (el refinado puede caer entre nodos de la malla).
    bi = int(np.argmin(np.abs(np.asarray(s_vals) - best.s)))
    bj = int(np.argmin(np.abs(np.asarray(v_vals) - best.v_kn)))
    bx, by = x0 + (bj + 0.5) * cw, top + (n_s - 1 - bi + 0.5) * ch
    mark = Element(
        "rect",
        {
            "x": bx - cw / 2 + 2,
            "y": by - ch / 2 + 2,
            "width": cw - 4,
            "height": ch - 4,
            "fill": "none",
            "class": "marker-best",
        },
    )
    best_txt = t("Mejor diseño: s = {s}, v = {v} kn", s=f"{best.s:.3f}", v=f"{best.v_kn:.2f}")
    mark.add(Element("title", text=best_txt))
    out.append(mark)
    base = top + h
    v_step = max(1, math.ceil(n_v / 8))
    for j, v in enumerate(v_vals):
        if j % v_step == 0 or j == n_v - 1:
            out.append(text((x0 + (j + 0.5) * cw, base + 15), f"{v:g}", cls="tick mid"))
    s_step = max(1, math.ceil(n_s / 8))
    for i, s in enumerate(s_vals):
        if i % s_step == 0 or i == n_s - 1:
            out.append(
                text((x0 - 6, top + (n_s - 1 - i + 0.5) * ch + 3.5), f"{s:.2f}", cls="tick end")
            )
    out.append(text((x0 + w / 2, base + 32), t("Velocidad de arrastre [kn]"), cls="axis-title mid"))
    out.append(text((x0, top - 8), t("Escala de la red s"), cls="axis-title"))
    n_ok = int(feas.sum())
    desc = t(
        "{n_ok} de {n} combinaciones factibles; {label} entre {lo} y {hi} {unit}. "
        "Mejor diseño s = {s}, v = {v} kn.",
        n_ok=n_ok,
        n=feas.size,
        label=label,
        lo=fmt(lo),
        hi=fmt(hi),
        unit=unit,
        s=f"{best.s:.3f}",
        v=f"{best.v_kn:.2f}",
    )
    svg = _chart(t("Región factible en escala × velocidad"), desc, out)
    extra = ".marker-best { stroke: var(--ink); stroke-width: 2.5; } .ink { stroke: var(--ink); }"
    return svg.replace("</style>", extra + "\n</style>", 1)


def pareto_chart(opt: OptimizationResult) -> str:
    """Frente de Pareto: área barrida por hora (miles de m²/h) vs R_T/AH, con el mejor diseño."""
    pts = sorted(opt.pareto, key=lambda e: e.area_rate_m2_h)
    xs = [e.area_rate_m2_h / 1000.0 for e in pts]
    ys = [e.energy_kgf_m_per_m2 for e in pts]
    b = opt.best
    bx, byv = b.area_rate_m2_h / 1000.0, b.energy_kgf_m_per_m2
    items: list[LegendItem] = [
        ("line", "series s1", t("Frente de Pareto (factibles no dominados)")),
        ("swatch", "f2", t("Mejor diseño")),
    ]
    lw = WIDTH - 84
    top = 44 + legend_height(items, lw) + 34
    out: list[Element] = [
        text((20, 24), t("Frente de Pareto"), "chart-title"),
        *legend(items, 64, 44, lw),
    ]
    all_x = [*xs, bx] if xs else [bx]
    all_y = [*ys, byv] if ys else [byv]
    xt = nice_ticks(min(all_x), max(all_x), 5)
    yt = nice_ticks(min(all_y), max(all_y), 5)
    plot = Plot(64, top, WIDTH - 64 - 32, HEIGHT - top - 46, xt[0], xt[-1], yt[0], yt[-1])
    out += axes(plot, xt, yt, t("Área barrida por hora [miles de m²/h]"), "R_T/AH [kgf·m/m²]")
    if xs:
        name = t("Frente de Pareto")
        g = _series("pareto", plot, xs, ys, "series s1", name, "kgf·m/m²", hit=False)
        out.append(g)
        for e, x, y in zip(pts, xs, ys, strict=True):
            c = Element("circle", {"cx": plot.x(x), "cy": plot.y(y), "r": 4.0, "class": "f1 dot"})
            c.add(
                Element(
                    "title",
                    text=f"s = {e.s:.3f}, v = {e.v_kn:.2f} kn: {fmt(e.area_rate_m2_h)} m²/h, "
                    f"R_T/AH = {fmt(e.energy_kgf_m_per_m2)} kgf·m/m²",
                )
            )
            out.append(c)
    px, py = plot.x(bx), plot.y(byv)
    d = Element(
        "path",
        {"d": f"M{px:.1f},{py - 7:.1f} L{px + 7:.1f},{py:.1f} L{px:.1f},{py + 7:.1f} "
         f"L{px - 7:.1f},{py:.1f} Z", "class": "f2 dot"},
    )  # fmt: skip
    d.add(
        Element(
            "title",
            text=t("Mejor diseño: s = {s}, v = {v} kn", s=f"{b.s:.3f}", v=f"{b.v_kn:.2f}"),
        )
    )
    out.append(d)
    desc = t(
        "{n} puntos no dominados; mejor diseño {area} m²/h.",
        n=len(pts),
        area=fmt(b.area_rate_m2_h),
    )
    return _chart(t("Frente de Pareto"), desc, out)


def optimization_charts(opt: OptimizationResult) -> dict[str, str]:
    """Gráficos de la optimización por clave."""
    return {"opt_mapa": feasibility_chart(opt), "opt_pareto": pareto_chart(opt)}


OPT_CHART_TITLES = {
    "opt_mapa": N_("Región factible en escala × velocidad"),
    "opt_pareto": N_("Frente de Pareto: área barrida vs trabajo por m² barrido"),
}


# ---------------------------------------------------------------------------------------------
# Simulación
# ---------------------------------------------------------------------------------------------


def _is_fao_a3_standard(result: DesignResult) -> bool:
    from trawlkit.io import load_net

    try:
        return result.case.net.model_dump() == load_net("fao_a3_standard").model_dump()
    except Exception:  # noqa: BLE001 - sin el preset no hay comparación con DynamiT
        return False


def simulation_table(result: DesignResult, sims: Sequence[SimResult]) -> Table:
    """Simulación frente al motor empírico (y DynamiT para la red FAO A-3 estándar)."""
    from trawlkit.sim.validation import DYNAMIT

    kn = np.asarray(result.case.speeds_kn, dtype=float)
    engine = {
        "ah": np.asarray(result.spread.fridman.dpa_std_m, dtype=float),
        "av": np.asarray(result.spread.vertical.fridman.std.av_m, dtype=float),
        "drag": np.asarray(result.drag.rn.std, dtype=float),
    }
    dyn_ok = _is_fao_a3_standard(result)
    dv = list(DYNAMIT["v_kn"])
    dyn_keys = {"ah": "AH_m", "av": "AV_m", "drag": "RA_kg"}
    rows: list[tuple[Cell, ...]] = []
    spec = (
        ("ah", t("Abertura horizontal AH"), "m", t("DPA de Fridman")),
        ("av", t("Abertura vertical AV"), "m", t("AV de Fridman")),
        ("drag", t("Resistencia de la red"), "kgf", "RN Aberdeen"),
    )
    for r in sims:
        v = float(r.speed_kn)
        simv = {"ah": r.ah_m, "av": r.av_m, "drag": r.drag_kgf}
        hit = [i for i, x in enumerate(dv) if abs(x - v) < 1e-9] if dyn_ok else []
        for k, name, unit, ename in spec:
            sv = float(simv[k])
            ev = float(np.interp(v, kn, engine[k]))
            dyn: float | None = float(DYNAMIT[dyn_keys[k]][hit[0]]) if hit else None
            rows.append(
                (
                    v,
                    f"{name} [{unit}]",
                    sv,
                    ename,
                    ev,
                    (sv - ev) / ev * 100.0 if ev else None,
                    dyn,
                    None if dyn is None else (sv - dyn) / dyn * 100.0,
                    None if dyn is None else (ev - dyn) / dyn * 100.0,
                )
            )
    params = sims[0].params if sims else {}
    return Table(
        key="simulacion",
        title=t("Simulación de forma frente al motor y a DynamiT"),
        columns=(
            Column("v_kn", t("Velocidad"), "kn"),
            Column("name", t("Magnitud")),
            Column("sim", t("Simulación")),
            Column("engine_name", t("Magnitud del motor")),
            Column("engine", t("Motor")),
            Column("sim_engine_pct", t("Δ sim/motor"), "%"),
            Column("dynamit", "DynamiT"),
            Column("sim_dynamit_pct", t("Δ sim/DynamiT"), "%"),
            Column("engine_dynamit_pct", t("Δ motor/DynamiT"), "%"),
        ),
        rows=tuple(rows),
        note=t(
            "Simulación cuasiestática (resolución {resolution}, C_N = {cn}, C_T = {ct}). "
            "La resistencia simulada (hilos de Morison más rozamiento con el fondo) queda ≈ 50 % "
            "por debajo de DynamiT en la red FAO A-3; las aberturas coinciden mucho mejor. "
            "DynamiT sólo está disponible para la red FAO A-3 estándar.",
            resolution=f"{params.get('resolution', 0):g}",
            cn=f"{params.get('cn', 0):g}",
            ct=f"{params.get('ct', 0):g}",
        ),
    )


def simulation_summary_table(sims: Sequence[SimResult]) -> Table:
    """Resultados de la simulación por velocidad (para el XLSX)."""
    rows = tuple(
        (
            float(r.speed_kn),
            float(r.ah_m),
            float(r.ah_lower_m),
            float(r.av_m),
            float(r.headrope_height_m),
            float(r.mouth_area_m2),
            float(r.hydro_drag_kgf),
            float(r.friction_kgf),
            float(r.drag_kgf),
            float(r.door_spread_m),
            float(r.net_length_m),
            t("sí") if r.converged else t("no"),
            int(r.iterations),
            float(r.residual),
            float(r.runtime_s),
        )
        for r in sims
    )
    return Table(
        key="simulacion_detalle",
        title=t("Simulación de forma: resultados por velocidad"),
        columns=(
            Column("v_kn", t("Velocidad"), "kn"),
            Column("ah", t("AH (lima)"), "m"),
            Column("ah_lower", t("AH (burlón)"), "m"),
            Column("av", "AV", "m"),
            Column("head_z", t("Altura de la lima"), "m"),
            Column("mouth", t("Área de la boca"), "m²"),
            Column("hydro", t("Arrastre del agua"), "kgf"),
            Column("friction", t("Rozamiento con el fondo"), "kgf"),
            Column("drag", t("Resistencia total de la red"), "kgf"),
            Column("dp", t("Distancia entre portones"), "m"),
            Column("length", t("Largo de la red"), "m"),
            Column("converged", t("Convergió")),
            Column("iterations", t("Iteraciones")),
            Column("residual", t("Residuo")),
            Column("runtime", t("Tiempo"), "s"),
        ),
        rows=rows,
    )


def simulation_tables(result: DesignResult, sims: Sequence[SimResult]) -> list[Table]:
    """Tablas de la simulación (orden de presentación)."""
    return [simulation_table(result, sims), simulation_summary_table(sims)]


def simulation_projections(
    sims: Sequence[SimResult], limit: int = 3
) -> dict[float, dict[str, str]]:
    """Planta, perfil y frente de las primeras ``limit`` velocidades."""
    from trawlkit.sim.render import projections_svg

    return {float(r.speed_kn): projections_svg(r) for r in list(sims)[:limit]}


__all__ = [
    "OPT_CHART_TITLES",
    "feasibility_chart",
    "optimization_charts",
    "optimization_tables",
    "pareto_chart",
    "simulation_projections",
    "simulation_table",
    "simulation_tables",
]
