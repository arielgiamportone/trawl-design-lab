"""El diámetro de boya de la spec llega al motor (Fase 19.8)."""

from trawlkit.catalog import catalog_case
from trawlkit.model import run

NET = "inidep_iat027_tangonera_modificada"


def test_spec_float_diameter_is_used() -> None:
    r = run(catalog_case(NET).case)
    assert r.floats.count == 5
    assert r.floats.diameter_mm == 200
    assert any("float_diameter_mm" in n and "200" in n for n in r.notes)


def test_explicit_diameter_wins_over_spec() -> None:
    r = run(catalog_case(NET, float_diameter_mm=300).case)
    assert r.floats.diameter_mm == 300
