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
from trawlkit.rigging import shrimp as SH
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
{cite:p}`roth2022ito043`. The length and angle of the Argentine booms **are not published**: neither
the INIDEP reports, Res. CFP 7/2018 nor the shipyard press give them. The engine uses the Gulf of
Mexico's 24 ft and 20° by analogy (assumed); an FAO review, citing Vendeville (1990), gives for
tropical shrimp outriggers "an angle of 20 to 30 degrees from the horizontal" {cite:p}`gillett2008`
(p. 19), and Knake et al.'s 20° sits at the low end of that range.

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
         "Knake et al. 1958, p. 5 (20–30°: Gillett 2008, p. 19); Verhoest and Maton 1964"],
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
`clump_weight_kg`, `beam_count`, `beam_length_m`, `beam_ticklers`, `beam_weight_kg`, `opening_method`,
`shrimp_bridle_m`…); in the app,
the **Rig** selector of the case panel and of the guided mode follows the net's rig by default and
the parameters are edited in "Advanced parameters".

## Openings of shrimp trawls

The workbook's opening average (`Dim!F61`) averages four wing spreads (from the cut angle,
geometric, geometric with the working net and the Fridman series) and the door spread comes from
the warp paid out: it was built for fish nets towed with long sweeps. In the INIDEP outrigger net
the two geometric terms already give DynamiT's 14 m, but the cut-angle wing spread
($2 b U_2 \tan\alpha$) gives 60 m and the door spread grows with the warp. With a **split bridle**
(*tijera*) that does not happen: "the door spread cannot be changed with the length of warp paid
out" {cite:p}`roth2016iat072`. So, with `opening_method="auto"` (the default), outrigger and twin
rigs use the **shrimp method** (`trawlkit.rigging.shrimp`, Phase 19.7b); `opening_method="book"`
returns to the workbook average and `"shrimp"` forces it, for instance for a shrimp net with otter
boards. Otter-board nets (even crustacean ones, such as the A-3 squat lobster net), pair trawls and
beam trawls do not change, and neither does the workbook's Excel mode.

**Door spread with a split bridle.** Planar balance of a door hanging from one leg of the split
bridle {cite:p}`roth2016iat072` (eqs. 13–17, with the corrected projection):

$$
\beta = \arcsin\!\left(\frac{L_C}{L_R}\sin\alpha\right),\qquad
T\cos\alpha = F_{CD} + \tfrac{R}{2}\cos\beta,\qquad
F_{CL} = T\sin\alpha + \tfrac{R}{2}\sin\beta,\qquad
DP = 2\,L_C\sin\alpha
$$

