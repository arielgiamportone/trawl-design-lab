"""Guía de construcción en tablas, HTML para el taller, PDF y XLSX (Fase 15).

El HTML está pensado para imprimir en A4 y llevar al taller: letra grande, una casilla por paso,
un croquis de cada paño con sus mallas y sus cortes, y las tablas de montaje, boyas, lastre y
cortes de cabos. El PDF sale con WeasyPrint como los demás informes (:mod:`trawlkit.report.pdf`);
el XLSX tiene una hoja por tabla.
"""

from __future__ import annotations

import datetime as _dt
import html
import math
from typing import TYPE_CHECKING, Any

from trawlkit.report.tables import Column, Table

if TYPE_CHECKING:
    from trawlkit.construction import ConstructionGuide, CutPiece

VARIANT_NAME = {"std": "estándar", "mod": "modificada"}


def _fmt(v: Any, nd: int = 2) -> str:
    if v is None or v == "":
        return "—"
    if isinstance(v, bool):
        return "sí" if v else "no"
    if isinstance(v, float):
        if math.isnan(v):
            return "—"
        return f"{v:,.{nd}f}".replace(",", " ").replace(".", ",")
    return str(v)


def _e(v: Any, nd: int = 2) -> str:
    return html.escape(_fmt(v, nd))


def _r(v: float, nd: int = 3) -> float | None:
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else round(v, nd)


# ---------------------------------------------------------------------------------------------
# Tablas
# ---------------------------------------------------------------------------------------------


