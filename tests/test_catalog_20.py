"""Fase 20.2: redes de merluza del INIDEP (VA-35,5/45, Engel) y de Baldino frente a lo medido."""

from __future__ import annotations

import warnings
from functools import cache

import numpy as np
import pytest

from trawlkit import fieldcheck as F  # noqa: N812
from trawlkit.api import service
from trawlkit.catalog import catalog_case, source_door
from trawlkit.io import load_net
from trawlkit.model import run
from trawlkit.netcheck import check
from trawlkit.provenance import coverage

#: Red → (estado, fuente, lima [m], burlón [m], buque del caso).
NETS_20 = {
    "inidep_iat101_va355_disenada": (
        "published",
        "roth2017angelescu",
        35.5,
        45.0,
        "bipo_victor_angelescu",
    ),
    "inidep_iat151_va355_construida": (
        "published",
        "bartozzetti2018iat151",
        35.5,
        45.0,
        "bipo_victor_angelescu",
    ),
    "inidep_iat101_engel355": ("draft", "roth2017angelescu", 35.5, 41.5, "bip_holmberg"),
    "inidep_iat045_baldino_original": ("draft", "roth2019iat045", 46.4, 55.7, "ar_congelador_e1"),
    "inidep_iat045_baldino_modificada": ("draft", "roth2019iat045", 46.4, 55.7, "ar_congelador_e1"),
}


def test_cantidades_del_catalogo() -> None:
    presets = service.net_presets()
    assert set(NETS_20) <= set(presets)
    inidep = {k: v for k, v in presets.items() if k.startswith("inidep_")}
    assert len(inidep) == 11
    assert sum(s.status == "published" for s in inidep.values()) == 5
    assert sum(s.status == "published" for s in presets.values()) == 22
    assert sum(s.status == "draft" for s in presets.values()) == 13


@pytest.mark.parametrize("net_id", sorted(NETS_20))
def test_red_valida_estado_y_caso(net_id: str) -> None:
    status, key, head, foot, vessel = NETS_20[net_id]
    spec = load_net(net_id)
    assert (spec.rig, spec.family, spec.status) == ("otter", "bottom", status)
    assert spec.sources[0].key == key
    assert spec.headrope is not None and spec.footrope is not None
    assert (spec.headrope.length_m, spec.footrope.length_m) == (head, foot)
    errs = [i for i in check(spec) if i.level == "error"]
    if status == "published":
        assert errs == []
    else:
        # Borrador: empalmes que no cierran (como se leen), con la razón en las notas.
        assert errs and all(i.code == "seam" for i in errs)
        assert spec.notes[0].startswith("BORRADOR")
    cc = catalog_case(spec)
    assert cc.case.vessel.id == vessel
    r = run(cc.case)
    assert r.dimensions.std.headrope_m == pytest.approx(head)
    assert np.all(np.isfinite(np.asarray(r.drag.rn.std)))


@pytest.mark.parametrize("net_id", sorted(NETS_20))
def test_procedencia_completa(net_id: str) -> None:
    spec = load_net(net_id)
    cov = coverage(spec)
    assert cov["fraction"] == 1.0, cov["missing"]
    for path, prov in spec.provenance.items():
        if prov.kind != "transcribed":
            assert prov.note, path
        if prov.kind == "assumed" and path.endswith(("rtex", "twine_diameter_mm")):
            assert "A VERIFICAR" in (prov.note or ""), path
    # Cada documento citado en la procedencia está entre las fuentes de la red.
    keys = {s.key for s in spec.sources}
    assert {p.document for p in spec.provenance.values() if p.document} <= keys


