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

# Zoom por malla y selectividad

```{code-cell} ipython3
:tags: [remove-cell]
import dataclasses
import math
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path.cwd().parent))
sys.path.insert(0, str(pathlib.Path.cwd()))

import numpy as np
import _plots_t2 as P
import _plots_v as PV
from myst_nb import glue
from trawlkit.model import run
from trawlkit.selectivity import (
    ESCAPE_ATTEMPTS,
    ESCAPE_ZONE_M,
    codend_variant,
    escape_zone,
    selectivity,
    species_catalogue,
)
from trawlkit.sim import Scenario, explore, simulate
from trawlkit.sim.core import DEFAULT_MESH_BENDING_PA
from trawlkit.sim.mesh import DIAMOND_REST_ANGLE_DEG
from trawlkit.sim.validation import standard_case

P.setup()
T0 = time.perf_counter()
RES = 3
CASE = standard_case()
SC = Scenario(seabed="mixed", catch_kg=300, mesh_bending=True)


def num(x: float, nd: int = 1) -> str:
    return f"{x:.{nd}f}".replace(".", ",")


def sim(orientation: str, mesh_mm: float, scenario: Scenario = SC):
    net = codend_variant(CASE.net, orientation, mesh_mm=mesh_mm)
    r = run(dataclasses.replace(CASE, net=net))
    return simulate(r, 3.0, resolution=RES, coarse_resolution=None, scenario=scenario)
```

## Propósito

{doc}`21_simulacion` a {doc}`23_mar_real` resuelven la forma de la red completa. Este capítulo baja
a **cada malla**: cómo queda abierta en el equilibrio, con la captura, la velocidad y el fondo de
cada lance. Con esa forma se calcula qué tallas de pez escapan por el copo (la **selectividad** por
tamaño) y se comparan copos de malla en **rombo**, **T90** y **cuadrada**.

Las herramientas de selectividad publicadas toman la apertura de la malla como dato (FISHSELECT,
{cite:t}`herrmann2009`) o simulan sólo el copo (PRESEMO, {cite:t}`herrmann2005`;
{cite:t}`herrmann2007`). Aquí la apertura sale de la simulación de la red completa, con los
portones, el fondo y la captura: el mismo modelo que mueve el explorador animado.

## La malla dentro del elemento

En el elemento triangular de Priour ({doc}`21_simulacion`) la posición es lineal en las
coordenadas de hilo $(i, j)$. Los vectores de pata de cada familia de hilos,

$$
\mathbf e_i = \frac{\partial \mathbf x}{\partial i}, \qquad
\mathbf e_j = \frac{\partial \mathbf x}{\partial j},
$$ (eq-24-legs)

son constantes en el triángulo, así que todas sus mallas tienen la misma forma: un paralelogramo
de lados $\mathbf e_i$ y $\mathbf e_j$. Su ángulo de apertura y las alturas entre lados opuestos son

$$
\beta = \arccos \frac{\mathbf e_i \cdot \mathbf e_j}{|\mathbf e_i| |\mathbf e_j|}, \qquad
h_i = |\mathbf e_j| \sin\beta, \qquad h_j = |\mathbf e_i| \sin\beta .
$$ (eq-24-opening)

La **luz** de la malla, por donde pasa un pez, descuenta el diámetro $d$ del hilo:
$h' = h - d$. La reconstrucción de las mallas de un triángulo es exacta, sin interpolar: es lo que
dibuja el zoom por malla de la aplicación ({doc}`web`).

## Rombo, T90 y malla cuadrada

En la malla **rómbica** la diagonal larga va a lo largo de la red; la tensión longitudinal la
cierra. En **T90** el mismo paño va girado 90°: la diagonal larga queda a lo ancho. En la malla
**cuadrada** los hilos van a lo largo y a lo ancho, y la tensión no cierra la malla.

