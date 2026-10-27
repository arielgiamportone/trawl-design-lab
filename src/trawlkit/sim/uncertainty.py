"""Incertidumbre de la simulación: Monte Carlo con hipercubo latino y sensibilidad.

Varios datos del simulador no se conocen con precisión: los coeficientes de Morison del hilo, el
rozamiento con el fondo (el catálogo da un rango por sedimento), la polar del portón, la
densidad aparente y la presión de la captura. :func:`uncertainty` los muestrea dentro de sus
rangos y simula cada muestra:

* **Muestreo**: hipercubo latino (McKay, Beckman y Conover 1979): con ``n`` muestras, cada
  variable cae una vez en cada uno de los ``n`` estratos de su rango, así que pocas muestras
  cubren bien el espacio. Las variables son uniformes e independientes.
* **Arranque en caliente**: todas las muestras comparten la malla y parten de la forma nominal,
  por eso cada una cuesta una fracción de una simulación desde cero.
* **Salidas**: percentiles P10, P50 y P90 de cada magnitud, junto al valor nominal.
* **Sensibilidad**: correlación de rangos de Spearman entre cada entrada y cada salida (signo y
  peso de cada fuente de incertidumbre; con pocas muestras es orientativa).
"""

from __future__ import annotations

import dataclasses
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import numpy.typing as npt

from trawlkit.i18n import N_, t, tr
from trawlkit.sim.core import (
    DEFAULT_CN,
    DEFAULT_CT,
    CaseLike,
    SimResult,
    _resolve,
    simulate,
)
from trawlkit.sim.mesh import NetModel, build_model
from trawlkit.sim.scenario import Scenario, seabed

FloatArray = npt.NDArray[np.float64]


@dataclass(frozen=True)
class Uncertain:
    """Entrada incierta: rango uniforme ``[low, high]`` y valor nominal."""

    name: str
    label: str
    low: float
    high: float
    nominal: float
    unit: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclasses.asdict(self)


#: Entradas que :func:`uncertainty` sabe variar (``simulate`` o campo del escenario).
INPUTS = (
    "cn",
    "ct",
    "mu_gear",
    "mu_door",
    "door_cl_factor",
    "door_cd_factor",
    "catch_bulk_density",
    "catch_cp",
)


def default_inputs(
    scenario: Scenario, cn: float = DEFAULT_CN, ct: float = DEFAULT_CT
) -> list[Uncertain]:
    """Entradas inciertas por defecto para un escenario (rangos de la literatura y del catálogo).

    * C_N 1,0–1,6 y C_T 0,04–0,12 (rangos del hilo de red, ver :mod:`trawlkit.sim.solver`);
    * μ del tren y de los portones: el rango del tipo de fondo del catálogo, o ±30 % del valor;
    * polar del portón: ±10 % en C_L y C_D (A VERIFICAR: ensayos de túnel frente al mar);
    * con captura: densidad aparente 650–850 kg/m³ y C_p 0,8–1,2 (A VERIFICAR).
    """
    mu_g, mu_d = scenario.friction(0.5)
    out = [
        Uncertain("cn", t("C_N del hilo"), 1.0, 1.6, cn, "", "Takagi et al. 2004; Priour 2013"),
        Uncertain("ct", t("C_T del hilo"), 0.04, 0.12, ct, "", "Lee et al. 2005"),
    ]
    if scenario.seabed and scenario.mu_gear is None:
        sb = seabed(scenario.seabed)
        out.append(
            Uncertain(
                "mu_gear",
                t("μ tren–fondo"),
                sb.mu_gear.low,
                sb.mu_gear.high,
                mu_g,
                "",
                t("catálogo de fondos"),
            )
        )
    else:
        out.append(
            Uncertain("mu_gear", t("μ tren–fondo"), 0.7 * mu_g, 1.3 * mu_g, mu_g, "", "±30 %")
        )
    if scenario.coupled_doors:
        if scenario.seabed and scenario.mu_door is None:
            sb = seabed(scenario.seabed)
            out.append(
                Uncertain(
                    "mu_door",
                    t("μ portón–fondo"),
                    sb.mu_door.low,
                    sb.mu_door.high,
                    mu_d,
                    "",
                    t("catálogo de fondos"),
                )
            )
        else:
            out.append(
                Uncertain("mu_door", t("μ portón–fondo"), 0.7 * mu_d, 1.3 * mu_d, mu_d, "", "±30 %")
            )
        out += [
            Uncertain(
                "door_cl_factor", t("C_L del portón"), 0.9, 1.1, 1.0, "×", t("±10 % (A VERIFICAR)")
            ),
            Uncertain(
                "door_cd_factor", t("C_D del portón"), 0.9, 1.1, 1.0, "×", t("±10 % (A VERIFICAR)")
            ),
        ]
    if scenario.catch_kg > 0:
        out += [
            Uncertain(
                "catch_bulk_density",
                t("Densidad aparente de la captura"),
                650.0,
                850.0,
                scenario.catch_bulk_density,
                "kg/m³",
                t("A VERIFICAR"),
            ),
            Uncertain(
                "catch_cp",
                t("C_p de la captura"),
                0.8,
                1.2,
                scenario.catch_cp,
                "",
                t("O'Neill y O'Donoghue 1997 (A VERIFICAR)"),
            ),
        ]
    return out


