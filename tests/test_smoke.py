from typer.testing import CliRunner

import trawlkit
from trawlkit.cli import app
from trawlkit.compat import ERRATA, ERRATA_BY_KEY, Compat
from trawlkit.units import kgf_to_n, knots_to_ms, ms_to_knots, n_to_kgf


def test_version() -> None:
    assert trawlkit.__version__ == "0.1.0"


def test_units_roundtrip() -> None:
    assert ms_to_knots(knots_to_ms(3.5)) == 3.5
    assert abs(knots_to_ms(1.0) - 0.5144) < 1e-12
    assert abs(n_to_kgf(kgf_to_n(100.0)) - 100.0) < 1e-9


def test_compat_registry() -> None:
    assert Compat("excel") is Compat.EXCEL
    assert len(ERRATA) >= 10
    assert ERRATA_BY_KEY["hamuro_sin_degrees"].sheet == "Resistencia de la RED"


def test_cli_errata() -> None:
    result = CliRunner().invoke(app, ["errata"])
    assert result.exit_code == 0
    assert "warp_undersized" in result.output
