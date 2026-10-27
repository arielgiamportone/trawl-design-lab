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

# Otter boards and rigging

## Purpose

The otter boards are the “wings” of the gear: two plates that, towed at an angle of attack, generate
a lateral force that spreads the warps and opens the net horizontally. That force has a price, the
drag of the otter boards $R_{OB}$, which the vessel pays with part of its pull. Between the otter
boards and the net is the **rigging**: crowfoot, sweeps and bridles, which transmit the spreading
force to the wing tips and fix the geometry of the mouth.

This chapter replicates the sheet *Portones y aparejamiento* [Otter boards and rigging]. In the
calculation chain ({doc}`motor`) it comes after the net drag ({doc}`14_resistencia`) and the warp
paid out, and it feeds the openings ({doc}`16_aberturas`), the buoyancy ({doc}`17_flotacion_lastre`)
and the warps ({doc}`18_cables`). In `trawlkit` it lives in `trawlkit.rigging.doors` and
`trawlkit.rigging.bridles`.

## Theory

### Hydrodynamic forces on the otter board

An otter board of area $S$ advancing at speed $v$ with an angle of attack $\alpha$ receives a
hydrodynamic force that splits into a component parallel to the motion, the drag, and a
perpendicular one, the spreading force (lift). With the dynamic pressure written in technical units,
as throughout the book {cite:p}`fridman1986`:

$$
R_{OB} = \tfrac12\,\frac{\rho}{g}\,C_D\,S\,v^2, \qquad
F_y = \tfrac12\,\frac{\rho}{g}\,C_L\,S\,v^2
$$ (eq-15-fuerzas)

with $\rho = 1024$ kg/m³, $g = 9.81$ m/s², $S$ in m² and $v$ in m/s, so that $\rho/g$ is the
“specific mass” in kgf·s²/m⁴ and the forces come out directly in kgf. Both grow with $v^2$: doubling
the speed quadruples the spreading force and the drag of the otter board.

The coefficients $C_L$ and $C_D$ depend on the angle of attack and are read from the **polar** of the
otter board (flume tank or wind tunnel tests). In a flat rectangular otter board of low aspect ratio
($\lambda = h/l \approx 0.5$), $C_L$ grows almost linearly up to a maximum near 30–35° and then the
plate stalls, while $C_D$ keeps increasing. The reasonable working point is just before the maximum
of $C_L$: the ratio $C_L/C_D$ (efficiency) falls from there on and each extra kgf of spreading force
costs more and more pull. The book works at $\alpha = 32°$ ($C_L = 0.93$, $C_D = 0.71$,
$C_L/C_D = 1.31$) with the FAO flat wooden otter board with an iron frame for the A3/B3/C3 nets; the
catalogue also includes a Morgère polyvalent oval otter board, more efficient
($C_L/C_D \approx 1.6$ at 27–30°). The two polars of the book are, number for number, the «Flat
Wooden» and «Morgère Polyvalent Ovale» data sheets of the Seafish, IFREMER and DIFTA flume tank
study {cite:p}`sfia1993` (see below).

### Door spread: the “per metre” rule

The distance between otter boards $D_s$ is estimated with a rule of thumb: each metre of warp paid
out $L_s$ opens a certain spread $k$ (2.65 m in the workbook), less the distance between the
vessel's towing blocks $a$, which is the starting spread:

$$
D_s = (k - a)\,L_s + a
$$ (eq-15-ds)

From it one obtains the half-angle of divergence of the warps, which is the angle $\delta_2$ of
chapter {doc}`18_cables`:

$$
\tfrac12\varphi = \arcsin\!\left(\frac{D_s - a}{2\,L_s}\right)
$$ (eq-15-divergencia)

and a corrected spread $D_s' = 1.15 \cdot 2\,L_s \sin(\tfrac12\varphi)$, which applies an empirical
factor for the curvature of the warp.

