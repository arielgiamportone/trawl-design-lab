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

# Case study: the FAO A-3 net in the Beagle Channel

```{code-cell} ipython3
:tags: [remove-cell]
import sys, pathlib
DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English
import math
import numpy as np
import matplotlib.pyplot as plt
from tests.golden_utils import golden
from trawlkit.i18n import t
import _plots_v as V
V.setup_style()

C150, C180 = V.run_case(150, "corrected"), V.run_case(180, "corrected")
E150, E180 = V.run_case(150, "excel"), V.run_case(180, "excel")
kn = C150.case.speeds
I = {v: C150.case.speed_index(v) for v in (2.0, 2.5, 3.0, 3.5)}
```

## Context

The model was born for a specific fishery: the **squat lobster** (*langostilla*, *Munida gregaria* /
*M. subrugosa*) of the Beagle Channel, a small crustacean living on intermediate seabeds at about
40 m depth, fished by the local fleet of inshore (*rada o ría*) vessels up to 9 m in length with
150–180 BHP engines {cite:p}`giamportone2024`. The design question is the one in
{doc}`01_introduccion`: which net can this vessel tow, at what speed, and with what rigging?

The chosen net is the A-3 from the FAO catalogue of nets for small vessels {cite:p}`faocatalogue`,
a two-panel bottom trawl designed precisely for 150–180 HP. The book evaluates it in two variants
that this chapter compares: the **standard** one, with a 40 mm codend, and the one **modified for
crustaceans**, with a 30 mm codend, which retains the squat lobster better at the cost of more twine
in the water.

The whole chapter uses the **corrected mode** (`Compat.CORRECTED`, see {doc}`erratas`), which is the
design mode; the `excel` mode appears as a comparison column and as the validation anchor against
the original workbook.

## Setting up the case

```{code-cell} ipython3
:tags: [hide-input]
c = C150.case
std, mod = c.net, c.net_modified
cod_std = [p for p in std.panels if p.section.value == "codend"]
cod_mod = [p for p in mod.panels if p.section.value == "codend"]

def codend(ps):
    return " + ".join(f"{p.id}: {V.fmt(p.mesh_mm, 0)} mm, {p.meshes_top}×{p.meshes_depth} meshes"
                      + (f" (×{p.count})" if p.count > 1 else "") for p in ps)

d = c.door
V.md_table(
    ["Input", "Value", "Source"],
    [
        ["Target species", f"{std.species.name} (Munida gregaria / M. subrugosa)", "Especie Blanco!C3, H3"],
        ["Working depth", f"{V.fmt(c.working_depth_m, 0)} m, {t(std.species.bottom_type).lower()} seabed", "Especie Blanco!E5:E6"],
        ["Standard net: codend", codend(cod_std), "Paños!H222:T224"],
        ["Modified net: codend", codend(cod_mod), "Paños!H255:H257"],
        ["Body and wing panels", "PA, 80/60/40 mm, Ø 1.13–1.37 mm (same in both)", "src/trawlkit/data/fao_a3_*.yaml"],
        ["Design vessel", f"{V.fmt(c.vessel.bhp, 0)} BHP, length ≤ {V.fmt(c.vessel.length_m, 0)} m, beam {V.fmt(c.vessel.beam_m, 1)} m", "Tipo de buques"],
        ["Class vessel", "180 BHP (Fridman buoyancy Ffz averaged, warp sized with 180 HP)", "Mec!O261, Rem!E81"],
        ["Propeller for ROB and buoyancy", "fixed pitch, K_F = 10 kgf/HP (Fridman)", "PotOK!L11"],
        ["Otter board", f"FAO flat wooden board, {V.fmt(d.length_m, 2)} × {V.fmt(d.height_m, 2)} m, S = {V.fmt(d.area_m2, 3)} m², {V.fmt(d.weight_air_kg, 0)} kg", "Tablas de Referencias!A245"],
        ["Otter board angle of attack", f"{V.fmt(c.door_attack_angle_deg, 0)}° (C_L = 0.93, C_D = 0.71)", "Port!C134"],
        ["Warp paid out", f"{V.fmt(C150.rigging.towing.warp_m, 0)} m (5 × depth)", "Mec!E177"],
        ["Speeds", "1 to 5 kn in 0.5 kn steps", "PotOK!B10:B18"],
    ],
)
```

