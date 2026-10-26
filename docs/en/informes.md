# Reports and plans

From a design case, `trawlkit` generates the plan of the net and a complete report.

## From the command line

```bash
# Complete report: HTML, PDF, XLSX and SVG sheets
uv run trawlkit report fao_a3_standard --modified fao_a3_modified \
    --vessel fao_a3_150hp --out informe/

# The same report in English (the global --lang option goes before the command)
uv run trawlkit --lang en report fao_a3_standard --modified fao_a3_modified \
    --vessel fao_a3_150hp --out report/

# Only some formats
uv run trawlkit report fao_a3_standard --format html,xlsx --out informe/

# With the optimization sections (area, volume or energy) and shape simulation
uv run trawlkit report fao_a3_standard --vessel fao_a3_150hp --out informe/ \
    --optimize area --simulate 2,3 --sim-resolution 6

# Plan on its own: technical sheet (sheet) or true scale (scale), standard or modified net
uv run trawlkit plan fao_a3_standard --view sheet --out lamina.svg
uv run trawlkit plan fao_a3_standard --modified fao_a3_modified \
    --view scale --variant mod --out escala_mod.svg
```

The PDF requires the `report` extra (`pip install "trawlkit[report]"`) and the system Pango
libraries used by WeasyPrint.

## From Python

```python
from trawlkit import DesignCase, run
from trawlkit.drawing import net_scale_svg, net_sheet_svg
from trawlkit.report.build import build_report

result = run(case)  # see docs/motor.md to build the case
svg = net_sheet_svg(result, "std")  # A3 sheet
paths = build_report(result, "informe/", formats=("html", "pdf", "xlsx", "svg"))

# Optional sections: optimization (chapter 20) and shape simulation (chapter 21)
from trawlkit.optimize import optimise
from trawlkit.sim import sweep

build_report(
    result,
    "informe/",
    optimization=optimise(case, objective="area", refine=False),
    simulation=sweep(result, [2.0, 3.0], resolution=6),
)
```

In Python the language of the report follows `trawlkit.i18n.set_lang("en")`, the same switch
that `--lang en` sets on the command line.

`--optimize` runs `optimise` with a 13 × 11 grid without refinement (a few seconds) and
`--simulate` runs `sweep` at the given speeds (`--sim-resolution`, 6 by default: ≈ 4 s per
speed).

## What it contains

| Output | Content |
|---|---|
| `informe.html` | Self-contained page (no connection or JavaScript needed), light and dark mode: cover, summary with indicators, sheets, true scale, charts, construction and materials (bill of materials and guide for the net loft, {doc}`36_construccion`), tables, errata, notes, methodology and credits. |
| `informe.pdf` | The same HTML printed: A4 portrait, wide tables in A4 landscape and sheets in A3 landscape. |
| `informe.xlsx` | One sheet per table (summary, panels, power, drag, demand, rigging, floats and ballast, warp, speed window, errata, bill of materials and the tables of the construction guide) plus “Caso” [case] with all the parameters and “Notas” [notes]. |
| Optimization (optional) | “Optimization” section of the HTML/PDF: best design, constraints (OK/NO), scale × speed feasibility map, Pareto front and its table; sheets `optimizacion`, `optimizacion_restricciones`, `optimizacion_pareto` and `optimizacion_malla` of the XLSX. |
| Simulation (optional) | “Simulation” section: simulation / engine / DynamiT table (standard FAO A-3 net) with percentage differences and plan, profile and front views of the first three speeds; sheets `simulacion` and `simulacion_detalle`. |
| `plano_estandar.svg`, `plano_modificada.svg` | A3 technical sheet like the 2014 plans: upper and lower panels, meshes per edge, cut codes, side tables, ropes, area and weight per panel, rigging diagram and title block. |
| `plano_escala_*.svg` | True-scale view in metres with a 1 m grid, dimensions per panel, graphic scale, stretched and mounted lengths and steps where the hanging ratio changes. |

## Charts

1. Available pull by method against total drag (standard and modified), with the viable speed
   window shaded and the maximum speed marked.
2. Net drag by the 13 methods, with the design method (Aberdeen demersal) highlighted.
3. Breakdown of total drag at 3.5 knots: net, floats, warps and otter boards.
4. Wing-end spread and Fridman vertical opening as a function of speed.

## Differences from the 2014 plans

The sheets come from the model, they are not copied from the drawing. That is why some values
differ from the original plan: in corrected mode the footrope measures 33.39 m, the solid area
38.75 m², the sweeps 25 m, the buoyancy 36 kgf and the selected warp is 13 mm. The drawing does
not invent data that the model does not have (for example, the diameter of sweeps and bridles).

Generated examples: folder `examples/fao_a3/` of the repository.
