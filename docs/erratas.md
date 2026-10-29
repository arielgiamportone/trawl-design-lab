---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

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
| warp_cd_horizontal_angle | Cables de Remolque | E103:E106 | CD del cable con la divergencia en planta δ2 = 4,3° (→ 0,02) en vez del ángulo de ataque al flujo, y fila más cercana sin interpolar | `rigging.warps.warp_attack_angle_deg`, `rigging.warps.warp_cd(interpolate=…)` (→ `model._stage_warps`) · `test_corrected_mode.py` |
| warp_undersized | Cables de Remolque | E267:E272 | Cable 12 mm (8.55 t) < 8.8 t requeridos | `rigging.warps.select_warp` · `test_rigging_warps.py`, `test_corrected_mode.py` |
| mod_length_wrong_rows | Dimensiones de la Red | G48 | Largo modificada suma filas equivocadas | `dimensions.body_length_no_bag_m` · `test_dimensions.py` |
| footrope_mid_truncation | Dimensiones de la Red | F46 | MID() trunca el burlón a 33.3 m (valor completo 33.389 m) | `dimensions.footrope_length_m` · `test_dimensions.py`, `test_corrected_mode.py` |
| dpa_std_uses_mod_edy | Mecánica de la Red | P164 | DPA Fridman estándar usa el Edy de la modificada | `rigging.spread.fridman_spread` · `test_rigging_spread.py`, `test_corrected_mode.py` |
| nomura_column_links_hamuro | Potencia Disponible Arrastre OK | G319, G342, G362 | Columna "Nomura" enlaza a Hamuro | sin conmutador: `power.power_curves` calcula Nomura de verdad; el enlace se documenta en `test_power.py` |
| sweep_degrees_of_sine | Portones y aparejamiento | G71 | DEGREES(SIN(20)) y error de precedencia | `rigging.bridles.sweeps_martini_m` · `test_rigging_bridles.py` |
| nomura_ratio_typo | Tablas de Referencias | G18, G21 | 10.6 donde corresponde 1.06 | sin conmutador: la tabla se copia tal cual en `src/trawlkit/data/reference/nomura_proportions.csv` (`test_data_reference.py`) |
| panel_f_cut_na | Paños de red y cortes | T122 | Razón de corte del panel F devuelve #N/A | `netting.cut_code` calcula el código que el libro no pudo · `test_netting.py` |
| codend_minor_side_uses_depth | Mecánica de la Red | K36:K37 | Bolsas I/J usan N (200) como lado menor en vez de T2 (113): Ss 40.90 en vez de 38.75 m² | `net.apply_excel_codend_quirk` (vía `net.analyse`) · `test_net.py`, `test_corrected_mode.py` |
| panel_b_cut_uses_plan_coef | Paños de red y cortes | S62 | Razón de corte del paño B con el coeficiente de plano en vez de N | sin conmutador: `netting.cut_ratio` usa N; el valor del libro se conserva sólo en el golden (`test_netting.py`) |
| panel_b_cut_code_lookup_a | Paños de red y cortes | T62 | Código de corte del paño B buscado con la razón del paño A | sin conmutador: `netting.cut_code` busca con la razón del propio paño (`test_netting.py`) |
| net_weight_ignores_panel_count | Mecánica de la Red | O107, O109 | Peso total sin multiplicar por cantidad de paneles | `net.analyse` (en CORRECTED cada fila pesa por su cantidad de paneles: aire, agua y reparto por plano) · `test_net.py`, `test_corrected_mode.py` |
| catenary_ratio_hardcoded | Mecánica de la Red | O266 | fL/L = 0.216 fijo, fuera del rango de la tabla | `DesignCase.catenary_ratio` (0.216 en ambos modos; `rigging.spread.catenary_ratio` da el valor de tabla y `run` lo anota en `notes`) · `test_rigging_spread.py` |
| float_lookup_unsorted | Flotación y Lastre | F92 | LOOKUP sobre vector sin ordenar | `rigging.floats.float_diameter_for_count_mm` (EXCEL) / boya de número más cercano en `model._stage_floats` (CORRECTED) · `test_rigging_floats.py`, `test_case_fao_a3.py` |
| flotation_rounding_inconsistent | Flotación y Lastre | M43:M50 | Redondeo aplicado sólo a parte de la columna | `rigging.floats.flotation_fridman(rounddown=…)`, máscara en `model._stage_floats` · `test_rigging_floats.py`, `test_corrected_mode.py` |
| door_area_power_extrapolation | Portones y aparejamiento | F212, F215 | Superficie requerida lineal en la potencia, calibrada para 150–180 HP y extrapolada a buques más potentes | `rigging.door_area_power_factor`, `rigging.required_area_summary(bhp=…)` (→ `model._stage_doors`, `door_selection.select_doors`, `optimize.evaluate`) · `test_door_area_power.py`, `test_door_polars.py` |
| fridman_dp_warp_saturation | Mecánica de la Red | P164:Q172 | La DPA de Fridman se satura con el cable: con un cable distinto del de la tabla la DP cambia menos que lo medido | `rigging.dp_warp_factor` (factor $(L_s/L_{s,tabla})^{\Delta n}$, 1 con el cable de la tabla) en `rigging.fridman_spread(warp_factor=…)` (→ `model.fridman_door_spread_m`, `model._stage_spread`) · `test_calibration_20_5.py` |

