"""Informe HTML: estructura, autocontención, escape y valores del resumen."""

from __future__ import annotations

import datetime as dt
import importlib
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

import pytest

from tests.test_report_tables import make_case
from trawlkit.model import DesignResult, run
from trawlkit.report import html as html_mod
from trawlkit.report.html import default_sheet_svgs, placeholder_svg, render_html, render_table
from trawlkit.report.labels import fmt
from trawlkit.report.tables import Column, Table

SECTIONS = (
    "portada",
    "resumen",
    "lamina-estandar",
    "lamina-modificada",
    "escala",
    "graficos",
    "tablas",
    "erratas",
    "notas",
    "metodologia",
    "creditos",
)


class Walker(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.links: list[tuple[str, str, str]] = []
        self.tags: dict[str, int] = {}
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags[tag] = self.tags.get(tag, 0) + 1
        for name, value in attrs:
            if name == "id" and value:
                self.ids.append(value)
            if name in {"src", "href", "xlink:href"} and value is not None:
                self.links.append((tag, name, value))

    def handle_data(self, data: str) -> None:
        self.text.append(data)


@pytest.fixture(scope="module")
def result() -> DesignResult:
    return run(make_case())


@pytest.fixture(scope="module")
def page(result: DesignResult) -> str:
    return render_html(result, generated=dt.date(2026, 1, 2))


@pytest.fixture(scope="module")
def walked(page: str) -> Walker:
    w = Walker()
    w.feed(page)
    w.close()
    return w


def test_sections_present(walked: Walker) -> None:
    for sid in SECTIONS:
        assert sid in walked.ids, sid
    assert len(walked.ids) == len(set(walked.ids))


def test_self_contained(page: str, walked: Walker) -> None:
    for tag, name, value in walked.links:
        assert not value.lower().startswith(("http://", "https://", "//")), (tag, name, value)
        assert value.startswith("#"), (tag, name, value)
    assert "<script" not in page.lower()
    assert "@import" not in page
    assert "<link" not in page.lower()
    assert walked.tags.get("svg", 0) >= 9  # 4 láminas + 5 gráficos


def test_print_css(page: str) -> None:
    assert "@page { size: A4; margin: 15mm;" in page
    assert "@page sheet { size: A3 landscape" in page
    assert "prefers-color-scheme: dark" in page
    assert "break-before: page" in page


def test_summary_values_and_cover(result: DesignResult, page: str, walked: Walker) -> None:
    text = " ".join(walked.text)
    summary = result.summary()
    for key in ("headrope_m", "footrope_m", "solid_surface_m2", "warp_breaking_load_t"):
        assert fmt(summary[key]) in text, key
    assert str(summary["warp_selected"]) in text
    assert "2026-01-02" in text
    assert "Ariel Luján Giamportone" in text
    assert "CC BY 4.0" in text and "MIT" in text
    assert result.case.compat.value in text
    win = result.performance.design
    assert win.max_speed_kn is not None
    assert f"{win.max_speed_kn:.2f}" in text
    for name in ("Fridman", "Suzuki", "Dremière", "Hamuro"):
        assert name in text


def test_text_is_escaped() -> None:
    t = Table(
        key="x",
        title="<b>título & más</b>",
        columns=(Column("a", "A<"), Column("b", "B")),
        rows=(("<script>alert(1)</script>", 1.5),),
    )
    out = render_table(t)
    assert "<script>" not in out and "&lt;script&gt;" in out
    assert "&lt;b&gt;título &amp; más&lt;/b&gt;" in out
    assert 'class="num"' in out


def test_no_modified_omits_mod_sections() -> None:
    r = run(make_case(modified=False))
    w = Walker()
    w.feed(render_html(r))
    assert "lamina-modificada" not in w.ids and "escala-modificada" not in w.ids
    assert "lamina-estandar" in w.ids


def test_placeholder_when_drawing_missing(
    result: DesignResult, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(html_mod, "_sheet_functions", lambda: None)
    sheets = default_sheet_svgs(result)
    assert set(sheets) == {"std", "mod", "scale_std", "scale_mod"}
    for svg in sheets.values():
        assert "Plano no disponible" in svg
        ET.fromstring(svg.encode())
    assert "Plano no disponible" in placeholder_svg()


def test_real_sheet_functions_when_available(result: DesignResult) -> None:
    drawing = importlib.import_module("trawlkit.drawing")
    if not (hasattr(drawing, "net_sheet_svg") and hasattr(drawing, "net_scale_svg")):
        pytest.skip("trawlkit.drawing.net_sheet_svg / net_scale_svg todavía no existen")
    sheets = default_sheet_svgs(result)
    for key, svg in sheets.items():
        assert "Plano no disponible" not in svg, key
        ET.fromstring(svg.encode())
    assert "<svg" in drawing.net_sheet_svg(result, "std")
