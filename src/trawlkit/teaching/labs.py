"""Laboratorios guiados sobre la app (Fase 17).

Un laboratorio (``data/teaching/labs/*.yaml``) es una secuencia de pasos sobre el caso de diseño
que el alumno tiene abierto en la app: cada paso dice qué hacer y dónde (``target``: pestaña de la
app), comprueba que se hizo (``checks``) y hace preguntas.

Las comprobaciones y las respuestas numéricas no se escriben a mano: se evalúan sobre *hechos*
que el motor calcula para el caso del alumno (:func:`facts`): el resumen del diseño
(``summary.max_speed_kn``), la red (``net.codend_mesh_mm``), el buque (``vessel.bhp``), los
parámetros del caso (``case.depth_m``) y, si hace falta, la guía de construcción
(``construction.joins``). Una comprobación compara un hecho con un valor fijo o con el mismo hecho
en el caso de partida del laboratorio (``baseline``). No hay ``eval``: sólo ruta, comparador y
valor.

Idiomas (Fase 18.1): los textos se escriben en español y cada objeto trae un bloque ``en:`` con su
traducción; los atributos (``title``, ``instruction``, ``label``, ``prompt``…) devuelven el texto
del idioma activo. Las opciones de las preguntas de opción múltiple tienen un ``id`` estable
(``answer`` es un id) y se corrigen por id o por el texto de la opción en cualquier idioma.
"""

from __future__ import annotations

import dataclasses
import math
import re
from dataclasses import asdict, dataclass
from functools import cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from trawlkit.i18n import t
from trawlkit.io import DATA_DIR
from trawlkit.teaching.bank import (
    DEFAULT_TOL_REL,
    Level,
    english,
    fmt,
    localized,
    number_readings,
)

LABS_DIR = DATA_DIR / "teaching" / "labs"

Op = Literal["==", "!=", "<", "<=", ">", ">="]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class CheckEn(_Model):
    """Comprobación en inglés."""

    label: str


class QuestionEn(_Model):
    """Pregunta en inglés."""

    prompt: str


class TargetEn(_Model):
    """Indicación del paso en inglés."""

    hint: str


class StepEn(_Model):
    """Paso en inglés."""

    title: str
    instruction: str


class LabEn(_Model):
    """Laboratorio en inglés."""

    title: str
    summary: str
    closing: str = ""


def _norm_text(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text)).strip().casefold()


class Option(_Model):
    """Opción de una pregunta de opción múltiple: id estable y texto en cada idioma."""

    id: str = Field(pattern=r"^[a-z0-9_]+$")
    es: str
    en: str | None = None

    @property
    def text(self) -> str:
        """Texto en el idioma activo."""
        return localized(self.es, self.en)

    def matches(self, given: Any) -> bool:
        """Verdadero si ``given`` es el id o el texto de la opción en algún idioma."""
        g = _norm_text(given)
        return g in {_norm_text(x) for x in (self.id, self.es, self.en) if x}


class Check(_Model):
    """Condición sobre un hecho del caso del alumno."""

    fact: str
    op: Op
    value: float | str | None = None
    baseline_factor: float | None = Field(
        default=None, description="Compara con el hecho del caso de partida por este factor"
    )
    label_es: str = Field(alias="label")
    en: CheckEn | None = None

    @property
    def label(self) -> str:
        """Rótulo en el idioma activo."""
        return localized(self.label_es, self.en.label if self.en else None)

    @model_validator(mode="after")
    def _one(self) -> Check:
        if (self.value is None) == (self.baseline_factor is None):
            raise ValueError("una comprobación usa value o baseline_factor")
        return self


