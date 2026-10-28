---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# Components: catalogues, equivalents and cost

```{code-cell} ipython3
:tags: [remove-cell]
import sys, pathlib
DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English
import dataclasses

import _plots_v as PV
from myst_nb import glue
from trawlkit import components as comp
from trawlkit.catalog import catalog_case
from trawlkit.cost import bill_of_materials
from trawlkit.i18n import t
from trawlkit.io import load_net
from trawlkit.model import run
from trawlkit.optimize import optimise_components


def num(x: float, nd: int = 1) -> str:
    return f"{x:,.{nd}f}"


ITEMS = {k: comp.load_components(k) for k in comp.KINDS}
N_ITEMS = sum(len(v) for v in ITEMS.values())
BRANDS = sorted({i.brand for v in ITEMS.values() for i in v if i.brand})
glue("n_items", N_ITEMS, display=False)
glue("n_brands", len(BRANDS), display=False)
```

## Purpose

A net is not built from the drawing alone: it takes netting, wire ropes, ropes, otter boards,
floats, chains and shackles, and what can be found changes from port to port. This chapter describes the
**components catalogue** (Phase 13): {glue:}`n_items` items from {glue:}`n_brands` brands and
**generic** equivalents, with the source of each value; how the engine uses them for sizing; how
the **bill of materials** is put together with its indicative cost; and how the optimizer **chooses
the rigging** among what is available. The tool is aimed at fishers with few resources: the
generics can be found in any ship chandler's, the prices are entered by the user and the app
computes **offline** on the phone.

## Sources and generic equivalents

Almost no manufacturer publishes open tables, let alone for small sizes. That is why each type has
a **generic family** derived from the tables of FAO's *Fisherman's Workbook* {cite}`prado1990`,
and the brands are cited **point data**, never complete tables (at most ten sizes per product
line; manufacturer otter boards, on the other hand, carry every published size of each line since
Phase 19.8a, because door selection needs the whole series):

* **Netting and twine**: diameter and breaking load per Rtex for twisted and braided PA, PES, PP
  and PE, with a power fit $y = a\,x^b$ on a logarithmic scale over the tables of the *Workbook*;
  Garware (India) for braided PE {cite}`garware_fisheries`; Hampidjan (Iceland) for the Magnet
  braided PE, the Advant and Primanet Dyneema/HMPE and the Utzon twisted nylon
  {cite}`hampidjan_catalogue`.
* **Steel wire ropes**: weight and breaking load with $y = k\,d^2$ over the 6x7, 6x12, 6x19 and
  6x24 tables of the *Workbook*; Bridon-Bekaert {cite}`bridon2023` (Marblue, Dyform Starfish,
  Dyform, SeaBeam and 6x7) and PFEIFER {cite}`pfeifer_6x19w` as manufacturers, and the Randers Reb
  and Oliveira wire ropes (compacted 6xK26 and 6x19 Green Strand) from the Hampidjan catalogue.
* **Ropes**: PA, PE, PES, PP and combination steel-and-fibre ropes; Garware X2, Maxima, PP, PE and
  Maxibraid; Hampidjan Nylex, Kraft (Polysteel), Danline, DynIce 75 and Prima (HMPE footrope), and
  the Randers Reb combination seine rope.
* **Otter boards**: area and weight by power from the *Workbook* for flat, oval, V and Süberkrüb
  otter boards, with the measured polar of their type (Phase 19.3, {doc}`15_portones_aparejo`): the
  Seafish/IFREMER/DIFTA sheets {cite}`sfia1993` for the flat, the oval and the mean of the three V
  boards, and the Thyborøn 15 VF of {cite}`mellibovsky2018` for the Süberkrüb; four boards from the
  shrimp fleet of the Colombian Caribbean {cite}`zuniga2006`; Vónin Storm 2, Tornado and Twister
  (area and weight of the 14, 15 and 8 published sizes, {cite}`vonin_doors`; four Tornado sizes,
  1, 2, 14 and 15 m², from the table reprinted by {cite:t}`fishfocus2019_tornado`) and Morgère
  OvalFoil, PolyFoil and PFPE (area of the 21, 19 and 17 catalogue models; weight «sur demande»,
  {cite}`morgere2025`), with the type polar as assumed. Since Phase 20.1, the large boards: 25
  Thyborøn data sheets {cite}`thyboron_trawldoor` (645 sizes from 0.82 to 21.34 m², bottom,
  semi-pelagic and pelagic), the 5 distinct tables of the Polar brochures {cite}`polardoors` (180
  sizes from 1 to 20 m²) and the three Poly-Ice tables {cite}`polyice_doors` (41 sizes up to
  14.2 m², with dimensions).
