# Architecture of the `trawlkit` engine

`trawlkit` reimplements, module by module, the thirteen sheets of the workbook
`Calculos_Red_FAO_A3.xlsx`. Each module contains pure functions (one per block of formulas, with
the representative cell in the docstring) and a result *dataclass*; `trawlkit.model.run` chains
them in the order in which the workbook resolves its dependencies and returns a `DesignResult`
with one stage per sheet.

## Modules and sheets

| Module | Workbook sheet(s) | What it computes |
|---|---|---|
| `trawlkit.io` | Especie Blanco, Tipo de buques [target species, vessel types], catalogues | Pydantic schema (`NetSpec`, `Vessel`, `Door`, `Catalogue`) and loading of `src/trawlkit/data/*.yaml` |
| `trawlkit.vessel`, `trawlkit.power` | Potenc disponible para arrastre, Potencia Disponible Arrastre OK [power available for towing] | Energy split (Fridman); available pull FT by Fridman, Prado-Dremière, Koyama, Nomura and Hamuro; summary `PotOK!L11:O19` |
| `trawlkit.netting`, `trawlkit.materials` | Paños de red y cortes, Tablas de Referencias [netting panels and cuts, reference tables] | Stretched lengths, netting panel areas, cuts (ratio, code, angle), twine density |
| `trawlkit.net` | Mecánica de la Red [net mechanics] (rows 6-113) | Filtration index d/l, solid and working areas, solidity, weights |
| `trawlkit.dimensions` | Dimensiones de la Red [net dimensions] | Headrope and footrope (Martini), lengths, circumferences, length factor, Nomura proportions |
| `trawlkit.drag` | Resistencia de la RED [net drag] | Thirteen net drag methods; Aberdeen demersal is the design RN |
| `trawlkit.rigging.doors`, `.bridles` | Portones y aparejamiento [otter boards and rigging] | Door spread, polar, ROB, forces, required area; bridles, sweeps, crowfoot, δ |
| `trawlkit.rigging.spread` | Mecánica de la Red (rows 162-282) | Fridman wing-end spread (DPA), geometric and by cutting angle; horizontal and vertical opening |
| `trawlkit.rigging.floats`, `.ballast`, `.ropes` | Flotación y Lastre, Cables Y Cabulleria [buoyancy and ballast, warps and ropes] | Buoyancy (Koyama, Prado, Fridman), floats and their drag; ballast and its distribution; ropes |
| `trawlkit.rigging.warps` | Cables de Remolque, Cables Y Cabulleria [warps, warps and ropes] | Warp angles, diameter, CD, Rw, total drag, weight, loads and selection |
| `trawlkit.performance` | (comparison implicit in the workbook) | Viable speed window FT(v) ≥ R(v) |
| `trawlkit.compat` | — | `EXCEL`/`CORRECTED` modes and `ERRATA` register |
| `trawlkit.model` | all | `DesignCase`, `DesignResult`, `run` |

Around that core, which reproduces the workbook, grew modules that the Excel did not have:

| Module | What it does | Chapter |
|---|---|---|
| `trawlkit.optimize` | Optimal net scale and speed under constraints; optimal rigging with the components catalogue (`optimize.components`) | {doc}`20_optimizacion`, {doc}`34_componentes` |
| `trawlkit.sim` | Equilibrium shape of the net (netting elements, Morison, FIRE relaxation), haul scenario, mesh state, uncertainty and calibration | {doc}`21_simulacion` to {doc}`25_incertidumbre_calibracion` |
| `trawlkit.selectivity`, `trawlkit.sensors` | Lengths retained per species according to the deformed mesh; reading of sensor logs | {doc}`24_malla_selectividad`, {doc}`25_incertidumbre_calibracion` |
| `trawlkit.catalog`, `.topology`, `.netcheck`, `.provenance` | Design case of each net of the FAO catalogue, topologies other than the A-3, consistency validator and value-by-value provenance | {doc}`33_catalogo_fao` |
| `trawlkit.rigging.multirig`, `trawlkit.drawing.rig` | Outrigger, twin and beam rigs: `RigStage` (nets, otter boards, warps, bridle, clump, beam), swept width and rig diagram | {doc}`26_aparejos_dobles_y_vara` |
| `trawlkit.components`, `trawlkit.cost` | Components catalogue with generic equivalents; bill of materials and indicative cost | {doc}`34_componentes` |
| `trawlkit.construction` | Construction guide: cutting sheet, netting to buy, joinings, mounting on the ropes, floats, ballast and rope cuts | {doc}`36_construccion` |
| `trawlkit.economics` | Economics of the operation: fuel, catch, costs by item, margin and break-even price by speed; comparison of nets with savings and payback | {doc}`37_economia` |
| `trawlkit.teaching` | Teaching mode: exercise bank with seeded data and grading with tolerance (the answers come from the same engine), guided labs checked on the student's case | “Exercises” section of the chapters |
| `trawlkit.batch` | Fleet, net and case spreadsheets; projection of a net onto each vessel; export | {doc}`35_lotes_proyeccion` |
| `trawlkit.drawing`, `trawlkit.report` | SVG plan (sheet and true scale), charts and HTML, PDF and XLSX reports | {doc}`informes` |
| `trawlkit.api` | FastAPI API (`app`, `service`, `schemas`) and `api.offline`, the same service without a server that the app runs in Pyodide | {doc}`api`, {doc}`web` |

