"""Fase 20.5: calibración de la separación de portones (cable y portón polivalente).

Sólo en modo corregido: el CL efectivo del portón polivalente sin polar publicada (aplicado) y el
factor de cable ``(Ls / Ls_tabla)^Δn`` de la DPA de Fridman (ajustado y **no aplicado**: Δn no es
significativo, ``DP_WARP_EXPONENT_CORRECTION = 0``). El libro (modo ``EXCEL``), los valores
dorados, el caso A-3 y todo caso con el cable de la tabla no cambian.
"""

from __future__ import annotations

import dataclasses
import warnings
from functools import cache

import numpy as np
import pytest

from tests.test_case_fao_a3 import fao_a3_case
from trawlkit import fieldcheck as F  # noqa: N812
from trawlkit import rigging
from trawlkit.catalog import catalog_case
from trawlkit.compat import ERRATA_BY_KEY, Compat
from trawlkit.io import load_doors, load_net
from trawlkit.io.schema import ProvenanceKind
from trawlkit.model import DesignCase, DesignResult, door_cl_factor, dp_warp_factor, run

#: Umbrales declarados de la mejora frente a lo medido (DP de los lances medidos de las redes de
#: merluza): el desvío medio absoluto tiene que bajar al menos 5 puntos y la fracción dentro de
#: ±20 % subir al menos 25 puntos; en las series con polar publicada (SPF), el desvío medio
#: absoluto no puede empeorar más de 0,5 puntos.
MAD_DROP_MIN = 0.05
WITHIN_RISE_MIN = 0.25
SPF_MAD_WORSEN_MAX = 0.005
#: Validación cruzada: con el Δn ajustado sin ella, la dispersión de la serie dejada afuera (en
#: log, alrededor de su nivel) no puede crecer más de 0,01 (≈ 1 % de la DP).
CV_SCATTER_TOLERANCE = 0.01
#: IC 041/25 es una sola media de campaña (101,2 m, lances de 64–158 m sin cable publicado): sin la
#: corrección de cable el motor calibrado queda en +20 %; umbral declarado ±22 %.
IC041_TOLERANCE = 0.22

HAKE_NETS = (
    "inidep_iat101_va355_disenada",
    "inidep_iat151_va355_construida",
    "inidep_iat101_engel355",
)
SPF_SERIES = ("ic012", "ic016", "ic029")
POLYVALENT_SERIES = ("iat151", "it66", "ic041")


def _same(a: DesignResult, b: DesignResult) -> None:
    assert a.doors.spread_m == b.doors.spread_m
    assert a.doors.polar == b.doors.polar
    np.testing.assert_array_equal(a.spread.fridman.dpa_std_m, b.spread.fridman.dpa_std_m)
    np.testing.assert_array_equal(a.spread.fridman.dpa_mod_m, b.spread.fridman.dpa_mod_m)
    assert a.spread.horizontal_opening_m == b.spread.horizontal_opening_m
    np.testing.assert_array_equal(a.warps.total.std, b.warps.total.std)


def _uncalibrated(case: DesignCase) -> DesignCase:
    return dataclasses.replace(case, calibrated=False)


# --- Lo que no cambia ---------------------------------------------------------------------------


@pytest.mark.parametrize("compat", [Compat.EXCEL, Compat.CORRECTED])
def test_caso_a3_sin_cambios(compat: Compat) -> None:
    case = fao_a3_case(150, compat)
    r = run(case)
    assert dp_warp_factor(case, r.rigging) == 1.0
    assert door_cl_factor(case) == 1.0
    _same(r, run(_uncalibrated(case)))
    assert not any(n.startswith(("fridman_dp_warp", "door_cl_calibrated")) for n in r.notes)


def test_modo_excel_sin_calibracion_con_otro_cable() -> None:
    case = dataclasses.replace(fao_a3_case(150, Compat.EXCEL), measured_warp_m=400.0)
    r = run(case)
    assert dp_warp_factor(case, r.rigging) == 1.0
    _same(r, run(_uncalibrated(case)))
    assert rigging.dp_warp_factor(400.0, 40.0, Compat.EXCEL) == 1.0


@pytest.mark.parametrize("depth", [20.0, 40.0, 62.7, 100.0, 250.0, 400.0])
def test_factor_uno_con_el_cable_de_la_tabla(depth: float) -> None:
    warp = rigging.table_warp_m(depth)
    assert warp == pytest.approx(depth * rigging.warp_depth_ratio(depth))
    assert rigging.dp_warp_factor(warp, depth) == 1.0
    # Con el exponente vigente (0, no aplicado) vale 1 con cualquier cable; la función queda
    # lista para un exponente futuro.
    assert rigging.dp_warp_factor(2.0 * warp, depth) == 1.0
    assert rigging.dp_warp_factor(0.5 * warp, depth) == 1.0
    assert rigging.dp_warp_factor(2.0 * warp, depth, exponent=0.105) == pytest.approx(2.0**0.105)


