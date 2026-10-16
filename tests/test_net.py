"""`trawlkit.net` contra 'Mecánica de la Red' (tests/golden/mecanica_de_la_red.json)."""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest

from tests.golden_utils import assert_close, golden, golden_entry, golden_series
from trawlkit.compat import Compat
from trawlkit.io import Plane, load_net
from trawlkit.materials import EXCEL_PI, twine_density_kg_m3
from trawlkit.net import (
    ERRATUM_CODEND_MINOR_SIDE,
    NetGeometry,
    analyse,
    filtering_coefficient,
    filtration_index,
    filtration_per_row,
    group_rows,
    panel_length_m,
    panel_weight_air_kg,
    reference_twine_weight_kg,
    solid_surface_m2,
    solidity,
    split_by_plane,
    weight_in_water_kg,
    working_surface_m2,
)

SHEET = "mecanica_de_la_red"
EXCEL_ROW_ORDER = ["A+B", "C", "E", "G", "H", "D", "F", "I", "J"]


@pytest.fixture(scope="module")
def std() -> NetGeometry:
    return analyse(load_net("fao_a3_standard"), Compat.EXCEL)


@pytest.fixture(scope="module")
def mod() -> NetGeometry:
    return analyse(load_net("fao_a3_modified"), Compat.EXCEL)


@pytest.fixture(scope="module")
def std_corrected() -> NetGeometry:
    return analyse(load_net("fao_a3_standard"), Compat.CORRECTED)


@pytest.fixture(scope="module")
def mod_corrected() -> NetGeometry:
    return analyse(load_net("fao_a3_modified"), Compat.CORRECTED)


def ids_for(keys: list[str]) -> list[str]:
    return [f"{k}[{golden_entry(SHEET, k)['cell']}]" for k in keys]


# ------------------------------------------------------------------------------------------
# Filas de paño
# ------------------------------------------------------------------------------------------


def test_group_rows_follows_sheet_order_and_counts() -> None:
    rows = group_rows(load_net("fao_a3_standard"))
    assert [r.id for r in rows] == EXCEL_ROW_ORDER
    assert [r.count for r in rows] == [4, 2, 1, 2, 2, 2, 2, 1, 1]
    ab = rows[0]
    assert ab.panel_ids == ("A", "B") and ab.planes == (Plane.UPPER, Plane.LOWER)
    assert (ab.t1, ab.t2, ab.n, ab.mesh_mm, ab.twine_mm) == (57, 3, 36, 80.0, 1.37)
    assert_close(ab.runnage_m_per_kg, 1e6 / 1280)
    mod_rows = group_rows(load_net("fao_a3_modified"))
    assert [r.id for r in mod_rows] == [*EXCEL_ROW_ORDER[:-2], "I'"]
    assert mod_rows[-1].planes == (Plane.UPPER, Plane.LOWER) and mod_rows[-1].count == 2


def test_rows_in_geometry_match_golden_labels(std: NetGeometry) -> None:
    labels, _ = golden_series(SHEET, "solid_surface_per_panel_m2")
    assert [r.row.id for r in std.rows] == labels


# ------------------------------------------------------------------------------------------
# Valores escalares (ambas variantes)
# ------------------------------------------------------------------------------------------

