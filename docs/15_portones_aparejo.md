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

# Portones y aparejo

## Propósito

Los portones son las "alas" del arte: dos placas que, remolcadas con un ángulo de ataque, generan
una fuerza lateral que separa los cables y abre la red en horizontal. Esa fuerza tiene un precio,
la resistencia de los portones $R_{OB}$, que el buque paga con parte de su tiro. Entre los portones
y la red está el **aparejo**: pies de gallo, patentes (malletas) y bridas (vientos), que transmiten
la fuerza de abertura a las puntas de ala y fijan la geometría de la boca.

Este capítulo replica la hoja *Portones y aparejamiento*. En la cadena de cálculo ({doc}`motor`)
se ubica después de la resistencia de la red ({doc}`14_resistencia`) y del cable filado, y
alimenta las aberturas ({doc}`16_aberturas`), la flotación ({doc}`17_flotacion_lastre`) y los
cables ({doc}`18_cables`). En `trawlkit` vive en `trawlkit.rigging.doors` y
`trawlkit.rigging.bridles`.

## Teoría

### Fuerzas hidrodinámicas del portón

Un portón de superficie $S$ que avanza a velocidad $v$ con un ángulo de ataque $\alpha$ recibe una
fuerza hidrodinámica que se descompone en una componente paralela al avance, la resistencia, y una
perpendicular, la fuerza de abertura (sustentación). Con la presión dinámica escrita en unidades
técnicas, como en todo el libro {cite:p}`fridman1986`:

$$
R_{OB} = \tfrac12\,\frac{\rho}{g}\,C_D\,S\,v^2, \qquad
F_y = \tfrac12\,\frac{\rho}{g}\,C_L\,S\,v^2
$$ (eq-15-fuerzas)

con $\rho = 1024$ kg/m³, $g = 9{,}81$ m/s², $S$ en m² y $v$ en m/s, de modo que $\rho/g$ es la
"masa específica" en kgf·s²/m⁴ y las fuerzas salen directamente en kgf. Ambas crecen con $v^2$:
duplicar la velocidad cuadruplica la abertura y la resistencia del portón.

Los coeficientes $C_L$ y $C_D$ dependen del ángulo de ataque y se leen de la **polar** del portón
(ensayos en canal o túnel). En un portón plano rectangular de baja relación de aspecto
($\lambda = h/l \approx 0{,}5$), $C_L$ crece casi linealmente hasta un máximo cerca de 30–35° y
luego la placa entra en pérdida, mientras $C_D$ sigue aumentando. El punto de trabajo razonable
está justo antes del máximo de $C_L$: la relación $C_L/C_D$ (eficiencia) cae a partir de allí y
cada kgf de abertura extra cuesta cada vez más tiro. El libro trabaja a $\alpha = 32°$
($C_L = 0{,}93$, $C_D = 0{,}71$, $C_L/C_D = 1{,}31$) con el portón plano de madera y bastidor de
hierro de la FAO para las redes A3/B3/C3; el catálogo incluye también un portón ovalado
polivalente Morgère, más eficiente ($C_L/C_D \approx 1{,}6$ a 27–30°). Las dos polares del libro
son, número por número, las hojas «Flat Wooden» y «Morgère Polyvalent Ovale» del ensayo en tanque
de flujo de Seafish, IFREMER y DIFTA {cite:p}`sfia1993` (ver más abajo).

### Separación entre portones: la regla "al metro"

La distancia entre portones $D_s$ se estima con una regla práctica: cada metro de cable filado
$L_s$ abre una cierta separación $k$ (2,65 m en el libro), descontada la distancia entre pastecas
$a$ del buque, que es la separación de partida:

$$
D_s = (k - a)\,L_s + a
$$ (eq-15-ds)

Con ella se obtiene el semiángulo de divergencia de los cables, que es el ángulo $\delta_2$ del
capítulo {doc}`18_cables`:

$$
\tfrac12\varphi = \arcsin\!\left(\frac{D_s - a}{2\,L_s}\right)
$$ (eq-15-divergencia)

