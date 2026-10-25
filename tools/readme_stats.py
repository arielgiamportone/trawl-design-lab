"""Indicadores del README, calculados del código y los datos.

Escribe el bloque entre ``<!-- indicadores:inicio -->`` y ``<!-- indicadores:fin -->`` de
``README.md`` (castellano) y ``README.en.md`` (inglés). Sólo cuenta lo que cambia con el
contenido (redes, componentes, capítulos, rutas, erratas), no lo que cambia en cada commit.

Uso: ``uv run python tools/readme_stats.py`` (reescribe) o ``--check`` (falla si quedó viejo).
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import quote

import yaml

ROOT = Path(__file__).resolve().parents[1]
START, END = "<!-- indicadores:inicio -->", "<!-- indicadores:fin -->"
READMES = {"es": ROOT / "README.md", "en": ROOT / "README.en.md"}

#: Tolerancias de las pruebas: golden contra el Excel y paridad de Pyodide.
EXCEL_RTOL = "1e-6"
PYODIDE_RTOL = "1e-9"


def _golden_values() -> int:
    return sum(
        len(json.loads(p.read_text(encoding="utf-8"))["values"])
        for p in sorted((ROOT / "tests" / "golden").glob("*.json"))
    )


def _chapters() -> int:
    toc = yaml.safe_load((ROOT / "docs" / "_toc.yml").read_text(encoding="utf-8"))
    return 1 + sum(len(part["chapters"]) for part in toc["parts"])


def _api_routes() -> int:
    spec = json.loads((ROOT / "web" / "openapi.json").read_text(encoding="utf-8"))
    verbs = {"get", "post", "put", "patch", "delete"}
    return sum(1 for ops in spec["paths"].values() for m in ops if m in verbs)


def _references() -> int:
    bib = (ROOT / "docs" / "referencias.bib").read_text(encoding="utf-8")
    return len(re.findall(r"^@\w+\{", bib, flags=re.M))


def stats() -> dict[str, Any]:
    """Los indicadores, del paquete instalado y de los archivos del repositorio."""
    from trawlkit.api.service import net_presets
    from trawlkit.compat import ERRATA
    from trawlkit.components import KINDS, load_components
    from trawlkit.drag import RN_METHODS
    from trawlkit.rigging.seabed import seabeds
    from trawlkit.selectivity import species_catalogue

    nets = Counter((spec.status or "published") for spec in net_presets().values())
    comps = {k: load_components(k, statuses=("published", "draft")) for k in KINDS}
    brands = {c.brand for items in comps.values() for c in items if getattr(c, "brand", None)}
    generic = sum(1 for items in comps.values() for c in items if not getattr(c, "brand", None))
    return {
        "nets": sum(nets.values()),
        "nets_published": nets["published"],
        "nets_draft": nets["draft"],
        "components": sum(len(v) for v in comps.values()),
        "component_kinds": len(KINDS),
        "components_generic": generic,
        "brands": len(brands),
        "drag_methods": len(RN_METHODS),
        "errata": len(ERRATA),
        "golden": _golden_values(),
        "chapters": _chapters(),
        "references": _references(),
        "routes": _api_routes(),
        "species": len(species_catalogue()),
        "seabeds": len(seabeds()),
    }


def _badge(label: str, value: object, color: str) -> str:
    def esc(s: str) -> str:
        return quote(s.replace("-", "--").replace("_", "__"), safe="")

    return (
        f"![{label}: {value}](https://img.shields.io/badge/{esc(label)}-{esc(str(value))}-{color})"
    )


def block(s: dict[str, Any], lang: str) -> str:
    """Bloque de indicadores (badges y tabla) en ``es`` o ``en``."""
    es = lang == "es"
    badges = " ".join(
        [
            _badge("redes" if es else "nets", s["nets"], "1c5cab"),
            _badge("componentes" if es else "components", s["components"], "1c5cab"),
            _badge("rutas API" if es else "API routes", s["routes"], "1c5cab"),
            _badge("capítulos" if es else "chapters", s["chapters"], "c35a1b"),
            _badge("Excel rtol", EXCEL_RTOL, "2e7d32"),
        ]
    )
    if es:
        rows = [
            (
                "Redes en el catálogo",
                f"{s['nets']} ({s['nets_published']} publicadas, "
                f"{s['nets_draft']} borradores), con procedencia valor por valor",
            ),
            (
                "Componentes",
                f"{s['components']} en {s['component_kinds']} tipos "
                f"({s['components_generic']} genéricos y datos puntuales de {s['brands']} marcas)",
            ),
            ("Métodos de resistencia de la red", str(s["drag_methods"])),
            ("Erratas del Excel documentadas y corregidas", str(s["errata"])),
            (
                "Valores de referencia del Excel",
                f"{s['golden']:,}".replace(",", " ")
                + f", reproducidos con rtol {EXCEL_RTOL} en modo `excel`",
            ),
            ("Motor sin conexión (Pyodide)", f"paridad con CPython, rtol {PYODIDE_RTOL}"),
            ("Especies y tipos de fondo", f"{s['species']} especies · {s['seabeds']} fondos"),
            ("Rutas de la API", str(s["routes"])),
            ("Capítulos del libro", f"{s['chapters']} · {s['references']} referencias"),
        ]
        head = "| Indicador | Valor |"
    else:
        rows = [
            (
                "Nets in the catalogue",
                f"{s['nets']} ({s['nets_published']} published, "
                f"{s['nets_draft']} drafts), with value-by-value provenance",
            ),
            (
                "Components",
                f"{s['components']} in {s['component_kinds']} kinds "
                f"({s['components_generic']} generic, spot data from {s['brands']} brands)",
            ),
            ("Net drag methods", str(s["drag_methods"])),
            ("Excel errata documented and fixed", str(s["errata"])),
            (
                "Excel reference values",
                f"{s['golden']:,}" + f", reproduced at rtol {EXCEL_RTOL} in `excel` mode",
            ),
            ("Offline engine (Pyodide)", f"parity with CPython, rtol {PYODIDE_RTOL}"),
            ("Species and seabed types", f"{s['species']} species · {s['seabeds']} seabeds"),
            ("API routes", str(s["routes"])),
            ("Book chapters", f"{s['chapters']} · {s['references']} references"),
        ]
        head = "| Indicator | Value |"
    note = (
        "Generado por `tools/readme_stats.py`; `tests/test_readme.py` verifica que esté al día."
        if es
        else "Generated by `tools/readme_stats.py`; `tests/test_readme.py` checks it is up to date."
    )
    table = "\n".join([head, "|---|---|", *(f"| {a} | {b} |" for a, b in rows)])
    return f"{START}\n{badges}\n\n{table}\n\n<sub>{note}</sub>\n{END}"


def render(text: str, new_block: str) -> str:
    """``text`` con el bloque de indicadores reemplazado."""
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), flags=re.S)
    if not pattern.search(text):
        raise ValueError(f"falta el bloque {START} … {END}")
    return pattern.sub(lambda _: new_block, text, count=1)


def main(argv: list[str]) -> int:
    check = "--check" in argv
    s = stats()
    stale = []
    for lang, path in READMES.items():
        old = path.read_text(encoding="utf-8")
        new = render(old, block(s, lang))
        if new != old:
            stale.append(path.name)
            if not check:
                path.write_text(new, encoding="utf-8")
    if check and stale:
        print(
            f"indicadores desactualizados en {', '.join(stale)}: "
            "corra `uv run python tools/readme_stats.py`"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
