"""Lógica del aula, independiente de HTTP: cuentas, cursos, tareas, entregas y notas.

Las funciones reciben una sesión de base de datos y el usuario que actúa, verifican permisos y
lanzan :class:`ClassroomError` con el estado HTTP que corresponde. La corrección de ejercicios y
laboratorios la hace siempre el servidor con :mod:`trawlkit.teaching`; los datos de cada alumno
salen de una semilla derivada con un secreto de la base, así dos alumnos no tienen los mismos
números.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import re
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from trawlkit.classroom.db import seed_secret
from trawlkit.classroom.models import (
    Assignment,
    AuthToken,
    Course,
    Enrollment,
    Invite,
    Submission,
    User,
    utcnow,
)
from trawlkit.classroom.security import (
    hash_password,
    new_code,
    new_token,
    normalise_code,
    student_seed,
    token_hash,
    verify_password,
)

TOKEN_DAYS = 14
MAX_FAILED = 10
LOCK_MINUTES = 15
USERNAME = re.compile(r"^[a-z0-9._-]{3,40}$")
MIN_PASSWORD = 8


class ClassroomError(Exception):
    """Error del aula con su estado HTTP."""

    def __init__(self, status: int, detail: str) -> None:
        """Error con estado HTTP ``status`` y mensaje ``detail``."""
        super().__init__(detail)
        self.status = status
        self.detail = detail


def _err(status: int, detail: str) -> ClassroomError:
    return ClassroomError(status, detail)


# =============================================================================================
# Cuentas
# =============================================================================================


def user_out(u: User) -> dict[str, Any]:
    """Datos públicos de un usuario."""
    return {"id": u.id, "username": u.username, "display_name": u.display_name, "role": u.role}


def _check_new_user(s: Session, username: str, password: str, display_name: str) -> str:
    name = username.strip().lower()
    if not USERNAME.match(name):
        raise _err(422, "usuario: 3 a 40 letras minúsculas, números, punto, guion o guion bajo")
    if len(password) < MIN_PASSWORD:
        raise _err(422, f"la contraseña necesita al menos {MIN_PASSWORD} caracteres")
    if not display_name.strip():
        raise _err(422, "falta el nombre para mostrar (nombre o legajo)")
    if s.scalar(select(User).where(User.username == name)) is not None:
        raise _err(409, "ese usuario ya existe")
    return name


def _issue_token(s: Session, user: User) -> str:
    token = new_token()
    s.add(
        AuthToken(
            token_hash=token_hash(token),
            user_id=user.id,
            expires_at=utcnow() + dt.timedelta(days=TOKEN_DAYS),
        )
    )
    return token


def create_admin(s: Session, username: str, password: str, display_name: str) -> User:
    """Crea un administrador (desde la CLI)."""
    name = _check_new_user(s, username, password, display_name)
    user = User(
        username=name,
        display_name=display_name.strip(),
        password_hash=hash_password(password),
        role="admin",
    )
    s.add(user)
    s.commit()
    return user


def register(
    s: Session,
    username: str,
    password: str,
    display_name: str,
    course_code: str | None = None,
    invite_code: str | None = None,
) -> tuple[str, User]:
    """Alta con código de curso (alumno) o de invitación (docente); devuelve token y usuario."""
    if bool(course_code) == bool(invite_code):
        raise _err(422, "use un código de curso (alumno) o uno de invitación (docente)")
    name = _check_new_user(s, username, password, display_name)
    course = None
    invite = None
    if course_code:
        course = s.scalar(select(Course).where(Course.code == normalise_code(course_code)))
        if course is None or course.archived:
            raise _err(404, "no hay un curso abierto con ese código")
    else:
        invite = s.get(Invite, normalise_code(invite_code or ""))
        if invite is None or invite.used_by is not None or invite.expires_at < utcnow():
            raise _err(404, "la invitación no existe, ya se usó o venció")
    user = User(
        username=name,
        display_name=display_name.strip(),
        password_hash=hash_password(password),
        role="student" if course else "teacher",
    )
    s.add(user)
    s.flush()
    if course is not None:
        s.add(Enrollment(course_id=course.id, user_id=user.id, role="student"))
    if invite is not None:
        invite.used_by = user.id
    token = _issue_token(s, user)
    s.commit()
    return token, user


def login(s: Session, username: str, password: str) -> tuple[str, User]:
    """Inicio de sesión con bloqueo temporal tras varios intentos fallidos."""
    user = s.scalar(select(User).where(User.username == username.strip().lower()))
    now = utcnow()
    if user is not None and user.locked_until is not None and user.locked_until > now:
        raise _err(429, "demasiados intentos: espere unos minutos")
    if user is None or not verify_password(password, user.password_hash):
        if user is not None:
            user.failed_logins += 1
            if user.failed_logins >= MAX_FAILED:
                user.locked_until = now + dt.timedelta(minutes=LOCK_MINUTES)
                user.failed_logins = 0
            s.commit()
        raise _err(401, "usuario o contraseña incorrectos")
    user.failed_logins = 0
    user.locked_until = None
    s.execute(delete(AuthToken).where(AuthToken.expires_at < now))
    token = _issue_token(s, user)
    s.commit()
    return token, user


def current_user(s: Session, token: str | None) -> User:
    """Usuario del token (401 si falta, es inválido o venció)."""
    if not token:
        raise _err(401, "inicie sesión")
    row = s.get(AuthToken, token_hash(token))
    if row is None or row.expires_at < utcnow():
        raise _err(401, "la sesión venció: vuelva a iniciar sesión")
    user = s.get(User, row.user_id)
    if user is None:  # pragma: no cover - el token se borra con el usuario
        raise _err(401, "inicie sesión")
    return user


def logout(s: Session, token: str) -> None:
    """Cierra la sesión del token."""
    row = s.get(AuthToken, token_hash(token))
    if row is not None:
        s.delete(row)
        s.commit()


def change_password(s: Session, user: User, old: str, new: str) -> None:
    """Cambia la contraseña propia."""
    if not verify_password(old, user.password_hash):
        raise _err(403, "la contraseña actual no coincide")
    if len(new) < MIN_PASSWORD:
        raise _err(422, f"la contraseña necesita al menos {MIN_PASSWORD} caracteres")
    user.password_hash = hash_password(new)
    s.commit()


def delete_account(s: Session, user: User, password: str) -> None:
    """Borra la cuenta propia con sus entregas (un administrador no puede borrarse así)."""
    if user.role == "admin":
        raise _err(403, "un administrador no puede borrar su cuenta desde la app")
    if not verify_password(password, user.password_hash):
        raise _err(403, "la contraseña no coincide")
    s.delete(user)
    s.commit()


def me(s: Session, user: User) -> dict[str, Any]:
    """Usuario y sus cursos."""
    return {**user_out(user), "courses": my_courses(s, user)}


# =============================================================================================
# Invitaciones (administrador)
# =============================================================================================


def _require(user: User, *roles: str) -> None:
    if user.role not in roles:
        raise _err(403, "no tiene permiso para esto")


def create_invites(s: Session, admin: User, count: int, days: int) -> list[dict[str, Any]]:
    """Códigos de invitación para docentes."""
    _require(admin, "admin")
    if not 1 <= count <= 50 or not 1 <= days <= 365:
        raise _err(422, "entre 1 y 50 invitaciones, de 1 a 365 días")
    out = []
    for _ in range(count):
        inv = Invite(
            code=new_code(10),
            created_by=admin.id,
            expires_at=utcnow() + dt.timedelta(days=days),
        )
        s.add(inv)
        out.append(inv)
    s.commit()
    return [_invite_out(s, i) for i in out]


def _invite_out(s: Session, i: Invite) -> dict[str, Any]:
    used = s.get(User, i.used_by) if i.used_by else None
    return {
        "code": i.code,
        "expires_at": i.expires_at,
        "used_by": used.username if used else None,
        "created_at": i.created_at,
    }


def list_invites(s: Session, admin: User) -> list[dict[str, Any]]:
    """Invitaciones creadas, la más nueva primero."""
    _require(admin, "admin")
    rows = s.scalars(select(Invite).order_by(Invite.created_at.desc())).all()
    return [_invite_out(s, i) for i in rows]


# =============================================================================================
# Cursos
# =============================================================================================


def _membership(s: Session, user: User, course_id: int) -> Enrollment | None:
    return s.scalar(
        select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.user_id == user.id)
    )


def _course(s: Session, user: User, course_id: int, *, teacher: bool = False) -> Course:
    course = s.get(Course, course_id)
    if course is None:
        raise _err(404, "curso desconocido")
    if user.role == "admin":
        return course
    m = _membership(s, user, course_id)
    if m is None or (teacher and m.role != "teacher"):
        raise _err(403, "no es " + ("docente" if teacher else "miembro") + " de este curso")
    return course


def course_out(s: Session, c: Course, role: str | None = None) -> dict[str, Any]:
    """Curso con conteos."""
    students = s.scalar(
        select(func.count()).where(Enrollment.course_id == c.id, Enrollment.role == "student")
    )
    teachers = s.scalars(
        select(User)
        .join(Enrollment, Enrollment.user_id == User.id)
        .where(Enrollment.course_id == c.id, Enrollment.role == "teacher")
    ).all()
    out = {
        "id": c.id,
        "name": c.name,
        "term": c.term,
        "archived": c.archived,
        "students": int(students or 0),
        "teachers": [t.display_name for t in teachers],
        "role": role,
        "code": c.code if role in ("teacher", "admin") else None,
    }
    return out


def my_courses(s: Session, user: User) -> list[dict[str, Any]]:
    """Cursos del usuario con su rol en cada uno."""
    rows = s.execute(
        select(Course, Enrollment.role)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .where(Enrollment.user_id == user.id)
        .order_by(Course.created_at.desc())
    ).all()
    return [course_out(s, c, role) for c, role in rows]


def create_course(s: Session, user: User, name: str, term: str = "") -> dict[str, Any]:
    """Curso nuevo; quien lo crea es su docente."""
    _require(user, "teacher", "admin")
    if not name.strip():
        raise _err(422, "falta el nombre del curso")
    c = Course(name=name.strip(), term=term.strip(), code=new_code(8))
    s.add(c)
    s.flush()
    s.add(Enrollment(course_id=c.id, user_id=user.id, role="teacher"))
    s.commit()
    return course_out(s, c, "teacher")


def get_course(s: Session, user: User, course_id: int) -> dict[str, Any]:
    """Un curso (los docentes ven el código)."""
    c = _course(s, user, course_id)
    m = _membership(s, user, course_id)
    role = m.role if m is not None else ("admin" if user.role == "admin" else None)
    return course_out(s, c, role)


def update_course(
    s: Session,
    user: User,
    course_id: int,
    *,
    name: str | None = None,
    term: str | None = None,
    archived: bool | None = None,
    new_code_: bool = False,
) -> dict[str, Any]:
    """Cambia nombre, cuatrimestre, archivado o código del curso."""
    c = _course(s, user, course_id, teacher=True)
    if name is not None:
        if not name.strip():
            raise _err(422, "falta el nombre del curso")
        c.name = name.strip()
    if term is not None:
        c.term = term.strip()
    if archived is not None:
        c.archived = archived
    if new_code_:
        c.code = new_code(8)
    s.commit()
    return course_out(s, c, "teacher")


def join_course(s: Session, user: User, code: str) -> dict[str, Any]:
    """Un alumno se suma a otro curso con su código."""
    _require(user, "student")
    c = s.scalar(select(Course).where(Course.code == normalise_code(code)))
    if c is None or c.archived:
        raise _err(404, "no hay un curso abierto con ese código")
    if _membership(s, user, c.id) is None:
        s.add(Enrollment(course_id=c.id, user_id=user.id, role="student"))
        s.commit()
    return course_out(s, c, "student")


def add_teacher(s: Session, user: User, course_id: int, username: str) -> dict[str, Any]:
    """Suma otro docente al curso."""
    c = _course(s, user, course_id, teacher=True)
    other = s.scalar(select(User).where(User.username == username.strip().lower()))
    if other is None or other.role not in ("teacher", "admin"):
        raise _err(404, "no hay un docente con ese usuario")
    m = _membership(s, other, course_id)
    if m is None:
        s.add(Enrollment(course_id=c.id, user_id=other.id, role="teacher"))
    else:
        m.role = "teacher"
    s.commit()
    return course_out(s, c, "teacher")


def students(s: Session, user: User, course_id: int) -> list[dict[str, Any]]:
    """Alumnos del curso."""
    _course(s, user, course_id, teacher=True)
    rows = s.scalars(
        select(User)
        .join(Enrollment, Enrollment.user_id == User.id)
        .where(Enrollment.course_id == course_id, Enrollment.role == "student")
        .order_by(User.display_name)
    ).all()
    return [user_out(u) for u in rows]


def _student_in(s: Session, course_id: int, student_id: int) -> User:
    st = s.get(User, student_id)
    m = None if st is None else _membership(s, st, course_id)
    if st is None or m is None or m.role != "student":
        raise _err(404, "ese alumno no está en el curso")
    return st


def remove_student(s: Session, user: User, course_id: int, student_id: int) -> None:
    """Quita a un alumno del curso (sus entregas quedan)."""
    _course(s, user, course_id, teacher=True)
    st = _student_in(s, course_id, student_id)
    m = _membership(s, st, course_id)
    s.delete(m)
    s.commit()


def reset_password(s: Session, user: User, course_id: int, student_id: int, password: str) -> None:
    """El docente pone una contraseña nueva a un alumno de su curso (no hay correo)."""
    _course(s, user, course_id, teacher=True)
    st = _student_in(s, course_id, student_id)
    if len(password) < MIN_PASSWORD:
        raise _err(422, f"la contraseña necesita al menos {MIN_PASSWORD} caracteres")
    st.password_hash = hash_password(password)
    st.failed_logins = 0
    st.locked_until = None
    s.execute(delete(AuthToken).where(AuthToken.user_id == st.id))
    s.commit()


# =============================================================================================
# Tareas
# =============================================================================================


def _item_title(item: dict[str, Any]) -> str:
    from trawlkit.teaching import exercise
    from trawlkit.teaching.labs import lab

    return exercise(item["ref"]).title if item["kind"] == "exercise" else lab(item["ref"]).title


def _check_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from trawlkit.teaching import load_bank
    from trawlkit.teaching.labs import load_labs

    if not items:
        raise _err(422, "la tarea necesita al menos un ejercicio o laboratorio")
    if len(items) > 40:
        raise _err(422, "hasta 40 ítems por tarea")
    out = []
    for it in items:
        kind, ref = it.get("kind"), it.get("ref")
        points = float(it.get("points", 1) or 1)
        if kind == "exercise" and ref in load_bank():
            pass
        elif kind == "lab" and ref in load_labs():
            pass
        else:
            raise _err(422, f"ítem desconocido: {kind} {ref}")
        if not 0 < points <= 100:
            raise _err(422, "puntos entre 0 y 100")
        out.append({"kind": kind, "ref": ref, "points": points})
    return out


def _is_open(a: Assignment, now: dt.datetime) -> bool:
    return a.opens_at is None or a.opens_at <= now


def _is_closed(a: Assignment, now: dt.datetime) -> bool:
    return a.due_at is not None and a.due_at < now


def assignment_out(a: Assignment) -> dict[str, Any]:
    """Resumen de una tarea."""
    now = utcnow()
    return {
        "id": a.id,
        "course_id": a.course_id,
        "title": a.title,
        "description": a.description,
        "items": [{**it, "title": _item_title(it)} for it in a.items],
        "opens_at": a.opens_at,
        "due_at": a.due_at,
        "max_attempts": a.max_attempts,
        "feedback": a.feedback,
        "per_student_data": a.per_student_data,
        "open": _is_open(a, now),
        "closed": _is_closed(a, now),
    }


def _naive_utc(v: dt.datetime | None) -> dt.datetime | None:
    if v is None:
        return None
    return v.astimezone(dt.UTC).replace(tzinfo=None) if v.tzinfo else v


def create_assignment(
    s: Session, user: User, course_id: int, data: dict[str, Any]
) -> dict[str, Any]:
    """Tarea nueva en el curso."""
    _course(s, user, course_id, teacher=True)
    if not str(data.get("title", "")).strip():
        raise _err(422, "falta el título de la tarea")
    a = Assignment(
        course_id=course_id,
        title=str(data["title"]).strip(),
        description=str(data.get("description") or ""),
        items=_check_items(list(data.get("items") or [])),
        opens_at=_naive_utc(data.get("opens_at")),
        due_at=_naive_utc(data.get("due_at")),
        max_attempts=int(data.get("max_attempts") or 3),
        feedback=str(data.get("feedback") or "immediate"),
        per_student_data=bool(data.get("per_student_data", True)),
    )
    _validate_assignment(a)
    s.add(a)
    s.commit()
    return assignment_out(a)


def _validate_assignment(a: Assignment) -> None:
    if a.feedback not in ("immediate", "after_due"):
        raise _err(422, "feedback: immediate o after_due")
    if not 1 <= a.max_attempts <= 20:
        raise _err(422, "intentos entre 1 y 20")
    if a.feedback == "after_due" and a.due_at is None:
        raise _err(422, "la devolución al cierre necesita una fecha de cierre")
    if a.opens_at and a.due_at and a.due_at <= a.opens_at:
        raise _err(422, "el cierre tiene que ser posterior a la apertura")


def _assignment(s: Session, user: User, assignment_id: int, *, teacher: bool = False) -> Assignment:
    a = s.get(Assignment, assignment_id)
    if a is None:
        raise _err(404, "tarea desconocida")
    _course(s, user, a.course_id, teacher=teacher)
    m = _membership(s, user, a.course_id)
    if not teacher and m is not None and m.role == "student" and not _is_open(a, utcnow()):
        raise _err(404, "tarea desconocida")
    return a


def update_assignment(
    s: Session, user: User, assignment_id: int, data: dict[str, Any]
) -> dict[str, Any]:
    """Cambia una tarea (los ítems sólo mientras no haya entregas)."""
    a = _assignment(s, user, assignment_id, teacher=True)
    if "items" in data and data["items"] is not None:
        has = s.scalar(select(func.count()).where(Submission.assignment_id == a.id))
        if has:
            raise _err(409, "la tarea ya tiene entregas: no se pueden cambiar los ítems")
        a.items = _check_items(list(data["items"]))
    for key in ("title", "description", "max_attempts", "feedback", "per_student_data"):
        if key in data and data[key] is not None:
            setattr(a, key, data[key])
    for key in ("opens_at", "due_at"):
        if key in data:
            setattr(a, key, _naive_utc(data[key]))
    _validate_assignment(a)
    s.commit()
    return assignment_out(a)


def delete_assignment(s: Session, user: User, assignment_id: int) -> None:
    """Borra una tarea con sus entregas."""
    a = _assignment(s, user, assignment_id, teacher=True)
    s.delete(a)
    s.commit()


def list_assignments(s: Session, user: User, course_id: int) -> list[dict[str, Any]]:
    """Tareas del curso (los alumnos sólo ven las abiertas)."""
    _course(s, user, course_id)
    m = _membership(s, user, course_id)
    student = m is not None and m.role == "student"
    rows = s.scalars(
        select(Assignment).where(Assignment.course_id == course_id).order_by(Assignment.id)
    ).all()
    now = utcnow()
    out = []
    for a in rows:
        if student and not _is_open(a, now):
            continue
        d = assignment_out(a)
        if student:
            d["progress"] = _progress(s, a, user)
        out.append(d)
    return out


def _seed(s: Session, a: Assignment, user_id: int, item: int) -> int:
    if not a.per_student_data:
        return 0
    return student_seed(seed_secret(s), a.id, user_id, item)


def _subs(s: Session, a: Assignment, user_id: int, item: int | None = None) -> list[Submission]:
    q = select(Submission).where(Submission.assignment_id == a.id, Submission.user_id == user_id)
    if item is not None:
        q = q.where(Submission.item == item)
    return list(s.scalars(q.order_by(Submission.item, Submission.attempt)).all())


def _score(sub: Submission) -> float | None:
    return sub.teacher_score if sub.teacher_score is not None else sub.auto_score


def _progress(s: Session, a: Assignment, user: User) -> dict[str, Any]:
    subs = _subs(s, a, user.id)
    done = {x.item for x in subs}
    return {"items": len(a.items), "submitted": len(done)}


def _can_reveal(a: Assignment, attempts_left: int, now: dt.datetime) -> bool:
    if a.feedback == "after_due":
        return _is_closed(a, now)
    return attempts_left <= 0 or _is_closed(a, now)


def _public_result(a: Assignment, sub: Submission, attempts_left: int) -> dict[str, Any]:
    """Lo que ve el alumno de una entrega según la política de devolución."""
    now = utcnow()
    hidden = a.feedback == "after_due" and not _is_closed(a, now)
    reveal = _can_reveal(a, attempts_left, now)
    base = {
        "id": sub.id,
        "item": sub.item,
        "attempt": sub.attempt,
        "created_at": sub.created_at,
        "teacher_score": sub.teacher_score,
        "comment": sub.comment,
    }
    if hidden:
        return {**base, "score": None, "result": None, "message": "entrega recibida"}
    result = dict(sub.result)
    if not reveal:
        result = _strip_solution(result)
    return {**base, "score": sub.auto_score, "result": result, "message": ""}


def _strip_solution(result: dict[str, Any]) -> dict[str, Any]:
    out = dict(result)
    out.pop("explanation", None)
    if "answers" in out:
        out["answers"] = [
            {**x, "expected": None, "expected_text": None} for x in out.get("answers", [])
        ]
    if "steps" in out:
        out["steps"] = {
            k: {
                **v,
                "questions": [{**q, "expected_text": None} for q in v.get("questions", [])],
            }
            for k, v in out["steps"].items()
        }
    return out


def assignment_view(s: Session, user: User, assignment_id: int) -> dict[str, Any]:
    """Una tarea: el alumno recibe cada ítem con sus datos y entregas; el docente, el resumen."""
    from trawlkit.api import service as api_service

    a = _assignment(s, user, assignment_id)
    out = assignment_out(a)
    m = _membership(s, user, a.course_id)
    if m is None or m.role != "student":
        return out
    items = []
    for n, it in enumerate(a.items):
        subs = _subs(s, a, user.id, n)
        left = a.max_attempts - len(subs)
        entry: dict[str, Any] = {
            "index": n,
            "kind": it["kind"],
            "ref": it["ref"],
            "points": it["points"],
            "title": _item_title(it),
            "attempts_used": len(subs),
            "attempts_left": max(0, left),
            "submissions": [_public_result(a, x, left) for x in subs],
        }
        if it["kind"] == "exercise":
            entry["exercise"] = api_service.teaching_exercise(it["ref"], _seed(s, a, user.id, n))
            entry["exercise"]["seed"] = None
        else:
            entry["lab"] = api_service.teaching_lab(it["ref"])
        items.append(entry)
    out["item_list"] = items
    return out


def submit(
    s: Session,
    user: User,
    assignment_id: int,
    item: int,
    answers: dict[str, Any],
    steps: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Entrega de un alumno: corrige en el servidor y guarda el intento."""
    from trawlkit.teaching import grade
    from trawlkit.teaching.labs import lab, lab_check

    a = _assignment(s, user, assignment_id)
    m = _membership(s, user, a.course_id)
    if m is None or m.role != "student":
        raise _err(403, "sólo los alumnos del curso entregan")
    now = utcnow()
    if _is_closed(a, now):
        raise _err(409, "la tarea ya cerró")
    if not 0 <= item < len(a.items):
        raise _err(404, "ítem desconocido")
    used = len(_subs(s, a, user.id, item))
    if used >= a.max_attempts:
        raise _err(409, "no le quedan intentos para este ítem")
    it = a.items[item]
    seed = _seed(s, a, user.id, item)
    design = None
    if it["kind"] == "exercise":
        g = grade(it["ref"], seed, answers, reveal=True).to_dict()
        auto = float(g["score"])
        result: dict[str, Any] = {"kind": "exercise", **g}
        result.pop("seed", None)
    else:
        spec = lab(it["ref"])
        steps = steps or {}
        step_results: dict[str, Any] = {}
        for st in spec.steps:
            got = steps.get(st.id) or {}
            if not isinstance(got, dict) or not isinstance(got.get("design"), dict):
                step_results[st.id] = {"done": False, "checks": [], "questions": []}
                continue
            r = lab_check(spec.id, st.id, got["design"], got.get("answers") or {}).to_dict()
            step_results[st.id] = {k: r[k] for k in ("done", "checks", "questions", "values")}
            design = got["design"]
        auto = sum(1 for v in step_results.values() if v["done"]) / len(spec.steps)
        result = {"kind": "lab", "score": auto, "steps": step_results}
        answers = {k: (v or {}).get("answers", {}) for k, v in steps.items()}
    sub = Submission(
        assignment_id=a.id,
        user_id=user.id,
        item=item,
        attempt=used + 1,
        seed=seed,
        answers=answers,
        design=design,
        auto_score=auto,
        result=_jsonable(result),
    )
    s.add(sub)
    s.commit()
    return _public_result(a, sub, a.max_attempts - used - 1)


