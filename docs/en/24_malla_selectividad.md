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

# Mesh zoom and selectivity

```{code-cell} ipython3
:tags: [remove-cell]
import sys, pathlib
DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English
import dataclasses
import math
import time

import numpy as np
import _plots_t2 as P
import _plots_v as PV
from myst_nb import glue
from trawlkit.model import run
from trawlkit.selectivity import (
    ESCAPE_ATTEMPTS,
    ESCAPE_ZONE_M,
    codend_variant,
    escape_zone,
    selectivity,
    species_catalogue,
)
from trawlkit.sim import Scenario, explore, simulate
from trawlkit.sim.core import DEFAULT_MESH_BENDING_PA
from trawlkit.sim.mesh import DIAMOND_REST_ANGLE_DEG
from trawlkit.sim.validation import standard_case

P.setup()
T0 = time.perf_counter()
RES = 3
CASE = standard_case()
SC = Scenario(seabed="mixed", catch_kg=300, mesh_bending=True)

from trawlkit.i18n import tr


def sp_name(s) -> str:
    return tr(s.name)


def num(x: float, nd: int = 1) -> str:
    return f"{x:.{nd}f}"


def sim(orientation: str, mesh_mm: float, scenario: Scenario = SC):
    net = codend_variant(CASE.net, orientation, mesh_mm=mesh_mm)
    r = run(dataclasses.replace(CASE, net=net))
    return simulate(r, 3.0, resolution=RES, coarse_resolution=None, scenario=scenario)
```

## Purpose

{doc}`21_simulacion` to {doc}`23_mar_real` solve the shape of the complete net. This chapter goes
down to **each mesh**: how open it stays at equilibrium, with the catch, the speed and the seabed
of each haul. With that shape, it computes which fish lengths escape through the codend (size
**selectivity**) and compares codends of **diamond**, **T90** and **square** mesh.

The published selectivity tools take the mesh opening as an input (FISHSELECT,
{cite:t}`herrmann2009`) or simulate only the codend (PRESEMO, {cite:t}`herrmann2005`;
{cite:t}`herrmann2007`). Here the opening comes from the simulation of the complete net, with the
otter boards, the seabed and the catch: the same model that drives the animated explorer.

## The mesh inside the element

In Priour's triangular element ({doc}`21_simulacion`) the position is linear in the twine
coordinates $(i, j)$. The bar vectors of each twine family,

$$
\mathbf e_i = \frac{\partial \mathbf x}{\partial i}, \qquad
\mathbf e_j = \frac{\partial \mathbf x}{\partial j},
$$ (eq-24-legs)

are constant in the triangle, so all its meshes have the same shape: a parallelogram with sides
$\mathbf e_i$ and $\mathbf e_j$. Its opening angle and the heights between opposite sides are

$$
\beta = \arccos \frac{\mathbf e_i \cdot \mathbf e_j}{|\mathbf e_i| |\mathbf e_j|}, \qquad
h_i = |\mathbf e_j| \sin\beta, \qquad h_j = |\mathbf e_i| \sin\beta .
$$ (eq-24-opening)

The **clear opening** of the mesh, through which a fish passes, subtracts the twine diameter $d$:
$h' = h - d$. The reconstruction of the meshes of a triangle is exact, with no interpolation: it is
what the mesh zoom of the application draws ({doc}`web`).

## Diamond, T90 and square mesh

In **diamond** mesh the long diagonal runs along the net; the longitudinal tension closes it. In
**T90** the same netting is turned 90°: the long diagonal lies across. In **square** mesh the
twines run along and across, and the tension does not close the mesh.

For an ideal twine (with no bending stiffness), diamond and T90 would be the same mesh. What sets
them apart is the **resistance of the mesh to opening or closing**: the knot and the braided twine
have a rest shape and resist moving away from it {cite:p}`sala2007`. The simulator models it as a
hinge at each knot:

$$
E = \tfrac12 K (\beta - \beta_0)^2, \qquad K = 4\,A_{ij}\,\frac{EI}{a}, \qquad
EI = E_b \frac{\pi d^4}{64},
$$ (eq-24-bending)

with $A_{ij}$ meshes per triangle, $a$ the bar length and $\beta_0$ the rest angle: that of the
diamond, its supplement in T90 (the turned knot tends to open the mesh across) and 90° in square
mesh.

```{code-cell} ipython3
:tags: [remove-cell]
glue("beta0", f"{DIAMOND_REST_ANGLE_DEG:.0f}", display=False)
glue("beta0_t90", f"{180 - DIAMOND_REST_ANGLE_DEG:.0f}", display=False)
glue("eb", num(DEFAULT_MESH_BENDING_PA / 1e8, 1), display=False)
glue("ei4", num(DEFAULT_MESH_BENDING_PA * math.pi * 0.004**4 / 64 * 1e3, 1), display=False)
```

