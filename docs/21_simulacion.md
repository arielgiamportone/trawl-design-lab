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

# Simulación de la forma de la red

```{code-cell} ipython3
:tags: [remove-cell]
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path.cwd().parent))
sys.path.insert(0, str(pathlib.Path.cwd()))

import numpy as np

import _plots_t2 as P
import _plots_v as V
from trawlkit.model import run
from trawlkit.sim import DEFAULT_CN, DEFAULT_CT, DEFAULT_MU, build_model, rigging_from_result, simulate
from trawlkit.sim.validation import (
    CN_RANGE,
    CT_RANGE,
    DYNAMIT,
    FISHING_BAND_KN,
    calibrate,
    speed_exponent,
    standard_case,
    validate,
)

P.setup()
T0 = time.perf_counter()
R = run(standard_case())  # red FAO A-3 estándar, 150 HP, portón FAO, modo corregido
RES = 6  # resolución de la validación (divisiones nominales por panel)
```

## Propósito

Todas las etapas anteriores del libro son **reglas empíricas independientes**: la resistencia de la
red sale de la superficie sólida ({doc}`14_resistencia`), la abertura horizontal del equilibrio de
portones de Fridman y la vertical del ángulo de la brida ({doc}`16_aberturas`). Ninguna sabe cuánto
se abrió la red cuando calcula su resistencia, ni cuánto se deformó el paño cuando calcula su
abertura. {doc}`32_validacion_dynamit` mostró que donde el libro usa una regla práctica la
discrepancia con un simulador físico llega al 35–47 %.

`trawlkit.sim` agrega un **modelo físico simplificado de la forma de la red remolcada**: el paño,
las relingas, las boyas, el lastre, las bridas y las patentes en equilibrio bajo el arrastre del
agua, el peso, la flotación y el contacto con el fondo, con el aparejo que calcula el motor. Las
aberturas y la resistencia salen de la **misma forma de equilibrio** y son, por construcción,
coherentes entre sí. No reemplaza a DynamiT {cite:p}`dynamit` (no modela los portones ni los
cables de remolque, cuya separación es un dato de entrada) y es experimental: este capítulo
describe el modelo, verifica su convergencia y lo valida contra DynamiT y contra el motor
empírico.

## Modelo

### Discretización

Cada panel del plano relingado se divide en una grilla estructurada de nodos (interpolada entre sus
cuatro esquinas) y cada celda en dos triángulos. Los nodos que representan el mismo punto físico se
unifican: borde inferior de un panel con el superior del siguiente, costuras laterales entre dorso
y vientre (que cierran el embudo) y el final de la bolsa atado en un nodo. La **resolución** es el
número nominal de divisiones por panel: el ancho de cada ala tiene `resolution // 2` columnas y las
filas de cada franja son proporcionales a su largo (`resolution` filas cada 9 m).

### Elementos triangulares de paño

El paño de malla rómbica tiene dos familias de hilos. En coordenadas de malla $(t, n)$ (mallas a lo
ancho y a lo alto del panel) las coordenadas de hilo son $i = n + t$ y $j = n - t$, en unidades de
una pata de largo $a = \text{mallero}/2$. Dentro de un triángulo la posición $\mathbf{x}$ es lineal en
$(i, j)$, de modo que $\partial\mathbf{x}/\partial i$ y $\partial\mathbf{x}/\partial j$ son constantes:
son los vectores de **una pata** de cada familia. Es el elemento triangular de
{cite:t}`priour1999` ({cite:t}`priour2013`). El triángulo contiene $A_{ij}$ patas de cada familia
($A_{ij}$, área del triángulo en coordenadas de hilo), y la tensión de cada familia es

$$
T_k = EA \,\max\left(\frac{\lVert \partial\mathbf{x}/\partial k \rVert}{a} - 1,\ 0\right),
\qquad k \in \{i, j\},
$$ (eq-21-twine)

