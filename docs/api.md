# API HTTP

La API expone el motor por HTTP. Se levanta con `uv run trawlkit serve` (puerto 8000) y la
documentación interactiva queda en `http://127.0.0.1:8000/docs`. El contrato completo está en
`web/openapi.json`; esta página se genera a partir de él.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Comprobación de vida. |
| GET | `/catalog/nets` | Redes predefinidas (FAO A-3 y catálogo FAO) con familia, aparejo, potencia, fuente, validador y cobertura de procedencia; `?status=published\|draft`. |
| GET | `/catalog/nets/{net_id}` | Especificación completa de una red predefinida (paneles, relingas, boyas). |
| GET | `/catalog/nets/{net_id}/provenance` | Procedencia de cada valor de la red (documento, figura, tipo y nota). |
| GET | `/catalog/nets/{net_id}/check` | Validador de consistencia de la red (empalmes, bocana, cortes, costados). |
| GET | `/catalog/components` | Tipos de componente (paño, cables, cabos, portones, boyas, cadenas) con cantidad de ítems, genéricos y marcas. |
| GET | `/catalog/components/{kind}` | Componentes de un tipo con su procedencia; filtros `brand` (repetible), `region`, `generic`, `status`. |
| GET | `/catalog/components/{kind}/{item_id}` | Un componente con sus observaciones y su genérico equivalente. |
| POST | `/components/check` | Valida un componente cargado por el usuario (esquema y coherencia física). |
| POST | `/design/bom` | Lista de materiales del caso (paño, relingas, malletas, cable, boyas, portones, lastre) con costo orientativo según `prices` o el precio del catálogo; cuenta las líneas sin precio. |
| POST | `/optimize/components` | Armado con componentes del catálogo (portón, cable, boyas, hilo) por `drag`, `efficiency` o `cost`, con alternativas y lista de materiales; filtros en `params` (`component_brands`, `component_region`, `generic_only`). |
| POST | `/batch/parse` | Lee una planilla de flota, redes o casos (CSV como texto o XLSX en base64): filas reconocidas, observaciones por fila y columna, y costo estimado del lote. |
| POST | `/batch/run` | Calcula el lote: proyecta una red a cada buque de la flota (escala por semejanza de potencia refinada, velocidad y armado), o calcula casos o redes cargadas. Guarda de costo `TRAWLKIT_MAX_BATCH_SECONDS`. |
| POST | `/batch/export` | El lote en `csv` (resumen), `xlsx` (resumen, materiales y una hoja de paneles por red escalada), `pdf` o `html` (ficha por buque). |
| GET | `/batch/template` | Plantilla de planilla (`kind`: `fleet`, `nets`, `cases`; `format`: `xlsx` con hoja de ayuda, o `csv`). |
| GET | `/catalog/vessels` | Buques del catálogo. |
| GET | `/catalog/doors` | Portones del catálogo con su polar CL/CD. |
| GET | `/catalog/fouling` | Escenarios de ensuciamiento y colmatación de la red (nivel por zona). |
| GET | `/catalog/species` | Especies para la selectividad, con la forma de su sección transversal (A VERIFICAR). |
| GET | `/catalog/seabeds` | Tipos de fondo con el rozamiento del tren y de los portones (nominal y rango). |
| GET | `/params` | Parámetros de diseño sobrescribibles en `DesignRequest.params`. |
| GET | `/errata` | Erratas del libro Excel original. |
| POST | `/design` | Calcula un caso de diseño completo. |
| POST | `/design/plan` | Plano SVG del caso: lámina técnica (`sheet`) o escala real (`scale`). |
| POST | `/design/layout` | Disposición 2D de la red (polígonos por plano, en metros; `variant`, `mode` = `schematic` o `true_scale`) para el editor interactivo. |
| POST | `/design/construction` | Guía de construcción para el taller ({doc}`36_construccion`): hoja de corte por paño con el ciclo de cada corte, paño a comprar, uniones paso a paso con la regla de toma, montaje en relingas (mallas por metro y coeficiente de armado), boyas, lastre y cortes de cabos; `variant` y `eye_allowance_m` (sobrante por gaza). |
| POST | `/design/construction/export` | La guía en `pdf` o `html` (A4 para imprimir) o `xlsx` (una hoja por tabla). |
| POST | `/economics` | Economía de la operación ({doc}`37_economia`): por velocidad, gasoil (arrastre, navegación y maniobras), captura, ingreso, costos por rubro (combustible, lubricante, tripulación, red y aparejo, marea, fijos), margen, costo por kg y precio de equilibrio; la velocidad de mayor margen, la de menor costo por kg y el año. Sin precios, los montos salen en `null` y `missing` dice qué falta. |
| POST | `/economics/compare` | Compara redes o buques con los mismos datos de operación: margen y gasoil por año, ahorro frente al primero y repago del armado. |
| GET | `/teaching/exercises` | Banco de ejercicios del modo docente, filtrable por `chapter`, `level` (`basico`, `intermedio`, `avanzado`) y `topic`. |
| GET | `/teaching/exercises/{id}?seed=` | Un ejercicio con sus datos para la semilla (0 = los del libro), sin las respuestas. |
| POST | `/teaching/grade` | Corrige las respuestas de práctica (números con coma o punto, dentro de la tolerancia de cada respuesta) y devuelve la solución y la explicación. |
| GET | `/teaching/labs`, `/teaching/labs/{id}` | Laboratorios guiados sobre la app: caso de partida, pasos, dónde se hace cada uno y sus preguntas (sin las respuestas). |
| POST | `/teaching/labs/check` | Comprueba un paso de laboratorio sobre el caso del alumno con hechos que calcula el motor y corrige sus preguntas. |
| — | `/classroom/…` | Aula UTN (sólo en línea, con `DATABASE_URL`; ver {doc}`despliegue`): alta con código de curso o de invitación, inicio de sesión con token *bearer*, cursos, alumnos, tareas con ejercicios y laboratorios del banco (datos propios por alumno, intentos, fechas y devolución inmediata o al cierre), entregas corregidas en el servidor, planilla de notas (JSON, XLSX, CSV), guía imprimible por alumno y revisión del docente. `GET /classroom/status` dice si está habilitada. |
| POST | `/optimize` | Optimiza la escala de la red y la velocidad de arrastre (malla + evolución diferencial). |
| POST | `/optimize/scaled-net` | Red escalada por `s` (mismas mallas y materiales), para usar el diseño optimizado. |
| POST | `/simulate` | Simula la forma de equilibrio de la red a varias velocidades (experimental). |
| POST | `/simulate/haul` | Lance progresivo: forma, separación de portones y tiro mientras entra captura (escenario con fondo y portones acoplados). |
| POST | `/simulate/explore` | Explorador: estados de red, portones y cables al recorrer una variable (captura, velocidad, cable, ensuciamiento, corriente, rozamiento), con conectividad común y posiciones por estado para animar; energía y huella. |
| POST | `/simulate/selectivity` | Selectividad del copo: hasta 3 variantes de copo (rombo, T90, cuadrada; mallero y U1) con la curva de retención por especie (L25, L50, L75, SR, SF), la talla máxima de paso por triángulo y la forma para el mapa 3D y el zoom por malla. `/simulate/explore` acepta `species` y suma L50, SR y SF por estado. |
| POST | `/simulate/uncertainty` | Incertidumbre: Monte Carlo con hipercubo latino sobre los datos inciertos (coeficientes del hilo, rozamientos, polar del portón, captura); P10/P50/P90 y sensibilidad (Spearman) por resultado. |
| POST | `/simulate/calibrate` | Calibración: Levenberg–Marquardt acotado de hasta 3 parámetros contra observaciones (de sensores) o la referencia DynamiT de la FAO A-3. |
| POST | `/sensors/parse` | Lee un registro de sensores (CSV de cualquier equipo) y lo resume en tramos estacionarios y observaciones. |
| GET | `/sensors/example` | Registro de sensores de ejemplo (sintético) en CSV. |
| POST | `/design/report` | Informe del caso en HTML, PDF o XLSX. |

