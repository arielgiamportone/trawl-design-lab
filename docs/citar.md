# Cómo citar y versiones

## Citar

Si usás `trawlkit`, la aplicación o este libro en un trabajo, citá la versión que usaste. Cada
versión publicada tiene un DOI propio en [Zenodo](https://zenodo.org/), y el DOI «concepto»
[10.5281/zenodo.23657981](https://doi.org/10.5281/zenodo.23657981) siempre apunta a la última:

| Versión | DOI |
|---|---|
| Todas (concepto) | [10.5281/zenodo.23657981](https://doi.org/10.5281/zenodo.23657981) |
| 1.1.0 | [10.5281/zenodo.23657982](https://doi.org/10.5281/zenodo.23657982) |
 Los metadatos están en
[`CITATION.cff`](https://github.com/arielgiamportone/trawl-design-lab/blob/main/CITATION.cff); en
GitHub, el botón **Cite this repository** los da en APA y BibTeX.

```bibtex
@software{giamportone_trawlkit,
  author    = {Giamportone, Ariel Luján},
  title     = {Trawl Design Lab (trawlkit): diseño y dimensionamiento de redes de arrastre},
  organization = {Universidad Tecnológica Nacional, Facultad Regional Tierra del Fuego},
  version   = {1.1.0},
  year      = {2026},
  publisher = {Zenodo},
  url       = {https://github.com/arielgiamportone/trawl-design-lab},
  doi       = {10.5281/zenodo.23657982}
}
```

El trabajo original en Excel, hecho en Ingeniería Pesquera de la UTN ({doc}`utn`), se cita como
{cite}`giamportone2024`.

## Instalación desde PyPI

```bash
pip install trawlkit                           # motor y CLI
pip install "trawlkit[api,report,optimize,excel]"   # + API, informes PDF/XLSX, optimización y planillas
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