#: Salidas que se resumen: nombre → (etiqueta, unidad, función sobre el resultado).
OUTPUTS: dict[str, tuple[str, str, Callable[[SimResult], float | None]]] = {
    "door_spread_m": (N_("Separación de portones"), "m", lambda r: r.door_spread_m),
    "ah_m": (N_("Abertura horizontal"), "m", lambda r: r.ah_m),
    "av_m": (N_("Abertura vertical"), "m", lambda r: r.av_m),
    "towing_pull_kgf": (
        N_("Tiro en el buque"),
        "kgf",
        lambda r: r.towing_pull_kgf or r.drag_kgf,
    ),
    "warp_tension_kgf": (N_("Tensión del cable (portón)"), "kgf", lambda r: r.warp_tension_kgf),
    "fuel_l_h": (N_("Combustible"), "L/h", lambda r: r.operation.get("fuel_l_h")),
    "contact_width_m": (
        N_("Ancho en contacto con el fondo"),
        "m",
        lambda r: r.operation.get("contact_width_m"),
    ),
}


def latin_hypercube(n: int, k: int, rng: np.random.Generator) -> FloatArray:
    """``n`` puntos en ``[0, 1]^k``: un punto por estrato y por variable, estratos permutados."""
    u = (np.arange(n)[:, None] + rng.random((n, k))) / n
    for j in range(k):
        u[:, j] = u[rng.permutation(n), j]
    return np.asarray(u, dtype=float)


def _ranks(a: FloatArray) -> FloatArray:
    """Rangos con empates promediados."""
    order = np.argsort(a, kind="mergesort")
    r = np.empty(a.size)
    r[order] = np.arange(a.size)
    for v in np.unique(a):
        tie = a == v
        if tie.sum() > 1:
            r[tie] = r[tie].mean()
    return r


def spearman(x: FloatArray, y: FloatArray) -> float:
    """Correlación de rangos de Spearman (0 si alguna serie es constante)."""
    rx, ry = _ranks(np.asarray(x, float)), _ranks(np.asarray(y, float))
    if rx.std() == 0 or ry.std() == 0:
        return 0.0
    return float(np.corrcoef(rx, ry)[0, 1])


@dataclass(frozen=True, eq=False)
class UncertaintyResult:
    """Resultado de :func:`uncertainty`."""

    speed_kn: float
    inputs: tuple[Uncertain, ...]
    samples: FloatArray  # (n, k) valores de las entradas
    outputs: dict[str, FloatArray]  # salida → (n,) (NaN si no aplica)
    nominal: SimResult
    converged: npt.NDArray[np.bool_]
    runtime_s: float
    extra_labels: dict[str, tuple[str, str]] = field(default_factory=dict)

    def label(self, key: str) -> tuple[str, str]:
        """(etiqueta, unidad) de una salida."""
        if key in OUTPUTS:
            return t(OUTPUTS[key][0]), OUTPUTS[key][1]
        return self.extra_labels.get(key, (key, ""))

    def nominal_value(self, key: str) -> float | None:
        """Valor nominal de una salida."""
        if key in OUTPUTS:
            v = OUTPUTS[key][2](self.nominal)
            return None if v is None else float(v)
        return None

    def percentiles(self, key: str) -> tuple[float, float, float] | None:
        """(P10, P50, P90) de una salida (None si no hay valores)."""
        y = self.outputs[key]
        y = y[np.isfinite(y)]
        if y.size == 0:
            return None
        p10, p50, p90 = np.percentile(y, [10, 50, 90])
        return float(p10), float(p50), float(p90)

    def sensitivity(self, key: str) -> dict[str, float]:
        """Correlación de rangos de cada entrada con la salida ``key``."""
        y = self.outputs[key]
        ok = np.isfinite(y)
        return {inp.name: spearman(self.samples[ok, j], y[ok]) for j, inp in enumerate(self.inputs)}

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        rows = []
        for key in self.outputs:
            p = self.percentiles(key)
            if p is None:
                continue
            label, unit = self.label(key)
            nom = self.nominal_value(key)
            rows.append(
                {
                    "key": key,
                    "label": label,
                    "unit": unit,
                    "nominal": nom,
                    "p10": p[0],
                    "p50": p[1],
                    "p90": p[2],
                    "values": [None if not np.isfinite(v) else float(v) for v in self.outputs[key]],
                    "sensitivity": self.sensitivity(key),
                }
            )
        return {
            "speed_kn": self.speed_kn,
            "n": int(self.samples.shape[0]),
            "inputs": [i.to_dict() for i in self.inputs],
            "samples": self.samples.tolist(),
            "outputs": rows,
            "converged": int(self.converged.sum()),
            "runtime_s": self.runtime_s,
            "nominal": self.nominal.to_dict(geometry=False),
        }


