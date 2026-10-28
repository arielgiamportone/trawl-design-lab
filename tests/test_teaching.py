"""Fase 17: banco de ejercicios, corrección, laboratorios guiados, API y CLI."""

from __future__ import annotations

import math
import re

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from trawlkit.api import service
from trawlkit.api.app import app
from trawlkit.cli import app as cli
from trawlkit.report.exercises import exercise_sheet_html
from trawlkit.teaching import bank, grade, instantiate, load_bank, parse_number, solve
from trawlkit.teaching import solvers as sv
from trawlkit.teaching.labs import facts, lab_check, load_labs

client = TestClient(app)
IDS = list(load_bank())
BIB = set(
    re.findall(r"^@\w+\{([^,]+),", open("docs/referencias.bib", encoding="utf-8").read(), re.M)
)


def test_bank_size_and_coverage() -> None:
    assert len(IDS) >= 40
    chapters = {e.chapter for e in load_bank().values()}
    for ch in ("10_potencia", "11_panos_y_cortes", "14_resistencia", "17_flotacion_lastre"):
        assert ch in chapters
    assert {e.level for e in load_bank().values()} == {"basico", "intermedio", "avanzado"}


@pytest.mark.parametrize("exercise_id", IDS)
def test_every_exercise_solves_and_grades_for_many_seeds(exercise_id: str) -> None:
    spec = load_bank()[exercise_id]
    assert spec.solver in sv.names()
    assert all(r in BIB for r in spec.refs), spec.refs
    for seed in range(20):
        inst = instantiate(exercise_id, seed)
        assert "{" not in inst.statement, inst.statement
        sol = solve(exercise_id, seed)
        assert "{" not in sol.explanation, sol.explanation
        for a in spec.answers:
            v = sol.values[a.key]
            if a.kind == "number":
                assert isinstance(v, float) and math.isfinite(v)
        given = {k: str(v).replace(".", ",") for k, v in sol.values.items()}
        assert grade(exercise_id, seed, given).score == 1.0


def test_same_seed_same_instance_and_seed_zero_is_the_book() -> None:
    assert instantiate("potencia.fridman_tiro", 9) == instantiate("potencia.fridman_tiro", 9)
    sol = solve("resistencia.aberdeen", 0)
    assert sol.values["rn_kgf"] == pytest.approx(1592.17, abs=0.1)  # R_N de la A-3 a 3 kn
    assert solve("dimensiones.lima_por_piezas", 0).values["lima_m"] == pytest.approx(28.698)
    assert solve("ventana.caso_a3", 0).values["v_max"] == pytest.approx(2.268, abs=1e-3)
    assert solve("flotacion.boyas", 0).values["boyas"] == 12


def test_solvers_match_the_engine() -> None:
    from trawlkit import power
    from trawlkit.io import PropellerType

    ft = solve("potencia.fridman_tiro", 0).values["ft_kgf"]
    assert ft == power.fridman_towing_force_kgf(
        150, 3.0, power.fridman_kf(PropellerType.FIXED_PITCH)
    )
    assert solve("panos.corte_simetrico", 0).values["codigo_corte"] == "1N2B"


def test_grading_tolerance_units_and_formats() -> None:
    sol = solve("resistencia.aberdeen", 0)
    y = sol.values["rn_kgf"]
    assert grade("resistencia.aberdeen", 0, {"rn_kgf": y * 1.019}).score == 1.0
    g = grade("resistencia.aberdeen", 0, {"rn_kgf": y * 1.05})
    assert g.score == 0.0 and g.answers[0].message == "fuera de la tolerancia"
    g = grade("resistencia.aberdeen", 0, {"rn_kgf": y / 1000})
    assert "unidades" in g.answers[0].message
    g = grade("resistencia.aberdeen", 0, {"rn_kgf": "mil"})
    assert g.answers[0].message == "no es un número"
    assert grade("resistencia.aberdeen", 0, {}).answers[0].message == "sin respuesta"
    hidden = grade("resistencia.aberdeen", 0, {"rn_kgf": 1}, reveal=False)
    assert hidden.answers[0].expected is None and hidden.explanation is None
    assert grade("panos.corte_simetrico", 0, {"codigo_corte": " 1n2b "}).answers[2].ok


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("1592", 1592.0),
        ("1592,5", 1592.5),
        ("1.592,5", 1592.5),
        ("1 592", 1592.0),
        ("2.27", 2.27),
        ("-0,5", -0.5),
        ("1e3", 1000.0),
        ("", None),
        ("abc", None),
        ("1,2,3", None),
    ],
)
def test_parse_number(text: str, value: float | None) -> None:
    assert parse_number(text) == value