### Otter board drag as a fraction of the pull, and required area

Fridman proposes sizing the otter boards so that their drag is between 15 and 30 % of the available
pull $F_T$ {cite:p}`fridman1986`; the book adopts 20 %:

$$
R_{OB} = p\,F_T, \qquad p \in [0.15;\ 0.30]
$$ (eq-15-rob-share)

Inverting {eq}`eq-15-fuerzas` with that drag gives the total otter board area that the vessel “can
afford” at each speed:

$$
S_{req} = \frac{2\,R_{OB}}{(\rho/g)\,C_D\,v^2}
$$ (eq-15-sreq)

Since $F_T$ decreases with speed and $v^2$ increases, $S_{req}$ falls very fast: at 1 kn it would
come out at tens of m². The book averages $S_{req}$ between 2 and 4 kn, divides it by two otter
boards and averages the 150 and 180 HP vessels.

### Force on the otter board, centre of pressure and moment balance

To check the adjustment (the position of the attachment points of the crowfoot) the book calculates
the normal force on the plate with the flat-plate formula

$$
P_\varphi = \tfrac12\,C_D\,\frac{\rho}{g}\,v^2\,S\,\frac{2\sin\varphi}{1+\sin^2\varphi}
$$ (eq-15-pphi)

and the centre of pressure, measured from the leading edge along the length $L$ of the otter board,

$$
d = \frac34\,\frac{\cos\varphi}{4 + \pi\sin\varphi}\,L, \qquad
h_A = \frac{0.8\,L}{4}, \quad h_B = \frac{L}{4}
$$ (eq-15-cp)

The otter board is in equilibrium when the moment of $P_\varphi$ about the attachment point
($P_\varphi\,d$) is balanced by that of the sweep tension ($\tfrac12 R_N$ per otter board) with its
arm $d_p$ (3 m in the workbook): $M_P = P_\varphi\,d$ against $M_R = \tfrac12\,R_N\,d_p$.

### Bridles, sweeps and crowfoot

The **bridles** join the wing tip with the end of the sweep. With the net open to a height $AV$, the
upper bridle forms an angle $\alpha_b$ (4.8° in the workbook) with the lower one, and its length
according to {cite:t}`martini` is

$$
V_s = \frac{AV}{\sin\alpha_b} - f_L \quad\text{(without triangle)}, \qquad
V_s^{\triangle} = \frac{AV - h_{dl}}{\sin\alpha_b} \quad\text{(with triangle / dan leno)}
$$ (eq-15-bridas)

where $f_L$ is the sag of the headrope (chapter {doc}`16_aberturas`) and $h_{dl}$ the height of the
triangle or dan leno (0.6 m). The lower bridle is shortened with an adjusting chain of 9.5 % of
$V_s$.

The **sweeps** are sized in two ways: Dremière's rule, a fraction of the warp paid out
($L_p = L_s/6$, {cite:p}`prado1990`), and Martini's geometry, which requires the net of length $L_R$
and opening $DPA$ to fit in the triangle formed by the otter boards:

$$
L_p = \left(\frac{D_s\,L_R}{DPA} - (V_s + L_R)\right) \cdot 1.1
$$ (eq-15-patentes)

Martini also gives a version by angle, $L_p = (D_s - DPA)/(2\sin\delta)$ with $\delta = 20°$. The
**crowfoot** is taken 20 % longer than the otter board, $PG = 1.2\,L$. Finally, the angle of attack
of bridles and sweeps, which matters for herding fish and for the DPA, is

$$
\delta = \arcsin\!\left(\frac{(D_s - DPA)/2}{PG + L_p + V_s}\right)
$$ (eq-15-delta)

The usual values of $\delta$ for bottom trawling are between 10 and 20°; larger angles increase the
herding but also the drag of the rigging.

### Polar library by otter board type

