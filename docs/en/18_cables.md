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

# Warps

## Purpose

The warps (towing wires) transmit the pull of the vessel to the otter boards and, through their
length, set the depth and the spread of the otter boards. They must be sized twice:
**hydrodynamically**, because their drag adds to that of the gear, and **structurally**, because
they must withstand the working tension with a margin for snatches and fasteners on the seabed.

This chapter reproduces the *Cables de Remolque* sheet [Warps] and the warp selection of *Cables Y
Cabulleria* [Wires and Ropes]. It uses the geometry of the otter boards and the rigging
({doc}`15_portones_aparejo`), the drag of the net ({doc}`14_resistencia`) and of the floats
({doc}`17_flotacion_lastre`), and delivers the total drag that is compared with the pull in
{doc}`19_ventana_velocidad`. In `trawlkit` it lives in `trawlkit.rigging.warps`.

## Theory

### Warp angles

Three angles describe the geometry of the system, all from lengths already known:

$$
\delta_1 = \arcsin\!\frac{d + h}{L_s}, \qquad
\delta_2 = \arcsin\!\frac{D_s - a}{2\,L_s}, \qquad
\delta_3 = \arcsin\!\frac{D_s - DPA}{2\,(L_p + V_s)}
$$ (eq-18-angulos)

$\delta_1$ is the **declination** of the warp in the vertical plane (depth $d$ plus the vessel's
depth (moulded) $h$, over the warp paid out $L_s$); $\delta_2$ the **divergence** in plan, the same
{eq}`eq-15-divergencia` of the otter board chapter; and $\delta_3$ the angle of the bridles and
sweeps, with the DPA from similar triangles $DPA = D_s\,m/(m + L_p + V_s)$ ($m$ = footrope). In
bottom trawling $\delta_1$ is usually between 10 and 20°: with smaller $L_s/d$ ratios the warp
pulls the otter boards upwards and lifts them off the seabed.

### Diameter

The book estimates the diameter with two rules. The first, intended for vessels of more than
500 HP, scales with the effective towing power:

$$
D_w = 18 + 0.0034\cdot EHP \quad [\text{mm}]
$$ (eq-18-d-ehp)

The second is the logarithmic fit of {cite:t}`perezaguila2010` for inshore (roadstead or estuary)
vessels:

$$
D_w = 5.6822\,\ln(NHP) - 17.225 \quad [\text{mm}]
$$ (eq-18-d-aguila)

For 150–180 HP the EHP rule is outside its range (it gives ≈ 18 mm almost independently of the
power), so the book adopts the Pérez Águila fit with the power of the largest vessel of the class,
180 HP: $D_w$ = 12.28 mm.

### Hydrodynamic drag of the warp

A warp inclined to the current receives a much smaller force than a perpendicular one. The drag
formula for the two warps is that of a long body of frontal area $D_w L_s$:

$$
R_W = 2\cdot\tfrac12\,C_D\,\frac{\rho}{g}\,D_w\,L_s\,v^2
$$ (eq-18-rw)

and all the physics is in $C_D$. {cite:t}`nomurayamazaki` tabulate $C_D$ as a function of the angle
of attack $\alpha$ between the warp and the flow: 0.02 at 0°, 0.04 at 10°, 0.09 at 20°, 0.18 at
30° and 0.30 at 40°. The book takes $\alpha = \delta_2$ = 4.3° and the nearest tabulated value,
0.02 (erratum `warp_cd_horizontal_angle`). The angle between the warp axis and the towing direction
combines the declination $\delta_1$ and the divergence $\delta_2$:

$$
\alpha = \arccos(\cos\delta_1\,\cos\delta_2)
$$ (eq-18-alpha)

and `Compat.CORRECTED` uses it with linear interpolation in the table (bounded to 0.02 and 0.30 at
the ends): for the FAO A-3 case, $\delta_1$ = 12.06° and $\delta_2$ = 4.30° give $\alpha$ = 12.80°
and $C_D$ = 0.054, 2.7 times the book value.

As references, the sheet also computes the warp as a **cylinder in cross-flow**
($C_D$ = 1.1–1.2 for $Re = v D_w/\nu \approx 10^4$) and the coefficient of {cite:t}`maclennan1981`
for wires normal to the flow,

