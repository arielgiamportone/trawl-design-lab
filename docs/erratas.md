# Erratas del modelo Excel original

Durante la migración se auditaron las ~5 500 fórmulas del libro `Calculos_Red_FAO_A3.xlsx`.
Las siguientes erratas se reproducen en modo `Compat.EXCEL` (para validar la migración) y se
corrigen en modo `Compat.CORRECTED`. La lista canónica vive en `trawlkit.compat.ERRATA`; la
columna *Implementación* indica la función que conmuta con `compat` y el test que verifica ambas
direcciones (`tests/test_corrected_mode.py` lo hace a nivel del caso completo, `trawlkit.model.run`).

| Clave | Hoja | Celda | Descripción | Implementación (función · test) |
|---|---|---|---|---|
| cut_ratio_first_panel | Paños de red y cortes | H274:I277 | Todos los paneles usan la razón de corte del primero | `netting.mean_cut_angle_deg` · `test_netting.py` |
| twine_density_units | Paños de red y cortes | L55 | Densidad del hilo dimensionalmente incorrecta | `materials.twine_density_kg_m3`, `net.analyse` · `test_net.py`, `test_netting.py` |
| filtration_double_count | Mecánica de la Red | J17 | J16 contado dos veces | `net.filtration_index` · `test_net.py` |
| hamuro_sin_degrees | Resistencia de la RED | D113 | SIN(DEGREES) en lugar de SIN(RADIANS) | `drag.hamuro_sin_alpha` · `test_drag.py`, `test_corrected_mode.py` |
| hamuro_mod_uses_std_dl | Resistencia de la RED | E117 | Variante modificada usa d/l de la estándar | `drag.drag_table` · `test_drag.py`, `test_corrected_mode.py` |
| reid_fixed_denominator | Resistencia de la RED | C154:C162 | Denominador fijo a 1 nudo | `drag.reid` · `test_drag.py`, `test_corrected_mode.py` |
| drag_average_pollution | Resistencia de la RED | R302:R310 | Promedio incluye velocidad y tiro de Nomura | `drag.average` · `test_drag.py`, `test_corrected_mode.py` |
| door_force_mixed_angles | Portones y aparejamiento | D252 | Mezcla grados y radianes | `rigging.doors.door_force_kgf` · `test_rigging_doors.py`, `test_corrected_mode.py` |
| float_reynolds | Flotación y Lastre | H138 | Re = π·D²·v/ν en lugar de v·D/ν | `rigging.floats.float_reynolds` · `test_rigging_floats.py`, `test_corrected_mode.py` |
| warp_total_omits_doors | Cables de Remolque | H118 | Omite la resistencia de los portones | `rigging.warps.total_drag_kgf` (→ `model._stage_warps`, `_stage_performance`) · `test_rigging_warps.py`, `test_corrected_mode.py` |
| warp_undersized | Cables de Remolque | E267:E272 | Cable 12 mm (8.55 t) < 8.8 t requeridos | `rigging.warps.select_warp` · `test_rigging_warps.py`, `test_corrected_mode.py` |
| mod_length_wrong_rows | Dimensiones de la Red | G48 | Largo modificada suma filas equivocadas | `dimensions.body_length_no_bag_m` · `test_dimensions.py` |
| footrope_mid_truncation | Dimensiones de la Red | F46 | MID() trunca el burlón a 33.3 m (valor completo 33.389 m) | `dimensions.footrope_length_m` · `test_dimensions.py`, `test_corrected_mode.py` |
| dpa_std_uses_mod_edy | Mecánica de la Red | P164 | DPA Fridman estándar usa el Edy de la modificada | `rigging.spread.fridman_spread` · `test_rigging_spread.py`, `test_corrected_mode.py` |
| nomura_column_links_hamuro | Potencia Disponible Arrastre OK | G319, G342, G362 | Columna "Nomura" enlaza a Hamuro | sin conmutador: `power.power_curves` calcula Nomura de verdad; el enlace se documenta en `test_power.py` |
| sweep_degrees_of_sine | Portones y aparejamiento | G71 | DEGREES(SIN(20)) y error de precedencia | `rigging.bridles.sweeps_martini_m` · `test_rigging_bridles.py` |
| nomura_ratio_typo | Tablas de Referencias | G18, G21 | 10.6 donde corresponde 1.06 | sin conmutador: la tabla se copia tal cual en `data/reference/nomura_proportions.csv` (`test_data_reference.py`) |
| panel_f_cut_na | Paños de red y cortes | T122 | Razón de corte del panel F devuelve #N/A | `netting.cut_code` calcula el código que el libro no pudo · `test_netting.py` |
| codend_minor_side_uses_depth | Mecánica de la Red | K36:K37 | Bolsas I/J usan N (200) como lado menor en vez de T2 (113): Ss 40.90 en vez de 38.75 m² | `net.apply_excel_codend_quirk` (vía `net.analyse`) · `test_net.py`, `test_corrected_mode.py` |
| panel_b_cut_uses_plan_coef | Paños de red y cortes | S62 | Razón de corte del paño B con el coeficiente de plano en vez de N | sin conmutador: `netting.cut_ratio` usa N; el valor del libro se conserva sólo en el golden (`test_netting.py`) |
| panel_b_cut_code_lookup_a | Paños de red y cortes | T62 | Código de corte del paño B buscado con la razón del paño A | sin conmutador: `netting.cut_code` busca con la razón del propio paño (`test_netting.py`) |
| net_weight_ignores_panel_count | Mecánica de la Red | O107, O109 | Peso total sin multiplicar por cantidad de paneles | reproducido en ambos modos por `net.analyse` (peso por fila; documentado en el docstring) · `test_net.py` |
| catenary_ratio_hardcoded | Mecánica de la Red | O266 | fL/L = 0.216 fijo, fuera del rango de la tabla | `DesignCase.catenary_ratio` (0.216 en ambos modos; `rigging.spread.catenary_ratio` da el valor de tabla y `run` lo anota en `notes`) · `test_rigging_spread.py` |
| float_lookup_unsorted | Flotación y Lastre | F92 | LOOKUP sobre vector sin ordenar | `rigging.floats.float_diameter_for_count_mm` (EXCEL) / boya de número más cercano en `model._stage_floats` (CORRECTED) · `test_rigging_floats.py`, `test_case_fao_a3.py` |
| flotation_rounding_inconsistent | Flotación y Lastre | M43:M50 | Redondeo aplicado sólo a parte de la columna | `rigging.floats.flotation_fridman(rounddown=…)`, máscara en `model._stage_floats` · `test_rigging_floats.py`, `test_corrected_mode.py` |

Además, varias tablas resumen contienen valores pegados a mano en lugar de fórmulas (marcados con
`"static": true` en `tests/golden/*.json`), y los coeficientes leídos con `MID()` desde etiquetas de
texto dependen del locale (marcados con `"coerced_from_text": true`).

Dos acoplamientos del libro que no son erratas pero condicionan un caso de diseño se exponen como
campos de `DesignCase`: la flotación total `Ffz` (`Mec!O261`) promedia los bloques de 150 y 180 HP
(`class_vessels`) y el cable de remolque se dimensiona con el NHP de 180 HP (`Rem!E110 = E81`,
`warp_nhp_hp`, por defecto el mayor BHP de la clase).
