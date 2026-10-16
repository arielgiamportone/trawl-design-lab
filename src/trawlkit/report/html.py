"""Informe HTML autocontenido (sin peticiones externas ni JavaScript) de un caso de diseño.

:func:`render_html` arma una sola página en español con CSS embebido (tema claro/oscuro por
``prefers-color-scheme`` y CSS de impresión para WeasyPrint: A4, saltos de página por sección,
A3 apaisado para las láminas y A4 apaisado para las tablas anchas). Todo el texto se escapa.
"""

from __future__ import annotations

import datetime as _dt
import re
from collections.abc import Callable, Sequence
from html import escape
from typing import TYPE_CHECKING

from trawlkit.report.labels import fmt
from trawlkit.report.tables import Table, all_tables, errata_table, notes_table, summary_table

if TYPE_CHECKING:
    from trawlkit.model import DesignResult

#: Claves de ``sheet_svgs``: lámina técnica y vista a escala real de cada variante.
SHEET_KEYS: tuple[str, ...] = ("std", "mod", "scale_std", "scale_mod")

#: Columnas a partir de las cuales una tabla va en página A4 apaisada.
WIDE_TABLE_COLUMNS = 8

#: Metodología: (etapa, autores / fuentes, descripción en una línea).
METHODOLOGY: tuple[tuple[str, str, str], ...] = (
    (
        "Potencia y tiro disponible",
        "Fridman; Prado y Dremière (FAO); Koyama; Nomura; Hamuro",
        "Reparto de la potencia al freno y fuerza de tiro FT disponible por velocidad.",
    ),
    (
        "Paños y cortes",
        "FAO (tabla de cortes); Prado",
        "Largos estirados, superficie de trabajo de cada paño, códigos y ángulo de corte.",
    ),
    (
        "Mecánica de la red",
        "FAO; L. G. Pérez Águila (2010)",
        "Índice de filtración d/l, superficies sólida y de trabajo, solidez y pesos.",
    ),
    (
        "Dimensiones",
        "Martini (nivel 2); A. Fujiishi; Nomura",
        "Lima y burlón, largos, circunferencias, factor largo y proporciones de referencia.",
    ),
    (
        "Resistencia de la red",
        "Tauti, Nomura y Shu; Koyama; Hamuro; Reid; Robertson; MacLennan; "
        "Marine Laboratory Aberdeen; Fridman; Dickson",
        "Trece fórmulas empíricas de RN; Aberdeen demersal es la RN de diseño.",
    ),
    (
        "Portones",
        "Fridman; catálogos FAO y Morgère",
        "Separación entre portones, polar CL/CD, ROB como fracción de FT y superficie requerida.",
    ),
    (
        "Bridas, patentes y pies de gallo",
        "Martini; P. Y. Dremière",
        "Longitudes de bridas y patentes y ángulo de ataque δ del aparejo.",
    ),
    (
        "Aberturas",
        "Baranov y Fridman; N. Suzuki (JICA); Prado y Dremière; A. Izzo (INIDEP); Martini",
        "DPA por Fridman, geométrica y por corte; abertura horizontal y vertical.",
    ),
    (
        "Flotación y lastre",
        "Koyama; Prado y Dremière; Fridman; Hoerner (1975)",
        "Flotación de la lima, número y reparto de boyas, su resistencia y el lastre del burlón.",
    ),
    (
        "Cables de remolque",
        "Nomura y Yamazaki; L. G. Pérez Águila; MacLennan; Kowalski y Gianotti",
        "Ángulos, diámetro, CD, resistencia del cable, cargas y selección del catálogo.",
    ),
    (
        "Ventana de velocidad",
        "trawlkit",
        "Velocidad máxima remolcable donde el tiro disponible iguala la resistencia total.",
    ),
)

