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

# Mar real y condiciones en funcionamiento

```{code-cell} ipython3
:tags: [remove-cell]
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path.cwd().parent))
sys.path.insert(0, str(pathlib.Path.cwd()))

import _plots_t2 as P
from myst_nb import glue
from trawlkit.model import run
from trawlkit.sim import Scenario, explore, fouling_catalogue, simulate
from trawlkit.sim.core import DIESEL_KG_L, SFC_KG_KWH, TOWING_EFFICIENCY
from trawlkit.sim.scenario import fouling_coefficients
from trawlkit.sim.validation import standard_case

P.setup()
T0 = time.perf_counter()
R = run(standard_case())
RES = 3
BASE = Scenario(seabed="mixed")
```

## Propósito

{doc}`22_simulacion_realista` agregó la captura, el tipo de fondo y los portones acoplados. Este
capítulo suma otras condiciones que cambian el funcionamiento del arte en el mar: el
**ensuciamiento** de la red (algas, medusas, organismos adheridos), la **corriente** a lo largo
del rumbo y el **largo de cable** filado. También agrega dos salidas para evaluar una
condición de pesca: la **energía** (potencia de remolque y combustible) y la **huella** sobre el
fondo.

Todo se recorre con `trawlkit.sim.explore`: una serie de equilibrios en la que cambia una sola
variable, con arranque en caliente y la misma malla. Como todos los estados comparten los nodos,
la forma se puede **animar** interpolando entre ellos; es lo que hace el «Explorador animado» de
la aplicación ({doc}`web`).

## Ensuciamiento y colmatación

Cada zona de la red (alas, cuerpo, copo) tiene un nivel de ensuciamiento $f \in [0, 1]$. El
catálogo `data/fouling.yaml` define escenarios típicos y el nivel cambia cada hilo:

$$
d_\text{ef} = d\,(1 + g_d f), \qquad C_{N,\text{ef}} = C_N\,(1 + g_c f), \qquad
w_\text{ef} = w\,(1 + g_w f).
$$ (eq-23-fouling)

```{code-cell} ipython3
:tags: [remove-input]
import _plots_v as PV

g = fouling_coefficients()
glue("gd", f"{g['diameter_gain']:.1f}".replace(".", ","), display=False)
glue("gc", f"{g['cn_gain']:.1f}".replace(".", ","), display=False)
glue("gw", f"{g['weight_gain']:.1f}".replace(".", ","), display=False)
PV.md_table(
    ["Escenario", "Alas", "Cuerpo", "Copo"],
    [
        [f.name, *(f"{f.zones[z]:.1f}".replace(".", ",") for z in ("wings", "body", "codend"))]
        for f in fouling_catalogue()
    ],
)
```

Ganancias usadas («A VERIFICAR»): $g_d$ = {glue:text}`gd`, $g_c$ = {glue:text}`gc` y
$g_w$ = {glue:text}`gw`.

Las ganancias se estimaron a partir de la literatura de redes de acuicultura. Con un
ensuciamiento importante, la solidez de un paño puede duplicarse y su arrastre crecer dos o tres
veces {cite:p}`swift2006`. La simulación de jaulas ensuciadas a escala real muestra el mismo
orden {cite:p}`bi2015`. Para artes de arrastre no hay mediciones publicadas: en el lance, algas o
medusas tapan zonas puntuales del paño, y por eso los escenarios son por zona.

```{code-cell} ipython3
:tags: [remove-cell]
FOUL = explore(R, "fouling_level", [0.0, 0.5, 1.0],
               scenario=Scenario(seabed="mixed", fouling="general"), resolution=RES)
pull = [r.towing_pull_kgf for r in FOUL]
dp = [r.door_spread_m for r in FOUL]
assert pull[0] < pull[1] < pull[2] and dp[0] > dp[2]
glue("foul_pull", f"{(pull[2] / pull[0] - 1) * 100:.0f}", display=False)
glue("foul_dp", f"{dp[0] - dp[2]:.1f}".replace(".", ","), display=False)
```