The 180 HP vessel is not a separate case: the workbook computes the two vessels of the class side by
side, and two results couple them (Fridman's total buoyancy averages both blocks and the warp is
sized with 180 HP, see {doc}`motor`). That is why each run carries the other vessel in
`class_vessels`, and what changes between them is the **available pull**.

## Main results

```{code-cell} ipython3
:tags: [hide-input]
def row(label, f, nd=2, unit=""):
    a, b = f(C150), f(E150)
    if isinstance(a, str):
        return [label, a, b, "—" if a == b else "changes"]
    return [label + (f" [{unit}]" if unit else ""), V.fmt(a, nd), V.fmt(b, nd),
            V.pct_s(a, b) if b else "—"]

i3, i35 = I[3.0], I[3.5]
rows = [
    row("Headrope", lambda r: r.dimensions.std.headrope_m, 2, "m"),
    row("Footrope", lambda r: r.dimensions.std.footrope_m, 2, "m"),
    row("Solid area Sₛ, standard", lambda r: r.geometry.std.solid_surface_m2, 2, "m²"),
    row("Solid area Sₛ, modified", lambda r: r.geometry.mod.solid_surface_m2, 2, "m²"),
    row("Weight of the standard net in air", lambda r: r.geometry.std.weight_air_kg, 1, "kg"),
    row("Vertical opening (Suzuki)", lambda r: r.spread.vertical.suzuki_m, 2, "m"),
    row("Horizontal opening AH", lambda r: r.spread.horizontal_opening_m, 2, "m"),
    row("Door spread", lambda r: r.doors.spread_m, 1, "m"),
    row("Design Rₙ at 3 kn (Aberdeen)", lambda r: r.drag.rn.std[i3], 0, "kgf"),
    row("Total drag at 3.5 kn", lambda r: r.warps.total.std[i35], 0, "kgf"),
    row("Total buoyancy (rounded)", lambda r: r.floats.flotation_rounded_kgf, 0, "kgf"),
    row("Floats", lambda r: f"{r.floats.count} × {r.floats.diameter_mm:.0f} mm"),
    row("Minimum ballast", lambda r: r.ballast.limits.min_kg, 0, "kg"),
    row("Maximum ballast", lambda r: r.ballast.limits.max_kg, 0, "kg"),
    row("Minimum breaking load of the warp", lambda r: r.warps.loads.min_breaking_load_kgf / 1000, 2, "t"),
    row("Selected warp", lambda r: f"{r.warps.selection.diameter_mm:.0f} mm, "
        f"{V.fmt(r.warps.selection.breaking_load_t, 2)} t"),
    row("Maximum speed (150 HP, PF, standard)", lambda r: r.performance.design.max_speed_kn, 2, "kn"),
]
V.md_table(["Result (150 BHP)", "Corrected", "Excel", "Δ corrected vs Excel"], rows)
```

The `excel` column reproduces the original workbook. The next cell checks it against the cached
Excel values (`tests/golden`) with the same tolerance as the test suite:

```{code-cell} ipython3
DIM, RES = "dimensiones_de_la_red", "resistencia_de_la_red"
REM, FLOT = "cables_de_remolque", "flotacion_y_lastre"
e = E150  # run in Excel mode, 150 BHP
checks = [
    (e.dimensions.std.headrope_m, golden(DIM, "headrope_m")),
    (e.dimensions.std.footrope_m, golden(DIM, "footrope_m")),
    (e.geometry.std.solid_surface_m2, golden(DIM, "solid_surface_std_m2")),
    (e.drag.rn.std / 1000, golden(RES, "aberdeen_demersal_rn_std_t")),
    (e.warps.total.std, golden(REM, "total_drag_std_kgf")),
    (e.warps.selection.diameter_mm, golden(DIM, "warp_diameter_mm")),
    (e.floats.flotation_rounded_kgf, golden(FLOT, "flotation_total_rounded_kgf")),
    (e.ballast.limits.min_kg, golden(FLOT, "ballast_min_150_kg")),
    (e.ballast.limits.max_kg, golden(FLOT, "ballast_max_150_kg")),
]
for got, ref in checks:
    assert np.allclose(got, ref, rtol=1e-6, atol=0)
f"{len(checks)} checks against the Excel workbook: OK"
```

