"""Constructor SVG mínimo, sin dependencias, compartido por planos y gráficos.

Produce texto SVG válido (XML) con escape de atributos y texto. Los estilos van por clase CSS
definidas en :data:`BASE_STYLE`, con colores en variables para que el mismo SVG se vea bien en
fondo claro y oscuro cuando se embebe en HTML; abierto solo, usa los valores claros por defecto.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from xml.sax.saxutils import escape, quoteattr

Point = tuple[float, float]

#: Hoja de estilos común. ``--ink`` trazo principal, ``--muted`` secundario, ``--accent`` resaltado,
#: ``--fill`` relleno de paneles, ``--paper`` fondo.
BASE_STYLE = """
svg { --ink:#1d2433; --muted:#6b7385; --accent:#1f6feb; --fill:#eef3fb; --paper:#ffffff;
      --grid:#d9dee8; font-family: "Helvetica Neue", Arial, "DejaVu Sans", sans-serif; }
@media (prefers-color-scheme: dark) {
  svg.themed { --ink:#e6e9ef; --muted:#9aa3b5; --accent:#58a6ff; --fill:#1b2433; --paper:#0d1117;
               --grid:#2a3242; }
}
.paper { fill: var(--paper); }
.line { stroke: var(--ink); stroke-width: 1; fill: none; }
.thin { stroke: var(--ink); stroke-width: 0.5; fill: none; }
.muted { stroke: var(--muted); stroke-width: 0.6; fill: none; }
.dash { stroke: var(--muted); stroke-width: 0.6; fill: none; stroke-dasharray: 4 3; }
.grid { stroke: var(--grid); stroke-width: 0.4; fill: none; }
.panel { stroke: var(--ink); stroke-width: 1; fill: var(--fill); }
.accent { stroke: var(--accent); stroke-width: 1.5; fill: none; }
.accent-fill { fill: var(--accent); stroke: none; }
.ink-fill { fill: var(--ink); stroke: none; }
text { fill: var(--ink); font-size: 10px; }
text.small { font-size: 7.5px; }
text.tiny { font-size: 6px; }
text.label { font-size: 13px; font-weight: 600; }
text.title { font-size: 15px; font-weight: 700; }
text.muted-text { fill: var(--muted); }
text.mid { text-anchor: middle; }
text.end { text-anchor: end; }
""".strip()


def _num(v: float) -> str:
    """Número compacto para coordenadas (2 decimales, sin ceros sobrantes)."""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _attrs(attrs: dict[str, object]) -> str:
    parts = []
    for k, v in attrs.items():
        if v is None or v is False:
            continue
        name = k.rstrip("_").replace("_", "-")
        val = _num(v) if isinstance(v, float) else str(v)
        parts.append(f" {name}={quoteattr(val)}")
    return "".join(parts)


@dataclass
class Element:
    """Elemento SVG genérico con hijos y texto opcional."""

    tag: str
    attrs: dict[str, object] = field(default_factory=dict)
    children: list[Element] = field(default_factory=list)
    text: str | None = None

    def add(self, *children: Element) -> Element:
        """Agrega hijos y devuelve ``self`` (encadenable)."""
        self.children.extend(children)
        return self

    def render(self) -> str:
        """Serializa el elemento y sus hijos."""
        a = _attrs(self.attrs)
        if not self.children and self.text is None:
            return f"<{self.tag}{a}/>"
        inner = escape(self.text) if self.text is not None else ""
        inner += "".join(c.render() for c in self.children)
        return f"<{self.tag}{a}>{inner}</{self.tag}>"


def group(
    *children: Element, cls: str | None = None, transform: str | None = None, id_: str | None = None
) -> Element:
    """``<g>`` con clase, transformación e id opcionales."""
    return Element("g", {"class": cls, "transform": transform, "id": id_}, list(children))


def line(p1: Point, p2: Point, cls: str = "line") -> Element:
    """Segmento de recta."""
    return Element(
        "line",
        {
            "x1": float(p1[0]),
            "y1": float(p1[1]),
            "x2": float(p2[0]),
            "y2": float(p2[1]),
            "class": cls,
        },
    )


def polyline(points: Sequence[Point], cls: str = "line") -> Element:
    """Polilínea abierta."""
    pts = " ".join(f"{_num(x)},{_num(y)}" for x, y in points)
    return Element("polyline", {"points": pts, "class": cls})


def polygon(points: Sequence[Point], cls: str = "panel", id_: str | None = None) -> Element:
    """Polígono cerrado."""
    pts = " ".join(f"{_num(x)},{_num(y)}" for x, y in points)
    return Element("polygon", {"points": pts, "class": cls, "id": id_})


def rect(x: float, y: float, w: float, h: float, cls: str = "line", rx: float = 0.0) -> Element:
    """Rectángulo."""
    return Element(
        "rect",
        {
            "x": float(x),
            "y": float(y),
            "width": float(w),
            "height": float(h),
            "class": cls,
            "rx": float(rx) if rx else None,
        },
    )


def circle(c: Point, r: float, cls: str = "line") -> Element:
    """Círculo."""
    return Element("circle", {"cx": float(c[0]), "cy": float(c[1]), "r": float(r), "class": cls})


def path(d: str, cls: str = "line") -> Element:
    """Trayecto SVG con datos ``d`` ya construidos."""
    return Element("path", {"d": d, "class": cls})


def text(p: Point, content: str, cls: str = "", rotate: float | None = None) -> Element:
    """Texto en ``p``; ``rotate`` en grados alrededor del punto."""
    tr = f"rotate({_num(rotate)} {_num(p[0])} {_num(p[1])})" if rotate else None
    return Element(
        "text",
        {"x": float(p[0]), "y": float(p[1]), "class": cls or None, "transform": tr},
        text=content,
    )


def title(content: str) -> Element:
    """``<title>`` accesible del documento o de un grupo."""
    return Element("title", text=content)


def document(
    width: float,
    height: float,
    children: Iterable[Element],
    *,
    title_text: str = "",
    themed: bool = True,
    extra_style: str = "",
) -> str:
    """Documento SVG completo con ``viewBox`` en unidades de usuario (1 = 1 px a 96 dpi)."""
    root = Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "viewBox": f"0 0 {_num(width)} {_num(height)}",
            "width": float(width),
            "height": float(height),
            "class": "themed" if themed else None,
            "role": "img",
        },
    )
    if title_text:
        root.add(title(title_text))
    root.add(
        Element(
            "style", text="\n" + BASE_STYLE + ("\n" + extra_style if extra_style else "") + "\n"
        )
    )
    root.add(rect(0, 0, width, height, cls="paper"))
    root.add(*children)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + root.render() + "\n"
