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

# Simulation with catch, seabed and coupled otter boards

```{code-cell} ipython3
:tags: [remove-cell]
import sys, pathlib
DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English
import time

import numpy as np

import _plots_t2 as P
from trawlkit.model import run
from trawlkit.rigging import seabeds
from trawlkit.sim import Scenario, haul, simulate
from trawlkit.sim.validation import DYNAMIT, standard_case

P.setup()
T0 = time.perf_counter()
R = run(standard_case())  # standard FAO A-3 net, 150 HP, FAO otter board, corrected mode
RES = 4
CATCHES = [0.0, 500.0, 1000.0, 1500.0]
V = 3.0
```

## Purpose

{doc}`21_simulacion` solves the shape of the **clean, empty** net, with a single friction with the
seabed and the otter boards fixed at the spread given by the engine's rule. At sea, the net works
under real conditions: the catch fills the codend and slows it down, the type of seabed changes the
friction of the groundgear and of the otter boards, and the otter boards do not run at a fixed
spread but at the one that results from the equilibrium between their lift, the net that pulls them
together and the warp that tows them. This chapter adds those three conditions to the simulator
(`trawlkit.sim.Scenario`) and the **progressive haul** (`trawlkit.sim.haul`): a sequence of
equilibria while the catch comes in.

### Overview: what is on the market and what this project adds

| Tool | Organization | Model | Catch | Seabed type | Uncertainty | Open |
|---|---|---|---|---|---|---|
| DynamiT {cite:p}`dynamit` | Ifremer | Priour finite elements, dynamic | no | flat seabed, no sediment | no | no |
| SimuTrawl | MPSL (Korea) | Mass-spring {cite:p}`lee2005` | no | mud only (according to {cite:t}`nguyen2016`) | no | no |
| Trawl Vision PRO | AcruxSoft | Semi-empirical + sensors | no | no | no | no |
| NaLA | Nitto Seimo | Masses and springs {cite:p}`takagi2004` | no | no | data assimilation in purse seines | no |
| FhSim | SINTEF | Time-domain simulation | no | no | state estimation | partial |
| **trawl-design-lab** | this project | Priour elements + FIRE, coupled otter boards | **yes** | **catalogue with range** | **(delivery 11.4)** | **yes** |

The comparison by {cite:t}`nguyen2016` and the search made for this chapter agree: no commercial
simulator models the catch in the codend, the type of sediment in detail, the fouling of the net or
the uncertainty. The catch and its effect on the shape of the codend exist in research tools
(FEMNET and PRESEMO, {cite:t}`herrmann2005`) but not integrated with the complete net, the otter
boards and the seabed in an open tool that runs in the browser. That is the differentiator built
in Phase 11: this chapter covers the catch, the seabed and the coupled otter boards; the following
deliveries add fouling, current, energy and seabed footprint, the mesh-by-mesh zoom with
selectivity and the uncertainty bands.

## Model

### Catch in the codend

The catch occupies the closed end of the codend with a volume

$$
V_c = \frac{m_c}{\rho_a},
$$ (eq-22-volume)

with $m_c$ the catch and $\rho_a$ the bulk density (organisms and interstitial water; 750 kg/m³ by
default for fish, 850 for crustaceans and 1000 for a mixture with mud or shell, values
“TO BE VERIFIED”). The codend is traversed ring by ring from the closed end (each ring is a row of
the central top and bottom panels) and the volume between sections is integrated as conical
frusta until $V_c$ is reached. Each section is taken with the area of the circle of its perimeter,
$A = P^2/4\pi$: the catch **inflates** the codend up to its circumference (an empty codend runs
flattened and its instantaneous area is almost zero, which would make the catch “occupy” the whole
net).

In the occupied zone the twines stop filtering (the flow is blocked) and the netting receives, as
in the model of {cite:t}`oneill1997codend`, the outward normal pressure of the catch “ball”:

$$
p_c = \tfrac12\,\rho\,C_p\,v^2 ,
$$ (eq-22-pressure)

with $C_p = 1$ by default (“TO BE VERIFIED”). On a surface that is closed except for the front of
the catch, the axial resultant of that pressure is $p_c\,A_f$, with $A_f$ the area of the front:
it is the drag of the catch. The submerged weight of the organisms, $m_c\,g\,(1-\rho/\rho_o)$ with
$\rho_o$ their density, is distributed over the lower half of the zone. The zone is recomputed
during the relaxation with the current shape.

### Seabed type

The friction with the seabed is Coulomb friction (normal reaction times $\mu$, opposite to the
motion). The catalogue `data/seabed.yaml` gives, per sediment type, a $\mu$ for the groundgear and
the netting resting on the seabed and another for the otter board shoes, each with a nominal value
and a range, and the BENTHIS penetration class {cite:p}`eigaard2016`:

