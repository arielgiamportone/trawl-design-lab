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
RIG = {
    "otter": "portones",
    "pair": "pareja",
    "outrigger": "tangones",
    "twin": "gemelo",
    "beam": "vara",
}


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
  de relinga, y (Fases 19.5 y 19.6) redes de tangones y de vara de 7 a 35 m.
- **Validar contra mediciones**: Schärfe (1983) midió la abertura de dos de sus redes en el mar.

## Fuentes y método

Las fuentes y los criterios están en {doc}`catalogo_fuentes`. En resumen:

- **Documentos**: BOBP/WP/10, /13 y /20 {cite}`bobpwp10,bobpwp13,bobpwp20` (arrastres de fondo de
  gran abertura de uno y dos barcos, golfo de Bengala, 1980–82), el *Fisherman's Workbook*
  {cite}`prado1990` y el informe de Schärfe {cite}`scharfe1983` (redes pelágicas de 4 paneles del
  B/I *Dr. Fridtjof Nansen*). Los catálogos clásicos de diseños de la FAO no están en línea.
- **Fase 19.5**: las redes tangoneras de langostino del INIDEP (ITO 043/2022, figs. 4 y 5)
  {cite}`roth2022ito043` y una red de vara para camarón del catálogo tailandés de la SEAFDEC
  (plano 03) {cite}`seafdec2016thai`, con su aparejo (tangones y vara; {doc}`26_aparejos_dobles_y_vara`).
  Las tres quedaron como borrador: sus copos no empalman en largo estirado con el cuerpo, como
  dibujan los planos. En la Fase 19.7c una nueva lectura mostró que en las dos del INIDEP el copo
  se une por la circunferencia (dorso + vientre = copo, 1–2 %) y los costados terminan antes, en
  un cabo de 0,50 m: el validador lo acepta como aviso (`codend_join`) y ambas se publican; la de
  vara sigue como borrador. Sus aberturas salen del método camaronero de la Fase 19.7b.
- **Fase 19.6**: ocho redes más del catálogo de la SEAFDEC, elegidas por aparejo y tamaño de
  buque (datos puntuales, no el catálogo entero): cinco camaroneras con tangón de 75 a 150 hp
  (planos 31, 33, 35, 38 y 39), la red de vara n.º 30 (165 hp) y dos redes de peces con portones
  (planos 21 y 22, de 250 y 365 hp). Cinco cierran y se publican; tres quedan como borrador
  porque el plano une 1/1 (o con una razón corta) paños de malleros muy distintos. Las redes
  camaroneras del golfo de México de la NOAA (Bullis 1951; Gutherz et al. 1974) no se
  digitalizaron: cosen las alas a lo largo del cuerpo, una topología que el motor no arma (ver
  {doc}`catalogo_fuentes`).
- **Fase 19.8c**: cuatro tangoneras de langostino más del INIDEP, de planos vectoriales: la red
  de Luis Solimeno e hijos S.A. (original redibujada por el INIDEP y modificada, IAT 27/2019, figs.
  2 y 3) {cite}`roth2019iat027` y las redes propuesta (2023) y tradicional de Pesquera Deseado
  (IAT 75/2023, figs. 1 y 2) {cite}`roth2023iat075`, con el aparejo, el portón y las aberturas de
  DynamiT de cada informe. La modificada cierra y se publica; las otras tres quedan como borrador
  (ver abajo).
- **Fase 19.9**: cada red del INIDEP lleva el cable de remolque de su fuente
  (`design.warp_diameter_mm`, transcripto): 24 mm con alma de acero en ITO 043/2022 e IAT 75/2023,
  22 mm en IAT 27/2019; un cable elegido en la app manda.
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
- **SEAFDEC (Fase 19.6)**: el validador confirmó cada plano con sus propios rótulos (cortes, razones
  de unión impresas y lima = 2 × ala + bocana). Quedaron dos avisos honestos de lectura: las alas
  del plano 38 se leen 1N2B y el ensanche pide 1N3B, y el cuerpo de 38 mm del plano 39 se lee 2N2B
  y pide 1N2B. En el plano 31 los rótulos de las alas no suman la lima total: se toma el total.
