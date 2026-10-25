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

# Flotas, lotes y proyección de redes

```{code-cell} ipython3
:tags: [remove-cell]
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.cwd().parent))
sys.path.insert(0, str(pathlib.Path.cwd()))

import matplotlib.pyplot as plt
from IPython.display import Markdown
import _plots_v as PV
from myst_nb import glue
from trawlkit.batch import fleet_vessel, project_net, read_input, run_input, template
from trawlkit.batch.project import ProjectOptions


def num(x: float, nd: int = 2) -> str:
    return f"{x:,.{nd}f}".replace(",", " ").replace(".", ",")


FLEET = [("Chico", 40), ("Costero", 60), ("Mediano", 100), ("Bolichero", 150), ("Grande", 220),
         ("Altura", 300)]
FAST = ProjectOptions(assemble=False)
PROJ = {
    net: [project_net(net, fleet_vessel({"name": n, "bhp": hp}), FAST) for n, hp in FLEET]
    for net in ("fao_wb_bt2p_60hp", "fao_a3_standard")
}
```

## Propósito

Una cooperativa, una escuela de pesca o un técnico de un puerto rara vez diseña una red para un
solo buque: tiene la **flota** del puerto, las redes que ya usa y muchas preguntas parecidas.
¿Qué tamaño de red le corresponde a cada buque? ¿A qué velocidad? ¿Con qué portón, cable y
boyas? Este capítulo describe la carga masiva de planillas, el **cálculo por lotes** y la
**proyección de una red probada a otros buques** (Fase 14).

## La proyección: semejanza y refinado

**Semejanza.** Si se agranda una red conservando el mallero, el hilo y el armado, todas sus
medidas lineales crecen con la escala $s$ y la superficie de paño con $s^2$. La resistencia de
la red es, a igual velocidad, proporcional a esa superficie, y el tiro que el buque puede dar es
proporcional a su potencia {cite}`prado1990`. Para que un buque de potencia $P$ remolque la red
como la remolca el buque para el que fue diseñada (potencia $P_d$) hay que conservar la razón
entre resistencia y tiro:

$$
s^2 \propto \frac{P}{P_d} \quad\Longrightarrow\quad s_0 = \sqrt{\frac{P}{P_d}}.
$$

El portón se escala con la misma regla (superficie proporcional a la potencia), la que ya usa el
catálogo de redes del capítulo 33 cuando el plano no da el portón, y la separación de portones
sale de la DPA de Fridman: la regla «al metro» del libro (Port!E13) está calibrada para la A-3 y
su cable, y con una red más chica daría una separación imposible.

**Refinado.** La semejanza es aproximada: el cable, los portones, las boyas y el lastre no
escalan igual, y la apertura depende de la velocidad. Por eso `trawlkit.batch.project_net`
toma $s_0$ como punto de partida y busca, con el evaluador del optimizador del capítulo 20, la
**mayor escala** entre $0{,}7\,s_0$ y $1{,}3\,s_0$ que cumple las restricciones de siempre
(tiro con 10 % de reserva, red abierta, cable y portón) a la velocidad que da el buque o, si no
la da, a alguna entre 2 y 4 nudos. Una bisección afina la escala. Después, el armado con el
catálogo de componentes del capítulo 34 elige portón, cable, boyas e hilo para la red ya
escalada.

## Ejemplo: una flota de seis buques

```{code-cell} ipython3
:tags: [remove-input]
rows = []
for net, label in (("fao_wb_bt2p_60hp", "Workbook 60 hp"), ("fao_a3_standard", "FAO A-3")):
    for p in PROJ[net]:
        s = p.summary()
        rows.append(
            [
                label,
                s["vessel"],
                f"{s['bhp']:g}",
                num(s["s0"], 3),
                num(s["s"], 3),
                num(s["speed_kn"], 2),
                num(s["headrope_m"], 1),
                num(s["demand_kgf"], 0),
                "sí" if s["feasible"] else "no",
            ]
        )
PV.md_table(
    ["Red base", "Buque", "hp", "s₀", "s", "v [kn]", "Lima [m]", "R_T [kgf]", "Cumple"], rows
)
ratios = [p.s / p.s0 for net in PROJ for p in PROJ[net]]
glue("ratio_lo", Markdown(num(min(ratios), 2)), display=False)
glue("ratio_hi", Markdown(num(max(ratios), 2)), display=False)
a3 = next(p for p in PROJ["fao_a3_standard"] if p.vessel.vessel.bhp == 150)
glue("a3_s", Markdown(num(a3.s, 2)), display=False)
```

