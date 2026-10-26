"""Rutas del aula (``/classroom``, Fase 17.2): cuentas, cursos, tareas, entregas y notas.

Sólo en línea: necesitan la base de datos (``DATABASE_URL``) y el extra ``classroom``; sin ellos
responden 503 y el resto de la API sigue igual. La sesión viaja como token *bearer*
(``Authorization: Bearer …``), sin cookies.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable, Iterator
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/classroom", tags=["aula"])

NOT_CONFIGURED = (
    "El aula no está habilitada en este servidor: falta la base de datos (DATABASE_URL). "
    "Los ejercicios de práctica y los laboratorios funcionan igual."
)


# --- esquemas ----------------------------------------------------------------------------------


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegisterIn(_In):
    """Alta: alumno con código de curso o docente con código de invitación."""

    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=8, max_length=200)
    display_name: str = Field(min_length=1, max_length=80)
    course_code: str | None = Field(default=None, max_length=20)
    invite_code: str | None = Field(default=None, max_length=20)


class LoginIn(_In):
    """Inicio de sesión."""

    username: str = Field(max_length=40)
    password: str = Field(max_length=200)


class UserOut(BaseModel):
    """Usuario."""

    id: int
    username: str
    display_name: str
    role: Literal["admin", "teacher", "student"]


class CourseOut(BaseModel):
    """Curso (el código sólo para sus docentes)."""

    id: int
    name: str
    term: str
    archived: bool
    students: int
    teachers: list[str]
    role: str | None
    code: str | None


class SessionOut(BaseModel):
    """Token de sesión y usuario."""

    token: str
    user: UserOut


class MeOut(UserOut):
    """Usuario con sus cursos."""

    courses: list[CourseOut]


class PasswordIn(_In):
    """Cambio de contraseña."""

    old_password: str = Field(max_length=200)
    new_password: str = Field(min_length=8, max_length=200)


class DeleteMeIn(_In):
    """Confirmación para borrar la cuenta."""

    password: str = Field(max_length=200)


class InvitesIn(_In):
    """Invitaciones nuevas para docentes."""

    count: int = Field(default=1, ge=1, le=50)
    days: int = Field(default=30, ge=1, le=365)


class InviteOut(BaseModel):
    """Invitación."""

    code: str
    expires_at: dt.datetime
    used_by: str | None
    created_at: dt.datetime


class CourseIn(_In):
    """Curso nuevo."""

    name: str = Field(min_length=1, max_length=120)
    term: str = Field(default="", max_length=40)


class CoursePatch(_In):
    """Cambios de un curso."""

    name: str | None = Field(default=None, max_length=120)
    term: str | None = Field(default=None, max_length=40)
    archived: bool | None = None
    new_code: bool = False


class JoinIn(_In):
    """Sumarse a un curso."""

    code: str = Field(max_length=20)


class TeacherIn(_In):
    """Otro docente para el curso."""

    username: str = Field(max_length=40)


class ResetPasswordIn(_In):
    """Contraseña nueva para un alumno."""

    password: str = Field(min_length=8, max_length=200)


class ItemIn(_In):
    """Ítem de una tarea: un ejercicio o un laboratorio del banco."""

    kind: Literal["exercise", "lab"]
    ref: str
    points: float = Field(default=1.0, gt=0, le=100)


class ItemOut(BaseModel):
    """Ítem de una tarea con su título."""

    kind: Literal["exercise", "lab"]
    ref: str
    points: float
    title: str


class AssignmentIn(_In):
    """Tarea nueva."""

    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=4000)
    items: list[ItemIn] = Field(min_length=1, max_length=40)
    opens_at: dt.datetime | None = None
    due_at: dt.datetime | None = None
    max_attempts: int = Field(default=3, ge=1, le=20)
    feedback: Literal["immediate", "after_due"] = "immediate"
    per_student_data: bool = True


class AssignmentPatch(_In):
    """Cambios de una tarea."""

    title: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    items: list[ItemIn] | None = Field(default=None, max_length=40)
    opens_at: dt.datetime | None = None
    due_at: dt.datetime | None = None
    max_attempts: int | None = Field(default=None, ge=1, le=20)
    feedback: Literal["immediate", "after_due"] | None = None
    per_student_data: bool | None = None


class ProgressOut(BaseModel):
    """Avance de un alumno en una tarea."""

    items: int
    submitted: int


class AssignmentOut(BaseModel):
    """Tarea."""

    id: int
    course_id: int
    title: str
    description: str
    items: list[ItemOut]
    opens_at: dt.datetime | None
    due_at: dt.datetime | None
    max_attempts: int
    feedback: Literal["immediate", "after_due"]
    per_student_data: bool
    open: bool
    closed: bool
    progress: ProgressOut | None = None


class StudentSubmissionOut(BaseModel):
    """Entrega vista por el alumno (según la política de devolución)."""

    id: int
    item: int
    attempt: int
    created_at: dt.datetime
    score: float | None
    teacher_score: float | None
    comment: str
    result: dict[str, Any] | None
    message: str


class StudentItemOut(BaseModel):
    """Ítem de la tarea para el alumno: sus datos y sus entregas."""

    index: int
    kind: Literal["exercise", "lab"]
    ref: str
    points: float
    title: str
    attempts_used: int
    attempts_left: int
    submissions: list[StudentSubmissionOut]
    exercise: dict[str, Any] | None = None
    lab: dict[str, Any] | None = None


class AssignmentViewOut(AssignmentOut):
    """Tarea con los ítems del alumno (vacío para el docente)."""

    item_list: list[StudentItemOut] = Field(default_factory=list)


class SubmitIn(_In):
    """Entrega de un ítem: respuestas de un ejercicio o pasos de un laboratorio."""

    answers: dict[str, str | float] = Field(default_factory=dict)
    steps: dict[str, dict[str, Any]] | None = Field(
        default=None,
        description="Laboratorio: por paso, {design: DesignRequest, answers: {pregunta: valor}}",
    )


class GradeCellOut(BaseModel):
    """Celda de la planilla: la mejor entrega de un ítem."""

    item: int
    attempts: int
    score: float | None
    submission_id: int | None
    needs_review: bool


class GradeRowOut(BaseModel):
    """Fila de la planilla: un alumno."""

    student: UserOut
    cells: list[GradeCellOut]
    points: float


class GradesOut(BaseModel):
    """Planilla de notas de una tarea."""

    assignment: AssignmentOut
    total_points: float
    rows: list[GradeRowOut]


class SubmissionOut(BaseModel):
    """Entrega completa (vista del docente)."""

    id: int
    assignment_id: int
    item: int
    item_info: ItemOut
    student: UserOut | None
    attempt: int
    seed: int
    answers: dict[str, Any]
    design: dict[str, Any] | None
    auto_score: float | None
    teacher_score: float | None
    comment: str
    result: dict[str, Any]
    created_at: dt.datetime


class ReviewIn(_In):
    """Nota del docente (0 a 1; nula vuelve a la automática) y comentario."""

    teacher_score: float | None = Field(default=None, ge=0, le=1)
    comment: str | None = Field(default=None, max_length=4000)


class StatusOut(BaseModel):
    """Estado del aula en este servidor."""

    enabled: bool
    detail: str


# --- dependencias -------------------------------------------------------------------------------


def _session() -> Iterator[Any]:
    try:
        from trawlkit.classroom import db
    except ImportError as exc:  # pragma: no cover - depende de los extras instalados
        raise HTTPException(503, NOT_CONFIGURED) from exc
    try:
        with db.session() as s:
            yield s
    except db.NotConfiguredError as exc:
        raise HTTPException(503, NOT_CONFIGURED) from exc


Db = Annotated[Any, Depends(_session)]
Auth = Annotated[str | None, Header(alias="Authorization")]


def _token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    kind, _, value = authorization.partition(" ")
    return value.strip() if kind.lower() == "bearer" and value.strip() else None


def _run(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    from trawlkit.classroom.service import ClassroomError

    try:
        return fn(*args, **kwargs)
    except ClassroomError as exc:
        raise HTTPException(exc.status, exc.detail) from exc


def _svc() -> Any:
    from trawlkit.classroom import service

    return service


def _user(s: Any, authorization: str | None) -> Any:
    return _run(_svc().current_user, s, _token(authorization))


# --- rutas --------------------------------------------------------------------------------------


@router.get("/status", response_model=StatusOut)
def status() -> Any:
    """Si el aula está habilitada en este servidor (sin tocar la base)."""
    try:
        from trawlkit.classroom import db
    except ImportError:  # pragma: no cover - depende de los extras instalados
        return {"enabled": False, "detail": NOT_CONFIGURED}
    if db.database_url() is None:
        return {"enabled": False, "detail": NOT_CONFIGURED}
    return {"enabled": True, "detail": "aula habilitada"}


@router.post("/auth/register", response_model=SessionOut)
def register(req: RegisterIn, s: Db) -> Any:
    """Alta de alumno (con código de curso) o de docente (con código de invitación)."""
    svc = _svc()
    token, user = _run(
        svc.register,
        s,
        req.username,
        req.password,
        req.display_name,
        course_code=req.course_code,
        invite_code=req.invite_code,
    )
    return {"token": token, "user": svc.user_out(user)}


@router.post("/auth/login", response_model=SessionOut)
def login(req: LoginIn, s: Db) -> Any:
    """Inicio de sesión (se bloquea unos minutos tras diez intentos fallidos)."""
    svc = _svc()
    token, user = _run(svc.login, s, req.username, req.password)
    return {"token": token, "user": svc.user_out(user)}


@router.post("/auth/logout", status_code=204)
def logout(s: Db, authorization: Auth = None) -> Response:
    """Cierra la sesión."""
    token = _token(authorization)
    if token:
        _svc().logout(s, token)
    return Response(status_code=204)


@router.get("/me", response_model=MeOut)
def me(s: Db, authorization: Auth = None) -> Any:
    """El usuario y sus cursos."""
    user = _user(s, authorization)
    return _run(_svc().me, s, user)


@router.post("/me/password", status_code=204)
def change_password(req: PasswordIn, s: Db, authorization: Auth = None) -> Response:
    """Cambia la contraseña propia."""
    user = _user(s, authorization)
    _run(_svc().change_password, s, user, req.old_password, req.new_password)
    return Response(status_code=204)


@router.post("/me/delete", status_code=204)
def delete_me(req: DeleteMeIn, s: Db, authorization: Auth = None) -> Response:
    """Borra la cuenta propia y sus entregas."""
    user = _user(s, authorization)
    _run(_svc().delete_account, s, user, req.password)
    return Response(status_code=204)


@router.get("/invites", response_model=list[InviteOut])
def invites(s: Db, authorization: Auth = None) -> Any:
    """Invitaciones para docentes (administrador)."""
    return _run(_svc().list_invites, s, _user(s, authorization))


@router.post("/invites", response_model=list[InviteOut])
def create_invites(req: InvitesIn, s: Db, authorization: Auth = None) -> Any:
    """Crea invitaciones para docentes (administrador)."""
    return _run(_svc().create_invites, s, _user(s, authorization), req.count, req.days)


@router.get("/courses", response_model=list[CourseOut])
def courses(s: Db, authorization: Auth = None) -> Any:
    """Cursos del usuario."""
    return _run(_svc().my_courses, s, _user(s, authorization))


@router.post("/courses", response_model=CourseOut)
def create_course(req: CourseIn, s: Db, authorization: Auth = None) -> Any:
    """Curso nuevo (docente); devuelve su código de inscripción."""
    return _run(_svc().create_course, s, _user(s, authorization), req.name, req.term)


@router.post("/courses/join", response_model=CourseOut)
def join_course(req: JoinIn, s: Db, authorization: Auth = None) -> Any:
    """Un alumno se suma a otro curso con su código."""
    return _run(_svc().join_course, s, _user(s, authorization), req.code)


@router.get("/courses/{course_id}", response_model=CourseOut)
def get_course(course_id: int, s: Db, authorization: Auth = None) -> Any:
    """Un curso."""
    return _run(_svc().get_course, s, _user(s, authorization), course_id)


@router.patch("/courses/{course_id}", response_model=CourseOut)
def update_course(course_id: int, req: CoursePatch, s: Db, authorization: Auth = None) -> Any:
    """Cambia nombre, cuatrimestre, archivado o código (docente del curso)."""
    return _run(
        _svc().update_course,
        s,
        _user(s, authorization),
        course_id,
        name=req.name,
        term=req.term,
        archived=req.archived,
        new_code_=req.new_code,
    )


@router.post("/courses/{course_id}/teachers", response_model=CourseOut)
def add_teacher(course_id: int, req: TeacherIn, s: Db, authorization: Auth = None) -> Any:
    """Suma otro docente al curso."""
    return _run(_svc().add_teacher, s, _user(s, authorization), course_id, req.username)


@router.get("/courses/{course_id}/students", response_model=list[UserOut])
def course_students(course_id: int, s: Db, authorization: Auth = None) -> Any:
    """Alumnos del curso (docente)."""
    return _run(_svc().students, s, _user(s, authorization), course_id)


@router.delete("/courses/{course_id}/students/{student_id}", status_code=204)
def remove_student(course_id: int, student_id: int, s: Db, authorization: Auth = None) -> Response:
    """Quita a un alumno del curso."""
    _run(_svc().remove_student, s, _user(s, authorization), course_id, student_id)
    return Response(status_code=204)


@router.post("/courses/{course_id}/students/{student_id}/password", status_code=204)
def reset_password(
    course_id: int, student_id: int, req: ResetPasswordIn, s: Db, authorization: Auth = None
) -> Response:
    """El docente pone una contraseña nueva a un alumno (no hay correo para recuperarla)."""
    user = _user(s, authorization)
    _run(_svc().reset_password, s, user, course_id, student_id, req.password)
    return Response(status_code=204)


@router.get("/courses/{course_id}/assignments", response_model=list[AssignmentOut])
def assignments(course_id: int, s: Db, authorization: Auth = None) -> Any:
    """Tareas del curso (los alumnos ven sólo las abiertas, con su avance)."""
    return _run(_svc().list_assignments, s, _user(s, authorization), course_id)


@router.post("/courses/{course_id}/assignments", response_model=AssignmentOut)
def create_assignment(course_id: int, req: AssignmentIn, s: Db, authorization: Auth = None) -> Any:
    """Tarea nueva con ejercicios y laboratorios del banco (docente)."""
    user = _user(s, authorization)
    return _run(_svc().create_assignment, s, user, course_id, req.model_dump())


@router.get("/assignments/{assignment_id}", response_model=AssignmentViewOut)
def get_assignment(assignment_id: int, s: Db, authorization: Auth = None) -> Any:
    """Una tarea; el alumno recibe sus datos (semilla propia) y sus entregas."""
    return _run(_svc().assignment_view, s, _user(s, authorization), assignment_id)


@router.patch("/assignments/{assignment_id}", response_model=AssignmentOut)
def update_assignment(
    assignment_id: int, req: AssignmentPatch, s: Db, authorization: Auth = None
) -> Any:
    """Cambia una tarea (los ítems, sólo sin entregas)."""
    user = _user(s, authorization)
    data = req.model_dump(exclude_unset=True)
    return _run(_svc().update_assignment, s, user, assignment_id, data)


@router.delete("/assignments/{assignment_id}", status_code=204)
def delete_assignment(assignment_id: int, s: Db, authorization: Auth = None) -> Response:
    """Borra una tarea con sus entregas."""
    _run(_svc().delete_assignment, s, _user(s, authorization), assignment_id)
    return Response(status_code=204)


@router.post(
    "/assignments/{assignment_id}/items/{item}/submit", response_model=StudentSubmissionOut
)
def submit(assignment_id: int, item: int, req: SubmitIn, s: Db, authorization: Auth = None) -> Any:
    """Entrega de un ítem: el servidor corrige y devuelve lo que la política permite ver."""
    user = _user(s, authorization)
    return _run(_svc().submit, s, user, assignment_id, item, dict(req.answers), req.steps)


@router.get("/assignments/{assignment_id}/grades", response_model=GradesOut)
def grades(assignment_id: int, s: Db, authorization: Auth = None) -> Any:
    """Planilla de notas de la tarea (docente)."""
    return _run(_svc().grades, s, _user(s, authorization), assignment_id)


@router.get(
    "/assignments/{assignment_id}/grades/export",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}, "application/octet-stream": {}}}},
)
def grades_export(
    assignment_id: int,
    s: Db,
    authorization: Auth = None,
    format: Literal["csv", "xlsx"] = "xlsx",  # noqa: A002 - nombre del parámetro HTTP
) -> Response:
    """La planilla en Excel o CSV."""
    user = _user(s, authorization)
    if format == "csv":
        text = _run(_svc().grades_csv, s, user, assignment_id)
        return Response(
            text.encode("utf-8-sig"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="notas-{assignment_id}.csv"'},
        )
    data = _run(_svc().grades_xlsx, s, user, assignment_id)
    return Response(
        data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="notas-{assignment_id}.xlsx"'},
    )


@router.get(
    "/assignments/{assignment_id}/sheet",
    response_class=Response,
    responses={200: {"content": {"text/html": {}, "application/pdf": {}}}},
)
def assignment_sheet(
    assignment_id: int,
    s: Db,
    authorization: Auth = None,
    format: Literal["html", "pdf"] = "html",  # noqa: A002 - nombre del parámetro HTTP
    key: bool = False,
    student_id: int | None = None,
    all_students: bool = Query(False, description="Una guía por alumno, cada uno con sus datos"),
) -> Response:
    """Guía imprimible de la tarea: enunciados o clave, de un alumno, de todos o del libro."""
    user = _user(s, authorization)
    html = _run(
        _svc().sheet,
        s,
        user,
        assignment_id,
        key=key,
        student_id=student_id,
        all_students=all_students,
    )
    name = f"tarea-{assignment_id}{'-clave' if key else ''}"
    if format == "html":
        return HTMLResponse(html)
    from trawlkit.report.exercises import exercise_sheet_pdf

    try:
        pdf = exercise_sheet_pdf(html)
    except RuntimeError as exc:  # pragma: no cover - depende de WeasyPrint
        raise HTTPException(501, str(exc)) from exc
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{name}.pdf"'},
    )


@router.get("/submissions/{submission_id}", response_model=SubmissionOut | StudentSubmissionOut)
def submission(submission_id: int, s: Db, authorization: Auth = None) -> Any:
    """Una entrega: completa para el docente; según la política, para su alumno."""
    return _run(_svc().submission_detail, s, _user(s, authorization), submission_id)


@router.patch("/submissions/{submission_id}", response_model=SubmissionOut)
def review(submission_id: int, req: ReviewIn, s: Db, authorization: Auth = None) -> Any:
    """Nota y comentario del docente sobre una entrega."""
    user = _user(s, authorization)
    return _run(_svc().review_submission, s, user, submission_id, req.teacher_score, req.comment)
