"""El libro en inglés (docs/en) tiene un capítulo por cada capítulo del libro en español."""

from __future__ import annotations

from pathlib import Path

import yaml

DOCS = Path(__file__).resolve().parent.parent / "docs"
#: Páginas sólo del libro en inglés.
EN_ONLY = {"glossary"}


def _files(toc: Path) -> list[str]:
    data = yaml.safe_load(toc.read_text(encoding="utf-8"))
    out = [data["root"]]
    for part in data.get("parts", []):
        out += [c["file"] for c in part["chapters"]]
    return out


def test_mismos_capitulos_en_el_mismo_orden() -> None:
    es = _files(DOCS / "_toc.yml")
    en = [f for f in _files(DOCS / "en" / "_toc.yml") if f not in EN_ONLY]
    assert en == es


def test_cada_capitulo_tiene_su_par() -> None:
    es = {p.stem for p in DOCS.glob("*.md")} & set(_files(DOCS / "_toc.yml"))
    en = {p.stem for p in (DOCS / "en").glob("*.md")}
    assert sorted(es - en) == []
    assert sorted(en - es - EN_ONLY) == []
