"""Sección «Ejercicios» de los capítulos, generada desde el banco del modo docente (Fase 17).

Los enunciados usan la semilla 0 (los datos del libro); la respuesta y la explicación van en un
desplegable. El libro y la app comparten el mismo banco (``trawlkit/data/teaching``), así que
nunca se desincronizan.
"""

from __future__ import annotations

import html

from IPython.display import Markdown

from trawlkit.teaching import bank, instantiate, solve
from trawlkit.teaching.bank import LEVEL_LABELS
from trawlkit.teaching.labs import labs


def _md(text: str) -> str:
    return html.escape(text, quote=False)


def section(chapter: str) -> Markdown:
    """Ejercicios (y laboratorios) del capítulo ``chapter`` en Markdown."""
    out: list[str] = []
    for n, spec in enumerate(bank(chapter), 1):
        ex = instantiate(spec.id, 0)
        sol = solve(spec.id, 0)
        level = LEVEL_LABELS[ex.level]
        out.append(f"**{n}. {_md(ex.title)}** ({level.lower()}). {_md(ex.statement)}\n")
        answers = "; ".join(
            f"{_md(a.label)}: <strong>{_md(sol.texts[a.key])}</strong>"
            + (f" {_md(a.unit)}" if a.unit else "")
            for a in spec.answers
        )
        out.append(
            '<details style="margin: 0.2em 0 1.4em"><summary>Respuesta</summary>'
            f"<p>{answers}.</p><p>{_md(sol.explanation)}</p></details>\n"
        )
    found = labs(chapter)
    if found:
        names = ", ".join(f"«{_md(x.title)}»" for x in found)
        many = len(found) > 1
        out.append(
            f"En la app, {'los laboratorios' if many else 'el laboratorio'} {names} "
            f"{'recorren' if many else 'recorre'} este capítulo paso a paso sobre el caso "
            "abierto.\n"
        )
    return Markdown("\n".join(out))
