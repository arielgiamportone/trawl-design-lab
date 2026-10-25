"""Fase 12: catálogo de redes FAO, procedencia por valor y validador de consistencia."""

from __future__ import annotations

import dataclasses

import pytest

from trawlkit.io.loader import NETS_DIR, load_net
from trawlkit.io.schema import NetSpec
from trawlkit.model import run
from trawlkit.netcheck import check, errors, summary
from trawlkit.provenance import coverage, provenance_of
from trawlkit.sim import simulate
from trawlkit.sim.validation import standard_case

CATALOGUE = sorted(p.stem for p in NETS_DIR.glob("*.yaml"))


def test_catalogue_is_not_empty() -> None:
    assert len(CATALOGUE) >= 3


@pytest.mark.parametrize("net_id", CATALOGUE)
def test_catalogue_net_is_consistent_and_sourced(net_id: str) -> None:
    spec = load_net(net_id)
    assert spec.id == net_id
    assert spec.family in ("bottom", "semi_pelagic", "pelagic")
    assert spec.rig in ("otter", "pair")
    assert spec.sources and spec.sources[0].url
    assert errors(spec) == []
    cov = coverage(spec)
    assert cov["fraction"] == 1.0, cov["missing"]
    kinds = set(cov["by_kind"])
    assert kinds <= {"transcribed", "derived", "assumed"}
    # Cada valor supuesto o derivado explica de dónde sale.
    for path, prov in spec.provenance.items():
        if prov.kind != "transcribed":
            assert prov.note, path


@pytest.mark.parametrize("net_id", CATALOGUE)
def test_catalogue_net_runs_and_simulates(net_id: str) -> None:
    case = dataclasses.replace(
        standard_case(), net=load_net(net_id), net_modified=None, depth_m=30.0
    )
    result = run(case)
    s = simulate(result, 2.5, resolution=2, coarse_resolution=None, door_spread_m=20.0)
    assert s.converged
    assert 0.5 < s.av_m < 8.0
    assert 3.0 < s.ah_m < 20.0
    assert s.drag_kgf > 0


def test_a3_provenance_is_excel() -> None:
    spec = load_net("fao_a3_standard")
    cov = coverage(spec)
    assert cov["fraction"] == 1.0
    assert set(cov["by_kind"]) == {"excel"}
    prov = provenance_of(spec, "panels.C.meshes_top")
    assert prov is not None and prov.kind == "excel" and prov.note


def test_a3_standard_closes() -> None:
    assert errors(load_net("fao_a3_standard")) == []
    assert summary(load_net("fao_a3_standard"))["ok"]


def _with(spec: NetSpec, pid: str, **changes: object) -> NetSpec:
    panels = [p.model_copy(update=changes) if p.id == pid else p for p in spec.panels]
    return spec.model_copy(update={"panels": panels})


def test_seam_error_detects_misread_count() -> None:
    spec = load_net("fao_a3_standard")
    # H (40 mm) debe empalmar con G (60 mm): 162 × 60 = 243 × 40. Un 243 leído como 343 no cierra.
    bad = _with(spec, "H", meshes_top=343)
    issues = [i for i in check(bad) if i.code == "seam"]
    assert issues and issues[0].level == "error" and "H" in issues[0].panels


def test_mouth_error_when_wings_too_wide() -> None:
    spec = load_net("fao_a3_standard")
    bad = _with(spec, "C", meshes_bottom=300)
    assert any(i.code == "mouth" and i.level == "error" for i in check(bad))


def test_missing_hanging_is_an_error() -> None:
    spec = load_net("fao_a3_standard")
    bad = _with(spec, "E", hanging_ratio=None)
    assert any(i.code == "data" and i.level == "error" for i in check(bad))
