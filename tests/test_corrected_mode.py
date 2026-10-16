"""El caso FAO A-3 en `Compat.CORRECTED`: cada errata conmutable cambia en la dirección esperada
a nivel de resultado, y lo que no está afectado coincide con el modo EXCEL."""

from __future__ import annotations

import numpy as np
import pytest

from tests.golden_utils import RTOL_TRUNCATED, assert_close
from tests.test_case_fao_a3 import fao_a3_case
from trawlkit import drag
from trawlkit.compat import Compat
from trawlkit.model import DOORS_PER_RIG, DesignResult, run
from trawlkit.rigging import dpa_fridman_m, kinematic_viscosity_m2_s


@pytest.fixture(scope="module")
def excel() -> DesignResult:
    return run(fao_a3_case(150, Compat.EXCEL))


@pytest.fixture(scope="module")
def corr() -> DesignResult:
    return run(fao_a3_case(150, Compat.CORRECTED))


def test_codend_minor_side_solid_surface(excel: DesignResult, corr: DesignResult) -> None:
    assert_close(excel.geometry.std.solid_surface_m2, 40.89506)
    assert_close(corr.geometry.std.solid_surface_m2, 38.74964, rtol=1e-5)
    assert corr.summary()["solid_surface_m2"] < excel.summary()["solid_surface_m2"]
    # La RN de diseño (Aberdeen ∝ Ss) baja en la misma proporción.
    assert_close(corr.drag.rn.std / excel.drag.rn.std, np.full(9, 38.74964 / 40.89506), rtol=1e-5)


def test_footrope_mid_truncation(excel: DesignResult, corr: DesignResult) -> None:
    assert_close(excel.dimensions.std.footrope_m, 33.3)
    assert_close(corr.dimensions.std.footrope_m, 33.389, rtol=RTOL_TRUNCATED)
    assert corr.summary()["footrope_m"] > excel.summary()["footrope_m"]


def test_hamuro_and_reid_lower(excel: DesignResult, corr: DesignResult) -> None:
    for v in ("std", "mod"):
        assert (corr.drag.table.variant(v)["hamuro"] < excel.drag.table.variant(v)["hamuro"]).all()
        reid_c, reid_e = corr.drag.table.variant(v)["reid"], excel.drag.table.variant(v)["reid"]
        # A 1 kn el denominador coincide (sólo cambia Ss); por encima el corregido es menor aún.
        assert (reid_c[1:] / reid_e[1:] < reid_c[0] / reid_e[0]).all()


def test_drag_average_is_clean(corr: DesignResult) -> None:
    t = corr.drag.table
    assert_close(corr.drag.average.std, np.mean([t.std[c] for c in drag.RN_METHODS], axis=0))
    polluted = drag.average(t, Compat.EXCEL)
    assert polluted.std[0] > corr.drag.average.std[0]


def test_dpa_std_uses_standard_edy(excel: DesignResult, corr: DesignResult) -> None:
    s = corr.spread.fridman
    expected = dpa_fridman_m(
        190.0, corr.rigging.towing.net_length_working_m, s.edy_std, 18.0, s.edx_std
    )
    assert_close(s.dpa_std_m, expected)
    # Con el Edy modificado (cruce del Excel) saldría otro número.
    crossed = dpa_fridman_m(
        190.0, corr.rigging.towing.net_length_working_m, s.edy_mod, 18.0, s.edx_std
    )
    assert not np.allclose(s.dpa_std_m, crossed)
    # El valor de referencia 5.661 m a 1 kn sólo se obtiene con la RN del Excel (Ss = 40.9); en la
    # corrida corregida Ss = 38.75 cambia la RN, por lo que la DPA estándar a 1 kn es otra.
    e = excel.spread.fridman
    with_excel_rn = dpa_fridman_m(190.0, 28.4316, e.edy_std, 18.0, e.edx_std)
    assert_close(np.asarray(with_excel_rn)[0], 5.661, rtol=1e-3)
    assert np.asarray(s.dpa_std_m)[0] != pytest.approx(np.asarray(e.dpa_std_m)[0])