y una separación corregida $D_s' = 1{,}15 \cdot 2\,L_s \sin(\tfrac12\varphi)$, que aplica un
factor empírico por la curvatura del cable.

### Resistencia de los portones como fracción del tiro y superficie requerida

Fridman propone dimensionar los portones para que su resistencia sea entre el 15 y el 30 % del tiro
disponible $F_T$ {cite:p}`fridman1986`; el libro adopta el 20 %:

$$
R_{OB} = p\,F_T, \qquad p \in [0{,}15;\ 0{,}30]
$$ (eq-15-rob-share)

Invirtiendo {eq}`eq-15-fuerzas` con esa resistencia se obtiene la superficie total de portones
que el buque "puede pagar" a cada velocidad:

$$
S_{req} = \frac{2\,R_{OB}}{(\rho/g)\,C_D\,v^2}
$$ (eq-15-sreq)

Como $F_T$ disminuye con la velocidad y $v^2$ aumenta, $S_{req}$ cae muy rápido: a 1 kn saldrían
decenas de m². El libro promedia $S_{req}$ entre 2 y 4 kn, lo divide por dos portones y promedia
los buques de 150 y 180 HP.

### Fuerza sobre el portón, centro de presión y equilibrio de momentos

Para verificar el reglaje (la posición de los puntos de enganche del pie de gallo) el libro calcula
la fuerza normal sobre la placa con la fórmula de placa plana

$$
P_\varphi = \tfrac12\,C_D\,\frac{\rho}{g}\,v^2\,S\,\frac{2\sin\varphi}{1+\sin^2\varphi}
$$ (eq-15-pphi)

y el centro de presión, medido desde el borde de ataque sobre el largo $L$ del portón,

$$
d = \frac34\,\frac{\cos\varphi}{4 + \pi\sin\varphi}\,L, \qquad
h_A = \frac{0{,}8\,L}{4}, \quad h_B = \frac{L}{4}
$$ (eq-15-cp)

El portón queda en equilibrio cuando el momento de $P_\varphi$ respecto del enganche
($P_\varphi\,d$) se compensa con el de la tensión de la patente ($\tfrac12 R_N$ por portón) con su
brazo $d_p$ (3 m en el libro): $M_P = P_\varphi\,d$ frente a $M_R = \tfrac12\,R_N\,d_p$.

### Bridas, patentes y pies de gallo

Las **bridas** (vientos) unen la punta de ala con el extremo de la patente. Con la red abierta una
altura $AV$, la brida superior forma un ángulo $\alpha_b$ (4,8° en el libro) con la inferior, y su
largo según {cite:t}`martini` es

$$
V_s = \frac{AV}{\sin\alpha_b} - f_L \quad\text{(sin triángulo)}, \qquad
V_s^{\triangle} = \frac{AV - h_{dl}}{\sin\alpha_b} \quad\text{(con triángulo / dan leno)}
$$ (eq-15-bridas)

donde $f_L$ es la flecha de la lima (capítulo {doc}`16_aberturas`) y $h_{dl}$ la altura del
triángulo o dan leno (0,6 m). La brida inferior se acorta con una cadena de reglaje del 9,5 % de
$V_s$.

Las **patentes** se dimensionan por dos caminos: la regla de Dremière, una fracción del cable
filado ($L_p = L_s/6$, {cite:p}`prado1990`), y la geometría de Martini, que pide que la red de
largo $L_R$ y abertura $DPA$ quepa en el triángulo que forman los portones:

$$
L_p = \left(\frac{D_s\,L_R}{DPA} - (V_s + L_R)\right) \cdot 1{,}1
$$ (eq-15-patentes)

Martini da además una versión por ángulo, $L_p = (D_s - DPA)/(2\sin\delta)$ con $\delta = 20°$.
El **pie de gallo** se toma 20 % más largo que el portón, $PG = 1{,}2\,L$. Finalmente, el ángulo
de ataque de bridas y patentes, que interesa para el arreo de peces y para la DPA, es

$$
\delta = \arcsin\!\left(\frac{(D_s - DPA)/2}{PG + L_p + V_s}\right)
$$ (eq-15-delta)

