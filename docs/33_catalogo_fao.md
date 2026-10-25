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

# Catálogo de redes FAO

```{code-cell} ipython3
:tags: [remove-cell]
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.cwd().parent))
sys.path.insert(0, str(pathlib.Path.cwd()))

import numpy as np
import _plots_v as PV
from myst_nb import glue
from trawlkit.catalog import catalog_case
from trawlkit.io.loader import NETS_DIR, load_net
from trawlkit.model import run
from trawlkit.netcheck import check
from trawlkit.provenance import coverage
from trawlkit.sim import simulate
from trawlkit.topology import has_sides

IDS = sorted(p.stem for p in NETS_DIR.glob("*.yaml"))
SPECS = {i: load_net(i) for i in IDS}
FAMILY = {"bottom": "fondo", "semi_pelagic": "semipelágica", "pelagic": "pelágica"}
RIG = {"otter": "portones", "pair": "pareja"}


def num(x: float, nd: int = 1) -> str:
    return f"{x:.{nd}f}".replace(".", ",")


def hp(spec) -> str:
    lo, hi = spec.vessel_hp
    return f"{lo:g}" if lo == hi else f"{lo:g}–{hi:g}"


PUBLISHED = [i for i in IDS if SPECS[i].status == "published"]
DRAFTS = [i for i in IDS if SPECS[i].status == "draft"]
glue("n_nets", len(IDS), display=False)
glue("n_pub", len(PUBLISHED), display=False)
glue("n_draft", len(DRAFTS), display=False)
glue("n_values", sum(coverage(SPECS[i])["values"] for i in IDS), display=False)
```

## Propósito

El motor nació para la red FAO A-3 del libro Excel. Este capítulo reúne un **catálogo de redes
públicas** digitalizadas de documentos de la FAO, cada una con la **procedencia de cada valor**, y
las calcula con el motor y el simulador generalizados (Fase 12). El catálogo tiene
{glue:text}`n_nets` redes ({glue:text}`n_pub` publicadas y {glue:text}`n_draft` borradores) y
{glue:text}`n_values` valores con fuente.

Sirve para tres cosas:

- **Diseñar a partir de una red probada**: cada red trae el buque, el portón y la profundidad
  para los que se ensayó, y la app la calcula con ese caso.
- **Probar el motor fuera de la A-3**: redes de pareja, de 4 paneles y pelágicas, de 20 a 113 m
  de relinga.
- **Validar contra mediciones**: Schärfe (1983) midió la abertura de dos de sus redes en el mar.

## Fuentes y método

Las fuentes y los criterios están en {doc}`catalogo_fuentes`. En resumen:

- **Documentos**: BOBP/WP/10, /13 y /20 {cite}`bobpwp10,bobpwp13,bobpwp20` (arrastres de fondo de
  gran abertura de uno y dos barcos, golfo de Bengala, 1980–82), el *Fisherman's Workbook*
  {cite}`prado1990` y el informe de Schärfe {cite}`scharfe1983` (redes pelágicas de 4 paneles del
  B/I *Dr. Fridtjof Nansen*). Los catálogos clásicos de diseños de la FAO no están en línea.
- **Lectura**: cada figura se rasterizó a 300 ppp (o se tomó la imagen embebida del PDF) y se
  leyó número por número. Ninguna figura se guarda en el repositorio (© FAO): sólo los datos.
- **Procedencia por valor**: cada número es *transcripto* (leído en la figura), *derivado*
  (calculado de lo leído: el diámetro del hilo de su Rtex, U1 de la bocana) o *supuesto* (lo que
  el plano no da), con la página, la figura y una nota.
- **Validador** (`trawlkit.netcheck`): empalmes entre paños, bocana, cortes contra mallas,
  costuras laterales y, en las redes de 4 paneles, costados por estaciones. Una red que no cierra
  queda como **borrador**: a la vista, pero fuera del modo guiado.

```{code-cell} ipython3
:tags: [remove-input]
rows = []
for i in IDS:
    s = SPECS[i]
    issues = check(s)
    err = sum(x.level == "error" for x in issues)
    warn = len(issues) - err
    cov = coverage(s)["by_kind"]
    total = sum(cov.values())
    sup = 100 * cov.get("assumed", 0) / total
    rows.append([
        s.name.split(" (")[0] + (" — borrador" if s.status == "draft" else ""),
        FAMILY[s.family] + (", 4 paneles" if has_sides(s) else ""),
        RIG[s.rig],
        hp(s),
        len(s.panels),
        f"{num(sup, 0)} %",
        f"{err} / {warn}",
        s.sources[0].key,
    ])
PV.md_table(
    ["Red", "Familia", "Aparejo", "hp", "Paños", "Supuestos", "Errores / avisos", "Fuente"],
    rows,
)
```

