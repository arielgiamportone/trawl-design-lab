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

# From design to net loft: construction guide

```{code-cell} ipython3
:tags: [remove-cell]
import sys, pathlib
DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English

from IPython.display import Markdown
import _plots_v as PV
from myst_nb import glue
from trawlkit.api import service
from trawlkit.construction import cut_ratio_of, guide
from trawlkit.netting import cut_code_ratio


def num(x: float, nd: int = 2) -> str:
    return f"{x:,.{nd}f}"


R = service.run_case(service.build_case("fao_a3_standard", "fao_a3_modified"))
G = guide(R)
P = {p.id: p for p in G.pieces}
J = {(j.a, j.b): j for j in G.joins}
H = {(h.rope, h.part): h for h in G.hanging}
```

## Purpose

The calculation ends in a plan and a bill of materials; the net maker needs something else: to
know how much netting to buy, how to cut each piece, in what order to join them and how to mount
the net on the ropes. This chapter describes `trawlkit.construction` (Phase 15), which takes the
design to the net loft with the classic rules of net construction {cite}`prado1990,klust1982`
and applies them to any net in the catalogue ({doc}`33_catalogo_fao`) or from a spreadsheet
({doc}`35_lotes_proyeccion`).

## Cuts: reading a cycle

A netting panel is narrowed or widened by cutting its sides with a repeating **cycle**. Each
**point** cut (N) goes down one mesh without changing the width; each **bar** cut (B, one leg of
a mesh) goes down half a mesh and advances half a mesh across; each **transversal** cut (T)
advances one mesh across. A cycle $n_N\,\mathrm{N}\;n_T\,\mathrm{T}\;n_B\,\mathrm{B}$ changes the
width by $n_T + n_B/2$ meshes for every $n_N + n_B/2$ in depth:

$$
r = \frac{n_T + n_B/2}{n_N + n_B/2}, \qquad \text{cycles} = \frac{N}{n_N + n_B/2}.
$$

Thus `1N2B` (one point and two bars) gives $r = 1/2$ and `AB` (all bars) $r = 1$. The guide
expands each code into a net-loft instruction (“1N2B: 1 point and 2 bars per cycle; repeat 18
times”) and says which edge to start from.

```{code-cell} ipython3
:tags: [remove-input]
PV.md_table(
    ["Panel", "Pieces", "Meshes mouth → codend end × depth", "Cuts", "Waste"],
    [
        [
            p.id,
            str(p.pieces),
            f"{p.meshes_mouth} → {p.meshes_codend} × {p.meshes_depth}",
            "; ".join(f"{s.side}: {s.code}" + (" (inferred)" if s.inferred else "") for s in p.sides),
            f"{num(100 * p.waste, 0)} %",
        ]
        for p in G.pieces
    ],
)
```

**Wings: two different sides.** A centre panel is cut the same on both sides. A wing piece has a
rope side (on the A-3, `AB`) and an inner side; together they give the change of width
$|T_\text{mouth} - T_\text{codend}|$, adding or subtracting: $|r_1 \pm r_2|\,N$, the same rule
the catalogue validator uses. When the plan gives only one cut, the guide infers the other and
marks it. That is what happens with panel F of the A-3: the workbook cannot give its cut (erratum
`panel_f_cut_na`, {doc}`erratas`). With an `AB` side that gains 40 meshes in 40 of depth and a
panel that only grows from 129 to 143, the inner side must lose 26 meshes in 40, $r = 0.65$: the
nearest cut in the table is `1N4B` ($r = 2/3$), the same as piece D that precedes it.

**Netting to buy.** Each piece comes from a rectangle of netting. Centre pieces come from a
rectangle as wide as their larger edge; wing pieces are cut **in nested pairs**, one the mirror
image of the other, from a rectangle of $(T_\text{mouth} + T_\text{codend}) \times N$ meshes,
with no waste other than that of the cut. The guide adds up the rectangles by quality (material,
mesh size and twine) and gives the weight of netting to buy with the waste included: for the A-3,
{glue:md}`stock_kg` kg against {glue:md}`finished_kg` kg of cut netting.

```{code-cell} ipython3
:tags: [remove-cell]
glue("stock_kg", Markdown(num(sum(s.weight_kg for s in G.stock), 1)), display=False)
glue("finished_kg", Markdown(num(sum(s.finished_kg for s in G.stock), 1)), display=False)
```

## Joins and take-ups

Two panels are joined edge to edge. If they have the same number of meshes, they are joined
**mesh to mesh**; if not, the panel with more meshes is gathered with **take-ups** (two meshes
together over one of the other panel) spread along the seam. The joins follow the same order as
the plan (see {doc}`33_catalogo_fao`): the centre panels from the mouth to the codend, the wings
from the wingtip to the body, each wing on a corner of the first centre panel and, finally, the
side seams between the top and the bottom (in 4-panel nets, each side station with the top one
and the bottom one, starting from the codend).

```{code-cell} ipython3
:tags: [remove-input]
PV.md_table(
    ["Step", "Face", "Join", "Meshes", "How"],
    [
        [str(j.step), j.plane, f"{j.a} + {j.b}", f"{j.meshes_a} : {j.meshes_b}", j.rule]
        for j in G.joins
    ],
)
w = J["C", "E"]
glue("wing_meshes", Markdown(str(w.meshes_b)), display=False)
glue("bosom_meshes", Markdown(str(H["headrope", "bosom"].meshes)), display=False)
```

