"""Unitarios de `trawlkit.model`: DesignCase, nota de red única, summary(), CLI y humo 180 HP."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.golden_utils import assert_close, golden
from trawlkit import DesignCase, DesignResult, run
from trawlkit.cli import app
from trawlkit.compat import Compat
from trawlkit.io import PropellerType, load_doors, load_net, load_vessels
from trawlkit.model import DEFAULT_SPEEDS_KN


def _parts() -> tuple:  # type: ignore[type-arg]
    vessels = load_vessels().vessels
    return load_net("fao_a3_standard"), vessels[0], vessels[1], load_doors().doors[0]


def test_defaults_match_excel_inputs() -> None:
    net, v150, _, door = _parts()
    case = DesignCase(net, v150, door)
    assert case.speeds_kn == DEFAULT_SPEEDS_KN
    assert case.compat is Compat.CORRECTED
    assert case.spread_per_m == 2.65 and case.bridle_angle_deg == 4.8
    assert case.dan_leno_m == 0.6 and case.sweeps_m == 25 and case.door_attack_angle_deg == 32
    assert case.warp_safety_factor == 4 and case.rob_share == 0.20
    assert case.working_depth_m == 40 and case.gallows_spacing_m == 2.5 and case.hull_depth_m == 1.8
    assert case.vessel_class == (v150,)
    assert case.warp_sizing_nhp_hp == 150
    assert case.speed_index(3.5) == 5
    doc = json.loads(json.dumps(case.to_dict()))
    assert doc["net"] == "fao_a3_standard" and doc["net_modified"] is None
    assert doc["compat"] == "corrected" and doc["ft_propeller"] == "fixed_pitch"


def test_validation() -> None:
    net, v150, v180, door = _parts()
    with pytest.raises(ValueError, match="speeds_kn"):
        DesignCase(net, v150, door, speeds_kn=(2.0, 1.0))
    with pytest.raises(ValueError, match="rob_share"):
        DesignCase(net, v150, door, rob_share=1.5)
    with pytest.raises(ValueError, match="33"):
        DesignCase(net, v150, door, door_attack_angle_deg=33)
    with pytest.raises(ValueError, match="profundidad"):
        DesignCase(net.model_copy(update={"species": None}), v150, door)
    with pytest.raises(ValueError, match="pastecas"):
        DesignCase(net, v150.model_copy(update={"beam_m": None}), door)
    with pytest.raises(ValueError, match="KF"):
        DesignCase(net, v150, door, ft_propeller=PropellerType.VARIABLE_PITCH)
    with pytest.raises(ValueError, match="warp_design_speed_kn"):
        DesignCase(net, v150, door, warp_design_speed_kn=3.3)
    with pytest.raises(ValueError, match="variante"):
        run(DesignCase(net, v150, door)).drag.rn.variant("x")
    # La clase no repite buques y ordena por BHP; el cable se dimensiona con el mayor.
    case = DesignCase(net, v180, door, class_vessels=(v150, v180))
    assert [v.id for v in case.vessel_class] == ["fao_a3_150hp", "fao_a3_180hp"]
    assert case.warp_sizing_nhp_hp == 180
    assert DesignCase(net, v150, door, warp_nhp_hp=200).warp_sizing_nhp_hp == 200


def test_single_net_fallback_note() -> None:
    net, v150, _, door = _parts()
    r = run(DesignCase(net, v150, door, compat=Compat.EXCEL))
    assert any("net_modified no indicado" in n for n in r.notes)
    assert r.geometry.mod is r.geometry.std
    assert r.dimensions.mod.net_id == "fao_a3_standard"
    assert_close(r.drag.rn.mod, r.drag.rn.std)
    # Sin el buque de 180 HP, Ffz promedia sólo la flotación del de 150 (Fridman y Prado).
    assert_close(
        r.spread.vertical.flotation_total_kgf,
        (r.floats.fridman_average_kgf + r.floats.prado_kgf) / 2,
    )
    # … y el cable se dimensiona con 150 HP (Águila 11.25 mm → LOOKUP 9.5 mm en modo EXCEL).
    assert_close(r.warps.diameter_mm, golden("cables_de_remolque", "warp_diameter_aguila_150_mm"))
    assert r.warps.selection.diameter_mm == 9.5


def test_summary_content_and_types() -> None:
    net, v150, _, door = _parts()
    s = run(DesignCase(net, v150, door)).summary()
    assert s["net_id"] == "fao_a3_standard" and s["compat"] == "corrected"
    assert all(isinstance(v, float | int | str) or v is None for v in s.values())
    assert s["float_count"] == 12 and s["warp_length_m"] == 200
    assert isinstance(s["max_speed_kn"], float)


def test_smoke_modified_net_180hp() -> None:
    net, v150, v180, door = _parts()
    r: DesignResult = run(
        DesignCase(net, v180, door, net_modified=load_net("fao_a3_modified"), class_vessels=(v150,))
    )
    assert r.case.vessel.bhp == 180 and r.geometry.mod.net_id == "fao_a3_modified"
    assert r.geometry.mod.solid_surface_m2 != r.geometry.std.solid_surface_m2
    assert r.floats.fridman_average_kgf > 36  # 180 HP: 39.9 kgf en el libro
    assert r.ballast.limits.max_kg >= r.ballast.limits.min_kg
    assert r.warps.selection.satisfies_breaking_load
    w = r.performance.design
    assert w.max_speed_kn is not None and w.feasible[0]
    json.dumps(r.to_dict())


def test_cli_run(tmp_path: Path) -> None:
    runner = CliRunner()
    out = tmp_path / "caso.json"
    result = runner.invoke(
        app,
        [
            "run",
            "fao_a3_standard",
            "--vessel",
            "fao_a3_150hp",
            "--modified",
            "fao_a3_modified",
            "--class-vessel",
            "fao_a3_180hp",
            "--compat",
            "excel",
            "--json",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "| Lima |" in result.output and "28.698" in result.output
    assert "Cable seleccionado" in result.output
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["warp_diameter_mm"] == 12
    assert doc["result"]["case"]["compat"] == "excel"
    bad = runner.invoke(app, ["run", "fao_a3_standard", "--vessel", "nope"])
    assert bad.exit_code != 0
    assert runner.invoke(app, ["version"]).exit_code == 0
