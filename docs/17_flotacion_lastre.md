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

# Flotación y lastre

## Propósito

La abertura vertical de una red de fondo se sostiene con **flotación** en la relinga superior
(lima) y el contacto con el fondo con **lastre** en la relinga inferior (burlón). Poca flotación
cierra la boca; demasiada levanta el burlón y la red "vuela" sin pescar las especies de fondo.
Poco lastre produce el mismo efecto, y demasiado hace que el burlón are el fondo, aumente la
resistencia y dañe el sustrato.

Este capítulo replica la hoja *Flotación y Lastre* y los pesos de las relingas de *Cables Y
Cabulleria*. Usa el tiro disponible ({doc}`10_potencia`), la resistencia de la red
({doc}`14_resistencia`) y la geometría de bridas ({doc}`15_portones_aparejo`); su flotación total
alimenta la AV de Baranov–Fridman ({doc}`16_aberturas`) y la resistencia de las boyas entra en la
resistencia total del sistema ({doc}`18_cables`, {doc}`19_ventana_velocidad`). En `trawlkit` vive
en `trawlkit.rigging.floats`, `trawlkit.rigging.ballast` y `trawlkit.rigging.ropes`.

## Teoría

### Métodos empíricos de flotación

{cite:t}`koyama1974` ajusta la flotación de redes japonesas de fondo al largo de la lima $L$:

$$
F_K = 1{,}11\,L - 6{,}81 \quad [\text{kgf}]
$$ (eq-17-koyama)

y {cite:t}`prado1990` la escala con la potencia del buque, que es un indicador del tamaño de red
que el buque puede remolcar:

$$
F_P = K\cdot NHP, \qquad K = 0{,}2 \ \text{kgf/HP para } 50\text{–}600\ \text{NHP}
$$ (eq-17-prado)

### Balance de fuerzas verticales de Fridman

{cite:t}`fridman1986` dimensiona la flotación con el equilibrio vertical de la lima. Sobre ella
actúan dos tensiones que tiran hacia abajo y hacia atrás:

- $F_1$, la tensión que llega por las bridas: el libro toma el 80 % del tiro repartido en las cuatro
  bridas, $F_1 = 0{,}8\,F_T/4$. La brida superior sube hacia la punta de ala con el ángulo
  $\alpha$ entre bridas (4,8°), y su componente vertical es $F_1' = F_1\sin\alpha$.
- $F_2$, la parte de la resistencia de la red que soporta la lima, un cuarto de $R_N$. El paño del
  cuerpo baja desde la lima hacia la bolsa con el ángulo $\beta$, que sale de la abertura vertical
  y el largo del cuerpo $L_c$: $\beta = \arctan\!\big((AV/2)/L_c\big)$. Su componente vertical es
  $F_2' = F_2\sin\beta$.

La flotación debe compensar ambas componentes y el peso en el agua de la propia lima, $W_L$:

$$
F = F_1\sin\alpha + F_2\sin\beta + W_L, \qquad
F_1 = \frac{0{,}8\,F_T}{4}, \quad F_2 = \frac{R_N}{4}
$$ (eq-17-fridman)

Como $F_T$ cae con la velocidad y $R_N$ crece con $v^2$, $F_1'$ disminuye y $F_2'$ aumenta: a
baja velocidad domina el tiro de las bridas, a alta velocidad la resistencia del paño. El libro
promedia $F$ entre 1 y 3 kn para las redes estándar y modificada, por buque, y la flotación total
que usa la AV de Fridman es el promedio de esos dos valores (150 y 180 HP) con los dos de Prado:

$$
F_{fz} = \tfrac14\left(\bar F_{150} + \bar F_{180} + F_{P,150} + F_{P,180}\right)
$$ (eq-17-ffz)

Los pesos en el agua de las relingas de cable combinado (polipropileno con alma de acero) se
toman como 0,087 veces su peso en aire.

### Boyas: número, distribución y resistencia