Los valores habituales de $\delta$ para arrastre de fondo están entre 10 y 20°; ángulos mayores
aumentan el arreo pero también la resistencia del aparejo.

### Biblioteca de polares por tipo de portón

La fuente primaria de las polares del libro es el informe *Otterboard Performance and Behaviour*
{cite:p}`sfia1993`: 26 modelos de portón ensayados en los tanques de flujo de Hull, Boulogne y
Hirtshals, a 0,9 m/s sobre la cinta móvil (el $C_D$ incluye el rozamiento con la cinta), de 25 a
45° de ataque. Cada hoja de datos del Apéndice IV da las medidas del modelo, la relación de
aspecto $H/L$, la relación de superficie, el peso en aire y en agua, $C_L$ y $C_D$ cada 5° y el
$C_L$ máximo con su ángulo. El libro Excel de la A-3 {cite:p}`giamportone2024` copió dos de ellas
tal cual: «Flat Wooden» (App. IV-3) y «Morgère Polyvalent Ovale» (App. IV-17; el «0» a 25° de la
hoja Excel es un ángulo no ensayado, marcado «–» en Seafish).

`trawlkit` guarda las 26 hojas, transcriptas y verificadas página por página, en
`trawlkit/data/door_polars.yaml`, junto con las tablas del portón pelágico Thyborøn 15 VF
(relación de aspecto 2,5) y del Grilli Fly (1,91) de {cite:t}`mellibovsky2018`, medidas en el
tanque de flujo de St John's y en túnel de viento. `rigging.polar_for_type` da una polar
representativa por tipo:

| Tipo | Polar | Procedencia |
|---|---|---|
| plano | hoja «Flat Wooden» | transcripta |
| en V | media de Reference Vee, Blooe Tech y Munkebo, como recomienda {cite:t}`sfia1993` (sección 3-16) | derivada |
| oval | hoja «Morgère Polyvalent Ovale» | transcripta |
| cambado (con ranura) | media de Net Tec, Perfect Patent B y Thyborøn Type 2 de 125" | derivada |
| multiperfil | media de Bison 3 Slots, Hydrofin, Morgère Polyfoil y Fjørtoft (30–45°) | derivada |
| pelágico de alta relación de aspecto (Süberkrüb) | Thyborøn 15 VF en tanque de flujo: $C_L$ lineal y $C_D$ cuadrático ajustados a los 11 puntos | derivada |

Hasta la Fase 19.2 la polar en V del catálogo era la del portón plano con $C_L$ multiplicado por
0,775/0,93 y la del Süberkrüb era la del oval: ninguna era medida. Para el pelágico,
{cite:t}`mellibovsky2018` encuentran que el tanque de flujo da 20–30 % menos que el túnel de viento
y lo atribuyen a un error de la velocidad nominal del tanque; los valores «teóricos» del Süberkrüb
de {cite:t}`scharfe1955` ($C_L/C_D \approx 14$ a 9,5°, sin fondo) no se usan: quedan como
referencia de confianza baja. Ningún fabricante publica la polar de sus portones: los de Vónin
{cite:p}`vonin_doors` (superficie y peso) y Morgère {cite:p}`morgere2025` (superficie; el peso es
«sur demande» y queda vacío) llevan la polar de su tipo marcada como *supuesta*. La afirmación de
Vónin de un $C_L$ de 4,39 para el Twister queda como nota, no como dato.

En modo corregido `rigging.door_polar` interpola linealmente entre los ángulos tabulados y, hasta
5° fuera del rango medido, extrapola con el tramo extremo y avisa (la nota `door_polar:` del
resultado); el modo `EXCEL` sigue pidiendo un ángulo de la tabla, como el `LOOKUP` del libro.

### Elección del portón: superficie equivalente

El motor da la superficie requerida por portón $A_1$ (`Port!F215`) para el portón del caso, con su
$C_D$. Para cambiar de tipo de portón conservando la fuerza de abertura, {cite:t}`sfia1993`
(App. III-9) igualan $A_1\,C_{L1} = A_2\,C_{L2}$:

$$
A_2 = A_1\,\frac{C_{L1}}{C_{L2}}, \qquad L_2 = \sqrt{\frac{A_1\,C_{L1}}{C_{L2}\,AR_2\,C_{A2}}}
$$ (eq-15-equivalente)