* **Floats and chains**: buoyancy and maximum depth by diameter, weight per metre by link;
  Atlantic Floats trawl floats and Trygg and Trawlex long-link chains (Hampidjan catalogue) and
  Gunnebo LLZ grade 6 galvanised chain {cite}`gunnebo_llz`.
* **Shackles** (a new type in Phase 19.2): size, working load limit (WLL), minimum breaking load,
  weight of one piece and body and pin diameters; Crosby G-209 {cite}`crosby_g209` and Van Beest
  Green Pin (Hampidjan catalogue). The *Workbook* has no shackle reference table: it is the only
  type without generics.

The Hampidjan catalogue is a page viewer with no PDF and its text layer scrambles columns: every row
was read on the image of the page, not in the text. Where the data sheet does not give a value the
engine needs, the item says so: the Garware twisted netting (380 D, 500 D, Sapphire twisted and
210 D nylon) has no diameter, so it was loaded as a **draft** with the diameter estimated by the
*Workbook* fit and the note “A VERIFICAR” (to be verified); drafts do not enter the automatic
selection.

### Large otter boards (Phase 20.1)

Up to Phase 19.9 the largest board in the catalogue was the 16 m² Vónin Storm 2, and the five
fleet vessels of 2100 hp or more had no candidate. No public manufacturer table goes beyond
**21.34 m²** (Thyborøn Type 2 Iceland 200", 6800 kg); Thyborøn says it builds up to 25 m² and
8000 kg, without publishing those rows. Each distinct data sheet is loaded whole; sheets that repeat
another one's table (Type 20 and 21 Slider, Type 22 VF/VFB, Type 32, Type 42 hydraulic, Type 23 VK,
Type 26, Type 28 V-construction, the 15 Polar brochures that repeat one of the 5 tables) are loaded
once, and every item says so in its notes. Weights follow the sheet: with minimum–maximum columns
(Thyborøn) or «from–to» (Polar, Poly-Ice) the **mean value** is taken, as in the *Workbook*
generics, with the range in the note and *derived* provenance; the Type 2 carries the NORMAL weight
(the HEAVY one in the note); the Xstream doors, the published minimum; the Bluestream doors, the
«Standard weight»; and the Type 23 Iceland, no weight («as requested»). Dimensions are the printed
ones («LxH/mm»), except for three rows with obvious misprints (Type 16 at 1 m², Type 21 at 6 and
8 m²) and the high-aspect boards whose sheet prints the long side first (Types 23 and 42, Poly-Ice
mid-water), where the long side is taken as the height (*assumed*). Without dimensions, the
proportions come from a polar sheet of the type (the Seafish Thyborøn Type 2 125" for the Type 2)
or from the Polar «r» number, taken as the aspect ratio. The polar is always the type polar,
*assumed*.

With this catalogue every vessel up to 2600 hp gets a board, including the Holmberg, the Oca Balda
and the 2348 hp freezer trawler. The Angelescu (2855 hp) and the 4159 hp freezer trawler still have
no candidate: the book rule asks them for 31.5 and 45.9 m² of flat board per door, more than any
table. Those numbers are far from practice: the Angelescu was designed with Morgère SPF08 boards of
4.5 m² and 1200 kg {cite}`roth2017angelescu`, and the only public table indexed by power, the Net
Systems Fishbuster one {cite}`netsystems_fishbuster`, gives 7 m² for 1800–2200 hp and 11 to 12.5 m² for
3000–5500 hp. The rule
(area = 20 % of the available thrust over $C_D\,v^2$, averaged between 2 and 4 knots) is calibrated
for the 150–180 hp of the A-3 and grows in proportion to power, while the *Workbook* and Fishbuster
tables grow as power to the 0.65. The rule is not changed in this phase: the diagnosis and the
proposed correction are left for a later phase, because they touch the book's golden values.

```{code-cell} ipython3
:tags: [remove-input]
rows = []
for k in comp.KINDS:
    s = comp.summary(ITEMS[k])
    rows.append([t(comp.KIND_LABEL[k]), s["items"], s["generic"], ", ".join(s["brands"]) or "—"])
PV.md_table(["Type", "Items", "Generic", "Brands"], rows)
```

Each item carries its **provenance per value** (transcribed, derived, assumed or from the Excel
workbook), like the nets of the previous chapter, and points to its **generic equivalent**: the one
with the same construction and the closest generic size (the *Workbook* table does not have every
size, and the generic may break at more or less than the branded one). The table compares branded
wire ropes with their generic:

```{code-cell} ipython3
:tags: [remove-input]
rows = []
for item in ITEMS["wire"]:
    if item.brand != "Bridon-Bekaert" or item.diameter_mm not in (14, 16, 18):
        continue
    g = comp.generic_for(item)
    if g is None or g.id == item.id:
        continue
    rows.append(
        [
            f"{item.diameter_mm:g} mm",
            f"{item.name}",
            num(item.weight_kg_per_m, 3),
            num(item.breaking_load_t, 1),
            g.name,
            num(g.weight_kg_per_m, 3),
            num(g.breaking_load_t, 1),
        ]
    )
PV.md_table(
    ["Ø", "Branded", "kg/m", "Breaking load [t]", "Generic", "kg/m", "Breaking load [t]"], rows[:6]
)
```

### Elongation and axial stiffness

Hampidjan publishes the **elongation at break** of every netting and rope (not the stiffness);
Garware, Bridon-Bekaert and the wire ropes do not. Where it exists, the catalogue keeps it
(`elongation_pct`) and derives the secant axial stiffness $EA \approx R / \varepsilon$ (`ea_kn`,
“derived” provenance, `trawlkit.materials.ea_from_breaking_load_n`), which the engine uses ahead of
the generic relations of the material table. For the Hampidjan netting the data sheet only gives the
**knot** breaking load, so no EA is derived. The secant is a lower bound of the stiffness at the
working load:

```{code-cell} ipython3
:tags: [remove-input]
rows = []
for rid in (
    "hampidjan_nylex_16mm",
    "hampidjan_danline_16mm",
    "hampidjan_dynice_75_duracoat_16mm",
    "hampidjan_prima_foot_rope_51mm",
):
    r = comp.get_component("rope", rid)
    rows.append(
        [r.name, num(r.breaking_load_t, 1), num(r.elongation_pct, 1), num(r.ea_kn, 0)]
    )
PV.md_table(["Rope", "Breaking load [t]", "Elongation at break [%]", "EA [kN]"], rows)
```

## Physical validation

A component entered by hand may carry a units error or a typo. The validator
(`trawlkit.components.check`) compares each value with physical ranges of the material: weight per
metre against $k\,d^2$ (steel, fibre, chain), breaking load against that of the material, twine
tenacity in gf/tex, buoyancy against the volume of the float, otter board weight per m² and, for
shackles, weight per mm³ of body, working load per mm², breaking load against working load (design
factor 4:1 to 8:1; a breaking load below the working load is an error) and pin against body. The
warnings flag values outside the reference tables, not errors: modern PP/PE (Polysteel, Danline)
and braided nylon ropes break and stretch more than those of the *Workbook* tables. For
example, a 10 mm wire rope entered with 2 kg/m and 50 t:

```{code-cell} ipython3
:tags: [remove-input]
bad = comp.parse_component(
    {
        "kind": "wire",
        "id": "user_wire",
        "name": "contribution",
        "status": "user",
        "construction": "6x19",
        "diameter_mm": 10,
        "weight_kg_per_m": 2.0,
        "breaking_load_t": 50,
    }
)
PV.md_table(["Level", "Code", "Remark"], [[i.level, i.code, i.message] for i in comp.check(bad)])
```

## The engine with components

`DesignCase` accepts a catalogue component by id for the warp (`warp_id`), the floats
(`float_id`), the twine of all panels except the codend (`twine_id`) and the chain (`chain_id`); the
headrope and footrope ropes and the otter board were already chosen by id. Without those fields,
the automatic selection uses the catalogues of the Excel workbook and **the A-3 result does not
change** (the golden tests verify it); with the filters `component_brands`, `component_region` or
`generic_only`, the automatic selection searches the filtered components catalogue. With a chosen
float, the number of floats comes from the required buoyancy (Flot!F72:F82); with a twine, the
weight and the drag of the netting are recomputed with its diameter.

**Headrope and footrope from the catalogue** (Phase 19.2). With those filters, the headrope and the
footrope also come from the filtered catalogue, unless the case chooses a rope (`headrope_rope`,
`footrope_rope`). The workbook has no rule; the rope of the net (or of the workbook) stays as the
reference and, among the ropes **of the same material** (a combination rope is replaced by another
combination rope, which is what gives the rope its weight), the one with the **smallest diameter
whose diameter and breaking load are not below** the reference is chosen; if none reaches it, the
one with the highest breaking load (`trawlkit.rigging.select_rope_component`).

**Ballast chain from the catalogue** (`chain_id`). The ballast stage converts the minimum and
maximum ballast and the adjusting chain of the workbook (Flot!F225:F226, H224) into metres with the
weight per metre of the chain, and gives the weight in water of those metres,
$W_\text{water} = L\,w\,(1 - \rho_\text{sea}/\rho_\text{steel})$. The ballast in kg does not
change: the chain only translates it. With the A-3 and its filters:

```{code-cell} ipython3
:tags: [remove-input]
from trawlkit.io import load_doors, load_vessels
from trawlkit.model import DesignCase

_v = {v.id: v for v in load_vessels().vessels}
a3 = DesignCase(load_net("fao_a3_standard"), _v["fao_a3_150hp"], load_doors().doors[0])
rows = []
for label, kw in (
    ("Workbook (no filters)", {}),
    ("Generics only", {"generic_only": True}),
    ("Region Europe", {"component_region": "europe"}),
):
    r = run(dataclasses.replace(a3, **kw))
    rows.append(
        [
            label,
            r.floats.headrope_rope.description,
            r.ballast.footrope_rope.description,
            f"{num(r.ballast.limits.min_kg, 0)}–{num(r.ballast.limits.max_kg, 0)}",
        ]
    )
PV.md_table(["Selection", "Headrope", "Footrope", "Ballast [kg]"], rows)
rc = run(dataclasses.replace(a3, chain_id="gunnebo_llz_9mm")).ballast.chain
glue("chain_max_m", num(rc.max_m, 1), display=False)
glue("chain_min_m", num(rc.min_m, 1), display=False)
glue("chain_water", num(rc.water_weight_max_kgf, 0), display=False)
```

With the 9 mm Gunnebo LLZ chain (1.4 kg/m), the A-3 ballast is {glue:text}`chain_min_m` to
{glue:text}`chain_max_m` m of chain, weighing {glue:text}`chain_water` kgf in water in the maximum case.

## Bill of materials and indicative cost

`trawlkit.cost.bill_of_materials` puts together the list of what has to be bought: the netting by
material (the weight in air that `net.analyse` already computes), the headrope and the footrope,
the bridles and sweeps, the warp (two warps of the length paid out with 50 % spare, Cab!D12), the
floats, the pair of otter boards, the ballast chain (in metres, if the case chose a chain) and the
**shackles** of the rigging connections. The number of shackles is an **assumption** (no source
gives it): five per side with otter boards (warp–door, door–sweep, sweep–bridles and the two
bridles to the wing end) and three per side for pair trawling; the size is the smallest shackle of
the filtered catalogue whose working load limit is not below the working load of the gear
(Rem!E267). The prices are **always indicative** and entered by the user: the catalogue has no
prices. A line without a price
is reported as such and **never counts as zero**. The table uses illustrative prices in a fictitious
currency (XXX, the ISO code for “no currency”):

```{code-cell} ipython3
:tags: [remove-input]
case_a3 = catalog_case(load_net("fao_wb_bt2p_60hp")).case
res = run(case_a3)
XXX = lambda v, u: {"value": v, "currency": "XXX", "unit": u, "date": "2026-10", "source": "example"}
prices = {"netting_pa": XXX(12, "kg"), "doors": XXX(300, "unit"), "floats": XXX(4, "unit")}
bom = bill_of_materials(res, prices)
rows = [
    [
        ln.label,
        ln.component_name or ln.component_id or "—",
        f"{num(ln.quantity, 1)} {ln.unit}",
        "no price" if ln.cost is None else num(ln.cost, 0),
    ]
    for ln in bom.lines
]
PV.md_table(["Item", "Component", "Quantity", "Cost [XXX]"], rows)
glue("bom_missing", bom.missing_prices, display=False)
glue("bom_total", round(bom.totals.get("XXX", 0)), display=False)
```

The total with these prices is {glue:}`bom_total` XXX and {glue:}`bom_missing` lines remain without
a price, which the app asks to fill in before comparing riggings by cost.

### The user's price list

Prices are entered line by line in the app or as a **price list** in CSV or XLSX
(`trawlkit.prices`, `POST /prices/parse` and `POST /prices/export`): one row per price with the
**key** (the component id, e.g. `crosby_g209_5_8in`, or the line key, e.g. `netting_pa` or
`doors`), the price, the currency (ISO 4217), the unit of the line (`kg`, `m` or unit), the date
and the source. Columns are recognised in Spanish or English, with the separator and decimal comma
detected; a row with an error is reported with its number and does not stop the rest, and a repeated
key takes the last row. The export includes, empty, the bill-of-materials lines that still have no
price, as a template to fill in with the supplier. The same list feeds the bill of materials,
rigging by cost, the economics of the operation (chapter 37) and the batches, is saved with the
app **project** and works offline.

```{code-cell} ipython3
:tags: [remove-input]
from trawlkit.prices import read_prices, write_prices

price_list = write_prices(prices, "csv", [ln.to_dict() for ln in bom.lines]).decode()
print("\n".join(price_list.splitlines()[:5]))
glue("prices_back", len(read_prices(price_list, "prices.csv").prices), display=False)
```

Read back, the spreadsheet gives the same {glue:}`prices_back` prices.

## Optimal rigging with what is available

`trawlkit.optimize.optimise_components` searches a discrete grid over the filtered catalogue:
otter boards that reach the area equivalent to the required one (Port!F215) with the Seafish rule
({doc}`15_portones_aparejo`; before, those within the power range of the vessel), floats that
withstand the fishing depth, twines that reach 90 % of the breaking load of the drawing's twine,
and the thinnest warp that meets the diameter and the breaking load at the
working speed. Each rigging is evaluated with the constraints of the optimizer of chapter 20 (pull
with reserve, open net, warp, otter board, speed range) plus the depth of the floats and the
breaking load of the twine, at the best speed of the 0.05 kn grid, and is ranked by **minimum
drag**, **minimum work per m² swept** (maximum area per litre) or **minimum cost**. With the
two-panel bottom trawl of the *Workbook* and its 60 hp vessel:

```{code-cell} ipython3
:tags: [remove-input]
opt_all = optimise_components(case_a3, "drag")
opt_gen = optimise_components(dataclasses.replace(case_a3, generic_only=True), "drag")


def row(label, a):
    ev = a.evaluation
    c = a.components()
    return [
        label,
        c["door"],
        c["warp"] or "—",
        f"{c['float'] or 'from the drawing'} × {a.float_count or '—'}",
        c["twine"] or "from the drawing",
        num(ev.v_kn, 2),
        num(ev.demand_kgf, 0),
        "yes" if a.feasible else "no",
    ]


rows = [row("Recommended", opt_all.best)]
rows += [row(f"Alternative {i + 1}", a) for i, a in enumerate(opt_all.alternatives[:2])]
rows.append(row("Generics only", opt_gen.best))
PV.md_table(
    ["Rigging", "Otter board", "Warp", "Floats", "Twine", "v [kn]", "R_T [kgf]", "Feasible"], rows
)
glue("opt_evaluated", opt_all.evaluated, display=False)
```

{glue:}`opt_evaluated` riggings were evaluated, one per engine run (≈ 0.05 s each). Here the
recommended rigging is already generic (the otter board from the drawing, a 6x12 wire rope of the
*Workbook* family, plastic floats and a polyester twine thinner than the drawing's with the same
breaking load), which is why “generics only” gives the same one; when the recommended one includes
brands, the app always adds a generic alternative. The alternatives differ by a few kgf: the otter
board and the floats weigh little in the drag of a small net, which depends mostly on the netting.

## Offline: the engine on the phone

In port there is often no signal. The app is an **installable web application** (PWA) and, with
“Prepare offline use”, it downloads once the Python interpreter compiled to WebAssembly (Pyodide),
numpy, pydantic, pyyaml and the `trawlkit` *wheel* (about 15 MB). From then on, without a network,
the design, the catalogues, the bill of materials, the rigging with components, the validator of
contributions and the grid optimization run **on the phone**: `trawlkit.api.offline` serves the
same routes as the API with the same request and response models. The tests compare each route
with the API and, in CI, the design of the A-3 inside Pyodide (in Node) with that of CPython: the
largest relative difference is of the order of $10^{-16}$. The simulation, the PDF reports and the
SVG drawings still need the server, and the app says so. The **low data usage mode** hides the 3D
views and the simulation, which download three.js.

## User contributions

Anyone who uses a wire rope, rope or float that is not in the catalogue enters it in the
“Components” tab with the data from the label or the data sheet. The contribution is validated with
`POST /components/check`, is stored **only in the browser** with the status “contribution, not
verified” and enters the calculation only if the user enables it: it travels in the `components`
field of each request and the engine sees it only during that request. To add it to the catalogue,
“Propose for the catalogue” opens a GitHub *issue* with the components template and the JSON of the
contribution; a maintainer reviews it and transcribes it in `tools/components/` with its source.
There are no accounts and no personal data.

## Assumptions and limits

* The generics are **fits** to reference tables, not products: a real wire rope or twine of the
  same diameter may weigh or break ±10 % differently. The data sheet of each item says which value
  is from the manufacturer and which is derived or assumed.
* The polars of the generic and manufacturer otter boards are those of their type (measured on
  flume tank models), not of each model; no manufacturer publishes C_L/C_D.
* There are hardly any open data sheets from Latin American suppliers or for small sizes: the
  contributions cover that gap and are always distinguished from the sourced data.
* The prices are indicative and the user's own; the cost optimizer ranks first the riggings with
  fewer missing prices.
* The components optimizer does not scale the net (that is what the one in chapter 20 is for) nor
  does it change the headrope and footrope ropes: with filters, the automatic selection takes them
  from the catalogue with the rule above; without filters, they are those of the net or of the
  workbook.
* The number of shackles in the bill of materials is an assumption; the size covers the working
  load of the whole gear, a generous bound for each connection.
* Several sizes and products were left out on purpose: those that repeat the values of another
  product (Dyform 6x26 from 20 to 44 mm, Prima Headline, Dyform RL), the purse-seine ones (Dyform
  SeaPurse), the rows with obvious errata (13 mm Trawlex) and the data sheets with no open table
  (WireCo, Usha Martin, Euronete, Castro, Mar del Plata suppliers).
