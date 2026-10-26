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

# Simulation of the net shape

```{code-cell} ipython3
:tags: [remove-cell]
import sys, pathlib
DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English
import time

import numpy as np

import _plots_t2 as P
import _plots_v as V
from trawlkit.model import run
from trawlkit.sim import DEFAULT_CN, DEFAULT_CT, DEFAULT_MU, build_model, rigging_from_result, simulate
from trawlkit.sim.validation import (
    CN_RANGE,
    CT_RANGE,
    DYNAMIT,
    FISHING_BAND_KN,
    calibrate,
    speed_exponent,
    standard_case,
    validate,
)

P.setup()
T0 = time.perf_counter()
R = run(standard_case())  # standard FAO A-3 net, 150 HP, FAO otter board, corrected mode
RES = 6  # validation resolution (nominal divisions per panel)
```

## Purpose

All the previous stages of the book are **independent empirical rules**: the drag of the net
comes from the solid area ({doc}`14_resistencia`), the horizontal opening from Fridman's otter
board equilibrium and the vertical opening from the bridle angle ({doc}`16_aberturas`). None of
them knows how far the net opened when it computes its drag, nor how much the netting deformed when
it computes its opening. {doc}`32_validacion_dynamit` showed that where the book uses a rule of
thumb the discrepancy with a physical simulator reaches 35–47 %.

`trawlkit.sim` adds a **simplified physical model of the shape of the towed net**: the netting,
the headrope and footrope, the floats, the ballast, the bridles and the sweeps in equilibrium
under the water drag, the weight, the buoyancy and the contact with the seabed, with the rigging
computed by the engine. The openings and the drag come from the **same equilibrium shape** and are,
by construction, consistent with each other. It does not replace DynamiT {cite:p}`dynamit` (it does
not model the otter boards or the warps, whose spread is an input) and it is experimental: this
chapter describes the model, checks its convergence and validates it against DynamiT and against
the empirical engine.

## Model

### Discretization

Each panel of the mounted plan is divided into a structured grid of nodes (interpolated between its
four corners) and each cell into two triangles. Nodes that represent the same physical point are
merged: the lower edge of a panel with the upper edge of the next one, the side seams between top
and bottom panels (which close the funnel) and the end of the codend tied into one node. The
**resolution** is the nominal number of divisions per panel: the width of each wing has
`resolution // 2` columns and the rows of each strip are proportional to its length (`resolution`
rows every 9 m).

### Triangular netting elements

Diamond-mesh netting has two families of twines. In mesh coordinates $(t, n)$ (meshes across and
along the panel) the twine coordinates are $i = n + t$ and $j = n - t$, in units of one bar of
length $a = \text{mesh size}/2$. Inside a triangle the position $\mathbf{x}$ is linear in
$(i, j)$, so $\partial\mathbf{x}/\partial i$ and $\partial\mathbf{x}/\partial j$ are constant:
they are the vectors of **one bar** of each family. This is the triangular element of
{cite:t}`priour1999` ({cite:t}`priour2013`). The triangle contains $A_{ij}$ bars of each family
($A_{ij}$, area of the triangle in twine coordinates), and the tension of each family is

$$
T_k = EA \,\max\left(\frac{\lVert \partial\mathbf{x}/\partial k \rVert}{a} - 1,\ 0\right),
\qquad k \in \{i, j\},
$$ (eq-21-twine)

in tension only (a slack twine does not push), with $EA = E\,\pi d^2/4$ and $E = 2$ GPa
(polyamide). The element gives the netting zero shear and bending stiffness and reproduces the
coupling $U_1^2 + U_2^2 \le 1$ of the diamond mesh: the netting narrows as it lengthens. The total
twine length of the triangle is $2\,a\,A_{ij}$ and, summed over a panel, $\sum d\,L$ equals the FAO
solid area $S_s$ of {doc}`12_mecanica_red` (checked below).

### Hydrodynamics: Morison on each twine family

Each twine family of a triangle is a cylinder of diameter $d$ and length $L = A_{ij}\,a$; with
$\mathbf{u} = v\,\hat{\mathbf{x}}$ the velocity of the water relative to the net and $u_n$, $u_t$
its components normal and tangential to the twine, the drag force is that of
{cite:t}`morison1950`:

$$
\mathbf{F}_n = \tfrac12 \rho\, C_N\, d\, L\, \lvert \mathbf{u}_n \rvert\, \mathbf{u}_n, \qquad
\mathbf{F}_t = \tfrac12 \rho\, C_T\, d\, L\, \lvert \mathbf{u}_t \rvert\, \mathbf{u}_t,
$$ (eq-21-morison)

with $\rho = 1024$ kg/m³, $C_N = 1.4$ and $C_T = 0.08$ by default (usual ranges for netting twine:
$C_N \approx 1.0$–$1.6$, $C_T \approx 0.01$–$0.12$; {cite:t}`lee2005`, {cite:t}`takagi2004`,
{cite:t}`priour2013`). The headrope and footrope receive the same drag with their diameter; the
bridles and sweeps receive none. The floats are spheres with buoyancy and drag
$\tfrac12 \rho\, C_D\, (\pi D^2/4)\, v^2$, with the engine's $C_D$ at each speed
({doc}`17_flotacion_lastre`). Optionally (`knot_factor`) the knots are modelled as two spheres per
mesh of diameter $k\,d$.

### Weights, buoyancy and seabed

The submerged weight of the twine is $(1 - \rho/\rho_{PA})\,g$ per unit mass (polyamide,
$\rho_{PA} = 1140$ kg/m³) and one third goes to each vertex; the headrope, footrope, bridles and
sweeps carry their submerged weight per metre, the footrope ballast is distributed between wings,
bosom and wing tips as in {doc}`17_flotacion_lastre` and the floats are placed on the headrope with
the engine's selective distribution. The seabed $z = 0$ is a unilateral constraint: a node resting
on it receives the reaction $R = \max(0, -F_z)$ and the kinetic friction

$$
F_x^{\text{seabed}} = \mu\, R, \qquad \mu = 0.5,
$$ (eq-21-friction)

directed aft: in steady towing every point resting on the seabed slides over it with velocity
$-v\,\hat{\mathbf{x}}$, so the direction is exact.

### Rigging and boundary conditions

The upper and lower bridles (the lower one with the adjusting chain, so that it adds up to the same
length as the upper one) run from each wing tip to a junction node, and the sweep from that node to
the towing point of the otter board. The **otter boards are fixed** at $x = 0$, $y = \pm D_P/2$ and
$z = h_{\text{door}}/2$, with $D_P$ the door spread from the engine ({doc}`15_portones_aparejo`,
32.5 m for the FAO A-3 case) or an imposed one. The lengths of headrope and footrope, bridles and
sweeps, the number and position of the floats and the ballast come from the `DesignResult`
(`rigging_from_result`). The net is symmetric about the plane $y = 0$: the forces are projected
onto the symmetric subspace, which is equivalent to simulating half a net.

### Solver: dynamic relaxation with FIRE

The equilibrium shape $\mathbf{F}(\mathbf{x}) = \mathbf{0}$ is found by **dynamic relaxation**
{cite:p}`barnes1999`: $M\,\ddot{\mathbf{x}} = \mathbf{F}(\mathbf{x})$ is integrated in a fictitious
time with fictitious masses equal to a Gershgorin bound of the axial stiffness of each node (stable
unit step) and the FIRE adaptive damping {cite:p}`bitzek2006`:

$$
\mathbf{v} \leftarrow (1 - \alpha)\,\mathbf{v} + \alpha\, \lVert\mathbf{v}\rVert\,
\frac{\mathbf{F}}{\lVert\mathbf{F}\rVert}, \qquad
\text{if } \mathbf{F}\cdot\mathbf{v} \le 0:\ \mathbf{v} \leftarrow \mathbf{0},\ \Delta t \leftarrow \Delta t/2,
$$ (eq-21-fire)

with $\Delta t$ growing by 10 % and $\alpha$ decaying while the power $\mathbf{F}\cdot\mathbf{v}$
is positive. It stops when the residual $\lVert\mathbf{F}\rVert/D$ and the global imbalance
$\lvert\sum F_x\rvert/D$ ($D$, drag of the net) fall below 1 % and AH, AV and $D$ change by less
than 0.3 % between windows of 1000 iterations. A coarse mesh (resolution 4) is solved first and
its shape is interpolated as the starting point. An implicit Newton method does not work well:
the slack/taut transition of nearly inextensible twines ruins the linearization.

