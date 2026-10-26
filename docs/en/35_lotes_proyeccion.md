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

# Fleets, batches and projection of nets

```{code-cell} ipython3
:tags: [remove-cell]
import math
import sys, pathlib
DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English

import matplotlib.pyplot as plt
from IPython.display import Markdown
import _plots_v as PV
from myst_nb import glue
from trawlkit.batch import fleet_vessel, project_net, read_input, run_input, template
from trawlkit.batch.project import ProjectOptions


def num(x: float, nd: int = 2) -> str:
    return f"{x:,.{nd}f}"


FLEET = [("Small", 40), ("Coastal", 60), ("Medium", 100), ("Inshore", 150), ("Large", 220),
         ("Offshore", 300)]
FAST = ProjectOptions(assemble=False)
PROJ = {
    net: [project_net(net, fleet_vessel({"name": n, "bhp": hp}), FAST) for n, hp in FLEET]
    for net in ("fao_wb_bt2p_60hp", "fao_a3_standard")
}
```

## Purpose

A cooperative, a fishing school or a port technician rarely designs a net for a single vessel:
they have the port's **fleet**, the nets already in use and many similar questions. What size of
net suits each vessel? At what speed? With which otter board, warp and floats? This chapter
describes the bulk loading of spreadsheets, **batch calculation** and the **projection of a
proven net onto other vessels** (Phase 14).

## The projection: similarity and refinement

**Similarity.** If a net is enlarged keeping the mesh size, the twine and the rigging, all its
linear measurements grow with the scale $s$ and the netting area with $s^2$. The drag of the
net is, at equal speed, proportional to that area, and the pull the vessel can deliver is
proportional to its power {cite}`prado1990`. For a vessel of power $P$ to tow the net as the
vessel for which it was designed (power $P_d$) tows it, the ratio between drag and pull must be
preserved:

$$
s^2 \propto \frac{P}{P_d} \quad\Longrightarrow\quad s_0 = \sqrt{\frac{P}{P_d}}.
$$

The otter board is scaled with the same rule (area proportional to power), the one the net
catalogue of chapter 33 already uses when the plan does not give the otter board, and the door
spread comes from Fridman's DPA: the workbook's “per metre” rule (Port!E13) is calibrated for the
A-3 and its warp, and with a smaller net it would give an impossible spread.

**Refinement.** Similarity is approximate: the warp, the otter boards, the floats and the
ballast do not scale in the same way, and the opening depends on the speed. That is why
`trawlkit.batch.project_net` takes $s_0$ as a starting point and searches, with the evaluator of
the optimizer of chapter 20, for the **largest scale** between $0.7\,s_0$ and $1.3\,s_0$ that
meets the usual constraints (pull with a 10 % reserve, open net, warp and otter board) at the
speed the vessel achieves or, if it does not achieve it, at some speed between 2 and 4 knots. A
bisection refines the scale. Then rigging with the component catalogue of chapter 34 chooses the
otter board, warp, floats and twine for the scaled net.

## Example: a fleet of six vessels

```{code-cell} ipython3
:tags: [remove-input]
rows = []
for net, label in (("fao_wb_bt2p_60hp", "Workbook 60 hp"), ("fao_a3_standard", "FAO A-3")):
    for p in PROJ[net]:
        s = p.summary()
        rows.append(
            [
                label,
                s["vessel"],
                f"{s['bhp']:g}",
                num(s["s0"], 3),
                num(s["s"], 3),
                num(s["speed_kn"], 2),
                num(s["headrope_m"], 1),
                num(s["demand_kgf"], 0),
                "yes" if s["feasible"] else "no",
            ]
        )
PV.md_table(
    ["Base net", "Vessel", "hp", "s₀", "s", "v [kn]", "Headrope [m]", "R_T [kgf]", "Feasible"], rows
)
ratios = [p.s / p.s0 for net in PROJ for p in PROJ[net]]
glue("ratio_lo", Markdown(num(min(ratios), 2)), display=False)
glue("ratio_hi", Markdown(num(max(ratios), 2)), display=False)
a3 = next(p for p in PROJ["fao_a3_standard"] if p.vessel.vessel.bhp == 150)
glue("a3_s", Markdown(num(a3.s, 2)), display=False)
```

