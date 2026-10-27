<p align="center">
  <img src="https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/docs/_static/img/banner.svg" alt="trawl-design-lab · trawlkit: diseño de redes de arrastre, nacido en la Ingeniería Pesquera de la UTN (FRTDF, FRCh y FRMDP)" width="100%">
</p>

<p align="center">
  <a href="https://github.com/arielgiamportone/trawl-design-lab/actions/workflows/ci.yml"><img src="https://github.com/arielgiamportone/trawl-design-lab/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/arielgiamportone/trawl-design-lab/actions/workflows/docs.yml"><img src="https://github.com/arielgiamportone/trawl-design-lab/actions/workflows/docs.yml/badge.svg" alt="Docs"></a>
  <a href="https://pypi.org/project/trawlkit/"><img src="https://img.shields.io/pypi/v/trawlkit" alt="PyPI"></a>
  <a href="https://pypi.org/project/trawlkit/"><img src="https://img.shields.io/pypi/pyversions/trawlkit" alt="Python"></a>
  <a href="https://github.com/arielgiamportone/trawl-design-lab/blob/main/LICENSE"><img src="https://img.shields.io/badge/c%C3%B3digo-MIT-blue" alt="Código: MIT"></a>
  <a href="https://github.com/arielgiamportone/trawl-design-lab/blob/main/LICENSE-docs"><img src="https://img.shields.io/badge/docs%20y%20datos-CC%20BY%204.0-blue" alt="Docs y datos: CC BY 4.0"></a>
  <a href="https://arielgiamportone.github.io/trawl-design-lab/"><img src="https://img.shields.io/badge/libro-Jupyter%20Book-c35a1b" alt="Libro"></a>
  <a href="https://arielgiamportone.github.io/trawl-design-lab/app/"><img src="https://img.shields.io/badge/app-funciona%20sin%20conexi%C3%B3n-2e7d32" alt="App: funciona sin conexión"></a>
  <a href="https://doi.org/10.5281/zenodo.23657981"><img src="https://zenodo.org/badge/DOI/10.5281/zenodo.23657981.svg" alt="DOI 10.5281/zenodo.23657981"></a>
  <a href="https://arielgiamportone.github.io/trawl-design-lab/citar.html"><img src="https://img.shields.io/badge/c%C3%B3mo-citar-6a4c93" alt="Cómo citar"></a>
</p>

<p align="center"><a href="https://github.com/arielgiamportone/trawl-design-lab/blob/main/README.en.md">English version</a></p>

**trawl-design-lab** es un laboratorio abierto para **diseñar, dimensionar y probar redes de
arrastre**: un motor de cálculo en Python (`trawlkit`), una aplicación web que funciona en el
teléfono aun sin señal, una API y un libro reproducible con la teoría. Está pensado para
pescadores y patrones, técnicos de redes, escuelas de pesca y estudiantes e ingenieros pesqueros:
elegir la red que el buque puede remolcar, a qué velocidad, con qué portones, cables y boyas, y
cuánto cuesta armarla con lo que se consigue en el puerto.

| Probar | |
|---|---|
| 📱 Aplicación web (instalable, sin conexión) | https://arielgiamportone.github.io/trawl-design-lab/app/ |
| 📘 Libro (Jupyter Book) | https://arielgiamportone.github.io/trawl-design-lab/ |
| 🔌 API (documentación interactiva) | https://trawl-design-lab-api.onrender.com/docs |

La API corre en el plan gratuito de Render: tras un rato sin uso se duerme y el primer cálculo puede
tardar hasta un minuto (la app usa entonces el motor del teléfono).

## Nacido en la UTN

<img src="https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/docs/_static/img/emblema-utn-pesquera.svg" alt="Emblema: la costa atlántica argentina con Mar del Plata, Puerto Madryn y Ushuaia, y una red de arrastre" width="220" align="right">

