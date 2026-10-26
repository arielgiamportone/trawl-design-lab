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

# Validation against the Excel workbook

```{code-cell} ipython3
:tags: [remove-cell]
import sys, pathlib
DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English
import math, json
import numpy as np
import matplotlib.pyplot as plt
from tests.golden_utils import golden, golden_entry, RTOL_EXACT
import _plots_v as V
V.setup_style()
```

## Purpose

`trawlkit` is a **migration**: before correcting or extending the model, one has to show that, with
the same inputs, it returns the same numbers as the workbook `Calculos_Red_FAO_A3.xlsx`. This
chapter describes how that demonstration was done, measures how much of the workbook it covers and
repeats it right here on the full case. The *intentional* differences from the workbook (the errata)
are dealt with in {doc}`erratas`; the comparison with an independent simulator, in
{doc}`32_validacion_dynamit`.

## Method

1. **Reference values.** `tools/extract/golden.py` opens the workbook with `openpyxl` in
   `data_only` mode, that is, it reads the **last value that Excel computed and saved** in each
   cell, not the formula. The reference is thus the number the author saw, errata included. The
   values are stored in `tests/golden/<sheet>.json`, one per sheet, with stable `snake_case` keys:
   scalars in `values` (cell, value, label, unit) and per-speed vectors in `series` (cell range,
   $x$ axis, values).
2. **Flags.** The cells that the workbook has **pasted by hand** instead of computed carry
   `"static": true`: they are summaries copied from other sheets or from another program (DynamiT)
   and cannot be reproduced with formulas, so they **do not count as validation**. The coefficients
   that the workbook extracts from text labels with `MID()` carry `"coerced_from_text": true`,
   because their value depends on the system's decimal separator.
3. **`Compat.EXCEL` mode.** Every comparison is made with the engine in Excel mode, which
   reproduces the errata of the workbook (see {doc}`motor`).
4. **Tolerance.** Relative, $\mathrm{rtol} = 10^{-6}$ (`tests/golden_utils.RTOL_EXACT`): it is
   stricter than any engineering rounding, and only lets floating-point differences through (order
   of sums, `0.5144` versus `0.514`, powers). The tolerance `RTOL_TRUNCATED = 1e-3` foreseen for
   the values truncated by `MID()` was not needed: the engine reproduces the exact truncation.
5. **Three levels of tests.** Per function (each block of formulas fed with the golden inputs of its
   preceding cells), end to end (`tests/test_case_fao_a3.py`: the full case, with no intermediate
   inputs, for 150 and 180 BHP) and corrected mode (`tests/test_corrected_mode.py`). The full suite
   has about 1,200 tests and runs in ≈ 15 s.

## Coverage by sheet

How many of the golden values are actually verified by some test? The next cell measures it by
reading the JSON files and looking for each key in the test code (`tests/test_*.py`, excluding
`test_golden.py`, which only validates the structure of the JSON files). A key counts as verified if
it appears as a literal string or if it matches a template of a parametrized test, for example
`f"summary_{column}_{variant}_t"` or `"fridman_summary_fixed_{hp}_kgf"`; so as not to inflate the
count, the template must have at least five fixed letters.

```{code-cell} ipython3
:tags: [hide-input]
cov = V.golden_coverage()  # one row per JSON in tests/golden
rows = []
for r in cov:
    p = r["tested"] / r["computed"] * 100
    rows.append([r["sheet"], r["keys"], r["series"], r["static"], r["computed"],
                 r["tested_literal"], r["tested"], V.fmt(p, 0) + " %"])
tot = {k: sum(r[k] for r in cov) for k in ("keys", "series", "static", "computed",
                                            "tested_literal", "tested")}
p_tot = tot["tested"] / tot["computed"] * 100
p_lit = tot["tested_literal"] / tot["computed"] * 100
rows.append(["**Total**", f"**{tot['keys']}**", f"**{tot['series']}**", f"**{tot['static']}**",
             f"**{tot['computed']}**", f"**{tot['tested_literal']}**", f"**{tot['tested']}**",
             f"**{V.fmt(p_tot, 1)} %**"])
V.md_table(["Sheet", "Keys", "of which series", "Static", "Computed",
            "In tests (literal)", "In tests (with templates)", "Coverage"], rows)
```

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Coverage of the computed golden values by the engine tests, per sheet of the workbook.
      Blue: key named literally in a test; light blue: covered by a parametrized test
      (template); grey: not referenced. Static cells (pasted by hand) are excluded.
    name: fig-31-cobertura
