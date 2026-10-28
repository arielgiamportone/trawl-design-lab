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

# Componentes: catálogos, equivalencias y costo

```{code-cell} ipython3
:tags: [remove-cell]
import dataclasses
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.cwd().parent))
sys.path.insert(0, str(pathlib.Path.cwd()))

import _plots_v as PV
from myst_nb import glue
from trawlkit import components as comp
from trawlkit.catalog import catalog_case
from trawlkit.cost import bill_of_materials
from trawlkit.io import load_net
from trawlkit.model import run
from trawlkit.optimize import optimise_components


def num(x: float, nd: int = 1) -> str:
    return f"{x:,.{nd}f}".replace(",", " ").replace(".", ",")


ITEMS = {k: comp.load_components(k) for k in comp.KINDS}
N_ITEMS = sum(len(v) for v in ITEMS.values())
BRANDS = sorted({i.brand for v in ITEMS.values() for i in v if i.brand})
glue("n_items", N_ITEMS, display=False)
glue("n_brands", len(BRANDS), display=False)
```

## Propósito

Una red no se arma sólo con el plano: hacen falta paño, cables, cabos, portones, boyas, cadenas y
grilletes, y lo que se consigue en cada puerto cambia. Este capítulo describe el **catálogo de componentes**
(Fase 13): {glue:}`n_items` ítems de {glue:}`n_brands` marcas y de equivalentes **genéricos**, con
la fuente de cada valor; cómo el motor los usa para dimensionar; cómo se arma la **lista de
materiales** con su costo orientativo; y cómo el optimizador **elige el armado** entre lo que hay.
La herramienta apunta a pescadores con pocos recursos: los genéricos se consiguen en cualquier
ferretería naval, los precios los carga el usuario y la app calcula **sin conexión** en el teléfono.

## Fuentes y equivalencias genéricas

Casi ningún fabricante publica tablas abiertas, y menos de tamaños chicos. Por eso cada tipo
tiene una **familia genérica** derivada de las tablas del *Fisherman's Workbook* de la FAO
{cite}`prado1990`, y las marcas son **datos puntuales** citados, nunca tablas completas (a lo sumo
diez medidas por línea de producto; los portones de fabricante, en cambio, llevan todos los
tamaños publicados de cada línea desde la Fase 19.8a, porque la elección de portón necesita la
serie completa):

* **Paño e hilo**: diámetro y rotura por Rtex para PA torcido y trenzado, PES, PP y PE, con un
  ajuste potencial $y = a\,x^b$ en escala logarítmica sobre las tablas del *Workbook*; Garware
  (India) para el PE trenzado {cite}`garware_fisheries`; Hampidjan (Islandia) para el PE trenzado
  Magnet, el Dyneema/HMPE Advant y Primanet y el nylon torcido Utzon {cite}`hampidjan_catalogue`.
* **Cables de acero**: peso y carga de rotura con $y = k\,d^2$ sobre las tablas 6x7, 6x12, 6x19 y
  6x24 del *Workbook*; Bridon-Bekaert {cite}`bridon2023` (Marblue, Dyform Starfish, Dyform,
  SeaBeam y 6x7) y PFEIFER {cite}`pfeifer_6x19w` como fabricantes, y los cables de Randers Reb y
  Oliveira (6xK26 compactados y 6x19 Green Strand) del catálogo de Hampidjan.
* **Cabos**: PA, PE, PES, PP y combinados de acero y fibra; Garware X2, Maxima, PP, PE y Maxibraid;
  Hampidjan Nylex, Kraft (Polysteel), Danline, DynIce 75 y Prima (burlón de HMPE), y el cabo
  combinado de cerco de Randers Reb.
* **Portones**: superficie y peso por potencia del *Workbook* para portones planos, ovales, en V y
  Süberkrüb, con la polar medida de su tipo (Fase 19.3, {doc}`15_portones_aparejo`): las hojas de
  Seafish/IFREMER/DIFTA {cite}`sfia1993` para el plano, el oval y la media de los tres en V, y el
  Thyborøn 15 VF de {cite}`mellibovsky2018` para el Süberkrüb; cuatro puertas de la flota
  camaronera del Caribe colombiano {cite}`zuniga2006`; Vónin Storm 2, Tornado y Twister
  (superficie y peso de los 14, 15 y 8 tamaños publicados, {cite}`vonin_doors`; cuatro del
  Tornado, de 1, 2, 14 y 15 m², de la tabla que reprodujo {cite:t}`fishfocus2019_tornado`) y
  Morgère OvalFoil, PolyFoil y PFPE (superficie de los 21, 19 y 17 modelos del catálogo; peso
  «sur demande», {cite}`morgere2025`), con la polar del tipo como supuesta. Desde la Fase 20.1,
  los portones grandes: 25 hojas de Thyborøn {cite}`thyboron_trawldoor` (645 tamaños de 0,82 a
  21,34 m², de fondo, semipelágicos y pelágicos), las 5 tablas distintas de los folletos de Polar
  {cite}`polardoors` (180 tamaños de 1 a 20 m²) y las tres de Poly-Ice {cite}`polyice_doors`
  (41 tamaños hasta 14,2 m², con medidas).