**What is measured.** AH is the distance between the wing tips of the headrope; AV the height of
the headrope above the footrope at the centre of the mouth; the drag of the net is the water drag
on netting, headrope, footrope and floats plus the friction with the seabed, equal (at
equilibrium) to the pull of the bridles.

```{code-cell} ipython3
:tags: [hide-input]
# Solid area identity: Σ d·L of the discretized netting = corrected Ss from the engine.
from trawlkit.compat import Compat
from trawlkit.net import analyse

ss = analyse(R.case.net, Compat.CORRECTED).solid_surface_m2
rows = []
for res in (3, 6, 8):
    m = build_model(R.case.net, rigging_from_result(R), resolution=res)
    assert abs(m.solid_surface_m2 / ss - 1) < 2e-3
    rows.append([str(res), str(m.n_nodes), str(len(m.tri)), V.fmt(m.solid_surface_m2, 2),
                 V.pct_s(m.solid_surface_m2, ss, 2) + " %"])
V.md_table(["Resolution", "Nodes", "Triangles", "Σ d·L [m²]", "Δ vs engine Ss"], rows)
print(f"Engine Ss (corrected mode): {ss:.2f} m²")
```

The only difference is the wing tip, whose 3-mesh mouth edge is reduced to a point: less than
0.2 % of the area.

## Mesh convergence

```{code-cell} ipython3
:tags: [hide-input]
CONV = {res: simulate(R, 3.0, resolution=res) for res in (3, 4, 6, 8)}
rows = [[str(res), str(r.nodes.shape[0]), V.fmt(r.ah_m, 2), V.fmt(r.av_m, 2),
         V.fmt(r.drag_kgf, 0), V.fmt(r.runtime_s, 1), "yes" if r.converged else "no"]
        for res, r in CONV.items()]
V.md_table(["Resolution", "Nodes", "AH [m]", "AV [m]", "Drag [kgf]", "Time [s]",
            "Converged"], rows)
c6, c8 = CONV[6], CONV[8]
assert abs(c8.ah_m / c6.ah_m - 1) < 0.02 and abs(c8.drag_kgf / c6.drag_kgf - 1) < 0.02
assert abs(c8.av_m / c6.av_m - 1) < 0.08
```

At 3 kn, AH and the drag change by less than 2 % between resolutions 6 and 8, and by less than
10 % from resolution 3. The vertical opening converges more slowly and **decreases** as the mesh is
refined: 1.96 / 1.72 / 1.63 m with resolutions 3, 6 and 8, and according to
`tests/test_sim_slow.py` 1.48 and 1.40 m with 10 and 12. A coarse mesh cannot represent the
curvature of the headrope between floats and overestimates it; the converged value is closer to the
1.4 m of DynamiT than the one at resolution 6. The cost grows with the number of nodes (≈ 1 s per
speed at resolution 3–4, ≈ 4 s at 6, ≈ 10 s at 8): the API (`POST /simulate`) uses 4 by default,
the web application offers 3 (“fast”) and 6 (“normal”), and this chapter validates with 6.

## Validation against DynamiT and against the engine

The standard FAO A-3 net is simulated at the nine speeds of the DynamiT table
({doc}`32_validacion_dynamit`) with the engine's door spread (32.5 m) and the default coefficients,
and compared with DynamiT and with the empirical quantities of the engine: Fridman's DPA, Fridman's
AV and the design $R_N$ (Aberdeen).

```{code-cell} ipython3
:tags: [hide-input]
VAL = validate(resolution=RES, result=R)
v = VAL.v_kn
band = (v >= FISHING_BAND_KN[0]) & (v <= FISHING_BAND_KN[1])
SPEC = (("AH", "m", 1, "DPA Fridman"), ("AV", "m", 2, "AV Fridman"),
        ("RA", "kgf", 0, "Rn diseño (Aberdeen)"))
rows = []
for var, unit, nd, ename in SPEC:
    sim, dyn, eng = VAL.sim[var], VAL.dynamit[var], VAL.engine[var][ename]
    rows.append([f"{var} DynamiT [{unit}]", *[V.fmt(x, nd) for x in dyn]])
    rows.append([f"**{var} simulation [{unit}]**", *[V.fmt(x, nd) for x in sim]])
    rows.append([f"{var} engine [{unit}]", *[V.fmt(x, nd) for x in eng]])
    rows.append([f"Δ {var} sim/DynamiT [%]", *[V.pct_s(a, b, 0) for a, b in zip(sim, dyn)]])
    rows.append([f"Δ {var} engine/DynamiT [%]", *[V.pct_s(a, b, 0) for a, b in zip(eng, dyn)]])
V.md_table(["v [kn]", *[V.fmt(x, 1) for x in v]], rows)
```

