"""Figuras SVG de la documentación: emblema UTN, banner y diagramas (README y libro).

Escribe en ``docs/_static/img/`` el emblema propio de la UTN e Ingeniería Pesquera (no es un logo
oficial), el banner del README y los diagramas de arquitectura, cadena de cálculo, fases y flujo
de flota, en castellano y en inglés (``*-en.svg``). Los colores son variables CSS dentro de cada
SVG con variante oscura (``prefers-color-scheme: dark``).

Uso: ``uv run python tools/make_figures.py``
"""

from __future__ import annotations

import html
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "_static" / "img"

STYLE = """
<style>
  :root { --ink: #1b2a3a; --muted: #5b6b7b; --line: #9fb3c8; --sea: #e7f0f8; --land: #f6f4ee;
    --accent: #1c5cab; --accent2: #0f8a7e; --warm: #c35a1b; --box: #ffffff; --boxline: #b9c8d8; }
  @media (prefers-color-scheme: dark) {
    :root { --ink: #e6edf3; --muted: #9fb0c0; --line: #4b6075; --sea: #11243a; --land: #1d2733;
      --accent: #6aa7ff; --accent2: #3cc7b5; --warm: #f08a4b; --box: #18212b; --boxline: #3a4b5d; }
  }
  text { font-family: "DejaVu Sans", "Segoe UI", Arial, sans-serif; fill: var(--ink); }
  .muted { fill: var(--muted); }
  .accent { fill: var(--accent); }
  .box { fill: var(--box); stroke: var(--boxline); stroke-width: 1.5; }
  .boxa { fill: var(--box); stroke: var(--accent); stroke-width: 2; }
  .arrow { stroke: var(--muted); stroke-width: 1.8; fill: none; marker-end: url(#arrow); }
  .net { fill: none; stroke: var(--accent); stroke-width: 2; stroke-linejoin: round; }
  .mesh { stroke: var(--accent); stroke-width: 0.8; opacity: 0.55; fill: none; }
</style>
<defs>
  <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"
    orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" style="fill: var(--muted)"/></marker>
</defs>
"""

#: Costa atlántica argentina simplificada (lon, lat), del Río de la Plata a Tierra del Fuego.
COAST: Sequence[tuple[float, float]] = (
    (-58.4, -34.6),
    (-57.2, -35.3),
    (-56.7, -36.3),
    (-57.5, -37.4),
    (-57.55, -38.0),
    (-58.7, -38.6),
    (-61.0, -38.95),
    (-62.3, -38.8),
    (-62.1, -39.6),
    (-62.4, -40.6),
    (-63.0, -41.1),
    (-64.6, -40.8),
    (-65.1, -41.6),
    (-64.9, -42.2),
    (-63.6, -42.5),
    (-63.7, -42.85),
    (-64.4, -42.95),
    (-65.0, -42.75),
    (-64.9, -43.3),
    (-65.3, -44.1),
    (-65.6, -45.0),
    (-66.9, -45.2),
    (-67.5, -45.9),
    (-66.7, -46.7),
    (-65.8, -47.4),
    (-65.9, -48.1),
    (-67.0, -48.6),
    (-67.7, -49.3),
    (-68.4, -50.2),
    (-69.0, -51.0),
    (-68.9, -51.6),
    (-68.4, -52.3),
)
TDF: Sequence[tuple[float, float]] = (
    (-68.6, -52.6),
    (-68.2, -53.1),
    (-67.7, -53.8),
    (-66.7, -54.3),
    (-65.2, -54.7),
    (-66.5, -54.95),
    (-67.3, -54.9),
    (-68.3, -54.85),
    (-68.6, -54.9),
    (-68.6, -52.6),
)

#: Facultades Regionales donde se dicta Ingeniería Pesquera (lon, lat).
SITES = (
    ("FRMDP", "Mar del Plata", -57.55, -38.0),
    ("FRCh", "Puerto Madryn", -65.04, -42.77),
    ("FRTDF", "Ushuaia", -68.3, -54.8),
)


