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

# Outrigger, twin and beam trawls

```{code-cell} ipython3
:tags: [remove-cell]
import dataclasses
import pathlib
import sys

DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English

from IPython.display import SVG, display
import _plots_t1 as P
from trawlkit.catalog import catalog_case
from trawlkit.cost import bill_of_materials
from trawlkit.drawing import rig_plan_svg
from trawlkit.io import load_net
from trawlkit.model import run
from trawlkit.netcheck import check
from trawlkit.rigging import multirig as M
from trawlkit.sim import simulate

P.setup_style()


def f(x, nd=1):
    return P.fmt(float(x), nd)
```

## Purpose

The original workbook computes **one** net towed with its pair of otter boards. Many fisheries do
not work that way. The Argentine shrimp fleet tows **two nets from outrigger booms**
(*tangones*), one on each side, each with its own otter boards (CFP Resolution 7/2018, art. 4:
outrigger trawlers "shall operate with booms carrying shrimp nets" {cite:p}`cfp2018res7`). In the
North Sea and the North Atlantic the **twin rig**, two nets side by side with a centre clump, and
the **beam trawl**, where a rigid beam sets the net opening, are common. This chapter shows how
`trawlkit` computes these three rigs (Phase 19.5), which source each value comes from and where the
limits of the computation lie.

## Three rigs

**Outrigger** (`rig: outrigger`). Two identical nets, one from the tip of each boom. In the Gulf of
Mexico the booms were "usually 24-feet long" and fished at about 20° above the horizontal, with
the towing blocks 10–12 feet above the water; each trawl has "but a single warp with bridle" to
both doors, and one net is set about 25 fathoms further astern than the other so they do not foul
{cite:p}`knake1958`. On the Argentine outrigger trawler the bridle is the **tijera**: in the INIDEP
simulations, 70 m of 22 mm steel wire, with a 24 mm warp and 540 kg flat wooden doors at 3.5 knots
{cite:p}`roth2022ito043`.

**Twin** (`rig: twin`). Two nets side by side towed by two warps: the doors are outside and the
inner wingends join a **clump** or sled in the middle, which has no lift
{cite:p}`bullisfloyd1972,arkley1987ir1310`. Each door spreads one net against the clump. Bullis and
Floyd describe a sled six feet long, 32 inches high aft on an eight-inch steel shoe, and note that
"two 35-foot nets can be spread with a single pair of seven-foot trawl doors; a 70-foot trawl
would require 10- to 12-foot doors". For the clump weight the Seafish gear database gives a **rule
of thumb**: about 1.5 times the weight of one door {cite:p}`seafishtwinrig`. Arkley tested a
125 kg sledge with 6 ft V doors.

**Beam** (`rig: beam`). A beam on two shoes sets the horizontal opening; there are no otter boards.
The drag is that of the net plus the beam, the shoes, the ground gear and the tickler chains.
Wageningen Marine Research measured the dimensions of the Dutch fleet and estimated the drag of
each component {cite:p}`rijnsdorp2020c056`: 12 m beams of Ø0.24 m on vessels above 221 kW and
4.5 m beams of Ø0.15 m on the smaller ones; shoes of 0.063 and 0.054 m² frontal area and 0.70 and
0.60 m height. The beam width grows with engine power following Eigaard et al.
{cite:p}`eigaard2016`, who also note that two beams are usually towed, one from each boom, and that
shrimp beam trawls carry no tickler chains. Verhoest and Maton describe the 8 m Belgian double-rig
shrimp beam trawl, with the booms at about 30° to the horizontal {cite:p}`verhoest1964`.

## How the engine computes them

The workbook stages still compute **one net** with its doors (geometry, dimensions, drag,
flotation, ballast and warps). A new stage, `RigStage` (`result.multirig`), counts the pieces of
each rig and builds the drag of the whole gear:

* **outrigger**: per net, net drag + floats + two doors + one warp + the two bridle legs; the
  vessel tows two;
* **twin**: per net, net drag + floats + one door + one warp + half the clump (drag of a sled of
  frontal area $A$ with $C_D = 1.05$, that of a beam-trawl shoe); the spread of each net is from
  door to clump;
* **beam**: per beam, net drag + beam ($C_D = 1.1$, area $d \cdot L$) + two shoes ($C_D = 1.05$)
  + ground gear and chains (drag per metre of beam from table 9 of C056/20 scaled with $v^2$); no
  doors and no floats (the headline is fixed to the beam).

