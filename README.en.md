# trawl-design-lab · `trawlkit`

[Versión en español](https://github.com/arielgiamportone/trawl-design-lab/blob/main/README.md)

Calculation engine, HTTP API and scientific documentation for **trawl net design and sizing**.
It evolves the FAO A-3 bottom-trawl model originally built in Excel for 150-180 HP vessels in the
Beagle Channel ([original repo](https://github.com/arielgiamportone/Trawl_net_model_in_Advanced_Excel))
into reproducible, tested software that generalises to any panel-defined net.

## Try it online

- Book: https://arielgiamportone.github.io/trawl-design-lab/
- Web app: https://arielgiamportone.github.io/trawl-design-lab/app/
- API (interactive docs): https://trawl-design-lab-api.onrender.com/docs

They work once GitHub Pages (source "GitHub Actions") is enabled and the Render service is created
from `render.yaml` ([docs/despliegue.md](https://github.com/arielgiamportone/trawl-design-lab/blob/main/docs/despliegue.md), in Spanish). The API runs on Render's
free plan, so the first request after a period of inactivity can take up to a minute.

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

Phase 3 adds reports and drawings: `trawlkit report NET --modified NET2 --vessel ID --out DIR`
writes a self-contained Spanish HTML report, a PDF (WeasyPrint), an XLSX workbook and SVG drawings
(an A3 technical sheet replicating the 2014 plans and a true-scale metric view);
`trawlkit plan` writes a single drawing. Generated examples live in `examples/`.

Phase 6 adds design optimisation (`trawlkit optimize`, `POST /optimize`): net scale and towing
speed maximising swept area or filtered volume, or minimising towing work per m² swept, under
thrust, net-opening, warp and door constraints, with a feasibility map and Pareto front.
Phase 7 adds an experimental quasi-static net-shape simulation (`trawlkit.sim`, `POST /simulate`):
Priour triangular netting elements with Morison drag, ropes, floats, ballast, bridles, sweeps and
seabed contact, solved by FIRE dynamic relaxation. Against DynamiT it matches the horizontal
opening within 3 % (2–4 kn) but under-predicts net drag by ≈ 50 % (book chapter 21). Both are in
the web app ("Optimizar" and "Simulación" tabs) and in the report
(`trawlkit report ... --optimize area --simulate 2,3`).
