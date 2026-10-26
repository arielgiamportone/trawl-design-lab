# Arquitectura del motor `trawlkit`

`trawlkit` reimplementa, módulo a módulo, las trece hojas del libro `Calculos_Red_FAO_A3.xlsx`.
Cada módulo contiene funciones puras (una por bloque de fórmulas, con la celda representativa en
el docstring) y un *dataclass* de resultado; `trawlkit.model.run` las encadena en el orden en que
el libro resuelve sus dependencias y devuelve un `DesignResult` con una etapa por hoja.

## Módulos y hojas

| Módulo | Hoja(s) del libro | Qué calcula |
|---|---|---|
| `trawlkit.io` | Especie Blanco, Tipo de buques, catálogos | Esquema pydantic (`NetSpec`, `Vessel`, `Door`, `Catalogue`) y carga de `src/trawlkit/data/*.yaml` |
| `trawlkit.vessel`, `trawlkit.power` | Potenc disponible para arrastre, Potencia Disponible Arrastre OK | Reparto de energía (Fridman); tiro disponible FT por Fridman, Prado-Dremière, Koyama, Nomura y Hamuro; resumen `PotOK!L11:O19` |
| `trawlkit.netting`, `trawlkit.materials` | Paños de red y cortes, Tablas de Referencias | Largos estirados, superficies de paño, cortes (razón, código, ángulo), densidad del hilo |
| `trawlkit.net` | Mecánica de la Red (filas 6-113) | Índice de filtración d/l, superficies sólida y de trabajo, solidez, pesos |
| `trawlkit.dimensions` | Dimensiones de la Red | Lima y burlón (Martini), largos, circunferencias, factor largo, proporciones de Nomura |
| `trawlkit.drag` | Resistencia de la RED | Trece métodos de resistencia de la red; Aberdeen demersal es la RN de diseño |
| `trawlkit.rigging.doors`, `.bridles` | Portones y aparejamiento | Separación entre portones, polar, ROB, fuerzas, superficie requerida; bridas, patentes, pies de gallo, δ |
| `trawlkit.rigging.spread` | Mecánica de la Red (filas 162-282) | DPA de Fridman, geométrica y por ángulo de corte; abertura horizontal y vertical |
| `trawlkit.rigging.floats`, `.ballast`, `.ropes` | Flotación y Lastre, Cables Y Cabulleria | Flotación (Koyama, Prado, Fridman), boyas y su resistencia; lastre y su distribución; cabos |
| `trawlkit.rigging.warps` | Cables de Remolque, Cables Y Cabulleria | Ángulos del cable, diámetro, CD, Rw, resistencia total, peso, cargas y selección |
| `trawlkit.performance` | (comparación implícita en el libro) | Ventana de velocidad viable FT(v) ≥ R(v) |
| `trawlkit.compat` | — | Modos `EXCEL`/`CORRECTED` y registro `ERRATA` |
| `trawlkit.model` | todas | `DesignCase`, `DesignResult`, `run` |

Alrededor de ese núcleo, que reproduce el libro, crecieron módulos que el Excel no tenía:

| Módulo | Qué hace | Capítulo |
|---|---|---|
| `trawlkit.optimize` | Escala de la red y velocidad óptimas con restricciones; armado óptimo con el catálogo de componentes (`optimize.components`) | {doc}`20_optimizacion`, {doc}`34_componentes` |
| `trawlkit.sim` | Forma de equilibrio de la red (elementos de paño, Morison, relajación FIRE), escenario de lance, estado de malla, incertidumbre y calibración | {doc}`21_simulacion` a {doc}`25_incertidumbre_calibracion` |
| `trawlkit.selectivity`, `trawlkit.sensors` | Tallas retenidas por especie según la malla deformada; lectura de registros de sensores | {doc}`24_malla_selectividad`, {doc}`25_incertidumbre_calibracion` |
| `trawlkit.catalog`, `.topology`, `.netcheck`, `.provenance` | Caso de diseño de cada red del catálogo FAO, topologías distintas de la A-3, validador de consistencia y procedencia valor por valor | {doc}`33_catalogo_fao` |
| `trawlkit.components`, `trawlkit.cost` | Catálogo de componentes con equivalentes genéricos; lista de materiales y costo orientativo | {doc}`34_componentes` |
| `trawlkit.construction` | Guía de construcción: hoja de corte, paño a comprar, uniones con tomas, montaje en relingas, boyas, lastre y cortes de cabos | {doc}`36_construccion` |
| `trawlkit.economics` | Economía de la operación: gasoil, captura, costos por rubro, margen y precio de equilibrio por velocidad; comparación de redes con ahorro y repago | {doc}`37_economia` |
| `trawlkit.batch` | Planillas de flota, redes y casos; proyección de una red a cada buque; exportación | {doc}`35_lotes_proyeccion` |
| `trawlkit.drawing`, `trawlkit.report` | Plano SVG (lámina y escala real), gráficos e informes HTML, PDF y XLSX | {doc}`informes` |
| `trawlkit.api` | API FastAPI (`app`, `service`, `schemas`) y `api.offline`, el mismo servicio sin servidor que la app corre en Pyodide | {doc}`api`, {doc}`web` |

