"""Fase 19.1: tabla de materiales con fuentes, rigidez axial, validador y simulador."""

from __future__ import annotations

import dataclasses
import math

import numpy as np
import pytest

from trawlkit.compat import Compat
from trawlkit.components import (
    DENSITY_KG_M3,
    RopeItem,
    TwineItem,
    WireItem,
    axial_stiffness,
    check,
    elongation_range_pct,
    parse_component,
)
from trawlkit.i18n import use_lang
from trawlkit.io import load_catalogue
from trawlkit.io.schema import NetSpec, ProvenanceKind
from trawlkit.materials import (
    POLYMER_DENSITY_KG_M3,
    ea_from_breaking_load_n,
    find_material,
    material_table,
    materials_from_catalogue,
    polymer_density,
    rope_ea_n,
    twine_modulus_pa,
    wire_core,
    wire_rope_ea_n,
    wire_rope_modulus_pa,
)
from trawlkit.model import DesignResult, run
from trawlkit.report.labels import label
from trawlkit.rigging import warp_elastic_stretch_m, warp_tension_kgf
from trawlkit.sim import rigging_from_result, simulate
from trawlkit.sim.mesh import DEFAULT_BRIDLE_EA_N, build_model, twine_weight_water_n_m
from trawlkit.sim.validation import standard_case

FIBRES = ("PA", "PES", "PE", "PP", "HMPE")


@pytest.fixture(scope="module")
def result() -> DesignResult:
    return run(standard_case())


def with_material(spec: NetSpec, material: str) -> NetSpec:
    panels = [p.model_copy(update={"material": material}) for p in spec.panels]
    return spec.model_copy(update={"panels": panels})


# ------------------------------------------------------------------------------------------
# Tabla
# ------------------------------------------------------------------------------------------


def test_material_table_loads_with_sources() -> None:
    tab = material_table()
    expected = {*FIBRES, "steel_wire_rope", "combination_steel_pp", "chain_steel"}
    assert expected <= set(tab.materials)
    for m in tab.materials.values():
        assert m.values, m.id
        for key, v in m.values.items():
            where = f"{m.id}.{key}"
            if v.kind is ProvenanceKind.ASSUMED:
                assert v.note and "A VERIFICAR" in v.note, where
            else:
                assert v.source, where
                assert v.kind in (ProvenanceKind.TRANSCRIBED, ProvenanceKind.DERIVED), where
            if v.kind is ProvenanceKind.DERIVED:
                assert v.note, f"{where}: derivado sin fórmula"
            if v.range is not None:
                assert v.range[0] <= v.value <= v.range[1], where
    # Toda clave citada está en la bibliografía de la tabla; Klust no se cita (no consultado).
    assert tab.sources() <= set(tab.references)
    assert "klust1982" not in tab.sources()
    assert any("A VERIFICAR" in s for s in tab.to_verify())


@pytest.mark.parametrize(
    ("name", "rho", "sea"),
    [("PA", 1140, 0.10), ("PES", 1380, 0.26), ("PE", 950, -0.08), ("PP", 910, -0.14)],
)
def test_densities_and_weight_in_water_factors(name: str, rho: float, sea: float) -> None:
    m = material_table()[name]
    assert m.value("density_kg_m3") == rho
    assert m.value("weight_in_water_seawater") == pytest.approx(sea)
    # Coherente con 1 − ρ_agua/ρ (prado1990 usa 1,026 g/cm³; el PP del libro con ρ = 0,90).
    assert 1 - 1026 / rho == pytest.approx(sea, abs=0.02)


def test_aliases_and_backwards_compatible_catalogue() -> None:
    tab = material_table()
    assert tab.find("UHMWPE") is tab.find("hmpe") is tab.find("Dyneema")
    assert tab.find("combinado (PP + acero)") is tab.materials["combination_steel_pp"]
    assert tab.find("acero") is tab.materials["steel_wire_rope"]
    assert tab.find("KEVLAR") is None
    # Los lectores de siempre ven lo mismo.
    cat = load_catalogue("materials")
    assert [it["id"] for it in cat.items] == ["pa_r1280tex", "pa_r950tex"]
    assert POLYMER_DENSITY_KG_M3 == {"PE": 950, "PP": 910, "PES": 1380, "UHMWPE": 970}
    assert DENSITY_KG_M3["PA"] == 1140 and DENSITY_KG_M3["HMPE"] == 970
    mats = materials_from_catalogue(cat)
    assert find_material(mats, "HMPE").density_kg_m3 == 970  # alias de UHMWPE
    assert polymer_density("KEVLAR") == 1140  # sin dato: PA


