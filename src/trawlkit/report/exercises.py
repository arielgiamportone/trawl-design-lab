"""Guía de ejercicios imprimible: enunciados y clave de respuestas en HTML o PDF (Fase 17).

La misma guía sirve para un trabajo práctico en papel (``key=False``) y para el docente
(``key=True``: respuestas y explicación de cada ejercicio con la semilla del alumno).
"""

from __future__ import annotations

import datetime as _dt
import html
from collections.abc import Sequence

from trawlkit.i18n import get_lang, t
from trawlkit.report.construction import _CSS
from trawlkit.teaching.bank import LEVEL_LABELS, ExerciseInstance, Solution

_EXTRA_CSS = """
.ex { border: 1px solid var(--line); padding: 3mm 4mm; margin: 0 0 4mm; page-break-inside: avoid; }
.ex h3 { margin-top: 0; }
.tag { display: inline-block; font-size: 8.5pt; border: 1px solid var(--line);
  border-radius: 2mm; padding: 0 2mm; margin-left: 2mm; color: var(--muted); }
.blank { display: inline-block; min-width: 32mm; border-bottom: 1px solid var(--ink); }
.key { background: var(--panel); padding: 2mm 3mm; margin-top: 2mm; }
"""


def _data_table(ex: ExerciseInstance) -> str:
    if not ex.data:
        return ""
    rows = "".join(
        f"<tr><td>{html.escape(d.label)}</td><td class='num'>{html.escape(d.text)}</td>"
        f"<td>{html.escape(d.unit)}</td></tr>"
        for d in ex.data
    )
    return f"<table class='kv small'>{rows}</table>"


def _answers_html(ex: ExerciseInstance, sol: Solution | None) -> str:
    items = []
    for a in ex.answers:
        unit = f" {html.escape(a.unit)}" if a.unit else ""
        if sol is None:
            value = "<span class='blank'>&nbsp;</span>"
        else:
            value = f"<strong>{html.escape(sol.texts.get(a.key, ''))}</strong>"
        items.append(f"<li>{html.escape(a.label)}: {value}{unit}</li>")
    out = f"<ol type='a'>{''.join(items)}</ol>"
    if sol is not None and sol.explanation:
        out += f"<div class='key small'>{html.escape(sol.explanation)}</div>"
    return out


def exercise_sheet_html(
    items: Sequence[tuple[ExerciseInstance, Solution | None]],
    *,
    title: str | None = None,
    subtitle: str | None = None,
    generated: _dt.date | None = None,
) -> str:
    """Guía en HTML autocontenido; con soluciones en los ítems es la clave de respuestas."""
    title = t("Guía de ejercicios") if title is None else title
    date = (generated or _dt.date.today()).isoformat()
    key = any(sol is not None for _, sol in items)
    blocks = []
    for n, (ex, sol) in enumerate(items, 1):
        level = t(LEVEL_LABELS.get(ex.level, ex.level))
        blocks.append(
            "<div class='ex'>"
            f"<h3>{n}. {html.escape(ex.title)}<span class='tag'>{html.escape(level)}</span>"
            f"<span class='tag'>{html.escape(ex.id)} · {t('semilla {seed}', seed=ex.seed)}</span>"
            "</h3>"
            f"<p>{html.escape(ex.statement)}</p>{_data_table(ex)}"
            f"{_answers_html(ex, sol)}</div>"
        )
    sub = f"<p class='muted'>{html.escape(subtitle)}</p>" if subtitle else ""
    kind = t("Clave de respuestas") if key else t("Enunciados")
    intro = t(
        "{kind}. Generada el {date} con trawlkit. Los números usan coma decimal; las "
        "respuestas se aceptan dentro de la tolerancia de cada ejercicio.",
        kind=kind,
        date=date,
    )
    return (
        f"<!doctype html><html lang='{get_lang()}'><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title><style>{_CSS}{_EXTRA_CSS}</style></head><body>"
        f"<h1>{html.escape(title)}</h1>{sub}"
        f"<p class='small muted'>{intro}</p>"
        f"{''.join(blocks)}</body></html>"
    )


def exercise_sheet_pdf(html_text: str) -> bytes:
    """La guía en PDF (WeasyPrint, extra ``report``)."""
    from trawlkit.report.pdf import flatten_css_vars

    try:
        from weasyprint import HTML
    except (ImportError, OSError) as exc:  # pragma: no cover - depende del entorno
        raise RuntimeError(
            t('el PDF necesita WeasyPrint: pip install "trawlkit[report]" (y Pango)')
        ) from exc
    out = HTML(string=flatten_css_vars(html_text)).write_pdf()
    assert isinstance(out, bytes)
    return out
