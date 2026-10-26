"""Banco de ejercicios: carga, instancias por semilla, solución y corrección (Fase 17).

Cada ejercicio vive en ``data/teaching/exercises/*.yaml`` con un enunciado en plantilla, los datos
(fijos o variables por semilla), las respuestas esperadas con su tolerancia y el nombre de un
*solver* registrado en :mod:`trawlkit.teaching.solvers`. El solver calcula las respuestas con las
mismas funciones del motor que usa el resto del proyecto, así el enunciado, la clave y el libro
nunca se desincronizan.

La semilla 0 da los valores ``default`` de cada dato (los del libro); cualquier otra semilla elige
datos «de pizarrón» con un generador determinista, igual en el servidor y en el teléfono.

Idiomas (Fase 18.1): el YAML se escribe en español y cada ejercicio trae un bloque ``en:`` con el
título, el enunciado, las pistas, la explicación y los rótulos en inglés. Los atributos ``title``,
``statement``, ``hints``, ``explanation`` y ``label`` de los modelos devuelven el texto del idioma
activo (:func:`trawlkit.i18n.get_lang`); el original está en ``title_es``, ``statement_es``…
Los datos, las semillas y las respuestas son los mismos en los dos idiomas.
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
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

from trawlkit.i18n import N_, get_lang, t
from trawlkit.io import DATA_DIR

EXERCISES_DIR = DATA_DIR / "teaching" / "exercises"

Level = Literal["basico", "intermedio", "avanzado"]
LEVELS: tuple[str, ...] = ("basico", "intermedio", "avanzado")
#: Rótulos de los niveles (en español; :func:`level_label` los da en el idioma activo).
LEVEL_LABELS = {"basico": N_("Básico"), "intermedio": N_("Intermedio"), "avanzado": N_("Avanzado")}


def level_label(level: str) -> str:
    """Rótulo del nivel ``level`` en el idioma activo."""
    return t(LEVEL_LABELS[level]) if level in LEVEL_LABELS else level


#: Tolerancia relativa por defecto de una respuesta numérica.
DEFAULT_TOL_REL = 0.02


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


def english() -> bool:
    """Verdadero si el idioma activo es el inglés."""
    return get_lang() == "en"


def localized(es: str, en: str | None) -> str:
    """``en`` si el idioma activo es el inglés y hay traducción; si no, ``es``."""
    return en if en and english() else es


#: Unidades que se escriben con palabras (las demás, HP, kgf, m…, son iguales en los dos idiomas).
WORD_UNITS: tuple[str, ...] = (N_("mallas"), N_("mallas/m"))


def unit_text(unit: str) -> str:
    """La unidad ``unit`` en el idioma activo."""
    return t(unit) if unit in WORD_UNITS else unit


class VarSpec(_Model):
    """Un dato del enunciado.

    Es fijo (``value``), una grilla (``min``/``max``/``step``) o una lista (``choices``);
    ``default`` es el valor de la semilla 0.
    """

    label_es: str = Field(alias="label")
    unit_es: str = Field(default="", alias="unit")
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

    _label_en: str | None = PrivateAttr(default=None)
    _choices_en: dict[str, str] = PrivateAttr(default_factory=dict)

    @property
    def label(self) -> str:
        """Rótulo en el idioma activo."""
        return localized(self.label_es, self._label_en)

    @property
    def label_en(self) -> str | None:
        """Rótulo en inglés (``None`` si falta)."""
        return self._label_en

    @property
    def unit(self) -> str:
        """Unidad en el idioma activo."""
        return unit_text(self.unit_es)

    @property
    def choices_en(self) -> dict[str, str]:
        """Traducción al inglés de las opciones de texto (``"en contra" → "against"``)."""
        return dict(self._choices_en)

    def text_choices(self) -> list[str]:
        """Opciones de texto de la lista (las que necesitan traducción)."""
        return [c for c in self.choices or [] if isinstance(c, str)]

    def display(self, value: Any) -> Any:
        """El valor tal como se muestra: las opciones de texto, traducidas."""
        if isinstance(value, str) and english():
            return self._choices_en.get(value, value)
        return value


class AnswerSpec(_Model):
    """Una respuesta esperada."""

    key: str
    label_es: str = Field(alias="label")
    unit_es: str = Field(default="", alias="unit")
    kind: Literal["number", "code", "choice"] = "number"
    tol_rel: float = Field(default=DEFAULT_TOL_REL, ge=0)
    tol_abs: float = Field(default=0.0, ge=0)
    decimals: int | None = None
    options_es: list[str] | None = Field(default=None, alias="options")

    _label_en: str | None = PrivateAttr(default=None)
    _options_en: list[str] | None = PrivateAttr(default=None)

    @property
    def label(self) -> str:
        """Rótulo en el idioma activo."""
        return localized(self.label_es, self._label_en)

    @property
    def label_en(self) -> str | None:
        """Rótulo en inglés (``None`` si falta)."""
        return self._label_en

    @property
    def unit(self) -> str:
        """Unidad en el idioma activo."""
        return unit_text(self.unit_es)

    @property
    def options(self) -> list[str] | None:
        """Opciones (respuestas de opción múltiple) en el idioma activo."""
        if self.options_es is None:
            return None
        return list(self._options_en if english() and self._options_en else self.options_es)

    @property
    def options_en(self) -> list[str] | None:
        """Opciones en inglés (``None`` si faltan)."""
        return None if self._options_en is None else list(self._options_en)

    def canonical(self, given: Any) -> Any:
        """Una opción escrita en inglés pasada a la original en español (para corregir)."""
        if not self.options_es or not self._options_en:
            return given
        g = _norm_code(given)
        for es, en in zip(self.options_es, self._options_en, strict=True):
            if g == _norm_code(en):
                return es
        return given


class ExerciseEn(_Model):
    """Textos en inglés de un ejercicio (bloque ``en:`` del YAML)."""

    title: str
    statement: str
    hints: list[str] = Field(default_factory=list)
    explanation: str = ""
    vars: dict[str, str] = Field(default_factory=dict, description="Rótulo de cada dato")
    answers: dict[str, str] = Field(default_factory=dict, description="Rótulo de cada respuesta")
    choices: dict[str, dict[str, str]] = Field(
        default_factory=dict, description="Opciones de texto de los datos: español → inglés"
    )
    options: dict[str, list[str]] = Field(
        default_factory=dict, description="Opciones de las respuestas de opción múltiple"
    )


class ExerciseSpec(_Model):
    """Ejercicio del banco tal como se escribe en el YAML."""

    id: str = Field(pattern=r"^[a-z0-9_]+\.[a-z0-9_]+$")
    chapter: str
    topic: str
    level: Level
    title_es: str = Field(alias="title")
    statement_es: str = Field(alias="statement")
    vars: dict[str, VarSpec] = Field(default_factory=dict)
    solver: str
    answers: list[AnswerSpec] = Field(min_length=1)
    hints_es: list[str] = Field(default_factory=list, alias="hints")
    explanation_es: str = Field(default="", alias="explanation")
    refs: list[str] = Field(default_factory=list)
    formats: dict[str, int] = Field(
        default_factory=dict, description="Decimales de valores intermedios de la explicación"
    )
    en: ExerciseEn | None = None

    @model_validator(mode="after")
    def _english(self) -> ExerciseSpec:
        en = self.en
        if en is None:
            return self
        keys = {a.key for a in self.answers}
        for name, known in (
            ("vars", set(self.vars)),
            ("choices", set(self.vars)),
            ("answers", keys),
            ("options", keys),
        ):
            extra = set(getattr(en, name)) - known
            if extra:
                raise ValueError(f"{self.id}: en.{name} con claves desconocidas {sorted(extra)}")
        for k, v in self.vars.items():
            v._label_en = en.vars.get(k)
            v._choices_en = dict(en.choices.get(k, {}))
            unknown = set(v._choices_en) - set(v.text_choices())
            if unknown:
                raise ValueError(f"{self.id}: en.choices.{k} traduce opciones que no existen")
        for a in self.answers:
            a._label_en = en.answers.get(a.key)
            opts = en.options.get(a.key)
            if opts is not None and len(opts) != len(a.options_es or []):
                raise ValueError(f"{self.id}: en.options.{a.key} no tiene las mismas opciones")
            a._options_en = None if opts is None else list(opts)
        if len(en.hints) not in (0, len(self.hints_es)):
            raise ValueError(f"{self.id}: en.hints no tiene las mismas pistas")
        return self

    def _en(self, name: str) -> Any:
        return getattr(self.en, name) if self.en is not None and english() else None

    @property
    def title(self) -> str:
        """Título en el idioma activo."""
        return localized(self.title_es, self._en("title"))

    @property
    def statement(self) -> str:
        """Enunciado (plantilla) en el idioma activo."""
        return localized(self.statement_es, self._en("statement"))

    @property
    def hints(self) -> list[str]:
        """Pistas (plantillas) en el idioma activo."""
        en = self._en("hints")
        return list(en if en else self.hints_es)

    @property
    def explanation(self) -> str:
        """Explicación (plantilla) en el idioma activo."""
        return localized(self.explanation_es, self._en("explanation"))


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
    """Número con los separadores del idioma activo; textos tal cual.

    Español: coma decimal y espacio de miles (``1 234,5``); inglés: ``1,234.5``.
    """
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
    text = f"{v:,.{decimals}f}"
    if not english():
        text = text.replace(",", " ").replace(".", ",")
    return "0" if re.fullmatch(r"-0([.,]0*)?", text) else text


_NUM = re.compile(r"^[+-]?\d+(\.\d+)?([eE][+-]?\d+)?$")
_THOUSANDS_COMMA = re.compile(r"^[+-]?\d{1,3}(,\d{3})+$")


def parse_number(text: Any) -> float | None:
    """Lee una respuesta numérica escrita con coma o con punto decimal (``None`` si no se puede).

    Se aceptan las dos convenciones en los dos idiomas: ``1 234,5``, ``1.234,5``, ``1,234.5`` y
    ``1234.5``. Con los dos separadores, el último es el decimal; varias comas que agrupan de a
    tres son miles (``1,234,567``). Una coma sola es decimal (``38,75``), salvo en inglés cuando
    agrupa miles (``1,234``); :func:`number_readings` da las dos lecturas de ese caso dudoso.
    """
    readings = number_readings(text)
    return readings[0] if readings else None


def number_readings(text: Any) -> list[float]:
    """Lecturas posibles de una respuesta numérica, la del idioma activo primero.

    Sólo ``1,234`` (una coma seguida de tres cifras) tiene dos: mil doscientos treinta y cuatro
    (inglés) o uno coma dos tres cuatro (español). La corrección se queda con la más cercana a la
    respuesta esperada, así que el alumno puede escribir con la convención de cualquier idioma.
    """
    if isinstance(text, bool):
        return []
    if isinstance(text, int | float):
        v = float(text)
        return [v] if math.isfinite(v) else []
    s = str(text).strip().replace(" ", "").replace("\u00a0", "").replace("\u202f", "")
    if not s:
        return []
    alt: str | None = None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        if _THOUSANDS_COMMA.match(s) and s.count(",") > 1:
            s = s.replace(",", "")
        elif _THOUSANDS_COMMA.match(s):
            grouped, decimal = s.replace(",", ""), s.replace(",", ".")
            s, alt = (grouped, decimal) if english() else (decimal, grouped)
        else:
            s = s.replace(",", ".")
    out = [float(x) for x in (s, alt) if x is not None and _NUM.match(x)]
    return [v for v in out if math.isfinite(v)]


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
        if spec is not None:
            out[k] = fmt(spec.display(v), spec.decimals)
        else:
            out[k] = fmt(v, ex.formats.get(k))
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
        DataItem(k, t(label), values[k], unit_text(unit), texts[k])
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
    specs = {a.key: a for a in ex.answers}
    for k, v in result.items():
        a = specs.get(k)
        nd = a.decimals if a is not None else None
        texts[k] = fmt(v, nd if nd is not None else ex.formats.get(k))
        if a is not None and isinstance(v, str) and a.options_es and v in a.options_es:
            texts[k] = (a.options or a.options_es)[a.options_es.index(v)]
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
            msg = t("sin respuesta")
        elif spec.kind == "number":
            y = float(expected)
            readings = number_readings(given)
            x = min(readings, key=lambda r: abs(r - y)) if readings else None
            if x is None:
                msg = t("no es un número")
            else:
                err = abs(x - y) / abs(y) if y else abs(x - y)
                ok = abs(x - y) <= max(spec.tol_abs, spec.tol_rel * abs(y)) + 1e-12
                factor = abs(x / y) if y else 0.0
                if not ok and (0.0009 < factor < 0.0011 or 900 < factor < 1100):
                    msg = t("revise las unidades (difiere en un factor 1000)")
                elif not ok:
                    msg = t("fuera de la tolerancia")
        else:
            ok = _norm_code(spec.canonical(given)) == _norm_code(expected)
            msg = "" if ok else t("no coincide")
        out.append(
            AnswerGrade(
                key=spec.key,
                ok=ok,
                given=given_text,
                expected=expected if reveal else None,
                expected_text=sol.texts[spec.key] if reveal else None,
                error_rel=err,
                message=t("correcta") if ok else msg,
            )
        )
    score = sum(a.ok for a in out) / len(out)
    return Grade(ex.id, seed, score, out, sol.explanation if reveal else None)
