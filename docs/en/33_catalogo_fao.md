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

# Catalogue of FAO nets

```{code-cell} ipython3
:tags: [remove-cell]
import sys, pathlib
DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English

import numpy as np
import _plots_v as PV
from myst_nb import glue
from trawlkit.catalog import catalog_case
from trawlkit.io.loader import NETS_DIR, load_net
from trawlkit.model import run
from trawlkit.netcheck import check
from trawlkit.provenance import coverage
from trawlkit.sim import simulate
from trawlkit.topology import has_sides

IDS = sorted(p.stem for p in NETS_DIR.glob("*.yaml"))
SPECS = {i: load_net(i) for i in IDS}
FAMILY = {"bottom": "bottom", "semi_pelagic": "semi-pelagic", "pelagic": "pelagic"}
RIG = {"otter": "otter boards", "pair": "pair"}


def num(x: float, nd: int = 1) -> str:
    return f"{x:.{nd}f}"


def hp(spec) -> str:
    lo, hi = spec.vessel_hp
    return f"{lo:g}" if lo == hi else f"{lo:g}–{hi:g}"


PUBLISHED = [i for i in IDS if SPECS[i].status == "published"]
DRAFTS = [i for i in IDS if SPECS[i].status == "draft"]
glue("n_nets", len(IDS), display=False)
glue("n_pub", len(PUBLISHED), display=False)
glue("n_draft", len(DRAFTS), display=False)
glue("n_values", sum(coverage(SPECS[i])["values"] for i in IDS), display=False)
```

## Purpose

The engine was born for the FAO A-3 net of the Excel workbook. This chapter brings together a
**catalogue of public nets** digitized from FAO documents, each with the **provenance of every
value**, and computes them with the generalized engine and simulator (Phase 12). The catalogue has
{glue:text}`n_nets` nets ({glue:text}`n_pub` published and {glue:text}`n_draft` drafts) and
{glue:text}`n_values` sourced values.

It serves three purposes:

- **Designing from a proven net**: each net comes with the vessel, the otter board and the depth it
  was trialled with, and the app computes it with that case.
- **Testing the engine beyond the A-3**: pair trawls, 4-panel and pelagic nets, from 20 to 113 m
  of headrope.
- **Validating against measurements**: Schärfe (1983) measured the opening of two of his nets at
  sea.

## Sources and method

The sources and the criteria are in {doc}`catalogo_fuentes`. In summary:

- **Documents**: BOBP/WP/10, /13 and /20 {cite}`bobpwp10,bobpwp13,bobpwp20` (high-opening bottom
  trawls for one and two boats, Bay of Bengal, 1980–82), the *Fisherman's Workbook*
  {cite}`prado1990` and Schärfe's report {cite}`scharfe1983` (4-panel pelagic nets of the R/V
  *Dr. Fridtjof Nansen*). The classic FAO catalogues of designs are not online.
- **Reading**: each figure was rasterized at 300 dpi (or the image embedded in the PDF was taken)
  and read number by number. No figure is stored in the repository (© FAO): only the data.
- **Provenance per value**: each number is *transcribed* (read from the figure), *derived*
  (computed from what was read: the twine diameter from its Rtex, U1 from the mouth) or *assumed*
  (what the drawing does not give), with the page, the figure and a note.
- **Validator** (`trawlkit.netcheck`): joins between panels, mouth, cuts against meshes, side
  seams and, in 4-panel nets, sides by stations. A net that does not close stays as a **draft**:
  visible, but out of the guided mode.

```{code-cell} ipython3
:tags: [remove-input]
rows = []
for i in IDS:
    s = SPECS[i]
    issues = check(s)
    err = sum(x.level == "error" for x in issues)
    warn = len(issues) - err
    cov = coverage(s)["by_kind"]
    total = sum(cov.values())
    sup = 100 * cov.get("assumed", 0) / total
    rows.append([
        s.name.split(" (")[0] + (" — draft" if s.status == "draft" else ""),
        FAMILY[s.family] + (", 4 panels" if has_sides(s) else ""),
        RIG[s.rig],
        hp(s),
        len(s.panels),
        f"{num(sup, 0)} %",
        f"{err} / {warn}",
        s.sources[0].key,
    ])
PV.md_table(
    ["Net", "Family", "Rigging", "hp", "Panels", "Assumed", "Errors / warnings", "Source"],
    rows,
)
```

