"""Lámina técnica A3 y vista a escala real (`trawlkit.drawing.sheet` / `scale`)."""

from __future__ import annotations

import datetime as dt
import xml.etree.ElementTree as ET

import pytest

from trawlkit.drawing import fmt_es, net_scale_svg, net_sheet_svg
from trawlkit.drawing.sheet import join_fraction, rope_short, spec_for
from trawlkit.io import load_doors, load_net, load_vessels
from trawlkit.model import DesignCase, DesignResult, run

NS = "{http://www.w3.org/2000/svg}"


@pytest.fixture(scope="module")
def result() -> DesignResult:
    vessels = {v.id: v for v in load_vessels().vessels}
    design = vessels["fao_a3_150hp"]
    return run(
        DesignCase(
            net=load_net("fao_a3_standard"),
            vessel=design,
            door=load_doors().doors[0],
            net_modified=load_net("fao_a3_modified"),
            class_vessels=tuple(v for v in vessels.values() if v.id != design.id),
        )
    )


def _texts(doc: str) -> list[str]:
    root = ET.fromstring(doc.split("\n", 1)[1])
    assert root.tag == f"{NS}svg"
    return ["".join(t.itertext()) for t in root.iter(f"{NS}text")]


@pytest.fixture(scope="module")
def std_texts(result: DesignResult) -> list[str]:
    return _texts(net_sheet_svg(result, "std", year=2014))


@pytest.fixture(scope="module")
def mod_texts(result: DesignResult) -> list[str]:
    return _texts(net_sheet_svg(result, "mod"))


def _has(texts: list[str], fragment: str) -> bool:
    return any(fragment in t for t in texts)


def test_fmt_es() -> None:
    assert fmt_es(28.698) == "28,70"
    assert fmt_es(1052.63, 0) == "1053"
    assert fmt_es(-0.001) == "0,00"
    assert fmt_es(2.5, 1) == "2,5"
    assert join_fraction(117, 156) == "3/4"
    assert join_fraction(243, 162) == "2/3"
    assert rope_short("COMBINADO 12 Acero6x24+7", 12) == "COMB. Ø12 mm"
    assert rope_short("PP 14 Retorcido", 14.5) == "PP Ø14,5 mm"


def test_sheet_is_a3_and_valid_xml(result: DesignResult) -> None:
    doc = net_sheet_svg(result)
    root = ET.fromstring(doc.split("\n", 1)[1])
    assert root.get("viewBox") == "0 0 1587 1123"
    assert len(list(root.iter(f"{NS}polygon"))) > 20
    with pytest.raises(ValueError):
        net_sheet_svg(result, "x")
    assert spec_for(result, "mod").id == "fao_a3_modified"


def test_sheet_panels_meshes_and_codes(std_texts: list[str]) -> None:
    for letter in "ABCDEFGHIJ":
        assert letter in std_texts
    for meshes in ("3", "57", "117", "(156)", "100", "412", "372", "97", "129", "143", "86"):
        assert meshes in std_texts, meshes
    for meshes in ("162", "243", "113"):
        assert meshes in std_texts
    for code in ("1N2B", "1N4B", "AB", "3/4", "2/3"):
        assert code in std_texts, code


def test_sheet_tables_and_lengths(result: DesignResult, std_texts: list[str]) -> None:
    dims = result.dimensions.std
    for header in ("Material", "Runnage", "Nº de mallas", "Mallero", "Ø hilo", "Largo"):
        assert header in std_texts
    assert std_texts.count("NY") == 12
    for v in ("781", "1053", "1,37", "1,16", "2,88", "9,60", "12,60", "8,00", "10,00"):
        assert v in std_texts, v
    assert "LARGO TOTAL 40,68 m" in std_texts
    assert f"LARGO TOTAL {fmt_es(dims.total_length_m)} m" in std_texts  # 42,68 m (vientre)
    assert f"Lima {fmt_es(dims.headrope_m)} m" in std_texts  # 28,70 m
    assert f"Burlón {fmt_es(dims.footrope_m)} m" in std_texts
    assert _has(std_texts, f"{fmt_es(dims.headrope.wing_corrected_m)} m · COMB. Ø12 mm")
    assert _has(std_texts, f"{fmt_es(dims.footrope.wing_corrected_m)} m · COMB. Ø14 mm")
    assert f"{fmt_es(dims.headrope.bosom_corrected_m)} m" in std_texts
    assert f"{fmt_es(dims.fishing_circle_m)} m" in std_texts  # 44,64 m
    assert f"{fmt_es(dims.wingtip_reinforcement_m)} m" in std_texts


def test_sheet_surface_weight_rigging_and_title(result: DesignResult, std_texts: list[str]) -> None:
    geo = result.geometry.std
    for plane in ("upper", "lower"):
        assert fmt_es(geo.solid_surface_by_plane[plane]) in std_texts
        assert fmt_es(geo.weight_by_plane[plane]) in std_texts
    assert fmt_es(geo.solid_surface_m2) in std_texts
    assert fmt_es(geo.weight_air_kg) in std_texts
    for label in ("Paneles inferiores", "Paneles superiores", "Total", "Sección de la red"):
        assert label in std_texts
    assert f"Ø {result.warps.selection.diameter_mm:g} mm" in std_texts
    assert f"{result.floats.count} boyas de Ø 200 mm" in std_texts
    assert f"Lastre total = {fmt_es(result.ballast.limits.max_kg, 0)} kg" in std_texts
    assert f"Patentes {fmt_es(result.bridles.sweeps_m)} m" in std_texts
    assert _has(std_texts, "Ángulo de ataque: 32°")
    assert _has(std_texts, "CD: 0,71")
    assert _has(std_texts, "1,90 m × 0,95 m")
    assert "RED DE ARRASTRE DE FONDO FAO A-3" in std_texts
    assert _has(std_texts, "CON BOLSA ESTÁNDAR")
    assert "PARA 150HP A 180HP" in std_texts
    assert "Ariel Luján Giamportone" in std_texts
    assert "Ingeniería Pesquera · UTN Ushuaia" in std_texts
    assert "2014" in std_texts
    assert "corregido" in std_texts


def test_modified_sheet(result: DesignResult, mod_texts: list[str]) -> None:
    assert "I'" in mod_texts
    assert "I" not in mod_texts and "J" not in mod_texts
    assert "30" in mod_texts and "139" in mod_texts and "300" in mod_texts
    assert _has(mod_texts, "MODIFICADA PARA CRUSTÁCEOS")
    assert _has(mod_texts, "MALLA 30 mm")
    assert mod_texts.count("LARGO TOTAL 41,68 m") == 2
    assert str(dt.date.today().year) in mod_texts
    geo = result.geometry.mod
    assert fmt_es(geo.solid_surface_by_plane["upper"]) in mod_texts


def test_scale_sheet(result: DesignResult) -> None:
    for variant, stretched_total in (("std", "42,68"), ("mod", "41,68")):
        texts = _texts(net_scale_svg(result, variant))
        assert "Escala gráfica" in texts
        assert {"0", "1", "5"} <= set(texts)
        assert _has(texts, f"estirado): {stretched_total} m")
        assert _has(texts, "Largo total ")
        assert _has(texts, "Boca ")
        assert "PLANO SUPERIOR (DORSO)" in texts
    texts = _texts(net_scale_svg(result))
    assert _has(texts, "G→H")  # escalón por U1 distinto (0,38 → 0,23)
