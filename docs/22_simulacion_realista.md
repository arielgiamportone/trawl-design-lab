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

# Simulación con captura, fondo y portones acoplados

```{code-cell} ipython3
:tags: [remove-cell]
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path.cwd().parent))
sys.path.insert(0, str(pathlib.Path.cwd()))

import numpy as np

import _plots_t2 as P
from trawlkit.model import run
from trawlkit.rigging import seabeds
from trawlkit.sim import Scenario, haul, simulate
from trawlkit.sim.validation import DYNAMIT, standard_case

P.setup()
T0 = time.perf_counter()
R = run(standard_case())  # red FAO A-3 estándar, 150 HP, portón FAO, modo corregido
RES = 4
CATCHES = [0.0, 500.0, 1000.0, 1500.0]
V = 3.0
```

## Propósito

{doc}`21_simulacion` resuelve la forma de la red **limpia y vacía**, con un único rozamiento con el
fondo y los portones fijos a la separación que da la regla del motor. En el mar, la red trabaja
condicionada por la realidad: la captura llena el copo y lo frena, el tipo de fondo cambia el roce
del tren y de los portones, y los portones no van a una separación fija sino a la que resulta del
equilibrio entre su sustentación, la red que los cierra y el cable que los remolca. Este capítulo
agrega esas tres condiciones al simulador (`trawlkit.sim.Scenario`) y el **lance progresivo**
(`trawlkit.sim.haul`): una secuencia de equilibrios mientras entra la captura.

### Panorama: qué hay en el mercado y qué agrega este proyecto

| Herramienta | Organización | Modelo | Captura | Tipo de fondo | Incertidumbre | Abierto |
|---|---|---|---|---|---|---|
| DynamiT {cite:p}`dynamit` | Ifremer | Elementos finitos de Priour, dinámico | no | fondo plano, sin sedimento | no | no |
| SimuTrawl | MPSL (Corea) | Masa-resorte {cite:p}`lee2005` | no | sólo fango (según {cite:t}`nguyen2016`) | no | no |
| Trawl Vision PRO | AcruxSoft | Semiempírico + sensores | no | no | no | no |
| NaLA | Nitto Seimo | Masas y resortes {cite:p}`takagi2004` | no | no | asimilación de datos en cerco | no |
| FhSim | SINTEF | Simulación en el tiempo | no | no | estimación de estado | parcial |
| **trawl-design-lab** | este proyecto | Elementos de Priour + FIRE, portones acoplados | **sí** | **catálogo con rango** | **(entrega 11.4)** | **sí** |

La comparación de {cite:t}`nguyen2016` y la búsqueda hecha para este capítulo coinciden: ningún
simulador comercial modela la captura en el copo, el tipo de sedimento con detalle, el ensuciamiento
de la red ni la incertidumbre. La captura y su efecto sobre la forma del copo existen en
herramientas de investigación (FEMNET y PRESEMO, {cite:t}`herrmann2005`) pero no integradas con la
red completa, los portones y el fondo en una herramienta abierta y en el navegador. Ese es el
diferencial que se construye en la Fase 11: este capítulo cubre la captura, el fondo y los portones
acoplados; las entregas siguientes agregan ensuciamiento, corriente, energía y huella sobre el
fondo, el zoom malla a malla con selectividad y las bandas de incertidumbre.

## Modelo

### Captura en el copo

La captura ocupa el extremo cerrado del copo con un volumen

$$
V_c = \frac{m_c}{\rho_a},
$$ (eq-22-volume)

con $m_c$ la captura y $\rho_a$ la densidad aparente (organismos y agua intersticial; 750 kg/m³ por
defecto para peces, 850 para crustáceos y 1000 para una mezcla con fango o conchilla, valores
«A VERIFICAR»). El copo se recorre anillo por anillo desde el extremo cerrado (cada anillo es una
fila de los paneles centrales del dorso y del vientre) y se integra el volumen entre secciones
como troncos de cono hasta llegar a $V_c$. Cada sección se toma con el área del círculo de su
perímetro, $A = P^2/4\pi$: la captura **infla** el copo hasta su circunferencia (un copo vacío va
aplastado y su área instantánea es casi nula, lo que haría que la captura «ocupara» toda la red).