class Question(_Model):
    """Pregunta de un paso: numérica (contra un hecho), de opción múltiple o abierta."""

    id: str
    kind: Literal["number", "choice", "text"]
    prompt_es: str = Field(alias="prompt")
    unit: str = ""
    fact: str | None = None
    tol_rel: float = DEFAULT_TOL_REL
    tol_abs: float = 0.0
    choices: list[Option] | None = Field(default=None, alias="options")
    answer: str | None = Field(default=None, description="Id de la opción correcta")
    en: QuestionEn | None = None

    @model_validator(mode="after")
    def _shape(self) -> Question:
        if self.kind == "number" and not self.fact:
            raise ValueError(f"{self.id}: una pregunta numérica necesita fact")
        ids = [o.id for o in self.choices or []]
        if self.kind == "choice" and (not ids or self.answer not in ids):
            raise ValueError(f"{self.id}: una opción múltiple necesita options y answer (un id)")
        if len(set(ids)) != len(ids):
            raise ValueError(f"{self.id}: ids de opción repetidos")
        return self

    @property
    def prompt(self) -> str:
        """Pregunta en el idioma activo."""
        return localized(self.prompt_es, self.en.prompt if self.en else None)

    @property
    def options(self) -> list[str] | None:
        """Textos de las opciones en el idioma activo (``None`` si no es de opción múltiple)."""
        return None if self.choices is None else [o.text for o in self.choices]

    @property
    def option_ids(self) -> list[str] | None:
        """Ids de las opciones, en el mismo orden que :attr:`options`."""
        return None if self.choices is None else [o.id for o in self.choices]

    def option_for(self, given: Any) -> Option | None:
        """La opción que nombra ``given`` (por id o por su texto en cualquier idioma)."""
        return next((o for o in self.choices or [] if o.matches(given)), None)

    def answer_text(self) -> str | None:
        """Texto de la opción correcta en el idioma activo."""
        opt = next((o for o in self.choices or [] if o.id == self.answer), None)
        return None if opt is None else opt.text


class Target(_Model):
    """Dónde se hace el paso en la app."""

    mode: Literal["expert", "simple"] = "expert"
    tab: str | None = None
    hint_es: str | None = Field(default=None, alias="hint")
    en: TargetEn | None = None

    @property
    def hint(self) -> str | None:
        """Indicación en el idioma activo."""
        if self.hint_es is None:
            return None
        return localized(self.hint_es, self.en.hint if self.en else None)


class Step(_Model):
    """Un paso del laboratorio."""

    id: str
    title_es: str = Field(alias="title")
    instruction_es: str = Field(alias="instruction")
    target: Target = Field(default_factory=Target)
    checks: list[Check] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)
    en: StepEn | None = None

    @property
    def title(self) -> str:
        """Título en el idioma activo."""
        return localized(self.title_es, self.en.title if self.en else None)

    @property
    def instruction(self) -> str:
        """Consigna en el idioma activo."""
        return localized(self.instruction_es, self.en.instruction if self.en else None)


class LabSpec(_Model):
    """Laboratorio tal como se escribe en el YAML."""

    id: str = Field(pattern=r"^lab\.[a-z0-9_]+$")
    chapter: str
    topic: str
    level: Level
    title_es: str = Field(alias="title")
    summary_es: str = Field(alias="summary")
    start: dict[str, Any] = Field(description="Caso de partida (un DesignRequest)")
    steps: list[Step] = Field(min_length=1)
    closing_es: str = Field(default="", alias="closing")
    en: LabEn | None = None

    def _en(self, name: str) -> str | None:
        return getattr(self.en, name) if self.en is not None and english() else None

    @property
    def title(self) -> str:
        """Título en el idioma activo."""
        return localized(self.title_es, self._en("title"))

    @property
    def summary(self) -> str:
        """Resumen en el idioma activo."""
        return localized(self.summary_es, self._en("summary"))

    @property
    def closing(self) -> str:
        """Cierre en el idioma activo."""
        return localized(self.closing_es, self._en("closing"))


class _File(_Model):
    labs: list[LabSpec]


@cache
def load_labs() -> dict[str, LabSpec]:
    """Todos los laboratorios, por id."""
    out: dict[str, LabSpec] = {}
    for path in sorted(Path(LABS_DIR).glob("*.yaml")):
        with path.open(encoding="utf-8") as fh:
            data = _File.model_validate(yaml.safe_load(fh))
        for lab in data.labs:
            if lab.id in out:
                raise ValueError(f"laboratorio repetido: {lab.id}")
            out[lab.id] = lab
    return out


class UnknownLabError(KeyError):
    """Id de laboratorio o de paso que no existe."""


def lab(lab_id: str) -> LabSpec:
    """El laboratorio ``lab_id``."""
    try:
        return load_labs()[lab_id]
    except KeyError:
        raise UnknownLabError(lab_id) from None


