# Introduction

## The bottom trawl

A bottom trawl is a funnel of netting towed by a vessel over the seabed. Its mouth is held open
horizontally by two **otter boards**, which spread apart hydrodynamically as they move forward, and
vertically by the **buoyancy** of the headrope and the **ballast** of the footrope. The vessel must
deliver enough pull to overcome the drag of the net, the rigging and the warps at fishing speed.

Designing the net is therefore a problem of balance: the largest net the vessel can tow at the
speed the target species demands, with sufficient openings and a rigging that keeps it in its
working geometry.

## The FAO A-3 net

FAO published a series of trawl designs for small and medium-sized vessels {cite:p}`faocatalogue`.
The A-3 is a two-panel bottom trawl for vessels of around 150–180 HP. The model in this book sizes
it panel by panel (wings, square, body and codend) and compares two variants:

- **standard**, with a 40 mm mesh codend;
- **modified**, with a 30 mm mesh codend for small crustaceans.

## The Beagle Channel case

The case study targets the **squat lobster** (*Munida gregaria* / *M. subrugosa*), at about 40 m
depth over intermediate seabed, with coastal (*rada o ría*) fishing vessels of up to 9 m length
overall and 150–180 BHP {cite:p}`giamportone2024`.

## The calculation chain

The design is solved in stages, each with its own chapter:

1. Power and available pull of the vessel ({doc}`10_potencia`).
2. Netting panels, rigging and cuts ({doc}`11_panos_y_cortes`).
3. Net mechanics: areas, solidity and weight ({doc}`12_mecanica_red`).
4. Main dimensions and ropes ({doc}`13_dimensiones`).
5. Net drag by 13 methods ({doc}`14_resistencia`).
6. Otter boards and rigging ({doc}`15_portones_aparejo`).
7. Horizontal and vertical openings ({doc}`16_aberturas`).
8. Buoyancy and ballast ({doc}`17_flotacion_lastre`).
9. Towing warps ({doc}`18_cables`).
10. Towable speed window ({doc}`19_ventana_velocidad`).

## From Excel to software

The model was born as an Excel workbook of 13 sheets and some 5,500 formulas. `trawlkit` translates
it into documented and verified functions: each function cites the Excel cell it reproduces, and
the tests compare the results with the values of the original workbook to a relative tolerance of
10⁻⁶ ({doc}`31_validacion_excel`).
