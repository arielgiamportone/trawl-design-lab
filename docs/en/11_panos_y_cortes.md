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

# Netting panels and cuts

```{code-cell} ipython3
:tags: [remove-cell]
import sys, pathlib, math
DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from tests.golden_utils import golden
import _plots_t1 as P
P.setup_style()
```

## Purpose

A trawl is a set of trapezoidal **netting panels** sewn together. Each panel is defined by its
netting specification (material, twine diameter and linear density, mesh size), by its number of
meshes along the two edges and in depth, and by the way it is cut and mounted on the ropes. This
stage translates the plan of the FAO A-3 net {cite:p}`faocatalogue` into geometric quantities:
stretched lengths, working area, number of meshes and angle of the cuts. Everything that follows
—solid areas ({doc}`12_mecanica_red`), ropes ({doc}`13_dimensiones`) and drag
({doc}`14_resistencia`)— is built on these numbers.

## Theory

### Twine and mesh

The mesh is measured **stretched**: $m_L$ is the distance between the centres of two opposite knots
with the mesh pulled taut (80, 60, 40 and 30 mm in the A-3). Each mesh has four **bars** of length
$m_L/2$. The twine is characterized by its diameter $d$ and its linear density in **Rtex** (grams per
kilometre of finished twine); its inverse is the **runnage**

$$
r = \frac{10^6}{\mathrm{Rtex}}\quad [\mathrm{m/kg}],
$$ (eq-runnage)

781.25 m/kg for 1.37 mm polyamide (PA) R1280tex and 1,052.6 m/kg for 1.16 mm R950tex.

### Panel geometry

With the workbook's convention, $T_1$ and $T_2$ are the meshes along the two edges of the panel and
$N$ the meshes in depth. The stretched panel is a trapezium whose sides measure

$$
L_{T} = \frac{T\,c_X\,m_L}{1000}, \qquad L_N = \frac{N\,c_Y\,m_L}{1000}\quad[\mathrm{m}],
$$ (eq-largo-estirado)

where $c_X = 0.5$ and $c_Y = 1$ are the "on the plan" coefficients with which the sheet draws the
panels (edges with the mesh half open, depth at stretched mesh).

When the net is rigged, the mesh does not work stretched but open. The **horizontal hanging ratio**
$U_1$ is the fraction of the stretched length that the mesh occupies across; since the bars do not
change length, the vertical opening is fixed by

$$
U_2 = \sqrt{1 - U_1^2}.
$$ (eq-u2)

The A-3 uses $U_1 = 0.38$ in the wings, square and first body, and $U_1 = 0.23$ in the second body and
the codend: the net closes towards the rear so that the catch does not escape. With those ratios,
the **working area** of the mounted panel (Prado) is that of a trapezium of diamond meshes:

$$
S_t = U_1 U_2\,\frac{T_1 + T_2}{2}\,N\,\left(\frac{m_L}{1000}\right)^2\quad[\mathrm{m^2}].
$$ (eq-st-pano)

The product $U_1U_2$ is at its maximum (0.5) at $U_1 = 0.707$, the square mesh; at 0.38 it is 0.35 and
at 0.23 it is 0.22. The **number of meshes** in the panel, used for costing the netting, is

$$
n = (T_1 + T_2 - 1)(N - 0.5) + 0.5 .
$$ (eq-n-mallas)

### Cuts

To go from an edge of $T_1$ meshes to one of $T_2$ over $N$ meshes in depth, the panel must be cut on
the diagonal. Cuts are combined from three elements: **N** (point: advances one mesh in depth without
changing the width), **T** (transversal mesh: reduces the width by one mesh without advancing) and
**B** (bar: advances half a mesh in depth and reduces the width by half a mesh). A code such as 1N2B
(one point, two bars, repeated) advances $1 + 2\cdot\tfrac12 = 2$ meshes in depth and reduces the
width by $2\cdot\tfrac12 = 1$ mesh per cycle, so that its **cutting rate** is

$$
RC = \frac{\Delta T}{\Delta N} = \frac{T + B/2}{N + B/2} = \frac12 .
$$ (eq-razon-corte)

The AB cut (all bars) gives 1/1; 1N1B, 1/3; 3N2B, 1/4; 1T2B, 2/1. The workbook's table of cuts
(`src/trawlkit/data/reference/cut_ratios.csv`) covers the rates 1/1 to 1/20 and some $2/x$.

