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


@app.command()
def run(
    net: Annotated[str, typer.Argument(help="Red (preset de data/ o ruta YAML).")],
    vessel: Annotated[str | None, typer.Option(help="Id del buque del catálogo.")] = None,
    door: Annotated[str | None, typer.Option(help="Id del portón del catálogo.")] = None,
    modified: Annotated[str | None, typer.Option(help="Red modificada (columna G).")] = None,
    class_vessel: Annotated[
        list[str] | None,
        typer.Option(
            help="Otros buques de la clase (repetible). Por defecto, el resto del catálogo, "
            "como hace el Excel con 150 y 180 HP."
        ),
    ] = None,
    compat: Annotated[str, typer.Option(help="excel | corrected")] = "corrected",
    json_path: Annotated[
        Path | None, typer.Option("--json", help="Escribe to_dict() en JSON.")
    ] = None,
) -> None:
    """Corre un caso de diseño completo y muestra el resumen como tabla Markdown."""
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
    case = DesignCase(
        net=load_net(net),
        vessel=v,
        door=d,
        net_modified=load_net(modified) if modified else None,
        class_vessels=others,
        compat=mode,
    )
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


if __name__ == "__main__":
    app()