def _jsonable(v: Any) -> Any:
    from trawlkit.api.service import to_jsonable

    return to_jsonable(v)


# =============================================================================================
# Notas y revisión
# =============================================================================================


def _best(subs: list[Submission]) -> Submission | None:
    scored = [x for x in subs if _score(x) is not None]
    if not scored:
        return subs[-1] if subs else None
    return max(scored, key=lambda x: (_score(x) or 0.0, x.attempt))


def grades(s: Session, user: User, assignment_id: int) -> dict[str, Any]:
    """Planilla de la tarea: por alumno, la mejor entrega de cada ítem y el total en puntos."""
    a = _assignment(s, user, assignment_id, teacher=True)
    sts = s.scalars(
        select(User)
        .join(Enrollment, Enrollment.user_id == User.id)
        .where(Enrollment.course_id == a.course_id, Enrollment.role == "student")
        .order_by(User.display_name)
    ).all()
    total_points = sum(float(it["points"]) for it in a.items)
    rows = []
    for st in sts:
        cells = []
        points = 0.0
        for n, it in enumerate(a.items):
            subs = _subs(s, a, st.id, n)
            best = _best(subs)
            sc = None if best is None else _score(best)
            if sc is not None:
                points += sc * float(it["points"])
            cells.append(
                {
                    "item": n,
                    "attempts": len(subs),
                    "score": sc,
                    "submission_id": None if best is None else best.id,
                    "needs_review": best is not None
                    and best.teacher_score is None
                    and _has_open_questions(best),
                }
            )
        rows.append({"student": user_out(st), "cells": cells, "points": points})
    return {
        "assignment": assignment_out(a),
        "total_points": total_points,
        "rows": rows,
    }


