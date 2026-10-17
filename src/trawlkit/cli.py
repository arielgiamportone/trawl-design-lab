"""Interfaz de línea de comandos de trawlkit."""

from __future__ import annotations

import dataclasses
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
NetArg = Annotated[str, typer.Argument(help="Red (id de preset de trawlkit/data o ruta YAML).")]
VesselOpt = Annotated[str | None, typer.Option(help="Id del buque del catálogo.")]
DoorOpt = Annotated[str | None, typer.Option(help="Id del portón del catálogo.")]
ModifiedOpt = Annotated[
    str | None, typer.Option(help="Red modificada (columna G; id de preset o ruta YAML).")
]
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
    optimize_: Annotated[
        str | None,
        typer.Option(
            "--optimize",
            help="Agrega la sección de optimización: area | volume | energy (malla 13 × 11, "
            "sin refinado).",
        ),
    ] = None,
    simulate_: Annotated[
        str | None,
        typer.Option(
            "--simulate",
            help="Agrega la simulación de forma a esas velocidades en kn, separadas por coma "
            "(p. ej. 2,3).",
        ),
    ] = None,
    sim_resolution: Annotated[
        int, typer.Option(help="Resolución de la simulación (divisiones por panel, 2–10).")
    ] = 6,
) -> None:
    """Genera el informe completo (HTML, PDF, XLSX y láminas SVG) de un caso de diseño."""
    from trawlkit.report.build import build_report

    formats = [f.strip() for f in format_.split(",") if f.strip()]
    case = build_case(net, vessel, door, modified, class_vessel, compat)
    result = run_case(case)
    optimization = None
    simulation = None
    try:
        if optimize_ is not None:
            from trawlkit.optimize import optimise

            if optimize_ not in ("area", "volume", "energy"):
                raise ValueError("--optimize debe ser area, volume o energy")
            optimization = optimise(case, objective=optimize_, grid=(13, 11), refine=False)
        if simulate_ is not None:
            from trawlkit.sim import sweep

            try:
                speeds = [float(x) for x in simulate_.replace(";", ",").split(",") if x.strip()]
            except ValueError as exc:
                raise ValueError(f"--simulate: velocidades inválidas {simulate_!r}") from exc
            if not speeds or any(not 0.5 <= v <= 6.0 for v in speeds):
                raise ValueError("--simulate: velocidades entre 0,5 y 6 kn")
            if not 2 <= sim_resolution <= 10:
                raise ValueError("--sim-resolution debe estar entre 2 y 10")
            simulation = sweep(result, sorted(set(speeds)), resolution=sim_resolution)
        paths = build_report(result, out, formats, optimization=optimization, simulation=simulation)
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


@app.command()
def optimize(
    net: NetArg,
    vessel: VesselOpt = None,
    door: DoorOpt = None,
    class_vessel: ClassOpt = None,
    objective: Annotated[
        str, typer.Option(help="area (área barrida/h) | energy (R_T/AH) | volume (volumen/h)")
    ] = "area",
    margin: Annotated[float, typer.Option(help="Reserva de tiro: F_T ≥ (1+margin)·R_T.")] = 0.1,
    s_min: Annotated[float, typer.Option(help="Escala mínima de la red.")] = 0.6,
    s_max: Annotated[float, typer.Option(help="Escala máxima de la red.")] = 1.4,
    v_min: Annotated[float, typer.Option(help="Velocidad mínima [kn].")] = 1.5,
    v_max: Annotated[float, typer.Option(help="Velocidad máxima [kn].")] = 4.0,
    propeller: Annotated[
        str | None,
        typer.Option(help="Hélice para el tiro: fixed_pitch | variable_pitch_nozzle."),
    ] = None,
    door_area: Annotated[
        float | None,
        typer.Option(help="Usa un portón semejante al elegido con esta superficie [m²]."),
    ] = None,
    n_s: Annotated[int, typer.Option(help="Puntos de la malla en s.")] = 17,
    n_v: Annotated[int, typer.Option(help="Puntos de la malla en v.")] = 11,
    refine: Annotated[bool, typer.Option(help="Refina con evolución diferencial (scipy).")] = True,
    seed: Annotated[int, typer.Option(help="Semilla del optimizador.")] = 0,
    json_path: Annotated[
        Path | None, typer.Option("--json", help="Escribe el resultado completo en JSON.")
    ] = None,
) -> None:
    """Optimiza la escala de la red y la velocidad de arrastre (resumen Markdown)."""
    from trawlkit.optimize import optimise, scale_door, summary_markdown

    case = build_case(net, vessel, door, None, class_vessel, "corrected")
    try:
        if door_area is not None:
            case = dataclasses.replace(case, door=scale_door(case.door, door_area))
        result = optimise(
            case,
            objective=objective,
            bounds=((s_min, s_max), (v_min, v_max)),
            margin=margin,
            seed=seed,
            grid=(n_s, n_v),
            refine=refine,
            propeller=propeller,
        )
    except (ValueError, RuntimeError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(summary_markdown(result))
    if json_path is not None:
        from trawlkit.api.service import to_jsonable

        json_path.write_text(
            json.dumps(to_jsonable(result.to_dict()), ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        typer.echo(f"JSON escrito en {json_path}")


@app.command()
def serve(
    host: Annotated[str, typer.Option(help="Interfaz de escucha.")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Puerto.")] = 8000,
    reload: Annotated[bool, typer.Option(help="Recarga al cambiar el código.")] = False,
) -> None:
    """Levanta la API HTTP (requiere el extra ``api``)."""
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise typer.BadParameter('instale el extra: pip install "trawlkit[api]"') from exc
    uvicorn.run("trawlkit.api.app:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
