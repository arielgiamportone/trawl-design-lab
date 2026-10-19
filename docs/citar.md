# Cómo citar y versiones

## Citar

Si usás `trawlkit`, la aplicación o este libro en un trabajo, citá la versión que usaste. Cada
versión publicada tiene un DOI propio en [Zenodo](https://zenodo.org/) (además hay un DOI
«concepto» que siempre apunta a la última). Los metadatos están en
[`CITATION.cff`](https://github.com/arielgiamportone/trawl-design-lab/blob/main/CITATION.cff); en
GitHub, el botón **Cite this repository** los da en APA y BibTeX.

```bibtex
@software{giamportone_trawlkit,
  author    = {Giamportone, Ariel Luján},
  title     = {Trawl Design Lab (trawlkit): diseño y dimensionamiento de redes de arrastre},
  version   = {1.0.0},
  year      = {2026},
  publisher = {Zenodo},
  url       = {https://github.com/arielgiamportone/trawl-design-lab},
  note      = {Completar con el DOI de Zenodo de la versión usada}
}
```

El trabajo original en Excel se cita como {cite}`giamportone2024`.

## Instalación desde PyPI

```bash
pip install trawlkit                           # motor y CLI
pip install "trawlkit[api,report,optimize]"    # + API, informes PDF/XLSX y optimización
python -c "import trawlkit; print(trawlkit.__version__)"
```

Los cambios de cada versión están en el
[registro de cambios](https://github.com/arielgiamportone/trawl-design-lab/blob/main/CHANGELOG.md).

## Publicar una versión (mantenimiento)

La versión vive en un solo lugar, `trawlkit.__version__` (`src/trawlkit/__init__.py`); el
`pyproject.toml` la lee de ahí y un test comprueba que coincida con `web/package.json`,
`web/openapi.json` y `CITATION.cff`.

1. Actualizar la versión en esos archivos, la fecha de `CITATION.cff` y el `CHANGELOG.md`; push a `main`
   con la CI en verde.
2. En GitHub, *Releases → Draft a new release*, tag `vX.Y.Z` (igual a la versión) y **Publish**.
3. El flujo `release.yml` construye la distribución, verifica tag y versión, instala la rueda y la
   publica en PyPI con *Trusted Publishing* (sin tokens guardados). Zenodo archiva el release y
   emite el DOI.

Configuración inicial (una sola vez, la hace el dueño de las cuentas):

- **PyPI**: en <https://pypi.org/manage/account/publishing/>, *Add a new pending publisher* →
  proyecto `trawlkit`, dueño `arielgiamportone`, repositorio `trawl-design-lab`, workflow
  `release.yml`, entorno `pypi`.
- **GitHub**: *Settings → Environments → New environment* `pypi` (opcional: exigir aprobación).
- **Zenodo**: iniciar sesión con GitHub en <https://zenodo.org/account/settings/github/> y activar
  el repositorio `trawl-design-lab` **antes** de publicar el release. Zenodo toma título,
  autores y licencia de `.zenodo.json`.