Para un hilo ideal (sin rigidez a la flexión), el rombo y el T90 serían la misma malla. Lo que los
distingue es la **resistencia de la malla a abrirse o cerrarse**: el nudo y el hilo trenzado
tienen una forma de reposo y resisten apartarse de ella {cite:p}`sala2007`. El simulador la
modela como una bisagra en cada nudo:

$$
E = \tfrac12 K (\beta - \beta_0)^2, \qquad K = 4\,A_{ij}\,\frac{EI}{a}, \qquad
EI = E_b \frac{\pi d^4}{64},
$$ (eq-24-bending)

con $A_{ij}$ mallas por triángulo, $a$ el largo de pata y $\beta_0$ el ángulo de reposo: el del
rombo, su suplemento en T90 (el nudo girado tiende a abrir la malla a lo ancho) y 90° en malla
cuadrada.

```{code-cell} ipython3
:tags: [remove-cell]
glue("beta0", f"{DIAMOND_REST_ANGLE_DEG:.0f}", display=False)
glue("beta0_t90", f"{180 - DIAMOND_REST_ANGLE_DEG:.0f}", display=False)
glue("eb", num(DEFAULT_MESH_BENDING_PA / 1e8, 1), display=False)
glue("ei4", num(DEFAULT_MESH_BENDING_PA * math.pi * 0.004**4 / 64 * 1e3, 1), display=False)
```

Valores usados («A VERIFICAR»): $\beta_0$ = {glue:text}`beta0`° en rombo y
{glue:text}`beta0_t90`° en T90, y $E_b$ = {glue:text}`eb`·10⁸ Pa. Este último da
$EI$ ≈ {glue:text}`ei4`·10⁻³ N·m² para un hilo de 4 mm, del orden de lo que midieron
{cite:t}`sala2007`. La rigidez se activa sola cuando la red tiene paños T90 o de malla cuadrada.
Al comparar copos se activa en todos, también en el de rombo, para que la comparación sea pareja.
Con hilo fino y mucha tensión la bisagra pesa poco; donde la tensión es baja, delante de la
captura, mantiene la malla T90 abierta.

En el motor empírico, la orientación cambia la superficie de trabajo del paño cuadrado (cada
malla es un cuadrado de una pata de lado) y el plano a escala real.

## Modelo de paso y curva de retención

Un pez de talla $L$ escapa por una malla si la elipse de su **sección transversal más
resistente** entra en la luz, girada a su favor {cite:p}`herrmann2009`. La elipse tiene semiejes
$A = c\,h\,L/2$ (alto) y $B = c\,w\,L/2$ (ancho), con $h$ y $w$ la forma de la especie y $c$ la
compresión de los tejidos. Entra si existe un giro $\theta$ con