def test_twine_modulus_by_material() -> None:
    assert twine_modulus_pa("PA") == pytest.approx(2.0e9)
    assert twine_modulus_pa("PE") == pytest.approx(0.60e9)
    # Escalados por el cociente de módulos de fibra de bexco2004 (p. 14).
    assert twine_modulus_pa("PES") == pytest.approx(2.0e9 * 9000 / 5500, rel=2e-3)
    assert twine_modulus_pa("PP") == pytest.approx(2.0e9 * 4200 / 5500, rel=2e-3)
    assert twine_modulus_pa("desconocido") == pytest.approx(2.0e9)
    # PA R1280tex Ø1,37 mm: 2,30 N/tex, del orden de 4,8 N/tex × 0,45–0,51 (informe §5b).
    ea = twine_modulus_pa("PA") * math.pi * 1.37e-3**2 / 4
    assert ea / 1280 == pytest.approx(2.30, abs=0.01)


def test_rope_and_wire_ea_relations() -> None:
    assert rope_ea_n("PP", 14) == pytest.approx(1060 * 14**2)
    assert rope_ea_n("PA", 12) == pytest.approx(17_000, rel=0.01)  # 1,18·10⁵ d² kN
    assert rope_ea_n("PE", 12) is None  # sin relación con fuente
    assert rope_ea_n("combinado", 12) == 1.0e6  # supuesto A VERIFICAR
    # 6x19: 46,9 GPa (FC) y 51,4 GPa (IWRC) sobre el área nominal = k·d².
    for core, e in (("FC", 46.9e9), ("IWRC", 51.4e9)):
        assert wire_rope_modulus_pa(core) == pytest.approx(e)
        # k (transcripto) y E (derivado, 0,455 · E metálico) difieren por redondeo (< 0,5 %).
        assert wire_rope_ea_n(13, core) == pytest.approx(e * math.pi / 4 * 13e-3**2, rel=5e-3)
    assert wire_core(None, "6x19 (9/9/1)") == "FC"
    assert wire_core("IWRC") == "IWRC" and wire_core("FC o IWRC") == "FC"
    # La EA de bridas del simulador (4·10⁶ N) es un 6x19 FC de ≈ 10,4 mm (informe §5d).
    assert math.sqrt(DEFAULT_BRIDLE_EA_N / wire_rope_ea_n(1.0)) == pytest.approx(10.4, abs=0.05)


# ------------------------------------------------------------------------------------------
# Componentes: EA y validador
# ------------------------------------------------------------------------------------------


def _rope(**kw: object) -> RopeItem:
    data = {
        "kind": "rope",
        "id": "t_rope",
        "name": "prueba",
        "material": "PP",
        "diameter_mm": 14.0,
        "weight_kg_per_m": 0.125,
        "breaking_load_t": 3.7,
        **kw,
    }
    item = parse_component(data)
    assert isinstance(item, RopeItem)
    return item


def test_ea_derivation_order() -> None:
    ea, prov = axial_stiffness(_rope(ea_kn=250.0)) or (0.0, None)
    assert ea == 250.0 and prov is not None and prov.kind is ProvenanceKind.TRANSCRIBED
    got = axial_stiffness(_rope(elongation_pct=20.0))
    assert got is not None and got[1].kind is ProvenanceKind.DERIVED
    assert got[0] == pytest.approx(3.7 * 1000 * 9.80665 / 0.20 / 1000)
    assert ea_from_breaking_load_n(1000.0, 10.0) == 10_000.0
    with pytest.raises(ValueError):
        ea_from_breaking_load_n(1000.0, 0.0)
    got = axial_stiffness(_rope())
    assert got is not None and got[0] == pytest.approx(1060 * 14**2 / 1000)
    assert got[1].document == "orcina_ropewire"
    comb = axial_stiffness(_rope(material="combinado"))
    assert comb is not None and comb[0] == 1000.0 and comb[1].kind is ProvenanceKind.ASSUMED
    assert axial_stiffness(_rope(material="PE")) is None
    wire = parse_component(
        {
            "kind": "wire",
            "id": "t_wire",
            "name": "prueba",
            "construction": "6x19 (9/9/1)",
            "core": "IWRC",
            "diameter_mm": 12.0,
            "weight_kg_per_m": 0.59,
            "breaking_load_t": 9.0,
        }
    )
    assert isinstance(wire, WireItem)
    got = axial_stiffness(wire)
    assert got is not None and got[0] == pytest.approx(40_400 * 144 / 1000)


