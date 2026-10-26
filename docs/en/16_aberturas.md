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

# Horizontal and vertical openings

## Purpose

The mouth of the net is the section that sweeps the seabed: its width, the **wing-end spread**
(DPA, or horizontal opening AH), and its height, the **vertical opening** AV, set the swept area and,
with it, the catch per hour of towing. Neither of the two is a dimension of the net: they result from
the balance between the spreading force of the otter boards, the drag of the net, the buoyancy of
the headrope and the geometry of the rigging.

The book estimates each opening by several independent methods and compares them. This chapter
replicates the blocks B162:P282 of *Mecánica de la Red* [Net mechanics] and the cell `Dim!F61`; in
`trawlkit` it lives in `trawlkit.rigging.spread`. It uses the net drag ({doc}`14_resistencia`), the
forces of the otter board and the rigging ({doc}`15_portones_aparejo`) and the total buoyancy
({doc}`17_flotacion_lastre`), and in turn it feeds Dickson's drag method and the sizing of the warps
({doc}`18_cables`).

## Theory

### Towing geometry

The warp paid out $L_s$ is chosen by depth $d$ with the tabulated ratio $L_s/d$ (table *depth → warp
paid out*, 6:1 at 20 m, 5:1 at 40 m, ≈ 3:1 at 200 m); the table is looked up like the Excel
`LOOKUP`, with the row of greatest depth not exceeding $d$:

$$
L_s = d\cdot\left(\frac{L_s}{d}\right)_{tab}, \qquad L_{sh} = 0.95\,L_s
$$ (eq-16-ls)

$L_{sh}$ is the horizontal projection of the warp in shallow water (0.85·$L_s$ in deep water). The
working net has a length $L_{Rw} = L_R\,U_2$, with $L_R$ the length without codend and $U_2 = 0.87$
the vertical hanging ratio of the open net.

### Fridman's DPA: expansion coefficients

{cite:t}`fridman1986` sets up the balance of half the system (one otter board, one warp, half the
net) and expresses the forces of the otter board relative to half the net drag with two **expansion
coefficients**:

$$
E_{dx} = \frac{R_{OB}}{R_N/2}, \qquad E_{dy} = \frac{F_y}{R_N/2}
$$ (eq-16-edx)

$E_{dy}$ measures how much the otter board “pulls outwards” against what the net “pulls backwards”;
$E_{dx}$ measures the extra drag that the otter board adds along the line of the warp. Both grow with
speed because the forces of the otter board scale with $v^2$ while $R_N$ grows somewhat more slowly.
With the working net $L_{Rw}$ and the bridles $L_{nc}$ ($=V_s$, upper bridle):

$$
DPA = \frac{2\,L_{sh}\,L_{Rw}\,E_{dy}}{L_{sh} + L_{nc}\,(1 + E_{dx})}
$$ (eq-16-dpa-fridman)

Fridman's DPA is the only one that depends on speed: at 1 kn the net opens barely 6 m and at 5 kn it
exceeds 15 m.

### Geometric DPA and DPA from the cut angle

By **similar triangles**, if the rigging (crowfoot $PG$, crowfoot extension $A_{PG}$, sweeps $L_p$,
bridle $V_s$) and the net (length $m$) are taut in a straight line from each otter board, the opening
at the wing tips is the fraction of $D_s$ that corresponds to the net:

$$
DPA_g = \frac{m\,D_s}{PG + A_{PG} + L_p + V_s + m}
$$ (eq-16-dpa-geom)

The book evaluates it with the footrope ($m$ = 33.3 m, rounding down) and with the working net
($m = L_{Rw}$, only in the numerator and in the net term, rounding up). The third method, from
{cite:t}`prado1990`, deduces the opening from the shape of the net: with a total length $b$ and the
mean angle of the cuts $\alpha$ (chapter {doc}`11_panos_y_cortes`),

$$
DPA_\alpha = 2\,b\,U_2\,\tan\alpha
$$ (eq-16-dpa-corte)

The design **horizontal opening** is the average of the four methods, counting Fridman's series
(standard, 1–5 kn) as a single term:

$$
AH = \tfrac14\left(DPA_\alpha + DPA_{g,L_{Rw}} + DPA_{g,m} + \overline{DPA_{F}}\right)
$$ (eq-16-ah)

### Vertical opening

The empirical methods express AV as a fraction of the stretched-mesh circumference of the mouth $a$:

- {cite:t}`prado1990`: $AV = 0.055\,a$ in low-opening nets and $0.065\,a$ in high-opening or
  shellfish nets;
- {cite:t}`izzo` (INIDEP): 4.35, 5, 6 and 7 % of $a$;
- {cite:t}`suzuki1982`: $AV = \tfrac{4}{90}\,a$ (4.4 %), the value that the book adopts as the
  design AV (`Dim!F60`).

{cite:t}`martini` starts instead from the stretched circumference of the first back plus belly
panel, $D_V$, less the $M_R$ meshes taken up in the joinings to the ropes:

$$
AV_M = \left(D_V - \frac{M_R\,m_L}{1000}\right)\cdot 0.05
$$ (eq-16-av-martini)

### Baranov–Fridman AV: the headrope as a catenary

The physical method considers the headrope as a flexible cable loaded by the total buoyancy $F_{fz}$
and pulled backwards by the net. The angle at which the headrope and the bridle rise from the seabed
results from the ratio between buoyancy and drag {cite:p}`fridman1986`:

$$
\alpha_v = \arctan\!\left(\frac{2\,F_{fz}}{R_N}\right), \qquad
AV = h_{dl} + (f_L + V_s)\,\sin\alpha_v
$$ (eq-16-av-fridman)

where $h_{dl}$ is the height of the triangle or dan leno (0.6 m) and $f_L$ the sag of the headrope.
The sag is obtained from the catenary table, which gives $f_L/L$ as a function of the ratio $DPA/L$
between the opening and the length of the headrope: the more closed the net (small DPA/L), the more
the headrope “hangs”. Since $R_N$ grows with $v^2$ and $F_{fz}$ is fixed, **Fridman's AV falls with
speed**: the net flattens as it speeds up, the behaviour observed at sea.

## Coefficients

| Symbol | Value | Unit | Source | Cell |
|---|---|---|---|---|
| $L_s/d$ at 40 m | 5 | — | depth → warp table | `Mec!J178` |
| $L_{sh}/L_s$ | 0.95 (shallow), 0.85 (deep) | — | {cite:t}`fridman1986` | `Mec!F179:F180` |
| $U_2$ working net | 0.87 | — | — | `Mec!E184` |
| AV Prado | 5.5 %; 6.5 % of $a$ | — | {cite:t}`prado1990` | `Mec!H245:H247` |
| AV Izzo | 4.35; 5; 6; 7 % of $a$ | — | {cite:t}`izzo` | `Mec!J242:J245` |
| AV Suzuki | 4/90 of $a$ | — | {cite:t}`suzuki1982` | `Mec!D255` |
| $M_R$, Martini's factor | 12 meshes; 0.05 | — | {cite:t}`martini` | `Mec!E270`, `E272` |
| $h_{dl}$ (dan leno) | 0.6 | m | — | `Mec!O262` |
| $f_L/L$ | 0.216 (fixed) | — | catenary table | `Mec!O266` |

## Excel ↔ `trawlkit` equivalence