## Orden de las etapas

El grafo de dependencias entre hojas (ver `legacy/formula_map.md`) obliga a un orden distinto al
de las pestañas. `run` lo recorre así:

```
geometry      Mecánica de la Red        d/l, Ss, St, pesos (columnas estándar y modificada)
    │
dimensions    Dimensiones de la Red     relingas, largos, circunferencia, ángulo de corte
    │
power         Potencia disponible       reparto de energía, curvas de tiro, FT de Fridman por buque
    │
drag (1)      Resistencia de la RED     13 métodos → RN de diseño (Aberdeen demersal); Dickson en NaN
    │
rigging       Mec!B175:F186, Port!A33   Ls = profundidad × relación tabulada; LR·U2; flecha de la
    │                                   lima (0.216·L); bridas a un punto (AV Suzuki); pies de gallo
doors         Portones y aparejamiento  Ds = (2.65 − pastecas)·Ls + pastecas; polar a 32°; ROB = 20 % FT;
    │                                   fuerzas ½·ρ/g·C·S·v²; superficie requerida; Pφ; momentos
floats        Flotación y Lastre        Koyama, Prado y Fridman por buque de la clase → Ffz (Mec!O261);
    │                                   boyas del catálogo, distribución, resistencia RB
spread        Mec!B162:P282, Dim!F61    DPA Fridman (Edx/Edy), geométrica, por corte → AH;
    │                                   AV por %, Suzuki, Martini y Baranov–Fridman (usa Ffz)
drag (2)      Res!C282:F290             se rellena Dickson con AH = Mec!P164:P172 y AV = O272:O280
    │
bridles       Port!A63:E110             patentes (Dremière, Martini), ángulo de ataque δ
    │
ballast       Flot!D153:I245            Koyama, Prado, Fridman (F1' + F2' − W burlón), límites, reparto
    │
warps         Cables de Remolque        ángulos δ1-δ3, Ø (EHP, Águila), CD, Rw, R total (+ROB en
    │                                   modo corregido), peso, cargas ×4, selección del catálogo
performance                             FT (PF y PV+T) frente a R(v) → velocidad máxima remolcable
```

Dos detalles explican el orden: el libro es circular entre Dickson y las aberturas de Fridman (que
usan la RN de Aberdeen); como Dickson no alimenta a Aberdeen, la tabla de resistencia se evalúa dos
veces. Y la AV de Fridman necesita la flotación total `Ffz`, que promedia los bloques de 150 y
180 HP de *Flotación y Lastre*, de modo que la flotación se calcula antes que las aberturas.

Cada número que el libro tiene escrito a mano es un campo de `DesignCase` con la celda en un
comentario (`spread_per_m` = `Port!D7`, `bridle_angle_deg` = `Port!F39`, `sweeps_m` = `Dim!F65`,
`catenary_ratio` = `Mec!O266`, `warp_safety_factor` = `Rem!D271`, …). Los acoplamientos entre los
dos buques del libro se modelan con `class_vessels` (flotación promedio y NHP del cable) y los de
las dos redes con `net_modified` (columna G).

