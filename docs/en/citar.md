# How to cite and versions

## Citing

If you use `trawlkit`, the application or this book in a piece of work, cite the version you
used. Each published version has its own DOI on [Zenodo](https://zenodo.org/), and the “concept”
DOI [10.5281/zenodo.23657981](https://doi.org/10.5281/zenodo.23657981) always points to the
latest one:

| Version | DOI |
|---|---|
| All (concept) | [10.5281/zenodo.23657981](https://doi.org/10.5281/zenodo.23657981) |
| 1.1.0 | [10.5281/zenodo.23657982](https://doi.org/10.5281/zenodo.23657982) |
 The metadata are in
[`CITATION.cff`](https://github.com/arielgiamportone/trawl-design-lab/blob/main/CITATION.cff); on
GitHub, the **Cite this repository** button gives them in APA and BibTeX.

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

The original Excel work, done in Fisheries Engineering at UTN ({doc}`utn`), is cited as
{cite}`giamportone2024`.

## Installing from PyPI

```bash
pip install trawlkit                           # engine and CLI
pip install "trawlkit[api,report,optimize,excel]"   # + API, PDF/XLSX reports, optimization and spreadsheets
python -c "import trawlkit; print(trawlkit.__version__)"
```

The changes of each version are in the
[changelog](https://github.com/arielgiamportone/trawl-design-lab/blob/main/CHANGELOG.md).

## Publishing a version (maintenance)

The version lives in a single place, `trawlkit.__version__` (`src/trawlkit/__init__.py`); the
`pyproject.toml` reads it from there and a test checks that it matches `web/package.json`,
`web/openapi.json` and `CITATION.cff`.

1. Update the version in those files, the date of `CITATION.cff` and the `CHANGELOG.md`; push to
   `main` with green CI.
2. On GitHub, *Releases → Draft a new release*, tag `vX.Y.Z` (equal to the version) and
   **Publish**.
3. The `release.yml` workflow builds the distribution, checks tag and version, installs the wheel
   and publishes it on PyPI with *Trusted Publishing* (no stored tokens). Zenodo archives the
   release and issues the DOI.

Initial configuration (only once, done by the owner of the accounts):

- **PyPI**: at <https://pypi.org/manage/account/publishing/>, *Add a new pending publisher* →
  project `trawlkit`, owner `arielgiamportone`, repository `trawl-design-lab`, workflow
  `release.yml`, environment `pypi`.
- **GitHub**: *Settings → Environments → New environment* `pypi` (optional: require approval).
- **Zenodo**: log in with GitHub at <https://zenodo.org/account/settings/github/> and enable the
  `trawl-design-lab` repository **before** publishing the release. Zenodo takes title, authors and
  licence from `.zenodo.json`.