con $C_L$ al ángulo de trabajo de cada portón, $AR_2 = H_2/L_2$ y $C_{A2}$ la relación de
superficie. Como portones del mismo tipo rinden distinto (el Munkebo da 27 % más $C_L$ que los
otros dos en V), al pasar a un portón de más $C_L$ recomiendan sumar **10 %** a la superficie
calculada (sección 3-16). La herramienta `trawlkit.door_selection.select_doors` (y
`POST /doors/select`, «Elegir portón» en la app) aplica la regla a todo el catálogo de componentes
filtrado y además:

- toma $C_{L2}$ al ángulo del caso si el portón es del mismo tipo y, si no, al ángulo de ataque
  recomendado del tipo: plano 35–40°, en V y oval 35°, Süberkrüb 15° {cite:p}`prado1990`;
  cambados 34–37° y multiperfil 40–45° (ángulo de $C_L$ máximo de las hojas de Seafish);
- deja fuera los pelágicos de alta relación de aspecto en una red de fondo: son inestables a las
  velocidades bajas del arrastre de fondo ({cite:t}`sfia1993`, §2.2.1);
- compara el peso con el del *Fisherman's Workbook* para el tipo y la superficie: la tabla da el
  peso máximo usado y aclara que con un material liviano un portón puede pesar hasta 50 % menos
  {cite:p}`prado1990`; un portón más liviano se marca y uno sin peso publicado se avisa;
- da el largo de las patas de gallo (*backstrops*): cada una no menos que el largo del portón y
  hasta 1,5 veces ({cite:t}`sfia1993`, §2.2.3).

## Coeficientes

| Símbolo | Valor | Unidad | Fuente | Celda |
|---|---|---|---|---|
| $k$ (apertura por metro de cable) | 2,65 | m | regla práctica "al metro" | `Port!D7` |
| $a$ (distancia entre pastecas) | 2,5 | m | Tipo de buques | `Port!D6` |
| factor de corrección de $D_s$ | 1,15 | — | — | `Port!D28` |
| $\alpha$ portón | 32 | ° | fila elegida de la polar | `Port!C134` |
| $C_L$, $C_D$ a 32° | 0,93; 0,71 | — | {cite:t}`sfia1993`, hoja «Flat Wooden» (vía el libro Excel) | `Port!D134:E134` |
| margen de superficie equivalente | 10 | % | {cite:t}`sfia1993`, sección 3-16 | — |
| patas de gallo / largo del portón | 1–1,5 | — | {cite:t}`sfia1993`, §2.2.3 | — |
| $S$ portón FAO | 1,805 | m² | catálogo | `Port!D122` |
| $p$ (ROB / FT) | 0,15–0,30 (0,20) | — | {cite:t}`fridman1986` | `Port!E146:H146`, `D210` |
| $\alpha_b$ entre bridas | 4,8 | ° | {cite:t}`martini` | `Port!F39` |
| cadena de reglaje | 0,095·$V_s$ | m | — | `Port!D46` |
| $L_s / L_p$ (Dremière) | 6 | — | {cite:t}`prado1990` | `Port!B68` |
| $\delta$ Martini | 20 | ° | {cite:t}`martini` | `Port!H65` |
| factor de patentes | 1,1 | — | {cite:t}`martini` | `Port!C83` |
| $d_p$ (brazo de la patente) | 3 | m | — | `Port!E277` |

## Equivalencia Excel ↔ `trawlkit`

