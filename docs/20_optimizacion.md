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

# Optimización del tamaño de la red y de la velocidad

## Propósito

Los capítulos anteriores responden a la pregunta *¿puede este buque remolcar esta red?*
({doc}`19_ventana_velocidad`). Este capítulo da vuelta la pregunta: **¿qué tamaño de red y qué
velocidad de arrastre le convienen a este buque?** La red FAO A-3 se diseñó para pesqueros de
150–180 HP, pero {doc}`30_caso_beagle` muestra que con 150 HP y hélice de paso fijo la ventana
viable es de apenas una décima de nudo. `trawlkit.optimize` explora la familia de redes
*geométricamente semejantes* a la original (mismo mallero, hilo, cortes y materiales, con $s$ veces
más mallas por borde) y busca el par $(s, v)$ que maximiza el rendimiento de pesca sin violar las
restricciones de tiro, apertura, cable y portón.

Cada evaluación es una corrida completa del motor ({doc}`motor`): no hay un modelo sustituto, y
por eso los resultados heredan los supuestos de todas las etapas, en particular la resistencia
empírica de {doc}`14_resistencia` y las aberturas de {doc}`16_aberturas`.

## Formulación

### Variables

* **Escala de la red** $s \in [s_{\min}, s_{\max}]$ (por defecto 0,6–1,4). `scale_net(spec, s)`
  multiplica por $s$ los números de mallas de cada borde y de alto de cada panel (también los
  extras T1/T2 del Excel) y redondea al entero más cercano, como mínimo 1. Como el redondeo depende
  sólo del número de origen, los bordes que se unen (iguales en la red original) siguen iguales.
  Relingas y circunferencias escalan ≈ $s$, superficies de paño ≈ $s^2$; el número de boyas escala
  con la lima. $s = 1$ es la red del libro.
* **Velocidad de arrastre** $v \in [v_{\min}, v_{\max}]$ (por defecto 1,5–4 kn).

### Aberturas a la velocidad $v$

La abertura horizontal es la DPA de Fridman ({cite:t}`fridman1986`, `Mec!P164`), la única del motor
que depende de $v$: la DPA geométrica y la AH promedio de `Dim!F61` son constantes y no ven que una
red lenta no termina de abrirse. Como el equilibrio de fuerzas de Fridman no satura, con una red
chica y el mismo portón la DPA calculada supera lo que permite la geometría del aparejo; se toma la
menor de las dos:

$$
A_H(s, v) = \min\left\{ \mathrm{DPA}_F(s, v),\ \frac{L_B\,D_s}{L_{PG} + L_P + L_{Vs} + L_B} \right\}
$$ (eq-20-ah)

con $L_B$ el burlón, $D_s$ la separación de portones y $L_{PG}$, $L_P$, $L_{Vs}$ pies de gallo,
patentes y bridas (`Mec!L211` sin el redondeo a metro entero). Del mismo modo, la AV de
Baranov–Fridman (`Mec!O272`) crece sin límite cuando $R_N \to 0$ (red lenta); se acota con la AV
máxima de {cite:t}`prado1990`, 6,5 % de la circunferencia de la boca:

$$
A_V(s, v) = \min\left\{ AV_F(s, v),\ 0{,}065\,C(s) \right\}
$$ (eq-20-av)

### Objetivos

$$
\dot A = 3600\,A_H\,v, \qquad \dot V = 3600\,A_H\,A_V\,v, \qquad
E = \frac{R_T}{A_H}
$$ (eq-20-obj)

$\dot A$ es el **área barrida por hora** [m²/h] (especies demersales asociadas al fondo, como la
langostilla), $\dot V$ el **volumen filtrado por hora** [m³/h] (especies que se despegan del fondo)
y $E$ el **trabajo de remolque por m² barrido** [kgf·m/m²], un indicador de consumo: el buque gasta
$R_T \cdot d$ para barrer $A_H \cdot d$. $\dot A$ y $\dot V$ se maximizan, $E$ se minimiza.

### Restricciones

