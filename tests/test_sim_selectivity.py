"""Fase 11.3: orientación de la malla, estado de cada malla y selectividad del copo."""

from __future__ import annotations

import dataclasses
import math

import numpy as np
import pytest

from trawlkit.drawing.layout import panel_size_m
from trawlkit.io.loader import load_net
from trawlkit.io.schema import MeshOrientation
from trawlkit.model import run
from trawlkit.net import working_surface_m2
from trawlkit.netting import opening_product, orientation_coefficients
from trawlkit.selectivity import (
    codend_variant,
    escape_zone,
    max_passing_length,
    retention_curve,
    selectivity,
    species,
    species_catalogue,
)
from trawlkit.sim import Scenario, simulate
from trawlkit.sim.core import rigging_from_result
from trawlkit.sim.mesh import DIAMOND_REST_ANGLE_DEG, build_model, rest_angle_rad
from trawlkit.sim.meshstate import mesh_patch, mesh_state
from trawlkit.sim.solver import ForceField, Params
from trawlkit.sim.validation import standard_case

RES = 3


# --- orientación ----------------------------------------------------------------------------


def test_orientation_coefficients() -> None:
    assert orientation_coefficients("diamond", 0.38) == pytest.approx(
        (0.38, math.sqrt(1 - 0.38**2))
    )
    assert orientation_coefficients("t90", 0.8) == pytest.approx((0.8, 0.6))
    assert orientation_coefficients("square", 0.38) == (0.5, 0.5)
    assert opening_product("square", 0.38) == 0.25


def test_default_orientation_is_diamond() -> None:
    net = load_net("fao_a3_standard")
    assert all(p.mesh_orientation is MeshOrientation.DIAMOND for p in net.panels)


def test_square_working_surface_is_leg_squared() -> None:
    # 10 × 10 cuadrados de 20 mm de lado (malla de 40 mm) = 0,04 m².
    st = working_surface_m2(0.38, 40.0, 10, 10, 10, opening=0.25)
    assert st == pytest.approx(0.25 * 0.04**2 * 100)


def test_variant_keeps_hung_dimensions() -> None:
    net = load_net("fao_a3_standard")
    base = {p.id: panel_size_m(p, "true_scale") for p in net.panels}
    for o in ("t90", "square"):
        var = codend_variant(net, o)
        for p in var.panels:
            w0, _, h0 = base[p.id]
            w1, _, h1 = panel_size_m(p, "true_scale")
            if p.section.value == "codend":
                assert p.mesh_orientation.value == o
                assert w1 == pytest.approx(w0, rel=0.05)
                assert h1 == pytest.approx(h0, rel=0.02)
            else:
                assert (w1, h1) == (w0, h0)


def test_rest_angles() -> None:
    beta = math.radians(DIAMOND_REST_ANGLE_DEG)
    assert rest_angle_rad("diamond") == pytest.approx(beta)
    assert rest_angle_rad("t90") == pytest.approx(math.pi - beta)
    assert rest_angle_rad("square") == pytest.approx(math.pi / 2)


@pytest.mark.parametrize(
    ("orientation", "expected"),
    [
        ("diamond", 2 * math.degrees(math.asin(0.23))),
        ("t90", 2 * math.degrees(math.asin(0.8))),
        ("square", 90.0),
    ],
)
def test_flat_codend_opening(orientation: str, expected: float) -> None:
    """En el plano relingado, la malla del copo tiene la apertura de su U1 (o 90° la cuadrada)."""
    case = standard_case()
    net = case.net if orientation == "diamond" else codend_variant(case.net, orientation)
    r = run(dataclasses.replace(case, net=net))
    m = build_model(net, rigging_from_result(r), resolution=RES)
    x = m.x0.copy()
    x[:, 2] = 0.0
    st = mesh_state(m, x)
    z = st.zone(("codend",))
    assert float(np.median(st.opening_deg[z])) == pytest.approx(expected, abs=0.5)
    assert float(np.median(st.leg_i_mm[z])) == pytest.approx(20.0, rel=1e-3)


def test_bending_force_is_energy_gradient() -> None:
    case = standard_case()
    net = codend_variant(case.net, "t90")
    m = build_model(net, rigging_from_result(run(dataclasses.replace(case, net=net))), resolution=2)
    ff = ForceField(m, Params(speed_ms=1.5, mesh_bending=1.6e8))
    rng = np.random.default_rng(1)
    x = m.x0 + rng.normal(scale=0.02, size=m.x0.shape)

    def energy(xx: np.ndarray) -> float:
        st = mesh_state(m, xx)
        beta = np.radians(st.opening_deg)
        return float(0.5 * np.sum(ff.bend_k * (beta - m.tri_rest_angle) ** 2))

    vec = np.einsum("sk,skc->sc", ff.g, x[ff.nodes])
    s = np.sqrt(np.einsum("ij,ij->i", vec, vec))
    f = ff._bending(vec, s).reshape(-1, 3)
    k = int(m.tri[0, 0])
    h = 1e-7
    for c in range(3):
        xp = x.copy()
        xm = x.copy()
        xp[k, c] += h
        xm[k, c] -= h
        grad = (energy(xp) - energy(xm)) / (2 * h)
        assert f[k, c] == pytest.approx(-grad, rel=1e-3, abs=1e-9)


# --- prueba de paso -------------------------------------------------------------------------