The primary source of the book's polars is the report *Otterboard Performance and Behaviour*
{cite:p}`sfia1993`: 26 otter board models tested in the flume tanks of Hull, Boulogne and
Hirtshals, at 0.9 m/s over the moving belt (the $C_D$ includes the belt friction), at 25 to 45°
angle of attack. Each data sheet of Appendix IV gives the model dimensions, the aspect ratio $H/L$,
the area ratio, the weight in air and in water, $C_L$ and $C_D$ every 5° and the maximum $C_L$ with
its angle. The A-3 Excel workbook {cite:p}`giamportone2024` copied two of them as they are: «Flat
Wooden» (App. IV-3) and «Morgère Polyvalent Ovale» (App. IV-17; the «0» at 25° in the Excel sheet
is an angle that was not tested, marked «–» by Seafish).

`trawlkit` keeps the 26 sheets, transcribed and checked page by page, in
`trawlkit/data/door_polars.yaml`, together with the tables of the Thyborøn 15 VF pelagic door
(aspect ratio 2.5) and the Grilli Fly (1.91) by {cite:t}`mellibovsky2018`, measured in the St
John's flume tank and in a wind tunnel. `rigging.polar_for_type` gives a representative polar per
type:

| Type | Polar | Provenance |
|---|---|---|
| flat | «Flat Wooden» sheet | transcribed |
| vee | mean of Reference Vee, Blooe Tech and Munkebo, as {cite:t}`sfia1993` recommend (section 3-16) | derived |
| oval | «Morgère Polyvalent Ovale» sheet | transcribed |
| cambered (slotted) | mean of Net Tec, Perfect Patent B and the 125" Thyborøn Type 2 | derived |
| multi-foil | mean of Bison 3 Slots, Hydrofin, Morgère Polyfoil and Fjørtoft (30–45°) | derived |
| high-aspect pelagic (Süberkrüb) | Thyborøn 15 VF in the flume tank: linear $C_L$ and quadratic $C_D$ fitted to the 11 points | derived |

Up to Phase 19.2 the catalogue vee polar was the flat polar with $C_L$ multiplied by 0.775/0.93,
and the Süberkrüb polar was the oval one: neither was measured. For the pelagic door,
{cite:t}`mellibovsky2018` find that the flume tank gives 20–30 % less than the wind tunnel and
attribute it to an error in the nominal flume tank speed; the «theoretical» Süberkrüb values of
{cite:t}`scharfe1955` ($C_L/C_D \approx 14$ at 9.5°, without ground contact) are not used and
remain a low-confidence reference. No manufacturer publishes the polar of its boards: the Vónin
{cite:p}`vonin_doors` (area and weight) and Morgère {cite:p}`morgere2025` (area; the weight is
«sur demande» and left empty) boards carry the polar of their type marked as *assumed*. Vónin's
claim of a $C_L$ of 4.39 for the Twister is kept as a note, not as data.

In corrected mode `rigging.door_polar` interpolates linearly between the tabulated angles and, up to
5° outside the measured range, extrapolates with the end segment and warns (the `door_polar:` note
of the result); `EXCEL` mode still asks for an angle of the table, like the book's `LOOKUP`.

### Choosing the otter board: equivalent area

The engine gives the required area per otter board $A_1$ (`Port!F215`) for the case board, with its
$C_D$. To change the type of otter board while keeping the spreading force, {cite:t}`sfia1993`
(App. III-9) set $A_1\,C_{L1} = A_2\,C_{L2}$:

$$
A_2 = A_1\,\frac{C_{L1}}{C_{L2}}, \qquad L_2 = \sqrt{\frac{A_1\,C_{L1}}{C_{L2}\,AR_2\,C_{A2}}}
$$ (eq-15-equivalente)

with $C_L$ at the working angle of each board, $AR_2 = H_2/L_2$ and $C_{A2}$ the area ratio.
Because boards of the same type perform differently (the Munkebo gives 27 % more $C_L$ than the
other two vees), when changing to a board with a higher $C_L$ they recommend adding **10 %** to the
calculated area (section 3-16). The tool `trawlkit.door_selection.select_doors` (and
`POST /doors/select`, «Choose otter boards» in the app) applies the rule to the whole filtered
components catalogue and also:

- takes $C_{L2}$ at the case angle if the board is of the same type and otherwise at the
  recommended angle of attack of the type: flat 35–40°, vee and oval 35°, Süberkrüb 15°
  {cite:p}`prado1990`; cambered 34–37° and multi-foil 40–45° (angle of maximum $C_L$ on the Seafish
  sheets);
- leaves high-aspect pelagic boards out of a bottom trawl: they are unstable at the low towing
  speeds of bottom trawling ({cite:t}`sfia1993`, §2.2.1);
- compares the weight with the *Fisherman's Workbook* weight for the type and area: the table gives
  the maximum weight used and notes that with a lighter material a board may weigh up to 50 % less
  {cite:p}`prado1990`; a lighter board is flagged and one without a published weight is warned;
- gives the backstrop length: each leg no less than the board length and up to 1.5 times
  ({cite:t}`sfia1993`, §2.2.3).

## Coefficients

| Symbol | Value | Unit | Source | Cell |
|---|---|---|---|---|
| $k$ (spread per metre of warp) | 2.65 | m | “per metre” rule of thumb | `Port!D7` |
| $a$ (distance between towing blocks) | 2.5 | m | Tipo de buques [vessel types] | `Port!D6` |
| correction factor of $D_s$ | 1.15 | — | — | `Port!D28` |
| $\alpha$ otter board | 32 | ° | chosen row of the polar | `Port!C134` |
| $C_L$, $C_D$ at 32° | 0.93; 0.71 | — | {cite:t}`sfia1993`, «Flat Wooden» sheet (through the Excel workbook) | `Port!D134:E134` |
| equivalent-area margin | 10 | % | {cite:t}`sfia1993`, section 3-16 | — |
| backstrops / board length | 1–1.5 | — | {cite:t}`sfia1993`, §2.2.3 | — |
| $S$ FAO otter board | 1.805 | m² | catalogue | `Port!D122` |
| $p$ (ROB / FT) | 0.15–0.30 (0.20) | — | {cite:t}`fridman1986` | `Port!E146:H146`, `D210` |
| $\alpha_b$ between bridles | 4.8 | ° | {cite:t}`martini` | `Port!F39` |
| adjusting chain | 0.095·$V_s$ | m | — | `Port!D46` |
| $L_s / L_p$ (Dremière) | 6 | — | {cite:t}`prado1990` | `Port!B68` |
| $\delta$ Martini | 20 | ° | {cite:t}`martini` | `Port!H65` |
| sweep factor | 1.1 | — | {cite:t}`martini` | `Port!C83` |
| $d_p$ (sweep arm) | 3 | m | — | `Port!E277` |

## Excel ↔ `trawlkit` equivalence