def guide_tables(g: ConstructionGuide) -> list[Table]:
    """Tablas de la guía, en el orden del taller."""
    cut = Table(
        "construccion_corte",
        "Hoja de corte",
        (
            Column("id", "Paño"),
            Column("name", "Nombre"),
            Column("planes", "Cara"),
            Column("pieces", "Piezas"),
            Column("material", "Material"),
            Column("mesh", "Mallero", "mm"),
            Column("twine", "Ø hilo", "mm"),
            Column("mouth", "Mallas boca"),
            Column("codend", "Mallas bolsa"),
            Column("depth", "Mallas alto"),
            Column("cut", "Corte de cada costado"),
            Column("start", "Por dónde empezar"),
            Column("weight", "Peso por pieza", "kg"),
        ),
        tuple(
            (
                p.id,
                p.name,
                p.planes,
                p.pieces,
                p.material,
                p.mesh_mm,
                p.twine_mm,
                p.meshes_mouth,
                p.meshes_codend,
                p.meshes_depth,
                " | ".join(
                    f"{s.side}: {s.instruction}{' (inferido)' if s.inferred else ''}"
                    for s in p.sides
                ),
                p.start,
                _r(p.weight_kg),
            )
            for p in g.pieces
        ),
        note="Mallas contadas a malla estirada. Las piezas de ala van de a pares (izquierda y "
        "derecha, una el reflejo de la otra).",
    )
    stock = Table(
        "construccion_pano",
        "Paño a comprar",
        (
            Column("material", "Material"),
            Column("mesh", "Mallero", "mm"),
            Column("twine", "Ø hilo", "mm"),
            Column("rtex", "Rtex"),
            Column("pieces", "Piezas"),
            Column("width", "Ancho", "mallas"),
            Column("depth", "Alto", "mallas"),
            Column("weight", "Peso del paño", "kg"),
            Column("finished", "Peso cortado", "kg"),
        ),
        tuple(
            (
                s.material,
                s.mesh_mm,
                s.twine_mm,
                s.rtex,
                s.pieces,
                s.width_meshes,
                s.depth_meshes,
                _r(s.weight_kg),
                _r(s.finished_kg),
            )
            for s in g.stock
        ),
        note="Tira del ancho del paño más ancho de cada calidad, con el alto que junta el área "
        "de todos los rectángulos de corte; el peso incluye el desperdicio de los cortes.",
    )
    joins = Table(
        "construccion_armado",
        "Armado: uniones paso a paso",
        (
            Column("step", "Paso"),
            Column("plane", "Cara"),
            Column("a", "Paño A"),
            Column("a_edge", "Borde A"),
            Column("b", "Paño B"),
            Column("b_edge", "Borde B"),
            Column("meshes_a", "Mallas A"),
            Column("meshes_b", "Mallas B"),
            Column("times", "Veces"),
            Column("ratio", "Relación"),
            Column("rule", "Cómo unir"),
            Column("note", "Nota"),
        ),
        tuple(
            (
                j.step,
                j.plane,
                j.a,
                j.a_edge,
                j.b,
                j.b_edge,
                j.meshes_a,
                j.meshes_b,
                j.times,
                j.ratio,
                j.rule,
                j.note,
            )
            for j in g.joins
        ),
    )
    hang = Table(
        "construccion_montaje",
        "Montaje en relingas",
        (
            Column("rope", "Relinga"),
            Column("part", "Tramo"),
            Column("panels", "Paños"),
            Column("times", "Veces"),
            Column("rope_m", "Cabo", "m"),
            Column("meshes", "Mallas a armar"),
            Column("netting_m", "Paño estirado", "m"),
            Column("hanging", "Coef. de armado E"),
            Column("per_m", "Mallas por metro"),
            Column("schedule", "Pauta"),
            Column("warning", "Aviso"),
        ),
        tuple(
            (
                h.rope,
                h.part,
                " + ".join(h.panels),
                h.times,
                _r(h.rope_m),
                h.meshes,
                _r(h.netting_m),
                _r(h.hanging),
                _r(h.meshes_per_m, 2),
                h.schedule,
                h.warning,
            )
            for h in g.hanging
        ),
        note="E = largo de cabo / largo del paño estirado. En las alas el paño se arma por su "
        "costado (una malla por cada fila de alto).",
    )
    floats = Table(
        "construccion_boyas",
        f"Boyas sobre la lima (Ø {_fmt(g.float_diameter_mm, 0)} mm)",
        (
            Column("n", "Boya"),
            Column("x", "Desde el centro", "m"),
            Column("zone", "Zona"),
        ),
        tuple((f.number, _r(f.x_m, 2), f.zone) for f in g.floats),
        note="Negativo: hacia el ala izquierda; positivo: hacia la derecha.",
    )
    ballast = Table(
        "construccion_lastre",
        "Lastre del burlón",
        (
            Column("zone", "Zona"),
            Column("where", "Dónde"),
            Column("kg_min", "Lastre mínimo", "kg"),
            Column("kg_m_min", "Mínimo", "kg/m"),
            Column("kg_max", "Lastre máximo", "kg"),
            Column("kg_m_max", "Máximo", "kg/m"),
        ),
        tuple(
            (
                b.zone,
                b.where,
                _r(b.kg_min, 1),
                _r(b.kg_m_min, 2),
                _r(b.kg_max, 1),
                _r(b.kg_m_max, 2),
            )
            for b in g.ballast
        ),
        note="Mínimo para la red modificada a 1 kn y máximo para la estándar a 3 kn (libro, "
        "hoja Flotación y Lastre).",
    )
    ropes = Table(
        "construccion_cortes",
        "Cortes de cabos, cables y cadenas",
        (
            Column("label", "Pieza"),
            Column("material", "Material"),
            Column("pieces", "Cantidad"),
            Column("length", "Largo terminado", "m"),
            Column("eyes", "Gazas"),
            Column("cut", "Largo de corte", "m"),
        ),
        tuple(
            (r.label, r.material, r.pieces, _r(r.length_m, 2), r.eyes, _r(r.cut_m, 2))
            for r in g.ropes
        ),
        note=f"Largo de corte = largo terminado + {_fmt(g.eye_allowance_m)} m por gaza.",
    )
    return [cut, stock, joins, hang, floats, ballast, ropes]


# ---------------------------------------------------------------------------------------------
# HTML del taller
# ---------------------------------------------------------------------------------------------

