import xml.etree.ElementTree as ET

import pytest

from trawlkit.drawing import svg
from trawlkit.report.labels import fmt, label, summary_markdown
from trawlkit.report.tables import Column, Table


def test_document_is_valid_xml_and_escapes_text() -> None:
    doc = svg.document(
        100,
        50,
        [
            svg.polygon([(0, 0), (10, 0), (5, 8)], id_="A"),
            svg.text((5, 5), "Ø <hilo> & 'malla'", cls="small mid"),
            svg.line((0, 0), (1.234567, 2)),
            svg.group(svg.circle((3, 3), 1), cls="g", transform="translate(1 2)"),
        ],
        title_text="prueba",
    )
    root = ET.fromstring(doc.split("\n", 1)[1])
    assert root.tag.endswith("svg")
    assert "Ø <hilo> & 'malla'" in "".join(root.itertext())
    assert 'x2="1.23"' in doc


def test_table_validates_rows_and_column_lookup() -> None:
    cols = (Column("v", "Velocidad", "kn"), Column("rn", "RN", "kgf"))
    t = Table("rn", "Resistencia", cols, ((1.0, 422.4), (1.5, 631.5)))
    assert t.column("rn") == [422.4, 631.5]
    assert cols[0].heading == "Velocidad [kn]"
    assert t.to_dict()["rows"][1] == [1.5, 631.5]
    with pytest.raises(ValueError):
        Table("x", "x", cols, ((1.0,),))


def test_labels_moved_from_cli() -> None:
    assert label("headrope_m") == ("Lima", "m")
    assert label("rn_std_3_5kn_kgf")[0] == "RN estándar a 3.5kn"
    assert fmt(None) == "—" and fmt(12.0) == "12"
    assert "| Lima | 28.698 | m |" in summary_markdown({"headrope_m": 28.698})
