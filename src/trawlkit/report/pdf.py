"""Conversión del informe HTML a PDF con WeasyPrint (extra ``report``).

El renderizador SVG de WeasyPrint no resuelve variables CSS (``var(--ink)``), con lo que los
planos y gráficos saldrían en negro. Antes de convertir, :func:`flatten_css_vars` sustituye cada
``var(--x)`` de cada bloque ``<style>`` por su valor del tema claro (el PDF es para imprimir).
"""

from __future__ import annotations

import re
from pathlib import Path

_STYLE_RE = re.compile(r"(<style[^>]*>)(.*?)(</style>)", re.DOTALL | re.IGNORECASE)
_DEF_RE = re.compile(r"--([\w-]+)\s*:\s*([^;}]+)")
_VAR_RE = re.compile(r"var\(\s*--([\w-]+)\s*(?:,\s*([^()]*))?\)")
_DARK_MEDIA = re.compile(r"@media[^{]*prefers-color-scheme\s*:\s*dark[^{]*\{", re.IGNORECASE)


def _strip_blocks(css: str, start: re.Pattern[str]) -> str:
    """Quita bloques ``@media … { … }`` con llaves anidadas."""
    out = []
    pos = 0
    for m in start.finditer(css):
        if m.start() < pos:
            continue
        out.append(css[pos : m.start()])
        depth, i = 1, m.end()
        while i < len(css) and depth:
            depth += {"{": 1, "}": -1}.get(css[i], 0)
            i += 1
        pos = i
    out.append(css[pos:])
    return "".join(out)


def light_vars(css: str) -> dict[str, str]:
    """Variables CSS del tema claro (sin bloques oscuros), en orden de aparición."""
    css = _strip_blocks(css, _DARK_MEDIA)
    css = re.sub(r"[^{}]*data-theme=\"dark\"[^{}]*\{[^{}]*\}", "", css)
    return {m.group(1): m.group(2).strip() for m in _DEF_RE.finditer(css)}


def flatten_css_vars(document: str) -> str:
    """Resuelve ``var(--x)`` en cada ``<style>`` del documento con los valores del tema claro."""

    def fix(m: re.Match[str]) -> str:
        css = m.group(2)
        values = light_vars(css)

        def sub(v: re.Match[str]) -> str:
            val = values.get(v.group(1))
            if val is None:
                return (v.group(2) or "initial").strip()
            return _VAR_RE.sub(sub, val)

        return m.group(1) + _VAR_RE.sub(sub, css) + m.group(3)

    return _STYLE_RE.sub(fix, document)


def html_to_pdf(html: str, path: str | Path) -> Path:
    """Escribe ``html`` como PDF en ``path`` con WeasyPrint y devuelve la ruta."""
    try:
        from weasyprint import HTML
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise RuntimeError(
            "La salida PDF necesita WeasyPrint: pip install trawlkit[report]"
        ) from exc
    except OSError as exc:  # pragma: no cover - faltan las bibliotecas de Pango
        raise RuntimeError(
            "WeasyPrint no pudo cargar sus bibliotecas del sistema (Pango); "
            "ver https://doc.courtbouillon.org/weasyprint/stable/first_steps.html. "
            f"Detalle: {exc}"
        ) from exc
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=flatten_css_vars(html)).write_pdf(out)
    return out


__all__ = ["flatten_css_vars", "html_to_pdf", "light_vars"]
