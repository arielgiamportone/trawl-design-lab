"""Fase 18: idiomas del motor (español original, inglés)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from trawlkit import i18n
from trawlkit.i18n import catalog, dec, fmt_num, normalize_lang, t, use_lang

SRC = Path(__file__).resolve().parents[1] / "src" / "trawlkit"
MARKERS = {"t", "tr", "N_"}


def marked_texts() -> dict[str, str]:
    """Textos marcados para traducir en el código (``t("…")``, ``tr("…")``, ``N_("…")``)."""
    out: dict[str, str] = {}
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            name = node.func.id if isinstance(node.func, ast.Name) else None
            first = node.args[0]
            if name in MARKERS and isinstance(first, ast.Constant) and isinstance(first.value, str):
                out[first.value] = f"{path.relative_to(SRC)}:{node.lineno}"
    return out


def test_every_marked_text_has_an_english_translation() -> None:
    en = catalog("en")
    missing = {k: v for k, v in marked_texts().items() if k not in en}
    assert not missing, "\n".join(f"{v}: {k!r}" for k, v in sorted(missing.items())[:40])


def test_translations_keep_the_placeholders() -> None:
    import string

    fields = string.Formatter()
    for es, en in catalog("en").items():
        a = {f for _, f, _, _ in fields.parse(es) if f}
        b = {f for _, f, _, _ in fields.parse(en) if f}
        assert a == b, (es, en)


def test_spanish_is_the_identity_and_english_falls_back() -> None:
    assert t("texto que no está en el catálogo {x}", x=1) == "texto que no está en el catálogo 1"
    with use_lang("en"):
        assert t("texto que no está en el catálogo") == "texto que no está en el catálogo"
    assert i18n.get_lang() == "es"


@pytest.mark.parametrize(
    ("raw", "lang"),
    [
        ("en", "en"),
        ("en-US,en;q=0.9", "en"),
        ("es-AR", "es"),
        ("fr", "es"),
        (None, "es"),
        ("pt, en", "en"),
    ],
)
def test_normalize_lang(raw: str | None, lang: str) -> None:
    assert normalize_lang(raw) == lang


def test_number_format_by_language() -> None:
    assert fmt_num(1234.5, 1) == "1 234,5"
    assert fmt_num(1234.5, 1, lang="en") == "1,234.5"
    assert dec(2.27, 2) == "2,27" and dec(2.27, 2, lang="en") == "2.27"
    with use_lang("en"):
        assert fmt_num(-0.0001, 1) == "0"
