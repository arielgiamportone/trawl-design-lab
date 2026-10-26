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

# Buoyancy and ballast

## Purpose

The vertical opening of a bottom trawl is held up by **buoyancy** on the headrope and the contact
with the seabed is kept by **ballast** on the footrope. Too little buoyancy closes the mouth; too
much lifts the footrope and the net “flies” without catching the bottom species. Too little ballast
has the same effect, and too much makes the footrope plough the seabed, increasing the drag and
damaging the substrate.

This chapter reproduces the *Flotación y Lastre* sheet [Buoyancy and Ballast] and the rope weights
of *Cables Y Cabulleria* [Wires and Ropes]. It uses the available pull ({doc}`10_potencia`), the
drag of the net ({doc}`14_resistencia`) and the bridle geometry ({doc}`15_portones_aparejo`); its
total buoyancy feeds the Baranov–Fridman vertical opening ({doc}`16_aberturas`) and the drag of the
floats enters the total drag of the system ({doc}`18_cables`, {doc}`19_ventana_velocidad`). In
`trawlkit` it lives in `trawlkit.rigging.floats`, `trawlkit.rigging.ballast` and
`trawlkit.rigging.ropes`.

## Theory

### Empirical buoyancy methods

{cite:t}`koyama1974` fits the buoyancy of Japanese bottom trawls to the headrope length $L$:

$$
F_K = 1.11\,L - 6.81 \quad [\text{kgf}]
$$ (eq-17-koyama)

and {cite:t}`prado1990` scales it with the power of the vessel, which is an indicator of the size of
net the vessel can tow:

$$
F_P = K\cdot NHP, \qquad K = 0.2 \ \text{kgf/HP for } 50\text{–}600\ \text{NHP}
$$ (eq-17-prado)

### Fridman's balance of vertical forces

{cite:t}`fridman1986` sizes the buoyancy from the vertical equilibrium of the headrope. Two
tensions pulling downwards and backwards act on it:

- $F_1$, the tension that arrives through the bridles: the book takes 80 % of the pull shared among
  the four bridles, $F_1 = 0.8\,F_T/4$. The upper bridle rises towards the wing end with the angle
  $\alpha$ between bridles (4.8°), and its vertical component is $F_1' = F_1\sin\alpha$.
- $F_2$, the part of the net drag carried by the headrope, a quarter of $R_N$. The body netting
  slopes down from the headrope towards the codend with the angle $\beta$, which follows from the
  vertical opening and the body length $L_c$: $\beta = \arctan\!\big((AV/2)/L_c\big)$. Its vertical
  component is $F_2' = F_2\sin\beta$.

The buoyancy must balance both components and the in-water weight of the headrope itself, $W_L$:

$$
F = F_1\sin\alpha + F_2\sin\beta + W_L, \qquad
F_1 = \frac{0.8\,F_T}{4}, \quad F_2 = \frac{R_N}{4}
$$ (eq-17-fridman)

Since $F_T$ falls with speed and $R_N$ grows with $v^2$, $F_1'$ decreases and $F_2'$ increases: at
low speed the bridle pull dominates, at high speed the drag of the netting. The book averages $F$
between 1 and 3 kn for the standard and modified nets, per vessel, and the total buoyancy used by
Fridman's vertical opening is the average of those two values (150 and 180 HP) with the two of
Prado:

$$
F_{fz} = \tfrac14\left(\bar F_{150} + \bar F_{180} + F_{P,150} + F_{P,180}\right)
$$ (eq-17-ffz)

The in-water weights of the combination-rope headrope and footrope (polypropylene with a steel
core) are taken as 0.087 times their weight in air.

### Floats: number, distribution and drag

The number of floats is the design buoyancy divided by the unit buoyancy from the catalogue,
rounded. The book chooses 12 floats of 200 mm (3.2 kgf each, 38.4 kgf in total, slightly more than
the 36 kgf required). They are distributed in two ways: **even**, at intervals $L/n$, or
**selective**, with 70 % on the wings (to lift the wing ends, which is where the headrope tends to
sag) and the rest in the centre of the mouth (bosom).