---
order = sorted(cov, key=lambda r: r["tested"] / r["computed"])
y = np.arange(len(order))
lit = np.array([r["tested_literal"] / r["computed"] for r in order]) * 100
tpl = np.array([(r["tested"] - r["tested_literal"]) / r["computed"] for r in order]) * 100
rest = 100 - lit - tpl
fig, ax = plt.subplots(figsize=(8.2, 4.6))
ax.barh(y, lit, color=V.BLUE_450, height=0.68, label="literal", zorder=3)
ax.barh(y, tpl, left=lit, color=V.BLUE_150, height=0.68, label="template", zorder=3)
ax.barh(y, rest, left=lit + tpl, color=V.GRID, height=0.68, label="no test", zorder=3)
for yi, r in zip(y, order):
    ax.annotate(f"{r['tested']}/{r['computed']}", (100, yi), xytext=(6, 0),
                textcoords="offset points", va="center", fontsize=8.5, color=V.INK_2,
                annotation_clip=False)
ax.set_yticks(y, [r["sheet"] for r in order])
ax.set_xlim(0, 100)
ax.set_xlabel("Computed golden keys [%]")
ax.grid(axis="y", visible=False)
ax.legend(loc="lower center", bbox_to_anchor=(0.45, 1.0), ncol=3)
fig.tight_layout()
plt.show()
```

```{code-cell} ipython3
:tags: [hide-input]
def kind(slug, k):
    v = golden(slug, k)
    return "text" if isinstance(v, str) else "number"

miss = [(r["slug"], k) for r in cov for k in r["untested_keys"]]
n_txt = sum(kind(s, k) == "text" for s, k in miss)
by_sheet = {}
for s, k in miss:
    by_sheet.setdefault(V.SHEET_NAMES[s], []).append(k)
V.md_table(["Sheet", "Keys without a test", "Examples"],
           [[h, len(ks), ", ".join(ks[:4]) + (" …" if len(ks) > 4 else "")]
            for h, ks in sorted(by_sheet.items(), key=lambda t: -len(t[1]))])
