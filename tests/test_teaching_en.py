"""Fase 18.1: el modo docente en inglés (banco de ejercicios y laboratorios)."""

from __future__ import annotations

import re
import string

import pytest
from fastapi.testclient import TestClient

from trawlkit.api import service
from trawlkit.api.app import app
from trawlkit.i18n import use_lang
from trawlkit.teaching import grade, instantiate, load_bank, parse_number, solve
from trawlkit.teaching.bank import level_label
from trawlkit.teaching.labs import facts, lab, lab_check, lab_view, load_labs

client = TestClient(app)
IDS = list(load_bank())
LAB_IDS = list(load_labs())
BASE = {"net": "fao_a3_standard", "vessel": "fao_a3_150hp"}
#: Un número con coma decimal (``38,75``) que se haya colado en un texto en inglés.
COMMA_DECIMAL = re.compile(r"\d,\d{1,2}(?!\d)")


def _fields(text: str) -> set[str]:
    return {f for _, f, _, _ in string.Formatter().parse(text) if f}


# --- traducciones completas -------------------------------------------------------------------


@pytest.mark.parametrize("exercise_id", IDS)
def test_every_exercise_has_complete_english(exercise_id: str) -> None:
    spec = load_bank()[exercise_id]
    en = spec.en
    assert en is not None, exercise_id
    assert en.title.strip() and en.statement.strip() and en.explanation.strip()
    assert len(en.hints) == len(spec.hints_es)
    assert all(h.strip() for h in en.hints)
    for k, v in spec.vars.items():
        assert v.label_en, (exercise_id, k)
        # Las opciones de texto con palabras se traducen; los códigos (PF, 1N2B, ids) no.
        words = {c for c in v.text_choices() if " " in c}
        assert words <= set(v.choices_en), (exercise_id, k)
    for a in spec.answers:
        assert a.label_en, (exercise_id, a.key)
        if a.options_es:
            assert a.options_en and len(a.options_en) == len(a.options_es)
    # Las plantillas en inglés usan los mismos datos que las españolas.
    assert _fields(en.statement) == _fields(spec.statement_es), exercise_id
    assert _fields(en.explanation) == _fields(spec.explanation_es), exercise_id


def test_spanish_choice_values_are_translated() -> None:
    sentido = load_bank()["mar.corriente"].vars["sentido"]
    assert sentido.choices_en == {"en contra": "against the tow", "a favor": "with the tow"}


@pytest.mark.parametrize("lab_id", LAB_IDS)
def test_every_lab_has_complete_english(lab_id: str) -> None:
    spec = lab(lab_id)
    assert spec.en is not None and spec.en.title.strip() and spec.en.summary.strip()
    assert bool(spec.en.closing.strip()) == bool(spec.closing_es.strip())
    for s in spec.steps:
        assert s.en is not None and s.en.title.strip() and s.en.instruction.strip(), s.id
        if s.target.hint_es:
            assert s.target.en is not None and s.target.en.hint.strip(), s.id
        for c in s.checks:
            assert c.en is not None and c.en.label.strip(), (s.id, c.fact)
        for q in s.questions:
            assert q.en is not None and q.en.prompt.strip(), (s.id, q.id)
            for o in q.choices or []:
                assert o.en and o.en.strip() and o.es.strip(), (s.id, q.id, o.id)


# --- instancias en inglés ---------------------------------------------------------------------


@pytest.mark.parametrize("exercise_id", IDS)
def test_english_instances_and_solutions(exercise_id: str) -> None:
    for seed in range(6):
        es_inst, es_sol = instantiate(exercise_id, seed), solve(exercise_id, seed)
        with use_lang("en"):
            inst, sol = instantiate(exercise_id, seed), solve(exercise_id, seed)
            spec = load_bank()[exercise_id]
            assert spec.en is not None and inst.title == spec.en.title
            texts = [inst.statement, sol.explanation, *inst.hints]
            for text in texts:
                assert "{" not in text and "}" not in text, text
                assert not COMMA_DECIMAL.search(text), text
            assert all(d.label for d in inst.data) and all(a.label for a in inst.answers)
            assert [d.value for d in inst.data] == [d.value for d in es_inst.data]
            assert sol.values == es_sol.values
            given = {k: str(v) for k, v in sol.values.items()}
            assert grade(exercise_id, seed, given).score == 1.0
            comma = {k: str(v).replace(".", ",") for k, v in sol.values.items()}
            assert grade(exercise_id, seed, comma).score == 1.0


def test_english_numbers_use_dot_decimals() -> None:
    with use_lang("en"):
        inst = instantiate("resistencia.aberdeen", 0)
        sol = solve("resistencia.aberdeen", 0)
    assert "38.75" in inst.statement and "solid area" in inst.statement
    assert sol.texts["rn_kgf"] == "1,592" and "1.592 t" in sol.explanation
    es = instantiate("resistencia.aberdeen", 0)
    assert "38,75" in es.statement and "superficie sólida" in es.statement
    assert solve("resistencia.aberdeen", 0).texts["rn_kgf"] == "1 592"


def test_english_labels_choices_units_and_levels() -> None:
    with use_lang("en"):
        inst = instantiate("mar.corriente", 0)
        assert "against the tow" in inst.statement
        sentido = next(d for d in inst.data if d.key == "sentido")
        assert sentido.value == "en contra" and sentido.text == "against the tow"
        derived = {d.key: d for d in instantiate("panos.corte_simetrico", 0).data}
        assert derived["n"].label == "Meshes in depth (N)" and derived["n"].unit == "meshes"
        assert level_label("intermedio") == "Intermediate"
        assert load_bank()["potencia.fridman_tiro"].answers[0].label.startswith("Available")
    assert level_label("intermedio") == "Intermedio"
    assert instantiate("mar.corriente", 0).data[2].text == "en contra"


