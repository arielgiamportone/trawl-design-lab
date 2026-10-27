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

# The real sea and operating conditions

```{code-cell} ipython3
:tags: [remove-cell]
import sys, pathlib
DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English
import time

import _plots_t2 as P
from myst_nb import glue
from trawlkit.model import run
from trawlkit.sim import Scenario, explore, fouling_catalogue, simulate
from trawlkit.sim.core import DIESEL_KG_L, SFC_KG_KWH, TOWING_EFFICIENCY
from trawlkit.sim.scenario import fouling_coefficients
from trawlkit.sim.validation import standard_case

P.setup()
T0 = time.perf_counter()
R = run(standard_case())
RES = 3
BASE = Scenario(seabed="mixed")
```

## Purpose

{doc}`22_simulacion_realista` added the catch, the seabed type and the coupled otter boards. This
chapter adds other conditions that change how the gear works at sea: the **fouling** of the net
(algae, jellyfish, attached organisms), the **current** along the course and the **warp length**
paid out. It also adds two outputs to assess a fishing condition: the **energy** (towing power and
fuel) and the **footprint** on the seabed.

Everything is swept with `trawlkit.sim.explore`: a series of equilibria in which a single variable
changes, with a warm start and the same mesh. Since all the states share the nodes, the shape can
be **animated** by interpolating between them; that is what the “Animated explorer” of the
application does ({doc}`web`).

## Fouling and clogging

Each zone of the net (wings, body, codend) has a fouling level $f \in [0, 1]$. The catalogue
`data/fouling.yaml` defines typical scenarios, and the level changes each twine:

$$
d_\text{ef} = d\,(1 + g_d f), \qquad C_{N,\text{ef}} = C_N\,(1 + g_c f), \qquad
w_\text{ef} = w\,(1 + g_w f).
$$ (eq-23-fouling)

```{code-cell} ipython3
:tags: [remove-input]
import _plots_v as PV

from trawlkit.i18n import tr

g = fouling_coefficients()
glue("gd", f"{g['diameter_gain']:.1f}", display=False)
glue("gc", f"{g['cn_gain']:.1f}", display=False)
glue("gw", f"{g['weight_gain']:.1f}", display=False)
PV.md_table(
    ["Scenario", "Wings", "Body", "Codend"],
    [
        [tr(f.name), *(f"{f.zones[z]:.1f}" for z in ("wings", "body", "codend"))]
        for f in fouling_catalogue()
    ],
)
```

Gains used (“TO BE VERIFIED”): $g_d$ = {glue:text}`gd`, $g_c$ = {glue:text}`gc` and
$g_w$ = {glue:text}`gw`.

The gains were estimated from the literature on aquaculture nets. With heavy fouling, the solidity
of a netting panel can double and its drag grow two or three times {cite:p}`swift2006`. The
simulation of fouled full-scale cages shows the same order {cite:p}`bi2015`. For trawl gear there
are no published measurements: during the haul, algae or jellyfish block particular zones of the
netting, and that is why the scenarios are per zone.

```{code-cell} ipython3
:tags: [remove-cell]
FOUL = explore(R, "fouling_level", [0.0, 0.5, 1.0],
               scenario=Scenario(seabed="mixed", fouling="general"), resolution=RES)
pull = [r.towing_pull_kgf for r in FOUL]
dp = [r.door_spread_m for r in FOUL]
assert pull[0] < pull[1] < pull[2] and dp[0] > dp[2]
glue("foul_pull", f"{(pull[2] / pull[0] - 1) * 100:.0f}", display=False)
glue("foul_dp", f"{dp[0] - dp[2]:.1f}", display=False)
```

With the “general fouling” scenario at its full level, the pull at the vessel rises by
{glue:text}`foul_pull` % and the otter boards close in by {glue:text}`foul_dp` m: the netting brakes
more and the net pulls the otter boards inwards.

## Current

With a current $c$ along the course (positive when following), the water flows through the net at
$v_\text{water} = v_\text{ground} - c$. The net, the otter boards and the floats respond to
$v_\text{water}$. The swept area and the production depend, on the other hand, on
$v_\text{ground}$. A cross current breaks the symmetry about the axis of the gear and is outside
this model.

```{code-cell} ipython3
:tags: [remove-cell]
against = simulate(R, 3.0, resolution=RES, scenario=Scenario(seabed="mixed", current_kn=-0.5))
faster = simulate(R, 3.5, resolution=RES, scenario=BASE)
calm = simulate(R, 3.0, resolution=RES, scenario=BASE)
assert abs(against.towing_pull_kgf / faster.towing_pull_kgf - 1) < 0.02
assert against.operation["swept_area_km2_h"] < faster.operation["swept_area_km2_h"]
glue("cur_pull", f"{(against.towing_pull_kgf / calm.towing_pull_kgf - 1) * 100:.0f}", display=False)
glue("cur_fuel", f"{(against.operation['fuel_l_h'] / calm.operation['fuel_l_h'] - 1) * 100:.0f}",
     display=False)
```

Towing at 3 kn over the ground against a 0.5 kn current is equivalent, for the net, to towing at
3.5 kn in still water: the pull rises by {glue:text}`cur_pull` % and the fuel by
{glue:text}`cur_fuel` %, but the area swept per hour is the same as at 3 kn.