El número de boyas es la flotación de diseño dividida por la flotación unitaria del catálogo,
redondeada. El libro elige 12 boyas de 200 mm (3,2 kgf cada una, 38,4 kgf en total, algo más que
los 36 kgf requeridos). Se reparten de dos maneras: **pareja**, a intervalos $L/n$, o
**selectiva**, con el 70 % en las alas (para levantar las puntas, que es donde la lima tiende a
caer) y el resto en el centro de la boca (bocana).

Cada boya es una esfera que agrega resistencia. Con el coeficiente de arrastre de una esfera lisa
en régimen subcrítico, $C_D \approx 0{,}47$ {cite:p}`hoerner1965`:

$$
R_B = n\cdot\tfrac12\,C_D\,\frac{\rho}{g}\,\frac{\pi D^2}{4}\,v^2, \qquad
Re = \frac{v\,D}{\nu}
$$ (eq-17-rb)

con $\nu$ el promedio de la viscosidad cinemática del agua de mar a 0 y 20 °C
(1,44·10⁻⁶ m²/s). El número de Reynolds verifica que la boya está por debajo de la crisis de
arrastre de la esfera lisa ($Re \approx 3$–$4\cdot10^5$), donde $C_D$ cae bruscamente a
≈ 0,1–0,2. El libro usa
0,47 hasta 2,5 kn y 0,5 desde 3 kn.

### Lastre

El lastre se calcula con las mismas tres escuelas. Koyama y Prado:

$$
W_K = 1{,}81\,L - 4{,}54, \qquad W_P = 0{,}28\cdot NHP \quad [\text{kg}]
$$ (eq-17-lastre-empirico)

y Fridman, por equilibrio vertical del burlón: el lastre debe compensar las mismas componentes
verticales que tiran del burlón hacia arriba, descontado el peso en el agua del propio burlón
$W_B$:

$$
W_F = F_1\sin\alpha + F_2\sin\beta - W_B
$$ (eq-17-lastre-fridman)

El **mínimo** es el lastre de Fridman de la red modificada a 1 kn (redondeado hacia abajo) y el
**máximo** el de la red estándar a 3 kn (redondeado hacia arriba). Se reparte con una cadena de
reglaje en el centro (20 % del mínimo, 30 % del máximo), la bocana (25 % y 20 %) y el resto en las
alas.

## Coeficientes

| Símbolo | Valor | Unidad | Fuente | Celda |
|---|---|---|---|---|
| Koyama flotación | 1,11; −6,81 | kgf/m; kgf | {cite:t}`koyama1974` | `Flot!F6` |
| $K$ Prado flotación | 0,2 | kgf/HP | {cite:t}`prado1990` | `Flot!I14` |
| fracción de $F_T$ en las bridas | 0,8 / 4 | — | {cite:t}`fridman1986` | `Flot!F42` |
| fracción de $R_N$ en la lima | 1/4 | — | {cite:t}`fridman1986` | `Flot!G42` |
| $\alpha$ entre bridas | 4,8 | ° | — | `Flot!F22` |
| peso en agua / peso en aire (cable combinado) | 0,087 | — | — | `Flot!F37`, `G191` |
| boya elegida | 12 × 200 mm (3,2 kgf) | — | catálogo | `Flot!F84`, `F92` |
| boyas en alas (selectiva) | 70 % | — | — | `Flot!F103` |
| $C_D$ esfera | 0,47 (≤ 2,5 kn); 0,5 (≥ 3 kn) | — | {cite:t}`hoerner1965` | `Flot!H129`, `I142` |
| $\nu$ agua de mar (0 / 20 °C) | 1,83·10⁻⁶ / 1,05·10⁻⁶ | m²/s | — | `Flot!H130:H131` |
| Koyama lastre | 1,81; −4,54 | kg/m; kg | {cite:t}`koyama1974` | `Flot!G159` |
| $K$ Prado lastre | 0,28 | kg/HP | {cite:t}`prado1990` | `Flot!G168` |
| reparto del lastre mínimo | 20 / 25 / 55 % | — | — | `Flot!F236:F238` |
| reparto del lastre máximo | 30 / 20 / 50 % | — | — | `Flot!F243:F245` |

