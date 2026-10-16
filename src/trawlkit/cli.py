"""Interfaz de línea de comandos de trawlkit."""

from __future__ import annotations

import typer

from trawlkit import __version__
from trawlkit.compat import ERRATA

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


if __name__ == "__main__":
    app()
