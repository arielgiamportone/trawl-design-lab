"""Fase 18.1: textos del motor y de la API en inglés (``?lang=en``), español sin cambios."""

from __future__ import annotations

import json
import re
from typing import Any

import pytest
from fastapi.testclient import TestClient

from trawlkit.api import offline
from trawlkit.api.app import app
from trawlkit.api.service import _field_comments
from trawlkit.i18n import catalog

client = TestClient(app)
STD = {"net": "fao_a3_standard", "net_modified": "fao_a3_modified", "vessel": "fao_a3_150hp"}

#: Palabras que delatan un texto en español.
SPANISH = (
    "boyas",
    "paño",
    "lima",
    "portón",
    "falta",
    "precio",
    "corte",
    "malla",
    "desconocid",
    "burlón",
    "bolsa",
    "relinga",
)
#: Campos que traen datos del catálogo (nombres de paños, cabos, redes), no textos del motor.
DATA_KEYS = {"name", "net_name", "material", "description", "id", "net_id", "vessel_id"}


def _texts(obj: Any, skip: set[str] = DATA_KEYS) -> list[str]:
    """Todos los textos de una respuesta JSON, sin los campos de datos."""
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, dict):
        return [s for k, v in obj.items() if k not in skip for s in _texts(v, skip)]
    if isinstance(obj, list):
        return [s for v in obj for s in _texts(v, skip)]
    return []


def _assert_english(texts: list[str]) -> None:
    assert texts
    for text in texts:
        low = text.lower()
        bad = [w for w in SPANISH if re.search(rf"\b{w}", low)]
        assert not bad, f"{bad}: {text!r}"


def test_design_notes_in_english() -> None:
    notes = client.post("/design?lang=en", json=STD).json()["result"]["notes"]
    _assert_english(notes)
    assert any(n.startswith("float_count taken from the spec") for n in notes)
    pair = client.post("/design?lang=en", json={"net": "bobp_wp13_pair_ho80"}).json()
    notes = pair["result"]["notes"]
    _assert_english(notes)
    assert any("pair trawling without otter boards" in n for n in notes)
    assert any("½ headrope" in n for n in notes)


def test_design_notes_in_spanish_by_default() -> None:
    notes = client.post("/design", json=STD).json()["result"]["notes"]
    assert "float_count tomado de la spec (12 boyas)" in notes
    es = client.post("/design", json=STD, headers={"Accept-Language": "es-AR"}).json()
    assert es["result"]["notes"] == notes
    en = client.post("/design", json=STD, headers={"Accept-Language": "en-GB"}).json()
    assert "float_count taken from the spec (12 floats)" in en["result"]["notes"]


def test_construction_guide_in_english() -> None:
    r = client.post("/design/construction?lang=en", json=STD)
    assert r.status_code == 200 and r.headers["content-language"] == "en"
    g = r.json()
    _assert_english(_texts(g))
    sides = [s["instruction"] for p in g["pieces"] for s in p["sides"]]
    assert any(
        re.fullmatch(r"1N2B: 1 point and 2 bars per cycle; repeat \d+ times", s) for s in sides
    )
    assert {p["section"] for p in g["pieces"]} >= {"wingtip", "wing", "body", "codend"}
    rules = [j["rule"] for j in g["joins"]]
    assert any("taking up 2 meshes" in r for r in rules)
    assert {h["rope"] for h in g["hanging"]} == {"headrope", "footrope"}
    assert any(
        s.startswith("≈ ") and "meshes every 50 cm" in s
        for s in [h["schedule"] for h in g["hanging"]]
    )
    assert any("0.50 m" in n for n in g["notes"])  # punto decimal en inglés
    assert {r["label"] for r in g["ropes"]} >= {"Headrope (upper rope)", "Sweeps", "Crowfoot"}


def test_construction_guide_in_spanish_unchanged() -> None:
    g = client.post("/design/construction", json=STD).json()
    sides = [s["instruction"] for p in g["pieces"] for s in p["sides"]]
    assert any(
        re.fullmatch(r"1N2B: 1 punta y 2 malletas por ciclo; repetir \d+ veces", s) for s in sides
    )
    assert any("0,50 m" in n for n in g["notes"])
    assert {h["rope"] for h in g["hanging"]} == {"lima", "burlón"}
    assert any("mallas cada 50 cm" in h["schedule"] for h in g["hanging"])