Además, varias tablas resumen contienen valores pegados a mano en lugar de fórmulas (marcados con
`"static": true` en `tests/golden/*.json`), y los coeficientes leídos con `MID()` desde etiquetas de
texto dependen del locale (marcados con `"coerced_from_text": true`).

Dos acoplamientos del libro que no son erratas pero condicionan un caso de diseño se exponen como
campos de `DesignCase`: la flotación total `Ffz` (`Mec!O261`) promedia los bloques de 150 y 180 HP
(`class_vessels`) y el cable de remolque se dimensiona con el NHP de 180 HP (`Rem!E110 = E81`,
`warp_nhp_hp`, por defecto el mayor BHP de la clase).

## Impacto de las erratas

¿Cuánto mueve cada errata el diseño? La tabla siguiente corre el caso completo del libro (red
estándar y modificada, buque de 150 BHP con el de 180 BHP en la clase, portón FAO; ver
{doc}`30_caso_beagle`) en los dos modos y compara el resultado afectado por cada errata conmutable.
Como el modo es global, cada fila mezcla el efecto de su errata con el de las erratas aguas arriba;
la columna *Arrastra* lo indica cuando corresponde (por ejemplo, toda resistencia basada en la
superficie de la red estándar arrastra el −5,2 % de $S_s$ de la errata de la bolsa).

