"""Conexión a la base del aula.

``DATABASE_URL`` (Postgres de Neon en producción; ``sqlite:///aula.db`` en desarrollo) habilita el
aula. Sin esa variable las rutas ``/classroom`` responden 503 y el resto de la API sigue igual: en
el plan gratuito de Render el disco se borra en cada despliegue, así que no se crea una base local
por defecto.
"""

from __future__ import annotations

import os
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from functools import cache
from typing import Any

from sqlalchemy import Engine, create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from trawlkit.classroom.models import SCHEMA_VERSION, Base, Setting

ENV = "DATABASE_URL"


class NotConfiguredError(RuntimeError):
    """El aula no tiene base de datos configurada."""


def normalise_url(url: str) -> str:
    """Acepta las URL de Neon/Heroku (``postgres://``) y usa el driver psycopg 3."""
    u = url.strip()
    for prefix in ("postgres://", "postgresql://"):
        if u.startswith(prefix):
            return "postgresql+psycopg://" + u[len(prefix) :]
    return u


def database_url() -> str | None:
    """La URL configurada, o ``None``."""
    raw = os.environ.get(ENV, "").strip()
    return normalise_url(raw) if raw else None


@cache
def _engine(url: str) -> Engine:
    kwargs: dict[str, Any] = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs = {"connect_args": {"check_same_thread": False}}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
    eng = create_engine(url, **kwargs)
    if url.startswith("sqlite"):

        @event.listens_for(eng, "connect")
        def _fk(dbapi_conn: Any, _rec: Any) -> None:
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    return eng


def engine() -> Engine:
    """Motor de la base configurada (``NotConfiguredError`` si no hay)."""
    url = database_url()
    if url is None:
        raise NotConfiguredError(
            "El aula no está configurada en este servidor (falta DATABASE_URL)."
        )
    return _engine(url)


@cache
def _sessions(url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=_engine(url), expire_on_commit=False)


def init_db(eng: Engine | None = None) -> None:
    """Crea las tablas que falten y registra la versión del esquema y el secreto de semillas."""
    eng = eng or engine()
    Base.metadata.create_all(eng)
    with Session(eng) as s:
        if s.get(Setting, "schema_version") is None:
            s.add(Setting(key="schema_version", value=str(SCHEMA_VERSION)))
        if s.get(Setting, "seed_secret") is None:
            s.add(Setting(key="seed_secret", value=secrets.token_hex(16)))
        s.commit()


_READY: set[str] = set()


@contextmanager
def session() -> Iterator[Session]:
    """Sesión de la base (crea las tablas la primera vez)."""
    eng = engine()
    url = str(eng.url)
    if url not in _READY:
        init_db(eng)
        _READY.add(url)
    with _sessions(database_url() or "")() as s:
        yield s


def seed_secret(s: Session) -> str:
    """Secreto con que se derivan las semillas de cada alumno."""
    row = s.scalar(select(Setting).where(Setting.key == "seed_secret"))
    if row is None:  # pragma: no cover - init_db siempre lo crea
        raise NotConfiguredError("falta el secreto de semillas: corra trawlkit classroom migrate")
    return row.value


def reset_for_tests() -> None:
    """Olvida motores y tablas creadas (para las pruebas con otra ``DATABASE_URL``)."""
    _engine.cache_clear()
    _sessions.cache_clear()
    _READY.clear()