In the wings, the workbook splits the cut edge into two stretches: $X_2 = N$ meshes in AB and the
rest, $X_1 = \lvert N - \lvert T_1 - T_2\rvert\rvert$, with rate

$$
RC_{X_1} = \frac{\lvert X_1 - N\rvert}{2X_1},
$$ (eq-rc-ala)

which is looked up in the table to obtain the code (panel A: $X_1 = 18$, $RC = 0.5$ → 1N2B).

### Angle of attack of the cuts

Once rigged, the cut edge forms an angle with the axis of the net that depends on the code and the
rigging. If the code reduces the width by $a$ meshes every $d$ meshes in depth (Prado),

$$
\tan\theta = \frac{a\,U_1}{d\,U_2}.
$$ (eq-angulo-corte)

For 1N2B ($a = 1$, $d = 2$) with $U_1 = 0.38$, $\theta = 11.6°$; with $U_1 = 0.23$, $6.7°$. The
workbook averages the angles of the panels of the upper plane (A, C, E, G, H) and obtains
$\alpha = 10.63°$, the **angle of attack** used by the Hamuro and Fridman drag methods and by the
DPA from the cut angle. The smaller the angle, the more aligned the panel is with the flow and the
lower its form drag; angles of 5–15° are typical in the body of a bottom trawl.

## Coefficients and tables

| Quantity | Value | Unit | Source | Excel cell |
|---|---|---|---|---|
| Netting 80 mm (wings) | PA, Ø 1.37, R1280tex | mm, g/km | FAO A-3 plan | `P!C3:C7` |
| Netting 60 mm (square, body 1) | PA, Ø 1.16, R950tex | mm, g/km | plan | `P!C13:C17` |
| Netting 40 mm (body 2 / codend) | Ø 1.16 R950tex / Ø 1.37 R1280tex | mm | plan | `P!O3:O7`, `O19:O23` |
| Netting 30 mm (modified codend) | PA, Ø 1.37, R1280tex | mm | plan | `P!C24:C28` |
| On-the-plan coefficients $c_X$, $c_Y$ | 0.5 / 1 | — | sheet | `P!D55`, `F57` |
| $U_1$ wings, square, body 1 | 0.38 | — | plan | `P!W271:W282` |
| $U_1$ body 2, codend | 0.23 | — | plan | `P!W276:W279` |
| Table of cuts | 1/1 … 1/20, 2/x | — | FAO | `Tab!A49:F88` |

## Excel ↔ `trawlkit` equivalence

| Cell(s) | Content | Function |
|---|---|---|
| `P!A55` | Runnage | `trawlkit.netting.runnage_m_per_kg` |
| `P!I55:I57` | Stretched lengths | `trawlkit.netting.stretched_length_m` |
| `P!L55` | Twine density | `trawlkit.materials.twine_density_kg_m3` |
| `P!A61` | Working area of the panel | `trawlkit.netting.panel_working_area_m2` |
| `P!A64` | Number of meshes | `trawlkit.netting.mesh_count` |
| `P!G63:G64` | Meshes of the cuts $X_1$, $X_2$ | `cut_meshes`, `cut_meshes_x2` |
| `P!H63`, `G127` | Cutting rate | `trawlkit.netting.cut_ratio`, `taper_ratio` |
| `P!I63` | Cut code | `trawlkit.netting.cut_code` |
| `P!H273:K273` | Cut angle | `trawlkit.netting.cut_angle_deg` |
| `P!K278` | Mean angle | `trawlkit.netting.mean_cut_angle_deg` |
| `P!J240`, `B243` | Joining of the modified codend | `join_ratio`, `join_offset_m` |
| `P!N269:W291` | Panel summary | YAML spec `src/trawlkit/data/fao_a3_standard.yaml` |

## Assumptions and limits

* **Swapped labels.** In the block for panel A the sheet labels `b (T2)` and `a (T1)` the other way
  round from the rest; the golden values keep the sheet's order and the functions are symmetric in
  $T_1$, $T_2$.
* **On-the-plan $U_1$ in `P!A61`.** The working area of the panels sheet uses $c_X = 0.5$ as if it
  were $U_1$ (2.99 m² for A), whereas that of {doc}`12_mecanica_red` uses the panel's real $U_1$
  (0.38). Only the latter feeds the drag.