$$
\begin{aligned}
g_1 &: F_T(v) \ge (1 + m)\,R_T(s, v) && \text{reserva de tiro (}m = 0{,}1\text{)} \\
g_2 &: \mathrm{DPA}_F(s, v) \ge 0{,}85\,\mathrm{DPA}_{geo}(s) && \text{red abierta} \\
g_3 &: \max_{c\,:\,\varnothing_c \ge \varnothing_{\min}} Q_c \ge 4\,R_T(s, v) && \text{algún cable del catálogo resiste} \\
g_4 &: S_{req} \le S_{port} && \text{portón suficiente (Port!F215)} \\
g_5 &: v_{\min} \le v \le v_{\max} && \text{rango operativo}
\end{aligned}
$$ (eq-20-g)

$F_T$ es el tiro de Fridman del propulsor ({eq}`eq-19-ft`) y $R_T$ la resistencia total con los dos
portones ({eq}`eq-19-rt`, modo corregido). $g_2$ es el criterio de velocidad mínima de
{doc}`30_caso_beagle` con la DPA geométrica del libro (`Mec!L211`). En $g_3$, $\varnothing_{\min}$
es el diámetro de Águila para la potencia de la clase y $Q_c$ la carga de rotura del cable $c$. En
$g_4$, $S_{req}$ es la superficie por portón que pide la regla del libro (ROB = 20 % de $F_T$,
promedio 2–4 kn, `Port!F215`): depende del buque y de la hélice, no de $(s, v)$, y funciona como
una verificación previa del aparejo.

## Método

1. **Malla.** Para cada escala $s_i$ se corre el motor **una vez** sobre una malla fina de
   velocidades (0,05 kn, de 1 a 5 kn más los nodos del libro) y cada $v_j$ se evalúa por
   interpolación lineal. Las magnitudes que el libro promedia en velocidad (superficie requerida
   del portón) se toman en los nodos del libro, así que a $s = 1$ y $v = 2$ kn la evaluación
   reproduce exactamente `run(case)`.
2. **Frente de Pareto.** `pareto_front` filtra exactamente los puntos factibles no dominados en
   $(\dot A, E)$: ningún otro punto barre más con menos trabajo por m².
3. **Evolución diferencial.** `optimise` refina con `scipy.optimize.differential_evolution`
   (Storn y Price, 1997) sobre $(s, v)$, minimizando

   $$
   f(s, v) = -\sigma\,\frac{J(s, v)}{|J_0|} + W \sum_k \max\{0, \tilde g_k(s, v)\}
   $$ (eq-20-pen)

   con $J$ el objetivo, $\sigma = \pm 1$ su sentido, $J_0$ el mejor valor de la malla,
   $\tilde g_k$ la violación relativa de cada restricción y $W = 100$. La población se siembra con
   el mejor punto de la malla (`x0`) y con una semilla fija (`seed`), de modo que el resultado es
   reproducible. La escala se redondea a 0,005 para reutilizar corridas del motor (una red con los
   mismos números de mallas no se recalcula). El resultado final es el mejor punto factible entre
   la malla y el refinado.

## Coeficientes

| Símbolo | Valor | Unidad | Fuente | Parámetro |
|---|---|---|---|---|
| $m$ | 0,1 | — | criterio de proyecto | `Limits.margin`, `--margin` |
| fracción de apertura | 0,85 | — | {doc}`30_caso_beagle` | `Limits.open_ratio` |
| factor de seguridad del cable | 4 | — | `Rem!D271` | `DesignCase.warp_safety_factor` |
| AV máxima | 6,5 % de $C$ | — | {cite:t}`prado1990`, `Mec!F246` | — |
| $W$ | 100 | — | — | `search.PENALTY_WEIGHT` |
| paso de $s$ en el refinado | 0,005 | — | — | `search.S_STEP` |
| malla de velocidades del motor | 0,05 | kn | — | `evaluate.GRID_STEP_KN` |

## Equivalencia Excel ↔ `trawlkit`