## Equivalencia Excel ↔ `trawlkit`

| Celda(s) | Cálculo | Función |
|---|---|---|
| `Flot!F6` | flotación Koyama | `rigging.flotation_koyama_kgf` |
| `Flot!F17:G17` | flotación Prado | `rigging.flotation_prado_kgf` |
| `Flot!F23` | ángulo $\beta$ | `rigging.beta_deg` |
| `Flot!F36:F37`, `G188:G191` | pesos de lima y burlón | `rigging.rope_weight_air_kg`, `rigging.rope_weight_in_water_kg` |
| `Flot!F42:M63` | flotación de Fridman | `rigging.flotation_fridman` |
| `Flot!N43`, `N55` | promedio 1–3 kn | `rigging.flotation_fridman_average_kgf` |
| `Mec!O261` | $F_{fz}$ | `rigging.fridman_flotation_total_kgf` |
| `Flot!F72:F82`, `F92` | número de boyas y diámetro | `rigging.float_count`, `rigging.float_diameter_for_count_mm` |
| `Flot!F94:K112` | distribución de boyas | `rigging.distribute_floats` |
| `Flot!H138:H146` | Reynolds | `rigging.float_reynolds` (errata `float_reynolds`) |
| `Flot!I138:J146` | $C_D$ y $R_B$ | `rigging.float_cd`, `rigging.float_drag_kgf` |
| `Flot!G159`, `I173`, `I180` | lastre Koyama y Prado | `rigging.ballast_koyama_kg`, `rigging.ballast_prado_kg` |
| `Flot!L197:M218` | lastre de Fridman | `rigging.ballast_fridman_kg` |
| `Flot!F225:F226` | mínimo y máximo | `rigging.ballast_limits` |
| `Flot!H224:I245` | reparto del lastre | `rigging.adjust_chain_weight_kg`, `rigging.distribute_ballast_min`, `rigging.distribute_ballast_max` |
| hoja completa | etapas `floats` y `ballast` | `model.run` → `result.floats`, `result.ballast` |

## Supuestos y límites

- **Fracciones de Fridman.** El 80 % del tiro en las bridas y el cuarto de $R_N$ en la lima son
  reparticiones simplificadas; en realidad dependen de la forma de la boca. Los ángulos $\alpha$ y
  $\beta$ son pequeños (4,8° y 3,2°), de modo que la flotación es muy sensible a ellos:
  $\sin 4{,}8° = 0{,}084$, y un grado más agrega ≈ 20 % a $F_1'$.
- **Flotación a profundidad.** Las boyas de plástico rígido conservan su volumen; las de espuma
  pierden flotación con la presión. A 40 m el efecto es menor, pero a más profundidad hay que usar
  la flotación nominal a la profundidad de trabajo.
- **Lastre igual a flotación.** Fridman calcula flotación y lastre con las mismas componentes
  $F_1'$ y $F_2'$; la diferencia sólo está en el peso de la relinga, que se suma o se resta.
- **Errata `float_reynolds`** (`Flot!H138`): la hoja calcula $Re = \pi D^2 v/\nu$, es decir, usa
  el área $\pi D^2$ (en m²) donde va el diámetro. Con $D$ = 0,2 m el Reynolds del Excel es
  $\pi \cdot 0{,}2 = 0{,}63$ veces el correcto. No cambia el $C_D$, que la hoja escribe a mano, pero oculta
  algo relevante: con el Reynolds correcto las boyas de 200 mm llegan a $2{,}9\cdot10^5$ a 4 kn y
  $3{,}6\cdot10^5$ a 5 kn, es decir, al borde de la crisis de arrastre; allí $C_D$ = 0,47–0,5 es
  conservador (sobreestima $R_B$). Con el valor del Excel las boyas parecen holgadamente
  subcríticas.
- **Errata `flotation_rounding_inconsistent`** (`Flot!M43:M50`): el `ROUNDDOWN` se aplica a toda
  la tabla salvo a la columna modificada del bloque de 150 HP, que entra al promedio sin redondear.