def _has_open_questions(sub: Submission) -> bool:
    steps = sub.result.get("steps") if isinstance(sub.result, dict) else None
    if not steps:
        return False
    return any(
        q.get("ok") is None and q.get("given") for v in steps.values() for q in v["questions"]
    )


def grades_csv(s: Session, user: User, assignment_id: int) -> str:
    """La planilla en CSV (punto y coma, coma decimal)."""
    g = grades(s, user, assignment_id)
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    titles = [f"{n + 1}. {it['title']}" for n, it in enumerate(g["assignment"]["items"])]
    w.writerow(["usuario", "nombre", *titles, f"puntos (de {_dec(g['total_points'])})"])
    for r in g["rows"]:
        w.writerow(
            [
                r["student"]["username"],
                r["student"]["display_name"],
                *["" if c["score"] is None else _dec(c["score"] * 100) + " %" for c in r["cells"]],
                _dec(r["points"]),
            ]
        )
    return buf.getvalue()


def grades_xlsx(s: Session, user: User, assignment_id: int) -> bytes:
    """La planilla en Excel."""
    from openpyxl import Workbook

    g = grades(s, user, assignment_id)
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Notas"
    titles = [f"{n + 1}. {it['title']}" for n, it in enumerate(g["assignment"]["items"])]
    ws.append(["Usuario", "Nombre", *titles, "Puntos"])
    for r in g["rows"]:
        ws.append(
            [
                r["student"]["username"],
                r["student"]["display_name"],
                *[None if c["score"] is None else round(c["score"], 4) for c in r["cells"]],
                round(r["points"], 3),
            ]
        )
    for row in ws.iter_rows(min_row=2, min_col=3, max_col=2 + len(titles)):
        for cell in row:
            cell.number_format = "0%"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _dec(x: float) -> str:
    return f"{x:.2f}".rstrip("0").rstrip(".").replace(".", ",") or "0"


