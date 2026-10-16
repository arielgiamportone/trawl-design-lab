from functools import cache

import numpy as np
import pytest

from trawlkit import DesignCase, run
from trawlkit.io import load_doors, load_net, load_vessels
from trawlkit.optimize import (
    Evaluator,
    Limits,
    evaluate,
    grid_search,
    optimise,
    pareto_front,
    scale_count,
    scale_door,
    scale_net,
    summary_markdown,
)


@cache
def _case(bhp: int = 150) -> DesignCase:
    vessels = {v.id: v for v in load_vessels().vessels}
    design = vessels[f"fao_a3_{bhp}hp"]
    return DesignCase(
        net=load_net("fao_a3_standard"),
        vessel=design,
        class_vessels=tuple(v for v in vessels.values() if v.id != design.id),
        door=load_doors().doors[0],
    )


def _dump(spec):  # type: ignore[no-untyped-def]
    d = spec.model_dump()
    d.pop("id")
    return d


def test_scale_net_identity_except_id() -> None:
    spec = load_net("fao_a3_standard")
    scaled = scale_net(spec, 1.0)
    assert scaled.id == "fao_a3_standard_s1.00"
    assert _dump(scaled) == _dump(spec)


def test_scale_net_counts_and_shared_edges() -> None:
    spec = load_net("fao_a3_standard")
    scaled = scale_net(spec, 1.23)
    by_id = {p.id: p for p in scaled.panels}
    orig = {p.id: p for p in spec.panels}
    for pid, p in by_id.items():
        o = orig[pid]
        assert p.meshes_top == scale_count(o.meshes_top, 1.23)
        assert p.meshes_depth == scale_count(o.meshes_depth, 1.23) >= 1
        assert p.mesh_mm == o.mesh_mm and p.twine_diameter_mm == o.twine_diameter_mm
        extra = p.model_extra or {}
        assert {extra["meshes_a"], extra["meshes_b"]} == {p.meshes_top, p.meshes_bottom}
    # Bordes que se unen en la red original siguen iguales: E abajo = G arriba, H abajo = I.
    for (a, ea), (b, eb) in (
        (("E", "meshes_bottom"), ("G", "meshes_top")),
        (("C", "meshes_top"), ("A", "meshes_bottom")),
        (("H", "meshes_bottom"), ("I", "meshes_top")),
        (("I", "meshes_bottom"), ("J", "meshes_top")),
    ):
        assert getattr(orig[a], ea) == getattr(orig[b], eb)
        assert getattr(by_id[a], ea) == getattr(by_id[b], eb)
    assert scaled.floats is not None and scaled.floats.count == 15
    assert scaled.headrope is not None and spec.headrope is not None
    assert scaled.headrope.length_m == pytest.approx(1.23 * spec.headrope.length_m)
    with pytest.raises(ValueError):
        scale_net(spec, 0.0)


def test_net_drag_and_headrope_grow_with_scale() -> None:
    ev = Evaluator(_case())
    rn, head = [], []
    for s in (0.7, 1.0, 1.3):
        r = ev.curves(s).result
        assert r.case.net.id.endswith(f"_s{s:.2f}")
        rn.append(float(r.drag.rn.std[r.case.speed_index(2.0)]))
        head.append(r.dimensions.std.headrope_m)
    assert rn[0] < rn[1] < rn[2]
    assert head[0] < head[1] < head[2]
    assert head[2] / head[1] == pytest.approx(1.3, rel=0.03)


def test_evaluate_matches_engine_at_book_speed() -> None:
    case = _case()
    r = run(case)
    e = evaluate(case, 1.0, 2.0)
    assert e.dpa_fridman_m == pytest.approx(float(r.spread.fridman.dpa_std_m[2]), rel=1e-9)
    assert e.demand_kgf == pytest.approx(float(r.warps.total.std[2]), rel=1e-9)
    assert e.available_kgf == pytest.approx(float(r.power.ft_kgf[2]), rel=1e-9)
    assert e.area_rate_m2_h == pytest.approx(e.ah_m * 2.0 * 0.5144 * 3600, rel=1e-3)
    assert e.energy_kgf_m_per_m2 == pytest.approx(e.demand_kgf / e.ah_m)
    assert e.door_required_m2 == pytest.approx(r.doors.required_area.per_door_m2, rel=1e-9)
    assert e.ah_m <= e.dpa_geometric_m


