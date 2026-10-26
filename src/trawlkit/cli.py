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
    """Arma un :class:`DesignCase` a partir de ids de catálogo y presets/rutas de red.

    Una red del catálogo FAO (con potencia de diseño) sin buque ni portón indicados se calcula
    con su propio caso de diseño (:func:`trawlkit.catalog.catalog_case`).
    """
    spec = load_net(net)
    if spec.vessel_hp is not None and vessel is None and door is None and modified is None:
        from trawlkit.catalog import catalog_case

        try:
            mode = Compat(compat)
        except ValueError as exc:
            raise typer.BadParameter("compat debe ser 'excel' o 'corrected'") from exc
        cc = catalog_case(spec, compat=mode)
        for a in cc.assumptions:
            typer.echo(f"* {a}")
        return cc.case
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
        net=spec,
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
def batch(
    sheet: Annotated[
        Path | None, typer.Argument(help="Planilla CSV o XLSX (flota, redes o casos).")
    ] = None,
    mode: Annotated[str, typer.Option(help="fleet (flota × red) | cases | nets")] = "fleet",
    net: Annotated[
        str | None, typer.Option(help="Red a proyectar a la flota (id del catálogo o ruta YAML).")
    ] = None,
    objective: Annotated[
        str, typer.Option(help="area (mayor red) | energy (R_T/AH) | cost (armado más barato)")
    ] = "area",
    margin: Annotated[float, typer.Option(help="Reserva de tiro: F_T ≥ (1+margin)·R_T.")] = 0.1,
    region: Annotated[str | None, typer.Option(help="Región del puerto (latam, africa…).")] = None,
    generic_only: Annotated[bool, typer.Option(help="Sólo componentes genéricos.")] = False,
    assemble: Annotated[
        bool, typer.Option(help="Elige portón, cable, boyas e hilo del catálogo.")
    ] = True,
    out: Annotated[
        Path | None, typer.Option("-o", "--out", help="Salida: .xlsx, .csv, .json o .pdf.")
    ] = None,
    template: Annotated[
        Path | None,
        typer.Option(help="Escribe una plantilla (de --mode) en esta ruta (.xlsx o .csv) y sale."),
    ] = None,
) -> None:
    """Carga masiva y cálculo por lotes: proyecta una red a una flota, o calcula casos o redes."""
    from trawlkit import batch as bt

    kind = {"fleet": "fleet", "cases": "cases", "nets": "nets"}.get(mode)
    if kind is None:
        raise typer.BadParameter("mode: fleet, cases o nets")
    if template is not None:
        data = bt.template(kind, "csv" if template.suffix.lower() == ".csv" else "xlsx")
        if isinstance(data, str):
            template.write_text(data, encoding="utf-8")
        else:
            template.write_bytes(data)
        typer.echo(f"plantilla escrita en {template}")
        return
    if sheet is None:
        raise typer.BadParameter("falta la planilla (o use --template)")
    inp = bt.read_input(sheet.read_bytes(), sheet.name, kind)  # type: ignore[arg-type]
    for i in inp.issues:
        where = ", ".join(x for x in (i.sheet, f"fila {i.row}" if i.row else "", i.column) if x)
        typer.echo(f"[{i.level}] {where}: {i.message}", err=True)
    spec = None if net is None else load_net(net)
    options = bt.ProjectOptions(
        objective=objective,  # type: ignore[arg-type]
        margin=margin,
        assemble=assemble,
        region=region,
        generic_only=generic_only,
    )
    res = bt.run_input(
        inp,
        net=spec,
        options=options,
        progress=lambda i, n: typer.echo(f"  {i}/{n}", err=True),
    )
    c = res.counts
    typer.echo(
        f"{len(res.rows)} filas: {c['ok']} cumplen, {c['infeasible']} no cumplen, "
        f"{c['error']} con error ({res.runtime_s:.1f} s, {res.engine_runs} corridas del motor)"
    )
    if out is None:
        typer.echo(bt.to_csv(res))
        return
    suffix = out.suffix.lower()
    if suffix == ".xlsx":
        out.write_bytes(bt.result_xlsx(res))
    elif suffix == ".csv":
        out.write_text(bt.to_csv(res), encoding="utf-8")
    elif suffix == ".json":
        from trawlkit.api.service import to_jsonable

        out.write_text(json.dumps(to_jsonable(res.to_dict()), ensure_ascii=False, indent=1))
    elif suffix == ".pdf":
        from trawlkit.report.batch import batch_pdf

        out.write_bytes(batch_pdf(res))
    else:
        raise typer.BadParameter("salida: .xlsx, .csv, .json o .pdf")
    typer.echo(f"resultados en {out}")


