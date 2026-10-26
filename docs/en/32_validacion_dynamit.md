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

# Validation against DynamiT

```{code-cell} ipython3
:tags: [remove-cell]
import sys, pathlib
DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English
import math
import numpy as np
import matplotlib.pyplot as plt
from tests.golden_utils import golden
from trawlkit import drag
import _plots_v as V
V.setup_style()

C, E = V.run_case(150, "corrected"), V.run_case(150, "excel")
kn = C.case.speeds
```

## Purpose

{doc}`31_validacion_excel` shows that `trawlkit` reproduces the Excel workbook. That says nothing
about whether the workbook is right: it validates the migration, not the model. For that an
**independent** reference is needed. The author of the workbook simulated the same FAO A-3 net with
DynamiT and pasted the results into the Excel file (`Res!S302:S310`) and into two screenshots
(`legacy/dynamit_*.png`). This chapter compares those results with the engine's, variable by
variable.

## What DynamiT is

DynamiT is Ifremer's program for simulating and optimizing trawl gear {cite:p}`dynamit`. Unlike the
workbook, which chains empirical rules that are independent of each other (one formula for the drag,
another for the opening, another for the door spread), DynamiT represents the whole gear —netting
panels, ropes, bridles, warps and otter boards— as a flexible structure and seeks its **equilibrium
shape** under the hydrodynamic forces on each twine, the weight, the buoyancy and the contact with
the seabed. The drag, the openings and the door spread come from that same shape, so they are
**consistent with each other**.

That does not make it the truth: it is a model with its own drag coefficients for the twine and the
otter boards, and only a measurement at sea (opening sensors and a dynamometer on the warps) would
tell which of the two is right. But it is an independent physical model, and where it agrees with
the workbook the result gains confidence.

## DynamiT results

The simulation uses the **standard** net: the screenshot `legacy/dynamit_resumen_fao_a3.png` lists
the panels with a mesh bar length of 40, 30 and 20 mm (stretched mesh 80, 60 and 40 mm) and codend
J1 with a 20 mm bar, that is, the standard 40 mm codend. Its total area is **38.76 m²**, which
matches the engine's **corrected** solid area (38.75 m²) and not the workbook's (40.90 m²): an
independent confirmation of the erratum `codend_minor_side_uses_depth` ({doc}`erratas`). The weight
it reports (32.30 kg) lies between the workbook's (28.3 kg, without counting all the panels) and the
corrected engine's (33.5 kg); DynamiT uses its own twine runnages (780 and 1160 m/kg), which are not
those of the workbook.

The results table is transcribed from `legacy/dynamit_resultados_fao_a3.png` (FAO A3 net, speeds
1.0–5.0 kn). The drag row matches the column pasted into the Excel workbook, which verifies the
transcription:

```{code-cell} ipython3
# Transcription of legacy/dynamit_resultados_fao_a3.png (DynamiT, Ifremer; standard FAO A3 net).
# Each number was checked against the enlarged image. Units of the screenshot: m and kg (kgf).
DYNAMIT = {
    "v_kn": [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
    "AH_m": [8.9, 11.2, 12.5, 12.9, 13.3, 13.2, 13.3, 13.5, 13.6],  # horizontal opening
    "AV_m": [6.0, 3.5, 2.4, 1.8, 1.4, 1.2, 1.0, 1.3, 1.6],  # vertical opening
    "DP_m": [28.5, 40.9, 46.6, 49.3, 51.4, 51.6, 52.3, 53.2, 53.4],  # door spread
    "RA_kg": [330.6, 476.0, 704.3, 967.3, 1331.3, 1751.9, 2208.7, 2784.5, 3371.8],  # drag
}
D = {k: np.array(v) for k, v in DYNAMIT.items()}
assert np.allclose(D["v_kn"], kn)
# The DynamiT column pasted in 'Resistencia de la RED'!S398:S406 is the same RA (in kgf).
assert np.allclose(D["RA_kg"], golden("resistencia_de_la_red", "summary_dynamit_std_kgf"), rtol=1e-9)
assert np.allclose(D["RA_kg"] / 1000, golden("resistencia_de_la_red", "summary_dynamit_std_t"), rtol=1e-9)
V.md_table(["Parameter"] + [V.fmt(v, 1) for v in D["v_kn"]],
           [[lab] + [V.fmt(x, 1) for x in D[k]] for lab, k in
            (("AH [m]", "AH_m"), ("AV [m]", "AV_m"), ("DP [m]", "DP_m"), ("RA [kgf]", "RA_kg"))])
```

The screenshot says “kg”: in the context of a drag it is kilogram-force (1 kgf = 9.81 N), the same
unit as the workbook.

## What is compared with what

DynamiT gives a single figure per variable and speed; the workbook has several, of different
nature. It is worth being explicit:

| DynamiT | Engine quantity (workbook cell) | Nature |
|---|---|---|
| AH, horizontal opening | **Fridman DPA**, standard net (`Mec!P164:P172`) | depends on $v$: equilibrium of otter boards, warps and net |
| | Geometric AH (`Dim!F61`) | fixed: average of geometric rules |
| AV, vertical opening | **Fridman AV**, standard net (`Mec!O272:O280`) | depends on $v$: bridle angle from buoyancy and $R_N$ |
| | Suzuki AV (`Mec!D255`) | fixed: fraction of the circumference |
| DP, door spread | **$D_s$ from the Fridman DPA** (`Mec!L164:L172`) | depends on $v$: similar triangles |
| | $D_s$ “per metre of warp” (`Port!E13`) | fixed: $(2.65 - D_6)\,L_s + D_6$ |
| RA, drag | **Design $R_N$**, Aberdeen demersal (`Res!N302:N310`) | net only |
| | Total $R_T$ (`Rem!H118:H126`) | net + floats + warps (+ one otter board in corrected mode) |

In `trawlkit` these are, in the same order, `spread.fridman.dpa_std_m`,
`spread.horizontal_opening_m`, `spread.vertical.fridman.std.av_m`, `spread.vertical.suzuki_m`,
`spread.table.door_spread_from_dpa_m`, `doors.spread_m`, `drag.rn.std` and `warps.total.std` of the
`DesignResult`.

The screenshot does not make clear whether RA is the drag of the net or of the whole gear. It is
compared with both, but the natural reading is the **net**: the author pasted it into the summary
table of net drag, next to the thirteen methods (`Res!S302:S310`), and it is already lower than the
$R_N$ of most of the solid-area methods; if it included two otter boards (≈ 320 kgf at 3 kn
according to the engine) and the warps, DynamiT's net would fall below all of them.

```{code-cell} ipython3
:tags: [hide-input]
def quantities(r):
    return {
        "AH": {"Fridman DPA": np.asarray(r.spread.fridman.dpa_std_m),
               "Geometric AH": np.full(9, r.spread.horizontal_opening_m)},
        "AV": {"Fridman AV": np.asarray(r.spread.vertical.fridman.std.av_m),
               "Suzuki AV": np.full(9, r.spread.vertical.suzuki_m)},
        "DP": {"Ds from Fridman DPA": np.asarray(r.spread.table.door_spread_from_dpa_m),
               "Ds per metre of warp": np.full(9, r.doors.spread_m)},
        "RA": {"Design Rₙ (Aberdeen)": np.asarray(r.drag.rn.std),
               "Total Rₜ": np.asarray(r.warps.total.std)},
    }

QC, QE = quantities(C), quantities(E)
REF = {"AH": D["AH_m"], "AV": D["AV_m"], "DP": D["DP_m"], "RA": D["RA_kg"]}
UNIT = {"AH": "m", "AV": "m", "DP": "m", "RA": "kgf"}
band = (kn >= 2.0) & (kn <= 4.0)  # fishing range

rows = []
for var, ref in REF.items():
    for name in QC[var]:
        for mode, Q in (("corrected", QC), ("Excel", QE)):
            x = Q[var][name]
            e = x - ref
            p = e / ref * 100
            rows.append([var, name, mode, V.sfmt(p[band].mean(), 1),
                         f"{V.fmt(np.abs(e[band]).mean(), 1 if var != 'RA' else 0)} {UNIT[var]}",
                         V.fmt(np.abs(p[band]).mean(), 1), V.fmt(np.abs(p).mean(), 1)])
V.md_table(["DynamiT", "Engine quantity", "Mode", "Bias 2–4 kn [%]", "Abs. error 2–4 kn",
            "Error 2–4 kn [%]", "Error 1–5 kn [%]"], rows)
```

The **bias** is the average of (engine − DynamiT), with sign: positive if the engine gives more. The
**mean error** is the average of its absolute value. The errors are summarized over the fishing
range, 2–4 kn, and over the whole range, 1–5 kn, where the extremes weigh heavily (at 1 kn the net
is poorly opened in both models).

## Comparison by speed

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      DynamiT (dots) against `trawlkit`. Blue: speed-dependent quantity (Fridman or Aberdeen);
      orange: fixed rule or total drag. Solid line: corrected mode; dashed: Excel mode. The grey
      band marks the fishing range, 2–4 kn.
    name: fig-32-dynamit
---
TITLES = {"AH": "Horizontal opening [m]", "AV": "Vertical opening [m]",
          "DP": "Door spread [m]", "RA": "Drag [kgf]"}
