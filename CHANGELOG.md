# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/); el proyecto usa
[versionado semántico](https://semver.org/lang/es/). La versión vive en `trawlkit.__version__`.

## [Sin publicar]

### Agregado
- **Motor, informes y banco docente en inglés (Fase 18.1)**: `trawlkit.i18n` (el texto en
  español es la clave; catálogos `data/i18n/en/*.yaml`, idioma por pedido con `ContextVar` y
  números con punto o coma según el idioma). La API lee `?lang=en` o `Accept-Language` y responde
  con `Content-Language`; el motor sin conexión acepta el mismo `lang`; la CLI suma `--lang en`
  global. Salen en inglés las notas y avisos del motor, la construcción, la economía, los
  sensores, la simulación, los errores de la API y del aula, la ayuda de `/params`, los informes
  HTML, PDF y XLSX, la guía de construcción, la lámina del plano, los lotes y la guía de
  ejercicios. Los ejercicios y laboratorios tienen su versión en inglés y las opciones de las
  preguntas tienen `id` estable, así una entrega se corrige en cualquier idioma. Las salidas en
  español no cambian. Pruebas de catálogo completo (todo texto marcado tiene traducción y los
  mismos campos) y de informes sin palabras españolas; paridad en Pyodide con `lang=en`. Los
  nombres de redes, buques y portones siguen siendo datos y no se traducen.
- **Todo el cálculo sin conexión (Fase 18.2)**: el motor del teléfono atiende también la
  simulación (forma, lance progresivo, explorador, selectividad, incertidumbre y calibración),
  los planos SVG, el informe HTML y XLSX, los registros de sensores y los catálogos de
  ensuciamiento y especies, con guardas de costo propias del teléfono. «Cancelar» corta una
  simulación (también detiene el motor local). Sólo los PDF, el refinamiento con scipy y el aula
  siguen necesitando servidor. Paridad en Pyodide con tolerancia propia para la simulación.
- Libro: capítulo 38 **«Guía para docentes»** (nueva parte «Docencia»): cómo usar la práctica
  libre, los laboratorios y el aula en clase, el banco por capítulo y nivel, cómo se corrige,
  una planificación de 16 semanas para tecnicatura y grado, ejemplos de parcial con datos por
  alumno y de trabajo práctico con rúbrica, privacidad y cómo sumar ejercicios. web.md, utn.md,
  intro, README es/en y hoja de ruta con la fase 17.
- App web, modo **«Aula UTN»** (Fase 17.3): práctica libre con el banco de ejercicios (filtros
  por capítulo y nivel, datos nuevos o los del libro, pistas, corrección por respuesta y
  explicación; sin cuenta y sin conexión) y laboratorios guiados en un panel sobre el modo
  experto que lleva a la pestaña de cada paso, comprueba el caso abierto y corrige las
  preguntas. Aula del curso, en línea: ingreso y alta con código; el alumno ve sus tareas con sus
  propios datos, entrega ejercicios y laboratorios y recibe la corrección según la política de la
  tarea; el docente crea cursos y tareas eligiendo del banco, ve la planilla de notas, revisa
  entregas con nota y comentario, resetea contraseñas y descarga notas (Excel) y enunciados o
  clave por alumno (PDF); la administración genera invitaciones. Pruebas Vitest y E2E (la API
  de las E2E arranca con el aula sobre SQLite); capturas nuevas.
- **Aula UTN en el servidor (Fase 17.2)**: `trawlkit.classroom` y rutas `/classroom`. Cuentas sin
  correo (usuario, nombre o legajo y contraseña con scrypt), alumnos que se registran con el
  código del curso y docentes con un código de invitación del administrador; sesión con token
  *bearer* y bloqueo tras diez intentos fallidos. Cursos, alumnos (reseteo de contraseña por el
  docente), tareas con ejercicios y laboratorios del banco, datos propios por alumno (semilla
  derivada con un secreto de la base), intentos, apertura y cierre, devolución inmediata o al
  cierre; corrección siempre en el servidor; planilla de notas (JSON, XLSX, CSV), revisión del
  docente con nota y comentario, y guía imprimible de enunciados o clave por alumno.
  Postgres (Neon) con `DATABASE_URL`, SQLite en desarrollo; sin base, el aula responde 503 y lo
  demás sigue igual. Extra `classroom`; `trawlkit classroom migrate|create-admin|invite`.
- **Modo docente, banco de ejercicios y laboratorios (Fase 17.1)**: `trawlkit.teaching`. Más de
  40 ejercicios de los capítulos 10 a 37 en tres niveles (básico, intermedio, avanzado), con
  datos que varían por semilla (la 0 son los del libro) y respuestas que calcula el mismo motor;
  corrección con tolerancia por respuesta, números con coma o punto y aviso de unidades.
  Laboratorios guiados sobre la app (paño y resistencia, buque y velocidad, portones,
  profundidad, una red a la medida del buque, del plano al taller) que se comprueban con hechos
  del motor sobre el caso del alumno. `GET /teaching/exercises`, `/teaching/labs`,
  `POST /teaching/grade` y `/teaching/labs/check`, también sin conexión;
  `trawlkit exercises list|show|solve|sheet` (guía imprimible de enunciados o clave en HTML o
  PDF). Libro: sección «Ejercicios» al final de los capítulos de teoría y aplicaciones.
- **Economía de la operación (Fase 16)**: `trawlkit.economics`. Por velocidad de arrastre,
  gasoil y lubricante (arrastre con la resistencia del motor, navegación y maniobras), captura
  proporcional al área barrida por hora, ingreso (captura × precio en playa o mezcla de
  especies), tripulación «a la parte» (antes o después de los gastos compartidos) o a jornal,
  amortización y reparación de la red y el aparejo (del costo cargado o de la lista de
  materiales con precios), gastos de la marea y fijos anuales; margen, costo por kg, precio de
  equilibrio, la velocidad de mayor margen, la de menor costo por kg y la de menos gasoil por
  kg, y el año. Sin precios no se inventan: los rubros sin dato quedan fuera y se avisan.
  `POST /economics` y `/economics/compare` (ahorro anual y repago del armado), también sin
  conexión; `trawlkit economics`; en los lotes de flota, gasoil, captura, costo por kg y margen
  por buque.
- App web, pestaña **«Economía»**: datos de la operación (precios en blanco, guardados en el
  navegador), resumen a la velocidad de mayor margen, curva de ingreso, costo y margen con la
  franja remolcable, tabla por velocidad, reparto del costo y comparación con otra red del
  catálogo (ahorro y repago); «Sumar la economía de la marea» en Lotes y flota; en el modo
  guiado, «¿Cuánto deja la marea?». Libro: capítulo 37 «Economía de la operación».
- **Guía de construcción (Fase 15)**: `trawlkit.construction` pasa del diseño al taller. Hoja de
  corte por paño (mallas, piezas, el ciclo de cada corte explicado, rectángulo de paño y
  desperdicio; las alas se cortan de a pares encastradas), paño a comprar por calidad, uniones
  paso a paso con la regla de toma cuando cambia la cantidad de mallas, montaje en relingas
  (coeficiente de armado y mallas por metro, con aviso si el cabo es más largo que el paño),
  posición de las boyas, zonas de lastre y cortes de cabos, cables y cadenas con sobrante por
  gaza. Salidas: `trawlkit build-guide` (PDF, HTML, XLSX, JSON), `POST /design/construction` y
  `/design/construction/export` (también sin conexión, salvo el PDF) y una sección
  «Construcción y materiales» en el informe del caso, con la lista de materiales.
- App web, pestaña **«Construcción»**: hoja de corte con casillas por pieza, armado paso a paso
  (una unión por vez en letra grande, «Hecho, siguiente →» y el plano con los dos paños
  resaltados), montaje en relingas con la línea de boyas y el lastre, cortes de cabos con el
  sobrante por gaza ajustable, avance del taller guardado en el navegador y descargas (PDF, XLSX,
  imprimir). En el modo guiado, «¿Cómo la armo? Guía para el taller». Funciona sin conexión salvo
  el PDF.
- Libro: capítulo 36 «Del diseño al taller: guía de construcción» (ciclos de corte, tomas,
  coeficiente de armado, boyas, lastre y cortes; la guía de todo el catálogo) y referencia Klust
  (1982), verificada.
- DOI de Zenodo (10.5281/zenodo.23657981, todas las versiones) en el README, `CITATION.cff`, la
  página «Cómo citar» y la introducción del libro.

## [1.1.0] - 2026-10-26

Primera versión publicada en PyPI y archivada en Zenodo.

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
- **Catálogo de redes FAO (Fase 12)**:
  - procedencia por valor (`NetSpec.provenance`, `trawlkit.provenance`): documento, página,
    figura y tipo (Excel, transcripto, derivado, supuesto) de cada número de la red;
  - validador de consistencia `trawlkit.netcheck`: empalmes (error por encima de 20 %: los
    planos fruncen hasta 18 %), bocana, costuras laterales, cortes contra mallas
    (`netting.cut_code_ratio`), costados de las redes de 4 paneles y datos;
  - 16 redes digitalizadas (`data/nets/`, `tools/catalog/`), 13 publicadas y 3 borradores:
    *Fisherman's Workbook*, BOBP/WP/10, /13 y /20 (fondo de gran abertura, uno y dos barcos) y
    Schärfe 1983 (pelágicas de 4 paneles, con las aberturas medidas en el mar);
  - motor generalizado: dimensiones genéricas para redes sin la estructura de la A-3 o con los
    largos de relinga del plano (`trawlkit.topology`), arrastre de **pareja**
    (`DesignCase.rig`, `pair_wing_spread_m`; sin portones, tiro de dos buques), redes de
    **4 paneles** (red equivalente de 2 paneles; costados en la disposición, la lámina y la escala
    real), redes **pelágicas** (sin fondo en el simulador, rozamiento nulo) y separación de
    portones de Fridman (`door_spread_rule`);
  - `trawlkit.catalog.catalog_case`: caso de diseño de cada red con su buque, portón y
    profundidad; lo usan `trawlkit run <red>` y `POST /design` sin buque ni portón;
  - API: `GET /catalog/nets` con familia, aparejo, potencia, estado, fuente, validador y
    cobertura (`?status=`); `GET /catalog/nets/{id}/provenance` y `/check`; `/health` informa
    `nets_failed`;
  - web: pestaña «Catálogo FAO» (filtros, procedencia valor por valor, validador, «Usar esta
    red») y, en el modo guiado, redes filtradas por la potencia del buque;
  - capítulo 33 «Catálogo de redes FAO», con la comparación del motor y el simulador entre sí y
    con las aberturas medidas por Schärfe.
- **Catálogo de componentes (Fase 13.1)**:
  - `trawlkit.components`: paño e hilo, cables de acero, cabos, portones, boyas y cadenas, con
    marca, región, genérico equivalente, estado, precio orientativo opcional y procedencia por
    valor;
  - 290 ítems (`data/components/`, `tools/components/`):
    - genéricos ajustados a las tablas del FAO *Fisherman's Workbook* (hilos, cabos, cables,
      boyas, cadenas y portones por potencia);
    - datos puntuales de Garware, Bridon-Bekaert y PFEIFER;
    - puertas de la flota camaronera colombiana (FAO REBYC);
    - los catálogos del libro Excel de la A-3;
  - validador físico de cada ítem (peso, rotura, tenacidad, flotación, polar);
  - API: `GET /catalog/components[/{kind}[/{id}]]` con filtros y `POST /components/check`.