def e(s: str) -> str:
    return html.escape(s, quote=True)


def svg(w: int, h: int, body: str, title: str, desc: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" '
        f'height="{h}" role="img" aria-labelledby="t d"><title id="t">{e(title)}</title>'
        f'<desc id="d">{e(desc)}</desc>{STYLE}{body}</svg>\n'
    )


def map_group(x0: float, y0: float, k: float, labels: bool = True, size: float = 13) -> str:
    """Costa con las tres Facultades; (x0, y0) es la esquina de lon −70, lat −33."""

    def pt(lon: float, lat: float) -> tuple[float, float]:
        return x0 + (lon + 70.0) * k, y0 + (-lat - 33.0) * k

    def path(points: Sequence[tuple[float, float]], close: bool) -> str:
        xy = [pt(lo, la) for lo, la in points]
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in xy)
        return d + (" Z" if close else "")

    # Tierra al oeste de la costa: polígono cerrado por el borde izquierdo.
    land = [(-70.0, -33.0), *COAST, (-70.0, -52.3)]
    out = [
        f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{15 * k:.1f}" height="{23 * k:.1f}" rx="10" '
        'style="fill: var(--sea)"/>',
        f'<path d="{path(land, True)}" style="fill: var(--land); stroke: var(--line); '
        'stroke-width: 1.4"/>',
        f'<path d="{path(TDF, True)}" style="fill: var(--land); stroke: var(--line); '
        'stroke-width: 1.4"/>',
    ]
    for code, city, lon, lat in SITES:
        x, y = pt(lon, lat)
        out.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{size * 0.42:.1f}" '
            'style="fill: var(--warm); stroke: var(--box); stroke-width: 2"/>'
        )
        if labels:
            out.append(
                f'<text x="{x + size * 0.8:.1f}" y="{y - 2:.1f}" font-size="{size}" '
                f'font-weight="700">{e(code)}</text>'
                f'<text x="{x + size * 0.8:.1f}" y="{y + size:.1f}" font-size="{size * 0.8:.1f}" '
                f'class="muted">{e(city)}</text>'
            )
    return "".join(out)


def net_group(x: float, y: float, w: float, h: float) -> str:
    """Silueta en planta de una red de arrastre (alas, cuerpo, copo) con mallas."""
    top, mid = y, y + h / 2
    wing = w * 0.28
    body = w * 0.48
    cod = w - wing - body
    pts = [
        (x, top),
        (x + wing, top + h * 0.18),
        (x + wing + body, mid - h * 0.12),
        (x + wing + body + cod, mid - h * 0.12),
        (x + wing + body + cod, mid + h * 0.12),
        (x + wing + body, mid + h * 0.12),
        (x + wing, top + h * 0.82),
        (x, top + h),
    ]
    d = "M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts)
    mesh = []
    n = 9
    for i in range(1, n):
        f = i / n
        xx = x + wing * 0.3 + (wing + body - wing * 0.3) * f
        half = (h / 2) * (1 - 0.76 * f) * 0.9
        mesh.append(
            f'<line class="mesh" x1="{xx:.1f}" y1="{mid - half:.1f}" x2="{xx:.1f}" '
            f'y2="{mid + half:.1f}"/>'
        )
    for j in (-0.25, 0, 0.25):
        mesh.append(
            f'<line class="mesh" x1="{x + wing:.1f}" y1="{mid + j * h * 0.6:.1f}" '
            f'x2="{x + wing + body + cod:.1f}" y2="{mid + j * h * 0.2:.1f}"/>'
        )
    floats = "".join(
        f'<circle cx="{x + wing * t:.1f}" cy="{top + h * 0.18 * t:.1f}" r="3.2" '
        'style="fill: var(--warm)"/>'
        for t in (0.2, 0.45, 0.7, 0.95)
    )
    return f'<path class="net" d="{d}"/>{"".join(mesh)}{floats}'