## Ejemplo

```bash
curl -s -X POST http://127.0.0.1:8000/design \
  -H 'Content-Type: application/json' \
  -d '{"net": "fao_a3_standard", "net_modified": "fao_a3_modified", "vessel": "fao_a3_150hp", "compat": "excel"}'
```

El cuerpo `DesignRequest` acepta redes, buques y portones por id del catálogo o como especificación
completa, el modo de cálculo y `params` con los parámetros de `GET /params`. Los ids se validan
contra el catálogo; los parámetros numéricos deben ser finitos y no negativos.

Una red del catálogo FAO ({doc}`33_catalogo_fao`) enviada **sin buque, portón ni red modificada**
se calcula con su propio caso (`trawlkit.catalog.catalog_case`): buque genérico de la potencia de
diseño, portón y profundidad del plano, pareja sin portones. Los supuestos vuelven en `notes`
con el prefijo `catalog:`, y `params` sobrescribe lo que sale de la fuente:

```bash
curl -s -X POST http://127.0.0.1:8000/design \
  -H 'Content-Type: application/json' -d '{"net": "bobp_wp13_pair_ho80"}'
```

Una red del catálogo FAO con `door` (por ejemplo un portón del catálogo de componentes) y sin
buque conserva el buque de la red y cambia sólo el portón.

