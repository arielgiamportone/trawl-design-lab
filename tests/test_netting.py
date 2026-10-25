"""`trawlkit.netting` y `trawlkit.materials` contra 'Paños de red y cortes' (tests/golden)."""

from __future__ import annotations

import math
import re
from collections.abc import Callable

import numpy as np
import pytest

from tests.golden_utils import assert_close, golden, golden_entry, golden_series, load_sheet
from trawlkit.compat import Compat
from trawlkit.io import NetSpec, Panel, load_catalogue, load_net
from trawlkit.materials import (
    EXCEL_PI,
    find_material,
    materials_from_catalogue,
    twine_density_kg_m3,
    weight_in_water_coefficient,
)
from trawlkit.net import group_rows
from trawlkit.netting import (
    cut_angle_deg,
    cut_code,
    cut_meshes,
    cut_meshes_x2,
    cut_ratio,
    cut_steps,
    join_offset_m,
    join_ratio,
    load_cut_table,
    mean_cut_angle_deg,
    mesh_count,
    panel_working_area_m2,
    runnage_m_per_kg,
    stretched_length_m,
    symmetric_cut_meshes,
    taper_ratio,
    vertical_opening_coefficient,
)

SHEET = "panos_de_red_y_cortes"

#: slug del golden -> (preset, id del panel en la spec)
PANEL_SLUGS: dict[str, tuple[str, str]] = {
    "a": ("fao_a3_standard", "A"),
    "b": ("fao_a3_standard", "B"),
    "c": ("fao_a3_standard", "C"),
    "d": ("fao_a3_standard", "D"),
    "e": ("fao_a3_standard", "E"),
    "f": ("fao_a3_standard", "F"),
    "g_back": ("fao_a3_standard", "G"),
    "g_belly": ("fao_a3_standard", "G"),
    "h_back": ("fao_a3_standard", "H"),
    "h_belly": ("fao_a3_standard", "H"),
    "i_bag_top": ("fao_a3_standard", "I"),
    "j_bag_bottom": ("fao_a3_standard", "J"),
    "i_mod_bag_top": ("fao_a3_modified", "I'"),
    "i_mod_bag_bottom": ("fao_a3_modified", "I'"),
}

_SPECS: dict[str, NetSpec] = {}


def spec(name: str) -> NetSpec:
    if name not in _SPECS:
        _SPECS[name] = load_net(name)
    return _SPECS[name]


def panel(slug: str) -> Panel:
    preset, pid = PANEL_SLUGS[slug]
    return next(p for p in spec(preset).panels if p.id == pid)


def extra(p: Panel, name: str) -> float:
    v = float((p.model_extra or {})[name])
    return int(v) if v.is_integer() else v


def _row(cell: str) -> int:
    return int(re.sub(r"[A-Z]+", "", cell))


def ids_for(keys: list[str]) -> list[str]:
    return [f"{k}[{golden_entry(SHEET, k)['cell']}]" for k in keys]


def keys_matching(pattern: str) -> list[str]:
    rx = re.compile(pattern)
    return [k for k in load_sheet(SHEET)["values"] if rx.match(k)]


# ------------------------------------------------------------------------------------------
# Compostura básica
# ------------------------------------------------------------------------------------------


def test_panel_a_runnage_m_kg() -> None:
    """A55 =1000000/K55."""
    assert_close(runnage_m_per_kg(1280), golden(SHEET, "panel_a_runnage_m_kg"))
    assert_close(runnage_m_per_kg(np.array([1280.0, 950.0])), [781.25, 1e6 / 950])


def test_panel_a_twine_density_excel() -> None:
    """L55: densidad 'dimensionalmente incorrecta' reproducida en modo EXCEL."""
    assert_close(
        twine_density_kg_m3(1.37, 80, 781.25, compat=Compat.EXCEL),
        golden(SHEET, "panel_a_twine_density_kg_m3"),
    )
    # L120 (950 tex): valor cacheado en el libro (no hay clave golden).
    assert_close(twine_density_kg_m3(1.16, 60, 1e6 / 950, compat=Compat.EXCEL), 1112.457094736842)


def test_twine_density_corrected_is_dimensionally_consistent() -> None:
    """Errata twine_density_units: CORRECTED = 1/(A[m²]·runnage) ≈ 868 kg/m³ < 1152."""
    excel = twine_density_kg_m3(1.37, 80, 781.25, compat=Compat.EXCEL)
    corrected = twine_density_kg_m3(1.37, 80, 781.25)
    area_m2 = math.pi * (1.37e-3 / 2) ** 2
    assert_close(corrected, 1 / (area_m2 * 781.25))
    assert 860 < corrected < 875 < excel
    # independiente del mallero
    assert_close(twine_density_kg_m3(1.37, 40, 781.25), corrected)
    # consistencia con el Excel: L55 = π·(d/2)²·runnage, es decir 1e-6/ρ_corr salvo 3.1416 vs π
    assert_close(excel, EXCEL_PI / math.pi * 1e6 / corrected)