The demand against the vessel's pull is $n_\text{nets}$ times that of one net plus the seabed
friction (each net's ground gear, the doors, the clump or the shoes). Each warp is sized with what
it tows: one net with outriggers and beams; the whole gear in the twin rig, as the workbook does
with its two warps. With outriggers the **swept width** runs from outer door to outer door: each
net is centred behind the tip of its boom, which is $L\cos\theta$ from the centreline.

The defaults come only from the sources; everything else is a case input:

```{code-cell} ipython3
P.md_table(
    ["Item", "Default", "Source"],
    [
        ["Boom length", f"{f(M.BOOM_LENGTH_M, 2)} m (24 ft)", "Knake et al. 1958, p. 3"],
        ["Boom angle", f"{f(M.BOOM_ANGLE_DEG, 0)}° (beam: {f(M.BEAM_BOOM_ANGLE_DEG, 0)}°)",
         "Knake et al. 1958, p. 5; Verhoest and Maton 1964"],
        ["Bridle", f"{f(M.OUTRIGGER_BRIDLE_M, 0)} m of Ø{f(M.OUTRIGGER_BRIDLE_DIAMETER_MM, 0)} mm",
         "Roth and Rubio 2022 (INIDEP)"],
        ["Twin clump", f"{f(M.CLUMP_DOOR_RATIO, 1)} × one door (rule of thumb)", "Seafish"],
        ["Clump frontal area", f"{f(M.SLED_FRONTAL_M2, 3)} m² (32 × 8 in, assumption)",
         "Bullis and Floyd 1972, p. 27"],
        ["Door area per foot of headline", "70–80 in²/ft (0.148–0.169 m²/m), spread 70–75 %",
         "Watson et al. 1984"],
        ["Beams per vessel", str(M.BEAMS_PER_VESSEL), "Eigaard et al. 2016, p. i29"],
        ["Beam width", "1.4812·kW^0.4578 (shrimp); 0.6601·kW^0.5078 (fish)",
         "Eigaard et al. 2016, table 4"],
        ["Beam, shoes and chains", "by vessel class (≤ 221 kW and > 221 kW)",
         "Rijnsdorp et al. 2020, tables 2, 3, 8 and 9"],
    ],
)
```

The case takes them as parameters (`boom_length_m`, `boom_angle_deg`, `outrigger_bridle_m`,
`clump_weight_kg`, `beam_count`, `beam_length_m`, `beam_ticklers`, `beam_weight_kg`…); in the app,
the **Rig** selector of the case panel and of the guided mode follows the net's rig by default and
the parameters are edited in "Advanced parameters".

## Argentine case: the INIDEP outrigger net

INIDEP evaluated in DynamiT an outrigger net proposed by the company Pesquera Deseado and one of
its own {cite:p}`roth2022ito043`. Its figure 5 (INIDEP net) is in the catalogue as
`inidep_ito043_tangonera_inidep`, digitised with the provenance of every value. It is a **draft**:
the validator flags that the rear Dyneema body (40 meshes of 120 mm in the top panel) joins a codend
of 100 meshes of 60 mm, a seam the plan draws that way but that does not close in stretched
length, and three cut labels that do not give the width change of their panel. The side panels of
the plan do not match the top panel station by station: the engine shares them out by stretched
length.

```{code-cell} ipython3
spec = load_net("inidep_ito043_tangonera_inidep")
P.md_table(
    ["Level", "Code", "Issue"],
    [[i.level, i.code, i.message] for i in check(spec)],
)
```

The net names the vessel and door it is computed with: the fleet's **typical outrigger trawler**
(1998 average, {doc}`39_flota_argentina`), because the report does not publish the length or power
of the F/V *Atlántico 1*, and the generic flat door of the catalogue closest in weight to the
report's 540 kg (510 kg, 2.5 × 1.25 m; the door dimensions are not published). The depth is not in
the report either: 30 m by family. All of it is in the case notes.

```{code-cell} ipython3
cc = catalog_case(spec)
r = run(cc.case)
mr = r.multirig
i = r.case.speed_index(3.5)
P.md_table(
    ["Result at 3.5 knots", "trawlkit", "DynamiT (INIDEP, sim. 3)"],
    [
        ["Horizontal opening AH [m]", f(r.spread.horizontal_opening_m), "14.0"],
        ["Door spread of one net [m]", f(r.doors.spread_m), "16.2"],
        ["Vertical opening AV [m] (Suzuki)", f(r.spread.vertical.suzuki_m, 2), "1.3"],
        ["One net with its rigging [kgf]", f(mr.per_net.std[i], 0), "3777 (warp tension)"],
        ["Both nets and friction [kgf]", f(mr.demand.std[i], 0), "—"],
        ["Swept width [m]", f(mr.swept_width_m), "—"],
        ["Maximum towing speed [kn]", f(r.performance.design.max_speed_kn, 2), "—"],
    ],
)
```

The drag of one net with its rigging is close to the warp tension DynamiT gave; the openings are
not. The workbook's empirical opening methods (Fridman, Suzuki) were built for higher-opening fish
nets and give, for this low-opening shrimp net, larger horizontal and vertical openings than the
INIDEP simulator, and the door spread grows with the 25 m sweeps the case takes from the workbook
because the plan does not give them. The limit of CFP Resolution 7/2018 on the vertical opening
(1.5 m) is checked in the notes:

```{code-cell} ipython3
for n in r.notes:
    if n.startswith(("cfp_res7_2018", "multirig_overlap", "watson_door_area")):
        print(n)
```

With the 24 ft booms of the North American source the two nets of this spread overlap: the note
says which boom length would be needed or, as in the Gulf of Mexico, that the nets have to be
staggered. The length of the Argentine booms is not published; it is changed with
`boom_length_m`:

```{code-cell} ipython3
need = M.boom_length_without_overlap_m(r.doors.spread_m, M.BOOM_ANGLE_DEG)
r_long = run(dataclasses.replace(cc.case, boom_length_m=round(need + 1.0, 1)))
lay = r_long.multirig.layout
print(f"boom of {f(r_long.case.boom_length_m)} m: tip {f(lay.tip_offset_m)} m from the "
      f"centreline, gap between nets {f(lay.gap_m)} m, swept width {f(lay.swept_width_m)} m")
display(SVG(rig_plan_svg(r_long)))
```

The bill of materials counts two nets, four doors, two bridles and two warps:

```{code-cell} ipython3
bom = bill_of_materials(r)
P.md_table(
    ["Line", "Quantity", "Unit"],
    [[ln.label, f(ln.quantity, 1), ln.unit] for ln in bom.lines],
)
```

## Twin case

The 2-panel bottom trawl of the Fisherman's Workbook (50–70 hp) on a twin rig: two identical nets,
the plan's doors (1.30 × 0.65 m, 50 kg) outside and a 75 kg clump (1.5 doors) in the middle.

```{code-cell} ipython3
single = run(catalog_case("fao_wb_bt2p_60hp").case)
twin = run(catalog_case("fao_wb_bt2p_60hp", rig="twin").case)
j = twin.case.speed_index(3.0)
mt = twin.multirig
P.md_table(
    ["At 3 knots", "One net with doors", "Twin (two nets)"],
    [
        ["Total drag [kgf]", f(single.performance.demand.std[j], 0), f(mt.demand.std[j], 0)],
        ["Swept width [m]", f(single.doors.spread_m), f(mt.swept_width_m)],
        ["Otter boards", "2", str(mt.n_doors)],
        ["Clump [kg]", "—", f(mt.clump_weight_kg, 0)],
        ["Clump drag [kgf]", "—", f(mt.clump_drag_kgf[j], 1)],
        ["Maximum speed [kn]", f(single.performance.design.max_speed_kn, 2),
         f(twin.performance.design.max_speed_kn, 2)],
    ],
)
```

With two nets of the same size the vessel tows almost twice the drag and sweeps twice the width;
the pair of doors is the same. That is why the twin rig is used with smaller nets than the one the
vessel would tow alone (Bullis and Floyd: two of 35 feet instead of one of 70).

## Beam case

Shrimp beam trawl no. 03 of the SEAFDEC Thai catalogue {cite:p}`seafdec2016thai` (17 m, 235 hp) is
in the catalogue as a draft: the 32 mm codend joins the 51 mm body 1:1, as the plan draws it, and
that seam does not close in stretched length. The plan gives neither the beam nor the shoes: the
case takes the width of Eigaard et al. for 175 kW (shrimp, two beams) and the beam and shoes of the
small vessels of C056/20.

```{code-cell} ipython3
rb = run(catalog_case("seafdec_03_beam_shrimp").case)
mb = rb.multirig
k = rb.case.speed_index(3.0)
bd = mb.beam
P.md_table(
    ["Component (one beam, 3 knots)", "kgf"],
    [
        ["Net (design net drag)", f(rb.drag.rn.std[k], 1)],
        ["Net by eq. 10 of C056/20 (comparison)", f(bd.net_c056_kgf[k], 1)],
        ["Beam", f(bd.beam_kgf[k], 1)],
        ["Shoes", f(bd.shoes_kgf[k], 1)],
        ["Ground gear", f(bd.ground_gear_kgf[k], 1)],
        ["Tickler chains", f(bd.ticklers_kgf[k], 1)],
        ["One beam with its net and warp", f(mb.per_net.std[k], 1)],
        ["Both beams", f(mb.demand.std[k], 1)],
    ],
)
print(f"beam of {f(bd.beam_length_m, 2)} m, vertical opening {f(mb.vertical_opening_m, 2)} m, "
      f"swept width {f(mb.swept_width_m)} m")
```

**Comparison with a measurement.** Depestele et al. {cite:p}`depestele2016` estimated the drag of a
4.4 m tickler-chain beam trawl at 4.4 knots (lower netting, chains and shoes). With the per-metre
data of C056/20 for the small class scaled to that width and speed:

```{code-cell} ipython3
chk = M.depestele_check("small")
P.md_table(
    ["Component", "C056/20 scaled [N]", "Depestele et al. 2016 [N]", "Ratio"],
    [
        ["Lower netting", f(chk.netting_n, 0), f(chk.measured["lower_netting_n"], 0),
         f(chk.ratio("netting"), 2)],
        ["Chains (tickler and ground gear)", f(chk.chains_n, 0), f(chk.measured["chains_n"], 0),
         f(chk.ratio("chains"), 2)],
        ["Shoes", f(chk.shoes_n, 0), f(chk.measured["shoes_n"], 0), f(chk.ratio("shoes"), 2)],
        ["Total", f(chk.total_n, 0), f(chk.measured["total_n"], 0), f(chk.ratio("total"), 2)],
    ],
)
```

The chains agree within 1 % and the total within 20 %; Depestele's netting is of thinner twine
("much lower hydrodynamic drag") and its shoes, with 0.72 m² of sole, are larger than those of
table 2 of C056/20. The package tests fix these tolerances (chains ±10 %, total ±25 %). Both are
model estimates, not tensions measured with a load cell: no published measurement of the warp
tension of a beam trawl was found.

## Simulation

The simulator solves **one** net with its towing points fixed and the 3D view replicates it: with
outriggers, centred behind each boom tip; in the twin rig, on each side of the clump (the towing
points of the simulated net are the door and the clump; the net stays symmetric about its own axis
and the clump, on the seabed, has no lift); in the beam trawl, the headline ends are fixed at the
beam ends at shoe height and the footrope ends at the shoes. Coupled doors (warp to the vessel) are
not used with these rigs.

```{code-cell} ipython3
sim = simulate(rb, 3.0, resolution=3)
print(f"simulated beam trawl: converged {sim.converged}, AH {f(sim.ah_m, 2)} m, "
      f"net {f(sim.drag_kgf, 0)} kgf × {sim.rig['n_nets']} = {f(sim.rig['drag_kgf'], 0)} kgf")
```

## Limits

* The openings of each net come from the workbook methods, tuned for fish nets; for low-opening
  shrimp nets they overestimate AH and AV (comparison with DynamiT above).
* With outriggers the geometry of each net is computed as the workbook's otter trawl (two warps
  from the gallows); the bridle only adds its drag. The nets are assumed centred behind their boom
  tips; the stagger astern is not modelled.
