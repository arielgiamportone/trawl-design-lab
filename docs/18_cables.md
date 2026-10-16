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

# Cables de remolque

## Propósito

Los cables de remolque (cables de arrastre o *warps*) transmiten el tiro del buque a los portones y
fijan, con su largo, la profundidad y la separación de los portones. Hay que dimensionarlos dos
veces: **hidrodinámicamente**, porque su resistencia se suma a la del arte, y **estructuralmente**,
porque deben soportar la tensión de trabajo con un margen para los tirones y enganches.

Este capítulo replica la hoja *Cables de Remolque* y la selección del cable de *Cables Y
Cabulleria*. Usa la geometría de los portones y del aparejo ({doc}`15_portones_aparejo`), la
resistencia de la red ({doc}`14_resistencia`) y de las boyas ({doc}`17_flotacion_lastre`), y
entrega la resistencia total que se compara con el tiro en {doc}`19_ventana_velocidad`. En
`trawlkit` vive en `trawlkit.rigging.warps`.

## Teoría

### Ángulos del cable

Tres ángulos describen la geometría del sistema, todos a partir de longitudes ya conocidas:

$$
\delta_1 = \arcsin\!\frac{d + h}{L_s}, \qquad
\delta_2 = \arcsin\!\frac{D_s - a}{2\,L_s}, \qquad
\delta_3 = \arcsin\!\frac{D_s - DPA}{2\,(L_p + V_s)}
$$ (eq-18-angulos)

$\delta_1$ es la **declinación** del cable en el plano vertical (profundidad $d$ más puntal del
buque $h$, sobre el cable filado $L_s$); $\delta_2$ la **divergencia** en planta, la misma
{eq}`eq-15-divergencia` del capítulo de portones; y $\delta_3$ el ángulo de bridas y patentes, con
la DPA por triángulos semejantes $DPA = D_s\,m/(m + L_p + V_s)$ ($m$ = burlón). En arrastre de
fondo $\delta_1$ suele estar entre 10 y 20°: con relaciones $L_s/d$ menores el cable tira de los
portones hacia arriba y los despega del fondo.

### Diámetro

El libro estima el diámetro con dos reglas. La primera, pensada para buques de más de 500 HP,
escala con la potencia efectiva de remolque:

$$
D_w = 18 + 0{,}0034\cdot EHP \quad [\text{mm}]
$$ (eq-18-d-ehp)

La segunda es el ajuste logarítmico de {cite:t}`perezaguila2010` sobre buques de rada o ría:

$$
D_w = 5{,}6822\,\ln(NHP) - 17{,}225 \quad [\text{mm}]
$$ (eq-18-d-aguila)

Para 150–180 HP la regla del EHP queda fuera de su rango (da ≈ 18 mm casi sin depender de la
potencia), por lo que el libro adopta el ajuste de Pérez Águila con la potencia del buque mayor de
la clase, 180 HP: $D_w$ = 12,28 mm.

### Resistencia hidrodinámica del cable

Un cable inclinado respecto de la corriente recibe una fuerza mucho menor que uno perpendicular. La
fórmula de resistencia de los dos cables es la de un cuerpo largo de área frontal $D_w L_s$:

$$
R_W = 2\cdot\tfrac12\,C_D\,\frac{\rho}{g}\,D_w\,L_s\,v^2
$$ (eq-18-rw)

y toda la física está en $C_D$. {cite:t}`nomurayamazaki` tabulan $C_D$ en función del ángulo de
ataque $\alpha$ entre el cable y el flujo: 0,02 a 0°, 0,04 a 10°, 0,09 a 20°, 0,18 a 30° y 0,30 a
40°. El libro toma $\alpha = \delta_2$ = 4,3° y el valor tabulado más cercano, 0,02.

Como referencias, la hoja calcula también el cable como **cilindro en flujo cruzado**
($C_D$ = 1,1–1,2 para $Re = v D_w/\nu \approx 10^4$) y el coeficiente de {cite:t}`maclennan1981`
para cables normales al flujo,