```{code-cell} ipython3
:tags: [remove-input]
import _plots_v as PV

# English names of the catalogue entries (the catalogue data/seabed.yaml is in Spanish).
SEABED_EN = {"mud": "Mud", "sand": "Sand", "mixed": "Intermediate (mixed)",
             "gravel": "Gravel and shell", "rock": "Rock or stone"}
PENETRATION_EN = {"alta": "high", "media": "medium", "baja": "low"}


def es(x: float) -> str:
    return f"{x:.2f}"

PV.md_table(
    ["Seabed", "μ groundgear and netting", "μ otter board", "Penetration"],
    [
        [
            SEABED_EN.get(s.id, s.name),
            f"{es(s.mu_gear.nominal)} ({es(s.mu_gear.low)}–{es(s.mu_gear.high)})",
            f"{es(s.mu_door.nominal)} ({es(s.mu_door.low)}–{es(s.mu_door.high)})",
            PENETRATION_EN.get(s.penetration, s.penetration),
        ]
        for s in seabeds()
    ],
)
```

There is no published table of friction coefficients per sediment for trawl gear (there are
measurements of the groundgear drag per sediment type, {cite:t}`oneill2016`): the values are
engineering estimates, marked “TO BE VERIFIED”, and that is why they carry a range. The uncertainty
delivery ({doc}`25_incertidumbre_calibracion`) treats them as uncertain variables instead of exact
numbers.

### Coupled otter boards

With `coupled_doors` each otter board is a free node with

$$
\mathbf{F}_\text{door} = \tfrac12\rho A v^2 \left(C_D\,\hat{\mathbf{x}} + C_L\,\hat{\mathbf{y}}_\text{out}\right)
- W_\text{water}\,\hat{\mathbf{z}} - \mu_\text{door} R\,\hat{\mathbf{x}}_\text{forward} ,
$$ (eq-22-door)

with $C_L$ and $C_D$ from its polar at the angle of attack of the case (32° for the FAO otter
board), its weight in water and the friction of the shoe. The warp is a chain of ten steel bars
with their weight and their Morison drag, from the otter board to the vessel's towing block, fixed
at the working depth and at half the gallows spread. The door spread $D_P$ is no longer an input:
it comes from the equilibrium with the net, the bridles and the sweeps.

## Validation: door spread

```{code-cell} ipython3
:tags: [remove-cell]
HAUL = {sb: haul(R, V, CATCHES, scenario=Scenario(seabed=sb), resolution=RES) for sb in ("mud", "rock")}
EMPTY = HAUL["mud"][0]
DYN_DP = DYNAMIT["DP_m"][DYNAMIT["v_kn"].index(V)]
ENG_DP = float(R.doors.spread_m)
# The coupled equilibrium comes much closer to DynamiT than the engine's rule.
assert abs(EMPTY.door_spread_m - DYN_DP) / DYN_DP < 0.15
assert abs(EMPTY.door_spread_m - DYN_DP) < abs(ENG_DP - DYN_DP)
```

At 3 kn, with no catch and on a mud seabed, the coupled equilibrium gives a door spread of
**{glue:text}`dp_sim` m**, against **{glue:text}`dp_dyn` m** from DynamiT and **{glue:text}`dp_eng`
m** from the engine's rule of thumb ({doc}`15_portones_aparejo`): the error with respect to DynamiT
drops from {glue:text}`err_eng` % to {glue:text}`err_sim` %.

```{code-cell} ipython3
:tags: [remove-cell]
from myst_nb import glue

glue("dp_sim", f"{EMPTY.door_spread_m:.1f}", display=False)
glue("dp_dyn", f"{DYN_DP:.1f}", display=False)
glue("dp_eng", f"{ENG_DP:.1f}", display=False)
glue("err_eng", f"{(ENG_DP - DYN_DP) / DYN_DP * 100:+.0f}".replace("-", "−"), display=False)
glue("err_sim", f"{(EMPTY.door_spread_m - DYN_DP) / DYN_DP * 100:+.0f}".replace("-", "−"), display=False)
glue("pull0", f"{EMPTY.towing_pull_kgf:.0f}", display=False)
glue("demand", f"{float(np.interp(V, R.case.speeds_kn, R.performance.demand.std)):.0f}", display=False)
```

The total pull of the gear at the vessel (both warps) is {glue:text}`pull0` kgf, against
{glue:text}`demand` kgf of the engine's demand at the same speed: the simulator inherits the
netting drag gap documented in {doc}`21_simulacion` (the drag of the twines alone stays ≈ 40–50 %
below that of DynamiT). The trends that follow are relative and do not depend on that gap.

## Progressive haul

