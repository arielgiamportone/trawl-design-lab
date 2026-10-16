# trawl-design-lab · `trawlkit`

[English version](README.en.md)

Motor de cálculo, API y documentación científica para el **diseño y dimensionamiento de redes de
arrastre**. Es la evolución del modelo FAO A-3 desarrollado en Excel para buques de 150-180 HP del
Canal Beagle ([repo original](https://github.com/arielgiamportone/Trawl_net_model_in_Advanced_Excel),
[informe en ResearchGate](https://www.researchgate.net/publication/379257264)), reimplementado como
software reproducible, testeado y generalizable a cualquier red parametrizable.

## Qué incluye

| Capa | Carpeta | Estado |
|---|---|---|
| Motor de cálculo (`trawlkit`) | `src/trawlkit/` | Fase 2: potencia, paños, mecánica, dimensiones, resistencia, aparejo (portones, bridas, aberturas, flotación, lastre, cables), ventana de velocidad y `model.run` que los encadena; validado contra el Excel (rtol 1e-6) en modo `EXCEL` |
| Datos y catálogos | `data/` | Fase 1: redes FAO A-3 (estándar y modificada), buques, portones, boyas, cabos, cadenas, cables, tablas de referencia |
| CLI | `src/trawlkit/cli.py` | `trawlkit run` (resumen), `report` (informe HTML/PDF/XLSX/SVG), `plan` (lámina o escala real), `version`, `errata` |
| Planos e informes | `src/trawlkit/drawing/`, `src/trawlkit/report/` | Fase 3: lámina A3 como los planos de 2014, vista a escala real, gráficos SVG, informe HTML/PDF/XLSX ([docs/informes.md](docs/informes.md), ejemplos en [`examples/`](examples/)) |
| API HTTP (FastAPI) | `api/` | Fase 0: `/health` |
| Frontend (React + Vite) | `web/` | Fase 4 |
| Documentación (Jupyter Book, es) | `docs/` | Índice, arquitectura del motor (`docs/motor.md`), informes y planos (`docs/informes.md`), erratas |
| Material original | `legacy/` | Excel, planos, validación DynamiT |

## Cadena de cálculo (del modelo original)

potencia disponible (Fridman, Prado-Dremière, Koyama, Nomura, Hamuro) → paños y cortes → mecánica
de la red (índice de filtración, superficie sólida y de trabajo, solidez, peso) → dimensiones →
resistencia de la red (13 métodos) → portones y bridas → distancia entre puntas de ala y abertura
vertical → flotación y lastre → cables de remolque → ventana de velocidad viable.

## Modos de compatibilidad

El Excel original contiene erratas de cálculo documentadas en [`docs/erratas.md`](docs/erratas.md).
Cada función afectada acepta `compat=Compat.EXCEL` (reproduce el número original, para validar la
migración) o `compat=Compat.CORRECTED` (fórmula correcta, por defecto). La arquitectura del motor y
el orden de las etapas están en [`docs/motor.md`](docs/motor.md).

## Instalación y uso (desarrollo)

```bash
uv sync --all-extras --dev
uv run pytest
uv run trawlkit errata
uv run trawlkit run fao_a3_standard --modified fao_a3_modified --class-vessel fao_a3_180hp --compat excel
uv run trawlkit report fao_a3_standard --modified fao_a3_modified --vessel fao_a3_150hp --out informe/
uv run uvicorn api.main:app --reload   # http://127.0.0.1:8000/health
uv run python tools/extract_excel.py   # regenera data/ y tests/golden/ desde legacy/*.xlsx
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
4. API FastAPI + frontend React
5. Documentación científica (Jupyter Book)
6. Optimización (área barrida vs potencia)
7. Simulación simplificada de la geometría de la red (experimental)
8. Release en PyPI y DOI en Zenodo

## Licencias

Código: [MIT](LICENSE). Documentación, datos y material heredado: [CC BY 4.0](LICENSE-docs).

## Autor

Ariel Luján Giamportone · ALG Data&Engineering Solutions · Ingeniería Pesquera, UTN Ushuaia.