def test_aparejo_y_portones_de_las_fuentes() -> None:
    # IAT 101/2017, p. 4: SPF08 de 4,5 m² y 1200 kg, CL 1,00 y CD 0,58; patentes de 50 m; 100 m.
    spec = load_net("inidep_iat101_va355_disenada")
    door, notes = source_door(spec, 2855.2)
    assert door.area_m2 == 4.5 and door.weight_air_kg == 1200.0
    assert {(c.cl, c.cd) for c in door.coefficients} == {(1.00, 0.58)}
    assert any("CL = 1 y CD = 0.58 de la fuente" in n for n in notes)
    case = catalog_case(spec).case
    assert (case.sweeps_m, case.depth_m) == (50.0, 100.0)
    # IAT 151/2018, p. 3: patentes de 100 m; polivalentes de 1200 kg (superficie supuesta).
    spec = load_net("inidep_iat151_va355_construida")
    assert catalog_case(spec).case.sweeps_m == 100.0
    assert spec.provenance["design.door_weight_air_kg"].kind == "transcribed"
    assert spec.provenance["design.door_area_m2"].kind == "assumed"
    assert spec.floats is not None and (spec.floats.count, spec.floats.diameter_mm) == (90, 200)
    assert spec.ballast_kg == 380.0
    # Engel: polivalentes de 1200 kg y 5,58 m² (EH 06/12), buque Holmberg (hélice sin KF: paso
    # fijo, como la API); 77 boyas y 240 kg de IC 016/24.
    spec = load_net("inidep_iat101_engel355")
    assert spec.provenance["design.door_area_m2"].document == "tringali2012eh0612"
    cc = catalog_case(spec)
    assert cc.case.door.area_m2 == 5.58 and cc.case.fridman_kf == 10.0
    assert any("paso fijo" in a for a in cc.assumptions)
    assert spec.floats is not None and spec.floats.count == 77 and spec.ballast_kg == 240.0
    # Baldino: Mercury de 2300 kg → el tamaño de 2300 kg de la tabla de Polar (7,5 m²).
    case = catalog_case("inidep_iat045_baldino_modificada").case
    assert case.door.weight_air_kg == 2300.0 and case.door.area_m2 == 7.5
    assert case.warp_id == "wire_6x19_991_24mm"


def test_lecturas_dudosas_documentadas() -> None:
    issues = check(load_net("inidep_iat101_engel355"))
    assert sum(i.code == "seam" and i.level == "error" for i in issues) == 4
    issues = check(load_net("inidep_iat045_baldino_modificada"))
    assert [i.panels for i in issues if i.level == "error"] == [("S1", "S2")]
    issues = check(load_net("inidep_iat045_baldino_original"))
    assert any("36 %" in i.message for i in issues if i.level == "error")
    built = load_net("inidep_iat151_va355_construida")
    assert built.provenance["panels.L1.mesh_mm"].kind == "assumed"


def test_cable_medido_es_una_entrada() -> None:
    """``measured_warp_m`` cambia el cable, no el método: con ``None`` todo queda igual."""
    base = run(catalog_case("inidep_iat101_va355_disenada").case)
    same = run(catalog_case("inidep_iat101_va355_disenada", measured_warp_m=None).case)
    assert same.doors.spread_m == base.doors.spread_m
    longer = run(catalog_case("inidep_iat101_va355_disenada", measured_warp_m=500.0).case)
    assert longer.rigging.towing.warp_m == 500.0
    assert longer.rigging.towing.warp_depth_ratio == pytest.approx(5.0)
    assert longer.doors.spread_m > base.doors.spread_m
    with pytest.raises(ValueError):
        catalog_case("inidep_iat101_va355_disenada", measured_warp_m=0.0)


