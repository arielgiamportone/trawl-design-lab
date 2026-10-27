"""Flota de buques desde una planilla (Fase 14)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from trawlkit.batch.columns import FLEET
from trawlkit.batch.sheets import Parsed, RowIssue, Sheet, norm, parse_sheet
from trawlkit.catalog import generic_vessel
from trawlkit.i18n import t
from trawlkit.io import PropellerType, Vessel
from trawlkit.power import FRIDMAN_KF


@dataclass(frozen=True)
class FleetVessel:
    """Un buque de la flota y cómo pesca (profundidad, velocidad, puerto, fondo)."""

    vessel: Vessel
    row: int | None = None
    fishing_depth_m: float | None = None
    speed_kn: float | None = None
    region: str | None = None
    seabed: str | None = None
    generic_only: bool = False
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "vessel": self.vessel.model_dump(mode="json"),
            "row": self.row,
            "fishing_depth_m": self.fishing_depth_m,
            "speed_kn": self.speed_kn,
            "region": self.region,
            "seabed": self.seabed,
            "generic_only": self.generic_only,
            "notes": list(self.notes),
        }


@dataclass
class Fleet:
    """Flota leída y observaciones de la lectura."""

    vessels: list[FleetVessel]
    parsed: Parsed
    issues: list[RowIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "vessels": [v.to_dict() for v in self.vessels],
            "columns": self.parsed.columns,
            "ignored": self.parsed.ignored,
            "issues": [i.to_dict() for i in self.issues],
        }


def fleet_vessel(rec: dict[str, Any], used: set[str] | None = None) -> FleetVessel:
    """Buque de una fila ya interpretada; las medidas que faltan se escalan del de la A-3."""
    bhp = float(rec["bhp"])
    name = str(rec.get("name") or t("Buque de {hp:g} hp", hp=bhp))
    base = norm(name) or "buque"
    vid = base
    k = 2
    while used is not None and vid in used:
        vid, k = f"{base}_{k}", k + 1
    if used is not None:
        used.add(vid)
    gen = generic_vessel(bhp, rec.get("length_m"))
    notes: list[str] = []
    dims = {}
    for key in ("length_m", "beam_m", "depth_m"):
        if rec.get(key) is not None:
            dims[key] = float(rec[key])
        else:
            dims[key] = getattr(gen, key)
            notes.append(
                t(
                    "{key} = {value} m escalado del buque de la A-3",
                    key=key,
                    value=getattr(gen, key),
                )
            )
    prop = PropellerType(rec.get("propeller", "fixed_pitch"))
    vessel = Vessel.model_validate(
        {
            "id": vid,
            "name": name,
            "bhp": bhp,
            "propeller": prop,
            "high_rpm": gen.high_rpm,
            "displacement_t": gen.displacement_t,
            **dims,
        }
    )
    if prop not in FRIDMAN_KF:
        notes.append(
            t(
                "hélice {prop}: el tiro se calcula como paso fijo (el libro sólo tabula PF y "
                "PV con tobera)",
                prop=prop.value,
            )
        )
    return FleetVessel(
        vessel=vessel,
        row=rec.get("_row"),
        fishing_depth_m=rec.get("fishing_depth_m"),
        speed_kn=rec.get("speed_kn"),
        region=rec.get("region"),
        seabed=rec.get("seabed"),
        generic_only=rec.get("generic_only") == "true",
        notes=tuple(notes),
    )


def read_fleet(sheet: Sheet) -> Fleet:
    """Flota de una hoja (un buque por fila); las filas con error quedan fuera y se informan."""
    parsed = parse_sheet(sheet, FLEET)
    issues = list(parsed.issues)
    bad = {i.row for i in issues if i.level == "error" and i.row is not None}
    used: set[str] = set()
    vessels: list[FleetVessel] = []
    for rec in parsed.records:
        if rec["_row"] in bad or "bhp" not in rec:
            continue
        try:
            vessels.append(fleet_vessel(rec, used))
        except ValueError as exc:
            issues.append(
                RowIssue("error", "bad_vessel", str(exc), row=rec["_row"], sheet=sheet.name)
            )
    return Fleet(vessels=vessels, parsed=parsed, issues=issues)


__all__ = ["Fleet", "FleetVessel", "fleet_vessel", "read_fleet"]
