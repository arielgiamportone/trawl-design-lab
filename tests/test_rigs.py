"""Fase 19.5: aparejos de tangones, gemelo y vara (motor, simulador, lista de materiales, API)."""

from __future__ import annotations

import dataclasses
import math

import numpy as np
import pytest
from fastapi.testclient import TestClient

from trawlkit.api.app import app
from trawlkit.catalog import catalog_case
from trawlkit.cost import bill_of_materials
from trawlkit.drawing import net_sheet_svg, rig_plan_svg
from trawlkit.i18n import use_lang
from trawlkit.io import load_net
from trawlkit.model import DesignCase, run
from trawlkit.netcheck import check
from trawlkit.rigging import multirig
from trawlkit.sim import simulate
from trawlkit.sim.validation import standard_case
from trawlkit.topology import equivalent_two_panel, has_sides

NEW_NETS = (
    "inidep_ito043_tangonera_inidep",
    "inidep_ito043_tangonera_empresa",
    "seafdec_03_beam_shrimp",
)


@pytest.fixture(scope="module")
def base() -> DesignCase:
    return standard_case()


def _run(base: DesignCase, **kw: object):  # type: ignore[no-untyped-def]
    return run(dataclasses.replace(base, **kw))


# --- constantes de las fuentes ------------------------------------------------------------------


def test_constantes_de_las_fuentes() -> None:
    assert multirig.BOOM_LENGTH_M == pytest.approx(7.3152)  # 24 pies (FL 470)
    assert multirig.BOOM_ANGLE_DEG == 20.0
    # 70–80 pulg²/pie = 0,148–0,169 m² por metro de relinga (Watson et al. 1984).
    lo, hi = multirig.watson_door_area_m2(1.0)
    assert lo == pytest.approx(0.148, abs=5e-4) and hi == pytest.approx(0.169, abs=5e-4)
    assert multirig.SLED_FRONTAL_M2 == pytest.approx(0.8128 * 0.2032)
    # Ancho de vara de Eigaard et al. (2016): 1471 kW (2000 hp) → ≈ 2 varas de 12–13 m.
    assert multirig.beam_width_total_m(1471, "DMF") == pytest.approx(26.8, abs=0.3)
    assert multirig.beam_class(221) == "small" and multirig.beam_class(222) == "large"


def test_vara_grande_reproduce_la_tabla_9_de_c056() -> None:
    """La vara de 12 m y Ø0,24 m con la ec. 1 da el arrastre por metro de la tabla 9."""
    data = multirig.BEAM_CLASSES["large"]
    d = multirig.beam_drag(
        np.array([data.speed_ms]),
        length_m=12.0,
        diameter_m=0.24,
        shoe_area_m2=data.shoe_area_m2,
        shoe_height_m=data.shoe_height_m,
        cls="large",
        ticklers=True,
        metier="DMF",
    )
    per_m_kn = float(d.beam_kgf[0]) * 9.81 / 12.0 / 1000.0
    assert per_m_kn == pytest.approx(data.beam_kn_m, rel=0.05)
    tick = float(d.ticklers_kgf[0]) * 9.81 / 12.0 / 1000.0
    assert tick == pytest.approx(data.ticklers_kn_m, rel=1e-9)


def test_vara_frente_a_depestele_2016() -> None:
    """C056/20 (clase chica, escalada a 4,4 m y 4,4 nudos) frente a Depestele et al. (2016).

    Tolerancias declaradas: cadenas (tickler + tren) ±10 %; total de los paños inferiores, las
    cadenas y los patines ±25 % (las redes de Depestele tienen hilo más fino).
    """
    chk = multirig.depestele_check("small")
    assert chk.ratio("chains") == pytest.approx(1.0, abs=0.10)
    assert chk.ratio("total") == pytest.approx(1.0, abs=0.25)
    assert chk.total_n == pytest.approx(11_160, rel=0.01)


# --- motor --------------------------------------------------------------------------------------


def test_portones_y_pareja_sin_cambios(base: DesignCase) -> None:
    r = run(base)
    assert r.multirig is None
    assert "multirig" not in r.to_dict()
    assert "n_nets" not in r.summary()
    assert base.n_nets == 1


