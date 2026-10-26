"""Fase 17.2: aula en el servidor (cuentas, cursos, tareas, entregas, notas) con SQLite."""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

pytest.importorskip("sqlalchemy")

from trawlkit.api.app import app  # noqa: E402
from trawlkit.classroom import db, security  # noqa: E402
from trawlkit.classroom import service as svc  # noqa: E402
from trawlkit.cli import app as cli  # noqa: E402
from trawlkit.teaching import solve  # noqa: E402

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    db.reset_for_tests()
    yield
    db.reset_for_tests()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _admin() -> str:
    with db.session() as s:
        svc.create_admin(s, "admin", "admin-clave", "Administración")
    r = client.post("/classroom/auth/login", json={"username": "admin", "password": "admin-clave"})
    assert r.status_code == 200
    return str(r.json()["token"])


def _teacher(admin: str, name: str = "profe") -> str:
    code = client.post("/classroom/invites", json={"count": 1}, headers=auth(admin)).json()[0][
        "code"
    ]
    r = client.post(
        "/classroom/auth/register",
        json={
            "username": name,
            "password": "docente-123",
            "display_name": "Prof.",
            "invite_code": code,
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["user"]["role"] == "teacher"
    return str(r.json()["token"])


def _student(code: str, name: str) -> tuple[str, int]:
    r = client.post(
        "/classroom/auth/register",
        json={
            "username": name,
            "password": "alumno-123",
            "display_name": name,
            "course_code": code,
        },
    )
    assert r.status_code == 200, r.text
    return str(r.json()["token"]), int(r.json()["user"]["id"])


def _course(teacher: str) -> dict[str, Any]:
    r = client.post(
        "/classroom/courses", json={"name": "TAP", "term": "2026"}, headers=auth(teacher)
    )
    assert r.status_code == 200
    return dict(r.json())


def _assignment(teacher: str, course_id: int, **extra: Any) -> dict[str, Any]:
    body = {
        "title": "TP 1",
        "items": [
            {"kind": "exercise", "ref": "resistencia.aberdeen"},
            {"kind": "lab", "ref": "lab.buque_y_velocidad", "points": 2},
        ],
        **extra,
    }
    r = client.post(f"/classroom/courses/{course_id}/assignments", json=body, headers=auth(teacher))
    assert r.status_code == 200, r.text
    return dict(r.json())


def test_not_configured_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL")
    db.reset_for_tests()
    assert client.get("/classroom/status").json()["enabled"] is False
    r = client.post("/classroom/auth/login", json={"username": "x", "password": "y"})
    assert r.status_code == 503 and "DATABASE_URL" in r.json()["detail"]
    assert client.post("/design", json={}).status_code == 200


def test_security_helpers() -> None:
    h = security.hash_password("una clave")
    assert h.startswith("scrypt$") and security.verify_password("una clave", h)
    assert not security.verify_password("otra", h) and not security.verify_password("x", "basura")
    assert security.token_hash("t") != "t" and len(security.new_token()) > 30
    a = security.student_seed("s", 1, 2, 0)
    assert a == security.student_seed("s", 1, 2, 0) != security.student_seed("s", 1, 3, 0)
    assert security.normalise_code(" ab-12 ") == "AB12"
    assert db.normalise_url("postgres://u:p@h/d") == "postgresql+psycopg://u:p@h/d"


def test_full_flow_teacher_student_grades() -> None:
    admin = _admin()
    teacher = _teacher(admin)
    course = _course(teacher)
    assert course["code"] and course["role"] == "teacher"
    a = _assignment(teacher, course["id"])
    st1, id1 = _student(course["code"], "alumno1")
    st2, _ = _student(course["code"].lower(), "alumno2")

    me = client.get("/classroom/me", headers=auth(st1)).json()
    assert me["role"] == "student" and me["courses"][0]["code"] is None

    v1 = client.get(f"/classroom/assignments/{a['id']}", headers=auth(st1)).json()
    client.get(f"/classroom/assignments/{a['id']}", headers=auth(st2)).json()
    ex1 = v1["item_list"][0]["exercise"]
    assert ex1["seed"] is None and "rn_kgf" not in str(ex1["data"])
    assert v1["item_list"][1]["lab"]["id"] == "lab.buque_y_velocidad"

    with db.session() as s:
        seed = svc._seed(s, s.get(svc.Assignment, a["id"]), id1, 0)
    right = solve("resistencia.aberdeen", seed).values["rn_kgf"]
    wrong = client.post(
        f"/classroom/assignments/{a['id']}/items/0/submit",
        json={"answers": {"rn_kgf": "1"}},
        headers=auth(st1),
    ).json()
    assert wrong["score"] == 0 and wrong["result"]["answers"][0]["expected"] is None
    ok = client.post(
        f"/classroom/assignments/{a['id']}/items/0/submit",
        json={"answers": {"rn_kgf": str(right).replace(".", ",")}},
        headers=auth(st1),
    ).json()
    assert ok["score"] == 1.0 and ok["attempt"] == 2
    lab = client.post(
        f"/classroom/assignments/{a['id']}/items/1/submit",
        json={
            "steps": {
                "base": {"design": {}, "answers": {"vmax": "2,27"}},
                "buque": {
                    "design": {"vessel": "fao_a3_180hp"},
                    "answers": {"vmax": "2,52", "rn": "No: la red es la misma"},
                },
            }
        },
        headers=auth(st1),
    ).json()
    assert lab["score"] == 1.0

    g = client.get(f"/classroom/assignments/{a['id']}/grades", headers=auth(teacher)).json()
    row = next(r for r in g["rows"] if r["student"]["username"] == "alumno1")
    assert g["total_points"] == 3 and row["points"] == 3.0
    assert [c["attempts"] for c in row["cells"]] == [2, 1]
    other = next(r for r in g["rows"] if r["student"]["username"] == "alumno2")
    assert other["points"] == 0 and other["cells"][0]["score"] is None

    sid = row["cells"][0]["submission_id"]
    det = client.get(f"/classroom/submissions/{sid}", headers=auth(teacher)).json()
    assert det["seed"] == seed and det["student"]["username"] == "alumno1"
    rev = client.patch(
        f"/classroom/submissions/{sid}",
        json={"teacher_score": 0.5, "comment": "revise las unidades"},
        headers=auth(teacher),
    ).json()
    assert rev["teacher_score"] == 0.5
    g = client.get(f"/classroom/assignments/{a['id']}/grades", headers=auth(teacher)).json()
    assert next(r for r in g["rows"] if r["student"]["id"] == id1)["points"] == 2.5

    csv = client.get(
        f"/classroom/assignments/{a['id']}/grades/export?format=csv", headers=auth(teacher)
    )
    assert csv.status_code == 200 and "alumno1" in csv.text
    xlsx = client.get(f"/classroom/assignments/{a['id']}/grades/export", headers=auth(teacher))
    assert xlsx.content[:2] == b"PK"
    sheet = client.get(
        f"/classroom/assignments/{a['id']}/sheet?all_students=true&key=true", headers=auth(teacher)
    )
    assert sheet.status_code == 200 and sheet.text.count("<h1>") == 2
    assert "Clave de respuestas" in sheet.text


def test_permissions_between_users_and_courses() -> None:
    admin = _admin()
    t1, t2 = _teacher(admin, "profe1"), _teacher(admin, "profe2")
    c1, c2 = _course(t1), _course(t2)
    a1 = _assignment(t1, c1["id"])
    s1, id1 = _student(c1["code"], "alumno1")
    s2, _ = _student(c2["code"], "alumno2")

    assert (
        client.get(f"/classroom/courses/{c1['id']}/students", headers=auth(t2)).status_code == 403
    )
    assert client.get(f"/classroom/assignments/{a1['id']}", headers=auth(s2)).status_code == 403
    assert (
        client.get(f"/classroom/assignments/{a1['id']}/grades", headers=auth(s1)).status_code == 403
    )
    assert (
        client.post("/classroom/courses", json={"name": "x"}, headers=auth(s1)).status_code == 403
    )
    assert client.post("/classroom/invites", json={}, headers=auth(t1)).status_code == 403
    r = client.post(
        f"/classroom/assignments/{a1['id']}/items/0/submit", json={"answers": {}}, headers=auth(t1)
    )
    assert r.status_code == 403
    sub = client.post(
        f"/classroom/assignments/{a1['id']}/items/0/submit", json={"answers": {}}, headers=auth(s1)
    ).json()
    assert client.get(f"/classroom/submissions/{sub['id']}", headers=auth(s2)).status_code == 403
    assert client.get("/classroom/me").status_code == 401
    assert client.get("/classroom/me", headers=auth("x")).status_code == 401

    # Reset de contraseña por el docente: cierra las sesiones del alumno.
    r = client.post(
        f"/classroom/courses/{c1['id']}/students/{id1}/password",
        json={"password": "nueva-clave"},
        headers=auth(t1),
    )
    assert r.status_code == 204
    assert client.get("/classroom/me", headers=auth(s1)).status_code == 401
    r = client.post(
        "/classroom/auth/login", json={"username": "alumno1", "password": "nueva-clave"}
    )
    assert r.status_code == 200


def test_attempts_due_date_and_after_due_feedback() -> None:
    admin = _admin()
    t = _teacher(admin)
    c = _course(t)
    soon = dt.datetime.now(dt.UTC) + dt.timedelta(days=1)
    a = _assignment(t, c["id"], max_attempts=1, feedback="after_due", due_at=soon.isoformat())
    st, _ = _student(c["code"], "alumno1")
    url = f"/classroom/assignments/{a['id']}/items/0/submit"
    r = client.post(url, json={"answers": {"rn_kgf": "1"}}, headers=auth(st)).json()
    assert r["score"] is None and r["message"] == "entrega recibida"
    assert client.post(url, json={"answers": {}}, headers=auth(st)).status_code == 409
    # Cierra la tarea: ahora se ve la corrección con la solución.
    with db.session() as s:
        row = s.get(svc.Assignment, a["id"])
        row.due_at = svc.utcnow() - dt.timedelta(minutes=1)
        s.commit()
    v = client.get(f"/classroom/assignments/{a['id']}", headers=auth(st)).json()
    seen = v["item_list"][0]["submissions"][0]
    assert seen["score"] == 0 and seen["result"]["answers"][0]["expected"] is not None
    assert client.post(url, json={"answers": {}}, headers=auth(st)).status_code == 409


def test_hidden_until_open_and_validation() -> None:
    admin = _admin()
    t = _teacher(admin)
    c = _course(t)
    later = (dt.datetime.now(dt.UTC) + dt.timedelta(days=3)).isoformat()
    a = _assignment(t, c["id"], opens_at=later)
    st, _ = _student(c["code"], "alumno1")
    assert client.get(f"/classroom/courses/{c['id']}/assignments", headers=auth(st)).json() == []
    assert client.get(f"/classroom/assignments/{a['id']}", headers=auth(st)).status_code == 404
    bad = {"title": "x", "items": [{"kind": "exercise", "ref": "nada.nada"}]}
    r = client.post(f"/classroom/courses/{c['id']}/assignments", json=bad, headers=auth(t))
    assert r.status_code == 422
    r = client.post(
        f"/classroom/courses/{c['id']}/assignments",
        json={**bad, "items": [{"kind": "lab", "ref": "lab.taller"}], "feedback": "after_due"},
        headers=auth(t),
    )
    assert r.status_code == 422  # devolución al cierre sin fecha de cierre


def test_registration_rules_and_lockout() -> None:
    admin = _admin()
    t = _teacher(admin)
    c = _course(t)
    base = {"password": "alumno-123", "display_name": "x", "course_code": c["code"]}
    assert (
        client.post("/classroom/auth/register", json={**base, "username": "A B"}).status_code == 422
    )
    assert (
        client.post(
            "/classroom/auth/register", json={**base, "username": "okey", "course_code": "NOPE"}
        ).status_code
        == 404
    )
    _student(c["code"], "alumno1")
    assert (
        client.post("/classroom/auth/register", json={**base, "username": "alumno1"}).status_code
        == 409
    )
    for _ in range(svc.MAX_FAILED):
        r = client.post("/classroom/auth/login", json={"username": "alumno1", "password": "mal"})
        assert r.status_code == 401
    r = client.post("/classroom/auth/login", json={"username": "alumno1", "password": "alumno-123"})
    assert r.status_code == 429
    # Una invitación usada no sirve dos veces.
    code = client.post("/classroom/invites", json={}, headers=auth(admin)).json()[0]["code"]
    body = {"password": "docente-123", "display_name": "p", "invite_code": code}
    assert (
        client.post("/classroom/auth/register", json={**body, "username": "prof1"}).status_code
        == 200
    )
    assert (
        client.post("/classroom/auth/register", json={**body, "username": "prof2"}).status_code
        == 404
    )


def test_delete_account_and_course_management() -> None:
    admin = _admin()
    t = _teacher(admin)
    c = _course(t)
    a = _assignment(t, c["id"])
    st, sid = _student(c["code"], "alumno1")
    client.post(
        f"/classroom/assignments/{a['id']}/items/0/submit", json={"answers": {}}, headers=auth(st)
    )
    r = client.patch(f"/classroom/courses/{c['id']}", json={"new_code": True}, headers=auth(t))
    assert r.json()["code"] != c["code"]
    assert (
        client.post("/classroom/me/delete", json={"password": "mal"}, headers=auth(st)).status_code
        == 403
    )
    assert (
        client.post(
            "/classroom/me/delete", json={"password": "alumno-123"}, headers=auth(st)
        ).status_code
        == 204
    )
    g = client.get(f"/classroom/assignments/{a['id']}/grades", headers=auth(t)).json()
    assert g["rows"] == []
    with db.session() as s:
        assert s.get(svc.User, sid) is None
    # Los ítems no se cambian cuando ya hay entregas; sin entregas, sí.
    r = client.patch(
        f"/classroom/assignments/{a['id']}",
        json={"items": [{"kind": "lab", "ref": "lab.taller"}]},
        headers=auth(t),
    )
    assert r.status_code == 200
    assert client.delete(f"/classroom/assignments/{a['id']}", headers=auth(t)).status_code == 204


def test_cli_admin_and_invites(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'aula.db'}")
    db.reset_for_tests()
    runner = CliRunner()
    assert runner.invoke(cli, ["classroom", "migrate"]).exit_code == 0
    res = runner.invoke(
        cli, ["classroom", "create-admin", "--username", "jefe", "--password", "clave-segura"]
    )
    assert res.exit_code == 0, res.output
    res = runner.invoke(cli, ["classroom", "invite", "--username", "jefe", "--count", "2"])
    assert res.exit_code == 0 and len(res.output.strip().splitlines()) == 2
    monkeypatch.delenv("DATABASE_URL")
    assert runner.invoke(cli, ["classroom", "migrate"]).exit_code != 0
