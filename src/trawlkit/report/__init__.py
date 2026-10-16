"""Informes del caso de diseño: tablas, gráficos SVG, HTML, PDF y XLSX.

Uso::

    from trawlkit.report import build_report
    build_report(result, "salida/")  # informe.html, informe.pdf, informe.xlsx, planos SVG

PDF y XLSX necesitan el extra ``report`` (``pip install trawlkit[report]``).
"""

from trawlkit.report.build import FORMATS, SVG_FILES, build_report
from trawlkit.report.charts import (
    all_charts,
    drag_breakdown_chart,
    drag_methods_chart,
    spread_chart,
    towing_chart,
)
from trawlkit.report.html import default_sheet_svgs, placeholder_svg, render_html
from trawlkit.report.pdf import html_to_pdf
from trawlkit.report.tables import (
    Column,
    Table,
    all_tables,
    demand_table,
    drag_table,
    errata_table,
    floats_ballast_table,
    notes_table,
    panels_table,
    power_table,
    rigging_table,
    speed_window_table,
    summary_table,
    warp_table,
)
from trawlkit.report.xlsx import write_xlsx

__all__ = [
    "FORMATS",
    "SVG_FILES",
    "Column",
    "Table",
    "all_charts",
    "all_tables",
    "build_report",
    "default_sheet_svgs",
    "demand_table",
    "drag_breakdown_chart",
    "drag_methods_chart",
    "drag_table",
    "errata_table",
    "floats_ballast_table",
    "html_to_pdf",
    "notes_table",
    "panels_table",
    "placeholder_svg",
    "power_table",
    "render_html",
    "rigging_table",
    "speed_window_table",
    "spread_chart",
    "summary_table",
    "towing_chart",
    "warp_table",
    "write_xlsx",
]
