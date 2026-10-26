"""Informe del lote en HTML y PDF: resumen de la flota y una ficha por buque (Fase 14).

La portada dice la red base, el objetivo y los filtros; la tabla resume cada buque (escala,
velocidad, cumple o no, armado, costo); cada ficha muestra la lámina de la red escalada
(:func:`trawlkit.drawing.net_sheet_svg`), el armado, las restricciones y la lista de materiales.
El PDF sale con WeasyPrint como los informes de un caso (:mod:`trawlkit.report.pdf`).
"""

from __future__ import annotations

import datetime as _dt
import html
from typing import Any

from trawlkit.batch.export import STATUS_LABEL, SUMMARY_COLUMNS
from trawlkit.batch.run import BatchResult, BatchRow
from trawlkit.i18n import N_, fmt_num, get_lang, t

OBJECTIVE_LABEL = {
    "area": N_("la mayor red que el buque remolca"),
    "energy": N_("menor trabajo por m² barrido"),
    "cost": N_("armado más barato"),
}

_CSS = """
:root { --ink: #1b1b1b; --muted: #5f5f5f; --line: #d8d6d0; --accent: #1c5cab;
  --good: #1f7a3a; --crit: #b3261e; --bg: #ffffff; }
body { font-family: "DejaVu Sans", Arial, sans-serif; color: var(--ink); background: var(--bg);
  font-size: 10pt; margin: 0; }
@page { size: A4; margin: 16mm 14mm; }
h1 { font-size: 18pt; margin: 0 0 4mm; }
h2 { font-size: 13pt; margin: 8mm 0 3mm; border-bottom: 1px solid var(--line); }
h3 { font-size: 11pt; margin: 4mm 0 2mm; }
table { border-collapse: collapse; width: 100%; margin: 2mm 0 4mm; }
th, td { border-bottom: 1px solid var(--line); padding: 1.2mm 1.6mm; text-align: left;
  vertical-align: top; }
th { background: #f0efea; font-weight: 600; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
.ok { color: var(--good); font-weight: 600; }
.bad { color: var(--crit); font-weight: 600; }
.muted { color: var(--muted); }
.card { page-break-before: always; }
.sheet svg { width: 100%; height: auto; max-height: 120mm; }
.small { font-size: 8.5pt; }
"""


def _fmt(v: Any, nd: int = 2) -> str:
    if v is None or v == "":
        return "—"
    if isinstance(v, bool):
        return t("sí") if v else t("no")
    if isinstance(v, float):
        # Miles con espacio fino (U+202F) en español; coma de miles en inglés.
        return fmt_num(v, nd).replace(" ", "\u202f")
    if isinstance(v, list | tuple):
        return "; ".join(str(x) for x in v) or "—"
    return str(v)


def _e(v: Any, nd: int = 2) -> str:
    return html.escape(_fmt(v, nd))