CSS = """
:root { color-scheme: light dark;
  --bg:#ffffff; --surface:#f6f7f9; --ink:#14171f; --ink-2:#4a5160; --muted:#6b7385;
  --rule:#d9dee8; --accent:#1f6feb; --good:#0b7a0b; --bad:#b42318; --zebra:#fafbfc; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --bg:#0d1117; --surface:#161b22; --ink:#e6e9ef;
    --ink-2:#c3c8d2; --muted:#9aa3b5; --rule:#2a3242; --accent:#58a6ff; --good:#3fb950;
    --bad:#f47067; --zebra:#11161d; }
}
:root[data-theme="dark"] { --bg:#0d1117; --surface:#161b22; --ink:#e6e9ef; --ink-2:#c3c8d2;
  --muted:#9aa3b5; --rule:#2a3242; --accent:#58a6ff; --good:#3fb950; --bad:#f47067;
  --zebra:#11161d; }
* { box-sizing: border-box; }
html { background: var(--bg); }
body { margin: 0 auto; max-width: 1100px; padding: 24px 16px 64px; background: var(--bg);
  color: var(--ink); font: 14px/1.5 system-ui, -apple-system, "Segoe UI", "Helvetica Neue",
  Arial, "DejaVu Sans", sans-serif; }
h1 { font-size: 30px; line-height: 1.15; margin: 0 0 8px; }
h2 { font-size: 22px; margin: 0 0 12px; padding-bottom: 6px; border-bottom: 2px solid var(--rule); }
h3 { font-size: 16px; margin: 20px 0 6px; }
p { margin: 0 0 10px; }
.muted { color: var(--muted); }
nav.toc ol { columns: 2; padding-left: 20px; }
nav.toc a, a { color: var(--accent); }
section { margin: 40px 0; }
.cover { min-height: 60vh; display: flex; flex-direction: column; justify-content: center; }
.cover .kicker { text-transform: uppercase; letter-spacing: .08em; font-size: 12px;
  color: var(--muted); }
dl.facts { display: grid; grid-template-columns: max-content 1fr; gap: 6px 18px; margin: 24px 0; }
dl.facts dt { color: var(--muted); }
dl.facts dd { margin: 0; font-weight: 600; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;
  margin: 12px 0 20px; }
.kpi { background: var(--surface); border: 1px solid var(--rule); border-radius: 8px;
  padding: 10px 12px; }
.kpi .label { font-size: 12px; color: var(--muted); }
.kpi .value { font-size: 22px; font-weight: 600; line-height: 1.25; }
.kpi .unit { font-size: 13px; color: var(--ink-2); font-weight: 400; }
.kpi .sub { font-size: 11.5px; color: var(--ink-2); }
.ok { color: var(--good); } .warn { color: var(--bad); }
.table-wrap { overflow-x: auto; margin: 8px 0 18px; }
table { border-collapse: collapse; width: 100%; font-size: 12.5px; }
caption { text-align: left; font-weight: 600; font-size: 14px; padding: 4px 0 6px; }
th, td { padding: 3px 6px; border-bottom: 1px solid var(--rule); vertical-align: top; }
th { text-align: left; font-weight: 600; color: var(--ink-2); background: var(--surface); }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
td.num { white-space: nowrap; }
tbody tr:nth-child(even) td { background: var(--zebra); }
td.group { color: var(--muted); }
.source { font-size: 11.5px; color: var(--muted); margin: 2px 0 0; }
figure { margin: 16px 0 24px; }
figure svg { display: block; width: 100%; height: auto; max-width: 100%; }
figcaption { font-size: 12.5px; color: var(--muted); margin-top: 4px; }
.sheet svg { display: block; width: 100%; height: auto; max-height: 80vh; }
.status-reproducida { color: var(--bad); font-weight: 600; }
.status-corregida { color: var(--good); font-weight: 600; }
.status-documentada { color: var(--muted); font-weight: 600; }
ul.notes li { margin-bottom: 4px; }
footer { margin-top: 48px; font-size: 12px; color: var(--muted); }
@media print {
  :root { --bg:#ffffff; --surface:#f3f5f8; --ink:#000000; --ink-2:#333a46; --muted:#5b6272;
    --rule:#cfd5df; --zebra:#fafbfc; }
  body { max-width: none; padding: 0; font-size: 10pt; }
  h1 { font-size: 26pt; } h2 { font-size: 15pt; } h3 { font-size: 11.5pt; }
  nav.toc { display: none; }
  section { margin: 0; }
  section.major { break-before: page; }
  .cover { min-height: 0; height: 240mm; }
  .table-wrap { overflow: visible; }
  table { font-size: 8.5pt; }
  th, td { padding: 1.5pt 4pt; }
  thead { display: table-header-group; }
  tr, figure, .kpi { break-inside: avoid; }
  h2, h3, caption { break-after: avoid; }
  p.source { break-before: avoid; }
  .tblock { break-inside: auto; }
  .tblock.small { break-inside: avoid; }
  .wide { page: wide; }
  .wide table { font-size: 7pt; table-layout: fixed; }
  .wide th { hyphens: auto; overflow-wrap: anywhere; }
  #resumen table { font-size: 8pt; }
  #resumen td, #resumen th { padding: 0.8pt 4pt; line-height: 1.3; }
  .kpi .label { font-size: 8pt; } .kpi .sub { font-size: 7.5pt; }
  .kpi { padding: 6px 8px; }
  .wide th, .wide td { padding: 2px 3px; }
  .sheet { page: sheet; break-before: page; }
  .sheet svg { max-height: 255mm; }
  figure svg { max-height: 120mm; }
  .kpi .value { font-size: 16pt; }
  .kpis { grid-template-columns: repeat(5, 1fr); }
  .erratas-block { page: wide; }
  .erratas-block table { font-size: 7.5pt; }
}
@page { size: A4; margin: 15mm;
  @bottom-right { content: counter(page) " / " counter(pages); font: 8pt "Helvetica Neue", Arial,
    "DejaVu Sans", sans-serif; color: #6b7385; }
  @bottom-left { content: "trawlkit · informe de diseño"; font: 8pt "Helvetica Neue", Arial,
    "DejaVu Sans", sans-serif; color: #6b7385; } }
@page wide { size: A4 landscape; margin: 12mm; }
@page sheet { size: A3 landscape; margin: 10mm; }
@page :first { @bottom-left { content: none; } @bottom-right { content: none; } }
"""

