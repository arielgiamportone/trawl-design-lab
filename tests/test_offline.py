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
    status, out = offline.handle("POST", "/simulate", "{}")
    assert status == 503 and "conexión" in out["detail"]
    assert offline.handle("GET", "/design")[0] == 405
    assert offline.supports("POST", "/design/bom") and not offline.supports("POST", "/simulate")
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
