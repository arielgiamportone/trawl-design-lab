"""Modelo de datos del aula (Fase 17.2): usuarios, cursos, tareas y entregas.

Datos personales mínimos: un usuario tiene nombre de usuario, un nombre para mostrar (nombre o
legajo) y la contraseña con hash; no hay correo. Las fechas se guardan en UTC.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

#: Versión del esquema; ``init_db`` la registra en ``settings``.
SCHEMA_VERSION = 1


def utcnow() -> dt.datetime:
    """Ahora en UTC, sin zona (todas las fechas de la base son UTC)."""
    return dt.datetime.now(dt.UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    """Base declarativa del aula."""

    type_annotation_map = {dict[str, Any]: JSON, list[Any]: JSON}


class Setting(Base):
    """Valores internos (versión del esquema, secreto de las semillas)."""

    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)


class User(Base):
    """Usuario: administrador, docente o alumno."""

    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(10))  # admin | teacher | student
    failed_logins: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[dt.datetime | None] = mapped_column(default=None)
    created_at: Mapped[dt.datetime] = mapped_column(default=utcnow)


class AuthToken(Base):
    """Sesión: sólo se guarda el hash del token."""

    __tablename__ = "auth_tokens"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[dt.datetime]
    created_at: Mapped[dt.datetime] = mapped_column(default=utcnow)


class Invite(Base):
    """Código de invitación para registrarse como docente."""

    __tablename__ = "invites"
    code: Mapped[str] = mapped_column(String(24), primary_key=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    used_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    expires_at: Mapped[dt.datetime]
    created_at: Mapped[dt.datetime] = mapped_column(default=utcnow)


class Course(Base):
    """Curso, con su código de inscripción."""

    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    term: Mapped[str] = mapped_column(String(40), default="")
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    archived: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[dt.datetime] = mapped_column(default=utcnow)
    members: Mapped[list[Enrollment]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )
    assignments: Mapped[list[Assignment]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )


class Enrollment(Base):
    """Pertenencia a un curso, como docente o como alumno."""

    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("course_id", "user_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(10))  # teacher | student
    created_at: Mapped[dt.datetime] = mapped_column(default=utcnow)
    course: Mapped[Course] = relationship(back_populates="members")
    user: Mapped[User] = relationship()


class Assignment(Base):
    """Tarea: ejercicios y laboratorios del banco, con fechas, intentos y política de devolución."""

    __tablename__ = "assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    items: Mapped[list[Any]] = mapped_column(default=list)  # [{"kind", "ref", "points"}]
    opens_at: Mapped[dt.datetime | None] = mapped_column(default=None)
    due_at: Mapped[dt.datetime | None] = mapped_column(default=None)
    max_attempts: Mapped[int] = mapped_column(default=3)
    feedback: Mapped[str] = mapped_column(String(12), default="immediate")  # | after_due
    per_student_data: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[dt.datetime] = mapped_column(default=utcnow)
    course: Mapped[Course] = relationship(back_populates="assignments")
    submissions: Mapped[list[Submission]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan"
    )


class Submission(Base):
    """Entrega de un alumno para un ítem de una tarea (un registro por intento)."""

    __tablename__ = "submissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    item: Mapped[int]
    attempt: Mapped[int] = mapped_column(default=1)
    seed: Mapped[int] = mapped_column(default=0)
    answers: Mapped[dict[str, Any]] = mapped_column(default=dict)
    design: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    auto_score: Mapped[float | None] = mapped_column(default=None)
    result: Mapped[dict[str, Any]] = mapped_column(default=dict)
    teacher_score: Mapped[float | None] = mapped_column(default=None)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(default=utcnow)
    assignment: Mapped[Assignment] = relationship(back_populates="submissions")
    user: Mapped[User] = relationship()
