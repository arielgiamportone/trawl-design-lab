"""Secciones opcionales del informe: optimización y simulación de forma."""

from __future__ import annotations

import datetime as dt
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.test_report_html import Walker
from trawlkit.cli import app
from trawlkit.model import DesignResult, run
from trawlkit.optimize import OptimizationResult, optimise
from trawlkit.report import build_report, render_html
from trawlkit.report.extras import (
    feasibility_chart,
    optimization_tables,
    pareto_chart,
    simulation_table,
    simulation_tables,
)
from trawlkit.sim import SimResult, sweep
from trawlkit.sim.validation import standard_case


@pytest.fixture(scope="module")
def result() -> DesignResult:
    return run(standard_case())


@pytest.fixture(scope="module")
def opt(result: DesignResult) -> OptimizationResult:
    return optimise(result.case, objective="area", grid=(4, 5), refine=False)


@pytest.fixture(scope="module")
def sims(result: DesignResult) -> list[SimResult]:
    return sweep(result, [2.0, 3.0], resolution=2)


@pytest.fixture(scope="module")
def page(result: DesignResult, opt: OptimizationResult, sims: list[SimResult]) -> str:
    return render_html(result, generated=dt.date(2026, 1, 2), optimization=opt, simulation=sims)


def test_optimization_tables(opt: OptimizationResult) -> None:
    best, cons, pareto, grid = optimization_tables(opt)
    assert best.key == "optimizacion"
    assert best.column("value")[best.column("name").index("Escala de la red s")] == opt.best.s
    assert cons.column("ok") == ["OK"] * 5
    assert len(pareto.rows) == len(opt.pareto)
    assert len(grid.rows) == 4 * 5


def test_optimization_charts_are_valid_svg(opt: OptimizationResult) -> None:
    for svg in (feasibility_chart(opt), pareto_chart(opt)):
        root = ET.fromstring(svg.split("\n", 1)[1])
        assert root.tag.endswith("svg")
    heat = feasibility_chart(opt)
    assert heat.count('fill="url(#opt-hatch)"') >= 1  # hay celdas no factibles
    assert "Mejor diseño" in heat


def test_simulation_table(result: DesignResult, sims: list[SimResult]) -> None:
    t = simulation_table(result, sims)
    assert len(t.rows) == 6  # 3 magnitudes × 2 velocidades
    drag3 = next(r for r in t.rows if r[0] == 3.0 and str(r[1]).startswith("Resistencia"))
    assert drag3[6] == pytest.approx(1331.3)  # DynamiT
    assert drag3[7] is not None and drag3[7] < 0  # la simulación da menos resistencia
    assert simulation_tables(result, sims)[1].key == "simulacion_detalle"


def test_html_sections(page: str) -> None:
    w = Walker()
    w.feed(page)
    assert "optimizacion" in w.ids and "simulacion" in w.ids
    assert (
        page.index('id="graficos"')
        < page.index('id="optimizacion"')
        < page.index('id="simulacion"')
        < page.index('id="tablas"')
    )
    assert page.count('<figure class="sim"') == 6  # planta, perfil y frente × 2 velocidades
    assert "Frente de Pareto" in page
    assert not [lk for lk in w.links if lk[2].startswith("http")]


def test_html_without_extras_has_no_sections(result: DesignResult) -> None:
    page = render_html(result, generated=dt.date(2026, 1, 2))
    assert 'id="optimizacion"' not in page and 'id="simulacion"' not in page


def test_build_report_xlsx_sheets(
    result: DesignResult, opt: OptimizationResult, sims: list[SimResult], tmp_path: Path
) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    paths = build_report(result, tmp_path, ("html", "xlsx"), optimization=opt, simulation=sims)
    xlsx = next(p for p in paths if p.suffix == ".xlsx")
    names = openpyxl.load_workbook(xlsx).sheetnames
    for name in (
        "optimizacion",
        "optimizacion_restricciones",
        "optimizacion_pareto",
        "optimizacion_malla",
        "simulacion",
        "simulacion_detalle",
    ):
        assert name in names
    assert names[-2:] == ["Caso", "Notas"]
    html = next(p for p in paths if p.suffix == ".html").read_text(encoding="utf-8")
    assert 'id="optimizacion"' in html


def test_cli_report_with_optimize_and_simulate(tmp_path: Path) -> None:
    res = CliRunner().invoke(
        app,
        [
            "report",
            "fao_a3_standard",
            "--vessel",
            "fao_a3_150hp",
            "--out",
            str(tmp_path),
            "--format",
            "html",
            "--optimize",
            "volume",
            "--simulate",
            "3",
            "--sim-resolution",
            "2",
        ],
    )
    assert res.exit_code == 0, res.output
    html = (tmp_path / "informe.html").read_text(encoding="utf-8")
    assert "máximo volumen filtrado por hora" in html
    assert 'id="simulacion"' in html


@pytest.mark.parametrize(
    "extra", [["--optimize", "speed"], ["--simulate", "x"], ["--simulate", "9"]]
)
def test_cli_report_rejects_bad_extras(tmp_path: Path, extra: list[str]) -> None:
    args = ["report", "fao_a3_standard", "--out", str(tmp_path), "--format", "html", *extra]
    assert CliRunner().invoke(app, args).exit_code != 0


def test_simulation_table_without_dynamit(sims: list[SimResult]) -> None:
    import dataclasses

    from trawlkit.io import load_net

    case = dataclasses.replace(standard_case(), net=load_net("fao_a3_modified"))
    t = simulation_table(run(case), sims)
    assert all(r[6] is None and r[7] is None for r in t.rows)