def test_bank_filters() -> None:
    assert all(e.level == "basico" for e in bank(level="basico"))
    assert {e.chapter for e in bank(chapter="37_economia")} == {"37_economia"}


# --- laboratorios -----------------------------------------------------------------------------

BASE = {"net": "fao_a3_standard", "vessel": "fao_a3_150hp"}


def test_labs_load_and_reference_real_facts() -> None:
    labs = load_labs()
    assert len(labs) >= 7
    for x in labs.values():
        # Los hechos del caso de partida de cada laboratorio (los de tangones tienen más).
        known = set(facts(x.start, construction=True))
        for s in x.steps:
            for c in s.checks:
                assert c.fact in known, (x.id, c.fact)
            for q in s.questions:
                assert q.fact is None or q.fact in known, (x.id, q.fact)


def test_lab_step_checks_and_questions() -> None:
    r = lab_check("lab.buque_y_velocidad", "buque", BASE, {})
    assert not r.done and not r.checks[0].ok
    vmax = facts({**BASE, "vessel": "fao_a3_180hp"})["summary.max_speed_kn"]
    r = lab_check(
        "lab.buque_y_velocidad",
        "buque",
        {**BASE, "vessel": "fao_a3_180hp"},
        {"vmax": f"{vmax:.2f}".replace(".", ","), "rn": "No: la red es la misma"},
    )
    assert r.done and all(c.ok for c in r.checks) and all(q.ok for q in r.questions)
    wrong = lab_check(
        "lab.buque_y_velocidad",
        "buque",
        {**BASE, "vessel": "fao_a3_180hp"},
        {"vmax": "9", "rn": "Sí, subió"},
    )
    assert not wrong.done and [q.ok for q in wrong.questions] == [False, False]


def test_lab_inline_net_and_open_questions() -> None:
    spec = service.net_preset("fao_a3_standard").model_copy(deep=True)
    for p in spec.panels:
        if str(p.section) in ("body", "square", "belly"):
            p.twine_diameter_mm = 0.9
    design = {**BASE, "net": spec.model_dump(mode="json")}
    vmax = facts(design)["summary.max_speed_kn"]
    r = lab_check("lab.pano_y_resistencia", "hilo", design, {"vmax": vmax, "costo": "se rompe"})
    assert r.done
    assert r.questions[1].ok is None and r.questions[1].message == "la corrige el docente"


def test_lab_construction_facts() -> None:
    f = facts(BASE, construction=True)
    assert f["construction.joins"] > 5 and f["construction.pieces"] == 10
    r = lab_check("lab.taller", "armado", BASE, {"uniones": f["construction.joins"]})
    assert r.questions[0].ok


# --- API, CLI e informe -----------------------------------------------------------------------


def test_api_routes() -> None:
    r = client.get("/teaching/exercises", params={"chapter": "10_potencia"})
    assert r.status_code == 200 and len(r.json()) >= 3
    r = client.get("/teaching/exercises/potencia.fridman_tiro", params={"seed": 4})
    body = r.json()
    assert r.status_code == 200 and body["seed"] == 4 and "ft_kgf" not in str(body["data"])
    r = client.post(
        "/teaching/grade", json={"id": "potencia.fridman_tiro", "answers": {"ft_kgf": "1185"}}
    )
    assert r.json()["score"] == 1.0
    assert client.get("/teaching/exercises/x.y").status_code == 404
    lab = client.get("/teaching/labs/lab.buque_y_velocidad").json()
    assert "answer" not in str(lab["step_list"])
    assert client.get("/teaching/labs/lab.nada").status_code == 404
    r = client.post(
        "/teaching/labs/check",
        json={"lab_id": "lab.buque_y_velocidad", "step_id": "nada", "design": {}},
    )
    assert r.status_code == 404


def test_cli_and_sheet(tmp_path: object) -> None:
    runner = CliRunner()
    res = runner.invoke(cli, ["exercises", "list", "--chapter", "14_resistencia"])
    assert res.exit_code == 0 and "resistencia.aberdeen" in res.output
    res = runner.invoke(cli, ["exercises", "solve", "resistencia.aberdeen"])
    assert res.exit_code == 0 and "1 592" in res.output
    res = runner.invoke(cli, ["exercises", "show", "nada"])
    assert res.exit_code != 0
    items = [(instantiate("resistencia.aberdeen", 1), solve("resistencia.aberdeen", 1))]
    html = exercise_sheet_html(items, title="TP 1")
    assert "Clave de respuestas" in html and "TP 1" in html
    blank = exercise_sheet_html([(instantiate("resistencia.aberdeen", 1), None)])
    assert "Enunciados" in blank and "class='blank'" in blank
