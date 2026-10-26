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

# Uncertainty, calibration and sensor data

```{code-cell} ipython3
:tags: [remove-cell]
import sys, pathlib
DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English
import time

import numpy as np
import _plots_t2 as P
import _plots_v as PV
from myst_nb import glue
from trawlkit.model import run
from trawlkit.sensors import example_log, parse_log, to_observations, windows
from trawlkit.sim import Scenario
from trawlkit.sim.calibration import PARAMETERS, calibrate, dynamit_observations
from trawlkit.sim.uncertainty import default_inputs, uncertainty
from trawlkit.sim.validation import standard_case

P.setup()
T0 = time.perf_counter()
R = run(standard_case())
RES = 3


def num(x: float, nd: int = 1) -> str:
    return f"{x:.{nd}f}"
```

## Purpose

Chapters {doc}`21_simulacion` to {doc}`24_malla_selectividad` give one value per result: a door
spread, a pull, an L50. But several inputs of the simulator are not known precisely, and with them
each result has a **band** of possible values. This chapter:

- propagates that uncertainty with Monte Carlo and tells **which input weighs most** in each
  result;
- **calibrates** the simulator against measurements: the DynamiT simulation of the FAO A-3 net or a
  sensor log from the haul;
- reads **sensor logs** in CSV from any equipment and summarizes them in steady segments.

No commercial net simulator reports uncertainty bands or is calibrated against the vessel's own
data ({doc}`22_simulacion_realista`). They are the step that takes the simulator from the
theoretical shape to the net that works at sea.

## Sources of uncertainty

```{code-cell} ipython3
:tags: [remove-input]
SC = Scenario(seabed="mixed", catch_kg=500)
INPUTS = default_inputs(SC)
PV.md_table(
    ["Input", "Nominal", "Range", "Source"],
    [
        [i.label, num(i.nominal, 3), f"{num(i.low, 3)} – {num(i.high, 3)} {i.unit}".strip(), i.source]
        for i in INPUTS
    ],
)
```

For a haul with 500 kg of catch on a mixed seabed, the uncertain inputs and their ranges are those
in the table. The twine coefficients come from the literature {cite:p}`takagi2004,lee2005`. The
friction coefficients use the range of the seabed type in the catalogue
({doc}`22_simulacion_realista`). The otter board polar is varied by ±10 % and the catch according
to {cite:t}`oneill1997codend`. The ranges marked “TO BE VERIFIED” are estimates.

## Monte Carlo with Latin hypercube

Each input is taken as uniform over its range. With $n$ samples, the **Latin hypercube**
{cite:p}`mckay1979` divides each range into $n$ strata and puts one sample in each stratum of each
input, with the strata randomly permuted between inputs. This way few samples cover the space
better than random sampling. Each sample is simulated starting from the nominal shape, which makes
each one cheaper.

From the outputs, the percentiles P10, P50 and P90 are reported: 80 % of the samples fall between
P10 and P90. The weight of each input is measured with the **Spearman rank correlation** between
the input and the output, $\rho_s \in [-1, 1]$ {cite:p}`saltelli2008`. With few samples it is an
indicative measure, not a variance decomposition.

```{code-cell} ipython3
:tags: [remove-cell]
U = uncertainty(R, 3.0, scenario=SC, n=16, resolution=RES, species=["hake_hubbsi"])
UD = U.to_dict()
OUT = {o["key"]: o for o in UD["outputs"]}
for o in UD["outputs"]:
    assert o["p10"] <= o["p50"] <= o["p90"]
assert U.converged.all()


def top(key: str) -> str:
    s = OUT[key]["sensitivity"]
    return max(s, key=lambda k: abs(s[k]))


LABELS = {i.name: i.label for i in U.inputs}
S_DP = OUT["door_spread_m"]["sensitivity"]
S_PULL = OUT["towing_pull_kgf"]["sensitivity"]
# Physical signs: the otter board lift spreads the otter boards and the netting drag closes them;
# the twine friction (C_T) raises the pull.
assert S_DP["door_cl_factor"] > 0 and S_DP["cn"] + S_DP["ct"] < 0
assert S_PULL["ct"] > 0
glue("rho_cl", num(S_DP["door_cl_factor"], 2), display=False)
glue("rho_net", num(S_DP["cn"] + S_DP["ct"], 2), display=False)
dp = OUT["door_spread_m"]
glue("dp_p10", num(dp["p10"]), display=False)
glue("dp_p90", num(dp["p90"]), display=False)
glue("dp_top", LABELS[top("door_spread_m")], display=False)
glue("pull_top", LABELS[top("towing_pull_kgf")], display=False)
glue("n_unc", str(UD["n"]), display=False)
```

