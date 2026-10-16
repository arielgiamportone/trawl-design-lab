"""Tablas del informe: cada constructor reproduce los valores de ``DesignResult``."""

from __future__ import annotations

import math

import numpy as np
import pytest

from trawlkit.compat import ERRATA, Compat
from trawlkit.drag import RN_METHODS, SUMMARY_COLUMNS, average
from trawlkit.io import load_doors, load_net, load_vessels
from trawlkit.model import DesignCase, DesignResult, run
from trawlkit.report.tables import (
    ERRATA_FIXED_TREATMENT,
    Table,
    all_tables,
    demand_table,
    drag_table,
    errata_table,
    floats_ballast_table,
    notes_table,
    panels_table,
    power_table,
    rigging_table,
    speed_window_table,
    summary_table,
    warp_table,
)


def make_case(compat: Compat = Compat.CORRECTED, modified: bool = True) -> DesignCase:
    vessels = {v.id: v for v in load_vessels().vessels}
    design = vessels["fao_a3_150hp"]
    return DesignCase(
        net=load_net("fao_a3_standard"),
        vessel=design,
        door=load_doors().doors[0],
        net_modified=load_net("fao_a3_modified") if modified else None,
        class_vessels=tuple(v for v in vessels.values() if v.id != design.id),
        compat=compat,
    )


@pytest.fixture(scope="module")
def result() -> DesignResult:
    return run(make_case())


@pytest.fixture(scope="module")
def result_excel() -> DesignResult:
    return run(make_case(Compat.EXCEL))


def kv(table: Table) -> dict[str, object]:
    return {str(r[1]): r[2] for r in table.rows}


def test_summary_table_matches_summary(result: DesignResult) -> None:
    t = summary_table(result)
    summary = result.summary()
    assert t.column("key") == list(summary)
    for key, value in zip(t.column("key"), t.column("value"), strict=True):
        expected = summary[str(key)]
        if isinstance(expected, str) or expected is None:
            assert value == expected
        else:
            assert value == pytest.approx(float(expected))
    names = dict(zip(t.column("key"), t.column("name"), strict=True))
    assert names["headrope_m"] == "Lima"
    assert t.source


@pytest.mark.parametrize("variant", ["std", "mod"])
def test_drag_table_equals_drag_kgf(result: DesignResult, variant: str) -> None:
    t = drag_table(result, variant)
    kgf = result.drag.table.kgf.variant(variant)
    assert t.column("speed_kn") == list(result.case.speeds_kn)
    for method in SUMMARY_COLUMNS:
        np.testing.assert_allclose(np.array(t.column(method), dtype=float), kgf[method])
    avg = average(result.drag.table.kgf, result.case.compat)
    np.testing.assert_allclose(
        np.array(t.column("average"), dtype=float), avg.std if variant == "std" else avg.mod
    )
    np.testing.assert_allclose(
        np.array(t.column(result.drag.design_method), dtype=float),
        result.drag.rn.variant(variant),
    )
    assert len(RN_METHODS) == 13
    assert all(c.unit == "kgf" for c in t.columns[1:])


def test_power_table(result: DesignResult) -> None:
    t = power_table(result)
    np.testing.assert_allclose(
        np.array(t.column("fridman_kgf"), float), result.power.curves.fridman_kgf
    )
    np.testing.assert_allclose(
        np.array(t.column("hamuro_kgf"), float), result.power.curves.hamuro_kgf
    )
    for vid, s in result.power.class_fridman.items():
        np.testing.assert_allclose(np.array(t.column(f"ft_pf_{vid}"), float), s.ft_fixed_pitch_kgf)
        np.testing.assert_allclose(
            np.array(t.column(f"ft_pvt_{vid}"), float), s.ft_variable_pitch_nozzle_kgf
        )
    assert len(result.power.class_fridman) == 2


@pytest.mark.parametrize("variant", ["std", "mod"])
def test_panels_table(result: DesignResult, variant: str) -> None:
    t = panels_table(result, variant)
    spec = result.case.net if variant == "std" else result.case.net_modified
    assert spec is not None
    assert t.column("id") == [p.id for p in spec.panels]
    assert t.column("mesh_mm") == [p.mesh_mm for p in spec.panels]
    assert t.column("count") == [p.count for p in spec.panels]
    geom = result.geometry.variant(variant)
    assert sum(float(x) for x in t.column("ss_m2")) == pytest.approx(  # type: ignore[arg-type]
        sum(r.solid_surface_m2 for r in geom.rows)
    )
    assert sum(float(x) for x in t.column("weight_kg")) == pytest.approx(  # type: ignore[arg-type]
        sum(r.weight_air_kg for r in geom.rows)
    )