## Warp length

```{code-cell} ipython3
:tags: [remove-input]
WARP = explore(R, "warp_length_m", [120.0, 160.0, 200.0, 250.0, 300.0], scenario=BASE,
               resolution=RES)
lengths = [r.operation["warp_length_m"] for r in WARP]
fig, axes = P.plt.subplots(1, 3, figsize=(10.2, 3.4))
P.line(axes[0], lengths, [r.door_spread_m for r in WARP], 1, "")
P.line(axes[1], lengths, [r.operation["warp_angle_deg"] for r in WARP], 1, "")
P.line(axes[2], lengths, [r.operation["contact_width_m"] for r in WARP], 1, "")
for ax, title in zip(axes, ("Door spread [m]", "Warp angle [°]",
                            "Width in contact with the seabed [m]"), strict=True):
    ax.set_title(title)
    ax.set_xlabel("Warp paid out [m] (depth 40 m)")
P.finish(fig)
```

```{code-cell} ipython3
:tags: [remove-cell]
dps = [r.door_spread_m for r in WARP]
angles = [r.operation["warp_angle_deg"] for r in WARP]
assert all(a < b for a, b in zip(dps, dps[1:])) and all(a > b for a, b in zip(angles, angles[1:]))
glue("short_contact", f"{WARP[0].operation['contact_width_m']:.1f}", display=False)
glue("long_contact", f"{WARP[-1].operation['contact_width_m']:.1f}", display=False)
```

At a depth of 40 m, when the warp is lengthened from 120 to 300 m the otter boards spread further
and the warp arrives flatter. With 120 m (ratio 3:1) the groundgear partly lifts off: the width in
contact with the seabed falls to {glue:text}`short_contact` m, against {glue:text}`long_contact` m
with 300 m. This is the practical reason for the warp/depth ratio tables of {doc}`18_cables`.

## Energy

The towing power and the fuel consumption are estimated as

$$
P = \frac{T\,v_\text{water}}{\eta}, \qquad
Q = \frac{P \cdot \text{SFC}}{\rho_\text{diesel}} ,
$$ (eq-23-energy)

where $T$ is the pull at the vessel, $\eta$ the towing efficiency (propeller and transmission) and
SFC the specific fuel consumption of the engine. The power is capped at that of the vessel; if the
demand exceeds it, the result says so (`power_limited`). With the duration of the haul and the
catch, the litres per kg are obtained; with the swept area, the litres per km². These are
order-of-magnitude estimates: they do not include the hull resistance or the load of the
equipment.

```{code-cell} ipython3
:tags: [remove-cell]
glue("eta", f"{TOWING_EFFICIENCY:.1f}", display=False)
glue("sfc", f"{SFC_KG_KWH:.2f}", display=False)
glue("rho", f"{DIESEL_KG_L:.2f}", display=False)
SPEED = explore(R, "speed_kn", [2.0, 2.5, 3.0, 3.5], scenario=Scenario(seabed="mixed", catch_kg=600),
                resolution=RES)
fuel = [r.operation["fuel_l_h"] for r in SPEED]
assert all(a < b for a, b in zip(fuel, fuel[1:]))
per_km2 = [r.operation["fuel_l_per_km2"] for r in SPEED]
glue("km2_lo", f"{min(per_km2):.0f}", display=False)
glue("km2_hi", f"{max(per_km2):.0f}", display=False)
```

Values used (“TO BE VERIFIED”): $\eta$ = {glue:text}`eta`, SFC = {glue:text}`sfc` kg/kWh and
$\rho_\text{diesel}$ = {glue:text}`rho` kg/L. The global median reported by {cite:t}`parker2015`
for bottom trawl fleets serves as a reference for the order of magnitude. Between 2 and 3.5 kn, the
fuel per km² swept by the FAO A-3 net ranges from {glue:text}`km2_lo` to {glue:text}`km2_hi`
L/km²: towing faster sweeps more area per hour, but each km² costs more fuel.

## Footprint on the seabed

Following the BENTHIS methodology {cite:p}`eigaard2016`:

- the **swept width** is the door spread;
- the **width in contact** is the footrope resting on the seabed plus the shoes of the two otter
  boards;
- the **areas per hour** are computed with the speed over the ground;
- the **penetration** comes from the seabed type of the catalogue.

The mobilized sediment grows with the drag of the elements in contact
{cite:p}`oneill2011,oneill2016`. It is not quantified yet because its coefficients depend on the
sediment and on the element.

## Assumptions and limits

- **Fouling**: a per-zone model with estimated gains; it does not model the progressive clogging
  during the haul. The effect of the shape of the meshes on selectivity is in
  {doc}`24_malla_selectividad`.
- **Current**: only along the course. Cross currents and manoeuvres require the asymmetric and
  dynamic model.
- **Energy**: constant $\eta$ and SFC; no hull resistance or auxiliary consumption.
- **Footprint**: the widths in contact are geometric; neither penetration nor sediment is
  quantified.
- **Animation**: it interpolates positions between quasi-static equilibria. It is not a dynamic
  simulation in time: it shows how the equilibrium state changes, not the physical transition
  between states.

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
_exercises.section("23_mar_real")
```