The differences between the columns are the errata of the workbook ({doc}`erratas`): the corrected
mode measures the whole footrope (33.39 m instead of the truncated 33.3), does not inflate the solid
area of the standard codend (38.75 m² instead of 40.90), adds the drag of the otter boards to the
total demand and, with it, calls for a 13 mm warp because the 12 mm one (8.55 t) does not reach the
minimum breaking load. It also weighs the net counting all its panels (33.5 kg instead of 28.3) and
takes the $C_D$ of the warp with its real angle of attack (0.054 instead of 0.02;
{doc}`18_cables`). Everything else (ropes, geometric openings, buoyancy, floats) matches between the
modes.

## Net drawings

The drawings are produced from the corrected result with `trawlkit.drawing.net_sheet_svg` (see
{doc}`informes`). Only the codend changes: the standard net has two 40 mm panels (upper I, 200
meshes deep, and lower J, 250), the modified one a single 30 mm panel I′, 139 × 300 meshes,
repeated top and bottom.

```{code-cell} ipython3
---
tags: [hide-input, full-width]
mystnb:
  figure:
    caption: A3 drawing of the standard FAO A-3 net (40 mm codend), corrected mode.
    name: fig-30-lamina-std
---
V.sheet_svg(C150, "std")
```

```{code-cell} ipython3
---
tags: [hide-input, full-width]
mystnb:
  figure:
    caption: A3 drawing of the FAO A-3 net modified for crustaceans (30 mm codend), corrected mode.
    name: fig-30-lamina-mod
---
V.sheet_svg(C150, "mod")
```

## Available pull and demand: 150 versus 180 HP

The speed window ({doc}`19_ventana_velocidad`) is the interval in which Fridman's pull $F_T(v)$
exceeds the total drag $R_T(v) = R_N + R_B + R_W + R_{OB}$. The demand does not depend on the
vessel; the pull does, and it depends both on the power and on the propeller: fixed pitch (PF,
$K_F = 10$) or controllable pitch with nozzle (PV+T, $K_F = 15$).

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Fridman pull (PF and PV+T) against the total drag of the standard and the modified net,
      corrected mode. The shaded area is the viable window with a fixed-pitch propeller and the
      standard net; the rings mark the maximum towable speed $v^*$ of each combination.
    name: fig-30-ventana
---
fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.2), sharey=True)
for ax, r, bhp in zip(axes, (C150, C180), (150, 180)):
    W = r.performance.windows
    pf, pvt = W["fixed_pitch_std"].available_kgf, W["variable_pitch_nozzle_std"].available_kgf
    dstd, dmod = r.performance.demand.std, r.performance.demand.mod
    vs = W["fixed_pitch_std"].max_speed_kn
    vv = np.linspace(kn[0], vs, 60)
    ax.fill_between(vv, np.interp(vv, kn, dstd), np.interp(vv, kn, pf), color=V.BLUE_150,
                    alpha=0.45, lw=0, zorder=1)
    ax.plot(kn, pf, color=V.SERIES[0], zorder=3)
    ax.plot(kn, pvt, color=V.SERIES[1], zorder=3)
    ax.plot(kn, dstd, color=V.INK, lw=1.8, zorder=3, label="Rₜ standard net")
    ax.plot(kn, dmod, color=V.INK_2, lw=1.4, ls=(0, (4, 2)), zorder=3, label="Rₜ modified net")
    for key in ("fixed_pitch_std", "variable_pitch_nozzle_std"):
        w = W[key]
        y = float(np.interp(w.max_speed_kn, kn, w.available_kgf))
        ax.plot([w.max_speed_kn], [y], "o", ms=11, mfc="none", mec=V.INK_2, mew=1.2, zorder=4)
        ax.annotate(f"v* = {V.fmt(w.max_speed_kn, 2)} kn", (w.max_speed_kn, y), xytext=(8, -14),
                    textcoords="offset points", fontsize=8.5, color=V.INK_2)
    V.end_label(ax, 5.0, pf[-1], "Fₜ PF", dy=-2)
    V.end_label(ax, 5.0, pvt[-1], "Fₜ PV+T")
    ax.set_title(f"{bhp} BHP")
    ax.set_xlabel("Towing speed [kn]")
    ax.set_xlim(1, 5)
    ax.set_ylim(0, 4400)