sólo a tracción (un hilo flojo no empuja), con $EA = E\,\pi d^2/4$ y $E = 2$ GPa (poliamida). El
elemento da al paño rigidez nula al corte y a la flexión y reproduce el acoplamiento
$U_1^2 + U_2^2 \le 1$ de la malla rómbica: el paño se angosta cuando se alarga. La longitud total de
hilo del triángulo es $2\,a\,A_{ij}$ y, sumada sobre un panel, $\sum d\,L$ coincide con la
superficie sólida FAO $S_s$ de {doc}`12_mecanica_red` (se verifica abajo).

### Hidrodinámica: Morison sobre cada familia de hilos

Cada familia de hilos de un triángulo es un cilindro de diámetro $d$ y largo $L = A_{ij}\,a$; con
$\mathbf{u} = v\,\hat{\mathbf{x}}$ la velocidad del agua relativa a la red y $u_n$, $u_t$ sus
componentes normal y tangencial al hilo, la fuerza de arrastre es la de {cite:t}`morison1950`:

$$
\mathbf{F}_n = \tfrac12 \rho\, C_N\, d\, L\, \lvert \mathbf{u}_n \rvert\, \mathbf{u}_n, \qquad
\mathbf{F}_t = \tfrac12 \rho\, C_T\, d\, L\, \lvert \mathbf{u}_t \rvert\, \mathbf{u}_t,
$$ (eq-21-morison)

con $\rho = 1024$ kg/m³, $C_N = 1{,}4$ y $C_T = 0{,}08$ por defecto (rangos usuales del hilo de red:
$C_N \approx 1{,}0$–$1{,}6$, $C_T \approx 0{,}01$–$0{,}12$; {cite:t}`lee2005`, {cite:t}`takagi2004`,
{cite:t}`priour2013`). Las relingas reciben el mismo arrastre con su diámetro; las bridas y
patentes, ninguno. Las boyas son esferas con empuje y arrastre
$\tfrac12 \rho\, C_D\, (\pi D^2/4)\, v^2$, con el $C_D$ del motor a cada velocidad
({doc}`17_flotacion_lastre`). Opcionalmente (`knot_factor`) los nudos se modelan como dos esferas
por malla de diámetro $k\,d$.

### Pesos, flotación y fondo

El peso sumergido del hilo es $(1 - \rho/\rho_{PA})\,g$ por unidad de masa (poliamida,
$\rho_{PA} = 1140$ kg/m³) y se reparte un tercio a cada vértice; relingas, bridas y patentes llevan
su peso sumergido por metro, el lastre del burlón se reparte entre alas, bocana y puntas como en
{doc}`17_flotacion_lastre` y las boyas se ubican sobre la lima con la distribución selectiva del
motor. El fondo $z = 0$ es una restricción unilateral: un nodo apoyado recibe la reacción
$R = \max(0, -F_z)$ y el rozamiento cinético

$$
F_x^{\text{fondo}} = \mu\, R, \qquad \mu = 0{,}5,
$$ (eq-21-friction)

dirigido hacia popa: en el arrastre estacionario todo punto apoyado desliza sobre el fondo con
velocidad $-v\,\hat{\mathbf{x}}$, así que la dirección es exacta.

### Aparejo y condiciones de borde

Las bridas superior e inferior (la inferior con la cadena de reglaje, de modo que suma lo mismo que
la superior) van de cada punta de ala a un nodo de unión, y la patente de ese nodo al punto de
remolque del portón. Los **portones están fijos** en $x = 0$, $y = \pm D_P/2$ y
$z = h_{\text{portón}}/2$, con $D_P$ la distancia entre portones del motor
({doc}`15_portones_aparejo`, 32,5 m para el caso FAO A-3) o la que se imponga. Las longitudes de
lima y burlón, bridas y patentes, el número y la posición de las boyas y el lastre salen del
`DesignResult` (`rigging_from_result`). La red es simétrica respecto del plano $y = 0$: las fuerzas
se proyectan sobre el subespacio simétrico, lo que equivale a simular media red.

### Solver: relajación dinámica con FIRE

