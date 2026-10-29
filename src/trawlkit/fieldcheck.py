"""El motor frente a mediciones en el mar y simulaciones publicadas de una red (Fase 20.2).

Las redes del catálogo pueden traer, además del plano, los lances medidos (``measured``) y las
simulaciones DynamiT (``simulated``) de su fuente, cada uno con la profundidad, el cable filado,
la velocidad y el portón de la serie (clave de ``validation_doors``). :func:`engine_point` corre el
caso de la red (:func:`trawlkit.catalog.catalog_case`, modo corregido, métodos del libro sin
cambios) con esas condiciones:

* la profundidad del lance (``depth_m``) y, si la fuente lo da, su cable filado
  (``DesignCase.measured_warp_m``; si no, el de la tabla del libro por profundidad);
* el portón de la serie (superficie, peso y polar, :func:`trawlkit.catalog.door_from_params`);
* las patentes de la serie si las da (``sweeps_m``).

Devuelve las magnitudes que se comparan: separación de portones (la de Fridman promediada entre
2 y 4 kn, como en todo caso del catálogo), abertura horizontal del libro (``Dim!F61``), abertura
vertical de Suzuki (``Mec!D255``) y, a la velocidad del lance, la DPA y la AV de Fridman, la
resistencia de la red (Aberdeen) y la total (``Rem!H118`` + portones). Las magnitudes que dependen
de la velocidad se interpolan linealmente entre las velocidades de cálculo (1–5 kn cada 0,5 kn):
agregar la velocidad del lance a la grilla cambiaría el promedio de 2–4 kn de la separación.

Calibración (Fase 20.5, sólo modo corregido): :func:`warp_exponent_fit` ajusta el exponente de la
corrección de cable de la DPA de Fridman (:data:`trawlkit.rigging.DP_WARP_EXPONENT_CORRECTION`) y
:func:`polyvalent_cl_fit` el CL efectivo del portón polivalente
(:data:`trawlkit.rigging.POLYVALENT_CL_EFFECTIVE_FACTOR`). ``engine_point(calibrated=False)`` da
el motor sin calibrar, para comparar.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np

from trawlkit.catalog import catalog_case, door_from_params
from trawlkit.i18n import t
from trawlkit.io import Door, NetSpec, load_net
from trawlkit.model import DesignCase, door_cl_factor, dp_warp_factor, run
from trawlkit.rigging import table_warp_m

#: Magnitudes comparadas: clave de la medición o simulación y atributo de :class:`EnginePoint`.
QUANTITIES: dict[str, str] = {
    "door_spread_m": "door_spread_m",
    "wing_spread_m": "wing_spread_m",
    "horizontal_opening_m": "wing_spread_m",
    "vertical_opening_m": "vertical_opening_m",
    "drag_kgf": "total_drag_kgf",
}

#: Tolerancias declaradas del capítulo «Validación con redes de merluza» (desvío relativo del motor
#: frente a la medición o la simulación). Son las de un modelo de diseño, no de calibración: la
#: separación de portones y las aberturas medidas varían 8–9 % de lance a lance en un mismo
#: aparejo (CV de la tabla 1 de IAT 151/2018: 0,081 en la DP y 0,087 en la AV) y los portones de
#: varias series no publican su polar.
TOLERANCES: dict[str, float] = {
    "door_spread_m": 0.20,
    "wing_spread_m": 0.20,
    "horizontal_opening_m": 0.20,
    "vertical_opening_m": 0.30,
    "drag_kgf": 0.25,
}


@dataclass(frozen=True)
class EnginePoint:
    """Resultado del motor en las condiciones de un lance o de una simulación."""

    depth_m: float
    speed_kn: float
    warp_m: float
    warp_from_source: bool
    warp_table_m: float
    dp_warp_factor: float
    door_cl_factor: float
    door_id: str
    door_area_m2: float
    sweeps_m: float
    door_spread_m: float
    wing_spread_m: float
    dpa_fridman_m: float
    vertical_opening_m: float
    av_fridman_m: float
    net_drag_kgf: float
    total_drag_kgf: float

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclasses.asdict(self)


def _spec(net: str | NetSpec) -> NetSpec:
    return load_net(net) if isinstance(net, str) else net


def validation_door(net: str | NetSpec, key: str) -> Door:
    """Portón ``key`` de ``validation_doors`` de la red (del catálogo o con su superficie)."""
    spec = _spec(net)
    doors: Mapping[str, Any] = (spec.model_extra or {}).get("validation_doors") or {}
    if key not in doors:
        raise KeyError(t("portón de validación desconocido: {key!r}", key=key))
    params = dict(doors[key])
    if params.get("door_id"):
        from trawlkit.components import DoorItem, get_component

        item = get_component("door", str(params["door_id"]))
        assert isinstance(item, DoorItem)
        return item.to_door()
    door, _ = door_from_params(params, str(params.get("label") or key), f"validation_{key}")
    return door


def _at(speeds: np.ndarray, values: Any, v: float) -> float:
    return float(np.interp(v, speeds, np.asarray(values, dtype=float)))


def engine_point(
    net: str | NetSpec,
    *,
    depth_m: float,
    speed_kn: float,
    warp_m: float | None = None,
    door: str | None = None,
    sweeps_m: float | None = None,
    calibrated: bool = True,
    door_cl_scale: float | None = None,
) -> EnginePoint:
    """El caso de la red con la profundidad, el cable, el portón y las patentes de un lance.

    ``calibrated=False`` corre el motor sin las calibraciones de la Fase 20.5;
    ``door_cl_scale`` multiplica el CL de la polar del portón en lugar del factor calibrado
    (para ajustarlo, :func:`polyvalent_cl_fit`).
    """
    case = _case(net, depth_m, warp_m, door, sweeps_m, calibrated, door_cl_scale)
    return _point(case, depth_m, speed_kn, warp_m is not None)


def _case(
    net: str | NetSpec,
    depth_m: float,
    warp_m: float | None,
    door: str | None,
    sweeps_m: float | None,
    calibrated: bool,
    door_cl_scale: float | None,
) -> DesignCase:
    spec = _spec(net)
    overrides: dict[str, Any] = {"depth_m": float(depth_m), "calibrated": calibrated}
    if warp_m is not None:
        overrides["measured_warp_m"] = float(warp_m)
    if sweeps_m is not None:
        overrides["sweeps_m"] = float(sweeps_m)
    case = catalog_case(spec, **overrides).case
    if door is not None:
        case = dataclasses.replace(case, door=validation_door(spec, door))
    if door_cl_scale is not None:
        data = case.door.model_dump()
        for c in data["coefficients"]:
            if c.get("cl") is not None:
                c["cl"] = c["cl"] * door_cl_scale
        data["polar_published"] = True  # el factor de la prueba reemplaza al calibrado
        case = dataclasses.replace(case, door=Door.model_validate(data))
    return case


def _point(case: DesignCase, depth_m: float, speed_kn: float, from_source: bool) -> EnginePoint:
    r = run(case)
    v = np.asarray(case.speeds, dtype=float)
    assert case.door.area_m2 is not None
    return EnginePoint(
        depth_m=float(depth_m),
        speed_kn=float(speed_kn),
        warp_m=float(r.rigging.towing.warp_m),
        warp_from_source=from_source,
        warp_table_m=table_warp_m(float(depth_m)),
        dp_warp_factor=dp_warp_factor(case, r.rigging),
        door_cl_factor=door_cl_factor(case),
        door_id=case.door.id,
        door_area_m2=float(case.door.area_m2),
        sweeps_m=float(case.sweeps_m),
        door_spread_m=float(r.doors.spread_m),
        wing_spread_m=float(r.spread.horizontal_opening_m),
        dpa_fridman_m=_at(v, r.spread.fridman.dpa_std_m, speed_kn),
        vertical_opening_m=float(r.spread.vertical_opening_m),
        av_fridman_m=_at(v, r.spread.vertical.fridman.std.av_m, speed_kn),
        net_drag_kgf=_at(v, r.drag.rn.std, speed_kn),
        total_drag_kgf=_at(v, r.warps.total.std, speed_kn),
    )


def reference_point(
    net: str | NetSpec,
    ref: Mapping[str, Any],
    *,
    calibrated: bool = True,
    door_cl_scale: float | None = None,
) -> EnginePoint:
    """:func:`engine_point` con las condiciones de una entrada de ``measured`` o ``simulated``."""
    return engine_point(
        net,
        depth_m=float(ref["depth_m"]),
        speed_kn=float(ref["speed_kn"]),
        warp_m=None if ref.get("warp_m") is None else float(ref["warp_m"]),
        door=ref.get("door"),
        sweeps_m=None if ref.get("sweeps_m") is None else float(ref["sweeps_m"]),
        calibrated=calibrated,
        door_cl_scale=door_cl_scale,
    )


def references(net: str | NetSpec, kind: str = "measured") -> list[dict[str, Any]]:
    """Las mediciones (``kind="measured"``) o simulaciones (``"simulated"``) de la red."""
    spec = _spec(net)
    return [dict(x) for x in (spec.model_extra or {}).get(kind) or []]


# ---------------------------------------------------------------------------
# Calibración de la separación de portones (Fase 20.5)
# ---------------------------------------------------------------------------

#: Series con cable publicado y pendiente medida para el ajuste de Δn: (red, serie).
WARP_FIT_SERIES: tuple[tuple[str, str], ...] = (
    ("inidep_iat151_va355_construida", "iat151"),
    ("inidep_iat151_va355_construida", "ic012"),
    ("inidep_iat101_engel355", "ic016"),
)
#: Serie a la que se ajusta el CL efectivo del portón polivalente (52 lances de IAT 151/18).
POLYVALENT_FIT_SERIES: tuple[str, str] = ("inidep_iat151_va355_construida", "iat151")
#: Series de verificación del CL efectivo: los mismos polivalentes de 5,58 m² con la Engel.
POLYVALENT_CHECK_SERIES: tuple[tuple[str, str], ...] = (
    ("inidep_iat101_engel355", "it66"),
    ("inidep_iat101_engel355", "ic041"),
)


@dataclass(frozen=True)
class WarpFitRow:
    """Un lance del ajuste de Δn: cable, cable de la tabla, DP medida y DP del motor."""

    series: str
    warp_m: float
    warp_table_m: float
    measured_m: float
    engine_m: float

    @property
    def x(self) -> float:
        """``log(Ls / Ls_tabla)``."""
        return float(np.log(self.warp_m / self.warp_table_m))

    @property
    def y(self) -> float:
        """``log(DP medida / DP del motor)``."""
        return float(np.log(self.measured_m / self.engine_m))


@dataclass(frozen=True)
class CrossValidationFold:
    """Δn ajustado sin una serie y probado con ella (dispersión en log alrededor de su nivel)."""

    held_out: str
    delta_n: float
    scatter_before: float
    scatter_after: float


@dataclass(frozen=True)
class WarpExponentFit:
    """Ajuste de Δn en ``log(DP medida / DP motor) = a_serie + Δn · log(Ls / Ls_tabla)``."""

    delta_n: float
    se: float
    ci95: tuple[float, float]
    n: int
    dof: int
    offsets: dict[str, float]
    slopes: dict[str, float]
    folds: tuple[CrossValidationFold, ...]


def warp_fit_rows(calibrated: bool = False) -> list[WarpFitRow]:
    """Lances de :data:`WARP_FIT_SERIES` con la DP del motor (por defecto, sin calibrar)."""
    rows = []
    for net_id, series in WARP_FIT_SERIES:
        spec = _spec(net_id)
        for ref in references(spec):
            if ref["series"] != series or ref.get("door_spread_m") is None:
                continue
            p = reference_point(spec, ref, calibrated=calibrated)
            rows.append(
                WarpFitRow(
                    series, p.warp_m, p.warp_table_m, float(ref["door_spread_m"]), p.door_spread_m
                )
            )
    return rows


def _lsq(rows: list[WarpFitRow]) -> tuple[np.ndarray, np.ndarray, int, list[str]]:
    series = list(dict.fromkeys(r.series for r in rows))
    x = np.zeros((len(rows), len(series) + 1))
    for i, r in enumerate(rows):
        x[i, series.index(r.series)] = 1.0
        x[i, -1] = r.x
    y = np.array([r.y for r in rows])
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    resid = y - x @ beta
    dof = len(rows) - x.shape[1]
    cov = float(resid @ resid / dof) * np.linalg.inv(x.T @ x)
    return beta, np.sqrt(np.diag(cov)), dof, series


def _scatter(rows: list[WarpFitRow], delta_n: float) -> float:
    """Desvío estándar de ``y − Δn·x`` alrededor de su media (el nivel de la serie)."""
    e = np.array([r.y - delta_n * r.x for r in rows])
    return float(np.std(e - e.mean()))


def _t975(dof: int) -> float:
    """Cuantil 0,975 de la t de Student (Cornish-Fisher; error < 10⁻³ con ``dof`` ≥ 10)."""
    z = 1.959964
    return z + (z**3 + z) / (4 * dof) + (5 * z**5 + 16 * z**3 + 3 * z) / (96 * dof**2)


def warp_exponent_fit(rows: list[WarpFitRow] | None = None) -> WarpExponentFit:
    """Δn por mínimos cuadrados en log con un nivel por serie y validación cruzada (Fase 20.5).

    El nivel de cada serie absorbe lo que no depende del cable (el CL del portón de la serie);
    Δn sale de la variación con ``log(Ls / Ls_tabla)`` dentro de cada serie. Intervalo del 95 %
    con la t de Student. Validación cruzada: Δn ajustado con dos series y probado con la tercera
    (dispersión de sus lances alrededor de su nivel, sin y con la corrección).
    """
    rows = warp_fit_rows() if rows is None else rows
    beta, se, dof, series = _lsq(rows)
    half = _t975(dof) * float(se[-1])
    slopes = {}
    for s in series:
        sub = [r for r in rows if r.series == s]
        slopes[s] = float(np.polyfit([r.x for r in sub], [r.y for r in sub], 1)[0])
    folds = []
    for s in series:
        train = [r for r in rows if r.series != s]
        test = [r for r in rows if r.series == s]
        dn = float(_lsq(train)[0][-1])
        folds.append(CrossValidationFold(s, dn, _scatter(test, 0.0), _scatter(test, dn)))
    dn = float(beta[-1])
    return WarpExponentFit(
        delta_n=dn,
        se=float(se[-1]),
        ci95=(dn - half, dn + half),
        n=len(rows),
        dof=dof,
        offsets={s: float(beta[i]) for i, s in enumerate(series)},
        slopes=slopes,
        folds=tuple(folds),
    )


@dataclass(frozen=True)
class PolyvalentFit:
    """CL efectivo del portón polivalente: factor, DP media medida y del motor por serie."""

    factor: float
    target_m: float
    engine_m: float
    checks: dict[str, tuple[float, float]]  # serie → (DP media medida, DP media del motor)


def _series_mean_dp(net_id: str, series: str, scale: float) -> tuple[float, float]:
    spec = _spec(net_id)
    meas, eng = [], []
    for ref in references(spec):
        if ref["series"] != series or ref.get("door_spread_m") is None:
            continue
        meas.append(float(ref["door_spread_m"]))
        eng.append(reference_point(spec, ref, door_cl_scale=scale).door_spread_m)
    return float(np.mean(meas)), float(np.mean(eng))


def polyvalent_cl_fit(start: float | None = None, tol_m: float = 0.02) -> PolyvalentFit:
    """Factor de CL que iguala la DP media del motor y la medida en IAT 151/18 (Fase 20.5).

    Con el factor de cable ya aplicado (modo corregido calibrado) y el CL de la hoja del tipo
    multiplicado por el factor; método de la secante desde ``start`` (por defecto, el factor
    vigente). Verifica con :data:`POLYVALENT_CHECK_SERIES`.
    """
    from trawlkit.rigging import POLYVALENT_CL_EFFECTIVE_FACTOR

    net_id, series = POLYVALENT_FIT_SERIES
    x0 = POLYVALENT_CL_EFFECTIVE_FACTOR if start is None else start
    target, e0 = _series_mean_dp(net_id, series, x0)
    x1 = x0 * 1.02
    e1 = _series_mean_dp(net_id, series, x1)[1]
    for _ in range(8):
        if abs(e1 - target) <= tol_m or e1 == e0:
            break
        x0, e0, x1 = x1, e1, x1 + (target - e1) * (x1 - x0) / (e1 - e0)
        e1 = _series_mean_dp(net_id, series, x1)[1]
    checks = {s: _series_mean_dp(n, s, x1) for n, s in POLYVALENT_CHECK_SERIES}
    return PolyvalentFit(factor=x1, target_m=target, engine_m=e1, checks=checks)


def deviation(engine: float, reference: float | None) -> float | None:
    """Desvío relativo (motor − referencia) / referencia, o ``None`` sin referencia."""
    if reference is None or not reference:
        return None
    return engine / float(reference) - 1.0


__all__ = [
    "POLYVALENT_CHECK_SERIES",
    "POLYVALENT_FIT_SERIES",
    "QUANTITIES",
    "TOLERANCES",
    "WARP_FIT_SERIES",
    "CrossValidationFold",
    "EnginePoint",
    "PolyvalentFit",
    "WarpExponentFit",
    "WarpFitRow",
    "deviation",
    "engine_point",
    "polyvalent_cl_fit",
    "reference_point",
    "references",
    "validation_door",
    "warp_exponent_fit",
    "warp_fit_rows",
]