- **Motor y optimizador con componentes (Fase 13.2)**:
  - `DesignCase` acepta componentes del catálogo: `warp_id`, `float_id`, `twine_id` (hilo de
    todos los paños salvo el copo), `chain_id` y filtros de la selección automática
    (`component_brands`, `component_region`, `generic_only`); sin ellos, la A-3 no cambia;
  - portones del catálogo de componentes por id en la API; en modo corregido, la polar del portón
    se interpola entre ángulos vecinos (en modo Excel el ángulo sigue debiendo estar en la polar);
  - `trawlkit.cost.bill_of_materials`: lista de materiales con cantidades y costo orientativo por
    moneda; un precio faltante se informa, nunca se toma como cero;
  - `trawlkit.optimize.optimise_components`: elige portón, cable, boyas e hilo del catálogo
    filtrado por mínima resistencia, mínimo R_T/AH o mínimo costo, con las restricciones de tiro,
    red abierta, cable, portón, profundidad de las boyas y rotura del hilo, y da alternativas
    (una genérica si el mejor armado lleva marcas);
  - API: `POST /design/bom` y `POST /optimize/components`; `params` admite booleanos en los
    campos booleanos.
- **Acceso: web, aportes y uso sin conexión (Fase 13.3)**:
  - pestaña «Componentes»: catálogo con filtros y ficha (procedencia, validador, genérico
    equivalente, «Usar en el caso»), lista de materiales con precios del usuario (CSV e
    impresión/PDF), «Armar con el catálogo» y aportes de usuarios (validados, guardados en el
    navegador como «aporte, sin verificar», exportables y proponibles como *issue* con la
    plantilla `.github/ISSUE_TEMPLATE/componente.yml`);
  - API: `components` (aportes en línea, sólo para ese pedido) en `/design`, `/design/bom` y
    `/optimize/components`; una red del catálogo FAO con un portón elegido conserva su buque;
  - PWA instalable (`vite-plugin-pwa`) y motor sin conexión: Pyodide 0.29.5 con la *wheel* de
    trawlkit en un *Web Worker* (`trawlkit.api.offline`, las mismas rutas que la API), descargado
    con «Preparar uso sin conexión»; prueba de paridad en Node contra CPython y e2e sin red;
  - modo de bajo consumo de datos (sin vistas 3D ni simulación);
  - pint se carga al primer uso de `trawlkit.ureg`/`trawlkit.Q_` (el motor no lo necesita);
  - capítulo 34 «Componentes: catálogos, equivalencias y costo».
