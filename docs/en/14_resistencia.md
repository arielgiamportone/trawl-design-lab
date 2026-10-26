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

# Net drag

```{code-cell} ipython3
:tags: [remove-cell]
import sys, pathlib, math
DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English
import numpy as np
import matplotlib.pyplot as plt
from tests.golden_utils import golden, SPEEDS_KN
import _plots_t1 as P
P.setup_style()
```

## Purpose

The hydrodynamic drag of the net, $R_N$, is the dominant term of the pull demand
({eq}`eq-pot-demanda` in {doc}`10_potencia`) and the number on which almost all the following stages
depend: the drag of the otter boards is set as a fraction of the pull, Fridman's horizontal opening
and his buoyancy use $R_N$, the warp is sized with the total drag and the speed window compares
$R_N(v)$ with the available pull ({doc}`19_ventana_velocidad`).

There is no universal formula. Each author fitted coefficients on one type of net —bottom or pelagic,
two-panel or four-panel, polyamide (PA) or polyethylene (PE)— and with a different size variable: the
circumference of the mouth, a rope, the solid area $S_s$ or the working area $S_t$. The book
evaluates thirteen methods for the two variants of the net, from 1 to 5 knots, and adopts one,
**Aberdeen demersal**, as the design $R_N$. This chapter presents the thirteen, their domain and why
that choice is reasonable.

## Theory

In all the formulas $R_N$ is in tonnes-force; $v$ in m/s except where $v_{kn}$ (knots, with
1 kn = 0.5144 m/s) is indicated. The geometric variables come from {doc}`12_mecanica_red` and
{doc}`13_dimensiones`: $d/l$, $S_s$, $S_t$, fishing circle $a$, length with codend $b$ and without
codend $L$, headrope, footrope and angle of attack $\alpha$.

### Japanese school: net size and $d/l$

Tauti's similarity law states that the drag of geometrically similar nets is proportional to $d/l$,
to the square of a linear dimension and to the square of the speed. Tauti, Nomura and Shu
{cite:p}`tauti1974` fitted it for two-panel trawls with the circumference of the mouth and a speed
exponent smaller than 2 (the net deforms and aligns with the flow as it speeds up):

$$
R_N = \frac{27\,(d/l)\,a^2\,v^{1.45}}{1000}.
$$ (eq-rn-tns)

Tauti's original form uses a rope $\ell$ (headrope or footrope) as the reference dimension:

$$
R_N = \frac{25\,(d/l)\,\ell^2\,v^2}{1000}.
$$ (eq-rn-tauti)

Koyama {cite:p}`koyama1974` replaces the square of a dimension by the product circumference × length
with codend, and in a later version {cite:p}`koyama1984` by circumference × length without codend,
with the speed in knots:

$$
R_N^{(1974)} = \frac{16\,(d/l)\,a\,b\,v^2}{1000}, \qquad
R_N^{(1984)} = \frac{8\,(d/l)\,a\,L\,v_{kn}^2}{1000}.
$$ (eq-rn-koyama)

Hamuro {cite:p}`hamuro` starts from the drag of a flat panel inclined at an angle $\alpha$ to the
flow:

$$
R_N = \frac{191\,(d/l)\,v^2\,S_t\,\lvert\sin\alpha\rvert}{1000}.
$$ (eq-rn-hamuro)

The “Nomura” column of the sheet, $T = 7.2\,\mathrm{NHP}/v$ {cite:p}`nomura1981`, **is not a drag**
but the available pull of a 150 or 180 NHP vessel; it is shown in the book's table but excluded from
the comparison.

### European school: solid area

The Scottish laboratories measured full-scale nets and found that the solid twine area $S_s$
explains drag better than any dimension of the mouth. Reid {cite:p}`reid1977` for pelagic nets and
Robertson {cite:p}`robertson1981` for semi-pelagic nets propose rational forms in knots:

$$
R_N^{\text{Reid}} = \frac{v_{kn}^2\,S_s}{54.72\,v_{kn} + 115.2}, \qquad
R_N^{\text{Rob}} = \frac{v_{kn}^2\,S_s}{66.18\,v_{kn} + 41.5}.
$$ (eq-rn-reid)

