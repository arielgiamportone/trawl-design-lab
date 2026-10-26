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

# Power available for trawling

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

Before drawing a single panel one has to know **how much force the vessel can exert** at fishing
speed. That force, the available pull $F_T$ (kgf), is the ceiling of the whole design: the drag of
the net, the otter boards, the floats and the warps must stay below it within the window of working
speeds. It is the first stage of the chain (see {doc}`motor`) and it feeds the otter board drag (ROB
as a fraction of $F_T$), Fridman's buoyancy and the speed window ({doc}`19_ventana_velocidad`).

The original workbook estimates $F_T$ by five independent routes —Fridman, Prado and Dremière,
Koyama, Nomura and Hamuro— for the two vessels of the class (150 and 180 BHP). They are not five
measurements of the same thing: each author starts from a different physical hypothesis, and
understanding that hypothesis is what allows one to choose, and to distrust, with judgement.

## Theory

### Distribution of the engine's energy (Fridman)

Fridman {cite:p}`fridman1986` proposes a rough but instructive balance: of the engine's energy, about
one third is lost before reaching the propeller (gearbox, auxiliaries), so that

$$
\mathrm{HP_{nom}} = \mathrm{BHP}\,(1 + 0.33)
$$ (eq-pot-nominal)

and of the power that reaches the propeller (BHP) only one third becomes useful pull on the net:

$$
\mathrm{HP_{tiro}} = 0.33\,\mathrm{BHP}.
$$ (eq-pot-tiro)

The rest is shared between propeller rotation (35 %), wave making (27 %), hull friction (18 %), wake
and turbulence (17 %) and air resistance (3 %). The total demand that the vessel must cover is

$$
P_{\text{total}} = R_N + 2R_W + 2R_{OB} + R_H ,
$$ (eq-pot-demanda)

with $R_N$ the net drag, $R_W$ that of each warp, $R_{OB}$ that of each otter board and $R_H$ that
of the hull.

### Fridman's available pull

Fridman's empirical formula relates the pull to the power at the propeller $P$ [HP] and the speed
$v$ [kn]:

$$
F_T = P\,(K_F - 0.7\,v)
$$ (eq-fridman-ft)

$K_F$ [kgf/HP] is the bollard pull per horsepower: 10 for a fixed pitch propeller (PF, Spanish *paso fijo*) and 15 for a
controllable pitch propeller with nozzle (PV+T, *paso variable con tobera*). The slope $0.7\,P$ expresses that, as it moves
forward, the propeller loses thrust because its effective angle of attack decreases. It is the only
one of the five formulas with a **finite bollard pull** ($F_T(0) = K_F P$): for 150 BHP and PF,
1,500 kgf.

### Prado and Dremière (FAO)

The *Fisherman's Workbook* {cite:p}`prado1990` chains four rules of thumb. The bollard pull is

$$
BP = \mathrm{BHP}\cdot 0.9\cdot \frac{p}{100}\ \ [\mathrm{t}],
$$ (eq-prado-bp)

with $p$ = 1.10 (PF), 1.20 (PF+T), 1.25 (PV) and 1.40 (PV+T), that is, between 9.9 and 12.6 kgf per
BHP. The workbook averages it with a second estimate, $BP_K = K\cdot\mathrm{BHP}/1000$, with $K$
tabulated by power and propeller. From the average bollard pull an apparent nominal power is
obtained and, from it, the power available for trawling:

$$
\mathrm{APN} = 0.09\,BP_{\text{prom}}, \qquad P_a = 0.75\,K\,\mathrm{APN},
$$ (eq-prado-apn)

with $K$ = 0.20 (fixed pitch, high RPM) to 0.30 (controllable pitch with nozzle). Finally the pull
when fishing (*bollard pull when fishing*) is

$$
BPF = \frac{150\,P_a}{v}\quad [\mathrm{kgf}],\ v\ \text{in kn},
$$ (eq-prado-bpf)

where 150 is a conversion constant ($\approx 75/0.5144$ kgf·kn per HP), **not** the BHP.

### Koyama, Nomura and Hamuro: constant power