def _summary_table(result: BatchResult) -> str:
    keys = [
        ("bhp", "hp", 0),
        ("s", t("Escala"), 3),
        ("speed_kn", "v [kn]", 2),
        ("demand_kgf", "R_T [kgf]", 0),
        ("area_rate_m2_h", t("Área [m²/h]"), 0),
        ("door", t("Portón"), 0),
        ("warp", t("Cable"), 0),
        ("cost", t("Costo"), 0),
    ]
    head = "".join(f"<th>{html.escape(h)}</th>" for _, h, _ in keys)
    rows = []
    for r in result.rows:
        status = t(STATUS_LABEL[r.status])
        cls = "ok" if r.status == "ok" else "bad"
        if r.status == "error":
            rows.append(
                f"<tr><td>{html.escape(r.name)}</td><td class='bad'>{t('error')}</td>"
                f"<td colspan='{len(keys)}'>{html.escape(r.error or '')}</td></tr>"
            )
            continue
        cells = "".join(
            f"<td class='num'>{_e(r.summary.get(k), nd)}</td>"
            if isinstance(r.summary.get(k), float | int)
            else f"<td>{_e(r.summary.get(k))}</td>"
            for k, _, nd in keys
        )
        rows.append(
            f"<tr><td>{html.escape(r.name)}</td><td class='{cls}'>{status}</td>{cells}</tr>"
        )
    return (
        f"<table><thead><tr><th>{t('Buque')}</th><th>{t('Estado')}</th>{head}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _sheet_svg(row: BatchRow) -> str:
    p = row.projection
    if p is None or p.case is None:
        return ""
    try:
        from trawlkit.drawing import net_sheet_svg
        from trawlkit.model import run

        return net_sheet_svg(run(p.case), "std")
    except (ValueError, KeyError, ZeroDivisionError, IndexError):
        return f"<p class='muted'>{t('No se pudo dibujar la lámina.')}</p>"


def _card(row: BatchRow) -> str:
    s = row.summary
    lines = []
    for key, label in SUMMARY_COLUMNS["fleet"]:
        if key in ("vessel", "failed"):
            continue
        lines.append(f"<tr><th>{html.escape(t(label))}</th><td>{_e(s.get(key), 3)}</td></tr>")
    failed = s.get("failed") or []
    cons = (
        f"<p class='ok'>{t('Cumple tiro, apertura, cable, portón y profundidad.')}</p>"
        if not failed
        else "<ul>" + "".join(f"<li class='bad'>{html.escape(f)}</li>" for f in failed) + "</ul>"
    )
    bom = ""
    p = row.projection
    if p is not None and p.assembly is not None:
        trs = "".join(
            f"<tr><td>{html.escape(ln.label)}</td>"
            f"<td>{html.escape(ln.component_name or ln.component_id or '—')}</td>"
            f"<td class='num'>{_e(ln.quantity, 1)} {html.escape(ln.unit)}</td>"
            f"<td class='num'>{t('sin precio') if ln.cost is None else _e(ln.cost, 0)}</td></tr>"
            for ln in p.assembly.bom.lines
        )
        bom = (
            f"<h3>{t('Lista de materiales')}</h3><table><thead><tr><th>{t('Ítem')}</th>"
            f"<th>{t('Componente')}</th><th>{t('Cantidad')}</th><th>{t('Costo')}</th></tr>"
            f"</thead><tbody>{trs}</tbody></table>"
        )
    notes = "".join(f"<li>{html.escape(n)}</li>" for n in row.notes)
    return (
        f"<section class='card'><h2>{html.escape(row.name)}</h2>"
        f"<div class='sheet'>{_sheet_svg(row)}</div>"
        f"<table class='small'>{''.join(lines)}</table>{cons}{bom}"
        f"<h3>{t('Supuestos y avisos')}</h3><ul class='small muted'>{notes}</ul></section>"
    )


def batch_html(result: BatchResult, generated: _dt.date | None = None) -> str:
    """Informe del lote en HTML autocontenido (para imprimir o convertir a PDF)."""
    st = result.settings
    date = (generated or _dt.date.today()).isoformat()
    c = result.counts
    filters = []
    if st.get("region"):
        filters.append(t("región {region}", region=st["region"]))
    if st.get("generic_only"):
        filters.append(t("sólo genéricos"))
    objective = OBJECTIVE_LABEL.get(st.get("objective", ""))
    margin = _e(st.get("margin", 0.1) * 100 if st.get("margin") is not None else None, 0)
    intro = (
        "<p>"
        + t(
            "Red base: <strong>{net}</strong>. Objetivo: {objective}. "
            "Reserva de tiro: {margin} %. ",
            net=html.escape(str(st.get("net_name") or st.get("net") or "—")),
            objective=html.escape(t(objective) if objective else "—"),
            margin=margin,
        )
        + (t("Filtros: {filters}.", filters=", ".join(filters)) if filters else "")
        + "</p><p>"
        + t(
            "{n} buques: {ok} cumplen, {infeasible} no cumplen y {error} con error. "
            "Generado el {date} con trawlkit.",
            n=len(result.rows),
            ok=c["ok"],
            infeasible=c["infeasible"],
            error=c["error"],
            date=date,
        )
        + "</p><p class='muted small'>"
        + t(
            "Resultados orientativos: la escala sale de la semejanza por potencia refinada con "
            "el optimizador, y el armado del catálogo de componentes. Verifique con el plano y "
            "la ficha de cada buque antes de construir."
        )
        + "</p>"
    )
    cards = "".join(_card(r) for r in result.rows if r.status != "error")
    return (
        f"<!doctype html><html lang='{get_lang()}'><head><meta charset='utf-8'>"
        f"<title>{t('Lote de flota')}</title><style>{_CSS}</style></head><body>"
        f"<h1>{t('Proyección de la red a la flota')}</h1>{intro}<h2>{t('Resumen')}</h2>"
        f"{_summary_table(result)}{cards}</body></html>"
    )


def batch_pdf(result: BatchResult) -> bytes:
    """Informe del lote en PDF (WeasyPrint, extra ``report``)."""
    from trawlkit.report.pdf import flatten_css_vars

    try:
        from weasyprint import HTML
    except (ImportError, OSError) as exc:  # pragma: no cover - depende del entorno
        raise RuntimeError(
            t('el PDF necesita WeasyPrint: pip install "trawlkit[report]" (y Pango)')
        ) from exc
    out = HTML(string=flatten_css_vars(batch_html(result))).write_pdf()
    assert isinstance(out, bytes)
    return out


__all__ = ["OBJECTIVE_LABEL", "batch_html", "batch_pdf"]