La forma de equilibrio $\mathbf{F}(\mathbf{x}) = \mathbf{0}$ se busca por **relajación dinámica**
{cite:p}`barnes1999`: se integra en un tiempo ficticio $M\,\ddot{\mathbf{x}} = \mathbf{F}(\mathbf{x})$
con masas ficticias iguales a una cota de Gershgorin de la rigidez axial de cada nodo (paso unitario
estable) y el amortiguamiento adaptativo FIRE {cite:p}`bitzek2006`:

$$
\mathbf{v} \leftarrow (1 - \alpha)\,\mathbf{v} + \alpha\, \lVert\mathbf{v}\rVert\,
\frac{\mathbf{F}}{\lVert\mathbf{F}\rVert}, \qquad
\text{si } \mathbf{F}\cdot\mathbf{v} \le 0:\ \mathbf{v} \leftarrow \mathbf{0},\ \Delta t \leftarrow \Delta t/2,
$$ (eq-21-fire)

con $\Delta t$ creciendo un 10 % y $\alpha$ decayendo mientras la potencia $\mathbf{F}\cdot\mathbf{v}$
sea positiva. Se detiene cuando el residuo $\lVert\mathbf{F}\rVert/D$ y el desbalance global
$\lvert\sum F_x\rvert/D$ ($D$, arrastre de la red) quedan por debajo de 1 % y AH, AV y $D$ cambian
menos de 0,3 % entre ventanas de 1000 iteraciones. Primero se resuelve una malla gruesa
(resolución 4) y su forma se interpola como punto de partida. Un Newton implícito no funciona
bien: la transición flojo/tenso de hilos casi inextensibles arruina la linealización.

**Qué se mide.** AH es la distancia entre puntas de ala de la lima; AV la altura de la lima sobre el
burlón en el centro de la boca; la resistencia de la red es el arrastre del agua sobre paño,
relingas y boyas más el rozamiento con el fondo, igual (en el equilibrio) al tiro de las bridas.

```{code-cell} ipython3
:tags: [hide-input]
# Identidad de la superficie sólida: Σ d·L del paño discretizado = Ss corregida del motor.
from trawlkit.compat import Compat
from trawlkit.net import analyse

ss = analyse(R.case.net, Compat.CORRECTED).solid_surface_m2
rows = []
for res in (3, 6, 8):
    m = build_model(R.case.net, rigging_from_result(R), resolution=res)
    assert abs(m.solid_surface_m2 / ss - 1) < 2e-3
    rows.append([str(res), str(m.n_nodes), str(len(m.tri)), V.fmt(m.solid_surface_m2, 2),
                 V.pct_s(m.solid_surface_m2, ss, 2) + " %"])
V.md_table(["Resolución", "Nodos", "Triángulos", "Σ d·L [m²]", "Δ vs Ss motor"], rows)
print(f"Ss del motor (modo corregido): {ss:.2f} m²".replace(".", ","))
```

La única diferencia es la punta de ala, cuyo borde de boca de 3 mallas se reduce a un punto: menos
de 0,2 % de la superficie.

## Convergencia de malla

```{code-cell} ipython3
:tags: [hide-input]
CONV = {res: simulate(R, 3.0, resolution=res) for res in (3, 4, 6, 8)}
rows = [[str(res), str(r.nodes.shape[0]), V.fmt(r.ah_m, 2), V.fmt(r.av_m, 2),
         V.fmt(r.drag_kgf, 0), V.fmt(r.runtime_s, 1), "sí" if r.converged else "no"]
        for res, r in CONV.items()]
V.md_table(["Resolución", "Nodos", "AH [m]", "AV [m]", "Resistencia [kgf]", "Tiempo [s]",
            "Convergió"], rows)
c6, c8 = CONV[6], CONV[8]
assert abs(c8.ah_m / c6.ah_m - 1) < 0.02 and abs(c8.drag_kgf / c6.drag_kgf - 1) < 0.02
assert abs(c8.av_m / c6.av_m - 1) < 0.08
```

