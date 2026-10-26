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

# Towable speed window

## Purpose

The whole design leads to one question: **can the vessel tow this net at the speed the species
requires?** The available pull $F_T$ decreases as speed increases (the propeller turns an ever
smaller fraction of its power into thrust) and the total drag $R_T$ increases roughly with $v^2$.
The two curves cross at the **maximum towable speed**; below it lies the feasible window.

The Excel workbook places one table next to the other (`'Potencia Disponible Arrastre OK'!L11:O19`
[Available towing power] and `'Cables de Remolque'!H118:I126` [Warps]) and leaves the conclusion to
the reader. `trawlkit.performance` formalizes it. This chapter closes the chain of {doc}`motor`: it
uses the pull from {doc}`10_potencia`, the drag of the net from {doc}`14_resistencia`, that of the
otter boards from {doc}`15_portones_aparejo`, that of the floats from {doc}`17_flotacion_lastre`
and that of the warps from {doc}`18_cables`.

## Theory

### Supply: the available pull

The book adopts as design pull the straight line of {cite:t}`fridman1986`:

$$
F_T(v) = P\,(K_F - 0.7\,v) \quad [\text{kgf}], \qquad
K_F = \begin{cases} 10 & \text{fixed pitch propeller (PF)} \\ 15 & \text{controllable pitch with nozzle (PV+T)} \end{cases}
$$ (eq-19-ft)

with $P$ in HP and $v$ in knots. The coefficient $K_F$ is the bollard pull per HP; the slope
$0.7\,P$ reflects the fall of thrust with the speed of advance. A controllable pitch propeller with
nozzle delivers 50 % more bollard pull than a fixed pitch propeller designed for free running,
which works far from its optimum point at towing speeds. The other power methods
(Prado–Dremière, Koyama, Nomura, Hamuro) are discussed in {doc}`10_potencia`.

### Demand: the total drag

$$
R_T(v) = R_N(v) + R_B(v) + R_W(v) + R_{OB}(v)
$$ (eq-19-rt)

The net dominates (≈ 90–98 % of the total); the otter boards are the second term, and floats and
warps contribute a few percentage points ({numref}`fig-18-demanda`).

### Feasible window and maximum speed

A speed $v$ is feasible when the margin $m(v) = F_T(v) - R_T(v)$ is non-negative. On the book's
speed vector ($v_i$ = 1; 1.5; … 5 kn), the maximum towable speed is the first crossing of $m$ from
positive to negative, linearly interpolated between the two points that surround it:

$$
v^* = v_k + (v_{k+1} - v_k)\,\frac{m_k}{m_k - m_{k+1}}, \qquad m_k \ge 0 > m_{k+1}
$$ (eq-19-vmax)

If the whole vector is feasible, $v^*$ is the last speed; if none is, there is no window. Since
$R_T$ is convex and $F_T$ linear, linear interpolation between nodes slightly overestimates the
demand within the interval and $v^*$ stays on the safe side.

## Coefficients

| Symbol | Value | Unit | Source | Cell |
|---|---|---|---|---|
| $K_F$ fixed pitch | 10 | kgf/HP | {cite:t}`fridman1986` | `PotOK!D10` |
| $K_F$ controllable pitch + nozzle | 15 | kgf/HP | {cite:t}`fridman1986` | `PotOK!F10` |
| slope | 0.7 | kgf/(HP·kn) | {cite:t}`fridman1986` | `PotOK!E10` |
| $P$ | 150 (180) | HP | Tipo de buques [Vessel types] | `PotOK!C10` (`C22`) |
| speed vector | 1–5, step 0.5 | kn | — | `PotOK!B10:B18` |

## Excel ↔ `trawlkit` equivalence

| Cell(s) | Calculation | Function |
|---|---|---|
| `PotOK!L11:O19` | Fridman $F_T$ (PF and PV+T, 150 and 180 HP) | `power.summary`, `power.fridman_towing_force_kgf` |
| `Rem!H118:I126` | $R_T$ (standard and modified) | `rigging.total_drag_kgf` (erratum `warp_total_omits_doors`) |
| — | demand with any combination of terms | `performance.total_demand_kgf` |
| — | margin, feasible speeds and $v^*$ | `performance.speed_window` |
| — | windows by propeller and net | `model.run` → `result.performance.windows`, `.design` |

## Assumptions and limits

