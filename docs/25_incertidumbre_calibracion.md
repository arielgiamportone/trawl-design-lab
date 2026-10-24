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

# Incertidumbre, calibración y datos de sensores

```{code-cell} ipython3
:tags: [remove-cell]
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
from trawlkit.sensors import example_log, parse_log, to_observations, windows
from trawlkit.sim import Scenario
from trawlkit.sim.calibration import PARAMETERS, calibrate, dynamit_observations
from trawlkit.sim.uncertainty import default_inputs, uncertainty
from trawlkit.sim.validation import standard_case

P.setup()
T0 = time.perf_counter()
R = run(standard_case())
RES = 3


def num(x: float, nd: int = 1) -> str:
    return f"{x:.{nd}f}".replace(".", ",")
```

## Propósito

Los capítulos {doc}`21_simulacion` a {doc}`24_malla_selectividad` dan un valor por resultado: una
separación de portones, un tiro, una L50. Pero varios datos del simulador no se conocen con
precisión, y con ellos cada resultado tiene una **banda** de valores posibles. Este capítulo:

- propaga esa incertidumbre con Monte Carlo y dice **qué dato pesa más** en cada resultado;
- **calibra** el simulador contra mediciones: la simulación DynamiT de la red FAO A-3 o un
  registro de sensores del lance;
- lee **registros de sensores** en CSV de cualquier equipo y los resume en tramos estacionarios.

Ningún simulador comercial de redes reporta bandas de incertidumbre ni se calibra contra los
datos del propio barco ({doc}`22_simulacion_realista`). Son el paso que lleva al simulador de la
forma teórica a la red que trabaja en el mar.

## Fuentes de incertidumbre

```{code-cell} ipython3
:tags: [remove-input]
SC = Scenario(seabed="mixed", catch_kg=500)
INPUTS = default_inputs(SC)
PV.md_table(
    ["Dato", "Nominal", "Rango", "Fuente"],
    [
        [i.label, num(i.nominal, 3), f"{num(i.low, 3)} – {num(i.high, 3)} {i.unit}".strip(), i.source]
        for i in INPUTS
    ],
)
```

Para un lance con 500 kg de captura sobre fondo mixto, los datos inciertos y sus rangos son los
de la tabla. Los coeficientes del hilo salen de la literatura {cite:p}`takagi2004,lee2005`. Los
rozamientos usan el rango del tipo de fondo del catálogo ({doc}`22_simulacion_realista`). La
polar del portón se varía ±10 % y la captura según {cite:t}`oneill1997codend`. Los rangos marcados
«A VERIFICAR» son estimaciones.

## Monte Carlo con hipercubo latino

Cada dato se toma uniforme en su rango. Con $n$ muestras, el **hipercubo latino**
{cite:p}`mckay1979` divide cada rango en $n$ estratos y pone una muestra en cada estrato de cada
dato, con los estratos permutados al azar entre datos. Así pocas muestras cubren el espacio mejor
que un muestreo al azar. Cada muestra se simula partiendo de la forma nominal, lo que abarata
cada una.

De las salidas se informan los percentiles P10, P50 y P90: el 80 % de las muestras cae entre P10
y P90. El peso de cada dato se mide con la **correlación de rangos de Spearman** entre el dato y
la salida, $\rho_s \in [-1, 1]$ {cite:p}`saltelli2008`. Con pocas muestras es una medida
orientativa, no una descomposición de la varianza.

```{code-cell} ipython3
:tags: [remove-cell]
U = uncertainty(R, 3.0, scenario=SC, n=16, resolution=RES, species=["hake_hubbsi"])
UD = U.to_dict()
OUT = {o["key"]: o for o in UD["outputs"]}
for o in UD["outputs"]:
    assert o["p10"] <= o["p50"] <= o["p90"]
assert U.converged.all()


def top(key: str) -> str:
    s = OUT[key]["sensitivity"]
    return max(s, key=lambda k: abs(s[k]))


LABELS = {i.name: i.label for i in U.inputs}
S_DP = OUT["door_spread_m"]["sensitivity"]
S_PULL = OUT["towing_pull_kgf"]["sensitivity"]
# Signos físicos: la sustentación del portón abre los portones y el arrastre del paño los cierra;
# el roce del hilo (C_T) sube el tiro.
assert S_DP["door_cl_factor"] > 0 and S_DP["cn"] + S_DP["ct"] < 0
assert S_PULL["ct"] > 0
glue("rho_cl", num(S_DP["door_cl_factor"], 2), display=False)
glue("rho_net", num(S_DP["cn"] + S_DP["ct"], 2), display=False)
dp = OUT["door_spread_m"]
glue("dp_p10", num(dp["p10"]), display=False)
glue("dp_p90", num(dp["p90"]), display=False)
glue("dp_top", LABELS[top("door_spread_m")], display=False)
glue("pull_top", LABELS[top("towing_pull_kgf")], display=False)
glue("n_unc", str(UD["n"]), display=False)
```