| Cell(s) | Calculation | Function |
|---|---|---|
| `Mec!E176:E186` | $L_s$, $L_{sh}$, $L_{Rw}$, $L_{nc}$ | `rigging.towing_geometry`, `rigging.warp_depth_ratio` |
| `Mec!H164:O172` | $R_d$, $F_{dy}$, $E_{dx}$, $E_{dy}$ | `rigging.door_forces_kgf`, `rigging.expansion_coefficients` |
| `Mec!P164:Q172` | Fridman's DPA | `rigging.dpa_fridman_m`, `rigging.fridman_spread` (erratum `dpa_std_uses_mod_edy`) |
| `Mec!I193:M201` | 2·Yn table and $D_s$ from the DPA | `rigging.dpa_fridman_table` |
| `Mec!L211` | geometric DPA (footrope) | `rigging.dpa_geometric_m` |
| `Mec!L225` | DPA with the working net | `rigging.dpa_geometric_working_m` |
| `Mec!L233` | DPA from the cut angle | `rigging.dpa_from_cut_angle_m` |
| `Dim!F61` | average AH | `rigging.horizontal_opening_m` |
| `Mec!F245:F247`, `K242:K245` | AV Prado, Izzo | `rigging.vertical_opening_pct_m` |
| `Mec!D255` | AV Suzuki | `rigging.vertical_opening_suzuki_m` |
| `Mec!E269:E272` | AV Martini | `rigging.vertical_opening_martini_m` |
| `Mec!O261` | $F_{fz}$ | `rigging.fridman_flotation_total_kgf` |
| `Mec!O265:O267` | $DPA/L$, $f_L/L$, $f_L$ | `rigging.catenary_ratio`, `rigging.headrope_sag_m` |
| `Mec!M272:O282` | AV Baranov–Fridman | `rigging.vertical_opening_fridman` |
| whole block | `spread` stage | `model.run` → `result.spread` |

## Assumptions and limits

- **Static equilibrium.** {eq}`eq-16-dpa-fridman` assumes straight warps in plan view, otter boards
  at a constant angle of attack and a symmetrical net; it considers neither the current nor the
  turning of the vessel.
- **Empirical design AV.** The percentages of the circumference condense the experience with
  two-panel nets on soft seabed; they depend neither on speed nor on buoyancy. The book adopts
  Suzuki (1.98 m) as the design AV; Baranov–Fridman gives 2.09 m on average, but 4.6 m at 1 kn and
  1.0 m at 5 kn.
- **Erratum `dpa_std_uses_mod_edy`** (`Mec!P164`). The DPA of the standard net is calculated with
  `$O164`, the $E_{dy}$ of the **modified** net, instead of `$N164`. Since the modified net has
  somewhat less drag, its $E_{dy}$ is larger by the ratio $R_{N,std}/R_{N,mod}$ (≈ 2.2 % at all
  speeds) and the standard DPA comes out overestimated in the same proportion. `Compat.CORRECTED`
  uses the standard $E_{dy}$ ({doc}`erratas`).
- **Erratum `catenary_ratio_hardcoded`** (`Mec!O266`): the circularity. The sag $f_L$ enters the
  length of the bridle ({eq}`eq-15-bridas`, $V_s = AV/\sin\alpha_b - f_L$); the bridle enters the
  DPAs ({eq}`eq-16-dpa-fridman` and {eq}`eq-16-dpa-geom`); and the DPA defines $DPA/L$, which is the
  input of the catenary table that gives $f_L$. The calculation is a **loop**:
  $f_L \to V_s \to DPA \to DPA/L \to f_L$. The Excel workbook breaks it by typing in
  $f_L/L = 0.216$ by hand, the value tabulated for $DPA/L = 0.87$, even though the sheet itself
  calculates $DPA/L = 0.45$ in `O265`. That value is moreover outside the table (which goes down to
  0.56, $f_L/L = 0.378$). The model keeps 0.216 in both modes so as not to change the design geometry
  (`DesignCase.catenary_ratio`) and records the discrepancy in `result.notes`; the example below
  solves the loop.

## Executable example

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

MEC = "mecanica_de_la_red"
r = P.fao_result(150, "excel")
s, tow = r.spread, r.rigging.towing


def close(actual, key, sheet=MEC):
    """Compare with the Excel value (scalar or series) at rtol = 1e-6."""
    got, exp = np.atleast_1d(actual), np.atleast_1d(golden(sheet, key))
    return all(math.isclose(a, b, rel_tol=1e-6) for a, b in zip(got, exp))


