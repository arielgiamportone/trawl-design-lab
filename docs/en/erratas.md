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

# Errata of the original Excel model

During the migration the ~5,500 formulas of the workbook `Calculos_Red_FAO_A3.xlsx` were audited.
The following errata are reproduced in `Compat.EXCEL` mode (to validate the migration) and
corrected in `Compat.CORRECTED` mode. The canonical list lives in `trawlkit.compat.ERRATA`; the
*Implementation* column gives the function that switches with `compat` and the test that checks
both directions (`tests/test_corrected_mode.py` does so at the level of the complete case,
`trawlkit.model.run`).

| Key | Sheet | Cell | Description | Implementation (function · test) |
|---|---|---|---|---|
| cut_ratio_first_panel | Paños de red y cortes [netting panels and cuts] | H274:I277 | All panels use the cutting ratio of the first one | `netting.mean_cut_angle_deg` · `test_netting.py` |
| twine_density_units | Paños de red y cortes | L55 | Dimensionally incorrect twine density | `materials.twine_density_kg_m3`, `net.analyse` · `test_net.py`, `test_netting.py` |
| filtration_double_count | Mecánica de la Red [net mechanics] | J17 | J16 counted twice | `net.filtration_index` · `test_net.py` |
| hamuro_sin_degrees | Resistencia de la RED [net drag] | D113 | SIN(DEGREES) instead of SIN(RADIANS) | `drag.hamuro_sin_alpha` · `test_drag.py`, `test_corrected_mode.py` |
| hamuro_mod_uses_std_dl | Resistencia de la RED | E117 | Modified variant uses the d/l of the standard net | `drag.drag_table` · `test_drag.py`, `test_corrected_mode.py` |
| reid_fixed_denominator | Resistencia de la RED | C154:C162 | Denominator fixed at 1 knot | `drag.reid` · `test_drag.py`, `test_corrected_mode.py` |
| drag_average_pollution | Resistencia de la RED | R302:R310 | Average includes Nomura's speed and pull | `drag.average` · `test_drag.py`, `test_corrected_mode.py` |
| door_force_mixed_angles | Portones y aparejamiento [otter boards and rigging] | D252 | Mixes degrees and radians | `rigging.doors.door_force_kgf` · `test_rigging_doors.py`, `test_corrected_mode.py` |
| float_reynolds | Flotación y Lastre [buoyancy and ballast] | H138 | Re = π·D²·v/ν instead of v·D/ν | `rigging.floats.float_reynolds` · `test_rigging_floats.py`, `test_corrected_mode.py` |
| warp_total_omits_doors | Cables de Remolque [warps] | H118 | Omits the drag of the otter boards | `rigging.warps.total_drag_kgf` (→ `model._stage_warps`, `_stage_performance`) · `test_rigging_warps.py`, `test_corrected_mode.py` |
| warp_cd_horizontal_angle | Cables de Remolque | E103:E106 | Warp CD taken with the plan-view divergence δ2 = 4.3° (→ 0.02) instead of the angle of attack to the flow, and nearest row without interpolation | `rigging.warps.warp_attack_angle_deg`, `rigging.warps.warp_cd(interpolate=…)` (→ `model._stage_warps`) · `test_corrected_mode.py` |
| warp_undersized | Cables de Remolque | E267:E272 | 12 mm warp (8.55 t) < 8.8 t required | `rigging.warps.select_warp` · `test_rigging_warps.py`, `test_corrected_mode.py` |
| mod_length_wrong_rows | Dimensiones de la Red [net dimensions] | G48 | Length of the modified net adds the wrong rows | `dimensions.body_length_no_bag_m` · `test_dimensions.py` |
| footrope_mid_truncation | Dimensiones de la Red | F46 | MID() truncates the footrope to 33.3 m (full value 33.389 m) | `dimensions.footrope_length_m` · `test_dimensions.py`, `test_corrected_mode.py` |
| dpa_std_uses_mod_edy | Mecánica de la Red | P164 | Standard Fridman DPA uses the Edy of the modified net | `rigging.spread.fridman_spread` · `test_rigging_spread.py`, `test_corrected_mode.py` |
| nomura_column_links_hamuro | Potencia Disponible Arrastre OK [available towing power] | G319, G342, G362 | "Nomura" column links to Hamuro | no switch: `power.power_curves` computes Nomura for real; the link is documented in `test_power.py` |
| sweep_degrees_of_sine | Portones y aparejamiento | G71 | DEGREES(SIN(20)) and precedence error | `rigging.bridles.sweeps_martini_m` · `test_rigging_bridles.py` |
| nomura_ratio_typo | Tablas de Referencias [reference tables] | G18, G21 | 10.6 where 1.06 is meant | no switch: the table is copied as is to `src/trawlkit/data/reference/nomura_proportions.csv` (`test_data_reference.py`) |
| panel_f_cut_na | Paños de red y cortes | T122 | Cutting ratio of panel F returns #N/A | `netting.cut_code` computes the code the workbook could not · `test_netting.py` |
| codend_minor_side_uses_depth | Mecánica de la Red | K36:K37 | Codends I/J use N (200) as the minor side instead of T2 (113): Ss 40.90 instead of 38.75 m² | `net.apply_excel_codend_quirk` (via `net.analyse`) · `test_net.py`, `test_corrected_mode.py` |
| panel_b_cut_uses_plan_coef | Paños de red y cortes | S62 | Cutting ratio of panel B with the plan coefficient instead of N | no switch: `netting.cut_ratio` uses N; the workbook's value is kept only in the golden file (`test_netting.py`) |
| panel_b_cut_code_lookup_a | Paños de red y cortes | T62 | Cut code of panel B looked up with the ratio of panel A | no switch: `netting.cut_code` looks up with the panel's own ratio (`test_netting.py`) |
| net_weight_ignores_panel_count | Mecánica de la Red | O107, O109 | Total weight not multiplied by the number of panels | `net.analyse` (in CORRECTED each row weighs by its number of panels: air, water and distribution by plane) · `test_net.py`, `test_corrected_mode.py` |
| catenary_ratio_hardcoded | Mecánica de la Red | O266 | fL/L = 0.216 fixed, outside the range of the table | `DesignCase.catenary_ratio` (0.216 in both modes; `rigging.spread.catenary_ratio` gives the table value and `run` records it in `notes`) · `test_rigging_spread.py` |
| float_lookup_unsorted | Flotación y Lastre | F92 | LOOKUP over an unsorted vector | `rigging.floats.float_diameter_for_count_mm` (EXCEL) / float with the nearest number in `model._stage_floats` (CORRECTED) · `test_rigging_floats.py`, `test_case_fao_a3.py` |
| flotation_rounding_inconsistent | Flotación y Lastre | M43:M50 | Rounding applied to only part of the column | `rigging.floats.flotation_fridman(rounddown=…)`, mask in `model._stage_floats` · `test_rigging_floats.py`, `test_corrected_mode.py` |
| door_area_power_extrapolation | Portones y aparejamiento | F212, F215 | Required area linear in power, calibrated for 150–180 HP and extrapolated to more powerful vessels | `rigging.door_area_power_factor`, `rigging.required_area_summary(bhp=…)` (→ `model._stage_doors`, `door_selection.select_doors`, `optimize.evaluate`) · `test_door_area_power.py`, `test_door_polars.py` |
| fridman_dp_warp_saturation | Mecánica de la Red | P164:Q172 | Fridman's wing spread saturates with the warp: with a warp other than the table's, DS changes less than measured | `rigging.dp_warp_factor` (factor $(L_s/L_{s,table})^{\Delta n}$, 1 with the table warp) in `rigging.fridman_spread(warp_factor=…)` (→ `model.fridman_door_spread_m`, `model._stage_spread`) · `test_calibration_20_5.py` |