$$
C_D = 2{,}11 - 12{,}24\,v\,D_w \qquad (D_w \text{ en m})
$$ (eq-18-maclennan)

Ambos suponen el cable perpendicular a la corriente y son, por lo tanto, cotas superiores muy
holgadas. La experiencia práctica resume el problema en una fracción del tiro: la resistencia de
los cables es del 4 al 10 % de $F_T$ (Craig 4 %, Podeur 5–8 %, Hansen 5 %, Gudnasson 5–10 %,
Nomura 4–10 %; {cite:p}`warpshare`). {cite:t}`kowalskigianotti` proponen $C_D$ = 0,02 para
cables casi alineados con el flujo, el mismo valor que resulta aquí.

### Resistencia total, peso y cargas

La resistencia total que el buque debe remolcar es

$$
R_T = R_N + R_B + R_W\,(+R_{OB})
$$ (eq-18-rt)

donde el término de los portones falta en el Excel (errata `warp_total_omits_doors`, ver
{doc}`19_ventana_velocidad`). El peso del cable de acero se estima con
$w_{aire} = \tfrac12(0{,}00368 + 0{,}00417)\,D_w^2$ kg/m ($D_w$ en mm) y en el agua
$w_{agua} = 0{,}87\,w_{aire}$.

La **carga de trabajo** es la resistencia total a la velocidad máxima de diseño (3,5 kn), y la
**carga mínima de rotura** se obtiene con un coeficiente de seguridad $n_s = 4$:

$$
T_{rot} \ge n_s\,R_T(v_{dis}), \qquad n_s = 4
$$ (eq-18-rotura)

Es una hipótesis conservadora: cada uno de los dos cables lleva aproximadamente la mitad de $R_T$,
de modo que el coeficiente efectivo por cable es ≈ 8. El margen cubre las cargas dinámicas
(cabeceo del buque, enganches en el fondo), que pueden multiplicar varias veces la tensión media.

Por último, el cable se elige del catálogo (acero 6×19+1 Seale compactado) como el **menor
diámetro que cumple a la vez** $D \ge D_w$ y $T_{rot}$, y la cantidad a comprar es
$2\,L_s + 0{,}5\,L_s$ (dos cables más un 50 % de reserva para filar más en fondos más profundos y
para recortar los extremos gastados).

## Coeficientes

| Símbolo | Valor | Unidad | Fuente | Celda |
|---|---|---|---|---|
| $h$ (puntal) | según buque | m | Tipo de buques | `Rem!E33` |
| regla EHP | 18; 0,0034 | mm; mm/HP | regla práctica (> 500 HP) | `Rem!F73` |
| Pérez Águila | 5,6822; −17,225 | mm | {cite:t}`perezaguila2010` | `Rem!E80` |
| NHP de dimensionado | 180 | HP | buque mayor de la clase | `Rem!E78`, `E110` |
| $C_D(\alpha)$ | 0,02 … 0,30 (0–40°) | — | {cite:t}`nomurayamazaki` | `Rem!A90:B94`, `E106` |
| $C_D$ cilindro | 1,1 (≤ 2,5 kn); 1,2 (≥ 3 kn) | — | — | `Rem!E167:E175` |
| MacLennan | 2,11; −12,24 | — | {cite:t}`maclennan1981` | `Rem!D227` |
| $R_W/F_T$ | 4–10 % | — | {cite:p}`warpshare` | `Rem!D184:H184` |
| peso en aire | ½(0,00368 + 0,00417)·$D^2$ | kg/m | catálogo | `Rem!E248` |
| peso en agua | 0,87 × aire | — | — | `Rem!F252` |
| $v_{dis}$ | 3,5 | kn | — | `Rem!E267` |
| $n_s$ | 4 | — | — | `Rem!D271` |
| reserva de cable | 0,5·$L_s$ | m | — | `Cab!D12` |

## Equivalencia Excel ↔ `trawlkit`

