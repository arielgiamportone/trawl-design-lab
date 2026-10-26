"""Idioma del libro que se está compilando (Fase 18.5).

El libro en español vive en ``docs/`` y el inglés en ``docs/en/``; las celdas corren con el
directorio del capítulo como directorio de trabajo, así que el idioma sale de ahí. Al importarse
en el libro inglés fija también el idioma del motor (``trawlkit.i18n``), para que tablas, notas y
avisos que produce el motor salgan en inglés.
"""

from __future__ import annotations

from pathlib import Path

LANG = "en" if Path.cwd().name == "en" else "es"


def L(es: str, en: str) -> str:  # noqa: N802 - nombre corto a propósito, como gettext
    """El texto en el idioma del libro."""
    return en if LANG == "en" else es


if LANG == "en":
    from trawlkit.i18n import set_lang

    set_lang("en")
