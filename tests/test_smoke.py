from typer.testing import CliRunner

import trawlkit
from trawlkit.cli import app
from trawlkit.compat import ERRATA, ERRATA_BY_KEY, Compat
from trawlkit.units import kgf_to_n, knots_to_ms, ms_to_knots, n_to_kgf


def test_version_is_single_sourced() -> None:
    import tomllib
    from pathlib import Path

    pyproject = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text())
    assert "version" in pyproject["project"]["dynamic"]
    assert pyproject["tool"]["hatch"]["version"]["path"] == "src/trawlkit/__init__.py"
    assert int(trawlkit.__version__.split(".")[0]) >= 1


def test_version_matches_web_and_citation() -> None:
    import json
    from pathlib import Path

    root = Path(__file__).parents[1]
    assert json.loads((root / "web/package.json").read_text())["version"] == trawlkit.__version__
    openapi = json.loads((root / "web/openapi.json").read_text())
    assert openapi["info"]["version"] == trawlkit.__version__
    cff = (root / "CITATION.cff").read_text()
    assert f"version: {trawlkit.__version__}\n" in cff


def test_units_roundtrip() -> None:
    assert ms_to_knots(knots_to_ms(3.5)) == 3.5
    assert abs(knots_to_ms(1.0) - 0.5144) < 1e-12
    assert abs(n_to_kgf(kgf_to_n(100.0)) - 100.0) < 1e-9


def test_compat_registry() -> None:
    assert Compat("excel") is Compat.EXCEL
    assert len(ERRATA) >= 25
    assert len({e.key for e in ERRATA}) == len(ERRATA)
    assert ERRATA_BY_KEY["hamuro_sin_degrees"].sheet == "Resistencia de la RED"


def test_cli_errata() -> None:
    result = CliRunner().invoke(app, ["errata"])
    assert result.exit_code == 0
    assert "warp_undersized" in result.output