$$
C_D = 2.11 - 12.24\,v\,D_w \qquad (D_w \text{ in m})
$$ (eq-18-maclennan)

Both assume the warp is perpendicular to the current and are therefore very generous upper bounds.
Practical experience sums up the problem as a fraction of the pull: the drag of the warps is 4 to
10 % of $F_T$ (Craig 4 %, Podeur 5–8 %, Hansen 5 %, Gudnasson 5–10 %, Nomura 4–10 %;
{cite:p}`warpshare`). {cite:t}`kowalskigianotti` propose $C_D$ = 0.02 for wires almost aligned with
the flow, the same value the book uses.

### Total drag, weight and loads

The total drag the vessel must tow is

$$
R_T = R_N + R_B + R_W\,(+R_{OB})
$$ (eq-18-rt)

where the otter board term is missing in the Excel workbook (erratum `warp_total_omits_doors`, see
{doc}`19_ventana_velocidad`). The weight of the steel wire is estimated with
$w_{air} = \tfrac12(0.00368 + 0.00417)\,D_w^2$ kg/m ($D_w$ in mm) and in water
$w_{water} = 0.87\,w_{air}$.

The **working load** is the total drag at the maximum design speed (3.5 kn), and the **minimum
breaking load** is obtained with a safety factor $n_s = 4$:

$$
T_{rot} \ge n_s\,R_T(v_{dis}), \qquad n_s = 4
$$ (eq-18-rotura)

It is a conservative assumption: each of the two warps carries roughly half of $R_T$, so the
effective factor per warp is ≈ 8. The margin covers the dynamic loads (pitching of the vessel,
fasteners on the seabed), which can multiply the mean tension several times.

Finally, the warp is chosen from the catalogue (compacted 6×19+1 Seale steel wire) as the
**smallest diameter that satisfies both** $D \ge D_w$ and $T_{rot}$, and the quantity to buy is
$2\,L_s + 0.5\,L_s$ (two warps plus a 50 % reserve to pay out more on deeper grounds and to cut off
worn ends).

## Coefficients

| Symbol | Value | Unit | Source | Cell |
|---|---|---|---|---|
| $h$ (moulded depth) | per vessel | m | Tipo de buques [Vessel types] | `Rem!E33` |
| EHP rule | 18; 0.0034 | mm; mm/HP | rule of thumb (> 500 HP) | `Rem!F73` |
| Pérez Águila | 5.6822; −17.225 | mm | {cite:t}`perezaguila2010` | `Rem!E80` |
| sizing NHP | 180 | HP | largest vessel of the class | `Rem!E78`, `E110` |
| $C_D(\alpha)$ | 0.02 … 0.30 (0–40°) | — | {cite:t}`nomurayamazaki` | `Rem!A90:B94`, `E106` |
| cylinder $C_D$ | 1.1 (≤ 2.5 kn); 1.2 (≥ 3 kn) | — | — | `Rem!E167:E175` |
| MacLennan | 2.11; −12.24 | — | {cite:t}`maclennan1981` | `Rem!D227` |
| $R_W/F_T$ | 4–10 % | — | {cite:p}`warpshare` | `Rem!D184:H184` |
| weight in air | ½(0.00368 + 0.00417)·$D^2$ | kg/m | catalogue | `Rem!E248` |
| weight in water | 0.87 × air | — | — | `Rem!F252` |
| $v_{dis}$ | 3.5 | kn | — | `Rem!E267` |
| $n_s$ | 4 | — | — | `Rem!D271` |
| warp reserve | 0.5·$L_s$ | m | — | `Cab!D12` |

## Excel ↔ `trawlkit` equivalence

