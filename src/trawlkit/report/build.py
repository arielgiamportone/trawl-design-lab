"""Generación de todos los archivos del informe en un directorio."""

from __future__ import annotations

import datetime as _dt
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

from trawlkit.report.html import default_sheet_svgs, render_html

if TYPE_CHECKING:
    from trawlkit.model import DesignResult

FORMATS: tuple[str, ...] = ("html", "pdf", "xlsx", "svg")

#: Archivo SVG de cada lámina (clave de ``default_sheet_svgs``).
SVG_FILES: dict[str, str] = {
    "std": "plano_estandar.svg",
    "mod": "plano_modificada.svg",
    "scale_std": "plano_escala_estandar.svg",
    "scale_mod": "plano_escala_modificada.svg",
}


def build_report(
    result: DesignResult,
    out_dir: str | Path,
    formats: Iterable[str] = FORMATS,
    basename: str = "informe",
    *,
    generated: _dt.date | None = None,
) -> list[Path]:
    """Escribe el informe en ``out_dir`` y devuelve las rutas creadas.

    ``formats`` ⊆ {"html", "pdf", "xlsx", "svg"}: ``<basename>.html``, ``<basename>.pdf``,
    ``<basename>.xlsx`` y las láminas ``plano_estandar.svg``, ``plano_modificada.svg``,
    ``plano_escala_estandar.svg``, ``plano_escala_modificada.svg`` (las de la modificada sólo
    si el caso tiene red modificada).
    """
    fmts = tuple(formats)
    unknown = set(fmts) - set(FORMATS)
    if unknown:
        raise ValueError(f"formatos desconocidos: {sorted(unknown)} (use {FORMATS})")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    sheets = default_sheet_svgs(result)
    html: str | None = None
    if "html" in fmts or "pdf" in fmts:
        html = render_html(result, sheet_svgs=sheets, generated=generated)
    if "html" in fmts:
        assert html is not None
        p = out / f"{basename}.html"
        p.write_text(html, encoding="utf-8")
        written.append(p)
    if "pdf" in fmts:
        from trawlkit.report.pdf import html_to_pdf

        assert html is not None
        written.append(html_to_pdf(html, out / f"{basename}.pdf"))
    if "xlsx" in fmts:
        from trawlkit.report.xlsx import write_xlsx

        written.append(write_xlsx(result, out / f"{basename}.xlsx"))
    if "svg" in fmts:
        for key, name in SVG_FILES.items():
            if key in sheets:
                p = out / name
                p.write_text(sheets[key], encoding="utf-8")
                written.append(p)
    return written


__all__ = ["FORMATS", "SVG_FILES", "build_report"]
