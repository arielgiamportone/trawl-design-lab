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

# Validation with hake trawls

```{code-cell} ipython3
:tags: [remove-cell]
import sys, pathlib
DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English
import numpy as np
import matplotlib.pyplot as plt
import _plots_v as V
import _hake as H
from trawlkit import fieldcheck as F
from trawlkit.io import load_net
from trawlkit.netcheck import check
V.setup_style()
PTS = H.points()  # runs the engine for every haul and every simulation (≈ 30 s)
```

## Purpose

{doc}`32_validacion_dynamit` compares the engine with a simulation of the A-3 net and
{doc}`26_aparejos_dobles_y_vara` with the simulations of INIDEP's shrimp outrigger nets. The most
important part was missing: **fish trawls measured at sea**. Argentine hake (*Merluccius hubbsi*)
is the largest bottom-trawl fishery in Argentina and INIDEP publishes, for its survey nets, the
plan, the rigging, DynamiT simulations and hauls measured with telemetry sensors (Simrad TV-80,
PX, Scanmar): door spread (DS), vertical opening (VO) and sometimes wing-end spread (WS), with
the depth, warp length and speed of each haul.

This chapter digitises five nets from those sources and compares the engine, **without changing
its methods**, with 114 measured hauls, one survey mean and six DynamiT simulations. Systematic
deviations are described with numbers and a calibration is proposed that is **not applied**: it is
left for a decision.

## The nets

```{code-cell} ipython3
:tags: [remove-input]
STATUS = {"published": "published", "draft": "draft"}
rows = []
for nid in H.NETS:
    s = load_net(nid)
    err = sum(i.level == "error" for i in check(s))
    d = s.model_extra["design"]
    rows.append([H.SHORT[nid], STATUS[s.status], s.sources[0].key, len(s.panels),
                 V.fmt(s.headrope.length_m, 2), V.fmt(s.footrope.length_m, 2), str(err),
                 d["vessel_id"]])
V.md_table(["Net", "Status", "Source", "Panels", "Headrope [m]", "Footrope [m]", "Errors",
            "Vessel"], rows)
```

- **VA-35.5/45 as designed** {cite:p}`roth2017angelescu`: a four-panel PE net designed by INIDEP for
  the BIPO Víctor Angelescu (IAT 101/2017, fig. 2, a vector plan with mesh sizes, twine Ø, meshes
  and cuts). It closes by stretched length and is published. DynamiT at 4 knots, 100 m and 500 m
  of warp with Morgère SPF08 doors of 4.5 m² and 1200 kg (CL 1.00; CD 0.58), 50 m bridles and 50 m
  sweeps.
- **VA-35.5/45 as built** {cite:p}`bartozzetti2018iat151`: the same net as it was made (IAT
  151/2018, fig. 1): the wing tips, the side panel, the lower panel (Ø4 mm) and the codend (double
  twine) change. The mesh-size column of the lower panel is not printed (the upper panel's are
  assumed). Rigging: 50/48.5 m bridles, 100 m sweeps, 90 floats of 200 mm and 380 kg of chain.
  Published. It carries three measured series and the 400 m DynamiT simulation of
  {cite:t}`roth2025iat026`.
- **Engel 35.5 m** (IAT 101/2017, fig. 1): the hake survey net since 1993 (Holmberg, Oca Balda,
  Angelescu). **Draft**: the plan keeps the number of meshes when the mesh size changes (194 of
  200 mm onto 194 of 160 mm, 160 of 160 mm onto 160 of 120 mm), joins that do not close by
  stretched length (20–25 %), and it gives neither the twine nor the codend (assumed: Ø3 mm nylon
  and the 103 mm, 22 m codend of {cite:t}`pappi2024ic004`). Polyvalent doors of 1200 kg and
  5.58 m² {cite:p}`tringali2012eh0612`. The footrope differs between reports: 41.50 m on the plan,
  50 m in EH 06/12, IC 004/24 and IC 041/25, 40.0 m in IC 019/13 {cite:p}`dato2013global` and
  40.3 m in Tech. Rep. 66 {cite:p}`casarsa2007inftec66`; the plan's is used.