| Celda(s) | Cálculo | Función |
|---|---|---|
| `Rem!F17`, `F19` | DPA por triángulos semejantes | `rigging.dpa_similar_triangles_m` |
| `Rem!E25`, `E29`, `E33` | $\delta_2$, $\delta_3$, $\delta_1$ | `rigging.warp_angles_deg` |
| `Rem!F73:F74` | diámetro por EHP | `rigging.warp_diameter_ehp_mm` |
| `Rem!E80:E81` | diámetro de Pérez Águila | `rigging.warp_diameter_aguila_mm` |
| `Rem!E106` | $C_D$ Nomura–Yamazaki | `rigging.warp_cd` |
| `Rem!G118:G126` | $R_W$ | `rigging.warp_drag_kgf` |
| `Rem!H118:I126` | $R_T$ | `rigging.total_drag_kgf` (errata `warp_total_omits_doors`) |
| `Rem!D167:G175` | cable como cilindro | `rigging.warp_drag_cylinder` |
| `Rem!E191:H199` | $R_W$ como % de $F_T$ | `rigging.warp_drag_share_kgf` |
| `Rem!D227:D235` | $C_D$ de MacLennan | `rigging.warp_cd_maclennan` |
| `Rem!E248:F257` | pesos | `rigging.warp_weight` |
| `Rem!E267`, `E272` | carga de trabajo y de rotura | `rigging.working_load_and_breaking_load` |
| `Cab!D11:I11` | selección | `rigging.select_warp` (errata `warp_undersized`) |
| `Cab!D12` | cantidad | `rigging.warp_quantity_m` |
| hoja completa | etapa `warps` | `model.run` → `result.warps` |

## Supuestos y límites

- **Ángulo de ataque.** El libro entra a la tabla de Nomura–Yamazaki con la divergencia en planta
  $\delta_2$ (4,3°) e ignora la declinación $\delta_1$ (12,1°), que es el ángulo dominante entre
  el cable y el flujo. Con 12° el valor tabulado más cercano sería 0,04 y $R_W$ se duplicaría.
  Aun así $R_W$ quedaría en ≈ 2 % de $F_T$, por debajo del 4–10 % de la literatura: el método
  del libro subestima la resistencia de los cables, aunque su peso en el total es pequeño.
- **Tabla discreta.** `Rem!E106` toma el ángulo tabulado **más cercano** (sin interpolar), de modo
  que $C_D$ salta en escalones de 10°.
- **Diámetro por potencia.** Ambas reglas de diámetro son correlaciones de flota; el criterio que
  manda es la carga de rotura.
- **Errata `warp_undersized`** (`Cab!D11`). La hoja elige el cable con
  `LOOKUP(Rem!E264, diamremolque, …)`: el mayor diámetro del catálogo que no supera el mínimo de
  12,28 mm, es decir, **12 mm**, cuya carga de rotura (8,55 t) es menor que los 8,80 t requeridos
  por {eq}`eq-18-rotura`. El cable seleccionado es a la vez más delgado que el diámetro mínimo y
  más débil que la carga mínima. `Compat.CORRECTED` elige el menor cable que cumple ambas
  condiciones: **13 mm, 10,3 t** ({doc}`erratas`).

## Ejemplo ejecutable