A 3 kn, AH y la resistencia cambian menos de 2 % entre las resoluciones 6 y 8, y menos de 10 %
desde la 3. La abertura vertical converge más lento y **decrece** al refinar: 1,96 / 1,70 / 1,64 m
con resoluciones 3, 6 y 8, y según `tests/test_sim_slow.py` 1,48 y 1,40 m con 10 y 12. Una malla
gruesa no puede representar la curvatura de la lima entre boyas y la sobrestima; el valor
convergido está más cerca de los 1,4 m de DynamiT que el de resolución 6. El costo crece con el
número de nodos (≈ 1 s por velocidad con resolución 3–4, ≈ 4 s con 6, ≈ 10 s con 8): la API
(`POST /simulate`) usa 4 por defecto, la aplicación web ofrece 3 («rápida») y 6 («normal»), y este
capítulo valida con 6.

## Validación contra DynamiT y contra el motor

Se simula la red FAO A-3 estándar a las nueve velocidades de la tabla de DynamiT
({doc}`32_validacion_dynamit`) con la separación de portones del motor (32,5 m) y los coeficientes
por defecto, y se compara con DynamiT y con las magnitudes empíricas del motor: DPA de Fridman, AV de
Fridman y $R_N$ de diseño (Aberdeen).

```{code-cell} ipython3
:tags: [hide-input]
VAL = validate(resolution=RES, result=R)
v = VAL.v_kn
band = (v >= FISHING_BAND_KN[0]) & (v <= FISHING_BAND_KN[1])
SPEC = (("AH", "m", 1, "DPA Fridman"), ("AV", "m", 2, "AV Fridman"),
        ("RA", "kgf", 0, "Rn diseño (Aberdeen)"))
rows = []
for var, unit, nd, ename in SPEC:
    sim, dyn, eng = VAL.sim[var], VAL.dynamit[var], VAL.engine[var][ename]
    rows.append([f"{var} DynamiT [{unit}]", *[V.fmt(x, nd) for x in dyn]])
    rows.append([f"**{var} simulación [{unit}]**", *[V.fmt(x, nd) for x in sim]])
    rows.append([f"{var} motor [{unit}]", *[V.fmt(x, nd) for x in eng]])
    rows.append([f"Δ {var} sim/DynamiT [%]", *[V.pct_s(a, b, 0) for a, b in zip(sim, dyn)]])
    rows.append([f"Δ {var} motor/DynamiT [%]", *[V.pct_s(a, b, 0) for a, b in zip(eng, dyn)]])
V.md_table(["v [kn]", *[V.fmt(x, 1) for x in v]], rows)
```

```{code-cell} ipython3
:tags: [hide-input]
rows = []
for var, _, _, ename in SPEC:
    es, ee = VAL.errors[var], VAL.engine_errors[var][ename]
    rows.append([var, V.sfmt(es.bias_pct_band, 1), V.fmt(es.mean_abs_pct_band, 1),
                 V.fmt(es.mean_abs_pct, 1), V.sfmt(ee.bias_pct_band, 1),
                 V.fmt(ee.mean_abs_pct_band, 1), V.fmt(ee.mean_abs_pct, 1)])
V.md_table(["Variable", "Sesgo sim 2–4 kn [%]", "Error sim 2–4 kn [%]", "Error sim 1–5 kn [%]",
            "Sesgo motor 2–4 kn [%]", "Error motor 2–4 kn [%]", "Error motor 1–5 kn [%]"], rows)
N_SIM = speed_exponent(v, VAL.sim["RA"])
N_DYN = speed_exponent(v, VAL.dynamit["RA"])
print(f"Exponente de velocidad de la resistencia: simulación v^{N_SIM:.2f}, "
      f"DynamiT v^{N_DYN:.2f}".replace(".", ","))
# Lo que dice el texto.
assert VAL.errors["AH"].mean_abs_pct_band < 5
assert VAL.errors["AV"].mean_abs_pct_band < 20
assert -55 < VAL.errors["RA"].bias_pct_band < -40
assert 1.6 < N_SIM < 1.85 and 1.4 < N_DYN < 1.55
```

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Red FAO A-3 estándar según DynamiT (puntos negros), la simulación de forma de `trawlkit.sim`
      (resolución 6, portones a 32,5 m) y el motor empírico (DPA y AV de Fridman, $R_N$ de
      Aberdeen). La banda gris marca el rango de pesca, 2–4 kn.
    name: fig-21-validacion
