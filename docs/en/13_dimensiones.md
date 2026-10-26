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

# Net dimensions

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

The main dimensions —length of the **headrope** (upper rope) and of the **footrope** (lower rope),
total length, circumference of the mouth— are the ones the owner recognizes and the ones used by the
drag methods, the openings and the rigging. This stage derives them from the panels
({doc}`11_panos_y_cortes`): first it rigs the ropes piece by piece (Martini {cite:p}`martini`),
then it measures lengths and circumferences, and finally it compares the proportions of the net with
those of reference nets (Nomura {cite:p}`nomura1981`) and with Fujiishi's length factor
{cite:p}`fujiishi`.

## Theory

### Ropes by pieces (Martini)

Each rope is made of two equal wing pieces and a central piece, the **bosom**. The wing piece of the
headrope is the cut edge of the wing tip and of the upper wing, which in the wing cuts measures
approximately its stretched depth:

$$
\ell_{\text{ala}} = \frac{(N_A + N_C)\,m_L}{1000},
$$ (eq-lima-ala)

and the bosom is half of what the mouth edge of the square exceeds the two joining edges of the
wings:

$$
\ell_{\text{boc}} = \frac{T_E\,m_{L,E} - 2\,T_C\,m_{L,C}}{2000}.
$$ (eq-lima-bocana)

On the footrope, the wing piece also adds the second section of the lower wing (F) and the bosom is
measured on the first body panel of the belly. Each piece is corrected by a **hanging ratio** $E$
—the ratio between the length of the rope and that of the netting mounted on it— and the rope is

$$
L_{\text{relinga}} = 2\,E_{\text{ala}}\,\ell_{\text{ala}} + E_{\text{boc}}\,\ell_{\text{boc}},
$$ (eq-relinga)

with $E_{\text{ala}} = 1.05$ (the rope is 5 % longer than the bar-cut edge, which works taut and
diagonally) and $E_{\text{boc}} = 0.83$ (the mesh edge of the bosom is mounted gathered on the rope).
For the A-3: headrope $= 2\cdot 13.104 + 2.49 = 28.70$ m and footrope $= 2\cdot 15.624 + 2.14 =
33.39$ m. The footrope is longer than the headrope: the headrope advances over the footrope (the
square forms an overhang) so that the fish that rises as the footrope passes does not escape over the
top.

### Lengths and circumferences

The **total length** $b$ is the sum of the stretched depths of the belly panels, codend included
(42.68 m in the standard net, 41.68 m in the modified one); the length without codend $L$ (32.68 m) is
that of the back (upper panel). The **fishing circle** is the stretched perimeter of the mouth of the
body, back plus belly:

$$
a = FC = \frac{(T_{D1} + T_{V1})\,m_L}{1000} = \frac{(372 + 372)\cdot 60}{1000} = 44.64\ \text{m}.
$$ (eq-fc)

It is the size measure used by the Japanese drag formulas and by the percentage-based vertical
opening formulas. Its ratio to the body length (2.51 in the A-3) indicates whether the net is “short
and wide” or “long and narrow”.

### Length factor (Fujiishi)

Fujiishi proposes checking the consistency between headrope, footrope and square with

$$
F_L = \frac{L_{\text{lima}} + 2\,N_E\,m_{L,E}/1000}{L_{\text{burlón}}} ,
$$ (eq-fujiishi)

that is, the headrope plus twice the depth of the square (the overhang, there and back) against the
footrope. $F_L \approx 1$ indicates that the overhang exactly compensates the difference in length
between the ropes; the A-3 gives 1.006.

### Nomura's proportions

Nomura tabulates, for different types of net, the dimensionless ratios between headrope $l$,
footrope $m$, total length $b$, circumference $a$, upper wing $c$, lower wing $d$, back $e$ and
codend $f$:

$$
\frac{l}{m},\ \frac{l}{b},\ \frac{m}{b},\ \frac{a}{b},\ \frac{c}{b},\ \frac{d}{b},\ \frac{e}{b},\
\frac{f}{b},\ \frac{d-c}{b}.
$$ (eq-nomura-prop)

Comparing them with those of proven nets of the same type (here, “bottom trawl, 2 panels”) is a quick
design check: a proportion far from the reference points to a disproportionate piece.

## Coefficients

| Quantity | Value | Unit | Source | Excel cell |
|---|---|---|---|---|
| Hanging ratio of the wings | 1.05 | — | Martini | `Dim!C142`, `C150` |
| Hanging ratio of the bosom | 0.83 | — | Martini | `Dim!G142`, `G150` |
| Hanging ratio of the wing tip (reinforcement) | 1 | — | — | `Dim!C157` |
| Depth and mesh size of the square | 40 / 60 | meshes / mm | plan | `Dim!F85:F86` |
| Reference proportions | row “Red de Fondo, 2 caras” [bottom trawl, 2 panels] | — | Nomura | `Tab!A16:L16` |