@app.command("build-guide")
def build_guide(
    net: NetArg,
    vessel: VesselOpt = None,
    door: DoorOpt = None,
    modified: ModifiedOpt = None,
    variant: Annotated[str, typer.Option(help="std (estándar) | mod (modificada)")] = "std",
    eye_allowance: Annotated[
        float, typer.Option(help="Sobrante por gaza o empalme al cortar cabos [m].")
    ] = 0.5,
    out: Annotated[
        Path | None, typer.Option("-o", "--out", help="Salida: .pdf, .html, .xlsx o .json.")
    ] = None,
) -> None:
    """Guía de construcción para el taller: hoja de corte, armado, montaje en relingas y cortes."""
    from trawlkit.construction import guide
    from trawlkit.report import construction as rc

    if variant not in ("std", "mod"):
        raise typer.BadParameter("variant: std o mod")
    case = build_case(net, vessel, door, modified, None, "corrected")
    g = guide(run_case(case), variant, eye_allowance)  # type: ignore[arg-type]
    typer.echo(
        f"{g.net_name}: {len(g.pieces)} paños, {sum(p.pieces for p in g.pieces)} piezas, "
        f"{len(g.joins)} uniones, {sum(s.weight_kg for s in g.stock):.1f} kg de paño a comprar"
    )
    if out is None:
        for j in g.joins:
            typer.echo(
                f"{j.step:3}. {j.plane}: {j.a} ({j.meshes_a}) + {j.b} ({j.meshes_b}): {j.rule}"
            )
        return
    suffix = out.suffix.lower()
    if suffix == ".pdf":
        out.write_bytes(rc.construction_pdf(g))
    elif suffix in (".html", ".htm"):
        out.write_text(rc.construction_html(g), encoding="utf-8")
    elif suffix == ".xlsx":
        out.write_bytes(rc.construction_xlsx(g))
    elif suffix == ".json":
        from trawlkit.api.service import to_jsonable

        out.write_text(json.dumps(to_jsonable(g.to_dict()), ensure_ascii=False, indent=1))
    else:
        raise typer.BadParameter("salida: .pdf, .html, .xlsx o .json")
    typer.echo(f"guía escrita en {out}")