- **Errata `float_lookup_unsorted`** (`Flot!F92`): el diámetro de la boya se busca con `LOOKUP`
  sobre el vector de cantidades, que no está ordenado; da 200 mm por casualidad. En modo corregido
  se elige la boya cuyo número requerido es el más cercano al elegido. Ver {doc}`erratas`.

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

FLOT = "flotacion_y_lastre"
r = P.fao_result(150, "excel")
f, b = r.floats, r.ballast


def close(actual, key, sheet=FLOT):
    """Compara con el valor del Excel (escalar o serie) a rtol = 1e-6."""
    got, exp = np.atleast_1d(actual), np.atleast_1d(golden(sheet, key))
    return all(math.isclose(a, b, rel_tol=1e-6) for a, b in zip(got, exp))


assert close(f.koyama_kgf, "flotation_koyama_kgf")
assert close(f.beta_deg, "beta_deg")
assert close(f.fridman.std.total_kgf, "flotation_total_std_150_kgf")
# modificada 150 HP sin ROUNDDOWN (errata flotation_rounding_inconsistent)
assert close(f.fridman.mod.total_kgf, "flotation_total_mod_150_kgf")
assert close(f.fridman_average_kgf, "flotation_fridman_avg_150_kgf")
assert close(f.flotation_total_kgf, "flotation_total_kgf", "mecanica_de_la_red")
assert close(f.reynolds, "float_reynolds")  # Re = π·D²·v/ν (errata)
assert close(f.drag_kgf, "float_drag_kgf")
assert close(b.fridman.std, "ballast_std_150_kg")
assert close(b.limits.min_kg, "ballast_min_150_kg")
assert close(b.limits.max_kg, "ballast_max_150_kg")

f180 = f.class_fridman_average_kgf["fao_a3_180hp"]
print(f"Flotación: Koyama {f.koyama_kgf:.1f}, Prado {f.prado_kgf:.0f}, "
      f"Fridman 150 HP {f.fridman_average_kgf:.1f}, Fridman 180 HP {f180:.1f}")
print(f"Ffz = {f.flotation_total_kgf:.2f} kgf")
dist = f.distribution
print(f"Boyas: {f.count} × {f.diameter_mm:g} mm = {f.count * 3.2:.1f} kgf; "
      f"pareja cada {dist.spacing_even_m:.2f} m")
print(f"Selectiva: {dist.on_wings} en alas, {dist.on_bosom} en la bocana")
print(f"Lastre: Koyama {b.koyama_kg:.1f} kg, Prado {b.prado_kg:.0f} kg, "
      f"Fridman {b.limits.min_kg:g}–{b.limits.max_kg:g} kg")
for tag, dd in (("mínimo", b.distribution_min), ("máximo", b.distribution_max)):
    print(f"Reparto {tag}: reglaje {dd.adjust_kg:g} kg, bocana {dd.bosom_kg:g} kg, "
          f"alas {dd.wings_kg:g} kg ({dd.wings_kg_m:.2f} kg/m)")