_CSS = """
:root { --ink: #1b1b1b; --muted: #5f5f5f; --line: #cfcdc6; --accent: #1c5cab;
  --panel: #e8eef7; --bg: #ffffff; }
body { font-family: "DejaVu Sans", Arial, sans-serif; color: var(--ink); background: var(--bg);
  font-size: 11.5pt; line-height: 1.35; margin: 0 auto; max-width: 190mm; padding: 0 4mm; }
@page { size: A4; margin: 14mm 12mm; }
h1 { font-size: 20pt; margin: 4mm 0 2mm; }
h2 { font-size: 15pt; margin: 8mm 0 3mm; border-bottom: 2px solid var(--ink);
  page-break-after: avoid; }
h3 { font-size: 12.5pt; margin: 3mm 0 1mm; }
table { border-collapse: collapse; width: 100%; margin: 2mm 0 4mm; }
th, td { border: 1px solid var(--line); padding: 1.6mm 2mm; text-align: left; vertical-align: top; }
th { background: #f0efea; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
.muted { color: var(--muted); }
.small { font-size: 9.5pt; }
.piece { display: flex; gap: 4mm; border: 1px solid var(--line); padding: 3mm; margin: 0 0 3mm;
  page-break-inside: avoid; }
.piece svg { flex: 0 0 46mm; width: 46mm; height: auto; }
.piece .body { flex: 1; }
.check { display: inline-block; width: 5mm; height: 5mm; border: 1.5px solid var(--ink);
  border-radius: 1mm; margin-right: 2mm; vertical-align: -1mm; }
ol.steps { list-style: none; padding: 0; }
ol.steps li { border-bottom: 1px solid var(--line); padding: 2.4mm 0; page-break-inside: avoid; }
.big { font-size: 13pt; font-weight: 700; }
.wide { font-size: 9pt; }
.wide th, .wide td { padding: 1mm 1.2mm; }
.kv td:first-child { width: 40%; color: var(--muted); }
"""


def piece_svg(p: CutPiece) -> str:
    """Croquis del paño: trapecio con las mallas de cada borde y los cortes de los costados."""
    u1 = p.hanging_ratio or 0.5
    u2 = math.sqrt(max(1.0 - u1 * u1, 0.05))
    m = p.mesh_mm / 1000.0
    top = p.meshes_mouth * m * u1
    bottom = p.meshes_codend * m * u1
    height = p.meshes_depth * m * u2
    w, h = 160.0, 150.0
    scale = min((w - 20) / max(top, bottom, 1e-6), (h - 40) / max(height, 1e-6))
    ht, hb, hh = top * scale / 2, bottom * scale / 2, height * scale
    cx, y0 = w / 2, 18.0
    if p.paired:
        # Pieza de ala: el costado de la relinga queda recto a la izquierda.
        x0 = cx - max(ht, hb)
        pts = [(x0, y0), (x0 + 2 * ht, y0), (x0 + 2 * hb, y0 + hh), (x0, y0 + hh)]
    else:
        pts = [(cx - ht, y0), (cx + ht, y0), (cx + hb, y0 + hh), (cx - hb, y0 + hh)]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    side = p.sides[0].code if p.sides else ""
    return (
        f"<svg viewBox='0 0 {w:.0f} {h:.0f}' xmlns='http://www.w3.org/2000/svg' role='img' "
        f"aria-label='Croquis del paño {html.escape(p.id)}'>"
        f"<polygon points='{poly}' fill='#e8eef7' stroke='#1c5cab' stroke-width='1.5'/>"
        f"<text x='{cx:.0f}' y='12' font-size='10' text-anchor='middle'>{p.meshes_mouth}</text>"
        f"<text x='{cx:.0f}' y='{y0 + hh + 13:.0f}' font-size='10' text-anchor='middle'>"
        f"{p.meshes_codend}</text>"
        f"<text x='{cx:.0f}' y='{y0 + hh / 2 + 4:.0f}' font-size='13' font-weight='700' "
        f"text-anchor='middle'>{html.escape(p.id)}</text>"
        f"<text x='{cx:.0f}' y='{y0 + hh / 2 + 17:.0f}' font-size='9' text-anchor='middle' "
        f"fill='#5f5f5f'>N {p.meshes_depth} · {html.escape(side)}</text></svg>"
    )


def _kv(rows: list[tuple[str, str]]) -> str:
    trs = "".join(f"<tr><td>{html.escape(k)}</td><td>{v}</td></tr>" for k, v in rows)
    return f"<table class='kv small'>{trs}</table>"