| Celda(s) | Cálculo | Función |
|---|---|---|
| `Port!E13` | $D_s$ al metro | `rigging.door_spread_m` |
| `Port!D21`, `F30` | $\tfrac12\varphi$ y $D_s$ corregida | `rigging.warp_divergence_deg`, `rigging.door_spread_corrected_m` |
| `Port!C132:F137` | polar $C_L$, $C_D$ | `rigging.door_polar`, `rigging.door_polar_table` |
| `Port!E146:H168` | ROB como % de FT | `rigging.door_drag_share_kgf` |
| `Port!D190:E198` | ROB y $F_y$ | `rigging.door_forces_kgf` |
| `Port!E210:F229` | superficie requerida | `rigging.required_area_m2`, `rigging.required_area_summary` |
| `Port!D252:D260` | $P_\varphi$ | `rigging.door_force_kgf` (errata `door_force_mixed_angles`) |
| `Port!C266:C270` | centro de presión | `rigging.centre_of_pressure_m` |
| `Port!G281:H289` | momentos | `rigging.moment_balance` |
| `Port!E52`, `E60`, `D44:D46` | bridas | `rigging.bridle_lengths` |
| `Port!C71` | patentes Dremière | `rigging.sweeps_dremiere_m` |
| `Port!G71` | patentes Martini por δ | `rigging.sweeps_martini_m` (errata `sweep_degrees_of_sine`) |
| `Port!C83`, `C87` | patentes sin / con triángulo | `rigging.sweeps_length_m` |
| `Port!E97:G99` | pie de gallo | `rigging.crowfoot_m` |
| `Port!D110` | ángulo $\delta$ | `rigging.attack_angle_deg` |
| hoja completa | etapa `doors` y `bridles` | `model.run` → `result.doors`, `result.bridles` |
| — (Fase 19.3) | polares medidas y polar por tipo | `rigging.load_door_polars`, `rigging.polar_for_type` |
| — (Fase 19.3) | elección del portón del catálogo | `door_selection.select_doors`, `POST /doors/select` |

## Supuestos y límites

- **Coeficientes de catálogo.** La polar es la de un ensayo en régimen estacionario, lejos del
  fondo. El contacto con el fondo (zapata), la inclinación (*heel* y *tilt*) y la estela de los
  cables cambian $C_L$ y $C_D$ en la práctica; los valores son una primera aproximación.
- **Un portón o el par.** {eq}`eq-15-fuerzas` se evalúa con la superficie de **un** portón
  (1,805 m²); la hoja rotula ese valor como "ROB". En cambio, {eq}`eq-15-rob-share` y
  {eq}`eq-15-sreq` se refieren al **par**: $S_{req}$ es la superficie total y el libro la divide
  por dos. Para comparar con la banda de Fridman hay que sumar los dos portones,
  $R_{OB}^{par} = 2\cdot\tfrac12(\rho/g)C_D S v^2$. La superficie requerida por portón
  (≈ 1,82 m² promediando 150 y 180 HP) queda casi igual a la del portón elegido, pero ese promedio
  entre 2 y 4 kn está dominado por el extremo lento, donde $S_{req}$ es grande.
- **Regla al metro.** {eq}`eq-15-ds` es empírica: no depende de la velocidad ni de la fuerza de
  abertura. La DPA de Fridman ({doc}`16_aberturas`) sí resuelve el equilibrio de fuerzas.
- **Errata `door_force_mixed_angles`** (`Port!D252`). La celda escribe
  `SIN(RADIANS($E$240))` en el numerador de {eq}`eq-15-pphi` pero `SIN($E$240)` en el
  denominador: toma 32 como radianes. Como $\sin(32\,\text{rad}) = 0{,}551$ y
  $\sin 32° = 0{,}530$, el error es pequeño (≈ 1,8 % en $P_\varphi$), pero existe. `Compat.EXCEL`
  lo reproduce; `Compat.CORRECTED` usa radianes en ambos senos ({doc}`erratas`).
- **Errata `sweep_degrees_of_sine`** (`Port!G71`). La fórmula escrita es
  `((E13/2)-(E78/2)/DEGREES(SIN(H65)))`: toma el seno de 20 rad, lo pasa a "grados" y, por la
  precedencia, divide sólo $DPA/2$. Resultado: 16,1 m en lugar de 28,5 m. El valor no se usa aguas
  abajo (las patentes de diseño son 25 m, `Dim!F65`), por lo que sólo afecta a la lectura de la
  hoja.
- **Unidades del momento.** `Port!H281` está rotulada en kgf·cm pero vale $\tfrac12 R_N d_p$ en
  kgf·m; `trawlkit` conserva el valor y lo nombra `sweep_moment_kgf_m`. Comparar directamente
  `G281` y `H281` mezcla órdenes de magnitud.

