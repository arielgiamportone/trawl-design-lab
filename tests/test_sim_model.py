"""Discretización y fuerzas del simulador de forma (`trawlkit.sim.mesh`, `trawlkit.sim.solver`)."""

from __future__ import annotations

import numpy as np
import pytest

from trawlkit.compat import Compat
from trawlkit.model import DesignResult, run
from trawlkit.net import analyse
from trawlkit.sim import build_model, rigging_from_result
from trawlkit.sim.mesh import NetModel, interpolate_shape
from trawlkit.sim.solver import ForceField, Params, nodal_stiffness
from trawlkit.sim.validation import (
    DYNAMIT,
    constant_plus_power,
    errors,
    speed_exponent,
    standard_case,
)


@pytest.fixture(scope="module")
def result() -> DesignResult:
    return run(standard_case(compat=Compat.CORRECTED))


@pytest.fixture(scope="module")
def model(result: DesignResult) -> NetModel:
    return build_model(result.case.net, rigging_from_result(result), resolution=6)


def test_solid_surface_identity(result: DesignResult, model: NetModel) -> None:
    """Σ d·L del paño discretizado = superficie sólida FAO corregida (38,75 m²).

    La única diferencia es la punta de ala (borde de 3 mallas de A y B reducido a un punto en la
    primera fila de la grilla): menos de 0,2 %.
    """
    ss = analyse(result.case.net, Compat.CORRECTED).solid_surface_m2
    assert ss == pytest.approx(38.75, abs=0.01)
    assert model.solid_surface_m2 == pytest.approx(ss, rel=2e-3)
    assert model.solid_surface_m2 < ss  # sólo se pierde la punta de ala


@pytest.mark.parametrize("resolution", [3, 6, 10])
def test_solid_surface_independent_of_resolution(result: DesignResult, resolution: int) -> None:
    m = build_model(result.case.net, rigging_from_result(result), resolution=resolution)
    ss = analyse(result.case.net, Compat.CORRECTED).solid_surface_m2
    assert m.solid_surface_m2 == pytest.approx(ss, rel=2e-3)


def test_topology(model: NetModel) -> None:
    n = model.n_nodes
    assert np.all(model.mirror[model.mirror] == np.arange(n))
    flip = np.array([1.0, -1.0, 1.0])
    assert np.allclose(model.x0[model.mirror] * flip, model.x0, atol=1e-9)
    assert np.all(model.tri_area > 0)
    # Lima y burlón van de punta a punta de ala, pasando por el centro.
    assert model.headrope[0] == model.wing_tips_upper[0]
    assert model.headrope[-1] == model.wing_tips_upper[1]
    assert model.footrope[0] == model.wing_tips_lower[0]
    assert model.footrope[-1] == model.wing_tips_lower[1]
    assert abs(model.x0[model.headrope_centre, 1]) < 1e-9
    assert abs(model.x0[model.footrope_centre, 1]) < 1e-9
    kinds = np.array(model.bar_kind)
    assert (kinds == "upper_bridle").sum() == 2
    assert (kinds == "lower_bridle").sum() == 2
    assert (kinds == "sweep").sum() == 2
    assert len(model.fixed) == 2


def test_rope_lengths_match_engine(result: DesignResult, model: NetModel) -> None:
    kinds = np.array(model.bar_kind)
    dims = result.dimensions.std
    assert model.bar_l0[kinds == "headrope"].sum() == pytest.approx(dims.headrope_m, rel=1e-9)
    assert model.bar_l0[kinds == "footrope"].sum() == pytest.approx(
        2 * dims.footrope.wing_corrected_m + dims.footrope.bosom_corrected_m, rel=1e-9
    )


def test_floats_and_ballast(result: DesignResult, model: NetModel) -> None:
    assert model.float_weights.sum() == pytest.approx(result.floats.count)
    assert set(model.float_nodes.tolist()) <= set(model.headrope.tolist())
    # Lastre (alas + bocana + cadenas de reglaje) sumergido, todo hacia abajo y en el burlón.
    bd = result.ballast.distribution_max
    steel = 1.0 - 1024.0 / 7850.0
    total = (bd.wings_kg + bd.bosom_kg + bd.adjust_kg) * steel * 9.80665
    assert -model.point_load[:, 2].sum() == pytest.approx(total, rel=1e-9)
    loaded = np.flatnonzero(model.point_load[:, 2])
    assert set(loaded.tolist()) <= set(model.footrope.tolist())


def test_drag_scales_with_speed_squared(model: NetModel) -> None:
    """A forma fija, las fuerzas de Morison escalan con v² (y el empuje no depende de v)."""
    f1 = ForceField(model, Params(speed_ms=1.0, mu=0.0)).evaluate(model.x0, full=True)[1]
    f2 = ForceField(model, Params(speed_ms=2.0, mu=0.0)).evaluate(model.x0, full=True)[1]
    assert f1 is not None and f2 is not None
    assert f2.hydro_x.sum() == pytest.approx(4.0 * f1.hydro_x.sum(), rel=1e-9)


def test_morison_limits(model: NetModel) -> None:
    """Hilo paralelo al agua: sólo C_T; perpendicular: sólo C_N (½ρ C d L v²)."""
    p = Params(speed_ms=1.5, cn=1.4, ct=0.08)
    ff = ForceField(model, p)
    e = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    v = p.speed_ms
    ue = v * e[:, 0]
    un = -ue[:, None] * e
    un[:, 0] += v
    un_mag = np.sqrt(np.maximum(v * v - ue * ue, 0.0))
    k = np.ones(2)
    f = k[:, None] * (p.cn * un_mag[:, None] * un + (p.ct * np.abs(ue) * ue)[:, None] * e)
    assert f[0] == pytest.approx([p.ct * v * v, 0.0, 0.0])
    assert f[1] == pytest.approx([p.cn * v * v, 0.0, 0.0])
    assert ff.k.sum() > 0


def test_stiffness_bound_positive(model: NetModel) -> None:
    k = nodal_stiffness(model)
    assert np.all(k > 0)
    assert k.shape == (model.n_nodes,)


def test_interpolate_shape_preserves_coarse_geometry(result: DesignResult) -> None:
    rig = rigging_from_result(result)
    coarse = build_model(result.case.net, rig, resolution=4)
    fine = build_model(result.case.net, rig, resolution=8)
    x = interpolate_shape(coarse, coarse.x0, fine)
    # La forma inicial interpolada del grueso se parece a la inicial del fino (mismo layout).
    net = np.unique(fine.tri)
    dev = np.linalg.norm(x[net, :2] - fine.x0[net, :2], axis=1)
    assert np.median(dev) < 0.01
    assert np.percentile(dev, 90) < 0.25
    assert dev.max() < 1.0  # bordes: escalón de U1 entre paneles (G→H) y bolsa cerrada


def test_validation_helpers() -> None:
    v = np.asarray(DYNAMIT["v_kn"])
    ra = np.asarray(DYNAMIT["RA_kg"])
    e = errors(ra * 1.1, ra, v)
    assert e.mean_abs_pct == pytest.approx(10.0)
    assert e.bias_pct_band == pytest.approx(10.0)
    assert speed_exponent(v, 3.0 * v**1.7) == pytest.approx(1.7)
    a, b, n = constant_plus_power(v, 200.0 + 100.0 * v**2)
    assert (a, b, n) == pytest.approx((200.0, 100.0, 2.0), rel=1e-6)
    # DynamiT: RA ≈ v^1,48 en log-log (docs/32).
    assert speed_exponent(v, ra) == pytest.approx(1.48, abs=0.01)