- **Baldino «Beagle I» 46.4 m** {cite:p}`roth2019iat045`: a commercial net of a Mar del Plata
  trawler, redrawn by INIDEP (original, fig. 2) and corrected (fig. 3). Both remain **drafts**: the
  original for the sections that do not join, which the report itself points out (134 meshes of
  140 mm onto 100 of 120 mm, 36 %); the modified one because its side panel goes from 30 to 45
  meshes of 200 mm between two sections (33 %), as the figure reads. The report gives neither the
  vessel, the sweeps nor the area of the 2300 kg Mercury doors (7.5 m² from Polar's table,
  derived).

Every value carries its provenance (transcribed, derived or assumed, with the page and the quote);
what comes from another report on the same net (rigging, measurements) cites that report. The
detailed record is in {doc}`catalogo_fuentes`.

## What is compared and with what tolerance

The engine runs each net's case (`trawlkit.catalog.catalog_case`, corrected mode) with the
conditions of each haul or simulation (`trawlkit.fieldcheck.engine_point`):

- the haul's **depth** and, when the source publishes it, its **warp length**: the case takes it in
  `DesignCase.measured_warp_m` instead of the book's warp/depth table (Mec!E177). It is an input,
  not a new method: with `None` the engine gives the same as before;
- the **door of the series**, with its published area and weight and the published polar (CL and
  CD from IAT 101/2017 and IAT 026/25) or, for the polyvalent doors, the Seafish «Morgère
  Polyvalent Ovale» sheet (assumed);
- the series' **sweeps** when given.

The quantities are the book's for fish trawls, unchanged: **DS** from Fridman's wing spread
averaged between 2 and 4 kn and carried to the doors (the rule of every catalogue case); the
book's **WS** (`Dim!F61`, mean of four rules); Suzuki's **VO** (`Mec!D255`, fixed); and the **total
drag** (`Rem!H118` + two doors) at the haul's speed, interpolated between the calculation speeds.
The declared **tolerances** are:

```{code-cell} ipython3
:tags: [remove-input]
NAMES = {"door_spread_m": "Door spread (DS)", "wing_spread_m": "Wing-end spread (WS)",
         "vertical_opening_m": "Vertical opening (VO)", "drag_kgf": "Total drag (R)"}
V.md_table(["Quantity", "Tolerance"],
           [[NAMES[k], f"± {V.fmt(100 * F.TOLERANCES[k], 0)} %"] for k in NAMES])
```

They are design tolerances: the measured DS and VO vary 8–9 % from haul to haul with the same
gear (coefficients of variation of 0.081 and 0.087 in table 1 of IAT 151/2018) and several doors
have no published polar. Cases outside the tolerance are **in bold** in the tables.

## Against DynamiT

Each cell is «engine / DynamiT (deviation)»:

```{code-cell} ipython3
:tags: [remove-input]
V.md_table(["Net", "Depth, warp, v", "DS [m]", "WS [m]", "VO [m]", "R [kgf]"], H.simulated_rows())
```

- **VA-35.5/45 at 100 m**: WS (+3 %) and VO (+7 %) fall within tolerance; DS is 24 % lower and the
  total drag 26 % higher (the net alone, Aberdeen, gives 6072 kgf: −3 %; the difference is the
  doors and warps the book adds, and DynamiT does not say what its «total drag» includes).
- **VA-35.5/45 at 400 m and 1200 m of warp** (SPF 08.5 doors): the drag matches (−2 %) and WS is
  within (−14 %), but DS is 42 % lower and Suzuki's VO, fixed at 4.21 m, does not drop to the
  simulated 2.4 m. The report shows that with those doors the net over-spreads at depth (WS = 80 %
  of the headrope): exactly the regime where the engine moves least.
- **Baldino 46.4 m**: the engine's DS is 36–39 % lower than DynamiT, but the report does not
  publish the sweeps and the case uses the book's 25 m (`Dim!F65`). The engine's DS is proportional
  to the rigging (wing spread · (LRw + rigging)/LRw): with 100 m of sweeps it would give 194 m,
  DynamiT's. Without the figure it cannot be decided. The book's WS (43 m, 0.93 of the headrope)
  exceeds DynamiT's by 50–63 %: Fridman's wing spread with a 7.5 m² door exceeds the headrope
  (54 m at 4 kn), which the net's geometry does not allow and which {doc}`32_validacion_dynamit`
  already showed above 4 kn. The total drag is 12–13 % lower.