$F_{CL}$ and $F_{CD}$ are the lift and drag of one door (the case's polar), $R$ the design net drag
at the design speed (3.5 knots, that of the INIDEP simulations), $L_C$ the bridle leg
(`outrigger_bridle_m`: 70 m by default; 55–73 m in the INIDEP reports) and $L_R$ the run from the
door to the point where the net converges: door-to-wing bridles + crowfoot + 0.90 × the stretched
length of the net without codend (wing tip → codend). The 0.90 is DynamiT's lengthwise reference
mesh shape (derived from the "Length ratio" column of its rope tables, see the Argentine case).
The **door-to-wing bridles** (*cañas*) are 3 m by default (IAT 85/2024 {cite:p}`roth2024iat085`
and ITO 61/2022 {cite:p}`roth2022ito061`; 2.5–4 m in the other INIDEP rigs, assumed) and are
changed with `shrimp_bridle_m`. α is found by bisection.

**Correction of Roth's eq. (12).** The printed equation is
$F_{CL} - (F_{CD} + R/2)\sin 2\alpha + (R/2)\sin 2\beta = 0$: it projects the components of eqs. 5–8
twice and gives $2\sin\alpha\cos\alpha$ where $\sin\alpha$ belongs. With the ITO 043/2022 data
(4.08 m², $C_L/C_D$ = 0.93/0.71, $R$ = 3777 − 2·$F_{CD}$, $L_C$ = 70 m) the printed form gives door
spreads no outrigger trawler has; the corrected one brackets DynamiT's 16.2 m:

```{code-cell} ipython3
import math
from trawlkit.rigging.doors import door_forces_kgf
from trawlkit.units import KNOT_TO_MS

fz = door_forces_kgf(4.08, 0.71, 0.93, 3.5 * KNOT_TO_MS)
FL, FD = float(fz.lift_kgf), float(fz.drag_kgf)
RN = 3777.2 - 2 * FD


def printed_eq12(lc, lr):
    """Door spread with the printed eq. (12) (root found by scanning α)."""
    amax = math.asin(min(1.0, lr / lc))
    g = lambda a: FL - (FD + RN / 2) * math.sin(2 * a) + (RN / 2) * math.sin(
        2 * math.asin(min(1.0, lc / lr * math.sin(a))))
    xs = [amax * k / 4000 for k in range(1, 4000)]
    for a, b in zip(xs, xs[1:]):
        if g(a) * g(b) < 0:
            return 2 * lc * math.sin(0.5 * (a + b))
    return float("nan")


P.md_table(
    ["L_R [m]", "DS, printed eq. (12) [m]", "DS, corrected balance [m]", "DynamiT [m]"],
    [[f(lr, 0), f(printed_eq12(70.0, lr)), f(SH.tijera_balance(FL, FD, RN, 70.0, lr).spread_m),
      "16.2"] for lr in (20.0, 25.0, 30.0, 35.0)],
)
```

Roth reports agreement within 0.6 m with DynamiT for his 22 m example (table 1), but does not print
$L_C$ or the door data, so that result could not be reproduced.

**Horizontal opening.** $AH = DP \cdot L_{Rw} / (L_{Rw} + \text{crowfoot} + \text{bridles})$: the
workbook's similar-triangle ratio (Mec!L225, without the rounding) with the short door-to-wing
bridles instead of the 25 m sweeps. $AH/DP$ is checked against 0.72–0.88, the range of the INIDEP
DynamiT simulations with a split bridle (ITO 043, IAT 85, 104 and 111; derived from their tables).
The cut-angle wing spread and the Fridman series leave the average.

**Fallback without a split bridle** (twin, otter boards, or if the balance has no solution):
$AH = k \cdot \text{headrope}$ with the workbook door spread and $k$ by family:

```{code-cell} ipython3
fam = {"inidep_dynamit": "Argentine low-opening outrigger net (DynamiT)",
       "us_conventional": "Conventional US shrimp trawl, no floats (measured)",
       "tongue": "Tongue, Mongoose, Cobra trawls (measured)"}
P.md_table(
    ["Family", "k", "Range", "Source"],
    [[fam[h.key], f(h.k, 2), f"{f(h.low, 2)}–{f(h.high, 2)}", h.source]
     for h in SH.HEADROPE_K.values()],
)
```

The sources disagree and the engine says so in the notes of every run. The DynamiT simulations of
Argentine outrigger nets give $AH/\text{headrope}$ = 0.36–0.50; the door spread **measured** with
Simrad sensors on the 25.4 m Iberconsa net is 18.8–19.5 m, 0.74–0.77 × the headrope
{cite:p}`roth2024iat094`, and INIDEP itself considers its simulated AH "well below the recommended
value (approximately 70 %)" {cite:p}`roth2024iat085`. The diver measurements of Watson et al.
{cite:p}`watson1984` and Harrington et al. {cite:p}`harrington1988` give 0.62–0.78 for
conventional US shrimp trawls. DynamiT may be biased low: the only measured/simulated comparison
(Iberconsa) does not use the same doors (400 kg double-slot Bison doors at sea; 500 kg, 4.5 m² flat
doors in the simulator).

**Vertical opening.** $AV = 0.04 \cdot \text{headrope}$ (0.03–0.07) for low-opening nets with few
or no floats: 0.026–0.049 in DynamiT and 0.029–0.080 in the measurements of Watson et al. and
Harrington et al. There is no float correction: table 3 of Watson et al. shows that 10–20 floats
multiply the AV by 1.75–2.9, but it gives no continuous relation, and the engine's float count is
the one the workbook computes, not the net's. Suzuki's AV (4/90 of the circumference) gives 3.2 m
for the INIDEP net, 2.5 times DynamiT's. The 1.5 m limit of CFP Resolution 7/2018 is checked with
this AV.

**Design depth.** The Argentine red shrimp fleet fishes at 71–87 m (IC 68/2022
{cite:p}`rubio2022ic068`) and at 86–106 m (IAT 94/2024); the INIDEP DynamiT simulations of
outrigger nets use 100 m. Red shrimp nets whose source gives no depth take 90 m (range 70–110 m,
`trawlkit.catalog.LANGOSTINO_DEPTH_M`; a value chosen within that range); other bottom nets keep
30 m. With a split bridle the depth changes the warp and its tension, not the door spread.

### Validation

The full engine with the two ITO 043/2022 nets of the catalogue (before: workbook average; after:
shrimp method) against DynamiT, and the balance alone with the published data of each INIDEP
simulation ($R$ = tension − 2·$F_{CD}$; $L_R$ from the digitised plan or estimated, TO BE VERIFIED):

```{code-cell} ipython3
rows = []
for nid, sim in (("inidep_ito043_tangonera_inidep", "ito043_sim3"),
                 ("inidep_ito043_tangonera_empresa", "ito043_sim2")):
    case = catalog_case(nid).case
    before = run(dataclasses.replace(case, opening_method="book"))
    after = run(case)
    dc = next(c for c in SH.DYNAMIT_CASES if c.key == sim)
    rows.append([
        f"`{nid}` (engine)",
        f"{f(before.doors.spread_m)} / {f(before.spread.horizontal_opening_m)} / "
        f"{f(before.spread.vertical_opening_m, 2)}",
        f"{f(after.doors.spread_m)} / {f(after.spread.horizontal_opening_m)} / "
        f"{f(after.spread.vertical_opening_m, 2)}",
        f"{f(dc.dynamit_spread_m)} / {f(dc.dynamit_ah_m)} / "
        + ("1.3" if sim == "ito043_sim3" else "1.5"),
        f"{f(100 * (after.doors.spread_m / dc.dynamit_spread_m - 1), 0)} %",
        "—",
    ])
labels = {
    "ito043_sim3": "ITO 043/2022, sim. 3 (INIDEP net, fig. 5)",
    "ito043_sim2": "ITO 043/2022, sim. 2 (company net with 3 mm twine, fig. 4)",
    "ito043_sim1": "ITO 043/2022, sim. 1 (company net, original materials)",
    "iat085_iberconsa": "IAT 85/2024, Iberconsa net 25.4/31.0 m (sim. 1)",
    "iat111_morales": "IAT 111/2022, Morales net 26.30/32.50 m (3 knots)",
}
for dc in SH.DYNAMIT_CASES:
    b = SH.dynamit_case_balance(dc)
    rows.append([
        f"{labels[dc.key]} (balance, L_R {f(dc.net_leg_m)} m"
        + (", estimated" if dc.net_leg_kind == "assumed" else "") + ")",
        "—",
        f(b.spread_m),
        f(dc.dynamit_spread_m),
        f"{f(100 * (b.spread_m / dc.dynamit_spread_m - 1), 0)} %",
        "18.8–19.5 (IAT 94/2024)" if dc.key == "iat085_iberconsa" else "—",
    ])
P.md_table(
    ["Case", "Before: DS / AH / AV [m]", "Shrimp method", "DynamiT", "DS − DynamiT",
     "Measured DS [m]"],
    rows,
)
```

The full engine is within 15 % of DynamiT's door spread and within 10 % of its AH for both nets;
before, the door spread came out 3.6 to 3.9 times larger. The balance alone is within ±20 % in the
four cases of the phase report (ITO 043 sims. 1 and 3, IAT 85 Iberconsa, IAT 111 Morales), the
tolerance the tests fix while $L_R$ does not come from a digitised plan; sim. 2 with the balance
alone (lower tension with almost the same $L_R$) gives +26 %. The measured door spread of the Iberconsa net
(18.8–19.5 m, other doors and a 60 m split bridle) lies above DynamiT and the balance: consistent
with the DynamiT bias noted above.

## Argentine case: the INIDEP outrigger net

INIDEP evaluated in DynamiT an outrigger net proposed by the company Pesquera Deseado and one of
its own {cite:p}`roth2022ito043`. Its figures 5 (INIDEP net) and 4 (company net with 3 mm twine)
are in the catalogue as `inidep_ito043_tangonera_inidep` and `inidep_ito043_tangonera_empresa`,
digitised with the provenance of every value, and they are **published** since Phase 19.7c.
Re-reading the plans showed that the two-panel codend (2 × 100 meshes of 60 mm = 12.0 m) matches
the sum of the aft edges of the top and bottom panels (4.80 + 7.32 = 12.12 m in fig. 5;
4.80 + 7.42 = 12.22 m in fig. 4) and that each side panel ends before the codend, gathered on a
0.50 m rope (N in fig. 5, L in fig. 4) that closes into the seams. The "Length ratio" column of the
DynamiT rope table confirms it (derived rule: rope length over the netting edge at the reference
mesh shape, 0.90 lengthwise and 0.436 across; for N, 0.50 / (17 × 0.14 × 0.436) = 0.48, as
printed). The validator therefore compares the circumference and not panel by panel
(`codend_join` warning): panel by panel the join is not 1:1 and the plan does not say how the
difference is taken up. Three cut labels that do not give the width change of their panel (they are
transcribed as read) and the side panels, which the engine shares out by stretched length, remain
as warnings.

```{code-cell} ipython3
spec = load_net("inidep_ito043_tangonera_inidep")
P.md_table(
    ["Level", "Code", "Issue"],
    [[i.level, i.code, i.message] for i in check(spec)],
)
```

The net names the vessel and door it is computed with: the fleet's **typical outrigger trawler**
(1998 average, {doc}`39_flota_argentina`), because the report does not publish the length or power
of the F/V *Atlántico 1*, and a 4.08 m² flat door, the area of the doors of the same company rig in
IAT 75/2023 {cite:p}`roth2023iat075` (p. 3), with the proportions of the catalogue's generic flat
door (2.86 × 1.43 m; assumed, ITO 043 publishes neither the dimensions nor the maker). Res. CFP
7/2018, art. 4, caps the door height at 1.50 m {cite:p}`cfp2018res7`: with 4.08 m² the length is at
least 2.72 m (*derived*), and the assumption meets it. The weight, 540 kg per door, is ITO 043's
(pp. 2 and 6); IAT 75/2023 gives 530 kg for the same doors. The depth is not in the
report either: 90 m, that of the red shrimp fleet. All of it is in the case notes.

```{code-cell} ipython3
cc = catalog_case(spec)
r = run(cc.case)
r_book = run(dataclasses.replace(cc.case, opening_method="book"))
mr = r.multirig
i = r.case.speed_index(3.5)
P.md_table(
    ["Result at 3.5 knots", "Workbook", "Shrimp method", "DynamiT (INIDEP, sim. 3)"],
    [
        ["Horizontal opening AH [m]", f(r_book.spread.horizontal_opening_m),
         f(r.spread.horizontal_opening_m), "14.0"],
        ["Door spread of one net [m]", f(r_book.doors.spread_m), f(r.doors.spread_m), "16.2"],
        ["Vertical opening AV [m]", f(r_book.spread.vertical_opening_m, 2),
         f(r.spread.vertical_opening_m, 2), "1.3"],
        ["One net with its rigging [kgf]", f(r_book.multirig.per_net.std[i], 0),
         f(mr.per_net.std[i], 0), "3777 (warp tension)"],
        ["Both nets and friction [kgf]", f(r_book.multirig.demand.std[i], 0),
         f(mr.demand.std[i], 0), "—"],
        ["Swept width [m]", f(r_book.multirig.swept_width_m), f(mr.swept_width_m), "—"],
    ],
)
```

The drag of one net with its rigging does not depend on the opening method and stays within 20 % of
DynamiT's warp tension (the engine computes it at 90 m, with more warp). The run notes say which
method was used, with which data and where the openings fall; the limit of CFP Resolution 7/2018 on
the vertical opening (1.5 m) is checked with the method's AV:

```{code-cell} ipython3
for n in r.notes:
    if n.startswith(("shrimp_opening", "cfp_res7_2018", "multirig_overlap", "watson_door_area")):
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

* The openings of shrimp trawls come from the Phase 19.7b method, calibrated with INIDEP DynamiT
  simulations and checked against a single measured series (door spread, IAT 94/2024); no
  measured AH of an Argentine outrigger net has been published. Its validity: split bridle of
  55–73 m, flat or Bison doors of 300–600 kg, headrope of 11–40 m, 2.5–4 knots and 30–110 m. The
  length $L_R$ and the door-to-wing bridles are derived or assumed; the tolerance is ±20 % on the
  door spread.
* With outriggers the rest of the geometry of each net (warp, sag, workbook bridles) is computed
  as the workbook's otter trawl; the split bridle adds its drag and sets the door spread. The nets are assumed centred behind their boom
  tips; the stagger astern is not modelled.
* The twin clump is a rule of thumb (1.5 doors) and its drag that of a sled of the Bullis and Floyd
  dimensions: there is no published design formula.
* The beam trawl takes the ground gear and chains per metre of the Dutch fleet (C056/20); there are
  no data for Thai or Argentine beams. Without the beam weight (`beam_weight_kg`) there is no shoe
  friction.
* The length and angle of the Argentine booms (and the position of their heel) and the power of the
  F/V *Atlántico 1* were not found published. The defaults are US values {cite:p}`knake1958`, with
  {cite:t}`gillett2008`'s 20–30° range as a second source.

## Digitised nets

| Net | Source | Rig | Status |
|---|---|---|---|
| `inidep_ito043_tangonera_inidep` | INIDEP ITO 043/2022, fig. 5 {cite:p}`roth2022ito043` | outrigger | published |
| `inidep_ito043_tangonera_empresa` | INIDEP ITO 043/2022, fig. 4 | outrigger | published |
| `seafdec_03_beam_shrimp` | SEAFDEC 2016, plan 03 {cite:p}`seafdec2016thai` | beam | draft |
| `seafdec_31_outrigger_shrimp` | SEAFDEC 2016, plan 31 (14 m, 75 hp) | outrigger | published |
| `seafdec_33_outrigger_shrimp` | SEAFDEC 2016, plan 33 (20 m, 90 hp) | outrigger | published |
| `seafdec_38_outrigger_shrimp` | SEAFDEC 2016, plan 38 (13.5 m, 100 hp) | outrigger | published |
| `seafdec_39_outrigger_shrimp` | SEAFDEC 2016, plan 39 (16 m, 150 hp) | outrigger | published |
| `seafdec_35_outrigger_shrimp` | SEAFDEC 2016, plan 35 (15 m, 112 hp) | outrigger | draft |
| `seafdec_30_beam_shrimp` | SEAFDEC 2016, plan 30 (11 m, 165 hp) | beam | published |

The Thai nets of Phase 19.6 were the first **published** outrigger and beam nets of the catalogue: their
plans give the net and the vessel, but not the outriggers, the doors or the beam, so their case uses
the defaults of this chapter (which are not those of the Thai fleet).

The 380 × 70 mm Seafish twin-rig plan {cite:p}`arkley1987ir1310` was not digitised: it is a scan in
British notation (rows of half meshes, S, SB and SK cuts, half-panel counts) that cannot be checked
on the image with the precision of the rest of the catalogue. The typed plans of IAT 27/2019
(Solimeno net, original and modified) and IAT 75/2023 (traditional Pesquera Deseado net, a legible
version of ITO 043 fig. 2) are left for a later phase. The sources consulted are in
{doc}`catalogo_fuentes`.