## What the validator found

The validator was written to catch reading errors, and it caught them:

- **464 × 80 mm pair trawl (BOBP/WP/13)**: the belly “F” had been read with 60 rows. With 60 rows
  the 1N2B cut does not give the change from 232 to 152 meshes, and the belly does not reach the
  203-mesh station with the length of the top panel. With **80 rows** both things close: the
  blurred figure was an 8. The lower wing “D” goes from 50 to 93 meshes in 127 rows: only **1N4B**
  (with the other side in bars) gives that widening, and it is the cut of the lower wing in the
  *Workbook*.
- An honest warning remains: the upper wing “C” of that net calls for a cutting rate of ≈ 0.42 and
  the drawing says 1N2B (0.5). What was read is kept, with the note.
- The **gathers** of the drawings: several nets sew a large-mesh panel to a small-mesh one without
  matching the stretched length (up to 18 % in Schärfe, 13–14 % in BOBP/WP/10). They are not
  reading errors, because the same number appears in the top and in the belly and the cut of each
  panel closes with its meshes. The validator reports them as warnings (error threshold: 20 %).
- The **drafts**: the Harstad net sews 260 meshes of 190 mm to 260 of 140 mm (26 %), which may be
  an extreme gather or a misread mesh count. The krill net with a 1600 mm front does not let one
  read the depth of the belly wing, and the fish and shrimp net of BOBP/WP/20 is scanned at
  107 dpi. All three remain to be reviewed against the original.
- The 4-panel pelagic net of the *Workbook* (a 450 px figure) **was not digitized**. The body can
  be read and closes (24 × 800 = 48 × 400, 42 × 400 = 84 × 200…), but the 800 mm front cannot be
  read well enough to build a net without inventing numbers.

## Each net with its design case

`trawlkit.catalog.catalog_case` builds the case for each net:

- **Generic vessel** with the average power of the trial, scaled from the 150 hp vessel of the A-3.
- **Otter board from the drawing** (length × height with the polar of the flat otter board), or none
  for the pair trawl.
- **Depth** from the document.
- **Door spread** from the Fridman DPA ({doc}`16_aberturas`), because the workbook's “per metre”
  rule only holds for the blocks of the A-3.

With that case, the engine and the simulator give, at 3 kn:

```{code-cell} ipython3
:tags: [remove-input]
RES = {}
for i in IDS:
    r = run(catalog_case(i).case)
    sim = simulate(r, 3.0, resolution=2, coarse_resolution=None)
    RES[i] = (r, sim)
rows = []
ratio = []
for i in IDS:
    r, sim = RES[i]
    s = r.summary()
    if SPECS[i].family == "bottom":
        ratio.append(s["rn_std_3kn_kgf"] / sim.drag_kgf)
    rows.append([
        i,
        num(s["headrope_m"]),
        num(s["horizontal_opening_m"]),
        num(sim.ah_m),
        num(s["vertical_opening_m"]),
        num(sim.av_m),
        num(s["rn_std_3kn_kgf"], 0),
        num(sim.drag_kgf, 0),
    ])
PV.md_table(
    [
        "Net",
        "Headrope [m]",
        "AH engine",
        "AH sim.",
        "AV engine",
        "AV sim.",
        "R engine [kgf]",
        "R sim. [kgf]",
    ],
    rows,
)
glue("ratio_lo", num(min(ratio), 1), display=False)
glue("ratio_hi", num(max(ratio), 1), display=False)
glue("ratio_med", num(float(np.median(ratio)), 1), display=False)
```

The bottom trawls all show the same pattern:

