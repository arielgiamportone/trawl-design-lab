# trawl-design-lab

```{image} ../_static/img/banner-en.svg
:alt: trawl-design-lab · trawlkit: bottom trawl design, born in UTN Fisheries Engineering (FRTDF, FRCh and FRMDP)
:width: 100%
```

**Design and sizing of bottom trawls: theory, reproducible calculation and software.**

This book documents `trawlkit`, an open calculation engine that reimplements and extends the design
model of the FAO A-3 bottom trawl for 150–180 HP fishing vessels of the Beagle Channel, originally
developed in an Excel workbook by Ariel Luján Giamportone in Fisheries Engineering at the
Universidad Tecnológica Nacional (UTN), Facultad Regional Tierra del Fuego {cite:p}`giamportone2024`.
The story of that origin and of the three UTN regional faculties where the degree is taught is in
{doc}`utn`.

This is the English edition. The Spanish edition, the original, has the same chapters (use the
«Español» button at the top of each page). The technical terms follow the FAO English usage; the
{doc}`glossary` lists the Spanish term next to each one.

## Who it is for

- **Fisheries engineers and students**: each stage of the calculation is presented with its
  theory, its equations, the empirical coefficients and the reference of the author who proposed
  them.
- **Designers, net makers and skippers**: the case study shows how to go from the power of the
  vessel to the net, the rigging, the buoyancy, the ballast and the warp, and what the towable
  speed is; the catalogue, the components and the batches take that calculation to other nets,
  to cost and to a whole fleet.
- **Developers**: the last part describes the software architecture, the reports, the API and the
  web application.

## Try the application

The web application is published next to this book:
**<https://arielgiamportone.github.io/trawl-design-lab/app/>** (choose EN at the top right; it also
shows imperial units). It has two modes: **guided**, four steps (vessel, net, operation and
result) with a plain-language diagnosis, and **expert**, with charts, interactive design on the
plan, optimization, 3D simulation, selectivity, the FAO catalogue, components and cost, and fleet
batches. It uses the public API of the engine and, offline, the same engine inside the phone
({doc}`web`). The first calculation with the API may take up to a minute if it was asleep (free
plan; see {doc}`despliegue`).

## How to read it

1. **Foundations**: the problem, the nomenclature and the origin of the project at UTN
   ({doc}`utn`).
2. **Theory and methods**: one chapter per stage, in the same order in which the design is solved
   (chapters 10 to 19). Each chapter runs the calculation with `trawlkit` and checks it against
   the original Excel workbook. Then come the optimization of the net size and of the speed
   ({doc}`20_optimizacion`), the simulation of the shape of the towed net ({doc}`21_simulacion`)
   and the realistic simulator: catch, seabed and coupled otter boards
   ({doc}`22_simulacion_realista`), the real sea ({doc}`23_mar_real`), mesh and selectivity
   ({doc}`24_malla_selectividad`), and uncertainty and calibration
   ({doc}`25_incertidumbre_calibracion`).
3. **Case study and validation**: the standard and modified FAO A-3 net, the validation against
   the Excel workbook and against the DynamiT simulator, the catalogue of FAO nets with their
   provenance ({doc}`33_catalogo_fao`), components and cost ({doc}`34_componentes`), batches and
   the projection of nets onto a fleet ({doc}`35_lotes_proyeccion`), the construction guide for
   the net loft ({doc}`36_construccion`), the economics of the operation ({doc}`37_economia`) and
   the errata of the original model.
4. **Teaching**: the guide to using the book and the app in class, with the exercise bank, the
   guided labs and the course classroom ({doc}`38_docentes`). The theory chapters close with an
   exercises section.
5. **Software**: engine, reports and plans, web application, API, online deployment and how to
   cite.

The chapters are executable notebooks: the code and the numbers they show are recomputed every
time the book is built.

## Calculation modes

The original model contains documented errata ({doc}`erratas`). Calculations can be done in
`excel` mode (reproduces the original workbook exactly, for validation) or in `corrected` mode
(corrected formulas, recommended for design). Each chapter states which mode it uses.

## How to cite

> Giamportone, A. L. (2026). *Trawl Design Lab (trawlkit): diseño y dimensionamiento de redes de
> arrastre*. Universidad Tecnológica Nacional, Facultad Regional Tierra del Fuego.
> Zenodo. https://doi.org/10.5281/zenodo.23657981

The full metadata and the DOI of each version are in {doc}`citar`.

Code under the MIT licence; documentation and data under CC BY 4.0.