SCALAR_CASES: dict[str, Callable[[NetGeometry, NetGeometry], float]] = {
    "filtration_sum_twine_mm_std": lambda s, m: s.filtration.sum_twine_mm,
    "filtration_sum_mesh_mm_std": lambda s, m: s.filtration.sum_mesh_mm,
    "filtration_sum_panels_std": lambda s, m: s.filtration.sum_panels,
    "filtration_index_std": lambda s, m: s.filtration_index,
    "filtration_sum_twine_mm_mod": lambda s, m: m.filtration.sum_twine_mm,
    "filtration_sum_mesh_mm_mod": lambda s, m: m.filtration.sum_mesh_mm,
    "filtration_sum_panels_mod": lambda s, m: m.filtration.sum_panels,
    "filtration_index_mod": lambda s, m: m.filtration_index,
    "solid_surface_std_m2": lambda s, m: s.solid_surface_m2,
    "solid_surface_mod_bag_m2": lambda s, m: m.row("I'").solid_surface_m2,
    "solid_surface_mod_m2": lambda s, m: m.solid_surface_m2,
    "solid_surface_lower_mod_m2": lambda s, m: m.solid_surface_by_plane["lower"],
    "solid_surface_upper_mod_m2": lambda s, m: m.solid_surface_by_plane["upper"],
    "solid_surface_lower_std_m2": lambda s, m: s.solid_surface_by_plane["lower"],
    "solid_surface_upper_std_m2": lambda s, m: s.solid_surface_by_plane["upper"],
    "working_surface_std_m2": lambda s, m: s.working_surface_m2,
    "working_surface_mod_bag_m2": lambda s, m: m.row("I'").working_surface_m2,
    "working_surface_mod_m2": lambda s, m: m.working_surface_m2,
    "solidity_std": lambda s, m: s.solidity,
    "solidity_mod": lambda s, m: m.solidity,
    "filtering_coef_std": lambda s, m: s.filtering_coefficient,
    "filtering_coef_mod": lambda s, m: m.filtering_coefficient,
    "net_weight_air_std_kg": lambda s, m: s.weight_air_kg,
    "net_weight_water_std_kg": lambda s, m: s.weight_water_kg,
    "net_weight_air_mod_kg": lambda s, m: m.weight_air_kg,
    "net_weight_water_mod_kg": lambda s, m: m.weight_water_kg,
    "mod_bag_twine_weight_kg": lambda s, m: m.row("I'").reference_twine_weight_kg,
    "mod_bag_weight_air_kg": lambda s, m: m.row("I'").weight_air_kg,
    "mod_bag_weight_water_kg": lambda s, m: m.row("I'").weight_water_kg,
    "lower_plan_weight_std_kg": lambda s, m: s.weight_by_plane["lower"],
    "upper_plan_weight_std_kg": lambda s, m: s.weight_by_plane["upper"],
    "lower_plan_weight_mod_kg": lambda s, m: m.weight_by_plane["lower"],
    "upper_plan_weight_mod_kg": lambda s, m: m.weight_by_plane["upper"],
}


@pytest.mark.parametrize("key", list(SCALAR_CASES), ids=ids_for(list(SCALAR_CASES)))
def test_scalar_excel(key: str, std: NetGeometry, mod: NetGeometry) -> None:
    assert_close(SCALAR_CASES[key](std, mod), golden(SHEET, key), where=key)


SERIES_CASES: dict[str, Callable[[NetGeometry], list[float]]] = {
    "filtration_per_panel": lambda g: [r.filtration for r in g.rows],
    "solid_surface_per_panel_m2": lambda g: [r.solid_surface_m2 for r in g.rows],
    "panel_length_m": lambda g: [r.length_m for r in g.rows],
    "panel_u1": lambda g: [r.row.u1 for r in g.rows],
    "panel_u2": lambda g: [r.u2 for r in g.rows],
    "working_surface_per_panel_m2": lambda g: [r.working_surface_m2 for r in g.rows],
    "twine_weight_per_panel_kg": lambda g: [r.reference_twine_weight_kg for r in g.rows],
    "weight_air_per_panel_kg": lambda g: [r.weight_air_kg for r in g.rows],
    "weight_water_per_panel_kg": lambda g: [r.weight_water_kg for r in g.rows],
}


@pytest.mark.parametrize(
    "key", list(SERIES_CASES), ids=[f"{k}[{golden_entry(SHEET, k)['cells']}]" for k in SERIES_CASES]
)
def test_series_excel(key: str, std: NetGeometry) -> None:
    labels, values = golden_series(SHEET, key)
    assert [r.row.id for r in std.rows] == labels
    assert_close(SERIES_CASES[key](std), values, where=key)


# ------------------------------------------------------------------------------------------
# Funciones puras (celdas representativas de la fila A+B)
# ------------------------------------------------------------------------------------------


def test_pure_formulas_row_ab() -> None:
    ss = golden_series(SHEET, "solid_surface_per_panel_m2")[1][0]
    st = golden_series(SHEET, "working_surface_per_panel_m2")[1][0]
    sn = golden_series(SHEET, "twine_weight_per_panel_kg")[1][0]
    w_air = golden_series(SHEET, "weight_air_per_panel_kg")[1][0]
    w_water = golden_series(SHEET, "weight_water_per_panel_kg")[1][0]
    k6 = golden_series(SHEET, "filtration_per_panel")[1][0]
    assert_close(filtration_per_row(1.37, 80, 4), k6)  # K6
    assert_close(panel_length_m(36, 80), 2.88)  # M29
    assert_close(solid_surface_m2(1.37, 80, 3, 57, 36, 4), ss)  # N29
    assert_close(working_surface_m2(0.38, 80, 3, 57, 36, 4), st)  # M56
    rho = twine_density_kg_m3(1.37, 80, 1e6 / 1280, compat=Compat.EXCEL)  # F98 = P!L55
    assert_close(reference_twine_weight_kg(80, 1.37, rho, pi=EXCEL_PI), sn)  # N98
    assert_close(panel_weight_air_kg(3, 57, 36, sn), w_air)  # O98
    assert_close(weight_in_water_kg(w_air, rho), w_water)  # P98
    assert_close(solidity(40.89506, 315.5655544971113), golden(SHEET, "solidity_std"))
    assert_close(filtering_coefficient(0.1295929147437236), golden(SHEET, "filtering_coef_std"))


