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