```{code-cell} ipython3
:tags: [remove-input]
import sys, pathlib
sys.path.insert(0, str(pathlib.Path.cwd().parent))
import numpy as np
from tests.golden_utils import golden
from trawlkit.compat import ERRATA_BY_KEY
from trawlkit.model import dp_warp_factor
import _plots_v as V

E, C = V.run_case(150, "excel"), V.run_case(150, "corrected")
i = E.case.speed_index
SS = "codend_minor_side_uses_depth"
rows_def = [
    # (errata, salida, función del resultado, decimales, unidad, arrastra)
    (SS, "Sₛ estándar", lambda r: r.geometry.std.solid_surface_m2, 2, "m²", ""),
    ("twine_density_units", "Peso estándar en aire, un panel por fila",
     lambda r: sum(g.weight_air_kg / (g.row.count if r.case.compat.value == "corrected" else 1)
                   for g in r.geometry.std.rows), 1, "kg", SS),
    ("net_weight_ignores_panel_count", "Peso estándar en aire",
     lambda r: r.geometry.std.weight_air_kg, 1, "kg", "twine_density_units"),
    ("filtration_double_count", "d/l red modificada", lambda r: r.geometry.mod.filtration_index, 4, "", ""),
    ("footrope_mid_truncation", "Burlón", lambda r: r.dimensions.std.footrope_m, 3, "m", ""),
    ("hamuro_sin_degrees", "Rₙ Hamuro a 3 kn",
     lambda r: r.drag.table.std["hamuro"][i(3.0)] * 1000, 0, "kgf", SS),
    ("hamuro_mod_uses_std_dl", "Rₙ Hamuro modificada a 3 kn",
     lambda r: r.drag.table.mod["hamuro"][i(3.0)] * 1000, 0, "kgf", "hamuro_sin_degrees"),
    ("reid_fixed_denominator", "Rₙ Reid a 5 kn",
     lambda r: r.drag.table.std["reid"][i(5.0)] * 1000, 0, "kgf", SS),
    ("drag_average_pollution", "Promedio de métodos a 3 kn",
     lambda r: r.drag.average.std[i(3.0)] * 1000, 0, "kgf", "varias"),
    ("dpa_std_uses_mod_edy", "DPA Fridman a 1 kn",
     lambda r: r.spread.fridman.dpa_std_m[0], 2, "m", SS),
    ("door_force_mixed_angles", "Fuerza del portón a 3 kn",
     lambda r: r.doors.force_kgf[i(3.0)], 1, "kgf", ""),
    ("float_reynolds", "Reynolds de la boya a 3 kn", lambda r: r.floats.reynolds[i(3.0)], 0, "", ""),
    ("flotation_rounding_inconsistent", "Flotación de Fridman",
     lambda r: r.floats.fridman_average_kgf, 2, "kgf", SS),
    ("warp_cd_horizontal_angle", "CD del cable", lambda r: r.warps.cd, 3, "", ""),
    ("warp_cd_horizontal_angle", "Resistencia de los cables a 3,5 kn",
     lambda r: r.warps.drag_kgf[i(3.5)], 1, "kgf", ""),
    ("warp_total_omits_doors", "Rₜ a 3,5 kn",
     lambda r: r.warps.total.std[i(3.5)], 0, "kgf", SS),
    ("warp_total_omits_doors", "Rotura mínima del cable",
     lambda r: r.warps.loads.min_breaking_load_kgf, 0, "kgf", SS),
    ("warp_undersized", "Cable",
     lambda r: r.warps.selection.diameter_mm, 0, "mm", "warp_total_omits_doors"),
    ("sweep_degrees_of_sine", "Patentes de Martini", lambda r: r.bridles.sweeps_martini_m, 2, "m", ""),
    ("warp_total_omits_doors", "v* (150 HP, PF)",
     lambda r: r.performance.design.max_speed_kn, 2, "kn", "todas"),
]
CARRY = {SS: "Sₛ de la bolsa", "hamuro_sin_degrees": "seno de Hamuro",
         "twine_density_units": "densidad del hilo",
         "warp_total_omits_doors": "Rₜ con portón"}
rows = []
for key, label, f, nd, unit, carry in rows_def:
    a, b = float(f(E)), float(f(C))
    assert key in ERRATA_BY_KEY, key
    rows.append([key.replace("_", "_\u200b"), label + (f" [{unit}]" if unit else ""),
                 V.fmt(a, nd), V.fmt(b, nd), V.pct_s(b, a), CARRY.get(carry, carry)])
V.md_table(["Errata", "Salida afectada", "Excel", "Corregido", "Cambio [%]", "Arrastra"], rows)
assert E.dimensions.std.footrope_m == golden("dimensiones_de_la_red", "footrope_m")
```

Otras erratas conmutables **no cambian** este caso porque la red FAO A-3 y su buque de 150 HP no
las activan:

```{code-cell} ipython3
:tags: [remove-input]
nulls = [
    ("cut_ratio_first_panel", "Ángulo de corte medio [°]", lambda r: r.dimensions.std.cut_angle_deg,
     "todos los paños del plan alto tienen corte 1N2B"),
    ("mod_length_wrong_rows", "Largo de la modificada sin bolsa [m]",
     lambda r: r.dimensions.mod.body_length_no_bag_m, "los dos planos miden 32,68 m sin la bolsa"),
    ("float_lookup_unsorted", "Diámetro de boya [mm]", lambda r: r.floats.diameter_mm,
     "el LOOKUP desordenado cae en la boya de 200 mm, la más cercana"),
    ("door_area_power_extrapolation", "Superficie requerida por portón [m²]",
     lambda r: r.doors.required_area.per_door_m2, "150 HP no pasa de la potencia de diseño (180 HP)"),
    ("fridman_dp_warp_saturation", "Factor de cable de la DPA de Fridman",
     lambda r: dp_warp_factor(r.case, r.rigging), "el caso usa el cable de la tabla del libro"),
]
rows = []
for key, label, f, why in nulls:
    a, b = f(E), f(C)
    assert a == b, key
    nd = 0 if float(a).is_integer() else 2
    rows.append([key.replace("_", "_\u200b"), label, V.fmt(a, nd), V.fmt(b, nd), why])
V.md_table(["Errata", "Salida", "Excel", "Corregido", "Por qué no cambia"], rows)
```

Tres órdenes de magnitud:

* **Erratas que cambian una decisión.** `warp_total_omits_doors` y `warp_undersized` cambian el cable
  de 12 a 13 mm: con los portones incluidos, el de 12 mm queda por debajo de la carga de rotura
  mínima. `codend_minor_side_uses_depth` invierte la comparación entre la red estándar y la
  modificada ({doc}`30_caso_beagle`) y es la de mayor alcance: el −5,2 % de $S_s$ se propaga a la
  resistencia de diseño, a la DPA, a la flotación de Fridman y a la demanda total.
* **Erratas que cambian mucho un número que no se usa para diseñar.** Reid (−59 % a 5 kn), las
  patentes de Martini (+77 %), el Reynolds de la boya (+59 %) y el peso de la red (−29 % por panel
  con la densidad corregida, +18 % en total al contar todos los paneles) cambian fuerte, pero
  ninguno alimenta otra etapa: el coeficiente de arrastre de la boya no depende del Reynolds
  calculado y el libro usa las patentes de diseño (25 m) en vez de las de Martini. La resistencia de
  los cables (+170 % con el ángulo de ataque real) sí entra en la demanda, pero es menos del 2 % de
  $R_T$.
* **Erratas menores.** El burlón (+0,27 %), la fuerza sobre el portón (+1,8 %) o el promedio de
  métodos (+0,7 %) quedan por debajo de la incertidumbre de cualquier método empírico.

La velocidad máxima, que resume el diseño, se mueve poco (−7 %, −0,17 kn): las correcciones que
aumentan la demanda (portones, cables) y las que la reducen (superficie sólida) se compensan en
parte.

## Superficie del portón por encima de la potencia del libro

La errata `door_area_power_extrapolation` no es una fórmula mal escrita: es una regla usada fuera de
su rango. La superficie requerida del libro (`Port!F212`, `F215`; {doc}`15_portones_aparejo`) toma
el 20 % del tiro disponible y lo divide por $(\rho/g)\,C_D\,v^2$, así que crece en proporción a la
potencia. Calibrada para los buques A-3 de 150 y 180 HP, extrapolada a la flota argentina pide
portones de 23 a 46 m² (2100–4159 BHP): más que el portón más grande publicado (21,34 m²), y de 4 a
7 veces los portones reales de los buques de investigación. Las tablas de portones crecen como la
potencia a la 0,65: el ajuste de la del *Workbook* {cite:p}`prado1990` da 0,646, y el de la de
Fishbuster {cite:p}`netsystems_fishbuster`, 0,656. En modo corregido, por encima de 180 BHP, la
superficie se multiplica por $(180/\mathrm{BHP})^{0{,}35}$; en modo `EXCEL` y hasta 180 BHP el
factor es 1, de modo que el caso del libro y sus valores dorados no cambian.