def test_feasibility_of_fao_a3_150hp_fixed_pitch() -> None:
    case = _case()
    ok = evaluate(case, 1.0, 2.1)
    assert ok.feasible, [c for c in ok.constraints if not c.ok]
    fast = evaluate(case, 1.0, 3.5)
    assert not fast.feasible and not fast.constraint("thrust").ok
    slow = evaluate(case, 1.0, 1.5)
    assert not slow.constraint("net_open").ok
    # Con paso variable + tobera el portón del libro queda chico (Port!F215 = 2,67 m²).
    pvt = evaluate(case, 1.0, 2.5, propeller="variable_pitch_nozzle")
    assert not pvt.constraint("door").ok and pvt.constraint("thrust").ok


def test_grid_mask_and_pareto() -> None:
    case = _case()
    g = grid_search(case, [0.8, 1.0, 1.2], [1.5, 2.1, 3.0, 3.5])
    mask = g.feasible
    assert mask.shape == (3, 4)
    assert mask[1, 1] and not mask[1, 3]
    assert not mask[:, 3].any()  # 3,5 kn: ninguna escala con 150 HP y paso fijo
    area = g.matrix("area_rate_m2_h")
    assert np.all(np.diff(area, axis=1) > 0)  # el área barrida/h crece con v
    front = pareto_front(g.flat())
    assert front and all(e.feasible for e in front)
    for a in front:
        for b in g.flat():
            if not b.feasible:
                continue
            dominates = (
                b.area_rate_m2_h >= a.area_rate_m2_h
                and b.energy_kgf_m_per_m2 <= a.energy_kgf_m_per_m2
                and (
                    b.area_rate_m2_h > a.area_rate_m2_h
                    or b.energy_kgf_m_per_m2 < a.energy_kgf_m_per_m2
                )
            )
            assert not dominates
    with pytest.raises(ValueError):
        pareto_front(g.flat(), ("nope",))


def test_evaluator_reuses_engine_runs() -> None:
    ev = Evaluator(_case(), s_step=0.005)
    ev.at(1.0, 2.0)
    ev.at(1.001, 3.0)  # misma escala tras redondear
    ev.at(1.0, 2.5)
    assert ev.runs == 1
    with pytest.raises(ValueError):
        ev.at(1.0, 9.0)


def test_limits_validation() -> None:
    with pytest.raises(ValueError):
        Limits(v_min_kn=3.0, v_max_kn=2.0)
    with pytest.raises(ValueError):
        Limits(margin=-0.1)


def test_scale_door() -> None:
    door = load_doors().doors[0]
    big = scale_door(door, 2.7)
    assert big.area_m2 == 2.7
    assert big.coefficients == door.coefficients
    assert big.length_m == pytest.approx(door.length_m * (2.7 / door.area_m2) ** 0.5)


def test_optimise_feasible_and_reproducible() -> None:
    case = _case()
    kw = {"objective": "area", "grid": (5, 6), "maxiter": 6, "popsize": 6, "seed": 3}
    a = optimise(case, **kw)  # type: ignore[arg-type]
    b = optimise(case, **kw)  # type: ignore[arg-type]
    assert a.feasible and a.best.feasible
    assert (a.best.s, a.best.v_kn) == (b.best.s, b.best.v_kn)
    assert a.grid_best is not None
    assert a.best.area_rate_m2_h >= a.grid_best.area_rate_m2_h
    assert a.refine is not None and a.refine["nfev"] > 0
    d = a.to_dict()
    assert d["objective"] == "area_rate" and d["best"]["feasible"]
    md = summary_markdown(a)
    assert "Mejor diseño" in md and "Frente de Pareto" in md


def test_optimise_without_refine_and_infeasible_case() -> None:
    case = _case(180)
    res = optimise(case, objective="energy", grid=(3, 3), refine=False)
    # El portón del libro (1,805 m²) queda chico para 180 HP según Port!F215 (1,99 m²).
    assert not res.feasible and res.refine is None
    assert not res.best.constraint("door").ok
    assert "Ningún diseño factible" in summary_markdown(res)
    sized = optimise(
        DesignCase(
            net=case.net,
            vessel=case.vessel,
            class_vessels=case.class_vessels,
            door=scale_door(case.door, 2.0),
        ),
        objective="volume",
        grid=(3, 4),
        refine=False,
    )
    assert sized.feasible
    with pytest.raises(ValueError):
        optimise(case, objective="speed")


@pytest.mark.slow
def test_optimise_default_settings_runtime() -> None:
    res = optimise(_case(), objective="area")
    assert res.feasible
    assert res.runtime_s < 15
    assert 0.6 <= res.best.s < 1.0  # la red del libro es grande para 150 HP con paso fijo