def _pieces_html(g: ConstructionGuide) -> str:
    out = []
    for p in g.pieces:
        cuts = "".join(
            f"<li><span class='check'></span><strong>{html.escape(s.side)}</strong>: "
            f"{html.escape(s.instruction)}"
            f"{' <em>(inferido: verificar en el plano)</em>' if s.inferred else ''}</li>"
            for s in p.sides
        )
        info = _kv(
            [
                ("Cara y sección", html.escape(f"{p.planes} · {p.section}")),
                (
                    "Piezas",
                    f"<span class='big'>{p.pieces}</span>"
                    + (" (par izquierda/derecha)" if p.paired else ""),
                ),
                (
                    "Paño",
                    html.escape(
                        f"{p.material}, mallero {_fmt(p.mesh_mm, 0)} mm, "
                        f"hilo Ø {_fmt(p.twine_mm)} mm"
                        + (f", R{_fmt(p.rtex, 0)} tex" if p.rtex else "")
                    ),
                ),
                (
                    "Mallas",
                    html.escape(
                        f"boca {p.meshes_mouth} · bolsa {p.meshes_codend} · alto {p.meshes_depth}"
                    ),
                ),
                (
                    "Rectángulo de corte",
                    html.escape(
                        f"{p.stock_width} × {p.stock_depth} mallas{' por par' if p.paired else ''} "
                        f"({_fmt(p.stretched_width_m)} × "
                        f"{_fmt(p.stretched_length_m)} m estirado), "
                        f"desperdicio {_fmt(100 * p.waste, 0)} %"
                    ),
                ),
                ("Peso por pieza", _e(p.weight_kg) + " kg"),
            ]
        )
        out.append(
            f"<div class='piece'>{piece_svg(p)}<div class='body'>"
            f"<h3>{html.escape(p.id)} · {html.escape(p.name)}</h3>{info}"
            f"<p class='small muted'>{html.escape(p.start)}</p><ul class='small'>{cuts}</ul>"
            "</div></div>"
        )
    return "".join(out)


def _table_html(t: Table, nd: int = 2, wide: bool = False) -> str:
    # Las columnas vacías en todas las filas (avisos sin avisos) no se imprimen.
    keep = [i for i in range(len(t.columns)) if any(r[i] not in (None, "") for r in t.rows)]
    head = "".join(f"<th>{html.escape(t.columns[i].heading)}</th>" for i in keep)

    def whole(i: int) -> bool:
        vals = [float(v) for r in t.rows if isinstance(v := r[i], float)]
        return bool(vals) and all(v.is_integer() for v in vals)

    digits = {i: 0 if whole(i) else nd for i in keep}
    rows = []
    for full in t.rows:
        cells = "".join(
            f"<td class='num'>{_e(full[i], digits[i])}</td>"
            if isinstance(full[i], int | float) and not isinstance(full[i], bool)
            else f"<td>{_e(full[i])}</td>"
            for i in keep
        )
        rows.append(f"<tr>{cells}</tr>")
    note = f"<p class='small muted'>{html.escape(t.note)}</p>" if t.note else ""
    cls = " class='wide'" if wide else ""
    return f"<table{cls}><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>{note}"


def _steps_html(g: ConstructionGuide) -> str:
    items = []
    for j in g.joins:
        times = f" · {j.times} veces" if j.times > 1 else ""
        note = f"<br><span class='small muted'>{html.escape(j.note)}</span>" if j.note else ""
        items.append(
            f"<li><span class='check'></span><strong>Paso {j.step}</strong> ({html.escape(j.plane)}"
            f"{times}): unir el {html.escape(j.a_edge)} de <strong>{html.escape(j.a)}</strong> "
            f"({j.meshes_a} mallas) con el {html.escape(j.b_edge)} de "
            f"<strong>{html.escape(j.b)}</strong> ({j.meshes_b} mallas). "
            f"{html.escape(j.rule[:1].upper() + j.rule[1:])}.{note}</li>"
        )
    return f"<ol class='steps'>{''.join(items)}</ol>"


