# Nomenclature and units

Symbols used throughout the book. In brackets, the unit in which the original model and `trawlkit`
work; the conversions are in `trawlkit.units`. The Spanish names of the gear terms, with their
English equivalents and short definitions, are listed in the {doc}`glossary`.

## Speed, force and power

| Symbol | Meaning | Unit |
|---|---|---|
| $v$ | Towing speed | kn (1 kn = 0.5144 m/s) |
| $P$, BHP | Brake power at the propeller | HP |
| NHP | Nominal power ("150 HP" in the original workbook is taken as BHP) | HP |
| $F_T$ | Available pull (towing force) | kgf |
| $R_N$ | Net drag | kgf or t |
| $R_B$ | Float drag | kgf |
| $R_W$ | Drag of the towing warps | kgf |
| $R_{OB}$ | Otter board drag | kgf |
| $R_T$ | Total drag of the system: $R_N + R_B + R_W\,(+R_{OB})$ | kgf |
| $\rho$, $g$ | Density of seawater (1024 kg/m³) and gravity (9.81 m/s²) | — |

## Netting and net

| Symbol | Meaning | Unit |
|---|---|---|
| $m_L$ | Mesh size: stretched mesh length | mm |
| $d$ | Twine diameter | mm |
| Rtex, runnage | Twine linear density and its inverse (m/kg = 10⁶/Rtex) | g/km, m/kg |
| $T_1$, $T_2$ | Meshes along the larger and smaller edge of the panel (Excel convention) | meshes |
| $N$ | Meshes in depth of the panel | meshes |
| $U_1$, $U_2$ | Horizontal and vertical hanging ratios, $U_2 = \sqrt{1-U_1^2}$ | — |
| $d/l$ | Filtration index: $\sum d / \sum m_L$ | — |
| $S_s$ | Solid (twine) area | m² |
| $S_t$ | Working area (mounted netting) | m² |
| $a$ | Mouth circumference at stretched mesh | m |
| $L$, $b$ | Net length without and with codend | m |
| $\alpha$ | Angle of attack of the cuts | ° |

## Rigging and geometry

| Symbol | Meaning | Unit |
|---|---|---|
| Headrope, footrope | Upper and lower rope (Spanish *lima*, *burlón*) | m |
| $L_s$, $L_{sh}$ | Warp paid out and its horizontal projection | m |
| $D_s$ | Distance between otter boards | m |
| DPA | Distance between wingtips (horizontal opening of the net) | m |
| AH, AV | Horizontal and vertical opening | m |
| $C_L$, $C_D$ | Lift and drag coefficients of the otter board | — |
| $E_{dx}$, $E_{dy}$ | Fridman expansion coefficients | — |
| $\delta$ | Angle of attack of the bridles and sweeps | ° |
| $f_L$ | Headrope sag (catenary) | m |

## Calculation modes

| Mode | Meaning |
|---|---|
| `excel` | Reproduces the numbers of the original Excel workbook, errata included. Used for validation. |
| `corrected` | Applies the correct formulas; it is the default mode for design. See {doc}`erratas`. |
