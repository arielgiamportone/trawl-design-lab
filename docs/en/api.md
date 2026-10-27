# HTTP API

The API exposes the engine over HTTP. It is started with `uv run trawlkit serve` (port 8000) and
the interactive documentation is at `http://127.0.0.1:8000/docs`. The full contract is in
`web/openapi.json`; this page is generated from it.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check. |
| GET | `/catalog/nets` | Predefined nets (FAO A-3 and FAO catalogue) with family, rigging, power, source, validator and provenance coverage; `?status=published\|draft`. |
| GET | `/catalog/nets/{net_id}` | Complete specification of a predefined net (panels, ropes, floats). |
| GET | `/catalog/nets/{net_id}/provenance` | Provenance of each value of the net (document, figure, type and note). |
| GET | `/catalog/nets/{net_id}/check` | Consistency validator of the net (joins, mouth, cuts, selvedges). |
| GET | `/catalog/components` | Component types (netting, warps, ropes, otter boards, floats, chains) with number of items, generics and brands. |
| GET | `/catalog/components/{kind}` | Components of a type with their provenance; filters `brand` (repeatable), `region`, `generic`, `status`. |
| GET | `/catalog/components/{kind}/{item_id}` | One component with its remarks and its equivalent generic. |
| POST | `/components/check` | Validates a component entered by the user (schema and physical consistency). |
| POST | `/design/bom` | Bill of materials of the case (netting, ropes, sweeps, warp, floats, otter boards, ballast) with indicative cost from `prices` or the catalogue price; counts the lines without a price. |
| POST | `/optimize/components` | Rigging with catalogue components (otter board, warp, floats, twine) by `drag`, `efficiency` or `cost`, with alternatives and bill of materials; filters in `params` (`component_brands`, `component_region`, `generic_only`). |
| POST | `/batch/parse` | Reads a fleet, net or case spreadsheet (CSV as text or XLSX in base64): recognized rows, remarks per row and column, and estimated cost of the batch. |
| POST | `/batch/run` | Computes the batch: projects a net onto each vessel of the fleet (power-similarity scale, refined, speed and rigging), or computes uploaded cases or nets. Cost guard `TRAWLKIT_MAX_BATCH_SECONDS`. |
| POST | `/batch/export` | The batch as `csv` (summary), `xlsx` (summary, materials and one panel sheet per scaled net), `pdf` or `html` (sheet per vessel). |
| GET | `/batch/template` | Spreadsheet template (`kind`: `fleet`, `nets`, `cases`; `format`: `xlsx` with a help sheet, or `csv`). |
| POST | `/prices/parse` | Reads a user price list (CSV or XLSX; Phase 19.2): key (component or line id), price, currency, unit, date and source. |
| POST | `/prices/export` | Price list as CSV or XLSX (`format`), with the bill-of-materials lines without a price as a template. |
| GET | `/catalog/vessels` | Vessels of the catalogue. |
| GET | `/catalog/doors` | Otter boards of the catalogue with their CL/CD polar. |
| GET | `/catalog/door-polars` | Representative polar of each otter board type (Phase 19.3), with its source and the recommended angle of attack. |
| POST | `/doors/select` | Catalogue otter boards that reach the equivalent area of the case ($A_2 = A_1 C_{L1}/C_{L2}$ + 10 %, Seafish 1993), with weight, angle of attack and backstrops; filters `brands`, `region`, `generic_only`, `types`. |
| GET | `/catalog/fouling` | Fouling and clogging scenarios of the net (level per zone). |
| GET | `/catalog/species` | Species for selectivity, with the shape of their cross-section (TO BE VERIFIED). |
| GET | `/catalog/seabeds` | Seabed types with the friction of the ground gear and of the otter boards (nominal and range). |
| GET | `/params` | Design parameters that can be overridden in `DesignRequest.params`. |
| GET | `/errata` | Errata of the original Excel workbook. |
| POST | `/design` | Computes a complete design case. |
| POST | `/design/plan` | SVG plan of the case: technical sheet (`sheet`) or true scale (`scale`). |
| POST | `/design/layout` | 2D layout of the net (polygons per panel, in metres; `variant`, `mode` = `schematic` or `true_scale`) for the interactive editor. |
| POST | `/design/construction` | Construction guide for the net loft ({doc}`36_construccion`): cutting sheet per panel with the cycle of each cut, netting to buy, step-by-step joinings with the joining rule, mounting on the ropes (meshes per metre and hanging ratio), floats, ballast and rope cuts; `variant` and `eye_allowance_m` (allowance per eye splice). |
| POST | `/design/construction/export` | The guide as `pdf` or `html` (A4 for printing) or `xlsx` (one sheet per table). |
| POST | `/economics` | Economics of the operation ({doc}`37_economia`): per speed, fuel (towing, steaming and manoeuvres), catch, revenue, costs by item (fuel, lubricant, crew, net and gear, fishing trip, fixed), margin, cost per kg and break-even price; the speed of highest margin, that of lowest cost per kg and the year. Without prices, the amounts come out as `null` and `missing` says what is missing. |
| POST | `/economics/compare` | Compares nets or vessels with the same operating data: margin and fuel per year, savings against the first one and payback of the rigging. |
| GET | `/teaching/exercises` | Exercise bank of the teaching mode, filterable by `chapter`, `level` (`basico`, `intermedio`, `avanzado`) and `topic`. |
| GET | `/teaching/exercises/{id}?seed=` | One exercise with its data for the seed (0 = those of the book), without the answers. |
| POST | `/teaching/grade` | Grades the practice answers (numbers with a decimal comma or point, within the tolerance of each answer) and returns the solution and the explanation. |
| GET | `/teaching/labs`, `/teaching/labs/{id}` | Guided labs on the app: starting case, steps, where each one is done and its questions (without the answers). |
| POST | `/teaching/labs/check` | Checks a lab step on the student's case with facts computed by the engine and grades its questions. |
| — | `/classroom/…` | UTN Classroom (online only, with `DATABASE_URL`; see {doc}`despliegue`): sign-up with a course or invitation code, log-in with a *bearer* token, courses, students, assignments with exercises and labs from the bank (own data per student, attempts, dates and feedback immediately or at closing), submissions graded on the server, grade sheet (JSON, XLSX, CSV), printable guide per student and teacher review. `GET /classroom/status` says whether it is enabled. |
| POST | `/optimize` | Optimizes the net scale and the towing speed (grid + differential evolution). |
| POST | `/optimize/scaled-net` | Net scaled by `s` (same meshes and materials), to use the optimized design. |
| POST | `/simulate` | Simulates the equilibrium shape of the net at several speeds (experimental). |
| POST | `/simulate/haul` | Progressive haul: shape, door spread and pull while catch comes in (scenario with seabed and coupled otter boards). |
| POST | `/simulate/explore` | Explorer: states of net, otter boards and warps when sweeping a variable (catch, speed, warp, fouling, current, friction), with common connectivity and positions per state for animation; energy and footprint. |
| POST | `/simulate/selectivity` | Codend selectivity: up to 3 codend variants (diamond, T90, square; mesh size and U1) with the retention curve per species (L25, L50, L75, SR, SF), the maximum passing length per triangle and the shape for the 3D map and the per-mesh zoom. `/simulate/explore` accepts `species` and adds L50, SR and SF per state. |
| POST | `/simulate/uncertainty` | Uncertainty: Monte Carlo with Latin hypercube over the uncertain data (twine coefficients, frictions, otter board polar, catch); P10/P50/P90 and sensitivity (Spearman) per result. |
| POST | `/simulate/calibrate` | Calibration: bounded Levenberg–Marquardt of up to 3 parameters against observations (from sensors) or the DynamiT reference of the FAO A-3. |
| POST | `/sensors/parse` | Reads a sensor log (CSV from any equipment) and summarizes it into steady stretches and observations. |
| GET | `/sensors/example` | Example sensor log (synthetic) in CSV. |
| POST | `/design/report` | Report of the case in HTML, PDF or XLSX. |

