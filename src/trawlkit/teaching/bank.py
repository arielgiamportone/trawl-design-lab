"""Banco de ejercicios: carga, instancias por semilla, solución y corrección (Fase 17).

Cada ejercicio vive en ``data/teaching/exercises/*.yaml`` con un enunciado en plantilla, los datos
(fijos o variables por semilla), las respuestas esperadas con su tolerancia y el nombre de un
*solver* registrado en :mod:`trawlkit.teaching.solvers`. El solver calcula las respuestas con las
mismas funciones del motor que usa el resto del proyecto, así el enunciado, la clave y el libro
nunca se desincronizan.

La semilla 0 da los valores ``default`` de cada dato (los del libro); cualquier otra semilla elige
datos «de pizarrón» con un generador determinista, igual en el servidor y en el teléfono.
"""

from __future__ import annotations

import math
import random
import re
from dataclasses import asdict, dataclass, field
from functools import cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from trawlkit.io import DATA_DIR

EXERCISES_DIR = DATA_DIR / "teaching" / "exercises"

Level = Literal["basico", "intermedio", "avanzado"]
LEVELS: tuple[str, ...] = ("basico", "intermedio", "avanzado")
LEVEL_LABELS = {"basico": "Básico", "intermedio": "Intermedio", "avanzado": "Avanzado"}

#: Tolerancia relativa por defecto de una respuesta numérica.
DEFAULT_TOL_REL = 0.02


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VarSpec(_Model):
    """Un dato del enunciado.

    Es fijo (``value``), una grilla (``min``/``max``/``step``) o una lista (``choices``);
    ``default`` es el valor de la semilla 0.
    """

    label: str
    unit: str = ""
    value: float | str | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    choices: list[float | str] | None = None
    default: float | str | None = None
    decimals: int | None = None
    show: bool = True

    @model_validator(mode="after")
    def _one_kind(self) -> VarSpec:
        kinds = [
            self.value is not None,
            self.min is not None or self.max is not None,
            self.choices is not None,
        ]
        if sum(kinds) != 1:
            raise ValueError("un dato es fijo (value), una grilla (min/max/step) o una lista")
        if kinds[1] and (self.min is None or self.max is None or not self.step):
            raise ValueError("la grilla necesita min, max y step")
        if kinds[1] and self.max is not None and self.min is not None and self.max < self.min:
            raise ValueError("max < min")
        return self


class AnswerSpec(_Model):
    """Una respuesta esperada."""

    key: str
    label: str
    unit: str = ""
    kind: Literal["number", "code", "choice"] = "number"
    tol_rel: float = Field(default=DEFAULT_TOL_REL, ge=0)
    tol_abs: float = Field(default=0.0, ge=0)
    decimals: int | None = None
    options: list[str] | None = None


class ExerciseSpec(_Model):
    """Ejercicio del banco tal como se escribe en el YAML."""

    id: str = Field(pattern=r"^[a-z0-9_]+\.[a-z0-9_]+$")
    chapter: str
    topic: str
    level: Level
    title: str
    statement: str
    vars: dict[str, VarSpec] = Field(default_factory=dict)
    solver: str
    answers: list[AnswerSpec] = Field(min_length=1)
    hints: list[str] = Field(default_factory=list)
    explanation: str = ""
    refs: list[str] = Field(default_factory=list)
    formats: dict[str, int] = Field(
        default_factory=dict, description="Decimales de valores intermedios de la explicación"
    )


class _File(_Model):
    exercises: list[ExerciseSpec]


@cache
def load_bank() -> dict[str, ExerciseSpec]:
    """Todos los ejercicios del banco, por id (en el orden de los archivos)."""
    out: dict[str, ExerciseSpec] = {}
    for path in sorted(Path(EXERCISES_DIR).glob("*.yaml")):
        with path.open(encoding="utf-8") as fh:
            data = _File.model_validate(yaml.safe_load(fh))
        for ex in data.exercises:
            if ex.id in out:
                raise ValueError(f"ejercicio repetido: {ex.id}")
            out[ex.id] = ex
    return out


class UnknownExerciseError(KeyError):
    """Id de ejercicio que no está en el banco."""


def exercise(exercise_id: str) -> ExerciseSpec:
    """El ejercicio ``exercise_id`` (``UnknownExerciseError`` si no existe)."""
    try:
        return load_bank()[exercise_id]
    except KeyError:
        raise UnknownExerciseError(exercise_id) from None