In addition, several summary tables contain values pasted by hand instead of formulas (marked
with `"static": true` in `tests/golden/*.json`), and the coefficients read with `MID()` from text
labels depend on the locale (marked with `"coerced_from_text": true`).

Two couplings of the workbook that are not errata but condition a design case are exposed as
fields of `DesignCase`: the total buoyancy `Ffz` (`Mec!O261`) averages the 150 and 180 HP blocks
(`class_vessels`) and the warp is sized with the NHP of 180 HP (`Rem!E110 = E81`, `warp_nhp_hp`,
by default the largest BHP of the class).

## Impact of the errata

How much does each erratum move the design? The following table runs the workbook's complete
case (standard and modified net, 150 BHP vessel with the 180 BHP one in the class, FAO otter
board; see {doc}`30_caso_beagle`) in both modes and compares the output affected by each
switchable erratum. Since the mode is global, each row mixes the effect of its erratum with that
of the errata upstream; the *Carries* column indicates it where applicable (for example, all drag
based on the area of the standard net carries the −5.2 % of $S_s$ from the codend erratum).

```{code-cell} ipython3
:tags: [remove-input]
import sys, pathlib
DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English
import numpy as np
from tests.golden_utils import golden
from trawlkit.compat import ERRATA_BY_KEY
from trawlkit.model import dp_warp_factor
import _plots_v as V

E, C = V.run_case(150, "excel"), V.run_case(150, "corrected")
i = E.case.speed_index
SS = "codend_minor_side_uses_depth"
rows_def = [
    # (erratum, output, function of the result, decimals, unit, carries)
    (SS, "Standard Sₛ", lambda r: r.geometry.std.solid_surface_m2, 2, "m²", ""),
    ("twine_density_units", "Standard weight in air, one panel per row",
     lambda r: sum(g.weight_air_kg / (g.row.count if r.case.compat.value == "corrected" else 1)
                   for g in r.geometry.std.rows), 1, "kg", SS),
    ("net_weight_ignores_panel_count", "Standard weight in air",
     lambda r: r.geometry.std.weight_air_kg, 1, "kg", "twine_density_units"),
    ("filtration_double_count", "d/l modified net", lambda r: r.geometry.mod.filtration_index, 4, "", ""),
    ("footrope_mid_truncation", "Footrope", lambda r: r.dimensions.std.footrope_m, 3, "m", ""),
    ("hamuro_sin_degrees", "Hamuro Rₙ at 3 kn",
     lambda r: r.drag.table.std["hamuro"][i(3.0)] * 1000, 0, "kgf", SS),
    ("hamuro_mod_uses_std_dl", "Hamuro Rₙ modified at 3 kn",
     lambda r: r.drag.table.mod["hamuro"][i(3.0)] * 1000, 0, "kgf", "hamuro_sin_degrees"),
    ("reid_fixed_denominator", "Reid Rₙ at 5 kn",
     lambda r: r.drag.table.std["reid"][i(5.0)] * 1000, 0, "kgf", SS),
    ("drag_average_pollution", "Average of methods at 3 kn",
     lambda r: r.drag.average.std[i(3.0)] * 1000, 0, "kgf", "several"),
    ("dpa_std_uses_mod_edy", "Fridman DPA at 1 kn",
     lambda r: r.spread.fridman.dpa_std_m[0], 2, "m", SS),
    ("door_force_mixed_angles", "Otter board force at 3 kn",
     lambda r: r.doors.force_kgf[i(3.0)], 1, "kgf", ""),
    ("float_reynolds", "Float Reynolds number at 3 kn", lambda r: r.floats.reynolds[i(3.0)], 0, "", ""),
    ("flotation_rounding_inconsistent", "Fridman buoyancy",
     lambda r: r.floats.fridman_average_kgf, 2, "kgf", SS),
    ("warp_cd_horizontal_angle", "Warp CD", lambda r: r.warps.cd, 3, "", ""),
    ("warp_cd_horizontal_angle", "Warp drag at 3.5 kn",
     lambda r: r.warps.drag_kgf[i(3.5)], 1, "kgf", ""),
    ("warp_total_omits_doors", "Rₜ at 3.5 kn",
     lambda r: r.warps.total.std[i(3.5)], 0, "kgf", SS),
    ("warp_total_omits_doors", "Minimum breaking load of the warp",
     lambda r: r.warps.loads.min_breaking_load_kgf, 0, "kgf", SS),
    ("warp_undersized", "Warp",
     lambda r: r.warps.selection.diameter_mm, 0, "mm", "warp_total_omits_doors"),
    ("sweep_degrees_of_sine", "Martini sweeps", lambda r: r.bridles.sweeps_martini_m, 2, "m", ""),
    ("warp_total_omits_doors", "v* (150 HP, FP)",
     lambda r: r.performance.design.max_speed_kn, 2, "kn", "all"),
]
CARRY = {SS: "codend Sₛ", "hamuro_sin_degrees": "Hamuro sine",
         "twine_density_units": "twine density",
         "warp_total_omits_doors": "Rₜ with otter board"}
rows = []
for key, label, f, nd, unit, carry in rows_def:
    a, b = float(f(E)), float(f(C))
    assert key in ERRATA_BY_KEY, key
    rows.append([key.replace("_", "_​"), label + (f" [{unit}]" if unit else ""),
                 V.fmt(a, nd), V.fmt(b, nd), V.pct_s(b, a), CARRY.get(carry, carry)])
V.md_table(["Erratum", "Affected output", "Excel", "Corrected", "Change [%]", "Carries"], rows)
assert E.dimensions.std.footrope_m == golden("dimensiones_de_la_red", "footrope_m")
```

