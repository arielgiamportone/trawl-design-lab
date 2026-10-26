"""Fase 13.3: la API sin servidor (motor en el navegador) responde igual que la API FastAPI."""

from __future__ import annotations

import json
import sys

import pytest
from fastapi.testclient import TestClient

from trawlkit.api import offline
from trawlkit.api.app import app

client = TestClient(app)

GETS = [
    "/catalog/nets",
    "/catalog/nets?status=draft",
    "/catalog/nets/fao_a3_standard",
    "/catalog/nets/fao_wb_bt2p_60hp/provenance",
    "/catalog/nets/fao_wb_bt2p_60hp/check",
    "/catalog/components",
    "/catalog/components/wire?generic=true",
    "/catalog/components/rope?brand=Garware&region=south_asia",
    "/catalog/components/door/door_flat_75hp",
    "/catalog/vessels",
    "/catalog/doors",
    "/catalog/seabeds",
    "/params",
    "/errata",
    "/catalog/nets/nope",
    "/catalog/components/bobbin",
    "/catalog/fouling",
    "/catalog/species",
    "/teaching/exercises",
    "/teaching/exercises?chapter=14_resistencia&level=basico",
    "/teaching/exercises?level=experto",
    "/teaching/exercises/panos.corte_simetrico?seed=7",
    "/teaching/exercises/nada",
    "/teaching/labs",
    "/teaching/labs/lab.pano_y_resistencia",
    "/teaching/labs/lab.nada",
]

POSTS: list[tuple[str, dict[str, object]]] = [
    ("/design", {}),
    ("/design", {"net": "fao_wb_bt2p_60hp", "params": {"generic_only": True}}),
    ("/design", {"params": {"sweeps_m": -1}}),
    ("/design", {"unknown": 1}),
    ("/design/bom", {"prices": {"doors": {"value": 450, "currency": "USD", "unit": "unit"}}}),
    ("/design/layout?mode=true_scale", {}),
    ("/design/construction", {}),
    ("/design/construction?variant=mod&eye_allowance_m=0.3", {"net_modified": "fao_a3_modified"}),
    ("/design/construction?variant=mod", {}),
    ("/economics", {"economics": {"fuel_price_l": 1.2, "catch_kg_h": 100, "price_kg": 3}}),
    ("/economics", {"economics": {"hauls_per_trip": 0}}),
    (
        "/economics/compare",
        {
            "cases": [
                {"label": "A", "case": {}},
                {"label": "B", "case": {"net": "fao_wb_bt2p_60hp"}},
            ],
            "economics": {"fuel_price_l": 1.2},
            "speed_kn": 2.0,
        },
    ),
    ("/simulate", {"speeds_kn": [3.0], "resolution": 2}),
    ("/simulate", {"speeds_kn": [3.0], "resolution": 9}),
    (
        "/simulate/haul",
        {"speed_kn": 3.0, "catches_kg": [0, 600], "resolution": 2, "scenario": {"seabed": "mud"}},
    ),
    ("/simulate/explore", {"variable": "catch_kg", "values": [0, 800], "resolution": 2}),
    ("/simulate/selectivity", {"resolution": 2, "species": ["cod"]}),
    (
        "/simulate/uncertainty",
        {"samples": 3, "resolution": 2, "inputs": [{"name": "cn", "low": 1.2, "high": 1.3}]},
    ),
    ("/simulate/calibrate", {}),
    ("/sensors/parse", {"csv": "a,b\n1,2"}),
    ("/teaching/grade", {"id": "resistencia.aberdeen", "seed": 5, "answers": {"rn_kgf": "900"}}),
    ("/teaching/grade", {"id": "nada", "answers": {}}),
    (
        "/teaching/labs/check",
        {
            "lab_id": "lab.buque_y_velocidad",
            "step_id": "buque",
            "design": {"vessel": "fao_a3_180hp"},
            "answers": {"vmax": "2,52", "rn": "No: la red es la misma"},
        },
    ),
    ("/teaching/labs/check", {"lab_id": "lab.taller", "step_id": "nada", "design": {}}),
    (
        "/components/check",
        {
            "kind": "float",
            "id": "x",
            "name": "b",
            "material": "PVC",
            "diameter_mm": 100,
            "buoyancy_kgf": 9,
        },
    ),
    (
        "/optimize/components",
        {"net": "fao_wb_bt2p_60hp", "max_doors": 2, "max_floats": 2, "max_twines": 2},
    ),
    ("/optimize", {"grid": {"n_s": 3, "n_v": 3}, "refine": False}),
    ("/optimize/scaled-net", {"net": "fao_a3_standard", "s": 1.1}),
    (
        "/batch/run",
        {
            "file": {"filename": "f.csv", "content": "nombre;potencia\nA;60\nB;150\n"},
            "net": "fao_wb_bt2p_60hp",
            "assemble": False,
        },
    ),
    (
        "/batch/parse",
        {
            "file": {"filename": "c.csv", "content": "caso;red\nuno;fao_a3_standard\n"},
            "mode": "cases",
        },
    ),
]


def _strip_runtime(obj: object) -> object:
    """Quita los tiempos de cómputo (``runtime_s``), que cambian entre corridas."""
    if isinstance(obj, dict):
        return {k: _strip_runtime(v) for k, v in obj.items() if k != "runtime_s"}
    if isinstance(obj, list):
        return [_strip_runtime(v) for v in obj]
    return obj