| Cell(s) | Calculation | Function |
|---|---|---|
| `Port!E13` | $D_s$ per metre | `rigging.door_spread_m` |
| `Port!D21`, `F30` | $\tfrac12\varphi$ and corrected $D_s$ | `rigging.warp_divergence_deg`, `rigging.door_spread_corrected_m` |
| `Port!C132:F137` | polar $C_L$, $C_D$ | `rigging.door_polar`, `rigging.door_polar_table` |
| `Port!E146:H168` | ROB as % of FT | `rigging.door_drag_share_kgf` |
| `Port!D190:E198` | ROB and $F_y$ | `rigging.door_forces_kgf` |
| `Port!E210:F229` | required area | `rigging.required_area_m2`, `rigging.required_area_summary` |
| `Port!D252:D260` | $P_\varphi$ | `rigging.door_force_kgf` (erratum `door_force_mixed_angles`) |
| `Port!C266:C270` | centre of pressure | `rigging.centre_of_pressure_m` |
| `Port!G281:H289` | moments | `rigging.moment_balance` |
| `Port!E52`, `E60`, `D44:D46` | bridles | `rigging.bridle_lengths` |
| `Port!C71` | Dremière sweeps | `rigging.sweeps_dremiere_m` |
| `Port!G71` | Martini sweeps by δ | `rigging.sweeps_martini_m` (erratum `sweep_degrees_of_sine`) |
| `Port!C83`, `C87` | sweeps without / with triangle | `rigging.sweeps_length_m` |
| `Port!E97:G99` | crowfoot | `rigging.crowfoot_m` |
| `Port!D110` | angle $\delta$ | `rigging.attack_angle_deg` |
| whole sheet | `doors` and `bridles` stages | `model.run` → `result.doors`, `result.bridles` |
| — (Phase 19.3) | measured polars and polar per type | `rigging.load_door_polars`, `rigging.polar_for_type` |
| — (Phase 19.3) | choice of the catalogue otter board | `door_selection.select_doors`, `POST /doors/select` |

## Assumptions and limits

- **Catalogue coefficients.** The polar comes from a steady-state test, far from the seabed. Contact
  with the seabed (shoe), the inclination (*heel* and *tilt*) and the wake of the warps change $C_L$
  and $C_D$ in practice; the values are a first approximation.
- **One otter board or the pair.** {eq}`eq-15-fuerzas` is evaluated with the area of **one** otter
  board (1.805 m²); the sheet labels that value as “ROB”. On the other hand, {eq}`eq-15-rob-share`
  and {eq}`eq-15-sreq` refer to the **pair**: $S_{req}$ is the total area and the book divides it by
  two. To compare with Fridman's band the two otter boards must be added,
  $R_{OB}^{par} = 2\cdot\tfrac12(\rho/g)C_D S v^2$. The required area per otter board (≈ 1.82 m²
  averaging 150 and 180 HP) is almost equal to that of the chosen otter board, but that average
  between 2 and 4 kn is dominated by the slow end, where $S_{req}$ is large.
- **Per metre rule.** {eq}`eq-15-ds` is empirical: it depends neither on the speed nor on the
  spreading force. Fridman's DPA ({doc}`16_aberturas`) does solve the force balance.
- **Erratum `door_force_mixed_angles`** (`Port!D252`). The cell writes `SIN(RADIANS($E$240))` in
  the numerator of {eq}`eq-15-pphi` but `SIN($E$240)` in the denominator: it takes 32 as radians.
  Since $\sin(32\,\text{rad}) = 0.551$ and $\sin 32° = 0.530$, the error is small (≈ 1.8 % in
  $P_\varphi$), but it exists. `Compat.EXCEL` reproduces it; `Compat.CORRECTED` uses radians in both
  sines ({doc}`erratas`).
- **Erratum `sweep_degrees_of_sine`** (`Port!G71`). The formula as written is
  `((E13/2)-(E78/2)/DEGREES(SIN(H65)))`: it takes the sine of 20 rad, converts it to “degrees” and,
  because of operator precedence, divides only $DPA/2$. Result: 16.1 m instead of 28.5 m. The value
  is not used downstream (the design sweeps are 25 m, `Dim!F65`), so it only affects the reading of
  the sheet.
- **Units of the moment.** `Port!H281` is labelled in kgf·cm but is worth $\tfrac12 R_N d_p$ in
  kgf·m; `trawlkit` keeps the value and names it `sweep_moment_kgf_m`. Comparing `G281` and `H281`
  directly mixes orders of magnitude.

## Executable example

We run the book's case (standard + modified net, 150 HP vessel with the 180 HP one in the class) in
`Compat.EXCEL` mode and check against the cached values of the Excel workbook.