MacLennan {cite:p}`maclennan1981` fitted demersal PE nets, with a part independent of speed (the
friction of the parts that drag on the seabed) and a quadratic one:

$$
R_N^{\text{MacL}} = \frac{S_s\,(61.2 + 46.6\,v_{kn}^2)}{(1 + 0.0641\,v_{kn})\,9807}.
$$ (eq-rn-maclennan)

The formulas of the Marine Laboratory, Aberdeen {cite:p}`aberdeen` for demersal (PE) and pelagic
(nylon) nets are

$$
R_N^{\text{Ab,dem}} = S_s\,\frac{0.00624 + 0.00475\,v_{kn}^2}{1 + 0.0641\,v_{kn}}, \qquad
R_N^{\text{Ab,pel}} = S_s\,\frac{0.00868\,v_{kn}^2}{1 + 0.00475\,v_{kn}}.
$$ (eq-rn-aberdeen)

Note that $61.2/9807 = 0.00624$ and $46.6/9807 = 0.00475$: **Aberdeen demersal and MacLennan are the
same formula**, one in newtons and the other in tonnes, and they differ only by the rounding of the
coefficients (0.02 %).

### Fridman and Dickson: working area and mouth

Fridman {cite:p}`fridman1973` corrects the drag coefficient of a panel for the angle of attack and
for the filtration index (the term $d/l - 0.01$ grows with denser panels):

$$
R_N = \frac{\left[1.8 + 2\alpha\,(d/l - 0.01)\right] S_t\,v^2}{1000},
$$ (eq-rn-fridman)

with $\alpha$ in degrees, as the sheet uses it. Dickson {cite:p}`dickson` expresses the drag as a
function of the area of the mouth, horizontal opening (AH) times vertical opening (AV), with $S_t$ in
square feet:

$$
R_N = \frac{1}{125}\,S_t^{\,\mathrm{ft^2}}\,(d/l)\,\frac{1 + 2\cdot 6.6\,\mathrm{AH}\,\mathrm{AV}}{S_t^{\,\mathrm{m^2}}}.
$$ (eq-rn-dickson)

Dickson does not contain the speed explicitly; it depends on it only through AH and AV, which the
book takes from Fridman ({doc}`16_aberturas`). Since Fridman's AV decreases faster with speed than
the AH grows, Dickson gives a **decreasing** drag with speed above 1.5 kn: it is not applicable away
from the design point for which the openings were calculated.

### Domain of validity

| Method | Variable | Original net type | Material | $v$ |
|---|---|---|---|---|
| Tauti–Nomura–Shu | $d/l$, $a$ | bottom trawl, 2 panels | PA | m/s |
| Tauti (headrope/footrope) | $d/l$, rope | similar nets in general | — | m/s |
| Koyama 1974 / 1984 | $d/l$, $a$, $b$ or $L$ | bottom trawl | PA | m/s / kn |
| Hamuro | $d/l$, $S_t$, $\alpha$ | inclined flat panel | — | m/s |
| Reid | $S_s$ | pelagic | nylon | kn |
| Robertson | $S_s$ | semi-pelagic | — | kn |
| MacLennan | $S_s$ | bottom, 4 panels | PE | kn |
| Aberdeen demersal | $S_s$ | bottom (demersal) | PE | kn |
| Aberdeen pelagic | $S_s$ | pelagic | nylon | kn |
| Fridman | $d/l$, $S_t$, $\alpha$ | trawls in general | — | m/s |
| Dickson | $d/l$, $S_t$, AH, AV | trawls in general | — | (via openings) |

### Why Aberdeen demersal is the design $R_N$

1. **Net type.** The A-3 is a bottom trawl; of the formulas based on $S_s$ —those that best represent
   the amount of twine, including that of the codend—, Aberdeen demersal and MacLennan are the only
   ones fitted on demersal nets measured at full scale. Reid, Robertson and Aberdeen pelagic come
   from nets that do not touch the seabed and lack the speed-independent term.
2. **Position in the spread.** At 3 kn it lies somewhat above the median of the thirteen methods
   (≈ 9 %), on the conservative side without being an extreme like Aberdeen pelagic or Koyama 1984.