- **Horizontal opening**: the engine and the simulator stay close for most of the nets.
- **Drag**: the engine gives between {glue:text}`ratio_lo` and {glue:text}`ratio_hi` times that of
  the simulator (median {glue:text}`ratio_med`). The engine's drag is the average of the empirical
  methods of the workbook ({doc}`14_resistencia`), fitted to A-3 bottom trawls, and the
  simulator's only counts the netting and the ropes (without otter boards).
- **Vertical opening**: this is the one that differs most. The simulator opens the top panel of
  these nets only a little with the buoyancy of the drawing, whereas the engine uses empirical
  proportion rules.

Neither was measured at sea for these nets: the BOBP documents report catches, not openings. That is
why the difference is left as data and not fitted.

## The pelagic nets against the measurements

Schärfe measured with a net sounder the opening of the krill net with both enlarged fronts. Those
measurements are stored in the net itself (`measured`) and are compared with the engine and with the
simulator under the same conditions:

```{code-cell} ipython3
:tags: [remove-input]
rows = []
for i in IDS:
    for m in SPECS[i].model_extra.get("measured", []):
        cc = catalog_case(i)
        r = run(cc.case)
        sim = simulate(r, m["speed_kn"], resolution=2, coarse_resolution=None)
        rows.append([
            i,
            num(m["speed_kn"]),
            num(m["warp_m"], 0),
            f"{num(m['height_m'], 0)} × {num(m['width_m'], 0)}",
            f"{num(r.summary()['vertical_opening_m'], 0)} × "
            f"{num(r.summary()['horizontal_opening_m'], 0)}",
            f"{num(sim.av_m, 0)} × {num(sim.ah_m, 0)}",
        ])
PV.md_table(
    ["Net", "v [kn]", "Warp [m]", "Measured height × width [m]", "Engine", "Simulator"],
    rows,
)
```

The differences are large, and they have three known causes:

- **Rigging**: Schärfe used 100 m bridles and front weights of 230 to 520 kg on the lower bridles.
  The catalogue case computes the bridles with the workbook's rule (meant for bottom trawls) and
  puts the ballast on the footrope. The simulator thus stretches the net downwards and closes it
  in width.
- **Equivalent 2-panel net**: the engine and the simulator add the sides to the top and to the
  belly ({doc}`21_simulacion`). That preserves the circumference, but lets the mouth deform without
  the side seams that keep it square in a 4-panel net.
- **Speed and warp**: the engine does not use the speed or the warp length for the opening.

The conclusion is that **the catalogue does not change what is known about the engine**: it is made
for 2-panel bottom trawls. For the 4-panel pelagic nets, the catalogue leaves the measurements and
the nets ready for a 4-sided simulator with real bridles and front weights, as a future improvement.

## Assumptions

| Assumption | Where | How to change it |
|---|---|---|
| Pair trawl wing tips at ½ headrope | `pair_wing_spread_m` | Case parameter |
| Fridman door spread | `door_spread_rule` | `"excel"` for the workbook's rule |
| 4-panel net = equivalent 2 panels | `trawlkit.topology` | — (4-sided simulator: future) |
| Generic vessel scaled from the A-3 | `catalog.generic_vessel` | Choose a vessel in the app |
| Side wings not modelled | Schärfe nets | — |

## Using the catalogue

- **In the app** (Expert mode), the “FAO catalogue” tab filters by family, rigging, source and
  power. It shows the provenance value by value and the validator warnings, and “Use this net”
  computes it with its case.
- **In the Guided mode**, the “Net” step offers the nets suited to the power of the chosen vessel
  (±25 % of the trial range).
- **From the API**:
  - `GET /catalog/nets` gives the filterable summary;
  - `/catalog/nets/{id}/provenance` and `/catalog/nets/{id}/check` give the provenance and the
    validator;
  - `POST /design` with a catalogue net and no vessel uses the catalogue case.
- **From the command line**: `trawlkit run bobp_wp13_pair_ho80`.
