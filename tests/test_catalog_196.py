"""Fase 19.6: redes de planos públicos del catálogo tailandés de la SEAFDEC (2016) y el portón de
la red de prueba de 16 pies de la NOAA (Fishery Facts 9)."""

from __future__ import annotations

import math

import pytest

from trawlkit.catalog import catalog_case
from trawlkit.components import DoorItem, get_component
from trawlkit.io import load_net
from trawlkit.model import run
from trawlkit.netcheck import check
from trawlkit.provenance import coverage

#: Red → (aparejo, estado, eslora del plano [m], potencia [hp], lima [m], burlón [m]).
NETS_196 = {
    "seafdec_31_outrigger_shrimp": ("outrigger", "published", 14.0, 75, 21.00, 22.40),
    "seafdec_33_outrigger_shrimp": ("outrigger", "published", 20.0, 90, 20.00, 23.00),
    "seafdec_35_outrigger_shrimp": ("outrigger", "draft", 15.0, 112, 26.90, 28.20),
    "seafdec_38_outrigger_shrimp": ("outrigger", "published", 13.5, 100, 21.00, 23.30),
    "seafdec_39_outrigger_shrimp": ("outrigger", "published", 16.0, 150, 28.70, 29.70),
    "seafdec_30_beam_shrimp": ("beam", "published", 11.0, 165, 19.60, 22.10),
    "seafdec_21_otter_fish": ("otter", "draft", 24.0, 250, 29.20, 33.60),
    "seafdec_22_otter_fish": ("otter", "draft", 20.0, 365, 46.10, 49.80),
}


@pytest.mark.parametrize("net_id", sorted(NETS_196))
def test_red_carga_valida_y_calcula(net_id: str) -> None:
    rig, status, loa, hp, head, foot = NETS_196[net_id]
    spec = load_net(net_id)
    assert (spec.rig, spec.family, spec.status) == (rig, "bottom", status)
    assert spec.vessel_hp == (hp, hp)
    assert spec.sources[0].key == "seafdec2016thai"
    assert spec.headrope is not None and spec.footrope is not None
    assert (spec.headrope.length_m, spec.footrope.length_m) == (head, foot)
    # El estado sigue al validador: publicada sin errores; borrador con al menos un empalme
    # que no cierra (uniones 1/1 o de copo con malleros muy distintos) y la razón en las notas.
    errs = [i for i in check(spec) if i.level == "error"]
    if status == "published":
        assert errs == []
    else:
        assert errs and all(i.code == "seam" for i in errs)
        assert any(n.startswith("BORRADOR") for n in spec.notes)
    cc = catalog_case(spec)
    assert cc.case.vessel.length_m == pytest.approx(loa)
    r = run(cc.case)
    assert r.dimensions.std.headrope_m == pytest.approx(head, rel=0.01)
    assert r.dimensions.std.footrope_m == pytest.approx(foot, rel=0.01)
    if rig in ("outrigger", "beam"):
        assert r.multirig is not None and r.multirig.n_nets == 2
        assert all(math.isfinite(float(x)) for x in r.multirig.demand.std)


@pytest.mark.parametrize("net_id", sorted(NETS_196))
def test_procedencia_completa_y_pocos_supuestos(net_id: str) -> None:
    spec = load_net(net_id)
    cov = coverage(spec)
    assert cov["fraction"] == 1.0, cov["missing"]
    by_kind = cov["by_kind"]
    # Lo leído domina; lo supuesto es poco (U1 sale de la bocana, el Rtex del denier).
    assert by_kind["transcribed"] > by_kind.get("derived", 0)
    assert by_kind.get("assumed", 0) <= 0.05 * cov["values"]
    for path, prov in spec.provenance.items():
        if prov.kind != "transcribed":
            assert prov.note, path


def test_cuerpo_comun_y_u1_de_la_bocana() -> None:
    spec = load_net("seafdec_33_outrigger_shrimp")
    by_id = {p.id: p for p in spec.panels}
    # El cuerpo y el copo se dibujan una vez: el vientre repite los paños del dorso.
    for up in ("U2", "U3", "U4", "UC"):
        lo = by_id["L" + up[1:]]
        assert (lo.mesh_mm, lo.meshes_top, lo.meshes_bottom, lo.meshes_depth) == (
            by_id[up].mesh_mm,
            by_id[up].meshes_top,
            by_id[up].meshes_bottom,
            by_id[up].meshes_depth,
        )
    # U1 del dorso: 2,00 m sobre (446 − 2 × 156) × 45 mm = 6,03 m.
    assert by_id["U1"].hanging_ratio == pytest.approx(2.00 / 6.03, abs=0.005)
    # Rtex del denier: PE 250d/9 → 250.
    assert by_id["UW"].rtex == pytest.approx(250.0)


def test_lecturas_que_no_cierran_quedan_como_avisos() -> None:
    # Plano 38: el ala se lee 1N2B, pero el ensanche pide 1N3B; se conserva y se avisa.
    issues = check(load_net("seafdec_38_outrigger_shrimp"))
    assert any(i.code == "cut" and "UW" in i.panels for i in issues)
    # Plano 31: los rótulos de las alas no suman el total; el ala se deriva del total.
    spec = load_net("seafdec_31_outrigger_shrimp")
    assert spec.headrope is not None and spec.headrope.wing_m == pytest.approx(9.50)
    prov = spec.provenance["headrope.wing_m"]
    assert prov.kind == "derived" and "10,00" in (prov.note or "")


def test_porton_de_la_red_de_prueba_noaa() -> None:
    door = get_component("door", "door_noaa_ff9_30x15in")
    assert isinstance(door, DoorItem)
    assert door.length_m == pytest.approx(30 * 0.0254, abs=1e-3)
    assert door.height_m == pytest.approx(15 * 0.0254, abs=1e-3)
    assert door.weight_air_kg is None  # el documento no da el peso
    assert door.provenance["coefficients"].kind == "assumed"
    assert door.to_door().area_m2 == pytest.approx(0.29, abs=0.01)
