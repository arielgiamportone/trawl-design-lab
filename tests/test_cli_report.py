import xml.etree.ElementTree as ET
from pathlib import Path

from typer.testing import CliRunner

from trawlkit.cli import app

runner = CliRunner()
ARGS = [
    "data/fao_a3_standard.yaml",
    "--modified",
    "data/fao_a3_modified.yaml",
    "--vessel",
    "fao_a3_150hp",
]


def test_plan_sheet_and_scale(tmp_path: Path) -> None:
    for view, variant in (("sheet", "std"), ("scale", "mod")):
        out = tmp_path / f"{view}_{variant}.svg"
        res = runner.invoke(
            app, ["plan", *ARGS, "--view", view, "--variant", variant, "--out", str(out)]
        )
        assert res.exit_code == 0, res.output
        ET.fromstring(out.read_text(encoding="utf-8").split("\n", 1)[1])


def test_plan_rejects_mod_without_modified_net(tmp_path: Path) -> None:
    res = runner.invoke(app, ["plan", "data/fao_a3_standard.yaml", "--variant", "mod"])
    assert res.exit_code != 0


def test_report_html_xlsx_svg(tmp_path: Path) -> None:
    res = runner.invoke(app, ["report", *ARGS, "--out", str(tmp_path), "--format", "html,xlsx,svg"])
    assert res.exit_code == 0, res.output
    names = {p.name for p in tmp_path.iterdir()}
    assert {"informe.html", "informe.xlsx", "plano_estandar.svg", "plano_modificada.svg"} <= names
    assert "informe.pdf" not in names


def test_report_rejects_unknown_format(tmp_path: Path) -> None:
    res = runner.invoke(app, ["report", *ARGS, "--out", str(tmp_path), "--format", "docx"])
    assert res.exit_code != 0