- **Carga masiva, lotes y proyección de redes a buques (Fase 14.1)**:
  - `trawlkit.batch`: lectura de planillas CSV y XLSX de flotas, redes (paneles) y casos, con
    nombres de columna en español o inglés, unidades convertibles (kW, ft, m/s…), coma decimal y
    observaciones por fila y columna sin abortar el lote; plantillas con hoja de ayuda;
  - redes desde planilla, validadas con `netcheck` (con errores quedan como borrador); la A-3
    exportada a planilla y releída da el mismo resultado;
  - `project_net`: proyección de una red a otro buque (escala por semejanza de potencia
    s₀ = √(P/P_diseño), la mayor escala factible entre 0,7·s₀ y 1,3·s₀ a la velocidad del buque o
    entre 2 y 4 kn, portón escalado y armado del catálogo de componentes);
  - lotes de flota × red, de casos (cualquier parámetro de `GET /params` como columna) y de
    redes; exportación CSV y XLSX (resumen, materiales, redes escaladas) e informe HTML/PDF con
    una ficha por buque;
  - CLI `trawlkit batch` (y `--template`); API `/batch/parse`, `/batch/run`, `/batch/export`,
    `/batch/template`, también en el motor sin conexión (salvo el PDF).
- **Lotes en la web, sin conexión e informe (Fase 14.2)**:
  - pestaña «Lotes y flota»: plantillas, carga de CSV/XLSX, vista previa editable de la flota,
    cálculo por tramos con avance y cancelación, resultados con semáforos y filtro, «Abrir este
    caso» (red escalada, buque y portón del lote en línea) y descargas XLSX, CSV, PDF e
    impresión; el último lote queda en IndexedDB; enlace desde el modo guiado;
  - el motor sin conexión calcula lotes y escribe planillas: openpyxl y et_xmlfile viajan con la
    wheel (`tools/offline_bundle.py`), y las respuestas binarias pasan por el *worker*;
  - informe del lote en HTML/PDF con una ficha por buque y su lámina;
  - capítulo 35 «Flotas, lotes y proyección de redes».