* **Errata** (see {doc}`erratas`):
  `cut_ratio_first_panel` (all the angle rows use the code of the first panel; in the A-3 they are all
  1N2B and the result does not change), `panel_f_cut_na` (the rate of panel F, 0.2692, is not in the
  table and the cell gives `#N/A`; in corrected mode the nearest one is taken, 3N2B),
  `panel_b_cut_uses_plan_coef` (the rate of panel B uses $c_X$ instead of $N$: 0.486 instead of 0.5),
  `panel_b_cut_code_lookup_a` and `twine_density_units` (the "density" in `P!L55` does not have units
  of density: 1,152 kg/m³ in the workbook against a dimensionally correct 868 kg/m³ for the braided
  twine, and 1,140 kg/m³ for the polymer).
* The geometry assumes flat panels and perfect diamond meshes; it ignores the size of the knot and the
  stretching of the twine under load.

## Executable example

Netting specification and quantities of panel A (upper wingtip), compared with the sheet:

```{code-cell} ipython3
from trawlkit import Compat
from trawlkit import netting
from trawlkit.materials import twine_density_kg_m3

G = "panos_de_red_y_cortes"
r = netting.runnage_m_per_kg(1280)
checks = {
    "panel_a_runnage_m_kg": r,
    "panel_a_stretched_t1_m": netting.stretched_length_m(57, 80, 0.5),
    "panel_a_stretched_n_m": netting.stretched_length_m(36, 80, 1.0),
    "panel_a_working_area_m2": netting.panel_working_area_m2(0.5, 57, 3, 36, 80),
    "panel_a_mesh_count": netting.mesh_count(57, 3, 36),
    "panel_a_cut_x1_meshes": netting.cut_meshes(57, 3, 36),
    "panel_a_cut_x1_ratio": netting.cut_ratio(netting.cut_meshes(57, 3, 36), 36),
    "panel_a_twine_density_kg_m3": twine_density_kg_m3(1.37, 80, r, Compat.EXCEL),
}
for key, value in checks.items():
    assert math.isclose(value, golden(G, key), rel_tol=1e-6), key
assert netting.cut_code(0.5) == golden(G, "panel_a_cut_x1_code") == "1N2B"
rc_f = golden(G, "panel_f_cut_x1_ratio")  # 0.2692: not in the table
assert netting.cut_code(rc_f, compat=Compat.EXCEL) is None  # the workbook's #N/A
assert netting.cut_code(rc_f) == "3N2B"  # corrected mode: nearest rate
P.md_table(["Quantity (panel A)", "trawlkit", "Excel"],
           [[k, P.fmt(v, 4), P.fmt(golden(G, k), 4)] for k, v in checks.items()])
```

Angle of attack of the cuts of the upper plane and their average (`P!K273:K278`):

```{code-cell} ipython3
codes = golden(G, "cut_codes")
u1 = golden(G, "cut_u1_horizontal")
angles = [netting.cut_angle_deg(c, u) for c, u in zip(codes, u1)]
for a, b in zip(angles, golden(G, "cut_angle_deg")):
    assert math.isclose(a, b, rel_tol=1e-6)
alpha = netting.mean_cut_angle_deg(codes, u1, compat=Compat.EXCEL)
assert math.isclose(alpha, golden(G, "cut_angle_average_deg"), rel_tol=1e-6)
P.md_table(["Panel", "Code", "U₁", "U₂", "θ [°]"],
           [[p, c, P.fmt(u, 2), P.fmt(math.sqrt(1 - u * u), 4), P.fmt(a, 2)]
            for p, c, u, a in zip("ACEGH", codes, u1, angles)]
           + [["**Average α**", "", "", "", f"**{P.fmt(alpha, 2)}**"]])
```

First rows of the table of cuts:

```{code-cell} ipython3
:tags: [hide-input]
rows = netting.load_cut_table()
P.md_table(["Rate", "Code", "Meshes in width", "Meshes in depth"],
           [[r.label, r.cut_code, r.mesh_increase_width or "—", r.mesh_increase_height or "—"]
            for r in rows[:8]] + [[r.label, r.cut_code, "—", "—"] for r in rows[20:]])
```