| Cell(s) | Calculation | Function |
|---|---|---|
| `Rem!F17`, `F19` | DPA from similar triangles | `rigging.dpa_similar_triangles_m` |
| `Rem!E25`, `E29`, `E33` | $\delta_2$, $\delta_3$, $\delta_1$ | `rigging.warp_angles_deg` |
| `Rem!F73:F74` | diameter from EHP | `rigging.warp_diameter_ehp_mm` |
| `Rem!E80:E81` | Pérez Águila diameter | `rigging.warp_diameter_aguila_mm` |
| `Rem!E106` | Nomura–Yamazaki $C_D$ | `rigging.warp_cd` |
| `Rem!G118:G126` | $R_W$ | `rigging.warp_drag_kgf` |
| `Rem!H118:I126` | $R_T$ | `rigging.total_drag_kgf` (erratum `warp_total_omits_doors`) |
| `Rem!D167:G175` | warp as a cylinder | `rigging.warp_drag_cylinder` |
| `Rem!E191:H199` | $R_W$ as % of $F_T$ | `rigging.warp_drag_share_kgf` |
| `Rem!D227:D235` | MacLennan $C_D$ | `rigging.warp_cd_maclennan` |
| `Rem!E248:F257` | weights | `rigging.warp_weight` |
| `Rem!E267`, `E272` | working and breaking load | `rigging.working_load_and_breaking_load` |
| `Cab!D11:I11` | selection | `rigging.select_warp` (erratum `warp_undersized`) |
| `Cab!D12` | quantity | `rigging.warp_quantity_m` |
| whole sheet | `warps` stage | `model.run` → `result.warps` |

## Assumptions and limits

- **Angle of attack** (erratum `warp_cd_horizontal_angle`, `Rem!E103:E106`). The book enters the
  Nomura–Yamazaki table with the divergence in plan $\delta_2$ (4.3°) and ignores the declination
  $\delta_1$ (12.1°), which is the dominant angle between the warp and the flow. The corrected mode
  uses {eq}`eq-18-alpha` ($\alpha$ = 12.8°, $C_D$ = 0.054) and $R_W$ grows 2.7 times. Even so,
  between 2 and 3.5 kn $R_W$ is 1.1–4.0 % of $F_T$ (fixed pitch, 150 HP), at the lower edge of or
  below the 4–10 % of the literature: the Nomura–Yamazaki table gives low warp drags, although
  their weight in the total is small (≈ 1.8 % of $R_T$ at 3.5 kn). No coefficient is adjusted to
  bring it closer to the band.
- **Discrete table.** `Rem!E106` takes the **nearest** tabulated angle (without interpolating), so
  $C_D$ jumps in 10° steps; the corrected mode interpolates linearly.
- **Diameter from power.** Both diameter rules are fleet correlations; the governing criterion is
  the breaking load.
- **Erratum `warp_undersized`** (`Cab!D11`). The sheet chooses the warp with
  `LOOKUP(Rem!E264, diamremolque, …)`: the largest catalogue diameter that does not exceed the
  minimum of 12.28 mm, that is, **12 mm**, whose breaking load (8.55 t) is less than the 8.80 t
  required by {eq}`eq-18-rotura`. The selected warp is both thinner than the minimum diameter and
  weaker than the minimum load. `Compat.CORRECTED` chooses the smallest warp that meets both
  conditions: **13 mm, 10.3 t** ({doc}`erratas`).

## Executable example

