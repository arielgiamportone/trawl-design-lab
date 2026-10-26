"""Economía de la operación (Fase 16): marea, curva por velocidad, comparación y lotes."""

from __future__ import annotations

import dataclasses
import json
from functools import cache

import pytest

from trawlkit.api import service
from trawlkit.economics import (
    EconomicInputs,
    EconomicsResult,
    Species,
    compare,
    economics,
    trip,
)
from trawlkit.sim.core import DIESEL_KG_L, KW_PER_HP, SFC_KG_KWH

FULL = EconomicInputs(
    currency="ARS",
    fuel_price_l=1200.0,
    lube_price_l=6000.0,
    catch_kg_h=150.0,
    species=(Species("langostilla", 0.8, 900.0), Species("merluza", 0.2, 1500.0)),
    crew_share=0.4,
    gear_cost=3_000_000.0,
    trip_costs=150_000.0,
    annual_costs=6_000_000.0,
)


def _trip(inp: EconomicInputs = FULL, **kw: float) -> object:
    args = dict(
        speed_kn=3.0,
        demand_kgf=1000.0,
        area_rate_m2_h=50_000.0,
        reference_area_rate_m2_h=50_000.0,
        vessel_hp=150.0,
    )
    args.update(kw)
    return trip(inp, **args)  # type: ignore[arg-type]


@cache
def _a3() -> EconomicsResult:
    return economics(service.build_case(), FULL)


def test_inputs_validation_and_price() -> None:
    assert FULL.mean_price == pytest.approx(0.8 * 900 + 0.2 * 1500)
    assert FULL.towing_hours == 8.0 and FULL.sea_hours == 4 + 8 + 2
    with pytest.raises(ValueError):
        EconomicInputs(hauls_per_trip=0)
    with pytest.raises(ValueError):
        EconomicInputs(crew_share=1.5)
    with pytest.raises(ValueError, match="desconocidos"):
        EconomicInputs.from_dict({"nope": 1})
    rt = EconomicInputs.from_dict(FULL.to_dict())
    assert rt == FULL
    assert EconomicInputs(species=(Species("x", 1.0, None),)).mean_price is None


def test_fuel_follows_towing_power() -> None:
    t = _trip()
    kw = 1000.0 * 9.80665 * 3.0 * 1852 / 3600 / 0.5 / 1000
    assert t.towing_power_kw == pytest.approx(kw)
    l_kwh = SFC_KG_KWH / DIESEL_KG_L
    assert t.fuel_l_h_tow == pytest.approx(kw * l_kwh)
    assert t.fuel_l_steam == pytest.approx(150 * KW_PER_HP * 0.8 * l_kwh * 4)
    assert t.fuel_l == pytest.approx(t.fuel_l_tow + t.fuel_l_steam + t.fuel_l_handling)
    capped = _trip(demand_kgf=10_000.0)
    assert capped.power_limited and capped.fuel_l_h_tow == pytest.approx(150 * KW_PER_HP * l_kwh)


def test_catch_scales_with_swept_area() -> None:
    assert _trip().catch_kg == pytest.approx(150 * 8)
    assert _trip(area_rate_m2_h=75_000.0).catch_kg == pytest.approx(1.5 * 150 * 8)


def test_crew_share_and_breakeven() -> None:
    t = _trip()
    shared = t.costs["fuel"] + t.costs["lube"] + 150_000
    assert t.costs["crew"] == pytest.approx(0.4 * (t.revenue - shared))
    assert t.margin == pytest.approx(t.revenue - t.total_cost)
    # Al precio de equilibrio el margen es cero.
    inp = dataclasses.replace(FULL, species=(), price_kg=t.breakeven_price)
    assert _trip(inp).margin == pytest.approx(0.0, abs=1e-6)
    gross = dataclasses.replace(FULL, share_after_costs=False)
    t2 = _trip(gross)
    assert t2.costs["crew"] == pytest.approx(0.4 * t2.revenue)
    inp2 = dataclasses.replace(gross, species=(), price_kg=t2.breakeven_price)
    assert _trip(inp2).margin == pytest.approx(0.0, abs=1e-6)
    wage = dataclasses.replace(FULL, crew_mode="wage", wage_day=50_000.0, crew_size=4)
    assert _trip(wage).costs["crew"] == pytest.approx(200_000.0)


def test_gear_amortisation() -> None:
    t = _trip()
    per_h = 3_000_000 / 2000 + 3_000_000 * 0.1 / (8 * 150)
    assert t.costs["gear"] == pytest.approx(per_h * 8)
    assert t.costs["annual"] == pytest.approx(6_000_000 / 150)


