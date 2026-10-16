"""Gráficos SVG del informe: XML válido, series esperadas y escalas."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from tests.test_report_tables import make_case
from trawlkit.drag import RN_METHODS
from trawlkit.model import DesignResult, run
from trawlkit.report.charts import (
    PALETTE_DARK,
    PALETTE_LIGHT,
    all_charts,
    breakdown_values,
    drag_breakdown_chart,
    drag_methods_chart,
    nice_ticks,
    spread_chart,
    towing_chart,
)

NS = "{http://www.w3.org/2000/svg}"


@pytest.fixture(scope="module")
def result() -> DesignResult:
    return run(make_case())


def parse(svg: str) -> ET.Element:
    return ET.fromstring(svg.encode("utf-8"))


def series(root: ET.Element) -> list[str]:
    return [el.attrib["data-series"] for el in root.iter() if "data-series" in el.attrib]


def test_nice_ticks() -> None:
    assert nice_ticks(0, 3970) == [0, 1000, 2000, 3000, 4000]
    assert nice_ticks(1, 5, 8) == [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]
    assert nice_ticks(0, 4.6) == [0, 1, 2, 3, 4, 5]
    t = nice_ticks(0.013, 0.92)
    assert t[0] <= 0.013 and t[-1] >= 0.92
    flat = nice_ticks(2, 2)
    assert flat[0] <= 2 < flat[-1]


def test_towing_chart(result: DesignResult) -> None:
    root = parse(towing_chart(result))
    assert root.find(f"{NS}title") is not None
    keys = series(root)
    assert len(keys) == 7  # 5 métodos de tiro + resistencia total estándar y modificada
    assert {"demand_std", "demand_mod", "fridman_kgf"} <= set(keys)
    markers = [el for el in root.iter() if el.attrib.get("data-marker") == "max_speed"]
    assert len(markers) == 1
    assert any("Ventana viable" in (el.text or "") for el in root.iter())


@pytest.mark.parametrize("variant", ["std", "mod"])
def test_drag_methods_chart(result: DesignResult, variant: str) -> None:
    root = parse(drag_methods_chart(result, variant))
    keys = series(root)
    assert len(keys) == len(RN_METHODS) + 1 == 14
    assert result.drag.design_method in keys and "average" in keys


def test_drag_breakdown_chart(result: DesignResult) -> None:
    svg = drag_breakdown_chart(result, 3.5)
    root = parse(svg)
    assert series(root) == ["std", "mod"]
    parts = [el.attrib["data-part"] for el in root.iter() if "data-part" in el.attrib]
    assert parts == ["RN", "RB", "Rw", "ROB"] * 2
    vals = breakdown_values(result, 3.5)
    i = result.case.speed_index(3.5)
    assert vals["std"]["RN"] == pytest.approx(float(result.drag.rn.std[i]))
    assert vals["mod"]["RN"] == pytest.approx(float(result.drag.rn.mod[i]))


def test_spread_chart(result: DesignResult) -> None:
    keys = series(parse(spread_chart(result)))
    assert keys == ["dpa_std", "dpa_mod", "av_std", "av_mod"]


def test_all_charts_and_palette(result: DesignResult) -> None:
    charts = all_charts(result)
    assert list(charts) == [
        "remolque",
        "resistencia_std",
        "resistencia_mod",
        "composicion",
        "aberturas",
    ]
    for svg in charts.values():
        root = parse(svg)
        assert "chart" in root.attrib["class"]
        style = root.find(f"{NS}style")
        assert style is not None and "prefers-color-scheme: dark" in (style.text or "")
        assert PALETTE_LIGHT[0] in (style.text or "") and PALETTE_DARK[0] in (style.text or "")


def test_charts_without_modified() -> None:
    r = run(make_case(modified=False))
    charts = all_charts(r)
    assert "resistencia_mod" not in charts
    assert series(parse(charts["aberturas"])) == ["dpa_std", "av_std"]
    assert series(parse(charts["composicion"])) == ["std"]