En la zona ocupada los hilos dejan de filtrar (el flujo queda bloqueado) y el paño recibe, como en
el modelo de {cite:t}`oneill1997codend`, la presión de la «bola» de captura normal hacia afuera:

$$
p_c = \tfrac12\,\rho\,C_p\,v^2 ,
$$ (eq-22-pressure)

con $C_p = 1$ por defecto («A VERIFICAR»). Sobre una superficie cerrada salvo por el frente de la
captura, la resultante axial de esa presión es $p_c\,A_f$, con $A_f$ el área del frente: es la
resistencia de la captura. El peso sumergido de los organismos,
$m_c\,g\,(1-\rho/\rho_o)$ con $\rho_o$ su densidad, se reparte en la mitad inferior de la zona. La
zona se recalcula durante la relajación con la forma actual.

### Tipo de fondo

El rozamiento con el fondo es de Coulomb (reacción normal por $\mu$, opuesto al avance). El
catálogo `data/seabed.yaml` da, por tipo de sedimento, un $\mu$ para el tren de fondo y el paño
apoyado y otro para las zapatas de los portones, cada uno con valor nominal y rango, y la clase de
penetración de BENTHIS {cite:p}`eigaard2016`:

```{code-cell} ipython3
:tags: [remove-input]
import _plots_v as PV

def es(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")

PV.md_table(
    ["Fondo", "μ tren y paño", "μ portón", "Penetración"],
    [
        [
            s.name,
            f"{es(s.mu_gear.nominal)} ({es(s.mu_gear.low)}–{es(s.mu_gear.high)})",
            f"{es(s.mu_door.nominal)} ({es(s.mu_door.low)}–{es(s.mu_door.high)})",
            s.penetration,
        ]
        for s in seabeds()
    ],
)
```

No existe una tabla publicada de coeficientes de rozamiento por sedimento para artes de arrastre
(sí mediciones del arrastre del tren de fondo por tipo de sedimento, {cite:t}`oneill2016`): los
valores son estimaciones de ingeniería, marcadas «A VERIFICAR», y por eso llevan rango. La entrega
de incertidumbre (11.4) los trata como variables inciertas en lugar de números exactos.

### Portones acoplados

Con `coupled_doors` cada portón es un nodo libre con

$$
\mathbf{F}_\text{portón} = \tfrac12\rho A v^2 \left(C_D\,\hat{\mathbf{x}} + C_L\,\hat{\mathbf{y}}_\text{afuera}\right)
- W_\text{agua}\,\hat{\mathbf{z}} - \mu_\text{portón} R\,\hat{\mathbf{x}}_\text{avance} ,
$$ (eq-22-door)

con $C_L$ y $C_D$ de su polar al ángulo de ataque del caso (32° para el portón FAO), su peso en el
agua y el rozamiento de la zapata. El cable de remolque es una cadena de diez barras de acero con
su peso y su arrastre de Morison, desde el portón hasta la pasteca del buque, fija a la profundidad
de trabajo y a media separación de pastecas. La separación de portones $D_P$ ya no es un dato:
sale del equilibrio con la red, las bridas y las patentes.

## Validación: separación de portones

```{code-cell} ipython3
:tags: [remove-cell]
HAUL = {sb: haul(R, V, CATCHES, scenario=Scenario(seabed=sb), resolution=RES) for sb in ("mud", "rock")}
EMPTY = HAUL["mud"][0]
DYN_DP = DYNAMIT["DP_m"][DYNAMIT["v_kn"].index(V)]
ENG_DP = float(R.doors.spread_m)
# El equilibrio acoplado se acerca a DynamiT mucho más que la regla del motor.
assert abs(EMPTY.door_spread_m - DYN_DP) / DYN_DP < 0.15
assert abs(EMPTY.door_spread_m - DYN_DP) < abs(ENG_DP - DYN_DP)
```