3. **Comparison with the simulation.** Against the DynamiT simulation {cite:p}`dynamit` of the same
   net ({doc}`32_validacion_dynamit`), Aberdeen demersal is between 15 and 33 % higher (more at low
   speed); for sizing otter boards and warps that bias is preferable to an optimistic one.
4. **Acknowledged limit.** Its coefficients are for PE; the A-3 is PA, with finer twine for the same
   strength and a smaller $S_s$. Applying it to PA is an extrapolation that the book accepts because
   the dominant term, $S_s$, already contains the actual twine diameter.

## Coefficients

| Method | Coefficients | Excel cell |
|---|---|---|
| Tauti–Nomura–Shu | 27; exponent 1.45 | `Res!D11:E19` |
| Tauti (headrope / footrope) | 25 | `Res!D30:E38`, `L30:M38` |
| Koyama 1974 / 1984 | 16 / 8 | `Res!D74:E82`, `C91:D99` |
| Hamuro | 191 | `Res!D117:E125` |
| Nomura (pull) | 7.2 | `Res!D132:E140` |
| Reid | 54.72; 115.2 | `Res!C154:D162` |
| Robertson | 66.18; 41.5 | `Res!C174:D182` |
| MacLennan | 61.2; 46.6; 0.0641; 9807 | `Res!C196:D204` |
| Aberdeen demersal | 0.00624; 0.00475; 0.0641 | `Res!C214:D222` |
| Aberdeen pelagic | 0.00868; 0.00475 | `Res!C237:D245` |
| Fridman | 1.8; 2; 0.01 | `Res!D258:E266` |
| Dickson | 1/125; 6.6; 10.76 ft²/m² | `Res!E282:F290` |

## Excel ↔ `trawlkit` equivalence

| Cell(s) | Content | Function |
|---|---|---|
| `Res!E4:E6`, `I25:I26`, … | Inputs | `trawlkit.drag.DragInputs` |
| `Res!D11` | Tauti–Nomura–Shu | `trawlkit.drag.tauti_nomura_shu` |
| `Res!D30`, `L30` | Tauti | `trawlkit.drag.tauti_rope` |
| `Res!D74`, `C91` | Koyama | `koyama_1974`, `koyama_1984` |
| `Res!D113`, `D117` | Hamuro | `hamuro_sin_alpha`, `hamuro` |
| `Res!D132` | Nomura (pull) | `trawlkit.drag.nomura` |
| `Res!C154`, `C174`, `C196` | Reid, Robertson, MacLennan | `reid`, `robertson`, `maclennan` |
| `Res!C214`, `C237` | Aberdeen | `aberdeen_demersal`, `aberdeen_pelagic` |
| `Res!D258`, `E282` | Fridman, Dickson | `fridman`, `dickson` |
| `Res!A298:S326`, `A394:S422` | Summary in t and kgf | `trawlkit.drag.drag_table`, `DragTable.kgf` |
| `Res!R302:R325`, `C326` | Averages | `trawlkit.drag.average`, `method_average` |
| `Res!N302:N310` | Design $R_N$ | `DragTable.design_rn`, `DesignResult.drag.rn` |

## Assumptions and limits

* **Hamuro with the sine of degrees** (`hamuro_sin_degrees`, `Res!D113`). The sheet calculates
  `ABS(SIN(DEGREES(α)))`: it converts 10.63 to “degrees” (609.3) and evaluates the sine in radians.
  By pure chance the result (0.1891) is close to the correct $\sin 10.63° = 0.1845$ (+2.5 %).
  In addition, the modified variant uses the $d/l$ of the standard one (`hamuro_mod_uses_std_dl`).
* **Reid with a fixed denominator** (`reid_fixed_denominator`, `Res!C154:C162`). The denominator
  always uses the speed of the first row (1 kn): $54.72\cdot 1 + 115.2$. The resulting curve is a
  pure parabola that at 5 kn more than doubles the correct formula (6.0 t against 2.5 t).
