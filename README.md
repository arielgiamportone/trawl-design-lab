# trawl-design-lab · `trawlkit`

[![PyPI](https://img.shields.io/pypi/v/trawlkit)](https://pypi.org/project/trawlkit/)
[![CI](https://github.com/arielgiamportone/trawl-design-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/arielgiamportone/trawl-design-lab/actions/workflows/ci.yml)
[![Libro](https://img.shields.io/badge/libro-Jupyter%20Book-blue)](https://arielgiamportone.github.io/trawl-design-lab/)

[English version](https://github.com/arielgiamportone/trawl-design-lab/blob/main/README.en.md)

Motor de cálculo, API y documentación científica para el **diseño y dimensionamiento de redes de
arrastre**. Es la evolución del modelo FAO A-3 desarrollado en Excel para buques de 150-180 HP del
Canal Beagle ([repo original](https://github.com/arielgiamportone/Trawl_net_model_in_Advanced_Excel),
[informe en ResearchGate](https://www.researchgate.net/publication/379257264)), reimplementado como
software reproducible, testeado y generalizable a cualquier red parametrizable.

## Qué incluye

| Capa | Carpeta | Estado |
|---|---|---|
| Motor de cálculo (`trawlkit`) | `src/trawlkit/` | Fase 2: potencia, paños, mecánica, dimensiones, resistencia, aparejo (portones, bridas, aberturas, flotación, lastre, cables), ventana de velocidad y `model.run` que los encadena; validado contra el Excel (rtol 1e-6) en modo `EXCEL` |
| Datos y catálogos | `src/trawlkit/data/` | Fase 1: redes FAO A-3 (estándar y modificada), buques, portones, boyas, cabos, cadenas, cables, tablas de referencia. Fase 12: catálogo de 13 redes FAO publicadas y 3 borradores (BOBP/WP/10, /13, /20, Workbook, Schärfe 1983) con procedencia por valor (`data/nets/`, `tools/catalog/`) |
| CLI | `src/trawlkit/cli.py` | `trawlkit run` (resumen), `report` (informe HTML/PDF/XLSX/SVG, con `--optimize` y `--simulate` opcionales), `plan` (lámina o escala real), `optimize`, `serve`, `version`, `errata` |
| Planos e informes | `src/trawlkit/drawing/`, `src/trawlkit/report/` | Fase 3: lámina A3 como los planos de 2014, vista a escala real, gráficos SVG, informe HTML/PDF/XLSX ([docs/informes.md](https://github.com/arielgiamportone/trawl-design-lab/blob/main/docs/informes.md), ejemplos en [`examples/`](https://github.com/arielgiamportone/trawl-design-lab/blob/main/examples/)) |
| Optimización | `src/trawlkit/optimize/` | Fase 6: escala de la red y velocidad de arrastre (área barrida, volumen filtrado o energía) con restricciones de tiro, apertura, cable y portón; malla, frente de Pareto y evolución diferencial (`trawlkit optimize`, [capítulo 20](https://github.com/arielgiamportone/trawl-design-lab/blob/main/docs/20_optimizacion.md)) |
| Simulación de forma | `src/trawlkit/sim/` | Fase 7 (experimental): forma de equilibrio de la red remolcada (elementos triangulares de paño, Morison, boyas, lastre, bridas y fondo; relajación dinámica FIRE), validada contra DynamiT ([capítulo 21](https://github.com/arielgiamportone/trawl-design-lab/blob/main/docs/21_simulacion.md)) |
| API HTTP y frontend | `src/trawlkit/api/`, `web/` | Fase 4: API FastAPI (`trawlkit serve`) y app React con editor de caso y paneles, indicadores, gráficos, plano, comparación y descargas ([docs/web.md](https://github.com/arielgiamportone/trawl-design-lab/blob/main/docs/web.md)); pestañas «Optimizar» y «Simulación» (`POST /optimize`, `POST /simulate`) |
| Documentación (Jupyter Book, es) | `docs/` | Índice, arquitectura del motor (`docs/motor.md`), informes y planos (`docs/informes.md`), erratas |
| Material original | `legacy/` | Excel, planos, validación DynamiT |

## Probar en línea

| | URL |
|---|---|
| Libro (Jupyter Book) | https://arielgiamportone.github.io/trawl-design-lab/ |
| Aplicación web | https://arielgiamportone.github.io/trawl-design-lab/app/ |
| API (documentación interactiva) | https://trawl-design-lab-api.onrender.com/docs |

La app y la API funcionan una vez completados los pasos de publicación (activar GitHub Pages con
fuente «GitHub Actions» y crear el servicio en Render desde `render.yaml`); están descritos en
[docs/despliegue.md](https://github.com/arielgiamportone/trawl-design-lab/blob/main/docs/despliegue.md). La API corre en el plan gratuito de Render: tras un rato
sin uso se duerme y el primer cálculo puede tardar hasta un minuto.

## Cadena de cálculo (del modelo original)

potencia disponible (Fridman, Prado-Dremière, Koyama, Nomura, Hamuro) → paños y cortes → mecánica
de la red (índice de filtración, superficie sólida y de trabajo, solidez, peso) → dimensiones →
resistencia de la red (13 métodos) → portones y bridas → distancia entre puntas de ala y abertura
vertical → flotación y lastre → cables de remolque → ventana de velocidad viable.

## Modos de compatibilidad

El Excel original contiene erratas de cálculo documentadas en [`docs/erratas.md`](https://github.com/arielgiamportone/trawl-design-lab/blob/main/docs/erratas.md).
Cada función afectada acepta `compat=Compat.EXCEL` (reproduce el número original, para validar la
migración) o `compat=Compat.CORRECTED` (fórmula correcta, por defecto). La arquitectura del motor y
el orden de las etapas están en [`docs/motor.md`](https://github.com/arielgiamportone/trawl-design-lab/blob/main/docs/motor.md).

## Instalación

```bash
pip install trawlkit                     # motor y CLI
pip install "trawlkit[api,report,optimize]"   # + API web, informes PDF/XLSX y optimización
trawlkit run fao_a3_standard
```

## Cómo citar

Ver [`CITATION.cff`](https://github.com/arielgiamportone/trawl-design-lab/blob/main/CITATION.cff)
(GitHub ofrece «Cite this repository») y la página
[Cómo citar](https://arielgiamportone.github.io/trawl-design-lab/citar.html) del libro, con el DOI de
Zenodo de cada versión.

## Desarrollo

```bash
uv sync --all-extras --dev
uv run pytest
uv run trawlkit errata
uv run trawlkit run fao_a3_standard --modified fao_a3_modified --class-vessel fao_a3_180hp --compat excel
uv run trawlkit report fao_a3_standard --modified fao_a3_modified --vessel fao_a3_150hp --out informe/
uv run uvicorn api.main:app --reload   # http://127.0.0.1:8000/health
uv run python tools/extract_excel.py   # regenera src/trawlkit/data/ y tests/golden/ desde legacy/*.xlsx
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

## Hoja de ruta

0. Bootstrap del repo ✔
1. Extracción del Excel a datos abiertos y valores de referencia ✔
2. Motor de cálculo validado contra el Excel (rtol 1e-6 en modo `EXCEL`; DynamiT pendiente) ✔
3. CLI, informe (HTML/PDF/XLSX) y plano 2D SVG (lámina y escala real) ✔
4. API FastAPI + frontend React ✔
5. Documentación científica (Jupyter Book): teoría por etapa, caso Beagle, validación contra Excel y DynamiT ✔ — https://arielgiamportone.github.io/trawl-design-lab/
6. Optimización (área barrida vs potencia) ✔
7. Simulación simplificada de la geometría de la red (experimental) ✔
8. Versión 1.0: paquete en PyPI, DOI en Zenodo, `CITATION.cff` y registro de cambios ✔
9. Interfaz con dos modos: asistente guiado (por defecto) y experto; proyectos, deshacer, ayuda contextual ✔
10. Diseño interactivo de la red sobre el plano, con recálculo en vivo y vista 3D ✔
11. Simulador realista: captura en el copo, tipo de fondo y portones acoplados (11.1 ✔);
    ensuciamiento, corriente, energía, huella y explorador animado (11.2 ✔); zoom malla a malla,
    malla T90 y cuadrada, y selectividad (11.3 ✔); incertidumbre, calibración y registros de
    sensores (11.4 ✔)
12. Catálogo de redes públicas (serie FAO) digitalizado con procedencia por valor ✔
13. Carga masiva (Excel/CSV), cálculo por lotes y proyección automática de redes a buques

## Licencias

Código: [MIT](https://github.com/arielgiamportone/trawl-design-lab/blob/main/LICENSE). Documentación, datos y material heredado: [CC BY 4.0](https://github.com/arielgiamportone/trawl-design-lab/blob/main/LICENSE-docs).

## Autor

Ariel Luján Giamportone · ALG Data&Engineering Solutions · Ingeniería Pesquera, UTN Ushuaia.