Other switchable errata **do not change** this case because the FAO A-3 net and its 150 HP vessel
do not trigger them:

```{code-cell} ipython3
:tags: [remove-input]
nulls = [
    ("cut_ratio_first_panel", "Mean cutting angle [°]", lambda r: r.dimensions.std.cut_angle_deg,
     "all panels of the top plan have a 1N2B cut"),
    ("mod_length_wrong_rows", "Length of the modified net without codend [m]",
     lambda r: r.dimensions.mod.body_length_no_bag_m, "both plans measure 32.68 m without the codend"),
    ("float_lookup_unsorted", "Float diameter [mm]", lambda r: r.floats.diameter_mm,
     "the unsorted LOOKUP lands on the 200 mm float, the nearest one"),
    ("door_area_power_extrapolation", "Required area per otter board [m²]",
     lambda r: r.doors.required_area.per_door_m2, "150 HP does not exceed the design power (180 HP)"),
    ("fridman_dp_warp_saturation", "Warp factor of Fridman's wing spread",
     lambda r: dp_warp_factor(r.case, r.rigging), "the case uses the book's table warp"),
]
rows = []
for key, label, f, why in nulls:
    a, b = f(E), f(C)
    assert a == b, key
    nd = 0 if float(a).is_integer() else 2
    rows.append([key.replace("_", "_​"), label, V.fmt(a, nd), V.fmt(b, nd), why])
V.md_table(["Erratum", "Output", "Excel", "Corrected", "Why it does not change"], rows)
```