def bank(
    chapter: str | None = None, level: str | None = None, topic: str | None = None
) -> list[ExerciseSpec]:
    """Ejercicios del banco filtrados por capítulo, nivel o tema."""
    return [
        e
        for e in load_bank().values()
        if (chapter is None or e.chapter == chapter)
        and (level is None or e.level == level)
        and (topic is None or e.topic == topic)
    ]


# --- números ---------------------------------------------------------------------------------


def fmt(x: Any, decimals: int | None = None) -> str:
    """Número con coma decimal y espacio de miles (``1 234,5``); textos tal cual."""
    if isinstance(x, str):
        return x
    if isinstance(x, bool) or x is None:
        return str(x)
    v = float(x)
    if not math.isfinite(v):
        return "—"
    if decimals is None:
        a = abs(v)
        if a == 0 or float(v).is_integer():
            decimals = 0
        elif a >= 100:
            decimals = 0
        elif a >= 10:
            decimals = 1
        elif a >= 1:
            decimals = 2
        else:
            decimals = 3
    text = f"{v:,.{decimals}f}".replace(",", " ").replace(".", ",")
    return "0" if text in ("-0", "-0,0") else text


_NUM = re.compile(r"^[+-]?\d+(\.\d+)?([eE][+-]?\d+)?$")


def parse_number(text: Any) -> float | None:
    """Lee una respuesta numérica escrita con coma o con punto decimal (``None`` si no se puede)."""
    if isinstance(text, bool):
        return None
    if isinstance(text, int | float):
        v = float(text)
        return v if math.isfinite(v) else None
    s = str(text).strip().replace(" ", "").replace(" ", "")
    if not s:
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    if not _NUM.match(s):
        return None
    return float(s)


def _norm_code(text: Any) -> str:
    return re.sub(r"\s+", "", str(text)).upper()


# --- instancias ------------------------------------------------------------------------------


def _pick(spec: VarSpec, rng: random.Random, seed: int) -> float | str:
    if spec.value is not None:
        return spec.value
    if spec.choices is not None:
        if seed == 0:
            return spec.default if spec.default is not None else spec.choices[0]
        return rng.choice(spec.choices)
    lo, hi, step = float(spec.min or 0), float(spec.max or 0), float(spec.step or 1)
    if seed == 0:
        return spec.default if spec.default is not None else lo
    n = int(math.floor((hi - lo) / step + 1e-9))
    v = lo + step * rng.randint(0, n)
    nd = max(0, -math.floor(math.log10(step))) if step < 1 else 0
    return round(v, nd + 2) if nd else float(round(v))


def _values(ex: ExerciseSpec, seed: int) -> dict[str, Any]:
    from trawlkit.teaching.solvers import derive

    rng = random.Random(f"{ex.id}:{seed}")
    raw = {k: _pick(v, rng, seed) for k, v in ex.vars.items()}
    return derive(ex.solver, raw)


@dataclass(frozen=True)
class DataItem:
    """Un dato del enunciado ya elegido."""

    key: str
    label: str
    value: float | str
    unit: str
    text: str


@dataclass(frozen=True)
class AnswerField:
    """Un campo a responder (sin la respuesta)."""

    key: str
    label: str
    unit: str
    kind: str
    options: list[str] | None


@dataclass(frozen=True)
class ExerciseInstance:
    """Un ejercicio con sus datos para una semilla, sin las respuestas."""

    id: str
    seed: int
    chapter: str
    topic: str
    level: str
    title: str
    statement: str
    data: list[DataItem]
    answers: list[AnswerField]
    hints: list[str]
    refs: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return asdict(self)


