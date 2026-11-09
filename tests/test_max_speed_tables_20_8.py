"""Fase 20.8: la velocidad máxima fuera de la grilla dice «> 5» en todas las tablas.

Caso: red ``inidep_iat151_va355_construida`` + buque ``bipo_victor_angelescu`` (modo corregido):
el tiro supera la resistencia en toda la grilla, ``max_speed_kn`` = 5 es una cota inferior. El
resumen lo marca con ``max_speed_beyond_grid`` y las tablas del informe y la CLI muestran «> 5».
La A-3 no cambia.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

from openpyxl import load_workbook

from trawlkit.api import service
from trawlkit.i18n import use_lang
from trawlkit.model import DesignResult
from trawlkit.report import render_html, write_xlsx
from trawlkit.report.labels import summary_markdown
from trawlkit.report.tables import speed_window_table, summary_table


@cache
def _va() -> DesignResult:
    case = service.build_case(
        net="inidep_iat151_va355_construida", vessel="bipo_victor_angelescu", compat="corrected"
    )
    return service.run_case(case)


@cache
def _a3() -> DesignResult:
    return service.run_case(service.build_case(net="fao_a3_standard", compat="corrected"))


def _max_row(result: DesignResult) -> tuple[object, ...]:
    return next(r for r in summary_table(result).rows if r[0] == "max_speed_kn")


def test_summary_flags_the_max_speed_beyond_the_grid() -> None:
    s = _va().summary()
    assert s["max_speed_kn"] == 5.0  # sigue numérica (banco docente, laboratorios)
    assert s["max_speed_beyond_grid"] is True


def test_report_tables_say_beyond_the_grid() -> None:
    r = _va()
    design = next(row for row in speed_window_table(r).rows if row[-1])
    assert design[2] == "> 5"
    assert _max_row(r)[2] == "> 5 (fuera de la grilla)"
    assert all(not str(row[0]).endswith("beyond_grid") for row in summary_table(r).rows)
    md = summary_markdown(r.summary())
    assert "| > 5 (fuera de la grilla) | kn |" in md
    assert "beyond_grid" not in md
    with use_lang("en"):
        assert _max_row(r)[2] == "> 5 (beyond the grid)"


def test_html_and_xlsx_reports(tmp_path: Path) -> None:
    r = _va()
    html = render_html(r)
    assert "&gt; 5 (fuera de la grilla)" in html or "> 5 (fuera de la grilla)" in html
    wb = load_workbook(write_xlsx(r, tmp_path / "va.xlsx"))
    cells = {str(c.value) for ws in wb.worksheets for row in ws.iter_rows() for c in row}
    assert "> 5" in cells and "> 5 (fuera de la grilla)" in cells


def test_a3_unchanged() -> None:
    r = _a3()
    s = r.summary()
    assert s["max_speed_beyond_grid"] is False
    assert abs(float(s["max_speed_kn"] or 0) - 2.2684049494387843) < 1e-9
    assert isinstance(_max_row(r)[2], float)
    assert all(isinstance(row[2], float) for row in speed_window_table(r).rows)