assert close(tow.net_length_working_m, "net_length_working_m")
assert close(s.fridman.edy_mod, "edy_mod")
assert close(s.fridman.dpa_std_m, "dpa_fridman_std_m")  # with the Edy erratum
assert close(s.dpa_cut_angle_m, "dpa_from_cut_angle_m")
DIM = "dimensiones_de_la_red"
assert close(s.horizontal_opening_m, "horizontal_opening_m", DIM)
assert close(s.vertical.martini_m, "av_martini_m")
assert close(s.vertical.flotation_total_kgf, "flotation_total_kgf")
assert close(s.vertical.fridman.std.av_average_m, "av_fridman_avg_std_m")

v = s.vertical
print(f"Ls = {tow.warp_m:g} m, Lsh = {tow.warp_horizontal_shallow_m:g} m, "
      f"LRw = {tow.net_length_working_m:.2f} m, Lnc = {tow.bridle_m:g} m")
print(f"Geometric DPA: footrope {s.dpa_geometric_m:g} m, LRw {s.dpa_working_m:g} m")
print(f"DPA from cut angle {s.dpa_cut_angle_m:.2f} m; "
      f"Fridman (mean 1–5 kn) {np.mean(s.fridman.dpa_std_m):.2f} m")
print(f"AH = {s.horizontal_opening_m:.2f} m")
pr = v.prado_m
print(f"AV Suzuki {v.suzuki_m:.2f} m; Prado {pr['low_opening']:.2f} / "
      f"{pr['high_opening']:.2f} m; Izzo {v.izzo_m[0]:.2f}–{v.izzo_m[-1]:.2f} m")
print(f"AV Martini {v.martini_m:.2f} m; "
      f"Fridman (mean) {v.fridman.std.av_average_m:.2f} m "
      f"with Ffz = {v.flotation_total_kgf:.1f} kgf")
```

The $E_{dy}$ erratum, isolated: the same inputs, in both modes.

```{code-cell} ipython3
d = r.doors
args = (d.door.area_m2, d.polar.cd, d.polar.cl, r.case.speeds_ms,
        r.drag.rn.std, r.drag.rn.mod, tow.warp_horizontal_shallow_m,
        tow.net_length_working_m, tow.bridle_m)
fx = rigging.fridman_spread(*args, compat=Compat.EXCEL)
fc = rigging.fridman_spread(*args, compat=Compat.CORRECTED)
assert close(fx.dpa_std_m, "dpa_fridman_std_m")
diff = 100 * (np.asarray(fx.dpa_std_m) / np.asarray(fc.dpa_std_m) - 1)
print(f"Standard DPA at 3 kn: Excel {fx.dpa_std_m[4]:.3f} m, "
      f"corrected {fc.dpa_std_m[4]:.3f} m")
print(f"Excel overestimate: {diff.min():.2f} % to {diff.max():.2f} %")
```

And the circularity of the catenary: starting from the Excel's 0.216, we go round the loop
$f_L \to V_s \to DPA_{g,L_{Rw}} \to DPA/L \to f_L/L$ until it repeats.

```{code-cell} ipython3
dims, case = r.dimensions.std, r.case
pg = r.rigging.crowfoot.length_m
ratio, seen = case.catenary_ratio, []
for _ in range(10):
    sag = rigging.headrope_sag_m(dims.headrope_m, ratio)
    vs = rigging.bridle_lengths(
        v.suzuki_m, sag, case.bridle_angle_deg, case.dan_leno_m
    ).upper_m
    dpa = rigging.dpa_geometric_working_m(
        d.spread_m, tow.net_length_working_m, pg, 0.0, case.sweeps_m, vs
    )
    seen.append((ratio, sag, vs, dpa, dpa / dims.headrope_m))
    new = rigging.catenary_ratio(dpa / dims.headrope_m)
    if new == ratio:
        break
    ratio = new
assert math.isclose(seen[0][4], golden(MEC, "dpa_over_l"), rel_tol=1e-6)
for i, (q, sag, vs, dpa, dl) in enumerate(seen):
    print(f"{i}: fL/L = {q:.3f} → fL = {sag:5.2f} m → Vs = {vs:g} m "
          f"→ DPA = {dpa:g} m → DPA/L = {dl:.3f}")
