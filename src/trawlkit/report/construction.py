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

from trawlkit.i18n import N_, fmt_num, get_lang, t
from trawlkit.report.tables import Column, Table

if TYPE_CHECKING:
    from trawlkit.construction import ConstructionGuide, CutPiece

VARIANT_NAME = {"std": N_("estándar"), "mod": N_("modificada")}


def _fmt(v: Any, nd: int = 2) -> str:
    if v is None or v == "":
        return "—"
    if isinstance(v, bool):
        return t("sí") if v else t("no")
    if isinstance(v, float):
        return fmt_num(v, nd)
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
        t("Hoja de corte"),
        (
            Column("id", t("Paño")),
            Column("name", t("Nombre")),
            Column("planes", t("Cara")),
            Column("pieces", t("Piezas")),
            Column("material", t("Material")),
            Column("mesh", t("Mallero"), "mm"),
            Column("twine", t("Ø hilo"), "mm"),
            Column("mouth", t("Mallas boca")),
            Column("codend", t("Mallas bolsa")),
            Column("depth", t("Mallas alto")),
            Column("cut", t("Corte de cada costado")),
            Column("start", t("Por dónde empezar")),
            Column("weight", t("Peso por pieza"), "kg"),
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
                    f"{s.side}: {s.instruction}{t(' (inferido)') if s.inferred else ''}"
                    for s in p.sides
                ),
                p.start,
                _r(p.weight_kg),
            )
            for p in g.pieces
        ),
        note=t(
            "Mallas contadas a malla estirada. Las piezas de ala van de a pares (izquierda y "
            "derecha, una el reflejo de la otra)."
        ),
    )
    stock = Table(
        "construccion_pano",
        t("Paño a comprar"),
        (
            Column("material", t("Material")),
            Column("mesh", t("Mallero"), "mm"),
            Column("twine", t("Ø hilo"), "mm"),
            Column("rtex", "Rtex"),
            Column("pieces", t("Piezas")),
            Column("width", t("Ancho"), t("mallas")),
            Column("depth", t("Alto"), t("mallas")),
            Column("weight", t("Peso del paño"), "kg"),
            Column("finished", t("Peso cortado"), "kg"),
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
        note=t(
            "Tira del ancho del paño más ancho de cada calidad, con el alto que junta el área "
            "de todos los rectángulos de corte; el peso incluye el desperdicio de los cortes."
        ),
    )
    joins = Table(
        "construccion_armado",
        t("Armado: uniones paso a paso"),
        (
            Column("step", t("Paso")),
            Column("plane", t("Cara")),
            Column("a", t("Paño A")),
            Column("a_edge", t("Borde A")),
            Column("b", t("Paño B")),
            Column("b_edge", t("Borde B")),
            Column("meshes_a", t("Mallas A")),
            Column("meshes_b", t("Mallas B")),
            Column("times", t("Veces")),
            Column("ratio", t("Relación")),
            Column("rule", t("Cómo unir")),
            Column("note", t("Nota")),
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
        t("Montaje en relingas"),
        (
            Column("rope", t("Relinga")),
            Column("part", t("Tramo")),
            Column("panels", t("Paños")),
            Column("times", t("Veces")),
            Column("rope_m", t("Cabo"), "m"),
            Column("meshes", t("Mallas a armar")),
            Column("netting_m", t("Paño estirado"), "m"),
            Column("hanging", t("Coef. de armado E")),
            Column("per_m", t("Mallas por metro")),
            Column("schedule", t("Pauta")),
            Column("warning", t("Aviso")),
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
        note=t(
            "E = largo de cabo / largo del paño estirado. En las alas el paño se arma por su "
            "costado (una malla por cada fila de alto)."
        ),
    )
    floats = Table(
        "construccion_boyas",
        t("Boyas sobre la lima (Ø {d} mm)", d=_fmt(g.float_diameter_mm, 0)),
        (
            Column("n", t("Boya")),
            Column("x", t("Desde el centro"), "m"),
            Column("zone", t("Zona")),
        ),
        tuple((f.number, _r(f.x_m, 2), f.zone) for f in g.floats),
        note=t("Negativo: hacia el ala izquierda; positivo: hacia la derecha."),
    )
    ballast = Table(
        "construccion_lastre",
        t("Lastre del burlón"),
        (
            Column("zone", t("Zona")),
            Column("where", t("Dónde")),
            Column("kg_min", t("Lastre mínimo"), "kg"),
            Column("kg_m_min", t("Mínimo"), "kg/m"),
            Column("kg_max", t("Lastre máximo"), "kg"),
            Column("kg_m_max", t("Máximo"), "kg/m"),
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
        note=t(
            "Mínimo para la red modificada a 1 kn y máximo para la estándar a 3 kn (libro, "
            "hoja Flotación y Lastre)."
        ),
    )
    ropes = Table(
        "construccion_cortes",
        t("Cortes de cabos, cables y cadenas"),
        (
            Column("label", t("Pieza")),
            Column("material", t("Material")),
            Column("pieces", t("Cantidad")),
            Column("length", t("Largo terminado"), "m"),
            Column("eyes", t("Gazas")),
            Column("cut", t("Largo de corte"), "m"),
        ),
        tuple(
            (r.label, r.material, r.pieces, _r(r.length_m, 2), r.eyes, _r(r.cut_m, 2))
            for r in g.ropes
        ),
        note=t("Largo de corte = largo terminado + {m} m por gaza.", m=_fmt(g.eye_allowance_m)),
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
        f"aria-label='{html.escape(t('Croquis del paño {id}', id=p.id))}'>"
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
            f"{t(' <em>(inferido: verificar en el plano)</em>') if s.inferred else ''}</li>"
            for s in p.sides
        )
        info = _kv(
            [
                (t("Cara y sección"), html.escape(f"{p.planes} · {p.section}")),
                (
                    t("Piezas"),
                    f"<span class='big'>{p.pieces}</span>"
                    + (t(" (par izquierda/derecha)") if p.paired else ""),
                ),
                (
                    t("Paño"),
                    html.escape(
                        t(
                            "{material}, mallero {mesh} mm, hilo Ø {twine} mm",
                            material=p.material,
                            mesh=_fmt(p.mesh_mm, 0),
                            twine=_fmt(p.twine_mm),
                        )
                        + (f", R{_fmt(p.rtex, 0)} tex" if p.rtex else "")
                    ),
                ),
                (
                    t("Mallas"),
                    html.escape(
                        t(
                            "boca {mouth} · bolsa {codend} · alto {depth}",
                            mouth=p.meshes_mouth,
                            codend=p.meshes_codend,
                            depth=p.meshes_depth,
                        )
                    ),
                ),
                (
                    t("Rectángulo de corte"),
                    html.escape(
                        t(
                            "{w} × {d} mallas{pair} ({sw} × {sl} m estirado), "
                            "desperdicio {waste} %",
                            w=p.stock_width,
                            d=p.stock_depth,
                            pair=t(" por par") if p.paired else "",
                            sw=_fmt(p.stretched_width_m),
                            sl=_fmt(p.stretched_length_m),
                            waste=_fmt(100 * p.waste, 0),
                        )
                    ),
                ),
                (t("Peso por pieza"), _e(p.weight_kg) + " kg"),
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
        times = t(" · {n} veces", n=j.times) if j.times > 1 else ""
        note = f"<br><span class='small muted'>{html.escape(j.note)}</span>" if j.note else ""
        items.append(
            "<li><span class='check'></span>"
            + t(
                "<strong>Paso {step}</strong> ({plane}{times}): unir el {a_edge} de "
                "<strong>{a}</strong> ({meshes_a} mallas) con el {b_edge} de "
                "<strong>{b}</strong> ({meshes_b} mallas). ",
                step=j.step,
                plane=html.escape(j.plane),
                times=times,
                a_edge=html.escape(j.a_edge),
                a=html.escape(j.a),
                meshes_a=j.meshes_a,
                b_edge=html.escape(j.b_edge),
                b=html.escape(j.b),
                meshes_b=j.meshes_b,
            )
            + f"{html.escape(j.rule[:1].upper() + j.rule[1:])}.{note}</li>"
        )
    return f"<ol class='steps'>{''.join(items)}</ol>"


def construction_html(
    g: ConstructionGuide, generated: _dt.date | None = None, link: str | None = None
) -> str:
    """Guía de construcción en HTML autocontenido, para imprimir en A4 o pasar a PDF."""
    tables = {t.key: t for t in guide_tables(g)}
    date = (generated or _dt.date.today()).isoformat()
    variant = t(VARIANT_NAME.get(g.variant, g.variant))
    total_pieces = sum(p.pieces for p in g.pieces)
    netting = sum(s.weight_kg for s in g.stock)
    intro = t(
        "<p>Red: <strong>{net}</strong> ({variant}). {n_panels} paños, {n_pieces} piezas a "
        "cortar, {n_joins} uniones y {kg} kg de paño a comprar (con desperdicio). Generada el "
        "{date} con trawlkit.</p>",
        net=html.escape(g.net_name),
        variant=html.escape(variant),
        n_panels=len(g.pieces),
        n_pieces=total_pieces,
        n_joins=len(g.joins),
        kg=_fmt(netting, 1),
        date=date,
    )
    if link:
        intro += f"<p class='small'>{t('Caso en la app: {link}', link=html.escape(link))}</p>"
    notes = "".join(f"<li>{html.escape(n)}</li>" for n in g.notes)
    title = t("Guía de construcción")
    return (
        f"<!doctype html><html lang='{get_lang()}'><head><meta charset='utf-8'>"
        f"<title>{title} · {html.escape(g.net_id)}</title><style>{_CSS}</style>"
        "</head><body>"
        f"<h1>{title}</h1>{intro}"
        f"<h2>1. {t('Paño a comprar')}</h2>{_table_html(tables['construccion_pano'], wide=True)}"
        f"<h2>2. {t('Hoja de corte')}</h2>{_pieces_html(g)}"
        f"<h2>3. {t('Armado paso a paso')}</h2>{_steps_html(g)}"
        f"<h2>4. {t('Montaje en relingas')}</h2>"
        f"{_table_html(tables['construccion_montaje'], wide=True)}"
        f"<h3>{t('Boyas')}</h3>{_table_html(tables['construccion_boyas'])}"
        f"<h3>{t('Lastre')}</h3>{_table_html(tables['construccion_lastre'], wide=True)}"
        f"<h2>5. {t('Cortes de cabos, cables y cadenas')}</h2>"
        f"{_table_html(tables['construccion_cortes'])}"
        f"<h2>{t('Supuestos')}</h2><ul class='small muted'>{notes}</ul>"
        "<p class='small muted'>"
        + t(
            "Resultados orientativos: verifique con el plano de la red y en la prueba de mar "
            "antes de construir en serie."
        )
        + "</p></body></html>"
    )


def construction_pdf(g: ConstructionGuide) -> bytes:
    """Guía de construcción en PDF (WeasyPrint, extra ``report``)."""
    from trawlkit.report.pdf import flatten_css_vars

    try:
        from weasyprint import HTML
    except (ImportError, OSError) as exc:  # pragma: no cover - depende del entorno
        raise RuntimeError(
            t('el PDF necesita WeasyPrint: pip install "trawlkit[report]" (y Pango)')
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
    sheets.append((t("Supuestos"), [t("Supuesto")], [[n] for n in g.notes]))
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
        t("Lista de materiales"),
        (
            Column("label", t("Ítem")),
            Column("component", t("Componente")),
            Column("quantity", t("Cantidad")),
            Column("unit", t("Unidad")),
            Column("cost", t("Costo")),
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
        note=t(
            "Precios orientativos del catálogo de componentes; sin precio la línea queda vacía."
        ),
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