def test_offline_construction_matches_the_api_in_english() -> None:
    status, body = offline.handle("POST", "/design/construction?lang=en", json.dumps(STD))
    assert status == 200
    api = client.post("/design/construction?lang=en", json=STD).json()
    assert body == api
    assert body != client.post("/design/construction", json=STD).json()


def test_economics_without_prices_in_english() -> None:
    e = client.post("/economics?lang=en", json=STD).json()
    trip = e["trips"][0]
    _assert_english(trip["missing"] + trip["warnings"] + e["notes"] + [e["gear_cost_source"]])
    assert "catch price" in trip["missing"] and "diesel price" in trip["missing"]
    assert e["gear_cost_source"] == "no data"
    es = client.post("/economics", json=STD).json()
    assert "precio de la captura" in es["trips"][0]["missing"]
    assert es["gear_cost_source"] == "sin dato"


def test_params_comments_follow_the_language() -> None:
    en = {p["name"]: p["comment"] for p in client.get("/params?lang=en").json()}
    es = {p["name"]: p["comment"] for p in client.get("/params").json()}
    assert en["sweeps_m"] == "Dim!F65 = Mec!E213 (design sweeps)"
    assert es["sweeps_m"] == "Dim!F65 = Mec!E213 (patentes de diseño)"
    assert en["pair_wing_spread_m"] == "pair trawl: wingtip spread (None → ½ headrope)"
    _assert_english(list(en.values()))


def test_every_params_comment_has_an_english_translation() -> None:
    en = catalog("en")
    missing = [c for c in _field_comments().values() if c not in en]
    assert not missing, missing


def test_error_details_in_english(monkeypatch: pytest.MonkeyPatch) -> None:
    r = client.get("/catalog/nets/nope?lang=en")
    assert r.status_code == 404 and r.json()["detail"] == "unknown net: 'nope'"
    r = client.post("/design?lang=en", json={**STD, "vessel": "nope"})
    assert r.status_code == 404 and r.json()["detail"] == "unknown vessel: 'nope'"
    r = client.post("/design?lang=en", json={**STD, "params": {"nope": 1}})
    assert r.status_code == 422 and r.json()["detail"] == "unknown parameters: ['nope']"
    assert client.get("/catalog/nets/nope").json()["detail"] == "red desconocida: 'nope'"
    monkeypatch.setenv("TRAWLKIT_MAX_SIM_SECONDS", "1")
    body = {"speeds_kn": [2.0, 3.0, 4.0], "resolution": 6}
    r = client.post("/simulate?lang=en", json=body)
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail.startswith("simulation too costly") and "lower the resolution" in detail
    _assert_english([detail])
    assert (
        client.post("/simulate", json=body)
        .json()["detail"]
        .startswith("simulación demasiado costosa")
    )


def test_offline_needs_server_in_english() -> None:
    status, body = offline.handle("POST", "/classroom/auth/login?lang=en", "{}")
    assert status == 503 and body["detail"].startswith("This feature needs a connection")
    assert (
        offline.handle("POST", "/classroom/auth/login", "{}")[1]["detail"] == offline.NEEDS_SERVER
    )


def test_classroom_status_in_english(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    r = client.get("/classroom/status?lang=en").json()
    assert r["enabled"] is False
    assert r["detail"].startswith("The classroom is not enabled on this server")
    _assert_english([r["detail"]])
    es = client.get("/classroom/status").json()
    assert es["detail"].startswith("El aula no está habilitada")


def test_netcheck_and_components_in_english() -> None:
    from trawlkit.i18n import use_lang
    from trawlkit.io import NetSpec
    from trawlkit.netcheck import check

    kinds = client.get("/catalog/components?lang=en").json()
    assert {k["label"] for k in kinds} >= {"Otter board", "Float", "Netting and twine"}
    r = client.get("/catalog/components/door/nope?lang=en")
    assert r.status_code == 404 and r.json()["detail"] == "unknown component: door/nope"
    spec = client.get("/catalog/nets/fao_a3_standard").json()
    spec["panels"][-1]["meshes_top"] += 60  # borde que no empalma
    with use_lang("en"):
        issues = check(NetSpec.model_validate(spec))
    seams = [i.message for i in issues if i.code == "seam"]
    assert seams and "does not match the mouth edge" in seams[0]
    _assert_english([i.message for i in issues])