---
fig, axes = P.plt.subplots(1, 3, figsize=(10.2, 3.6))
TITLES = {"AH": "Abertura horizontal AH [m]", "AV": "Abertura vertical AV [m]",
          "RA": "Resistencia de la red [kgf]"}
for ax, (var, unit, nd, ename) in zip(axes, SPEC):
    ax.axvspan(*FISHING_BAND_KN, color=P.NEUTRAL_WASH, lw=0, zorder=0)
    ax.plot(v, VAL.dynamit[var], "o", color=P.INK, ms=6, mec=P.SURFACE, mew=1.2, zorder=4,
            label="DynamiT")
    P.line(ax, v, VAL.sim[var], 1, "Simulación")
    P.line(ax, v, VAL.engine[var][ename], 2, "Motor empírico")
    ax.set_title(TITLES[var], fontsize=10.5)
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.set_xlim(0.8, 5.2)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Velocidad [kn]")
P.legend(axes[2], loc="upper left", fontsize=8.5)
P.finish(fig)
```

**Abertura horizontal.** Es donde la simulación acierta: dentro del 3 % de DynamiT entre 2 y 4 kn,
y con la misma **meseta** (13–13,5 m) que la DPA de Fridman no tiene: en la simulación las
relingas y el paño, de largo fijo, limitan la abertura, mientras que la fórmula de Fridman sigue
creciendo con la velocidad (16 m a 5 kn). Por debajo de 2 kn la simulación sobrestima: con los
portones fijos a 32,5 m la red queda abierta aunque no haya arrastre que la tense, y DynamiT, que
sí calcula los portones, los cierra a 28,5 m a 1 kn.

**Abertura vertical.** La tendencia es la de DynamiT —la red se aplasta al acelerar porque la
resistencia crece más que la flotación— con un sesgo de +10 % en el rango de pesca, comparable al
de la AV de Fridman, y que baja al refinar la malla (sección anterior). Igual que Fridman, la
simulación no reproduce el **repunte** de DynamiT por encima de 4 kn (1,0 → 1,6 m): en la
simulación la AV sigue cayendo hasta 0,5 m. Ese repunte necesita algo que el modelo no tiene: un
burlón que se despega del fondo o un cambio en el reparto de tensiones entre alas y bridas que
depende de los portones y los cables.

**Resistencia.** Es la gran discrepancia: la simulación da **la mitad** que DynamiT en todo el
rango (≈ −50 %), mientras el motor empírico da ≈ 20 % más. Además crece más rápido con la velocidad
($v^{1,73}$ contra $v^{1,48}$), algo más cerca del $v^2$ de un cuerpo rígido: el paño simulado se
alinea con el flujo, pero no tanto como en DynamiT. La siguiente sección analiza la brecha.

### Con la separación de portones de DynamiT

DynamiT calcula la distancia entre portones (47–52 m en el rango de pesca), mientras que el motor la
fija en 32,5 m con la regla "al metro de cable" (−35 %, {doc}`32_validacion_dynamit`). Imponer en
la simulación la DP de DynamiT aísla la red del modelo de portones:

```{code-cell} ipython3
:tags: [hide-input]
VAL_D = validate(resolution=4, door_spread="dynamit", result=R)  # resolución 4: más rápido
rows = []
for var in ("AH", "AV", "RA"):
    a, b = VAL.errors[var], VAL_D.errors[var]
    rows.append([var, V.sfmt(a.bias_pct_band, 1), V.sfmt(b.bias_pct_band, 1)])
V.md_table(["Variable", "Sesgo 2–4 kn, DP del motor [%]", "Sesgo 2–4 kn, DP de DynamiT (resolución 4) [%]"],
           rows)