STRETCHED_KEYS = keys_matching(r"^panel_.*_stretched_.*_m$")


@pytest.mark.parametrize("key", STRETCHED_KEYS, ids=ids_for(STRETCHED_KEYS))
def test_stretched_length(key: str) -> None:
    """I55:I57 (y bloques homólogos): n_mallas · coef · mallero / 1000.

    Los golden siguen el orden de filas de cada bloque (t2 = primera fila, t1 = segunda), que en el
    bloque A está invertido respecto a los demás; se localiza el campo de la spec por la fila de la
    celda de origen.
    """
    slug = re.match(r"^panel_(.*)_stretched_", key).group(1)
    p = panel(slug)
    row = _row(golden_entry(SHEET, key)["cell"])
    src = p.source_cells or {}
    field = next(
        f for f in ("meshes_a", "meshes_b", "meshes_depth") if _row(src[f].split("!")[1]) == row
    )
    meshes = p.meshes_depth if field == "meshes_depth" else extra(p, field)
    coef = extra(p, "plan_coef_y") if field == "meshes_depth" else extra(p, "plan_coef_x")
    assert_close(stretched_length_m(meshes, p.mesh_mm, coef), golden(SHEET, key))


AREA_KEYS = keys_matching(r"^panel_.*_working_area_m2$")


@pytest.mark.parametrize("key", AREA_KEYS, ids=ids_for(AREA_KEYS))
def test_panel_working_area(key: str) -> None:
    """A61: U1·√(1−U1²)·((T1+T2)/2)·N·mL² con U1 = coeficiente X en el plano (0.5)."""
    p = panel(re.match(r"^panel_(.*)_working_area_m2$", key).group(1))
    area = panel_working_area_m2(
        extra(p, "plan_coef_x"),
        extra(p, "meshes_a"),
        extra(p, "meshes_b"),
        p.meshes_depth,
        p.mesh_mm,
    )
    assert_close(area, golden(SHEET, key))


COUNT_KEYS = keys_matching(r"^panel_.*_mesh_count$")


@pytest.mark.parametrize("key", COUNT_KEYS, ids=ids_for(COUNT_KEYS))
def test_mesh_count(key: str) -> None:
    """A64: ((T1+T2−1)·(N−0.5))+0.5."""
    p = panel(re.match(r"^panel_(.*)_mesh_count$", key).group(1))
    assert_close(
        mesh_count(extra(p, "meshes_a"), extra(p, "meshes_b"), p.meshes_depth), golden(SHEET, key)
    )


# ------------------------------------------------------------------------------------------
# Cortes: cada bloque escribe su propia fórmula; se reproducen con las primitivas
# ------------------------------------------------------------------------------------------


def _edges(slug: str) -> tuple[int, int, int]:
    p = panel(slug)
    return extra(p, "meshes_a"), extra(p, "meshes_b"), p.meshes_depth


def _wing_x1(slug: str) -> float:
    a, b, n = _edges(slug)
    return float(cut_meshes(a, b, n))


def _wing_x2(slug: str) -> float:
    a, b, n = _edges(slug)
    return float(cut_meshes_x2(a, b, n))


def _sym(slug: str) -> float:
    a, b, _ = _edges(slug)
    return float(symmetric_cut_meshes(a, b))