```{code-cell} ipython3
:tags: [hide-input]
rows = []
for var, _, _, ename in SPEC:
    es, ee = VAL.errors[var], VAL.engine_errors[var][ename]
    rows.append([var, V.sfmt(es.bias_pct_band, 1), V.fmt(es.mean_abs_pct_band, 1),
                 V.fmt(es.mean_abs_pct, 1), V.sfmt(ee.bias_pct_band, 1),
                 V.fmt(ee.mean_abs_pct_band, 1), V.fmt(ee.mean_abs_pct, 1)])
V.md_table(["Variable", "Sim bias 2–4 kn [%]", "Sim error 2–4 kn [%]", "Sim error 1–5 kn [%]",
            "Engine bias 2–4 kn [%]", "Engine error 2–4 kn [%]", "Engine error 1–5 kn [%]"], rows)
N_SIM = speed_exponent(v, VAL.sim["RA"])
N_DYN = speed_exponent(v, VAL.dynamit["RA"])
print(f"Speed exponent of the drag: simulation v^{N_SIM:.2f}, "
      f"DynamiT v^{N_DYN:.2f}")
# What the text says.
assert VAL.errors["AH"].mean_abs_pct_band < 5
assert VAL.errors["AV"].mean_abs_pct_band < 20
assert -55 < VAL.errors["RA"].bias_pct_band < -40
assert 1.6 < N_SIM < 1.85 and 1.4 < N_DYN < 1.55
```

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Standard FAO A-3 net according to DynamiT (black dots), the shape simulation of
      `trawlkit.sim` (resolution 6, otter boards at 32.5 m) and the empirical engine (Fridman's
      DPA and AV, Aberdeen $R_N$). The grey band marks the fishing range, 2–4 kn.
    name: fig-21-validacion
---
fig, axes = P.plt.subplots(1, 3, figsize=(10.2, 3.6))
TITLES = {"AH": "Horizontal opening AH [m]", "AV": "Vertical opening AV [m]",
          "RA": "Net drag [kgf]"}
for ax, (var, unit, nd, ename) in zip(axes, SPEC):
    ax.axvspan(*FISHING_BAND_KN, color=P.NEUTRAL_WASH, lw=0, zorder=0)
    ax.plot(v, VAL.dynamit[var], "o", color=P.INK, ms=6, mec=P.SURFACE, mew=1.2, zorder=4,
            label="DynamiT")
    P.line(ax, v, VAL.sim[var], 1, "Simulation")
    P.line(ax, v, VAL.engine[var][ename], 2, "Empirical engine")
    ax.set_title(TITLES[var], fontsize=10.5)
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.set_xlim(0.8, 5.2)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Speed [kn]")
P.legend(axes[2], loc="upper left", fontsize=8.5)
P.finish(fig)
```

**Horizontal opening.** This is where the simulation gets it right: within 3 % of DynamiT between 2
and 4 kn, and with the same **plateau** (13–13.5 m) that Fridman's DPA does not have: in the
simulation the headrope, footrope and netting, of fixed length, limit the opening, whereas
Fridman's formula keeps growing with speed (16 m at 5 kn). Below 2 kn the simulation
overestimates: with the otter boards fixed at 32.5 m the net stays open even when there is no drag
to stretch it, and DynamiT, which does compute the otter boards, closes them to 28.5 m at 1 kn.

**Vertical opening.** The trend is that of DynamiT —the net flattens as it speeds up because the
drag grows faster than the buoyancy— with a bias of +10 % in the fishing range, comparable to that
of Fridman's AV, and which decreases as the mesh is refined (previous section). Like Fridman, the
simulation does not reproduce the **upturn** of DynamiT above 4 kn (1.0 → 1.6 m): in the
simulation the AV keeps falling down to 0.5 m. That upturn needs something the model does not
have: a footrope that lifts off the seabed or a change in the share of tension between wings and
bridles that depends on the otter boards and the warps.

**Drag.** This is the big discrepancy: the simulation gives **half** of DynamiT over the whole
range (≈ −50 %), while the empirical engine gives ≈ 20 % more. It also grows faster with speed
($v^{1.73}$ against $v^{1.48}$), somewhat closer to the $v^2$ of a rigid body: the simulated
netting aligns with the flow, but not as much as in DynamiT. The next section analyses the gap.

### With the DynamiT door spread

DynamiT computes the door spread (47–52 m in the fishing range), whereas the engine fixes it at
32.5 m with the “per metre of warp” rule (−35 %, {doc}`32_validacion_dynamit`). Imposing the
DynamiT DP on the simulation isolates the net from the otter board model:

```{code-cell} ipython3
:tags: [hide-input]
VAL_D = validate(resolution=4, door_spread="dynamit", result=R)  # resolution 4: faster
rows = []
for var in ("AH", "AV", "RA"):
    a, b = VAL.errors[var], VAL_D.errors[var]
    rows.append([var, V.sfmt(a.bias_pct_band, 1), V.sfmt(b.bias_pct_band, 1)])