## Modos de compatibilidad

Toda función afectada por una errata del libro acepta `compat`:

* `Compat.EXCEL` reproduce el número del libro, errata incluida. Es el modo con el que los golden
  tests validan la migración.
* `Compat.CORRECTED` (por defecto) aplica la fórmula correcta. `tests/test_corrected_mode.py`
  comprueba, a nivel del caso completo, que cada conmutador mueve el resultado en la dirección
  esperada (Ss 38.75 en vez de 40.90 m², burlón 33.389 m, Hamuro y Reid menores, resistencia total
  con ROB, cable de 13 mm en vez de 12, Reynolds de la boya ÷ π·D, promedio de resistencias
  limpio) y que lo no afectado coincide entre modos.

La tabla completa, con la función y el test de cada errata, está en [Erratas](erratas.md).

## Cómo correr un caso

En Python:

```python
from trawlkit import Compat, DesignCase, run
from trawlkit.io import load_doors, load_net, load_vessels

vessels = {v.id: v for v in load_vessels().vessels}
case = DesignCase(
    net=load_net("fao_a3_standard"),
    net_modified=load_net("fao_a3_modified"),
    vessel=vessels["fao_a3_150hp"],
    class_vessels=(vessels["fao_a3_180hp"],),
    door=load_doors().doors[0],
    compat=Compat.EXCEL,  # o Compat.CORRECTED (por defecto)
)
result = run(case)
result.summary()  # 'Dimensiones de la Red'!F45:F71 + RN, ROB, boyas, lastre, cable, v máx
result.drag.rn.std  # RN de diseño [kgf] a 1…5 kn
result.performance.design.max_speed_kn
result.to_dict()  # serializable en JSON
```

Desde la línea de comandos:

```bash
uv run trawlkit run fao_a3_standard --vessel fao_a3_150hp --door fao_flat_wood_a3 \
    --modified fao_a3_modified --class-vessel fao_a3_180hp --compat excel --json caso.json
```

imprime la tabla Markdown del resumen (etiquetas en español, con unidades), las notas de la
corrida y, con `--json`, escribe `summary()` y `to_dict()`.

### Muchos casos: lotes y flotas

`trawlkit.batch` ({doc}`35_lotes_proyeccion`) lee planillas de flota, redes o casos y calcula
todo de una vez; `project_net` proyecta una red a otro buque (semejanza por potencia y refinado):

```python
from trawlkit.batch import fleet_vessel, project_net, read_input, result_xlsx, run_input

p = project_net("fao_wb_bt2p_60hp", fleet_vessel({"name": "Mi buque", "bhp": 120}))
p.s0, p.s, p.summary()["speed_kn"], p.net  # escala por semejanza, escala final, red escalada

inp = read_input(open("flota.xlsx", "rb").read(), "flota.xlsx", "fleet")
res = run_input(inp, net="fao_wb_bt2p_60hp")
open("lote.xlsx", "wb").write(result_xlsx(res))
```

```bash
uv run trawlkit batch --template flota.xlsx
uv run trawlkit batch flota.xlsx --net fao_wb_bt2p_60hp -o lote.pdf
```

## Validación con los valores de referencia

`tools/extract_excel.py` vuelca los valores cacheados del libro en `tests/golden/*.json` (un JSON
por hoja, claves `snake_case` estables, marcas `static` y `coerced_from_text`). Hay tres niveles
de test:

1. **Por función** (`tests/test_<módulo>.py`): cada bloque de fórmulas se alimenta con las entradas
   golden de sus celdas precedentes y se compara con `rtol = 1e-6` en modo `EXCEL`.
2. **Extremo a extremo** (`tests/test_case_fao_a3.py`): `run` sobre la red estándar + modificada
   para los buques de 150 y 180 BHP, sin entradas intermedias, contra ~120 claves de las ocho hojas
   de cálculo, también a `rtol = 1e-6` (el motor reproduce exactamente el truncado `MID()` del
   burlón, por lo que no hace falta la tolerancia `1e-3`).
3. **Modo corregido** (`tests/test_corrected_mode.py`): dirección de cada errata a nivel de
   resultado e igualdad de lo no afectado.
