"""Validación de la simulación de forma contra DynamiT (Ifremer) y contra el motor empírico.

La única referencia física del proyecto es la simulación DynamiT de la red FAO A-3 **estándar**
(superficie sólida 38,76 m², igual a la ``Ss`` corregida del motor), transcrita en
``docs/32_validacion_dynamit.md`` desde ``legacy/dynamit_resultados_fao_a3.png``: abertura
horizontal AH, vertical AV, distancia entre portones DP y resistencia RA (kgf) de 1 a 5 kn.

Este módulo corre :func:`trawlkit.sim.sweep` sobre el caso estándar y arma las comparaciones
(errores absolutos y relativos, exponente de velocidad de la resistencia), para que un capítulo
del libro pueda llamarlo directamente::

    from trawlkit.sim.validation import validate, markdown_table
    v = validate()                  # DP del motor, C_N = 1,4, C_T = 0,08
    print(markdown_table(v))

Qué se compara con qué (como en ``docs/32``): AH de DynamiT con la AH simulada (distancia entre
puntas de ala de la lima) y con la DPA de Fridman del motor; AV con la AV simulada (lima sobre
burlón en el centro) y la AV de Fridman; RA con el arrastre simulado de la red (agua + fondo,
igual al tiro de las bridas) y la RN de diseño del motor (Aberdeen). DP no se simula (es un dato
de entrada): se usa la del motor (``doors.spread_m``) o la de DynamiT, según ``door_spread``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
import numpy.typing as npt

from trawlkit.compat import Compat
from trawlkit.io import load_doors, load_net, load_vessels
from trawlkit.model import DesignCase, DesignResult, run
from trawlkit.sim.core import DEFAULT_CN, DEFAULT_CT, DEFAULT_RESOLUTION, SimResult, sweep

FloatArray = npt.NDArray[np.float64]

#: Transcripción de ``legacy/dynamit_resultados_fao_a3.png`` (DynamiT, Ifremer; red FAO A-3
#: estándar), idéntica a la de ``docs/32_validacion_dynamit.md``. Unidades: m y kgf.
DYNAMIT: dict[str, tuple[float, ...]] = {
    "v_kn": (1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0),
    "AH_m": (8.9, 11.2, 12.5, 12.9, 13.3, 13.2, 13.3, 13.5, 13.6),
    "AV_m": (6.0, 3.5, 2.4, 1.8, 1.4, 1.2, 1.0, 1.3, 1.6),
    "DP_m": (28.5, 40.9, 46.6, 49.3, 51.4, 51.6, 52.3, 53.2, 53.4),
    "RA_kg": (330.6, 476.0, 704.3, 967.3, 1331.3, 1751.9, 2208.7, 2784.5, 3371.8),
}

#: Rango de pesca en el que se resumen los errores (como en ``docs/32``).
FISHING_BAND_KN = (2.0, 4.0)

#: Rangos de la literatura para los coeficientes de Morison del hilo de red (calibración).
CN_RANGE = (1.0, 1.6)
CT_RANGE = (0.01, 0.12)

#: Mejor par (C_N, C_T) de :func:`calibrate` contra la RA de DynamiT (2–4 kn, DP del motor):
#: los extremos superiores de ambos rangos. Baja el error medio de RA de 50 % a 37 % (2–4 kn),
#: pero sube el de AV de 12 % a 15 %: los coeficientes del hilo no alcanzan para cerrar la
#: brecha de resistencia (ver el informe de validación y ``knot_factor``).
CALIBRATED_CN = 1.6
CALIBRATED_CT = 0.12


def standard_case(
    speeds_kn: Sequence[float] | FloatArray = DYNAMIT["v_kn"], compat: Compat = Compat.CORRECTED
) -> DesignCase:
    """Caso FAO A-3 estándar (buque de 150 HP, portón FAO A3), como ``tests/test_case_fao_a3``."""
    vessels = {v.id: v for v in load_vessels().vessels}
    design = vessels["fao_a3_150hp"]
    return DesignCase(
        net=load_net("fao_a3_standard"),
        vessel=design,
        door=load_doors().doors[0],
        net_modified=load_net("fao_a3_modified"),
        class_vessels=tuple(v for v in vessels.values() if v.id != design.id),
        speeds_kn=tuple(float(v) for v in speeds_kn),
        compat=compat,
    )


def engine_reference(r: DesignResult) -> dict[str, dict[str, FloatArray]]:
    """Magnitudes empíricas del motor comparables con DynamiT (ver ``docs/32``)."""
    n = len(r.case.speeds_kn)
    return {
        "AH": {
            "DPA Fridman": np.asarray(r.spread.fridman.dpa_std_m, dtype=float),
            "AH geométrica": np.full(n, float(r.spread.horizontal_opening_m)),
        },
        "AV": {"AV Fridman": np.asarray(r.spread.vertical.fridman.std.av_m, dtype=float)},
        "DP": {
            "Ds desde DPA Fridman": np.asarray(r.spread.table.door_spread_from_dpa_m, dtype=float),
            "Ds al metro de cable": np.full(n, float(r.doors.spread_m)),
        },
        "RA": {"Rn diseño (Aberdeen)": np.asarray(r.drag.rn.std, dtype=float)},
    }


@dataclass(frozen=True)
class Errors:
    """Errores de una serie contra DynamiT."""

    abs: FloatArray  # x − DynamiT
    pct: FloatArray  # (x − DynamiT) / DynamiT · 100
    mean_abs_pct: float  # 1–5 kn
    mean_abs_pct_band: float  # 2–4 kn
    bias_pct_band: float  # sesgo (con signo) 2–4 kn


def errors(
    x: Sequence[float] | FloatArray, ref: Sequence[float] | FloatArray, v: FloatArray
) -> Errors:
    """Errores absolutos y relativos de ``x`` respecto de ``ref``."""
    xa = np.asarray(x, dtype=float)
    ra = np.asarray(ref, dtype=float)
    e = xa - ra
    p = e / ra * 100.0
    band = (v >= FISHING_BAND_KN[0]) & (v <= FISHING_BAND_KN[1])
    return Errors(
        abs=e,
        pct=p,
        mean_abs_pct=float(np.abs(p).mean()),
        mean_abs_pct_band=float(np.abs(p[band]).mean()),
        bias_pct_band=float(p[band].mean()),
    )


def speed_exponent(v_kn: Sequence[float] | FloatArray, ra: Sequence[float] | FloatArray) -> float:
    """Exponente ``n`` del ajuste ``RA ∝ vⁿ`` (mínimos cuadrados en log-log)."""
    return float(np.polyfit(np.log(np.asarray(v_kn, float)), np.log(np.asarray(ra, float)), 1)[0])


def constant_plus_power(
    v_kn: Sequence[float] | FloatArray, ra: Sequence[float] | FloatArray
) -> tuple[float, float, float]:
    """Ajuste ``RA = a + b·vⁿ`` (``a`` término independiente de la velocidad, p. ej. fondo)."""
    v = np.asarray(v_kn, float)
    y = np.asarray(ra, float)
    best = (np.inf, 0.0, 0.0, 2.0)
    for n in np.linspace(1.0, 2.5, 151):
        design = np.stack([np.ones_like(v), v**n], axis=1)
        coef, *_ = np.linalg.lstsq(design, y, rcond=None)
        err = float(np.sum((design @ coef - y) ** 2))
        if err < best[0]:
            best = (err, float(coef[0]), float(coef[1]), float(n))
    return best[1], best[2], best[3]


@dataclass(frozen=True)
class Validation:
    """Simulación a las velocidades de DynamiT y su comparación."""

    v_kn: FloatArray
    sim: dict[str, FloatArray]  # AH, AV, DP, RA (+ AH_lower, mouth_area, ...)
    dynamit: dict[str, FloatArray]
    engine: dict[str, dict[str, FloatArray]]
    errors: dict[str, Errors]  # sim vs DynamiT
    engine_errors: dict[str, dict[str, Errors]]
    settings: dict[str, Any]
    results: list[SimResult] = field(repr=False, default_factory=list)

    def summary(self) -> dict[str, Any]:
        """Resumen serializable (sin geometría)."""
        out: dict[str, Any] = {"settings": dict(self.settings), "v_kn": self.v_kn.tolist()}
        for k, arr in self.sim.items():
            out[f"sim_{k}"] = arr.tolist()
        for k, e in self.errors.items():
            out[f"err_{k}"] = {
                "mean_abs_pct": e.mean_abs_pct,
                "mean_abs_pct_band": e.mean_abs_pct_band,
                "bias_pct_band": e.bias_pct_band,
            }
        out["ra_exponent_sim"] = speed_exponent(self.v_kn, self.sim["RA"])
        out["ra_exponent_dynamit"] = speed_exponent(self.v_kn, self.dynamit["RA"])
        return out


def validate(
    *,
    resolution: int = DEFAULT_RESOLUTION,
    cn: float = DEFAULT_CN,
    ct: float = DEFAULT_CT,
    door_spread: Literal["engine", "dynamit"] = "engine",
    knot_factor: float = 0.0,
    speeds_kn: Sequence[float] | None = None,
    result: DesignResult | None = None,
) -> Validation:
    """Corre la simulación del caso estándar y la compara con DynamiT y con el motor.

    ``door_spread="engine"`` usa la separación de portones del motor (``doors.spread_m``, fija);
    ``"dynamit"`` impone la DP de DynamiT a cada velocidad, para aislar la red del modelo de
    portones. ``speeds_kn`` permite un subconjunto de las velocidades de DynamiT.
    """
    all_v = np.asarray(DYNAMIT["v_kn"], float)
    sel = (
        np.ones(all_v.size, dtype=bool)
        if speeds_kn is None
        else np.isin(all_v, np.asarray(speeds_kn, float))
    )
    v = all_v[sel]
    r = result if result is not None else run(standard_case(all_v))
    dyn = {k[:2]: np.asarray(DYNAMIT[k], float)[sel] for k in ("AH_m", "AV_m", "DP_m", "RA_kg")}
    dp: list[float] | None = dyn["DP"].tolist() if door_spread == "dynamit" else None
    res = sweep(
        r,
        v.tolist(),
        resolution=resolution,
        cn=cn,
        ct=ct,
        door_spread_m=dp,
        knot_factor=knot_factor,
    )
    sim = {
        "AH": np.array([s.ah_m for s in res]),
        "AV": np.array([s.av_m for s in res]),
        "DP": np.array([s.door_spread_m for s in res]),
        "RA": np.array([s.drag_kgf for s in res]),
        "AH_lower": np.array([s.ah_lower_m for s in res]),
        "mouth_area": np.array([s.mouth_area_m2 for s in res]),
        "friction": np.array([s.friction_kgf for s in res]),
        "residual": np.array([s.residual for s in res]),
        "runtime": np.array([s.runtime_s for s in res]),
    }
    eng_all = engine_reference(r)
    speeds_engine = np.asarray(r.case.speeds_kn, float)
    eng = {
        var: {name: np.interp(v, speeds_engine, arr) for name, arr in d.items()}
        for var, d in eng_all.items()
    }
    errs = {var: errors(sim[var], dyn[var], v) for var in ("AH", "AV", "RA")}
    if door_spread == "engine":
        errs["DP"] = errors(sim["DP"], dyn["DP"], v)
    eng_errs = {
        var: {name: errors(arr, dyn[var], v) for name, arr in d.items()} for var, d in eng.items()
    }
    return Validation(
        v_kn=v,
        sim=sim,
        dynamit=dyn,
        engine=eng,
        errors=errs,
        engine_errors=eng_errs,
        settings={
            "resolution": resolution,
            "cn": cn,
            "ct": ct,
            "door_spread": door_spread,
            "knot_factor": knot_factor,
        },
        results=res,
    )


def calibrate(
    *,
    cn_values: Sequence[float] = (1.0, 1.3, 1.6),
    ct_values: Sequence[float] = (0.01, 0.06, 0.12),
    speeds_kn: Sequence[float] = (2.0, 3.0, 4.0),
    resolution: int = 6,
    door_spread: Literal["engine", "dynamit"] = "dynamit",
    result: DesignResult | None = None,
) -> list[dict[str, float]]:
    """Barrido de ``C_N`` y ``C_T`` dentro de los rangos de la literatura contra la RA de DynamiT.

    Devuelve, por combinación, el error medio absoluto y el sesgo de RA en ``speeds_kn`` (y los
    de AH y AV, para ver qué se pierde), ordenado de mejor a peor RA.
    """
    r = result if result is not None else run(standard_case())
    rows: list[dict[str, float]] = []
    for cn in cn_values:
        for ct in ct_values:
            val = validate(
                resolution=resolution,
                cn=cn,
                ct=ct,
                door_spread=door_spread,
                speeds_kn=speeds_kn,
                result=r,
            )
            rows.append(
                {
                    "cn": float(cn),
                    "ct": float(ct),
                    "ra_mean_abs_pct": val.errors["RA"].mean_abs_pct,
                    "ra_bias_pct": float(val.errors["RA"].pct.mean()),
                    "ah_mean_abs_pct": val.errors["AH"].mean_abs_pct,
                    "av_mean_abs_pct": val.errors["AV"].mean_abs_pct,
                }
            )
    return sorted(rows, key=lambda d: d["ra_mean_abs_pct"])


def _fmt(x: float, nd: int) -> str:
    return f"{x:.{nd}f}".replace(".", ",")


def markdown_table(v: Validation) -> str:
    """Tabla por velocidad (sim, DynamiT, motor y error %) en Markdown."""
    head = "| Variable | " + " | ".join(_fmt(x, 1) for x in v.v_kn) + " |"
    sep = "|---|" + "---|" * v.v_kn.size
    lines = [head, sep]
    spec = (("AH", "m", 1), ("AV", "m", 2), ("DP", "m", 1), ("RA", "kgf", 0))
    for var, unit, nd in spec:
        lines.append(
            f"| {var} sim [{unit}] | " + " | ".join(_fmt(x, nd) for x in v.sim[var]) + " |"
        )
        lines.append(
            f"| {var} DynamiT [{unit}] | " + " | ".join(_fmt(x, nd) for x in v.dynamit[var]) + " |"
        )
        if var in v.errors:
            lines.append(
                f"| Δ {var} sim [%] | " + " | ".join(_fmt(x, 0) for x in v.errors[var].pct) + " |"
            )
        for name, arr in v.engine.get(var, {}).items():
            lines.append(
                f"| {var} motor: {name} [{unit}] | " + " | ".join(_fmt(x, nd) for x in arr) + " |"
            )
    return "\n".join(lines)