LEG = {"AH": "lower right", "AV": "upper right", "DP": "lower right", "RA": "upper left"}
fig, axes = plt.subplots(2, 2, figsize=(9.4, 7.2))
for ax, var in zip(axes.flat, REF):
    ax.axvspan(2.0, 4.0, color=V.GRID, alpha=0.45, lw=0, zorder=0)
    ax.plot(kn, REF[var], "o", color=V.INK, ms=5.5, mec=V.SURFACE, mew=1.2, zorder=4,
            label="DynamiT")
    for k, name in enumerate(QC[var]):
        col = V.SERIES[k]
        ax.plot(kn, QC[var][name], color=col, zorder=3, label=name)
        ax.plot(kn, QE[var][name], color=col, lw=1.1, ls=(0, (3, 2)), zorder=2)
    ax.legend(loc=LEG[var], fontsize=8.5, handlelength=1.6)
    ax.set_title(TITLES[var])
    ax.set_xlim(0.85, 5.15)
    ax.set_xticks(np.arange(1, 5.5, 1))
    ax.set_ylim(bottom=0)
for ax in axes[1]:
    ax.set_xlabel("Towing speed [kn]")
fig.tight_layout(w_pad=2.0)
plt.show()
```

```{code-cell} ipython3
:tags: [hide-input]
lines = [("AH DynamiT [m]", D["AH_m"], 1), ("Fridman DPA [m]", QC["AH"]["Fridman DPA"], 1),
         ("AV DynamiT [m]", D["AV_m"], 1), ("Fridman AV [m]", QC["AV"]["Fridman AV"], 2),
         ("DP DynamiT [m]", D["DP_m"], 1), ("Fridman Ds [m]", QC["DP"]["Ds from Fridman DPA"], 1),
         ("RA DynamiT [kgf]", D["RA_kg"], 0), ("Aberdeen Rₙ [kgf]", QC["RA"]["Design Rₙ (Aberdeen)"], 0)]
rows = [[lab] + [V.fmt(x, nd) for x in arr] for lab, arr, nd in lines]
rows.append(["Δ Rₙ [%]"] + [V.pct_s(a, b) for a, b in zip(QC["RA"]["Design Rₙ (Aberdeen)"], D["RA_kg"])])
V.md_table(["v [kn]"] + [V.fmt(v, 1) for v in kn], rows)
```

## Which drag method is closest to DynamiT?

The workbook's design $R_N$ is Aberdeen demersal, but there are twelve more ({doc}`14_resistencia`).
With DynamiT as the reference they can be ranked:

```{code-cell} ipython3
:tags: [hide-input]
NAMES = {"tauti_nomura_shu": "Tauti, Nomura and Shu", "tauti_headrope": "Tauti (headrope)",
         "tauti_footrope": "Tauti (footrope)", "koyama_1974": "Koyama 1974",
         "koyama_1984": "Koyama 1984", "hamuro": "Hamuro", "reid": "Reid",
         "robertson": "Robertson", "maclennan": "MacLennan",
         "aberdeen_demersal": "Aberdeen demersal (design)", "aberdeen_pelagic": "Aberdeen pelagic",
         "fridman": "Fridman", "dickson": "Dickson"}
ra = D["RA_kg"]
def score(r, m):
    x = np.asarray(r.drag.table.std[m]) * 1000
    p = (x - ra) / ra * 100
    return p.mean(), np.abs(p).mean(), np.abs(p[band]).mean()
sc = {m: (score(C, m), score(E, m)) for m in NAMES}
order = sorted(NAMES, key=lambda m: sc[m][0][1])
# DynamiT speed exponent: RA ∝ v^n
n_dyn = np.polyfit(np.log(kn), np.log(ra), 1)[0]
rows = []
for m in order:
    (bc, ac, gc), (be, ae, ge) = sc[m]
    name = f"**{NAMES[m]}**" if m == drag.DESIGN_METHOD else NAMES[m]
    rows.append([name, V.sfmt(bc, 1), V.fmt(ac, 1), V.fmt(gc, 1), V.fmt(ae, 1)])
V.md_table(["Method (standard net)", "Bias corrected [%]", "Mean error corrected 1–5 kn [%]",
            "Mean error corrected 2–4 kn [%]", "Mean error Excel 1–5 kn [%]"], rows)