CUT_CASES: dict[str, Callable[[], object]] = {
    # Paño A (G63:I64)
    "panel_a_cut_x1_meshes": lambda: _wing_x1("a"),
    "panel_a_cut_x1_ratio": lambda: cut_ratio(_wing_x1("a"), _edges("a")[2]),
    "panel_a_cut_x1_code": lambda: cut_code(cut_ratio(_wing_x1("a"), _edges("a")[2])),
    "panel_a_cut_x2_meshes": lambda: _wing_x2("a"),
    "panel_a_cut_x2_ratio": lambda: taper_ratio(_edges("a")[0], _edges("a")[0]),
    "panel_a_cut_x2_code": lambda: cut_code(taper_ratio(_edges("a")[0], _edges("a")[0])),
    # Paño B (R62:T63): S62 pasa el coeficiente X (P55 = 0.5) en vez de N; T62 apunta a H63 (A).
    "panel_b_cut_x1_meshes": lambda: _wing_x1("b"),
    "panel_b_cut_x1_ratio": lambda: cut_ratio(_wing_x1("b"), extra(panel("b"), "plan_coef_x")),
    "panel_b_cut_x1_code": lambda: cut_code(cut_ratio(_wing_x1("a"), _edges("a")[2])),
    "panel_b_cut_x2_meshes": lambda: _wing_x2("b"),
    "panel_b_cut_x2_ratio": lambda: taper_ratio(_edges("b")[0], _edges("b")[0]),
    "panel_b_cut_x2_code": lambda: cut_code(taper_ratio(_edges("b")[0], _edges("b")[0])),
    # Paño C (F97:H98)
    "panel_c_cut_x1_meshes": lambda: _wing_x1("c"),
    "panel_c_cut_x1_ratio": lambda: cut_ratio(_wing_x1("c"), _edges("c")[2]),
    "panel_c_cut_x1_code": lambda: cut_code(cut_ratio(_wing_x1("c"), _edges("c")[2])),
    "panel_c_cut_x2_meshes": lambda: _wing_x2("c"),
    "panel_c_cut_x2_ratio": lambda: taper_ratio(_edges("c")[1], _edges("c")[1]),
    "panel_c_cut_x2_code": lambda: cut_code(taper_ratio(_edges("c")[1], _edges("c")[1])),
    # Paño D (R97:T98): S97 = X1/N (razón directa) → 2/3 → 1N4B (fila 71 de la tabla)
    "panel_d_cut_x1_meshes": lambda: _wing_x1("d"),
    "panel_d_cut_x1_ratio": lambda: taper_ratio(_wing_x1("d"), _edges("d")[2]),
    "panel_d_cut_x1_code": lambda: cut_code(taper_ratio(_wing_x1("d"), _edges("d")[2])),
    "panel_d_cut_x2_meshes": lambda: _wing_x2("d"),
    "panel_d_cut_x2_ratio": lambda: taper_ratio(_edges("d")[1], _edges("d")[1]),
    "panel_d_cut_x2_code": lambda: cut_code(taper_ratio(_edges("d")[1], _edges("d")[1])),
    # Paño E (F127:H127): corte simétrico
    "panel_e_cut_x1_meshes": lambda: _sym("e"),
    "panel_e_cut_x1_ratio": lambda: taper_ratio(_sym("e"), _edges("e")[2]),
    "panel_e_cut_x1_code": lambda: cut_code(taper_ratio(_sym("e"), _edges("e")[2])),
    # Paño F (R122:T123): T122 es #N/A (sin clave golden)
    "panel_f_cut_x1_meshes": lambda: _wing_x1("f"),
    "panel_f_cut_x1_ratio": lambda: cut_ratio(_wing_x1("f"), _edges("f")[2]),
    "panel_f_cut_x2_meshes": lambda: _wing_x2("f"),
    "panel_f_cut_x2_ratio": lambda: taper_ratio(_edges("f")[1], _edges("f")[1]),
    "panel_f_cut_x2_code": lambda: cut_code(taper_ratio(_edges("f")[1], _edges("f")[1])),
    # Paños G y H, dorso y vientre (F163:H163, R163:T163, F196:H196, R196:T196)
    "panel_g_back_cut_x1_meshes": lambda: _sym("g_back"),
    "panel_g_back_cut_x1_ratio": lambda: taper_ratio(_sym("g_back"), _edges("g_back")[2]),
    "panel_g_back_cut_x1_code": lambda: cut_code(taper_ratio(_sym("g_back"), _edges("g_back")[2])),
    "panel_g_belly_cut_x1_meshes": lambda: _sym("g_belly"),
    "panel_g_belly_cut_x1_ratio": lambda: taper_ratio(_sym("g_belly"), _edges("g_belly")[2]),
    "panel_g_belly_cut_x1_code": lambda: cut_code(
        taper_ratio(_sym("g_belly"), _edges("g_belly")[2])
    ),
    "panel_h_back_cut_x1_meshes": lambda: _sym("h_back"),
    "panel_h_back_cut_x1_ratio": lambda: taper_ratio(_sym("h_back"), _edges("h_back")[2]),
    "panel_h_back_cut_x1_code": lambda: cut_code(taper_ratio(_sym("h_back"), _edges("h_back")[2])),
    "panel_h_belly_cut_x1_meshes": lambda: _sym("h_belly"),
    "panel_h_belly_cut_x1_ratio": lambda: taper_ratio(_sym("h_belly"), _edges("h_belly")[2]),
    "panel_h_belly_cut_x1_code": lambda: cut_code(
        taper_ratio(_sym("h_belly"), _edges("h_belly")[2])
    ),
}