Summary per panel of the standard net —A/B upper and lower wingtips, C/D wings, E square,
F second section of the lower wing, G/H bodies (top panel and belly the same), I/J codends— with the length
at stretched mesh, the working area with each panel's $U_1$ and the number of meshes, per panel:

```{code-cell} ipython3
:tags: [hide-input]
from trawlkit.io import load_net
from trawlkit.net import working_surface_m2

std = load_net("fao_a3_standard")
rows = []
for p in std.panels:
    rows.append([p.id, P.fmt(p.mesh_mm, 0), P.fmt(p.twine_diameter_mm, 2),
                 f"{p.meshes_top}/{p.meshes_bottom}", p.meshes_depth, P.fmt(p.hanging_ratio, 2),
                 p.count, P.fmt(netting.stretched_length_m(p.meshes_depth, p.mesh_mm), 2),
                 P.fmt(working_surface_m2(p.hanging_ratio, p.mesh_mm, p.meshes_top,
                                          p.meshes_bottom, p.meshes_depth), 2),
                 f"{netting.mesh_count(p.meshes_top, p.meshes_bottom, p.meshes_depth):,.0f}"
                 .replace(",", " "),
                 p.cut_code or "—"])
P.md_table(["Panel", "mL [mm]", "d [mm]", "T mouth/codend", "N", "U₁",
            "Qty", "Length N [m]", "Sₜ each [m²]", "Meshes each", "Cut"], rows)
```

```{code-cell} ipython3
:tags: [hide-input]
from trawlkit.drawing.layout import layout_net

lay = layout_net(std, mode="schematic")
colours = {0.38: P.SERIES[0], 0.23: P.SERIES[1]}
fig, axes = plt.subplots(1, 2, figsize=(9.2, 6.4), sharey=True)
titles = {"upper": "Upper plane (top panel)", "lower": "Lower plane (belly)"}
for ax, plane in zip(axes, lay.planes):
    for s in lay.shapes[plane]:
        c = colours[s.hanging_ratio]
        ax.add_patch(Polygon(s.points, closed=True, facecolor=c, alpha=0.16, lw=0))
        ax.add_patch(Polygon(s.points, closed=True, fill=False, edgecolor=c, lw=1.2))
        if s.side != "left":
            cx, cy = s.centroid
            label = s.id if s.cut_code is None else f"{s.id}\n{s.cut_code}"
            if s.section.value == "wing_tip":  # small triangle: label to the side
                ax.annotate(label, xy=(cx, cy), xytext=(cx - 7.5, cy - 0.3), fontsize=8.5,
                            ha="center", va="center", color=P.INK, linespacing=1.1,
                            arrowprops=dict(arrowstyle="-", color=P.MUTED, lw=0.8))
            else:
                ax.text(cx, cy, label, ha="center", va="center", fontsize=8.5, color=P.INK,
                        linespacing=1.1)
    ax.set_title(titles[plane])
    ax.set_xlim(-19.5, 19.5)
    ax.set_xlabel("Width at stretched mesh [m]")
    ax.grid(False)
axes[0].set_ylim(43.5, -1)
axes[0].set_ylabel("Distance from the mouth at stretched mesh [m]")
from matplotlib.patches import Patch
fig.legend(handles=[Patch(facecolor=colours[u], alpha=0.35, edgecolor=colours[u], label=f"$U_1$ = {P.fmt(u, 2)}")
                    for u in colours], loc="lower center", ncol=2)
fig.tight_layout(rect=(0, 0.05, 1, 1))
plt.show()
```

The diagram draws the standard net at stretched mesh, with the cut code of each panel. The logic of
the design can be seen: 80 mm wings with 1N2B cuts (in the belly, wing D uses 1N4B, more open, and
the second section F completes the bosom along the footrope), a 60 mm square and first body that close
with the same cut, and a 40 mm second body and codend mounted more closed ($U_1 = 0.23$), which is
what reduces the angle of attack from 11.6° to 6.7° in that area.

## Exercises

From the teaching-mode bank, with the data of the book. In the app, the “UTN Classroom” mode
generates them with other data and marks them ({doc}`38_docentes`).

```{code-cell} ipython3
:tags: [remove-input]
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path.cwd().parent))
import _exercises
_exercises.section("11_panos_y_cortes")
```