- **A single pull method.** The window uses Fridman's straight line; the other methods of
  {doc}`10_potencia` give different $F_T$ and therefore different windows. It is a design
  comparison, not a prediction of the actual speed, which depends on the condition of the
  propeller, the hull and the sea.
- **Erratum `warp_total_omits_doors`** (`Rem!H118`). The total drag of the Excel workbook is
  `G118+F118+D118` = $R_W + R_B + R_N$: it omits the otter boards. In `CORRECTED` mode `trawlkit`
  adds $R_{OB}$, which lowers the maximum speed ({doc}`erratas`).
- **One otter board or two.** The sheet computes the drag of **one** otter board of 1.805 m²
  (`Port!D190`, {doc}`15_portones_aparejo`). The corrected mode adds that of the **two** otter
  boards of the gear (`trawlkit.model.DOORS_PER_RIG = 2`); the sensitivity table shows both cases.
- **Speed grid.** $v^*$ is interpolated on the book's 0.5 kn grid; `DesignCase.speeds_kn` accepts
  a finer grid.

## Executable example

```{code-cell} ipython3
import math
import sys, pathlib
DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English

import numpy as np
from IPython.display import Markdown

from tests.golden_utils import golden
from trawlkit.performance import speed_window, total_demand_kgf
import _plots_t2 as P

REM = "cables_de_remolque"
r = P.fao_result(150, "excel")
win = r.performance.design  # fixed pitch, standard net


def close(actual, key, sheet=REM):
    """Compare with the Excel value (scalar or series) at rtol = 1e-6."""
    got, exp = np.atleast_1d(actual), np.atleast_1d(golden(sheet, key))
    return all(math.isclose(a, b, rel_tol=1e-6) for a, b in zip(got, exp))


pvt_win = r.performance.windows["variable_pitch_nozzle_std"]
assert close(win.available_kgf, "fridman_ft_fixed_150_kgf")
assert close(win.demand_kgf, "total_drag_std_kgf")
assert close(pvt_win.available_kgf, "fridman_ft_variable_nozzle_150_kgf")

# v* recomputed by hand from the Excel values (equation for v*)
ft = np.array(golden(REM, "fridman_ft_fixed_150_kgf"))
rt = np.array(golden(REM, "total_drag_std_kgf"))
m = ft - rt
k = int(np.argmax(m < 0)) - 1
v_hand = r.case.speeds[k] + 0.5 * m[k] / (m[k] - m[k + 1])
assert math.isclose(win.max_speed_kn, v_hand, rel_tol=1e-9)

for key, w in r.performance.windows.items():
    print(f"{key:<26} v* = {w.max_speed_kn:.2f} kn, feasible {w.feasible_speeds_kn}")
```

The design window (fixed pitch propeller, standard net) closes at 2.44 kn in the Excel workbook.
With the otter boards included, and with the other errata corrected, the crossing comes earlier
({numref}`fig-19-ventana`).

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Speed window of the 150 HP vessel with the standard FAO A-3 net. Fridman pull with a fixed
      pitch propeller (PF) and a controllable pitch propeller with nozzle (PV+T) against the total
      drag of the Excel workbook ($R_N + R_B + R_W$) and of the corrected mode (which adds
      $R_{OB}$). The shaded area is the feasible design window (PF, Excel); the rings mark $v^*$.
    name: fig-19-ventana
---
P.setup()
rc = P.fao_result(150, "corrected")
kn = r.case.speeds
fig, ax = P.plt.subplots(figsize=(7.2, 4.6))
pf, pvt = win.available_kgf, r.performance.windows["variable_pitch_nozzle_std"].available_kgf

# feasible window: between R_T and F_T up to v*
vv = np.linspace(kn[0], win.max_speed_kn, 60)
ax.fill_between(vv, np.interp(vv, kn, win.demand_kgf), np.interp(vv, kn, pf),
                color=P.GOOD, alpha=0.12, lw=0)
ax.annotate("feasible window\n(PF, Excel)", (1.45, 1050), color=P.INK_2, fontsize=9, ha="center")

P.line(ax, kn, pf, 1, "$F_T$ fixed pitch (PF)")
P.line(ax, kn, pvt, 7, "$F_T$ controllable pitch + nozzle (PV+T)")
P.line(ax, kn, win.demand_kgf, 2, "$R_T$ Excel ($R_N+R_B+R_W$)")
P.line(ax, kn, rc.performance.design.demand_kgf, 4, "$R_T$ corrected ($+R_{OB}$)")

