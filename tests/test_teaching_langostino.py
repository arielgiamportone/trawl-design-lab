"""Fase 20.3: ejercicios y laboratorio de la red langostinera de tangones."""

from __future__ import annotations

import pytest

from trawlkit.i18n import use_lang
from trawlkit.rigging import shrimp
from trawlkit.teaching import bank, grade, instantiate, load_bank, solve
from trawlkit.teaching.labs import facts, lab_check, lab_view, load_labs

IDS = [
    "langostino.abertura_horizontal",
    "langostino.equilibrio_roth",
    "langostino.abertura_vertical",
    "langostino.tangon",
    "langostino.cable",
]
LAB = "lab.langostino_tangones"
START = {"net": "inidep_ito043_tangonera_inidep", "vessel": "ar_tangonero_1998"}


def test_exercises_are_in_the_bank_for_chapter_26() -> None:
    found = [e.id for e in bank(chapter="26_aparejos_dobles_y_vara")]
    assert found == IDS
    assert {load_bank()[i].topic for i in IDS} == {"langostino"}


def _wrong(value: float | str) -> float | str:
    if isinstance(value, str):
        return "No" if value == "Sí" else "Sí"
    return value * 1.5 + 1.0


@pytest.mark.parametrize("exercise_id", IDS)
def test_engine_answer_scores_full_and_wrong_answer_low(exercise_id: str) -> None:
    for seed in range(12):
        inst = instantiate(exercise_id, seed)
        assert inst.data and "{" not in inst.statement
        sol = solve(exercise_id, seed)
        assert grade(exercise_id, seed, dict(sol.values)).score == 1.0
        wrong = {k: _wrong(v) for k, v in sol.values.items()}
        assert grade(exercise_id, seed, wrong).score == 0.0
        with use_lang("en"):
            english = {k: ("Yes" if v == "Sí" else v) for k, v in sol.values.items()}
            assert grade(exercise_id, seed, english).score == 1.0


def test_seed_zero_matches_the_engine_for_the_inidep_net() -> None:
    f = facts(START)
    # AV = 0,04·lima de la red del INIDEP y el límite de la Res. CFP 7/2018.
    av = solve("langostino.abertura_vertical", 0).values
    assert av["av_m"] == pytest.approx(f["summary.vertical_opening_m"])
    assert av["cumple"] == "Sí" and f["summary.cfp_av_limit_m"] == shrimp.CFP_AV_LIMIT_M
    # AH con la DP del motor redondeada: la misma razón de triángulos semejantes.
    ah = solve("langostino.abertura_horizontal", 0).values
    assert ah["ah_m"] == pytest.approx(f["summary.horizontal_opening_m"], rel=0.01)
    lo, hi = shrimp.AH_OVER_DP_RANGE
    assert lo <= ah["ah_dp"] <= hi
    # El equilibrio con los datos de ITO 043/2022, sim. 3 (R = tensión − 2·F_CD).
    sim3 = next(c for c in shrimp.DYNAMIT_CASES if c.key == "ito043_sim3")
    dp = solve("langostino.equilibrio_roth", 0).values["dp_m"]
    assert dp == pytest.approx(shrimp.dynamit_case_balance(sim3).spread_m, rel=0.005)
    # Tangones de 24 pies: las redes se superponen como en el capítulo 26.
    tg = solve("langostino.tangon", 0).values
    assert tg["superponen"] == "Sí" and f["summary.nets_gap_m"] < 0
    # Cable: la carga es la de una red con su aparejo a 3,5 nudos y el de 24 mm de la fuente.
    cable = solve("langostino.cable", 0).values
    assert 4510 == pytest.approx(f["summary.net_total_3_5kn_kgf"], rel=0.001)
    assert cable["fs_fuente"] == pytest.approx(f["summary.warp_safety_factor"], rel=0.001)
    assert cable["dw_mm"] == 20.0


def test_lab_runs_step_by_step() -> None:
    spec = load_labs()[LAB]
    assert spec.start == START and [s.id for s in spec.steps] == [
        "base",
        "velocidad",
        "profundidad",
        "tangones",
    ]
    cases = {
        "base": (START, {"dynamit": "dentro_20", "cfp": "Sí"}),
        "velocidad": (
            {**START, "params": {"warp_design_speed_kn": 3.0}},
            {"porque": "sustentacion"},
        ),
        "profundidad": ({**START, "params": {"depth_m": 60}}, {"tijera": "igual"}),
        "tangones": ({**START, "params": {"boom_length_m": 9.5}}, {"limites": "los tangones"}),
    }
    for step in spec.steps:
        design, extra = cases[step.id]
        f = facts(design)
        answers = {q.id: f[q.fact] for q in step.questions if q.kind == "number" and q.fact}
        r = lab_check(LAB, step.id, design, {**answers, **extra})
        assert r.done, (step.id, r)
        # Con el caso de partida, los pasos que piden un cambio no se cumplen.
        if step.id != "base":
            assert not lab_check(LAB, step.id, START, {**answers, **extra}).done
    # La separación de portones no depende del cable filado con tijera (capítulo 26).
    assert facts({**START, "params": {"depth_m": 60}})["summary.door_spread_m"] == pytest.approx(
        facts(START)["summary.door_spread_m"]
    )
    wrong = lab_check(LAB, "base", START, {"dp": "40", "dynamit": "doble", "cfp": "No"})
    assert not wrong.done and not any(q.ok for q in wrong.questions)


def test_lab_view_in_english() -> None:
    with use_lang("en"):
        view = lab_view(load_labs()[LAB])
    assert view["title"] == "Outrigger shrimp trawl" and view["steps"] == 4
    assert "answer" not in str(view["step_list"])
