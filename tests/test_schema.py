import pytest
from pydantic import ValidationError

from trawlkit.io import NetSpec, Panel, Plane, PropellerType, Section, Vessel


def _panel(**kw):
    base = dict(
        id="A",
        plane=Plane.UPPER,
        section=Section.WING_TIP,
        mesh_mm=80,
        twine_diameter_mm=1.37,
        meshes_top=3,
        meshes_bottom=57,
        meshes_depth=36,
    )
    base.update(kw)
    return Panel(**base)


def test_panel_defaults() -> None:
    p = _panel()
    assert p.material == "PA"
    assert p.count == 1
    assert p.hanging_ratio is None


def test_panel_rejects_bad_values() -> None:
    with pytest.raises(ValidationError):
        _panel(mesh_mm=0)
    with pytest.raises(ValidationError):
        _panel(hanging_ratio=1.5)
    with pytest.raises(ValidationError):
        _panel(plane="diagonal")


def test_net_spec_minimal() -> None:
    net = NetSpec(id="x", name="X", panels=[_panel()])
    assert net.panels[0].id == "A"
    assert net.notes == []


def test_vessel_enum_from_string() -> None:
    v = Vessel.model_validate({"id": "v", "bhp": 150, "propeller": "variable_pitch_nozzle"})
    assert v.propeller is PropellerType.VARIABLE_PITCH_NOZZLE
    with pytest.raises(ValidationError):
        Vessel.model_validate({"id": "v", "bhp": 0})