```{code-cell} ipython3
:tags: [remove-input]
digits = {"kgf": 0, "L/h": 1, "cm": 1}
PV.md_table(
    ["Result", "Nominal", "P10", "P50", "P90"],
    [
        [
            f"{o['label']} [{o['unit']}]",
            "—" if o["nominal"] is None else num(o["nominal"], digits.get(o["unit"], 2)),
            *(num(o[k], digits.get(o["unit"], 2)) for k in ("p10", "p50", "p90")),
        ]
        for o in UD["outputs"]
    ],
)
```

```{code-cell} ipython3
:tags: [remove-input]
fig, axes = P.plt.subplots(1, 2, figsize=(10.2, 3.8), sharey=True)
names = [i.name for i in U.inputs]
ypos = np.arange(len(names))
for ax, key in zip(axes, ("door_spread_m", "towing_pull_kgf"), strict=True):
    rho = [OUT[key]["sensitivity"][n] for n in names]
    ax.barh(ypos, rho, color=[P.color(0) if r >= 0 else P.color(1) for r in rho])
    ax.axvline(0, color="0.5", lw=0.8)
    ax.set_xlim(-1, 1)
    ax.set_title(f"Spearman ρ with {OUT[key]['label'].lower()}")
axes[0].set_yticks(ypos, [LABELS[n] for n in names])
axes[0].invert_yaxis()
P.finish(fig)
```

With {glue:text}`n_unc` samples at 3 kn, the door spread lies between {glue:text}`dp_p10` and
{glue:text}`dp_p90` m (P10–P90). The input with the greatest weight in this run is
“{glue:text}`dp_top`”. The otter board lift spreads it ($\rho_s$ = {glue:text}`rho_cl`), and the
netting drag closes it (sum of C_N and C_T: {glue:text}`rho_net`). The net pulls the otter boards
inwards. The pull at the vessel depends most on “{glue:text}`pull_top`”. To reduce the uncertainty
of a result it pays to measure first the inputs that weigh most in it. For the spread of the gear,
those inputs are the real polar of the otter board at sea and the drag of the netting.

## Calibration

Calibrating means adjusting some uncertain parameters $\boldsymbol\theta$ so that the simulation
reproduces measurements $y_k$ (door spread, openings, pull, warp tension at a given speed and with a
given catch). The sum of the squared relative errors is minimized:

$$
\min_{\boldsymbol\theta \in [\boldsymbol\theta_{\min}, \boldsymbol\theta_{\max}]}
\sum_k \left[ w_k \left( \frac{s_k(\boldsymbol\theta)}{y_k} - 1 \right) \right]^2 .
$$ (eq-25-ls)

The relative errors make it possible to mix quantities with different units. The method is
Levenberg–Marquardt {cite:p}`levenberg1944,marquardt1963`. The Jacobian is computed by finite
differences and the parameters are projected onto their physical ranges. Each evaluation simulates
the observed states starting from the last shape of each one. The standard deviation of each
parameter comes from $(J^\mathsf{T} J)^{-1}$ and is only indicative.

```{code-cell} ipython3
:tags: [remove-input]
PV.md_table(
    ["Parameter", "Range"],
    [[lab, f"{num(lo, 2)} – {num(hi, 2)}"] for lab, lo, hi in PARAMETERS.values()],
)
```

### Against DynamiT

```{code-cell} ipython3
:tags: [remove-cell]
CD = calibrate(
    R,
    dynamit_observations(),
    ["cn", "door_cl_factor"],
    scenario=Scenario(seabed="mixed"),
    resolution=RES,
    max_evals=24,
)
assert CD.rmse_after < CD.rmse_before
glue("dyn_before", num(CD.rmse_before), display=False)
glue("dyn_after", num(CD.rmse_after), display=False)
glue("dyn_cn", num(CD.fitted[0], 2), display=False)
glue("dyn_cl", num(CD.fitted[1], 2), display=False)
glue("cn_max", num(PARAMETERS["cn"][2], 1), display=False)
```

```{code-cell} ipython3
:tags: [remove-input]
PV.md_table(
    ["Quantity", "v [kn]", "DynamiT", "Before", "After"],
    [
        [
            o.quantity.replace("_", " "),
            num(o.speed_kn, 0),
            num(o.value, 1),
            f"{num(CD.before[k], 1)} ({num(100 * (CD.before[k] / o.value - 1), 0)} %)",
            f"{num(CD.after[k], 1)} ({num(100 * (CD.after[k] / o.value - 1), 0)} %)",
        ]
        for k, o in enumerate(CD.observations)
    ],
)
```

