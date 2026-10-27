"""Planos de red en SVG: lámina técnica y vista a escala real."""

from trawlkit.drawing.layout import NetLayout, PanelShape, layout_net
from trawlkit.drawing.rig import rig_plan_svg
from trawlkit.drawing.scale import net_scale_svg
from trawlkit.drawing.sheet import fmt_es, net_sheet_svg

__all__ = [
    "NetLayout",
    "PanelShape",
    "fmt_es",
    "layout_net",
    "net_scale_svg",
    "net_sheet_svg",
    "rig_plan_svg",
]