def test_validator_material_warnings() -> None:
    # PP: tenacidad del cabo del Workbook 26,9–32,4 gf/tex (± 10 %); 60 gf/tex avisa.
    assert "tenacity" not in {i.code for i in check(_rope())}
    strong = check(_rope(breaking_load_t=7.5))
    assert {i.code for i in strong} == {"tenacity"}
    assert all(i.level == "warning" for i in strong)
    # Alargamiento del PP: 10 % (cabo al 75 % de la rotura) a 12 % (fibra) ± 10 %.
    lo, hi = elongation_range_pct("PP") or (0.0, 0.0)
    assert lo == pytest.approx(9.0) and hi == pytest.approx(13.2)
    assert "elongation" in {i.code for i in check(_rope(elongation_pct=40.0))}
    assert "elongation" not in {i.code for i in check(_rope(elongation_pct=11.0))}
    # Hilo de PE: seco sin nudo 27–39,5 gf/tex.
    twine = parse_component(
        {
            "kind": "twine",
            "id": "t_twine",
            "name": "prueba",
            "material": "PE",
            "rtex": 1000.0,
            "diameter_mm": 1.5,
            "breaking_load_kgf": 60.0,
        }
    )
    assert isinstance(twine, TwineItem)
    codes = {i.code for i in check(twine)}
    assert "tenacity_material" in codes and "tenacity" not in codes
    # Cable: sólo cota inferior (el alambre se alarga 1,1 %).
    assert math.isinf((elongation_range_pct("steel") or (0.0, 0.0))[1])
    wire = parse_component(
        {
            "kind": "wire",
            "id": "t_wire",
            "name": "prueba",
            "construction": "6x19",
            "diameter_mm": 12.0,
            "weight_kg_per_m": 0.52,
            "breaking_load_t": 7.0,
            "elongation_pct": 0.5,
        }
    )
    assert {i.code for i in check(wire)} == {"elongation"}
    with use_lang("en"):
        assert "below" in check(wire)[0].message


# ------------------------------------------------------------------------------------------
# Simulador
# ------------------------------------------------------------------------------------------


def test_twine_weight_sign_by_material(result: DesignResult) -> None:
    panel = result.case.net.panels[0]
    w = {m: twine_weight_water_n_m(panel.model_copy(update={"material": m})) for m in FIBRES}
    assert w["PA"] > 0 and w["PES"] > w["PA"]
    assert w["PP"] < w["PE"] < 0 and w["HMPE"] < 0
    # Sin cambio para el PA: (1 − 1024/1140) como antes de la Fase 19.1.
    assert w["PA"] == pytest.approx(9.80665 / panel.runnage_m_per_kg * (1 - 1024 / 1140))  # type: ignore[operator]


def test_pp_net_is_buoyant_and_its_codend_rises(result: DesignResult) -> None:
    out = {}
    for mat in ("PA", "PP"):
        case = dataclasses.replace(
            result.case, net=with_material(result.case.net, mat), net_modified=None
        )
        r = run(case)
        model = build_model(r.case.net, rigging_from_result(r), resolution=2)
        twine_w = float(np.sum(model.tri_w * 2.0 * model.tri_area * model.tri_a))
        sim = simulate(r, 3.0, resolution=2, coarse_resolution=None, model=model)
        z = float(sim.nodes[model.codend_rings[0], 2].mean())
        out[mat] = (r.geometry.std.weight_water_kg, twine_w, z, sim.converged)
    assert out["PA"][0] > 0 > out["PP"][0]  # motor: peso de la red en el agua
    assert out["PA"][1] > 0 > out["PP"][1]  # simulador: peso sumergido del paño
    assert out["PP"][3] and out["PA"][3]
    assert out["PP"][2] > out["PA"][2]  # el copo de PP queda más alto


