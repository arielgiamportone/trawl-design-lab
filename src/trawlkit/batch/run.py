"""Cálculo por lotes: flota × red, casos y redes cargadas (Fase 14).

* **Flota** (``fleet``): una red elegida se proyecta a cada buque (:func:`~trawlkit.batch.project.
  project_net`).
* **Casos** (``cases``): cada fila es un caso completo (red, buque, portón, modo y cualquier
  parámetro de ``GET /params`` como columna) que se calcula con el motor.
* **Redes** (``nets``): cada red cargada se valida y se calcula con su caso de catálogo
  (:func:`trawlkit.catalog.catalog_case`).

Una fila que falla no detiene el lote: queda con su error. ``progress(i, n)`` se llama después de
cada fila. :func:`estimate_cost_s` da el costo aproximado para la guarda del servidor.
"""

from __future__ import annotations

import dataclasses
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, get_args

from trawlkit.batch.columns import CASES
from trawlkit.batch.fleet import Fleet, FleetVessel, read_fleet
from trawlkit.batch.nets import LoadedNet, read_nets
from trawlkit.batch.project import Projection, ProjectOptions, estimated_runs, project_net
from trawlkit.batch.sheets import RowIssue, Sheet, norm, number, parse_sheet, read_book
from trawlkit.catalog import catalog_case
from trawlkit.compat import Compat
from trawlkit.io import Door, NetSpec, Vessel, load_doors, load_net, load_vessels
from trawlkit.model import DesignCase, DesignResult, run

Mode = Literal["fleet", "cases", "nets"]
MODES: tuple[Mode, ...] = get_args(Mode)

#: Costo de una corrida del motor [s] (medido: 0,03–0,06 s en un servidor; ×5 en un teléfono).
RUN_COST_S = 0.06
#: Filas máximas de un lote.
MAX_ROWS = 500

Progress = Callable[[int, int], None]

_SHEET_KIND = {
    "flota": "fleet",
    "buques": "fleet",
    "fleet": "fleet",
    "vessels": "fleet",
    "casos": "cases",
    "cases": "cases",
    "paneles": "panels",
    "panels": "panels",
    "red": "nets",
    "redes": "nets",
    "nets": "nets",
    "ayuda": "skip",
    "help": "skip",
    "instrucciones": "skip",
    "leeme": "skip",
}

#: Magnitudes del resumen de un caso calculado (clave de ``DesignResult.summary``).
CASE_SUMMARY = (
    "headrope_m",
    "footrope_m",
    "vertical_opening_m",
    "horizontal_opening_m",
    "rn_std_3kn_kgf",
    "max_speed_kn",
    "warp_selected",
    "warp_diameter_mm",
    "float_count",
    "net_weight_kg",
)