| Celda(s) | Magnitud | Uso en `trawlkit.optimize` |
|---|---|---|
| `Paños!H55:W230` | mallas de cada panel (T1, T2, N) | `scale_net` |
| `Mec!P164:P172` | DPA de Fridman por velocidad | $A_H$, restricción $g_2$ |
| `Mec!L211` | DPA geométrica | tope de $A_H$, umbral de $g_2$ |
| `Mec!O272:O280`, `F246` | AV de Fridman, AV máx. de Prado | $A_V$ |
| `PotOK!L11:O19` | $F_T$ PF y PV+T | $g_1$ |
| `Rem!H118` (+ ROB) | $R_T$ | $g_1$, $g_3$, $E$ |
| `Rem!E110`, `Cab!D11` | Ø mínimo, catálogo de cables | $g_3$ |
| `Port!F215` | superficie requerida por portón | $g_4$ |

## Resultados del caso FAO A-3

Se optimizan las cuatro combinaciones del libro: 150 y 180 HP, hélice de paso fijo (PF) y de paso
variable con tobera (PV+T). La regla del libro pide portones más grandes que el FAO de 1,805 m²
para 180 HP con PF (≈ 2,0 m²) y para PV+T (≈ 2,7 y 3,2 m²): en esos casos se usa un portón
semejante al del libro (misma polar) con la superficie requerida redondeada hacia arriba a
0,05 m² (`scale_door`). Sin ese cambio $g_4$ no se cumple en ningún punto.

```{code-cell} ipython3
---
mystnb:
  markdown_format: myst
---
import dataclasses
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.cwd().parent))
sys.path.insert(0, str(pathlib.Path.cwd()))

import numpy as np
from IPython.display import Markdown

import _plots_t2 as P
from trawlkit import DesignCase
from trawlkit.io import load_doors, load_net, load_vessels
from trawlkit.optimize import Evaluator, evaluate, optimise, pareto_front, scale_door

VESSELS = {v.id: v for v in load_vessels().vessels}
DOOR = load_doors().doors[0]
PROPS = {"fixed_pitch": "PF", "variable_pitch_nozzle": "PV+T"}
CONFIGS = [(hp, prop) for hp in (150, 180) for prop in PROPS]


def case_for(hp, prop):
    """Caso FAO A-3 (red estándar) con el portón del libro o uno semejante dimensionado (F215)."""
    vid = f"fao_a3_{hp}hp"
    case = DesignCase(
        net=load_net("fao_a3_standard"),
        vessel=VESSELS[vid],
        class_vessels=tuple(v for k, v in VESSELS.items() if k != vid),
        door=DOOR,
        ft_propeller=prop,
    )
    req = evaluate(case, 1.0, 2.0).door_required_m2
    if req > DOOR.area_m2:
        case = dataclasses.replace(case, door=scale_door(DOOR, math.ceil(req * 20) / 20))
    return case


CASES = {c: case_for(*c) for c in CONFIGS}

# Red del libro, 150 HP, paso fijo, portón FAO: factible a 2,1 kn y no a 3,5 kn (ni a 1,5 kn).
base = CASES[(150, "fixed_pitch")]
assert base.door.area_m2 == DOOR.area_m2
assert evaluate(base, 1.0, 2.1).feasible
assert not evaluate(base, 1.0, 3.5).constraint("thrust").ok
assert not evaluate(base, 1.0, 1.5).constraint("net_open").ok

OBJ = {"area": "área/h", "volume": "volumen/h", "energy": "R_T/AH"}
RES = {(c, o): optimise(CASES[c], objective=o, seed=0) for c in CONFIGS for o in OBJ}

lines = [
    "| Buque | Hélice | Portón [m²] | Objetivo | $s$ | $v$ [kn] | Lima [m] | $A_H$ [m] "
    "| $A_V$ [m] | Área [m²/h] | Volumen [m³/h] | $R_T/A_H$ | $R_T$ [kgf] | Margen |",
    "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
]
for (hp, prop), case in CASES.items():
    for o, name in OBJ.items():
        b = RES[((hp, prop), o)].best
        assert b.feasible
        lines.append(
            f"| {hp} HP | {PROPS[prop]} | {case.door.area_m2:.2f} | {name} | {b.s:.3f} | "
            f"{b.v_kn:.2f} | {b.headrope_m:.1f} | {b.ah_m:.1f} | {b.av_m:.2f} | "
            f"{b.area_rate_m2_h:,.0f} | {b.volume_rate_m3_h:,.0f} | {b.energy_kgf_m_per_m2:.1f} | "
            f"{b.demand_kgf:.0f} | {b.thrust_margin:.0%} |".replace(",", " ").replace(".", ",")
        )
Markdown("\n".join(lines))
```

