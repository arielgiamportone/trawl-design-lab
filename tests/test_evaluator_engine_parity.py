"""Fase 20.6: el optimizador y la economía usan la demanda, el tiro y las aberturas del motor.

Antes, :class:`~trawlkit.optimize.evaluate.Evaluator` tomaba la resistencia de una sola red
(``warps.total``) sin el rozamiento con el fondo ni el resto del arte (tangones, gemelo, vara), el
tiro de un solo buque en la pareja, la DPA de Fridman con el tope geométrico del libro aun con el
método camaronero, la tijera y la separación de Fridman promediadas sobre su malla fina, y los
cables del libro en vez del de la fuente: con el tangonero y la red del INIDEP la economía decía
que el buque no podía remolcar a ninguna velocidad mientras el motor daba 128 % de reserva.
"""

from __future__ import annotations

import dataclasses
from functools import cache

import numpy as np
import pytest
from fastapi.testclient import TestClient

from trawlkit.api import service
from trawlkit.api.app import app
from trawlkit.economics import EconomicInputs, economics
from trawlkit.model import DesignCase, run
from trawlkit.optimize.evaluate import Evaluator
from trawlkit.sim.validation import standard_case
from trawlkit.units import KNOT_TO_MS

TANGONERA = "inidep_ito043_tangonera_inidep"
TANGONERO = "ar_tangonero_1998"


@cache
def _cases() -> dict[str, DesignCase]:
    base = standard_case()
    return {
        "a3": base,
        "a3_seabed": dataclasses.replace(base, seabed="sand"),
        "fleet_otter": service.build_case(net="fao_a3_standard", vessel="bip_capitan_canepa"),
        "outrigger_inidep": service.build_case(net=TANGONERA, vessel=TANGONERO),
        "twin": dataclasses.replace(base, rig="twin"),
        "beam": dataclasses.replace(base, rig="beam"),
        "pair": dataclasses.replace(base, rig="pair"),
    }


@pytest.mark.parametrize("name", list(_cases()))
def test_evaluator_matches_engine(name: str) -> None:
    case = _cases()[name]
    r = run(case)
    ev = Evaluator(case)
    c = ev.curves(1.0)
    win = r.performance.design
    for i, v in enumerate(case.speeds_kn):
        if not ev.speeds[0] <= v <= ev.speeds[-1]:
            continue
        e = ev.from_curves(c, v)
        assert e.demand_kgf == pytest.approx(float(win.demand_kgf[i]), rel=1e-9), v
        assert e.available_kgf == pytest.approx(float(win.available_kgf[i]), rel=1e-9), v
    assert c.result.doors.spread_m == pytest.approx(r.doors.spread_m, rel=1e-12)
    assert c.door_required_m2 == pytest.approx(r.doors.required_area.per_door_m2, rel=1e-12)
    if case.fixed_opening:
        e = ev.from_curves(c, 3.0)
        assert e.ah_m == pytest.approx(r.spread.horizontal_opening_m, rel=1e-12)


def test_a3_unchanged_by_averaging_speeds() -> None:
    """Fijar las velocidades de los promedios en las del caso no cambia el resultado del libro."""
    base = standard_case()
    a = run(base)
    b = run(dataclasses.replace(base, averaging_speeds_kn=base.speeds_kn))
    assert np.array_equal(a.performance.design.demand_kgf, b.performance.design.demand_kgf)
    assert a.summary() == b.summary()
    with pytest.raises(ValueError, match="averaging_speeds_kn"):
        dataclasses.replace(base, averaging_speeds_kn=(2.25,))


def test_tangonero_economics_feasible_where_engine_has_reserve() -> None:
    case = _cases()["outrigger_inidep"]
    r = run(case)
    win = r.performance.design
    res = economics(case, EconomicInputs())
    assert not any("A ninguna velocidad" in n for n in res.notes)
    margin = {
        float(v): float(a / d - 1.0)
        for v, a, d in zip(win.speeds_kn, win.available_kgf, win.demand_kgf, strict=True)
    }
    # A 2 kn el motor da ≈ 128 % de reserva de tiro; la economía, la misma.
    assert margin[2.0] == pytest.approx(1.28, abs=0.01)
    for trip in res.trips:
        v = trip.speed_kn
        if v in margin:
            # Factible donde el motor tiene reserva por encima del margen (10 %); no factible
            # donde no tiene tiro (el cable de 24 mm de la fuente alcanza en todo el rango).
            assert trip.feasible == (margin[v] >= 0.1), v
    assert res.trips[0].feasible and not res.trips[-1].feasible


def test_area_rate_counts_every_net() -> None:
    """El área barrida por hora suma las bocas de las dos redes (como el modo guiado, 19.8d)."""
    case = _cases()["outrigger_inidep"]
    r = run(case)
    e = Evaluator(case).at(1.0, 2.0)
    ah = r.spread.horizontal_opening_m
    assert e.ah_m == pytest.approx(ah)
    assert e.area_rate_m2_h == pytest.approx(2 * ah * 2.0 * KNOT_TO_MS * 3600.0)
    assert e.energy_kgf_m_per_m2 == pytest.approx(e.demand_kgf / (2 * ah))


def test_tangonero_economics_api() -> None:
    client = TestClient(app)
    body = {"net": TANGONERA, "vessel": TANGONERO, "economics": {}}
    res = client.post("/economics", json=body)
    assert res.status_code == 200, res.text
    out = res.json()
    assert any(t["feasible"] for t in out["trips"])
    assert not any("A ninguna velocidad" in n for n in out["notes"])