assert VAL_D.errors["AH"].bias_pct_band > 25 and VAL_D.errors["AV"].bias_pct_band < -35
```

Con los portones 15–20 m más separados la red simulada se abre ≈ 35 % más que en DynamiT y se
aplasta (AV ≈ −45 %); la resistencia sube, pero sigue ≈ 40 % por debajo. Que la AH empeore con la DP
"correcta" indica que en DynamiT la geometría del aparejo es otra (patentes y bridas más largas, o
un ángulo de ataque distinto) y no se conoce: la captura de DynamiT no trae esos datos. Con la DP
del motor la red simulada tiene la geometría de las otras etapas del libro, y es la comparación que
se usa en el resto del capítulo.

## Calibración: ¿alcanza con los coeficientes del hilo?

La resistencia de Morison es lineal en $C_N$ y $C_T$, así que la pregunta natural es si existen
coeficientes razonables que cierren la brecha. Se barre $C_N$ en todo el rango de la literatura y
$C_T$ entre 0,04 y 0,12, a 3 kn. Con $C_T \approx 0{,}01$ la relajación no converge en 40 000
iteraciones: casi sin fuerza tangencial el cuerpo y la bolsa, alineados con el flujo, quedan sin
tensión que los estire y siguen derivando.

```{code-cell} ipython3
:tags: [hide-input]
CAL = calibrate(cn_values=(1.0, 1.4, 1.6), ct_values=(0.04, 0.08, 0.12), speeds_kn=(3.0,),
                resolution=3, door_spread="engine", result=R)
rows = [[V.fmt(c["cn"], 1), V.fmt(c["ct"], 2), V.sfmt(c["ra_bias_pct"], 0),
         V.fmt(c["ah_mean_abs_pct"], 0), V.fmt(c["av_mean_abs_pct"], 0)] for c in CAL]
V.md_table(["C_N", "C_T", "Δ RA vs DynamiT [%]", "|Δ AH| [%]", "|Δ AV| [%]"], rows)
best = CAL[0]
assert (best["cn"], best["ct"]) == (1.6, 0.12) and best["ra_bias_pct"] < -30
print(f"Rangos: C_N {CN_RANGE}, C_T {CT_RANGE}".replace(".", ","))
```

Aun con los dos coeficientes en el extremo superior la resistencia queda ≈ 40 % por debajo de
DynamiT. $C_T$ pesa más que $C_N$: buena parte del paño, sobre todo el cuerpo y la bolsa, trabaja
casi alineado con el flujo, donde sólo actúa la componente tangencial. Subir $C_T$ también abre la
red en vertical (la tensión adicional levanta la lima), así que la calibración no es gratis: mueve
la AV. Los nudos, ignorados por defecto, agregan arrastre de forma, independiente de la orientación
del hilo:

```{code-cell} ipython3
:tags: [hide-input]
rows = []
KNOTS = {}
for kf in (0.0, 2.0, 3.0):
    kv = KNOTS[kf] = validate(resolution=4, knot_factor=kf, speeds_kn=[2.0, 3.0, 4.0], result=R)
    rows.append([V.fmt(kf, 1), *[V.fmt(x, 0) for x in kv.sim["RA"]],
                 V.sfmt(kv.errors["RA"].pct.mean(), 0), *[V.fmt(x, 2) for x in kv.sim["AV"]],
                 V.fmt(speed_exponent(kv.v_kn, kv.sim["RA"]), 2)])
V.md_table(["Nudo k = D/d", "RA 2 kn", "RA 3 kn", "RA 4 kn", "Δ RA medio [%]", "AV 2 kn",
            "AV 3 kn", "AV 4 kn", "Exponente"], rows)
print("DynamiT: RA", [round(x) for x in np.asarray(DYNAMIT["RA_kg"])[[2, 4, 6]]],
      "AV", [float(x) for x in np.asarray(DYNAMIT["AV_m"])[[2, 4, 6]]])