def test_tangones(base: DesignCase) -> None:
    r = _run(base, rig="outrigger")
    mr = r.multirig
    assert mr is not None and mr.kind == "outrigger"
    assert (mr.n_nets, mr.n_doors, mr.n_warps) == (2, 4, 2)
    i = base.speed_index(3.5)
    door = float(r.doors.forces.drag_kgf[i])
    rw_one = float(r.warps.drag_kgf[i]) / 2.0
    bridle = float(mr.bridle_drag_kgf[i]) / 2.0  # type: ignore[index]
    expected = float(r.drag.rn.std[i]) + float(r.floats.drag_kgf[i]) + 2 * door + rw_one + bridle
    assert float(mr.per_net.std[i]) == pytest.approx(expected)
    assert float(mr.demand.std[i]) == pytest.approx(2 * expected)
    tip = 7.3152 * math.cos(math.radians(20.0))
    assert mr.layout is not None and mr.layout.tip_offset_m == pytest.approx(tip)
    assert mr.swept_width_m == pytest.approx(2 * tip + r.doors.spread_m)
    s = r.summary()
    assert s["n_nets"] == 2 and s["swept_width_m"] == pytest.approx(mr.swept_width_m)
    assert s["total_drag_3_5kn_kgf"] == pytest.approx(float(mr.demand.std[i]))
    # Cada cable remolca una red: carga de trabajo = una red con su aparejo.
    assert r.warps.loads.working_load_kgf == pytest.approx(float(mr.per_net.std[i]))
    assert r.warps.quantity_m == pytest.approx(2.5 * r.warps.warp_m)
    # Con la separación del libro (40 m) las redes de la A-3 se superponen con tangones de 24 pies;
    # con el método camaronero (Fase 19.7b) la tijera las cierra.
    book = _run(base, rig="outrigger", opening_method="book")
    assert any(n.startswith("multirig_overlap") for n in book.notes)
    assert r.doors.spread_m < book.doors.spread_m


def test_gemelo(base: DesignCase) -> None:
    r = _run(base, rig="twin")
    mr = r.multirig
    assert mr is not None and (mr.n_nets, mr.n_doors, mr.n_warps) == (2, 2, 2)
    assert mr.clump_weight_kg == pytest.approx(1.5 * float(base.door.weight_air_kg or 0))
    assert mr.swept_width_m == pytest.approx(2 * r.doors.spread_m)
    i = base.speed_index(3.5)
    clump = float(mr.clump_drag_kgf[i])  # type: ignore[index]
    assert clump > 0
    # Los dos cables remolcan todo el arte, como en el libro.
    assert r.warps.loads.working_load_kgf == pytest.approx(2 * float(mr.per_net.std[i]))
    # El muerto pesa en el rozamiento con el fondo.
    with_seabed = _run(base, rig="twin", seabed="sand")
    otter = _run(base, seabed="sand")
    assert with_seabed.multirig is not None
    assert with_seabed.multirig.friction_kgf > 2 * otter.performance.seabed_friction_kgf


def test_vara(base: DesignCase) -> None:
    r = _run(base, rig="beam")
    mr = r.multirig
    assert mr is not None and mr.beam is not None
    assert (mr.n_doors, mr.n_nets) == (0, 2)
    kw = base.vessel.bhp * 0.7457
    assert mr.net_spread_m == pytest.approx(multirig.beam_width_total_m(kw, base.beam_metier) / 2)
    assert r.doors.spread_m == pytest.approx(mr.net_spread_m)
    assert r.spread.horizontal_opening_m == pytest.approx(mr.net_spread_m)
    assert mr.vertical_opening_m == pytest.approx(0.60)  # patín de C056/20 (≤ 221 kW)
    assert float(np.max(r.doors.forces.drag_kgf)) == 0.0
    i = base.speed_index(3.0)
    beam = mr.beam
    parts = beam.beam_kgf[i] + beam.shoes_kgf[i] + beam.ground_gear_kgf[i] + beam.ticklers_kgf[i]
    assert float(beam.total_kgf[i]) == pytest.approx(float(parts))
    # La ec. 10 de C056/20 y la RN de diseño (Aberdeen) son de la misma forma (±15 %).
    assert float(beam.net_c056_kgf[i]) == pytest.approx(float(r.drag.rn.std[i]), rel=0.15)
    one = _run(base, rig="beam", beam_count=1, beam_length_m=6.0, beam_ticklers=True)
    assert one.multirig is not None and one.multirig.n_nets == 1
    assert one.multirig.swept_width_m == pytest.approx(6.0)
    assert float(one.multirig.beam.ticklers_kgf[i]) > 0  # type: ignore[union-attr]