```{code-cell} ipython3
:tags: [remove-input]
fig, axes = P.plt.subplots(1, 3, figsize=(10.2, 3.5))
labels = {"mud": "Mud", "rock": "Rock"}
for slot, (sb, runs) in enumerate(HAUL.items(), start=1):
    kg = [r.scenario["catch_kg"] for r in runs]
    P.line(axes[0], kg, [r.door_spread_m for r in runs], slot, labels[sb])
    P.line(axes[1], kg, [r.towing_pull_kgf for r in runs], slot, labels[sb])
    P.line(axes[2], kg, [r.ah_m for r in runs], slot, labels[sb])
axes[0].axhline(DYN_DP, color=P.INK_2, lw=1, ls="--")
axes[0].annotate("DynamiT, no catch", (0, DYN_DP), xytext=(4, -12), textcoords="offset points",
                 color=P.INK_2, fontsize=8.5)
for ax, title in zip(axes, ("Door spread [m]", "Pull at the vessel [kgf]",
                            "Horizontal opening [m]"), strict=True):
    ax.set_title(title)
    ax.set_xlabel("Catch in the codend [kg]")
P.legend(axes[0], loc="lower left")
P.finish(fig)
```

```{code-cell} ipython3
:tags: [remove-cell]
for runs in HAUL.values():
    dp = [r.door_spread_m for r in runs]
    pull = [r.towing_pull_kgf for r in runs]
    assert all(a > b for a, b in zip(dp, dp[1:])), dp  # the otter boards close in
    assert all(a < b for a, b in zip(pull, pull[1:])), pull  # the pull rises
    assert all(r.converged for r in runs)
mud, rock = HAUL["mud"], HAUL["rock"]
assert rock[0].friction_kgf > 1.5 * mud[0].friction_kgf
last = mud[-1]
glue("ddp", f"{mud[0].door_spread_m - last.door_spread_m:.1f}", display=False)
glue("dpull", f"{last.towing_pull_kgf - mud[0].towing_pull_kgf:.0f}", display=False)
glue("clen", f"{last.catch['length_m']:.1f}", display=False)
glue("cdiam", f"{last.catch['max_diameter_m']:.2f}", display=False)
glue("cdrag", f"{last.catch_drag_kgf:.0f}", display=False)
glue("fric_mud", f"{mud[0].friction_kgf + mud[0].door_friction_kgf:.0f}", display=False)
glue("fric_rock", f"{rock[0].friction_kgf + rock[0].door_friction_kgf:.0f}", display=False)
```

With 1500 kg of catch (mud, 3 kn) the catch occupies {glue:text}`clen` m of the codend, which
inflates to {glue:text}`cdiam` m in diameter, and adds {glue:text}`cdrag` kgf of drag. The otter
boards close in by {glue:text}`ddp` m and the pull at the vessel rises by {glue:text}`dpull` kgf.
This is the behaviour measured by {cite:t}`priour2015catch` over 37 hauls: the door spread
decreases and the tension in the sweeps rises as the catch comes in. On rock the friction of
groundgear and otter boards without catch is {glue:text}`fric_rock` kgf, against
{glue:text}`fric_mud` kgf on mud.

The catch also changes the opening of the codend meshes, and with it the selectivity
{cite:p}`oneill1996kynoch,herrmann2005`; the mesh-by-mesh zoom of {doc}`24_malla_selectividad`
quantifies it.

## Seabed friction in the empirical engine

The `seabed` parameter of `DesignCase` adds to the engine's demand the friction of the groundgear
(footrope and ballast in water times the groundgear $\mu$) and of the two otter boards (weight in
water times the shoe $\mu$). It is a simple bound, with all the weight resting on the seabed; the
coupled simulator shares the reaction with the lift of the floats and the warps and gives smaller
values.

```{code-cell} ipython3
import dataclasses

for sb in (None, "mud", "rock"):
    r = run(dataclasses.replace(standard_case(), seabed=sb))
    s = r.summary()
    print(f"{sb or 'no seabed':>9}: friction {s.get('seabed_friction_kgf', 0.0):6.1f} kgf, "
          f"maximum speed {s['max_speed_kn']:.2f} kn")
```

## Assumptions and limits

- **Catch**: a fluid that fills the codend from the closed end, with no stratification or shape of
  its own; $C_p$ and the densities are reference values (“TO BE VERIFIED”). It does not model the
  effect of live fish swimming nor the catch that escapes.
- **Seabed**: flat Coulomb friction, without penetration or mobilized sediment (footprint and
  penetration arrive in delivery 11.2). The coefficients are estimates with a range.
- **Otter boards**: constant angle of attack and polar (their pitch and roll are not solved); the
  shoe rests on the seabed and its centre sits at half height.
- **Warps**: ten straight bars with weight and Morison drag (the catenary comes out of the
  equilibrium); the vessel is a fixed point.
- **Drag**: the netting gap with respect to DynamiT ({doc}`21_simulacion`) is still there; the
  trends with catch and seabed are relative to the state without catch.
- **Cost**: with coupled otter boards each equilibrium costs ≈ 2.5 times more than with fixed otter
  boards (2–5 s per step at resolution 4).

```{code-cell} ipython3
:tags: [remove-cell]
print(f"chapter executed in {time.perf_counter() - T0:.0f} s")
```
