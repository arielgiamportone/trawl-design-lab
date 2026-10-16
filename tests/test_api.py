import json

import pytest
from fastapi.testclient import TestClient

from trawlkit.api.app import app
from trawlkit.api.service import to_jsonable

client = TestClient(app)
STD = {"net": "fao_a3_standard", "net_modified": "fao_a3_modified", "vessel": "fao_a3_150hp"}


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_catalogs() -> None:
    nets = {n["id"] for n in client.get("/catalog/nets").json()}
    assert {"fao_a3_standard", "fao_a3_modified"} <= nets
    spec = client.get("/catalog/nets/fao_a3_standard").json()
    assert [p["id"] for p in spec["panels"]][:2] == ["A", "B"]
    assert client.get("/catalog/nets/nope").status_code == 404
    assert {v["id"] for v in client.get("/catalog/vessels").json()} >= {"fao_a3_150hp"}
    doors = client.get("/catalog/doors").json()
    assert doors[0]["coefficients"]
    params = {p["name"]: p for p in client.get("/params").json()}
    assert params["sweeps_m"]["default"] == 25.0
    assert "Dim!F65" in params["sweeps_m"]["comment"]
    assert len(client.get("/errata").json()) >= 25


def test_design_excel_mode_reproduces_summary() -> None:
    r = client.post("/design", json={**STD, "compat": "excel"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"]["headrope_m"] == pytest.approx(28.698, rel=1e-6)
    assert body["summary"]["solid_surface_m2"] == pytest.approx(40.89506, rel=1e-6)
    assert body["summary"]["warp_diameter_mm"] == 12
    assert body["case"]["compat"] == "excel"
    # JSON estricto: sin NaN ni Infinity
    json.loads(r.text, parse_constant=lambda c: pytest.fail(f"constante no JSON: {c}"))


def test_design_corrected_and_params_override() -> None:
    base = client.post("/design", json=STD).json()["summary"]
    assert base["solid_surface_m2"] == pytest.approx(38.74964, rel=1e-5)
    over = client.post("/design", json={**STD, "params": {"sweeps_m": 30.0}}).json()
    assert over["summary"]["sweeps_m"] == 30.0


def test_design_inline_net_spec() -> None:
    spec = client.get("/catalog/nets/fao_a3_standard").json()
    spec["id"] = "custom"
    r = client.post("/design", json={"net": spec, "vessel": "fao_a3_150hp"})
    assert r.status_code == 200, r.text
    assert r.json()["summary"]["net_id"] == "custom"


@pytest.mark.parametrize(
    ("payload", "status"),
    [
        ({"net": "../../etc/passwd"}, 404),
        ({"vessel": "nope"}, 404),
        ({"params": {"not_a_param": 1}}, 422),
        ({"params": {"speeds_kn": []}}, 422),
        ({"compat": "other"}, 422),
        ({"unexpected": 1}, 422),
    ],
)
def test_design_rejects_bad_input(payload: dict[str, object], status: int) -> None:
    assert client.post("/design", json=payload).status_code == status


def test_plan_svg() -> None:
    r = client.post("/design/plan?view=sheet&variant=mod", json=STD)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/svg+xml")
    assert "<svg" in r.text
    assert (
        client.post("/design/plan?variant=mod", json={"net": "fao_a3_standard"}).status_code == 422
    )


@pytest.mark.parametrize("fmt", ["html", "xlsx", "pdf"])
def test_report_formats(fmt: str) -> None:
    r = client.post(f"/design/report?format={fmt}", json=STD)
    assert r.status_code == 200, r.text[:300]
    if fmt == "pdf":
        assert r.content.startswith(b"%PDF")
    elif fmt == "xlsx":
        assert r.content[:2] == b"PK"
    else:
        assert "<html" in r.text.lower()


def test_to_jsonable() -> None:
    assert to_jsonable({"a": float("nan"), "b": (1.0, float("inf"))}) == {
        "a": None,
        "b": [1.0, None],
    }