The twine C_N and the otter board lift were calibrated against the DynamiT door spread, openings
and drag at 2, 3 and 4 kn. The relative root mean square error drops from {glue:text}`dyn_before` %
to {glue:text}`dyn_after` %. C_N ends at {glue:text}`dyn_cn`, the limit of its range
({glue:text}`cn_max`), and the otter board factor at {glue:text}`dyn_cl`. That a parameter ends up
at its limit is the useful signal of the exercise: with physical coefficients the model does not
reach the DynamiT drag. The difference is structural (knots, headrope and footrope, flow inside the
net), as seen in {doc}`32_validacion_dynamit`. Calibrating does not correct it: it reveals it.

### Against a sensor log

```{code-cell} ipython3
:tags: [remove-cell]
LOG = parse_log(example_log())
WS = windows(LOG, by="time", width=20)
OBS = to_observations(WS)
CS = calibrate(R, OBS, ["door_cl_factor"], scenario=Scenario(seabed="mixed"), resolution=RES, max_evals=12)
assert abs(CS.fitted[0] - 0.9) < 0.03 and CS.rmse_after < CS.rmse_before
glue("log_rows", str(LOG.rows), display=False)
glue("log_fit", num(CS.fitted[0], 3), display=False)
glue("log_before", num(CS.rmse_before), display=False)
glue("log_after", num(CS.rmse_after), display=False)
```

The package ships a **synthetic** log (`data/examples/sensor_log.csv`) generated with the
simulator. The otter board lift is 90 % of the catalogue value, and measurement noise is added. It
has {glue:text}`log_rows` rows every 10 s in three speed segments, with the catch growing.
Calibrating the lift factor against those measurements gives {glue:text}`log_fit` (the hidden
value is 0.90). The error drops from {glue:text}`log_before` % to {glue:text}`log_after` %. With a
real log, that factor measures how well the otter board performs in the water compared with its
catalogue polar.

## Sensor logs

```{code-cell} ipython3
:tags: [remove-input]
PV.md_table(
    ["Speed [kn]", "Catch [kg]", "Rows", "Door spread [m]", "Headrope height [m]", "Warp tension [kgf]"],
    [
        [
            num(w.speed_kn, 2),
            num(w.catch_kg, 0),
            str(w.n),
            num(w.values["door_spread_m"], 1),
            num(w.values["headrope_height_m"], 2),
            num(w.values["warp_tension_kgf"], 0),
        ]
        for w in WS
    ],
)
```

`trawlkit.sensors` reads the CSV exported by the gear sensors: door spread, headrope height,
tension meters and GPS. No fixed format is required:

- the separator can be a comma, a semicolon or a tab, and with a semicolon the decimal comma is
  accepted;
- the columns are recognized by their name, in Spanish or in English (`Velocidad`, `SOG`,
  `Separacion portones`, `door_spread`, `Altura relinga`, `headline_height`, `Tension babor`…);
- the unit goes in brackets or as a suffix (`(m/s)`, `[t]`, `_kN`, `(fm)`) and is converted;
- the port and starboard tensions are averaged;
- lines starting with `#` are comments.

The rows are grouped into **steady segments**, by time or by speed, and each segment is summarized
with the median. The table shows the segments of the example log. Each segment gives one
observation per quantity, which is the input of the calibration. In the application, the
“Uncertainty and calibration” view does the whole process in the browser ({doc}`web`).

## Assumptions and limits

- **Uncertainty**:
  - uniform and independent inputs, in the ranges of the table;
  - the uncertainty of the net geometry (cuts, rigging) and that of the model (shape of the
    elements, knots) are not included;
  - with 10–20 samples the extreme percentiles are approximate.
- **Sensitivity**: rank correlation captures monotonic effects. It does not separate interactions
  between inputs (that would require Sobol indices and many more samples
  {cite:p}`saltelli2008`).
- **Calibration**:
  - local minima are possible;
  - correlated parameters (for example, C_N and the otter board drag with respect to the pull)
    can compensate each other. It is advisable to calibrate few parameters and with quantities
    that separate them: the door spread for the lift and the tension for the drag.
- **Logs**:
  - a steady regime is assumed within each segment, and the same net and rigging throughout the
    haul;
  - turns and changes of course must be filtered out beforehand.

```{code-cell} ipython3
:tags: [remove-cell]
print(f"chapter executed in {time.perf_counter() - T0:.0f} s")
```
