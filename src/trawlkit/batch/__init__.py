"""Carga masiva, cálculo por lotes y proyección de redes a buques (Fase 14).

Uso::

    from trawlkit.batch import read_input, run_input, result_xlsx
    inp = read_input(open("flota.xlsx", "rb").read(), "flota.xlsx", "fleet")
    res = run_input(inp, net="fao_wb_bt2p_60hp")
    open("resultados.xlsx", "wb").write(result_xlsx(res))
"""

from trawlkit.batch.export import result_xlsx, tables, template, to_csv, to_xlsx
from trawlkit.batch.fleet import Fleet, FleetVessel, fleet_vessel, read_fleet
from trawlkit.batch.nets import LoadedNet, net_rows, read_nets
from trawlkit.batch.project import Projection, ProjectOptions, project_net
from trawlkit.batch.run import (
    MODES,
    BatchInput,
    BatchResult,
    BatchRow,
    estimate_cost_s,
    read_input,
    run_cases,
    run_fleet,
    run_input,
    run_nets,
)
from trawlkit.batch.sheets import RowIssue, Sheet, read_book

__all__ = [
    "MODES",
    "BatchInput",
    "BatchResult",
    "BatchRow",
    "Fleet",
    "FleetVessel",
    "LoadedNet",
    "ProjectOptions",
    "Projection",
    "RowIssue",
    "Sheet",
    "estimate_cost_s",
    "fleet_vessel",
    "net_rows",
    "project_net",
    "read_book",
    "read_fleet",
    "read_input",
    "read_nets",
    "result_xlsx",
    "run_cases",
    "run_fleet",
    "run_input",
    "run_nets",
    "tables",
    "template",
    "to_csv",
    "to_xlsx",
]