def test_catalogue_species() -> None:
    ids = {s.id for s in species_catalogue()}
    assert {
        "hake_hubbsi",
        "hake_european",
        "cod",
        "haddock",
        "nephrops",
        "pleoticus",
        "plaice",
        "sole",
    } <= ids
    for s in species_catalogue():
        assert 0 < s.width <= s.height and 0 < s.compression <= 1 and s.length_min < s.length_max


def test_round_fish_through_square_mesh() -> None:
    sp = dataclasses.replace(species("cod"), height=0.1, width=0.1, compression=1.0)
    # Malla cuadrada con 20 mm de luz: pasa una sección circular de 20 mm (L = 20 cm).
    fit = max_passing_length(np.array([90.0]), np.array([20.0]), np.array([20.0]), sp)
    assert fit[0] == pytest.approx(20.0, rel=1e-3)


def test_passing_length_grows_with_opening_and_closed_mesh_retains() -> None:
    sp = species("hake_hubbsi")
    beta = np.array([1.0, 20.0, 40.0, 60.0, 90.0])
    leg = 50.0
    clear = leg * np.sin(np.radians(beta)) - 2.0
    fit = max_passing_length(beta, clear, clear, sp)
    assert fit[0] == 0.0
    assert np.all(np.diff(fit) > 0)


def test_flat_fish_passes_more_than_round() -> None:
    clear = np.array([30.0])
    beta = np.array([60.0])
    plaice = max_passing_length(beta, clear, clear, species("plaice"))[0]
    cod = max_passing_length(beta, clear, clear, species("cod"))[0]
    assert plaice > 0 and cod > 0
    # Por cm de largo, la platija es más alta pero mucho más delgada: pasa de canto.
    assert plaice * species("plaice").width < cod * species("cod").height


# --- simulación y curvas ---------------------------------------------------------------------


@pytest.fixture(scope="module")
def sims() -> dict[str, object]:
    case = standard_case()
    out: dict[str, object] = {}
    for key, (orient, mesh, kg) in {
        "d120": ("diamond", 120.0, 300.0),
        "d120_heavy": ("diamond", 120.0, 1000.0),
        "d80": ("diamond", 80.0, 300.0),
        "t120": ("t90", 120.0, 300.0),
    }.items():
        net = codend_variant(case.net, orient, mesh_mm=mesh)
        r = run(dataclasses.replace(case, net=net))
        out[key] = simulate(
            r,
            3.0,
            resolution=RES,
            coarse_resolution=None,
            scenario=Scenario(seabed="mixed", catch_kg=kg, mesh_bending=True),
        )
    return out


def test_mesh_state_in_result(sims: dict[str, object]) -> None:
    r = sims["d120"]
    st = r.mesh  # type: ignore[attr-defined]
    assert st is not None and st.opening_deg.size == r.triangles.shape[0]  # type: ignore[attr-defined]
    assert st.catch_fill.max() > 0
    d = r.to_dict()  # type: ignore[attr-defined]
    assert "mesh" in d and "mesh_summary" in d
    assert r.params["mesh_bending_pa"] > 0  # type: ignore[attr-defined]


def test_default_diamond_net_has_no_bending() -> None:
    r = simulate(run(standard_case()), 3.0, resolution=2, coarse_resolution=None, max_iter=200)
    assert r.params["mesh_bending_pa"] == 0.0
    assert r.mesh is not None


def test_retention_monotone_and_l50(sims: dict[str, object]) -> None:
    c = selectivity(sims["d120"], "cod")[0]
    assert np.all(np.diff(c.retention) >= -1e-9)
    assert 0 <= c.retention.min() and c.retention.max() <= 1
    assert c.l25 < c.l50 < c.l75
    # Orden de magnitud de un copo rómbico de 120 mm para bacalao (SF publicado ≈ 3–3,5).
    assert 2.0 < c.sf < 4.5


def test_l50_grows_with_mesh_and_t90(sims: dict[str, object]) -> None:
    l50 = {k: selectivity(v, "cod")[0].l50 for k, v in sims.items()}
    assert l50["d80"] < l50["d120"] < l50["t120"]


def test_catch_opens_meshes_ahead_of_bulge(sims: dict[str, object]) -> None:
    def front_opening(r: object) -> float:
        st = r.mesh  # type: ignore[attr-defined]
        z = escape_zone(st)
        return float(np.average(st.opening_deg[z], weights=st.meshes[z]))

    assert front_opening(sims["d120_heavy"]) > front_opening(sims["d120"])


def test_contact_lowers_escape(sims: dict[str, object]) -> None:
    st = sims["d120"].mesh  # type: ignore[attr-defined]
    full = retention_curve(st, "cod")
    half = retention_curve(st, "cod", contact=0.5)
    assert np.all(half.retention >= full.retention - 1e-12)


def test_mesh_patch(sims: dict[str, object]) -> None:
    st = sims["d120"].mesh  # type: ignore[attr-defined]
    k = int(np.flatnonzero(st.zone())[0])
    patch = mesh_patch(st, k, n=4)
    assert len(patch["knots"]) == 25
    assert len(patch["twines_i"]) == 20 and len(patch["twines_j"]) == 20
    assert patch["opening_deg"] == pytest.approx(float(st.opening_deg[k]))
    with pytest.raises(IndexError):
        mesh_patch(st, 10**6)
