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

# Optimization of net size and speed

## Purpose

The previous chapters answer the question *can this vessel tow this net?*
({doc}`19_ventana_velocidad`). This chapter turns the question around: **what net size and what
towing speed suit this vessel?** The FAO A-3 net was designed for 150–180 HP fishing vessels, but
{doc}`30_caso_beagle` shows that with 150 HP and a fixed pitch propeller the feasible window is
barely a tenth of a knot. `trawlkit.optimize` explores the family of nets *geometrically similar*
to the original (same mesh size, twine, cuts and materials, with $s$ times more meshes per edge)
and searches for the pair $(s, v)$ that maximizes fishing performance without violating the pull,
opening, warp and otter board constraints.

Each evaluation is a full run of the engine ({doc}`motor`): there is no surrogate model, and
therefore the results inherit the assumptions of all the stages, in particular the empirical drag
of {doc}`14_resistencia` and the openings of {doc}`16_aberturas`.

## Formulation

### Variables

* **Net scale** $s \in [s_{\min}, s_{\max}]$ (0.6–1.4 by default). `scale_net(spec, s)` multiplies
  by $s$ the numbers of meshes of each edge and of the depth of each panel (also the Excel extras
  T1/T2) and rounds to the nearest integer, with a minimum of 1. Since the rounding depends only on
  the original number, the edges that are joined (equal in the original net) remain equal. Ropes
  and circumferences scale ≈ $s$, netting areas ≈ $s^2$; the number of floats scales with the
  headrope. $s = 1$ is the book's net.
* **Towing speed** $v \in [v_{\min}, v_{\max}]$ (1.5–4 kn by default).

### Openings at speed $v$

The horizontal opening is Fridman's DPA ({cite:t}`fridman1986`, `Mec!P164`), the only one in the
engine that depends on $v$: the geometric DPA and the average AH of `Dim!F61` are constant and do
not see that a slow net does not open fully. Since Fridman's force balance does not saturate, with
a small net and the same otter board the computed DPA exceeds what the rigging geometry allows;
the smaller of the two is taken:

$$
A_H(s, v) = \min\left\{ \mathrm{DPA}_F(s, v),\ \frac{L_B\,D_s}{L_{PG} + L_P + L_{Vs} + L_B} \right\}
$$ (eq-20-ah)

with $L_B$ the footrope, $D_s$ the otter board spread and $L_{PG}$, $L_P$, $L_{Vs}$ the crowfoot,
sweeps and bridles (`Mec!L211` without the rounding to the whole metre). Likewise, the
Baranov–Fridman AV (`Mec!O272`) grows without limit when $R_N \to 0$ (slow net); it is capped with
the maximum AV of {cite:t}`prado1990`, 6.5 % of the mouth circumference:

$$
A_V(s, v) = \min\left\{ AV_F(s, v),\ 0.065\,C(s) \right\}
$$ (eq-20-av)

### Objectives

$$
\dot A = 3600\,A_H\,v, \qquad \dot V = 3600\,A_H\,A_V\,v, \qquad
E = \frac{R_T}{A_H}
$$ (eq-20-obj)

$\dot A$ is the **area swept per hour** [m²/h] (demersal species associated with the seabed, such
as squat lobster), $\dot V$ the **volume filtered per hour** [m³/h] (species that rise off the
seabed) and $E$ the **towing work per m² swept** [kgf·m/m²], an indicator of consumption: the
vessel spends $R_T \cdot d$ to sweep $A_H \cdot d$. $\dot A$ and $\dot V$ are maximized, $E$ is
minimized.

### Constraints

$$
\begin{aligned}
g_1 &: F_T(v) \ge (1 + m)\,R_T(s, v) && \text{pull reserve (}m = 0.1\text{)} \\
g_2 &: \mathrm{DPA}_F(s, v) \ge 0.85\,\mathrm{DPA}_{geo}(s) && \text{net open} \\
g_3 &: \max_{c\,:\,\varnothing_c \ge \varnothing_{\min}} Q_c \ge 4\,R_T(s, v) && \text{some catalogue warp holds} \\
g_4 &: S_{req} \le S_{port} && \text{otter board large enough (Port!F215)} \\
g_5 &: v_{\min} \le v \le v_{\max} && \text{operating range}
\end{aligned}
$$ (eq-20-g)