- **INIDEP (Fase 19.8c)**: tres borradores con la razón a la vista. En la red Solimeno original
  (IAT 27/2019, fig. 2) el cuerpo termina en 140 mallas de 80 mm (11,20 m) sobre un copo de 100 de
  60 mm (6,00 m) en cada cara (46 %) y el costado termina en una malla, sin cabo de cierre: es el
  «exceso de material en la parte final del cuerpo» que el propio informe señala y corrige en la
  red modificada (75 mallas: 6,00 m), que se publica. En las dos redes de IAT 75/2023 el borde de
  bolsa del vientre se lee «26» (2,08 m en la fig. 1, 1,56 m en la fig. 2) sobre un copo de 70
  mallas de 60 mm (4,20 m); el corte 1N4B del paño daría 46 y 66 mallas, con las que cerraría:
  falta verificarlo con el autor (A VERIFICAR). Además, en las cuatro los hilos no están
  publicados (salvo el «Ny Tr 4 mm» del copo de la fig. 2 de IAT 27 y los Ø3 y Ø1,9 mm de la red
  propuesta de IAT 75): el Rtex y el diámetro del resto son supuestos; el sector de malla cuadrada
  de la red propuesta de IAT 75 no está dimensionado en el plano y no se modela; el corte exterior
  del ala del vientre de la red tradicional se deriva (no está rotulado). La red propuesta se
  modela con los dos flotadores de 200 mm que recomienda el informe (la flotación de la red no está
  publicada) y con ellos el simulador ({doc}`21_simulacion`) no converge a 2,5 nudos: queda fuera de la
  prueba de simulación del catálogo hasta revisarla.
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

Con ese caso, el motor y el simulador dan, a 3 kn (el simulador, sólo en las redes publicadas; en
los borradores queda «—»):

```{code-cell} ipython3
:tags: [remove-input]
RES = {}
for i in IDS:
    r = run(catalog_case(i).case)
    # El simulador corre sólo en las redes publicadas (tiempo de compilación del libro).
    sim = (
        simulate(r, 3.0, resolution=2, coarse_resolution=None) if i in PUBLISHED else None
    )
    RES[i] = (r, sim)
rows = []
ratio = []
for i in IDS:
    r, sim = RES[i]
    s = r.summary()
    if sim is not None and SPECS[i].family == "bottom":
        ratio.append(s["rn_std_3kn_kgf"] / sim.drag_kgf)
    rows.append([
        i,
        num(s["headrope_m"]),
        num(s["horizontal_opening_m"]),
        "—" if sim is None else num(sim.ah_m),
        num(s["vertical_opening_m"]),
        "—" if sim is None else num(sim.av_m),
        num(s["rn_std_3kn_kgf"], 0),
        "—" if sim is None else num(sim.drag_kgf, 0),
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
| Alas de los costados no modeladas | redes de Schärfe y del INIDEP | — |
| Costados repartidos por largo estirado | redes del INIDEP | `trawlkit.topology` |
| Buque y portón de la red tangonera | `design.vessel_id`; portón de 4,08 m² (IAT 75/2023) y 540 kg (ITO 043); 2,86 × 1,43 m supuestos, alto ≤ 1,50 m (Res. CFP 7/2018, art. 4) | Elegir un buque o un portón en la app |
| Profundidad de las redes de langostino: 90 m | `catalog.LANGOSTINO_DEPTH_M`, `design.depth_m` | `depth_m` del caso |
| Unión al copo por la circunferencia | redes del INIDEP (`aft_rope_m`) | — |
| Hilos de las redes de IAT 27/2019 y de la red tradicional de IAT 75/2023 | Ø y Rtex de los hilos de ITO 043/2022 escalados con d² (A VERIFICAR) | — |
| Costados repartidos por largo con hasta 30 % de diferencia | `topology.SIDE_LENGTH_TOL` (red tradicional de IAT 75/2023: 25 %) | — |

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