def test_mediciones_transcriptas() -> None:
    built = F.references("inidep_iat151_va355_construida")
    by_series: dict[str, list[dict[str, object]]] = {}
    for m in built:
        by_series.setdefault(str(m["series"]), []).append(m)
    assert {k: len(v) for k, v in by_series.items()} == {"iat151": 52, "ic029": 3, "ic012": 40}
    # IAT 151/2018, tabla 1: promedio 92,2 m y 3,72 m, mín. 75 y 3,1, máx. 103 y 4,9.
    dp = [float(m["door_spread_m"]) for m in by_series["iat151"]]  # type: ignore[arg-type]
    av = [float(m["vertical_opening_m"]) for m in by_series["iat151"]]  # type: ignore[arg-type]
    assert round(float(np.mean(dp)), 1) == 92.2 and round(float(np.mean(av)), 2) == 3.72
    assert (min(dp), max(dp), min(av), max(av)) == (75, 103, 3.1, 4.9)
    engel = F.references("inidep_iat101_engel355")
    assert sum(m["series"] == "ic016" for m in engel) == 11
    sims = F.references("inidep_iat101_va355_disenada", "simulated")
    assert sims[0]["door_spread_m"] == 89.2 and sims[0]["drag_kgf"] == 6243.47


# --- Validación frente a lo medido y a DynamiT ----------------------------------------------


@cache
def _points(net_id: str, kind: str) -> tuple[tuple[dict[str, object], F.EnginePoint], ...]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return tuple((ref, F.reference_point(net_id, ref)) for ref in F.references(net_id, kind))


def _devs(net_id: str, series: str, key: str, attr: str, kind: str = "measured") -> np.ndarray:
    out = []
    for ref, p in _points(net_id, kind):
        if ref.get("series", ref.get("variant")) == series and ref.get(key) is not None:
            d = F.deviation(getattr(p, attr), float(ref[key]))  # type: ignore[arg-type]
            assert d is not None
            out.append(d)
    return np.asarray(out)


def test_dp_con_spf08_dentro_de_tolerancia() -> None:
    # IC 012/2021: 40 lances con SPF08 de superficie publicada: todos dentro de ±20 %.
    d = _devs("inidep_iat151_va355_construida", "ic012", "door_spread_m", "door_spread_m")
    assert len(d) == 40
    assert abs(d.mean()) < 0.05
    assert np.all(np.abs(d) <= F.TOLERANCES["door_spread_m"])


def test_ah_y_av_de_la_engel_con_sensores() -> None:
    ah = _devs("inidep_iat101_engel355", "ic016", "wing_spread_m", "wing_spread_m")
    # Ocho de nueve dentro de ±20 %; el lance 18 (+20 %) es el que el informe anota con 15 m de AH
    # «y por plano debería ser de 21 m» (IC 016/24, p. 12; capítulo de validación).
    assert len(ah) == 9 and abs(ah.mean()) < 0.10
    assert np.sum(np.abs(ah) <= F.TOLERANCES["wing_spread_m"]) >= 8
    assert np.all(np.abs(ah) <= 0.21)
    av = _devs("inidep_iat101_engel355", "ic016", "vertical_opening_m", "vertical_opening_m")
    assert np.all(np.abs(av) <= F.TOLERANCES["vertical_opening_m"])


def test_va_frente_a_dynamit_a_100_m() -> None:
    ((ref, p),) = _points("inidep_iat101_va355_disenada", "simulated")
    assert p.warp_m == 500.0 and p.door_area_m2 == 4.5 and p.sweeps_m == 50.0
    assert abs(F.deviation(p.wing_spread_m, 23.0) or 0) <= 0.10
    assert abs(F.deviation(p.vertical_opening_m, 3.7) or 0) <= 0.10


def test_av_de_la_va_construida_iat151() -> None:
    d = _devs(
        "inidep_iat151_va355_construida", "iat151", "vertical_opening_m", "vertical_opening_m"
    )
    assert np.mean(np.abs(d) <= F.TOLERANCES["vertical_opening_m"]) >= 0.95


def test_dp_con_polivalentes_iat151() -> None:
    """Fase 20.5: con el CL efectivo calibrado la DP de IAT 151/18 entra en tolerancia.

    Antes de la calibración el motor daba +26 % de promedio (polar de Seafish supuesta). El CL
    efectivo se ajusta a la DP media de esta serie, así que el promedio queda en ±1 %; los lances
    tienen que quedar todos dentro de ±20 % y con un desvío medio absoluto menor que el 6 %.
    """
    d = _devs("inidep_iat151_va355_construida", "iat151", "door_spread_m", "door_spread_m")
    assert len(d) == 52
    assert abs(d.mean()) <= 0.01
    assert np.mean(np.abs(d)) <= 0.06
    assert np.all(np.abs(d) <= F.TOLERANCES["door_spread_m"])