@dataclass
class BatchInput:
    """Lo leído de una planilla para un modo: flota, redes y casos, con sus observaciones."""

    mode: Mode
    fleet: Fleet | None = None
    nets: list[LoadedNet] = field(default_factory=list)
    cases: list[dict[str, Any]] = field(default_factory=list)
    issues: list[RowIssue] = field(default_factory=list)

    @property
    def size(self) -> int:
        """Filas a calcular."""
        if self.mode == "fleet":
            return len(self.fleet.vessels) if self.fleet else 0
        if self.mode == "cases":
            return len(self.cases)
        return len(self.nets)

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable (vista previa)."""
        return {
            "mode": self.mode,
            "size": self.size,
            "fleet": None if self.fleet is None else self.fleet.to_dict(),
            "nets": [n.to_dict() for n in self.nets],
            "cases": self.cases,
            "issues": [i.to_dict() for i in self.issues],
        }


def _kind(sheet: Sheet, mode: Mode, single: bool) -> str:
    k = _SHEET_KIND.get(norm(sheet.name))
    if k:
        return k
    if single or mode == "cases":
        return {"fleet": "fleet", "cases": "cases", "nets": "panels"}[mode]
    return "panels" if mode == "nets" else mode


def read_input(data: bytes | str, filename: str, mode: Mode) -> BatchInput:
    """Lee la planilla para el modo pedido (las hojas se reconocen por su nombre)."""
    if mode not in MODES:
        raise ValueError(f"modo desconocido: {mode!r} (use {', '.join(MODES)})")
    sheets = read_book(data, filename)
    single = len(sheets) == 1
    out = BatchInput(mode=mode)
    by_kind: dict[str, list[Sheet]] = {}
    sheets = [sh for sh in sheets if _SHEET_KIND.get(norm(sh.name)) != "skip"]
    single = len(sheets) == 1
    for sh in sheets:
        by_kind.setdefault(_kind(sh, mode, single), []).append(sh)
    if by_kind.get("fleet"):
        fleets = [read_fleet(sh) for sh in by_kind["fleet"]]
        fl = fleets[0]
        for extra in fleets[1:]:
            fl.vessels += extra.vessels
            fl.issues += extra.issues
        out.fleet = fl
        out.issues += fl.issues
    net_sheets = by_kind.get("panels", []) + by_kind.get("nets", [])
    if net_sheets:
        out.nets, issues = read_nets(net_sheets)
        out.issues += issues
    for sh in by_kind.get("cases", []):
        cases, issues = read_cases(sh)
        out.cases += cases
        out.issues += issues
    if out.size == 0:
        out.issues.append(
            RowIssue("error", "empty", f"la planilla no tiene filas para el modo «{mode}»")
        )
    if out.size > MAX_ROWS:
        out.issues.append(
            RowIssue("error", "too_many", f"{out.size} filas: el máximo es {MAX_ROWS}")
        )
    return out


# -- casos -------------------------------------------------------------------------------------


def _param_types() -> dict[str, str]:
    skip = {"net", "net_modified", "vessel", "door", "class_vessels", "compat", "assumptions"}
    return {f.name: str(f.type) for f in dataclasses.fields(DesignCase) if f.name not in skip}


def _param(type_name: str, cell: Any, decimal_comma: bool) -> Any:
    t = type_name.replace(" ", "").removesuffix("|None")
    if t == "bool":
        v = norm(str(cell))
        if v in ("si", "s", "yes", "true", "1", "x"):
            return True
        if v in ("no", "n", "false", "0"):
            return False
        raise ValueError("se espera sí o no")
    if t == "float":
        return number(cell, decimal_comma)
    if t == "int":
        x = number(cell, decimal_comma)
        if abs(x - round(x)) > 1e-9:
            raise ValueError("se espera un entero")
        return int(round(x))
    if t.startswith("tuple[float"):
        return tuple(number(x, decimal_comma) for x in str(cell).replace("|", ";").split(";"))
    if t.startswith("tuple[str"):
        return tuple(x.strip() for x in str(cell).split(";") if x.strip())
    return str(cell).strip()


def read_cases(sheet: Sheet) -> tuple[list[dict[str, Any]], list[RowIssue]]:
    """Casos de una hoja: columnas de :data:`CASES` más parámetros de ``DesignCase``."""
    parsed = parse_sheet(sheet, CASES)
    issues = list(parsed.issues)
    types = _param_types()
    extra: dict[int, str] = {}
    for i, h in enumerate(sheet.headers):
        if h in parsed.ignored:
            key = norm(h)
            if key in types:
                extra[i] = key
            elif key:
                issues.append(
                    RowIssue(
                        "warning",
                        "unknown_column",
                        f"columna «{h}» no reconocida (no es un parámetro de GET /params)",
                        column=h,
                        sheet=sheet.name,
                    )
                )
    bad = {i.row for i in issues if i.level == "error" and i.row is not None}
    rows_by_index = {r: raw for r, raw in enumerate(sheet.rows, start=1)}
    cases: list[dict[str, Any]] = []
    for rec in parsed.records:
        r = rec["_row"]
        if r in bad:
            continue
        params: dict[str, Any] = {}
        raw = rows_by_index.get(r, [])
        for i, key in extra.items():
            cell = raw[i] if i < len(raw) else ""
            if cell is None or str(cell).strip() == "":
                continue
            try:
                params[key] = _param(types[key], cell, sheet.decimal_comma)
            except ValueError as exc:
                issues.append(
                    RowIssue(
                        "error",
                        "bad_value",
                        f"«{cell}» no vale para {key}: {exc}",
                        row=r,
                        column=sheet.headers[i],
                        sheet=sheet.name,
                    )
                )
        cases.append({**rec, "params": params})
    return cases, issues


# -- resultados --------------------------------------------------------------------------------


@dataclass
class BatchRow:
    """Resultado de una fila del lote."""

    index: int
    name: str
    status: Literal["ok", "infeasible", "error"]
    summary: dict[str, Any] = field(default_factory=dict)
    detail: dict[str, Any] | None = None
    error: str | None = None
    notes: list[str] = field(default_factory=list)
    projection: Projection | None = field(default=None, repr=False)

    def to_dict(self, detail: bool = True) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "index": self.index,
            "name": self.name,
            "status": self.status,
            "summary": self.summary,
            "detail": self.detail if detail else None,
            "error": self.error,
            "notes": self.notes,
        }


@dataclass
class BatchResult:
    """Resultado del lote."""

    mode: Mode
    rows: list[BatchRow]
    settings: dict[str, Any]
    issues: list[RowIssue] = field(default_factory=list)
    runtime_s: float = 0.0
    engine_runs: int = 0

    @property
    def counts(self) -> dict[str, int]:
        """Filas por estado."""
        out = {"ok": 0, "infeasible": 0, "error": 0}
        for r in self.rows:
            out[r.status] += 1
        return out

    def to_dict(self, detail: bool = True) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "mode": self.mode,
            "rows": [r.to_dict(detail) for r in self.rows],
            "counts": self.counts,
            "settings": self.settings,
            "issues": [i.to_dict() for i in self.issues],
            "runtime_s": self.runtime_s,
            "engine_runs": self.engine_runs,
        }


def estimate_cost_s(mode: Mode, n: int, options: ProjectOptions | None = None) -> float:
    """Costo estimado del lote [s] (corridas del motor × :data:`RUN_COST_S`)."""
    per = estimated_runs(options or ProjectOptions()) if mode == "fleet" else 1
    return n * per * RUN_COST_S


def run_fleet(
    vessels: Sequence[FleetVessel],
    net: str | NetSpec,
    options: ProjectOptions | None = None,
    progress: Progress | None = None,
) -> BatchResult:
    """Proyecta la red ``net`` a cada buque de la flota."""
    opt = options or ProjectOptions()
    t0 = time.perf_counter()
    spec = load_net(net) if isinstance(net, str) else net
    rows: list[BatchRow] = []
    runs = 0
    for i, fv in enumerate(vessels):
        name = fv.vessel.name or fv.vessel.id
        try:
            p = project_net(spec, fv, opt)
        except (ValueError, KeyError, ZeroDivisionError, IndexError) as exc:
            rows.append(BatchRow(i, name, "error", error=str(exc)))
        else:
            runs += p.engine_runs
            rows.append(
                BatchRow(
                    i,
                    name,
                    "ok" if p.feasible else "infeasible",
                    summary=p.summary(),
                    detail=p.to_dict(),
                    notes=list(p.notes),
                    projection=p,
                )
            )
        if progress:
            progress(i + 1, len(vessels))
    if opt.economics is not None:
        _add_economics(rows, spec, opt.economics)
    settings = {
        "net": spec.id,
        "net_name": spec.name,
        "objective": opt.objective,
        "margin": opt.margin,
        "assemble": opt.assemble,
        "region": opt.region,
        "generic_only": opt.generic_only,
    }
    return BatchResult(
        "fleet", rows, settings, runtime_s=time.perf_counter() - t0, engine_runs=runs
    )


#: Columnas económicas que se suman al resumen de cada buque (Fase 16).
ECONOMIC_KEYS = (
    "fuel_l_trip",
    "catch_kg_trip",
    "revenue_trip",
    "cost_trip",
    "cost_per_kg",
    "margin_trip",
    "margin_year",
)


def _add_economics(rows: list[BatchRow], spec: NetSpec, inputs: Any) -> None:
    """Economía de la marea de cada buque a su velocidad proyectada.

    La captura por hora del usuario vale para la red base, en su caso de diseño, a la velocidad
    de referencia; cada buque pesca en proporción a su área barrida por hora.
    """
    from trawlkit.catalog import catalog_case
    from trawlkit.economics import trip
    from trawlkit.optimize.evaluate import Evaluator

    ev = Evaluator(catalog_case(spec).case)
    lo, hi = float(ev.speeds[0]), float(ev.speeds[-1])
    ref = ev.at(1.0, min(max(inputs.reference_speed_kn, lo), hi)).area_rate_m2_h
    for row in rows:
        p = row.projection
        if p is None or row.summary is None:
            continue
        s = row.summary
        inp = inputs
        if (
            inp.gear_cost is None
            and s.get("cost") is not None
            and s.get("currency") == inp.currency
        ):
            if not s.get("missing_prices"):
                inp = dataclasses.replace(inp, gear_cost=float(s["cost"]))
        t = trip(
            inp,
            speed_kn=float(s["speed_kn"]),
            demand_kgf=float(s["demand_kgf"]),
            area_rate_m2_h=float(s["area_rate_m2_h"]),
            reference_area_rate_m2_h=ref,
            vessel_hp=float(s["bhp"]),
            feasible=bool(s["feasible"]),
        )
        n = inp.trips_per_year
        s.update(
            {
                "fuel_l_trip": t.fuel_l,
                "catch_kg_trip": t.catch_kg,
                "revenue_trip": t.revenue,
                "cost_trip": t.total_cost,
                "cost_per_kg": t.cost_per_kg,
                "margin_trip": t.margin,
                "margin_year": None if t.margin is None else t.margin * n,
            }
        )
        row.notes.extend(f"economía: falta {m}" for m in t.missing[:3])


def _case_summary(result: DesignResult) -> dict[str, Any]:
    s = result.summary()
    return {k: s.get(k) for k in CASE_SUMMARY} | {
        "net_id": s.get("net_id"),
        "vessel_id": s.get("vessel_id"),
        "door_id": s.get("door_id"),
    }


def _door(door_id: str) -> Door:
    doors = {d.id: d for d in load_doors().doors}
    if door_id in doors:
        return doors[door_id]
    from trawlkit.components import DoorItem, get_component

    item = get_component("door", door_id)
    assert isinstance(item, DoorItem)
    return item.to_door()


def build_case(
    rec: dict[str, Any],
    nets: dict[str, NetSpec],
    vessels: dict[str, Vessel],
) -> DesignCase:
    """Caso de una fila de la planilla de casos (ver :func:`read_cases`)."""
    key = norm(rec["net"])
    spec = nets.get(key)
    if spec is None:
        try:
            spec = load_net(rec["net"])
        except FileNotFoundError as exc:
            raise KeyError(f"red desconocida: {rec['net']!r}") from exc
    params = dict(rec.get("params") or {})
    compat = Compat(rec.get("compat", "corrected"))
    vessel_name = rec.get("vessel")
    door_id = rec.get("door")
    if vessel_name is None and spec.vessel_hp is not None:
        case = catalog_case(spec, compat=compat, **params).case
        return case if door_id is None else dataclasses.replace(case, door=_door(door_id))
    catalogue = {v.id: v for v in load_vessels().vessels}
    if vessel_name is None:
        vessel = catalogue["fao_a3_150hp"]
    else:
        found = vessels.get(norm(vessel_name)) or catalogue.get(str(vessel_name))
        if found is None:
            raise KeyError(f"buque desconocido: {vessel_name!r}")
        vessel = found
    door = _door(door_id or "fao_flat_wood_a3")
    return DesignCase(net=spec, vessel=vessel, door=door, compat=compat, **params)


def run_cases(
    cases: Sequence[dict[str, Any]],
    nets: Sequence[LoadedNet] = (),
    fleet: Sequence[FleetVessel] = (),
    progress: Progress | None = None,
) -> BatchResult:
    """Calcula cada caso de la planilla."""
    t0 = time.perf_counter()
    net_map = {norm(n.spec.name): n.spec for n in nets} | {norm(n.spec.id): n.spec for n in nets}
    vessel_map = {norm(fv.vessel.name or fv.vessel.id): fv.vessel for fv in fleet}
    rows: list[BatchRow] = []
    for i, rec in enumerate(cases):
        name = str(rec.get("case") or f"Caso {i + 1}")
        try:
            res = run(build_case(rec, net_map, vessel_map))
        except (ValueError, KeyError, TypeError, ZeroDivisionError, IndexError) as exc:
            msg = exc.args[0] if isinstance(exc, KeyError) and exc.args else str(exc)
            rows.append(BatchRow(i, name, "error", error=str(msg)))
        else:
            rows.append(
                BatchRow(
                    i,
                    name,
                    "ok",
                    summary={"row": rec.get("_row"), "case": name, **_case_summary(res)},
                    notes=list(res.notes),
                )
            )
        if progress:
            progress(i + 1, len(cases))
    return BatchResult(
        "cases", rows, {}, runtime_s=time.perf_counter() - t0, engine_runs=len(cases)
    )


def run_nets(nets: Sequence[LoadedNet], progress: Progress | None = None) -> BatchResult:
    """Valida y calcula cada red cargada con su caso de catálogo."""
    t0 = time.perf_counter()
    rows: list[BatchRow] = []
    for i, ln in enumerate(nets):
        name = ln.spec.name
        errors = sum(1 for c in ln.check if c.level == "error")
        warnings = sum(1 for c in ln.check if c.level == "warning")
        base = {
            "net_id": ln.spec.id,
            "panels": len(ln.spec.panels),
            "errors": errors,
            "warnings": warnings,
        }
        try:
            res = run(catalog_case(ln.spec).case)
        except (ValueError, KeyError, ZeroDivisionError, IndexError) as exc:
            rows.append(BatchRow(i, name, "error", summary=base, error=str(exc)))
        else:
            rows.append(
                BatchRow(
                    i,
                    name,
                    "ok" if ln.ok else "infeasible",
                    summary=base | _case_summary(res),
                    detail=ln.to_dict(),
                    notes=[c.message for c in ln.check],
                )
            )
        if progress:
            progress(i + 1, len(nets))
    return BatchResult("nets", rows, {}, runtime_s=time.perf_counter() - t0, engine_runs=len(nets))


def run_input(
    inp: BatchInput,
    *,
    net: str | NetSpec | None = None,
    options: ProjectOptions | None = None,
    progress: Progress | None = None,
) -> BatchResult:
    """Corre el lote de una planilla leída con :func:`read_input`."""
    if inp.mode == "fleet":
        if inp.fleet is None:
            raise ValueError("la planilla no tiene flota")
        if net is None:
            if len(inp.nets) == 1:
                net = inp.nets[0].spec
            else:
                raise ValueError("elija la red a proyectar (net)")
        res = run_fleet(inp.fleet.vessels, net, options, progress)
    elif inp.mode == "cases":
        res = run_cases(inp.cases, inp.nets, inp.fleet.vessels if inp.fleet else (), progress)
    else:
        res = run_nets(inp.nets, progress)
    res.issues = list(inp.issues)
    return res


__all__ = [
    "CASE_SUMMARY",
    "MAX_ROWS",
    "MODES",
    "RUN_COST_S",
    "BatchInput",
    "BatchResult",
    "BatchRow",
    "Mode",
    "build_case",
    "estimate_cost_s",
    "read_cases",
    "read_input",
    "run_cases",
    "run_fleet",
    "run_input",
    "run_nets",
]
