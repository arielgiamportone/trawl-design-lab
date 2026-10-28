"""Fase 19.8c: tangoneras de langostino de INIDEP IAT 27/2019 (Solimeno) e IAT 75/2023 (Deseado)."""

from __future__ import annotations

import math

import pytest

from trawlkit.api import service
from trawlkit.catalog import LANGOSTINO_DEPTH_M, catalog_case
from trawlkit.io import load_net
from trawlkit.model import run
from trawlkit.netcheck import check
from trawlkit.provenance import coverage
from trawlkit.rigging import shrimp

#: Red → (estado, fuente, lima [m], burlón [m], profundidad del caso [m]).
NETS_198 = {
    "inidep_iat027_tangonera_solimeno": ("draft", "roth2019iat027", 37.8, 46.6, 100.0),
    "inidep_iat027_tangonera_modificada": ("published", "roth2019iat027", 39.4, 45.0, 100.0),
    "inidep_iat075_tangonera_propuesta": ("draft", "roth2023iat075", 34.84, 36.9, 90.0),
    "inidep_iat075_tangonera_tradicional": ("draft", "roth2023iat075", 34.84, 41.34, 90.0),
}
#: Red → (velocidad, AH, AV y resistencia o tensión de DynamiT), de los informes.
DYNAMIT_198 = {
    "inidep_iat027_tangonera_solimeno": (4.0, 17.5, 1.1, 5853.1),
    "inidep_iat027_tangonera_modificada": (4.0, 17.9, 1.5, 5350.7),
    "inidep_iat075_tangonera_propuesta": (3.5, 13.7, 1.1, 4221.3),  # + 2 flotadores
    "inidep_iat075_tangonera_tradicional": (3.5, 13.3, 1.1, 4054.3),
}


def test_cantidades_del_catalogo() -> None:
    presets = service.net_presets()
    assert set(NETS_198) <= set(presets)
    inidep = {k: v for k, v in presets.items() if k.startswith("inidep_")}
    assert len(inidep) == 6
    assert sum(s.status == "published" for s in inidep.values()) == 3
    assert sum(s.status == "published" for s in presets.values()) == 20
    assert sum(s.status == "draft" for s in presets.values()) == 10


@pytest.mark.parametrize("net_id", sorted(NETS_198))
def test_red_valida_estado_y_caso(net_id: str) -> None:
    status, key, head, foot, depth = NETS_198[net_id]
    spec = load_net(net_id)
    assert (spec.rig, spec.family, spec.status) == ("outrigger", "bottom", status)
    assert spec.sources[0].key == key
    assert spec.headrope is not None and spec.footrope is not None
    assert (spec.headrope.length_m, spec.footrope.length_m) == (head, foot)
    # El estado sigue al validador: publicada sin errores; borrador con empalmes de copo que no
    # cierran (como dibuja el plano) y la razón en las notas.
    errs = [i for i in check(spec) if i.level == "error"]
    if status == "published":
        assert errs == []
    else:
        assert errs and all(i.code == "seam" for i in errs)
        assert all(any(p.endswith(("C", "C1")) for p in i.panels) for i in errs)
        assert spec.notes[0].startswith("BORRADOR")
    cc = catalog_case(spec)
    assert cc.case.vessel.id == "ar_tangonero_1998"
    assert cc.case.depth_m == depth
    r = run(cc.case)
    assert r.dimensions.std.headrope_m == pytest.approx(head)
    assert r.multirig is not None and r.multirig.n_nets == 2
    assert all(math.isfinite(float(x)) for x in r.multirig.demand.std)


@pytest.mark.parametrize("net_id", sorted(NETS_198))
def test_procedencia_completa(net_id: str) -> None:
    spec = load_net(net_id)
    cov = coverage(spec)
    assert cov["fraction"] == 1.0, cov["missing"]
    assert cov["by_kind"]["transcribed"] > cov["by_kind"].get("assumed", 0)
    for path, prov in spec.provenance.items():
        if prov.kind != "transcribed":
            assert prov.note, path
        if prov.kind == "assumed" and path.endswith(("rtex", "twine_diameter_mm")):
            assert "A VERIFICAR" in (prov.note or ""), path