_XML_DECL = re.compile(r"^\s*<\?xml[^>]*\?>\s*")


def inline_svg(svg: str) -> str:
    """SVG listo para embeber en HTML (sin declaración XML)."""
    return _XML_DECL.sub("", svg).strip()


def placeholder_svg(title: str = "Plano no disponible") -> str:
    """Lámina provisoria: marco con el texto 'Plano no disponible'."""
    from trawlkit.drawing.svg import document, rect, text

    w, h = 1190.0, 842.0
    return document(
        w,
        h,
        [
            rect(10, 10, w - 20, h - 20, cls="line"),
            rect(20, 20, w - 40, h - 40, cls="thin"),
            text((w / 2, h / 2), title, cls="title mid"),
            text((w / 2, h / 2 + 22), "trawlkit.drawing no está disponible", cls="muted-text mid"),
        ],
        title_text=title,
    )


def _sheet_functions() -> tuple[Callable[..., str], Callable[..., str]] | None:
    """``net_sheet_svg`` y ``net_scale_svg`` de :mod:`trawlkit.drawing` si existen."""
    try:
        import trawlkit.drawing as drawing
    except ImportError:  # pragma: no cover
        return None
    sheet = getattr(drawing, "net_sheet_svg", None)
    scale = getattr(drawing, "net_scale_svg", None)
    if callable(sheet) and callable(scale):
        return sheet, scale
    return None


def default_sheet_svgs(result: DesignResult) -> dict[str, str]:
    """Láminas de la red (``std``, ``mod``, ``scale_std``, ``scale_mod``) o el reemplazo.

    Usa ``trawlkit.drawing.net_sheet_svg`` / ``net_scale_svg`` si están disponibles; si no (o si
    fallan), un marco con "Plano no disponible". Las variantes ``mod`` sólo si hay red modificada.
    """
    fns = _sheet_functions()
    variants = ("std", "mod") if result.case.net_modified is not None else ("std",)
    out: dict[str, str] = {}
    for v in variants:
        for key, idx in ((v, 0), (f"scale_{v}", 1)):
            svg: str | None = None
            if fns is not None:
                try:
                    svg = fns[idx](result, v)
                except Exception:  # noqa: BLE001 - el informe no debe caerse por un plano
                    svg = None
            out[key] = svg if svg is not None else placeholder_svg()
    return out


# ---------------------------------------------------------------------------------------------
# Piezas HTML
# ---------------------------------------------------------------------------------------------


def _e(value: object) -> str:
    return escape(str(value), quote=True)


def _cell(value: object) -> tuple[str, bool]:
    """Texto formateado y si es numérico."""
    if isinstance(value, bool):
        return ("sí" if value else "no"), False
    if isinstance(value, int | float):
        return fmt(float(value)), True
    if value is None:
        return "—", False
    return str(value), False