La tabla resume el mejor diseño por objetivo (mejor punto factible tras la evolución diferencial).
Antes de leerla conviene ver la región factible completa: la {numref}`fig-20-mapa` barre
$s \times v$ con 41 × 51 puntos (una corrida del motor por fila) y la usa además para verificar que
el optimizador no se quedó en un óptimo local.

```{code-cell} ipython3
S = np.round(np.arange(0.6, 1.4001, 0.02), 3)
V = np.round(np.arange(1.5, 4.0001, 0.05), 3)
MAPS = {}
for c, case in CASES.items():
    ev = Evaluator(case)
    rows = [[ev.from_curves(ev.curves(s), v) for v in V] for s in S]
    MAPS[c] = rows
    dense = [e for row in rows for e in row if e.feasible]
    for o, attr in (("area", "area_rate_m2_h"), ("volume", "volume_rate_m3_h")):
        best_dense = max(getattr(e, attr) for e in dense)
        # El refinado iguala o mejora la malla densa (tolerancia 1 %).
        assert getattr(RES[(c, o)].best, attr) >= 0.99 * best_dense, (c, o)
    s_max = max(e.s for e in dense)
    at_book = [e.v_kn for e in rows[list(S).index(1.0)] if e.feasible]
    window = f"{at_book[0]:.2f}–{at_book[-1]:.2f} kn" if at_book else "ninguna"
    print(f"{c[0]} HP {PROPS[c[1]]:<5} escala máxima factible {s_max:.2f}; "
          f"velocidades factibles de la red del libro: {window}")
```

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Región factible (verde) en el plano velocidad–escala para la red FAO A-3 escalada, con
      isolíneas de área barrida por hora (miles de m²/h). La línea de trazos es la red del libro
      ($s = 1$). Los marcadores son los óptimos de área (círculo) y de volumen (cuadrado). Arriba
      150 HP, abajo 180 HP; a la izquierda paso fijo (PF) y a la derecha paso variable con tobera
      (PV+T), cada uno con su portón.
    name: fig-20-mapa
---
P.setup()
fig, axes = P.plt.subplots(2, 2, figsize=(8.6, 7.2), sharex=True, sharey=True)
for ax, c in zip(axes.flat, CONFIGS):
    rows = MAPS[c]
    feas = np.array([[e.feasible for e in row] for row in rows], dtype=float)
    area = np.array([[e.area_rate_m2_h for e in row] for row in rows]) / 1000
    ax.contourf(V, S, feas, levels=[0.5, 1.5], colors=[P.GOOD], alpha=0.22)
    ax.contour(V, S, feas, levels=[0.5], colors=[P.GOOD], linewidths=1.2)
    cs = ax.contour(V, S, area, levels=np.arange(20, 121, 10), colors=P.MUTED, linewidths=0.7)
    ax.clabel(cs, fmt="%d", fontsize=7.5, inline=True)
    ax.axhline(1.0, color=P.INK_2, lw=1.0, ls="--")
    for o, mk, slot in (("area", "o", 1), ("volume", "s", 2)):
        b = RES[(c, o)].best
        ax.plot([b.v_kn], [b.s], mk, color=P.color(slot), ms=9, mec=P.SURFACE, mew=1.5,
                label=f"óptimo de {OBJ[o]}")
    door = CASES[c].door.area_m2
    ax.set_title(f"{c[0]} HP, {PROPS[c[1]]} (portón {door:.2f} m²)".replace(".", ","))
    ax.grid(False)
for ax in axes[1]:
    ax.set_xlabel("Velocidad de arrastre v [kn]")
for ax in axes[:, 0]:
    ax.set_ylabel("Escala de la red s")
axes[0, 0].annotate("red del libro", (3.95, 1.01), ha="right", va="bottom", fontsize=8.5,
                    color=P.INK_2)