def submission_detail(s: Session, user: User, submission_id: int) -> dict[str, Any]:
    """Una entrega completa: para el docente del curso o, según la política, para su alumno."""
    sub = s.get(Submission, submission_id)
    if sub is None:
        raise _err(404, "entrega desconocida")
    a = sub.assignment
    m = _membership(s, user, a.course_id)
    teacher = user.role == "admin" or (m is not None and m.role == "teacher")
    if not teacher:
        if sub.user_id != user.id:
            raise _err(403, "no puede ver esa entrega")
        left = a.max_attempts - len(_subs(s, a, user.id, sub.item))
        return _public_result(a, sub, left)
    st = s.get(User, sub.user_id)
    return {
        "id": sub.id,
        "assignment_id": a.id,
        "item": sub.item,
        "item_info": {**a.items[sub.item], "title": _item_title(a.items[sub.item])},
        "student": user_out(st) if st else None,
        "attempt": sub.attempt,
        "seed": sub.seed,
        "answers": sub.answers,
        "design": sub.design,
        "auto_score": sub.auto_score,
        "teacher_score": sub.teacher_score,
        "comment": sub.comment,
        "result": sub.result,
        "created_at": sub.created_at,
    }


def review_submission(
    s: Session, user: User, submission_id: int, teacher_score: float | None, comment: str | None
) -> dict[str, Any]:
    """El docente pone nota (0 a 1, reemplaza la automática) y comentario."""
    sub = s.get(Submission, submission_id)
    if sub is None:
        raise _err(404, "entrega desconocida")
    _course(s, user, sub.assignment.course_id, teacher=True)
    if teacher_score is not None and not 0 <= teacher_score <= 1:
        raise _err(422, "la nota va de 0 a 1")
    sub.teacher_score = teacher_score
    if comment is not None:
        sub.comment = comment
    s.commit()
    return submission_detail(s, user, submission_id)