# -- emblema y banner --------------------------------------------------------------------------


def emblem(lang: str) -> str:
    """Emblema circular: UTN · Ingeniería Pesquera, costa con las tres FR y la red."""
    ring = (
        "UNIVERSIDAD TECNOLÓGICA NACIONAL · INGENIERÍA PESQUERA · FRTDF · FRCh · FRMDP ·"
        if lang == "es"
        else "UNIVERSIDAD TECNOLÓGICA NACIONAL · FISHERIES ENGINEERING · FRTDF · FRCh · FRMDP ·"
    )
    body = (
        '<circle cx="260" cy="260" r="250" style="fill: var(--box); stroke: var(--accent); '
        'stroke-width: 6"/>'
        '<circle cx="260" cy="260" r="200" style="fill: none; stroke: var(--line); '
        'stroke-width: 1.5"/>'
        '<path id="ring" d="M260,260 m-224,0 a224,224 0 1,1 448,0 a224,224 0 1,1 -448,0" '
        'fill="none"/>'
        '<text font-size="19" font-weight="700" class="accent">'
        '<textPath href="#ring" startOffset="0" textLength="1395" lengthAdjust="spacing">'
        f"{e(ring)}</textPath></text>"
        '<clipPath id="disc"><circle cx="260" cy="260" r="198"/></clipPath>'
        f'<g clip-path="url(#disc)">{map_group(120, 72, 14.0, labels=True, size=14)}</g>'
        f"{net_group(300, 250, 130, 64)}"
        '<text x="260" y="452" font-size="30" font-weight="800" text-anchor="middle" '
        'class="accent">UTN</text>'
    )
    title = "Emblema UTN · Ingeniería Pesquera" if lang == "es" else "UTN · Fisheries Engineering"
    desc = (
        "Emblema propio (no es un logo oficial de la UTN): costa atlántica argentina con las "
        "Facultades Regionales Mar del Plata, Chubut y Tierra del Fuego, y una red de arrastre."
        if lang == "es"
        else "Own emblem (not an official UTN logo): Argentine Atlantic coast with the Mar del "
        "Plata, Chubut and Tierra del Fuego regional faculties, and a trawl net."
    )
    return svg(520, 520, body, title, desc)


def banner(lang: str) -> str:
    sub = (
        "Diseño, dimensionamiento y armado de redes de arrastre"
        if lang == "es"
        else "Design, sizing and rigging of trawl nets"
    )
    foot = (
        "Nacido en la UTN · Ingeniería Pesquera · FRTDF · FRCh · FRMDP"
        if lang == "es"
        else "Born at UTN (Argentina) · Fisheries Engineering · FRTDF · FRCh · FRMDP"
    )
    tags = (
        "motor Python · API · app sin conexión · libro reproducible"
        if lang == "es"
        else "Python engine · API · offline app · reproducible book"
    )
    body = (
        '<rect x="1" y="1" width="1198" height="318" rx="22" style="fill: var(--box); '
        'stroke: var(--boxline); stroke-width: 2"/>'
        f"{map_group(34, 22, 12.0, labels=True, size=12)}"
        '<text x="290" y="112" font-size="54" font-weight="800">trawl-design-lab</text>'
        '<text x="292" y="156" font-size="26" class="accent" font-weight="700">trawlkit</text>'
        f'<text x="292" y="200" font-size="22">{e(sub)}</text>'
        f'<text x="292" y="236" font-size="17" class="muted">{e(tags)}</text>'
        f'<text x="292" y="288" font-size="17" font-weight="700" class="accent">{e(foot)}</text>'
        f"{net_group(960, 80, 210, 130)}"
    )
    title = "trawl-design-lab · trawlkit"
    desc = sub + ". " + foot
    return svg(1200, 320, body, title, desc)


# -- diagramas ---------------------------------------------------------------------------------