def render_table(table: Table, *, caption: bool = True, hide: Sequence[str] = ()) -> str:
    """Una :class:`Table` como ``<table>`` (números alineados a la derecha, todo escapado).

    ``hide`` son claves de columnas que no se muestran (siguen en el XLSX).
    """
    if hide:
        keep = [i for i, c in enumerate(table.columns) if c.key not in hide]
        table = Table(
            key=table.key,
            title=table.title,
            columns=tuple(table.columns[i] for i in keep),
            rows=tuple(tuple(r[i] for i in keep) for r in table.rows),
            note=table.note,
            source=table.source,
            meta=table.meta,
        )
    kv = [c.key for c in table.columns] == ["group", "name", "value", "unit"]
    head = "".join(
        f'<th scope="col"{" class=num" if _is_num_col(table, i) else ""}>{_e(c.heading)}</th>'
        for i, c in enumerate(table.columns)
    )
    body = []
    prev_group: object = None
    for row in table.rows:
        tds = []
        for i, value in enumerate(row):
            txt, num = _cell(value)
            cls = "num" if num else ""
            if kv and i == 0:
                cls = "group"
                if value == prev_group:
                    txt = ""
                prev_group = value
            if table.key == "erratas" and table.columns[i].key == "status":
                cls = f"status-{txt}"
            tds.append(f'<td class="{cls}">{_e(txt)}</td>' if cls else f"<td>{_e(txt)}</td>")
        body.append("<tr>" + "".join(tds) + "</tr>")
    cap = f"<caption>{_e(table.title)}</caption>" if caption else ""
    foot = ""
    if table.note:
        foot += f'<p class="source">{_e(table.note)}</p>'
    if table.source:
        foot += f'<p class="source">Celdas del libro: {_e(table.source)}</p>'
    wide = len(table.columns) >= WIDE_TABLE_COLUMNS
    small = len(table.rows) <= 14
    classes = "tblock" + (" wide" if wide else "") + (" small" if small else "")
    return (
        f'<div class="{classes}" id="tabla-{_e(table.key)}"><div class="table-wrap"><table>'
        f"{cap}<thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
        f"{foot}</div>"
    )


def _is_num_col(table: Table, i: int) -> bool:
    vals = [r[i] for r in table.rows if r[i] is not None]
    return bool(vals) and all(isinstance(v, int | float) and not isinstance(v, bool) for v in vals)


def _kpis(result: DesignResult) -> str:
    case = result.case
    win = result.performance.design
    sel = result.warps.selection
    tiles: list[tuple[str, str, str, str, str]] = [
        ("Abertura vertical (AV)", fmt(result.spread.vertical.suzuki_m), "m", "Suzuki", ""),
        ("Abertura horizontal (AH)", fmt(result.spread.horizontal_opening_m), "m", "", ""),
    ]
    if any(abs(v - 3.0) < 1e-9 for v in case.speeds_kn):
        rn3 = float(result.drag.rn.std[case.speed_index(3.0)])
        tiles.append(("RN a 3 kn", fmt(round(rn3, 1)), "kgf", "red estándar, Aberdeen", ""))
    vmax = "—" if win.max_speed_kn is None else f"{win.max_speed_kn:.2f}"
    tiles.append(("Velocidad máxima", vmax, "kn", "FT ≥ R, red estándar", ""))
    ok = sel.satisfies_breaking_load
    tiles.append(
        (
            "Cable seleccionado",
            fmt(sel.diameter_mm),
            "mm",
            f"rotura {fmt(sel.breaking_load_t)} t — "
            + ("cumple" if ok else "no cumple la rotura mínima"),
            "ok" if ok else "warn",
        )
    )
    parts = []
    for label, value, unit, sub, cls in tiles:
        sub_html = f'<div class="sub {cls}">{_e(sub)}</div>' if sub else ""
        parts.append(
            f'<div class="kpi"><div class="label">{_e(label)}</div>'
            f'<div class="value">{_e(value)} <span class="unit">{_e(unit)}</span></div>'
            f"{sub_html}</div>"
        )
    return '<div class="kpis">' + "".join(parts) + "</div>"


