"""Fase 20.7: lastre, cable y velocidad máxima coherentes con buques de mucho tiro.

Caso de la app: red ``inidep_iat151_va355_construida`` con el BIPO Víctor Angelescu (2855 BHP),
modo corregido, por ``service.build_case``. Antes daba lastre mínimo 461 kg > máximo 454 kg, el
cable de 18 mm (18,46 t) «no cumple la rotura» de 28,46 t (el catálogo del libro termina en 18 mm)
y velocidad máxima 5 kn, el extremo de la grilla, como si fuera el cruce FT = R.
"""

from __future__ import annotations

from functools import cache

import numpy as np
import pytest

from trawlkit import rigging
from trawlkit.api import service
from trawlkit.model import DesignCase, DesignResult, run, warp_pools
from trawlkit.optimize.evaluate import Evaluator
from trawlkit.performance import speed_window
from trawlkit.sim.validation import standard_case

NET = "inidep_iat151_va355_construida"
VESSEL = "bipo_victor_angelescu"


@cache
def _case() -> DesignCase:
    return service.build_case(net=NET, vessel=VESSEL, compat="corrected")


@cache
def _result() -> DesignResult:
    return run(_case())


def test_ballast_min_not_above_max() -> None:
    r = _result()
    lim = r.ballast.limits
    assert lim.min_kg <= lim.max_kg
    # Envolvente de las dos redes entre 1 y 3 kn (antes 461 > 454 kg).
    window = np.concatenate([r.ballast.fridman.std[:5], r.ballast.fridman.mod[:5]])
    assert lim.min_kg == np.floor(window.min()) and lim.max_kg == np.ceil(window.max())
    assert any(n.startswith("ballast_limits:") for n in r.notes)


def test_ballast_envelope_equals_book_rule_for_the_a3() -> None:
    for hp in ("fao_a3_150hp", "fao_a3_180hp"):
        r = run(
            service.build_case(net="fao_a3_standard", net_modified="fao_a3_modified", vessel=hp)
        )
        f = r.ballast.fridman
        c = r.case
        book = rigging.ballast_limits(
            float(f.mod[c.speed_index(c.ballast_min_speed_kn)]),
            float(f.std[c.speed_index(c.ballast_max_speed_kn)]),
        )
        assert r.ballast.limits == book
        assert not any(n.startswith("ballast_limits:") for n in r.notes)


def test_ballast_limits_envelope() -> None:
    lim = rigging.ballast_limits_envelope(np.array([461.6, 454.7, 451.1]), np.array([450.8]))
    assert (lim.min_kg, lim.max_kg) == (450.0, 462.0)
    with pytest.raises(ValueError):
        rigging.ballast_limits_envelope(np.array([]))


def test_warp_meets_breaking_load_beyond_the_book_catalogue() -> None:
    r = _result()
    sel = r.warps.selection
    book = warp_pools(r.case)[0]
    assert (
        max(float(w["breaking_load_t"]) for w in book) * 1000 < r.warps.loads.min_breaking_load_kgf
    )
    assert sel.satisfies_breaking_load
    assert sel.breaking_load_t * 1000 >= r.warps.loads.min_breaking_load_kgf
    assert sel.id not in {str(w["id"]) for w in book}
    assert any(n.startswith("warp_catalogue:") for n in r.notes)
    assert not any(n.startswith("warp_undersized:") for n in r.notes)


def test_a3_still_picks_from_the_book_catalogue() -> None:
    r = run(standard_case())
    assert r.warps.selection.id == "steel_6x19_seale_13mm"
    assert not any(n.startswith(("warp_catalogue:", "warp_diameter:")) for n in r.notes)


def test_evaluator_picks_the_engine_warp() -> None:
    case = _case()
    r = _result()
    ev = Evaluator(case)
    need = r.warps.loads.min_breaking_load_kgf
    chosen, best = ev._warp(r.warps.diameter_mm, need)
    assert chosen == r.warps.selection.id
    assert best >= need


def test_max_speed_beyond_the_grid() -> None:
    r = _result()
    win = r.performance.design
    assert win.beyond_grid and win.max_speed_kn == r.case.speeds_kn[-1]
    assert win.to_dict()["beyond_grid"] is True
    assert win.max_speed_label() == "> 5 kn (fuera de la grilla)"
    assert any(n.startswith("max_speed:") and "> 5 kn (fuera de la grilla)" in n for n in r.notes)
    a3 = run(standard_case()).performance.design
    assert not a3.beyond_grid and a3.max_speed_label().endswith(" kn")


def test_speed_window_beyond_grid_flag() -> None:
    v = [1.0, 2.0, 3.0]
    assert speed_window(v, [10, 10, 10], [1, 2, 3]).beyond_grid
    assert not speed_window(v, [10, 10, 10], [1, 20, 30]).beyond_grid
    none = speed_window(v, [1, 1, 1], [5, 5, 5])
    assert not none.beyond_grid and none.max_speed_label() == "ninguna"
