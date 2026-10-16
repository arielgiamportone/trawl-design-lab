"""`trawlkit.dimensions` contra 'Dimensiones de la Red' (tests/golden) y Cab!J5."""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest

from tests.golden_utils import (
    RTOL_TRUNCATED,
    assert_close,
    golden,
    golden_entry,
    golden_series,
)
from trawlkit.compat import Compat
from trawlkit.dimensions import (
    NetDimensions,
    body_length_no_bag_m,
    compute,
    corrected_piece_m,
    excel_mid_truncate,
    fc_body_ratio,
    fishing_circle_m,
    footrope_bosom_piece_m,
    footrope_length_m,
    footrope_wing_piece_m,
    headrope_bosom_piece_m,
    headrope_length_m,
    headrope_wing_piece_m,
    length_factor,
    load_nomura_reference,
    max_circumference_m,
    nomura_ratios,
    wingtip_reinforcement_m,
    wingtip_reinforcement_rope_m,
)
from trawlkit.io import load_net
from trawlkit.net import analyse

SHEET = "dimensiones_de_la_red"


@pytest.fixture(scope="module")
def std() -> NetDimensions:
    return compute(load_net("fao_a3_standard"), compat=Compat.EXCEL)


@pytest.fixture(scope="module")
def mod() -> NetDimensions:
    return compute(load_net("fao_a3_modified"), compat=Compat.EXCEL)


@pytest.fixture(scope="module")
def std_corrected() -> NetDimensions:
    return compute(load_net("fao_a3_standard"))


def ids_for(keys: list[str]) -> list[str]:
    return [f"{k}[{golden_entry(SHEET, k)['cell']}]" for k in keys]


SCALAR_CASES: dict[str, Callable[[NetDimensions, NetDimensions], float]] = {
    "headrope_m": lambda s, m: s.headrope_m,
    "footrope_m": lambda s, m: s.footrope_m,
    "total_length_belly_std_m": lambda s, m: s.total_length_m,
    "total_length_belly_mod_m": lambda s, m: m.total_length_m,
    "total_length_back_no_bag_std_m": lambda s, m: s.body_length_no_bag_m,
    "total_length_back_no_bag_mod_m": lambda s, m: m.body_length_no_bag_m,
    "circumference_m": lambda s, m: s.max_circumference_m,
    "upper_wing_m": lambda s, m: s.upper_wing_m,
    "lower_wing_m": lambda s, m: s.lower_wing_m,
    "back_belly_m": lambda s, m: s.back_belly_m,
    "bag_m": lambda s, m: s.bag_m,
    "square_m": lambda s, m: s.square_m,
    "cut_angle_deg": lambda s, m: s.cut_angle_deg,
    "filtration_index_std": lambda s, m: s.filtration_index,
    "filtration_index_mod": lambda s, m: m.filtration_index,
    "solid_surface_std_m2": lambda s, m: s.solid_surface_m2,
    "solid_surface_mod_m2": lambda s, m: m.solid_surface_m2,
    "working_surface_std_m2": lambda s, m: s.working_surface_m2,
    "working_surface_mod_m2": lambda s, m: m.working_surface_m2,
    "net_weight_std_kg": lambda s, m: s.net_weight_kg,
    "net_weight_mod_kg": lambda s, m: m.net_weight_kg,
    "square_depth_meshes": lambda s, m: 40,  # F85 =P!R275: entrada (E.meshes_depth)
    "square_mesh_mm": lambda s, m: 60,  # F86 =P!Q275: entrada (E.mesh_mm)
    "length_factor": lambda s, m: s.length_factor,
    "fishing_circle_m": lambda s, m: s.fishing_circle_m,
    "body_length_m": lambda s, m: s.body_length_m,
    "fc_body_ratio": lambda s, m: s.fc_body_ratio,
    "headrope_wing_m": lambda s, m: s.headrope.wing_m,
    "headrope_bosom_m": lambda s, m: s.headrope.bosom_m,
    "headrope_wing_hanging": lambda s, m: s.headrope.wing_hanging,
    "headrope_bosom_hanging": lambda s, m: s.headrope.bosom_hanging,
    "headrope_wing_corrected_m": lambda s, m: s.headrope.wing_corrected_m,
    "headrope_bosom_corrected_m": lambda s, m: s.headrope.bosom_corrected_m,
    "footrope_wing_m": lambda s, m: s.footrope.wing_m,
    "footrope_bosom_m": lambda s, m: s.footrope.bosom_m,
    "footrope_wing_hanging": lambda s, m: s.footrope.wing_hanging,
    "footrope_bosom_hanging": lambda s, m: s.footrope.bosom_hanging,
    "footrope_wing_corrected_m": lambda s, m: s.footrope.wing_corrected_m,
    "footrope_bosom_corrected_m": lambda s, m: s.footrope.bosom_corrected_m,
    "wingtip_reinforcement_m": lambda s, m: s.wingtip_reinforcement_m,
    "wingtip_hanging": lambda s, m: s.wingtip_hanging,
}