```{code-cell} ipython3
import math
import pathlib
import sys

DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English

import numpy as np

from tests.golden_utils import golden
from trawlkit import Compat, rigging
import _plots_t2 as P

PORT = "portones_y_aparejamiento"
r = P.fao_result(150, "excel")
d, br = r.doors, r.bridles


def close(actual, key, sheet=PORT):
    """Compare with the Excel value (scalar or series) at rtol = 1e-6."""
    exp = np.atleast_1d(golden(sheet, key))
    got = np.atleast_1d(actual)
    return all(math.isclose(a, b, rel_tol=1e-6) for a, b in zip(got, exp))


assert close(d.spread_m, "door_spread_m")  # per-metre spread
assert close(d.polar.cl_cd, "door_cl_cd_selected")  # polar at 32°
assert close(d.forces.drag_kgf, "rob_kgf")  # ½·ρ/g·CD·S·v²
assert close(d.forces.lift_kgf, "door_spreading_force_kgf")  # ½·ρ/g·CL·S·v²
assert close(d.required_area_per_door_class_m2, "required_door_area_overall_m2")
assert close(br.attack_angle_deg, "bridle_attack_angle_deg")

print(f"Ds = {d.spread_m:.2f} m; ½φ = {d.half_divergence_deg:.2f}°; "
      f"corrected Ds = {d.spread_corrected_m:.2f} m")
print(f"Required S per otter board = {d.required_area_per_door_class_m2:.3f} m² "
      f"(FAO otter board: {d.door.area_m2} m²)")
print(f"Bridles: Vs = {br.lengths.upper_m:g} m, "
      f"lower = {br.lengths.lower_m:g} m, "
      f"chain = {br.lengths.adjust_chain_m:.2f} m")
print(f"Crowfoot = {br.crowfoot.length_m} m; Dremière sweeps = "
      f"{br.sweeps_dremiere_m:.1f} m")
print(f"Martini sweeps without/with triangle = {br.sweeps_no_triangle_m:.1f} / "
      f"{br.sweeps_triangle_m:.1f} m; δ = {br.attack_angle_deg:.2f}°")
```

The two errata of the chapter, in both modes. Both are checked against the Excel workbook in `EXCEL`
mode:

```{code-cell} ipython3
v = r.case.speeds_ms
p_excel = rigging.door_force_kgf(0.71, 1.805, 32.0, v, compat=Compat.EXCEL)
p_corr = rigging.door_force_kgf(0.71, 1.805, 32.0, v, compat=Compat.CORRECTED)
assert close(p_excel, "door_force_kgf")

lp_excel = rigging.sweeps_martini_m(d.spread_m, 13.0, 20.0, compat=Compat.EXCEL)
lp_corr = rigging.sweeps_martini_m(d.spread_m, 13.0, 20.0, compat=Compat.CORRECTED)
assert close(lp_excel, "sweeps_martini_m")

print(f"Pφ at 3.5 kn: Excel {p_excel[5]:.1f} kgf, corrected {p_corr[5]:.1f} kgf "
      f"({100 * (p_corr[5] / p_excel[5] - 1):+.1f} %)")
print(f"Martini sweeps (δ = 20°): Excel {lp_excel:.2f} m, "
      f"corrected {lp_corr:.2f} m")
cop = d.centre_of_pressure
print(f"Centre of pressure d = {cop.d_m:.3f} m; "
      f"hA = {cop.ha_m:.3f} m; hB = {cop.hb_m:.3f} m")
```

The polar of the two otter boards in the catalogue shows why one works near 30°: beyond the maximum
of $C_L$, the drag coefficient keeps growing and the efficiency falls ({numref}`fig-15-polar`).

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Polar of the otter boards in the catalogue. Top, lift coefficient $C_L$; bottom, drag
      coefficient $C_D$, as a function of the angle of attack. The ring marks the book's working
      point (FAO otter board at 32°). The Morgère has no data at 25°.
    name: fig-15-polar
---
from trawlkit.io import load_doors

