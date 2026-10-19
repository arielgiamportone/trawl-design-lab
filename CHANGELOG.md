# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/); el proyecto usa
[versionado semántico](https://semver.org/lang/es/). La versión vive en `trawlkit.__version__`.

## [Sin publicar]

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
