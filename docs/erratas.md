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
