import xml.etree.ElementTree as ET
from pathlib import Path

from typer.testing import CliRunner

from trawlkit.cli import app
from trawlkit.io import DATA_DIR

runner = CliRunner()
ARGS = [
    "fao_a3_standard",
    "--modified",
    "fao_a3_modified",
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
    # Ruta explícita a un YAML (además del id de preset que usa ARGS).
    path = str(DATA_DIR / "fao_a3_standard.yaml")
    res = runner.invoke(app, ["plan", path, "--variant", "mod"])
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


def test_optimize_command(tmp_path: Path) -> None:
    import json

    out = tmp_path / "opt.json"
    res = runner.invoke(
        app,
        [
            "optimize",
            "fao_a3_standard",
            "--vessel",
            "fao_a3_150hp",
            "--objective",
            "volume",
            "--n-s",
            "3",
            "--n-v",
            "3",
            "--no-refine",
            "--json",
            str(out),
        ],
    )
    assert res.exit_code == 0, res.output
    assert "Mejor diseño" in res.output and "Frente de Pareto" in res.output
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["objective"] == "volume_rate"
    bad = runner.invoke(app, ["optimize", "fao_a3_standard", "--objective", "nope"])
    assert bad.exit_code != 0