def _apply(
    inputs: Sequence[Uncertain], values: Sequence[float], scenario: Scenario, cn: float, ct: float
) -> tuple[Scenario, float, float]:
    changes: dict[str, Any] = {}
    for inp, v in zip(inputs, values, strict=True):
        if inp.name == "cn":
            cn = float(v)
        elif inp.name == "ct":
            ct = float(v)
        else:
            changes[inp.name] = float(v)
    return dataclasses.replace(scenario, **changes), cn, ct


def uncertainty(
    case: CaseLike,
    speed_kn: float = 3.0,
    *,
    scenario: Scenario | None = None,
    inputs: Sequence[Uncertain] | None = None,
    n: int = 12,
    seed: int = 0,
    resolution: int = 3,
    cn: float = DEFAULT_CN,
    ct: float = DEFAULT_CT,
    species: Sequence[str] = (),
    tol: float = 1e-2,
    qoi_tol: float = 3e-3,
    max_iter: int = 40_000,
) -> UncertaintyResult:
    """Monte Carlo (hipercubo latino) de la simulación a ``speed_kn`` (ver el módulo).

    ``inputs`` reemplaza las entradas por defecto (:func:`default_inputs`); ``species`` suma la
    L50 del copo de esas especies a las salidas.
    """
    if n < 2:
        raise ValueError(t("n debe ser ≥ 2"))
    t0 = time.perf_counter()
    sc = scenario or Scenario()
    inps = tuple(inputs) if inputs is not None else tuple(default_inputs(sc, cn, ct))
    for inp in inps:
        if inp.name not in INPUTS:
            raise ValueError(
                t(
                    "entrada desconocida: {name!r} (use {names})",
                    name=inp.name,
                    names=", ".join(INPUTS),
                )
            )
        if not inp.low <= inp.high:
            raise ValueError(t("rango inválido para {name}", name=inp.name))
    spec, rig, result = _resolve(case, None)
    base_case = result if result is not None else case
    model: NetModel | None = build_model(
        spec, rig, resolution=resolution, coupled_doors=sc.coupled_doors
    )
    if sc.warp_length_m is not None and sc.coupled_doors:
        model = None  # simulate reconstruye el modelo con el largo de cable del escenario
    nominal = simulate(
        base_case,
        speed_kn,
        resolution=resolution,
        cn=cn,
        ct=ct,
        scenario=sc,
        model=model,
        tol=tol,
        qoi_tol=qoi_tol,
        max_iter=max_iter,
    )
    rng = np.random.default_rng(seed)
    u = latin_hypercube(n, len(inps), rng)
    lows = np.array([i.low for i in inps])
    highs = np.array([i.high for i in inps])
    samples = lows + u * (highs - lows)
    outs: dict[str, list[float]] = {k: [] for k in OUTPUTS}
    extra: dict[str, tuple[str, str]] = {}
    sel_keys = [f"l50_{s}" for s in species]
    for k in sel_keys:
        outs[k] = []
    conv = []
    from trawlkit.selectivity import selectivity
    from trawlkit.selectivity import species as species_of

    for s in species:
        sp = species_of(s)
        extra[f"l50_{s}"] = (f"L50 {(tr(sp.name) or sp.name).lower()}", sp.unit)
    for row in samples:
        sc_i, cn_i, ct_i = _apply(inps, row, sc, cn, ct)
        r = simulate(
            base_case,
            speed_kn,
            resolution=resolution,
            cn=cn_i,
            ct=ct_i,
            scenario=sc_i,
            model=model,
            x_init=nominal.nodes,
            coarse_resolution=None,
            tol=tol,
            qoi_tol=qoi_tol,
            max_iter=max_iter,
        )
        conv.append(r.converged)
        for key, (_, _, fn) in OUTPUTS.items():
            v = fn(r)
            outs[key].append(float("nan") if v is None else float(v))
        if species:
            for c in selectivity(r, list(species)):
                outs[f"l50_{c.species.id}"].append(c.l50)
    if not nominal.towing_pull_kgf and not sc.coupled_doors:
        outs.pop("warp_tension_kgf", None)
    return UncertaintyResult(
        speed_kn=float(speed_kn),
        inputs=inps,
        samples=samples,
        outputs={k: np.asarray(v, dtype=float) for k, v in outs.items()},
        nominal=nominal,
        converged=np.asarray(conv, dtype=bool),
        runtime_s=time.perf_counter() - t0,
        extra_labels=extra,
    )