def lab_view(spec: LabSpec) -> dict[str, Any]:
    """El laboratorio en el idioma activo, sin las respuestas (``LabOut`` de la API).

    Las preguntas de opción múltiple dan los textos (``options``) y sus ids (``option_ids``); la
    corrección acepta cualquiera de los dos.
    """
    steps = [
        {
            "id": s.id,
            "title": s.title,
            "instruction": s.instruction,
            "target": {"mode": s.target.mode, "tab": s.target.tab, "hint": s.target.hint},
            "checks": [{"label": c.label, "fact": c.fact, "op": c.op} for c in s.checks],
            "questions": [
                {
                    "id": q.id,
                    "kind": q.kind,
                    "prompt": q.prompt,
                    "unit": q.unit,
                    "options": q.options,
                    "option_ids": q.option_ids,
                }
                for q in s.questions
            ],
        }
        for s in spec.steps
    ]
    return {
        "id": spec.id,
        "chapter": spec.chapter,
        "topic": spec.topic,
        "level": spec.level,
        "title": spec.title,
        "summary": spec.summary,
        "steps": len(spec.steps),
        "start": spec.start,
        "step_list": steps,
        "closing": spec.closing,
    }


def labs(chapter: str | None = None, level: str | None = None) -> list[LabSpec]:
    """Laboratorios filtrados por capítulo o nivel."""
    return [
        x
        for x in load_labs().values()
        if (chapter is None or x.chapter == chapter) and (level is None or x.level == level)
    ]


# --- hechos ------------------------------------------------------------------------------------


def _scalar(v: Any) -> bool:
    return isinstance(v, bool | int | float | str) or v is None


def _min_of(values: list[float]) -> float | None:
    return min(values) if values else None


def facts(request: dict[str, Any], *, construction: bool = False) -> dict[str, Any]:
    """Hechos del caso ``request`` (un ``DesignRequest`` como diccionario) según el motor."""
    from trawlkit.api import service
    from trawlkit.api.schemas import DesignRequest

    req = DesignRequest.model_validate(request)
    with service.user_items(req.components):
        case = service.build_case(
            net=req.net,
            net_modified=req.net_modified,
            vessel=req.vessel,
            door=req.door,
            class_vessels=req.class_vessels,
            compat=req.compat,
            params=req.params,
        )
        result = service.run_case(case)
    out: dict[str, Any] = {}
    for k, v in result.summary().items():
        if _scalar(v):
            out[f"summary.{k}"] = v
    for f in dataclasses.fields(case):
        v = getattr(case, f.name)
        if _scalar(v):
            out[f"case.{f.name}"] = v.value if hasattr(v, "value") else v
    spec = case.net
    codend = [p for p in spec.panels if str(p.section) == "codend"]
    body = [p for p in spec.panels if str(p.section) in ("body", "square", "belly")]
    wings = [p for p in spec.panels if str(p.section) in ("wing", "wing_tip")]
    out.update(
        {
            "net.id": spec.id,
            "net.name": spec.name,
            "net.panels": len(spec.panels),
            "net.codend_mesh_mm": _min_of([p.mesh_mm for p in codend]),
            "net.codend_twine_mm": _min_of([p.twine_diameter_mm for p in codend]),
            "net.codend_orientation": str(codend[0].mesh_orientation) if codend else None,
            "net.body_twine_mm": _min_of([p.twine_diameter_mm for p in body]),
            "net.body_twine_max_mm": max((p.twine_diameter_mm for p in body), default=None),
            "net.wing_mesh_mm": _min_of([p.mesh_mm for p in wings]),
            "vessel.id": case.vessel.id,
            "vessel.bhp": case.vessel.bhp,
            "door.id": case.door.id,
        }
    )
    if construction:
        g = service._guide(case, "std", 0.5)
        out["construction.pieces"] = len(g.pieces)
        out["construction.joins"] = len(g.joins)
        out["construction.stock_kg"] = sum(s.weight_kg for s in g.stock)
    return out


def _needs_construction(spec: LabSpec) -> bool:
    paths = [c.fact for s in spec.steps for c in s.checks]
    paths += [q.fact or "" for s in spec.steps for q in s.questions]
    return any(p.startswith("construction.") for p in paths)


@cache
def baseline_facts(lab_id: str) -> dict[str, Any]:
    """Hechos del caso de partida del laboratorio."""
    spec = lab(lab_id)
    return facts(spec.start, construction=_needs_construction(spec))