Con el escenario «ensuciamiento general» al nivel completo, el tiro en el buque sube
{glue:text}`foul_pull` % y los portones se cierran {glue:text}`foul_dp` m: el paño frena más y la
red tira de los portones hacia adentro.

## Corriente

Con una corriente $c$ a lo largo del rumbo (positiva a favor), el agua pasa por la red a
$v_\text{agua} = v_\text{fondo} - c$. La red, los portones y las boyas responden a
$v_\text{agua}$. El área barrida y la producción dependen, en cambio, de $v_\text{fondo}$. La
corriente cruzada rompe la simetría respecto del eje del arte y queda fuera de este modelo.

```{code-cell} ipython3
:tags: [remove-cell]
against = simulate(R, 3.0, resolution=RES, scenario=Scenario(seabed="mixed", current_kn=-0.5))
faster = simulate(R, 3.5, resolution=RES, scenario=BASE)
calm = simulate(R, 3.0, resolution=RES, scenario=BASE)
assert abs(against.towing_pull_kgf / faster.towing_pull_kgf - 1) < 0.02
assert against.operation["swept_area_km2_h"] < faster.operation["swept_area_km2_h"]
glue("cur_pull", f"{(against.towing_pull_kgf / calm.towing_pull_kgf - 1) * 100:.0f}", display=False)
glue("cur_fuel", f"{(against.operation['fuel_l_h'] / calm.operation['fuel_l_h'] - 1) * 100:.0f}",
     display=False)
```

Arrastrar a 3 kn sobre el fondo con 0,5 kn de corriente en contra equivale, para la red, a
arrastrar a 3,5 kn en agua quieta: el tiro sube {glue:text}`cur_pull` % y el combustible
{glue:text}`cur_fuel` %, pero el área barrida por hora es la misma que a 3 kn.

## Largo de cable

```{code-cell} ipython3
:tags: [remove-input]
WARP = explore(R, "warp_length_m", [120.0, 160.0, 200.0, 250.0, 300.0], scenario=BASE,
               resolution=RES)
lengths = [r.operation["warp_length_m"] for r in WARP]
fig, axes = P.plt.subplots(1, 3, figsize=(10.2, 3.4))
P.line(axes[0], lengths, [r.door_spread_m for r in WARP], 1, "")
P.line(axes[1], lengths, [r.operation["warp_angle_deg"] for r in WARP], 1, "")
P.line(axes[2], lengths, [r.operation["contact_width_m"] for r in WARP], 1, "")
for ax, title in zip(axes, ("Separación de portones [m]", "Ángulo del cable [°]",
                            "Ancho en contacto con el fondo [m]"), strict=True):
    ax.set_title(title)
    ax.set_xlabel("Cable filado [m] (profundidad 40 m)")
P.finish(fig)
```

```{code-cell} ipython3
:tags: [remove-cell]
dps = [r.door_spread_m for r in WARP]
angles = [r.operation["warp_angle_deg"] for r in WARP]
assert all(a < b for a, b in zip(dps, dps[1:])) and all(a > b for a, b in zip(angles, angles[1:]))
glue("short_contact", f"{WARP[0].operation['contact_width_m']:.1f}".replace(".", ","), display=False)
glue("long_contact", f"{WARP[-1].operation['contact_width_m']:.1f}".replace(".", ","), display=False)
```

A 40 m de profundidad, al alargar el cable de 120 a 300 m los portones se abren y el cable llega
más tendido. Con 120 m (relación 3:1) el tren de fondo se despega en parte: el ancho en contacto
con el fondo cae a {glue:text}`short_contact` m, frente a {glue:text}`long_contact` m con 300 m.
Es la razón práctica de las tablas de relación cable/profundidad de {doc}`18_cables`.

## Energía

La potencia de remolque y el consumo de combustible se estiman como