def box(
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    lines: Sequence[str] = (),
    accent: bool = False,
) -> str:
    out = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" '
        f'class="{"boxa" if accent else "box"}"/>'
    ]
    out.append(
        f'<text x="{x + w / 2}" y="{y + 26}" font-size="16" font-weight="700" '
        f'text-anchor="middle">{e(title)}</text>'
    )
    for i, ln in enumerate(lines):
        out.append(
            f'<text x="{x + w / 2}" y="{y + 48 + 18 * i}" font-size="13" '
            f'text-anchor="middle" class="muted">{e(ln)}</text>'
        )
    return "".join(out)


def arrow(x1: float, y1: float, x2: float, y2: float) -> str:
    return f'<path class="arrow" d="M{x1},{y1} L{x2},{y2}"/>'


T = {
    "es": {
        "arch_t": "Arquitectura de trawl-design-lab",
        "data": (
            "Datos abiertos",
            [
                "redes FAO A-3 y catálogo FAO",
                "buques, portones, cables",
                "componentes (290 ítems)",
                "procedencia por valor",
            ],
        ),
        "engine": (
            "Motor trawlkit (Python)",
            [
                "potencia · paños · resistencia",
                "aparejo · cables · velocidad",
                "optimización · simulación",
                "componentes · costo · lotes",
            ],
        ),
        "cli": ("CLI", ["trawlkit run · report", "optimize · batch"]),
        "api": ("API FastAPI", ["Render (Docker)", "/design · /batch · …"]),
        "off": ("Motor sin conexión", ["Pyodide en un Web Worker", "mismas rutas que la API"]),
        "web": ("App web (PWA)", ["React · modo guiado y experto", "GitHub Pages"]),
        "book": ("Libro (Jupyter Book)", ["35 capítulos ejecutables", "teoría · validación"]),
        "ci": ("CI", ["pytest · Vitest · e2e", "paridad Excel 1e-6 · Pyodide 1e-9"]),
        "chain_t": "Cadena de cálculo del modelo",
        "chain": [
            ("Potencia", "cap. 10"),
            ("Paños y cortes", "cap. 11"),
            ("Mecánica", "cap. 12"),
            ("Dimensiones", "cap. 13"),
            ("Resistencia", "13 métodos · cap. 14"),
            ("Portones y bridas", "cap. 15"),
            ("Aberturas", "cap. 16"),
            ("Flotación y lastre", "cap. 17"),
            ("Cables", "cap. 18"),
            ("Velocidad viable", "cap. 19"),
        ],
        "phases_t": "Hoja de ruta: fases 0 a 17",
        "phases": [
            ("0–1", "datos abiertos"),
            ("2", "motor validado"),
            ("3", "planos e informes"),
            ("4", "API y app"),
            ("5", "libro"),
            ("6", "optimización"),
            ("7", "simulación"),
            ("8", "v1.0 PyPI"),
            ("9–10", "modo guiado, 3D"),
            ("11", "simulador realista"),
            ("12", "catálogo FAO"),
            ("13", "componentes, sin conexión"),
            ("14", "flotas y lotes"),
            ("15", "guía de taller"),
            ("16", "economía"),
            ("17", "aula UTN"),
        ],
        "fleet_t": "Del puerto a la red: flota, proyección y armado",
        "fleet": [
            ("Planilla", ["flota del puerto", "CSV o Excel"]),
            ("Semejanza", ["s₀ = √(P / P_diseño)", "portón ∝ potencia"]),
            ("Refinado", ["mayor red que cumple", "tiro · apertura · cable"]),
            ("Armado", ["portón, cable, boyas", "e hilo del catálogo"]),
            ("Resultado", ["red escalada · costo", "XLSX · PDF por buque"]),
        ],
    },
    "en": {
        "arch_t": "trawl-design-lab architecture",
        "data": (
            "Open data",
            [
                "FAO A-3 nets and FAO catalogue",
                "vessels, doors, warps",
                "components (290 items)",
                "per-value provenance",
            ],
        ),
        "engine": (
            "trawlkit engine (Python)",
            [
                "power · netting · drag",
                "rigging · warps · speed",
                "optimisation · simulation",
                "components · cost · batches",
            ],
        ),
        "cli": ("CLI", ["trawlkit run · report", "optimize · batch"]),
        "api": ("FastAPI API", ["Render (Docker)", "/design · /batch · …"]),
        "off": ("Offline engine", ["Pyodide in a Web Worker", "same routes as the API"]),
        "web": ("Web app (PWA)", ["React · guided and expert", "GitHub Pages"]),
        "book": ("Book (Jupyter Book)", ["35 executable chapters", "theory · validation"]),
        "ci": ("CI", ["pytest · Vitest · e2e", "Excel parity 1e-6 · Pyodide 1e-9"]),
        "chain_t": "Calculation chain of the model",
        "chain": [
            ("Power", "ch. 10"),
            ("Netting and cuts", "ch. 11"),
            ("Net mechanics", "ch. 12"),
            ("Dimensions", "ch. 13"),
            ("Drag", "13 methods · ch. 14"),
            ("Doors and bridles", "ch. 15"),
            ("Openings", "ch. 16"),
            ("Floats and ballast", "ch. 17"),
            ("Warps", "ch. 18"),
            ("Feasible speed", "ch. 19"),
        ],
        "phases_t": "Roadmap: phases 0 to 17",
        "phases": [
            ("0–1", "open data"),
            ("2", "validated engine"),
            ("3", "plans and reports"),
            ("4", "API and app"),
            ("5", "book"),
            ("6", "optimisation"),
            ("7", "simulation"),
            ("8", "v1.0 PyPI"),
            ("9–10", "guided mode, 3D"),
            ("11", "realistic simulator"),
            ("12", "FAO catalogue"),
            ("13", "components, offline"),
            ("14", "fleets and batches"),
            ("15", "workshop guide"),
            ("16", "economics"),
            ("17", "UTN classroom"),
        ],
        "fleet_t": "From the port to the net: fleet, projection and rigging",
        "fleet": [
            ("Spreadsheet", ["the port's fleet", "CSV or Excel"]),
            ("Similarity", ["s₀ = √(P / P_design)", "door ∝ power"]),
            ("Refinement", ["largest feasible net", "pull · opening · warp"]),
            ("Rigging", ["door, warp, floats", "and twine from catalogue"]),
            ("Result", ["scaled net · cost", "XLSX · PDF per vessel"]),
        ],
    },
}


