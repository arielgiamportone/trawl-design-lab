"""Salidas de archivo del informe: XLSX, PDF y ``build_report``."""

from __future__ import annotations

import datetime as dt
import re
import zlib
from pathlib import Path

import pytest

from tests.test_report_tables import make_case
from trawlkit.model import DesignResult, run
from trawlkit.report import build_report, html_to_pdf, render_html, write_xlsx
from trawlkit.report.pdf import flatten_css_vars, light_vars
from trawlkit.report.tables import all_tables
from trawlkit.report.xlsx import flatten, number_format, sheet_name

openpyxl = pytest.importorskip("openpyxl")


@pytest.fixture(scope="module")
def result() -> DesignResult:
    return run(make_case())


@pytest.fixture(scope="module")
def built(result: DesignResult, tmp_path_factory: pytest.TempPathFactory) -> list[Path]:
    pytest.importorskip("weasyprint")
    out = tmp_path_factory.mktemp("informe")
    return build_report(result, out, generated=dt.date(2026, 1, 2))


def pdf_page_count(data: bytes) -> int:
    """Cuenta objetos ``/Type /Page`` (también dentro de flujos comprimidos)."""
    chunks = [data]
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.DOTALL):
        try:
            chunks.append(zlib.decompress(m.group(1)))
        except zlib.error:
            continue
    return sum(len(re.findall(rb"/Type\s*/Page(?![s\w])", c)) for c in chunks)


def test_build_report_writes_all_files(built: list[Path]) -> None:
    names = sorted(p.name for p in built)
    assert names == sorted(
        [
            "informe.html",
            "informe.pdf",
            "informe.xlsx",
            "plano_estandar.svg",
            "plano_modificada.svg",
            "plano_escala_estandar.svg",
            "plano_escala_modificada.svg",
        ]
    )
    for p in built:
        assert p.exists() and p.stat().st_size > 0


def test_pdf(built: list[Path]) -> None:
    pdf = next(p for p in built if p.suffix == ".pdf").read_bytes()
    assert pdf.startswith(b"%PDF")
    assert pdf_page_count(pdf) >= 5


def test_xlsx_matches_tables(result: DesignResult, built: list[Path]) -> None:
    path = next(p for p in built if p.suffix == ".xlsx")
    wb = openpyxl.load_workbook(path)
    from trawlkit.report.construction import report_tables

    tables = [t for t in all_tables(result) if t.key != "notas"] + report_tables(result)
    assert wb.sheetnames == [t.key for t in tables] + ["Caso", "Notas"]
    for t in tables:
        ws = wb[t.key]
        assert ws.cell(row=1, column=1).value == t.title
        assert [c.value for c in ws[2]][: len(t.columns)] == [c.heading for c in t.columns]
        assert ws.cell(row=2, column=1).font.bold
        assert ws.freeze_panes == "B3"
        for i, row in enumerate(t.rows):
            got = [ws.cell(row=3 + i, column=j + 1).value for j in range(len(row))]
            for g, e in zip(got, row, strict=True):
                if isinstance(e, float):
                    assert g == pytest.approx(e)
                else:
                    assert g == (None if e == "" else e)
    caso = {r[0].value: r[1].value for r in wb["Caso"].iter_rows(min_row=2)}
    assert caso["net"] == result.case.net.id
    assert caso["compat"] == result.case.compat.value
    notas = [r[1].value for r in wb["Notas"].iter_rows(min_row=2)]
    assert notas == result.notes


def test_write_xlsx_direct(result: DesignResult, tmp_path: Path) -> None:
    out = write_xlsx(result, tmp_path / "sub" / "x.xlsx")
    assert out.exists()


def test_xlsx_helpers() -> None:
    used: set[str] = set()
    a = sheet_name("x" * 40, used)
    b = sheet_name("x" * 40, used)
    assert len(a) == len(b) == 31 and a != b
    assert sheet_name("a/b:c", used) == "a_b_c"
    assert number_format(0.0213) == "0.0000"
    assert number_format(12.5) == "0.00"
    assert number_format(40.0) == "0"
    assert dict(flatten({"a": {"b": 1, "c": [1, 2]}, "d": [{"e": 3}]})) == {
        "a.b": 1,
        "a.c": "1, 2",
        "d[0].e": 3,
    }


def test_flatten_css_vars() -> None:
    css = (
        "svg { --ink:#111; --s1:#222; } @media (prefers-color-scheme: dark) { svg.themed "
        '{ --ink:#eee; } } :root[data-theme="dark"] svg { --ink:#fff; } '
        ".a { stroke: var(--ink); fill: var(--s1); color: var(--missing, red); }"
    )
    assert light_vars(css) == {"ink": "#111", "s1": "#222"}
    out = flatten_css_vars(f"<p>var(--ink)</p><style>{css}</style>")
    assert "stroke: #111" in out and "fill: #222" in out and "color: red" in out
    assert "<p>var(--ink)</p>" in out


def test_html_to_pdf_direct(result: DesignResult, tmp_path: Path) -> None:
    pytest.importorskip("weasyprint")
    page = "<html><body><h1>x</h1></body></html>"
    out = html_to_pdf(page, tmp_path / "a.pdf")
    assert out.read_bytes().startswith(b"%PDF")
    assert render_html  # API exportada


def test_build_without_modified(tmp_path: Path) -> None:
    r = run(make_case(modified=False))
    files = build_report(r, tmp_path, formats=("html", "xlsx", "svg"), basename="caso")
    names = {p.name for p in files}
    assert names == {"caso.html", "caso.xlsx", "plano_estandar.svg", "plano_escala_estandar.svg"}


def test_build_rejects_unknown_format(result: DesignResult, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="formatos desconocidos"):
        build_report(result, tmp_path, formats=("docx",))