P.setup()
doors = load_doors().doors
names = {"fao_flat_wood_a3": "FAO flat wooden (A3)", "morgere_polivalente_oval": "Morgère polyvalent oval"}
fig, axes = P.plt.subplots(2, 1, figsize=(7, 6.6), sharex=True)
for slot, door in enumerate(doors, start=1):
    pol = rigging.door_polar_table(door)
    ang = [p.angle_deg for p in pol]
    P.line(axes[0], ang, [p.cl for p in pol], slot, names[door.id])
    P.line(axes[1], ang, [p.cd for p in pol], slot, names[door.id])
sel = d.polar
for ax, val, dy in ((axes[0], sel.cl, 10), (axes[1], sel.cd, -16)):
    ax.plot([sel.angle_deg], [val], "o", ms=14, mfc="none", mec=P.INK_2, mew=1.2)
    ax.annotate(f"32°: {val:.2f}", (sel.angle_deg, val), xytext=(10, dy),
                textcoords="offset points", color=P.INK_2, fontsize=9)
axes[0].set_title("Lift $C_L$")
axes[1].set_title("Drag $C_D$")
axes[1].set_xlabel("Angle of attack α [°]")
axes[0].set_ylim(0.6, 1.3)
axes[1].set_ylim(0.4, 1.0)
P.legend(axes[0], loc="lower center")
P.finish(fig)
```

The forces of the otter boards grow with $v^2$, while the drag that the vessel “can afford”
($p\,F_T$, between 15 and 30 % of a pull that falls with speed) decreases. The otter boards are well
sized for the speed at which the drag of the pair crosses the band ({numref}`fig-15-fuerzas`).

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Drag and spreading force of the pair of FAO otter boards at 32° (twice the force of one
      otter board) against Fridman's band, 15–30 % of the available pull $F_T$ (fixed pitch
      propeller, 150 HP). The dotted line is the 20 % adopted by the book.
    name: fig-15-fuerzas
---
fig, ax = P.plt.subplots(figsize=(7, 4))
kn = r.case.speeds
lo, hi = d.rob_shares_kgf["15pct"], d.rob_shares_kgf["30pct"]
ax.fill_between(kn, lo, hi, color=P.NEUTRAL_WASH, lw=0, label="15–30 % of $F_T$")
ax.plot(kn, d.rob_share_kgf, color=P.NEUTRAL, lw=1.2, ls=(0, (3, 3)), label="20 % of $F_T$")
lift2 = 2 * np.asarray(d.forces.lift_kgf)
drag2 = 2 * np.asarray(d.forces.drag_kgf)
P.line(ax, kn, lift2, 1, "Spreading force of the pair $2F_y$")
P.line(ax, kn, drag2, 2, "Drag of the pair $2R_{OB}$")
P.end_label(ax, kn[-1], lift2[-1], f"{lift2[-1]:.0f} kgf", dx=0.08)
P.end_label(ax, kn[-1], drag2[-1], f"{drag2[-1]:.0f} kgf", dx=0.08)
cross = np.interp(0.0, drag2 - np.asarray(d.rob_share_kgf), kn)
ax.axvline(cross, color=P.AXIS, lw=1)
ax.annotate(f"crosses the 20 %: {cross:.2f} kn", (cross, 900), xytext=(6, 0),
            textcoords="offset points", color=P.INK_2, fontsize=9, va="center")
P.speed_axis(ax)
ax.set_xlim(0.9, 5.6)
ax.set_ylabel("Force of the pair of otter boards [kgf]")
ax.set_ylim(0, 1250)
P.legend(ax)
P.finish(fig)
```

