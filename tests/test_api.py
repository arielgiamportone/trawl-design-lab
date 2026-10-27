import json

import pytest
from fastapi.testclient import TestClient

from trawlkit.api.app import app
from trawlkit.api.service import to_jsonable

client = TestClient(app)
STD = {"net": "fao_a3_standard", "net_modified": "fao_a3_modified", "vessel": "fao_a3_150hp"}


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_catalogs() -> None:
    nets = {n["id"] for n in client.get("/catalog/nets").json()}
    assert {"fao_a3_standard", "fao_a3_modified"} <= nets
    spec = client.get("/catalog/nets/fao_a3_standard").json()
    assert [p["id"] for p in spec["panels"]][:2] == ["A", "B"]
    assert client.get("/catalog/nets/nope").status_code == 404
    assert {v["id"] for v in client.get("/catalog/vessels").json()} >= {"fao_a3_150hp"}
    doors = client.get("/catalog/doors").json()
    assert doors[0]["coefficients"]
    params = {p["name"]: p for p in client.get("/params").json()}
    assert params["sweeps_m"]["default"] == 25.0
    assert "Dim!F65" in params["sweeps_m"]["comment"]
    assert len(client.get("/errata").json()) >= 25


def test_catalog_items_have_filter_fields() -> None:
    items = {n["id"]: n for n in client.get("/catalog/nets").json()}
    pair = items["bobp_wp13_pair_ho80"]
    assert pair["family"] == "bottom" and pair["rig"] == "pair"
    assert pair["vessel_hp"] == [30, 33] and pair["status"] == "published"
    assert pair["source"]["url"].startswith("https://www.fao.org/")
    assert pair["check"]["ok"] and pair["coverage"]["fraction"] == 1.0
    assert items["scharfe_krill_1420x200"]["four_panel"] is True
    drafts = client.get("/catalog/nets", params={"status": "draft"}).json()
    assert drafts and all(d["status"] == "draft" for d in drafts)
    assert not client.get("/health").json().get("nets_failed")


def test_catalog_provenance_and_check() -> None:
    rows = client.get("/catalog/nets/bobp_wp13_pair_ho80/provenance").json()
    by_path = {r["path"]: r for r in rows}
    f = by_path["panels.F.meshes_depth"]
    assert f["value"] == 80 and f["provenance"]["kind"] == "transcribed"
    assert "80" in f["provenance"]["note"]
    a3 = client.get("/catalog/nets/fao_a3_standard/provenance").json()
    assert all(r["provenance"]["kind"] == "excel" for r in a3)
    chk = client.get("/catalog/nets/bobp_wp13_pair_ho80/check").json()
    assert chk["ok"] and chk["warnings"] >= 1
    assert any(i["code"] == "cut" for i in chk["issues"])
    assert client.get("/catalog/nets/nope/check").status_code == 404


def test_design_catalog_net_uses_its_own_case() -> None:
    r = client.post("/design", json={"net": "bobp_wp13_pair_ho80"})
    assert r.status_code == 200, r.text
    body = r.json()
    notes = body["notes"]
    assert any(n.startswith("pair_trawl") for n in notes)
    assert any(n.startswith("catalog: buque genérico de 31.5 hp") for n in notes)
    assert body["summary"]["rob_3kn_kgf"] == 0.0
    # Los parámetros del usuario mandan sobre los de la fuente.
    r2 = client.post("/design", json={"net": "bobp_wp13_pair_ho80", "params": {"depth_m": 25}})
    assert r2.json()["summary"]["working_depth_m"] == 25.0
    # Con buque elegido, se usa el caso del libro (con portones).
    r3 = client.post("/design", json={"net": "fao_wb_bt2p_60hp", "vessel": "fao_a3_150hp"})
    assert not any(n.startswith("catalog:") for n in r3.json()["notes"])