def architecture(lang: str) -> str:
    t = T[lang]
    b = [
        f'<text x="600" y="34" font-size="22" font-weight="800" text-anchor="middle">'
        f"{e(t['arch_t'])}</text>"
    ]
    b.append(box(40, 70, 300, 130, t["data"][0], t["data"][1]))
    b.append(box(450, 70, 300, 130, t["engine"][0], t["engine"][1], accent=True))
    b.append(box(860, 70, 300, 130, t["ci"][0], t["ci"][1]))
    b.append(arrow(340, 135, 448, 135))
    b.append(arrow(752, 135, 858, 135))
    xs = (30, 264, 498, 732, 966)
    keys = ("cli", "api", "off", "book", "web")
    for x, k in zip(xs, keys, strict=True):
        b.append(box(x, 270, 204, 90, t[k][0], t[k][1]))
        b.append(arrow(600, 200, x + 102, 268))
    # La app usa la API o, sin red, el motor del teléfono: conectores por debajo de las cajas.
    b.append('<path class="arrow" d="M366,360 L366,384 L1050,384 L1050,363"/>')
    b.append('<path class="arrow" d="M600,360 L600,374 L1090,374 L1090,363"/>')
    note = (
        "la app usa la API o, sin red, el motor del teléfono"
        if lang == "es"
        else "the app uses the API or, offline, the engine on the phone"
    )
    b.append(
        f'<text x="840" y="406" font-size="13" text-anchor="middle" class="muted">{e(note)}</text>'
    )
    return svg(1200, 420, "".join(b), t["arch_t"], t["arch_t"])


