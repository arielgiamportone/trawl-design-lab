"""Cualquier red del catálogo con un buque elegido calcula por la API (Fase 19.7a).

La app (modos guiado y experto, también sin conexión) siempre manda un buque. Las redes cuya
fuente no da profundidad (INIDEP, SEAFDEC) respondían 422; los buques sin KF de Fridman
tabulado (paso variable sin tobera) respondían 400; y con buques que no son los de la A-3 la
regla «al metro» del libro daba separaciones de portones sin sentido (NaN en el cable).
"""

from __future__ import annotations

import json
import math

import pytest
from fastapi.testclient import TestClient

from trawlkit.api import offline, service
from trawlkit.api.app import app

client = TestClient(app)
#: Un buque del libro, uno de la flota argentina por estrato y uno con hélice de paso variable.
VESSELS = ("fao_a3_150hp", "ar_fresquero_e2", "bip_holmberg")


@pytest.mark.parametrize("net", sorted(service.net_presets()))
@pytest.mark.parametrize("vessel", VESSELS)
def test_red_del_catalogo_con_buque_elegido(net: str, vessel: str) -> None:
    res = client.post("/design", json={"net": net, "vessel": vessel})
    assert res.status_code == 200, res.text
    summary = res.json()["summary"]
    nan = [k for k, v in summary.items() if isinstance(v, float) and math.isnan(v)]
    assert nan == []


def test_profundidad_supuesta_queda_anotada() -> None:
    case = service.build_case(net="seafdec_31_outrigger_shrimp", vessel="fao_a3_150hp")
    assert case.working_depth_m == 30.0
    assert any("profundidad" in a for a in case.assumptions)
    # Una profundidad indicada por el usuario manda.
    case = service.build_case(
        net="seafdec_31_outrigger_shrimp", vessel="fao_a3_150hp", params={"depth_m": 18}
    )
    assert case.working_depth_m == 18.0


def test_helice_sin_kf_se_calcula_como_paso_fijo() -> None:
    case = service.build_case(net="fao_a3_standard", vessel="bip_holmberg")
    assert case.fridman_kf == 10.0
    assert any("paso fijo" in a for a in case.assumptions)


def test_caso_del_libro_sin_cambios() -> None:
    case = service.build_case(net="fao_a3_standard", vessel="fao_a3_150hp")
    assert case.door_spread_rule == "excel" and case.fridman_kf is None


def test_sin_conexion_igual() -> None:
    body = json.dumps({"net": "inidep_ito043_tangonera_inidep", "vessel": "ar_tangonero_1998"})
    status, _ = offline.handle("POST", "/design", body)
    assert status == 200


def test_tangonera_con_buque_usa_el_porton_y_la_tijera_del_plano() -> None:
    """Fase 19.8d: con el buque elegido (como manda la app) y sin portón, la tangonera usa el
    portón y la tijera de su plano, igual que su propio caso; con el de la A-3 abría a la mitad."""
    for net in ("inidep_ito043_tangonera_inidep", "inidep_iat027_tangonera_modificada"):
        own = client.post("/design", json={"net": net}).json()["summary"]
        res = client.post("/design", json={"net": net, "vessel": "ar_tangonero_1998"}).json()
        s = res["summary"]
        assert s["door_id"] == own["door_id"] and s["door_id"].startswith("plan_")
        assert s["horizontal_opening_m"] == pytest.approx(own["horizontal_opening_m"])
        assert s["door_spread_m"] == pytest.approx(own["door_spread_m"])
        assert s["cfp_av_limit_m"] == 1.5
        assert any(n.startswith("catalog: portón del plano") for n in res["notes"])
    # Un portón elegido manda.
    s = client.post(
        "/design",
        json={
            "net": "inidep_ito043_tangonera_inidep",
            "vessel": "ar_tangonero_1998",
            "door": "fao_flat_wood_a3",
        },
    ).json()["summary"]
    assert s["door_id"] == "fao_flat_wood_a3"