axes[0].set_ylabel("Force [kgf]")
axes[0].legend(loc="upper left")
fig.tight_layout()
plt.show()
```

```{code-cell} ipython3
:tags: [hide-input]
combos = [("fixed_pitch", "PF"), ("variable_pitch_nozzle", "PV+T")]
rows = []
for bhp, rc, re_ in ((150, C150, E150), (180, C180, E180)):
    for key, lab in combos:
        a, b = rc.performance.windows, re_.performance.windows
        rows.append([f"{bhp} BHP, {lab}",
                     V.fmt(a[f"{key}_std"].max_speed_kn, 2), V.fmt(a[f"{key}_mod"].max_speed_kn, 2),
                     V.fmt(b[f"{key}_std"].max_speed_kn, 2), V.fmt(b[f"{key}_mod"].max_speed_kn, 2)])
V.md_table(["Vessel and propeller", "v* standard, corrected [kn]", "v* modified, corrected [kn]",
            "v* standard, Excel [kn]", "v* modified, Excel [kn]"], rows)
```

Three readings:

* **The propeller matters more than the 30 HP.** With fixed pitch, the 150 HP vessel tows the net
  only up to 2.27 kn, and the 180 HP one up to 2.52 kn. Switching to a controllable pitch propeller
  with nozzle, without touching the engine, takes the limit to 2.97 kn (150 HP) and 3.27 kn
  (180 HP): +0.70 and +0.75 kn, against the +0.25 kn that 30 more HP provide with fixed pitch.
* **The margin is narrow.** The net alone already uses almost all the pull: at 2.5 kn the drag of
  the standard net is 82 % of the total demand and equals 97 % of the PF pull of the 150 HP vessel.
* **The corrected mode is more demanding**: it adds the drag of the two otter boards to the demand
  and corrects the standard codend, which in the Excel workbook appeared heavier than the modified
  one (the speed differences are computed in the table above).

## Standard versus modified net: what the 30 mm codend costs

The modified codend has smaller meshes and more of them (139 × 300 against 113 × 200/250): more
twine in the water per square metre of netting, more solid area and therefore more drag in any
method based on $S_s$.

```{code-cell} ipython3
:tags: [hide-input]
rows = []
for v in (2.0, 2.5, 3.0, 3.5):
    i = I[v]
    rs, rm = C150.drag.rn.std[i], C150.drag.rn.mod[i]
    es, em = E150.drag.rn.std[i], E150.drag.rn.mod[i]
    rows.append([V.fmt(v, 1), V.fmt(rs, 0), V.fmt(rm, 0),
                 f"{V.sfmt(rm - rs, 0)} ({V.pct_s(rm, rs)} %)",
                 f"{V.sfmt(em - es, 0)} ({V.pct_s(em, es)} %)"])
gs, gm = C150.geometry.std.solid_surface_m2, C150.geometry.mod.solid_surface_m2
V.md_table(["v [kn]", "Rₙ standard [kgf]", "Rₙ modified [kgf]",
            "Δ Rₙ corrected [kgf]", "Δ Rₙ Excel [kgf]"], rows)