La tabla siguiente es el caso por defecto de cada buque de la flota ({doc}`39_flota_argentina`;
red A-3 y portón plano de la A-3 a 32°), con la superficie por portón según la regla del libro y la
corregida. La columna *Fishbuster* da las tallas de esa tabla cuyo rango de potencia cruza la del
buque (±5 %). Los portones reales son los que documenta el INIDEP: 5,58 m² en el Holmberg
{cite:p}`tringali2012eh0612`, el mismo equipo en el Oca Balda {cite:p}`dato2013global`, y el
Morgère SPF08 de 4,5 m² en el Angelescu {cite:p}`roth2017angelescu` (hoy un SPF 08,5 de 4,8 m²,
{cite:p}`rubio2024calibracion`). Un congelador comercial de la flota, el «Beagle I», usa portones
Polar Mercury de 2300 kg; por la tabla de Polar serían de unos 7–8 m², pero el informe no da la
superficie.

```{code-cell} ipython3
:tags: [remove-input]
sys.path.insert(0, str(pathlib.Path.cwd()))
import _door_area as DA

V.md_table(DA.TABLE_HEADERS, DA.table_rows())
```

La superficie corregida queda dentro del rango Fishbuster o hasta un 33 % por encima (el test
`test_door_area_power.py` admite hasta un 35 %). Con la regla del libro, los buques de más de
1300 BHP quedaban de 2,6 a 3,7 veces por encima del máximo de la tabla. Para los buques de
investigación la corregida sigue siendo una cota superior: remolcan una red de campaña estándar muy
por debajo de su tiro total.

## Saturación de la DPA de Fridman con el cable

La errata `fridman_dp_warp_saturation` tampoco es una fórmula mal escrita: en la DPA de Fridman
(`Mec!P164`, {doc}`16_aberturas`) el cable horizontal $L_{sh}$ está arriba y abajo de la fracción,
$2 L_{sh} L_{Rw} E_{dy} / (L_{sh} + L_{nc}(1 + E_{dx}))$, así que con cable largo la separación de
portones casi no cambia. En el mar sigue creciendo ({doc}`32_validacion_merluza`). En modo
corregido la DPA se multiplica por $(L_s/L_{s,tabla})^{\Delta n}$, con $L_{s,tabla}$ el cable de
la tabla del libro para la profundidad y $\Delta n$ ajustado a 103 lances medidos con cable
publicado (procedencia *calibrada*). Con el cable de la tabla el factor vale 1: el caso del libro,
sus valores dorados y todo caso de diseño no cambian; sólo actúa con un cable medido
(`DesignCase.measured_warp_m`).

```{code-cell} ipython3
:tags: [remove-input]
from trawlkit import rigging
from trawlkit.compat import Compat

DN = rigging.DP_WARP_EXPONENT_CORRECTION
rows = []
for depth in (40.0, 100.0, 400.0):
    tab = rigging.table_warp_m(depth)
    for k in (0.5, 1.0, 1.5, 2.0):
        w = k * tab
        rows.append([V.fmt(depth, 0), V.fmt(w, 0), V.fmt(k, 1),
                     V.fmt(rigging.dp_warp_factor(w, depth), 3),
                     V.fmt(rigging.dp_warp_factor(w, depth, Compat.EXCEL), 3)])
print(f"Δn = {DN:.2f}".replace(".", ","))
V.md_table(["Profundidad [m]", "Cable [m]", "Cable / tabla", "Factor (corregido)", "Factor (Excel)"],
           rows)
```