The final scale follows the similarity scale: the ratio $s/s_0$ lies between {glue:md}`ratio_lo`
and {glue:md}`ratio_hi` for the twelve cases, from 40 to 300 hp; that is, the law
$s \propto \sqrt{P}$ describes the behaviour of the engine well and the refinement only corrects
the level. That the ratio is somewhat below 1 says that, with the 10 % pull reserve and Fridman's
door spread, the engine finds the design nets a little large for their vessel: the A-3 with its
150 hp vessel ends up at {glue:md}`a3_s`.

```{code-cell} ipython3
:tags: [remove-input]
fig, ax = plt.subplots(figsize=(7.2, 4.2))
for net, label, color in (
    ("fao_wb_bt2p_60hp", "Workbook (60 hp design)", "#1c5cab"),
    ("fao_a3_standard", "FAO A-3 (150 hp design)", "#c35a1b"),
):
    hp = [p.vessel.vessel.bhp for p in PROJ[net]]
    ax.plot(hp, [p.s for p in PROJ[net]], "o-", color=color, label=f"{label}: final scale")
    ax.plot(hp, [p.s0 for p in PROJ[net]], "--", color=color, alpha=0.6,
            label=f"{label}: similarity s₀")
ax.set_xlabel("Vessel power [hp]")
ax.set_ylabel("Net scale s")
ax.grid(alpha=0.3)
ax.legend(fontsize=8, frameon=False)
fig.tight_layout()
plt.show()
```

## Spreadsheets: fleet, nets and cases

`trawlkit.batch` reads **CSV** and **XLSX**:

- **Fleet**: one vessel per row, with name, power (hp or kW), length overall, beam, depth,
  propeller, fishing depth, speed, port region, seabed and “generic only”. Missing measurements
  are scaled from the A-3 vessel, with a warning.
- **Nets**: a sheet of panels (mesh size, twine, meshes at the mouth, at the codend end and in
  depth, U1, quantity, cut) and an optional “net” sheet (ropes, floats, design power, depth).
  Each net goes through the validator of chapter 33; with errors it is kept as a draft. The A-3
  exported to a spreadsheet and read back gives exactly the same result.
- **Cases**: each row is a complete case (net, vessel, otter board, mode) and any parameter of
  `GET /params` can be a column.

Column names are accepted in Spanish or English, regardless of accents or capitals, with the unit
as a suffix or in brackets (`Potencia (kW)`, `eslora_ft`); numbers accept a decimal comma. An
error in a row (a value that is not a number, an unknown option) is reported with its row and
column and **does not stop the batch**. The templates come with examples and a help sheet with
each column, its unit and its usual range:

```{code-cell} ipython3
:tags: [remove-input]
inp = read_input(template("fleet", "xlsx"), "flota.xlsx", "fleet")
res = run_input(inp, net="fao_wb_bt2p_60hp", options=FAST)
PV.md_table(
    ["Vessel", "hp", "s", "v [kn]", "Feasible"],
    [
        [r.name, f"{r.summary['bhp']:g}", num(r.summary["s"], 3), num(r.summary["speed_kn"], 2),
         "yes" if r.status == "ok" else "no"]
        for r in res.rows
    ],
)
```

## Where it is used

- **Web**: the “Batches and fleet” tab (template download, upload, editable preview, calculation
  in chunks with progress, table with traffic lights and filter, “Open this case”, download as
  XLSX, CSV, PDF or print view) and, in Guided mode, “Do you have several vessels?” in the vessel
  step.
- **Offline**: the engine on the phone (chapter 34) also computes batches and writes XLSX
  (openpyxl travels with the engine); the PDF needs the server and, without a network, the HTML
  view is printed.
- **CLI**: `trawlkit batch flota.xlsx --net fao_wb_bt2p_60hp -o lote.xlsx` (or `.csv`, `.json`,
  `.pdf`) and `trawlkit batch --template plantilla.xlsx`.
- **API**: `POST /batch/parse`, `/batch/run`, `/batch/export` and `GET /batch/template`
  ({doc}`api`), with the cost guard `TRAWLKIT_MAX_BATCH_SECONDS`.

## Assumptions and limits

- Similarity assumes geometrically similar nets: same mesh size and twine. For a vessel much
  smaller or larger than the design vessel (s outside 0.5–2) the mesh size, the twine and the
  rigging, which scaling does not change, should be reviewed.
- The search range is $0.7$–$1.3\,s_0$: if the result hits the upper limit, the case sheet warns
  about it (the vessel could handle a larger net).
- Without a speed in the spreadsheet the search is between 2 and 4 knots; at lower speed any net
  “fits”, but it does not fish.
- With the engine on the phone, batches are split into chunks of 10 vessels so as not to freeze
  it.