print(f"Sₛ standard = {V.fmt(gs)} m², Sₛ modified = {V.fmt(gm)} m² ({V.pct_s(gm, gs)} %)")
```

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Difference in net drag (modified − standard) as a function of speed. In corrected mode
      the 30 mm codend costs 3.3 % more; in the Excel workbook, the erratum of the standard codend
      (`codend_minor_side_uses_depth`) reverses the sign and the modified net looks lighter.
    name: fig-30-bolsa
---
fig, ax = plt.subplots(figsize=(7.4, 3.4))
w = 0.18
dc = C150.drag.rn.mod - C150.drag.rn.std
de = E150.drag.rn.mod - E150.drag.rn.std
ax.bar(kn - w / 2, dc, width=w * 0.95, color=V.SERIES[0], label="Corrected", zorder=3)
ax.bar(kn + w / 2, de, width=w * 0.95, color=V.MUTED, label="Excel (with erratum)", zorder=3)
ax.axhline(0, color=V.INK_2, lw=0.8, zorder=4)
for x, y in zip(kn[::2], dc[::2]):
    ax.annotate(V.fmt(y, 0), (x - w / 2, y), xytext=(0, 3), textcoords="offset points",
                ha="center", fontsize=8, color=V.INK_2)
ax.set_xticks(kn)
ax.set_xlabel("Towing speed [kn]")
ax.set_ylabel("Rₙ modified − Rₙ standard [kgf]")
ax.legend(loc="lower left", ncol=2)
fig.tight_layout()
plt.show()
```

In corrected mode the 30 mm codend adds 1.28 m² of solid area (+3.3 %) and, since the Aberdeen
design drag is proportional to $S_s$, the same +3.3 % of $R_N$: ≈ 40 kgf at 2.5 kn and ≈ 68 kgf at
3.5 kn. On the window the effect is small, between −0.04 and −0.05 kn of maximum speed depending on
vessel and propeller. In other words: **retaining squat lobster with the 30 mm codend costs little
in pull**; the limiting factor is still the vessel and its propeller. The original workbook reached
the opposite conclusion (the modified net “has less drag”) because of the erratum of the standard
codend, which counted 200 meshes as the minor side instead of 113.

## Design recommendations

The following recommendations are **model outputs** under the assumptions of this chapter (corrected
mode, Fridman for the pull, Aberdeen demersal for the net, 200 m of warp at 40 m depth). They do not
replace sea trials; {doc}`32_validacion_dynamit` shows that the empirical design drag is ≈ 18 %
above the one simulated by DynamiT, so they are recommendations on the conservative side.

```{code-cell} ipython3
:tags: [hide-input]
# Minimum speed: Fridman's DPA (which grows with v) reaches 85 % of the geometric AH.
ah = C150.spread.horizontal_opening_m
dpa = np.asarray(C150.spread.fridman.dpa_std_m)
v_min = float(np.interp(0.85 * ah, dpa, kn))
fl = C150.floats
unit = fl.catalogue_buoyancy_kgf[fl.catalogue_diameters_mm.index(fl.diameter_mm)]
ws = C150.warps
V.md_table(
    ["Item", "Recommendation (model output)", "Criterion"],
    [
        ["Minimum speed", f"≈ {V.fmt(v_min, 1)} kn",
         f"Fridman DPA ≥ 85 % of AH = {V.fmt(ah, 1)} m"],
        ["Maximum speed, 150 HP", f"PF: {V.fmt(C150.performance.windows['fixed_pitch_mod'].max_speed_kn, 2)} kn · PV+T: "
         f"{V.fmt(C150.performance.windows['variable_pitch_nozzle_mod'].max_speed_kn, 2)} kn", "Fₜ ≥ Rₜ, modified net"],
        ["Maximum speed, 180 HP", f"PF: {V.fmt(C180.performance.windows['fixed_pitch_mod'].max_speed_kn, 2)} kn · PV+T: "
         f"{V.fmt(C180.performance.windows['variable_pitch_nozzle_mod'].max_speed_kn, 2)} kn", "Fₜ ≥ Rₜ, modified net"],
        ["Warp", f"Ø {ws.selection.diameter_mm:.0f} mm ({ws.selection.construction}), "
         f"breaking load {V.fmt(ws.selection.breaking_load_t, 2)} t; {V.fmt(ws.warp_m, 0)} m paid out, "
         f"{V.fmt(ws.quantity_m, 0)} m to buy (2 warps + {V.fmt(ws.quantity_m - 2 * ws.warp_m, 0)} m spare)",
         f"minimum breaking load {V.fmt(ws.loads.min_breaking_load_kgf / 1000, 2)} t (4 × Rₜ at 3.5 kn)"],
        ["Buoyancy", f"{fl.count} floats of {fl.diameter_mm:.0f} mm (≈ {V.fmt(fl.count * unit, 0)} kgf), "
         f"{fl.distribution.per_wing} per wing and {fl.distribution.on_bosom} in the centre",
         f"Fridman, average 1–3 kn: {V.fmt(fl.flotation_rounded_kgf, 0)} kgf"],
        ["Footrope ballast", f"{V.fmt(C150.ballast.limits.min_kg, 0)}–{V.fmt(C150.ballast.limits.max_kg, 0)} kg",
         "Fridman: modified at 1 kn / standard at 3 kn"],
        ["Otter boards", f"FAO flat {V.fmt(C150.case.door.area_m2, 3)} m² at 32° (required ≈ "
         f"{V.fmt(C150.doors.required_area_per_door_class_m2, 2)} m² per board)", "ROB = 20 % of Fₜ, average 2–4 kn"],
    ],
)
```

