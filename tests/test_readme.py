"""El README: indicadores al día e imágenes con URL absoluta (PyPI no resuelve rutas relativas)."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RAW = "https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/"

_spec = importlib.util.spec_from_file_location("readme_stats", ROOT / "tools" / "readme_stats.py")
assert _spec and _spec.loader
readme_stats = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(readme_stats)


@pytest.mark.parametrize("lang", ["es", "en"])
def test_indicators_up_to_date(lang: str) -> None:
    path = readme_stats.READMES[lang]
    text = path.read_text(encoding="utf-8")
    assert readme_stats.render(text, readme_stats.block(readme_stats.stats(), lang)) == text, (
        "corra `uv run python tools/readme_stats.py`"
    )


def test_stats_are_plausible() -> None:
    s = readme_stats.stats()
    assert s["nets"] == s["nets_published"] + s["nets_draft"] >= 15
    assert s["drag_methods"] == 13
    assert s["routes"] >= 36
    assert s["components_generic"] < s["components"]


@pytest.mark.parametrize("lang", ["es", "en"])
def test_images_are_absolute_and_exist(lang: str) -> None:
    text = readme_stats.READMES[lang].read_text(encoding="utf-8")
    srcs = re.findall(r"!\[[^\]]*\]\(([^)\s]+)", text) + re.findall(r'<img[^>]+src="([^"]+)"', text)
    assert srcs
    for src in srcs:
        assert src.startswith("https://"), src
        if src.startswith(RAW):
            assert (ROOT / src.removeprefix(RAW)).is_file(), src