Each float is a sphere that adds drag. With the drag coefficient of a smooth sphere in the
subcritical regime, $C_D \approx 0.47$ {cite:p}`hoerner1965`:

$$
R_B = n\cdot\tfrac12\,C_D\,\frac{\rho}{g}\,\frac{\pi D^2}{4}\,v^2, \qquad
Re = \frac{v\,D}{\nu}
$$ (eq-17-rb)

with $\nu$ the average kinematic viscosity of seawater at 0 and 20 °C
(1.44·10⁻⁶ m²/s). The Reynolds number checks that the float is below the drag crisis of the
smooth sphere ($Re \approx 3$–$4\cdot10^5$), where $C_D$ drops sharply to
≈ 0.1–0.2. The book uses
0.47 up to 2.5 kn and 0.5 from 3 kn.

### Ballast

The ballast is computed with the same three schools. Koyama and Prado:

$$
W_K = 1.81\,L - 4.54, \qquad W_P = 0.28\cdot NHP \quad [\text{kg}]
$$ (eq-17-lastre-empirico)

and Fridman, from the vertical equilibrium of the footrope: the ballast must balance the same
vertical components that pull the footrope upwards, less the in-water weight of the footrope
itself $W_B$:

$$
W_F = F_1\sin\alpha + F_2\sin\beta - W_B
$$ (eq-17-lastre-fridman)

The **minimum** is Fridman's ballast for the modified net at 1 kn (rounded down) and the
**maximum** that of the standard net at 3 kn (rounded up). It is distributed with an adjusting
chain in the centre (20 % of the minimum, 30 % of the maximum), the bosom (25 % and 20 %) and the
rest on the wings.

## Coefficients

| Symbol | Value | Unit | Source | Cell |
|---|---|---|---|---|
| Koyama buoyancy | 1.11; −6.81 | kgf/m; kgf | {cite:t}`koyama1974` | `Flot!F6` |
| $K$ Prado buoyancy | 0.2 | kgf/HP | {cite:t}`prado1990` | `Flot!I14` |
| fraction of $F_T$ in the bridles | 0.8 / 4 | — | {cite:t}`fridman1986` | `Flot!F42` |
| fraction of $R_N$ on the headrope | 1/4 | — | {cite:t}`fridman1986` | `Flot!G42` |
| $\alpha$ between bridles | 4.8 | ° | — | `Flot!F22` |
| weight in water / weight in air (combination rope) | 0.087 | — | — | `Flot!F37`, `G191` |
| chosen float | 12 × 200 mm (3.2 kgf) | — | catalogue | `Flot!F84`, `F92` |
| floats on the wings (selective) | 70 % | — | — | `Flot!F103` |
| sphere $C_D$ | 0.47 (≤ 2.5 kn); 0.5 (≥ 3 kn) | — | {cite:t}`hoerner1965` | `Flot!H129`, `I142` |
| seawater $\nu$ (0 / 20 °C) | 1.83·10⁻⁶ / 1.05·10⁻⁶ | m²/s | — | `Flot!H130:H131` |
| Koyama ballast | 1.81; −4.54 | kg/m; kg | {cite:t}`koyama1974` | `Flot!G159` |
| $K$ Prado ballast | 0.28 | kg/HP | {cite:t}`prado1990` | `Flot!G168` |
| distribution of the minimum ballast | 20 / 25 / 55 % | — | — | `Flot!F236:F238` |
| distribution of the maximum ballast | 30 / 20 / 50 % | — | — | `Flot!F243:F245` |

## Excel ↔ `trawlkit` equivalence

