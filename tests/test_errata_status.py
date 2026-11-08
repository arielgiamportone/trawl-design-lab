"""Fase 20.7: el estado de cada errata es el declarado en ``trawlkit.compat.ERRATA``.

La app (``GET /errata``; el modo sin conexión lo compara ``test_offline.py``), el informe,
``docs/erratas.md`` y los indicadores del README muestran el mismo estado; ninguno lo deduce por
su cuenta.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trawlkit.api.app import app
from trawlkit.compat import (
    ERRATA,
    ERRATA_BY_KEY,
    STATUS_LABELS,
    Compat,
    ErratumStatus,
    ErratumTreatment,
)
from trawlkit.i18n import t, use_lang
from trawlkit.model import run
from trawlkit.report.tables import ERRATA_FIXED_TREATMENT, errata_table

from .test_report_tables import make_case

ROOT = Path(__file__).resolve().parents[1]


def test_declared_status_by_mode() -> None:
    for e in ERRATA:
        if e.treatment is ErratumTreatment.BY_MODE:
            assert e.note is None, e.key
            assert e.status(Compat.EXCEL) is ErratumStatus.REPRODUCED
            assert e.status(Compat.CORRECTED) is ErratumStatus.CORRECTED
        else:
            assert e.note, e.key
            assert e.status(Compat.EXCEL) is e.status(Compat.CORRECTED)
            assert e.status(Compat.CORRECTED).value == e.treatment.value
    assert set(ERRATA_FIXED_TREATMENT) == {
        e.key for e in ERRATA if e.treatment is not ErratumTreatment.BY_MODE
    }


def test_documented_errata_are_not_called_corrected() -> None:
    """Una errata que la descripción da por «no corregida» no puede figurar como corregida."""
    fridman = ERRATA_BY_KEY["fridman_dp_warp_saturation"]
    assert fridman.treatment is ErratumTreatment.DOCUMENTED
    assert ERRATA_BY_KEY["nomura_column_links_hamuro"].treatment is ErratumTreatment.DOCUMENTED
    for e in ERRATA:
        if re.search(r"no corregid", e.description):
            assert e.status(Compat.CORRECTED) is not ErratumStatus.CORRECTED, e.key
    counts = Counter(e.status(Compat.CORRECTED) for e in ERRATA)
    assert counts == {
        ErratumStatus.CORRECTED: 24,
        ErratumStatus.REPRODUCED: 2,
        ErratumStatus.DOCUMENTED: 2,
    }


@pytest.mark.parametrize("compat", list(Compat))
def test_report_table_shows_the_declared_status(compat: Compat) -> None:
    table = errata_table(run(make_case(compat)))
    shown = dict(zip(table.column("key"), table.column("status"), strict=True))
    for e in ERRATA:
        assert shown[e.key] == STATUS_LABELS[e.status(compat)], e.key


def test_api_shows_the_declared_status() -> None:
    api = TestClient(app).get("/errata").json()
    assert [r["key"] for r in api] == [e.key for e in ERRATA]
    for row in api:
        e = ERRATA_BY_KEY[row["key"]]
        assert row["treatment"] == e.treatment.value
        assert row["status_excel"] == e.status(Compat.EXCEL).value
        assert row["status_corrected"] == e.status(Compat.CORRECTED).value
        assert row["note"] == (t(e.note) if e.note else None)


def test_web_fixture_is_the_api_output() -> None:
    """``web/src/test/fixtures/errata.json`` (la app en los tests) es la salida de la API."""
    fixture = json.loads((ROOT / "web/src/test/fixtures/errata.json").read_text(encoding="utf-8"))
    assert fixture == TestClient(app).get("/errata").json()


@pytest.mark.parametrize(
    ("path", "lang"), [("docs/erratas.md", "es"), ("docs/en/erratas.md", "en")]
)
def test_docs_table_shows_the_declared_status(path: str, lang: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    shown = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) > 6 and cells[1] in ERRATA_BY_KEY:
            shown[cells[1]] = cells[5]
    assert set(shown) == set(ERRATA_BY_KEY)
    with use_lang(lang):
        for e in ERRATA:
            assert shown[e.key] == t(STATUS_LABELS[e.status(Compat.CORRECTED)]), e.key
    counts = Counter(e.status(Compat.CORRECTED) for e in ERRATA)
    nums = (
        (counts[ErratumStatus.CORRECTED], "corregidas" if lang == "es" else "corrected"),
        (counts[ErratumStatus.REPRODUCED], "reproducidas" if lang == "es" else "reproduced"),
        (counts[ErratumStatus.DOCUMENTED], "documentadas" if lang == "es" else "documented"),
    )
    flat = " ".join(text.split())
    for n, word in nums:
        assert f"{n} {word}" in flat