def _texts(ex: ExerciseSpec, values: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in values.items():
        spec = ex.vars.get(k)
        nd = spec.decimals if spec is not None else ex.formats.get(k)
        out[k] = fmt(v, nd)
    return out


class _Fmt(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def render(template: str, texts: dict[str, str]) -> str:
    """Rellena ``{clave}`` con los textos (las claves desconocidas quedan como están)."""
    return template.format_map(_Fmt(texts)).strip()


def instantiate(exercise_id: str, seed: int = 0) -> ExerciseInstance:
    """El ejercicio con sus datos para ``seed``, listo para mostrar."""
    ex = exercise(exercise_id)
    values = _values(ex, seed)
    texts = _texts(ex, values)
    data = [
        DataItem(k, s.label, values[k], s.unit, texts[k])
        for k, s in ex.vars.items()
        if s.show and k in values
    ]
    data += [
        DataItem(k, label, values[k], unit, texts[k])
        for k, (label, unit) in _derived_labels(ex.solver).items()
        if k in values
    ]
    return ExerciseInstance(
        id=ex.id,
        seed=seed,
        chapter=ex.chapter,
        topic=ex.topic,
        level=ex.level,
        title=ex.title,
        statement=render(ex.statement, texts),
        data=data,
        answers=[AnswerField(a.key, a.label, a.unit, a.kind, a.options) for a in ex.answers],
        hints=[render(h, texts) for h in ex.hints],
        refs=list(ex.refs),
    )


def _derived_labels(solver_name: str) -> dict[str, tuple[str, str]]:
    from trawlkit.teaching.solvers import derived_labels

    return derived_labels(solver_name)


@dataclass(frozen=True)
class Solution:
    """Respuestas y explicación de un ejercicio para una semilla."""

    id: str
    seed: int
    values: dict[str, float | str]
    texts: dict[str, str]
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return asdict(self)


def solve(exercise_id: str, seed: int = 0) -> Solution:
    """Respuestas calculadas con el motor y la explicación con los números de esta semilla."""
    from trawlkit.teaching.solvers import run_solver

    ex = exercise(exercise_id)
    values = _values(ex, seed)
    result = run_solver(ex.solver, values)
    missing = [a.key for a in ex.answers if a.key not in result]
    if missing:
        raise RuntimeError(f"el solver {ex.solver} no devolvió {missing}")
    texts = _texts(ex, values)
    for k, v in result.items():
        nd = next((a.decimals for a in ex.answers if a.key == k), None)
        texts[k] = fmt(v, nd if nd is not None else ex.formats.get(k))
    answers = {a.key: result[a.key] for a in ex.answers}
    return Solution(ex.id, seed, answers, texts, render(ex.explanation, texts))


@dataclass(frozen=True)
class AnswerGrade:
    """Corrección de una respuesta."""

    key: str
    ok: bool
    given: str | None
    expected: float | str | None = None
    expected_text: str | None = None
    error_rel: float | None = None
    message: str = ""


@dataclass(frozen=True)
class Grade:
    """Corrección de un ejercicio."""

    id: str
    seed: int
    score: float
    answers: list[AnswerGrade] = field(default_factory=list)
    explanation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return asdict(self)


def grade(exercise_id: str, seed: int, answers: dict[str, Any], *, reveal: bool = True) -> Grade:
    """Corrige ``answers`` (por clave). Con ``reveal`` devuelve también la respuesta esperada."""
    ex = exercise(exercise_id)
    sol = solve(exercise_id, seed)
    out: list[AnswerGrade] = []
    for spec in ex.answers:
        expected = sol.values[spec.key]
        given = answers.get(spec.key)
        given_text = None if given is None else str(given)
        ok = False
        err: float | None = None
        msg = ""
        if given is None or str(given).strip() == "":
            msg = "sin respuesta"
        elif spec.kind == "number":
            x = parse_number(given)
            y = float(expected)
            if x is None:
                msg = "no es un número"
            else:
                err = abs(x - y) / abs(y) if y else abs(x - y)
                ok = abs(x - y) <= max(spec.tol_abs, spec.tol_rel * abs(y)) + 1e-12
                factor = abs(x / y) if y else 0.0
                if not ok and (0.0009 < factor < 0.0011 or 900 < factor < 1100):
                    msg = "revise las unidades (difiere en un factor 1000)"
                elif not ok:
                    msg = "fuera de la tolerancia"
        else:
            ok = _norm_code(given) == _norm_code(expected)
            msg = "" if ok else "no coincide"
        out.append(
            AnswerGrade(
                key=spec.key,
                ok=ok,
                given=given_text,
                expected=expected if reveal else None,
                expected_text=sol.texts[spec.key] if reveal else None,
                error_rel=err,
                message="correcta" if ok else msg,
            )
        )
    score = sum(a.ok for a in out) / len(out)
    return Grade(ex.id, seed, score, out, sol.explanation if reveal else None)