@pytest.mark.parametrize("key", list(SCALAR_CASES), ids=ids_for(list(SCALAR_CASES)))
def test_scalar_excel(key: str, std: NetDimensions, mod: NetDimensions) -> None:
    """Modo EXCEL con rtol 1e-6: el burlón (F46) y sus derivados (D89, C124:C126) reproducen el
    truncado de MID() exactamente, por lo que no hace falta la tolerancia RTOL_TRUNCATED."""
    assert_close(SCALAR_CASES[key](std, mod), golden(SHEET, key), where=key)


def test_square_inputs_match_spec(std: NetDimensions) -> None:
    e = next(p for p in load_net("fao_a3_standard").panels if p.id == "E")
    assert e.meshes_depth == golden(SHEET, "square_depth_meshes")
    assert e.mesh_mm == golden(SHEET, "square_mesh_mm")


def test_nomura_ratio_fao_a3_series(std: NetDimensions) -> None:
    """C124:C132."""
    labels, values = golden_series(SHEET, "nomura_ratio_fao_a3")
    assert list(std.nomura_ratios) == labels
    assert_close([std.nomura_ratios[k] for k in labels], values)


def test_nomura_ratio_reference_series(std: NetDimensions) -> None:
    """E124:E132 = 'Tablas de Referencias'!D16:L16."""
    labels, values = golden_series(SHEET, "nomura_ratio_reference")
    assert_close([std.nomura_reference[k] for k in labels], values)
    assert load_nomura_reference() == std.nomura_reference


def test_wingtip_reinforcement_rope_cables_j5(std: NetDimensions) -> None:
    """'Cables Y Cabulleria'!J5 =ROUNDUP(4*C155,1)."""
    assert_close(
        std.wingtip_reinforcement_rope_m, golden("cables_y_cabulleria", "wingtip_reinforcement_m")
    )
    assert wingtip_reinforcement_rope_m(2.0) == 8.0 and wingtip_reinforcement_rope_m(2.01) == 8.1


def test_modified_variant_specifics(mod: NetDimensions) -> None:
    assert mod.bag_m == 9.0  # I': 300 mallas de 30 mm
    assert_close(mod.headrope_m, golden(SHEET, "headrope_m"))
    assert_close(mod.footrope_m, golden(SHEET, "footrope_m"))
    assert_close(
        mod.nomura_ratios["l/m"], golden(SHEET, "headrope_m") / golden(SHEET, "footrope_m")
    )


# ------------------------------------------------------------------------------------------
# Funciones puras (celdas representativas)
# ------------------------------------------------------------------------------------------


def test_pure_rope_pieces() -> None:
    assert_close(headrope_wing_piece_m(36, 120, 80), golden(SHEET, "headrope_wing_m"))  # C140
    assert_close(
        headrope_bosom_piece_m(412, 60, 117, 80), golden(SHEET, "headrope_bosom_m")
    )  # F140
    assert_close(corrected_piece_m(12.48, 1.05), golden(SHEET, "headrope_wing_corrected_m"))  # C143
    assert_close(headrope_length_m(13.104, 2.49), golden(SHEET, "headrope_m"))  # F45
    assert_close(
        footrope_wing_piece_m(36, 120, 80, 40, 60), golden(SHEET, "footrope_wing_m")
    )  # C148
    assert_close(
        footrope_bosom_piece_m(372, 60, 143, 60), golden(SHEET, "footrope_bosom_m")
    )  # F148
    assert_close(wingtip_reinforcement_m(36, 80), golden(SHEET, "wingtip_reinforcement_m"))  # C155


def test_pure_lengths_and_ratios() -> None:
    assert_close(max_circumference_m(372, 60, 372, 60), golden(SHEET, "circumference_m"))  # F49
    assert_close(fishing_circle_m(372, 372, 60), golden(SHEET, "fishing_circle_m"))  # D97
    assert_close(length_factor(28.698, 33.3, 40, 60), golden(SHEET, "length_factor"))  # D89
    assert_close(fc_body_ratio(44.64, 17.8), golden(SHEET, "fc_body_ratio"))  # D109
    ratios = nomura_ratios(28.698, 33.3, 42.68, 44.64, 12.48, 14.88, 12.6, 8.0)
    assert_close(list(ratios.values()), golden_series(SHEET, "nomura_ratio_fao_a3")[1])


