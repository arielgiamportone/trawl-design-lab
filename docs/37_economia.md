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

# Economía de la operación

```{code-cell} ipython3
:tags: [remove-cell]
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.cwd().parent))
sys.path.insert(0, str(pathlib.Path.cwd()))

import matplotlib.pyplot as plt
from IPython.display import Markdown
import _plots_v as PV
from myst_nb import glue
from trawlkit.api import service
from trawlkit.economics import EconomicInputs, compare, economics


def num(x: float, nd: int = 0) -> str:
    return f"{x:,.{nd}f}".replace(",", " ").replace(".", ",")


# Valores ILUSTRATIVOS para mostrar el cálculo: no son precios reales de ningún puerto.
EJ = EconomicInputs(
    currency="ARS",
    fuel_price_l=1200.0,
    lube_price_l=6000.0,
    catch_kg_h=150.0,
    price_kg=1000.0,
    crew_share=0.4,
    gear_cost=3_000_000.0,
    trip_costs=150_000.0,
    annual_costs=6_000_000.0,
)
CASE = service.build_case()
R = economics(CASE, EJ)
B = R.best
```

## Propósito

Una red no se elige sólo porque el buque la pueda remolcar: se elige porque la marea deja
plata. Este capítulo describe `trawlkit.economics` (Fase 16), que suma al cálculo de la red la
economía de la operación: cuánto gasoil se quema, cuánto se pesca, cuánto cuesta la marea y
cuánto queda, a cada velocidad de arrastre. Con eso responde tres preguntas: **a qué velocidad
conviene arrastrar**, **qué red conviene** para un buque y **en cuánto tiempo se paga** una red
nueva.

La app no trae precios: los carga el usuario, en su moneda. Sin un dato, ese rubro queda fuera
del cálculo y se avisa; no se reemplaza por un valor inventado. Los números de este capítulo
usan **valores ilustrativos** (gasoil a 1 200 ARS/L, langostilla a 1 000 ARS/kg, 150 kg por hora
de arrastre a 3 kn, 40 % para la tripulación) sólo para mostrar el cálculo.

## Gasoil

Durante el lance, la potencia al freno que pide la red es

$$
P = \frac{R_T(v)\, v}{\eta},
$$

con $R_T(v)$ la resistencia total del motor de cálculo ({doc}`19_ventana_velocidad`) y $\eta$
un rendimiento de remolque (tiro × velocidad sobre potencia al freno) de 0,5 por defecto (A
VERIFICAR; incluye hélice, reductor y pérdidas). La potencia se recorta a la del buque. En la
navegación al caladero se usa una fracción de la potencia del motor (0,8 por defecto) y en el
calado y virado otra (0,2). El combustible es $P \cdot \text{SFC} / \rho$, con un consumo
específico de 0,22 kg/kWh y gasoil de 0,84 kg/L, y el lubricante una proporción del gasoil
{cite}`parker2015`. Todas estas constantes se pueden cambiar.

## Captura e ingreso

La captura por hora de arrastre que carga el usuario vale a una velocidad de referencia (3 kn
por defecto). A otra velocidad, la red barre otra área por hora, $A_H \cdot v$, y la captura se
escala en proporción:

$$
C(v) = C_\text{ref}\;\frac{A_H(v)\, v}{A_H(v_\text{ref})\, v_\text{ref}}.
$$

Es una hipótesis simple: no tiene en cuenta el escape de los peces a baja velocidad ni el arreo
de los portones y las bridas, que dependen de la especie. El ingreso es la captura por el precio
en playa, o por el promedio ponderado de varias especies.

## Costos de la marea

| Rubro | Cómo se calcula |
|---|---|
| Combustible y lubricante | Gasoil del arrastre, la navegación y las maniobras, por su precio; lubricante en proporción. |
| Tripulación | «A la parte»: un porcentaje del ingreso después de descontar gasoil, lubricante y gastos de la marea (o del ingreso bruto); o un jornal por día por tripulante. |
| Red y aparejo | El costo del armado (cargado o de la lista de materiales, {doc}`34_componentes`) dividido por su vida útil en horas de arrastre, más una reparación anual como fracción del costo. |
| Gastos de la marea | Hielo, víveres, carnada y puerto. |
| Fijos anuales | Permisos, seguro y otros, divididos por las mareas del año. |

El **margen** es el ingreso menos el costo; el **costo por kg**, el costo sobre la captura; y el
**precio de equilibrio**, el precio de la captura que deja margen cero. Como la parte de la
tripulación depende del ingreso, el margen es lineal en el precio y el equilibrio sale directo:
con la parte después de los gastos compartidos $G$ y los costos que no dependen del precio $F$,

$$
p^* = \frac{F - c\,G}{(1 - c)\,C},
$$

con $c$ la parte de la tripulación y $C$ la captura de la marea.

## A qué velocidad conviene arrastrar

