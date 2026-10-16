# Erratas del modelo Excel original

Durante la migración se auditaron las ~5 500 fórmulas del libro `Calculos_Red_FAO_A3.xlsx`.
Las siguientes erratas se reproducen en modo `Compat.EXCEL` (para validar la migración) y se
corrigen en modo `Compat.CORRECTED`. La lista canónica vive en `trawlkit.compat.ERRATA`.

| Clave | Hoja | Celda | Descripción |
|---|---|---|---|
| cut_ratio_first_panel | Paños de red y cortes | H274:I277 | Todos los paneles usan la razón de corte del primero |
| twine_density_units | Paños de red y cortes | L55 | Densidad del hilo dimensionalmente incorrecta |
| filtration_double_count | Mecánica de la Red | J17 | J16 contado dos veces |
| hamuro_sin_degrees | Resistencia de la RED | D113 | SIN(DEGREES) en lugar de SIN(RADIANS) |
| hamuro_mod_uses_std_dl | Resistencia de la RED | E117 | Variante modificada usa d/l de la estándar |
| reid_fixed_denominator | Resistencia de la RED | C154:C162 | Denominador fijo a 1 nudo |
| drag_average_pollution | Resistencia de la RED | R302:R310 | Promedio incluye velocidad y tiro de Nomura |
| door_force_mixed_angles | Portones y aparejamiento | D252 | Mezcla grados y radianes |
| float_reynolds | Flotación y Lastre | H138 | Re = π·D²·v/ν en lugar de v·D/ν |
| warp_total_omits_doors | Cables de Remolque | H118 | Omite la resistencia de los portones |
| warp_undersized | Cables de Remolque | E267:E272 | Cable 12 mm (8.55 t) < 8.8 t requeridos |
| mod_length_wrong_rows | Dimensiones de la Red | G48 | Largo modificada suma filas equivocadas |
| footrope_mid_truncation | Dimensiones de la Red | F46 | MID() trunca el burlón a 33.3 m (valor completo 33.389 m) |
| dpa_std_uses_mod_edy | Mecánica de la Red | P164 | DPA Fridman estándar usa el Edy de la modificada |
| nomura_column_links_hamuro | Potencia Disponible Arrastre OK | G319, G342, G362 | Columna "Nomura" enlaza a Hamuro |
| sweep_degrees_of_sine | Portones y aparejamiento | G71 | DEGREES(SIN(20)) y error de precedencia |
| nomura_ratio_typo | Tablas de Referencias | G18, G21 | 10.6 donde corresponde 1.06 |
| panel_f_cut_na | Paños de red y cortes | T122 | Razón de corte del panel F devuelve #N/A |

Además, varias tablas resumen contienen valores pegados a mano en lugar de fórmulas (marcados con
`"static": true` en `tests/golden/*.json`), y los coeficientes leídos con `MID()` desde etiquetas de
texto dependen del locale (marcados con `"coerced_from_text": true`).