# ------------------------------------------------------------------------------------------
# Erratas en modo CORRECTED
# ------------------------------------------------------------------------------------------


def test_excel_mid_truncate() -> None:
    assert excel_mid_truncate(15.624000000000002, 4) == 15.6
    assert excel_mid_truncate(2.1414, 3) == 2.1
    assert excel_mid_truncate(123.456, 4) == 123.0  # "123." → 123
    assert excel_mid_truncate(123.456, 5) == 123.4


def test_footrope_mid_truncation_corrected(
    std: NetDimensions, std_corrected: NetDimensions
) -> None:
    """F46: EXCEL 2·15.6 + 2.1 = 33.3; CORRECTED 2·15.624 + 2.1414 = 33.3894 (> 33.3).

    La referencia 33.389 del enunciado está redondeada a 3 decimales: rtol 1e-3 por el truncado.
    """
    wing_c, bosom_c = std.footrope.wing_corrected_m, std.footrope.bosom_corrected_m
    assert_close(footrope_length_m(wing_c, bosom_c, Compat.EXCEL), 33.3)
    assert_close(footrope_length_m(wing_c, bosom_c), 2 * wing_c + bosom_c)
    assert std_corrected.footrope_m > std.footrope_m
    assert_close(std_corrected.footrope_m, 33.389, rtol=RTOL_TRUNCATED)
    assert_close(std_corrected.footrope_m, 33.3894)
    # Arrastre a D89 y a las proporciones de Nomura que usan el nombre 'Burlon'
    assert std_corrected.length_factor < std.length_factor
    assert_close(std_corrected.length_factor, (28.698 + 4.8) / 33.3894)
    assert std_corrected.nomura_ratios["l/m"] < std.nomura_ratios["l/m"]
    assert std_corrected.headrope_m == std.headrope_m


def test_mod_length_wrong_rows_corrected() -> None:
    """G48 suma el plan inferior (B, D, F, G, H) en vez del dorso (A, C, E, G, H)."""
    upper, lower = [2.88, 9.6, 2.4, 12.6, 5.2], [2.88, 9.6, 2.4, 12.6, 5.2]
    assert body_length_no_bag_m(upper, lower, modified=True, compat=Compat.EXCEL) == 32.68
    # Con planos de distinto largo, sólo el modo EXCEL de la red modificada cambia.
    lower2 = [2.88, 9.6, 3.0, 12.6, 5.2]
    assert body_length_no_bag_m(upper, lower2, modified=True, compat=Compat.EXCEL) == pytest.approx(
        33.28
    )
    assert body_length_no_bag_m(upper, lower2, modified=True) == pytest.approx(32.68)
    assert body_length_no_bag_m(upper, lower2, modified=False, compat=Compat.EXCEL) == 32.68

    spec = load_net("fao_a3_modified")
    panels = [p.model_copy(update={"meshes_depth": 100}) if p.id == "D" else p for p in spec.panels]
    spec2 = spec.model_copy(update={"panels": panels})
    excel = compute(spec2, compat=Compat.EXCEL)
    corrected = compute(spec2)
    assert excel.body_length_no_bag_m == pytest.approx(32.68 - 1.6)  # plan inferior: D 120→100
    assert corrected.body_length_no_bag_m == pytest.approx(32.68)  # dorso, sin cambios
    assert corrected.body_length_no_bag_m > excel.body_length_no_bag_m
    # la columna estándar no se ve afectada aunque cambie el plan inferior
    assert compute(
        spec2, compat=Compat.EXCEL, modified=False
    ).body_length_no_bag_m == pytest.approx(32.68)


# ------------------------------------------------------------------------------------------
# Extremo a extremo
# ------------------------------------------------------------------------------------------


def test_end_to_end_standard_net() -> None:
    spec = load_net("fao_a3_standard")
    geo = analyse(spec, Compat.EXCEL)
    assert_close(geo.solid_surface_m2, 40.89506)
    assert_close(geo.working_surface_m2, 315.566, rtol=1e-5)
    assert_close(geo.filtration_index, 0.0212778, rtol=1e-5)
    assert_close(geo.weight_air_kg, 28.27, rtol=1e-4)
    dims = compute(spec, geo, Compat.EXCEL)
    assert_close(dims.headrope_m, 28.698)
    assert_close(dims.footrope_m, 33.3)
    assert_close(compute(spec).footrope_m, 33.389, rtol=RTOL_TRUNCATED)  # MID: ver test anterior
    assert dims.solid_surface_m2 == geo.solid_surface_m2
    doc = json.loads(json.dumps(dims.to_dict()))
    assert doc["compat"] == "excel" and doc["headrope"]["length_m"] == 28.698