## Ejemplo ejecutable

Corremos el caso del libro (red estándar + modificada, buque de 150 HP con el de 180 HP en la
clase) en modo `Compat.EXCEL` y verificamos contra los valores cacheados del Excel.

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

PORT = "portones_y_aparejamiento"
r = P.fao_result(150, "excel")
d, br = r.doors, r.bridles


def close(actual, key, sheet=PORT):
    """Compara con el valor del Excel (escalar o serie) a rtol = 1e-6."""
    exp = np.atleast_1d(golden(sheet, key))
    got = np.atleast_1d(actual)
    return all(math.isclose(a, b, rel_tol=1e-6) for a, b in zip(got, exp))


assert close(d.spread_m, "door_spread_m")  # separación al metro
assert close(d.polar.cl_cd, "door_cl_cd_selected")  # polar a 32°
assert close(d.forces.drag_kgf, "rob_kgf")  # ½·ρ/g·CD·S·v²
assert close(d.forces.lift_kgf, "door_spreading_force_kgf")  # ½·ρ/g·CL·S·v²
assert close(d.required_area_per_door_class_m2, "required_door_area_overall_m2")
assert close(br.attack_angle_deg, "bridle_attack_angle_deg")

print(f"Ds = {d.spread_m:.2f} m; ½φ = {d.half_divergence_deg:.2f}°; "
      f"Ds corregida = {d.spread_corrected_m:.2f} m")
print(f"S requerida por portón = {d.required_area_per_door_class_m2:.3f} m² "
      f"(portón FAO: {d.door.area_m2} m²)")
print(f"Bridas: Vs = {br.lengths.upper_m:g} m, "
      f"inferior = {br.lengths.lower_m:g} m, "
      f"cadena = {br.lengths.adjust_chain_m:.2f} m")
print(f"Pie de gallo = {br.crowfoot.length_m} m; patentes Dremière = "
      f"{br.sweeps_dremiere_m:.1f} m")
print(f"Patentes Martini sin/con triángulo = {br.sweeps_no_triangle_m:.1f} / "
      f"{br.sweeps_triangle_m:.1f} m; δ = {br.attack_angle_deg:.2f}°")
```

Las dos erratas del capítulo, en los dos modos. Ambas se verifican contra el Excel en modo
`EXCEL`:

```{code-cell} ipython3
v = r.case.speeds_ms
p_excel = rigging.door_force_kgf(0.71, 1.805, 32.0, v, compat=Compat.EXCEL)
p_corr = rigging.door_force_kgf(0.71, 1.805, 32.0, v, compat=Compat.CORRECTED)
assert close(p_excel, "door_force_kgf")

lp_excel = rigging.sweeps_martini_m(d.spread_m, 13.0, 20.0, compat=Compat.EXCEL)
lp_corr = rigging.sweeps_martini_m(d.spread_m, 13.0, 20.0, compat=Compat.CORRECTED)
assert close(lp_excel, "sweeps_martini_m")

print(f"Pφ a 3,5 kn: Excel {p_excel[5]:.1f} kgf, corregido {p_corr[5]:.1f} kgf "
      f"({100 * (p_corr[5] / p_excel[5] - 1):+.1f} %)")
print(f"Patentes Martini (δ = 20°): Excel {lp_excel:.2f} m, "
      f"corregido {lp_corr:.2f} m")
cop = d.centre_of_pressure
print(f"Centro de presión d = {cop.d_m:.3f} m; "
      f"hA = {cop.ha_m:.3f} m; hB = {cop.hb_m:.3f} m")