def chain(lang: str) -> str:
    t = T[lang]
    b = [
        f'<text x="600" y="34" font-size="22" font-weight="800" text-anchor="middle">'
        f"{e(t['chain_t'])}</text>"
    ]
    w, h, gap = 206, 70, 30
    for i, (name, ch) in enumerate(t["chain"]):
        row, col = divmod(i, 5)
        c = col if row == 0 else 4 - col
        x = 40 + c * (w + gap)
        y = 64 + row * 130
        b.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" class="box"/>'
            f'<text x="{x + w / 2}" y="{y + 30}" font-size="16" font-weight="700" '
            f'text-anchor="middle">{i + 1}. {e(name)}</text>'
            f'<text x="{x + w / 2}" y="{y + 52}" font-size="13" text-anchor="middle" '
            f'class="muted">{e(ch)}</text>'
        )
        if i < len(t["chain"]) - 1:
            if col < 4:
                if row == 0:
                    b.append(arrow(x + w, y + h / 2, x + w + gap - 2, y + h / 2))
                else:
                    b.append(arrow(x, y + h / 2, x - gap + 2, y + h / 2))
            else:
                b.append(arrow(x + w / 2, y + h, x + w / 2, y + 130 - 2))
    return svg(1200, 290, "".join(b), t["chain_t"], t["chain_t"])


def phases(lang: str) -> str:
    t = T[lang]
    n = len(t["phases"])
    b = [
        f'<text x="600" y="34" font-size="22" font-weight="800" text-anchor="middle">'
        f"{e(t['phases_t'])}</text>",
        '<line x1="50" y1="120" x2="1150" y2="120" style="stroke: var(--line); stroke-width: 4"/>',
    ]
    for i, (code, label) in enumerate(t["phases"]):
        x = 80 + i * (1040 / (n - 1))
        up = i % 2 == 0
        color = "var(--accent)" if i < n - 3 else "var(--accent2)"
        b.append(
            f'<circle cx="{x:.1f}" cy="120" r="11" style="fill: {color}; '
            'stroke: var(--box); stroke-width: 3"/>'
        )
        ty = 86 if up else 162
        b.append(
            f'<text x="{x:.1f}" y="{ty}" font-size="15" font-weight="800" '
            f'text-anchor="middle">{e(code)}</text>'
        )
        b.append(
            f'<text x="{x:.1f}" y="{ty + (-18 if up else 18)}" font-size="12.5" '
            f'text-anchor="middle" class="muted">{e(label)}</text>'
        )
    return svg(1200, 200, "".join(b), t["phases_t"], t["phases_t"])


def fleet_flow(lang: str) -> str:
    t = T[lang]
    b = [
        f'<text x="600" y="34" font-size="22" font-weight="800" text-anchor="middle">'
        f"{e(t['fleet_t'])}</text>"
    ]
    w, gap = 200, 40
    for i, (name, lines) in enumerate(t["fleet"]):
        x = 30 + i * (w + gap)
        b.append(box(x, 64, w, 104, name, lines, accent=i in (1, 2)))
        if i:
            b.append(arrow(x - gap + 2, 116, x - 2, 116))
    return svg(1200, 190, "".join(b), t["fleet_t"], t["fleet_t"])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for lang in ("es", "en"):
        suffix = "" if lang == "es" else "-en"
        files = {
            f"emblema-utn-pesquera{suffix}.svg": emblem(lang),
            f"banner{suffix}.svg": banner(lang),
            f"arquitectura{suffix}.svg": architecture(lang),
            f"cadena-calculo{suffix}.svg": chain(lang),
            f"fases{suffix}.svg": phases(lang),
            f"flujo-flota{suffix}.svg": fleet_flow(lang),
        }
        for name, text in files.items():
            (OUT / name).write_text(text, encoding="utf-8")
            print(f"escrito {OUT / name}")


if __name__ == "__main__":
    main()
