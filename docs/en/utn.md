# Born at UTN

```{image} ../_static/img/emblema-utn-pesquera-en.svg
:alt: Project emblem: the Argentine Atlantic coast with Mar del Plata, Puerto Madryn and Ushuaia, and a trawl net
:width: 260px
:align: right
```

This project was born in the classrooms of **Fisheries Engineering at the Universidad Tecnológica
Nacional (UTN)**. There, at the Facultad Regional Tierra del Fuego, its author did the first piece
of work in which he learned to calculate a trawl: the sizing of the FAO A-3 net for the
150–180 HP fishing vessels of the Beagle Channel {cite:p}`giamportone2024`.

## From Excel to `trawlkit`

The calculation was first solved in an Excel workbook of some 5,500 formulas, spread over sheets
that follow the order of the design: available power, netting panels and cuts, net mechanics,
dimensions, drag, otter boards, buoyancy, ballast and warps
([original repository](https://github.com/arielgiamportone/Trawl_net_model_in_Advanced_Excel),
[report on ResearchGate](https://www.researchgate.net/publication/379257264)).

That workbook is the basis of `trawlkit`:

- **Migration and validation.** Each formula was migrated to Python and validated against the
  values of the Excel workbook, to a relative tolerance of 10⁻⁶ ({doc}`31_validacion_excel`).
- **Errata.** The errata that turned up in the audit were documented and corrected
  ({doc}`erratas`). The `excel` mode still reproduces them for comparison.
- **Generalization.** The calculation was extended to any net defined by panels, from the FAO
  catalogue ({doc}`33_catalogo_fao`) to the spreadsheets of a whole fleet
  ({doc}`35_lotes_proyeccion`).
- **New tools.** Optimization, shape simulation, selectivity and components with their cost were
  added, together with an application that works on the phone offline.

The goal is still that of the original coursework: that a student, a technician or a skipper can
know which net a vessel can tow and how to rig it, and understand why.

## The three Fisheries Engineering faculties

UTN teaches Fisheries Engineering at three Regional Faculties on the Argentine Sea. The project is
dedicated to all three:

| Regional Faculty | City | Website |
|---|---|---|
| **FRTDF** · Tierra del Fuego | Ushuaia | <https://www.frtdf.utn.edu.ar/> |
| **FRCh** · Chubut | Puerto Madryn | <https://www.frch.utn.edu.ar/> |
| **FRMDP** · Mar del Plata | Mar del Plata | <https://mdp.utn.edu.ar/> |

For their courses, the app has a **“UTN Classroom”** mode: exercises with marking, guided labs on
the app and a classroom with courses, assignments and grades ({doc}`38_docentes`).

All three sit on fishing ports: Mar del Plata, on the Buenos Aires shelf; Puerto Madryn, on Golfo
Nuevo; Ushuaia, on the Beagle Channel. This book, the engine and its data are open (MIT and
CC BY 4.0) so that they can be used in their courses, practical work and final-year projects.

```{note}
The emblem is the project's own drawing: the Atlantic coast with the three campuses and the
silhouette of a trawl net. It is not an official logo of UTN or of its Faculties.
```