La escala final sigue a la de semejanza: la razón $s/s_0$ queda entre {glue:md}`ratio_lo` y
{glue:md}`ratio_hi` para los doce casos, de 40 a 300 hp, es decir, la ley $s \propto \sqrt{P}$
describe bien el comportamiento del motor y el refinado sólo corrige el nivel. Que la razón sea
algo menor que 1 dice que, con la reserva de tiro del 10 % y la separación de portones de
Fridman, el motor encuentra las redes de diseño un poco grandes para su buque: la A-3 con su
buque de 150 hp queda en {glue:md}`a3_s`.

```{code-cell} ipython3
:tags: [remove-input]
fig, ax = plt.subplots(figsize=(7.2, 4.2))
for net, label, color in (
    ("fao_wb_bt2p_60hp", "Workbook (diseño 60 hp)", "#1c5cab"),
    ("fao_a3_standard", "FAO A-3 (diseño 150 hp)", "#c35a1b"),
):
    hp = [p.vessel.vessel.bhp for p in PROJ[net]]
    ax.plot(hp, [p.s for p in PROJ[net]], "o-", color=color, label=f"{label}: escala final")
    ax.plot(hp, [p.s0 for p in PROJ[net]], "--", color=color, alpha=0.6,
            label=f"{label}: semejanza s₀")
ax.set_xlabel("Potencia del buque [hp]")
ax.set_ylabel("Escala de la red s")
ax.grid(alpha=0.3)
ax.legend(fontsize=8, frameon=False)
fig.tight_layout()
plt.show()
```

## Planillas: flota, redes y casos

`trawlkit.batch` lee **CSV** y **XLSX**:

- **Flota**: un buque por fila, con nombre, potencia (hp o kW), eslora, manga, puntal, hélice,
  profundidad, velocidad, región del puerto, fondo y «sólo genéricos». Las medidas que faltan se
  escalan del buque de la A-3, y se avisa.
- **Redes**: una hoja de paneles (mallero, hilo, mallas de boca, bolsa y alto, U1, cantidad,
  corte) y una hoja «red» opcional (relingas, boyas, potencia de diseño, profundidad). Cada red
  pasa por el validador del capítulo 33; con errores queda como borrador. La A-3 exportada a
  planilla y releída da exactamente el mismo resultado.
- **Casos**: cada fila es un caso completo (red, buque, portón, modo) y cualquier parámetro de
  `GET /params` puede ser una columna.

Los nombres de columna se aceptan en español o inglés, sin importar acentos ni mayúsculas, con la
unidad como sufijo o entre paréntesis (`Potencia (kW)`, `eslora_ft`); los números aceptan coma
decimal. Un error en una fila (un valor que no es número, una opción desconocida) se informa con
su fila y su columna y **no detiene el lote**. Las plantillas traen ejemplos y una hoja de ayuda
con cada columna, su unidad y su rango habitual:

```{code-cell} ipython3
:tags: [remove-input]
inp = read_input(template("fleet", "xlsx"), "flota.xlsx", "fleet")
res = run_input(inp, net="fao_wb_bt2p_60hp", options=FAST)
PV.md_table(
    ["Buque", "hp", "s", "v [kn]", "Cumple"],
    [
        [r.name, f"{r.summary['bhp']:g}", num(r.summary["s"], 3), num(r.summary["speed_kn"], 2),
         "sí" if r.status == "ok" else "no"]
        for r in res.rows
    ],
)
```

## Dónde se usa

- **Web**: pestaña «Lotes y flota» (descarga de plantillas, carga, vista previa editable, cálculo
  por tramos con avance, tabla con semáforos y filtro, «Abrir este caso», descarga en XLSX, CSV,
  PDF o vista para imprimir) y, en el modo guiado, «¿Tiene varios buques?» en el paso del buque.
- **Sin conexión**: el motor del teléfono (capítulo 34) también calcula lotes y escribe XLSX
  (openpyxl viaja con el motor); el PDF necesita el servidor y, sin red, se imprime la vista HTML.
- **CLI**: `trawlkit batch flota.xlsx --net fao_wb_bt2p_60hp -o lote.xlsx` (o `.csv`, `.json`,
  `.pdf`) y `trawlkit batch --template plantilla.xlsx`.
- **API**: `POST /batch/parse`, `/batch/run`, `/batch/export` y `GET /batch/template`
  ({doc}`api`), con la guarda de costo `TRAWLKIT_MAX_BATCH_SECONDS`.

## Supuestos y límites

- La semejanza supone redes geométricamente semejantes: mismo mallero e hilo. Para un buque
  mucho más chico o más grande que el de diseño (s fuera de 0,5–2) conviene revisar el mallero, el
  hilo y el armado, que el escalado no cambia.
- El rango de búsqueda es $0{,}7$–$1{,}3\,s_0$: si el resultado toca el tope, la ficha lo avisa
  (el buque podría con una red mayor).
- Sin velocidad en la planilla se busca entre 2 y 4 nudos; a menos velocidad cualquier red
  «entra», pero no pesca.
- Con el motor del teléfono los lotes se parten en tramos de 10 buques para no congelarlo.