## Order of the stages

The dependency graph between sheets (see `legacy/formula_map.md`) forces an order different from
that of the tabs. `run` goes through it like this:

```
geometry      Mecánica de la Red        d/l, Ss, St, weights (standard and modified columns)
    │
dimensions    Dimensiones de la Red     ropes, lengths, circumference, cutting angle
    │
power         Potencia disponible       energy split, pull curves, Fridman FT per vessel
    │
drag (1)      Resistencia de la RED     13 methods → design RN (Aberdeen demersal); Dickson as NaN
    │
rigging       Mec!B175:F186, Port!A33   Ls = depth × tabulated ratio; LR·U2; headrope sag
    │                                   (0.216·L); bridles to one point (Suzuki AV); crowfoot
doors         Portones y aparejamiento  Ds = (2.65 − blocks)·Ls + blocks; polar at 32°; ROB = 20 % FT;
    │                                   forces ½·ρ/g·C·S·v²; required area; Pφ; moments
floats        Flotación y Lastre        Koyama, Prado and Fridman per vessel of the class → Ffz (Mec!O261);
    │                                   catalogue floats, distribution, drag RB
spread        Mec!B162:P282, Dim!F61    Fridman DPA (Edx/Edy), geometric, by cut → AH;
    │                                   AV by %, Suzuki, Martini and Baranov–Fridman (uses Ffz)
drag (2)      Res!C282:F290             Dickson is filled in with AH = Mec!P164:P172 and AV = O272:O280
    │
bridles       Port!A63:E110             sweeps (Dremière, Martini), angle of attack δ
    │
ballast       Flot!D153:I245            Koyama, Prado, Fridman (F1' + F2' − W footrope), limits, split
    │
warps         Cables de Remolque        angles δ1-δ3, Ø (EHP, Águila), CD, Rw, total R (+ROB in
    │                                   corrected mode), weight, loads ×4, selection from the catalogue
multirig                                outrigger, twin or beam (Phase 19.5): all the nets, otter boards,
    │                                   warps, bridle, clump or beam; warps by what they tow
performance                             FT (FP and CP+N) against R(v) → maximum towable speed
```

Two details explain the order: the workbook is circular between Dickson and the Fridman openings
(which use the Aberdeen RN); since Dickson does not feed Aberdeen, the drag table is evaluated
twice. And the Fridman AV (vertical opening) needs the total buoyancy `Ffz`, which averages the 150 and 180 HP blocks
of *Flotación y Lastre*, so buoyancy is computed before the openings.

Every number that the workbook has typed in by hand is a field of `DesignCase` with the cell in a
comment (`spread_per_m` = `Port!D7`, `bridle_angle_deg` = `Port!F39`, `sweeps_m` = `Dim!F65`,
`catenary_ratio` = `Mec!O266`, `warp_safety_factor` = `Rem!D271`, …). The couplings between the
two vessels of the workbook are modelled with `class_vessels` (averaged buoyancy and NHP of the
warp) and those between the two nets with `net_modified` (column G).

## Compatibility modes

