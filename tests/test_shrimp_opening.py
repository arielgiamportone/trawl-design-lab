"""Fase 19.7b-c: aberturas de las redes camaroneras (tijera) y unión al copo de las tangoneras."""

from __future__ import annotations

import dataclasses
import math

import pytest

from trawlkit.catalog import LANGOSTINO_DEPTH_M, catalog_case, default_depth
from trawlkit.i18n import use_lang
from trawlkit.io import NetSpec, load_net
from trawlkit.model import DesignCase, run
from trawlkit.netcheck import check
from trawlkit.rigging import shrimp
from trawlkit.sim.validation import standard_case

INIDEP = {
    # red: (DP, AH y AV de DynamiT a 3,5 nudos; ITO 043/2022, p. 6)
    "inidep_ito043_tangonera_inidep": (16.2, 14.0, 1.3),
    "inidep_ito043_tangonera_empresa": (16.2, 14.0, 1.5),
}


@pytest.fixture(scope="module")
def base() -> DesignCase:
    return standard_case()


# --- equilibrio de la tijera ------------------------------------------------------------------


def test_equilibrio_cumple_las_ecuaciones() -> None:
    lift, drag, rn, lc, lr = 642.5, 490.5, 2796.0, 70.0, 34.0
    b = shrimp.tijera_balance(lift, drag, rn, lc, lr)
    assert b.converged
    a, beta = math.radians(b.alpha_deg), math.radians(b.beta_deg)
    # Misma separación lateral por la tijera y por la red.
    assert lc * math.sin(a) == pytest.approx(lr * math.sin(beta), rel=1e-9)
    # Equilibrio a lo largo y a lo ancho.
    assert b.tension_kgf * math.cos(a) == pytest.approx(drag + rn / 2 * math.cos(beta))
    assert lift == pytest.approx(b.tension_kgf * math.sin(a) + rn / 2 * math.sin(beta), rel=1e-9)
    assert b.spread_m == pytest.approx(2 * lc * math.sin(a))


def test_equilibrio_sin_solucion() -> None:
    # La sustentación supera lo que la red puede equilibrar: no es un resultado.
    b = shrimp.tijera_balance(5000.0, 10.0, 100.0, 70.0, 20.0)
    assert not b.converged
    with pytest.raises(ValueError):
        shrimp.tijera_balance(0.0, 10.0, 100.0, 70.0, 20.0)


@pytest.mark.parametrize(
    "key", ["ito043_sim3", "ito043_sim1", "iat085_iberconsa", "iat111_morales"]
)
def test_equilibrio_frente_a_dynamit(key: str) -> None:
    # Los cuatro casos del informe de la fase: ±20 % de la DP de DynamiT mientras L_R no salga
    # del plano (sección 5.1).
    case = next(c for c in shrimp.DYNAMIT_CASES if c.key == key)
    b = shrimp.dynamit_case_balance(case)
    assert b.converged
    assert b.spread_m == pytest.approx(case.dynamit_spread_m, rel=shrimp.DYNAMIT_SPREAD_TOLERANCE)


def test_valores_del_informe_reproducidos() -> None:
    # Informe de la Fase 19.7b, tabla de la sección 5.1: 19,0 / 22,2 / 17,8 / 11,3 m.
    got = {c.key: shrimp.dynamit_case_balance(c).spread_m for c in shrimp.DYNAMIT_CASES}
    assert got["ito043_sim3"] == pytest.approx(19.0, abs=0.1)
    assert got["ito043_sim1"] == pytest.approx(22.2, abs=0.1)
    assert got["iat085_iberconsa"] == pytest.approx(17.8, abs=0.1)
    assert got["iat111_morales"] == pytest.approx(11.3, abs=0.1)


# --- motor ------------------------------------------------------------------------------------


@pytest.mark.parametrize("net_id", sorted(INIDEP))
def test_redes_del_inidep_con_el_metodo_camaronero(net_id: str) -> None:
    dp, ah, av = INIDEP[net_id]
    cc = catalog_case(net_id)
    r = run(cc.case)
    op = r.spread.shrimp
    assert op is not None and op.method == "tijera"
    assert r.doors.spread_m == pytest.approx(dp, rel=0.20)
    assert r.spread.horizontal_opening_m == pytest.approx(ah, rel=0.20)
    assert shrimp.AH_OVER_DP_RANGE[0] <= op.ah_over_dp <= shrimp.AH_OVER_DP_RANGE[1]
    assert op.vertical_opening_m == pytest.approx(0.04 * 35.5)
    assert r.summary()["vertical_opening_m"] == pytest.approx(op.vertical_opening_m)
    assert r.summary()["opening_method"] == "tijera"
    assert r.multirig is not None and r.multirig.net_spread_m == pytest.approx(r.doors.spread_m)
    assert op.vertical_opening_m == pytest.approx(av, rel=0.10) and op.vertical_opening_m < 1.5
    # El método del libro sobrestimaba: DP de más de 50 m.
    book = run(dataclasses.replace(cc.case, opening_method="book"))
    assert book.spread.shrimp is None and book.doors.spread_m > 50.0
    assert op.book_door_spread_m == pytest.approx(book.doors.spread_m)
    assert op.book_horizontal_opening_m == pytest.approx(book.spread.horizontal_opening_m)
    notes = [n for n in r.notes if n.startswith("shrimp_opening")]
    assert any("Roth 2016" in n for n in notes)
    assert any("0,74–0,77" in n for n in notes)
    assert any("método camaronero" in n for n in r.notes if n.startswith("cfp_res7_2018"))
    with use_lang("en"):
        en = run(cc.case).notes
    assert any(n.startswith("shrimp_opening: shrimp method with a split bridle") for n in en)