marks = ((win, "$v^*$ PF, Excel", (2.8, 850)),
         (r.performance.windows["variable_pitch_nozzle_std"], "$v^*$ PV+T, Excel", (2.05, 2700)),
         (rc.performance.design, "$v^*$ PF, corrected", (2.8, 550)))
for w, lab, xy in marks:
    vs = w.max_speed_kn
    y = float(np.interp(vs, kn, w.available_kgf))
    ax.plot([vs], [y], "o", ms=13, mfc="none", mec=P.INK_2, mew=1.2)
    ax.annotate(f"{lab}: {vs:.2f} kn", (vs, y), xytext=xy, textcoords="data",
                color=P.INK_2, fontsize=9, va="center",
                arrowprops={"arrowstyle": "-", "color": P.MUTED, "lw": 0.8, "shrinkB": 7})
ax.set_ylabel("Force [kgf]")
ax.set_ylim(0, 4200)
P.speed_axis(ax)
P.legend(ax, loc="upper left")
P.finish(fig)
```

### Sensitivity

The table varies one factor at a time on the design case (150 HP, PF, standard net, Excel mode).

```{code-cell} ipython3
---
mystnb:
  markdown_format: myst
---
r180 = P.fao_result(180, "excel")
rn, rb, rw = r.drag.rn.std, r.floats.drag_kgf, r.warps.drag_kgf
rob = np.asarray(r.doors.forces.drag_kgf)
pvt = r.performance.windows["variable_pitch_nozzle_std"].available_kgf


def vmax(ft, *terms):
    return speed_window(kn, ft, total_demand_kgf(*terms)).max_speed_kn


base = vmax(pf, rn, rb, rw)
assert math.isclose(base, win.max_speed_kn, rel_tol=1e-12)
rows = [
    ("Design case (Excel: $R_N+R_B+R_W$)", base),
    ("$R_N$ − 10 %", vmax(pf, 0.9 * rn, rb, rw)),
    ("$R_N$ + 10 %", vmax(pf, 1.1 * rn, rb, rw)),
    ("+ $R_{OB}$ of one otter board", vmax(pf, rn, rb, rw, rob)),
    ("+ $R_{OB}$ of both otter boards (corrected mode)", vmax(pf, rn, rb, rw, 2 * rob)),
    ("Modified net", r.performance.windows["fixed_pitch_mod"].max_speed_kn),
    ("PV+T propeller", vmax(pvt, rn, rb, rw)),
    ("180 HP vessel (PF)", r180.performance.design.max_speed_kn),
    ("180 HP vessel (PV+T)",
     r180.performance.windows["variable_pitch_nozzle_std"].max_speed_kn),
    ("Full corrected mode (PF)", rc.performance.design.max_speed_kn),
]
lines = ["| Variant | $v^*$ [kn] | Δ [kn] |", "|---|---|---|"]
for name, v in rows:
    lines.append(f"| {name} | {v:.2f} | {v - base:+.2f} |")
Markdown("\n".join(lines))
```

Three readings:

1. **The propeller matters more than the power.** Changing from fixed pitch to controllable pitch
   with nozzle (same engine) gains ≈ 0.8 kn; changing from 150 to 180 HP with fixed pitch gains
   less than 0.3 kn. To tow at 2.5–3 kn, usual speeds in bottom trawling, the
   150 HP vessel needs a controllable pitch propeller or a smaller net.
2. **The otter boards are not negligible.** With one otter board the window loses ≈ 0.1 kn; with
   both, which is the real configuration, ≈ 0.2 kn. Omitting them (erratum
   `warp_total_omits_doors`) gives an optimistic window.
3. **The uncertainty of $R_N$ dominates.** A ±10 % in the net drag, which is less than the spread
   between the methods of {doc}`14_resistencia`, moves $v^*$ by ≈ ±0.15 kn, as much as the otter
   boards. That is why the full corrected mode lowers $v^*$ less than the otter boards suggest: the
   corrections to the net (solid area, footrope) reduce $R_N$ by ≈ 5 % and offset a good part of
   the otter board that is added. The standard and modified nets are almost equivalent (the 30 mm
   codend has slightly less drag in Excel mode).

## Exercises

From the bank of the teaching mode, with the data of the book. In the app, the “UTN Classroom” mode
generates them with other data and marks them ({doc}`38_docentes`).

```{code-cell} ipython3
:tags: [remove-input]
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path.cwd().parent))
import _exercises
_exercises.section("19_ventana_velocidad")
```