def construction_html(
    g: ConstructionGuide, generated: _dt.date | None = None, link: str | None = None
) -> str:
    """Guía de construcción en HTML autocontenido, para imprimir en A4 o pasar a PDF."""
    tables = {t.key: t for t in guide_tables(g)}
    date = (generated or _dt.date.today()).isoformat()
    variant = VARIANT_NAME.get(g.variant, g.variant)
    total_pieces = sum(p.pieces for p in g.pieces)
    netting = sum(s.weight_kg for s in g.stock)
    intro = (
        f"<p>Red: <strong>{html.escape(g.net_name)}</strong> ({html.escape(variant)}). "
        f"{len(g.pieces)} paños, {total_pieces} piezas a cortar, {len(g.joins)} uniones y "
        f"{_fmt(netting, 1)} kg de paño a comprar (con desperdicio). Generada el {date} con "
        "trawlkit.</p>"
    )
    if link:
        intro += f"<p class='small'>Caso en la app: {html.escape(link)}</p>"
    notes = "".join(f"<li>{html.escape(n)}</li>" for n in g.notes)
    return (
        "<!doctype html><html lang='es'><head><meta charset='utf-8'>"
        f"<title>Guía de construcción · {html.escape(g.net_id)}</title><style>{_CSS}</style>"
        "</head><body>"
        f"<h1>Guía de construcción</h1>{intro}"
        f"<h2>1. Paño a comprar</h2>{_table_html(tables['construccion_pano'], wide=True)}"
        f"<h2>2. Hoja de corte</h2>{_pieces_html(g)}"
        f"<h2>3. Armado paso a paso</h2>{_steps_html(g)}"
        f"<h2>4. Montaje en relingas</h2>{_table_html(tables['construccion_montaje'], wide=True)}"
        f"<h3>Boyas</h3>{_table_html(tables['construccion_boyas'])}"
        f"<h3>Lastre</h3>{_table_html(tables['construccion_lastre'], wide=True)}"
        f"<h2>5. Cortes de cabos, cables y cadenas</h2>{_table_html(tables['construccion_cortes'])}"
        f"<h2>Supuestos</h2><ul class='small muted'>{notes}</ul>"
        "<p class='small muted'>Resultados orientativos: verifique con el plano de la red y en "
        "la prueba de mar antes de construir en serie.</p></body></html>"
    )


def construction_pdf(g: ConstructionGuide) -> bytes:
    """Guía de construcción en PDF (WeasyPrint, extra ``report``)."""
    from trawlkit.report.pdf import flatten_css_vars

    try:
        from weasyprint import HTML
    except (ImportError, OSError) as exc:  # pragma: no cover - depende del entorno
        raise RuntimeError(
            'el PDF necesita WeasyPrint: pip install "trawlkit[report]" (y Pango)'
        ) from exc
    out = HTML(string=flatten_css_vars(construction_html(g))).write_pdf()
    assert isinstance(out, bytes)
    return out


def construction_xlsx(g: ConstructionGuide) -> bytes:
    """Guía de construcción en XLSX, una hoja por tabla (extra ``excel``)."""
    from trawlkit.batch.export import to_xlsx

    sheets = [
        (t.title, [c.heading for c in t.columns], [list(r) for r in t.rows])
        for t in guide_tables(g)
    ]
    sheets.append(("Supuestos", ["Supuesto"], [[n] for n in g.notes]))
    return to_xlsx(sheets)


__all__ = [
    "construction_html",
    "construction_pdf",
    "construction_xlsx",
    "guide_tables",
    "bom_table",
    "piece_svg",
    "report_tables",
]


def bom_table(result: Any) -> Table:
    """Lista de materiales del caso como tabla del informe (sin precios cargados)."""
    from trawlkit.cost import bill_of_materials

    bom = bill_of_materials(result)
    return Table(
        "lista_materiales",
        "Lista de materiales",
        (
            Column("label", "Ítem"),
            Column("component", "Componente"),
            Column("quantity", "Cantidad"),
            Column("unit", "Unidad"),
            Column("cost", "Costo"),
        ),
        tuple(
            (
                ln.label,
                ln.component_name or ln.component_id or "—",
                _r(ln.quantity, 2),
                ln.unit,
                None if ln.cost is None else _r(ln.cost, 2),
            )
            for ln in bom.lines
        ),
        note="Precios orientativos del catálogo de componentes; sin precio la línea queda vacía.",
    )


def report_tables(result: Any) -> list[Table]:
    """Tablas de la guía (red estándar) y la lista de materiales para el informe del caso.

    Si la red no admite la guía (falta un dato del armado) se devuelve sólo la lista.
    """
    from trawlkit.construction import guide

    out = [bom_table(result)]
    try:
        out += guide(result).tables()
    except (ValueError, KeyError, ZeroDivisionError, IndexError):
        pass
    return out