# Fuera de tolerancia, documentado en el capítulo «Validación con redes de merluza» (strict: si el
# motor cambia y el caso entra en tolerancia, la prueba avisa para actualizar el capítulo).


@pytest.mark.xfail(
    strict=True,
    reason="la DP del motor crece con el cable menos que la medida: −33 % a 500–930 m (IC 029/18); "
    "la corrección de cable no se aplica (Δn no significativo, Fase 20.5)",
)
def test_dp_con_cable_largo() -> None:
    d = _devs("inidep_iat151_va355_construida", "ic029", "door_spread_m", "door_spread_m")
    assert np.all(d < -0.25)  # el desvío documentado
    assert np.all(np.abs(d) <= F.TOLERANCES["door_spread_m"])


@pytest.mark.xfail(
    strict=True,
    reason="DP −42 % y AV de Suzuki fija (+76 %) frente a DynamiT a 400 m (IAT 026/25)",
)
def test_va_frente_a_dynamit_a_400_m() -> None:
    ((ref, p),) = _points("inidep_iat151_va355_construida", "simulated")
    assert p.warp_m == 1200.0
    assert abs(F.deviation(p.total_drag_kgf, 9175.828) or 0) <= F.TOLERANCES["drag_kgf"]
    assert -0.50 < (F.deviation(p.door_spread_m, 162.3) or 0) < -0.35  # el desvío documentado
    assert abs(F.deviation(p.door_spread_m, 162.3) or 0) <= F.TOLERANCES["door_spread_m"]


@pytest.mark.xfail(
    strict=True,
    reason="Baldino: malletas no publicadas (25 m del libro) y AH del libro > lima",
)
def test_baldino_frente_a_dynamit() -> None:
    dp = _devs(
        "inidep_iat045_baldino_modificada",
        "modificada",
        "door_spread_m",
        "door_spread_m",
        "simulated",
    )
    ah = _devs(
        "inidep_iat045_baldino_modificada",
        "modificada",
        "horizontal_opening_m",
        "wing_spread_m",
        "simulated",
    )
    assert -0.45 < dp[0] < -0.30 and ah[0] > 0.40  # los desvíos documentados
    assert abs(dp[0]) <= F.TOLERANCES["door_spread_m"]


def test_sensibilidad_al_cable_menor_que_la_medida() -> None:
    """Desvío sistemático documentado: dDP/dcable del motor < la medida en las tres series."""
    for net_id, series in (
        ("inidep_iat151_va355_construida", "iat151"),
        ("inidep_iat151_va355_construida", "ic012"),
        ("inidep_iat101_engel355", "ic016"),
    ):
        pts = [
            (p.warp_m, float(ref["door_spread_m"]), p.door_spread_m)  # type: ignore[arg-type]
            for ref, p in _points(net_id, "measured")
            if ref["series"] == series
        ]
        a = np.asarray(pts)
        measured = np.polyfit(a[:, 0], a[:, 1], 1)[0]
        engine = np.polyfit(a[:, 0], a[:, 2], 1)[0]
        assert 0 < engine < measured, series


def test_portones_de_validacion() -> None:
    door = F.validation_door("inidep_iat151_va355_construida", "spf08_1000")
    assert (door.area_m2, door.weight_air_kg) == (4.68, 1000.0)
    poly = F.validation_door("inidep_iat151_va355_construida", "polivalente_1200")
    assert poly.coefficients and poly.coefficients[0].angle_deg == 27
    with pytest.raises(KeyError):
        F.validation_door("inidep_iat151_va355_construida", "no_existe")