```{code-cell} ipython3
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.cwd().parent))
sys.path.insert(0, str(pathlib.Path.cwd()))

import numpy as np

from tests.golden_utils import golden
from trawlkit import Compat, rigging
import _plots_t2 as P

REM, CAB = "cables_de_remolque", "cables_y_cabulleria"
r = P.fao_result(150, "excel")
w = r.warps


def close(actual, key, sheet=REM):
    """Compara con el valor del Excel (escalar o serie) a rtol = 1e-6."""
    got, exp = np.atleast_1d(actual), np.atleast_1d(golden(sheet, key))
    return all(math.isclose(a, b, rel_tol=1e-6) for a, b in zip(got, exp))


assert close(w.angles.declination_deg, "warp_declination_deg")
assert close(w.angles.bridle_divergence_deg, "bridle_divergence_deg")
assert close(w.diameter_mm, "warp_diameter_aguila_180_mm")
assert close(w.cd, "warp_cd")
assert close(w.drag_kgf, "warp_drag_2_kgf")
assert close(w.total.std, "total_drag_std_kgf")  # RN + RB + Rw, sin ROB
assert close(w.cd_maclennan, "warp_cd_maclennan")
assert close(w.weight.total_water_kg, "warp_total_weight_water_kg")
assert close(w.loads.min_breaking_load_kgf, "warp_min_breaking_load_kgf")
assert close(w.selection.breaking_load_t, "warp_strength_t", CAB)  # 8,55 t
assert close(w.quantity_m, "warp_quantity_m", CAB)

a = w.angles
print(f"δ1 = {a.declination_deg:.2f}°, δ2 = {a.divergence_deg:.2f}°, "
      f"δ3 = {a.bridle_divergence_deg:.2f}°")
print(f"Ø: EHP {w.diameter_ehp_mm:.2f} mm, "
      f"Águila 150 HP {w.diameter_aguila_mm:.2f} mm, "
      f"Águila 180 HP {w.diameter_mm:.2f} mm")
i = r.case.speed_index(3.5)
print(f"A 3,5 kn: RN = {r.drag.rn.std[i]:.0f}, RB = {r.floats.drag_kgf[i]:.1f}, "
      f"Rw = {w.drag_kgf[i]:.1f} → RT = {w.total.std[i]:.0f} kgf")
print(f"Rotura mínima = 4 × {w.loads.working_load_kgf:.0f} "
      f"= {w.loads.min_breaking_load_kgf:.0f} kgf")
print(f"Peso del cable filado en agua = {w.weight.total_water_kg:.0f} kg; "
      f"a comprar {w.quantity_m:g} m")
```

La errata de la selección, con las mismas cargas en los dos modos:

```{code-cell} ipython3
need = w.loads.min_breaking_load_kgf
sx = rigging.select_warp(w.diameter_mm, need, compat=Compat.EXCEL)
sc = rigging.select_warp(w.diameter_mm, need, compat=Compat.CORRECTED)
assert sx.diameter_mm == golden(CAB, "warp_diameter_mm") == 12
assert sc.diameter_mm == 13
for tag, sel in (("Excel", sx), ("corregido", sc)):
    ok = "cumple" if sel.satisfies_breaking_load else "NO cumple"
    print(f"{tag:>9}: {sel.diameter_mm:g} mm, rotura {sel.breaking_load_t} t "
          f"→ {ok} los {need / 1000:.2f} t")
```

Cuatro maneras de estimar $R_W$ dan resultados que difieren en dos órdenes de magnitud
({numref}`fig-18-rw`): la de Nomura–Yamazaki con $C_D$ = 0,02 que usa el libro, la banda empírica
del 5–10 % del tiro y las dos cotas de cable perpendicular al flujo.

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Resistencia de los dos cables de remolque (12,28 mm, 200 m) por método, en escala
      logarítmica. La banda es el 5–10 % del tiro disponible (paso fijo, 150 HP). Los métodos de
      cilindro y de MacLennan tratan el cable como perpendicular a la corriente.
    name: fig-18-rw
---
P.setup()
kn, v = r.case.speeds, r.case.speeds_ms
rw_ny20 = rigging.warp_drag_kgf(rigging.warp_cd(a.declination_deg), w.diameter_mm / 1000, w.warp_m, v)
rw_mcl = rigging.warp_drag_kgf(1.0, w.diameter_mm / 1000, w.warp_m, v) * np.asarray(w.cd_maclennan)
fig, ax = P.plt.subplots(figsize=(7, 4.4))
ax.fill_between(kn, w.shares_kgf["fixed_pitch_5pct"], w.shares_kgf["fixed_pitch_10pct"],
                color=P.NEUTRAL_WASH, lw=0, label="5–10 % de $F_T$ (Craig … Nomura)")
