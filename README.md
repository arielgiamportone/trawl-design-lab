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
| Motor de cálculo (`trawlkit`) | `src/trawlkit/` | Fase 1: esqueleto, unidades, registro de erratas, esquema de specs y loader |
| Datos y catálogos | `data/` | Fase 1: redes FAO A-3 (estándar y modificada), buques, portones, boyas, cabos, cadenas, cables, tablas de referencia |
| CLI | `src/trawlkit/cli.py` | Fase 0: `trawlkit version`, `trawlkit errata` |
| API HTTP (FastAPI) | `api/` | Fase 0: `/health` |
| Frontend (React + Vite) | `web/` | Fase 4 |
| Documentación (Jupyter Book, es) | `docs/` | Fase 0: índice + erratas |
| Material original | `legacy/` | Excel, planos, validación DynamiT |

## Cadena de cálculo (del modelo original)

potencia disponible (Fridman, Prado-Dremière, Koyama, Nomura, Hamuro) → paños y cortes → mecánica
de la red (índice de filtración, superficie sólida y de trabajo, solidez, peso) → dimensiones →
resistencia de la red (13 métodos) → portones y bridas → distancia entre puntas de ala y abertura
vertical → flotación y lastre → cables de remolque → ventana de velocidad viable.

## Modos de compatibilidad

El Excel original contiene erratas de cálculo documentadas en [`docs/erratas.md`](docs/erratas.md).
Cada función afectada acepta `compat=Compat.EXCEL` (reproduce el número original, para validar la
migración) o `compat=Compat.CORRECTED` (fórmula correcta, por defecto).

## Instalación y uso (desarrollo)

```bash
uv sync --all-extras --dev
uv run pytest
uv run trawlkit errata
uv run uvicorn api.main:app --reload   # http://127.0.0.1:8000/health
uv run python tools/extract_excel.py   # regenera data/ y tests/golden/ desde legacy/*.xlsx
```

```python
from trawlkit.io import load_net, load_vessels

net = load_net("fao_a3_standard")  # 10 paneles A..J con procedencia de celda
v150 = load_vessels().vessels[0]  # 150 BHP
```

## Hoja de ruta

0. Bootstrap del repo ✔
1. Extracción del Excel a datos abiertos y valores de referencia ✔
2. Motor de cálculo validado contra el Excel (tolerancia 1 %) y contra DynamiT
3. CLI, informe y plano 2D SVG
4. API FastAPI + frontend React
5. Documentación científica (Jupyter Book)
6. Optimización (área barrida vs potencia)
7. Simulación simplificada de la geometría de la red (experimental)
8. Release en PyPI y DOI en Zenodo

## Licencias

Código: [MIT](LICENSE). Documentación, datos y material heredado: [CC BY 4.0](LICENSE-docs).

## Autor

Ariel Luján Giamportone · ALG Data&Engineering Solutions · Ingeniería Pesquera, UTN Ushuaia.