## Excel ↔ `trawlkit` equivalence

| Cell(s) | Content | Function |
|---|---|---|
| `Dim!C140`, `F140` | Headrope pieces | `headrope_wing_piece_m`, `headrope_bosom_piece_m` |
| `Dim!C148`, `F148` | Footrope pieces | `footrope_wing_piece_m`, `footrope_bosom_piece_m` |
| `Dim!C143`, `G143`, `C151`, `G151` | Corrected pieces | `trawlkit.dimensions.corrected_piece_m` |
| `Dim!F45` | Headrope | `trawlkit.dimensions.headrope_length_m` |
| `Dim!F46` | Footrope | `trawlkit.dimensions.footrope_length_m` |
| `Dim!F47:F54` | Lengths by plan and piece | `trawlkit.dimensions.compute` |
| `Dim!F49`, `D97` | Maximum circumference and fishing circle | `max_circumference_m`, `fishing_circle_m` |
| `Dim!D89` | Length factor | `trawlkit.dimensions.length_factor` |
| `Dim!D103`, `D109` | Body length, FC/body | `trawlkit.dimensions.fc_body_ratio` |
| `Dim!C124:E132` | Nomura's proportions | `nomura_ratios`, `load_nomura_reference` |
| `Dim!C155`, `Cab!J5` | Wing tip reinforcement | `wingtip_reinforcement_m`, `wingtip_reinforcement_rope_m` |

## Assumptions and limits

* **Truncated footrope** (`footrope_mid_truncation`, `Dim!F46`). The formula applies `MID()` to
  numbers: 15.624 → "15.6" and 2.1414 → "2.1", so the workbook uses **33.3 m** instead of
  **33.389 m**. The difference (−0.27 %) propagates to everything that uses the name `Burlon`:
  Fujiishi's factor, Nomura's proportions, Tauti (footrope), the geometric door spread (DPA) and the
  ballast. It also depends on the regional settings: with a decimal comma `MID` would return
  something else.
* **Modified length** (`mod_length_wrong_rows`, `Dim!G48`). The column of the modified net adds rows
  of the lower plan instead of the back; in the A-3 both plans measure 32.68 m and the number does not
  change.
* **Reference erratum** (`nomura_ratio_typo`). In Nomura's table, two rows have $a/b = 10.6$ where it
  should be 1.06; it does not affect the row used here.
* The ropes by pieces assume wings with a bar-cut edge and a bosom with a mesh edge; the hanging
  ratios 1.05 and 0.83 are practical values, not the result of a force balance. Nomura's proportions
  are a statistical check, not an optimality criterion.

## Executable example

```{code-cell} ipython3
from trawlkit import Compat
from trawlkit.io import load_net
from trawlkit.dimensions import compute

G = "dimensiones_de_la_red"
dx = compute(load_net("fao_a3_standard"), compat=Compat.EXCEL, modified=False)
dc = compute(load_net("fao_a3_standard"), compat=Compat.CORRECTED, modified=False)

checks = {
    "headrope_m": dx.headrope_m,
    "footrope_m": dx.footrope_m,
    "headrope_wing_corrected_m": dx.headrope.wing_corrected_m,
    "footrope_bosom_corrected_m": dx.footrope.bosom_corrected_m,
    "total_length_belly_std_m": dx.total_length_m,
    "fishing_circle_m": dx.fishing_circle_m,
    "body_length_m": dx.body_length_m,
    "length_factor": dx.length_factor,
    "fc_body_ratio": dx.fc_body_ratio,
}
for key, value in checks.items():
    assert math.isclose(value, golden(G, key), rel_tol=1e-6), key
for a, b in zip(dx.nomura_ratios.values(), golden(G, "nomura_ratio_fao_a3")):
    assert math.isclose(a, b, rel_tol=1e-6)

labels = {"headrope_m": "Headrope [m]", "footrope_m": "Footrope [m]",
          "total_length_m": "Total length with codend b [m]",
          "body_length_no_bag_m": "Length without codend L [m]",
          "fishing_circle_m": "Fishing circle a [m]",
          "length_factor": "Length factor (Fujiishi)",
          "fc_body_ratio": "FC / body length"}
P.md_table(["Quantity", "Excel", "Corrected"],
           [[lab, P.fmt(getattr(dx, k), 4), P.fmt(getattr(dc, k), 4)]
            for k, lab in labels.items()])
```