def _compare(a: Any, op: str, b: Any) -> bool:
    if isinstance(a, str) or isinstance(b, str):
        a, b = str(a), str(b)
        return bool({"==": a == b, "!=": a != b}.get(op, False))
    if a is None or b is None:
        return False
    x, y = float(a), float(b)
    tol = 1e-9 * max(1.0, abs(y))
    return {
        "==": abs(x - y) <= tol,
        "!=": abs(x - y) > tol,
        "<": x < y - tol,
        "<=": x <= y + tol,
        ">": x > y + tol,
        ">=": x >= y - tol,
    }[op]


@dataclass(frozen=True)
class CheckResult:
    """Resultado de una comprobación."""

    label: str
    ok: bool
    fact: str
    value: Any
    target: Any


@dataclass(frozen=True)
class QuestionResult:
    """Corrección de una pregunta (``ok`` es ``None`` en las abiertas: las corrige el docente)."""

    id: str
    ok: bool | None
    given: str | None
    expected_text: str | None
    message: str


@dataclass(frozen=True)
class StepResult:
    """Estado de un paso para el caso del alumno."""

    lab_id: str
    step_id: str
    done: bool
    checks: list[CheckResult]
    questions: list[QuestionResult]
    values: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return asdict(self)


def _step(spec: LabSpec, step_id: str) -> Step:
    for s in spec.steps:
        if s.id == step_id:
            return s
    raise UnknownLabError(f"{spec.id}:{step_id}")


def _grade_question(q: Question, given: Any, f: dict[str, Any], reveal: bool) -> QuestionResult:
    text = None if given is None else str(given)
    if given is None or str(given).strip() == "":
        return QuestionResult(
            q.id, False if q.kind != "text" else None, text, None, t("sin respuesta")
        )
    if q.kind == "text":
        return QuestionResult(q.id, None, text, None, t("la corrige el docente"))
    if q.kind == "choice":
        chosen = q.option_for(given)
        ok = chosen is not None and chosen.id == q.answer
        return QuestionResult(
            q.id,
            ok,
            text,
            q.answer_text() if reveal else None,
            t("correcta") if ok else t("no es esa"),
        )
    expected = f.get(q.fact or "")
    if expected is None or not isinstance(expected, int | float) or not math.isfinite(expected):
        return QuestionResult(q.id, False, text, None, t("el caso no tiene ese dato"))
    y = float(expected)
    readings = number_readings(given)
    if not readings:
        return QuestionResult(q.id, False, text, None, t("no es un número"))
    x = min(readings, key=lambda r: abs(r - y))
    ok = abs(x - y) <= max(q.tol_abs, q.tol_rel * abs(y)) + 1e-12
    return QuestionResult(
        q.id,
        ok,
        text,
        fmt(y) if reveal else None,
        t("correcta") if ok else t("no coincide con su caso"),
    )


def lab_check(
    lab_id: str,
    step_id: str,
    request: dict[str, Any],
    answers: dict[str, Any] | None = None,
    *,
    reveal: bool = True,
) -> StepResult:
    """Comprueba el paso ``step_id`` sobre el caso ``request`` y corrige sus preguntas.

    ``done`` es verdadero cuando se cumplen todas las comprobaciones y ninguna pregunta cerrada
    está mal o sin responder (las abiertas sólo tienen que tener texto).
    """
    spec = lab(lab_id)
    step = _step(spec, step_id)
    f = facts(request, construction=_needs_construction(spec))
    base = baseline_facts(lab_id) if any(c.baseline_factor is not None for c in step.checks) else {}
    checks: list[CheckResult] = []
    for c in step.checks:
        value = f.get(c.fact)
        if c.baseline_factor is not None:
            b = base.get(c.fact)
            target: Any = None if b is None else float(b) * c.baseline_factor
        else:
            target = c.value
        checks.append(CheckResult(c.label, _compare(value, c.op, target), c.fact, value, target))
    given = answers or {}
    qs = [_grade_question(q, given.get(q.id), f, reveal) for q in step.questions]
    done = all(c.ok for c in checks) and all(
        (q.ok is not False) and q.given is not None and q.given.strip() != "" for q in qs
    )
    shown = {c.fact for c in step.checks} | {q.fact for q in step.questions if q.fact}
    return StepResult(lab_id, step_id, done, checks, qs, {k: f.get(k) for k in sorted(shown)})
