"""Fase 20.1b: superficie requerida del portón por encima de la potencia de diseño del libro.

Errata ``door_area_power_extrapolation``: en modo corregido, por encima de 180 BHP,
``S = S_libro · (180/BHP)^0,35``; en modo EXCEL y hasta 180 BHP no cambia nada.
"""

from __future__ import annotations

import dataclasses
import warnings

import numpy as np
import pytest

from tests.golden_utils import golden
from tests.test_case_fao_a3 import fao_a3_case
from trawlkit import model
from trawlkit.api import service
from trawlkit.compat import ERRATA_BY_KEY, Compat
from trawlkit.door_selection import select_doors
from trawlkit.model import DesignCase, DesignResult, DoorStage, run
from trawlkit.optimize.evaluate import Evaluator
from trawlkit.report.tables import all_tables
from trawlkit.rigging import (
    DOOR_AREA_DESIGN_POWER_HP,
    DOOR_AREA_POWER_EXPONENT,
    door_area_power_factor,
    fishbuster_area_range_m2,
)

#: Tolerancia declarada frente a la tabla Fishbuster: la superficie corregida (portón plano de
#: referencia del caso) puede quedar hasta 35 % por encima del máximo de las filas de la tabla
#: para esa potencia (±5 % de potencia) y nunca por debajo del mínimo. El 35 % cubre el error
#: máximo del ajuste log–log a la tabla (33 %) y la diferencia de CL entre el portón plano de la
#: A-3 y el portón en V de Fishbuster («lift-to-drag ratio in excess of 2 to 1»).
FISHBUSTER_TOLERANCE = 0.35


def _fleet() -> dict[str, DesignResult]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return {vid: run(service.build_case(vessel=vid)) for vid in service.vessel_presets()}


@pytest.fixture(scope="module")
def fleet() -> dict[str, DesignResult]:
    return _fleet()


def test_factor_definition() -> None:
    assert DOOR_AREA_POWER_EXPONENT == 0.65
    assert DOOR_AREA_DESIGN_POWER_HP == 180.0
    assert door_area_power_factor(150) == 1.0
    assert door_area_power_factor(180) == 1.0
    assert door_area_power_factor(2855) == pytest.approx((180 / 2855) ** 0.35, rel=1e-12)
    assert door_area_power_factor(4159, Compat.EXCEL) == 1.0
    assert "door_area_power_extrapolation" in ERRATA_BY_KEY


@pytest.mark.parametrize("hp", [150, 180])
@pytest.mark.parametrize("compat", [Compat.EXCEL, Compat.CORRECTED])
def test_book_case_unchanged(hp: int, compat: Compat) -> None:
    """El caso A-3 (150 y 180 HP) da F212/F215/F220 del libro en los dos modos."""
    r = run(fao_a3_case(hp, compat))
    req = r.doors.required_area
    assert req.power_factor == 1.0
    assert req.per_door_m2 == req.book_per_door_m2
    f215 = "required_door_area_each_150_m2" if hp == 150 else "required_door_area_each_180_m2"
    assert req.per_door_m2 == pytest.approx(golden("portones_y_aparejamiento", f215), rel=1e-4)
    assert r.doors.required_area_per_door_class_m2 == pytest.approx(
        golden("portones_y_aparejamiento", "required_door_area_overall_m2"), rel=1e-4
    )
    assert not any("door_area_power_extrapolation" in n for n in r.notes)


def _door_stage(case: DesignCase) -> DoorStage:
    """Etapa de portones sola (el modo EXCEL no corre entero con un buque de la flota)."""
    geometry = model._stage_geometry(case)
    dimensions = model._stage_dimensions(case, geometry)
    power = model._stage_power(case)
    drag = model._stage_drag(case, geometry, dimensions)
    rig = model._stage_rigging(case, dimensions)
    return model._stage_doors(case, power, drag, rig)


def test_excel_mode_unchanged_for_large_vessel() -> None:
    case = service.build_case(vessel="bipo_victor_angelescu")
    exc = _door_stage(dataclasses.replace(case, compat=Compat.EXCEL))
    cor = _door_stage(case)
    assert exc.required_area.power_factor == 1.0
    assert exc.required_area.per_door_m2 == exc.required_area.book_per_door_m2
    # La serie E210:E218 y el valor del libro son los mismos en los dos modos.
    np.testing.assert_array_equal(exc.required_area_m2, cor.required_area_m2)
    assert cor.required_area.book_per_door_m2 == exc.required_area.per_door_m2
    assert cor.required_area.per_door_m2 == pytest.approx(
        exc.required_area.per_door_m2 * (180 / case.vessel.bhp) ** 0.35
    )


def test_fleet_within_fishbuster_range(fleet: dict[str, DesignResult]) -> None:
    """Cada buque de la flota cae en el rango Fishbuster de su potencia (tolerancia declarada)."""
    checked = 0
    for vid, r in fleet.items():
        bhp = r.power.fridman.bhp
        req = r.doors.required_area
        assert req.power_factor == pytest.approx(min(1.0, (180.0 / bhp) ** 0.35)), vid
        assert req.per_door_m2 == pytest.approx(req.book_per_door_m2 * req.power_factor), vid
        rng = fishbuster_area_range_m2(bhp)
        if rng is None:  # por debajo de la tabla (< 250 hp): factor 1, regla del libro
            assert bhp < 250 and req.power_factor == 1.0, vid
            continue
        lo, hi = rng
        assert lo <= req.per_door_m2 <= hi * (1 + FISHBUSTER_TOLERANCE), (vid, bhp, req, rng)
        # la regla del libro sin corregir se sale de la tolerancia en los buques grandes
        if bhp >= 1300:
            assert req.book_per_door_m2 > hi * (1 + FISHBUSTER_TOLERANCE), vid
        checked += 1
    assert checked >= 14


def test_note_and_report_rows(fleet: dict[str, DesignResult]) -> None:
    r = fleet["bip_holmberg"]
    assert any(n.startswith("door_area_power_extrapolation:") for n in r.notes)
    rows = {row[1]: row[2] for tbl in all_tables(r) if tbl.key == "aparejo" for row in tbl.rows}
    assert rows["Superficie requerida por portón"] == pytest.approx(
        r.doors.required_area.per_door_m2, rel=1e-3
    )
    assert rows["Superficie requerida por portón (regla del libro)"] == pytest.approx(
        r.doors.required_area.book_per_door_m2, rel=1e-3
    )


def test_selection_and_optimizer_use_engine_value(fleet: dict[str, DesignResult]) -> None:
    """La selección de portones y el optimizador usan la superficie del motor."""
    for vid in ("bip_holmberg", "ar_congelador_e3", "fao_a3_150hp"):
        r = fleet[vid]
        sel = select_doors(r, max_results=5)
        assert sel.required_m2 == r.doors.required_area.per_door_m2
        ev = Evaluator(r.case, compat=r.case.compat)
        curves = ev.curves(1.0)
        assert curves.door_required_m2 == pytest.approx(
            r.doors.required_area.per_door_m2, rel=1e-12
        ), vid