@app.command("economics")
def economics_cmd(
    net: NetArg,
    vessel: VesselOpt = None,
    door: DoorOpt = None,
    inputs: Annotated[
        Path | None,
        typer.Option(help="Datos de la operación en YAML o JSON (campos de EconomicInputs)."),
    ] = None,
    currency: Annotated[str | None, typer.Option(help="Moneda (ARS, USD…).")] = None,
    fuel_price: Annotated[float | None, typer.Option(help="Precio del gasoil por litro.")] = None,
    lube_price: Annotated[float | None, typer.Option(help="Precio del lubricante por L.")] = None,
    catch_kg_h: Annotated[
        float | None,
        typer.Option(help="Captura por hora de arrastre a la velocidad de referencia."),
    ] = None,
    price_kg: Annotated[float | None, typer.Option(help="Precio en playa por kg.")] = None,
    crew_share: Annotated[float | None, typer.Option(help="Parte de la tripulación (0–1).")] = None,
    gear_cost: Annotated[float | None, typer.Option(help="Costo de la red y el aparejo.")] = None,
    trip_costs: Annotated[
        float | None, typer.Option(help="Hielo, víveres, carnada y puerto por marea.")
    ] = None,
    annual_costs: Annotated[
        float | None, typer.Option(help="Permisos, seguro y otros fijos por año.")
    ] = None,
    out: Annotated[Path | None, typer.Option("-o", "--out", help="Salida .json o .csv.")] = None,
) -> None:
    """Economía de la operación: costo, ingreso y margen de una marea a cada velocidad."""
    import yaml

    from trawlkit.api.service import to_jsonable
    from trawlkit.economics import EconomicInputs, economics

    data: dict[str, object] = {}
    if inputs is not None:
        loaded = yaml.safe_load(inputs.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise typer.BadParameter("inputs: se espera un mapa de campos")
        data.update(loaded)
    flags = {
        "currency": currency,
        "fuel_price_l": fuel_price,
        "lube_price_l": lube_price,
        "catch_kg_h": catch_kg_h,
        "price_kg": price_kg,
        "crew_share": crew_share,
        "gear_cost": gear_cost,
        "trip_costs": trip_costs,
        "annual_costs": annual_costs,
    }
    data.update({k: v for k, v in flags.items() if v is not None})
    try:
        inp = EconomicInputs.from_dict(data)
    except (TypeError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    case = build_case(net, vessel, door, None, None, "corrected")
    res = economics(case, inp)

    def f(x: float | None, nd: int = 0) -> str:
        return "—" if x is None else f"{x:,.{nd}f}".replace(",", " ").replace(".", ",")

    typer.echo(
        f"| v [kn] | cumple | gasoil [L] | captura [kg] | costo/kg [{inp.currency}] | margen |"
    )
    typer.echo("|---|---|---|---|---|---|")
    for t in res.trips:
        typer.echo(
            f"| {f(t.speed_kn, 2)} | {'sí' if t.feasible else 'no'} | {f(t.fuel_l)} | "
            f"{f(t.catch_kg)} | {f(t.cost_per_kg, 2)} | {f(t.margin)} |"
        )
    typer.echo(
        f"Mayor margen: {f(res.best_margin_kn, 2)} kn · menor costo por kg: "
        f"{f(res.best_cost_kg_kn, 2)} kn · menos gasoil por kg: {f(res.least_fuel_kg_kn, 2)} kn"
    )
    missing = sorted({m for t in res.trips for m in t.missing})
    if missing:
        typer.echo("Faltan datos: " + ", ".join(missing))
    if out is None:
        return
    if out.suffix.lower() == ".json":
        out.write_text(json.dumps(to_jsonable(res.to_dict()), ensure_ascii=False, indent=1))
    elif out.suffix.lower() == ".csv":
        cols = ["speed_kn", "feasible", "fuel_l", "catch_kg", "revenue", "total_cost"]
        cols += ["margin", "cost_per_kg", "breakeven_price"]
        lines = [";".join(cols)]
        for t in res.trips:
            d = t.to_dict()
            lines.append(";".join("" if d[c] is None else str(d[c]) for c in cols))
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        raise typer.BadParameter("salida: .json o .csv")
    typer.echo(f"resultado en {out}")


exercises_app = typer.Typer(
    help="Banco de ejercicios del modo docente: listar, ver, resolver e imprimir guías.",
    no_args_is_help=True,
)
app.add_typer(exercises_app, name="exercises")

SeedOpt = Annotated[int, typer.Option(help="Semilla de los datos (0 = los del libro).")]


@exercises_app.command("list")
def exercises_list(
    chapter: Annotated[
        str | None, typer.Option(help="Capítulo del libro (14_resistencia).")
    ] = None,
    level: Annotated[str | None, typer.Option(help="basico, intermedio o avanzado.")] = None,
) -> None:
    """Lista los ejercicios del banco."""
    from trawlkit.teaching import bank

    for e in bank(chapter, level):
        typer.echo(f"{e.id:34s} {e.level:11s} {e.chapter:24s} {e.title}")


@exercises_app.command("show")
def exercises_show(exercise_id: str, seed: SeedOpt = 0) -> None:
    """Muestra el enunciado de un ejercicio."""
    from trawlkit.teaching import UnknownExerciseError, instantiate

    try:
        ex = instantiate(exercise_id, seed)
    except UnknownExerciseError as exc:
        raise typer.BadParameter(f"ejercicio desconocido: {exercise_id}") from exc
    typer.echo(f"{ex.title} ({ex.level}, semilla {seed})\n\n{ex.statement}\n")
    for d in ex.data:
        typer.echo(f"  {d.label}: {d.text} {d.unit}".rstrip())
    typer.echo("")
    for a in ex.answers:
        typer.echo(f"  ? {a.label}" + (f" [{a.unit}]" if a.unit else ""))


@exercises_app.command("solve")
def exercises_solve(exercise_id: str, seed: SeedOpt = 0) -> None:
    """Muestra las respuestas y la explicación de un ejercicio."""
    from trawlkit.teaching import UnknownExerciseError, exercise, solve

    try:
        spec = exercise(exercise_id)
    except UnknownExerciseError as exc:
        raise typer.BadParameter(f"ejercicio desconocido: {exercise_id}") from exc
    sol = solve(exercise_id, seed)
    for a in spec.answers:
        typer.echo(f"{a.label}: {sol.texts[a.key]} {a.unit}".rstrip())
    typer.echo(f"\n{sol.explanation}")


@exercises_app.command("sheet")
def exercises_sheet(
    out: Annotated[Path, typer.Option("-o", "--out", help="Salida .html o .pdf.")],
    chapter: Annotated[str | None, typer.Option(help="Capítulo del libro.")] = None,
    level: Annotated[str | None, typer.Option(help="basico, intermedio o avanzado.")] = None,
    ids: Annotated[
        list[str] | None, typer.Option("--id", help="Ejercicio (se puede repetir).")
    ] = None,
    seed: SeedOpt = 0,
    key: Annotated[bool, typer.Option(help="Clave de respuestas en lugar de enunciados.")] = False,
    title: Annotated[str, typer.Option(help="Título de la guía.")] = "Guía de ejercicios",
) -> None:
    """Guía imprimible de enunciados o su clave de respuestas."""
    from trawlkit.report.exercises import exercise_sheet_html, exercise_sheet_pdf
    from trawlkit.teaching import bank, exercise, instantiate, solve

    chosen = [exercise(i).id for i in ids] if ids else [e.id for e in bank(chapter, level)]
    if not chosen:
        raise typer.BadParameter("no hay ejercicios con esos filtros")
    items = [(instantiate(i, seed), solve(i, seed) if key else None) for i in chosen]
    text = exercise_sheet_html(items, title=title)
    if out.suffix.lower() == ".html":
        out.write_text(text, encoding="utf-8")
    elif out.suffix.lower() == ".pdf":
        out.write_bytes(exercise_sheet_pdf(text))
    else:
        raise typer.BadParameter("salida: .html o .pdf")
    typer.echo(f"{len(items)} ejercicios en {out}")


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
