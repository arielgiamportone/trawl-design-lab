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

Una red no se arma sólo con el plano: hacen falta paño, cables, cabos, portones, boyas y cadenas,
y lo que se consigue en cada puerto cambia. Este capítulo describe el **catálogo de componentes**
(Fase 13): {glue:}`n_items` ítems de {glue:}`n_brands` marcas y de equivalentes **genéricos**, con
la fuente de cada valor; cómo el motor los usa para dimensionar; cómo se arma la **lista de
materiales** con su costo orientativo; y cómo el optimizador **elige el armado** entre lo que hay.
La herramienta apunta a pescadores con pocos recursos: los genéricos se consiguen en cualquier
ferretería naval, los precios los carga el usuario y la app calcula **sin conexión** en el teléfono.

## Fuentes y equivalencias genéricas

Casi ningún fabricante publica tablas abiertas, y menos de tamaños chicos. Por eso cada tipo
tiene una **familia genérica** derivada de las tablas del *Fisherman's Workbook* de la FAO
{cite}`prado1990`, y las marcas son **datos puntuales** citados, nunca tablas completas (a lo sumo
diez medidas por línea de producto):

* **Paño e hilo**: diámetro y rotura por Rtex para PA torcido y trenzado, PES, PP y PE, con un
  ajuste potencial $y = a\,x^b$ en escala logarítmica sobre las tablas del *Workbook*; Garware
  (India) para el PE trenzado {cite}`garware_fisheries`.
* **Cables de acero**: peso y carga de rotura con $y = k\,d^2$ sobre las tablas 6x7, 6x12, 6x19 y
  6x24 del *Workbook*; Bridon-Bekaert {cite}`bridon2023` y PFEIFER {cite}`pfeifer_6x19w` como
  fabricantes.
* **Cabos**: PA, PE, PES, PP y combinados de acero y fibra; Garware X2.
* **Portones**: superficie y peso por potencia del *Workbook* para portones planos, ovales, en V y
  Süberkrüb; la polar de cada tipo sale de la plana del libro Excel (C_L máx. 0,93, consistente con
  0,95 de {cite}`lange1993`) o de la Morgère, escalada para el portón en V; y cuatro puertas de la
  flota camaronera del Caribe colombiano {cite}`zuniga2006`.
* **Boyas y cadenas**: flotación y profundidad máxima por diámetro, peso por metro por eslabón.

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

## Validación física

Un componente cargado a mano puede traer un error de unidades o de tipeo. El validador
(`trawlkit.components.check`) compara cada valor con rangos físicos del material: peso por metro
contra $k\,d^2$ (acero, fibra, cadena), rotura contra la del material, tenacidad del hilo en gf/tex,
flotación contra el volumen de la boya y peso del portón por m². Por ejemplo, un cable de 10 mm
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

## Lista de materiales y costo orientativo

`trawlkit.cost.bill_of_materials` arma la lista de lo que hay que comprar: el paño por material (el
peso en aire que ya calcula `net.analyse`), la lima y el burlón, las malletas y patentes, el cable
de remolque (dos cables del largo filado con 50 % de reserva, Cab!D12), las boyas, el par de
portones y la cadena de lastre. Los precios son **siempre orientativos**: los carga el usuario o
vienen del catálogo con fecha y fuente. Una línea sin precio se informa como tal y **nunca cuenta
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

## Armado óptimo con lo que se consigue

`trawlkit.optimize.optimise_components` busca en una grilla discreta sobre el catálogo filtrado:
portones del rango de potencia del buque o de superficie cercana a la requerida (Port!F215), boyas
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
* Las polares de los portones genéricos son las de su tipo (plano, oval, en V), no medidas de cada
  modelo; ningún fabricante publica C_L/C_D.
* Casi no hay fichas abiertas de proveedores latinoamericanos ni de tamaños chicos: los aportes
  cubren ese hueco y se distinguen siempre de los datos con fuente.
* Los precios son orientativos y del usuario; el optimizador por costo pone primero los armados con
  menos precios faltantes.
* El optimizador de componentes no escala la red (para eso está el del capítulo 20) ni cambia los
  cabos de relinga, que se eligen a mano.