* The twin clump is a rule of thumb (1.5 doors) and its drag that of a sled of the Bullis and Floyd
  dimensions: there is no published design formula.
* The beam trawl takes the ground gear and chains per metre of the Dutch fleet (C056/20); there are
  no data for Thai or Argentine beams. Without the beam weight (`beam_weight_kg`) there is no shoe
  friction.
* The length and angle of the Argentine booms and the power of the F/V *Atlántico 1* were not found
  published.

## Digitised nets

| Net | Source | Rig | Status |
|---|---|---|---|
| `inidep_ito043_tangonera_inidep` | INIDEP ITO 043/2022, fig. 5 {cite:p}`roth2022ito043` | outrigger | draft |
| `inidep_ito043_tangonera_empresa` | INIDEP ITO 043/2022, fig. 4 | outrigger | draft |
| `seafdec_03_beam_shrimp` | SEAFDEC 2016, plan 03 {cite:p}`seafdec2016thai` | beam | draft |
| `seafdec_31_outrigger_shrimp` | SEAFDEC 2016, plan 31 (14 m, 75 hp) | outrigger | published |
| `seafdec_33_outrigger_shrimp` | SEAFDEC 2016, plan 33 (20 m, 90 hp) | outrigger | published |
| `seafdec_38_outrigger_shrimp` | SEAFDEC 2016, plan 38 (13.5 m, 100 hp) | outrigger | published |
| `seafdec_39_outrigger_shrimp` | SEAFDEC 2016, plan 39 (16 m, 150 hp) | outrigger | published |
| `seafdec_35_outrigger_shrimp` | SEAFDEC 2016, plan 35 (15 m, 112 hp) | outrigger | draft |
| `seafdec_30_beam_shrimp` | SEAFDEC 2016, plan 30 (11 m, 165 hp) | beam | published |

The Thai nets of Phase 19.6 are the first **published** outrigger and beam nets of the catalogue: their
plans give the net and the vessel, but not the outriggers, the doors or the beam, so their case uses
the defaults of this chapter (which are not those of the Thai fleet).

The 380 × 70 mm Seafish twin-rig plan {cite:p}`arkley1987ir1310` was not digitised: it is a scan in
British notation (rows of half meshes, S, SB and SK cuts, half-panel counts) that cannot be checked
on the image with the precision of the rest of the catalogue. The sources consulted are in
{doc}`catalogo_fuentes`.