| Cell(s) | Calculation | Function |
|---|---|---|
| `Flot!F6` | Koyama buoyancy | `rigging.flotation_koyama_kgf` |
| `Flot!F17:G17` | Prado buoyancy | `rigging.flotation_prado_kgf` |
| `Flot!F23` | angle $\beta$ | `rigging.beta_deg` |
| `Flot!F36:F37`, `G188:G191` | headrope and footrope weights | `rigging.rope_weight_air_kg`, `rigging.rope_weight_in_water_kg` |
| `Flot!F42:M63` | Fridman buoyancy | `rigging.flotation_fridman` |
| `Flot!N43`, `N55` | 1–3 kn average | `rigging.flotation_fridman_average_kgf` |
| `Mec!O261` | $F_{fz}$ | `rigging.fridman_flotation_total_kgf` |
| `Flot!F72:F82`, `F92` | number of floats and diameter | `rigging.float_count`, `rigging.float_diameter_for_count_mm` |
| `Flot!F94:K112` | float distribution | `rigging.distribute_floats` |
| `Flot!H138:H146` | Reynolds | `rigging.float_reynolds` (erratum `float_reynolds`) |
| `Flot!I138:J146` | $C_D$ and $R_B$ | `rigging.float_cd`, `rigging.float_drag_kgf` |
| `Flot!G159`, `I173`, `I180` | Koyama and Prado ballast | `rigging.ballast_koyama_kg`, `rigging.ballast_prado_kg` |
| `Flot!L197:M218` | Fridman ballast | `rigging.ballast_fridman_kg` |
| `Flot!F225:F226` | minimum and maximum | `rigging.ballast_limits` |
| `Flot!H224:I245` | ballast distribution | `rigging.adjust_chain_weight_kg`, `rigging.distribute_ballast_min`, `rigging.distribute_ballast_max` |
| whole sheet | `floats` and `ballast` stages | `model.run` → `result.floats`, `result.ballast` |

## Assumptions and limits

- **Fridman's fractions.** The 80 % of the pull in the bridles and the quarter of $R_N$ on the
  headrope are simplified splits; in reality they depend on the shape of the mouth. The angles
  $\alpha$ and $\beta$ are small (4.8° and 3.2°), so the buoyancy is very sensitive to them:
  $\sin 4.8° = 0.084$, and one more degree adds ≈ 20 % to $F_1'$.
- **Buoyancy at depth.** Rigid plastic floats keep their volume; foam floats lose buoyancy with
  pressure. At 40 m the effect is small, but deeper the nominal buoyancy at the working depth must
  be used.
- **Ballast equal to buoyancy.** Fridman computes buoyancy and ballast with the same components
  $F_1'$ and $F_2'$; the only difference is the weight of the rope, which is added or subtracted.
- **Erratum `float_reynolds`** (`Flot!H138`): the sheet computes $Re = \pi D^2 v/\nu$, that is, it
  uses the area $\pi D^2$ (in m²) where the diameter belongs. With $D$ = 0.2 m the Excel Reynolds
  number is $\pi \cdot 0.2 = 0.63$ times the correct one. It does not change $C_D$, which the sheet
  enters by hand, but it hides something relevant: with the correct Reynolds number the 200 mm
  floats reach $2.9\cdot10^5$ at 4 kn and $3.6\cdot10^5$ at 5 kn, that is, the edge of the drag
  crisis; there $C_D$ = 0.47–0.5 is conservative (it overestimates $R_B$). With the Excel value the
  floats look comfortably subcritical.
- **Erratum `flotation_rounding_inconsistent`** (`Flot!M43:M50`): the `ROUNDDOWN` is applied to the
  whole table except the modified-net column of the 150 HP block, which enters the average
  unrounded.
- **Erratum `float_lookup_unsorted`** (`Flot!F92`): the float diameter is looked up with `LOOKUP`
  over the vector of quantities, which is not sorted; it gives 200 mm by chance. In corrected mode
  the float whose required number is closest to the chosen one is selected. See {doc}`erratas`.

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