```

The loop converges in two steps to $f_L/L = 0.378$ (the end of the table), with a bridle of 13 m
instead of 18 m. That the table runs out indicates that, with this rigging, the net works more closed
than the catenary table contemplates (DPA ≈ 0.45–0.49 times the headrope).

{numref}`fig-16-aberturas` compares all the methods. The geometric and empirical methods are
constant; only Fridman's respond to speed, in opposite directions: the net opens horizontally and
flattens vertically as it speeds up.

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Horizontal (top) and vertical (bottom) opening of the standard FAO A-3 net with the
      150 HP vessel, by method. The curves are Fridman's methods (Excel mode); the straight lines,
      the methods that do not depend on speed. The grey band is Izzo's range (4.35–7 % of the
      circumference).
    name: fig-16-aberturas
---
P.setup()
kn = r.case.speeds
fig, (a1, a2) = P.plt.subplots(2, 1, figsize=(7, 8.4))

P.line(a1, kn, s.fridman.dpa_std_m, 1, "Fridman, standard")
P.line(a1, kn, fc.dpa_std_m, 1, "Fridman, standard corrected", marker=False, ls=(0, (4, 3)), lw=1.6)
flat = [(s.dpa_geometric_m, 2, "Geometric (footrope and $L_{Rw}$)"),
        (s.dpa_cut_angle_m, 3, "From the cut angle"),
        (s.horizontal_opening_m, 7, "Design AH (average)")]
for val, slot, lab in flat:
    style = {"ls": (0, (1.5, 2)), "lw": 2.4} if slot == 7 else {"lw": 2}
    a1.plot([1, 5], [val, val], color=P.color(slot), label=lab, **style)
a1.annotate("geometric = 13 m ≈ AH = 13.01 m", (3.2, 12.5), color=P.INK_2, fontsize=9, va="top")
a1.set_title("Wing-end spread")
a1.set_ylabel("DPA [m]")
a1.set_ylim(0, 18)
P.speed_axis(a1)
P.legend(a1, loc="lower right")

a2.fill_between([1, 5], v.izzo_m[0], v.izzo_m[-1], color=P.NEUTRAL_WASH, lw=0, label="Izzo 4.35–7 %")
P.line(a2, kn, v.fridman.std.av_m, 1, "Baranov–Fridman, standard")
for val, slot, lab in ((v.suzuki_m, 2, "Suzuki (design)"),
                       (v.prado_m["low_opening"], 3, "Prado 5.5 %"),
                       (v.prado_m["high_opening"], 4, "Prado 6.5 %"),
                       (v.martini_m, 5, "Martini")):
    a2.plot([1, 5], [val, val], color=P.color(slot), lw=2, label=lab)
a2.set_title("Vertical opening")
a2.set_ylabel("AV [m]")
a2.set_ylim(0, 5)
P.speed_axis(a2)
P.legend(a2, loc="upper right")
P.finish(fig)
```

| v [kn] | 1.0 | 2.0 | 2.5 | 3.0 | 4.0 | 5.0 |
|---|---|---|---|---|---|---|
| $E_{dx}$ standard | 0.084 | 0.155 | 0.175 | 0.190 | 0.212 | 0.229 |
| $E_{dy}$ standard | 0.110 | 0.203 | 0.229 | 0.248 | 0.277 | 0.300 |
| Fridman DPA standard (Excel) [m] | 5.78 | 10.61 | 11.96 | 12.96 | 14.44 | 15.58 |
| Baranov–Fridman AV standard [m] | 4.61 | 2.47 | 1.95 | 1.62 | 1.24 | 1.04 |

At fishing speed (2.5 kn) the two physical estimates agree with the design ones: Fridman's DPA
≈ 12 m against AH = 13.0 m, and Fridman's AV ≈ 1.95 m against Suzuki's 1.98 m.

## Exercises

From the bank of the teaching mode, with the book's data. In the app, the “UTN Classroom” mode
generates them with other data and marks them ({doc}`38_docentes`).

```{code-cell} ipython3
:tags: [remove-input]
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path.cwd().parent))
import _exercises
_exercises.section("16_aberturas")
```