def sheet(
    s: Session,
    user: User,
    assignment_id: int,
    *,
    key: bool = False,
    student_id: int | None = None,
    all_students: bool = False,
) -> str:
    """Guía imprimible de la tarea (enunciados o clave), con los datos de un alumno o de todos."""
    from trawlkit.report.exercises import exercise_sheet_html
    from trawlkit.teaching import instantiate, solve

    a = _assignment(s, user, assignment_id, teacher=True)
    course = s.get(Course, a.course_id)
    refs = [(n, it["ref"]) for n, it in enumerate(a.items) if it["kind"] == "exercise"]
    if not refs:
        raise _err(422, "la tarea no tiene ejercicios para imprimir")
    targets: list[tuple[str, int | None]]
    if all_students:
        targets = [(u["display_name"], u["id"]) for u in students(s, user, a.course_id)]
        if not targets:
            raise _err(422, "el curso todavía no tiene alumnos")
    elif student_id is not None:
        st = _student_in(s, a.course_id, student_id)
        targets = [(st.display_name, st.id)]
    else:
        targets = [("", None)]
    parts = []
    for name, uid in targets:
        seeds = [(n, ref, 0 if uid is None else _seed(s, a, uid, n)) for n, ref in refs]
        items = [(instantiate(ref, sd), solve(ref, sd) if key else None) for _, ref, sd in seeds]
        sub = f"{course.name if course else ''} · {name}".strip(" ·")
        parts.append(exercise_sheet_html(items, title=a.title, subtitle=sub or None))
    if len(parts) == 1:
        return parts[0]
    bodies = [p.split("<body>", 1)[1].rsplit("</body>", 1)[0] for p in parts]
    head = parts[0].split("<body>", 1)[0]
    brk = "<div style='page-break-after: always'></div>"
    return f"{head}<body>{brk.join(bodies)}</body></html>"