print(f"DynamiT: RA ∝ v^{n_dyn:.2f}")
```

## Discussion

**Drag.** The design $R_N$ (Aberdeen demersal) lies **above** DynamiT at all speeds: +18 % on
average in corrected mode and +25 % in Excel mode. The difference is greatest between 1.5 and
2.5 kn (+23 to +26 % in corrected mode), where Aberdeen's constant term (the friction of the parts
dragging on the seabed) still weighs, and drops to +9 % at 5 kn. Correcting the solid area of the
codend brings the workbook 6–7 points closer to DynamiT. The methods closest to the simulation are
Reid in corrected mode, Robertson and Tauti with the footrope (mean errors of 14–17 % over 1–5 kn,
7–13 % in the fishing range); Reid is so only once the fixed denominator
(`reid_fixed_denominator`) is corrected, which in the Excel workbook gives it a mean error of 55 %.
The shape of the curve also tells something: DynamiT grows as $v^{1.48}$, very close to the 1.45
exponent of Tauti, Nomura and Shu and far from the $v^2$ of the pure quadratic formulas: the net
deforms and aligns with the flow as it speeds up, and a shape simulator captures this without anyone
fitting it. For design, the choice of Aberdeen is **conservative**: ≈ 18 % more drag means, in the
window of {doc}`30_caso_beagle`, somewhat lower maximum speeds than DynamiT would give.

**Horizontal opening.** This is the variable with the best agreement. The workbook's geometric AH
(13.1 m) falls right on the plateau that DynamiT reaches from 2.5 kn on (12.9–13.6 m): mean error of
2 % in the fishing range. The Fridman DPA crosses DynamiT at 3 kn, with a mean bias below 1 % and a
mean error of 7 % between 2 and 4 kn, but with a different slope: it underestimates at 2 kn (−12 %)
and overestimates at 4 kn (+12 %). Outside the range the curves part ways. Below 2 kn Fridman closes
the net much faster than the simulation (6.0 versus 8.9 m at 1 kn): its model assumes otter boards,
warps and net aligned and taut, and at low speed the force of the otter boards, which grows with
$v^2$, is not enough to tension them. Above 4 kn the Fridman DPA keeps growing (16.1 m at 5 kn)
while DynamiT levels off at 13.5 m: in the simulation the ropes and the netting, of fixed length,
limit the opening; in Fridman's formula nothing limits it.

**Vertical opening.** Both models agree on the trend —the net “flattens” as it speeds up because the
drag grows faster than the buoyancy— and on the order of magnitude in the fishing range
(1.0–2.6 m). The Fridman AV overestimates by 14–17 % between 2 and 4 kn and does not reproduce two
features of DynamiT: the large opening at 1 kn (6 m), where the net has almost no tension, and the
**upturn** above 4 kn (1.0 → 1.6 m). That upturn is a shape effect that a formula based on a single
bridle angle cannot have: with more speed the distribution of tensions among the headrope, the wings
and the bridles changes, or the footrope begins to lift off the seabed. The Suzuki AV (1.98 m, mean
error of 47 %) is only a reference number for the drawing.

**Door spread.** This is the largest discrepancy. DynamiT spreads the otter boards 47–52 m apart in
the fishing range; the workbook, 32.5 m with the “per metre of warp” rule (−35 % on average) and
25–34 m with the one derived from the Fridman DPA (−40 %). There are two reasons. The first is
methodological: the two rules of the workbook are geometric or empirical (how far a generic otter
board spreads per metre of warp; similar triangles from the DPA), whereas DynamiT computes the
spreading force of **this** otter board with its polar. The second is about data: we do not know the
warp paid out or the sweep length of the simulation, and the door spread is very sensitive to both.
It is the variable on which the final design should rely on simulation or measurement. Fortunately
it is also the one that least affects the other stages of the workbook, which use $D_s$ only through
the warp angles.

**Why they disagree.** The workbook is a chain of empirical rules, each one fitted on other nets and
other vessels, and evaluated independently: the drag does not “know” how much the net opened, nor
the opening how far apart the otter boards went. DynamiT forces all quantities to come from the same
equilibrium shape. Where the workbook uses a formula based on the dominant physical mechanism (the
solid area for the drag, Fridman's force balance for the DPA, the bridle angle for the AV) the two
tools agree within 2–20 % in the fishing range; where it uses a rule of thumb (door spread per metre
of warp, AV as a fraction of the circumference), the discrepancy reaches 35–47 %.

**A shape simulation of our own.** {doc}`21_simulacion` adds to `trawlkit` a simplified physical
model of the towed net (netting of triangular elements with Morison drag, ropes, floats, ballast,
bridles and seabed contact) and compares it with this same DynamiT table. With the engine's door
spread, the simulated horizontal opening stays within 3 % of DynamiT between 2 and 4 kn —with the
same plateau that the Fridman DPA lacks— and the vertical one with a bias of ≈ +10 %, but the
simulated drag is half of DynamiT's, a gap that twine coefficients within the ranges of the
literature do not close. The simulation therefore serves for the shape and the openings; the design
drag is still the engine's.

**Limitations of this comparison.** A single simulation, whose author and date are not documented in
the repository, without the rigging parameters (warp paid out, sweeps, otter board, angle of attack,
seabed type) or the DynamiT version; a single net and a single depth. Neither of the two models was
compared with measurements at sea.