The three Japanese schools start from an effective towing power $P_e$ [HP] and assume that it stays
constant, so that the pull is power over speed:

$$
F = \frac{75\,P_e}{v}\quad [\mathrm{kgf}],\ v\ \text{in m/s}.
$$ (eq-potencia-constante)

What changes is how $P_e$ is estimated:

* **Koyama** {cite:p}`koyama1974`: $P_e = \mathrm{EHP} = K\cdot 0.6\,\mathrm{BHP}$, with 0.6 the engine
  load while fishing and $K$ = 0.15 for vessels below 600 BHP (0.18 for 1200–1500 BHP).
* **Nomura** {cite:p}`nomura1981`: $P_e = 0.8\,K_1K_2K_3\,\mathrm{NHP}$, with $K_1 = 0.85$ (engine
  use), $K_2 = 0.85$ (sea state), $K_3$ = 0.17–0.29 (propulsive efficiency according to the size of
  the trawler; the workbook uses 0.17) and 0.8 the fraction of the demand attributed to the net.
* **Hamuro** {cite:p}`hamuro`: $P_e = P_s = K_1K_2K_3\,\mathrm{NHP}$, with $K_1 = 0.825$, $K_2 = 0.85$ and
  $K_3$ between 0.20 (PF, high RPM) and 0.30 (PV+T, high RPM).

The form {eq}`eq-potencia-constante` diverges as $v \to 0$: at 1 kn it predicts pulls of 2 to 4 t for
a vessel whose bollard pull is 1.5–1.9 t, which is physically impossible. These formulas only make
sense in the trawling range (≈ 2.5–4.5 kn), where the propeller works close to its design point.
That is why, although the workbook averages the five methods, the one that feeds the rest of the
design is Fridman's: it is linear, bounded and conservative at low speed.

## Coefficients

| Coefficient | Value | Unit | Source | Excel cell |
|---|---|---|---|---|
| $K_F$ fixed pitch / PV+T | 10 / 15 | kgf/HP | Fridman | `PotOK!D10`, `F10` |
| Fridman slope | 0.7 | kgf/(HP·kn) | Fridman | `PotOK!E10` |
| Fractions of BHP (nominal, pull) | 0.33 / 0.33 | — | Fridman | `Pot!C24`, `C26` |
| Losses (propeller, waves, friction, wake, air) | 0.35 / 0.27 / 0.18 / 0.17 / 0.03 | — | Fridman | `Pot!C27:C31` |
| Bollard pull $p$ (PF, PF+T, PV, PV+T) | 1.10 / 1.20 / 1.25 / 1.40 | % | Prado | `PotOK!A49:A55` |
| Bollard pull $K$ (150 HP, PF) | 11.23 | t/1000 HP | Prado | `PotOK!K52:L55` |
| APN / available fraction | 0.09 / 0.75 | — | Prado | `PotOK!B73`, `K68` |
| Trawling $K$ | 0.20–0.30 | — | Prado | `PotOK!K68:L77` |
| Koyama $K$ / load | 0.15 / 0.6 | — | Koyama | `PotOK!M165`, `C169` |
| Nomura $K_1$, $K_2$, $K_3$, net fraction | 0.85 / 0.85 / 0.17 / 0.8 | — | Nomura | `PotOK!L205:L213` |
| Hamuro $K_1$, $K_2$, $K_3$ | 0.825 / 0.85 / 0.20–0.30 | — | Hamuro | `PotOK!C254`, `F257:L258` |

The values are in `src/trawlkit/data/reference/power_coefficients.yaml`, generated from the workbook.

## Excel ↔ `trawlkit` equivalence