Every function affected by an erratum of the workbook accepts `compat`:

* `Compat.EXCEL` reproduces the workbook's number, erratum included. It is the mode with which
  the golden tests validate the migration.
* `Compat.CORRECTED` (default) applies the correct formula. `tests/test_corrected_mode.py`
  checks, at the level of the complete case, that each switch moves the result in the expected
  direction (Ss 38.75 instead of 40.90 m², footrope 33.389 m, smaller Hamuro and Reid, total drag
  with ROB, 13 mm warp instead of 12, float Reynolds number ÷ π·D, clean average of drags) and
  that what is not affected matches between modes.

The complete table, with the function and the test of each erratum, is in [Errata](erratas.md).

## How to run a case

In Python:

```python
from trawlkit import Compat, DesignCase, run
from trawlkit.io import load_doors, load_net, load_vessels

vessels = {v.id: v for v in load_vessels().vessels}
case = DesignCase(
    net=load_net("fao_a3_standard"),
    net_modified=load_net("fao_a3_modified"),
    vessel=vessels["fao_a3_150hp"],
    class_vessels=(vessels["fao_a3_180hp"],),
    door=load_doors().doors[0],
    compat=Compat.EXCEL,  # or Compat.CORRECTED (default)
)
result = run(case)
result.summary()  # 'Dimensiones de la Red'!F45:F71 + RN, ROB, floats, ballast, warp, max v
result.drag.rn.std  # design RN [kgf] at 1…5 kn
result.performance.design.max_speed_kn
result.to_dict()  # JSON-serializable
```

From the command line:

```bash
uv run trawlkit run fao_a3_standard --vessel fao_a3_150hp --door fao_flat_wood_a3 \
    --modified fao_a3_modified --class-vessel fao_a3_180hp --compat excel --json caso.json
```

prints the Markdown table of the summary (labels in Spanish, with units), the notes of the run
and, with `--json`, writes `summary()` and `to_dict()`. The global `--lang` option switches the
labels and notes to English:

```bash
uv run trawlkit --lang en run fao_a3_standard --vessel fao_a3_150hp --door fao_flat_wood_a3 \
    --modified fao_a3_modified --class-vessel fao_a3_180hp --compat excel --json caso.json
```

### Many cases: batches and fleets

`trawlkit.batch` ({doc}`35_lotes_proyeccion`) reads fleet, net or case spreadsheets and computes
everything at once; `project_net` projects a net onto another vessel (power similarity and
refinement):

```python
from trawlkit.batch import fleet_vessel, project_net, read_input, result_xlsx, run_input

p = project_net("fao_wb_bt2p_60hp", fleet_vessel({"name": "My vessel", "bhp": 120}))
p.s0, p.s, p.summary()["speed_kn"], p.net  # similarity scale, final scale, scaled net

inp = read_input(open("flota.xlsx", "rb").read(), "flota.xlsx", "fleet")
res = run_input(inp, net="fao_wb_bt2p_60hp")
open("lote.xlsx", "wb").write(result_xlsx(res))
```

```bash
uv run trawlkit batch --template flota.xlsx
uv run trawlkit batch flota.xlsx --net fao_wb_bt2p_60hp -o lote.pdf
uv run trawlkit --lang en batch flota.xlsx --net fao_wb_bt2p_60hp -o lote.pdf  # sheets in English
```

## Validation with the reference values

`tools/extract_excel.py` dumps the cached values of the workbook into `tests/golden/*.json` (one
JSON per sheet, stable `snake_case` keys, `static` and `coerced_from_text` marks). There are three
levels of tests:

1. **Per function** (`tests/test_<module>.py`): each block of formulas is fed with the golden
   inputs of its preceding cells and compared with `rtol = 1e-6` in `EXCEL` mode.
2. **End to end** (`tests/test_case_fao_a3.py`): `run` on the standard + modified net for the
   150 and 180 BHP vessels, with no intermediate inputs, against ~120 keys of the eight
   calculation sheets, also at `rtol = 1e-6` (the engine reproduces exactly the `MID()`
   truncation of the footrope, so the `1e-3` tolerance is not needed).
3. **Corrected mode** (`tests/test_corrected_mode.py`): direction of each erratum at the level of
   the result and equality of what is not affected.