* **Polluted average** (`drag_average_pollution`, `Res!R302:R310`). The “average” column includes
  the two Nomura columns, which are available pull and not drag, and in the first row also the speed
  in m/s. At 1 kn the workbook's average (554 kgf) doubles the mean of the thirteen drag methods
  (264 kgf). `trawlkit.drag.average` in corrected mode averages only `RN_METHODS`.
* **Carry-over of earlier errata.** All the methods based on $S_s$ inherit the +5.5 % of the standard
  codend (`codend_minor_side_uses_depth`); Tauti (footrope) inherits the footrope truncation, and
  those based on $d/l$ in the modified variant inherit the double counting (see
  {doc}`12_mecanica_red`).
* No method explicitly models the catch in the codend, the contact of the footrope with the seabed or
  the deformation of the net at high speed; all are empirical correlations valid near their database.

## Executable example

The full case in `Compat.EXCEL` mode (needed for Dickson, which uses Fridman's openings) reproduces
the workbook's summary method by method:

```{code-cell} ipython3
from trawlkit import Compat, DesignCase, run, drag
from trawlkit.io import load_doors, load_net, load_vessels

vessels = {v.id: v for v in load_vessels().vessels}

def case(compat):
    return run(DesignCase(
        net=load_net("fao_a3_standard"),
        net_modified=load_net("fao_a3_modified"),
        vessel=vessels["fao_a3_150hp"],
        class_vessels=(vessels["fao_a3_180hp"],),
        door=load_doors().doors[0],
        compat=compat,
    ))

def same(xs, ys):
    return all(math.isclose(a, b, rel_tol=1e-6) for a, b in zip(xs, ys, strict=True))

res_x, res_c = case(Compat.EXCEL), case(Compat.CORRECTED)
tx, tc = res_x.drag.table, res_c.drag.table
G = "resistencia_de_la_red"
for col in drag.SUMMARY_COLUMNS:
    for variant in ("std", "mod"):
        ref = golden(G, f"summary_{col}_{variant}_t")
        got = tx.variant(variant)[col]
        assert same(got, ref), (col, variant)
# workbook average (with the drag_average_pollution erratum) and design RN in kgf
assert same(res_x.drag.average.std, golden(G, "summary_average_std_t"))
assert same(res_x.drag.rn.std, golden(G, "summary_aberdeen_demersal_std_kgf"))
```

```{code-cell} ipython3
:tags: [hide-input]
NAMES = {"tauti_nomura_shu": "Tauti–Nomura–Shu", "tauti_headrope": "Tauti (headrope)",
         "tauti_footrope": "Tauti (footrope)", "koyama_1974": "Koyama 1974",
         "koyama_1984": "Koyama 1984", "hamuro": "Hamuro", "reid": "Reid",
         "robertson": "Robertson", "maclennan": "MacLennan",
         "aberdeen_demersal": "Aberdeen demersal (design)",
         "aberdeen_pelagic": "Aberdeen pelagic", "fridman": "Fridman", "dickson": "Dickson"}
v = np.array(SPEEDS_KN)
kx, kc = tx.kgf, tc.kgf
dyn = golden(G, "summary_dynamit_std_kgf")
rows = []
for col in drag.RN_METHODS:
    x = kx.std[col]
    rows.append([NAMES[col], *(P.fmt(x[SPEEDS_KN.index(s)], 0) for s in (2.0, 3.0, 4.0)),
                 P.fmt(kc.std[col][SPEEDS_KN.index(3.0)], 0)])
rows.append(["*Average (Excel with Nomura; corrected RN only)*",
             *(P.fmt(res_x.drag.average.std[SPEEDS_KN.index(s)] * 1000, 0) for s in (2.0, 3.0, 4.0)),
             P.fmt(res_c.drag.average.std[SPEEDS_KN.index(3.0)] * 1000, 0)])
rows.append(["*DynamiT (simulation)*", *(P.fmt(dyn[SPEEDS_KN.index(s)], 0) for s in (2.0, 3.0, 4.0)), "—"])
P.md_table(["Method (standard net)", "2 kn [kgf]", "3 kn [kgf]", "4 kn [kgf]", "3 kn corrected [kgf]"],
           rows)
```

```{code-cell} ipython3
:tags: [hide-input]
families = [
    ("Dimensions and $d/l$", ["tauti_nomura_shu", "tauti_headrope", "tauti_footrope",
                              "koyama_1974", "koyama_1984"]),
    ("Solid area $S_s$", ["reid", "robertson", "maclennan", "aberdeen_pelagic"]),
    ("Working area and mouth", ["hamuro", "fridman", "dickson"]),
]
fig, axes = plt.subplots(1, 3, figsize=(10.5, 5.4), sharey=True)
design = kx.std["aberdeen_demersal"]
for ax, (title, cols) in zip(axes, families):
    for k, col in enumerate(cols, start=1):
        ls = (0, (4, 2)) if col == "maclennan" else "-"
        ax.plot(v, kx.std[col], color=P.SERIES[k], lw=1.8, ls=ls, label=NAMES[col], zorder=2)
    ax.plot(v, design, color=P.SERIES[0], lw=3, label="Aberdeen demersal (design)", zorder=3)
    ax.set_title(title)
    ax.set_xlabel("Speed [kn]")
    ax.set_xlim(1, 5)
    ax.set_ylim(0, 9000)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), fontsize=8.5, handlelength=1.8)
axes[0].set_ylabel("Net drag $R_N$ [kgf]")
fig.tight_layout()
plt.show()
```

The thirteen methods grouped by the variable they use, with the design $R_N$ (blue, thick line) as a
reference in each panel. MacLennan (dashed line) lies exactly under Aberdeen demersal. The Reid curve
is the workbook's, with the fixed denominator; the corrected one lies below Robertson at high speed.

```{code-cell} ipython3
:tags: [hide-input]
i3 = SPEEDS_KN.index(3.0)
vals = sorted(((kx.std[c][i3], c) for c in drag.RN_METHODS), reverse=False)
fig, ax = plt.subplots(figsize=(9.2, 4.6))
y = np.arange(len(vals))
for k, (val, col) in enumerate(vals):
    is_design = col == "aberdeen_demersal"
    ax.plot([0, val], [k, k], color=P.GRID, lw=1, zorder=1)
    ax.scatter(val, k, s=80 if is_design else 46, color=P.SERIES[0] if is_design else P.BLUE_300,
               edgecolor=P.SURFACE, linewidth=2, zorder=3)
    ax.annotate(P.fmt(val, 0), xy=(val, k), xytext=(8, 0), textcoords="offset points",
                va="center", fontsize=8.5, color=P.INK if is_design else P.INK_2,
                fontweight="bold" if is_design else "normal")
med = float(np.median([val for val, _ in vals]))
for x0, lab, dx, ha in ((dyn[i3], "DynamiT", -4, "right"), (med, "median", 4, "left")):
    ax.axvline(x0, color=P.INK_2, lw=1, zorder=0)
    ax.annotate(lab, xy=(x0, len(vals) - 0.4), xytext=(dx, 0), textcoords="offset points",
                fontsize=8.5, color=P.INK_2, va="center", ha=ha)
ax.set_yticks(y, [NAMES[c] for _, c in vals])
ax.set_xlim(0, 3600)
ax.set_ylim(-0.7, len(vals) - 0.1)
ax.set_xlabel("$R_N$ at 3 kn, standard net [kgf]")
ax.grid(axis="y", visible=False)
fig.tight_layout()
plt.show()
```

At the design speed (3 kn) the methods range from 510 kgf (Dickson) to 3150 kgf (Aberdeen pelagic), a
factor of 6. If those outside their domain are set aside —Dickson, Hamuro (flat panel, no codend),
Aberdeen pelagic and Reid (pelagic nets)—, the spread narrows to 1040–2240 kgf, a factor of 2, which
is the honest uncertainty of an empirical drag estimate. The design $R_N$ (1680 kgf) lies at the
centre of that spread, somewhat above its median (1545 kgf), and 26 % above the DynamiT simulation
(1331 kgf).

## Exercises

From the bank of the teaching mode, with the book's data. In the app, the “UTN Classroom” mode
generates them with other data and marks them ({doc}`38_docentes`).

```{code-cell} ipython3
:tags: [remove-input]
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path.cwd().parent))
import _exercises
_exercises.section("14_resistencia")
```