- Cables: si ningún cable del catálogo alcanza la carga de rotura, se elige el más grueso con la
  nota `warp_undersized` (antes, error).
- Web: vista «Lance progresivo» con gráficos contra la captura y 3D por paso (tensión o contacto
  con el fondo); tipo de fondo y captura esperada en el modo guiado.
- `/health` informa la huella de rutas (`contract`) y el commit desplegado; la app avisa «API
  desactualizada» si la API en línea es de otra versión, y un 404 de ruta lo explica. El flujo
  «Docs» comprueba la API en línea al terminar (`tools/check_api_contract.py`).

- Libro: capítulo 22 «Simulación con captura, fondo y portones acoplados», con el panorama de
  simuladores del mercado; 7 referencias nuevas (6 verificadas en Crossref).
- **Documentación, identidad UTN**: README en castellano e inglés reescritos (banner, capturas,
  capacidades, arquitectura, cadena de cálculo, indicadores, hoja de ruta) y sección «Nacido en la
  UTN» con las tres Facultades Regionales de Ingeniería Pesquera (FRTDF, FRCh y FRMDP); página
  `docs/utn.md` del libro, el emblema como logo del libro y el pie de la app con las tres Facultades.
  El emblema es un dibujo propio, no un logo oficial.
- Figuras SVG con tema claro y oscuro (`tools/make_figures.py`, `docs/_static/img/`): emblema,
  banner, arquitectura, cadena de cálculo, fases y flujo de flota, en castellano e inglés.
- Indicadores del README calculados del código y los datos (`tools/readme_stats.py`, con
  `--check`); `tests/test_readme.py` verifica que estén al día y que las imágenes tengan URL
  absoluta (PyPI).
- Capturas de la app regeneradas con `npm run screenshots` (12 vistas: modo guiado, experto,
  diseño interactivo, 3D, selectividad, optimizar, catálogo, componentes, lotes, teléfono y sin
  conexión).
- `CITATION.cff` y `.zenodo.json`: afiliación (UTN, Facultad Regional Tierra del Fuego) y palabras
  clave de Ingeniería Pesquera.
- Libro: introducción con todas las partes (capítulos 22 a 25 y 33 a 35), módulos nuevos en
  `docs/motor.md` y el motor sin conexión en `docs/despliegue.md`.

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