```{code-cell} ipython3
:tags: [hide-input]
fig, ax = plt.subplots(figsize=(9.2, 2.6))
for k, (name, rope) in enumerate((("Headrope", dc.headrope), ("Footrope", dc.footrope))):
    w, b = rope.wing_corrected_m, rope.bosom_corrected_m
    left = 0.0
    for part, length, colour in (("wing", w, P.SERIES[0]), ("bosom", b, P.SERIES[1]),
                                 ("wing", w, P.SERIES[0])):
        ax.barh(k, length - 0.06, left=left + 0.03, height=0.5, color=colour)
        ax.text(left + length / 2, k, P.fmt(length, 2), ha="center", va="center", fontsize=8.5,
                color="white" if colour == P.SERIES[0] else P.INK)
        left += length
    ax.annotate(f"{P.fmt(left, 3)} m", xy=(left, k), xytext=(6, 0), textcoords="offset points",
                va="center", fontsize=9, color=P.INK)
ax.set_yticks([0, 1], ["Headrope", "Footrope"])
ax.invert_yaxis()
ax.set_xlim(0, 37)
ax.set_xlabel("Rope length, pieces corrected by the hanging ratio [m]")
ax.grid(axis="y", visible=False)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=P.SERIES[0], label="Wing (hanging ratio 1.05)"),
                   Patch(color=P.SERIES[1], label="Bosom (hanging ratio 0.83)")],
          loc="lower right", ncol=2, bbox_to_anchor=(1, 1.0))
fig.tight_layout()
plt.show()
```

Composition of the ropes (corrected values, without the `MID` truncation). The wings are almost the
whole length; the bosom of the footrope is shorter than that of the headrope because the belly is
narrower at the mouth than the square.

```{code-cell} ipython3
:tags: [hide-input]
import csv
from trawlkit.io.loader import DATA_DIR
from trawlkit.dimensions import NOMURA_LABELS

with open(DATA_DIR / "reference" / "nomura_proportions.csv", encoding="utf-8") as fh:
    ref_rows = [r for r in csv.DictReader(fh) if r["net_type"] == "Red de Fondo, 2 caras"]
labels = [lab for lab, _ in NOMURA_LABELS]
lo = [min(float(r[col]) for r in ref_rows) for _, col in NOMURA_LABELS]
hi = [max(float(r[col]) for r in ref_rows) for _, col in NOMURA_LABELS]
a3 = [dc.nomura_ratios[lab] for lab in labels]

fig, ax = plt.subplots(figsize=(9.2, 4.0))
y = np.arange(len(labels))
for k in y:
    ax.plot([lo[k], hi[k]], [k, k], color=P.BLUE_150, lw=9, solid_capstyle="round", zorder=1)
ax.scatter(lo + hi, list(y) * 2, s=28, color=P.BLUE_300, zorder=2,
           label="Nomura reference (bottom trawl, 2 panels)")
ax.scatter(a3, y, s=64, color=P.SERIES[1], edgecolor=P.SURFACE, linewidth=2, zorder=3,
           label="FAO A-3 standard")
for k, val in enumerate(a3):
    ax.annotate(P.fmt(val, 2), xy=(val, k), xytext=(0, 9), textcoords="offset points",
                ha="center", fontsize=8, color=P.INK_2)
ax.set_yticks(y, [f"${lab}$" if lab != "(d-c)/b" else "$(d-c)/b$" for lab in labels])
ax.invert_yaxis()
ax.set_xlabel("Proportion (dimensionless)")
ax.grid(axis="y", visible=False)
ax.legend(loc="lower right")
fig.tight_layout()
plt.show()
```

Against the two two-panel bottom trawls of Nomura's table (blue band), almost all the proportions of
the A-3 fall outside the range, and they do so consistently: the headrope is long ($l/m = 0.86$
against 0.71–0.74; $l/b$ and $c/b$ above) and the footrope and the lower wing short ($m/b$, $d/b$
below), so that the wing difference $(d-c)/b = 0.06$ is half the reference one. It is a net with a
short square overhang, with little advance of the headrope over the footrope; the back and the codend
are also relatively short. The relative circumference $a/b$ (1.05) is just below the usual. None of
this is an error —the A-3 is a proven FAO design for small vessels—, but it explains why its vertical
opening and the escape over the headrope should be watched ({doc}`16_aberturas`).

## Exercises

From the bank of the teaching mode, with the book's data. In the app, the “UTN Classroom” mode
generates them with other data and marks them ({doc}`38_docentes`).

```{code-cell} ipython3
:tags: [remove-input]
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path.cwd().parent))
import _exercises
_exercises.section("13_dimensiones")
```
