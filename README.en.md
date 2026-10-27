<p align="center">
  <img src="https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/docs/_static/img/banner-en.svg" alt="trawl-design-lab · trawlkit: trawl net design, born in UTN Fisheries Engineering (FRTDF, FRCh and FRMDP)" width="100%">
</p>

<p align="center">
  <a href="https://github.com/arielgiamportone/trawl-design-lab/actions/workflows/ci.yml"><img src="https://github.com/arielgiamportone/trawl-design-lab/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/arielgiamportone/trawl-design-lab/actions/workflows/docs.yml"><img src="https://github.com/arielgiamportone/trawl-design-lab/actions/workflows/docs.yml/badge.svg" alt="Docs"></a>
  <a href="https://pypi.org/project/trawlkit/"><img src="https://img.shields.io/pypi/v/trawlkit" alt="PyPI"></a>
  <a href="https://pypi.org/project/trawlkit/"><img src="https://img.shields.io/pypi/pyversions/trawlkit" alt="Python"></a>
  <a href="https://github.com/arielgiamportone/trawl-design-lab/blob/main/LICENSE"><img src="https://img.shields.io/badge/code-MIT-blue" alt="Code: MIT"></a>
  <a href="https://github.com/arielgiamportone/trawl-design-lab/blob/main/LICENSE-docs"><img src="https://img.shields.io/badge/docs%20%26%20data-CC%20BY%204.0-blue" alt="Docs and data: CC BY 4.0"></a>
  <a href="https://arielgiamportone.github.io/trawl-design-lab/en/"><img src="https://img.shields.io/badge/book-Jupyter%20Book-c35a1b" alt="Book"></a>
  <a href="https://arielgiamportone.github.io/trawl-design-lab/app/"><img src="https://img.shields.io/badge/app-works%20offline-2e7d32" alt="App: works offline"></a>
  <a href="https://doi.org/10.5281/zenodo.23657981"><img src="https://zenodo.org/badge/DOI/10.5281/zenodo.23657981.svg" alt="DOI 10.5281/zenodo.23657981"></a>
  <a href="https://arielgiamportone.github.io/trawl-design-lab/citar.html"><img src="https://img.shields.io/badge/how%20to-cite-6a4c93" alt="How to cite"></a>
</p>

<p align="center"><a href="https://github.com/arielgiamportone/trawl-design-lab/blob/main/README.md">Versión en español</a></p>

**trawl-design-lab** is an open laboratory to **design, size and test trawl nets**: a Python
calculation engine (`trawlkit`), a web app that works on a phone even without signal, an HTTP API
and a reproducible book with the theory. It is meant for fishers and skippers, net makers,
fishing schools, and fisheries students and engineers: choose the net a vessel can tow, at what
speed, with which doors, warps and floats, and what it costs to rig it with what the port sells.
The app and the book are in English and Spanish; the code comments are in Spanish.

| Try it | |
|---|---|
| 📱 Web app (installable, offline) | https://arielgiamportone.github.io/trawl-design-lab/app/ |
| 📘 Book (Jupyter Book, English) | https://arielgiamportone.github.io/trawl-design-lab/en/ |
| 📗 Book (Spanish original) | https://arielgiamportone.github.io/trawl-design-lab/ |
| 🔌 API (interactive docs) | https://trawl-design-lab-api.onrender.com/docs |

The API runs on Render's free plan: after a period of inactivity it sleeps and the first request
can take up to a minute (meanwhile the app uses the on-phone engine).

## Born at UTN

<img src="https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/docs/_static/img/emblema-utn-pesquera-en.svg" alt="Emblem: the Argentine Atlantic coast with Mar del Plata, Puerto Madryn and Ushuaia, and a trawl net" width="220" align="right">