A 3 kn, sin captura y sobre fondo de fango, el equilibrio acoplado da una separación de portones
de **{glue:text}`dp_sim` m**, frente a **{glue:text}`dp_dyn` m** de DynamiT y **{glue:text}`dp_eng`
m** de la regla práctica del motor ({doc}`15_portones_aparejo`): el error frente a DynamiT baja de
{glue:text}`err_eng` % a {glue:text}`err_sim` %.

```{code-cell} ipython3
:tags: [remove-cell]
from myst_nb import glue

glue("dp_sim", f"{EMPTY.door_spread_m:.1f}".replace(".", ","), display=False)
glue("dp_dyn", f"{DYN_DP:.1f}".replace(".", ","), display=False)
glue("dp_eng", f"{ENG_DP:.1f}".replace(".", ","), display=False)
glue("err_eng", f"{(ENG_DP - DYN_DP) / DYN_DP * 100:+.0f}".replace("-", "−"), display=False)
glue("err_sim", f"{(EMPTY.door_spread_m - DYN_DP) / DYN_DP * 100:+.0f}".replace("-", "−"), display=False)
glue("pull0", f"{EMPTY.towing_pull_kgf:.0f}", display=False)
glue("demand", f"{float(np.interp(V, R.case.speeds_kn, R.performance.demand.std)):.0f}", display=False)
```

El tiro total del arte en el buque (los dos cables) es {glue:text}`pull0` kgf, contra
{glue:text}`demand` kgf de la demanda del motor a la misma velocidad: el simulador hereda la brecha
de resistencia del paño que documenta {doc}`21_simulacion` (la resistencia de los hilos sola queda
≈ 40–50 % por debajo de la de DynamiT). Las tendencias que siguen son relativas y no dependen de esa
brecha.

## Lance progresivo

```{code-cell} ipython3
:tags: [remove-input]
fig, axes = P.plt.subplots(1, 3, figsize=(10.2, 3.5))
labels = {"mud": "Fango", "rock": "Roca"}
for slot, (sb, runs) in enumerate(HAUL.items(), start=1):
    kg = [r.scenario["catch_kg"] for r in runs]
    P.line(axes[0], kg, [r.door_spread_m for r in runs], slot, labels[sb])
    P.line(axes[1], kg, [r.towing_pull_kgf for r in runs], slot, labels[sb])
    P.line(axes[2], kg, [r.ah_m for r in runs], slot, labels[sb])
axes[0].axhline(DYN_DP, color=P.INK_2, lw=1, ls="--")
axes[0].annotate("DynamiT, sin captura", (0, DYN_DP), xytext=(4, -12), textcoords="offset points",
                 color=P.INK_2, fontsize=8.5)
for ax, title in zip(axes, ("Separación de portones [m]", "Tiro en el buque [kgf]",
                            "Abertura horizontal [m]"), strict=True):
    ax.set_title(title)
    ax.set_xlabel("Captura en el copo [kg]")
P.legend(axes[0], loc="lower left")
P.finish(fig)
```

