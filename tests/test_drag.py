"""Resistencia de la red (trawlkit.drag) contra los valores golden de 'Resistencia de la RED'."""

from __future__ import annotations

import numpy as np
import pytest

from tests.golden_utils import SPEEDS_KN, assert_close, golden, golden_entry, is_static
from trawlkit import drag
from trawlkit.compat import Compat
from trawlkit.units import KNOT_TO_MS

SHEET = "resistencia_de_la_red"
V_KN = np.array(SPEEDS_KN)
V_MS = V_KN * KNOT_TO_MS


def g(key: str) -> float:
    return float(golden(SHEET, key))


def series(key: str) -> np.ndarray:
    return np.asarray(golden(SHEET, key), dtype=float)


def cell(key: str) -> str:
    return str(golden_entry(SHEET, key)["cells"])


@pytest.fixture(scope="module")
def inputs() -> drag.DragInputs:
    return drag.DragInputs(
        dl_std=g("filtration_index_std"),
        dl_mod=g("filtration_index_mod"),
        circumference_m=g("circumference_m"),
        length_with_bag_std_m=g("koyama74_length_std_m"),
        length_with_bag_mod_m=g("koyama74_length_mod_m"),
        length_without_bag_std_m=g("koyama84_length_std_m"),
        length_without_bag_mod_m=g("koyama84_length_mod_m"),
        st_std_m2=g("hamuro_st_std_m2"),
        st_mod_m2=g("hamuro_st_mod_m2"),
        ss_std_m2=g("reid_ss_std_m2"),
        ss_mod_m2=g("reid_ss_mod_m2"),
        headrope_m=g("headrope_m"),
        footrope_m=g("footrope_m"),
        alpha_deg=g("hamuro_alpha_deg"),
        ah_m=tuple(series("dickson_ah_m")),
        av_m=tuple(series("dickson_av_m")),
    )


@pytest.fixture(scope="module")
def excel_table(inputs: drag.DragInputs) -> drag.DragTable:
    return drag.drag_table(inputs, SPEEDS_KN, Compat.EXCEL)


@pytest.fixture(scope="module")
def corrected_table(inputs: drag.DragInputs) -> drag.DragTable:
    return drag.drag_table(inputs, SPEEDS_KN, Compat.CORRECTED)


# ---------------------------------------------------------------------------------------------
# Velocidades
# ---------------------------------------------------------------------------------------------


def test_speed_vectors() -> None:
    assert_close(V_KN, series("speed_kn"))
    assert_close(V_MS, series("speed_ms"))


# ---------------------------------------------------------------------------------------------
# Métodos individuales (función pura por método × variante)
# ---------------------------------------------------------------------------------------------

STD_MOD = ["std", "mod"]


def _dl(v: str) -> float:
    return g(f"filtration_index_{v}")


def _st(v: str) -> float:
    return g(f"hamuro_st_{v}_m2")


def _ss(v: str) -> float:
    return g(f"reid_ss_{v}_m2")


def _ids(prefix: str) -> list[str]:
    return [f"{prefix}_{v}:{cell(f'{prefix}_rn_{v}_t')}" for v in STD_MOD]


@pytest.mark.parametrize("variant", STD_MOD, ids=_ids("tauti_nomura_shu"))
def test_tauti_nomura_shu(variant: str) -> None:
    rn = drag.tauti_nomura_shu(_dl(variant), g("circumference_m"), V_MS)
    assert_close(rn, series(f"tauti_nomura_shu_rn_{variant}_t"))


@pytest.mark.parametrize("variant", STD_MOD, ids=_ids("tauti_headrope"))
def test_tauti_headrope(variant: str) -> None:
    rn = drag.tauti_rope(_dl(variant), g("headrope_m"), V_MS)
    assert_close(rn, series(f"tauti_headrope_rn_{variant}_t"))


@pytest.mark.parametrize("variant", STD_MOD, ids=_ids("tauti_footrope"))
def test_tauti_footrope(variant: str) -> None:
    rn = drag.tauti_rope(_dl(variant), g("footrope_m"), V_MS)
    assert_close(rn, series(f"tauti_footrope_rn_{variant}_t"))


@pytest.mark.parametrize("variant", STD_MOD, ids=_ids("koyama_1974"))
def test_koyama_1974(variant: str) -> None:
    rn = drag.koyama_1974(
        _dl(variant), g("circumference_m"), g(f"koyama74_length_{variant}_m"), V_MS
    )
    assert_close(rn, series(f"koyama_1974_rn_{variant}_t"))