* **Boyas y cadenas**: flotación y profundidad máxima por diámetro, peso por metro por eslabón;
  boyas de arrastre de Atlantic Floats y cadenas de eslabón largo Trygg y Trawlex (catálogo de
  Hampidjan) y Gunnebo LLZ de grado 6 galvanizada {cite}`gunnebo_llz`.
* **Grilletes** (tipo nuevo de la Fase 19.2): tamaño, carga de trabajo (WLL), rotura mínima, peso
  de una pieza y diámetros del cuerpo y del perno; Crosby G-209 {cite}`crosby_g209` y Green Pin de
  Van Beest (catálogo de Hampidjan). No hay tabla de referencia de grilletes en el *Workbook*: es el
  único tipo sin genéricos.

El catálogo de Hampidjan es un visor de páginas sin PDF y su capa de texto desordena columnas: cada
fila se leyó en la imagen de la página, no en el texto. Donde la ficha no da un dato que el motor
necesita, el ítem lo dice: el paño torcido de Garware (380 D, 500 D, Sapphire torcido y nylon
210 D) no trae diámetro, así que se cargó como **borrador** con el diámetro estimado por el ajuste
del *Workbook* y la nota «A VERIFICAR»; los borradores no entran en la selección automática.

### Portones grandes (Fase 20.1)