def _cover(result: DesignResult, generated: _dt.date) -> str:
    from trawlkit import __version__

    case = result.case
    nets = f"{case.net.name} ({case.net.id})"
    if case.net_modified is not None:
        nets_mod = f"{case.net_modified.name} ({case.net_modified.id})"
    else:
        nets_mod = "— (misma red que la estándar)"
    others = [v for v in case.vessel_class if v.id != case.vessel.id]
    vessel = f"{case.vessel.name or case.vessel.id} — {case.vessel.bhp:g} BHP"
    facts = [
        ("Red estándar", nets),
        ("Red modificada", nets_mod),
        ("Buque de diseño", vessel),
        (
            "Buques de la clase",
            ", ".join(f"{v.id} ({v.bhp:g} BHP)" for v in others) if others else "—",
        ),
        ("Portón", f"{case.door.name} ({case.door.id})"),
        ("Modo de compatibilidad", case.compat.value),
        ("Velocidades", ", ".join(f"{v:g}" for v in case.speeds_kn) + " kn"),
        ("Fecha", generated.isoformat()),
        ("Versión de trawlkit", __version__),
    ]
    dl = "".join(f"<dt>{_e(k)}</dt><dd>{_e(v)}</dd>" for k, v in facts)
    return (
        '<section id="portada" class="cover">'
        '<div class="kicker">Informe de diseño · trawlkit</div>'
        f"<h1>{_e(case.net.name)}</h1>"
        '<p class="muted">Dimensionamiento de red, aparejo, flotación, lastre y cable de '
        "remolque a partir del modelo FAO A-3.</p>"
        f'<dl class="facts">{dl}</dl></section>'
    )


def _toc(entries: Sequence[tuple[str, str]]) -> str:
    items = "".join(f'<li><a href="#{_e(i)}">{_e(t)}</a></li>' for i, t in entries)
    return f'<nav class="toc" aria-label="Contenido"><h2>Contenido</h2><ol>{items}</ol></nav>'


def _sheet_section(sid: str, title: str, svg: str, note: str) -> str:
    return (
        f'<section id="{_e(sid)}" class="major sheet"><h2>{_e(title)}</h2>'
        f'<figure role="img" aria-label="{_e(title)}">{inline_svg(svg)}'
        f"<figcaption>{_e(note)}</figcaption></figure></section>"
    )