```{code-cell} ipython3
:tags: [remove-input]
digits = {"kgf": 0, "L/h": 1, "cm": 1}
PV.md_table(
    ["Resultado", "Nominal", "P10", "P50", "P90"],
    [
        [
            f"{o['label']} [{o['unit']}]",
            "—" if o["nominal"] is None else num(o["nominal"], digits.get(o["unit"], 2)),
            *(num(o[k], digits.get(o["unit"], 2)) for k in ("p10", "p50", "p90")),
        ]
        for o in UD["outputs"]
    ],
)
```

```{code-cell} ipython3
:tags: [remove-input]
fig, axes = P.plt.subplots(1, 2, figsize=(10.2, 3.8), sharey=True)
names = [i.name for i in U.inputs]
ypos = np.arange(len(names))
for ax, key in zip(axes, ("door_spread_m", "towing_pull_kgf"), strict=True):
    rho = [OUT[key]["sensitivity"][n] for n in names]
    ax.barh(ypos, rho, color=[P.color(0) if r >= 0 else P.color(1) for r in rho])
    ax.axvline(0, color="0.5", lw=0.8)
    ax.set_xlim(-1, 1)
    ax.set_title(f"ρ de Spearman con {OUT[key]['label'].lower()}")
axes[0].set_yticks(ypos, [LABELS[n] for n in names])
axes[0].invert_yaxis()
P.finish(fig)
```

Con {glue:text}`n_unc` muestras a 3 kn, la separación de portones queda entre
{glue:text}`dp_p10` y {glue:text}`dp_p90` m (P10–P90). El dato de mayor peso en esta corrida es
«{glue:text}`dp_top`». La sustentación del portón la abre ($\rho_s$ = {glue:text}`rho_cl`), y la
resistencia del paño la cierra (suma de C_N y C_T: {glue:text}`rho_net`). La red tira de los
portones hacia adentro. El tiro en el buque depende más de «{glue:text}`pull_top`». Para reducir
la incertidumbre de un resultado conviene medir primero los datos que más pesan en él. Para la
apertura del aparejo, esos datos son la polar real del portón en el mar y la resistencia del paño.

## Calibración

Calibrar es ajustar algunos parámetros inciertos $\boldsymbol\theta$ para que la simulación
reproduzca mediciones $y_k$ (separación de portones, aberturas, tiro, tensión del cable a una
velocidad y con una captura dadas). Se minimiza la suma de los errores relativos al cuadrado:

$$
\min_{\boldsymbol\theta \in [\boldsymbol\theta_{\min}, \boldsymbol\theta_{\max}]}
\sum_k \left[ w_k \left( \frac{s_k(\boldsymbol\theta)}{y_k} - 1 \right) \right]^2 .
$$ (eq-25-ls)

Los errores relativos permiten mezclar magnitudes de distinta unidad. El método es
Levenberg–Marquardt {cite:p}`levenberg1944,marquardt1963`. El jacobiano se calcula por
diferencias finitas y los parámetros se proyectan sobre sus rangos físicos. Cada evaluación
simula los estados observados partiendo de la última forma de cada uno. El desvío de cada
parámetro sale de $(J^\mathsf{T} J)^{-1}$ y es sólo orientativo.

```{code-cell} ipython3
:tags: [remove-input]
PV.md_table(
    ["Parámetro", "Rango"],
    [[lab, f"{num(lo, 2)} – {num(hi, 2)}"] for lab, lo, hi in PARAMETERS.values()],
)
```

### Contra DynamiT

```{code-cell} ipython3
:tags: [remove-cell]
CD = calibrate(
    R,
    dynamit_observations(),
    ["cn", "door_cl_factor"],
    scenario=Scenario(seabed="mixed"),
    resolution=RES,
    max_evals=24,
)
assert CD.rmse_after < CD.rmse_before
glue("dyn_before", num(CD.rmse_before), display=False)
glue("dyn_after", num(CD.rmse_after), display=False)
glue("dyn_cn", num(CD.fitted[0], 2), display=False)
glue("dyn_cl", num(CD.fitted[1], 2), display=False)
glue("cn_max", num(PARAMETERS["cn"][2], 1), display=False)
```

```{code-cell} ipython3
:tags: [remove-input]
PV.md_table(
    ["Magnitud", "v [kn]", "DynamiT", "Antes", "Después"],
    [
        [
            o.quantity.replace("_", " "),
            num(o.speed_kn, 0),
            num(o.value, 1),
            f"{num(CD.before[k], 1)} ({num(100 * (CD.before[k] / o.value - 1), 0)} %)",
            f"{num(CD.after[k], 1)} ({num(100 * (CD.after[k] / o.value - 1), 0)} %)",
        ]
        for k, o in enumerate(CD.observations)
    ],
)
```