def test_rigging_axial_stiffness(result: DesignResult) -> None:
    rig = rigging_from_result(result)
    # Relingas combinadas: supuesto 10⁶ N; bridas 4·10⁶ N sin diámetro conocido.
    assert rig.rope_ea("headrope") == rig.rope_ea("footrope") == 1.0e6
    assert rig.wire_ea() == DEFAULT_BRIDLE_EA_N
    assert dataclasses.replace(rig, bridle_diameter_mm=12.0).wire_ea() == pytest.approx(
        wire_rope_ea_n(12.0, rig.warp_core)
    )
    # Cable de remolque: el elegido por el motor (13 mm IWRC del catálogo de componentes).
    st = result.warps.stretch
    assert st is not None and rig.warp_core == st.core == "IWRC"
    assert rig.warp_ea() == pytest.approx(40_400 * 13**2)
    # Módulo efectivo sobre el área nominal: la mitad de los 100 GPa de antes.
    old = 1.0e11 * math.pi * (rig.warp_diameter_mm / 1000) ** 2 / 4
    assert 0.4 < rig.warp_ea() / old < 0.6
    # Una relinga de PP toma la relación del material.
    pp = dataclasses.replace(result.case, headrope_rope="pp_14_retorcido_3_cordones")
    assert rigging_from_result(run(pp)).rope_ea("headrope") == pytest.approx(1060 * 14**2)


def test_warp_stiffness_reaches_the_coupled_model(result: DesignResult) -> None:
    rig = rigging_from_result(result)
    soft = build_model(result.case.net, rig, resolution=2, coupled_doors=True)
    stiff = build_model(
        result.case.net,
        dataclasses.replace(rig, warp_ea_n=2 * rig.warp_ea()),
        resolution=2,
        coupled_doors=True,
    )
    warp = np.array([k == "warp" for k in soft.bar_kind])
    assert np.allclose(soft.bar_ea[warp], rig.warp_ea())
    assert np.allclose(stiff.bar_ea[warp], 2 * rig.warp_ea())
    assert np.array_equal(soft.bar_ea[~warp], stiff.bar_ea[~warp])
    # Explícito sigue mandando (compatibilidad con build_model(..., wire_ea_n=…)).
    forced = build_model(result.case.net, rig, resolution=2, wire_ea_n=1.0e6)
    bridles = np.array([k in ("upper_bridle", "lower_bridle", "sweep") for k in forced.bar_kind])
    assert np.allclose(forced.bar_ea[bridles], 1.0e6)


# ------------------------------------------------------------------------------------------
# Motor: estiramiento del cable
# ------------------------------------------------------------------------------------------


def test_warp_stretch_is_sane(result: DesignResult) -> None:
    st = result.warps.stretch
    assert st is not None
    warp_m = result.warps.warp_m
    assert 0.001 < st.stretch_m / warp_m < 0.02  # 0,1–2 % del largo filado
    assert st.strain == pytest.approx(st.stretch_m / warp_m)
    assert st.tension_kgf == pytest.approx(
        warp_tension_kgf(result.warps.loads.working_load_kgf, st.attack_angle_deg)
    )
    assert st.stretch_m == pytest.approx(
        warp_elastic_stretch_m(st.tension_kgf, warp_m, st.ea_n), rel=1e-12
    )
    # ΔL ∝ 1/EA: con el doble de rigidez, la mitad.
    assert warp_elastic_stretch_m(st.tension_kgf, warp_m, 2 * st.ea_n) == pytest.approx(
        st.stretch_m / 2
    )
    assert st.safety_factor == pytest.approx(
        result.warps.selection.breaking_load_t * 1000 / result.warps.loads.working_load_kgf
    )
    s = result.summary()
    assert s["warp_stretch_m"] == pytest.approx(st.stretch_m)
    assert s["warp_safety_factor"] == pytest.approx(st.safety_factor)
    assert float(s["warp_safety_factor"] or 0) >= result.case.warp_safety_factor  # cable 13 mm
    assert result.to_dict()["warps"]["stretch"]["stretch_m"] == pytest.approx(st.stretch_m)
    assert label("warp_stretch_m") == ("Estiramiento elástico del cable", "m")
    with use_lang("en"):
        assert label("warp_stretch_m")[0] == "Elastic stretch of the warp"


def test_excel_summary_keeps_its_keys() -> None:
    excel = run(standard_case(compat=Compat.EXCEL))
    s = excel.summary()
    assert "warp_stretch_m" not in s and "warp_safety_factor" not in s
    # El estiramiento se calcula igual (dato nuevo, fuera del libro); el 12 mm del libro no
    # llega al coeficiente 4 (errata warp_undersized).
    assert excel.warps.stretch is not None and excel.warps.stretch.safety_factor < 4.0