def test_rigging_table(result: DesignResult) -> None:
    values = kv(rigging_table(result))
    assert values["Distancia entre portones (Ds)"] == pytest.approx(result.doors.spread_m)
    assert values["CL"] == pytest.approx(result.doors.polar.cl)
    assert values["CD"] == pytest.approx(result.doors.polar.cd)
    i = result.case.speed_index(3.0)
    assert values["ROB = 20 % de FT a 3 kn"] == pytest.approx(
        float(result.doors.rob_shares_kgf["20pct"][i])
    )
    assert values["Brida superior"] == pytest.approx(result.bridles.lengths.upper_m)
    assert values["Ángulo de ataque de bridas (δ)"] == pytest.approx(
        result.bridles.attack_angle_deg
    )
    assert values["Abertura horizontal (AH)"] == pytest.approx(result.spread.horizontal_opening_m)
    assert values["AV Suzuki"] == pytest.approx(result.spread.vertical.suzuki_m)
    assert values["AV Martini"] == pytest.approx(result.spread.vertical.martini_m)
    assert values["DPA Fridman estándar a 3 kn"] == pytest.approx(
        float(np.asarray(result.spread.fridman.dpa_std_m)[i])
    )


def test_floats_ballast_table(result: DesignResult) -> None:
    values = kv(floats_ballast_table(result))
    assert values["Cantidad de boyas"] == result.floats.count
    assert values["Flotación total de la clase (Ffz)"] == pytest.approx(
        result.floats.flotation_total_kgf
    )
    assert values["Lastre mínimo"] == pytest.approx(result.ballast.limits.min_kg)
    assert values["Lastre máximo"] == pytest.approx(result.ballast.limits.max_kg)


def test_warp_and_demand_tables(result: DesignResult) -> None:
    values = kv(warp_table(result))
    sel = result.warps.selection
    assert values["Cable seleccionado"] == sel.id
    assert values["Rotura mínima requerida"] == pytest.approx(
        result.warps.loads.min_breaking_load_kgf
    )
    assert values["Cumple la rotura mínima"] == ("sí" if sel.satisfies_breaking_load else "no")
    assert values["Divergencia (δ2)"] == pytest.approx(result.warps.angles.divergence_deg)
    assert values["Ø Pérez Águila (buque de diseño)"] == pytest.approx(
        result.warps.diameter_aguila_mm
    )
    d = demand_table(result)
    np.testing.assert_allclose(np.array(d.column("total_std"), float), result.warps.total.std)
    np.testing.assert_allclose(np.array(d.column("total_mod"), float), result.warps.total.mod)
    np.testing.assert_allclose(np.array(d.column("rw"), float), result.warps.drag_kgf)
    np.testing.assert_allclose(np.array(d.column("ft"), float), result.power.ft_kgf)


def test_speed_window_table(result: DesignResult) -> None:
    t = speed_window_table(result)
    assert len(t.rows) == len(result.performance.windows) == 4
    maxes = [w.max_speed_kn for w in result.performance.windows.values()]
    for got, exp in zip(t.column("max_speed_kn"), maxes, strict=True):
        assert got == (None if exp is None else pytest.approx(exp))
    assert t.column("design").count("sí") == 1


def test_errata_table_modes(result: DesignResult, result_excel: DesignResult) -> None:
    corr = errata_table(result)
    exc = errata_table(result_excel)
    assert corr.column("key") == [e.key for e in ERRATA] == exc.column("key")
    for key, s_corr, s_exc in zip(
        corr.column("key"), corr.column("status"), exc.column("status"), strict=True
    ):
        if key in ERRATA_FIXED_TREATMENT:
            assert s_corr == s_exc
        else:
            assert (s_corr, s_exc) == ("corregida", "reproducida")
    assert "excel" in exc.title and "corrected" in corr.title


def test_notes_and_all_tables(result: DesignResult) -> None:
    assert notes_table(result).column("note") == result.notes
    keys = [t.key for t in all_tables(result)]
    assert len(keys) == len(set(keys))
    assert {"resumen", "panos_std", "panos_mod", "resistencia_std", "resistencia_mod"} <= set(keys)
    assert all(len(k) <= 31 for k in keys)
    for t in all_tables(result):
        for row in t.rows:
            for cell in row:
                assert not (isinstance(cell, float) and math.isnan(cell))


def test_all_tables_without_modified() -> None:
    r = run(make_case(modified=False))
    keys = [t.key for t in all_tables(r)]
    assert "panos_mod" not in keys and "resistencia_mod" not in keys