P.legend(axes[0, 0], loc="upper right")
P.finish(fig)
```

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Frente de Pareto entre área barrida por hora (a maximizar) y trabajo de remolque por m²
      barrido $R_T/A_H$ (a minimizar), sobre la malla densa de la figura anterior. Cada punto del
      frente es un par $(s, v)$ que no puede mejorarse en un objetivo sin empeorar el otro. Los
      anillos marcan la red del libro ($s = 1$) en su ventana factible, cuando la tiene.
    name: fig-20-pareto
---
fig, ax = P.plt.subplots(figsize=(7.2, 4.6))
for slot, c in enumerate(CONFIGS, start=1):
    flat = [e for row in MAPS[c] for e in row]
    front = sorted(pareto_front(flat), key=lambda e: e.area_rate_m2_h)
    x = [e.area_rate_m2_h / 1000 for e in front]
    y = [e.energy_kgf_m_per_m2 for e in front]
    P.line(ax, x, y, slot, f"{c[0]} HP, {PROPS[c[1]]}", marker=False)
    book = [e for e in flat if e.feasible and math.isclose(e.s, 1.0)]
    if book:
        ax.plot([e.area_rate_m2_h / 1000 for e in book], [e.energy_kgf_m_per_m2 for e in book],
                "o", ms=8, mfc="none", mec=P.color(slot), mew=1.4)
ax.set_xlabel("Área barrida por hora [miles de m²/h]")
ax.set_ylabel("$R_T/A_H$ [kgf·m/m²]")
P.legend(ax, loc="upper left")
P.finish(fig)
```

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  markdown_format: myst
---
# Primeros puntos del frente (150 HP, PF) según el optimizador con malla 17 × 11.
r = RES[((150, "fixed_pitch"), "area")]
lines = ["| $s$ | $v$ [kn] | $A_H$ [m] | Área [m²/h] | $R_T/A_H$ | $R_T$ [kgf] | Margen |",
         "|---|---|---|---|---|---|---|"]
for e in r.pareto[:6]:
    lines.append(f"| {e.s:.3f} | {e.v_kn:.2f} | {e.ah_m:.1f} | {e.area_rate_m2_h:,.0f} | "
                 f"{e.energy_kgf_m_per_m2:.1f} | {e.demand_kgf:.0f} | {e.thrust_margin:.0%} |"
                 .replace(",", " ").replace(".", ","))