$F_T$ is the Fridman pull of the propulsion unit ({eq}`eq-19-ft`) and $R_T$ the total drag with
both otter boards ({eq}`eq-19-rt`, corrected mode). $g_2$ is the minimum-speed criterion of
{doc}`30_caso_beagle` with the book's geometric DPA (`Mec!L211`). In $g_3$, $\varnothing_{\min}$
is the Águila diameter for the power of the class and $Q_c$ the breaking load of warp $c$. In
$g_4$, $S_{req}$ is the area per otter board required by the book's rule (ROB = 20 % of $F_T$,
2–4 kn average, `Port!F215`): it depends on the vessel and the propeller, not on $(s, v)$, and works
as a preliminary check of the rigging.

## Method

1. **Grid.** For each scale $s_i$ the engine is run **once** on a fine speed grid (0.05 kn, from 1
   to 5 kn plus the book's nodes) and each $v_j$ is evaluated by linear interpolation. The
   quantities that the book averages over speed (required otter board area) are taken at the
   book's nodes, so at $s = 1$ and $v = 2$ kn the evaluation reproduces `run(case)` exactly.
2. **Pareto front.** `pareto_front` filters exactly the feasible non-dominated points in
   $(\dot A, E)$: no other point sweeps more with less work per m².
3. **Differential evolution.** `optimise` refines with `scipy.optimize.differential_evolution`
   (Storn and Price, 1997) over $(s, v)$, minimizing

   $$
   f(s, v) = -\sigma\,\frac{J(s, v)}{|J_0|} + W \sum_k \max\{0, \tilde g_k(s, v)\}
   $$ (eq-20-pen)

   with $J$ the objective, $\sigma = \pm 1$ its sense, $J_0$ the best value of the grid,
   $\tilde g_k$ the relative violation of each constraint and $W = 100$. The population is seeded
   with the best grid point (`x0`) and with a fixed seed (`seed`), so the result is reproducible.
   The scale is rounded to 0.005 to reuse engine runs (a net with the same numbers of meshes is
   not recomputed). The final result is the best feasible point between the grid and the
   refinement.

## Coefficients

| Symbol | Value | Unit | Source | Parameter |
|---|---|---|---|---|
| $m$ | 0.1 | — | design criterion | `Limits.margin`, `--margin` |
| opening fraction | 0.85 | — | {doc}`30_caso_beagle` | `Limits.open_ratio` |
| warp safety factor | 4 | — | `Rem!D271` | `DesignCase.warp_safety_factor` |
| maximum AV | 6.5 % of $C$ | — | {cite:t}`prado1990`, `Mec!F246` | — |
| $W$ | 100 | — | — | `search.PENALTY_WEIGHT` |
| step of $s$ in the refinement | 0.005 | — | — | `search.S_STEP` |
| engine speed grid | 0.05 | kn | — | `evaluate.GRID_STEP_KN` |

## Excel ↔ `trawlkit` equivalence

| Cell(s) | Quantity | Use in `trawlkit.optimize` |
|---|---|---|
| `Paños!H55:W230` | meshes of each panel (T1, T2, N) | `scale_net` |
| `Mec!P164:P172` | Fridman DPA by speed | $A_H$, constraint $g_2$ |
| `Mec!L211` | geometric DPA | cap on $A_H$, threshold of $g_2$ |
| `Mec!O272:O280`, `F246` | Fridman AV, Prado maximum AV | $A_V$ |
| `PotOK!L11:O19` | $F_T$ FP and CP+N | $g_1$ |
| `Rem!H118` (+ ROB) | $R_T$ | $g_1$, $g_3$, $E$ |
| `Rem!E110`, `Cab!D11` | minimum Ø, warp catalogue | $g_3$ |
| `Port!F215` | required area per otter board | $g_4$ |

## Results for the FAO A-3 case

The four combinations of the book are optimized: 150 and 180 HP, fixed pitch propeller (FP) and
controllable pitch propeller with nozzle (CP+N). The book's rule calls for otter boards larger than
the 1.805 m² FAO board for 180 HP with FP (≈ 2.0 m²) and for CP+N (≈ 2.7 and 3.2 m²): in those cases
an otter board similar to the book's (same polar) is used, with the required area rounded up to
0.05 m² (`scale_door`). Without that change $g_4$ is not met at any point.

```{code-cell} ipython3
---
mystnb:
  markdown_format: myst
---
import dataclasses
import math
import sys, pathlib
DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English

import numpy as np
from IPython.display import Markdown

import _plots_t2 as P
from trawlkit import DesignCase
from trawlkit.io import load_doors, load_net, load_vessels
from trawlkit.optimize import Evaluator, evaluate, optimise, pareto_front, scale_door

VESSELS = {v.id: v for v in load_vessels().vessels}
DOOR = load_doors().doors[0]
PROPS = {"fixed_pitch": "FP", "variable_pitch_nozzle": "CP+N"}
CONFIGS = [(hp, prop) for hp in (150, 180) for prop in PROPS]


def case_for(hp, prop):
    """FAO A-3 case (standard net) with the book's otter board or a similar one sized (F215)."""
    vid = f"fao_a3_{hp}hp"
    case = DesignCase(
        net=load_net("fao_a3_standard"),
        vessel=VESSELS[vid],
        class_vessels=tuple(v for k, v in VESSELS.items() if k != vid),
        door=DOOR,
        ft_propeller=prop,
    )
    req = evaluate(case, 1.0, 2.0).door_required_m2
    if req > DOOR.area_m2:
        case = dataclasses.replace(case, door=scale_door(DOOR, math.ceil(req * 20) / 20))
    return case


CASES = {c: case_for(*c) for c in CONFIGS}

# Book's net, 150 HP, fixed pitch, FAO otter board: feasible at 2.1 kn and not at 3.5 kn (nor at 1.5 kn).
base = CASES[(150, "fixed_pitch")]
assert base.door.area_m2 == DOOR.area_m2
assert evaluate(base, 1.0, 2.1).feasible
assert not evaluate(base, 1.0, 3.5).constraint("thrust").ok
assert not evaluate(base, 1.0, 1.5).constraint("net_open").ok

OBJ = {"area": "area/h", "volume": "volume/h", "energy": "R_T/AH"}
RES = {(c, o): optimise(CASES[c], objective=o, seed=0) for c in CONFIGS for o in OBJ}

lines = [
    "| Vessel | Propeller | Otter board [m²] | Objective | $s$ | $v$ [kn] | Headrope [m] | $A_H$ [m] "
    "| $A_V$ [m] | Area [m²/h] | Volume [m³/h] | $R_T/A_H$ | $R_T$ [kgf] | Margin |",
    "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
]
for (hp, prop), case in CASES.items():
    for o, name in OBJ.items():
        b = RES[((hp, prop), o)].best
        assert b.feasible
        lines.append(
            f"| {hp} HP | {PROPS[prop]} | {case.door.area_m2:.2f} | {name} | {b.s:.3f} | "
            f"{b.v_kn:.2f} | {b.headrope_m:.1f} | {b.ah_m:.1f} | {b.av_m:.2f} | "
            f"{b.area_rate_m2_h:,.0f} | {b.volume_rate_m3_h:,.0f} | {b.energy_kgf_m_per_m2:.1f} | "
            f"{b.demand_kgf:.0f} | {b.thrust_margin:.0%} |"
        )
Markdown("\n".join(lines))
```

The table summarizes the best design per objective (best feasible point after differential
evolution). Before reading it, it is worth seeing the whole feasible region: {numref}`fig-20-mapa`
sweeps $s \times v$ with 41 × 51 points (one engine run per row) and also uses it to check that the
optimizer did not get stuck in a local optimum.

```{code-cell} ipython3
S = np.round(np.arange(0.6, 1.4001, 0.02), 3)
V = np.round(np.arange(1.5, 4.0001, 0.05), 3)
MAPS = {}
for c, case in CASES.items():
    ev = Evaluator(case)
    rows = [[ev.from_curves(ev.curves(s), v) for v in V] for s in S]
    MAPS[c] = rows
    dense = [e for row in rows for e in row if e.feasible]
    for o, attr in (("area", "area_rate_m2_h"), ("volume", "volume_rate_m3_h")):
        best_dense = max(getattr(e, attr) for e in dense)
        # The refinement matches or improves on the dense grid (1 % tolerance).
        assert getattr(RES[(c, o)].best, attr) >= 0.99 * best_dense, (c, o)
    s_max = max(e.s for e in dense)
    at_book = [e.v_kn for e in rows[list(S).index(1.0)] if e.feasible]
    window = f"{at_book[0]:.2f}–{at_book[-1]:.2f} kn" if at_book else "none"
    print(f"{c[0]} HP {PROPS[c[1]]:<5} maximum feasible scale {s_max:.2f}; "
          f"feasible speeds of the book's net: {window}")
```

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Feasible region (green) in the speed–scale plane for the scaled FAO A-3 net, with contours
      of area swept per hour (thousands of m²/h). The dashed line is the book's net ($s = 1$). The
      markers are the area optimum (circle) and the volume optimum (square). Top 150 HP, bottom
      180 HP; left fixed pitch (FP) and right controllable pitch with nozzle (CP+N), each with its
      own otter board.
    name: fig-20-mapa
---
P.setup()
fig, axes = P.plt.subplots(2, 2, figsize=(8.6, 7.2), sharex=True, sharey=True)
for ax, c in zip(axes.flat, CONFIGS):
    rows = MAPS[c]
    feas = np.array([[e.feasible for e in row] for row in rows], dtype=float)
    area = np.array([[e.area_rate_m2_h for e in row] for row in rows]) / 1000
    ax.contourf(V, S, feas, levels=[0.5, 1.5], colors=[P.GOOD], alpha=0.22)
    ax.contour(V, S, feas, levels=[0.5], colors=[P.GOOD], linewidths=1.2)
    cs = ax.contour(V, S, area, levels=np.arange(20, 121, 10), colors=P.MUTED, linewidths=0.7)
    ax.clabel(cs, fmt="%d", fontsize=7.5, inline=True)
    ax.axhline(1.0, color=P.INK_2, lw=1.0, ls="--")
    for o, mk, slot in (("area", "o", 1), ("volume", "s", 2)):
        b = RES[(c, o)].best
        ax.plot([b.v_kn], [b.s], mk, color=P.color(slot), ms=9, mec=P.SURFACE, mew=1.5,
                label=f"{OBJ[o]} optimum")
    door = CASES[c].door.area_m2
    ax.set_title(f"{c[0]} HP, {PROPS[c[1]]} (otter board {door:.2f} m²)")
    ax.grid(False)
for ax in axes[1]:
    ax.set_xlabel("Towing speed v [kn]")
for ax in axes[:, 0]:
    ax.set_ylabel("Net scale s")
axes[0, 0].annotate("book's net", (3.95, 1.01), ha="right", va="bottom", fontsize=8.5,
                    color=P.INK_2)
P.legend(axes[0, 0], loc="upper right")
P.finish(fig)
```

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Pareto front between area swept per hour (to be maximized) and towing work per m² swept
      $R_T/A_H$ (to be minimized), on the dense grid of the previous figure. Each point of the
      front is a pair $(s, v)$ that cannot be improved in one objective without worsening the
      other. The rings mark the book's net ($s = 1$) within its feasible window, when it has one.
    name: fig-20-pareto
---
fig, ax = P.plt.subplots(figsize=(7.2, 4.6))
for slot, c in enumerate(CONFIGS, start=1):
    flat = [e for row in MAPS[c] for e in row]
    front = sorted(pareto_front(flat), key=lambda e: e.area_rate_m2_h)
    x = [e.area_rate_m2_h / 1000 for e in front]
    y = [e.energy_kgf_m_per_m2 for e in front]
    P.line(ax, x, y, slot, f"{c[0]} HP, {PROPS[c[1]]}", marker=False)
    book = [e for e in flat if e.feasible and math.isclose(e.s, 1.0)]
    if book:
        ax.plot([e.area_rate_m2_h / 1000 for e in book], [e.energy_kgf_m_per_m2 for e in book],
                "o", ms=8, mfc="none", mec=P.color(slot), mew=1.4)
ax.set_xlabel("Area swept per hour [thousands of m²/h]")
ax.set_ylabel("$R_T/A_H$ [kgf·m/m²]")
P.legend(ax, loc="upper left")
P.finish(fig)
```

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  markdown_format: myst
---
# First points of the front (150 HP, FP) according to the optimizer with a 17 × 11 grid.
r = RES[((150, "fixed_pitch"), "area")]
lines = ["| $s$ | $v$ [kn] | $A_H$ [m] | Area [m²/h] | $R_T/A_H$ | $R_T$ [kgf] | Margin |",
         "|---|---|---|---|---|---|---|"]
for e in r.pareto[:6]:
    lines.append(f"| {e.s:.3f} | {e.v_kn:.2f} | {e.ah_m:.1f} | {e.area_rate_m2_h:,.0f} | "
                 f"{e.energy_kgf_m_per_m2:.1f} | {e.demand_kgf:.0f} | {e.thrust_margin:.0%} |")
print(f"{r.engine_runs} engine runs in {r.runtime_s:.1f} s")
Markdown("\n".join(lines))
```

## Discussion

**The book's net is large for 150 HP with fixed pitch.** With the 10 % pull reserve, the original
net is only feasible in a band of ≈ 0.1 kn around 2.1 kn: below it the net does not open
(constraint $g_2$), above it the vessel cannot tow it with reserve ($g_1$). It is the same
conclusion as in {doc}`30_caso_beagle`, now as a point on the edge of the feasible region
({numref}`fig-20-mapa`). No net with $s > 1.02$ has a feasible speed.

**To sweep more area, a smaller and faster net pays off.** The area swept per hour is $A_H\,v$, and
$A_H$ depends mostly on the rigging (otter board spread, sweeps and bridles), not on the size of the
net: when the net is made smaller, the geometric DPA falls much less than $s$ (from ≈ 13.8 m to
≈ 11.4 m between $s = 1$ and $s = 0.6$), while the drag falls ≈ $s^2$ and frees pull to go
faster. That is why the area optimum lies at the lower edge of the scale ($s ≈ 0.6$–0.66) and at
the maximum speed the pull allows: ≈ 3.2 kn with 150 HP and FP, ≈ 3.8 kn with CP+N. With 180 HP the
optimum barely moves. This result is only as good as the $A_H$ model: it assumes that the catch is
proportional to the area between the wing ends, which is reasonable for species that the gear
herds (squat lobster, flatfish) and optimistic for species that escape from a slow net.

**To filter more volume, an intermediate net pays off.** Fridman's AV falls with speed (the
headrope is flattened as $R_N$ grows), so the volume $A_H A_V v$ has an interior maximum. The
optimum lies at $s ≈ 0.83$–0.89 and 2.3–2.6 kn, with plenty of pull reserve (30–90 %): it is set
not by the power but by the vertical opening model, at the point where Fridman's AV drops below the
cap of {eq}`eq-20-av`. That is why it is the same with 150 and 180 HP and fixed pitch, and changes
with CP+N only because the larger otter board opens the net more. It is the result most sensitive
to the assumptions of the chapter.

**The work per m² swept always favours the smallest and slowest.** $R_T/A_H$ grows with $v$ and
with $s$, so minimizing it alone leads to the corner $(s_{\min}, v_{\min})$. That is why it is
presented as a Pareto front ({numref}`fig-20-pareto`): for each area swept per hour, the front
gives the least work per m², and the designer chooses the point according to the cost of fuel and
of sea time. Along the front, going from ≈ 30,000 to ≈ 65,000 m²/h with 150 HP and FP triples the
work per m².

**The propeller matters more than the power.** Changing from FP to CP+N with the same engine
enlarges the feasible region much more than changing from 150 to 180 HP: with CP+N the book's net is
feasible from 1.5 kn up to ≈ 2.7 kn (150 HP) or ≈ 2.9 kn (180 HP), and the maximum feasible scale
rises to ≈ 1.3 (150 HP) and to more than 1.4 (180 HP), against ≈ 1.02 and ≈ 1.06 with fixed pitch.
According to the book's rule, CP+N requires otter boards of 2.7–3.25 m², considerably larger than
the 1.805 m² FAO board.

**The book's net is dominated.** In all four cases the $s = 1$ points lie above the Pareto front
({numref}`fig-20-pareto`): for the same area swept per hour there is a smaller net, towed faster,
that achieves it with less work per m². With fixed pitch the difference is ≈ 50 % (the original net
can only go at 2–2.3 kn); with CP+N, ≈ 10–25 %.

## Assumptions and limits

- **Empirical drag.** $R_N$ is the Aberdeen demersal formula ({doc}`14_resistencia`), fitted for
  nets of this size; extrapolating to $s = 0.6$ or $1.4$ is reasonable for the drag (which scales
  with the netting area), but the ±10 % uncertainty of $R_N$ moves the maximum speed by
  ≈ ±0.15 kn ({doc}`19_ventana_velocidad`) and shifts the optima by the same amount.
  {doc}`32_validacion_dynamit` suggests that the design drag is conservative.
- **Opening model.** $A_H$ and $A_V$ come from Fridman's equilibria and simple geometric caps;
  there is no net shape model that couples both openings or the deformation of the panels with
  speed.
- **Geometric scaling.** The family $s$ keeps mesh size, twine and rigging. It does not optimize
  the shape (cuts, headrope/footrope ratio, body length), the mesh size or the rigging (sweep
  length, warp paid out), which move $A_H$ as much as $s$.
- **No catch and no seabed.** The drag does not include the catch in the codend or the contact of
  the footrope and the otter boards with the seabed; fishing performance is measured by area or
  volume, without selectivity or species behaviour. The pull reserve $m$ is what covers, in part,
  these effects.
- **Otter board as a check.** The `Port!F215` rule does not depend on $(s, v)$; a different otter
  board changes $R_T$ (its drag) and Fridman's DPA, but its area is not optimized.
- **Optima at the edges.** The area and energy optima fall at $s_{\min}$: the result says “as small
  as allowed” and depends on the chosen range, which must reflect the practical minimum of the net
  (handling on deck, target species).

## Exercises

From the bank of the teaching mode, with the data of the book. In the app, the “UTN Classroom” mode
generates them with other data and marks them ({doc}`38_docentes`).

```{code-cell} ipython3
:tags: [remove-input]
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path.cwd().parent))
import _exercises
_exercises.section("20_optimizacion")
```