FLOT = "flotacion_y_lastre"
r = P.fao_result(150, "excel")
f, b = r.floats, r.ballast


def close(actual, key, sheet=FLOT):
    """Compare with the Excel value (scalar or series) at rtol = 1e-6."""
    got, exp = np.atleast_1d(actual), np.atleast_1d(golden(sheet, key))
    return all(math.isclose(a, b, rel_tol=1e-6) for a, b in zip(got, exp))


assert close(f.koyama_kgf, "flotation_koyama_kgf")
assert close(f.beta_deg, "beta_deg")
assert close(f.fridman.std.total_kgf, "flotation_total_std_150_kgf")
# modified net, 150 HP, without ROUNDDOWN (erratum flotation_rounding_inconsistent)
assert close(f.fridman.mod.total_kgf, "flotation_total_mod_150_kgf")
assert close(f.fridman_average_kgf, "flotation_fridman_avg_150_kgf")
assert close(f.flotation_total_kgf, "flotation_total_kgf", "mecanica_de_la_red")
assert close(f.reynolds, "float_reynolds")  # Re = π·D²·v/ν (erratum)
assert close(f.drag_kgf, "float_drag_kgf")
assert close(b.fridman.std, "ballast_std_150_kg")
assert close(b.limits.min_kg, "ballast_min_150_kg")
assert close(b.limits.max_kg, "ballast_max_150_kg")

f180 = f.class_fridman_average_kgf["fao_a3_180hp"]
print(f"Buoyancy: Koyama {f.koyama_kgf:.1f}, Prado {f.prado_kgf:.0f}, "
      f"Fridman 150 HP {f.fridman_average_kgf:.1f}, Fridman 180 HP {f180:.1f}")
print(f"Ffz = {f.flotation_total_kgf:.2f} kgf")
dist = f.distribution
print(f"Floats: {f.count} × {f.diameter_mm:g} mm = {f.count * 3.2:.1f} kgf; "
      f"even, every {dist.spacing_even_m:.2f} m")
print(f"Selective: {dist.on_wings} on the wings, {dist.on_bosom} in the bosom")
print(f"Ballast: Koyama {b.koyama_kg:.1f} kg, Prado {b.prado_kg:.0f} kg, "
      f"Fridman {b.limits.min_kg:g}–{b.limits.max_kg:g} kg")
for tag, dd in (("minimum", b.distribution_min), ("maximum", b.distribution_max)):
    print(f"Distribution of the {tag}: adjusting chain {dd.adjust_kg:g} kg, bosom {dd.bosom_kg:g} kg, "
          f"wings {dd.wings_kg:g} kg ({dd.wings_kg_m:.2f} kg/m)")