k3 = KNOTS[3.0]
assert -25 < k3.errors["RA"].pct[0] < -5 and k3.errors["RA"].pct[2] > -5
assert speed_exponent(k3.v_kn, k3.sim["RA"]) > 1.8 and k3.sim["AV"][2] < 0.7
```

Con nudos de 3 veces el diámetro del hilo la resistencia llega a la de DynamiT entre 3 y 4 kn, pero
con la forma equivocada: el arrastre de los nudos es de esfera, $\propto v^2$, de modo que la curva
queda demasiado empinada (exponente ≈ 1,9 contra 1,48; −17 % a 2 kn y por encima a 4 kn) y la red
se aplasta (AV de 0,4–0,6 m a 4 kn contra 1,0 m de DynamiT).
Ningún parámetro físico aislado del modelo cierra la brecha sin romper otra cosa.

## La brecha de resistencia

Las causas plausibles, en orden de importancia estimada:

1. **Coeficientes de un hilo aislado.** Morison con $C_N$, $C_T$ de un cilindro liso en flujo
   uniforme subestima el arrastre de un hilo trenzado de red: rugosidad, vibración inducida por
   vórtices y la ondulación del paño ("flameo") aumentan el arrastre efectivo. Los simuladores de
   redes, DynamiT incluido, usan coeficientes del **paño** ajustados en canal o en tanque, no del
   hilo; con hilos de PA de 1–2 mm y 2–3 kn el número de Reynolds del hilo (≈ 10³) está además en
   la zona donde $C_N$ cambia con la velocidad.
2. **Nudos y bordes.** Los nudos (≈ 2–3 diámetros de hilo, dos por malla), las costuras, las
   relingas armadas y los refuerzos no están en el modelo por defecto; la tabla anterior muestra que
   alcanzan para explicar una fracción grande de la diferencia.
3. **Bolsa y captura.** La bolsa simulada está vacía y su exceso de largo (bolsa J de 250 mallas
   cosida a la I de 200) forma un bolsón flojo; en una red real la bolsa se llena de agua retenida y
   de captura, con un arrastre de cuerpo romo.
4. **Fondo.** El rozamiento simulado del burlón es pequeño (≈ 12 kgf a 3 kn, el 2 % de la
   resistencia), porque el burlón apenas apoya con el lastre de este diseño; DynamiT no informa el
   suyo. El término independiente de la velocidad de Aberdeen (el rozamiento de las partes que
   arrastran por el fondo, {doc}`32_validacion_dynamit`) sugiere que el motor sí carga un
   rozamiento de fondo mayor.
5. **Qué incluye RA.** Si RA de DynamiT incluyera parte del aparejo (bridas, patentes, los cables
   entre portones y red) la brecha sería menor; la captura no lo aclara ({doc}`32_validacion_dynamit`).

La conclusión práctica es la misma de la nota de la aplicación web: **la simulación sirve para la
forma y las aberturas**, que dependen del equilibrio entre fuerzas y no de su valor absoluto, y el
**motor sigue siendo la referencia para la resistencia de diseño**, que es conservadora.

## La forma a 3 kn

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Forma de equilibrio de la red FAO A-3 estándar a 3 kn (resolución 6, portones a 32,5 m),
      coloreada por la tensión del hilo. La lima (azul) y el burlón (negro) delimitan la boca; la
      red avanza hacia la izquierda. Escala vertical × 3. La figura es interactiva (girar, acercar).
    name: fig-21-forma
---
import plotly.graph_objects as go
from IPython.display import HTML

r3 = next(r for r in VAL.results if r.speed_kn == 3.0)
xyz = r3.nodes
tens = np.zeros(len(xyz))
cnt = np.zeros(len(xyz))
tt = r3.twine_tension_n.max(axis=1)
for k in range(3):
    np.add.at(tens, r3.triangles[:, k], tt)
    np.add.at(cnt, r3.triangles[:, k], 1)
tens = np.divide(tens, cnt, out=np.zeros_like(tens), where=cnt > 0)
EX = 3.0  # exageración vertical
fig = go.Figure()
fig.add_trace(go.Mesh3d(
    x=xyz[:, 0], y=xyz[:, 1], z=xyz[:, 2] * EX,
    i=r3.triangles[:, 0], j=r3.triangles[:, 1], k=r3.triangles[:, 2],
    intensity=tens, colorscale="Blues", opacity=0.85, flatshading=True,
    colorbar=dict(title="Tensión del hilo [N]", thickness=12), name="paño",
    hovertemplate="x %{x:.1f} m<br>y %{y:.1f} m<extra></extra>"))
for idx, color, name in ((r3.headrope, P.color(1), "lima"), (r3.footrope, P.INK, "burlón")):
    p = xyz[idx]
    fig.add_trace(go.Scatter3d(x=p[:, 0], y=p[:, 1], z=p[:, 2] * EX, mode="lines",
                               line=dict(color=color, width=6), name=name))
# Escena acotada a la red (sin portones ni patentes) con proporciones reales (z exagerada).
net = xyz[np.unique(r3.triangles)]
lo, hi = net.min(axis=0), net.max(axis=0)
lo[2], hi[2] = 0.0, hi[2] * EX
span = hi - lo
fig.update_layout(
    height=500, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor=P.SURFACE,
    scene=dict(
        xaxis=dict(title="x [m]", range=[lo[0], hi[0]]),
        yaxis=dict(title="y [m]", range=[lo[1], hi[1]]),
        zaxis=dict(title="z × 3 [m]", range=[lo[2], hi[2]]),
        aspectmode="manual",
        aspectratio=dict(x=1.0, y=span[1] / span[0], z=span[2] / span[0]),
        camera=dict(eye=dict(x=-0.55, y=-1.15, z=0.6), center=dict(x=0, y=0, z=-0.15)),
    ),
    legend=dict(x=0.02, y=0.98))
# Una sola salida HTML (plotly.js desde su CDN): se ve en el libro estático sin servidor.
HTML(fig.to_html(full_html=False, include_plotlyjs="cdn", config={"displaylogo": False}))
```

