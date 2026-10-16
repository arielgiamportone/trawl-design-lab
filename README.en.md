# trawl-design-lab · `trawlkit`

[Versión en español](README.md)

Calculation engine, HTTP API and scientific documentation for **trawl net design and sizing**.
It evolves the FAO A-3 bottom-trawl model originally built in Excel for 150-180 HP vessels in the
Beagle Channel ([original repo](https://github.com/arielgiamportone/Trawl_net_model_in_Advanced_Excel))
into reproducible, tested software that generalises to any panel-defined net.

Calculation chain: available towing power (Fridman, Prado-Dremière, Koyama, Nomura, Hamuro) →
netting panels and cuts → net mechanics (filtration index, twine and working areas, solidity, weight)
→ dimensions → net drag (13 empirical methods) → doors and bridles → wing-end spread and vertical
opening → floats and ballast → warps → feasible towing-speed window.

Phase 2 is complete: every sheet is reimplemented as a module (`net`, `dimensions`, `power`,
`drag`, `rigging.*`, `performance`) and `trawlkit.model.run(DesignCase)` chains them in the
workbook's dependency order, reproducing the Excel figures to `rtol = 1e-6` in `Compat.EXCEL`
(`tests/test_case_fao_a3.py`). See `docs/motor.md` for the architecture and stage order.

The original workbook contains documented calculation errata (`docs/erratas.md`). Every affected
function takes `compat=Compat.EXCEL` (reproduces the original figure, used to validate the
migration) or `compat=Compat.CORRECTED` (correct formula, default).

```bash
uv sync --all-extras --dev
uv run pytest
uv run trawlkit errata
uv run trawlkit run fao_a3_standard --modified fao_a3_modified --class-vessel fao_a3_180hp --json case.json
```

```python
from trawlkit import DesignCase, run
from trawlkit.io import load_doors, load_net, load_vessels

result = run(
    DesignCase(load_net("fao_a3_standard"), load_vessels().vessels[0], load_doors().doors[0])
)
result.summary()  # headrope, footrope, Ss, St, AV, AH, floats, ballast, warp, max towing speed
```

Code is MIT-licensed; documentation, data and legacy material are CC BY 4.0.
