"""Superficie requerida del portón contra la potencia (Fase 20.1b; capítulo 15 y erratas).

Corre el caso por defecto de cada buque de la flota (`service.build_case(vessel=…)`: red A-3,
portón plano A-3 a 32°, modo corregido) y lo compara con la tabla Fishbuster de Net Systems
(`rigging.FISHBUSTER_AREA_HP`), la tabla de portones planos del *Workbook* y los portones reales
documentados de los buques de investigación argentinos.
"""

from __future__ import annotations

import warnings
from functools import cache

import numpy as np
from _lang import L
from _plots_t1 import fmt

from trawlkit import rigging
from trawlkit.api import service

#: Portones documentados de la flota: id del buque → (portón, superficie por portón [m²], fuente).
#: Holmberg: Tringali et al. 2012 (EH 06/12); Oca Balda: «el mismo tipo» de equipo que el Holmberg
#: (Dato 2013), así que la superficie es la del Holmberg; Angelescu: Roth y García 2017 (diseño)
#: y Rubio et al. 2024 (SPF 08,5 en uso).
REAL_DOORS: dict[str, tuple[str, float, str]] = {
    "bip_holmberg": (L("polivalente 1200 kg", "polyvalent 1200 kg"), 5.58, "Tringali 2012"),
    "bip_oca_balda": (L("polivalente 1200 kg", "polyvalent 1200 kg"), 5.58, "Dato 2013"),
    "bipo_victor_angelescu": ("Morgère SPF08 1200 kg", 4.5, "Roth & García 2017"),
}
#: Otros portones reales para la figura: (BHP, superficie [m²], rótulo).
EXTRA_DOORS: tuple[tuple[float, float, str], ...] = ((2855.2, 4.8, "Angelescu SPF 08,5"),)


@cache
def fleet_rows() -> tuple[dict[str, object], ...]:
    """Una fila por buque de la flota, ordenada por potencia."""
    rows = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for vid in service.vessel_presets():
            r = service.run_case(service.build_case(vessel=vid))
            req = r.doors.required_area
            bhp = float(r.power.fridman.bhp)
            rows.append(
                {
                    "id": vid,
                    "bhp": bhp,
                    "book": req.book_per_door_m2,
                    "factor": req.power_factor,
                    "corrected": req.per_door_m2,
                    "fishbuster": rigging.fishbuster_area_range_m2(bhp),
                    "real": REAL_DOORS.get(vid),
                }
            )
    rows.sort(key=lambda d: (d["bhp"], d["id"]))  # type: ignore[arg-type,return-value]
    return tuple(rows)


def _range(rng: tuple[float, float] | None) -> str:
    if rng is None:
        return "—"
    lo, hi = rng
    return fmt(lo, 1) if lo == hi else f"{fmt(lo, 1)}–{fmt(hi, 1)}"


def table_rows(min_hp: float = 0.0) -> list[list[str]]:
    """Filas para ``md_table``: buque, BHP, libro, factor, corregida, Fishbuster, portón real."""
    out = []
    for d in fleet_rows():
        if d["bhp"] < min_hp:  # type: ignore[operator]
            continue
        real = d["real"]
        out.append(
            [
                str(d["id"]).replace("_", "_​"),
                fmt(d["bhp"], 0),  # type: ignore[arg-type]
                fmt(d["book"], 2),  # type: ignore[arg-type]
                fmt(d["factor"], 3),  # type: ignore[arg-type]
                f"**{fmt(d['corrected'], 2)}**",  # type: ignore[arg-type]
                _range(d["fishbuster"]),  # type: ignore[arg-type]
                "—" if real is None else f"{fmt(real[1], 2)} ({real[0]}; {real[2]})",
            ]
        )
    return out


TABLE_HEADERS = (
    L("Buque", "Vessel"),
    "BHP",
    L("Libro [m²]", "Book [m²]"),
    L("Factor", "Factor"),
    L("Corregida [m²]", "Corrected [m²]"),
    "Fishbuster [m²]",
    L("Portón real documentado [m²]", "Documented real door [m²]"),
)


def workbook_flat() -> list[tuple[float, float]]:
    """Tabla de portones planos del *Workbook* (potencia media del rango, superficie)."""
    from tools.components.sources import DOOR_FLAT

    return [((lo + hi) / 2.0, area) for (lo, hi), _, _, area, _ in DOOR_FLAT]


def plot(ax, P) -> None:  # noqa: N803 - P es el módulo de estilo del capítulo (_plots_t2)
    """Superficie por portón contra BHP (ejes logarítmicos)."""
    rows = fleet_rows()
    hp = np.array([d["bhp"] for d in rows], dtype=float)
    book = np.array([d["book"] for d in rows], dtype=float)
    k = float(np.median(book / hp))  # la regla del libro es lineal en la potencia
    x = np.geomspace(100, 6000, 200)
    s_book = k * x
    s_corr = s_book * np.array([rigging.door_area_power_factor(v) for v in x])
    for area, lo, hi in rigging.FISHBUSTER_AREA_HP:
        hi = min(hi, 6500.0)
        ax.plot([lo, hi], [area, area], color=P.NEUTRAL, lw=3, alpha=0.45, solid_capstyle="butt")
    ax.plot(
        [],
        [],
        color=P.NEUTRAL,
        lw=3,
        alpha=0.45,
        label=L(
            "Fishbuster (Net Systems): rango de hp por talla",
            "Fishbuster (Net Systems): hp range per size",
        ),
    )
    wb = workbook_flat()
    ax.plot(
        [p[0] for p in wb],
        [p[1] for p in wb],
        ls="none",
        marker="s",
        ms=4,
        color=P.color(3),
        label=L("Workbook, portones planos", "Workbook, flat boards"),
    )
    ax.plot(
        x,
        s_book,
        color=P.color(2),
        lw=1.4,
        ls=(0, (4, 3)),
        label=L("Regla del libro (∝ hp)", "Book rule (∝ hp)"),
    )
    ax.plot(
        x,
        s_corr,
        color=P.color(1),
        lw=1.8,
        label=L("Corregida: × (180/hp)^0,35", "Corrected: × (180/hp)^0.35"),
    )
    ax.plot(hp, book, ls="none", marker="o", mfc="none", color=P.color(2), ms=5)
    ax.plot(
        hp,
        [d["corrected"] for d in rows],
        ls="none",
        marker="o",
        color=P.color(1),
        ms=5,
        label=L("Flota: caso por defecto", "Fleet: default case"),
    )
    real = [(d["bhp"], d["real"][1]) for d in rows if d["real"]]  # type: ignore[index]
    real += [(b, a) for b, a, _ in EXTRA_DOORS]
    ax.plot(
        [p[0] for p in real],
        [p[1] for p in real],
        ls="none",
        marker="*",
        ms=11,
        color=P.INK,
        label=L("Portones reales (INIDEP)", "Real doors (INIDEP)"),
    )
    ax.axvline(rigging.DOOR_AREA_DESIGN_POWER_HP, color=P.AXIS, lw=1)
    ax.annotate(
        "180 HP", (180, 0.6), xytext=(4, 0), textcoords="offset points", color=P.INK_2, fontsize=9
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(100, 6500)
    ax.set_ylim(0.5, 60)
    ax.set_xlabel(L("Potencia del buque [BHP]", "Vessel power [BHP]"))
    ax.set_ylabel(L("Superficie por portón [m²]", "Area per otter board [m²]"))
    P.legend(ax, fontsize=8)