Hasta la Fase 19.9 el portón más grande del catálogo era el Vónin Storm 2 de 16 m², y los cinco
buques de la flota de 2100 hp o más no tenían candidato. Ninguna tabla pública de fabricante pasa
de **21,34 m²** (Thyborøn Type 2 Iceland de 200", 6800 kg); Thyborøn dice que construye hasta
25 m² y 8000 kg, sin publicar esas filas. Cada hoja distinta se carga entera; las hojas que repiten
la tabla de otra (Type 20 y 21 Slider, Type 22 VF/VFB, Type 32, Type 42 hidráulico, Type 23 VK,
Type 26, Type 28 en V, los 15 folletos de Polar que repiten una de las 5 tablas) se cargan una sola
vez, y cada ítem lo dice en sus notas. Los pesos siguen la hoja: con columnas mínimo–máximo
(Thyborøn) o «desde–hasta» (Polar, Poly-Ice) se toma el **valor medio**, como en los genéricos del
*Workbook*, con el rango en la nota y procedencia *derivada*; el Type 2 lleva el peso NORMAL (el
HEAVY, en la nota); los Xstream, el mínimo publicado; los Bluestream, el «Standard weight»; y el
Type 23 Iceland, sin peso («as requested»). Las medidas son las impresas («LxH/mm»), salvo tres
filas con erratas evidentes (Type 16 de 1 m², Type 21 de 6 y 8 m²) y los portones de alta relación
de aspecto cuya hoja imprime primero el lado mayor (Types 23 y 42, Poly-Ice de media agua), donde
el lado mayor se toma como alto (*supuesto*). Sin medidas, las proporciones salen de una hoja de
polar del tipo (la del Thyborøn Type 2 de 125" de Seafish para el Type 2) o del número «r» de
Polar, tomado como relación de aspecto. La polar es siempre la del tipo, *supuesta*.

Con este catálogo eligen portón todos los buques de hasta 2600 hp, incluidos el Holmberg, el Oca
Balda y el congelador de 2348 hp. El Angelescu (2855 hp) y el congelador de 4159 hp siguen sin
candidato: la regla del libro les pide 31,5 y 45,9 m² de portón plano por portón, más que cualquier
tabla. Esos números están muy lejos de la práctica: el Angelescu se diseñó con portones Morgère
SPF08 de 4,5 m² y 1200 kg {cite}`roth2017angelescu`, y la única tabla pública indexada por
potencia, la de los Fishbuster de Net Systems {cite}`netsystems_fishbuster`, pone 7 m²
para 1800–2200 hp y de 11 a 12,5 m² para 3000–5500 hp. La regla (superficie = 20 % del tiro disponible sobre $C_D\,v^2$, promediada
entre 2 y 4 nudos) está calibrada para los 150–180 hp de la A-3 y crece en proporción a la
potencia, mientras que las tablas del *Workbook* y de Fishbuster crecen como la potencia a la
0,65. La regla no se cambia en esta fase: el diagnóstico y la corrección propuesta quedan para una
fase posterior, porque tocan los valores dorados del libro.

```{code-cell} ipython3
:tags: [remove-input]
rows = []
for k in comp.KINDS:
    s = comp.summary(ITEMS[k])
    rows.append([comp.KIND_LABEL[k], s["items"], s["generic"], ", ".join(s["brands"]) or "—"])
PV.md_table(["Tipo", "Ítems", "Genéricos", "Marcas"], rows)
```

Cada ítem lleva su **procedencia por valor** (transcripto, derivado, supuesto o del libro Excel),
como las redes del capítulo anterior, y apunta a su **genérico equivalente**: el de la misma
construcción y la medida genérica más cercana (la tabla del *Workbook* no tiene todas las
medidas, y el genérico puede romper más o menos que el de marca). La tabla compara cables de marca
con su genérico:

```{code-cell} ipython3
:tags: [remove-input]
rows = []
for item in ITEMS["wire"]:
    if item.brand != "Bridon-Bekaert" or item.diameter_mm not in (14, 16, 18):
        continue
    g = comp.generic_for(item)
    if g is None or g.id == item.id:
        continue
    rows.append(
        [
            f"{item.diameter_mm:g} mm",
            f"{item.name}",
            num(item.weight_kg_per_m, 3),
            num(item.breaking_load_t, 1),
            g.name,
            num(g.weight_kg_per_m, 3),
            num(g.breaking_load_t, 1),
        ]
    )
PV.md_table(
    ["Ø", "De marca", "kg/m", "Rotura [t]", "Genérico", "kg/m", "Rotura [t]"], rows[:6]
)
```

### Alargamiento y rigidez axial

Hampidjan publica el **alargamiento de rotura** de cada paño y cabo (no la rigidez); Garware,
Bridon-Bekaert y los cables no lo publican. Donde está, el catálogo lo guarda (`elongation_pct`) y
deriva la rigidez axial secante $EA \approx R / \varepsilon$ (`ea_kn`, procedencia «derivada»,
`trawlkit.materials.ea_from_breaking_load_n`), que el motor usa por encima de las relaciones
genéricas de la tabla de materiales. En el paño de Hampidjan la ficha da sólo la rotura **con
nudo**, así que no se deriva EA. La secante es una cota inferior de la rigidez a la carga de
trabajo:

```{code-cell} ipython3
:tags: [remove-input]
rows = []
for rid in (
    "hampidjan_nylex_16mm",
    "hampidjan_danline_16mm",
    "hampidjan_dynice_75_duracoat_16mm",
    "hampidjan_prima_foot_rope_51mm",
):
    r = comp.get_component("rope", rid)
    rows.append(
        [r.name, num(r.breaking_load_t, 1), num(r.elongation_pct, 1), num(r.ea_kn, 0)]
    )
PV.md_table(["Cabo", "Rotura [t]", "Alargamiento de rotura [%]", "EA [kN]"], rows)
```

## Validación física

Un componente cargado a mano puede traer un error de unidades o de tipeo. El validador
(`trawlkit.components.check`) compara cada valor con rangos físicos del material: peso por metro
contra $k\,d^2$ (acero, fibra, cadena), rotura contra la del material, tenacidad del hilo en gf/tex,
flotación contra el volumen de la boya, peso del portón por m² y, en los grilletes, peso por mm³ del
cuerpo, carga de trabajo por mm², rotura contra carga de trabajo (factor de diseño 4:1 a 8:1; una
rotura menor que la carga de trabajo es un error) y perno contra cuerpo. Los avisos señalan valores
fuera de las tablas de referencia, no errores: los cabos modernos de PP/PE (Polysteel, Danline) y de
nylon trenzado rompen y se alargan más que los de las tablas del *Workbook*. Por ejemplo, un cable de 10 mm
cargado con 2 kg/m y 50 t:

```{code-cell} ipython3
:tags: [remove-input]
bad = comp.parse_component(
    {
        "kind": "wire",
        "id": "user_wire",
        "name": "aporte",
        "status": "user",
        "construction": "6x19",
        "diameter_mm": 10,
        "weight_kg_per_m": 2.0,
        "breaking_load_t": 50,
    }
)
PV.md_table(["Nivel", "Código", "Observación"], [[i.level, i.code, i.message] for i in comp.check(bad)])
```

## El motor con componentes

`DesignCase` acepta un componente del catálogo por id para el cable (`warp_id`), las boyas
(`float_id`), el hilo de todos los paños salvo el copo (`twine_id`) y la cadena (`chain_id`); los
cabos de relinga y el portón ya se elegían por id. Sin esos campos, la selección automática usa los
catálogos del libro Excel y **el resultado de la A-3 no cambia** (las pruebas doradas lo verifican);
con los filtros `component_brands`, `component_region` o `generic_only`, la selección automática
busca en el catálogo de componentes filtrado. Con una boya elegida, el número de boyas sale de la
flotación requerida (Flot!F72:F82); con un hilo, el peso y la resistencia del paño se recalculan con
su diámetro.

**Cabos de relinga del catálogo** (Fase 19.2). Con esos filtros, la lima y el burlón también salen
del catálogo filtrado, salvo que el caso elija un cabo (`headrope_rope`, `footrope_rope`). El libro
no trae una regla; el cabo de la red (o el del libro) queda como referencia y se elige, entre los
cabos **del mismo material** (un combinado se reemplaza por otro combinado, que es el que pone el
peso de la relinga), el de **menor diámetro con diámetro y rotura no menores** que los de la
referencia; si ninguno alcanza, el de mayor rotura
(`trawlkit.rigging.select_rope_component`).

**Cadena de lastre del catálogo** (`chain_id`). La etapa de lastre pasa a metros el lastre mínimo,
el máximo y la cadena de reglaje del libro (Flot!F225:F226, H224) con el peso por metro de la
cadena, y da el peso en el agua de esos metros, $W_\text{agua} = L\,w\,(1 - \rho_\text{mar}/
\rho_\text{acero})$. El lastre en kg no cambia: la cadena sólo lo traduce. Con la A-3 y sus
filtros:

```{code-cell} ipython3
:tags: [remove-input]
from trawlkit.io import load_doors, load_vessels
from trawlkit.model import DesignCase

_v = {v.id: v for v in load_vessels().vessels}
a3 = DesignCase(load_net("fao_a3_standard"), _v["fao_a3_150hp"], load_doors().doors[0])
rows = []
for label, kw in (
    ("Libro (sin filtros)", {}),
    ("Sólo genéricos", {"generic_only": True}),
    ("Región Europa", {"component_region": "europe"}),
):
    r = run(dataclasses.replace(a3, **kw))
    rows.append(
        [
            label,
            r.floats.headrope_rope.description,
            r.ballast.footrope_rope.description,
            f"{num(r.ballast.limits.min_kg, 0)}–{num(r.ballast.limits.max_kg, 0)}",
        ]
    )
PV.md_table(["Selección", "Lima", "Burlón", "Lastre [kg]"], rows)
rc = run(dataclasses.replace(a3, chain_id="gunnebo_llz_9mm")).ballast.chain
glue("chain_max_m", num(rc.max_m, 1), display=False)
glue("chain_min_m", num(rc.min_m, 1), display=False)
glue("chain_water", num(rc.water_weight_max_kgf, 0), display=False)
```

Con la cadena Gunnebo LLZ de 9 mm (1,4 kg/m), el lastre de la A-3 son {glue:text}`chain_min_m` a
{glue:text}`chain_max_m` m de cadena, que pesan {glue:text}`chain_water` kgf en el agua en el caso máximo.

## Lista de materiales y costo orientativo

`trawlkit.cost.bill_of_materials` arma la lista de lo que hay que comprar: el paño por material (el
peso en aire que ya calcula `net.analyse`), la lima y el burlón, las malletas y patentes, el cable
de remolque (dos cables del largo filado con 50 % de reserva, Cab!D12), las boyas, el par de
portones, la cadena de lastre (en metros, si el caso eligió una cadena) y los **grilletes** de las
uniones del aparejo. La cantidad de grilletes es un **supuesto** (no hay fuente que la dé): cinco
por banda con portones (cable–portón, portón–patente, patente–malletas y las dos malletas a la
punta del ala) y tres por banda en la pareja; el tamaño es el grillete más chico del catálogo
filtrado con carga de trabajo no menor que la carga de trabajo del arte (Rem!E267). Los precios son
**siempre orientativos** y los carga el usuario: el catálogo no trae precios. Una línea sin precio se informa como tal y **nunca cuenta
como cero**. La tabla usa precios ilustrativos en una moneda ficticia (XXX, el código ISO de
«sin moneda»):

```{code-cell} ipython3
:tags: [remove-input]
case_a3 = catalog_case(load_net("fao_wb_bt2p_60hp")).case
res = run(case_a3)
XXX = lambda v, u: {"value": v, "currency": "XXX", "unit": u, "date": "2026-10", "source": "ejemplo"}
prices = {"netting_pa": XXX(12, "kg"), "doors": XXX(300, "unit"), "floats": XXX(4, "unit")}
bom = bill_of_materials(res, prices)
rows = [
    [
        ln.label,
        ln.component_name or ln.component_id or "—",
        f"{num(ln.quantity, 1)} {ln.unit}",
        "sin precio" if ln.cost is None else num(ln.cost, 0),
    ]
    for ln in bom.lines
]
PV.md_table(["Ítem", "Componente", "Cantidad", "Costo [XXX]"], rows)
glue("bom_missing", bom.missing_prices, display=False)
glue("bom_total", round(bom.totals.get("XXX", 0)), display=False)
```

El total con estos precios es {glue:}`bom_total` XXX y quedan {glue:}`bom_missing` líneas sin
precio, que la app pide completar antes de comparar armados por costo.

### Lista de precios del usuario

Los precios se cargan línea por línea en la app o como **lista de precios** en CSV o XLSX
(`trawlkit.prices`, `POST /prices/parse` y `POST /prices/export`): una fila por precio con la
**clave** (el id del componente, p. ej. `crosby_g209_5_8in`, o la clave de la línea, p. ej.
`netting_pa` o `doors`), el precio, la moneda (ISO 4217), la unidad de la línea (`kg`, `m` o
unidad), la fecha y la fuente. Las columnas se reconocen en español o en inglés, con separador y
coma decimal detectados; una fila con error se informa con su número y no detiene el resto, y una
clave repetida vale por la última fila. La exportación incluye, vacías, las líneas de la lista de
materiales que todavía no tienen precio, como plantilla para completar con el proveedor. La misma
lista alimenta la lista de materiales, el armado por costo, la economía de la operación
(capítulo 37) y los lotes, se guarda con el **proyecto** de la app y funciona sin conexión.

```{code-cell} ipython3
:tags: [remove-input]
from trawlkit.prices import read_prices, write_prices

lista = write_prices(prices, "csv", [ln.to_dict() for ln in bom.lines]).decode()
print("\n".join(lista.splitlines()[:5]))
glue("prices_back", len(read_prices(lista, "precios.csv").prices), display=False)
```

Leída de vuelta, la planilla da los mismos {glue:}`prices_back` precios.

## Armado óptimo con lo que se consigue

`trawlkit.optimize.optimise_components` busca en una grilla discreta sobre el catálogo filtrado:
portones que alcanzan la superficie equivalente a la requerida (Port!F215) con la regla de Seafish
({doc}`15_portones_aparejo`; antes, los del rango de potencia del buque), boyas
que aguantan la profundidad de pesca, hilos que llegan al 90 % de la rotura del hilo del plano, y el
cable más delgado que cumple el diámetro y la rotura a la velocidad de trabajo. Cada armado se
evalúa con las restricciones del optimizador del capítulo 20 (tiro con reserva, red abierta, cable,
portón, rango de velocidad) más la profundidad de las boyas y la rotura del hilo, a la mejor
velocidad de la malla de 0,05 kn, y se ordena por **mínima resistencia**, **mínimo trabajo por m²
barrido** (máxima área por litro) o **mínimo costo**. Con la red de fondo de dos paneles del
*Workbook* y su buque de 60 hp:

```{code-cell} ipython3
:tags: [remove-input]
opt_all = optimise_components(case_a3, "drag")
opt_gen = optimise_components(dataclasses.replace(case_a3, generic_only=True), "drag")


def row(label, a):
    ev = a.evaluation
    c = a.components()
    return [
        label,
        c["door"],
        c["warp"] or "—",
        f"{c['float'] or 'del plano'} × {a.float_count or '—'}",
        c["twine"] or "del plano",
        num(ev.v_kn, 2),
        num(ev.demand_kgf, 0),
        "sí" if a.feasible else "no",
    ]


rows = [row("Recomendado", opt_all.best)]
rows += [row(f"Alternativa {i + 1}", a) for i, a in enumerate(opt_all.alternatives[:2])]
rows.append(row("Sólo genéricos", opt_gen.best))
PV.md_table(
    ["Armado", "Portón", "Cable", "Boyas", "Hilo", "v [kn]", "R_T [kgf]", "Factible"], rows
)
glue("opt_evaluated", opt_all.evaluated, display=False)
```

Se evaluaron {glue:}`opt_evaluated` armados, uno por corrida del motor (≈ 0,05 s cada una). Aquí
el armado recomendado ya es genérico (el portón del plano, un cable 6x12 de la familia del
*Workbook*, boyas plásticas y un hilo de poliéster más delgado que el del plano con la misma
rotura), por eso «sólo genéricos» da el mismo; cuando el recomendado lleva marcas, la app agrega
siempre una alternativa genérica. Las alternativas difieren en pocos kgf: el portón y las boyas
pesan poco en la resistencia de una red chica, que depende sobre todo del paño.

## Sin conexión: el motor en el teléfono

En el puerto suele no haber señal. La app es una **aplicación web instalable** (PWA) y, con
«Preparar uso sin conexión», descarga una sola vez el intérprete de Python compilado a
WebAssembly (Pyodide), numpy, pydantic, pyyaml y la *wheel* de `trawlkit` (unos 15 MB). Desde
entonces, sin red, el diseño, los catálogos, la lista de materiales, el armado con componentes, el
validador de aportes y la optimización por malla corren **en el teléfono**:
`trawlkit.api.offline` atiende las mismas rutas que la API con los mismos modelos de pedido y
respuesta. Las pruebas comparan cada ruta con la API y, en la CI, el diseño de la A-3 dentro de
Pyodide (en Node) con el de CPython: la mayor diferencia relativa es del orden de $10^{-16}$. La
simulación, los informes PDF y los planos SVG siguen necesitando el servidor, y la app lo avisa.
El **modo de bajo consumo de datos** oculta las vistas 3D y la simulación, que descargan three.js.

## Aportes de usuarios

Quien usa un cable, un cabo o una boya que no está en el catálogo lo carga en la pestaña
«Componentes» con los datos de la etiqueta o la ficha. El aporte se valida con
`POST /components/check`, queda guardado **sólo en el navegador** con el estado «aporte, sin
verificar» y entra en el cálculo únicamente si el usuario lo habilita: viaja en el campo
`components` de cada pedido y el motor lo ve sólo durante ese pedido. Para sumarlo al catálogo,
«Proponer al catálogo» abre un *issue* de GitHub con la plantilla de componentes y el JSON del
aporte; un mantenedor lo revisa y lo transcribe en `tools/components/` con su fuente. No hay
cuentas ni datos personales.

## Supuestos y límites

* Los genéricos son **ajustes** a tablas de referencia, no productos: un cable o un hilo real del
  mismo diámetro puede pesar o romper ±10 % distinto. La ficha de cada ítem dice qué valor es de
  fábrica y cuál es derivado o supuesto.
* Las polares de los portones genéricos y de fabricante son las de su tipo (medidas en modelos de
  tanque de flujo), no de cada modelo; ningún fabricante publica C_L/C_D.
* Casi no hay fichas abiertas de proveedores latinoamericanos ni de tamaños chicos: los aportes
  cubren ese hueco y se distinguen siempre de los datos con fuente.
* Los precios son orientativos y del usuario; el optimizador por costo pone primero los armados con
  menos precios faltantes.
* El optimizador de componentes no escala la red (para eso está el del capítulo 20) ni cambia los
  cabos de relinga: con filtros, la selección automática los toma del catálogo con la regla de
  arriba; sin filtros, son los de la red o del libro.
* La cantidad de grilletes de la lista de materiales es un supuesto; el tamaño cuida la carga de
  trabajo del arte entero, una cota holgada para cada unión.
* Varios tamaños y productos quedaron afuera a propósito: los que repiten valores de otro producto
  (Dyform 6x26 de 20 a 44 mm, Prima Headline, Dyform RL), los de cerco (Dyform SeaPurse), las filas
  con erratas evidentes (Trawlex de 13 mm) y las fichas sin tabla abierta (WireCo, Usha Martin,
  Euronete, Castro, proveedores de Mar del Plata).
