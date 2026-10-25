# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/); el proyecto usa
[versionado semántico](https://semver.org/lang/es/). La versión vive en `trawlkit.__version__`.

## [Sin publicar]

### Agregado
- App web, **modo guiado** (por defecto): asistente en 4 pasos (buque, red, operación, resultado)
  con diagnóstico por semáforos en lenguaje llano a la velocidad elegida (potencia, velocidad
  máxima, cable, boca y área barrida) y enlaces al libro. El **modo experto** es la interfaz
  completa; el conmutador se recuerda.
- Proyectos: guardar/abrir en el navegador, exportar/importar `.trawl.json`, caso nuevo.
- Deshacer/rehacer del caso (botones y atajos de teclado).
- Ayuda contextual «?» con unidad, rango habitual y capítulo del libro; avisos fuera de rango.
- **Diseño interactivo**: plano editable (arrastre de alto y bordes, teclado, inspector del panel)
  con recálculo en vivo, impacto frente a la red de base y contorno original superpuesto.
- `POST /design/layout`: disposición 2D de la red por plano (la geometría de la lámina) en JSON.
- **Vista 3D** de la forma simulada (three.js): paño coloreado por la tensión del hilo, aparejo,
  boyas, vistas estándar y descarga PNG.
- `tools/export_openapi.py` y un test que verifica que `web/openapi.json` esté al día.
- **Simulador realista (Fase 11.1)**: captura en el copo (volumen por densidad aparente, flujo
  bloqueado y presión ½ρC_pv² sobre el copo, O'Neill y O'Donoghue 1997), catálogo de tipos de
  fondo con rango de rozamiento (`data/seabed.yaml`, A VERIFICAR), portones acoplados (polar
  C_L/C_D, peso y cable de remolque hasta el buque) y lance progresivo (`trawlkit.sim.haul`,
  `POST /simulate/haul`, `GET /catalog/seabeds`). La separación de portones de la FAO A-3 a 3 kn
  pasa de 32,5 m (regla del motor) a 46,8 m frente a 51,4 m de DynamiT.
- Motor: parámetro `seabed` que suma el rozamiento del tren y de los portones a la demanda.
- **Simulador realista (Fase 11.2), explorador animado**:
  - ensuciamiento por zona (`data/fouling.yaml`, A VERIFICAR, a partir de Swift et al. 2006 y
    Bi et al. 2015);
  - corriente a lo largo del rumbo, largo de cable filado y duración del lance;
  - salidas de energía (potencia de remolque, L/h, L/kg, L/km²) y huella (anchos y áreas barrida
    y en contacto, penetración; BENTHIS);
  - `trawlkit.sim.explore`, `POST /simulate/explore` y `GET /catalog/fouling`;
  - en la web, el «Explorador animado»: animación 3D del aparejo completo, línea de tiempo,
    tablero sincronizado, gráficos con cursor y exportación PNG/WebM;
  - capítulo 23 «Mar real y condiciones en funcionamiento».
- **Zoom por malla y selectividad (Fase 11.3)**:
  - orientación de la malla por paño (`Panel.mesh_orientation`: rombo, T90, cuadrada) en el motor
    empírico, el plano a escala real y el simulador, con rigidez de apertura de la malla (bisagras
    en los nudos, Sala et al. 2007) que distingue T90 del rombo;
  - estado de cada malla en la simulación (`trawlkit.sim.meshstate`: ángulo, patas, luz, área
    libre, captura) y parche de mallas exacto para el zoom;
  - `trawlkit.selectivity`: prueba de paso geométrica tipo FISHSELECT (Herrmann et al. 2009),
    curva de retención con L25/L50/L75, SR y SF, catálogo de especies (`data/species.yaml`,
    A VERIFICAR) y `codend_variant` para rehacer el copo en otra orientación o mallero;
  - `POST /simulate/selectivity`, `GET /catalog/species` y especies en `/simulate/explore`;
  - en la web, la vista «Mallas y selectividad» (tabla, curvas, mapa 3D y zoom por malla), la
    orientación en el inspector del panel y L50/SR en el explorador;
  - capítulo 24 «Zoom por malla y selectividad».
- **Incertidumbre y calibración (Fase 11.4)**:
  - `trawlkit.sim.uncertainty`: Monte Carlo con hipercubo latino (C_N, C_T, rozamientos según el
    fondo, polar del portón, captura), P10/P50/P90 y sensibilidad de Spearman;
  - `trawlkit.sim.calibration`: Levenberg–Marquardt acotado contra observaciones o DynamiT;
  - `trawlkit.sensors`: importador genérico de registros de sensores en CSV (nombres y unidades
    en español o inglés), tramos estacionarios y observaciones; registro de ejemplo sintético;
  - `Scenario.door_cl_factor` / `door_cd_factor`;
  - `POST /simulate/uncertainty`, `POST /simulate/calibrate`, `POST /sensors/parse`,
    `GET /sensors/example` y la guarda `TRAWLKIT_MAX_BATCH_SECONDS`;
  - en la web, la vista «Incertidumbre y calibración» (bandas, tornado, carga del CSV y ajuste);
  - capítulo 25 «Incertidumbre, calibración y datos de sensores».
- **Catálogo de redes FAO (Fase 12, en curso)**:
  - procedencia por valor (`NetSpec.provenance`, `trawlkit.provenance`): documento, página,
    figura y tipo (Excel, transcripto, derivado, supuesto) de cada número de la red;
  - validador de consistencia `trawlkit.netcheck`: empalmes, bocana, costuras laterales, cortes
    contra mallas (`netting.cut_code_ratio`), costados de las redes de 4 paneles y datos;
  - primeras redes digitalizadas (`data/nets/`): arrastre de fondo de 2 paneles del Fisherman's
    Workbook y dos arrastres de pareja de BOBP/WP/13 (`tools/catalog/`);
  - motor generalizado: dimensiones genéricas para redes que no tienen la estructura de la A-3
    (`trawlkit.topology`), arrastre de **pareja** (`DesignCase.rig`, `pair_wing_spread_m`; sin
    portones, tiro de dos buques), redes de **4 paneles** (red equivalente de 2 paneles; costados
    en la disposición, la lámina y la escala real), redes **pelágicas** (sin fondo en el
    simulador, rozamiento nulo) y separación de portones de Fridman (`door_spread_rule`);
  - `trawlkit.catalog.catalog_case`: caso de diseño de cada red con su buque, portón y
    profundidad; `trawlkit run <red del catálogo>` lo usa.
- Web: vista «Lance progresivo» con gráficos contra la captura y 3D por paso (tensión o contacto
  con el fondo); tipo de fondo y captura esperada en el modo guiado.
- `/health` informa la huella de rutas (`contract`) y el commit desplegado; la app avisa «API
  desactualizada» si la API en línea es de otra versión, y un 404 de ruta lo explica. El flujo
  «Docs» comprueba la API en línea al terminar (`tools/check_api_contract.py`).

- Libro: capítulo 22 «Simulación con captura, fondo y portones acoplados», con el panorama de
  simuladores del mercado; 7 referencias nuevas (6 verificadas en Crossref).

### Corregido
- Libro: las tablas generadas desde código en los capítulos 22 y 23 salían como texto (MyST-NB
  no renderiza tablas Markdown en las salidas); ahora son tablas HTML.
- La API de Render quedaba sin redesplegar (404 en `/simulate/haul`, `/catalog/seabeds` y
  `/design/layout`): se quitó el `buildFilter` del Blueprint.

## [1.0.0] - 2026-10-19

Primera versión pública: paquete en PyPI, DOI en Zenodo y metadatos de cita (`CITATION.cff`).

### Agregado
- Publicación: `CITATION.cff`, `.zenodo.json`, este registro, workflow `release.yml`
  (PyPI con *Trusted Publishing* al publicar un release `v*`) y página "Cómo citar" en el libro.
- Versión única en `trawlkit.__version__` (pyproject dinámico), con test de coherencia con la web.

## [0.1.0] - 2026-10-18

Desarrollo inicial (fases 0 a 7), sin publicar en PyPI.

### Agregado
- **Datos** (fase 1): modelo FAO A-3 del Excel extraído a YAML/CSV abiertos, valores de referencia
  (1025 claves) y mapa de fórmulas.
- **Motor** `trawlkit` (fase 2): paños, mecánica de la red, dimensiones, potencia (5 métodos),
  resistencia (13 métodos), portones, bridas, abertura, flotación, lastre, cables y ventana de velocidad;
  modos `excel` (idéntico al libro) y `corrected` (por defecto) con 26 erratas registradas.
- **Informes y planos** (fase 3): HTML, PDF y XLSX; lámina A3 y vista a escala real en SVG.
- **API y aplicación web** (fase 4): FastAPI y React (resumen, gráficos, editor de paneles, plano,
  comparación, descargas, erratas).
- **Libro** (fase 5): Jupyter Book con capítulos de teoría, caso Canal Beagle, validación contra el
  Excel y DynamiT, y bibliografía.
- **Optimización** (fase 6): escalado de redes, búsqueda en malla, frente de Pareto y evolución
  diferencial con búsqueda local.
- **Simulación** (fase 7): forma de la red por elementos triangulares y relajación dinámica (FIRE).
- **Vista previa en línea**: API en Render (Docker) y aplicación en GitHub Pages.

### Corregido
- Resistencia del cable con el ángulo de ataque real, peso de la red por número de paños y par de
  portones en la demanda total del aparejo.

[Sin publicar]: https://github.com/arielgiamportone/trawl-design-lab/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/arielgiamportone/trawl-design-lab/releases/tag/v1.0.0
[0.1.0]: https://github.com/arielgiamportone/trawl-design-lab/commits/0a283a2