def test_english_grading_messages() -> None:
    y = solve("resistencia.aberdeen", 0).values["rn_kgf"]
    with use_lang("en"):
        assert grade("resistencia.aberdeen", 0, {"rn_kgf": y}).answers[0].message == "correct"
        g = grade("resistencia.aberdeen", 0, {"rn_kgf": y * 1.05})
        assert g.answers[0].message == "outside the tolerance"
        assert "units" in grade("resistencia.aberdeen", 0, {"rn_kgf": y / 1000}).answers[0].message
        assert grade("resistencia.aberdeen", 0, {}).answers[0].message == "no answer"
        assert grade("resistencia.aberdeen", 0, {"rn_kgf": "x"}).answers[0].message == (
            "not a number"
        )
        g = grade("panos.corte_simetrico", 0, {"codigo_corte": "AB"})
        assert g.answers[2].message == "does not match"


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("1,592", 1592.0),
        ("1,592.5", 1592.5),
        ("1592.5", 1592.5),
        ("38,75", 38.75),
        ("1.592,5", 1592.5),
        ("1 592,5", 1592.5),
    ],
)
def test_parse_number_in_english(text: str, value: float) -> None:
    with use_lang("en"):
        assert parse_number(text) == value


def test_parse_number_both_separators_in_spanish() -> None:
    assert parse_number("1,592.5") == 1592.5
    assert parse_number("1,592") == 1.592


# --- laboratorios -----------------------------------------------------------------------------


def test_lab_view_in_both_languages() -> None:
    es = lab_view(lab("lab.buque_y_velocidad"))
    with use_lang("en"):
        en = lab_view(lab("lab.buque_y_velocidad"))
    assert es["title"] == "Más potencia, más velocidad" and en["title"] == "More power, more speed"
    q_es, q_en = es["step_list"][1]["questions"][1], en["step_list"][1]["questions"][1]
    assert q_es["options"][2] == "No: la red es la misma"
    assert q_en["options"][2] == "No: the net is the same"
    assert q_es["option_ids"] == q_en["option_ids"] == ["subio", "bajo", "misma_red"]
    assert en["step_list"][1]["target"]["hint"] and en["step_list"][1]["checks"][0]["label"]
    assert en["closing"].startswith("The power")
    assert "answer" not in str(en["step_list"])


@pytest.mark.parametrize("lang", ["es", "en"])
@pytest.mark.parametrize(
    "given",
    ["No: la red es la misma", "misma_red", "No: the net is the same", " no: THE net is the same "],
)
def test_lab_choice_accepts_id_or_text_in_any_language(lang: str, given: str) -> None:
    design = {**BASE, "vessel": "fao_a3_180hp"}
    with use_lang(lang):
        r = lab_check("lab.buque_y_velocidad", "buque", design, {"rn": given})
        q = r.questions[1]
        assert q.ok is True
        assert q.expected_text == (
            "No: the net is the same" if lang == "en" else "No: la red es la misma"
        )
        wrong = lab_check("lab.buque_y_velocidad", "buque", design, {"rn": "Yes, it rose"})
        assert wrong.questions[1].ok is False


def test_lab_messages_in_english() -> None:
    design = {**BASE, "vessel": "fao_a3_180hp"}
    vmax = facts(design)["summary.max_speed_kn"]
    with use_lang("en"):
        r = lab_check(
            "lab.buque_y_velocidad", "buque", design, {"vmax": f"{vmax:.2f}", "rn": "bajo"}
        )
        assert r.done is False
        assert [q.message for q in r.questions] == ["correct", "not that one"]
        assert r.checks[0].label == "Vessel of 180 HP or more"
        r = lab_check("lab.buque_y_velocidad", "buque", design, {"vmax": "9"})
        assert [q.message for q in r.questions] == ["does not match your case", "no answer"]
        r = lab_check("lab.pano_y_resistencia", "hilo", BASE, {"costo": "it breaks"})
        assert r.questions[1].message == "graded by the teacher"


def test_api_in_english() -> None:
    r = client.get("/teaching/exercises/resistencia.aberdeen", params={"seed": 0, "lang": "en"})
    assert r.status_code == 200
    assert r.json()["title"].startswith("Design drag") and "38.75" in r.json()["statement"]
    r = client.get("/teaching/labs/lab.buque_y_velocidad", params={"lang": "en"})
    q = r.json()["step_list"][1]["questions"][1]
    assert q["options"][2] == "No: the net is the same" and q["option_ids"][2] == "misma_red"
    r = client.get("/teaching/exercises", params={"chapter": "14_resistencia", "lang": "en"})
    assert "Design drag (Aberdeen demersal)" in {e["title"] for e in r.json()}
    with use_lang("en"):
        body = service.teaching_lab("lab.profundidad")
        assert body["title"] == "Fishing deeper"
        q = body["step_list"][1]["questions"][2]
        assert q["option_ids"] == ["siempre_5", "baja", "sube"]
        assert q["options"][1] == "No: the deeper, the lower the ratio"
        assert service.teaching_exercise("mar.corriente", 0)["title"].startswith("Towing")
    body = service.teaching_lab("lab.profundidad")
    assert body["step_list"][1]["questions"][2]["options"][1].startswith("No: a más")


def test_ambiguous_comma_is_read_both_ways_when_grading() -> None:
    # «1,543» es 1543 en inglés y 1,543 en español: se corrige con la lectura más cercana.
    for lang in ("es", "en"):
        with use_lang(lang):
            g = grade("resistencia.tauti", 0, {"v_ms": "1,543", "rn_kgf": "2,150"})
            assert g.answers[0].ok and g.answers[1].ok, lang