def test_portones_y_pareja_sin_cambios(base: DesignCase) -> None:
    # La A-3 (langostilla, portones) sigue con el promedio del libro aunque sea de crustáceos.
    auto = run(base)
    assert auto.spread.shrimp is None and auto.doors.tijera is None
    book = run(dataclasses.replace(base, opening_method="book"))
    assert auto.summary() == book.summary()
    assert "shrimp" not in auto.to_dict()["spread"]
    assert "tijera" not in auto.to_dict()["doors"]
    for net_id in ("fao_wb_bt2p_60hp", "bobp_wp10_pair_480x160"):
        case = catalog_case(net_id).case
        a = run(case).summary()
        b = run(dataclasses.replace(case, opening_method="book")).summary()
        assert a == b


def test_portones_forzado_usa_k(base: DesignCase) -> None:
    r = run(dataclasses.replace(base, opening_method="shrimp"))
    op = r.spread.shrimp
    assert op is not None and op.method == "headrope_k"
    assert op.k.key == "us_conventional"
    assert r.spread.horizontal_opening_m == pytest.approx(0.70 * r.dimensions.std.headrope_m)
    assert r.doors.spread_m == pytest.approx(run(base).doors.spread_m)


def test_gemelo_usa_k(base: DesignCase) -> None:
    r = run(dataclasses.replace(base, rig="twin"))
    op = r.spread.shrimp
    assert op is not None and op.method == "headrope_k"
    assert r.multirig is not None
    assert r.multirig.vertical_opening_m == pytest.approx(op.vertical_opening_m)


def test_familias_de_k() -> None:
    assert shrimp.headrope_k("langostino patagónico").k == 0.43
    assert shrimp.headrope_k("camarón", "Super X-3 tongue trawl").k == 0.80
    assert shrimp.headrope_k("camarón (shrimp)").k == 0.70


def test_entradas_invalidas(base: DesignCase) -> None:
    with pytest.raises(ValueError):
        dataclasses.replace(base, opening_method="otro")
    with pytest.raises(ValueError):
        dataclasses.replace(base, shrimp_bridle_m=0.0)


def test_canas_cambian_la_abertura() -> None:
    case = catalog_case("inidep_ito043_tangonera_inidep").case
    short = run(dataclasses.replace(case, shrimp_bridle_m=2.5))
    long_ = run(dataclasses.replace(case, shrimp_bridle_m=4.0))
    assert short.spread.horizontal_opening_m != long_.spread.horizontal_opening_m
    assert not any("cañas de" in n for n in short.notes)


# --- profundidad de la flota langostinera -----------------------------------------------------


def test_profundidad_del_langostino() -> None:
    spec = load_net("inidep_ito043_tangonera_inidep")
    assert default_depth(spec) == (90.0, None)  # design.depth_m de la red (supuesto con fuente)
    data = spec.model_dump()
    data["design"].pop("depth_m")
    bare = NetSpec.model_validate(data)
    depth, note = default_depth(bare)
    assert depth == LANGOSTINO_DEPTH_M == 90.0
    assert note is not None and "langostinera" in note
    # Las demás redes de fondo siguen con 30 m.
    assert default_depth(load_net("seafdec_31_outrigger_shrimp"))[0] == 30.0


# --- unión al copo (Fase 19.7c) ---------------------------------------------------------------


def test_union_al_copo_requiere_el_cabo_del_costado() -> None:
    spec = load_net("inidep_ito043_tangonera_inidep")
    assert not [i for i in check(spec) if i.level == "error"]
    data = spec.model_dump()
    for p in data["panels"]:
        p.pop("aft_rope_m", None)
    bare = NetSpec.model_validate(data)
    issues = check(bare)
    assert not any(i.code == "codend_join" for i in issues)
    assert any(i.code == "seam" and i.level == "error" for i in issues)
