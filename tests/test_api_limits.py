"""Guardas de costo de la API configurables por entorno (despliegue en CPU lenta)."""

import pytest
from fastapi.testclient import TestClient

from trawlkit.api import service
from trawlkit.api.app import app

client = TestClient(app)

_ENV = ("TRAWLKIT_MAX_SIM_SECONDS", "TRAWLKIT_MAX_OPT_GRID", "TRAWLKIT_ALLOW_REFINE")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _ENV:
        monkeypatch.delenv(name, raising=False)


def test_defaults_without_env() -> None:
    assert service.sim_max_cost_s() == service.SIM_MAX_COST_S == 30.0
    assert service.opt_max_grid() == 25
    assert service.refine_allowed() is True


@pytest.mark.parametrize("raw", ["", "abc", "-5", "0", "nan", "inf"])
def test_invalid_sim_seconds_fall_back_to_default(
    monkeypatch: pytest.MonkeyPatch, raw: str
) -> None:
    monkeypatch.setenv("TRAWLKIT_MAX_SIM_SECONDS", raw)
    assert service.sim_max_cost_s() == 30.0


@pytest.mark.parametrize(("raw", "expected"), [("15", 15), ("1", 2), ("99", 25), ("x", 25)])
def test_opt_grid_is_clamped(monkeypatch: pytest.MonkeyPatch, raw: str, expected: int) -> None:
    monkeypatch.setenv("TRAWLKIT_MAX_OPT_GRID", raw)
    assert service.opt_max_grid() == expected


@pytest.mark.parametrize(
    ("raw", "allowed"),
    [("0", False), ("false", False), ("No", False), ("off", False), ("1", True), ("yes", True)],
)
def test_refine_flag(monkeypatch: pytest.MonkeyPatch, raw: str, allowed: bool) -> None:
    monkeypatch.setenv("TRAWLKIT_ALLOW_REFINE", raw)
    assert service.refine_allowed() is allowed


def test_simulate_respects_env_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    # 3 velocidades a resolución 2 ≈ 2,9 s estimados: pasa con 30 s, se rechaza con 2 s.
    assert 2.0 < service.estimate_sim_cost(3, 2) < 30.0
    monkeypatch.setenv("TRAWLKIT_MAX_SIM_SECONDS", "2")
    r = client.post("/simulate", json={"speeds_kn": [2.0, 3.0, 4.0], "resolution": 2})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "demasiado costosa" in detail and "máximo 2 s" in detail


def test_optimize_grid_respects_env_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRAWLKIT_MAX_OPT_GRID", "3")
    body = {"grid": {"n_s": 4, "n_v": 2}, "refine": False}
    r = client.post("/optimize", json=body)
    assert r.status_code == 422
    assert "máximo 3 × 3" in r.json()["detail"]
    ok = client.post("/optimize", json={**body, "grid": {"n_s": 3, "n_v": 2}})
    assert ok.status_code == 200, ok.text[:300]


def test_optimize_refine_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRAWLKIT_ALLOW_REFINE", "0")
    r = client.post("/optimize", json={"grid": {"n_s": 2, "n_v": 2}, "refine": True})
    assert r.status_code == 422
    assert "refinado" in r.json()["detail"]
    ok = client.post("/optimize", json={"grid": {"n_s": 2, "n_v": 2}, "refine": False})
    assert ok.status_code == 200, ok.text[:300]
