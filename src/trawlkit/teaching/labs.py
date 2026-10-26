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
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import asdict, dataclass
from functools import cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from trawlkit.io import DATA_DIR
from trawlkit.teaching.bank import DEFAULT_TOL_REL, Level, fmt, parse_number

LABS_DIR = DATA_DIR / "teaching" / "labs"

Op = Literal["==", "!=", "<", "<=", ">", ">="]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Check(_Model):
    """Condición sobre un hecho del caso del alumno."""

    fact: str
    op: Op
    value: float | str | None = None
    baseline_factor: float | None = Field(
        default=None, description="Compara con el hecho del caso de partida por este factor"
    )
    label: str

    @model_validator(mode="after")
    def _one(self) -> Check:
        if (self.value is None) == (self.baseline_factor is None):
            raise ValueError("una comprobación usa value o baseline_factor")
        return self


class Question(_Model):
    """Pregunta de un paso: numérica (contra un hecho), de opción múltiple o abierta."""

    id: str
    kind: Literal["number", "choice", "text"]
    prompt: str
    unit: str = ""
    fact: str | None = None
    tol_rel: float = DEFAULT_TOL_REL
    tol_abs: float = 0.0
    options: list[str] | None = None
    answer: str | None = None

    @model_validator(mode="after")
    def _shape(self) -> Question:
        if self.kind == "number" and not self.fact:
            raise ValueError(f"{self.id}: una pregunta numérica necesita fact")
        if self.kind == "choice" and (not self.options or self.answer not in self.options):
            raise ValueError(f"{self.id}: una opción múltiple necesita options y answer")
        return self


class Target(_Model):
    """Dónde se hace el paso en la app."""

    mode: Literal["expert", "simple"] = "expert"
    tab: str | None = None
    hint: str | None = None


class Step(_Model):
    """Un paso del laboratorio."""

    id: str
    title: str
    instruction: str
    target: Target = Field(default_factory=Target)
    checks: list[Check] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)


class LabSpec(_Model):
    """Laboratorio tal como se escribe en el YAML."""

    id: str = Field(pattern=r"^lab\.[a-z0-9_]+$")
    chapter: str
    topic: str
    level: Level
    title: str
    summary: str
    start: dict[str, Any] = Field(description="Caso de partida (un DesignRequest)")
    steps: list[Step] = Field(min_length=1)
    closing: str = ""


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
            q.id, False if q.kind != "text" else None, text, None, "sin respuesta"
        )
    if q.kind == "text":
        return QuestionResult(q.id, None, text, None, "la corrige el docente")
    if q.kind == "choice":
        ok = str(given).strip() == q.answer
        return QuestionResult(
            q.id, ok, text, q.answer if reveal else None, "correcta" if ok else "no es esa"
        )
    expected = f.get(q.fact or "")
    x = parse_number(given)
    if expected is None or not isinstance(expected, int | float) or not math.isfinite(expected):
        return QuestionResult(q.id, False, text, None, "el caso no tiene ese dato")
    if x is None:
        return QuestionResult(q.id, False, text, None, "no es un número")
    y = float(expected)
    ok = abs(x - y) <= max(q.tol_abs, q.tol_rel * abs(y)) + 1e-12
    return QuestionResult(
        q.id,
        ok,
        text,
        fmt(y) if reveal else None,
        "correcta" if ok else "no coincide con su caso",
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