@pytest.mark.parametrize("variant", STD_MOD, ids=_ids("koyama_1984"))
def test_koyama_1984(variant: str) -> None:
    rn = drag.koyama_1984(
        _dl(variant), g("circumference_m"), g(f"koyama84_length_{variant}_m"), V_KN
    )
    assert_close(rn, series(f"koyama_1984_rn_{variant}_t"))


def test_hamuro_sin_alpha_excel_matches_d113() -> None:
    assert_close(drag.hamuro_sin_alpha(g("hamuro_alpha_deg"), Compat.EXCEL), g("hamuro_sin_alpha"))


@pytest.mark.parametrize("variant", STD_MOD, ids=_ids("hamuro"))
def test_hamuro_excel(variant: str) -> None:
    # Errata hamuro_mod_uses_std_dl: ambas columnas usan $E$4 (d/l estándar).
    rn = drag.hamuro(_dl("std"), _st(variant), g("hamuro_alpha_deg"), V_MS, Compat.EXCEL)
    assert_close(rn, series(f"hamuro_rn_{variant}_t"))


@pytest.mark.parametrize(("nhp", "key"), [(150.0, "nomura_rn_150_t"), (180.0, "nomura_rn_180_t")])
def test_nomura(nhp: float, key: str) -> None:
    assert_close(drag.nomura(nhp, V_MS), series(key))


@pytest.mark.parametrize("variant", STD_MOD, ids=_ids("reid"))
def test_reid_excel(variant: str) -> None:
    rn = drag.reid(_ss(variant), V_KN, Compat.EXCEL)
    assert_close(rn, series(f"reid_rn_{variant}_t"))


@pytest.mark.parametrize("variant", STD_MOD, ids=_ids("robertson"))
def test_robertson(variant: str) -> None:
    assert_close(drag.robertson(_ss(variant), V_KN), series(f"robertson_rn_{variant}_t"))


@pytest.mark.parametrize("variant", STD_MOD, ids=_ids("maclennan"))
def test_maclennan(variant: str) -> None:
    assert_close(drag.maclennan(_ss(variant), V_KN), series(f"maclennan_rn_{variant}_t"))


@pytest.mark.parametrize("variant", STD_MOD, ids=_ids("aberdeen_demersal"))
def test_aberdeen_demersal(variant: str) -> None:
    rn = drag.aberdeen_demersal(_ss(variant), V_KN)
    assert_close(rn, series(f"aberdeen_demersal_rn_{variant}_t"))


@pytest.mark.parametrize("variant", STD_MOD, ids=_ids("aberdeen_pelagic"))
def test_aberdeen_pelagic(variant: str) -> None:
    rn = drag.aberdeen_pelagic(_ss(variant), V_KN)
    assert_close(rn, series(f"aberdeen_pelagic_rn_{variant}_t"))


@pytest.mark.parametrize("variant", STD_MOD, ids=_ids("fridman"))
def test_fridman(variant: str) -> None:
    rn = drag.fridman(_dl(variant), _st(variant), g("hamuro_alpha_deg"), V_MS)
    assert_close(rn, series(f"fridman_rn_{variant}_t"))


def test_dickson_ft2_conversion() -> None:
    assert drag.DICKSON_M2_TO_FT2 == g("dickson_m2_to_ft2")
    for v in STD_MOD:
        assert_close(_st(v) * drag.DICKSON_M2_TO_FT2, g(f"dickson_st_{v}_ft2"))


@pytest.mark.parametrize("variant", STD_MOD, ids=_ids("dickson"))
def test_dickson(variant: str) -> None:
    rn = drag.dickson(_st(variant), _dl(variant), series("dickson_ah_m"), series("dickson_av_m"))
    assert_close(rn, series(f"dickson_rn_{variant}_t"))


def test_functions_accept_scalars() -> None:
    v = 1.5
    assert drag.tauti_nomura_shu(0.02, 44.64, v * KNOT_TO_MS).shape == ()
    assert drag.reid(40.0, v, Compat.EXCEL).shape == ()
    assert_close(drag.reid(40.0, v, Compat.EXCEL), drag.reid(40.0, v, Compat.CORRECTED))
    assert_close(
        drag.aberdeen_demersal(40.0, v), 40.0 * (0.00624 + 0.00475 * v**2) / (1 + 0.0641 * v)
    )


# ---------------------------------------------------------------------------------------------
# Tabla resumen en modo EXCEL (A302:Q325 en t, A398:Q421 en kgf)
# ---------------------------------------------------------------------------------------------