```

La errata del Reynolds en los dos modos:

```{code-cell} ipython3
v = r.case.speeds_ms
re_x = rigging.float_reynolds(0.2, v, compat=Compat.EXCEL)
re_c = rigging.float_reynolds(0.2, v, compat=Compat.CORRECTED)
assert close(re_x, "float_reynolds")
print(f"Re a 1 kn: Excel {re_x[0]:,.0f}, corregido {re_c[0]:,.0f}")
print(f"Re a 5 kn: Excel {re_x[-1]:,.0f}, corregido {re_c[-1]:,.0f}")
print(f"cociente Excel/corregido = π·D = {re_x[0] / re_c[0]:.4f}")
```

{numref}`fig-17-flotacion` resume los métodos. La flotación de Fridman crece con la velocidad
porque domina la componente de la resistencia del paño; la de diseño (promedio 1–3 kn) queda entre
Prado y la flotación real de las 12 boyas. El lastre de Fridman sigue la misma forma desplazada por
el peso de las relingas, y Koyama queda por encima del rango de Fridman para esta red liviana.

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Arriba, flotación requerida por la lima según Fridman (150 HP, redes estándar y
      modificada) frente a los métodos de Koyama y Prado, la flotación total $F_{fz}$ y la
      flotación instalada (12 boyas de 200 mm). Abajo, lastre de Fridman y rango mínimo–máximo
      adoptado (banda), con Koyama y Prado como referencia.
    name: fig-17-flotacion
---
P.setup()
kn = r.case.speeds
fig, (a1, a2) = P.plt.subplots(2, 1, figsize=(7, 8.4))

P.line(a1, kn, f.fridman.std.total_kgf, 1, "Fridman, estándar")
P.line(a1, kn, f.fridman.mod.total_kgf, 2, "Fridman, modificada")
consts = ((f.koyama_kgf, 3, "Koyama"), (f.prado_kgf, 4, "Prado (150 HP)"),
          (f.flotation_total_kgf, 7, "$F_{fz}$ (total, Mec!O261)"))
for val, slot, lab in consts:
    a1.plot([1, 5], [val, val], color=P.color(slot), lw=2, label=lab)
inst = f.count * 3.2
a1.plot([1, 5], [inst, inst], color=P.NEUTRAL, lw=1.4, ls=(0, (4, 3)), label="Instalada: 12 × 3,2 kgf")
a1.axvline(3, color=P.AXIS, lw=1, zorder=0)
a1.annotate("← promedio de diseño (1–3 kn)", (3.05, 12), color=P.INK_2, fontsize=9)
a1.set_title("Flotación de la lima")
a1.set_ylabel("Flotación [kgf]")
a1.set_ylim(0, 76)
P.speed_axis(a1)
P.legend(a1, loc="upper left")

a2.fill_between([1, 5], b.limits.min_kg, b.limits.max_kg, color=P.NEUTRAL_WASH, lw=0,
                label=f"Rango adoptado {b.limits.min_kg:g}–{b.limits.max_kg:g} kg")
P.line(a2, kn, b.fridman.std, 1, "Fridman, estándar")
P.line(a2, kn, b.fridman.mod, 2, "Fridman, modificada")
for val, slot, lab in ((b.koyama_kg, 3, "Koyama"), (b.prado_kg, 4, "Prado (150 HP)")):
    a2.plot([1, 5], [val, val], color=P.color(slot), lw=2, label=lab)
a2.set_title("Lastre del burlón")
a2.set_ylabel("Lastre [kg]")
a2.set_ylim(0, 76)
P.speed_axis(a2)
P.legend(a2, loc="upper left")
P.finish(fig)
```

| v [kn] | 1,0 | 1,5 | 2,0 | 2,5 | 3,0 | 4,0 | 5,0 |
|---|---|---|---|---|---|---|---|
| $F_1' = F_1\sin\alpha$ [kgf] | 23,3 | 22,5 | 21,6 | 20,7 | 19,8 | 18,1 | 16,3 |
| $F_2' = F_2\sin\beta$ estándar [kgf] | 5,9 | 8,8 | 12,7 | 17,6 | 23,4 | 37,2 | 53,8 |
| Flotación Fridman estándar [kgf] | 30 | 32 | 35 | 39 | 44 | 56 | 71 |
| Lastre Fridman estándar [kg] | 27,4 | 29,4 | 32,5 | 36,5 | 41,4 | 53,5 | 68,4 |
| $R_B$ (12 boyas) [kgf] | 2,4 | 5,5 | 9,8 | 15,3 | 23,4 | 41,7 | 65,1 |

La resistencia de las boyas es pequeña frente a la de la red (≈ 1,4 % a 3 kn), pero no
despreciable: a 5 kn duplica la de los dos cables de remolque calculada con el coeficiente de
Nomura–Yamazaki ({doc}`18_cables`).

## Ejercicios

Del banco del modo docente, con los datos del libro. En la app, el modo «Aula UTN» los genera con
otros datos y los corrige ({doc}`38_docentes`).

```{code-cell} ipython3
:tags: [remove-input]
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path.cwd()))
import _exercises
_exercises.section("17_flotacion_lastre")
```