## Against measurements

Per series: mean engine deviation [minimum; maximum] and share of hauls within tolerance. An
asterisk on the warp means the source does not publish it and the engine uses its table:

```{code-cell} ipython3
:tags: [remove-input]
V.md_table(["Net", "Series", "Hauls", "Depth [m]", "Warp [m]", "DS", "WS", "VO"], H.series_rows())
```

```{code-cell} ipython3
---
tags: [remove-input]
mystnb:
  figure:
    caption: |
      Door spread of the VA-35.5/45 against warp length. Dots: measured hauls (IAT 151/18 with
      polyvalent doors; IC 029/18 and IC 012/21 with SPF08) and the DynamiT simulation of IAT
      026/25 (diamond). Crosses: the engine in the same conditions (depth, warp, speed and door of
      each haul).
    name: fig-32m-dp-cable
---
fig, ax = plt.subplots(figsize=(8.6, 5.0))
for k, ser in enumerate(("iat151", "ic012", "ic029")):
    hv = H.hauls(ser)
    w = [p.warp_m for _, p in hv]
    ax.plot(w, [r["door_spread_m"] for r, _ in hv], "o", color=V.SERIES[k], ms=5, alpha=0.85,
            mec=V.SURFACE, mew=0.6, label=H.SERIES[ser][0] + " (measured)")
    ax.plot(w, [p.door_spread_m for _, p in hv], "x", color=V.SERIES[k], ms=5, alpha=0.9,
            label=H.SERIES[ser][0] + " (engine)")
sim = [(r, p) for nid, k, r, p in PTS if k == "simulated" and nid == "inidep_iat151_va355_construida"]
for r, p in sim:
    ax.plot(r["warp_m"], r["door_spread_m"], "D", color=V.INK, ms=7, label="DynamiT, IAT 026/25")
    ax.plot(p.warp_m, p.door_spread_m, "x", color=V.INK, ms=8, mew=2, label="engine, IAT 026/25")
ax.set_xlabel("Warp length [m]")
ax.set_ylabel("Door spread [m]")
ax.set_ylim(bottom=0)
ax.legend(fontsize=8, ncol=2, loc="lower right")
fig.tight_layout()
plt.show()
```

### The Engel net, haul by haul

Hauls 17–28 of the VA-05/2024 cruise {cite:p}`rubio2024calibracion` are the only ones with WS
measured by wing-end sensors, at 21–24 m and at 105–117 m, with SPF 08.5 doors of 4.8 m² (each
cell: engine / measured):

```{code-cell} ipython3
:tags: [remove-input]
V.md_table(["Haul", "Depth [m]", "Warp [m]", "v [kn]", "DS [m]", "WS [m]", "VO [m]"],
           H.haul_rows("ic016"))
```

The book's WS stays within ±20 % in eight of the nine hauls with wing sensors (−5 % to +13 %).
Haul 18 gives +20 %: it is the haul for which the report notes that «the wing-end spread averaged
15 m and by the plan it should be 21 m» and changes the door shackling (p. 12). DS shows the same pattern as
the VA net: the engine overestimates it with little warp (+23 % to +47 % with 104–160 m, although
in hauls 17–19 the door was shackled for the «lowest spreading force», pp. 11–12) and
underestimates it with 351–403 m (−12 % to −16 %).

## Systematic deviations

**1. Door spread grows with warp about half as fast as measured.** With each haul's depth, warp
and door, the slope of the engine's DS against warp is a fraction of the measured one in the three
series with published warp:

```{code-cell} ipython3
:tags: [remove-input]
V.md_table(["Net", "Series", "Hauls", "dDS/dwarp measured", "dDS/dwarp engine",
            "n measured (DS ∝ warpⁿ)", "n engine", "measured / engine"], H.warp_fit_rows())
FITS = H.warp_fits()
DN = float(np.mean([f["exp_measured"] - f["exp_engine"] for f in FITS]))
print(f"mean Δn = {DN:.2f}")
```