## Lo que encontró el validador

El validador se escribió para atrapar errores de lectura, y los atrapó:

- **Arrastre de pareja de 464 × 80 mm (BOBP/WP/13)**: el vientre «F» se había leído con 60 filas.
  Con 60 filas el corte 1N2B no da el cambio de 232 a 152 mallas, y el vientre no llega a la
  estación de 203 mallas con el largo del dorso. Con **80 filas** cierran las dos cosas: la cifra
  borrosa era un 8. El ala inferior «D» pasa de 50 a 93 mallas en 127 filas: sólo **1N4B**
  (con el otro costado en malletas) da ese ensanche, y es el corte del ala inferior del
  *Workbook*.
- Queda un aviso honesto: el ala superior «C» de esa red pide un corte de ≈ 0,42 y el plano dice
  1N2B (0,5). Se conserva lo leído con la nota.
- Los **fruncidos** de los planos: varias redes cosen un paño de malla grande con uno de malla
  chica sin igualar el largo estirado (hasta 18 % en Schärfe, 13–14 % en BOBP/WP/10). No son
  errores de lectura, porque el mismo número aparece en el dorso y en el vientre y el corte de
  cada paño cierra con sus mallas. El validador los informa como avisos (umbral de error: 20 %).
- Los **borradores**: la red Harstad cose 260 mallas de 190 mm con 260 de 140 mm (26 %), que puede
  ser un fruncido extremo o un mallero mal leído. La red de krill con frente de 1600 mm no deja
  leer el alto del ala del vientre, y la de pescado y camarón de BOBP/WP/20 está escaneada a
  107 ppp. Las tres quedan para revisar con el original.
- La red pelágica de 4 paneles del *Workbook* (figura de 450 px) **no se digitalizó**. El cuerpo
  se lee y cierra (24 × 800 = 48 × 400, 42 × 400 = 84 × 200…), pero el frente de 800 mm no se
  lee lo suficiente para armar una red sin inventar números.

## Cada red con su caso de diseño

`trawlkit.catalog.catalog_case` arma el caso de cada red:

- **Buque genérico** con la potencia media del ensayo, escalado del buque de 150 hp de la A-3.
- **Portón del plano** (largo × alto con la polar del portón plano), o ninguno en la pareja.
- **Profundidad** del documento.
- **Separación de portones** por la DPA de Fridman ({doc}`16_aberturas`), porque la regla «al
  metro» del libro sólo vale para las pastecas de la A-3.

Con ese caso, el motor y el simulador dan, a 3 kn:

```{code-cell} ipython3
:tags: [remove-input]
RES = {}
for i in IDS:
    r = run(catalog_case(i).case)
    sim = simulate(r, 3.0, resolution=2, coarse_resolution=None)
    RES[i] = (r, sim)
rows = []
ratio = []
for i in IDS:
    r, sim = RES[i]
    s = r.summary()
    if SPECS[i].family == "bottom":
        ratio.append(s["rn_std_3kn_kgf"] / sim.drag_kgf)
    rows.append([
        i,
        num(s["headrope_m"]),
        num(s["horizontal_opening_m"]),
        num(sim.ah_m),
        num(s["vertical_opening_m"]),
        num(sim.av_m),
        num(s["rn_std_3kn_kgf"], 0),
        num(sim.drag_kgf, 0),
    ])
PV.md_table(
    [
        "Red",
        "Lima [m]",
        "AH motor",
        "AH sim.",
        "AV motor",
        "AV sim.",
        "R motor [kgf]",
        "R sim. [kgf]",
    ],
    rows,
)
glue("ratio_lo", num(min(ratio), 1), display=False)
glue("ratio_hi", num(max(ratio), 1), display=False)
glue("ratio_med", num(float(np.median(ratio)), 1), display=False)
```

Las redes de fondo tienen, todas, el mismo patrón:

