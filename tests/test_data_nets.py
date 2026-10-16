"""Los YAML de src/trawlkit/data/ generados por tools/extract/nets.py cargan y tienen la
estructura esperada."""

import pytest

from trawlkit.io import Section, load_net, load_vessels


@pytest.fixture(scope="module")
def standard():
    return load_net("fao_a3_standard")


@pytest.fixture(scope="module")
def modified():
    return load_net("fao_a3_modified")


def test_both_nets_load(standard, modified) -> None:
    assert standard.id == "fao_a3_standard"
    assert modified.id == "fao_a3_modified"
    assert modified.variant_of == "fao_a3_standard"
    assert standard.species is not None and standard.species.name == "Langostilla"


def test_standard_has_panels_a_to_j(standard) -> None:
    assert [p.id for p in standard.panels] == list("ABCDEFGHIJ")


def test_modified_replaces_codends_by_i_prime(standard, modified) -> None:
    assert [p.id for p in modified.panels] == [*"ABCDEFGH", "I'"]
    common_std = [p for p in standard.panels if p.id not in {"I", "J"}]
    common_mod = [p for p in modified.panels if p.id != "I'"]
    assert common_std == common_mod


def test_codend_mesh_40_vs_30(standard, modified) -> None:
    std_codends = [p for p in standard.panels if p.section is Section.CODEND]
    mod_codends = [p for p in modified.panels if p.section is Section.CODEND]
    assert {p.mesh_mm for p in std_codends} == {40.0}
    assert {p.mesh_mm for p in mod_codends} == {30.0}
    (i_prime,) = mod_codends
    assert (i_prime.meshes_top, i_prime.meshes_bottom, i_prime.meshes_depth) == (139, 139, 300)
    assert i_prime.count == 2


def test_panel_counts_and_source_cells(standard) -> None:
    counts = {p.id: p.count for p in standard.panels}
    assert counts == {
        "A": 2,
        "B": 2,
        "C": 2,
        "D": 2,
        "E": 1,
        "F": 2,
        "G": 2,
        "H": 2,
        "I": 1,
        "J": 1,
    }
    for p in standard.panels:
        assert p.source_cells and p.source_cells["meshes_depth"].startswith(
            "Paños de red y cortes!"
        )


def test_edge_convention_follows_plans(standard, modified) -> None:
    edges = {p.id: (p.meshes_top, p.meshes_bottom) for p in standard.panels}
    assert edges["A"] == (3, 57)
    assert edges["B"] == (3, 57)
    assert edges["C"] == (57, 117)
    assert edges["D"] == (57, 97)
    assert edges["E"] == (412, 372)
    assert edges["F"] == (129, 143)
    assert edges["G"] == (372, 162)
    assert edges["H"] == (243, 113)
    assert edges["I"] == edges["J"] == (113, 113)
    a = next(p for p in standard.panels if p.id == "A")
    assert (a.meshes_a, a.meshes_b) == (57, 3)
    assert a.source_cells["meshes_top"] == a.source_cells["meshes_b"]
    i_prime = next(p for p in modified.panels if p.id == "I'")
    assert (i_prime.meshes_top, i_prime.meshes_bottom) == (139, 139)


def test_rigging(standard) -> None:
    assert standard.headrope is not None and standard.headrope.length_m == pytest.approx(28.698)
    assert standard.footrope is not None and standard.footrope.length_m == pytest.approx(33.3)
    assert standard.floats is not None and standard.floats.count == 12
    assert standard.floats.total_buoyancy_kgf == 36
    assert standard.ballast_kg == 42


def test_vessels_catalogue() -> None:
    cat = load_vessels()
    assert sorted(v.bhp for v in cat.vessels) == [150.0, 180.0]
    assert {v.propeller.value for v in cat.vessels} == {"fixed_pitch"}