Three orders of magnitude:

* **Errata that change a decision.** `warp_total_omits_doors` and `warp_undersized` change the
  warp from 12 to 13 mm: with the otter boards included, the 12 mm one falls below the minimum
  breaking load. `codend_minor_side_uses_depth` reverses the comparison between the standard and
  the modified net ({doc}`30_caso_beagle`) and is the one with the widest reach: the −5.2 % of
  $S_s$ propagates to the design drag, the DPA, the Fridman buoyancy and the total demand.
* **Errata that greatly change a number that is not used for design.** Reid (−59 % at 5 kn), the
  Martini sweeps (+77 %), the float Reynolds number (+59 %) and the weight of the net (−29 % per
  panel with the corrected density, +18 % in total when all panels are counted) change sharply,
  but none of them feeds another stage: the drag coefficient of the float does not depend on the
  computed Reynolds number and the workbook uses the design sweeps (25 m) instead of Martini's.
  The drag of the warps (+170 % with the real angle of attack) does enter the demand, but it is
  less than 2 % of $R_T$.
* **Minor errata.** The footrope (+0.27 %), the force on the otter board (+1.8 %) or the average
  of methods (+0.7 %) stay below the uncertainty of any empirical method.

The maximum speed, which sums up the design, moves little (−7 %, −0.17 kn): the corrections that
increase the demand (otter boards, warps) and those that reduce it (solid area) partly offset
each other.

