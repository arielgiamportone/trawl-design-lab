import numpy as np
import pytest

from tests.golden_utils import SPEEDS_KN, golden
from trawlkit.performance import speed_window, total_demand_kgf


def test_window_against_excel_series_150hp_fixed_pitch() -> None:
    ft = golden("cables_de_remolque", "fridman_ft_fixed_150_kgf")
    demand = golden("cables_de_remolque", "total_drag_std_kgf")
    w = speed_window(SPEEDS_KN, ft, demand)
    assert w.feasible[0]
    assert w.max_speed_kn is not None
    assert 1.0 < w.max_speed_kn < 5.0
    # El margen es decreciente: FT cae con v y R crece con v².
    assert np.all(np.diff(w.margin_kgf) < 0)
    assert w.feasible_speeds_kn == [v for v, ok in zip(SPEEDS_KN, w.feasible, strict=True) if ok]


def test_all_feasible_and_none_feasible() -> None:
    v = [1.0, 2.0, 3.0]
    assert speed_window(v, [10, 10, 10], [1, 2, 3]).max_speed_kn == 3.0
    assert speed_window(v, [1, 1, 1], [5, 6, 7]).max_speed_kn is None


def test_crossing_is_linearly_interpolated() -> None:
    w = speed_window([1.0, 2.0], [10.0, 10.0], [5.0, 15.0])  # margen 5 → -5, cruce en 1.5
    assert w.max_speed_kn == pytest.approx(1.5)


def test_total_demand_sums_components() -> None:
    rn = golden("cables_de_remolque", "rn_std_kgf")
    rb = golden("cables_de_remolque", "float_drag_kgf")
    rw = golden("cables_de_remolque", "warp_drag_2_kgf")
    total = total_demand_kgf(rn, rb, rw)
    np.testing.assert_allclose(total, golden("cables_de_remolque", "total_drag_std_kgf"), rtol=1e-6)


def test_shape_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        speed_window([1, 2], [1, 2, 3], [1, 2])