@pytest.mark.parametrize("path", GETS)
def test_get_routes_match_the_api(path: str) -> None:
    status, body = offline.handle("GET", path)
    r = client.get(path)
    assert status == r.status_code
    if status == 200:
        assert body == r.json()


@pytest.mark.parametrize(("path", "body"), POSTS)
def test_post_routes_match_the_api(path: str, body: dict[str, object]) -> None:
    status, out = offline.handle("POST", path, json.dumps(body))
    r = client.post(path, json=body)
    assert status == r.status_code, out
    if status == 200:
        assert _strip_runtime(out) == _strip_runtime(r.json())
    else:
        assert isinstance(out["detail"], type(r.json()["detail"]))


def test_binary_batch_routes() -> None:
    import base64

    status, out = offline.handle("GET", "/batch/template?kind=fleet&format=xlsx")
    assert status == 200 and isinstance(out, offline.Binary)
    assert out.data == client.get("/batch/template?kind=fleet&format=xlsx").content
    body = {
        "file": {"filename": "f.csv", "content": "nombre;potencia\nA;60\n"},
        "net": "fao_wb_bt2p_60hp",
        "assemble": False,
    }
    wrapped = json.loads(offline.handle_json("POST", "/batch/export?format=csv", json.dumps(body)))
    assert wrapped["status"] == 200 and wrapped["media"].startswith("text/csv")
    api_csv = client.post("/batch/export?format=csv", json=body).content
    assert base64.b64decode(wrapped["binary"]) == api_csv
    pdf = offline.handle("POST", "/batch/export?format=pdf", json.dumps(body))
    assert pdf[0] == 503


def test_server_only_routes_and_json_wrapper() -> None:
    status, out = offline.handle("POST", "/classroom/auth/login", "{}")
    assert status == 503 and "conexión" in out["detail"]
    assert offline.handle("GET", "/design")[0] == 405
    assert offline.supports("POST", "/design/bom") and offline.supports("POST", "/simulate")
    assert not offline.supports("POST", "/classroom/auth/login")
    wrapped = json.loads(offline.handle_json("GET", "/health"))
    assert wrapped["status"] == 200 and wrapped["body"]["status"] == "ok"
    refine = offline.handle("POST", "/optimize", json.dumps({"refine": True}))
    assert refine[0] == 422


def test_offline_engine_does_not_import_server_or_heavy_packages() -> None:
    code = (
        "import sys, json; from trawlkit.api import offline; "
        "offline.handle('POST', '/design', '{}'); "
        "bad = [m for m in sys.modules if m.split('.')[0] in "
        "('fastapi', 'starlette', 'scipy', 'pint', 'typer', 'matplotlib', 'weasyprint')]; "
        "print(json.dumps(bad))"
    )
    import subprocess

    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert json.loads(out.stdout.strip().splitlines()[-1]) == []


def test_binary_design_routes_offline() -> None:
    """Fase 18: el plano SVG, el informe HTML y XLSX y el registro de ejemplo, sin servidor."""
    plan = offline.handle("POST", "/design/plan?view=sheet", "{}")
    assert plan[0] == 200 and isinstance(plan[1], offline.Binary)
    assert plan[1].data == client.post("/design/plan?view=sheet", json={}).content
    assert offline.handle("POST", "/design/plan?variant=mod", "{}")[0] == 422
    html = offline.handle("POST", "/design/report?format=html", "{}")
    assert html[0] == 200 and isinstance(html[1], offline.Binary)
    assert html[1].media.startswith("text/html") and b"<html" in html[1].data[:400].lower()
    xlsx = offline.handle("POST", "/design/report?format=xlsx", "{}")
    assert xlsx[0] == 200 and isinstance(xlsx[1], offline.Binary) and xlsx[1].data[:2] == b"PK"
    pdf = offline.handle("POST", "/design/report?format=pdf", "{}")
    assert pdf[0] == 503 and "html" in pdf[1]["detail"]
    ex = offline.handle("GET", "/sensors/example")
    assert isinstance(ex[1], offline.Binary)
    assert ex[1].data.decode() == client.get("/sensors/example").text
    assert offline.handle("POST", "/classroom/auth/login", "{}")[0] == 503


def test_phone_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Las guardas del teléfono rechazan una simulación cara con 422, no la cuelgan."""
    import os

    for key in offline.PHONE_LIMITS:
        monkeypatch.delenv(key, raising=False)
    offline.phone_limits()
    try:
        assert all(os.environ[k] == v for k, v in offline.PHONE_LIMITS.items())
        status, out = offline.handle(
            "POST",
            "/simulate",
            json.dumps({"speeds_kn": [1.0, 2.0, 3.0, 4.0, 5.0], "resolution": 6}),
        )
        assert status == 422 and "costosa" in out["detail"]
        status, _ = offline.handle("POST", "/optimize", json.dumps({"refine": True}))
        assert status == 422
    finally:
        # phone_limits() escribió en os.environ: no debe quedar para otras pruebas.
        for key in offline.PHONE_LIMITS:
            os.environ.pop(key, None)