V.md_table(["Variable", "Bias 2–4 kn, engine DP [%]", "Bias 2–4 kn, DynamiT DP (resolution 4) [%]"],
           rows)
assert VAL_D.errors["AH"].bias_pct_band > 25 and VAL_D.errors["AV"].bias_pct_band < -35
```

With the otter boards 15–20 m further apart the simulated net opens ≈ 35 % more than in DynamiT
and flattens (AV ≈ −45 %); the drag rises, but stays ≈ 40 % below. That the AH gets worse with the
“correct” DP indicates that in DynamiT the rigging geometry is different (longer sweeps and
bridles, or a different angle of attack) and is not known: the DynamiT screenshot does not include
those data. With the engine DP the simulated net has the geometry of the other stages of the book,
and that is the comparison used in the rest of the chapter.

## Calibration: are the twine coefficients enough?

The Morison drag is linear in $C_N$ and $C_T$, so the natural question is whether there are
reasonable coefficients that close the gap. $C_N$ is swept over the whole range of the literature
and $C_T$ between 0.04 and 0.12, at 3 kn. With $C_T \approx 0.01$ the relaxation does not converge
in 40,000 iterations: with almost no tangential force the body and the codend, aligned with the
flow, have no tension to stretch them and keep drifting.

```{code-cell} ipython3
:tags: [hide-input]
CAL = calibrate(cn_values=(1.0, 1.4, 1.6), ct_values=(0.04, 0.08, 0.12), speeds_kn=(3.0,),
                resolution=3, door_spread="engine", result=R)
rows = [[V.fmt(c["cn"], 1), V.fmt(c["ct"], 2), V.sfmt(c["ra_bias_pct"], 0),
         V.fmt(c["ah_mean_abs_pct"], 0), V.fmt(c["av_mean_abs_pct"], 0)] for c in CAL]
V.md_table(["C_N", "C_T", "Δ RA vs DynamiT [%]", "|Δ AH| [%]", "|Δ AV| [%]"], rows)
best = CAL[0]
assert (best["cn"], best["ct"]) == (1.6, 0.12) and best["ra_bias_pct"] < -30
print(f"Ranges: C_N {CN_RANGE}, C_T {CT_RANGE}")
```

Even with both coefficients at the top of their range the drag stays ≈ 40 % below DynamiT. $C_T$
weighs more than $C_N$: a large part of the netting, above all the body and the codend, works
almost aligned with the flow, where only the tangential component acts. Raising $C_T$ also opens
the net vertically (the extra tension lifts the headrope), so the calibration is not free: it
moves the AV. The knots, ignored by default, add form drag, independent of the orientation of the
twine:

```{code-cell} ipython3
:tags: [hide-input]
rows = []
KNOTS = {}
for kf in (0.0, 2.0, 3.0):
    kv = KNOTS[kf] = validate(resolution=4, knot_factor=kf, speeds_kn=[2.0, 3.0, 4.0], result=R)
    rows.append([V.fmt(kf, 1), *[V.fmt(x, 0) for x in kv.sim["RA"]],
                 V.sfmt(kv.errors["RA"].pct.mean(), 0), *[V.fmt(x, 2) for x in kv.sim["AV"]],
                 V.fmt(speed_exponent(kv.v_kn, kv.sim["RA"]), 2)])
