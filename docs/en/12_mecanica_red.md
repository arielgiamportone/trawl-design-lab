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

# Net mechanics

```{code-cell} ipython3
:tags: [remove-cell]
import sys, pathlib, math
DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English
import numpy as np
import matplotlib.pyplot as plt
from tests.golden_utils import golden
import _plots_t1 as P
P.setup_style()
```

## Purpose

The hydrodynamic drag of a net depends, above all, on **how much twine** faces the water and on
**how much area** the netting occupies once mounted. This stage sums up the net in four quantities:
the filtration index $d/l$, the solid area $S_s$, the working area $S_t$ and their quotient, the
solidity. It adds the weight of the net in air and in water, which enters the ballast. They are the
direct inputs of the thirteen drag methods ({doc}`14_resistencia`) and are computed for the two
variants of the net: the **standard** one (40 mm codend) and the one **modified** for crustaceans
(30 mm codend I', top and bottom).

The sheet does not work with individual panels but with **netting rows**: one per letter (A+B, C, E,
G, H, D, F, I, J or I'), with the number of identical panels in each row.

## Theory

### Filtration index

The ratio between the twine diameter and the mesh size measures what fraction of the mesh is
occupied by twine. For the whole net the workbook uses the ratio of sums over the netting rows

$$
\frac{d}{l} = \frac{\sum_i d_i}{\sum_i m_{L,i}} ,
$$ (eq-dl)

without weighting by area or by number of panels. In the standard A-3 it is
$11.49/540 = 0.0213$; the rows vary between 0.017 (80 mm wings) and 0.034 (40 mm codend). It is the
variable of the Japanese drag formulas (Tauti, Koyama, Hamuro): for the same net size, the drag
grows almost in proportion to $d/l$.

### Solid area

The area that the twine projects is the product of its total length by its diameter. A panel of
$N$ meshes in depth and edges $T_1$, $T_2$ has, at stretched mesh, a length $L = N\,m_L/1000$ [m]
and contains $\approx (T_1+T_2)\,N$ bars of $m_L/2$ in each direction, whence

$$
S_s = \frac{L\,d\,(T_1 + T_2)}{1000}\,n_p\quad[\mathrm{m^2}],
$$ (eq-ss)

with $d$ in mm and $n_p$ the number of identical panels (FAO). It is equivalent to
$S_s = 2\,d\,m_L\,n$ with $n$ the number of meshes: each mesh contributes twice its stretched length
of twine. Knots are not included. $S_s$ is the variable of the European formulas (Reid, Robertson,
MacLennan, Aberdeen).

### Working area and solidity

The working area is that of the mounted panel ({eq}`eq-st-pano` in {doc}`11_panos_y_cortes`):

$$
S_t = \tfrac12\,U_1 U_2\,m_L^2\,(T_1+T_2)\,N\,n_p\quad[\mathrm{m^2}],\ m_L\ \text{in m}.
$$ (eq-st)

The quotient

$$
\sigma = \frac{S_s}{S_t} = \frac{2\,(d/m_L)}{U_1U_2}
$$ (eq-solidez)

is the **solidity** (Pérez Águila {cite:p}`perezaguila2010`): the fraction of the mounted area
blocked by twine; $1-\sigma$ is the filtering coefficient. For $d/m_L \approx 0.02$ and
$U_1U_2 = 0.35$, $\sigma \approx 0.12$; a more closed panel (small $U_1$) or one of thicker twine is
more solid, filters worse and builds up more pressure ahead of the codend.

### Weight of the net

The workbook weighs the twine in two steps (methods A and B). First the weight of a reference panel
of $T = 500$ by $N = 100$ meshes:

$$
S_N = \left(T\,\frac{m_L}{1000}\,2N\right)\pi\left(\frac{d}{2000}\right)^2\rho\quad[\mathrm{kg}],
$$ (eq-peso-ref)

length of twine times cross-section times density. It is then scaled to the real panel by the ratio
of meshes, $W = \frac{(T_1+T_2)/2}{T}\cdot\frac{N_p}{N}\cdot S_N$, and the weight in water is
$W_a = W\,(1 - \rho_w/\rho)$ with $\rho_w = 1025$ kg/m³. For polyamide ($\rho = 1140$ kg/m³) the
weight in water is barely 10 % of the weight in air.

## Coefficients

| Quantity | Value | Unit | Source | Excel cell |
|---|---|---|---|---|
| Density of seawater (forces) | 1024 | kg/m³ | — | `Mec!O127` |
| Density of water (weights) | 1025 | kg/m³ | — | `Mec!P98` |
| Reference panel $T \times N$ | 500 × 100 | meshes | — | `Mec!L98:M98` |
| π in the weight formulas | 3.1416 | — | — | `Mec!N98`, `P!L55` |
| Density of PA polymer | 1140 | kg/m³ | catalogue | `Tab!A35:I37` |
| $U_1$ per row | 0.38 / 0.23 | — | plan | `Mec!K56:K64` |

## Excel ↔ `trawlkit` equivalence

| Cell(s) | Content | Function |
|---|---|---|
| `Mec!K6:K14` | $d/m_L$ per row | `trawlkit.net.filtration_per_row` |
| `Mec!K15`, `K17` | $d/l$ of the net | `trawlkit.net.filtration_index` |
| `Mec!M29:N37` | Length and $S_s$ per row | `panel_length_m`, `solid_surface_m2` |
| `Mec!N38`, `N40`, `O30:O37` | Total $S_s$ and per plane | `trawlkit.net.analyse`, `split_by_plane` |
| `Mec!K56:M64`, `M65`, `M67` | $U_1$, $U_2$, $S_t$ | `trawlkit.net.working_surface_m2` |
| `Mec!E75:M79` | Solidity and filtering | `trawlkit.net.solidity`, `filtering_coefficient` |
| `Mec!N98:P109` | Weights (methods A and B) | `reference_twine_weight_kg`, `panel_weight_air_kg`, `weight_in_water_kg` |
| `Mec!I110:I113` | Weight per plane | `trawlkit.net.split_by_plane` |
| whole sheet | — | `trawlkit.net.analyse(spec, compat)` |

## Assumptions and limits

* **Standard codend with the wrong side** (`codend_minor_side_uses_depth`, `Mec!K36:K37`). The cell
  for the minor side of the upper codend I points to the depth $N = 200$ instead of the edge
  $T_2 = 113$, and the lower codend J copies it. So the codends count $(113 + 200)$ edge meshes
  instead of $(113 + 113)$ and the solid area of the standard net rises from **38.75 to 40.90 m²**
  (+5.5 %); their $S_t$ and their weight also increase. Since the design RN (Aberdeen) is proportional
  to $S_s$, the workbook overestimates the drag of the standard net by that same 5.5 %. The modified
  codend I' is referenced correctly.
* **Double count in the modified $d/l$** (`filtration_double_count`, `Mec!J17`). The sum of mesh
  sizes of the modified net includes the 30 mm of codend I' twice: $\sum m_L = 520$ instead of 490
  and $d/l = 0.01946$ instead of 0.02065 (−5.8 %). It affects all the drag methods based on $d/l$ for
  the modified variant.
* **Twine density** (`twine_density_units`). The weights use the "density" in `P!L55`
  (≈1,152 kg/m³), which does not have units of density; the resulting weight-in-water coefficient
  (0.11) is similar by chance to the 0.10 of polyamide.
* **Weights without number of panels** (`net_weight_ignores_panel_count`, `Mec!O107`, `O109`). The
  total weight adds up the rows without multiplying by the panels of each one (left and right wings,
  upper and lower planes): with the workbook's density, multiplying each row by its count would take
  the 28.3 kg to 45.4 kg (+60 %). Corrected mode multiplies each row by its count (in air, in water
  and in the split by plane), just as $S_s$ and $S_t$ already do; Excel mode reproduces it.
* Global $d/l$ as a quotient of sums gives the same weight to a row of two small panels as to the
  body; an average weighted by $S_t$ would be more representative, but the coefficients of the drag
  formulas were fitted with the workbook's definition.

## Executable example

```{code-cell} ipython3
from trawlkit import Compat
from trawlkit.io import load_net
from trawlkit.net import analyse

G = "mecanica_de_la_red"
std_x = analyse(load_net("fao_a3_standard"), Compat.EXCEL)
mod_x = analyse(load_net("fao_a3_modified"), Compat.EXCEL)
std_c = analyse(load_net("fao_a3_standard"), Compat.CORRECTED)
mod_c = analyse(load_net("fao_a3_modified"), Compat.CORRECTED)

checks = {
    "filtration_index_std": std_x.filtration_index,
    "filtration_index_mod": mod_x.filtration_index,
    "solid_surface_std_m2": std_x.solid_surface_m2,
    "solid_surface_mod_m2": mod_x.solid_surface_m2,
    "working_surface_std_m2": std_x.working_surface_m2,
    "solidity_std": std_x.solidity,
    "net_weight_air_std_kg": std_x.weight_air_kg,
    "net_weight_water_std_kg": std_x.weight_water_kg,
}
for key, value in checks.items():
    assert math.isclose(value, golden(G, key), rel_tol=1e-6), key
for row, ref in zip(std_x.rows, golden(G, "solid_surface_per_panel_m2")):
    assert math.isclose(row.solid_surface_m2, ref, rel_tol=1e-6), row.row.id

cases = (std_x, std_c, mod_x, mod_c)
show = [("d/l", "filtration_index", 5), ("Sₛ [m²]", "solid_surface_m2", 2),
        ("Sₜ [m²]", "working_surface_m2", 1), ("Solidity Sₛ/Sₜ", "solidity", 4),
        ("Weight in air [kg]", "weight_air_kg", 2),
        ("Weight in water [kg]", "weight_water_kg", 2)]
P.md_table(["Quantity", "Standard (Excel)", "Standard (corrected)",
            "Modified (Excel)", "Modified (corrected)"],
           [[lab, *(P.fmt(getattr(g, attr), nd) for g in cases)]
            for lab, attr, nd in show])
```

The errata can be seen in the table: between "Excel" and "corrected", the standard net changes in
$S_s$ and $S_t$ (codends I/J) and the modified one in $d/l$ (double count). The weights change in
both for two causes that pull in opposite directions: per panel they are 20–30 % lower because they
use the correct apparent density of the braided twine (≈868 kg/m³ instead of 1,152; with it the
weight of the reference panel is exactly its length of twine divided by the runnage), but the total
counts all the panels of each row (`net_weight_ignores_panel_count`). The net result is a corrected
weight of about 33 kg in air for the standard net and 35 kg for the modified one, against the
workbook's 28 and 23 kg.

```{code-cell} ipython3
:tags: [hide-input]
ids = [g.row.id for g in std_x.rows]
y = np.arange(len(ids))
h = 0.36
fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.4), sharey=True)
for ax, attr, title, unit in (
    (axes[0], "solid_surface_m2", "Solid area $S_s$", "[m²]"),
    (axes[1], "working_surface_m2", "Working area $S_t$", "[m²]"),
):
    vc = [getattr(g, attr) for g in std_c.rows]
    vx = [getattr(g, attr) for g in std_x.rows]
    ax.barh(y - h / 2 - 0.02, vc, height=h, color=P.SERIES[0], label="Corrected")
    ax.barh(y + h / 2 + 0.02, vx, height=h, color=P.SERIES[1], label="Excel")
    for k, (a, b) in enumerate(zip(vc, vx)):
        if abs(a - b) > 1e-9:
            ax.annotate(f"{P.fmt(a, 2)} → {P.fmt(b, 2)}", xy=(b, k + h / 2), xytext=(5, 0),
                        textcoords="offset points", va="center", fontsize=8, color=P.INK_2)
    ax.set_title(title)
    ax.set_xlabel(f"Area per netting row {unit}")
    ax.grid(axis="y", visible=False)
    ax.margins(x=0.22)
axes[0].set_yticks(y, ids)
axes[0].invert_yaxis()
axes[0].set_ylabel("Netting row (standard net)")
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", ncol=2)
fig.tight_layout(rect=(0, 0.06, 1, 1))
plt.show()
```

By netting row, body G concentrates 38 % of the solid area and 45 % of the working area: it is the
piece that weighs most in the drag. The only rows that change between modes are codends I and J
(erratum `codend_minor_side_uses_depth`); in them the workbook adds 2.15 m² of twine that do not
exist. Because of their $U_1 = 0.23$, the codends have little working area for their solid area,
that is, the highest solidity in the net (≈0.31 against ≈0.10 for the wings).

## Exercises

From the teaching-mode bank, with the data of the book. In the app, the “UTN Classroom” mode
generates them with other data and marks them ({doc}`38_docentes`).

```{code-cell} ipython3
:tags: [remove-input]
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path.cwd().parent))
import _exercises
_exercises.section("12_mecanica_red")
```