```{code-cell} ipython3
import math
import sys, pathlib
DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English

import numpy as np

from tests.golden_utils import golden
from trawlkit import Compat, rigging
import _plots_t2 as P

REM, CAB = "cables_de_remolque", "cables_y_cabulleria"
r = P.fao_result(150, "excel")
w = r.warps


def close(actual, key, sheet=REM):
    """Compare with the Excel value (scalar or series) at rtol = 1e-6."""
    got, exp = np.atleast_1d(actual), np.atleast_1d(golden(sheet, key))
    return all(math.isclose(a, b, rel_tol=1e-6) for a, b in zip(got, exp))


assert close(w.angles.declination_deg, "warp_declination_deg")
assert close(w.angles.bridle_divergence_deg, "bridle_divergence_deg")
assert close(w.diameter_mm, "warp_diameter_aguila_180_mm")
assert close(w.cd, "warp_cd")
assert close(w.drag_kgf, "warp_drag_2_kgf")
assert close(w.total.std, "total_drag_std_kgf")  # RN + RB + Rw, without ROB
assert close(w.cd_maclennan, "warp_cd_maclennan")
assert close(w.weight.total_water_kg, "warp_total_weight_water_kg")
assert close(w.loads.min_breaking_load_kgf, "warp_min_breaking_load_kgf")
assert close(w.selection.breaking_load_t, "warp_strength_t", CAB)  # 8.55 t
assert close(w.quantity_m, "warp_quantity_m", CAB)

a = w.angles
print(f"δ1 = {a.declination_deg:.2f}°, δ2 = {a.divergence_deg:.2f}°, "
      f"δ3 = {a.bridle_divergence_deg:.2f}°")
print(f"Ø: EHP {w.diameter_ehp_mm:.2f} mm, "
      f"Águila 150 HP {w.diameter_aguila_mm:.2f} mm, "
      f"Águila 180 HP {w.diameter_mm:.2f} mm")
i = r.case.speed_index(3.5)
print(f"At 3.5 kn: RN = {r.drag.rn.std[i]:.0f}, RB = {r.floats.drag_kgf[i]:.1f}, "
      f"Rw = {w.drag_kgf[i]:.1f} → RT = {w.total.std[i]:.0f} kgf")
print(f"Minimum breaking load = 4 × {w.loads.working_load_kgf:.0f} "
      f"= {w.loads.min_breaking_load_kgf:.0f} kgf")
print(f"In-water weight of the warp paid out = {w.weight.total_water_kg:.0f} kg; "
      f"to buy {w.quantity_m:g} m")
```

The selection erratum, with the same loads in both modes:

```{code-cell} ipython3
need = w.loads.min_breaking_load_kgf
sx = rigging.select_warp(w.diameter_mm, need, compat=Compat.EXCEL)
sc = rigging.select_warp(w.diameter_mm, need, compat=Compat.CORRECTED)
assert sx.diameter_mm == golden(CAB, "warp_diameter_mm") == 12
assert sc.diameter_mm == 13
for tag, sel in (("Excel", sx), ("corrected", sc)):
    ok = "meets" if sel.satisfies_breaking_load else "does NOT meet"
    print(f"{tag:>9}: {sel.diameter_mm:g} mm, breaking load {sel.breaking_load_t} t "
          f"→ {ok} the {need / 1000:.2f} t")
```

Four ways of estimating $R_W$ give results that differ by two orders of magnitude
({numref}`fig-18-rw`): Nomura–Yamazaki, with $C_D$ = 0.02 as in the book or with the combined angle
of attack of the corrected mode, the empirical band of 5–10 % of the pull and the two bounds for a
warp perpendicular to the flow.

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Drag of the two warps (12.28 mm, 200 m) by method, on a logarithmic scale. The band is
      5–10 % of the available pull (fixed pitch, 150 HP). The cylinder and MacLennan methods treat
      the warp as perpendicular to the current.
    name: fig-18-rw
---
P.setup()
kn, v = r.case.speeds, r.case.speeds_ms
alpha = rigging.warp_attack_angle_deg(a.declination_deg, a.divergence_deg)
cd_c = rigging.warp_cd(alpha, interpolate=True)
rw_corr = rigging.warp_drag_kgf(cd_c, w.diameter_mm / 1000, w.warp_m, v)
rw_mcl = rigging.warp_drag_kgf(1.0, w.diameter_mm / 1000, w.warp_m, v) * np.asarray(w.cd_maclennan)
fig, ax = P.plt.subplots(figsize=(7, 4.4))
ax.fill_between(kn, w.shares_kgf["fixed_pitch_5pct"], w.shares_kgf["fixed_pitch_10pct"],
                color=P.NEUTRAL_WASH, lw=0, label="5–10 % of $F_T$ (Craig … Nomura)")
series = ((w.drag_kgf, 1, "Nomura–Yamazaki, α = δ2 → $C_D$ = 0.02 (book)"),
          (rw_corr, 2, f"Nomura–Yamazaki, α = {alpha:.1f}° → $C_D$ = {cd_c:.3f} (corrected)"),
          (w.cylinder.drag_two_kgf, 3, "Cylinder, $C_D$ = 1.1–1.2"),
          (rw_mcl, 7, "MacLennan, $C_D$ = 2.11 − 12.24·v·D"))