# Bolsas (F229:H230, R229:T230, F262:H263, R262:T263): corte n = N/N, corte t = T1/T2.
for _slug in ("i_bag_top", "j_bag_bottom", "i_mod_bag_top", "i_mod_bag_bottom"):
    CUT_CASES[f"panel_{_slug}_cut_n_meshes"] = lambda s=_slug: _edges(s)[2]
    CUT_CASES[f"panel_{_slug}_cut_n_ratio"] = lambda s=_slug: taper_ratio(
        _edges(s)[2], _edges(s)[2]
    )
    CUT_CASES[f"panel_{_slug}_cut_n_code"] = lambda s=_slug: cut_code(
        taper_ratio(_edges(s)[2], _edges(s)[2])
    )
    CUT_CASES[f"panel_{_slug}_cut_t_meshes"] = lambda s=_slug: _edges(s)[0]
    CUT_CASES[f"panel_{_slug}_cut_t_ratio"] = lambda s=_slug: taper_ratio(
        _edges(s)[0], _edges(s)[1]
    )
    CUT_CASES[f"panel_{_slug}_cut_t_code"] = lambda s=_slug: cut_code(
        taper_ratio(_edges(s)[0], _edges(s)[1])
    )

CUT_KEYS = list(CUT_CASES)


def test_cut_cases_cover_every_cut_golden_key() -> None:
    assert set(keys_matching(r"^panel_.*_cut_")) == set(CUT_KEYS)


@pytest.mark.parametrize("key", CUT_KEYS, ids=ids_for(CUT_KEYS))
def test_cut(key: str) -> None:
    expected = golden(SHEET, key)
    actual = CUT_CASES[key]()
    if isinstance(expected, str):
        assert actual == expected
    else:
        assert_close(actual, expected)


def test_cut_code_exact_match_uses_tolerance() -> None:
    assert cut_code(1 / 3) == "1N1B"
    assert cut_code(0.5) == "1N2B"
    assert cut_code(2 / 3) == "1N4B"
    rows = load_cut_table()
    assert len(rows) == 24 and rows[0].cut_code == "AB" and rows[-1].cut_code == "1N2B"


def test_panel_f_cut_na_erratum() -> None:
    """P!T122: VLOOKUP sin coincidencia → #N/A (EXCEL: None); CORRECTED: razón más cercana."""
    ratio = float(golden(SHEET, "panel_f_cut_x1_ratio"))
    assert cut_code(ratio, compat=Compat.EXCEL) is None
    assert cut_code(ratio) == "3N2B"  # 0.269 → 1/4


# ------------------------------------------------------------------------------------------
# Cantidad de paneles, pegadura de la bolsa modificada
# ------------------------------------------------------------------------------------------

PANEL_COUNT_KEYS = {
    "panel_a_panel_count": ("fao_a3_standard", "A+B"),
    "panel_c_panel_count": ("fao_a3_standard", "C"),
    "panel_d_panel_count": ("fao_a3_standard", "D"),
    "panel_e_panel_count": ("fao_a3_standard", "E"),
    "panel_f_panel_count": ("fao_a3_standard", "F"),
    "panel_g_belly_panel_count": ("fao_a3_standard", "G"),
    "panel_h_belly_panel_count": ("fao_a3_standard", "H"),
    "panel_i_bag_top_panel_count": ("fao_a3_standard", "I"),
    "panel_j_bag_bottom_panel_count": ("fao_a3_standard", "J"),
    "panel_i_mod_bag_bottom_panel_count": ("fao_a3_modified", "I'"),
}


@pytest.mark.parametrize("key", list(PANEL_COUNT_KEYS), ids=ids_for(list(PANEL_COUNT_KEYS)))
def test_panel_count(key: str) -> None:
    """COUNTIF de letras (N62 = A + B) ↔ cantidad de paneles de la fila agrupada."""
    preset, row_id = PANEL_COUNT_KEYS[key]
    rows = {r.id: r for r in group_rows(spec(preset))}
    assert rows[row_id].count == golden(SHEET, key)


def test_mod_bag_join_ratio() -> None:
    """J240 =I256/I190."""
    h, ip = panel("h_back"), panel("i_mod_bag_top")
    nxt = stretched_length_m(extra(ip, "meshes_b"), ip.mesh_mm, 0.5)
    prev = stretched_length_m(extra(h, "meshes_b"), h.mesh_mm, 0.5)
    assert_close(join_ratio(nxt, prev), golden(SHEET, "mod_bag_join_ratio"))