V.md_table(["Knot k = D/d", "RA 2 kn", "RA 3 kn", "RA 4 kn", "Mean Δ RA [%]", "AV 2 kn",
            "AV 3 kn", "AV 4 kn", "Exponent"], rows)
print("DynamiT: RA", [round(x) for x in np.asarray(DYNAMIT["RA_kg"])[[2, 4, 6]]],
      "AV", [float(x) for x in np.asarray(DYNAMIT["AV_m"])[[2, 4, 6]]])
k3 = KNOTS[3.0]
assert -25 < k3.errors["RA"].pct[0] < -5 and k3.errors["RA"].pct[2] > -5
assert speed_exponent(k3.v_kn, k3.sim["RA"]) > 1.8 and k3.sim["AV"][2] < 0.7
```

With knots of 3 times the twine diameter the drag reaches that of DynamiT between 3 and 4 kn, but
with the wrong shape: the drag of the knots is that of a sphere, $\propto v^2$, so the curve ends up
too steep (exponent ≈ 1.9 against 1.48; −17 % at 2 kn and above at 4 kn) and the net flattens (AV
of 0.4–0.6 m at 4 kn against 1.0 m in DynamiT).
No single physical parameter of the model closes the gap without breaking something else.

## The drag gap

The plausible causes, in order of estimated importance:

1. **Coefficients of an isolated twine.** Morison with the $C_N$, $C_T$ of a smooth cylinder in
   uniform flow underestimates the drag of a braided netting twine: roughness, vortex-induced
   vibration and the undulation of the netting (“flapping”) increase the effective drag. Net
   simulators, DynamiT included, use **netting** coefficients fitted in a flume or tank, not twine
   coefficients; with PA twines of 1–2 mm and 2–3 kn the Reynolds number of the twine (≈ 10³) is
   moreover in the zone where $C_N$ changes with speed.
2. **Knots and edges.** The knots (≈ 2–3 twine diameters, two per mesh), the seams, the mounted
   headrope and footrope and the reinforcements are not in the default model; the previous table
   shows that they are enough to explain a large fraction of the difference.
3. **Codend and catch.** The simulated codend is empty and its excess length (codend J of 250
   meshes sewn to codend I of 200) forms a slack bag; in a real net the codend fills with retained
   water and catch, with the drag of a bluff body.
4. **Seabed.** The simulated friction of the footrope is small (≈ 12 kgf at 3 kn, 2 % of the drag),
   because the footrope barely rests on the seabed with the ballast of this design; DynamiT does not
   report its own. The speed-independent term of Aberdeen (the friction of the parts that drag on
   the seabed, {doc}`32_validacion_dynamit`) suggests that the engine does carry a larger seabed
   friction.
5. **What RA includes.** If the DynamiT RA included part of the rigging (bridles, sweeps, the
   cables between otter boards and net) the gap would be smaller; the screenshot does not make it
   clear ({doc}`32_validacion_dynamit`).

The practical conclusion is the same as in the note of the web application: **the simulation is
useful for the shape and the openings**, which depend on the balance between forces and not on
their absolute value, and the **engine remains the reference for the design drag**, which is
conservative.

## The shape at 3 kn

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Equilibrium shape of the standard FAO A-3 net at 3 kn (resolution 6, otter boards at
      32.5 m), coloured by twine tension. The headrope (blue) and the footrope (black) bound the
      mouth; the net moves to the left. Vertical scale × 3. The figure is interactive (rotate,
      zoom).
    name: fig-21-forma
---
import plotly.graph_objects as go
from IPython.display import HTML

r3 = next(r for r in VAL.results if r.speed_kn == 3.0)
xyz = r3.nodes
tens = np.zeros(len(xyz))
cnt = np.zeros(len(xyz))
tt = r3.twine_tension_n.max(axis=1)
for k in range(3):
    np.add.at(tens, r3.triangles[:, k], tt)
    np.add.at(cnt, r3.triangles[:, k], 1)
tens = np.divide(tens, cnt, out=np.zeros_like(tens), where=cnt > 0)
EX = 3.0  # vertical exaggeration
fig = go.Figure()
fig.add_trace(go.Mesh3d(
    x=xyz[:, 0], y=xyz[:, 1], z=xyz[:, 2] * EX,
    i=r3.triangles[:, 0], j=r3.triangles[:, 1], k=r3.triangles[:, 2],
    intensity=tens, colorscale="Blues", opacity=0.85, flatshading=True,
    colorbar=dict(title="Twine tension [N]", thickness=12), name="netting",
    hovertemplate="x %{x:.1f} m<br>y %{y:.1f} m<extra></extra>"))
for idx, color, name in ((r3.headrope, P.color(1), "headrope"), (r3.footrope, P.INK, "footrope")):
    p = xyz[idx]
    fig.add_trace(go.Scatter3d(x=p[:, 0], y=p[:, 1], z=p[:, 2] * EX, mode="lines",
                               line=dict(color=color, width=6), name=name))
# Scene bounded to the net (no otter boards or sweeps) with real proportions (z exaggerated).
net = xyz[np.unique(r3.triangles)]
lo, hi = net.min(axis=0), net.max(axis=0)
lo[2], hi[2] = 0.0, hi[2] * EX
span = hi - lo
fig.update_layout(
    height=500, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor=P.SURFACE,
    scene=dict(
        xaxis=dict(title="x [m]", range=[lo[0], hi[0]]),
        yaxis=dict(title="y [m]", range=[lo[1], hi[1]]),
        zaxis=dict(title="z × 3 [m]", range=[lo[2], hi[2]]),
        aspectmode="manual",
        aspectratio=dict(x=1.0, y=span[1] / span[0], z=span[2] / span[0]),
        camera=dict(eye=dict(x=-0.55, y=-1.15, z=0.6), center=dict(x=0, y=0, z=-0.15)),
    ),
    legend=dict(x=0.02, y=0.98))
# A single HTML output (plotly.js from its CDN): it shows in the static book without a server.
HTML(fig.to_html(full_html=False, include_plotlyjs="cdn", config={"displaylogo": False}))
```