def _summary_ids(unit: str) -> list[str]:
    return [
        f"{col}_{v}_{unit}:{cell(f'summary_{col}_{v}_{unit}')}"
        for col in drag.SUMMARY_COLUMNS
        for v in STD_MOD
    ]


@pytest.mark.parametrize(
    ("column", "variant"),
    [(c, v) for c in drag.SUMMARY_COLUMNS for v in STD_MOD],
    ids=_summary_ids("t"),
)
def test_summary_table_t(excel_table: drag.DragTable, column: str, variant: str) -> None:
    assert excel_table.unit == "t"
    assert_close(excel_table.variant(variant)[column], series(f"summary_{column}_{variant}_t"))


@pytest.mark.parametrize(
    ("column", "variant"),
    [(c, v) for c in drag.SUMMARY_COLUMNS for v in STD_MOD],
    ids=_summary_ids("kgf"),
)
def test_summary_table_kgf(excel_table: drag.DragTable, column: str, variant: str) -> None:
    kgf = excel_table.kgf
    assert kgf.unit == "kgf"
    assert kgf.kgf is kgf
    assert_close(kgf.variant(variant)[column], series(f"summary_{column}_{variant}_kgf"))


def test_summary_speeds_and_matrix(excel_table: drag.DragTable) -> None:
    assert_close(excel_table.speed_kn, series("speed_kn"))
    assert_close(excel_table.speed_ms, series("speed_ms"))
    m = excel_table.matrix("std")
    assert m.shape == (len(SPEEDS_KN), len(drag.SUMMARY_COLUMNS))
    assert_close(m[:, drag.SUMMARY_COLUMNS.index("hamuro")], series("summary_hamuro_std_t"))


def test_design_rn_is_aberdeen_demersal(excel_table: drag.DragTable) -> None:
    assert drag.DESIGN_METHOD == "aberdeen_demersal"
    assert_close(excel_table.design_rn("std"), series("aberdeen_demersal_rn_std_t"))
    assert_close(excel_table.design_rn("mod"), series("aberdeen_demersal_rn_mod_t"))


@pytest.mark.parametrize("variant", STD_MOD)
@pytest.mark.parametrize("unit", ["t", "kgf"])
def test_average_excel(excel_table: drag.DragTable, variant: str, unit: str) -> None:
    table = excel_table if unit == "t" else excel_table.kgf
    avg = drag.average(table, Compat.EXCEL)
    assert avg.unit == unit
    got = avg.std if variant == "std" else avg.mod
    assert_close(got, series(f"summary_average_{variant}_{unit}"))


@pytest.mark.parametrize("unit", ["t", "kgf"])
def test_method_average_excel(excel_table: drag.DragTable, unit: str) -> None:
    table = excel_table if unit == "t" else excel_table.kgf
    got = drag.method_average(table, "mod", Compat.EXCEL)
    expected = series(f"summary_method_average_mod_{unit}")
    # C326:R326 = columnas del resumen + promedio; S326 (DynamiT) es estático.
    keys = [*drag.SUMMARY_COLUMNS, "average"]
    assert len(expected) == len(keys) + 1
    assert_close([got[k] for k in keys], expected[: len(keys)])


def test_dynamit_reference_is_static() -> None:
    for key in (
        "summary_dynamit_std_t",
        "summary_dynamit_mod_t",
        "summary_dynamit_std_kgf",
        "summary_dynamit_mod_kgf",
        "summary_dynamit_1kn_std_t",
    ):
        assert is_static(SHEET, key)


def test_to_dict_roundtrip(excel_table: drag.DragTable, inputs: drag.DragInputs) -> None:
    d = excel_table.to_dict()
    assert d["unit"] == "t" and d["compat"] == "excel"
    assert set(d["std"]) == set(drag.SUMMARY_COLUMNS)
    assert len(d["mod"]["reid"]) == len(SPEEDS_KN)
    di = inputs.to_dict()
    assert di["nhp"] == [150.0, 180.0] and len(di["ah_m"]) == len(SPEEDS_KN)
    assert drag.average(excel_table, Compat.EXCEL).to_dict()["unit"] == "t"


def test_dickson_without_openings_is_nan(inputs: drag.DragInputs) -> None:
    no_dickson = drag.DragInputs(
        **{**inputs.to_dict(), "nhp": inputs.nhp, "ah_m": None, "av_m": None}
    )
    table = drag.drag_table(no_dickson, SPEEDS_KN, Compat.EXCEL)
    assert np.isnan(table.std["dickson"]).all()
    assert_close(table.std["reid"], series("reid_rn_std_t"))