def test_missing_data_is_reported_not_invented() -> None:
    t = _trip(EconomicInputs())
    assert t.total_cost is None and t.revenue is None and t.margin is None
    assert "precio del gasoil" in t.missing and not t.complete
    partial = _trip(EconomicInputs(fuel_price_l=1000.0, catch_kg_h=100.0, price_kg=500.0))
    assert partial.total_cost == pytest.approx(partial.costs["fuel"])
    assert partial.margin is not None and not partial.complete
    assert _trip().complete


def test_a3_curve() -> None:
    r = _a3()
    assert [t.speed_kn for t in r.trips][0] == 1.5 and r.trips[-1].speed_kn == 4.0
    assert all(t.feasible == (t.speed_kn <= 2.25) for t in r.trips if t.speed_kn != 2.25)
    assert r.best_margin_kn is not None and r.best_margin_kn <= 2.25
    assert r.best is not None and r.best.feasible
    assert r.year["margin"] == pytest.approx(r.best.margin * FULL.trips_per_year)
    fuel = [t.fuel_l for t in r.trips]
    assert fuel == sorted(fuel)
    assert any("poco abierta" in w for t in r.trips for w in t.warnings)


def test_gear_cost_from_the_bill_of_materials() -> None:
    from trawlkit.cost import bill_of_materials

    case = service.build_case()
    lines = bill_of_materials(service.run_case(case)).lines
    prices = {
        ln.key: {
            "value": 10.0,
            "currency": "ARS",
            "unit": ln.unit,
            "date": "2026-10",
            "source": "t",
        }
        for ln in lines
    }
    inp = dataclasses.replace(FULL, gear_cost=None)
    r = economics(case, inp, prices=prices)
    assert r.gear_cost_source == "lista de materiales" and r.gear_cost and r.gear_cost > 0
    assert economics(case, inp).gear_cost_source == "sin dato"


def test_compare_and_payback() -> None:
    a3 = service.build_case()
    wb = service.build_case("fao_wb_bt2p_60hp", vessel="fao_a3_150hp")
    rows = compare([("A-3", a3, None), ("Workbook", wb, 2_000_000.0)], FULL)
    assert rows[0].savings_year is None
    b = rows[1]
    assert b.savings_year == pytest.approx(b.annual_margin - rows[0].annual_margin)
    if b.savings_year and b.savings_year > 0:
        assert b.payback_years == pytest.approx(2_000_000.0 / b.savings_year)
    fixed = compare([("A-3", a3, None), ("A-3", a3, None)], FULL, speed_kn=2.0)
    assert fixed[1].savings_year == pytest.approx(0.0, abs=1e-6)
    assert fixed[1].trip is not None and fixed[1].trip.speed_kn == 2.0


def test_fleet_batch_with_economics() -> None:
    from trawlkit.batch import ProjectOptions, run_fleet
    from trawlkit.batch.export import to_csv
    from trawlkit.batch.fleet import fleet_vessel

    vessels = [fleet_vessel({"name": n, "bhp": hp}) for n, hp in (("A", 60), ("B", 150))]
    opts = ProjectOptions(assemble=False, economics=FULL)
    res = run_fleet(vessels, "fao_wb_bt2p_60hp", opts)
    a, b = (r.summary for r in res.rows)
    assert a["catch_kg_trip"] < b["catch_kg_trip"]
    assert a["margin_year"] == pytest.approx(a["margin_trip"] * FULL.trips_per_year)
    assert "Margen por marea" in to_csv(res).splitlines()[0]


def test_api_offline_and_cli(tmp_path: object) -> None:
    from pathlib import Path

    from fastapi.testclient import TestClient
    from typer.testing import CliRunner

    from trawlkit.api import offline
    from trawlkit.api.app import app
    from trawlkit.cli import app as cli

    client = TestClient(app)
    body = {"economics": json.loads(json.dumps(FULL.to_dict()))}
    r = client.post("/economics", json=body)
    assert r.status_code == 200 and r.json()["best_margin_kn"] == _a3().best_margin_kn
    status, out = offline.handle("POST", "/economics", json.dumps(body))
    assert status == 200 and out == r.json()
    assert client.post("/economics", json={"economics": {"x": 1}}).status_code == 422
    comp = {
        "cases": [
            {"label": "A-3", "case": {}},
            {"label": "WB", "case": {"net": "fao_wb_bt2p_60hp"}},
        ],
        "economics": body["economics"],
    }
    r = client.post("/economics/compare", json=comp)
    assert r.status_code == 200 and [x["label"] for x in r.json()["rows"]] == ["A-3", "WB"]
    out_path = Path(str(tmp_path)) / "eco.csv"
    res = CliRunner().invoke(
        cli,
        [
            "economics",
            "fao_a3_standard",
            "--fuel-price",
            "1200",
            "--catch-kg-h",
            "150",
            "--price-kg",
            "1000",
            "-o",
            str(out_path),
        ],
    )
    assert res.exit_code == 0, res.output
    assert "Mayor margen" in res.output and out_path.read_text().startswith("speed_kn;")
