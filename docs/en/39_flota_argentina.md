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

# The Argentine fleet

```{code-cell} ipython3
:tags: [remove-cell]
import pathlib
import sys

DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English

import numpy as np
import matplotlib.pyplot as plt
import _plots_t1 as P
from trawlkit import propulsion as pr
from trawlkit.api import service
from trawlkit.i18n import tr
from trawlkit.model import run
from trawlkit.power import bollard_pull_t

P.setup_style()
TYPES = {
    "rada_ria": "Inshore (rada/ría)",
    "costero": "Coastal",
    "fresquero": "Fresh-fish trawler",
    "congelador": "Freezer trawler",
    "tangonero": "Outrigger shrimp trawler",
    "investigacion": "Research",
    None: "Workbook (A-3)",
}
VESSELS = service.vessel_list()
```

## Purpose

The original workbook designs the net for two inshore (*rada o ría*) vessels of 150 and 180 BHP.
This chapter describes the vessel catalogue that Phase 19.4 added to `trawlkit`: **vessel types** of
the Argentine fleet built from the mean values published by INIDEP and FAO, and **vessels with
published particulars** (INIDEP's research vessels and two from secondary sources). Every value
cites its table and page; computed values carry the formula; what the source does not give is left
empty and marked «A VERIFICAR» (to be verified). No dimension is invented: when a case needs a beam
or a depth that the source does not publish, the engine scales it from the A-3 vessel and says so.

## The fleet by segment

The official classification {cite:p}`fao2005argentina` separates the **coastal** fleet (*rada o ría*
and coastal) from the **offshore** fleet (fresh-fish and freezer trawlers, outrigger shrimp trawlers,
surimi and scallop vessels; longliners; squid jiggers). Lengths and vessels registered in 2005
(transcribed from PDF pp. 14–16):

| Segment | Length | Registered 2005 |
|---|---|---|
| Rada o ría (inshore) | «average length of 10 to 15 metres» | 144 |
| Coastal | «between 15 and 25 metres long» | 120 |
| Offshore fresh-fish trawlers | «25 to 63 metres long» | 140 |
| Freezer trawlers | «between 30 and 100 m (most often between 60 and 80 m)» | 62 |
| Outrigger shrimp trawlers (tangoneros) | «between 26 and 39 metres long» | 76 |
| Surimi vessels | «more than 100 m long» | 3 |

The powers come from INIDEP's 2001 papers: the 1998 industrial fleet {cite:p}`bertolotti2001flota`,
the fresh-fish trawler strata {cite:p}`bertolotti2001fresqueros` and freezer trawler strata
{cite:p}`bertolotti2001congeladores`, the coastal fleet {cite:p}`lasta2001costera` and Mar del
Plata's small-scale fleet {cite:p}`errazti2001costera`. In all of them power correlates strongly
with length ($r$ = 0.88 for fresh-fish trawlers and 0.89 for freezer trawlers). Outrigger shrimp
trawlers are bounded by CFP Res. 7/2018 {cite:p}`cfp2018res7`: up to 40 m tonnage length and
2000 hp, with doors and net vertical opening of up to 150 cm.

In Tierra del Fuego, this book's case, 5 to 7 coastal vessels per year operate from Ushuaia, 9 to
24 m long and 70 to 600 HP, in the Beagle Channel (Lasta et al. 2001, p. 105). Stratum I of Mar del
Plata's small-scale fleet (13 m, 134 ± 92 HP) is the closest published analogue of the A-3's
150–180 BHP vessels.

## The `trawlkit` catalogue

The vessels live in `src/trawlkit/data/vessels/*.yaml` (the two A-3 vessels stay in
`data/vessels.yaml`, first and unchanged) and are requested with `GET /catalog/vessels`, which
filters by type (`?type=tangonero`), region and status. The **types** (`typical: true`) are stratum
means, not real vessels; those marked *provisional* come from an encyclopedia or the press.

```{code-cell} ipython3
rows = []
for v in VESSELS:
    src = v.sources[0].key if v.sources else "giamportone2024"
    status = "provisional" if v.status == "draft" else ("typical" if v.typical else "published")
    rows.append([
        v.id,
        TYPES[v.vessel_type.value if v.vessel_type else None],
        P.fmt(v.bhp, 0),
        P.fmt(v.length_m, 2) if v.length_m else "—",
        P.fmt(v.beam_m, 2) if v.beam_m else "A VERIFICAR",
        status,
        src,
    ])
P.md_table(["Id", "Type", "BHP", "Length [m]", "Beam [m]", "Status", "Source"], rows)
```

The provenance of each value is in the file itself. For example, that of the typical outrigger
trawler (the notes stay in Spanish, as in the source data):

```{code-cell} ipython3
tang = next(v for v in VESSELS if v.id == "ar_tangonero_1998")
P.md_table(
    ["Field", "Kind", "Document", "Page", "Note"],
    [[k, p.kind.value, p.document or "—", p.page or "—", p.note or ""]
     for k, p in tang.provenance.items()],
)
```

## Vessels with published particulars

* **RV Dr. Eduardo L. Holmberg** (INIDEP, Hitachi Zosen 1980): 61.95 m, 11 m beam, 2100 hp
  {cite:p}`giorgini2023poder`; Yanmar engine of 2100 PS at 680 rpm, four-blade controllable-pitch
  propeller and Kawasaki winch with two drums of 2000 m of 24 mm warp {cite:p}`inidepholmberg`.
* **RV Capitán Cánepa** (decommissioned): 39.17 m, 7.35 m, 760 hp {cite:p}`giorgini2023poder`.
* **RV Víctor Angelescu** (2017): 52.8 m, 12.8 × 5.0 m, 4.8 m draft, two 1050 kW electric motors
  {cite:p}`inidepangelescu`.
* **RV Mar Argentino** (2020): 36.0 m, 8.5 × 4.0 m, 3.40 m draft, 253 GRT, 550 kW
  {cite:p}`inidepmarargentino`.
* **RV Capitán Oca Balda** (provisional): dimensions from an encyclopedia without references
  {cite:p}`wikipediaocabalda`; build data from {cite:p}`argentinaocabalda`.
* **FV San Severo** (provisional): Contessi multipurpose outrigger trawler, 20.95 × 7.50 × 3.30 m and
  926 HP according to the press {cite:p}`pescare2026sansevero,argenports2026sansevero`.

Powers in kW are converted to metric hp (0.7355 kW/hp) and recorded as *derived*.

## What was not found

* **Propeller diameter, pitch and rpm, and measured bollard pull**: no Argentine fishing vessel has
  them published. That is why no catalogue vessel uses the propeller-based pull yet
  ({doc}`10_potencia`).
* **Distribution of propeller types** (fixed or controllable pitch, with or without nozzle) by
  segment: not found. The types keep the schema default (fixed pitch), marked as an assumption.
* **Beam, depth and draft by segment**: INIDEP's tables give length, GRT, HP, hold and crew, not hull
  form.
* **Fridman's KF for FP+N and CP**: the Holmberg and the Oca Balda, controllable pitch with no nozzle
  data, require `fridman_kf` to compute a case.

## Propeller-based pull on the fleet types

With no published diameters, the propeller model can be used backwards: what diameter would make
Wärtsilä's formula {eq}`eq-wartsila` give the 10–12 kgf/BHP that the *Fisherman's Workbook*
{cite:p}`prado1990` gives for a fixed propeller? The inverse is
$D = (BP\cdot 9.81/k_1)^{3/2}/P_D$, with $P_D = 0.9\,\mathrm{BHP}$ (all *derived*):

```{code-cell} ipython3
rows = []
for v in VESSELS:
    if not v.typical:
        continue
    pd = pr.delivered_power_kw(v.bhp)
    d10 = pr.diameter_for_bollard_pull_m(10 * v.bhp / 1000, pd)
    d12 = pr.diameter_for_bollard_pull_m(12 * v.bhp / 1000, pd)
    rows.append([
        v.name,
        P.fmt(v.bhp, 0),
        P.fmt(pd, 0),
        f"{P.fmt(10 * v.bhp / 1000, 1)}–{P.fmt(12 * v.bhp / 1000, 1)}",
        P.fmt(bollard_pull_t(v.bhp, v.propeller), 1),
        f"{P.fmt(d10, 2)}–{P.fmt(d12, 2)}",
    ])
P.md_table(
    ["Type", "BHP", "P_D [kW]", "Workbook BP [t]", "Workbook-rule BP (Zahalka) [t]",
     "Equivalent D [m]"],
    rows,
)
```

```{code-cell} ipython3
:tags: [hide-input]
d = np.linspace(0.4, 4.0, 200)
fig, ax = plt.subplots(figsize=(8.6, 4.2))
pick = ["ar_rada_ria_mdp_e1", "ar_fresquero_e1", "ar_tangonero_1998", "ar_congelador_e2"]
for k, vid in enumerate(pick):
    v = next(x for x in VESSELS if x.id == vid)
    pd = pr.delivered_power_kw(v.bhp)
    kgf = [1000 * pr.bollard_pull_wartsila_t(x, pd) / v.bhp for x in d]
    ax.plot(d, kgf, color=P.SERIES[k], label=f"{v.name} ({v.bhp:.0f} BHP)", zorder=3)
ax.axhspan(10, 12, color=P.MUTED, alpha=0.18, zorder=1)
ax.annotate("Workbook, fixed propeller: 10–12 kgf/BHP", xy=(4.0, 11), ha="right", va="center",
            fontsize=8, color=P.INK_2)
ax.axhline(9.9, color=P.MUTED, lw=1, ls="--", zorder=2)
ax.annotate("workbook rule: BHP·0.9·1.10/100 (Zahalka, tugs)", xy=(4.0, 9.9), xytext=(0, -10),
            textcoords="offset points", ha="right", fontsize=8, color=P.INK_2)
ax.set_xlabel("Propeller diameter D [m]")
ax.set_ylabel("Bollard pull per BHP [kgf/BHP]")
ax.set_xlim(0.4, 4.0)
ax.set_ylim(0, 30)
ax.legend(loc="upper left", fontsize=8)
fig.tight_layout()
plt.show()
```

With an open propeller, Wärtsilä's formula reaches the Workbook's 10–12 kgf/BHP with diameters of
0.6–0.8 m on the inshore vessel and 1.7–2.2 m on the typical outrigger trawler. The larger and slower
the propeller, the more pull per horsepower: doubling the diameter raises the pull by 59 %
($2^{2/3}$). FAO FTP 383 {cite:p}`wilson1999` cites a case in which a 50 % larger propeller gave 27 %
more bollard pull. That is the information that the BHP alone does not carry and that the workbook
formula cannot see.

## Computing a case with a catalogue vessel

A fleet type is used like any catalogue vessel. Beam and depth that the source does not give are
scaled from the A-3 vessel with the length ratio and recorded in the notes; with a vessel other than
the A-3's, the door spread comes from Fridman's DPA (`door_spread_rule = "fridman"`), because the
workbook's «per metre» rule is calibrated for the A-3.

```{code-cell} ipython3
case = service.build_case(
    vessel="ar_rada_ria_mdp_e1",
    net_modified="fao_a3_modified",
    params={"door_spread_rule": "fridman"},
)
r = run(case)
print("\n".join(n for n in r.notes if n.startswith("catalog")))
s = r.summary()
P.md_table(
    ["Quantity", "Value"],
    [
        ["Vessel", tr(case.vessel.name)],
        ["BHP", P.fmt(case.vessel.bhp, 2)],
        ["Length × beam × depth [m]",
         f"{P.fmt(case.vessel.length_m, 2)} × {P.fmt(case.vessel.beam_m, 2)} × "
         f"{P.fmt(case.vessel.depth_m, 2)}"],
        ["Maximum speed with the A-3 net [kn]", P.fmt(s["max_speed_kn"], 2)],
    ],
)
```

In the app, the «Vessel» step of guided mode filters the catalogue by type and region, and the
**Use my vessel** box (also in the expert mode case panel) opens a form with the power, length,
beam, depth, propeller type, nozzle, propeller diameter, drum capacity and region. The data are
saved with the case and the project and travel to the API as an inline vessel, always in metric
(imperial units only change what is displayed). With the diameter, the result adds the
propeller-based pull; with the drum capacity, the engine checks that the warp paid out plus the
workbook's reserve fits on each drum and that the winch pull reaches 80 % of the bollard pull
without exceeding 1/3 of the warp's breaking load {cite:p}`prado1990`.

## Assumptions and limits

* The types are **means** of 1997–1998 strata: the fleet has changed since (the 2021 coastal mixed
  fishery report {cite:p}`magyp2021variado` already stratifies by under 19 m, 19–28.25 m and
  28.26–38.95 m). The standard deviations of power are 15 to 70 % of the mean.
* The register's «HP» is taken as BHP. GRT (gross register tonnage) is stored as `gross_tonnage`.
* Beam and depth scaled from the A-3 are a geometric assumption (similar vessels) made to be able to
  compute, not data.
* The propeller-based pull is an optimistic bound (≈ +25 % against Kartha and Roy Choudhury's
  measurement {cite:p}`kartha1966`, see {doc}`10_potencia`) and is only computed with a real
  diameter.