print(f"{r.engine_runs} corridas del motor en {r.runtime_s:.1f} s")
Markdown("\n".join(lines))
```

## Discusión

**La red del libro es grande para 150 HP con paso fijo.** Con la reserva de tiro del 10 %, la red
original sólo es factible en una franja de ≈ 0,1 kn alrededor de 2,1 kn: por debajo no abre
(restricción $g_2$), por encima el buque no la remolca con reserva ($g_1$). Es la misma conclusión
de {doc}`30_caso_beagle`, ahora como un punto en el borde de la región factible
({numref}`fig-20-mapa`). Ninguna red con $s > 1{,}02$ tiene una velocidad factible.

**Para barrer más área conviene una red más chica y más rápida.** El área barrida por hora es
$A_H\,v$ y $A_H$ depende sobre todo del aparejo (separación de portones, patentes y bridas), no del
tamaño de la red: al achicarla, la DPA geométrica cae mucho menos que $s$ (de ≈ 13,8 m a ≈ 11,4 m
entre $s = 1$ y $s = 0{,}6$), mientras que la resistencia cae ≈ $s^2$ y libera tiro para ir más
rápido. Por eso el óptimo de área queda en el borde inferior de la escala ($s ≈ 0{,}6$–0,66) y a la
máxima velocidad que permite el tiro: ≈ 3,2 kn con 150 HP y PF, ≈ 3,8 kn con PV+T. Con 180 HP el
óptimo apenas se corre. Este resultado es tan bueno como el modelo de $A_H$: supone que la captura
es proporcional al área entre puntas de ala, que es razonable para especies que el aparejo arrea
(langostilla, peces planos) y optimista para especies que escapan a velocidad baja de la red.

**Para filtrar más volumen conviene una red intermedia.** La AV de Fridman cae con la velocidad
(la lima se aplasta al crecer $R_N$), así que el volumen $A_H A_V v$ tiene un máximo interior. El
óptimo queda en $s ≈ 0{,}83$–0,89 y 2,3–2,6 kn, con reserva de tiro de sobra (30–90 %): no lo fija
la potencia sino el modelo de abertura vertical, en el punto donde la AV de Fridman baja del tope
de {eq}`eq-20-av`. Por eso es el mismo con 150 y 180 HP y paso fijo, y cambia con PV+T sólo porque
el portón más grande abre más la red. Es el resultado más sensible a los supuestos del capítulo.

**El trabajo por m² barrido siempre favorece lo más chico y lo más lento.** $R_T/A_H$ crece con $v$
y con $s$, así que minimizarlo solo lleva a la esquina $(s_{\min}, v_{\min})$. Por eso se
presenta como frente de Pareto ({numref}`fig-20-pareto`): para cada área barrida por hora, el
frente da el menor trabajo por m², y el diseñador elige el punto según el costo del combustible y
del tiempo de mar. A lo largo del frente, pasar de ≈ 30 000 a ≈ 65 000 m²/h con 150 HP y PF triplica
el trabajo por m².

**La hélice pesa más que la potencia.** Pasar de PF a PV+T con el mismo motor agranda la región
factible mucho más que pasar de 150 a 180 HP: con PV+T la red del libro es factible desde 1,5 kn
hasta ≈ 2,7 kn (150 HP) o ≈ 2,9 kn (180 HP), y la escala máxima factible sube a ≈ 1,3 (150 HP) y
a más de 1,4 (180 HP), contra ≈ 1,02 y ≈ 1,06 con paso fijo. PV+T exige, según la regla del libro,
portones de 2,7–3,25 m², bastante más grandes que el FAO de 1,805 m².

**La red del libro está dominada.** En los cuatro casos los puntos de $s = 1$ quedan por encima del
frente de Pareto ({numref}`fig-20-pareto`): para la misma área barrida por hora hay una red más
chica, remolcada más rápido, que la consigue con menos trabajo por m². Con paso fijo la diferencia
es de ≈ 50 % (la red original sólo puede ir a 2–2,3 kn); con PV+T, de ≈ 10–25 %.

## Supuestos y límites

- **Resistencia empírica.** $R_N$ es la fórmula demersal de Aberdeen ({doc}`14_resistencia`),
  ajustada para redes de este tamaño; extrapolar a $s = 0{,}6$ o $1{,}4$ es razonable para la
  resistencia (que escala con la superficie de paño), pero la incertidumbre de ±10 % de $R_N$ mueve
  la velocidad máxima ≈ ±0,15 kn ({doc}`19_ventana_velocidad`) y desplaza los óptimos en la misma
  medida. {doc}`32_validacion_dynamit` sugiere que la resistencia de diseño es conservadora.
- **Modelo de abertura.** $A_H$ y $A_V$ salen de los equilibrios de Fridman y de topes geométricos
  simples; no hay un modelo de forma de la red que acople ambas aberturas ni la deformación de los
  paños con la velocidad.
- **Escalado geométrico.** La familia $s$ conserva mallero, hilo y armado. No optimiza la forma
  (cortes, relación lima/burlón, largo del cuerpo), el mallero ni el aparejo (largo de patentes,
  cable filado), que mueven $A_H$ tanto como $s$.
- **Sin captura ni fondo.** La resistencia no incluye la captura en la bolsa ni el contacto del
  burlón y los portones con el fondo; el rendimiento de pesca se mide por área o volumen, sin
  selectividad ni comportamiento de la especie. La reserva de tiro $m$ es la que cubre, en parte,
  estos efectos.
- **Portón como verificación.** La regla `Port!F215` no depende de $(s, v)$; un portón distinto
  cambia $R_T$ (su resistencia) y la DPA de Fridman, pero no se optimiza su superficie.
- **Óptimos en los bordes.** Los óptimos de área y de energía caen en $s_{\min}$: el resultado
  dice "lo más chico que se permita" y depende del rango elegido, que debe reflejar el mínimo
  práctico de la red (manejo en cubierta, especie objetivo).