def test_total_demand_includes_rob_and_selects_13mm(
    excel: DesignResult, corr: DesignResult
) -> None:
    rob = DOORS_PER_RIG * np.asarray(corr.doors.forces.drag_kgf)  # par de portones
    assert_close(
        corr.warps.total.std, corr.drag.rn.std + corr.floats.drag_kgf + corr.warps.drag_kgf + rob
    )
    assert_close(corr.performance.design.demand_kgf, corr.warps.total.std)
    assert any(n.startswith("warp_total_omits_doors") for n in corr.notes)
    assert corr.warps.loads.min_breaking_load_kgf > 8550.0
    assert corr.warps.selection.diameter_mm == 13 and corr.warps.selection.satisfies_breaking_load
    assert corr.summary()["warp_selected"] == "steel_6x19_seale_13mm"
    assert excel.warps.selection.diameter_mm == 12
    assert not any(n.startswith("warp_undersized") for n in corr.notes)


def test_float_reynolds(excel: DesignResult, corr: DesignResult) -> None:
    d = corr.floats.diameter_mm / 1000.0
    assert_close(corr.floats.reynolds, excel.floats.reynolds / (np.pi * d))
    assert_close(corr.floats.reynolds, corr.case.speeds_ms * d / kinematic_viscosity_m2_s())


def test_flotation_rounding_consistent(corr: DesignResult) -> None:
    mod = np.asarray(corr.floats.fridman.mod.total_kgf)
    assert_close(mod, np.floor(mod))


def test_door_force_corrected_higher(excel: DesignResult, corr: DesignResult) -> None:
    assert (corr.doors.force_kgf > excel.doors.force_kgf).all()


def test_unaffected_outputs_identical(excel: DesignResult, corr: DesignResult) -> None:
    pairs = [
        (excel.dimensions.std.headrope_m, corr.dimensions.std.headrope_m),
        (excel.dimensions.std.max_circumference_m, corr.dimensions.std.max_circumference_m),
        (excel.dimensions.std.cut_angle_deg, corr.dimensions.std.cut_angle_deg),
        (excel.power.fridman.ft_fixed_pitch_kgf, corr.power.fridman.ft_fixed_pitch_kgf),
        (excel.power.curves.average_kgf, corr.power.curves.average_kgf),
        (excel.rigging.towing.warp_m, corr.rigging.towing.warp_m),
        (excel.rigging.headrope_sag_m, corr.rigging.headrope_sag_m),
        (excel.rigging.bridles.upper_m, corr.rigging.bridles.upper_m),
        (excel.doors.spread_m, corr.doors.spread_m),
        (excel.doors.forces.drag_kgf, corr.doors.forces.drag_kgf),
        (excel.doors.rob_share_kgf, corr.doors.rob_share_kgf),
        (excel.spread.vertical.suzuki_m, corr.spread.vertical.suzuki_m),
        (excel.spread.vertical.martini_m, corr.spread.vertical.martini_m),
        (excel.bridles.crowfoot.length_m, corr.bridles.crowfoot.length_m),
        (excel.bridles.sweeps_dremiere_m, corr.bridles.sweeps_dremiere_m),
        (excel.floats.koyama_kgf, corr.floats.koyama_kgf),
        (excel.floats.prado_kgf, corr.floats.prado_kgf),
        (excel.ballast.prado_kg, corr.ballast.prado_kg),
        (excel.warps.diameter_mm, corr.warps.diameter_mm),
        (excel.warps.angles.divergence_deg, corr.warps.angles.divergence_deg),
        (excel.warps.quantity_m, corr.warps.quantity_m),
    ]
    for e, c in pairs:
        assert_close(c, e)
    unaffected = set(drag.SUMMARY_COLUMNS) - {"hamuro", "reid"}
    # Con la misma Ss/St las demás columnas coinciden: se comprueba reconstruyendo la tabla
    # corregida con las entradas del Excel.
    rebuilt = drag.drag_table(excel.drag.inputs, excel.case.speeds, Compat.CORRECTED)
    for col in unaffected:
        assert_close(rebuilt.std[col], excel.drag.table.std[col], where=col)


# ---------------------------------------------------------------------------------------------
# Erratas warp_cd_horizontal_angle y net_weight_ignores_panel_count; columna mod fantasma
# ---------------------------------------------------------------------------------------------