| v [kn] | 1.0 | 2.0 | 3.0 | 3.5 | 4.0 | 5.0 |
|---|---|---|---|---|---|---|
| $R_{OB}$ of one otter board [kgf] | 17.7 | 70.8 | 159.3 | 216.8 | 283.2 | 442.5 |
| $F_y$ of one otter board [kgf] | 23.2 | 92.7 | 208.6 | 284.0 | 370.9 | 579.6 |
| $2R_{OB}$ of the pair [kgf] | 35.4 | 141.6 | 318.6 | 433.6 | 566.4 | 884.9 |
| 20 % of $F_T$ [kgf] | 279.0 | 258.0 | 237.0 | 226.5 | 216.0 | 195.0 |

The pair of 1.8 m² otter boards consumes exactly 20 % of the pull at about 2.6 kn, a typical bottom
trawling speed; at 3.5 kn it already consumes 38 %. That is why the average of $S_{req}$ between 2
and 4 kn (≈ 1.66 m² per otter board for 150 HP) is somewhat smaller than the chosen otter board.
Note that the total drag of chapter {doc}`19_ventana_velocidad` (corrected mode) adds the sheet's
“ROB”, that is, the drag of **one** otter board.

The polar library compares the otter board types ({numref}`fig-15-tipos`): the flat board has the
lowest maximum $C_L$; the slotted cambered boards reach 1.4–1.5; the multi-foil boards keep gaining
$C_L$ up to 40–45°; the high-aspect pelagic board gives a lot of $C_L$ with little $C_D$ at low
angles.

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Representative polar of each otter board type (`rigging.polar_for_type`). Top $C_L$, bottom
      $C_D$. Flat and oval: Seafish/IFREMER/DIFTA (1993) sheets; vee, cambered and multi-foil: mean
      of several sheets; pelagic: fit to the points of the Thyborøn 15 VF in the flume tank
      (Mellibovsky et al. 2018), which the wind tunnel gives 20–30 % higher.
    name: fig-15-tipos
---
from trawlkit.rigging.polars import DOOR_TYPE_LABEL, DOOR_TYPES
from trawlkit.i18n import t as _t

fig, axes = P.plt.subplots(2, 1, figsize=(7, 6.6), sharex=True)
for slot, kind in enumerate(DOOR_TYPES, start=1):
    tp = rigging.polar_for_type(kind)
    ang = [c.angle_deg for c in tp.coefficients]
    P.line(axes[0], ang, [c.cl for c in tp.coefficients], slot, _t(DOOR_TYPE_LABEL[kind]))
    P.line(axes[1], ang, [c.cd for c in tp.coefficients], slot, _t(DOOR_TYPE_LABEL[kind]))
axes[0].set_title("Lift $C_L$")
axes[1].set_title("Drag $C_D$")
axes[1].set_xlabel("Angle of attack α [°]")
P.legend(axes[1], loc="upper left", fontsize=8)
P.finish(fig)
```

Choosing the otter board for the book's case (corrected mode): the required area per otter board
with the FAO board at 32° is carried over to every catalogue board with {eq}`eq-15-equivalente`. The
A-3 board is among the candidates, and it is the tightest flat board.

```{code-cell} ipython3
from trawlkit.door_selection import select_doors

sel = select_doors(P.fao_result(150, "corrected"))
assert any(c.id == "fao_flat_wood_a3" for c in sel.candidates)
print(f"Required area per otter board: {sel.required_m2:.2f} m²")
for c in sel.candidates[:6]:
    weight = "no weight" if c.weight_air_kg is None else f"{c.weight_air_kg:.0f} kg"
    extra = " (+10 %)" if c.margin_applied else ""
    print(f"{c.name[:44]:44s} {c.area_m2:5.2f} m² ≥ {c.required_m2:4.2f}{extra:8s} "
          f"margin {100 * c.area_margin:4.1f} %  {weight}")
```

## Exercises

From the bank of the teaching mode, with the book's data. In the app, the “UTN Classroom” mode
generates them with other data and marks them ({doc}`38_docentes`).

```{code-cell} ipython3
:tags: [remove-input]
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path.cwd().parent))
import _exercises
_exercises.section("15_portones_aparejo")
```