```{code-cell} ipython3
:tags: [hide-input]
rows = [["Horizontal opening AH (headrope)", V.fmt(r3.ah_m, 2), "m"],
        ["Horizontal opening (footrope)", V.fmt(r3.ah_lower_m, 2), "m"],
        ["Vertical opening AV", V.fmt(r3.av_m, 2), "m"],
        ["Headrope height at the centre", V.fmt(r3.headrope_height_m, 2), "m"],
        ["Mouth area", V.fmt(r3.mouth_area_m2, 1), "m²"],
        ["Water drag", V.fmt(r3.hydro_drag_kgf, 0), "kgf"],
        ["Seabed friction", V.fmt(r3.friction_kgf, 0), "kgf"],
        ["Bridle pull", V.fmt(r3.bridle_pull_kgf, 0), "kgf"],
        ["Net length (wing tip to codend)", V.fmt(r3.net_length_m, 1), "m"],
        ["Iterations / residual", f"{r3.iterations} / {r3.residual:.1e}", ""]]
V.md_table(["Quantity at 3 kn", "Value", "Unit"], rows)
assert abs(r3.bridle_pull_kgf / r3.drag_kgf - 1) < 0.03  # global equilibrium
```

The pull of the bridles equals the drag of the net (water plus seabed) within 3 %: global
equilibrium holds. The tension is concentrated in the wings and in the body near the bosom, which
transmit the pull of the bridles, and it falls towards the codend.

## Assumptions and limits

- **Otter boards and warps outside the model.** The door spread is an input (the engine's or an
  imposed one); there is no otter board equilibrium and no catenary of the warp. That is why the
  simulation does not predict the DP and overestimates the AH at low speed.
- **Drag ≈ 50 % low** compared with DynamiT with the twine coefficients of the literature
  (previous section). Do not use the simulated drag to size the vessel or the warp.
- **Quasi-static.** A single steady state per speed, without waves, vessel pitching or changes of
  course; no catch in the codend.
- **Coarse mesh.** The AV converges slowly with the resolution (≈ 15 % between 6 and 12); AH and
  drag converge quickly.
- **A single validation case.** The standard FAO A-3 net against a single DynamiT simulation with
  unknown rigging; neither tool has been compared with measurements at sea.

```{code-cell} ipython3
:tags: [remove-cell]
print(f"Total chapter time: {time.perf_counter() - T0:.0f} s")
```