def render_html(
    result: DesignResult,
    *,
    sheet_svgs: dict[str, str] | None = None,
    charts: dict[str, str] | None = None,
    generated: _dt.date | None = None,
) -> str:
    """Informe completo como una página HTML autocontenida.

    ``sheet_svgs`` (claves de :data:`SHEET_KEYS`) y ``charts`` (clave → SVG) se calculan si se
    omiten (:func:`default_sheet_svgs`, :func:`trawlkit.report.charts.all_charts`).
    """
    from trawlkit.report.charts import CHART_TITLES, all_charts

    case = result.case
    generated = generated or _dt.date.today()
    sheets = default_sheet_svgs(result) if sheet_svgs is None else sheet_svgs
    chart_svgs = all_charts(result) if charts is None else charts
    has_mod = case.net_modified is not None

    sections: list[str] = []
    toc: list[tuple[str, str]] = [("resumen", "Resumen")]

    summary = summary_table(result)
    sections.append(
        '<section id="resumen" class="major"><h2>Resumen</h2>'
        + _kpis(result)
        + render_table(summary, hide=("key",))
        + "</section>"
    )

    def sheet(key: str) -> str:
        return sheets.get(key) or placeholder_svg()

    toc.append(("lamina-estandar", "Lámina de la red estándar"))
    sections.append(
        _sheet_section(
            "lamina-estandar",
            "Lámina de la red estándar",
            sheet("std"),
            f"Plano de paños de {case.net.id}.",
        )
    )
    if has_mod:
        assert case.net_modified is not None
        toc.append(("lamina-modificada", "Lámina de la red modificada"))
        sections.append(
            _sheet_section(
                "lamina-modificada",
                "Lámina de la red modificada",
                sheet("mod"),
                f"Plano de paños de {case.net_modified.id}.",
            )
        )
    toc.append(("escala", "Escala real"))
    scale_html = [
        _sheet_section(
            "escala",
            "Escala real — red estándar",
            sheet("scale_std"),
            "Vista a escala real reducida para la página; el archivo plano_escala_estandar.svg "
            "conserva la escala.",
        )
    ]
    if has_mod:
        scale_html.append(
            _sheet_section(
                "escala-modificada",
                "Escala real — red modificada",
                sheet("scale_mod"),
                "Vista a escala real reducida para la página; el archivo "
                "plano_escala_modificada.svg conserva la escala.",
            )
        )
    sections.extend(scale_html)

    toc.append(("graficos", "Gráficos"))
    figs = "".join(
        f'<figure id="grafico-{_e(k)}" role="img" aria-label="{_e(CHART_TITLES.get(k, k))}">'
        f"{inline_svg(svg)}<figcaption>{_e(CHART_TITLES.get(k, k))}</figcaption></figure>"
        for k, svg in chart_svgs.items()
    )
    sections.append(
        '<section id="graficos" class="major"><h2>Gráficos</h2>'
        '<p class="muted">Los valores de cada gráfico están en las tablas de la sección '
        "siguiente.</p>"
        f"{figs}</section>"
    )

    toc.append(("tablas", "Tablas"))
    skip = {"resumen", "erratas", "notas"}
    tables = [t for t in all_tables(result) if t.key not in skip]
    # Primero las angostas (A4 vertical, junto al título) y luego las anchas (A4 apaisado),
    # para no forzar un cambio de página por cada tabla.
    tables.sort(key=lambda t: len(t.columns) >= WIDE_TABLE_COLUMNS)
    tables_html = "".join(render_table(t) for t in tables)
    sections.append(f'<section id="tablas" class="major"><h2>Tablas</h2>{tables_html}</section>')

    toc.append(("erratas", "Erratas"))
    sections.append(
        '<section id="erratas" class="major erratas-block"><h2>Erratas del libro original</h2>'
        f"<p>Modo de compatibilidad del caso: <strong>{_e(case.compat.value)}</strong>. "
        "En modo <em>excel</em> se reproducen las erratas para validar la migración contra el "
        "libro; en modo <em>corrected</em> se aplican las fórmulas correctas.</p>"
        + '<div class="erratas-block">'
        + render_table(errata_table(result), caption=False)
        + "</div></section>"
    )

    toc.append(("notas", "Notas"))
    notes = notes_table(result)
    notes_html = (
        '<ul class="notes">' + "".join(f"<li>{_e(r[1])}</li>" for r in notes.rows) + "</ul>"
        if notes.rows
        else "<p>La corrida no dejó notas.</p>"
    )
    sections.append(f'<section id="notas"><h2>Notas de la corrida</h2>{notes_html}</section>')

    toc.append(("metodologia", "Metodología"))
    rows = "".join(
        f"<tr><td>{_e(stage)}</td><td>{_e(authors)}</td><td>{_e(desc)}</td></tr>"
        for stage, authors, desc in METHODOLOGY
    )
    sections.append(
        '<section id="metodologia" class="major"><h2>Metodología</h2>'
        "<p>El motor reproduce, hoja por hoja, el libro <em>Calculos_Red_FAO_A3.xlsx</em> y "
        "encadena las etapas en el orden en que el libro resuelve sus dependencias.</p>"
        '<div class="table-wrap"><table><thead><tr><th scope="col">Etapa</th>'
        '<th scope="col">Autores y fuentes</th><th scope="col">Qué calcula</th></tr></thead>'
        f"<tbody>{rows}</tbody></table></div></section>"
    )

    toc.append(("creditos", "Créditos"))
    sections.append(
        '<section id="creditos"><h2>Créditos y licencias</h2>'
        "<p>Modelo Excel original (<em>Calculos_Red_FAO_A3.xlsx</em>, 2014-2024): "
        "<strong>Ariel Luján Giamportone</strong>.</p>"
        "<p>Documentación y datos: licencia Creative Commons Atribución 4.0 (CC BY 4.0). "
        "Código de trawlkit: licencia MIT.</p>"
        '<p class="muted">Repositorio: github.com/arielgiamportone/trawl-design-lab · '
        "Modelo original: github.com/arielgiamportone/Trawl_net_model_in_Advanced_Excel</p>"
        "</section>"
    )

    title = f"Informe de diseño — {case.net.name}"
    return (
        '<!DOCTYPE html>\n<html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<meta name="generator" content="trawlkit"><title>{_e(title)}</title>'
        f"<style>{CSS}</style></head><body>"
        + _cover(result, generated)
        + _toc(toc)
        + "".join(sections)
        + f"<footer>Generado por trawlkit el {_e(generated.isoformat())}.</footer>"
        + "</body></html>\n"
    )


__all__ = [
    "CSS",
    "METHODOLOGY",
    "SHEET_KEYS",
    "default_sheet_svgs",
    "inline_svg",
    "placeholder_svg",
    "render_html",
    "render_table",
]
