"""Sección «Ejercicios» de los capítulos, generada desde el banco del modo docente (Fase 17).

Los enunciados usan la semilla 0 (los datos del libro); la respuesta y la explicación van en un
desplegable. El libro y la app comparten el mismo banco (``trawlkit/data/teaching``), así que
nunca se desincronizan.
"""

from __future__ import annotations

import html

from IPython.display import Markdown

from _lang import LANG, L
from trawlkit.i18n import use_lang
from trawlkit.teaching import bank, instantiate, solve
from trawlkit.teaching.bank import level_label
from trawlkit.teaching.labs import labs


def _md(text: str) -> str:
    return html.escape(text, quote=False)


def section(chapter: str) -> Markdown:
    """Ejercicios (y laboratorios) del capítulo ``chapter`` en Markdown, en el idioma del libro."""
    with use_lang(LANG):
        return _section(chapter)


def _section(chapter: str) -> Markdown:
    out: list[str] = []
    for n, spec in enumerate(bank(chapter), 1):
        ex = instantiate(spec.id, 0)
        sol = solve(spec.id, 0)
        level = level_label(ex.level)
        out.append(f"**{n}. {_md(ex.title)}** ({level.lower()}). {_md(ex.statement)}\n")
        answers = "; ".join(
            f"{_md(a.label)}: <strong>{_md(sol.texts[a.key])}</strong>"
            + (f" {_md(a.unit)}" if a.unit else "")
            for a in spec.answers
        )
        out.append(
            '<details style="margin: 0.2em 0 1.4em">'
            f"<summary>{L('Respuesta', 'Answer')}</summary>"
            f"<p>{answers}.</p><p>{_md(sol.explanation)}</p></details>\n"
        )
    found = labs(chapter)
    if found:
        names = ", ".join(f"«{_md(x.title)}»" for x in found)
        many = len(found) > 1
        if LANG == "en":
            names_en = ", ".join(f"“{_md(x.title)}”" for x in found)
            out.append(
                f"In the app, the {'labs' if many else 'lab'} {names_en} "
                f"{'walk' if many else 'walks'} through this chapter step by step on the open "
                "case.\n"
            )
        else:
            out.append(
                f"En la app, {'los laboratorios' if many else 'el laboratorio'} {names} "
                f"{'recorren' if many else 'recorre'} este capítulo paso a paso sobre el caso "
                "abierto.\n"
            )
    return Markdown("\n".join(out))
