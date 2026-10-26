"""Idiomas del motor (Fase 18): español (original) e inglés.

Los textos que el motor entrega a la app, la API, la CLI y los informes se escriben en español,
como siempre, y pasan por :func:`t`. En español devuelve el mismo texto; en inglés lo busca en
``data/i18n/en.yaml``, un catálogo plano «texto en español → traducción» (al estilo gettext).
Si falta una traducción se usa el español: nunca se pierde un texto. ``tests/test_i18n.py``
recorre el código y exige que cada texto marcado tenga su traducción.

El idioma vive en una :class:`~contextvars.ContextVar`: la API lo fija por pedido (``?lang=en`` o
``Accept-Language``), la CLI con ``--lang`` y el código con :func:`use_lang`.

Los textos que se definen en constantes (tablas de rótulos) se marcan con :func:`N_`, que no los
traduce al importar el módulo, y se traducen con :func:`t` al usarlos.
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from functools import cache
from typing import Any

import yaml

from trawlkit.io import DATA_DIR

LANGS: tuple[str, ...] = ("es", "en")
DEFAULT_LANG = "es"
I18N_DIR = DATA_DIR / "i18n"

_lang: ContextVar[str] = ContextVar("trawlkit_lang", default=DEFAULT_LANG)


def normalize_lang(raw: str | None) -> str:
    """``"en-US"``, ``"EN"``, ``"en;q=0.8, es"`` → ``"en"``; lo desconocido → español."""
    if not raw:
        return DEFAULT_LANG
    for part in raw.split(","):
        code = part.split(";")[0].strip().lower()[:2]
        if code in LANGS:
            return code
    return DEFAULT_LANG


def get_lang() -> str:
    """Idioma activo."""
    return _lang.get()


def set_lang(lang: str | None) -> Token[str]:
    """Fija el idioma (devuelve el *token* para volver al anterior)."""
    return _lang.set(normalize_lang(lang))


def reset_lang(token: Token[str]) -> None:
    """Vuelve al idioma anterior a :func:`set_lang`."""
    _lang.reset(token)


@contextmanager
def use_lang(lang: str | None) -> Iterator[str]:
    """Contexto con el idioma ``lang``."""
    token = set_lang(lang)
    try:
        yield get_lang()
    finally:
        _lang.reset(token)


@cache
def catalog(lang: str) -> dict[str, str]:
    """Catálogo «español → idioma» (vacío para el español).

    Se arma con ``data/i18n/<lang>.yaml`` y los archivos de ``data/i18n/<lang>/`` (uno por área:
    informes, motor, API…); una misma entrada en dos archivos es un error.
    """
    if lang == DEFAULT_LANG:
        return {}
    paths = [I18N_DIR / f"{lang}.yaml", *sorted((I18N_DIR / lang).glob("*.yaml"))]
    out: dict[str, str] = {}
    for path in paths:
        if not path.is_file():
            continue
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        if not isinstance(data, dict):
            raise ValueError(f"{path}: se espera un mapa «español: traducción»")
        for k, v in data.items():
            if str(k) in out and out[str(k)] != str(v):
                raise ValueError(f"{path}: traducción repetida y distinta para {k!r}")
            out[str(k)] = str(v)
    return out


def N_(msgid: str) -> str:  # noqa: N802 - convención de gettext
    """Marca un texto para traducir más tarde (lo devuelve sin cambios)."""
    return msgid


def t(msgid: str, /, **kw: Any) -> str:
    """El texto ``msgid`` (en español) en el idioma activo, con ``{campos}`` rellenados."""
    lang = get_lang()
    text = msgid if lang == DEFAULT_LANG else catalog(lang).get(msgid, msgid)
    return text.format(**kw) if kw else text


def tr(msgid: str | None) -> str | None:
    """:func:`t` que deja pasar ``None`` (rótulos opcionales)."""
    return None if msgid is None else t(msgid)


def fmt_num(x: float | int | None, nd: int = 2, *, lang: str | None = None) -> str:
    """Número con el separador decimal y de miles del idioma.

    Español: ``1 234,5`` (espacio de miles, coma decimal); inglés: ``1,234.5``.
    """
    if x is None:
        return "—"
    v = float(x)
    if not math.isfinite(v):
        return "—"
    text = f"{v:,.{nd}f}"
    if (lang or get_lang()) == "es":
        text = text.replace(",", " ").replace(".", ",")
    return "0" if text in ("-0", "-0,0", "-0.0") else text


def dec(x: float, nd: int = 1, *, lang: str | None = None) -> str:
    """Número sin separador de miles y con el decimal del idioma (``12,5`` o ``12.5``)."""
    text = f"{x:.{nd}f}"
    return text.replace(".", ",") if (lang or get_lang()) == "es" else text