This project started in the **Fisheries Engineering** classrooms of the **Universidad Tecnológica
Nacional** (National Technological University, Argentina), at the Tierra del Fuego Regional
Faculty, with the first assignment in which its author learnt to calculate a trawl net: sizing the
FAO A-3 net for the 150-180 HP fishing vessels of the Beagle Channel, solved in an Excel workbook
of about 5,500 formulas
([original repository](https://github.com/arielgiamportone/Trawl_net_model_in_Advanced_Excel),
[report on ResearchGate](https://www.researchgate.net/publication/379257264)).

That workbook is now `trawlkit`: every formula migrated, validated against the Excel file, its
errata documented and fixed, generalised to any net and extended with catalogues, optimisation,
simulation and an app to use on the quay. The project is dedicated to the three Regional
Faculties where **Fisheries Engineering** is taught, along the Argentine Sea:

- **FRTDF** · Tierra del Fuego Regional Faculty, Ushuaia — https://www.frtdf.utn.edu.ar/
- **FRCh** · Chubut Regional Faculty, Puerto Madryn — https://www.frch.utn.edu.ar/
- **FRMDP** · Mar del Plata Regional Faculty — https://mdp.utn.edu.ar/

<sub>The emblem is the project's own drawing, not an official UTN logo.</sub>

<br clear="right">

## Screenshots

The app speaks English and Spanish (ES/EN in the header) and shows metric or imperial units
(Metric/Imperial); the engine always computes in metric.

| | |
|---|---|
| ![Guided mode in English: the diagnosis](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/en-guided-diagnosis.png) | ![Expert mode in English with imperial units](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/en-expert-summary-imperial.png) |
| ![Trip economics with prices per gallon and per pound](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/en-economics-imperial.png) | ![UTN Classroom: an exercise in English with instant grading](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/en-classroom-practice.png) |

The rest of the screenshots show the Spanish interface:

| | |
|---|---|
| ![Guided mode: the diagnosis with traffic lights for power, speed and warp](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/guiado-diagnostico.png) | ![Expert mode: the design case and its indicators](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-claro-caso.png) |
| **Guided mode**: four steps and a plain-language diagnosis | **Expert mode**: case, indicators and tables for each stage |
| ![Interactive design: the panels on the plan, with handles](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-diseno-interactivo.png) | ![3D simulation of the net shape, coloured by tension](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-simulacion-3d.png) |
| **Interactive design** on the plan, with live recalculation | **3D simulation** of the towed net shape |
| ![FAO catalogue with the provenance of each value and the validator](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-catalogo-fao.png) | ![Bill of materials with catalogue components](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-componentes.png) |
| **FAO catalogue** with value-by-value provenance | **Components**: bill of materials and cost |
| ![Batches: one net projected onto each vessel of the fleet](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-lotes.png) | ![Codend selectivity: diamond versus T90](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-selectividad.png) |
| **Batches and fleets**: the net for each vessel in port | **Selectivity**: which sizes the codend retains |
| ![Charts in dark theme: available pull and drag](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-oscuro-graficos.png) | ![On the phone, offline, with the on-phone engine](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/movil-sin-conexion.png) |
| **Charts** (dark theme) | **Offline**: the engine runs on the phone |
| ![Construction: step-by-step assembly with the plan highlighted](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-construccion.png) | ![The workshop guide on the phone](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/movil-guia-taller.png) |
| **Construction**: cutting sheet, joins and hanging | **Workshop guide** on the phone, step by step |
| ![Economics: margin by speed and cost breakdown](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-economia.png) | ![Optimise: best design, feasible region and Pareto front](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-claro-optimizar.png) |
| **Economics**: margin, cost per kg and most profitable speed | **Optimise**: net scale and towing speed |
| ![UTN classroom: the teacher's grade sheet](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-aula-docente.png) | ![Guided lab over the app](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-aula-laboratorio.png) |
| **UTN classroom**: courses, per-student data and grades | **Guided lab**: each step is checked against the open case |

## What it does

- **Design and sizing**: available power, netting and cuts, net mechanics, dimensions, drag by
  13 methods, doors and bridles, openings, buoyancy and ballast, warps and speed window. A3
  technical plan and full-scale view; HTML, PDF and XLSX report.
- **FAO catalogue**: bottom and pelagic nets from the FAO and BOBP series, digitised with the
  provenance of every value (document, page, kind) and a consistency validator.
- **Components and cost**: netting, wire, rope, doors, floats and chain, with generic
  equivalents and spot manufacturer data; bill of materials, indicative cost and optimal rigging
  from what is available in port.
- **Optimisation**: net scale and towing speed (swept area, filtered volume or energy) subject to
  pull, opening, warp and door constraints.
- **Simulation**: 3D equilibrium shape of the net (validated against DynamiT), catch in the
  codend, seabed type, current, fouling, energy and footprint.
- **Selectivity**: diamond, T90 and square mesh; retained sizes by species.
- **Uncertainty and calibration**: sampled bands, sensitivity tornado and fitting to sensor logs.
- **Batches and fleets**: fleet, net and case spreadsheets (CSV or XLSX); a proven net projected
  onto each vessel by similarity and refined with the engine.
- **Construction guide**: from design to workshop. Netting to buy, cutting sheet with each cut
  cycle, step-by-step joins with their take-ups, hanging on the ropes (meshes per metre), floats,
  ballast and rope cuts; as a printable PDF, a spreadsheet and step by step on the phone.
- **Operating economics**: fuel, catch, costs by item and trip margin at each speed, with the
  port's prices; the most profitable speed, comparison between nets and payback of a new net,
  also in fleet batches.
- **UTN classroom**: chapter exercises with changing data and automatic marking, guided labs
  over the app, and a classroom with courses, assignments, submissions and grades for technical
  and engineering degrees.
- **Offline**: the app installs and the same engine runs on the phone (Pyodide).

## Architecture

![Architecture: data and catalogues feed the trawlkit engine, which serves the CLI, the API, the offline engine, the web app and the book](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/docs/_static/img/arquitectura-en.svg)

One engine (`src/trawlkit/`) and one data source (`src/trawlkit/data/`) for everything: the CLI,
the FastAPI API (`src/trawlkit/api/`), the offline engine the app loads in a Web Worker, the React
app (`web/`) and the book (`docs/`), whose numbers come from running the engine. The engine
architecture is described in [docs/en/motor.md](https://github.com/arielgiamportone/trawl-design-lab/blob/main/docs/en/motor.md).

## Calculation chain

![Calculation chain: power, netting, mechanics, dimensions, drag, doors, openings, buoyancy, warps and speed window](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/docs/_static/img/cadena-calculo-en.svg)

The same chain as the original model, stage by stage, each with its chapter in the
[book](https://arielgiamportone.github.io/trawl-design-lab/en/). For a fleet, the projection chains
similarity, refinement and rigging:

![Fleet flow: spreadsheet, projection by similarity, refinement and rigging, results](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/docs/_static/img/flujo-flota-en.svg)

## Indicators

<!-- indicadores:inicio -->
![nets: 26](https://img.shields.io/badge/nets-26-1c5cab) ![components: 564](https://img.shields.io/badge/components-564-1c5cab) ![API routes: 79](https://img.shields.io/badge/API%20routes-79-1c5cab) ![chapters: 40](https://img.shields.io/badge/chapters-40-c35a1b) ![Excel rtol: 1e-6](https://img.shields.io/badge/Excel%20rtol-1e--6-2e7d32)

| Indicator | Value |
|---|---|
| Nets in the catalogue | 26 (17 published, 9 drafts), with value-by-value provenance |
| Components | 564 in 7 kinds (244 generic, spot data from 15 brands) |
| Net drag methods | 13 |
| Excel errata documented and fixed | 26 |
| Excel reference values | 697, reproduced at rtol 1e-6 in `excel` mode |
| Offline engine (Pyodide) | parity with CPython, rtol 1e-9 |
| Species and seabed types | 8 species · 5 seabeds |
| API routes | 79 |
| Book chapters | 40 · 132 references |

<sub>Generated by `tools/readme_stats.py`; `tests/test_readme.py` checks it is up to date.</sub>
<!-- indicadores:fin -->

## Install and use

```bash
pip install trawlkit                            # engine and CLI
pip install "trawlkit[api,report,optimize,excel]"   # + API, PDF/XLSX reports, optimisation and spreadsheets
```

```bash
trawlkit run fao_a3_standard                    # case summary
trawlkit report fao_a3_standard --vessel fao_a3_150hp --out report/    # HTML, PDF, XLSX and plan
trawlkit optimize fao_a3_standard               # optimal scale and speed
trawlkit batch fleet.xlsx --net fao_wb_bt2p_60hp -o batch.xlsx        # one net for each vessel
trawlkit batch --template template.xlsx         # fleet template with its help sheet
trawlkit build-guide fao_a3_standard -o guide.pdf   # workshop construction guide
trawlkit economics fao_a3_standard --fuel-price 1.1 --catch-kg-h 150 --price-kg 3
trawlkit exercises sheet --chapter 14_resistencia --key -o key.pdf
trawlkit serve                                  # API at http://127.0.0.1:8000/docs
trawlkit errata                                 # errata of the original Excel workbook
```

```python
from trawlkit import Compat, DesignCase, run
from trawlkit.io import load_doors, load_net, load_vessels

vessels = {v.id: v for v in load_vessels().vessels}
case = DesignCase(
    net=load_net("fao_a3_standard"),  # 10 panels A..J with cell provenance
    net_modified=load_net("fao_a3_modified"),  # column G of the workbook (30 mm codend)
    vessel=vessels["fao_a3_150hp"],
    class_vessels=(vessels["fao_a3_180hp"],),  # the workbook computes 150 and 180 BHP side by side
    door=load_doors().doors[0],  # FAO flat door
    compat=Compat.CORRECTED,  # or Compat.EXCEL to reproduce the workbook
)
result = run(case)
result.summary()["horizontal_opening_m"]  # 'Dimensiones de la Red'!F61
result.performance.design.max_speed_kn  # maximum towable speed [kn]
```

### `excel` and `corrected` modes

The original workbook contains calculation errata, documented in
[docs/erratas.md](https://github.com/arielgiamportone/trawl-design-lab/blob/main/docs/erratas.md).
Each affected function accepts `compat=Compat.EXCEL`, which reproduces the workbook's number to
validate the migration, or `compat=Compat.CORRECTED`, the correct formula and the default.

### Development

```bash
uv sync --all-extras --dev
uv run pytest                                   # engine, API, spreadsheets, README indicators
uv run ruff check . && uv run mypy
uv run python tools/readme_stats.py             # refreshes the README indicators
uv run python tools/make_figures.py             # regenerates the emblem and the diagrams
uv run python tools/extract_excel.py            # regenerates data and reference values from Excel
cd web && npm ci && npm run dev                 # app at http://localhost:5173
cd web && npm run screenshots                   # regenerates this README's screenshots
```

Deployment (GitHub Pages for the book and the app, Render for the API) is described in
[docs/despliegue.md](https://github.com/arielgiamportone/trawl-design-lab/blob/main/docs/despliegue.md) (Spanish).

## Roadmap

![Project phases 0 to 17](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/docs/_static/img/fases-en.svg)

| Phase | What it added |
|---|---|
| 0–2 | Repository, Excel extraction to open data, and engine validated against the workbook (rtol 1e-6) |
| 3–5 | CLI, reports and plans; API and web app; book with the theory, the Beagle case and validation |
| 6–8 | Optimisation, net shape simulation (DynamiT) and version 1.0 (PyPI, Zenodo, `CITATION.cff`) |
| 9–10 | Guided and expert modes, projects and undo; interactive design on the plan and 3D view |
| 11 | Realistic simulator: catch and seabed, real sea, mesh and selectivity, uncertainty and calibration |
| 12 | FAO net catalogue with value-by-value provenance |
| 13 | Components with generic equivalents, cost, optimal rigging and offline use |
| 14 | Fleet spreadsheets, batch calculation and projection of a net onto each vessel |
| 15 | Workshop construction guide: cutting, assembly, hanging on the ropes and rope cuts |
| 16 | Operating economics: cost, margin and most profitable speed; comparison and payback |
| 17 | Teaching mode «Aula UTN»: exercise bank, guided labs, courses, assignments and grades |

Each release is detailed in the [CHANGELOG](https://github.com/arielgiamportone/trawl-design-lab/blob/main/CHANGELOG.md).

## How to cite

See [`CITATION.cff`](https://github.com/arielgiamportone/trawl-design-lab/blob/main/CITATION.cff)
(GitHub offers "Cite this repository") and the book's
[How to cite](https://arielgiamportone.github.io/trawl-design-lab/citar.html) page. Zenodo DOI
(all versions): [10.5281/zenodo.23657981](https://doi.org/10.5281/zenodo.23657981).

## Licences

Code: [MIT](https://github.com/arielgiamportone/trawl-design-lab/blob/main/LICENSE).
Documentation, data and legacy material: [CC BY 4.0](https://github.com/arielgiamportone/trawl-design-lab/blob/main/LICENSE-docs).

## Author

**Ariel Luján Giamportone** · Fisheries Engineering, Universidad Tecnológica Nacional, Tierra del
Fuego Regional Faculty · ALG Data&Engineering Solutions.