$$
\sqrt{A^2 (\mathbf n_k\cdot\mathbf u)^2 + B^2 (\mathbf n_k\cdot\mathbf v)^2} \le \frac{h_k'}{2},
\qquad k = i, j ,
$$ (eq-24-pass)

donde $\mathbf n_k$ es la normal a cada par de lados y $\mathbf u$, $\mathbf v$ los ejes de la
elipse. Como $A$ y $B$ crecen con $L$, cada malla tiene una talla máxima de paso $L_m$.

Las mallas candidatas son las del copo en una franja delante de la captura. Allí se acumulan los
peces y buscan salir {cite:p}`herrmann2005`. La parte tapada por la captura no cuenta. Con la
variabilidad morfológica $cv$, la probabilidad de pasar por una malla al azar de la franja es

$$
p(L) = \frac{\sum_m w_m\, \Phi\!\left(\frac{L_m/L - 1}{cv}\right)}{\sum_m w_m} .
$$ (eq-24-pmesh)

Cada pez prueba $k$ mallas y escapa si pasa por alguna; una fracción $C$ llega a probar. La
retención es

$$
r(L) = 1 - C\left[1 - \bigl(1 - p(L)\bigr)^k\right] .
$$ (eq-24-retention)

De la curva salen $L_{50}$ (talla retenida al 50 %), el rango de selección
$SR = L_{75} - L_{25}$ y el factor de selección $SF = L_{50}/\text{mallero}$.

```{code-cell} ipython3
:tags: [remove-cell]
glue("zone", num(ESCAPE_ZONE_M, 0), display=False)
glue("attempts", str(ESCAPE_ATTEMPTS), display=False)
```

Valores usados («A VERIFICAR»): franja de {glue:text}`zone` m, $k$ = {glue:text}`attempts`
intentos y $C$ = 1.

## Especies

```{code-cell} ipython3
:tags: [remove-input]
PV.md_table(
    ["Especie", "Nombre científico", "Talla", "Alto / talla", "Ancho / talla", "Compresión"],
    [
        [
            s.name,
            s.scientific_name,
            f"{s.measure} [{s.unit}]",
            num(s.height, 3),
            num(s.width, 3),
            num(s.compression, 2),
        ]
        for s in species_catalogue()
    ],
)
```

Las secciones salen de `data/species.yaml` y son estimaciones de orden de magnitud («A
VERIFICAR»). Para bacalao, eglefino y cigala existen mediciones con FISHSELECT
{cite:p}`herrmann2009,frandsen2010`, que deben reemplazar a estas para un uso cuantitativo. En los
crustáceos la talla es el largo del caparazón (cigala) o el largo total (langostino), y la
sección es la del caparazón, rígido. Las pinzas de la cigala se enredan en el paño y no se
modelan {cite:p}`krag2008`.

## Copo de 120 mm: rombo, T90 y cuadrada

```{code-cell} ipython3
:tags: [remove-cell]
VAR = {o: sim(o, 120.0) for o in ("diamond", "t90", "square")}
LABEL = {"diamond": "Rombo", "t90": "T90", "square": "Cuadrada"}
SPECIES = ("cod", "haddock", "hake_hubbsi", "plaice")
CURVES = {o: {c.species.id: c for c in selectivity(r, SPECIES)} for o, r in VAR.items()}
l50 = {o: CURVES[o]["cod"].l50 for o in VAR}
assert l50["diamond"] < l50["t90"] and l50["diamond"] < l50["square"]
assert 2.5 < CURVES["diamond"]["cod"].sf < 4.5
glue("cod_d", num(l50["diamond"]), display=False)
glue("cod_t", num(l50["t90"]), display=False)
glue("sf_d", num(CURVES["diamond"]["cod"].sf, 1), display=False)
glue("sr_d", num(CURVES["diamond"]["cod"].sr), display=False)
glue("sr_t", num(CURVES["t90"]["cod"].sr), display=False)
```

Copo de la red FAO A-3 rehecho con malla de 120 mm (mismo ancho y largo relingados), 300 kg de
captura, fondo mixto, 3 kn:

```{code-cell} ipython3
:tags: [remove-input]
rows = []
for o, r in VAR.items():
    ms = r.mesh.summary()
    rows.append(
        [LABEL[o], f"{ms['opening_deg']:.0f}°"]
        + [f"{num(CURVES[o][s].l50)} · {num(CURVES[o][s].sr)}" for s in SPECIES]
    )
PV.md_table(
    ["Copo", "Apertura media", *(f"{CURVES['diamond'][s].species.name} L50 · SR [cm]" for s in SPECIES)],
    rows,
)
```

```{code-cell} ipython3
:tags: [remove-input]
fig, axes = P.plt.subplots(1, 2, figsize=(10.2, 3.6))
for ax, sp in zip(axes, ("cod", "plaice"), strict=True):
    for k, o in enumerate(VAR):
        c = CURVES[o][sp]
        P.line(ax, c.lengths, c.retention, k, LABEL[o], marker=False)
    ax.axhline(0.5, color="0.6", lw=0.8, ls="--")
    ax.set_title(f"Retención de {CURVES['diamond'][sp].species.name.lower()}")
    ax.set_xlabel("Largo total [cm]")
    ax.set_ylim(0, 1.02)
P.legend(axes[0])
P.finish(fig)
```

Para bacalao, el copo de rombo da $L_{50}$ = {glue:text}`cod_d` cm y SR = {glue:text}`sr_d` cm
($SF$ ≈ {glue:text}`sf_d`). Es el orden de los copos rómbicos de 120 mm medidos en el mar
{cite:p}`wienbeck2011`. El T90 sube $L_{50}$ a {glue:text}`cod_t` cm y da una selección más
nítida (SR = {glue:text}`sr_t` cm), en el sentido de lo que observaron {cite:t}`wienbeck2011` y
predijeron {cite:t}`herrmann2007`.

La platija, plana y delgada, pasa de canto. Su $L_{50}$ casi no depende de cómo se abra la malla:
depende de la luz más chica. Por eso un copo cuadrado o T90 no la selecciona mejor que uno de
rombo, como se sabe de las pesquerías mixtas de peces planos.

## La captura abre las mallas de delante

```{code-cell} ipython3
:tags: [remove-cell]
net = codend_variant(CASE.net, "diamond", mesh_mm=120.0)
R = run(dataclasses.replace(CASE, net=net))
CATCHES = [100.0, 300.0, 600.0, 1000.0]
HAUL = explore(R, "catch_kg", CATCHES, scenario=SC, resolution=RES)


def front_opening(r) -> float:
    st = r.mesh
    z = escape_zone(st)
    return float(np.average(st.opening_deg[z], weights=st.meshes[z]))


opening = [front_opening(r) for r in HAUL]
l50_haul = [selectivity(r, "cod")[0].l50 for r in HAUL]
assert opening[-1] > opening[0] and l50_haul[-1] > l50_haul[0]
glue("op_lo", f"{opening[0]:.0f}", display=False)
glue("op_hi", f"{opening[-1]:.0f}", display=False)
glue("l50_lo", num(l50_haul[0]), display=False)
glue("l50_hi", num(l50_haul[-1]), display=False)
```

```{code-cell} ipython3
:tags: [remove-input]
fig, axes = P.plt.subplots(1, 2, figsize=(10.2, 3.4))
P.line(axes[0], CATCHES, opening, 1, "")
P.line(axes[1], CATCHES, l50_haul, 0, "")
axes[0].set_title("Apertura de malla delante de la captura [°]")
axes[1].set_title("L50 del bacalao [cm]")
for ax in axes:
    ax.set_xlabel("Captura en el copo [kg]")
P.finish(fig)
```

Al crecer la captura, la bola de captura infla el copo. Las mallas de la franja de escape pasan de
{glue:text}`op_lo`° a {glue:text}`op_hi`° de apertura entre 100 y 1000 kg, y $L_{50}$ del bacalao
sube de {glue:text}`l50_lo` a {glue:text}`l50_hi` cm. Es el efecto del tamaño de la captura que
describió {cite:t}`herrmann2005`. El explorador animado de la aplicación lo muestra estado a estado
si se elige una especie.

## Supuestos y límites

- **Escape sólo geométrico**: no hay comportamiento del pez (natación, agotamiento, búsqueda de la
  malla), y el contacto $C$ y los intentos $k$ son constantes.
- **Sección elíptica** escalada con la talla, con coeficientes estimados («A VERIFICAR»). FISHSELECT
  usa formas medidas y modelos de penetración más finos.
- **Rigidez de apertura**: una bisagra lineal por nudo con $E_b$ y $\beta_0$ estimados. No modela
  el deslizamiento de los nudos ni la histéresis del paño usado.
- **Resolución**: dentro de un triángulo todas las mallas son iguales. La variación de malla a
  malla depende de la resolución de la simulación (3–4 en la aplicación).
- **Paneles de escape** (ventanas de malla cuadrada, rejillas) y la selectividad en la maniobra
  de virado no se modelan.

```{code-cell} ipython3
:tags: [remove-cell]
print(f"capítulo ejecutado en {time.perf_counter() - T0:.0f} s")
```