## Otter-board area above the book's power

The erratum `door_area_power_extrapolation` is not a mistyped formula: it is a rule used outside
its range. The book's required area (`Port!F212`, `F215`; {doc}`15_portones_aparejo`) takes 20 % of
the available pull and divides it by $(\rho/g)\,C_D\,v^2$, so it grows in proportion to power.
Calibrated for the 150 and 180 HP A-3 vessels and extrapolated to the Argentine fleet, it asks for
otter boards of 23 to 46 m² (2100–4159 BHP): more than the largest published board (21.34 m²), and
4 to 7 times the real boards of the research vessels. Otter-board tables grow as power to the 0.65:
the fit of the *Workbook* table {cite:p}`prado1990` gives 0.646, and that of the Fishbuster table
{cite:p}`netsystems_fishbuster`, 0.656. In corrected mode, above 180 BHP, the area is multiplied by
$(180/\mathrm{BHP})^{0.35}$; in `EXCEL` mode and up to 180 BHP the factor is 1, so the book's case
and its golden values do not change.

The table below is the default case of every fleet vessel ({doc}`39_flota_argentina`; A-3 net and
A-3 flat board at 32°), with the area per otter board by the book rule and by the corrected one.
The *Fishbuster* column gives the sizes of that table whose power range overlaps the vessel's
(±5 %). The real boards are those documented by INIDEP: 5.58 m² on the Holmberg
{cite:p}`tringali2012eh0612`, the same gear on the Oca Balda {cite:p}`dato2013global`, and the
4.5 m² Morgère SPF08 on the Angelescu {cite:p}`roth2017angelescu` (now a 4.8 m² SPF 08,5,
{cite:p}`rubio2024calibracion`). A commercial freezer trawler of the fleet, the «Beagle I», uses
2300 kg Polar Mercury boards; by Polar's table they would be about 7–8 m², but the report does not
give the area.

```{code-cell} ipython3
:tags: [remove-input]
import _door_area as DA

V.md_table(DA.TABLE_HEADERS, DA.table_rows())
```

The corrected area falls inside the Fishbuster range or up to 33 % above it (the test
`test_door_area_power.py` allows up to 35 %). With the book rule, the vessels above 1300 BHP were
2.6 to 3.7 times the top of the table. For the research vessels the corrected area is still an
upper bound: they tow a standard survey net well below their full pull.

## Saturation of Fridman's wing spread with the warp

The erratum `fridman_dp_warp_saturation` is not a mistyped formula either: in Fridman's wing
spread (`Mec!P164`, {doc}`16_aberturas`) the horizontal warp $L_{sh}$ is above and below the
fraction, $2 L_{sh} L_{Rw} E_{dy} / (L_{sh} + L_{nc}(1 + E_{dx}))$, so with a long warp the door
spread hardly changes. At sea it keeps growing ({doc}`32_validacion_merluza`). In corrected mode the
wing spread is multiplied by $(L_s/L_{s,table})^{\Delta n}$, with $L_{s,table}$ the book's table
warp for the depth and $\Delta n$ fitted to 103 measured hauls with published warp (*calibrated*
provenance). With the table's warp the factor is 1: the book's case, its golden values and every
design case do not change; it only acts with a measured warp (`DesignCase.measured_warp_m`).

```{code-cell} ipython3
:tags: [remove-input]
from trawlkit import rigging
from trawlkit.compat import Compat

DN = rigging.DP_WARP_EXPONENT_CORRECTION
rows = []
for depth in (40.0, 100.0, 400.0):
    tab = rigging.table_warp_m(depth)
    for k in (0.5, 1.0, 1.5, 2.0):
        w = k * tab
        rows.append([V.fmt(depth, 0), V.fmt(w, 0), V.fmt(k, 1),
                     V.fmt(rigging.dp_warp_factor(w, depth), 3),
                     V.fmt(rigging.dp_warp_factor(w, depth, Compat.EXCEL), 3)])
print(f"Δn = {DN:.2f}")
V.md_table(["Depth [m]", "Warp [m]", "Warp / table", "Factor (corrected)", "Factor (Excel)"],
           rows)
```