```{code-cell} ipython3
:tags: [remove-cell]
for runs in HAUL.values():
    dp = [r.door_spread_m for r in runs]
    pull = [r.towing_pull_kgf for r in runs]
    assert all(a > b for a, b in zip(dp, dp[1:])), dp  # los portones se cierran
    assert all(a < b for a, b in zip(pull, pull[1:])), pull  # el tiro sube
    assert all(r.converged for r in runs)
mud, rock = HAUL["mud"], HAUL["rock"]
assert rock[0].friction_kgf > 1.5 * mud[0].friction_kgf
last = mud[-1]
glue("ddp", f"{mud[0].door_spread_m - last.door_spread_m:.1f}".replace(".", ","), display=False)
glue("dpull", f"{last.towing_pull_kgf - mud[0].towing_pull_kgf:.0f}", display=False)
glue("clen", f"{last.catch['length_m']:.1f}".replace(".", ","), display=False)
glue("cdiam", f"{last.catch['max_diameter_m']:.2f}".replace(".", ","), display=False)
glue("cdrag", f"{last.catch_drag_kgf:.0f}", display=False)
glue("fric_mud", f"{mud[0].friction_kgf + mud[0].door_friction_kgf:.0f}", display=False)
glue("fric_rock", f"{rock[0].friction_kgf + rock[0].door_friction_kgf:.0f}", display=False)
```

Con 1500 kg de captura (fango, 3 kn) la captura ocupa {glue:text}`clen` m del copo, que se infla
hasta {glue:text}`cdiam` m de diámetro, y agrega {glue:text}`cdrag` kgf de resistencia. Los
portones se cierran {glue:text}`ddp` m y el tiro en el buque sube {glue:text}`dpull` kgf. Es el
comportamiento que midieron {cite:t}`priour2015catch` en 37 lances: la separación de portones baja
y la tensión de las malletas sube a medida que entra la captura. Sobre roca el rozamiento de tren y
portones sin captura es {glue:text}`fric_rock` kgf, frente a {glue:text}`fric_mud` kgf sobre
fango.

La captura también cambia la abertura de las mallas del copo, y con ella la selectividad
{cite:p}`oneill1996kynoch,herrmann2005`; el zoom malla a malla de {doc}`24_malla_selectividad` lo
cuantifica.

## Rozamiento de fondo en el motor empírico

El parámetro `seabed` de `DesignCase` agrega a la demanda del motor el rozamiento del tren
(burlón y lastre en el agua por $\mu$ del tren) y de los dos portones (peso en el agua por $\mu$ de
la zapata). Es una cota simple, con todo el peso apoyado; el simulador acoplado reparte la reacción
con la sustentación de las boyas y los cables y da valores menores.

```{code-cell} ipython3
import dataclasses

for sb in (None, "mud", "rock"):
    r = run(dataclasses.replace(standard_case(), seabed=sb))
    s = r.summary()
    print(f"{sb or 'sin fondo':>9}: rozamiento {s.get('seabed_friction_kgf', 0.0):6.1f} kgf, "
          f"velocidad máxima {s['max_speed_kn']:.2f} kn")
```

## Supuestos y límites

- **Captura**: un fluido que llena el copo desde el extremo cerrado, sin estratificación ni forma
  propia; $C_p$ y las densidades son valores de referencia («A VERIFICAR»). No modela el efecto de
  los peces vivos que nadan ni la captura que se escapa.
- **Fondo**: rozamiento de Coulomb plano, sin penetración ni sedimento movilizado (la huella y la
  penetración llegan en la entrega 11.2). Los coeficientes son estimaciones con rango.
- **Portones**: ángulo de ataque y polar constantes (no se resuelve su cabeceo ni su balanceo);
  la zapata apoya en el fondo y su centro queda a media altura.
- **Cables**: diez barras rectas con peso y Morison (la catenaria sale del equilibrio); el buque es
  un punto fijo.
- **Resistencia**: la brecha del paño frente a DynamiT ({doc}`21_simulacion`) sigue presente; las
  tendencias con la captura y el fondo son relativas al estado sin captura.
- **Costo**: con portones acoplados cada equilibrio cuesta ≈ 2,5 veces más que con portones fijos
  (2–5 s por paso a resolución 4).

```{code-cell} ipython3
:tags: [remove-cell]
print(f"capítulo ejecutado en {time.perf_counter() - T0:.0f} s")
```