$$
P = \frac{T\,v_\text{agua}}{\eta}, \qquad
Q = \frac{P \cdot \text{SFC}}{\rho_\text{gasoil}} ,
$$ (eq-23-energy)

donde $T$ es el tiro en el buque, $\eta$ el rendimiento de remolque (hélice y transmisión) y SFC
el consumo específico del motor. La potencia se recorta a la del buque; si la demanda la supera,
el resultado lo indica (`power_limited`). Con la duración del lance y la captura se obtienen los
litros por kg; con el área barrida, los litros por km². Son estimaciones de orden de magnitud: no
incluyen la resistencia del casco ni la carga de los equipos.

```{code-cell} ipython3
:tags: [remove-cell]
glue("eta", f"{TOWING_EFFICIENCY:.1f}".replace(".", ","), display=False)
glue("sfc", f"{SFC_KG_KWH:.2f}".replace(".", ","), display=False)
glue("rho", f"{DIESEL_KG_L:.2f}".replace(".", ","), display=False)
SPEED = explore(R, "speed_kn", [2.0, 2.5, 3.0, 3.5], scenario=Scenario(seabed="mixed", catch_kg=600),
                resolution=RES)
fuel = [r.operation["fuel_l_h"] for r in SPEED]
assert all(a < b for a, b in zip(fuel, fuel[1:]))
per_km2 = [r.operation["fuel_l_per_km2"] for r in SPEED]
glue("km2_lo", f"{min(per_km2):.0f}", display=False)
glue("km2_hi", f"{max(per_km2):.0f}", display=False)
```

Valores usados («A VERIFICAR»): $\eta$ = {glue:text}`eta`, SFC = {glue:text}`sfc` kg/kWh y
$\rho_\text{gasoil}$ = {glue:text}`rho` kg/L. La mediana mundial que informan
{cite:t}`parker2015` para las flotas de arrastre de fondo sirve de referencia para el orden de
magnitud. Entre 2 y 3,5 kn, el combustible por km² barrido de la red FAO A-3 va de
{glue:text}`km2_lo` a {glue:text}`km2_hi` L/km²: arrastrar más rápido barre más área por hora,
pero cada km² cuesta más combustible.

## Huella sobre el fondo

Siguiendo la metodología de BENTHIS {cite:p}`eigaard2016`:

- el **ancho barrido** es la separación de portones;
- el **ancho en contacto** es el burlón apoyado más las zapatas de los dos portones;
- las **áreas por hora** se calculan con la velocidad sobre el fondo;
- la **penetración** sale del tipo de fondo del catálogo.

El sedimento movilizado crece con el arrastre de los elementos en contacto
{cite:p}`oneill2011,oneill2016`. Todavía no se cuantifica porque sus coeficientes dependen del
sedimento y del elemento.

## Supuestos y límites

- **Ensuciamiento**: es un modelo por zona con ganancias estimadas; no modela la colmatación
  progresiva durante el lance. El efecto de la forma de las mallas sobre la selectividad está en
  {doc}`24_malla_selectividad`.
- **Corriente**: sólo a lo largo del rumbo. La corriente cruzada y las maniobras requieren el
  modelo asimétrico y dinámico.
- **Energía**: $\eta$ y SFC constantes; sin resistencia del casco ni consumo auxiliar.
- **Huella**: los anchos en contacto son geométricos; no hay penetración ni sedimento cuantificados.
- **Animación**: interpola posiciones entre equilibrios cuasiestáticos. No es una simulación
  dinámica en el tiempo: muestra cómo cambia el estado de equilibrio, no la transición física
  entre estados.

```{code-cell} ipython3
:tags: [remove-cell]
print(f"capítulo ejecutado en {time.perf_counter() - T0:.0f} s")
```

## Ejercicios

Del banco del modo docente, con los datos del libro. Con la CLI (`trawlkit exercises`) se generan
con otros datos y se corrigen.

```{code-cell} ipython3
:tags: [remove-input]
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path.cwd()))
import _exercises
_exercises.section("23_mar_real")
```