@pytest.mark.parametrize(
    "kw",
    [
        {"rig": "trawl"},
        {"rig": "beam", "beam_count": 3},
        {"rig": "outrigger", "boom_length_m": -1.0},
        {"rig": "outrigger", "boom_angle_deg": 95.0},
    ],
)
def test_entradas_invalidas(base: DesignCase, kw: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        dataclasses.replace(base, **kw)


def test_lista_de_materiales(base: DesignCase) -> None:
    otter = {ln.key: ln.quantity for ln in bill_of_materials(run(base)).lines}
    out = {ln.key: ln.quantity for ln in bill_of_materials(_run(base, rig="outrigger")).lines}
    assert out["doors"] == 4 and out["floats"] == 2 * otter["floats"]
    assert out["headrope"] == pytest.approx(2 * otter["headrope"], abs=1e-3)
    assert out["outrigger_bridles"] == pytest.approx(4 * 70.0)
    twin = {ln.key: ln.quantity for ln in bill_of_materials(_run(base, rig="twin")).lines}
    assert twin["doors"] == 2 and twin["clump"] == 1
    beam = {ln.key: ln.quantity for ln in bill_of_materials(_run(base, rig="beam")).lines}
    assert "doors" not in beam and "floats" not in beam and "bridles" not in beam
    assert beam["beams"] == 2 and beam["beam_shoes"] == 4


# --- redes del catálogo ------------------------------------------------------------------------


@pytest.mark.parametrize("net_id", NEW_NETS)
def test_redes_nuevas_validan_y_calculan(net_id: str) -> None:
    spec = load_net(net_id)
    assert spec.rig in ("outrigger", "beam") and spec.family == "bottom"
    issues = check(spec)
    if net_id.startswith("inidep_"):
        # Fase 19.7c: los costados terminan en un cabo antes del copo y el copo se une por la
        # circunferencia (dorso + vientre = copo): la red cierra y está publicada.
        assert spec.status == "published"
        assert not [i for i in issues if i.level == "error"]
        assert any(i.code == "codend_join" and i.level == "warning" for i in issues)
    else:
        assert spec.status == "draft"  # los empalmes del copo no cierran: borrador
        assert any(i.code == "seam" for i in issues)
    cc = catalog_case(spec)
    r = run(cc.case)
    assert r.multirig is not None and r.multirig.n_nets == 2
    assert all(math.isfinite(float(x)) for x in r.multirig.demand.std)


def test_red_inidep_costados_por_largo() -> None:
    spec = load_net("inidep_ito043_tangonera_inidep")
    assert has_sides(spec)
    eq = equivalent_two_panel(spec)
    assert not has_sides(eq)
    assert any("largo estirado" in n for n in eq.notes)
    assert any(i.code == "side" and i.level == "warning" for i in check(spec))
    # Relingas del plano: 2 × (11,00 + 3,75) + 6,00 = 35,5 m; 2 × (10,00 + 3,75) + 5,00 = 32,5 m.
    r = run(catalog_case(spec).case)
    assert r.dimensions.std.headrope_m == pytest.approx(35.5)
    assert r.dimensions.std.footrope_m == pytest.approx(32.5)
    assert r.case.vessel.id == "ar_tangonero_1998"
    assert r.multirig is not None and r.multirig.bridle_m == 70.0
    assert any(n.startswith("cfp_res7_2018") for n in r.notes)
    # Resistencia de una red con su aparejo frente a la tensión del cable de DynamiT (3777 kgf).
    i = r.case.speed_index(3.5)
    assert float(r.multirig.per_net.std[i]) == pytest.approx(3777.2, rel=0.25)


# --- simulador ----------------------------------------------------------------------------------


@pytest.mark.parametrize("rig", ["twin", "beam"])
def test_simulacion_converge(base: DesignCase, rig: str) -> None:
    r = _run(base, rig=rig)
    sim = simulate(r, 3.0, resolution=3)
    assert sim.converged
    assert sim.rig["n_nets"] == 2 and len(sim.rig["offsets_m"]) == 2
    assert sim.rig["drag_kgf"] == pytest.approx(2 * sim.drag_kgf)
    if rig == "beam":
        assert r.multirig is not None
        assert sim.ah_m == pytest.approx(r.multirig.net_spread_m, rel=1e-6)
        tips = [*sim.wing_tips_upper]
        assert sim.nodes[tips, 2] == pytest.approx(r.multirig.vertical_opening_m)
    assert "rig" in sim.to_dict(geometry=False)


# --- dibujo, idioma y API ---------------------------------------------------------------------


def test_esquema_del_aparejo(base: DesignCase) -> None:
    r = _run(base, rig="outrigger")
    svg_text = rig_plan_svg(r)
    assert "Aparejo de tangones" in svg_text
    assert "Aparejo de tangones" in net_sheet_svg(r)
    assert "Aparejo de tangones" not in net_sheet_svg(run(base))
    with pytest.raises(ValueError):
        rig_plan_svg(run(base))
    with use_lang("en"):
        assert "Outrigger rig" in rig_plan_svg(r)
        notes = _run(base, rig="twin").notes
    assert any(n.startswith("multirig: twin rig") for n in notes)


client = TestClient(app)


def test_api_design_y_params() -> None:
    res = client.post("/design", json={"params": {"rig": "outrigger", "boom_length_m": 20.0}})
    assert res.status_code == 200, res.text
    s = res.json()["summary"]
    assert s["n_nets"] == 2 and s["rig"] == "outrigger"
    assert "multirig" in res.json()["result"]
    res = client.post("/design", json={"params": {"rig": "beam", "beam_ticklers": True}})
    assert res.status_code == 200, res.text
    names = {p["name"]: p for p in client.get("/params").json()}
    assert names["beam_ticklers"]["type"] == "bool | None"
    assert client.post("/design", json={"params": {"rig": "foo"}}).status_code in (400, 422)


def test_api_catalogo_y_simulacion() -> None:
    items = {n["id"]: n for n in client.get("/catalog/nets").json()}
    assert items["inidep_ito043_tangonera_inidep"]["rig"] == "outrigger"
    assert items["seafdec_03_beam_shrimp"]["rig"] == "beam"
    res = client.post(
        "/simulate",
        json={"speeds_kn": [3.0], "resolution": 2, "params": {"rig": "twin"}},
    )
    assert res.status_code == 200, res.text
    assert res.json()["results"][0]["rig"]["kind"] == "twin"