def test_caso_de_diseno_con_portón_publicado_sin_cambios() -> None:
    """La VA diseñada (SPF08 con CL y CD publicados): sin cable medido o con el de la tabla."""
    case = catalog_case("inidep_iat101_va355_disenada").case
    r = run(case)
    _same(r, run(_uncalibrated(case)))
    at_table = dataclasses.replace(case, measured_warp_m=r.rigging.towing.warp_m)
    _same(run(at_table), r)


def test_correccion_de_cable_no_aplicada() -> None:
    """Δn = 0: con un cable medido distinto del de la tabla, la DP no cambia y no hay nota."""
    assert rigging.DP_WARP_EXPONENT_CORRECTION == 0.0
    case = catalog_case("inidep_iat101_va355_disenada", measured_warp_m=500.0).case
    r = run(case)
    assert r.rigging.towing.warp_m != rigging.table_warp_m(case.working_depth_m)
    assert dp_warp_factor(case, r.rigging) == 1.0
    _same(r, run(_uncalibrated(case)))
    assert not any(n.startswith("fridman_dp_warp_saturation") for n in r.notes)


def test_factor_de_cable_en_fridman_spread() -> None:
    """La maquinaria queda lista: ``warp_factor`` multiplica las dos DPA de Fridman."""
    args = (1.8, 0.6, 1.1, np.array([1.0, 1.5]), np.array([900.0, 1500.0]))
    kw = {"warp_horizontal_m": 300.0, "net_length_working_m": 25.0, "bridle_m": 30.0}
    base = rigging.fridman_spread(*args, np.array([950.0, 1550.0]), **kw)
    scaled = rigging.fridman_spread(*args, np.array([950.0, 1550.0]), **kw, warp_factor=1.1)
    np.testing.assert_allclose(scaled.dpa_std_m, 1.1 * np.asarray(base.dpa_std_m))
    np.testing.assert_allclose(scaled.dpa_mod_m, 1.1 * np.asarray(base.dpa_mod_m))


def test_camaroneras_sin_cambios() -> None:
    """El método de las camaroneras (tangones, Fase 19.7b) no usa el cable: factor 1."""
    for net_id in ("inidep_ito043_tangonera_inidep", "inidep_iat027_tangonera_modificada"):
        cc = catalog_case(net_id)
        case = dataclasses.replace(cc.case, measured_warp_m=3.0 * cc.case.working_depth_m)
        assert case.uses_shrimp_opening
        r = run(case)
        assert dp_warp_factor(case, r.rigging) == 1.0
        _same(r, run(_uncalibrated(case)))


def test_spf08_con_polar_publicada_sin_cambio_de_cl() -> None:
    door = F.validation_door("inidep_iat151_va355_construida", "spf08_1000")
    assert rigging.polar_published(door)
    assert rigging.cl_effective_factor(door) == 1.0
    p = F.engine_point(
        "inidep_iat151_va355_construida", depth_m=130.0, speed_kn=4.0, door="spf08_1000"
    )
    q = F.engine_point(
        "inidep_iat151_va355_construida",
        depth_m=130.0,
        speed_kn=4.0,
        door="spf08_1000",
        calibrated=False,
    )
    assert p.door_cl_factor == 1.0 and p.dp_warp_factor == 1.0
    assert p.door_spread_m == q.door_spread_m


# --- El portón polivalente ----------------------------------------------------------------------


def test_portón_polivalente_calibrado_sólo_en_modo_corregido() -> None:
    poly = F.validation_door("inidep_iat151_va355_construida", "polivalente_1200")
    assert poly.type == rigging.CALIBRATED_DOOR_TYPE and not rigging.polar_published(poly)
    assert rigging.canonical_type(poly.type) == "oval"
    f = rigging.POLYVALENT_CL_EFFECTIVE_FACTOR
    assert rigging.cl_effective_factor(poly) == f
    assert rigging.cl_effective_factor(poly, Compat.EXCEL) == 1.0
    case = catalog_case("inidep_iat151_va355_construida").case
    r, base = run(case), run(_uncalibrated(case))
    assert r.doors.polar.cl == pytest.approx(f * base.doors.polar.cl)
    assert r.doors.polar.cd == base.doors.polar.cd
    assert r.doors.spread_m < base.doors.spread_m
    assert any(n.startswith("door_cl_calibrated") for n in r.notes)
    # El portón oval del libro (polar de su ficha) no se calibra.
    oval = next(d for d in load_doors().doors if d.type == "oval_polyvalent")
    assert rigging.cl_effective_factor(oval) == 1.0


