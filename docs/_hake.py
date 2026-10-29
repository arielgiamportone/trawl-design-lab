"""El motor frente a las redes de merluza del INIDEP (Fase 20.2).

Capítulo «Validación con redes de merluza».

Corre :func:`trawlkit.fieldcheck.reference_point` para cada lance medido y cada simulación DynamiT
de las cinco redes de la fase (con la profundidad, el cable, la velocidad y el portón de cada uno)
y arma las tablas del capítulo. Todo se calcula al compilar el libro.
"""

from __future__ import annotations

import warnings
from functools import cache
from typing import Any

import numpy as np
from _lang import L
from _plots_t1 import fmt

from trawlkit import fieldcheck as F  # noqa: N812
from trawlkit.io import load_net

#: Redes de la fase, en el orden del capítulo.
NETS: tuple[str, ...] = (
    "inidep_iat101_va355_disenada",
    "inidep_iat151_va355_construida",
    "inidep_iat101_engel355",
    "inidep_iat045_baldino_original",
    "inidep_iat045_baldino_modificada",
)
SHORT: dict[str, str] = {
    "inidep_iat101_va355_disenada": L("VA-35,5/45 diseñada", "VA-35.5/45 as designed"),
    "inidep_iat151_va355_construida": L("VA-35,5/45 construida", "VA-35.5/45 as built"),
    "inidep_iat101_engel355": "Engel 35,5 m" if L("es", "en") == "es" else "Engel 35.5 m",
    "inidep_iat045_baldino_original": L("Baldino original", "Baldino original"),
    "inidep_iat045_baldino_modificada": L("Baldino modificada", "Baldino modified"),
}
#: Serie de mediciones → (rótulo, fuente).
SERIES: dict[str, tuple[str, str]] = {
    "iat151": (
        L("IAT 151/18, polivalentes 1200 kg", "IAT 151/18, polyvalent 1200 kg"),
        "bartozzetti2018iat151",
    ),
    "ic029": (L("IC 029/18, SPF08 1000 kg", "IC 029/18, SPF08 1000 kg"), "cabreira2018ic029"),
    "ic012": (L("IC 012/21, SPF08 1000 kg", "IC 012/21, SPF08 1000 kg"), "roth2021ic012"),
    "ic016": (
        L("IC 016/24, SPF 08,5 (Engel)", "IC 016/24, SPF 08.5 (Engel)"),
        "rubio2024calibracion",
    ),
    "it66": (
        L("Inf. Téc. 66, polivalentes 1260 kg", "Tech. Rep. 66, polyvalent 1260 kg"),
        "casarsa2007inftec66",
    ),
    "ic041": (
        L("IC 041/25, media de campaña", "IC 041/25, survey mean"),
        "alvarezcolombo2025ic041",
    ),
}
#: Magnitudes de las tablas: clave de la referencia, atributo del motor, rótulo, decimales.
QTY: tuple[tuple[str, str, str, int], ...] = (
    ("door_spread_m", "door_spread_m", L("DP", "DS"), 1),
    ("wing_spread_m", "wing_spread_m", L("AH", "WS"), 1),
    ("vertical_opening_m", "vertical_opening_m", L("AV", "VO"), 2),
    ("drag_kgf", "total_drag_kgf", L("R", "R"), 0),
)


def _ref_value(ref: dict[str, Any], key: str) -> float | None:
    if key == "wing_spread_m":
        v = ref.get("wing_spread_m", ref.get("horizontal_opening_m"))
    else:
        v = ref.get(key)
    return None if v is None else float(v)


@cache
def points() -> tuple[tuple[str, str, dict[str, Any], F.EnginePoint], ...]:
    """(red, tipo, referencia, motor) para cada medición y simulación."""
    out = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for nid in NETS:
            spec = load_net(nid)
            for kind in ("simulated", "measured"):
                for ref in F.references(spec, kind):
                    out.append((nid, kind, ref, F.reference_point(spec, ref)))
    return tuple(out)


def _dev(e: float, r: float | None) -> float | None:
    d = F.deviation(e, r)
    return None if d is None else 100.0 * d


def _cell(e: float, r: float | None, key: str, nd: int) -> str:
    """«motor / referencia (desvío)», en negrita si sale de la tolerancia."""
    if r is None:
        return f"{fmt(e, nd)} / —"
    d = _dev(e, r)
    assert d is not None
    sign = "+" if d > 0 else "−"
    text = f"{fmt(e, nd)} / {fmt(r, nd)} ({sign}{fmt(abs(d), 0)} %)"
    return f"**{text}**" if abs(d) > 100 * F.TOLERANCES[key] else text


def simulated_rows() -> list[list[str]]:
    """Una fila por simulación DynamiT publicada."""
    rows = []
    for nid, kind, ref, p in points():
        if kind != "simulated":
            continue
        cond = (
            f"{fmt(ref['depth_m'], 0)} m, {fmt(ref['warp_m'], 0)} m, {fmt(ref['speed_kn'], 1)} kn"
        )
        variant = ref.get("variant")
        name = SHORT[nid] + (f" ({variant})" if variant and variant not in nid else "")
        rows.append(
            [name, cond]
            + [_cell(getattr(p, attr), _ref_value(ref, key), key, nd) for key, attr, _, nd in QTY]
        )
    return rows