Values used (“TO BE VERIFIED”): $\beta_0$ = {glue:text}`beta0`° in diamond and
{glue:text}`beta0_t90`° in T90, and $E_b$ = {glue:text}`eb`·10⁸ Pa. The latter gives
$EI$ ≈ {glue:text}`ei4`·10⁻³ N·m² for a 4 mm twine, of the order of what {cite:t}`sala2007`
measured. The stiffness switches on by itself when the net has T90 or square-mesh panels. When
comparing codends it is switched on in all of them, the diamond one included, so that the
comparison is fair. With fine twine and high tension the hinge matters little; where the tension
is low, ahead of the catch, it keeps the T90 mesh open.

In the empirical engine, the orientation changes the working area of the square-mesh panel (each
mesh is a square with a side of one bar) and the full-scale plan.

## Passage model and retention curve

A fish of length $L$ escapes through a mesh if the ellipse of its **least compressible cross
section** fits through the clear opening, turned in its favour {cite:p}`herrmann2009`. The ellipse
has semi-axes $A = c\,h\,L/2$ (height) and $B = c\,w\,L/2$ (width), with $h$ and $w$ the shape of
the species and $c$ the compression of the tissues. It fits if there is a rotation $\theta$ with

$$
\sqrt{A^2 (\mathbf n_k\cdot\mathbf u)^2 + B^2 (\mathbf n_k\cdot\mathbf v)^2} \le \frac{h_k'}{2},
\qquad k = i, j ,
$$ (eq-24-pass)

where $\mathbf n_k$ is the normal to each pair of sides and $\mathbf u$, $\mathbf v$ the axes of
the ellipse. Since $A$ and $B$ grow with $L$, each mesh has a maximum passing length $L_m$.

The candidate meshes are those of the codend in a band ahead of the catch. That is where the fish
accumulate and try to get out {cite:p}`herrmann2005`. The part covered by the catch does not count.
With the morphological variability $cv$, the probability of passing through a random mesh of the
band is

$$
p(L) = \frac{\sum_m w_m\, \Phi\!\left(\frac{L_m/L - 1}{cv}\right)}{\sum_m w_m} .
$$ (eq-24-pmesh)

Each fish tries $k$ meshes and escapes if it passes through any of them; a fraction $C$ gets to
try. The retention is

$$
r(L) = 1 - C\left[1 - \bigl(1 - p(L)\bigr)^k\right] .
$$ (eq-24-retention)

From the curve come $L_{50}$ (length retained at 50 %), the selection range
$SR = L_{75} - L_{25}$ and the selection factor $SF = L_{50}/\text{mesh size}$.

```{code-cell} ipython3
:tags: [remove-cell]
glue("zone", num(ESCAPE_ZONE_M, 0), display=False)
glue("attempts", str(ESCAPE_ATTEMPTS), display=False)
```

Values used (“TO BE VERIFIED”): band of {glue:text}`zone` m, $k$ = {glue:text}`attempts`
attempts and $C$ = 1.

## Species

```{code-cell} ipython3
:tags: [remove-input]
PV.md_table(
    ["Species", "Scientific name", "Length", "Height / length", "Width / length", "Compression"],
    [
        [
            sp_name(s),
            s.scientific_name,
            f"{s.measure} [{s.unit}]",
            num(s.height, 3),
            num(s.width, 3),
            num(s.compression, 2),
        ]
        for s in species_catalogue()
    ],
)
```

The cross sections come from `data/species.yaml` and are order-of-magnitude estimates (“TO BE
VERIFIED”). For cod, haddock and Norway lobster there are measurements with FISHSELECT
{cite:p}`herrmann2009,frandsen2010`, which should replace these for quantitative use. In
crustaceans the length is the carapace length (Norway lobster) or the total length (Argentine red
shrimp), and the cross section is that of the rigid carapace. The claws of the Norway lobster get
entangled in the netting and are not modelled {cite:p}`krag2008`.

## 120 mm codend: diamond, T90 and square

```{code-cell} ipython3
:tags: [remove-cell]
VAR = {o: sim(o, 120.0) for o in ("diamond", "t90", "square")}
LABEL = {"diamond": "Diamond", "t90": "T90", "square": "Square"}
SPECIES = ("cod", "haddock", "hake_hubbsi", "plaice")
CURVES = {o: {c.species.id: c for c in selectivity(r, SPECIES)} for o, r in VAR.items()}
l50 = {o: CURVES[o]["cod"].l50 for o in VAR}
assert l50["diamond"] < l50["t90"] and l50["diamond"] < l50["square"]
assert 2.5 < CURVES["diamond"]["cod"].sf < 4.5
glue("cod_d", num(l50["diamond"]), display=False)
glue("cod_t", num(l50["t90"]), display=False)
glue("sf_d", num(CURVES["diamond"]["cod"].sf, 1), display=False)
glue("sr_d", num(CURVES["diamond"]["cod"].sr), display=False)
glue("sr_t", num(CURVES["t90"]["cod"].sr), display=False)
```

Codend of the FAO A-3 net remade with 120 mm mesh (same mounted width and length), 300 kg of
catch, mixed seabed, 3 kn:

```{code-cell} ipython3
:tags: [remove-input]
rows = []
for o, r in VAR.items():
    ms = r.mesh.summary()
    rows.append(
        [LABEL[o], f"{ms['opening_deg']:.0f}°"]
        + [f"{num(CURVES[o][s].l50)} · {num(CURVES[o][s].sr)}" for s in SPECIES]
    )
PV.md_table(
    ["Codend", "Mean opening", *(f"{sp_name(CURVES['diamond'][s].species)} L50 · SR [cm]" for s in SPECIES)],
    rows,
)
```

```{code-cell} ipython3
:tags: [remove-input]
fig, axes = P.plt.subplots(1, 2, figsize=(10.2, 3.6))
for ax, sp in zip(axes, ("cod", "plaice"), strict=True):
    for k, o in enumerate(VAR):
        c = CURVES[o][sp]
        P.line(ax, c.lengths, c.retention, k, LABEL[o], marker=False)
    ax.axhline(0.5, color="0.6", lw=0.8, ls="--")
    ax.set_title(f"Retention of {sp_name(CURVES['diamond'][sp].species).lower()}")
    ax.set_xlabel("Total length [cm]")
    ax.set_ylim(0, 1.02)
P.legend(axes[0])
P.finish(fig)
```

For cod, the diamond codend gives $L_{50}$ = {glue:text}`cod_d` cm and SR = {glue:text}`sr_d` cm
($SF$ ≈ {glue:text}`sf_d`). This is the order of the 120 mm diamond codends measured at sea
{cite:p}`wienbeck2011`. The T90 raises $L_{50}$ to {glue:text}`cod_t` cm and gives a sharper
selection (SR = {glue:text}`sr_t` cm), in the direction of what {cite:t}`wienbeck2011` observed and
{cite:t}`herrmann2007` predicted.

Plaice, flat and thin, passes edgewise. Its $L_{50}$ hardly depends on how the mesh opens: it
depends on the smallest clear opening. That is why a square-mesh or T90 codend does not select it
better than a diamond one, as is known from mixed flatfish fisheries.

## The catch opens the meshes ahead of it

```{code-cell} ipython3
:tags: [remove-cell]
net = codend_variant(CASE.net, "diamond", mesh_mm=120.0)
R = run(dataclasses.replace(CASE, net=net))
CATCHES = [100.0, 300.0, 600.0, 1000.0]
HAUL = explore(R, "catch_kg", CATCHES, scenario=SC, resolution=RES)


def front_opening(r) -> float:
    st = r.mesh
    z = escape_zone(st)
    return float(np.average(st.opening_deg[z], weights=st.meshes[z]))


opening = [front_opening(r) for r in HAUL]
l50_haul = [selectivity(r, "cod")[0].l50 for r in HAUL]
assert opening[-1] > opening[0] and l50_haul[-1] > l50_haul[0]
glue("op_lo", f"{opening[0]:.0f}", display=False)
glue("op_hi", f"{opening[-1]:.0f}", display=False)
glue("l50_lo", num(l50_haul[0]), display=False)
glue("l50_hi", num(l50_haul[-1]), display=False)
```

```{code-cell} ipython3
:tags: [remove-input]
fig, axes = P.plt.subplots(1, 2, figsize=(10.2, 3.4))
P.line(axes[0], CATCHES, opening, 1, "")
P.line(axes[1], CATCHES, l50_haul, 0, "")
axes[0].set_title("Mesh opening ahead of the catch [°]")
axes[1].set_title("Cod L50 [cm]")
for ax in axes:
    ax.set_xlabel("Catch in the codend [kg]")
P.finish(fig)
```

As the catch grows, the catch ball inflates the codend. The meshes of the escape band go from
{glue:text}`op_lo`° to {glue:text}`op_hi`° of opening between 100 and 1000 kg, and the $L_{50}$ of
cod rises from {glue:text}`l50_lo` to {glue:text}`l50_hi` cm. This is the catch size effect
described by {cite:t}`herrmann2005`. The animated explorer of the application shows it state by
state if a species is chosen.

## Assumptions and limits

- **Geometric escape only**: there is no fish behaviour (swimming, exhaustion, searching for the
  mesh), and the contact $C$ and the attempts $k$ are constant.
- **Elliptical cross section** scaled with length, with estimated coefficients (“TO BE VERIFIED”).
  FISHSELECT uses measured shapes and finer penetration models.
- **Opening stiffness**: a linear hinge per knot with estimated $E_b$ and $\beta_0$. It does not
  model the slipping of the knots or the hysteresis of used netting.
- **Resolution**: inside a triangle all the meshes are equal. The variation from mesh to mesh
  depends on the resolution of the simulation (3–4 in the application).
- **Escape panels** (square-mesh windows, grids) and selectivity during the hauling manoeuvre are
  not modelled.

```{code-cell} ipython3
:tags: [remove-cell]
print(f"chapter executed in {time.perf_counter() - T0:.0f} s")
```

## Exercises

From the bank of the teaching mode, with the data of the book. In the app, the “UTN Classroom”
mode generates them with other data and marks them ({doc}`38_docentes`).

```{code-cell} ipython3
:tags: [remove-input]
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path.cwd().parent))
import _exercises
_exercises.section("24_malla_selectividad")
```
