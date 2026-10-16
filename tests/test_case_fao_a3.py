"""Caso FAO A-3 extremo a extremo (`trawlkit.model.run`) contra los golden en modo EXCEL.

Se corre la red estándar + modificada para los buques de 150 y 180 BHP. Como el libro calcula
ambos buques lado a lado (Ffz promedia la flotación de los dos; el cable se dimensiona con el
NHP de 180), cada corrida lleva al otro buque en ``class_vessels``. Todas las comparaciones son a
``rtol=1e-6``: en modo EXCEL el motor reproduce exactamente el truncado ``MID()`` del burlón, por
lo que no hace falta la tolerancia ``RTOL_TRUNCATED``.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import numpy as np
import pytest

from tests.golden_utils import SPEEDS_KN, assert_close, golden
from trawlkit.compat import Compat
from trawlkit.io import load_doors, load_net, load_vessels
from trawlkit.model import DesignCase, DesignResult, run

DIM = "dimensiones_de_la_red"
POT = "potencia_disponible_arrastre_ok"
RES = "resistencia_de_la_red"
MEC = "mecanica_de_la_red"
PORT = "portones_y_aparejamiento"
FLOT = "flotacion_y_lastre"
REM = "cables_de_remolque"
CAB = "cables_y_cabulleria"


def fao_a3_case(bhp: int, compat: Compat = Compat.EXCEL) -> DesignCase:
    vessels = {v.id: v for v in load_vessels().vessels}
    design = vessels[f"fao_a3_{bhp}hp"]
    others = tuple(v for v in vessels.values() if v.id != design.id)
    return DesignCase(
        net=load_net("fao_a3_standard"),
        vessel=design,
        door=load_doors().doors[0],
        net_modified=load_net("fao_a3_modified"),
        class_vessels=others,
        speeds_kn=tuple(SPEEDS_KN),
        compat=compat,
    )


@pytest.fixture(scope="module")
def r150() -> DesignResult:
    return run(fao_a3_case(150))


@pytest.fixture(scope="module")
def r180() -> DesignResult:
    return run(fao_a3_case(180))


# ---------------------------------------------------------------------------------------------
# Claves comunes a ambos buques (no dependen del BHP)
# ---------------------------------------------------------------------------------------------

COMMON: list[tuple[str, str, Callable[[DesignResult], Any]]] = [
    # 'Dimensiones de la Red'!F45:F71
    (DIM, "headrope_m", lambda r: r.dimensions.std.headrope_m),
    (DIM, "footrope_m", lambda r: r.dimensions.std.footrope_m),
    (DIM, "cut_angle_deg", lambda r: r.dimensions.std.cut_angle_deg),
    (DIM, "filtration_index_std", lambda r: r.geometry.std.filtration_index),
    (DIM, "filtration_index_mod", lambda r: r.geometry.mod.filtration_index),
    (DIM, "solid_surface_std_m2", lambda r: r.geometry.std.solid_surface_m2),
    (DIM, "solid_surface_mod_m2", lambda r: r.geometry.mod.solid_surface_m2),
    (DIM, "working_surface_std_m2", lambda r: r.geometry.std.working_surface_m2),
    (DIM, "working_surface_mod_m2", lambda r: r.geometry.mod.working_surface_m2),
    (DIM, "net_weight_std_kg", lambda r: r.geometry.std.weight_air_kg),
    (DIM, "net_weight_mod_kg", lambda r: r.geometry.mod.weight_air_kg),
    (DIM, "vertical_opening_m", lambda r: r.spread.vertical.suzuki_m),
    (DIM, "horizontal_opening_m", lambda r: r.spread.horizontal_opening_m),
    (DIM, "working_depth_m", lambda r: r.case.working_depth_m),
    (DIM, "dan_leno_m", lambda r: r.case.dan_leno_m),
    (DIM, "sweeps_m", lambda r: r.bridles.sweeps_m),
    (DIM, "crowfoot_m", lambda r: r.bridles.crowfoot.length_m),
    (DIM, "crowfoot_extension_m", lambda r: r.bridles.crowfoot.extension_m),
    (DIM, "upper_bridle_std_m", lambda r: r.bridles.lengths.upper_m),
    (DIM, "lower_bridle_std_m", lambda r: r.bridles.lengths.lower_m),
    (DIM, "warp_diameter_mm", lambda r: r.warps.selection.diameter_mm),
    (DIM, "warp_length_m", lambda r: r.warps.warp_m),
    (DIM, "total_length_belly_std_m", lambda r: r.dimensions.std.total_length_m),
    (DIM, "total_length_belly_mod_m", lambda r: r.dimensions.mod.total_length_m),
    # 'Resistencia de la RED' N302:N310 / N317:N325 (RN de diseño) y Dickson E282:F290
    (RES, "aberdeen_demersal_rn_std_t", lambda r: r.drag.table.design_rn("std")),
    (RES, "aberdeen_demersal_rn_mod_t", lambda r: r.drag.table.design_rn("mod")),
    (RES, "dickson_rn_std_t", lambda r: r.drag.table.std["dickson"]),
    (RES, "dickson_rn_mod_t", lambda r: r.drag.table.mod["dickson"]),
    (RES, "summary_average_std_t", lambda r: r.drag.average.std),
    (RES, "summary_average_mod_t", lambda r: r.drag.average.mod),
    # 'Mecánica de la Red': DPA, AH, AV
    (MEC, "warp_length_m", lambda r: r.rigging.towing.warp_m),
    (MEC, "net_length_working_m", lambda r: r.rigging.towing.net_length_working_m),
    (MEC, "dpa_fridman_std_m", lambda r: r.spread.fridman.dpa_std_m),
    (MEC, "dpa_fridman_mod_m", lambda r: r.spread.fridman.dpa_mod_m),
    (MEC, "door_spread_from_dpa_m", lambda r: r.spread.table.door_spread_from_dpa_m),
    (MEC, "dpa_geometric_std_m", lambda r: r.spread.dpa_geometric_m),
    (MEC, "dpa_geometric_working_m", lambda r: r.spread.dpa_working_m),
    (MEC, "dpa_from_cut_angle_m", lambda r: r.spread.dpa_cut_angle_m),
    (MEC, "flotation_total_kgf", lambda r: r.spread.vertical.flotation_total_kgf),
    (MEC, "headrope_sag_m", lambda r: r.rigging.headrope_sag_m),
    (MEC, "av_martini_m", lambda r: r.spread.vertical.martini_m),
    (MEC, "av_prado_low_opening_m", lambda r: r.spread.vertical.prado_m["low_opening"]),
    (MEC, "av_izzo_7pct_m", lambda r: r.spread.vertical.izzo_m[3]),
    (MEC, "av_fridman_std_m", lambda r: r.spread.vertical.fridman.std.av_m),
    (MEC, "av_fridman_mod_m", lambda r: r.spread.vertical.fridman.mod.av_m),
    (MEC, "av_fridman_avg_std_m", lambda r: r.spread.vertical.fridman.std.av_average_m),
    (MEC, "dpa_over_l", lambda r: r.spread.dpa_over_headrope),
    # 'Portones y aparejamiento'
    (PORT, "door_spread_m", lambda r: r.doors.spread_m),
    (PORT, "door_spread_corrected_m", lambda r: r.doors.spread_corrected_m),
    (PORT, "rob_kgf", lambda r: r.doors.forces.drag_kgf),
    (PORT, "door_spreading_force_kgf", lambda r: r.doors.forces.lift_kgf),
    (PORT, "door_force_kgf", lambda r: r.doors.force_kgf),
    (PORT, "door_moment_kgf_cm", lambda r: r.doors.moments.door_moment_kgf_cm),
    (PORT, "sweeps_dremiere_m", lambda r: r.bridles.sweeps_dremiere_m),
    (PORT, "sweeps_martini_m", lambda r: r.bridles.sweeps_martini_m),
    (PORT, "sweeps_no_triangle_m", lambda r: r.bridles.sweeps_no_triangle_m),
    (PORT, "sweeps_triangle_m", lambda r: r.bridles.sweeps_triangle_m),
    (PORT, "bridle_attack_angle_deg", lambda r: r.bridles.attack_angle_deg),
    (PORT, "required_door_area_overall_m2", lambda r: r.doors.required_area_per_door_class_m2),
    # 'Flotación y Lastre' (independiente del buque)
    (FLOT, "flotation_koyama_kgf", lambda r: r.floats.koyama_kgf),
    (FLOT, "beta_deg", lambda r: r.floats.beta_deg),
    (FLOT, "headrope_weight_water_kgf", lambda r: r.floats.headrope_weight_water_kgf),
    (FLOT, "footrope_weight_water_kgf", lambda r: r.ballast.footrope_weight_water_kgf),
    (FLOT, "ballast_koyama_kg", lambda r: r.ballast.koyama_kg),
    (FLOT, "float_count", lambda r: r.floats.count),
    (FLOT, "float_diameter_mm", lambda r: r.floats.diameter_mm),
    (FLOT, "float_spacing_even_m", lambda r: r.floats.distribution.spacing_even_m),
    (FLOT, "float_reynolds", lambda r: r.floats.reynolds),
    (FLOT, "float_drag_kgf", lambda r: r.floats.drag_kgf),
    (
        FLOT,
        "flotation_fridman_avg_150_kgf",
        lambda r: r.floats.class_fridman_average_kgf["fao_a3_150hp"],
    ),
    (
        FLOT,
        "flotation_fridman_avg_180_kgf",
        lambda r: r.floats.class_fridman_average_kgf["fao_a3_180hp"],
    ),
    # 'Cables de Remolque' (el libro dimensiona el cable con 180 HP para ambos buques)
    (REM, "dpa_a_m", lambda r: r.warps.dpa_a_m),
    (REM, "dpa_b_m", lambda r: r.warps.dpa_b_m),
    (REM, "warp_divergence_deg", lambda r: r.warps.angles.divergence_deg),
    (REM, "bridle_divergence_deg", lambda r: r.warps.angles.bridle_divergence_deg),
    (REM, "warp_declination_deg", lambda r: r.warps.angles.declination_deg),
    (REM, "warp_diameter_aguila_180_mm", lambda r: r.warps.diameter_mm),
    (REM, "warp_cd", lambda r: r.warps.cd),
    (REM, "warp_drag_2_kgf", lambda r: r.warps.drag_kgf),
    (REM, "total_drag_std_kgf", lambda r: r.warps.total.std),
    (REM, "total_drag_mod_kgf", lambda r: r.warps.total.mod),
    (REM, "warp_drag_cylinder_2_kgf", lambda r: r.warps.cylinder.drag_two_kgf),
    (REM, "warp_total_weight_water_kg", lambda r: r.warps.weight.total_water_kg),
    (REM, "warp_working_load_kgf", lambda r: r.warps.loads.working_load_kgf),
    (REM, "warp_min_breaking_load_kgf", lambda r: r.warps.loads.min_breaking_load_kgf),
    # 'Cables Y Cabulleria'
    (CAB, "warp_diameter_mm", lambda r: r.warps.selection.diameter_mm),
    (CAB, "warp_strength_t", lambda r: r.warps.selection.breaking_load_t),
    (CAB, "warp_quantity_m", lambda r: r.warps.quantity_m),
    (CAB, "headrope_rope_kg_per_m", lambda r: r.floats.headrope_rope.weight_kg_per_m),
    (CAB, "footrope_rope_kg_per_m", lambda r: r.ballast.footrope_rope.weight_kg_per_m),
]

#: Claves propias de cada bloque de buque (sufijo 150/180 en el golden).
PER_VESSEL: list[tuple[str, str, Callable[[DesignResult], Any]]] = [
    (POT, "fridman_summary_fixed_{hp}_kgf", lambda r: r.power.fridman.ft_fixed_pitch_kgf),
    (
        POT,
        "fridman_summary_variable_nozzle_{hp}_kgf",
        lambda r: r.power.fridman.ft_variable_pitch_nozzle_kgf,
    ),
    (POT, "koyama_ehp_{hp}_hp", lambda r: r.power.koyama_ehp_hp),
    (PORT, "rob_20pct_{hp}_kgf", lambda r: r.doors.rob_share_kgf),
    (PORT, "rob_30pct_{hp}_kgf", lambda r: r.doors.rob_shares_kgf["30pct"]),
    (PORT, "required_door_area_{hp}_m2", lambda r: r.doors.required_area_m2),
    (PORT, "required_door_area_each_{hp}_m2", lambda r: r.doors.required_area.per_door_m2),
    (FLOT, "flotation_prado_{hp}_kgf", lambda r: r.floats.prado_kgf),
    (FLOT, "flotation_total_std_{hp}_kgf", lambda r: r.floats.fridman.std.total_kgf),
    (FLOT, "flotation_total_mod_{hp}_kgf", lambda r: r.floats.fridman.mod.total_kgf),
    (FLOT, "flotation_fridman_avg_{hp}_kgf", lambda r: r.floats.fridman_average_kgf),
    (FLOT, "flotation_design_{hp}_kgf", lambda r: r.floats.fridman_average_kgf),
    (FLOT, "float_count_{hp}", lambda r: r.floats.catalogue_counts),
    (FLOT, "ballast_prado_{hp}_kg", lambda r: r.ballast.prado_kg),
    (FLOT, "ballast_std_{hp}_kg", lambda r: r.ballast.fridman.std),
    (FLOT, "ballast_mod_{hp}_kg", lambda r: r.ballast.fridman.mod),
    (REM, "warp_diameter_ehp_{hp}_mm", lambda r: r.warps.diameter_ehp_mm),
    (REM, "warp_diameter_aguila_{hp}_mm", lambda r: r.warps.diameter_aguila_mm),
]

#: Claves que sólo existen para el bloque de 150 HP (la hoja no las repite para 180).
ONLY_150: list[tuple[str, str, Callable[[DesignResult], Any]]] = [
    (DIM, "flotation_total_kgf", lambda r: r.floats.flotation_rounded_kgf),
    (FLOT, "flotation_total_rounded_kgf", lambda r: r.floats.flotation_rounded_kgf),
    (FLOT, "ballast_min_150_kg", lambda r: r.ballast.limits.min_kg),
    (FLOT, "ballast_max_150_kg", lambda r: r.ballast.limits.max_kg),
    (FLOT, "adjust_chain_weight_kg", lambda r: r.ballast.adjust_chain_weight_kg),
    (FLOT, "ballast_even_kg_m", lambda r: r.ballast.even_kg_m),
    (FLOT, "ballast_min_wings_kg_m", lambda r: r.ballast.distribution_min.wings_kg_m),
    (FLOT, "ballast_max_wings_kg_m", lambda r: r.ballast.distribution_max.wings_kg_m),
    (FLOT, "floats_on_wings", lambda r: r.floats.distribution.on_wings),
    (FLOT, "float_spacing_front_fifth_m", lambda r: r.floats.distribution.spacing_front_fifth_m),
    (REM, "warp_drag_5pct_fixed_kgf", lambda r: r.warps.shares_kgf["fixed_pitch_5pct"]),
    (
        REM,
        "warp_drag_10pct_variable_kgf",
        lambda r: r.warps.shares_kgf["variable_pitch_nozzle_10pct"],
    ),
]


@pytest.mark.parametrize("hp", [150, 180])
@pytest.mark.parametrize(("sheet", "key", "get"), COMMON, ids=[f"{s}:{k}" for s, k, _ in COMMON])
def test_common_keys(
    hp: int, sheet: str, key: str, get: Callable[[DesignResult], Any], request: Any
) -> None:
    r = request.getfixturevalue(f"r{hp}")
    assert_close(get(r), golden(sheet, key), where=f"{sheet}:{key} ({hp} HP)")


@pytest.mark.parametrize("hp", [150, 180])
@pytest.mark.parametrize(
    ("sheet", "key", "get"), PER_VESSEL, ids=[f"{s}:{k}" for s, k, _ in PER_VESSEL]
)
def test_per_vessel_keys(
    hp: int, sheet: str, key: str, get: Callable[[DesignResult], Any], request: Any
) -> None:
    r = request.getfixturevalue(f"r{hp}")
    k = key.format(hp=hp)
    assert_close(get(r), golden(sheet, k), where=f"{sheet}:{k}")


@pytest.mark.parametrize(
    ("sheet", "key", "get"), ONLY_150, ids=[f"{s}:{k}" for s, k, _ in ONLY_150]
)
def test_150_only_keys(
    r150: DesignResult, sheet: str, key: str, get: Callable[[DesignResult], Any]
) -> None:
    assert_close(get(r150), golden(sheet, key), where=f"{sheet}:{key}")


def test_summary_reproduces_dimensiones_f55_f71(r150: DesignResult) -> None:
    s = r150.summary()
    expected = {
        "cut_angle_deg": "cut_angle_deg",
        "filtration_index": "filtration_index_std",
        "solid_surface_m2": "solid_surface_std_m2",
        "working_surface_m2": "working_surface_std_m2",
        "net_weight_kg": "net_weight_std_kg",
        "vertical_opening_m": "vertical_opening_m",
        "horizontal_opening_m": "horizontal_opening_m",
        "working_depth_m": "working_depth_m",
        "flotation_total_kgf": "flotation_total_kgf",
        "dan_leno_m": "dan_leno_m",
        "sweeps_m": "sweeps_m",
        "crowfoot_m": "crowfoot_m",
        "crowfoot_extension_m": "crowfoot_extension_m",
        "upper_bridle_m": "upper_bridle_std_m",
        "lower_bridle_m": "lower_bridle_std_m",
        "warp_diameter_mm": "warp_diameter_mm",
        "warp_length_m": "warp_length_m",
        "headrope_m": "headrope_m",
        "footrope_m": "footrope_m",
    }
    for skey, gkey in expected.items():
        assert_close(s[skey], golden(DIM, gkey), where=skey)
    for key in (
        "rn_std_3_5kn_kgf",
        "rob_3_5kn_kgf",
        "float_count",
        "ballast_min_kg",
        "ballast_max_kg",
        "warp_selected",
        "max_speed_kn",
    ):
        assert key in s
    assert s["warp_selected"] == "steel_6x19_seale_12mm"
    assert s["float_count"] == 12 and s["ballast_min_kg"] == 27 and s["ballast_max_kg"] == 42
    assert_close(s["rn_std_3_5kn_kgf"], golden(REM, "rn_std_kgf")[5])
    assert_close(s["warp_min_breaking_load_kgf"], golden(REM, "warp_min_breaking_load_kgf"))


def test_speed_window_matches_excel_comparison(r150: DesignResult) -> None:
    w = r150.performance.design
    assert_close(w.available_kgf, golden(REM, "fridman_ft_fixed_150_kgf"))
    assert_close(w.demand_kgf, golden(REM, "total_drag_std_kgf"))
    assert w.max_speed_kn is not None and 2.0 < w.max_speed_kn < 3.0
    assert set(r150.performance.windows) == {
        "fixed_pitch_std",
        "fixed_pitch_mod",
        "variable_pitch_nozzle_std",
        "variable_pitch_nozzle_mod",
    }


def test_to_dict_roundtrips_json(r150: DesignResult) -> None:
    doc = json.loads(json.dumps(r150.to_dict()))
    assert doc["case"]["net"] == "fao_a3_standard" and doc["case"]["vessel"] == "fao_a3_150hp"
    assert doc["case"]["class_vessels"] == ["fao_a3_180hp"]
    assert len(doc["drag"]["rn"]["std"]) == len(SPEEDS_KN)
    assert doc["warps"]["selection"]["diameter_mm"] == 12
    assert np.isfinite(doc["drag"]["table"]["std"]["dickson"]).all()
    assert isinstance(doc["notes"], list) and doc["notes"]


def test_excel_quirks_are_reproduced(r150: DesignResult) -> None:
    # dpa_std_uses_mod_edy: la DPA estándar se calcula con el Edy de la modificada.
    s = r150.spread.fridman
    assert_close(
        s.dpa_std_m,
        2 * 190 * 28.4316 * np.asarray(s.edy_mod) / (190 + 18 * (1 + np.asarray(s.edx_std))),
    )
    # warp_total_omits_doors: la resistencia total no incluye ROB.
    assert_close(
        r150.warps.total.std, r150.drag.rn.std + r150.floats.drag_kgf + r150.warps.drag_kgf
    )
    # warp_undersized: 12 mm (8.55 t) < 8.8 t requeridas.
    assert not r150.warps.selection.satisfies_breaking_load
    assert any(n.startswith("warp_undersized") for n in r150.notes)