def test_warp_cd_interpolation() -> None:
    from trawlkit.rigging import WARP_CD_TABLE, warp_attack_angle_deg, warp_cd

    # Fila más cercana (libro) frente a interpolación lineal acotada.
    assert warp_cd(4.3) == 0.02
    assert warp_cd(12.8) == 0.04
    assert warp_cd(15.0, interpolate=True) == pytest.approx(0.065)
    assert warp_cd(25.0, interpolate=True) == pytest.approx(0.135)
    for a, cd in WARP_CD_TABLE:
        assert warp_cd(a, interpolate=True) == pytest.approx(cd)
    assert warp_cd(-5.0, interpolate=True) == 0.02
    assert warp_cd(60.0, interpolate=True) == 0.30
    # α combina declinación y divergencia; con una de las dos nula queda la otra.
    assert warp_attack_angle_deg(12.0, 0.0) == pytest.approx(12.0)
    assert warp_attack_angle_deg(0.0, 4.3) == pytest.approx(4.3)
    assert warp_attack_angle_deg(12.06375613548482, 4.301222304670363) == pytest.approx(
        12.79689, abs=1e-5
    )


def test_warp_cd_uses_attack_angle(excel: DesignResult, corr: DesignResult) -> None:
    assert excel.warps.cd == 0.02
    assert_close(excel.warps.cd_angle_deg, excel.warps.angles.divergence_deg)
    assert corr.warps.cd > 0.02
    assert corr.warps.cd_angle_deg == pytest.approx(12.79689, abs=1e-5)
    assert corr.warps.cd == pytest.approx(0.053984, abs=1e-6)
    assert_close(corr.warps.drag_kgf / excel.warps.drag_kgf, np.full(9, corr.warps.cd / 0.02))
    assert any(n.startswith("warp_cd_horizontal_angle") for n in corr.notes)


def test_warp_drag_share_of_ft(corr: DesignResult) -> None:
    """Rw / FT (paso fijo, 150 HP) entre 2 y 3.5 kn: ≈ 1.1–4 %, por debajo de la banda 4–10 %
    de la bibliografía (Rem!D184:H184) aun con el CD corregido; se documenta, no se ajusta."""
    speeds = list(corr.case.speeds_kn)
    idx = [speeds.index(v) for v in (2.0, 2.5, 3.0, 3.5)]
    share = 100 * corr.warps.drag_kgf[idx] / corr.power.fridman.ft_fixed_pitch_kgf[idx]
    assert_close(share, [1.14, 1.85, 2.78, 3.96], rtol=5e-3)


def test_net_weight_counts_panels(excel: DesignResult, corr: DesignResult) -> None:
    g = corr.geometry.std
    assert_close(excel.geometry.std.weight_air_kg, 28.27022, rtol=1e-6)
    assert_close(g.weight_air_kg, 33.481784, rtol=1e-6)
    assert_close(corr.geometry.mod.weight_air_kg, 34.679864, rtol=1e-6)
    assert_close(g.weight_water_kg, sum(r.weight_water_kg for r in g.rows))
    assert_close(sum(g.weight_by_plane.values()), g.weight_air_kg)
    assert corr.summary()["net_weight_kg"] == pytest.approx(g.weight_air_kg)
    # Con la densidad del libro y la cantidad de paneles el total sería ≈ 45 kg (1.6× el Excel).
    with_counts = sum(r.weight_air_kg * r.row.count for r in excel.geometry.std.rows)
    assert_close(with_counts, 45.3503, rtol=1e-5)


def test_phantom_modified_serialises_null() -> None:
    from dataclasses import replace

    case = replace(fao_a3_case(150, Compat.CORRECTED), net_modified=None)
    res = run(case)
    d = res.to_dict()
    assert d["drag"]["rn"] == {"std": d["drag"]["rn"]["std"], "mod": None}
    assert d["geometry"]["mod"] is None and d["warps"]["total"]["mod"] is None
    assert d["spread"]["vertical"]["fridman"]["mod"] is None
    assert res.summary()["headrope_m"] == pytest.approx(28.698, rel=1e-6)
    # Con red modificada la columna se serializa.
    assert run(fao_a3_case(150, Compat.CORRECTED)).to_dict()["drag"]["rn"]["mod"] is not None