for y, slot, lab in series:
    P.line(ax, kn, y, slot, lab)
ax.set_yscale("log")
ax.set_ylim(0.8, 5000)
ax.set_ylabel("$R_W$ of the two warps [kgf]")
P.speed_axis(ax)
P.legend(ax, loc="lower right", fontsize=8.5)
P.finish(fig)
```

{numref}`fig-18-demanda` breaks down the total drag by component. The net accounts for more than
97 % of the Excel total; the otter board, which the Excel workbook omits, would be the second term.

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Composition of the total drag of the system by speed (standard net, Excel mode): net $R_N$,
      floats $R_B$ and warps $R_W$. The top segment is the drag of the pair of otter boards
      $R_{OB}$, which the Excel workbook does not add and the corrected mode does. $R_W$ (green) is
      so small that it is barely visible above the floats.
    name: fig-18-demanda
---
fig, ax = P.plt.subplots(figsize=(7, 4.4))
parts = ((r.drag.rn.std, 1, "Net $R_N$"), (r.floats.drag_kgf, 2, "Floats $R_B$"),
         (w.drag_kgf, 3, "Warps $R_W$"), (r.doors.rig_drag_kgf, 4, "Otter boards $R_{OB}$ (pair, corrected only)"))
bottom = np.zeros_like(kn)
width = 0.22
for y, slot, lab in parts:
    y = np.asarray(y)
    ax.bar(kn, y, width, bottom=bottom, color=P.color(slot), label=lab,
           edgecolor=P.SURFACE, linewidth=1.5, hatch="///" if slot == 4 else None)
    bottom = bottom + y
for x, tot, rt, rob in zip(kn, bottom, w.total.std, r.doors.rig_drag_kgf):
    if x in (2.0, 3.0, 4.0, 5.0):
        ax.annotate(f"{rt:,.0f} + {rob:.0f}", (x, tot), xytext=(0, 3),
                    textcoords="offset points", ha="center", fontsize=8.5, color=P.INK_2)
ax.set_ylabel("Drag [kgf]")
ax.set_ylim(0, 4800)
P.speed_axis(ax)
ax.grid(axis="x", visible=False)
P.legend(ax)
ax.text(0.02, 0.62, "labels: Excel $R_T$ ($R_N + R_B + R_W$)\n+ $R_{OB}$ of the pair of otter boards [kgf]", transform=ax.transAxes,
        color=P.INK_2, fontsize=8.5, va="top")
P.finish(fig)
```

| v [kn] | 1.0 | 2.0 | 3.0 | 3.5 | 4.0 | 5.0 |
|---|---|---|---|---|---|---|
| $R_N$ standard [kgf] | 422 | 915 | 1,680 | 2,152 | 2,677 | 3,871 |
| $R_B$ [kgf] | 2.4 | 9.8 | 23.4 | 31.9 | 41.7 | 65.1 |
| $R_W$ (Nomura–Yamazaki) [kgf] | 1.4 | 5.4 | 12.2 | 16.6 | 21.7 | 33.9 |
| Excel $R_T$ [kgf] | 426 | 930 | 1,716 | 2,200 | 2,740 | 3,970 |
| $R_{OB}$ of one otter board [kgf] | 17.7 | 70.8 | 159.3 | 216.8 | 283.2 | 442.5 |
| $R_W$ as % of $F_T$ | 0.1 % | 0.4 % | 1.0 % | 1.5 % | 2.0 % | 3.5 % |
| corrected $R_W$ ($C_D$ = 0.054) [kgf] | 3.7 | 14.7 | 33.0 | 44.9 | 58.6 | 91.6 |
| corrected $R_W$ as % of $F_T$ | 0.3 % | 1.1 % | 2.8 % | 4.0 % | 5.4 % | 9.4 % |

## Exercises

From the bank of the teaching mode, with the data of the book. In the app, the “UTN Classroom” mode
generates them with other data and marks them ({doc}`38_docentes`).

```{code-cell} ipython3
:tags: [remove-input]
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path.cwd().parent))
import _exercises
_exercises.section("18_cables")
```