```

The Reynolds erratum in both modes:

```{code-cell} ipython3
v = r.case.speeds_ms
re_x = rigging.float_reynolds(0.2, v, compat=Compat.EXCEL)
re_c = rigging.float_reynolds(0.2, v, compat=Compat.CORRECTED)
assert close(re_x, "float_reynolds")
print(f"Re at 1 kn: Excel {re_x[0]:,.0f}, corrected {re_c[0]:,.0f}")
print(f"Re at 5 kn: Excel {re_x[-1]:,.0f}, corrected {re_c[-1]:,.0f}")
print(f"ratio Excel/corrected = π·D = {re_x[0] / re_c[0]:.4f}")
```

{numref}`fig-17-flotacion` summarizes the methods. Fridman's buoyancy grows with speed because the
drag component of the netting dominates; the design buoyancy (1–3 kn average) lies between Prado
and the actual buoyancy of the 12 floats. Fridman's ballast follows the same shape shifted by the
weight of the ropes, and Koyama lies above Fridman's range for this light net.

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Top, buoyancy required by the headrope according to Fridman (150 HP, standard and modified
      nets) compared with the Koyama and Prado methods, the total buoyancy $F_{fz}$ and the
      installed buoyancy (12 floats of 200 mm). Bottom, Fridman's ballast and the adopted
      minimum–maximum range (band), with Koyama and Prado as reference.
    name: fig-17-flotacion
---
P.setup()
kn = r.case.speeds
fig, (a1, a2) = P.plt.subplots(2, 1, figsize=(7, 8.4))

P.line(a1, kn, f.fridman.std.total_kgf, 1, "Fridman, standard")
P.line(a1, kn, f.fridman.mod.total_kgf, 2, "Fridman, modified")
consts = ((f.koyama_kgf, 3, "Koyama"), (f.prado_kgf, 4, "Prado (150 HP)"),
          (f.flotation_total_kgf, 7, "$F_{fz}$ (total, Mec!O261)"))
for val, slot, lab in consts:
    a1.plot([1, 5], [val, val], color=P.color(slot), lw=2, label=lab)
inst = f.count * 3.2
a1.plot([1, 5], [inst, inst], color=P.NEUTRAL, lw=1.4, ls=(0, (4, 3)), label="Installed: 12 × 3.2 kgf")
a1.axvline(3, color=P.AXIS, lw=1, zorder=0)
a1.annotate("← design average (1–3 kn)", (3.05, 12), color=P.INK_2, fontsize=9)
a1.set_title("Headrope buoyancy")
a1.set_ylabel("Buoyancy [kgf]")
a1.set_ylim(0, 76)
P.speed_axis(a1)
P.legend(a1, loc="upper left")

a2.fill_between([1, 5], b.limits.min_kg, b.limits.max_kg, color=P.NEUTRAL_WASH, lw=0,
                label=f"Adopted range {b.limits.min_kg:g}–{b.limits.max_kg:g} kg")
P.line(a2, kn, b.fridman.std, 1, "Fridman, standard")
P.line(a2, kn, b.fridman.mod, 2, "Fridman, modified")
for val, slot, lab in ((b.koyama_kg, 3, "Koyama"), (b.prado_kg, 4, "Prado (150 HP)")):
    a2.plot([1, 5], [val, val], color=P.color(slot), lw=2, label=lab)
a2.set_title("Footrope ballast")
a2.set_ylabel("Ballast [kg]")
a2.set_ylim(0, 76)
P.speed_axis(a2)
P.legend(a2, loc="upper left")
P.finish(fig)
```

| v [kn] | 1.0 | 1.5 | 2.0 | 2.5 | 3.0 | 4.0 | 5.0 |
|---|---|---|---|---|---|---|---|
| $F_1' = F_1\sin\alpha$ [kgf] | 23.3 | 22.5 | 21.6 | 20.7 | 19.8 | 18.1 | 16.3 |
| $F_2' = F_2\sin\beta$ standard [kgf] | 5.9 | 8.8 | 12.7 | 17.6 | 23.4 | 37.2 | 53.8 |
| Fridman buoyancy, standard [kgf] | 30 | 32 | 35 | 39 | 44 | 56 | 71 |
| Fridman ballast, standard [kg] | 27.4 | 29.4 | 32.5 | 36.5 | 41.4 | 53.5 | 68.4 |
| $R_B$ (12 floats) [kgf] | 2.4 | 5.5 | 9.8 | 15.3 | 23.4 | 41.7 | 65.1 |

The drag of the floats is small compared with that of the net (≈ 1.4 % at 3 kn), but not
negligible: at 5 kn it is twice that of the two warps computed with the Nomura–Yamazaki
coefficient ({doc}`18_cables`).

## Exercises

From the bank of the teaching mode, with the data of the book. In the app, the “UTN Classroom” mode
generates them with other data and marks them ({doc}`38_docentes`).

```{code-cell} ipython3
:tags: [remove-input]
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path.cwd().parent))
import _exercises
_exercises.section("17_flotacion_lastre")
```
