"""Interfaz de línea de comandos de trawlkit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from trawlkit import __version__
from trawlkit.compat import ERRATA, Compat
from trawlkit.io import load_doors, load_net, load_vessels
from trawlkit.model import DesignCase
from trawlkit.model import run as run_case
from trawlkit.report.labels import SUMMARY_LABELS, fmt, label, summary_markdown

__all__ = ["SUMMARY_LABELS", "app", "fmt", "label", "summary_markdown"]

app = typer.Typer(
    help="trawlkit: diseño y dimensionamiento de redes de arrastre.",
    no_args_is_help=True,
)


@app.command()
def version() -> None:
    """Muestra la versión instalada."""
    typer.echo(f"trawlkit {__version__}")


@app.command()
def errata() -> None:
    """Lista las erratas documentadas del modelo Excel original."""
    for e in ERRATA:
        typer.echo(f"[{e.key}] {e.sheet}!{e.cell}: {e.description}")


# Opciones comunes a run/report/plan.
NetArg = Annotated[str, typer.Argument(help="Red (preset de data/ o ruta YAML).")]
VesselOpt = Annotated[str | None, typer.Option(help="Id del buque del catálogo.")]
DoorOpt = Annotated[str | None, typer.Option(help="Id del portón del catálogo.")]
ModifiedOpt = Annotated[str | None, typer.Option(help="Red modificada (columna G).")]
ClassOpt = Annotated[
    list[str] | None,
    typer.Option(
        help="Otros buques de la clase (repetible). Por defecto, el resto del catálogo, "
        "como hace el Excel con 150 y 180 HP."
    ),
]
CompatOpt = Annotated[str, typer.Option(help="excel | corrected")]


def build_case(
    net: str,
    vessel: str | None = None,
    door: str | None = None,
    modified: str | None = None,
    class_vessel: list[str] | None = None,
    compat: str = "corrected",
) -> DesignCase:
    """Arma un :class:`DesignCase` a partir de ids de catálogo y presets/rutas de red."""
    vessels = {v.id: v for v in load_vessels().vessels}
    doors = {d.id: d for d in load_doors().doors}
    try:
        v = vessels[vessel] if vessel else next(iter(vessels.values()))
        d = doors[door] if door else next(iter(doors.values()))
        if class_vessel is None:
            others = tuple(o for o in vessels.values() if o.id != v.id)
        else:
            others = tuple(vessels[c] for c in class_vessel)
    except KeyError as exc:
        raise typer.BadParameter(f"id desconocido: {exc.args[0]!r}") from exc
    try:
        mode = Compat(compat)
    except ValueError as exc:
        raise typer.BadParameter("compat debe ser 'excel' o 'corrected'") from exc
    return DesignCase(
        net=load_net(net),
        vessel=v,
        door=d,
        net_modified=load_net(modified) if modified else None,
        class_vessels=others,
        compat=mode,
    )


@app.command()
def run(
    net: NetArg,
    vessel: VesselOpt = None,
    door: DoorOpt = None,
    modified: ModifiedOpt = None,
    class_vessel: ClassOpt = None,
    compat: CompatOpt = "corrected",
    json_path: Annotated[
        Path | None, typer.Option("--json", help="Escribe to_dict() en JSON.")
    ] = None,
) -> None:
    """Corre un caso de diseño completo y muestra el resumen como tabla Markdown."""
    case = build_case(net, vessel, door, modified, class_vessel, compat)
    result = run_case(case)
    summary = result.summary()
    typer.echo(summary_markdown(summary))
    for note in result.notes:
        typer.echo(f"- {note}")
    if json_path is not None:
        json_path.write_text(
            json.dumps(
                {"summary": summary, "result": result.to_dict()}, ensure_ascii=False, indent=1
            ),
            encoding="utf-8",
        )
        typer.echo(f"JSON escrito en {json_path}")


@app.command()
def report(
    net: NetArg,
    vessel: VesselOpt = None,
    door: DoorOpt = None,
    modified: ModifiedOpt = None,
    class_vessel: ClassOpt = None,
    compat: CompatOpt = "corrected",
    out: Annotated[Path, typer.Option(help="Carpeta de salida.")] = Path("informe"),
    format_: Annotated[
        str, typer.Option("--format", help="Formatos separados por coma: html,pdf,xlsx,svg.")
    ] = "html,pdf,xlsx,svg",
) -> None:
    """Genera el informe completo (HTML, PDF, XLSX y láminas SVG) de un caso de diseño."""
    from trawlkit.report.build import build_report

    formats = [f.strip() for f in format_.split(",") if f.strip()]
    case = build_case(net, vessel, door, modified, class_vessel, compat)
    try:
        paths = build_report(run_case(case), out, formats)
    except (ValueError, RuntimeError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    for p in paths:
        typer.echo(str(p))


@app.command()
def plan(
    net: NetArg,
    vessel: VesselOpt = None,
    door: DoorOpt = None,
    modified: ModifiedOpt = None,
    class_vessel: ClassOpt = None,
    compat: CompatOpt = "corrected",
    view: Annotated[str, typer.Option(help="sheet (lámina) | scale (escala real)")] = "sheet",
    variant: Annotated[str, typer.Option(help="std | mod")] = "std",
    out: Annotated[Path | None, typer.Option(help="Archivo SVG de salida.")] = None,
) -> None:
    """Dibuja el plano de la red (lámina técnica o escala real) en SVG."""
    from trawlkit.drawing import net_scale_svg, net_sheet_svg

    if view not in ("sheet", "scale"):
        raise typer.BadParameter("view debe ser 'sheet' o 'scale'")
    if variant not in ("std", "mod"):
        raise typer.BadParameter("variant debe ser 'std' o 'mod'")
    if variant == "mod" and not modified:
        raise typer.BadParameter("variant 'mod' requiere --modified")
    result = run_case(build_case(net, vessel, door, modified, class_vessel, compat))
    svg = (net_sheet_svg if view == "sheet" else net_scale_svg)(result, variant)
    target = out or Path(f"plano_{'lamina' if view == 'sheet' else 'escala'}_{variant}.svg")
    target.write_text(svg, encoding="utf-8")
    typer.echo(str(target))


if __name__ == "__main__":
    app()
