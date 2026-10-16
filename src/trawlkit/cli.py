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

app = typer.Typer(
    help="trawlkit: diseño y dimensionamiento de redes de arrastre.",
    no_args_is_help=True,
)

#: Etiquetas en español y unidades de las claves de ``DesignResult.summary()``.
SUMMARY_LABELS: dict[str, tuple[str, str]] = {
    "net_id": ("Red", ""),
    "vessel_id": ("Buque", ""),
    "door_id": ("Portón", ""),
    "compat": ("Modo de compatibilidad", ""),
    "headrope_m": ("Lima", "m"),
    "footrope_m": ("Burlón", "m"),
    "cut_angle_deg": ("Ángulo de ataque de los cortes (α)", "°"),
    "filtration_index": ("Índice de filtración (d/l)", ""),
    "solid_surface_m2": ("Superficie sólida (Ss)", "m²"),
    "working_surface_m2": ("Superficie de trabajo (St)", "m²"),
    "net_weight_kg": ("Peso de la red", "kg"),
    "vertical_opening_m": ("Abertura vertical (AV)", "m"),
    "horizontal_opening_m": ("Abertura horizontal (AH)", "m"),
    "working_depth_m": ("Profundidad de trabajo", "m"),
    "flotation_total_kgf": ("Flotación total", "kgf"),
    "dan_leno_m": ("Dan leno", "m"),
    "sweeps_m": ("Patentes", "m"),
    "crowfoot_m": ("Pies de gallo", "m"),
    "crowfoot_extension_m": ("Alargue de pies de gallo", "m"),
    "upper_bridle_m": ("Brida superior", "m"),
    "lower_bridle_m": ("Brida inferior", "m"),
    "warp_diameter_mm": ("Ø cable de remolque", "mm"),
    "warp_length_m": ("Cable filado", "m"),
    "float_count": ("Boyas", "u"),
    "float_diameter_mm": ("Ø boya", "mm"),
    "ballast_min_kg": ("Lastre mínimo", "kg"),
    "ballast_max_kg": ("Lastre máximo", "kg"),
    "warp_selected": ("Cable seleccionado", ""),
    "warp_breaking_load_t": ("Rotura del cable seleccionado", "t"),
    "warp_min_breaking_load_kgf": ("Rotura mínima requerida", "kgf"),
    "warp_quantity_m": ("Cable a comprar", "m"),
    "max_speed_kn": ("Velocidad máxima remolcable", "kn"),
}


def _label(key: str) -> tuple[str, str]:
    if key in SUMMARY_LABELS:
        return SUMMARY_LABELS[key]
    if key.startswith("rn_std_"):
        return (f"RN estándar a {key[7:-4].replace('_', '.')}", "kgf")
    if key.startswith("rob_"):
        return (f"ROB a {key[4:-4].replace('_', '.')}", "kgf")
    return (key, "")


def _fmt(value: float | str | None) -> str:
    if value is None:
        return "—"
    if isinstance(value, str):
        return value
    if float(value).is_integer():
        return f"{int(value)}"
    return f"{value:.4g}" if abs(value) < 1 else f"{value:.5g}"


def summary_markdown(summary: dict[str, float | str | None]) -> str:
    """Tabla Markdown (etiquetas en español, unidades) de ``DesignResult.summary()``."""
    lines = ["| Magnitud | Valor | Unidad |", "|---|---|---|"]
    for key, value in summary.items():
        label, unit = _label(key)
        lines.append(f"| {label} | {_fmt(value)} | {unit} |")
    return "\n".join(lines)


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