## Example

```bash
curl -s -X POST http://127.0.0.1:8000/design \
  -H 'Content-Type: application/json' \
  -d '{"net": "fao_a3_standard", "net_modified": "fao_a3_modified", "vessel": "fao_a3_150hp", "compat": "excel"}'
```

The `DesignRequest` body accepts nets, vessels and otter boards by catalogue id or as a complete
specification, the calculation mode and `params` with the parameters of `GET /params`. The ids
are validated against the catalogue; numerical parameters must be finite and non-negative.
Notes, warnings, table labels and reports come out in English with `?lang=en` (or an
`Accept-Language: en` header); the response says which language it used in `Content-Language`.

A net of the FAO catalogue ({doc}`33_catalogo_fao`) sent **without vessel, otter board or
modified net** is computed with its own case (`trawlkit.catalog.catalog_case`): generic vessel of
the design power, otter board and depth from the plan, pair trawl without otter boards. The
assumptions come back in `notes` with the prefix `catalog:`, and `params` overrides what comes from
the source:

```bash
curl -s -X POST http://127.0.0.1:8000/design \
  -H 'Content-Type: application/json' -d '{"net": "bobp_wp13_pair_ho80"}'
```

A net of the FAO catalogue with `door` (for example an otter board from the components
catalogue) and without a vessel keeps the vessel of the net and changes only the otter board.