def test_filtration_index_function_double_count() -> None:
    """J17 =SUM(J16,J6:J12,J16): el mallero de la bolsa I' se suma dos veces en modo EXCEL."""
    d = [1.37, 1.37, 1.16, 1.16, 1.16, 1.37, 1.16, 1.37]
    ml = [80, 80, 60, 60, 40, 80, 60, 30]
    excel = filtration_index(d, ml, mod_codend_index=7, compat=Compat.EXCEL)
    corrected = filtration_index(d, ml, mod_codend_index=7)
    assert_close(excel.sum_mesh_mm, golden(SHEET, "filtration_sum_mesh_mm_mod"))
    assert_close(excel.value, golden(SHEET, "filtration_index_mod"))
    assert corrected.sum_mesh_mm == 490 and corrected.value > excel.value
    assert_close(corrected.value, sum(d) / 490)
    # sin índice de bolsa modificada el modo EXCEL no duplica nada
    assert filtration_index(d, ml, compat=Compat.EXCEL).sum_mesh_mm == 490


def test_split_by_plane_rule() -> None:
    rows = group_rows(load_net("fao_a3_standard"))
    ss = golden_series(SHEET, "solid_surface_per_panel_m2")[1]
    out = split_by_plane(rows, ss)
    assert_close(out["lower"], golden(SHEET, "solid_surface_lower_std_m2"))
    assert_close(out["upper"], golden(SHEET, "solid_surface_upper_std_m2"))


# ------------------------------------------------------------------------------------------
# Modo CORRECTED
# ------------------------------------------------------------------------------------------


def test_filtration_double_count_corrected(mod: NetGeometry, mod_corrected: NetGeometry) -> None:
    assert mod.filtration.sum_mesh_mm == 520 and mod_corrected.filtration.sum_mesh_mm == 490
    assert mod_corrected.filtration_index > mod.filtration_index
    assert_close(mod_corrected.filtration_index, 10.12 / 490)


def test_codend_minor_side_quirk_corrected(std: NetGeometry, std_corrected: NetGeometry) -> None:
    """Mec!K36 = P!H224 (N) en vez de H223 (T2): sólo en modo EXCEL."""
    assert ERRATUM_CODEND_MINOR_SIDE in " ".join(std.notes) and not std_corrected.notes
    assert std.row("I").row.t2 == 200 and std_corrected.row("I").row.t2 == 113
    assert_close(std_corrected.row("I").solid_surface_m2, 8 * 1.37 * 226 / 1000)
    assert std_corrected.solid_surface_m2 < std.solid_surface_m2
    assert_close(std_corrected.solid_surface_m2, 38.74964)
    assert std_corrected.working_surface_m2 < std.working_surface_m2
    # la bolsa modificada (I', ambos planos) está bien referenciada: no cambia
    assert_close(
        analyse(load_net("fao_a3_modified")).solid_surface_m2, golden(SHEET, "solid_surface_mod_m2")
    )


def test_twine_density_units_corrected_weights(
    std: NetGeometry, std_corrected: NetGeometry
) -> None:
    """Con la densidad corregida SN = longitud de hilo / runnage y el peso en agua usa ρ(PA)."""
    ab = std_corrected.row("A+B")
    assert_close(ab.reference_twine_weight_kg, 500 * 0.08 * 200 / (1e6 / 1280))
    # Por panel (el modo corregido multiplica cada fila por su cantidad de paneles, errata
    # net_weight_ignores_panel_count) el peso con la densidad corregida es menor.
    per_panel = sum(r.weight_air_kg / r.row.count for r in std_corrected.rows)
    assert_close(per_panel, 20.016988, rtol=1e-6)
    assert per_panel < std.weight_air_kg
    for r in std_corrected.rows:
        assert_close(r.weight_water_kg / r.weight_air_kg, 1 - 1025 / 1140)
    assert_close(
        std.row("A+B").weight_water_kg / std.row("A+B").weight_air_kg, 1 - 1025 / 1151.654109375
    )


def test_to_dict_is_json_serialisable(std: NetGeometry) -> None:
    doc = json.loads(json.dumps(std.to_dict()))
    assert doc["compat"] == "excel" and len(doc["rows"]) == 9
    assert doc["rows"][0]["row"]["planes"] == ["upper", "lower"]
    assert_close(doc["solid_surface_m2"], golden(SHEET, "solid_surface_std_m2"))