print(f"{len(miss)} computed keys without a test ({n_txt} are texts).")
print(f"Total coverage {V.fmt(p_tot, 1)} % ({V.fmt(p_lit, 1)} % with literal names only).")
```

Coverage is complete or almost complete in the calculation sheets proper —power, drag, net
mechanics, dimensions, otter boards, buoyancy and warps—, which are the ones that define the design.
The gaps are concentrated in three groups that **are not model results**:

* **Inputs and catalogues.** *Tablas de Referencias* [reference tables], the netting tables of
  *Paños de red y cortes* [netting panels and cuts] (`netting_80mm_*`, …), *Especie Blanco* [target
  species] and *Tipo de buques* [vessel types] are data. They are validated another way:
  `tools/extract` dumps them to `src/trawlkit/data/*.yaml` and `src/trawlkit/data/reference/*.csv`,
  and `tests/test_data_*.py` checks those files against the workbook, not against the golden JSON.
* **Conversions and texts.** The powers in kW of *Potenc disponible* [available power]
  (`nominal_kw_150`, …), the labels (`bottom_type`, `headrope_material`) and repeated physical
  constants (`gravity_m_s2`).
* **Intermediate values per panel** of *Paños de red y cortes* (stretched lengths, area and number
  of meshes per panel) that the engine computes but that the tests verify through the totals and
  the solid area.

## End-to-end check

The most demanding test is to run the full case —standard and modified net, 150 BHP vessel with the
180 BHP one in the class, FAO otter board— without any intermediate input, and compare the final
results of each sheet with the workbook. This is what `tests/test_case_fao_a3.py` does with about
120 keys; here it is repeated with a selection of thirteen.

```{code-cell} ipython3
r = V.run_case(150, "excel")
DIM, MEC = "dimensiones_de_la_red", "mecanica_de_la_red"
RES, PORT = "resistencia_de_la_red", "portones_y_aparejamiento"
FLOT, REM = "flotacion_y_lastre", "cables_de_remolque"
POT = "potencia_disponible_arrastre_ok"
checks = [
    (DIM, "footrope_m", r.dimensions.std.footrope_m),
    (DIM, "solid_surface_std_m2", r.geometry.std.solid_surface_m2),
    (DIM, "horizontal_opening_m", r.spread.horizontal_opening_m),
    (POT, "fridman_summary_fixed_150_kgf", r.power.fridman.ft_fixed_pitch_kgf),
    (RES, "aberdeen_demersal_rn_std_t", r.drag.table.design_rn("std")),
    (RES, "dickson_rn_std_t", r.drag.table.std["dickson"]),
    (MEC, "dpa_fridman_std_m", r.spread.fridman.dpa_std_m),
    (MEC, "av_fridman_std_m", r.spread.vertical.fridman.std.av_m),
    (PORT, "door_spread_m", r.doors.spread_m),
    (FLOT, "flotation_total_rounded_kgf", r.floats.flotation_rounded_kgf),
    (FLOT, "ballast_std_150_kg", r.ballast.fridman.std),
    (REM, "total_drag_std_kgf", r.warps.total.std),
    (REM, "warp_min_breaking_load_kgf", r.warps.loads.min_breaking_load_kgf),
]
SUP = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")
PREFIX = {DIM: "Dim", MEC: "Mec", RES: "Res", PORT: "Port", FLOT: "Flot", REM: "Rem",
          POT: "PotOK"}
rows = []
for slug, key, got in checks:
    ref = np.asarray(golden(slug, key), dtype=float)
    got = np.asarray(got, dtype=float)
    assert np.allclose(got, ref, rtol=RTOL_EXACT, atol=0), (slug, key)
    err = np.max(np.abs(got - ref) / np.maximum(np.abs(ref), 1e-300))
    e = golden_entry(slug, key)
    cell = e.get("cell", e.get("cells"))
    pick = (lambda a: float(a)) if got.ndim == 0 else (lambda a: float(a[4]))  # series: 3 kn
    m, ex = f"{err:.0e}".split("e")
    err_s = "0" if err == 0 else f"{m}·10{str(int(ex)).translate(SUP)}"
    rows.append([f"{PREFIX[slug]}!{cell}", key, V.fmt(pick(got), 3), V.fmt(pick(ref), 3), err_s])
V.md_table(["Cell(s)", "Golden key", "trawlkit", "Excel", "Rel. error"], rows)
```

The series are shown at 3 kn, but they are compared at all nine speeds. The thirteen comparisons
pass with relative errors of zero or of the order of $10^{-16}$, that is, in the last bit of the
mantissa: the engine reproduces the workbook to **machine precision**, not only to engineering
precision.

## What this validation does not show

* **That the workbook is right.** It was validated against the numbers of the workbook, errata
  included; the corrected differences are in {doc}`erratas`.
* **The static values.** The 33 keys pasted by hand (“worst/best case” power summaries, summary of
  vertical openings, DynamiT column in the drag sheet) cannot be recomputed. The tests mention them
  only to document that they do not match the formulas or to expose them as an external reference
  (DynamiT, {doc}`32_validacion_dynamit`).
* **Other cases.** The validation is for the FAO A-3 net with the two vessels of the workbook. That
  the engine works for other nets and vessels rests on the fact that it reproduces the workbook
  formula by formula, not a fit: changing an input follows exactly the same path as in the
  workbook.