Este proyecto empezó en las aulas de **Ingeniería Pesquera de la Universidad Tecnológica Nacional**,
en la Facultad Regional Tierra del Fuego, con el primer trabajo en el que su autor aprendió a
calcular una red de arrastre: el dimensionamiento de la red FAO A-3 para los pesqueros de
150-180 HP del Canal Beagle, resuelto en una planilla de Excel de unas 5 500 fórmulas
([repositorio original](https://github.com/arielgiamportone/Trawl_net_model_in_Advanced_Excel),
[informe en ResearchGate](https://www.researchgate.net/publication/379257264)).

Ese libro de cálculo es hoy `trawlkit`: cada fórmula migrada, validada contra el Excel y con sus
erratas documentadas y corregidas, generalizada a cualquier red y ampliada con catálogos,
optimización, simulación y una app para usar en el muelle. El proyecto se dedica a las tres
Facultades Regionales donde se dicta **Ingeniería Pesquera**, sobre el Mar Argentino:

- **FRTDF** · Facultad Regional Tierra del Fuego, Ushuaia — https://www.frtdf.utn.edu.ar/
- **FRCh** · Facultad Regional Chubut, Puerto Madryn — https://www.frch.utn.edu.ar/
- **FRMDP** · Facultad Regional Mar del Plata — https://mdp.utn.edu.ar/

<sub>El emblema es un dibujo propio del proyecto, no un logo oficial de la UTN.</sub>

<br clear="right">

## Capturas

| | |
|---|---|
| ![Modo guiado: el diagnóstico con semáforos de potencia, velocidad y cable](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/guiado-diagnostico.png) | ![Modo experto: el caso de diseño y sus indicadores](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-claro-caso.png) |
| **Modo guiado**: cuatro pasos y un diagnóstico en lenguaje llano | **Modo experto**: caso, indicadores y tablas de cada etapa |
| ![Diseño interactivo: los paneles sobre el plano, con tiradores](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-diseno-interactivo.png) | ![Simulación de la forma de la red en 3D, coloreada por tensión](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-simulacion-3d.png) |
| **Diseño interactivo** sobre el plano, con recálculo en vivo | **Simulación 3D** de la forma de la red remolcada |
| ![Catálogo FAO con la procedencia de cada valor y el validador](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-catalogo-fao.png) | ![Lista de materiales con componentes del catálogo](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-componentes.png) |
| **Catálogo FAO** con procedencia valor por valor | **Componentes**: lista de materiales y costo |
| ![Lotes: una red proyectada a cada buque de la flota](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-lotes.png) | ![Selectividad del copo: rombo frente a T90](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-selectividad.png) |
| **Lotes y flota**: la red para cada buque del puerto | **Selectividad**: qué tallas retiene el copo |
| ![Gráficos en tema oscuro: tiro disponible y resistencia](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-oscuro-graficos.png) | ![En el teléfono, sin conexión, con el motor del teléfono](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/movil-sin-conexion.png) |
| **Gráficos** (tema oscuro) | **Sin conexión**: el motor corre en el teléfono |
| ![Construcción: armado paso a paso con el plano resaltado](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-construccion.png) | ![La guía para el taller en el teléfono](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/movil-guia-taller.png) |
| **Construcción**: hoja de corte, uniones y montaje | **Guía para el taller** en el teléfono, paso a paso |
| ![Economía: margen por velocidad y reparto del costo](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-economia.png) | ![Optimizar: mejor diseño, región factible y frente de Pareto](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-claro-optimizar.png) |
| **Economía**: margen, costo por kg y velocidad más rentable | **Optimizar**: escala de la red y velocidad |
| ![Aula UTN: planilla de notas del docente](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-aula-docente.png) | ![Laboratorio guiado sobre la app](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/web/docs/screenshots/escritorio-aula-laboratorio.png) |
| **Aula UTN**: cursos, tareas con datos por alumno y notas | **Laboratorio guiado**: cada paso se comprueba con el caso abierto |

## Qué hace

- **Diseño y dimensionamiento**: potencia disponible, paños y cortes, mecánica de la red,
  dimensiones, resistencia por 13 métodos, portones y bridas, aberturas, flotación y lastre,
  cables y ventana de velocidad. Plano técnico A3 y a escala real, informe HTML, PDF y XLSX.
- **Catálogo FAO**: redes de fondo y pelágicas de la serie FAO y BOBP digitalizadas con la
  procedencia de cada valor (documento, página, tipo) y un validador de consistencia.
- **Componentes y costo**: paño, cables, cabos, portones, boyas y cadenas, con equivalentes
  genéricos y datos puntuales de fabricantes; lista de materiales, costo orientativo y armado
  óptimo con lo que se consigue en el puerto.
- **Optimización**: escala de la red y velocidad (área barrida, volumen filtrado o energía) con
  restricciones de tiro, apertura, cable y portón.
- **Simulación**: forma de equilibrio de la red en 3D (validada contra DynamiT), captura en el
  copo, tipo de fondo, corriente, ensuciamiento, energía y huella.
- **Selectividad**: malla rombo, T90 y cuadrada; tallas retenidas por especie.
- **Incertidumbre y calibración**: bandas por muestreo, tornado de sensibilidad y ajuste a
  registros de sensores.
- **Lotes y flota**: planillas de flota, redes y casos (CSV o XLSX); una red probada proyectada a
  cada buque por semejanza y refinada con el motor.
- **Guía de construcción**: del diseño al taller. Paño a comprar, hoja de corte con el ciclo de
  cada corte, uniones paso a paso con sus tomas, montaje en relingas (mallas por metro), boyas,
  lastre y cortes de cabos; en PDF para imprimir, planilla y paso a paso en el teléfono.
- **Economía de la operación**: gasoil, captura, costos por rubro y margen de la marea a cada
  velocidad, con los precios del puerto; la velocidad más rentable, la comparación entre redes y
  el repago de una red nueva, también en los lotes de flota.
- **Aula UTN**: ejercicios de los capítulos con datos que cambian y corrección automática,
  laboratorios guiados sobre la app y un aula con cursos, tareas, entregas y notas para la
  tecnicatura y el grado.
- **Sin conexión**: la app se instala y el mismo motor corre en el teléfono (Pyodide).

## Arquitectura

![Arquitectura: datos y catálogos alimentan el motor trawlkit, que sirve a la CLI, la API, el motor sin conexión, la app web y el libro](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/docs/_static/img/arquitectura.svg)

Un solo motor (`src/trawlkit/`) y una sola fuente de datos (`src/trawlkit/data/`) para todo: la
CLI, la API FastAPI (`src/trawlkit/api/`), el motor sin conexión que la app carga en un *Web
Worker*, la app React (`web/`) y el libro (`docs/`), cuyos números salen de ejecutar el motor. La
arquitectura del motor está en [docs/motor.md](https://github.com/arielgiamportone/trawl-design-lab/blob/main/docs/motor.md).

## Cadena de cálculo

![Cadena de cálculo: potencia, paños, mecánica, dimensiones, resistencia, portones, aberturas, flotación, cables y ventana de velocidad](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/docs/_static/img/cadena-calculo.svg)

La misma cadena del modelo original, etapa por etapa, cada una con su capítulo en el
[libro](https://arielgiamportone.github.io/trawl-design-lab/). Para una flota, la proyección
encadena semejanza, refinado y armado:

![Flujo de flota: planilla, proyección por semejanza, refinado y armado, resultados](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/docs/_static/img/flujo-flota.svg)

## Indicadores

<!-- indicadores:inicio -->
![redes: 26](https://img.shields.io/badge/redes-26-1c5cab) ![componentes: 564](https://img.shields.io/badge/componentes-564-1c5cab) ![rutas API: 79](https://img.shields.io/badge/rutas%20API-79-1c5cab) ![capítulos: 40](https://img.shields.io/badge/cap%C3%ADtulos-40-c35a1b) ![Excel rtol: 1e-6](https://img.shields.io/badge/Excel%20rtol-1e--6-2e7d32)

| Indicador | Valor |
|---|---|
| Redes en el catálogo | 26 (17 publicadas, 9 borradores), con procedencia valor por valor |
| Componentes | 564 en 7 tipos (244 genéricos y datos puntuales de 15 marcas) |
| Métodos de resistencia de la red | 13 |
| Erratas del Excel documentadas y corregidas | 26 |
| Valores de referencia del Excel | 697, reproducidos con rtol 1e-6 en modo `excel` |
| Motor sin conexión (Pyodide) | paridad con CPython, rtol 1e-9 |
| Especies y tipos de fondo | 8 especies · 5 fondos |
| Rutas de la API | 79 |
| Capítulos del libro | 40 · 132 referencias |

<sub>Generado por `tools/readme_stats.py`; `tests/test_readme.py` verifica que esté al día.</sub>
<!-- indicadores:fin -->

## Instalación y uso

```bash
pip install trawlkit                            # motor y CLI
pip install "trawlkit[api,report,optimize,excel]"   # + API, informes PDF/XLSX, optimización y planillas
```

```bash
trawlkit run fao_a3_standard                    # resumen del caso
trawlkit report fao_a3_standard --vessel fao_a3_150hp --out informe/   # HTML, PDF, XLSX y plano
trawlkit optimize fao_a3_standard               # escala y velocidad óptimas
trawlkit batch flota.xlsx --net fao_wb_bt2p_60hp -o lote.xlsx         # una red para cada buque
trawlkit batch --template plantilla.xlsx        # plantilla de flota con su hoja de ayuda
trawlkit build-guide fao_a3_standard -o guia.pdf    # guía de construcción para el taller
trawlkit economics fao_a3_standard --fuel-price 1200 --catch-kg-h 150 --price-kg 1000
trawlkit exercises sheet --chapter 14_resistencia --key -o clave.pdf
trawlkit serve                                  # API en http://127.0.0.1:8000/docs
trawlkit errata                                 # erratas del Excel original
```

```python
from trawlkit import Compat, DesignCase, run
from trawlkit.io import load_doors, load_net, load_vessels

vessels = {v.id: v for v in load_vessels().vessels}
case = DesignCase(
    net=load_net("fao_a3_standard"),  # 10 paneles A..J con procedencia de celda
    net_modified=load_net("fao_a3_modified"),  # columna G del libro (bolsa de 30 mm)
    vessel=vessels["fao_a3_150hp"],
    class_vessels=(vessels["fao_a3_180hp"],),  # el libro calcula 150 y 180 BHP lado a lado
    door=load_doors().doors[0],  # portón plano FAO
    compat=Compat.CORRECTED,  # o Compat.EXCEL para reproducir el libro
)
result = run(case)
result.summary()["horizontal_opening_m"]  # 'Dimensiones de la Red'!F61
result.performance.design.max_speed_kn  # velocidad máxima remolcable [kn]
```

### Modos `excel` y `corrected`

El Excel original tiene erratas de cálculo, documentadas en
[docs/erratas.md](https://github.com/arielgiamportone/trawl-design-lab/blob/main/docs/erratas.md).
Cada función afectada acepta `compat=Compat.EXCEL`, que reproduce el número del libro para validar
la migración, o `compat=Compat.CORRECTED`, la fórmula correcta y el modo por defecto.

### Desarrollo

```bash
uv sync --all-extras --dev
uv run pytest                                   # motor, API, planillas, indicadores del README
uv run ruff check . && uv run mypy
uv run python tools/readme_stats.py             # actualiza los indicadores de los README
uv run python tools/make_figures.py             # regenera el emblema y los diagramas
uv run python tools/extract_excel.py            # regenera datos y valores de referencia del Excel
cd web && npm ci && npm run dev                 # app en http://localhost:5173
cd web && npm run screenshots                   # regenera las capturas de este README
```

El despliegue (GitHub Pages para el libro y la app, Render para la API) está en
[docs/despliegue.md](https://github.com/arielgiamportone/trawl-design-lab/blob/main/docs/despliegue.md).

## Hoja de ruta

![Fases 0 a 17 del proyecto](https://raw.githubusercontent.com/arielgiamportone/trawl-design-lab/main/docs/_static/img/fases.svg)

| Fase | Qué agregó |
|---|---|
| 0–2 | Repositorio, extracción del Excel a datos abiertos y motor validado contra el libro (rtol 1e-6) |
| 3–5 | CLI, informes y planos; API y app web; libro con la teoría, el caso Beagle y la validación |
| 6–8 | Optimización, simulación de la forma (DynamiT) y versión 1.0 (PyPI, Zenodo, `CITATION.cff`) |
| 9–10 | Modo guiado y experto, proyectos y deshacer; diseño interactivo sobre el plano y vista 3D |
| 11 | Simulador realista: captura y fondo, mar real, malla y selectividad, incertidumbre y calibración |
| 12 | Catálogo de redes FAO con procedencia valor por valor |
| 13 | Componentes con equivalentes genéricos, costo, armado óptimo y uso sin conexión |
| 14 | Planillas de flota, cálculo por lotes y proyección de una red a cada buque |
| 15 | Guía de construcción para el taller: corte, armado, montaje en relingas y cortes de cabos |
| 16 | Economía de la operación: costo, margen y velocidad más rentable; comparación y repago |
| 17 | Modo docente «Aula UTN»: banco de ejercicios, laboratorios guiados, cursos, tareas y notas |

El detalle de cada versión está en el [CHANGELOG](https://github.com/arielgiamportone/trawl-design-lab/blob/main/CHANGELOG.md).

## Cómo citar

Ver [`CITATION.cff`](https://github.com/arielgiamportone/trawl-design-lab/blob/main/CITATION.cff)
(GitHub ofrece «Cite this repository») y la página
[Cómo citar](https://arielgiamportone.github.io/trawl-design-lab/citar.html) del libro. DOI de Zenodo
(todas las versiones): [10.5281/zenodo.23657981](https://doi.org/10.5281/zenodo.23657981).

## Licencias

Código: [MIT](https://github.com/arielgiamportone/trawl-design-lab/blob/main/LICENSE).
Documentación, datos y material heredado: [CC BY 4.0](https://github.com/arielgiamportone/trawl-design-lab/blob/main/LICENSE-docs).

## Autor

**Ariel Luján Giamportone** · Ingeniería Pesquera, Universidad Tecnológica Nacional, Facultad
Regional Tierra del Fuego · ALG Data&Engineering Solutions.