```

La polar de los dos portones del catálogo muestra por qué se trabaja cerca de 30°: más allá del
máximo de $C_L$, el coeficiente de arrastre sigue creciendo y la eficiencia cae
({numref}`fig-15-polar`).

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Polar de los portones del catálogo. Arriba, coeficiente de sustentación $C_L$; abajo,
      coeficiente de arrastre $C_D$, en función del ángulo de ataque. El anillo marca el punto de
      trabajo del libro (portón FAO a 32°). El Morgère no tiene datos a 25°.
    name: fig-15-polar
---
from trawlkit.io import load_doors

P.setup()
doors = load_doors().doors
names = {"fao_flat_wood_a3": "FAO plano de madera (A3)", "morgere_polivalente_oval": "Morgère polivalente oval"}
fig, axes = P.plt.subplots(2, 1, figsize=(7, 6.6), sharex=True)
for slot, door in enumerate(doors, start=1):
    pol = rigging.door_polar_table(door)
    ang = [p.angle_deg for p in pol]
    P.line(axes[0], ang, [p.cl for p in pol], slot, names[door.id])
    P.line(axes[1], ang, [p.cd for p in pol], slot, names[door.id])
sel = d.polar
for ax, val, dy in ((axes[0], sel.cl, 10), (axes[1], sel.cd, -16)):
    ax.plot([sel.angle_deg], [val], "o", ms=14, mfc="none", mec=P.INK_2, mew=1.2)
    ax.annotate(f"32°: {val:.2f}".replace(".", ","), (sel.angle_deg, val), xytext=(10, dy),
                textcoords="offset points", color=P.INK_2, fontsize=9)
axes[0].set_title("Sustentación $C_L$")
axes[1].set_title("Arrastre $C_D$")
axes[1].set_xlabel("Ángulo de ataque α [°]")
axes[0].set_ylim(0.6, 1.3)
axes[1].set_ylim(0.4, 1.0)
P.legend(axes[0], loc="lower center")
P.finish(fig)
```

Las fuerzas de los portones crecen con $v^2$, mientras que la resistencia que el buque "puede
pagar" ($p\,F_T$, entre 15 y 30 % de un tiro que cae con la velocidad) disminuye. Los portones
están bien dimensionados para la velocidad a la que la resistencia del par cruza la banda
({numref}`fig-15-fuerzas`).

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Resistencia y fuerza de abertura del par de portones FAO a 32° (dos veces la fuerza de un
      portón) frente a la banda de Fridman, 15–30 % del tiro disponible $F_T$ (hélice de paso
      fijo, 150 HP). La línea punteada es el 20 % que adopta el libro.
    name: fig-15-fuerzas
---
fig, ax = P.plt.subplots(figsize=(7, 4))
kn = r.case.speeds
lo, hi = d.rob_shares_kgf["15pct"], d.rob_shares_kgf["30pct"]
ax.fill_between(kn, lo, hi, color=P.NEUTRAL_WASH, lw=0, label="15–30 % de $F_T$")
ax.plot(kn, d.rob_share_kgf, color=P.NEUTRAL, lw=1.2, ls=(0, (3, 3)), label="20 % de $F_T$")
lift2 = 2 * np.asarray(d.forces.lift_kgf)
drag2 = 2 * np.asarray(d.forces.drag_kgf)
P.line(ax, kn, lift2, 1, "Fuerza de abertura del par $2F_y$")
P.line(ax, kn, drag2, 2, "Resistencia del par $2R_{OB}$")
P.end_label(ax, kn[-1], lift2[-1], f"{lift2[-1]:.0f} kgf", dx=0.08)
P.end_label(ax, kn[-1], drag2[-1], f"{drag2[-1]:.0f} kgf", dx=0.08)
cross = np.interp(0.0, drag2 - np.asarray(d.rob_share_kgf), kn)
ax.axvline(cross, color=P.AXIS, lw=1)
ax.annotate(f"cruce con el 20 %: {cross:.2f} kn".replace(".", ","), (cross, 900), xytext=(6, 0),
            textcoords="offset points", color=P.INK_2, fontsize=9, va="center")