| Cell(s) | Content | Function |
|---|---|---|
| `Pot!C24:E31` | Energy distribution | `trawlkit.vessel.power_budget` |
| `Pot!H27`, `H38` | Admiralty speed | `trawlkit.vessel.admiralty_speed_kn` |
| `PotOK!E10:G30` | Fridman's $F_T$ | `trawlkit.power.fridman_towing_force_kgf` |
| `PotOK!B60:E63` | Bollard pull | `trawlkit.power.bollard_pull_kgf` |
| `PotOK!I59:L62`, `G58:G68` | BP via $K$ and average | `bollard_pull_k_t`, `bollard_pull_avg_kgf` |
| `PotOK!B73:C76` | APN | `trawlkit.power.apparent_nominal_power_hp` |
| `PotOK!K68:L77` | Trawling power | `trawlkit.power.trawling_power_hp` |
| `PotOK!C88:L111`, `C123:F131` | BPF and averages | `bollard_pull_fishing_kgf`, `bollard_pull_fishing_avg_kgf` |
| `PotOK!K171:L179` | Koyama | `trawlkit.power.koyama_pull_series_kgf` |
| `PotOK!E216:F224` | Nomura | `trawlkit.power.nomura_pull_series_kgf` |
| `PotOK!F259:L266`, `E272:H280` | Hamuro | `hamuro_ps_table`, `hamuro_pull_series_kgf` |
| `PotOK!L11:O19` | Fridman summary (PF and PV+T) | `trawlkit.power.summary` |
| — | The five curves for one vessel | `trawlkit.power.power_curves` |

## Assumptions and limits

* **Speed in m/s.** Koyama and Nomura convert knots with **0.514** (`PotOK!H171`); Hamuro and the rest
  of the workbook with **0.5144** (`PotOK!B272`). `trawlkit` reproduces both factors; the difference
  is 0.08 %.
* **NHP = BHP.** Nomura and Hamuro call for the nominal power, but the workbook takes
  `MID("150 HP",1,3)`, that is the BHP (150/180), and not the nominal HP of {eq}`eq-pot-nominal`
  (199.5/239.4). Using the nominal values would raise these two curves by 33 %.
* **The 150 in BPF** is a units constant and is also used for the 180 HP vessel.
* **Static summary tables.** The "worst/best case" summaries (`PotOK!A295:I370`) are pasted numbers
  that do not always match the formulas (Koyama pasted as 2,382 kgf at 1 kn against 1,970 kgf from
  the formula), and their "Nomura" column links to Hamuro in three of the four tables (erratum
  `nomura_column_links_hamuro`, see {doc}`erratas`). `trawlkit` actually computes Nomura.
* **Domain.** The constant-power formulas only hold in the trawling range; none of them considers the
  state of the propeller, the draught or hull fouling. The ranges of $K_3$ given by Nomura and Hamuro
  give an honest idea of the uncertainty: ±20 % on $F_T$.

## Executable example

Energy distribution of the two vessels of the class:

```{code-cell} ipython3
from trawlkit.vessel import power_budget

G0 = "potenc_disponible_para_arrastre"
rows = []
for bhp in (150, 180):
    b = power_budget(bhp)
    ref = golden(G0, f"towing_hp_{bhp}")
    assert math.isclose(b.towing_hp, ref, rel_tol=1e-6)
    hp = (b.nominal_hp, b.towing_hp, b.propeller_loss_hp, b.wave_loss_hp,
          b.friction_loss_hp, b.wake_loss_hp, b.air_loss_hp)
    rows.append([f"{bhp:.0f}", *(P.fmt(x, 1) for x in hp)])
P.md_table(["BHP", "Nominal HP", "Net pull", "Propeller", "Waves",
            "Friction", "Wake", "Air"], rows)
```

The five pull curves with the **fixed pitch** configuration that the workbook uses as worst case
(Prado: average of the six fixed pitch rows, `C123`; Hamuro: PF at low RPM, `E272`), checked against
the Excel values:

```{code-cell} ipython3
from trawlkit import power
from trawlkit.io.schema import PropellerType

v = np.array(SPEEDS_KN)
G = "potencia_disponible_arrastre_ok"

PF = PropellerType.FIXED_PITCH
K3_PF_LOW_RPM = power.hamuro_k3(PF, high_rpm=False)  # 0.265, column E272

def curves(bhp):
    return {
        "Fridman": power.fridman_towing_force_kgf(bhp, v, power.FRIDMAN_KF[PF]),
        "Prado": power.bollard_pull_fishing_avg_kgf(bhp, v, "fixed"),
        "Koyama": power.koyama_pull_series_kgf(bhp, v),
        "Nomura": power.nomura_pull_series_kgf(bhp, v),
        "Hamuro": power.hamuro_pull_series_kgf(bhp, v, k3=K3_PF_LOW_RPM),
    }

ft = {bhp: curves(bhp) for bhp in (150, 180)}
keys = {"Fridman": "fridman_ft_fixed_pitch_{}_kgf",
        "Prado": "prado_bpf_avg_fixed_{}_kgf",
        "Koyama": "koyama_pull_{}_kgf",
        "Nomura": "nomura_pull_{}_kgf",
        "Hamuro": "hamuro_pull_fixed_{}_kgf"}
for bhp, c in ft.items():
    for name, key in keys.items():
        ref = golden(G, key.format(bhp))
        ok = all(math.isclose(a, b, rel_tol=1e-6) for a, b in zip(c[name], ref))
        assert ok, (bhp, name)

i3 = SPEEDS_KN.index(3.0)
P.md_table(["Method", "150 BHP at 3 kn [kgf]", "180 BHP at 3 kn [kgf]"],
           [[n, P.fmt(ft[150][n][i3], 0), P.fmt(ft[180][n][i3], 0)] for n in keys])
```

```{code-cell} ipython3
:tags: [hide-input]
from trawlkit.drag import aberdeen_demersal

rn = aberdeen_demersal(golden("mecanica_de_la_red", "solid_surface_std_m2"), v) * 1000
order = ["Fridman", "Prado", "Koyama", "Nomura", "Hamuro"]
fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0), sharey=True)
for ax, bhp in zip(axes, (150, 180)):
    for k, name in enumerate(order):
        y = ft[bhp][name]
        mk = dict(marker="o", ms=5, mec=P.SURFACE, mew=1.5) if name == "Hamuro" else {}
        ax.plot(v, y, color=P.SERIES[k], label=name, zorder=3, **mk)
    ax.plot(v, rn, color=P.INK_2, lw=1.2, label="Design RN (Aberdeen)", zorder=2)
    bp = power.bollard_pull_kgf(bhp, PF)
    ax.axhline(bp, color=P.MUTED, lw=1, zorder=1)
    ax.annotate(f"bollard pull PF = {P.fmt(bp, 0)} kgf", xy=(5.0, bp), xytext=(0, 4),
                textcoords="offset points", ha="right", fontsize=8, color=P.INK_2)
    ax.set_title(f"{bhp} BHP, fixed pitch propeller")
    ax.set_xlabel("Towing speed [kn]")
    ax.set_xlim(1, 5)
    ax.set_ylim(0, 5200)
    ax.set_xticks(np.arange(1, 5.5, 0.5))
axes[0].set_ylabel("Available pull $F_T$ [kgf]")
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", ncol=6, bbox_to_anchor=(0.5, -0.02))
fig.tight_layout(rect=(0, 0.07, 1, 1))
plt.show()
```

The figure sums up the theoretical discussion. Fridman (blue) is a straight line bounded by the
bollard pull; the other four are hyperbolas that exceed it below 2 kn. In the fishing range
(2.5–3.5 kn) the methods spread by almost 2:1: Prado and Hamuro are the most optimistic, Koyama and
Nomura the most cautious, and Fridman sits in the middle at 3 kn. The grey line is the design drag of
the net alone ({doc}`14_resistencia`). With a fixed pitch propeller, the net alone already equals
Fridman's pull at around 2.5 kn on the 150 BHP vessel and around 2.7 kn on the 180 BHP one; with
controllable pitch and nozzle ($K_F = 15$) those crossings rise to 3.25 and 3.6 kn. According to
Koyama or Nomura the crossing drops to 2.1–2.3 kn. The real margin, once otter boards, warps and
floats are added, is analysed in {doc}`19_ventana_velocidad`.

## Exercises

From the teaching-mode bank, with the data of the book. In the app, the “UTN Classroom” mode
generates them with other data and marks them ({doc}`38_docentes`).

```{code-cell} ipython3
:tags: [remove-input]
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path.cwd().parent))
import _exercises
_exercises.section("10_potencia")
```