In words:

1. **Towing speed.** Below ≈ 2.1 kn the net does not fully open horizontally according to Fridman
   (the DPA does not reach 85 % of the geometric opening); above $v^*$ the vessel cannot tow it.
   With **150 HP and fixed pitch the window of the modified net is only 2.1–2.23 kn**: workable, but
   with no reserve for current, sea state or catch in the codend. With a **controllable pitch
   propeller and nozzle** the useful range becomes 2.1–2.9 kn (150 HP) or 2.1–3.2 kn (180 HP), and
   it is the recommended configuration for the modified net.
2. **Warp.** 13 mm 6 × 19 Seale steel wire rope (10.3 t breaking load). The 12 mm one chosen by the
   workbook falls below the minimum breaking load (8.55 t < 10.2 t) once the demand includes the
   otter boards.
3. **Buoyancy.** 12 floats of 200 mm, five per wing and two in the centre of the headrope.
4. **Ballast.** Between 27 and 41 kg of chain spread along the footrope: 27 kg are enough to keep
   the footrope on the seabed at 1 kn with the modified net and 41 kg keep it there at 3 kn with the
   standard one; more ballast only increases friction and makes the footrope “plough” the seabed.
5. **Otter boards.** The 1.805 m² FAO otter board is of the order of the required area
   (≈ 1.8 m² per board): adequate, but with no margin if more spread were wanted.

## Limitations

* **Empirical methods.** The net drag comes from a single formula (Aberdeen demersal) out of the
  thirteen in {doc}`14_resistencia`, whose scatter exceeds ±50 %. The comparison with DynamiT
  ({doc}`32_validacion_dynamit`) suggests that Aberdeen overestimates the drag of this net by
  ≈ 18 %, so the maximum speeds of this chapter are conservative.
* **Fridman pull.** It is a bounded straight line, with no real propeller curve or hull condition;
  the other four schools in {doc}`10_potencia` give pulls up to 2:1 apart at 3 kn.
* **Otter boards in the demand.** The corrected mode adds the drag of the two otter boards to
  $R_T$ (≈ 434 kgf at 3.5 kn); the Excel workbook does not (erratum `warp_total_omits_doors`, see
  the sensitivity analysis in {doc}`19_ventana_velocidad`).
* **Hull and sea state.** The demand does not include the hull resistance $R_H$ nor that of the
  catch in the codend; both narrow the window.
* **Fixed geometry.** The headrope sag uses a fixed $f_L/L = 0.216$ (erratum
  `catenary_ratio_hardcoded`), the door spread is a per-metre-of-warp rule and the warp paid out is
  5 × the depth: the model does not solve the equilibrium of the gear, which is what a simulator such
  as DynamiT does.
* **A single net and a single seabed.** The results hold for the A-3 at 40 m. A different depth
  changes the warp paid out, the door spread and the openings; the case has to be run again.