def test_dickson_openings_length_mismatch(inputs: drag.DragInputs) -> None:
    with pytest.raises(ValueError, match="ah_m"):
        drag.drag_table(inputs, [1.0, 2.0], Compat.EXCEL)


# ---------------------------------------------------------------------------------------------
# Modo CORRECTED: cada errata en la dirección esperada
# ---------------------------------------------------------------------------------------------


def test_hamuro_corrected_uses_radians() -> None:
    alpha = g("hamuro_alpha_deg")
    assert_close(drag.hamuro_sin_alpha(alpha), abs(np.sin(np.radians(alpha))))
    # El Excel evalúa sin(609.3 rad) → 0.189; el valor correcto es sin(10.63°) = 0.18453.
    assert drag.hamuro_sin_alpha(alpha, Compat.EXCEL) == pytest.approx(0.18911, abs=1e-5)
    assert drag.hamuro_sin_alpha(alpha) == pytest.approx(0.18453, abs=1e-5)
    rn_excel = drag.hamuro(_dl("std"), _st("std"), alpha, V_MS, Compat.EXCEL)
    rn_corr = drag.hamuro(_dl("std"), _st("std"), alpha, V_MS)
    assert_close(rn_corr / rn_excel, np.full_like(V_MS, 0.18453 / 0.18911), rtol=1e-4)


def test_hamuro_mod_corrected_uses_mod_dl(
    excel_table: drag.DragTable, corrected_table: drag.DragTable
) -> None:
    alpha = g("hamuro_alpha_deg")
    expected = drag.hamuro(_dl("mod"), _st("mod"), alpha, V_MS, Compat.CORRECTED)
    assert_close(corrected_table.mod["hamuro"], expected)
    # d/l_mod < d/l_std y sin corregido < sin Excel ⇒ la RN corregida es menor.
    assert (corrected_table.mod["hamuro"] < excel_table.mod["hamuro"]).all()
    ratio = corrected_table.mod["hamuro"] / corrected_table.std["hamuro"]
    assert_close(ratio, np.full_like(V_MS, _dl("mod") * _st("mod") / (_dl("std") * _st("std"))))


def test_reid_corrected_uses_row_speed() -> None:
    ss = _ss("std")
    corr = drag.reid(ss, V_KN)
    exc = drag.reid(ss, V_KN, Compat.EXCEL)
    assert_close(corr, V_KN**2 * ss / (54.72 * V_KN + 115.2))
    # A 1 kn coinciden; a mayor velocidad el denominador corregido es mayor ⇒ RN menor.
    assert_close(corr[0], exc[0])
    assert (corr[1:] < exc[1:]).all()
    # Con v_ref explícito el modo EXCEL usa ese denominador fijo.
    assert_close(
        drag.reid(ss, V_KN, Compat.EXCEL, v_ref_kn=2.0), V_KN**2 * ss / (54.72 * 2 + 115.2)
    )


def test_average_corrected_is_clean_mean_of_rn_methods(corrected_table: drag.DragTable) -> None:
    avg = drag.average(corrected_table)
    assert set(drag.RN_METHODS) == set(drag.SUMMARY_COLUMNS) - {"nomura_150", "nomura_180"}
    expected_std = np.mean([corrected_table.std[c] for c in drag.RN_METHODS], axis=0)
    expected_mod = np.mean([corrected_table.mod[c] for c in drag.RN_METHODS], axis=0)
    assert_close(avg.std, expected_std)
    assert_close(avg.mod, expected_mod)
    # La contaminación de Nomura (≈2 t a 1 kn) infla el promedio del Excel a baja velocidad.
    polluted = drag.average(corrected_table, Compat.EXCEL)
    assert polluted.std[0] > avg.std[0]
    assert polluted.mod[0] > avg.mod[0]


def test_method_average_corrected(corrected_table: drag.DragTable) -> None:
    got = drag.method_average(corrected_table, "std")
    assert got["aberdeen_demersal"] == pytest.approx(
        float(np.mean(corrected_table.std["aberdeen_demersal"]))
    )
    assert got["average"] == pytest.approx(float(np.mean(drag.average(corrected_table).std)))


def test_corrected_table_matches_excel_where_no_erratum(
    excel_table: drag.DragTable, corrected_table: drag.DragTable
) -> None:
    unaffected = set(drag.SUMMARY_COLUMNS) - {"hamuro", "reid"}
    for col in unaffected:
        for v in STD_MOD:
            assert_close(corrected_table.variant(v)[col], excel_table.variant(v)[col], where=col)


def test_variant_name_validation(excel_table: drag.DragTable) -> None:
    with pytest.raises(ValueError):
        excel_table.variant("other")