series = ((w.drag_kgf, 1, "Nomura–Yamazaki, α = δ2 → $C_D$ = 0,02 (libro)"),
          (rw_ny20, 2, "Nomura–Yamazaki, α = δ1 → $C_D$ = 0,04"),
          (w.cylinder.drag_two_kgf, 3, "Cilindro, $C_D$ = 1,1–1,2"),
          (rw_mcl, 7, "MacLennan, $C_D$ = 2,11 − 12,24·v·D"))
for y, slot, lab in series:
    P.line(ax, kn, y, slot, lab)
ax.set_yscale("log")
ax.set_ylim(0.8, 5000)
ax.set_ylabel("$R_W$ de los dos cables [kgf]")
P.speed_axis(ax)
P.legend(ax, loc="lower right", fontsize=8.5)
P.finish(fig)
```

{numref}`fig-18-demanda` descompone la resistencia total por componente. La red explica más del
97 % del total del Excel; el portón, que el Excel omite, sería el segundo término.

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Composición de la resistencia total del sistema por velocidad (red estándar, modo Excel):
      red $R_N$, boyas $R_B$ y cables $R_W$. El segmento superior es la resistencia de un portón
      $R_{OB}$, que el Excel no suma y el modo corregido sí. $R_W$ (verde) es tan pequeña que apenas
      se ve sobre las boyas.
    name: fig-18-demanda
---
fig, ax = P.plt.subplots(figsize=(7, 4.4))
parts = ((r.drag.rn.std, 1, "Red $R_N$"), (r.floats.drag_kgf, 2, "Boyas $R_B$"),
         (w.drag_kgf, 3, "Cables $R_W$"), (r.doors.forces.drag_kgf, 4, "Portón $R_{OB}$ (sólo corregido)"))
bottom = np.zeros_like(kn)
width = 0.22
for y, slot, lab in parts:
    y = np.asarray(y)
    ax.bar(kn, y, width, bottom=bottom, color=P.color(slot), label=lab,
           edgecolor=P.SURFACE, linewidth=1.5, hatch="///" if slot == 4 else None)
    bottom = bottom + y
for x, tot, rt, rob in zip(kn, bottom, w.total.std, r.doors.forces.drag_kgf):
    if x in (2.0, 3.0, 4.0, 5.0):
        ax.annotate(f"{rt:,.0f} + {rob:.0f}".replace(",", " "), (x, tot), xytext=(0, 3),
                    textcoords="offset points", ha="center", fontsize=8.5, color=P.INK_2)
ax.set_ylabel("Resistencia [kgf]")
ax.set_ylim(0, 4800)
P.speed_axis(ax)
ax.grid(axis="x", visible=False)
P.legend(ax)
ax.text(0.02, 0.62, "etiquetas: $R_T$ del Excel ($R_N + R_B + R_W$)\n+ $R_{OB}$ de un portón [kgf]", transform=ax.transAxes,
        color=P.INK_2, fontsize=8.5, va="top")
P.finish(fig)
```

| v [kn] | 1,0 | 2,0 | 3,0 | 3,5 | 4,0 | 5,0 |
|---|---|---|---|---|---|---|
| $R_N$ estándar [kgf] | 422 | 915 | 1680 | 2152 | 2677 | 3871 |
| $R_B$ [kgf] | 2,4 | 9,8 | 23,4 | 31,9 | 41,7 | 65,1 |
| $R_W$ (Nomura–Yamazaki) [kgf] | 1,4 | 5,4 | 12,2 | 16,6 | 21,7 | 33,9 |
| $R_T$ Excel [kgf] | 426 | 930 | 1716 | 2200 | 2740 | 3970 |
| $R_{OB}$ de un portón [kgf] | 17,7 | 70,8 | 159,3 | 216,8 | 283,2 | 442,5 |
| $R_W$ como % de $F_T$ | 0,1 % | 0,4 % | 1,0 % | 1,5 % | 2,0 % | 3,5 % |