P.speed_axis(ax)
ax.set_xlim(0.9, 5.6)
ax.set_ylabel("Fuerza del par de portones [kgf]")
ax.set_ylim(0, 1250)
P.legend(ax)
P.finish(fig)
```

| v [kn] | 1,0 | 2,0 | 3,0 | 3,5 | 4,0 | 5,0 |
|---|---|---|---|---|---|---|
| $R_{OB}$ de un portón [kgf] | 17,7 | 70,8 | 159,3 | 216,8 | 283,2 | 442,5 |
| $F_y$ de un portón [kgf] | 23,2 | 92,7 | 208,6 | 284,0 | 370,9 | 579,6 |
| $2R_{OB}$ del par [kgf] | 35,4 | 141,6 | 318,6 | 433,6 | 566,4 | 884,9 |
| 20 % de $F_T$ [kgf] | 279,0 | 258,0 | 237,0 | 226,5 | 216,0 | 195,0 |

El par de portones de 1,8 m² consume exactamente el 20 % del tiro a unos 2,6 kn, una velocidad
típica de arrastre de fondo; a 3,5 kn ya consume el 38 %. Por eso el promedio de
$S_{req}$ entre 2 y 4 kn (≈ 1,66 m² por portón para 150 HP) es algo menor que el portón elegido.
Nótese que la resistencia total del capítulo {doc}`19_ventana_velocidad` (modo corregido) suma el
"ROB" de la hoja, es decir, la resistencia de **un** portón.

La biblioteca de polares compara los tipos de portón ({numref}`fig-15-tipos`): el plano tiene el
$C_L$ máximo más bajo; los cambados con ranura llegan a 1,4–1,5; los multiperfil siguen ganando
$C_L$ hasta 40–45°; el pelágico de alta relación de aspecto da mucho $C_L$ con poco $C_D$ a
ángulos bajos.

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Polar representativa de cada tipo de portón (`rigging.polar_for_type`). Arriba $C_L$, abajo
      $C_D$. Plano y oval: hojas de Seafish/IFREMER/DIFTA (1993); en V, cambado y multiperfil:
      media de varias hojas; pelágico: ajuste a los puntos del Thyborøn 15 VF en tanque de flujo
      (Mellibovsky et al. 2018), que el túnel de viento da 20–30 % más altos.
    name: fig-15-tipos
---
from trawlkit.rigging.polars import DOOR_TYPE_LABEL, DOOR_TYPES
from trawlkit.i18n import t as _t

fig, axes = P.plt.subplots(2, 1, figsize=(7, 6.6), sharex=True)
for slot, kind in enumerate(DOOR_TYPES, start=1):
    tp = rigging.polar_for_type(kind)
    ang = [c.angle_deg for c in tp.coefficients]
    P.line(axes[0], ang, [c.cl for c in tp.coefficients], slot, _t(DOOR_TYPE_LABEL[kind]))
    P.line(axes[1], ang, [c.cd for c in tp.coefficients], slot, _t(DOOR_TYPE_LABEL[kind]))
axes[0].set_title("Sustentación $C_L$")
axes[1].set_title("Arrastre $C_D$")
axes[1].set_xlabel("Ángulo de ataque α [°]")
P.legend(axes[1], loc="upper left", fontsize=8)
P.finish(fig)
```

La elección del portón para el caso del libro (modo corregido): la superficie requerida por portón
con el portón FAO a 32° se lleva a cada portón del catálogo con {eq}`eq-15-equivalente`. El portón
de la A-3 aparece entre los candidatos, y es el plano más justo.

```{code-cell} ipython3
from trawlkit.door_selection import select_doors

sel = select_doors(P.fao_result(150, "corrected"))
assert any(c.id == "fao_flat_wood_a3" for c in sel.candidates)
print(f"Superficie requerida por portón: {sel.required_m2:.2f} m²")
for c in sel.candidates[:6]:
    peso = "sin peso" if c.weight_air_kg is None else f"{c.weight_air_kg:.0f} kg"
    extra = " (+10 %)" if c.margin_applied else ""
    print(f"{c.name[:44]:44s} {c.area_m2:5.2f} m² ≥ {c.required_m2:4.2f}{extra:8s} "
          f"margen {100 * c.area_margin:4.1f} %  {peso}")
```

## Ejercicios

Del banco del modo docente, con los datos del libro. En la app, el modo «Aula UTN» los genera con
otros datos y los corrige ({doc}`38_docentes`).

```{code-cell} ipython3
:tags: [remove-input]
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path.cwd()))
import _exercises
_exercises.section("15_portones_aparejo")
```