def test_aparejo_de_los_informes() -> None:
    # IAT 27/2019, p. 2: portones de 4,20 × 1,30 m y 450 kg, tijera de 55 m, bridas de 4 m,
    # 5 flotadores de 200 mm, 140 kg de cadena, 100 m.
    spec = load_net("inidep_iat027_tangonera_modificada")
    design = (spec.model_extra or {})["design"]
    assert (design["door_length_m"], design["door_height_m"]) == (4.20, 1.30)
    assert design["door_weight_air_kg"] == 450.0 and design["outrigger_bridle_m"] == 55.0
    assert spec.provenance["design.door_length_m"].kind == "transcribed"
    assert spec.floats is not None and (spec.floats.count, spec.floats.diameter_mm) == (5, 200)
    assert spec.ballast_kg == 140.0
    r = run(catalog_case(spec).case)
    assert r.multirig is not None and r.multirig.bridle_m == 55.0
    op = r.spread.shrimp
    assert op is not None and op.bridle_m == 4.0
    # IAT 75/2023, p. 2: 530 kg y 4,08 m²; medidas y profundidad supuestas.
    spec = load_net("inidep_iat075_tangonera_propuesta")
    design = (spec.model_extra or {})["design"]
    assert design["door_weight_air_kg"] == 530.0
    assert design["door_length_m"] * design["door_height_m"] == pytest.approx(4.08, abs=0.02)
    assert spec.provenance["design.door_length_m"].kind == "assumed"
    assert design["depth_m"] == LANGOSTINO_DEPTH_M
    assert spec.provenance["design.depth_m"].kind == "assumed"


def test_lecturas_a_verificar() -> None:
    # IAT 75: el vientre se lee «26»; el corte 1N4B daría 46 (fig. 1) y 66 (fig. 2).
    for net_id, cut in (
        ("inidep_iat075_tangonera_propuesta", 46),
        ("inidep_iat075_tangonera_tradicional", 66),
    ):
        spec = load_net(net_id)
        l1 = next(p for p in spec.panels if p.id == "L1")
        assert l1.meshes_bottom == 26
        assert f"daría {cut} mallas" in (l1.note or "")
    # IAT 27 fig. 2: el exceso de paño que señala el informe (140 × 80 mm sobre 100 × 60 mm).
    issues = check(load_net("inidep_iat027_tangonera_solimeno"))
    assert any(i.code == "seam" and "46 %" in i.message for i in issues)


@pytest.mark.parametrize("net_id", sorted(DYNAMIT_198))
def test_aberturas_frente_a_dynamit(net_id: str) -> None:
    v, ah, av, res = DYNAMIT_198[net_id]
    spec = load_net(net_id)
    # La primera simulación a esa velocidad es la de la variante del catálogo.
    sim = next(s for s in (spec.model_extra or {})["simulated"] if s["speed_kn"] == v)
    assert sim["horizontal_opening_m"] == ah and sim["vertical_opening_m"] == av
    r = run(catalog_case(spec).case)
    op = r.spread.shrimp
    assert op is not None and op.method == "tijera"
    assert shrimp.AH_OVER_DP_RANGE[0] <= op.ah_over_dp <= shrimp.AH_OVER_DP_RANGE[1]
    got = r.spread.horizontal_opening_m
    if net_id.startswith("inidep_iat075"):
        assert got == pytest.approx(ah, rel=0.10)
    else:
        # IAT 27: la AH del método queda 28–30 % por debajo de DynamiT (fuera de ±20 %; capítulo
        # 26): la DP del equilibrio (16,9–17,9 m) no supera la AH de DynamiT.
        assert -0.35 < got / ah - 1 < -0.20
        assert r.doors.spread_m <= ah + 0.1
    assert op.vertical_opening_m == pytest.approx(0.04 * spec.headrope.length_m)  # type: ignore[union-attr]
    assert r.spread.vertical_opening_m >= av
    assert r.multirig is not None
    per_net = float(r.multirig.per_net.std[r.case.speed_index(v)])
    assert per_net == pytest.approx(res, rel=0.20)