```{code-cell} ipython3
:tags: [hide-input]
rows = [["Abertura horizontal AH (lima)", V.fmt(r3.ah_m, 2), "m"],
        ["Abertura horizontal (burlón)", V.fmt(r3.ah_lower_m, 2), "m"],
        ["Abertura vertical AV", V.fmt(r3.av_m, 2), "m"],
        ["Altura de la lima en el centro", V.fmt(r3.headrope_height_m, 2), "m"],
        ["Área de la boca", V.fmt(r3.mouth_area_m2, 1), "m²"],
        ["Arrastre del agua", V.fmt(r3.hydro_drag_kgf, 0), "kgf"],
        ["Rozamiento con el fondo", V.fmt(r3.friction_kgf, 0), "kgf"],
        ["Tiro de las bridas", V.fmt(r3.bridle_pull_kgf, 0), "kgf"],
        ["Largo de la red (punta de ala a bolsa)", V.fmt(r3.net_length_m, 1), "m"],
        ["Iteraciones / residuo", f"{r3.iterations} / {r3.residual:.1e}", ""]]
V.md_table(["Magnitud a 3 kn", "Valor", "Unidad"], rows)
assert abs(r3.bridle_pull_kgf / r3.drag_kgf - 1) < 0.03  # equilibrio global
```

El tiro de las bridas iguala la resistencia de la red (agua más fondo) dentro del 3 %: el
equilibrio global se cumple. La tensión se concentra en las alas y en el cuerpo cerca de la
bocana, que transmiten el tiro de las bridas, y cae hacia la bolsa.

## Supuestos y límites

- **Portones y cables fuera del modelo.** La distancia entre portones es un dato (la del motor o una
  impuesta); no hay equilibrio de portones ni catenaria del cable de remolque. Por eso la simulación
  no predice la DP y sobrestima la AH a baja velocidad.
- **Resistencia ≈ 50 % baja** frente a DynamiT con los coeficientes del hilo de la literatura
  (sección anterior). No usar la resistencia simulada para dimensionar el buque ni el cable.
- **Cuasiestático.** Un solo estado estacionario por velocidad, sin oleaje, cabeceo del buque ni
  cambios de rumbo; sin captura en la bolsa.
- **Malla gruesa.** La AV converge lento con la resolución (≈ 15 % entre 6 y 12); AH y resistencia
  convergen enseguida.
- **Un solo caso de validación.** La red FAO A-3 estándar contra una sola simulación DynamiT de
  aparejo desconocido; ninguna de las dos herramientas se comparó con mediciones en el mar.

```{code-cell} ipython3
:tags: [remove-cell]
print(f"Tiempo total del capítulo: {time.perf_counter() - T0:.0f} s")
```