**Components** ({doc}`34_componentes`). `params` accepts `warp_id`, `float_id`, `twine_id` and
`chain_id` (ids from `GET /catalog/components/{kind}`) and the filters of the automatic selection
`component_brands` (list), `component_region` and `generic_only` (boolean). `components` carries
inline user contributions (up to 50, with status “user”): the engine sees them only in that
request. `POST /design/bom` accepts the same plus `prices` (component id or line key → indicative
price with currency and unit):

```bash
curl -s -X POST http://127.0.0.1:8000/design/bom \
  -H 'Content-Type: application/json' \
  -d '{"net": "fao_wb_bt2p_60hp", "params": {"generic_only": true},
       "prices": {"doors": {"value": 300, "currency": "USD", "unit": "unit"}}}'
```

`POST /optimize/components` chooses otter board, warp, floats and twine from the filtered
catalogue (`objective`: `drag`, `efficiency` or `cost`; `speed_kn` fixes the speed, otherwise the
best one within `v_bounds` is chosen) and returns the recommended rigging, alternatives and the
bill of materials of each one.

`POST /optimize` runs the scale and speed optimization of {doc}`20_optimizacion` (grid and, if
`refine`, differential evolution) and returns the best design, the feasibility grid and the Pareto
front. `POST /optimize/scaled-net` returns the `NetSpec` of the net scaled by `s`
(`trawlkit.optimize.scale_net`), ready to be sent as an inline net to `POST /design`.

`POST /simulate` runs the shape simulation of {doc}`21_simulacion` (experimental):

```bash
curl -s -X POST http://127.0.0.1:8000/simulate \
  -H 'Content-Type: application/json' \
  -d '{"net": "fao_a3_standard", "speeds_kn": [2, 3], "resolution": 4}'
```

It accepts from 1 to 9 speeds between 0.5 and 6 kn, `resolution` from 2 to 10 (4 by default), the
twine coefficients `cn`/`ct`, `knot_factor`, `door_spread_m` and `include_geometry` (nodes and
triangles of the shape, heavy). For each speed it returns the `SimResult` (openings, drag,
convergence), the SVG projections (plan, profile and front) of the first three speeds, the
engine's empirical quantities at the same speeds and, for the unedited standard FAO A-3 net, the
comparison with DynamiT. Each speed takes from ~1 s (resolution 2–4) to ~20 s (resolution
9–10): requests whose estimated cost exceeds 30 s are rejected with 422.

The variable `TRAWLKIT_CORS_ORIGINS` limits the allowed origins (`*` by default).