def series_stats() -> dict[tuple[str, str], dict[str, Any]]:
    """Por (red, serie) y magnitud: n, desvío medio, mínimo, máximo y fracción en tolerancia."""
    acc: dict[tuple[str, str], dict[str, list[float]]] = {}
    meta: dict[tuple[str, str], dict[str, Any]] = {}
    for nid, kind, ref, p in points():
        if kind != "measured":
            continue
        k = (nid, ref["series"])
        m = meta.setdefault(k, {"depth": [], "warp": [], "door": ref["door"], "warp_src": True})
        m["depth"].append(float(ref["depth_m"]))
        m["warp"].append(p.warp_m)
        m["warp_src"] = m["warp_src"] and p.warp_from_source
        for key, attr, _, _ in QTY:
            d = _dev(getattr(p, attr), _ref_value(ref, key))
            if d is not None:
                acc.setdefault(k, {}).setdefault(key, []).append(d)
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for k, m in meta.items():
        q: dict[str, Any] = {}
        for key, ds in acc.get(k, {}).items():
            a = np.asarray(ds)
            q[key] = {
                "n": len(a),
                "mean": float(a.mean()),
                "min": float(a.min()),
                "max": float(a.max()),
                "within": float(np.mean(np.abs(a) <= 100 * F.TOLERANCES[key])),
            }
        out[k] = {**m, "q": q}
    return out


def series_rows() -> list[list[str]]:
    """Una fila por serie de mediciones: condiciones y desvío medio [mín, máx] por magnitud."""
    rows = []
    for (nid, ser), m in series_stats().items():
        d, w = m["depth"], m["warp"]
        cells = []
        for key, _, _, _ in QTY[:3]:
            s = m["q"].get(key)
            if s is None:
                cells.append("—")
                continue
            txt = (
                f"{'+' if s['mean'] > 0 else '−'}{fmt(abs(s['mean']), 0)} % "
                f"[{fmt(s['min'], 0)}; {fmt(s['max'], 0)}] · {fmt(100 * s['within'], 0)} %"
            )
            cells.append(f"**{txt}**" if abs(s["mean"]) > 100 * F.TOLERANCES[key] else txt)
        n = max(s["n"] for s in m["q"].values())
        warp = f"{fmt(min(w), 0)}–{fmt(max(w), 0)}" + ("" if m["warp_src"] else "*")
        rows.append(
            [SHORT[nid], SERIES[ser][0], str(n), f"{fmt(min(d), 0)}–{fmt(max(d), 0)}", warp, *cells]
        )
    return rows


def warp_fits() -> list[dict[str, Any]]:
    """Ajuste DP = a + b·cable de lo medido y del motor en cada serie con cable publicado."""
    out = []
    groups: dict[tuple[str, str], list[tuple[float, float, float]]] = {}
    for nid, kind, ref, p in points():
        if kind == "measured" and p.warp_from_source and ref.get("door_spread_m") is not None:
            groups.setdefault((nid, ref["series"]), []).append(
                (p.warp_m, float(ref["door_spread_m"]), p.door_spread_m)
            )
    for (nid, ser), pts in groups.items():
        if len(pts) < 5:
            continue
        a = np.asarray(pts)
        bm, am = np.polyfit(a[:, 0], a[:, 1], 1)
        be, ae = np.polyfit(a[:, 0], a[:, 2], 1)
        nm = np.polyfit(np.log(a[:, 0]), np.log(a[:, 1]), 1)[0]
        ne = np.polyfit(np.log(a[:, 0]), np.log(a[:, 2]), 1)[0]
        out.append(
            {
                "net": nid,
                "series": ser,
                "n": len(a),
                "slope_measured": float(bm),
                "slope_engine": float(be),
                "exp_measured": float(nm),
                "exp_engine": float(ne),
                "ratio_mean": float(np.mean(a[:, 1] / a[:, 2])),
            }
        )
    return out


def warp_fit_rows() -> list[list[str]]:
    """Tabla de los ajustes de :func:`warp_fits`."""
    return [
        [
            SHORT[f["net"]],
            SERIES[f["series"]][0],
            str(f["n"]),
            fmt(f["slope_measured"], 3),
            fmt(f["slope_engine"], 3),
            fmt(f["exp_measured"], 2),
            fmt(f["exp_engine"], 2),
            fmt(f["ratio_mean"], 2),
        ]
        for f in warp_fits()
    ]


def hauls(series: str) -> list[tuple[dict[str, Any], F.EnginePoint]]:
    """Las mediciones de una serie con su punto del motor."""
    return [(ref, p) for _, k, ref, p in points() if k == "measured" and ref["series"] == series]


def haul_rows(series: str) -> list[list[str]]:
    """Lance por lance: condiciones y motor / medido de DP, AH y AV."""
    rows = []
    for ref, p in hauls(series):
        rows.append(
            [
                str(ref["haul"]),
                fmt(ref["depth_m"], 0),
                fmt(p.warp_m, 0) + ("" if p.warp_from_source else "*"),
                fmt(ref["speed_kn"], 2),
                *[
                    _cell(getattr(p, attr), _ref_value(ref, key), key, nd)
                    for key, attr, _, nd in QTY[:3]
                ],
            ]
        )
    return rows