Se calibraron C_N del hilo y la sustentación del portón contra separación de portones, aberturas
y resistencia de DynamiT a 2, 3 y 4 kn. El error cuadrático medio relativo baja de
{glue:text}`dyn_before` % a {glue:text}`dyn_after` %. C_N termina en {glue:text}`dyn_cn`, el
límite de su rango ({glue:text}`cn_max`), y el factor del portón en {glue:text}`dyn_cl`. Que un
parámetro quede en el límite es la señal útil del ejercicio: con coeficientes físicos el modelo
no alcanza la resistencia de DynamiT. La diferencia es estructural (nudos, relingas,
flujo dentro de la red), como se vio en {doc}`32_validacion_dynamit`. Calibrar no la corrige:
la muestra.

### Contra un registro de sensores

```{code-cell} ipython3
:tags: [remove-cell]
LOG = parse_log(example_log())
WS = windows(LOG, by="time", width=20)
OBS = to_observations(WS)
CS = calibrate(R, OBS, ["door_cl_factor"], scenario=Scenario(seabed="mixed"), resolution=RES, max_evals=12)
assert abs(CS.fitted[0] - 0.9) < 0.03 and CS.rmse_after < CS.rmse_before
glue("log_rows", str(LOG.rows), display=False)
glue("log_fit", num(CS.fitted[0], 3), display=False)
glue("log_before", num(CS.rmse_before), display=False)
glue("log_after", num(CS.rmse_after), display=False)
```

El paquete trae un registro **sintético** (`data/examples/sensor_log.csv`) generado con el
simulador. La sustentación del portón es el 90 % de la del catálogo, y se agrega ruido de
medición. Tiene {glue:text}`log_rows` filas cada 10 s en tres tramos de velocidad, con la captura
creciendo. Calibrando el factor de sustentación contra esas mediciones se obtiene
{glue:text}`log_fit` (el valor oculto es 0,90). El error baja de {glue:text}`log_before` % a
{glue:text}`log_after` %. Con un registro real, ese factor mide cuánto rinde el portón en el agua
frente a su polar de catálogo.

## Registros de sensores

```{code-cell} ipython3
:tags: [remove-input]
PV.md_table(
    ["Velocidad [kn]", "Captura [kg]", "Filas", "Separación de portones [m]", "Altura de la relinga [m]", "Tensión del cable [kgf]"],
    [
        [
            num(w.speed_kn, 2),
            num(w.catch_kg, 0),
            str(w.n),
            num(w.values["door_spread_m"], 1),
            num(w.values["headrope_height_m"], 2),
            num(w.values["warp_tension_kgf"], 0),
        ]
        for w in WS
    ],
)
```

`trawlkit.sensors` lee el CSV que exportan los sensores del arte: separación de portones, altura
de la relinga, tensiómetros y GPS. No hace falta un formato fijo:

- el separador puede ser coma, punto y coma o tabulador, y con punto y coma se acepta la coma
  decimal;
- las columnas se reconocen por su nombre, en español o en inglés (`Velocidad`, `SOG`,
  `Separacion portones`, `door_spread`, `Altura relinga`, `headline_height`, `Tension babor`…);
- la unidad va entre paréntesis o como sufijo (`(m/s)`, `[t]`, `_kN`, `(fm)`) y se convierte;
- las tensiones de babor y estribor se promedian;
- las líneas que empiezan con `#` son comentarios.

Las filas se agrupan en **tramos estacionarios**, por tiempo o por velocidad, y cada tramo se
resume con la mediana. La tabla muestra los tramos del registro de ejemplo. Cada tramo da una
observación por magnitud, que es la entrada de la calibración. En la aplicación, la vista
«Incertidumbre y calibración» hace todo el recorrido en el navegador ({doc}`web`).

## Supuestos y límites

- **Incertidumbre**:
  - entradas uniformes e independientes, en los rangos de la tabla;
  - no se incluyen la incertidumbre de la geometría de la red (cortes, armado) ni la del
    modelo (forma de los elementos, nudos);
  - con 10–20 muestras los percentiles extremos son aproximados.
- **Sensibilidad**: la correlación de rangos capta efectos monótonos. No separa interacciones
  entre datos (para eso harían falta índices de Sobol y muchas más muestras
  {cite:p}`saltelli2008`).
- **Calibración**:
  - mínimos locales posibles;
  - parámetros correlacionados (por ejemplo, C_N y el arrastre del portón frente al tiro)
    pueden compensarse entre sí. Conviene calibrar pocos parámetros y con magnitudes que los
    separen: la separación de portones para la sustentación y la tensión para el arrastre.
- **Registros**:
  - se supone régimen estacionario dentro de cada tramo y la misma red y aparejo en todo el
    lance;
  - las curvas y los virajes deben filtrarse antes.

```{code-cell} ipython3
:tags: [remove-cell]
print(f"capítulo ejecutado en {time.perf_counter() - T0:.0f} s")
```
