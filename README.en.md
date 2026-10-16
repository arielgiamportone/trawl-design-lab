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

The original workbook contains documented calculation errata (`docs/erratas.md`). Every affected
function takes `compat=Compat.EXCEL` (reproduces the original figure, used to validate the
migration) or `compat=Compat.CORRECTED` (correct formula, default).

```bash
uv sync --all-extras --dev
uv run pytest
uv run trawlkit errata
```

Code is MIT-licensed; documentation, data and legacy material are CC BY 4.0.