def test_procedencia_calibrada() -> None:
    assert ProvenanceKind("calibrated") is ProvenanceKind.CALIBRATED
    for prov in (rigging.DP_WARP_EXPONENT_PROVENANCE, rigging.POLYVALENT_CL_PROVENANCE):
        assert prov.kind is ProvenanceKind.CALIBRATED and prov.document and prov.note
    assert "fridman_dp_warp_saturation" in ERRATA_BY_KEY


# --- Ajustes y validación cruzada ---------------------------------------------------------------


@cache
def _warp_fit() -> F.WarpExponentFit:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return F.warp_exponent_fit()


def test_ajuste_de_delta_n_no_significativo() -> None:
    """El ajuste da Δn ≈ 0,105 ± 0,091 y su intervalo del 95 % incluye el 0: no se aplica."""
    fit = _warp_fit()
    assert fit.n == 103 and set(fit.offsets) == {"iat151", "ic012", "ic016"}
    assert fit.delta_n == pytest.approx(0.105, abs=0.005)
    assert fit.se == pytest.approx(0.091, abs=0.005)
    lo, hi = fit.ci95
    assert lo < 0.0 < hi  # la razón de no aplicarlo
    assert lo < rigging.DP_WARP_EXPONENT_CORRECTION < hi
    assert hi - lo == pytest.approx(2 * 1.984 * fit.se, rel=1e-3)
    assert fit.slopes["iat151"] < 0.0 < fit.slopes["ic012"]  # las series no coinciden


def test_validación_cruzada() -> None:
    fit = _warp_fit()
    assert [f.held_out for f in fit.folds] == ["iat151", "ic012", "ic016"]
    lo, hi = fit.ci95
    for fold in fit.folds:
        assert lo <= fold.delta_n <= hi, fold
        assert fold.scatter_after <= fold.scatter_before + CV_SCATTER_TOLERANCE, fold


def test_ajuste_del_cl_polivalente() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = F.polyvalent_cl_fit()
    assert fit.target_m == pytest.approx(92.2, abs=0.05)  # IAT 151/2018, tabla 1
    assert abs(fit.factor - rigging.POLYVALENT_CL_EFFECTIVE_FACTOR) <= 0.005
    # Verificación con la Engel (mismos polivalentes de 5,58 m²): el Inf. Téc. 66 dentro de
    # ±20 %; la media de campaña de IC 041/25 (un solo valor, a la profundidad media y con el
    # cable de la tabla) queda en +20 %, dentro de ±22 % (umbral declarado para ese punto).
    (m66, e66), (m41, e41) = fit.checks["it66"], fit.checks["ic041"]
    assert abs(e66 / m66 - 1.0) <= F.TOLERANCES["door_spread_m"]
    assert abs(e41 / m41 - 1.0) <= IC041_TOLERANCE


# --- Las series medidas mejoran ------------------------------------------------------------------


@cache
def _devs() -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Por serie medida: desvíos de la DP sin calibrar y calibrada."""
    out: dict[str, tuple[list[float], list[float]]] = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for net_id in HAKE_NETS:
            spec = load_net(net_id)
            for ref in F.references(spec):
                m = ref.get("door_spread_m")
                if m is None:
                    continue
                before = F.reference_point(spec, ref, calibrated=False).door_spread_m
                after = F.reference_point(spec, ref).door_spread_m
                b, a = out.setdefault(ref["series"], ([], []))
                b.append(before / float(m) - 1.0)
                a.append(after / float(m) - 1.0)
    return {k: (np.asarray(b), np.asarray(a)) for k, (b, a) in out.items()}


def _mad(d: np.ndarray) -> float:
    return float(np.mean(np.abs(d)))


def _within(d: np.ndarray) -> float:
    return float(np.mean(np.abs(d) <= F.TOLERANCES["door_spread_m"]))


def test_las_series_medidas_mejoran() -> None:
    devs = _devs()
    assert set(devs) == set(SPF_SERIES) | set(POLYVALENT_SERIES)
    before = np.concatenate([b for b, _ in devs.values()])
    after = np.concatenate([a for _, a in devs.values()])
    assert len(before) == 115
    assert _mad(after) <= _mad(before) - MAD_DROP_MIN
    assert _within(after) >= _within(before) + WITHIN_RISE_MIN
    for s in POLYVALENT_SERIES:
        b, a = devs[s]
        assert _mad(a) < _mad(b), s
    for s in ("iat151", "it66"):
        b, a = devs[s]
        assert _within(a) > _within(b) and _within(a) == 1.0, s
    assert np.all(np.abs(devs["ic041"][1]) <= IC041_TOLERANCE)
    for s in SPF_SERIES:
        b, a = devs[s]
        assert _mad(a) <= _mad(b) + SPF_MAD_WORSEN_MAX, s
        assert _within(a) >= _within(b), s
