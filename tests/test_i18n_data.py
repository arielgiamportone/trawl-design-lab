"""Nombres de los catálogos de datos y siglas de hélice en inglés (Fase 19.0)."""

from __future__ import annotations

from trawlkit.api import service
from trawlkit.i18n import use_lang
from trawlkit.teaching import instantiate


def test_catalogos_de_datos_en_ingles() -> None:
    with use_lang("en"):
        seabeds = service.seabed_catalogue()
        fouling = service.fouling_catalogue()
        species = service.species_catalogue()
    assert [s["name"] for s in seabeds][:2] == ["Mud", "Sand"]
    assert {s["penetration"] for s in seabeds} <= {"high", "medium", "low"}
    assert fouling[0]["name"] == "Clean net"
    assert "Argentine hake" in {s["name"] for s in species}
    # Ninguna nota queda en español.
    for item in (*seabeds, *fouling, *species):
        assert not any(w in f" {item['notes']} " for w in (" del ", " con ", " las ", " los "))


def test_catalogos_de_datos_en_espanol_sin_cambios() -> None:
    assert service.seabed_catalogue()[0]["name"] == "Fango"
    assert service.species_catalogue()[0]["name"] == "Merluza común"


def test_siglas_de_helice_en_ingles() -> None:
    with use_lang("en"):
        ex = instantiate("potencia.prado_bollard", 0)
    assert "propeller type FP" in ex.statement
    assert "(PF" not in ex.statement and "PV+T" not in ex.statement
    assert "hélice PF" in instantiate("potencia.prado_bollard", 0).statement