**Componentes** ({doc}`34_componentes`). `params` acepta `warp_id`, `float_id`, `twine_id` y
`chain_id` (ids de `GET /catalog/components/{kind}`) y los filtros de la selección automática
`component_brands` (lista), `component_region` y `generic_only` (booleano). `components` lleva
aportes de usuario en línea (hasta 50, con estado «user»): el motor los ve sólo en ese pedido.
`POST /design/bom` acepta lo mismo más `prices` (id de componente o clave de línea → precio
orientativo con moneda y unidad):

```bash
curl -s -X POST http://127.0.0.1:8000/design/bom \
  -H 'Content-Type: application/json' \
  -d '{"net": "fao_wb_bt2p_60hp", "params": {"generic_only": true},
       "prices": {"doors": {"value": 300, "currency": "USD", "unit": "unit"}}}'
```

`POST /optimize/components` elige portón, cable, boyas e hilo del catálogo filtrado
(`objective`: `drag`, `efficiency` o `cost`; `speed_kn` fija la velocidad, si no se elige la mejor
entre `v_bounds`) y devuelve el armado recomendado, alternativas y la lista de materiales de cada
uno.

`POST /optimize` corre la optimización de escala y velocidad de {doc}`20_optimizacion` (malla y,
si `refine`, evolución diferencial) y devuelve el mejor diseño, la malla de factibilidad y el frente
de Pareto. `POST /optimize/scaled-net` devuelve la `NetSpec` de la red escalada por `s`
(`trawlkit.optimize.scale_net`), lista para enviarla como red en línea a `POST /design`.

`POST /simulate` corre la simulación de forma de {doc}`21_simulacion` (experimental):

```bash
curl -s -X POST http://127.0.0.1:8000/simulate \
  -H 'Content-Type: application/json' \
  -d '{"net": "fao_a3_standard", "speeds_kn": [2, 3], "resolution": 4}'
```

Acepta de 1 a 9 velocidades entre 0,5 y 6 kn, `resolution` de 2 a 10 (4 por defecto), los
coeficientes del hilo `cn`/`ct`, `knot_factor`, `door_spread_m` e `include_geometry` (nodos y
triángulos de la forma, pesado). Devuelve por velocidad el `SimResult` (aberturas, arrastre,
convergencia), las proyecciones SVG (planta, perfil y frente) de las tres primeras velocidades, las
magnitudes empíricas del motor a las mismas velocidades y, para la red FAO A-3 estándar sin editar,
la comparación con DynamiT. Cada velocidad tarda de ~1 s (resolución 2–4) a ~20 s (resolución
9–10): los pedidos cuyo costo estimado supera 30 s se rechazan con 422.

La variable `TRAWLKIT_CORS_ORIGINS` limita los orígenes permitidos (por defecto `*`).