def test_design_excel_mode_reproduces_summary() -> None:
    r = client.post("/design", json={**STD, "compat": "excel"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"]["headrope_m"] == pytest.approx(28.698, rel=1e-6)
    assert body["summary"]["solid_surface_m2"] == pytest.approx(40.89506, rel=1e-6)
    assert body["summary"]["warp_diameter_mm"] == 12
    assert body["case"]["compat"] == "excel"
    # JSON estricto: sin NaN ni Infinity
    json.loads(r.text, parse_constant=lambda c: pytest.fail(f"constante no JSON: {c}"))


def test_design_corrected_and_params_override() -> None:
    base = client.post("/design", json=STD).json()["summary"]
    assert base["solid_surface_m2"] == pytest.approx(38.74964, rel=1e-5)
    over = client.post("/design", json={**STD, "params": {"sweeps_m": 30.0}}).json()
    assert over["summary"]["sweeps_m"] == 30.0


def _pairs(node: object) -> list[dict[str, object]]:
    """Todos los objetos ``{"std": …, "mod": …}`` (serialización de ``Pair``) del árbol."""
    out: list[dict[str, object]] = []
    if isinstance(node, dict):
        if set(node) == {"std", "mod"}:
            out.append(node)
        for v in node.values():
            out.extend(_pairs(v))
    elif isinstance(node, list):
        for v in node:
            out.extend(_pairs(v))
    return out


def test_design_without_modified_returns_null_mod() -> None:
    r = client.post("/design", json={"net": "fao_a3_standard", "vessel": "fao_a3_150hp"})
    assert r.status_code == 200, r.text
    body = r.json()
    res = body["result"]
    assert body["case"]["net_modified"] is None
    assert res["drag"]["rn"]["mod"] is None and res["drag"]["rn"]["std"]
    assert res["warps"]["total"]["mod"] is None
    assert res["performance"]["demand"]["mod"] is None
    assert res["geometry"]["mod"] is None and res["dimensions"]["mod"] is None
    pairs = _pairs(res)
    assert len(pairs) > 5 and all(p["mod"] is None for p in pairs)
    # El resumen no cambia (sólo usa la columna estándar).
    with_mod = client.post("/design", json=STD).json()
    assert body["summary"]["headrope_m"] == with_mod["summary"]["headrope_m"]
    assert with_mod["result"]["drag"]["rn"]["mod"] is not None


def test_design_inline_net_spec() -> None:
    spec = client.get("/catalog/nets/fao_a3_standard").json()
    spec["id"] = "custom"
    r = client.post("/design", json={"net": spec, "vessel": "fao_a3_150hp"})
    assert r.status_code == 200, r.text
    assert r.json()["summary"]["net_id"] == "custom"


@pytest.mark.parametrize(
    ("payload", "status"),
    [
        ({"net": "../../etc/passwd"}, 404),
        ({"vessel": "nope"}, 404),
        ({"params": {"not_a_param": 1}}, 422),
        ({"params": {"speeds_kn": []}}, 422),
        ({"params": {"sweeps_m": -5}}, 422),
        ({"params": {"speeds_kn": [1.0, -2.0]}}, 422),
        ({"params": {"sweeps_m": True}}, 422),
        ({"compat": "other"}, 422),
        ({"unexpected": 1}, 422),
    ],
)
def test_design_rejects_bad_input(payload: dict[str, object], status: int) -> None:
    assert client.post("/design", json=payload).status_code == status


def test_plan_svg() -> None:
    r = client.post("/design/plan?view=sheet&variant=mod", json=STD)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/svg+xml")
    assert "<svg" in r.text
    assert (
        client.post("/design/plan?variant=mod", json={"net": "fao_a3_standard"}).status_code == 422
    )


@pytest.mark.parametrize("fmt", ["html", "xlsx", "pdf"])
def test_report_formats(fmt: str) -> None:
    r = client.post(f"/design/report?format={fmt}", json=STD)
    assert r.status_code == 200, r.text[:300]
    if fmt == "pdf":
        assert r.content.startswith(b"%PDF")
    elif fmt == "xlsx":
        assert r.content[:2] == b"PK"
    else:
        assert "<html" in r.text.lower()


def test_to_jsonable() -> None:
    assert to_jsonable({"a": float("nan"), "b": (1.0, float("inf"))}) == {
        "a": None,
        "b": [1.0, None],
    }


def test_inline_net_edge_edit_changes_geometry() -> None:
    spec = client.get("/catalog/nets/fao_a3_standard").json()
    base = client.post("/design", json={"net": spec}).json()["summary"]["solid_surface_m2"]
    panel_c = next(p for p in spec["panels"] if p["id"] == "C")
    panel_c["meshes_bottom"] = 140  # sin tocar meshes_a/meshes_b (57/117)
    edited = client.post("/design", json={"net": spec}).json()["summary"]["solid_surface_m2"]
    assert edited > base


def test_optimize_endpoint() -> None:
    body = {
        "net": "fao_a3_standard",
        "vessel": "fao_a3_150hp",
        "objective": "area",
        "margin": 0.1,
        "s_bounds": [0.8, 1.2],
        "v_bounds": [1.5, 3.5],
        "grid": {"n_s": 3, "n_v": 5},
        "refine": False,
    }
    r = client.post("/optimize", json=body)
    assert r.status_code == 200, r.text[:500]
    json.loads(r.text, parse_constant=lambda c: pytest.fail(f"constante no JSON: {c}"))
    out = r.json()
    assert out["objective"] == "area_rate" and out["feasible"]
    assert out["best"]["feasible"] and out["refine"] is None
    assert {c["name"] for c in out["best"]["constraints"]} == {
        "thrust",
        "net_open",
        "warp",
        "door",
        "speed",
    }
    assert len(out["grid"]["feasible"]) == 3 and len(out["grid"]["feasible"][0]) == 5
    assert out["pareto"] and all(p["feasible"] for p in out["pareto"])
    assert out["settings"]["limits"]["margin"] == 0.1


@pytest.mark.slow
def test_optimize_endpoint_refine_is_seeded() -> None:
    body = {"grid": {"n_s": 3, "n_v": 3}, "objective": "volume", "seed": 1}
    a = client.post("/optimize", json=body).json()
    b = client.post("/optimize", json=body).json()
    assert a["refine"]["nfev"] > 0
    assert (a["best"]["s"], a["best"]["v_kn"]) == (b["best"]["s"], b["best"]["v_kn"])


@pytest.mark.parametrize(
    "patch",
    [
        {"objective": "speed"},
        {"s_bounds": [1.2, 0.8]},
        {"v_bounds": [0.1, 3.0]},
        {"grid": {"n_s": 40, "n_v": 5}},
        {"margin": -0.1},
        {"door_angle": 80.0},
        {"unknown": 1},
    ],
)
def test_optimize_endpoint_validation(patch: dict[str, object]) -> None:
    body = {"grid": {"n_s": 2, "n_v": 2}, "refine": False, **patch}
    assert client.post("/optimize", json=body).status_code == 422


def test_optimize_endpoint_unknown_vessel() -> None:
    body = {"vessel": "nope", "grid": {"n_s": 2, "n_v": 2}, "refine": False}
    assert client.post("/optimize", json=body).status_code == 404


def test_scaled_net_endpoint() -> None:
    r = client.post("/optimize/scaled-net", json={"net": "fao_a3_standard", "s": 0.8})
    assert r.status_code == 200, r.text[:300]
    spec = r.json()
    assert spec["id"] == "fao_a3_standard_s0.80"
    base = client.get("/catalog/nets/fao_a3_standard").json()
    c0 = next(p for p in base["panels"] if p["id"] == "C")
    c1 = next(p for p in spec["panels"] if p["id"] == "C")
    assert c1["meshes_depth"] == round(0.8 * c0["meshes_depth"])
    assert c1["mesh_mm"] == c0["mesh_mm"]
    # la red escalada sirve como red en línea de /design
    d = client.post("/design", json={"net": spec}).json()
    assert d["summary"]["net_id"] == "fao_a3_standard_s0.80"
    for body, status in (({"s": 0.1}, 422), ({"s": 1.0, "net": "nope"}, 404), ({}, 422)):
        assert client.post("/optimize/scaled-net", json=body).status_code == status


def test_simulate_endpoint() -> None:
    body = {"speeds_kn": [3.0, 2.0], "resolution": 2}
    r = client.post("/simulate", json=body)
    assert r.status_code == 200, r.text[:500]
    json.loads(r.text, parse_constant=lambda c: pytest.fail(f"constante no JSON: {c}"))
    out = r.json()
    assert [x["speed_kn"] for x in out["results"]] == [3.0, 2.0]  # orden pedido
    assert "nodes" not in out["results"][0]
    assert set(out["projections_svg"]) == {"3", "2"}
    assert set(out["projections_svg"]["3"]) == {"plan", "profile", "front"}
    assert out["projections_svg"]["3"]["plan"].lstrip().startswith(("<svg", "<?xml"))
    r3 = out["results"][0]
    assert r3["converged"] and 10.0 < r3["ah_m"] < 16.0 and 0.5 < r3["av_m"] < 4.0
    assert out["results"][1]["drag_kgf"] < r3["drag_kgf"]  # más lento, menos arrastre
    assert [e["speed_kn"] for e in out["engine"]] == [3.0, 2.0]
    assert out["engine"][0]["drag_kgf"] > 0
    dyn = out["dynamit_comparison"]
    assert dyn and [d["speed_kn"] for d in dyn] == [3.0, 2.0]
    assert dyn[0]["dynamit"]["drag_kgf"] == pytest.approx(1331.3)
    assert dyn[0]["sim_pct"]["ah_m"] == pytest.approx((r3["ah_m"] - 13.3) / 13.3 * 100, rel=1e-9)
    assert out["settings"]["resolution"] == 2 and out["runtime_s"] > 0


def test_simulate_geometry_and_other_net() -> None:
    body = {
        "net": "fao_a3_modified",
        "speeds_kn": [2.25],
        "resolution": 2,
        "include_geometry": True,
        "cn": 1.2,
        "ct": 0.05,
    }
    r = client.post("/simulate", json=body)
    assert r.status_code == 200, r.text[:500]
    out = r.json()
    assert out["dynamit_comparison"] is None  # sólo para la red estándar
    res = out["results"][0]
    assert len(res["nodes"]) > 50 and len(res["triangles"][0]) == 3
    assert res["params"]["cn"] == 1.2 and res["params"]["ct"] == 0.05
    assert set(out["projections_svg"]) == {"2.25"}


def test_simulate_projections_limited_to_three() -> None:
    body = {"speeds_kn": [1.5, 2.0, 2.5, 3.0], "resolution": 2}
    out = client.post("/simulate", json=body).json()
    assert len(out["results"]) == 4
    assert list(out["projections_svg"]) == ["1.5", "2", "2.5"]


@pytest.mark.parametrize(
    "patch",
    [
        {"speeds_kn": []},
        {"speeds_kn": [0.2]},
        {"speeds_kn": [7.0]},
        {"speeds_kn": [3.0, 3.0]},
        {"speeds_kn": [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5]},
        {"resolution": 1},
        {"resolution": 11},
        {"cn": -1},
        {"unknown": 1},
        # costo estimado > 30 s
        {"speeds_kn": [1, 2, 3, 4, 5], "resolution": 10},
    ],
)
def test_simulate_validation(patch: dict[str, object]) -> None:
    body = {"speeds_kn": [3.0], "resolution": 2, **patch}
    r = client.post("/simulate", json=body)
    assert r.status_code == 422, r.text[:300]


def test_simulate_cost_message() -> None:
    body = {"speeds_kn": [1, 2, 3], "resolution": 9}
    r = client.post("/simulate", json=body)
    assert r.status_code == 422
    assert "demasiado costosa" in r.json()["detail"]


@pytest.mark.slow
def test_simulate_default_resolution() -> None:
    out = client.post("/simulate", json={"speeds_kn": [2.0, 3.0, 4.0]}).json()
    assert out["settings"]["resolution"] == 4
    assert all(r["converged"] for r in out["results"])
    assert len(out["projections_svg"]) == 3


def test_layout_matches_engine_layout() -> None:
    from trawlkit.drawing.layout import layout_net
    from trawlkit.io import load_net

    r = client.post("/design/layout", json=STD)
    assert r.status_code == 200, r.text
    body = r.json()
    ref = layout_net(load_net("fao_a3_standard"))
    assert body["mode"] == "schematic"
    assert [p["plane"] for p in body["planes"]] == list(ref.planes)
    upper = body["planes"][0]
    shapes = ref.shapes[upper["plane"]]
    assert len(upper["shapes"]) == len(shapes)
    for got, exp in zip(upper["shapes"], shapes, strict=True):
        assert (got["id"], got["side"], got["meshes_depth"]) == (exp.id, exp.side, exp.meshes_depth)
        flat = [c for pt in got["points"] for c in pt]
        assert flat == pytest.approx([c for pt in exp.points for c in pt])
    assert upper["mouth_y"] == pytest.approx(ref.mouth_y(upper["plane"]))
    mod = client.post("/design/layout?variant=mod&mode=true_scale", json=STD).json()
    assert mod["net_id"] == "fao_a3_modified"
    assert mod["mode"] == "true_scale"


def test_layout_follows_inline_edits_and_validates() -> None:
    spec = client.get("/catalog/nets/fao_a3_standard").json()
    base = client.post("/design/layout", json={"net": spec}).json()
    panel_c = next(p for p in spec["panels"] if p["id"] == "C")
    panel_c["meshes_depth"] += 40
    edited = client.post("/design/layout", json={"net": spec}).json()

    def height(body: dict[str, object], pid: str) -> float:
        plane = body["planes"][0]  # type: ignore[index]
        s = next(s for s in plane["shapes"] if s["id"] == pid)
        return float(s["y_bottom"] - s["y_top"])

    assert height(edited, "C") > height(base, "C")
    assert (
        client.post("/design/layout?variant=mod", json={"net": "fao_a3_standard"}).status_code
        == 422
    )
    assert client.post("/design/layout", json={"net": "nope"}).status_code == 404
    assert client.post("/design/layout?mode=other", json=STD).status_code == 422


def test_openapi_json_is_current() -> None:
    from pathlib import Path

    import tools.export_openapi as export

    current = (Path(__file__).parents[1] / "web" / "openapi.json").read_text(encoding="utf-8")
    assert current == export.render(), "regenerar con: uv run python tools/export_openapi.py"


def test_seabed_catalogue_endpoint() -> None:
    r = client.get("/catalog/seabeds")
    assert r.status_code == 200
    body = r.json()
    assert [s["id"] for s in body] == ["mud", "sand", "mixed", "gravel", "rock"]
    assert body[0]["mu_gear"]["range"][0] <= body[0]["mu_gear"]["nominal"]


def test_design_with_seabed_param() -> None:
    r = client.post("/design", json={**STD, "params": {"seabed": "gravel"}})
    assert r.status_code == 200, r.text
    assert r.json()["summary"]["seabed_friction_kgf"] > 0
    assert client.post("/design", json={**STD, "params": {"seabed": "lava"}}).status_code in (
        400,
        422,
    )


def test_simulate_with_scenario() -> None:
    r = client.post(
        "/simulate",
        json={
            "net": "fao_a3_standard",
            "speeds_kn": [3.0],
            "resolution": 3,
            "scenario": {"catch_kg": 500, "seabed": "sand"},
        },
    )
    assert r.status_code == 200, r.text
    res = r.json()["results"][0]
    assert res["scenario"]["seabed"] == "sand"
    assert res["catch"]["volume_m3"] == pytest.approx(500 / 750, rel=0.02)
    assert res["towing_pull_kgf"] > res["drag_kgf"] > 0
    assert 30 < res["door_spread_m"] < 70
    assert r.json()["settings"]["scenario"]["catch_kg"] == 500


def test_haul_endpoint_and_validation() -> None:
    r = client.post(
        "/simulate/haul",
        json={
            "net": "fao_a3_standard",
            "speed_kn": 3.0,
            "catches_kg": [0, 600],
            "resolution": 3,
            "scenario": {"seabed": "mud"},
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    a, b = body["results"]
    assert b["door_spread_m"] < a["door_spread_m"]
    assert b["towing_pull_kgf"] > a["towing_pull_kgf"]
    assert body["engine"]["seabed_friction_kgf"] > 0
    assert body["engine"]["demand_kgf"] > 0
    for bad in (
        {"catches_kg": [500, 100]},
        {"catches_kg": []},
        {"scenario": {"seabed": "lava"}},
        {"scenario": {"catch_cp": 9}},
        {"resolution": 9},
    ):
        assert client.post("/simulate/haul", json=bad).status_code in (400, 422), bad


def test_health_reports_contract_and_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    from pathlib import Path

    from trawlkit.api.contract import fingerprint, routes

    body = client.get("/health").json()
    web = json.loads((Path(__file__).parents[1] / "web" / "openapi.json").read_text())
    # La app compara esta huella con la de su build (vite.config.ts, mismo algoritmo).
    assert body["contract"] == fingerprint(web)
    assert len(body["contract"]) == 12
    assert "POST /simulate/haul" in routes(web)
    assert body["commit"] is None
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abc123")
    assert client.get("/health").json()["commit"] == "abc123"


def test_fouling_catalogue_endpoint() -> None:
    body = client.get("/catalog/fouling").json()
    assert [f["id"] for f in body] == ["clean", "algae_wings", "jellyfish_codend", "general"]
    assert set(body[3]["zones"]) == {"wings", "body", "codend"}


def test_explore_endpoint_frames_and_validation() -> None:
    r = client.post(
        "/simulate/explore",
        json={
            "net": "fao_a3_standard",
            "variable": "catch_kg",
            "values": [0, 800],
            "resolution": 2,
            "scenario": {"seabed": "mixed", "fouling": "algae_wings"},
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    a, b = body["results"]
    assert b["door_spread_m"] < a["door_spread_m"]
    assert "nodes" not in a  # la geometría va aparte, una sola vez
    geo, frames = body["geometry"], body["frames"]
    n = len(frames[0]["nodes"])
    assert len(frames) == 2 and all(len(f["nodes"]) == n for f in frames)
    assert len(frames[0]["twine_tension_n"]) == len(geo["triangles"])
    assert len(frames[0]["fouling_tri"]) == len(geo["triangles"])
    assert len(geo["doors"]) == 2 and len(geo["warps"]) == 2
    assert a["operation"]["fuel_l_h"] > 0
    assert body["engine"]["demand_kgf"] > 0
    for bad in (
        {"values": [1]},
        {"variable": "colour", "values": [0, 1]},
        {"values": [0, 1], "resolution": 9},
        {"values": [0, 1], "scenario": {"fouling": "barnacles"}},
        {"variable": "speed_kn", "values": [1.0, 1.5], "scenario": {"current_kn": 1.5}},
    ):
        assert client.post("/simulate/explore", json=bad).status_code in (400, 422), bad


def test_species_catalogue_endpoint() -> None:
    r = client.get("/catalog/species")
    assert r.status_code == 200
    ids = {s["id"] for s in r.json()}
    assert {"hake_hubbsi", "cod", "nephrops", "plaice"} <= ids


def test_selectivity_endpoint_variants_and_validation() -> None:
    r = client.post(
        "/simulate/selectivity",
        json={
            "resolution": 3,
            "species": ["cod", "hake_hubbsi"],
            "variants": [
                {"orientation": "diamond", "mesh_mm": 120},
                {"orientation": "t90", "mesh_mm": 120},
            ],
            "scenario": {"seabed": "mixed", "catch_kg": 300},
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    rombo, t90 = body["variants"]
    assert rombo["label"] == "Rombo 120 mm" and t90["orientation"] == "t90"
    assert all(p["mesh_orientation"] == "t90" for p in t90["codend_panels"])
    c_r, c_t = rombo["curves"][0], t90["curves"][0]
    assert c_r["species"] == "cod" and c_r["l50"] is not None
    assert c_t["l50"] > c_r["l50"]
    n_tri = len(rombo["geometry"]["triangles"])
    assert len(rombo["frame"]["opening_deg"]) == n_tri == len(c_r["fit_tri"])
    assert len(rombo["geometry"]["tri_orientation"]) == n_tri
    assert rombo["result"]["params"]["mesh_bending_pa"] > 0
    assert "mesh_summary" in rombo["result"]
    for bad, code in (
        ({"species": ["shark"]}, 422),
        ({"variants": [{"orientation": "hexagonal"}]}, 422),
        ({"variants": [{}, {}, {}, {}]}, 422),
        ({"contact": 2}, 422),
    ):
        assert (
            client.post("/simulate/selectivity", json={"resolution": 2, **bad}).status_code == code
        )


def test_explore_with_species_adds_selectivity() -> None:
    r = client.post(
        "/simulate/explore",
        json={"variable": "catch_kg", "values": [100, 600], "resolution": 2, "species": ["cod"]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    sel = body["results"][1]["selectivity"][0]
    assert sel["species"] == "cod" and "lengths" not in sel and "l50" in sel
    assert len(body["frames"][0]["opening_deg"]) == len(body["geometry"]["triangles"])
    assert len(body["geometry"]["tri_leg_mm"]) == len(body["geometry"]["triangles"])


def test_layout_reports_mesh_orientation() -> None:
    r = client.post("/design/layout", json={"net": "fao_a3_standard"})
    assert r.status_code == 200, r.text
    shapes = [s for p in r.json()["planes"] for s in p["shapes"]]
    assert {s["mesh_orientation"] for s in shapes} == {"diamond"}


def test_sensor_example_and_parse() -> None:
    ex = client.get("/sensors/example")
    assert ex.status_code == 200 and ex.headers["content-type"].startswith("text/csv")
    assert "SINTÉTICO" in ex.text
    r = client.post("/sensors/parse", json={"csv": ex.text, "by": "time", "width": 20})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["log"]["rows"] == 360 and len(body["windows"]) == 3
    assert {o["quantity"] for o in body["observations"]} == {
        "door_spread_m",
        "headrope_height_m",
        "warp_tension_kgf",
    }
    bad = client.post("/sensors/parse", json={"csv": "a,b\n1,2"})
    assert bad.status_code == 422 and "registro inválido" in bad.json()["detail"]


def test_uncertainty_endpoint() -> None:
    r = client.post(
        "/simulate/uncertainty",
        json={
            "samples": 4,
            "scenario": {"seabed": "mixed", "catch_kg": 200},
            "inputs": [{"name": "cn", "low": 1.2, "high": 1.3}],
        },
    )
    assert r.status_code == 200, r.text
    res = r.json()["result"]
    assert res["n"] == 4 and len(res["samples"]) == 4
    cn = next(i for i in res["inputs"] if i["name"] == "cn")
    assert (cn["low"], cn["high"]) == (1.2, 1.3)
    dp = next(o for o in res["outputs"] if o["key"] == "door_spread_m")
    assert dp["p10"] <= dp["p50"] <= dp["p90"] and len(dp["values"]) == 4
    assert client.post("/simulate/uncertainty", json={"samples": 100}).status_code == 422
    bad = client.post(
        "/simulate/uncertainty", json={"inputs": [{"name": "cn", "low": 2, "high": 1}]}
    )
    assert bad.status_code == 422


def test_calibrate_endpoint_validation_and_cost(monkeypatch: pytest.MonkeyPatch) -> None:
    assert client.post("/simulate/calibrate", json={}).status_code == 422  # sin observaciones
    assert (
        client.post("/simulate/calibrate", json={"params": ["gravity"], "reference": "dynamit"})
    ).status_code == 422
    monkeypatch.setenv("TRAWLKIT_MAX_BATCH_SECONDS", "1")
    r = client.post("/simulate/calibrate", json={"reference": "dynamit"})
    assert r.status_code == 422 and "costosa" in r.json()["detail"]


def test_calibrate_endpoint_recovers_example() -> None:
    parsed = client.post(
        "/sensors/parse",
        json={"csv": client.get("/sensors/example").text, "by": "time", "width": 20},
    ).json()
    r = client.post(
        "/simulate/calibrate",
        json={
            "observations": [o for o in parsed["observations"] if o["quantity"] == "door_spread_m"],
            "params": ["door_cl_factor"],
            "scenario": {"seabed": "mixed"},
            "max_evals": 6,
        },
    )
    assert r.status_code == 200, r.text
    res = r.json()["result"]
    assert res["params"][0]["fitted"] == pytest.approx(0.9, abs=0.04)
    assert res["rmse_after_pct"] < res["rmse_before_pct"]


def test_component_catalogue_endpoints() -> None:
    kinds = {k["kind"]: k for k in client.get("/catalog/components").json()}
    assert set(kinds) == {"twine", "wire", "rope", "door", "float", "chain", "shackle"}
    assert kinds["wire"]["generic"] > 0 and "Bridon-Bekaert" in kinds["wire"]["brands"]
    wires = client.get("/catalog/components/wire", params={"generic": True}).json()
    assert wires and all("brand" not in w for w in wires)
    bridon = client.get(
        "/catalog/components/wire", params={"brand": ["Bridon-Bekaert"], "region": "europe"}
    ).json()
    assert any(w.get("brand") == "Bridon-Bekaert" for w in bridon)
    one = client.get("/catalog/components/twine/garware_sapphire_3_1mm").json()
    assert one["provenance"]["breaking_load_kgf"]["kind"] == "transcribed"
    assert one["generic"]["material"] == "PE"
    assert client.get("/catalog/components/bobbin").status_code == 404
    assert client.get("/catalog/components/wire/nope").status_code == 404


def test_component_check_flags_bad_contribution() -> None:
    ok = client.post(
        "/components/check",
        json={
            "kind": "rope",
            "id": "mi_cabo",
            "name": "PP 12 del puerto",
            "material": "PP",
            "diameter_mm": 12,
            "weight_kg_per_m": 0.066,
            "breaking_load_t": 2.0,
        },
    ).json()
    assert ok["ok"] and ok["item"]["status"] == "user" and not ok["issues"]
    bad = client.post(
        "/components/check",
        json={
            "kind": "float",
            "id": "x",
            "name": "boya",
            "material": "plástico",
            "diameter_mm": 100,
            "buoyancy_kgf": 9,
        },
    ).json()
    assert any(i["code"] == "buoyancy" for i in bad["issues"])
    schema = client.post(
        "/components/check", json={"kind": "wire", "id": "y", "name": "sin datos"}
    ).json()
    assert not schema["ok"] and schema["issues"][0]["code"] == "schema"


def test_design_bom_and_component_params() -> None:
    price = {"value": 450.0, "currency": "USD", "unit": "unit"}
    bom = client.post("/design/bom", json={"prices": {"doors": price}}).json()
    lines = {ln["key"]: ln for ln in bom["lines"]}
    assert lines["doors"]["cost"] == 900.0 and bom["totals"] == {"USD": 900.0}
    # Sin precio: todo salvo los portones y los grilletes (opcionales).
    assert bom["missing_prices"] == len(bom["lines"]) - 2
    # Parámetros de componentes: booleano sólo en campos booleanos; portón del catálogo nuevo.
    body = {"params": {"generic_only": True, "warp_id": "wire_6x24_fc_16mm"}}
    r = client.post("/design/bom", json=body)
    assert r.status_code == 200
    warps = next(ln for ln in r.json()["lines"] if ln["key"] == "warps")
    assert warps["component_id"] == "wire_6x24_fc_16mm"
    assert client.post("/design", json={"params": {"depth_m": True}}).status_code == 422
    r = client.post("/design", json={"vessel": "fao_a3_180hp", "door": "door_flat_200hp"})
    assert r.status_code == 200 and r.json()["case"]["door"] == "door_flat_200hp"
    assert client.post("/design", json={"door": "no_door"}).status_code == 404


def test_optimize_components_endpoint() -> None:
    body = {"net": "fao_wb_bt2p_60hp", "params": {"generic_only": True}, "max_doors": 3}
    r = client.post("/optimize/components", json=body)
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["feasible"] and out["best"]["generic"]
    assert out["best"]["components"]["warp"] is not None
    assert out["best"]["bom"]["lines"]
    assert len(out["candidates"]["door"]) == 3
    bad = client.post("/optimize/components", json={**body, "objective": "speed"})
    assert bad.status_code == 422
    missing = client.post("/optimize/components", json={**body, "doors": ["no_door"]})
    assert missing.status_code == 404


def test_inline_user_components_enter_only_that_request() -> None:
    wire = {
        "kind": "wire",
        "id": "user_wire_puerto",
        "name": "Cable 6x19 del puerto",
        "construction": "6x19",
        "diameter_mm": 14,
        "weight_kg_per_m": 0.72,
        "breaking_load_t": 10.5,
        "price": {"value": 1.5, "currency": "USD", "unit": "m", "date": "2026-10", "source": "u"},
    }
    body = {"params": {"warp_id": "user_wire_puerto"}, "components": [wire]}
    r = client.post("/design/bom", json=body)
    assert r.status_code == 200, r.text
    warps = next(ln for ln in r.json()["lines"] if ln["key"] == "warps")
    assert warps["component_id"] == "user_wire_puerto" and warps["cost"] is not None
    # Sin el aporte en el pedido, el id no existe.
    assert client.post("/design/bom", json={"params": body["params"]}).status_code == 422
    bad = client.post("/design", json={"components": [{"kind": "wire", "id": "x", "name": "x"}]})
    assert bad.status_code == 422


def _fleet_file() -> dict[str, str]:
    import base64

    r = client.get("/batch/template?kind=fleet&format=xlsx")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/vnd")
    return {
        "filename": "flota.xlsx",
        "content": base64.b64encode(r.content).decode(),
        "encoding": "base64",
    }


def test_batch_endpoints() -> None:
    f = _fleet_file()
    p = client.post("/batch/parse", json={"file": f, "mode": "fleet"}).json()
    assert p["size"] == 3 and p["issues"] == [] and p["estimated_s"] < p["max_s"]
    body = {"file": f, "mode": "fleet", "net": "fao_wb_bt2p_60hp", "assemble": False}
    r = client.post("/batch/run", json=body)
    assert r.status_code == 200, r.text
    out = r.json()
    assert len(out["rows"]) == 3 and out["counts"]["error"] == 0
    first = out["rows"][0]
    assert first["summary"]["s"] > 0 and first["detail"]["net"]["panels"]
    csv_r = client.post("/batch/export?format=csv", json=body)
    assert csv_r.status_code == 200 and csv_r.text.startswith("Fila;Nombre;Estado")
    assert "lote.csv" in csv_r.headers["content-disposition"]
    tpl = client.get("/batch/template?kind=cases&format=csv")
    assert tpl.status_code == 200 and tpl.text.startswith("caso;red")
    # sin red elegida, archivo dañado, lote demasiado caro
    assert client.post("/batch/run", json={"file": f, "mode": "fleet"}).status_code == 422
    bad = {"filename": "x.xlsx", "content": "aGVsbG8=", "encoding": "base64"}
    assert client.post("/batch/parse", json={"file": bad, "mode": "fleet"}).status_code == 422
    assert client.get("/batch/template?kind=otra").status_code == 422


def test_batch_cost_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRAWLKIT_MAX_BATCH_SECONDS", "0.5")
    body = {"file": _fleet_file(), "mode": "fleet", "net": "fao_wb_bt2p_60hp"}
    r = client.post("/batch/run", json=body)
    assert r.status_code == 422 and "tramos" in r.json()["detail"]
