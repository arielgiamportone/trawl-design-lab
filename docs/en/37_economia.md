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

# Economics of the operation

```{code-cell} ipython3
:tags: [remove-cell]
import sys, pathlib
DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English

import matplotlib.pyplot as plt
from IPython.display import Markdown
import _plots_v as PV
from myst_nb import glue
from trawlkit.api import service
from trawlkit.economics import EconomicInputs, compare, economics


def num(x: float, nd: int = 0) -> str:
    return f"{x:,.{nd}f}"


# ILLUSTRATIVE values to show the calculation: they are not real prices of any port.
EJ = EconomicInputs(
    currency="ARS",
    fuel_price_l=1200.0,
    lube_price_l=6000.0,
    catch_kg_h=150.0,
    price_kg=1000.0,
    crew_share=0.4,
    gear_cost=3_000_000.0,
    trip_costs=150_000.0,
    annual_costs=6_000_000.0,
)
CASE = service.build_case()
R = economics(CASE, EJ)
B = R.best
```

## Purpose

A net is not chosen only because the vessel can tow it: it is chosen because the fishing trip
makes money. This chapter describes `trawlkit.economics` (Phase 16), which adds to the net
calculation the economics of the operation: how much diesel is burned, how much is caught, how
much the trip costs and how much is left, at each towing speed. With that it answers three
questions: **at what speed it pays to tow**, **which net suits** a vessel and **how long it takes
to pay back** a new net.

The app does not come with prices: the user enters them, in their own currency. Without a
figure, that item is left out of the calculation with a warning; it is not replaced by an
invented value. The numbers in this chapter use **illustrative values** (diesel at
1,200 ARS/L, squat lobster at 1,000 ARS/kg, 150 kg per hour of towing at 3 kn, 40 % for the
crew) only to show the calculation.

## Diesel

During the haul, the brake power demanded by the net is

$$
P = \frac{R_T(v)\, v}{\eta},
$$

with $R_T(v)$ the total drag from the calculation engine ({doc}`19_ventana_velocidad`) and
$\eta$ a towing efficiency (pull × speed over brake power) of 0.5 by default (TO BE VERIFIED;
it includes propeller, gearbox and losses). The power is capped at that of the vessel. On the
steam to the fishing ground a fraction of the engine power is used (0.8 by default) and during
shooting and hauling another (0.2). The fuel is $P \cdot \text{SFC} / \rho$, with a specific
fuel consumption of 0.22 kg/kWh and diesel of 0.84 kg/L, and the lubricant a proportion of the
diesel {cite}`parker2015`. All these constants can be changed.

## Catch and revenue

The catch per hour of towing entered by the user holds at a reference speed (3 kn by default).
At another speed, the net sweeps another area per hour, $A_H \cdot v$, and the catch is scaled
in proportion:

$$
C(v) = C_\text{ref}\;\frac{A_H(v)\, v}{A_H(v_\text{ref})\, v_\text{ref}}.
$$

It is a simple hypothesis: it does not take into account the escape of fish at low speed or the
herding by the otter boards and the bridles, which depend on the species. The revenue is the
catch times the first-sale (ex-vessel) price, or times the weighted average of several species.

## Costs of the trip

| Item | How it is calculated |
|---|---|
| Fuel and lubricant | Diesel for towing, steaming and manoeuvres, times its price; lubricant in proportion. |
| Crew | “Share system”: a percentage of the revenue after deducting diesel, lubricant and trip expenses (or of the gross revenue); or a daily wage per crew member. |
| Net and gear | The cost of the rigged gear (entered or from the bill of materials, {doc}`34_componentes`) divided by its service life in towing hours, plus an annual repair as a fraction of the cost. |
| Trip expenses | Ice, provisions, bait and port. |
| Annual fixed costs | Permits, insurance and others, divided by the trips of the year. |

The **margin** is the revenue minus the cost; the **cost per kg**, the cost over the catch; and
the **break-even price**, the price of the catch that leaves zero margin. Since the crew share
depends on the revenue, the margin is linear in the price and the break-even follows directly:
with the share after the shared expenses $G$ and the costs that do not depend on the price $F$,

$$
p^* = \frac{F - c\,G}{(1 - c)\,C},
$$

with $c$ the crew share and $C$ the catch of the trip.

## At what speed it pays to tow