```{code-cell} ipython3
:tags: [remove-input]
fig, ax = plt.subplots(figsize=(7.2, 4.0))
v = [t.speed_kn for t in R.trips]
ax.plot(v, [t.revenue / 1e3 for t in R.trips], color="#1baf7a", label="Ingreso")
ax.plot(v, [t.total_cost / 1e3 for t in R.trips], color="#eb6834", label="Costo")
ax.plot(v, [t.margin / 1e3 for t in R.trips], color="#2a78d6", lw=2.5, label="Margen")
ok = [t.speed_kn for t in R.trips if t.feasible]
ax.axvspan(min(ok), max(ok), color="#1baf7a", alpha=0.12, label="el buque remolca con reserva")
ax.axvline(R.best_margin_kn, color="#52514e", lw=1, ls="--")
ax.set_xlabel("Velocidad de arrastre [kn]")
ax.set_ylabel("Por marea [miles de ARS]")
ax.grid(alpha=0.3)
ax.legend(fontsize=8, frameon=False)
fig.tight_layout()
plt.show()
glue("best_v", Markdown(num(R.best_margin_kn, 2)), display=False)
glue("best_margin", Markdown(num(B.margin)), display=False)
glue("best_ckg", Markdown(num(B.cost_per_kg, 0)), display=False)
glue("best_fuel", Markdown(num(B.fuel_l)), display=False)
glue("best_be", Markdown(num(B.breakeven_price, 0)), display=False)
glue("year_margin", Markdown(num(R.year["margin"] / 1e6, 1)), display=False)
```

Con estos valores, el ingreso y el costo crecen con la velocidad y el margen también: más
velocidad es más área barrida y más captura. Pero la A-3 en su buque de 150 hp sólo tiene tiro
con reserva hasta poco más de 2 kn ({doc}`30_caso_beagle`). La mejor velocidad **posible** es
{glue:md}`best_v` kn: {glue:md}`best_fuel` L de gasoil por marea, un costo de
{glue:md}`best_ckg` ARS por kg, un margen de {glue:md}`best_margin` ARS por marea
({glue:md}`year_margin` millones por año) y un precio de equilibrio de {glue:md}`best_be` ARS/kg.
La economía confirma lo que mostraba el optimizador ({doc}`20_optimizacion`): este buque
aprovecharía mejor una red más chica, que pueda remolcar más rápido.

## Qué red conviene

```{code-cell} ipython3
:tags: [remove-input]
rows = compare(
    [
        ("FAO A-3", CASE, None),
        ("Workbook 2 paneles", service.build_case("fao_wb_bt2p_60hp", vessel="fao_a3_150hp"), 2_000_000.0),
        ("BOBP/WP/20, un barco", service.build_case("bobp_wp20_ho", vessel="fao_a3_150hp"), 2_500_000.0),
    ],
    EJ,
)
PV.md_table(
    ["Red (buque de 150 hp)", "v [kn]", "Gasoil por año [L]", "Margen por año [ARS]", "Ahorro por año", "Repago"],
    [
        [
            r.label,
            num(r.trip.speed_kn, 2) if r.trip else "—",
            num(r.annual_fuel_l) if r.annual_fuel_l is not None else "—",
            num(r.annual_margin) if r.annual_margin is not None else "—",
            num(r.savings_year) if r.savings_year is not None else "—",
            (f"{num(r.payback_years * 12, 1)} meses" if r.payback_years is not None else "—"),
        ]
        for r in rows
    ],
)
```

La comparación usa el mismo buque, el mismo portón y los mismos datos de operación; cada red
trabaja a su velocidad de mayor margen. La captura por hora cargada vale para la primera red a
la velocidad de referencia; las otras pescan en proporción a su área barrida por hora (una red
más chica barre menos y pesca menos). El **ahorro** es la diferencia de margen por año frente
a la primera y el **repago**, el costo de la red nueva sobre ese ahorro. Es la cuenta que hace un
armador antes de cambiar la red: con estos números ilustrativos, una red que el buque puede
arrastrar más rápido se paga en pocas semanas o meses. Con los precios reales del puerto el resultado puede
cambiar, y por eso la app no trae precios propios.

## Dónde se usa

- **Web**: pestaña «Economía» del modo experto (datos de la operación, mejor velocidad, curva de
  ingreso, costo y margen, tabla por velocidad, reparto del costo y comparación con otra red del
  catálogo) y, en el modo guiado, «¿Cuánto deja la marea?» en el resultado ({doc}`web`).
- **Lotes**: con «Sumar la economía de la marea», cada buque de la flota suma gasoil, captura,
  costo por kg y margen por marea y por año ({doc}`35_lotes_proyeccion`).
- **Sin conexión**: la economía corre en el motor del teléfono.
- **CLI**: `trawlkit economics fao_a3_standard --fuel-price 1200 --catch-kg-h 150 --price-kg 1000`
  o `--inputs datos.yaml`.
- **API**: `POST /economics` y `/economics/compare` ({doc}`api`).

## Supuestos y límites

- La captura escala con el área barrida; no se modela el escape ni el arreo, ni la variación de
  la abundancia en el caladero.
- El consumo usa un rendimiento de remolque y un consumo específico constantes; un motor viejo o
  una hélice mal adaptada consumen más.
- La velocidad «posible» es la que deja tiro con reserva y un cable que aguanta; las demás
  restricciones del optimizador (apertura de la red, portón) se avisan pero no la descartan.
- Los costos sin dato quedan fuera del total: el resultado es incompleto y se avisa.

## Ejercicios

Del banco del modo docente, con los datos del libro. Con la CLI (`trawlkit exercises`) se generan
con otros datos y se corrigen.

```{code-cell} ipython3
:tags: [remove-input]
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path.cwd()))
import _exercises
_exercises.section("37_economia")
```