Wing C ends in 117 meshes of 80 mm (9.36 m stretched) and rests on panel E, of 60 mm: it takes up
{glue:md}`wing_meshes` meshes of its mouth edge at each corner (the “117/156” ratio drawn on the
sheet). Of the 412 meshes of E, {glue:md}`bosom_meshes` remain free in the centre: the
**bosom**, which is not sewn to another panel but mounted directly on the headrope.

## Mounting on the ropes

The netting is mounted on the rope with a **hanging ratio** $E$, the quotient between the length
of rope and the stretched length of netting mounted on it {cite}`prado1990`:

$$
E = \frac{L_\text{rope}}{n \cdot m}, \qquad \text{meshes per metre} = \frac{n}{L_\text{rope}},
$$

with $n$ meshes of mesh size $m$. In the wings the netting is mounted along its cut side, one
mesh for each row of depth (the same count as the wing piece of the Dimensiones de la Red [net
dimensions] sheet, $(N_A + N_C)\cdot m$), and the workbook mounts at $E = 1.05$; in the bosom
the free meshes of the mouth edge are mounted.

```{code-cell} ipython3
:tags: [remove-input]
PV.md_table(
    ["Rope", "Section", "Rope [m]", "Meshes", "E", "Schedule"],
    [
        [h.rope, h.part, num(h.rope_m), str(h.meshes), num(h.hanging), h.schedule]
        for h in G.hanging
    ],
)
glue("e_bosom", Markdown(num(H["headrope", "bosom"].hanging, 3)), display=False)
```

The bosom of the A-3 ends up at $E =$ {glue:md}`e_bosom`, which is the workbook's bosom hanging
ratio (0.83) applied to half the free edge: the sheet computes the bosom piece as half of what
the mouth edge exceeds the wings by. If the rope turns out longer than the netting ($E > 1.1$),
the netting cannot go directly on it: it goes on a hanging line or fishing line, and the rope
(for example, a footrope with discs or chain) is joined to it with droppers. The guide warns
about it; it happens with the footrope of the BOBP/WP/13 pair trawl.

**Floats and ballast.** The position of each float follows the workbook's selective rule
(Flotación y Lastre [buoyancy and ballast] sheet): 70 % of the floats on the wings and, of
those, 60 % in the first fifth of the wing, next to the bosom, where the headrope needs more
lift; the rest is spread evenly. The ballast is distributed over three zones of the footrope
(adjusting chain at the centre, bosom and wings) with their kg and kg/m for the minimum and the maximum ballast.

**Rope cuts.** To each finished length (headrope, footrope, wingtip reinforcements, bridle legs,
sweeps, crowfoot, chains and wires) an allowance is added for an eye or splice. The default
value, 0.5 m per eye, is a net-loft rule (TO BE VERIFIED depending on the rope and the type of
splice) and can be changed in the app and with `trawlkit build-guide --eye-allowance`.

## The whole catalogue

The same guide comes out for any net in the catalogue:

```{code-cell} ipython3
:tags: [remove-input]
rows = []
for nid, spec in service.net_presets().items():
    g = guide(service.run_case(service.build_case(nid)))
    inferred = sum(s.inferred for p in g.pieces for s in p.sides)
    warns = sum(bool(h.warning) for h in g.hanging)
    rows.append(
        [
            nid,
            str(sum(p.pieces for p in g.pieces)),
            str(len(g.joins)),
            num(sum(s.weight_kg for s in g.stock), 1),
            str(inferred),
            str(warns),
        ]
    )
PV.md_table(
    ["Net", "Pieces", "Joins", "Netting to buy [kg]", "Inferred cuts", "Mounting warnings"],
    rows,
)
```

## Where it is used

- **Web**: the “Construction” tab of Expert mode, with the cutting sheet, step-by-step assembly
  (the plan highlights the panels of each join), the mounting on the ropes with the float line,
  the rope cuts and the net-loft progress, which is saved in the browser; in Guided mode, “How do
  I rig it? Workshop guide” in the result ({doc}`web`).
- **Offline**: the engine on the phone builds the guide and its XLSX spreadsheet; the PDF needs
  the server and, without a network, the HTML view is printed.
- **CLI**: `trawlkit build-guide fao_a3_standard -o guia.pdf` (or `.html`, `.xlsx`, `.json`).
- **API**: `POST /design/construction` and `/design/construction/export` ({doc}`api`).
- **Case report**: the “Construction and materials” section, with the bill of materials.

## Assumptions and limits

- Meshes are counted stretched and the rope lengths include the engine's hanging ratio.
- Inferred cuts come from the change of width of the panel: they must be checked against the
  plan.
- Nesting the wings in pairs assumes mirrored pieces; with asymmetric wings the real waste is
  larger.
- The position of the floats and the distribution of the ballast are a starting point for the
  sea trial.
- The side seams are given as one seam per side with the meshes of each face; the side
  reinforcements (selvedge ropes, *selvedges*) depend on the plan.

## Exercises

From the teaching-mode bank, with the book's data. In the app, the “UTN Classroom” mode generates
them with other data and grades them ({doc}`38_docentes`).

```{code-cell} ipython3
:tags: [remove-input]
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path.cwd().parent))
import _exercises
_exercises.section("36_construccion")
```