```{code-cell} ipython3
:tags: [remove-input]
fig, ax = plt.subplots(figsize=(7.2, 4.0))
v = [t.speed_kn for t in R.trips]
ax.plot(v, [t.revenue / 1e3 for t in R.trips], color="#1baf7a", label="Revenue")
ax.plot(v, [t.total_cost / 1e3 for t in R.trips], color="#eb6834", label="Cost")
ax.plot(v, [t.margin / 1e3 for t in R.trips], color="#2a78d6", lw=2.5, label="Margin")
ok = [t.speed_kn for t in R.trips if t.feasible]
ax.axvspan(min(ok), max(ok), color="#1baf7a", alpha=0.12, label="the vessel tows with reserve")
ax.axvline(R.best_margin_kn, color="#52514e", lw=1, ls="--")
ax.set_xlabel("Towing speed [kn]")
ax.set_ylabel("Per trip [thousand ARS]")
ax.grid(alpha=0.3)
ax.legend(fontsize=8, frameon=False)
fig.tight_layout()
plt.show()
glue("best_v", Markdown(num(R.best_margin_kn, 2)), display=False)
glue("best_margin", Markdown(num(B.margin)), display=False)
glue("best_ckg", Markdown(num(B.cost_per_kg, 0)), display=False)
glue("best_fuel", Markdown(num(B.fuel_l)), display=False)
glue("best_be", Markdown(num(B.breakeven_price, 0)), display=False)
glue("year_margin", Markdown(num(R.year["margin"] / 1e6, 1)), display=False)
```

With these values, revenue and cost grow with speed and so does the margin: more speed is more
swept area and more catch. But the A-3 on its 150 hp vessel only has pull with reserve up to a
little over 2 kn ({doc}`30_caso_beagle`). The best **feasible** speed is {glue:md}`best_v` kn:
{glue:md}`best_fuel` L of diesel per trip, a cost of {glue:md}`best_ckg` ARS per kg, a margin of
{glue:md}`best_margin` ARS per trip ({glue:md}`year_margin` million per year) and a break-even
price of {glue:md}`best_be` ARS/kg. The economics confirm what the optimizer showed
({doc}`20_optimizacion`): this vessel would make better use of a smaller net that it can tow
faster.

## Which net suits

```{code-cell} ipython3
:tags: [remove-input]
rows = compare(
    [
        ("FAO A-3", CASE, None),
        ("Workbook 2 panels", service.build_case("fao_wb_bt2p_60hp", vessel="fao_a3_150hp"), 2_000_000.0),
        ("BOBP/WP/20, single boat", service.build_case("bobp_wp20_ho", vessel="fao_a3_150hp"), 2_500_000.0),
    ],
    EJ,
)
PV.md_table(
    ["Net (150 hp vessel)", "v [kn]", "Diesel per year [L]", "Margin per year [ARS]", "Savings per year", "Payback"],
    [
        [
            r.label,
            num(r.trip.speed_kn, 2) if r.trip else "—",
            num(r.annual_fuel_l) if r.annual_fuel_l is not None else "—",
            num(r.annual_margin) if r.annual_margin is not None else "—",
            num(r.savings_year) if r.savings_year is not None else "—",
            (f"{num(r.payback_years * 12, 1)} months" if r.payback_years is not None else "—"),
        ]
        for r in rows
    ],
)
```

The comparison uses the same vessel, the same otter board and the same operating data; each net
works at its speed of highest margin. The catch per hour entered holds for the first net at the
reference speed; the others fish in proportion to their swept area per hour (a smaller net sweeps
less and catches less). The **savings** are the difference in margin per year relative to the
first net and the **payback**, the cost of the new net over those savings. It is the sum an
owner does before changing the net: with these illustrative numbers, a net the vessel can tow
faster pays for itself in a few weeks or months. With the real prices of the port the result may
change, and that is why the app does not come with prices of its own.

## Where it is used

- **Web**: the “Economics” tab of Expert mode (operating data, best speed, revenue, cost and
  margin curve, table by speed, cost breakdown and comparison with another net from the
  catalogue) and, in Guided mode, “What does a trip earn?” in the result ({doc}`web`).
- **Batches**: with “Add the trip economics”, each vessel of the fleet adds diesel, catch, cost
  per kg and margin per trip and per year ({doc}`35_lotes_proyeccion`).
- **Offline**: the economics run in the engine on the phone.
- **CLI**: `trawlkit economics fao_a3_standard --fuel-price 1200 --catch-kg-h 150 --price-kg 1000`
  or `--inputs datos.yaml`.
- **API**: `POST /economics` and `/economics/compare` ({doc}`api`).

## Assumptions and limits

- The catch scales with the swept area; escape and herding are not modelled, nor is the
  variation of abundance on the fishing ground.
- Consumption uses a constant towing efficiency and specific fuel consumption; an old engine or a
  poorly matched propeller consumes more.
- The “feasible” speed is the one that leaves pull with reserve and a warp that holds; the other
  constraints of the optimizer (net opening, otter board) are warned about but do not rule it
  out.
- Costs without a figure are left out of the total: the result is incomplete, with a warning.

## Exercises

From the teaching-mode bank, with the book's data. In the app, the “UTN Classroom” mode generates
them with other data and grades them ({doc}`38_docentes`).

```{code-cell} ipython3
:tags: [remove-input]
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path.cwd().parent))
import _exercises
_exercises.section("37_economia")
```