In Fridman's wing spread the warp enters above and below the fraction
(`2·Lsh·LRw·Edy / (Lsh + Lnc·(1 + Edx))`), so with long warps DS hardly changes. At sea DS keeps
growing: 75 → 103 m between 180 and 450 m of warp (IAT 151/18), 129 → 158 m between 500 and 930 m
(IC 029/18) and 162 m at 1200 m in DynamiT (IAT 026/25). Hence the engine falls short with long
warps (−33 % in IC 029/18, −42 % against IAT 026/25) and overshoots with short ones (Engel at
21 m: up to +47 %).

**2. The level of DS depends on the door, and the polar of the polyvalent doors is not
published.** With the SPF08 doors of published area (IC 012/21, 240–470 m of warp) the mean
deviation is nil and all 40 hauls fall within ±20 %. With the 1200–1260 kg polyvalent doors (area
of 5.58 m² and Morgère Polyvalent Ovale polar assumed) the engine overestimates: +26 % in IAT
151/18, +39 % in Tech. Rep. 66 and +51 % against the mean of IC 041/25 (the last two without
published warp). A CL of 1.18 at 32° is more than those doors seem to give at sea.

**3. Suzuki's vertical opening is fixed.** It is a fraction of the net's circumference: 4.21 m on
the as-built VA and 3.76 m on the Engel, with no speed, floats or depth. What is measured on the VA
drops from 4.9 m (35 m depth) to 2.3 m (125–135 m): +14 % on average in IAT 151/18 (98 % of hauls
within ±30 %), +38 % in IC 012/21 and +62 % in IC 029/18. On the Engel, with twice the floatation
per metre of headrope, the engine falls short (−13 % with sensors, −40 % with the 2000 net sonar).
The book's Fridman VO, which does depend on speed, gives 7–10 m and is no alternative.

**4. The book's WS is right on the Engel with sensors and overshoots on the large net.** +5 % on
average in IC 016/24 (eight of nine hauls within ±20 %) and +3 % against DynamiT on the VA at
100 m; +61 % against the sonar of Tech. Rep. 66, where DS is also +39 % because of the assumed
door; +50 to +63 % on the 46.4 m net, where Fridman's wing spread exceeds the headrope.

**5. Drag.** There are only simulations: +26 % (VA, 100 m), −2 % (VA, 400 m) and −12 to −13 %
(Baldino). No measured warp tension was published for these nets.

## Proposed calibration (not applied)

The engine was not changed: the book's methods and the golden values stay as they are. For the user
to decide, the calibration these data suggest is:

1. **Sensitivity of DS to warp**, only in corrected mode and for fish trawls:
   $DS_{cal} = DS_{engine} \cdot (L_s / L_{s,ref})^{\Delta n}$, with $L_{s,ref}$ the book's warp for
   the case depth and $\Delta n$ the difference of exponents in the table above (0.10 to 0.37
   depending on the series; the mean is printed above). With the table's warp the factor is 1 and
   the design case does not change; only the response to a different warp changes.
2. **Polyvalent doors**: an effective CL lower than the Seafish sheet's at 32°, fitted to the 52
   hauls of IAT 151/18 (with the sheet, the measured value is 0.80 times the engine's), or
   publishing the polar INIDEP uses. Meanwhile the area (5.58 m²) and the polar remain assumptions.
3. **VO**: no rule of the book reproduces the drop with depth; a correction for floatation (the
   floats of the Engel and the VA) needs more series than this chapter's.

## Limitations

- The measurements do not give each haul's speed in IAT 151/18 (the 3.8 kn mean is used), nor the
  warp in Tech. Rep. 66 and IC 041/25 (the book's table is used), nor warp tension in any case.
- INIDEP's polyvalent doors have no published area or polar for every cruise; the SPF doors have
  CL and CD published for one angle, assumed constant.
- The hauls of IC 012/21 carry selectivity devices (square mesh, T90, grid) and those of IC 016/24
  change the door shackling between hauls.
- The Engel and both Baldino nets are drafts: the engine computes them, but their result depends on
  the readings and assumptions recorded.