- **Abertura horizontal**: el motor y el simulador quedan cerca en la mayoría de las redes.
- **Resistencia**: el motor da entre {glue:text}`ratio_lo` y {glue:text}`ratio_hi` veces la del
  simulador (mediana {glue:text}`ratio_med`). La resistencia del motor es el promedio de los
  métodos empíricos del libro ({doc}`14_resistencia`), ajustados a redes de fondo de la A-3, y
  la del simulador sólo cuenta el paño y las relingas (sin portones).
- **Abertura vertical**: es la que más difiere. El simulador abre poco el dorso de estas redes
  con la flotación del plano, mientras que el motor usa reglas empíricas de proporción.

Ninguno de los dos se midió en el mar para estas redes: los documentos BOBP informan capturas,
no aberturas. Por eso la diferencia queda como dato y no se ajusta.

## Las redes pelágicas contra lo medido

Schärfe midió con sonda de red la abertura de la red de krill con los dos frentes agrandados.
Esas mediciones están en la propia red (`measured`) y se comparan con el motor y con el
simulador en las mismas condiciones:

```{code-cell} ipython3
:tags: [remove-input]
rows = []
for i in IDS:
    for m in SPECS[i].model_extra.get("measured", []):
        cc = catalog_case(i)
        r = run(cc.case)
        sim = simulate(r, m["speed_kn"], resolution=2, coarse_resolution=None)
        rows.append([
            i,
            num(m["speed_kn"]),
            num(m["warp_m"], 0),
            f"{num(m['height_m'], 0)} × {num(m['width_m'], 0)}",
            f"{num(r.summary()['vertical_opening_m'], 0)} × "
            f"{num(r.summary()['horizontal_opening_m'], 0)}",
            f"{num(sim.av_m, 0)} × {num(sim.ah_m, 0)}",
        ])
PV.md_table(
    ["Red", "v [kn]", "Cable [m]", "Medido alto × ancho [m]", "Motor", "Simulador"],
    rows,
)
```

Las diferencias son grandes, y tienen tres causas conocidas:

- **Aparejo**: Schärfe usó malletas de 100 m y pesos delanteros de 230 a 520 kg en las malletas
  inferiores. El caso del catálogo calcula las malletas con la regla del libro (pensada para redes
  de fondo) y pone el lastre en el burlón. Así el simulador estira la red hacia abajo y la cierra
  a lo ancho.
- **Red equivalente de 2 paneles**: el motor y el simulador suman los costados al dorso y al
  vientre ({doc}`21_simulacion`). Eso conserva la circunferencia, pero deja que la boca se
  deforme sin las costuras de los costados, que en una red de 4 paneles la mantienen cuadrada.
- **Velocidad y cable**: el motor no usa la velocidad ni el largo del cable para la abertura.

La conclusión es que **el catálogo no cambia lo que se sabe del motor**: está hecho para redes de
fondo de 2 paneles. Para las pelágicas de 4 paneles, el catálogo deja las mediciones y las redes
listas para un simulador de 4 caras con malletas y pesos delanteros reales, como mejora futura.

## Supuestos

| Supuesto | Dónde | Cómo cambiarlo |
|---|---|---|
| Puntas de ala de la pareja a ½ lima | `pair_wing_spread_m` | Parámetro del caso |
| Separación de portones de Fridman | `door_spread_rule` | `"excel"` para la regla del libro |
| Red de 4 paneles = 2 paneles equivalentes | `trawlkit.topology` | — (simulador de 4 caras: futuro) |
| Buque genérico escalado de la A-3 | `catalog.generic_vessel` | Elegir un buque en la app |
| Alas de los costados no modeladas | redes de Schärfe | — |

## Usar el catálogo

- **En la app** (modo experto), la pestaña «Catálogo FAO» filtra por familia, aparejo, fuente y
  potencia. Muestra la procedencia valor por valor y los avisos del validador, y «Usar esta red»
  la calcula con su caso.
- **En el modo guiado**, el paso «Red» ofrece las redes adecuadas a la potencia del buque elegido
  (±25 % del rango de ensayo).
- **Desde la API**:
  - `GET /catalog/nets` da el resumen filtrable;
  - `/catalog/nets/{id}/provenance` y `/catalog/nets/{id}/check` dan la procedencia y el
    validador;
  - `POST /design` con una red del catálogo y sin buque usa el caso del catálogo.
- **Desde la línea de comandos**: `trawlkit run bobp_wp13_pair_ho80`.