def test_mod_bag_join_offset_m() -> None:
    """B243 =(I189-I255)/2."""
    h, ip = panel("h_back"), panel("i_mod_bag_top")
    prev = stretched_length_m(extra(h, "meshes_a"), h.mesh_mm, 0.5)
    nxt = stretched_length_m(extra(ip, "meshes_a"), ip.mesh_mm, 0.5)
    assert_close(join_offset_m(prev, nxt), golden(SHEET, "mod_bag_join_offset_m"))


# ------------------------------------------------------------------------------------------
# Ángulo de ataque de los cortes (B272:K278)
# ------------------------------------------------------------------------------------------


def test_cut_u2_vertical_series() -> None:
    """F273:F277 = SQRT(1 − U1²)."""
    _, u1 = golden_series(SHEET, "cut_u1_horizontal")
    _, u2 = golden_series(SHEET, "cut_u2_vertical")
    assert_close(vertical_opening_coefficient(np.array(u1)), u2)


def test_cut_steps_series() -> None:
    """H273:I277 = VLOOKUP(código, Tab!C49:F88, 3/4)."""
    _, codes = golden_series(SHEET, "cut_codes")
    _, w = golden_series(SHEET, "cut_width_meshes")
    _, h = golden_series(SHEET, "cut_height_meshes")
    steps = [cut_steps(c) for c in codes]
    assert [s[0] for s in steps] == w and [s[1] for s in steps] == h


def test_cut_tan_theta_and_angle_series() -> None:
    """J273:J277 = (a·U1)/(d·U2); K273:K277 = DEGREES(ATAN(J))."""
    _, codes = golden_series(SHEET, "cut_codes")
    _, u1 = golden_series(SHEET, "cut_u1_horizontal")
    _, tan = golden_series(SHEET, "cut_tan_theta")
    _, deg = golden_series(SHEET, "cut_angle_deg")
    angles = [cut_angle_deg(c, u) for c, u in zip(codes, u1, strict=True)]
    assert_close(angles, deg)
    assert_close([math.tan(math.radians(a)) for a in angles], tan)


def test_cut_angle_average_deg_excel() -> None:
    """K278 =AVERAGE(K273:K277), con la errata cut_ratio_first_panel (todas usan $G$273)."""
    _, codes = golden_series(SHEET, "cut_codes")
    _, u1 = golden_series(SHEET, "cut_u1_horizontal")
    assert_close(
        mean_cut_angle_deg(codes, u1, compat=Compat.EXCEL), golden(SHEET, "cut_angle_average_deg")
    )
    assert golden(SHEET, "cut_ratio_first_panel") == codes[0] == panel("a").cut_code


def test_cut_ratio_first_panel_corrected_differs() -> None:
    """Errata cut_ratio_first_panel: con códigos distintos, CORRECTED usa el de cada paño."""
    codes = ["1N2B", "AB", "1N2B"]
    u1 = [0.38, 0.38, 0.23]
    excel = mean_cut_angle_deg(codes, u1, compat=Compat.EXCEL)
    corrected = mean_cut_angle_deg(codes, u1)
    assert_close(excel, mean_cut_angle_deg(["1N2B"] * 3, u1))
    ab = cut_angle_deg("AB", 0.38)
    assert corrected > excel and ab > cut_angle_deg("1N2B", 0.38)
    assert_close(corrected, (cut_angle_deg("1N2B", 0.38) + ab + cut_angle_deg("1N2B", 0.23)) / 3)


# ------------------------------------------------------------------------------------------
# Catálogo de materiales
# ------------------------------------------------------------------------------------------


def test_material_catalogue_lookup() -> None:
    mats = materials_from_catalogue(load_catalogue("materials"))
    pa = find_material(mats, "PA", rtex=1280)
    assert pa.id == "pa_r1280tex" and pa.density_kg_m3 == 1140
    assert find_material(mats, "pa", rtex=950).id == "pa_r950tex"
    assert find_material(mats, "PA", diameter_mm=1.2).id == "pa_r950tex"
    assert_close(weight_in_water_coefficient(1140, 1025), 1 - 1025 / 1140)
    assert abs(weight_in_water_coefficient(1140) - pa.weight_in_water_coefficient_seawater) < 0.002
    assert pa.to_dict()["material"] == "PA"
    # El libro sólo trae PA; PE, PP y PES se agregan como polímeros genéricos (Fase 12).
    pe = find_material(mats, "PE")
    assert pe.id == "pe_generic" and pe.density_kg_m3 == 950
    with pytest.raises(KeyError):
        find_material(mats, "KEVLAR")
