"""Evaluación de un diseño (escala de red ``s``, velocidad ``v``): objetivos y restricciones.

Una corrida del motor por escala da todas las curvas en función de la velocidad sobre una malla
fina (0,05 kn); evaluar a una velocidad cualquiera es interpolar linealmente en esa malla. Así
:func:`trawlkit.optimize.grid_search` y el optimizador comparten una sola corrida por ``s``.

Magnitudes por velocidad (red estándar, modo corregido por defecto):

* **AH** = DPA de Fridman a la velocidad ``v`` (``result.spread.fridman.dpa_std_m``, Mec!P164)
  con tope en la DPA geométrica (Mec!L211 sin el redondeo a metro entero). Es la única abertura
  horizontal del motor que depende de ``v``: la DPA geométrica y la AH promedio de Dim!F61 son
  constantes y no ven que una red lenta no termina de abrirse; el tope evita que una red chica
  con el mismo portón "abra" más de lo que permite el aparejo.
* **AV** = AV de Baranov–Fridman a la velocidad ``v`` (``spread.vertical.fridman.std.av_m``) con
  tope en el 6,5 % de la circunferencia (Prado y Dremière, "mucha AV").
* **R_T** = resistencia total (red + boyas + cables + dos portones, ``warps.total.std``).
* **F_T** = tiro de Fridman del propulsor elegido (``power.ft_kgf``).
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

from trawlkit import rigging
from trawlkit.compat import Compat
from trawlkit.io import Door, PropellerType, load_catalogue, load_doors
from trawlkit.model import DesignCase, DesignResult, run
from trawlkit.optimize.scaling import scale_count, scale_net
from trawlkit.units import KNOT_TO_MS

FloatArray = NDArray[np.float64]

#: Paso de la malla fina de velocidades sobre la que se corre el motor [kn].
GRID_STEP_KN = 0.05

#: Objetivos: nombre corto → (atributo de :class:`Evaluation`, sentido: +1 maximizar, -1 minimizar).
OBJECTIVES: dict[str, tuple[str, int]] = {
    "area_rate": ("area_rate_m2_h", +1),
    "volume_rate": ("volume_rate_m3_h", +1),
    "energy": ("energy_kgf_m_per_m2", -1),
}
#: Alias de ``optimise(objective=...)``.
OBJECTIVE_ALIASES = {"area": "area_rate", "volume": "volume_rate", "energy": "energy"}


@dataclass(frozen=True)
class Limits:
    """Parámetros de las restricciones.

    ``margin``: reserva de tiro, F_T ≥ (1 + margin)·R_T. ``open_ratio``: la DPA de Fridman debe
    llegar a esa fracción de la DPA geométrica (red abierta). ``v_min_kn``/``v_max_kn``: rango
    operativo. ``door_tolerance``: holgura sobre la superficie del portón. ``warp_safety_factor``:
    rotura del cable ≥ factor·R_T (``None`` → el del caso, Rem!D271 = 4).
    """

    margin: float = 0.1
    open_ratio: float = 0.85
    v_min_kn: float = 1.5
    v_max_kn: float = 4.0
    door_tolerance: float = 0.0
    warp_safety_factor: float | None = None

    def __post_init__(self) -> None:
        """Valida los rangos."""
        if not (math.isfinite(self.margin) and self.margin >= 0):
            raise ValueError("margin debe ser ≥ 0")
        if not 0 < self.open_ratio <= 1.5:
            raise ValueError("open_ratio debe estar en (0, 1.5]")
        if not 0 < self.v_min_kn < self.v_max_kn:
            raise ValueError("se requiere 0 < v_min_kn < v_max_kn")
        if self.door_tolerance < 0:
            raise ValueError("door_tolerance debe ser ≥ 0")
        if self.warp_safety_factor is not None and self.warp_safety_factor <= 0:
            raise ValueError("warp_safety_factor debe ser positivo")

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class Constraint:
    """Una restricción evaluada: ``lower ≤ value ≤ upper`` (``None`` = sin límite)."""

    name: str
    value: float
    lower: float | None
    upper: float | None
    ok: bool
    violation: float
    """Violación relativa al límite (0 si se cumple)."""
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return dataclasses.asdict(self)


def _constraint(
    name: str, value: float, lower: float | None, upper: float | None, description: str
) -> Constraint:
    viol = 0.0
    if lower is not None and value < lower:
        viol = max(viol, (lower - value) / max(abs(lower), 1e-9))
    if upper is not None and value > upper:
        viol = max(viol, (value - upper) / max(abs(upper), 1e-9))
    return Constraint(name, float(value), lower, upper, viol == 0.0, float(viol), description)


@dataclass(frozen=True)
class Evaluation:
    """Diseño ``(s, v)`` evaluado: aberturas, tasas, fuerzas, restricciones y factibilidad."""

    s: float
    v_kn: float
    net_id: str
    vessel_id: str
    door_id: str
    propeller: str
    ah_m: float
    """Abertura horizontal = min(DPA de Fridman a ``v``, DPA geométrica) [m]."""
    dpa_fridman_m: float
    """DPA de Fridman a ``v`` sin tope geométrico [m]."""
    av_m: float
    """Abertura vertical = min(AV de Baranov–Fridman a ``v``, 6,5 % de la circunferencia) [m]."""
    av_fridman_m: float
    """AV de Baranov–Fridman a ``v`` sin tope [m]."""
    area_rate_m2_h: float
    """Área barrida por hora AH·v·3600 [m²/h]."""
    volume_rate_m3_h: float
    """Volumen filtrado por hora AH·AV·v·3600 [m³/h]."""
    demand_kgf: float
    """Resistencia total R_T(v) [kgf]."""
    available_kgf: float
    """Tiro disponible F_T(v) [kgf]."""
    thrust_margin: float
    """F_T/R_T − 1."""
    energy_kgf_m_per_m2: float
    """Trabajo de remolque por m² barrido, R_T/AH [kgf·m/m²]."""
    net_drag_kgf: float
    dpa_geometric_m: float
    """DPA geométrica del libro (Mec!L211, redondeada a metro entero) [m]."""
    headrope_m: float
    footrope_m: float
    door_area_m2: float
    door_required_m2: float
    warp_id: str | None
    """Cable más delgado del catálogo que cumple diámetro y rotura (``None`` si ninguno)."""
    constraints: tuple[Constraint, ...]
    feasible: bool
    penalty: float
    """Suma de violaciones relativas (0 si es factible)."""

    def objective(self, name: str) -> float:
        """Valor de un objetivo (``area_rate``, ``volume_rate``, ``energy`` o sus alias)."""
        attr, _ = OBJECTIVES[OBJECTIVE_ALIASES.get(name, name)]
        return float(getattr(self, attr))

    def constraint(self, name: str) -> Constraint:
        """Restricción por nombre."""
        return next(c for c in self.constraints if c.name == name)

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        out = {f.name: getattr(self, f.name) for f in dataclasses.fields(self)}
        out["constraints"] = [c.to_dict() for c in self.constraints]
        return out


@dataclass(frozen=True)
class Curves:
    """Curvas de una red escalada sobre la malla fina de velocidades (una corrida del motor)."""

    s: float
    net_id: str
    speeds_kn: FloatArray
    ah_m: FloatArray
    av_m: FloatArray
    demand_kgf: FloatArray
    available_kgf: FloatArray
    net_drag_kgf: FloatArray
    dpa_geometric_m: float
    dpa_geometric_exact_m: float
    av_max_m: float
    headrope_m: float
    footrope_m: float
    door_required_m2: float
    warp_min_diameter_mm: float
    result: DesignResult = field(repr=False)


def _dpa_geometric_m(result: DesignResult) -> float:
    """DPA geométrica de Mec!L211 sin el ROUNDDOWN: burlón·Ds/(PG + APG + LP + Vs + burlón).

    Es el tope físico de la AH (continuo en ``s``); la restricción de red abierta usa, como el
    libro, la DPA geométrica redondeada a metro entero (``spread.dpa_geometric_m``).
    """
    rig = result.rigging
    footrope = result.dimensions.std.footrope_m
    total = (
        rig.crowfoot.length_m
        + rig.crowfoot.extension_m
        + result.case.sweeps_m
        + rig.bridles.upper_m
        + footrope
    )
    return float(footrope * result.doors.spread_m / total)


def _resolve_door(door: str | Door | None, case: DesignCase) -> Door:
    if door is None:
        return case.door
    if isinstance(door, Door):
        return door
    doors = {d.id: d for d in load_doors().doors}
    if door not in doors:
        raise ValueError(f"portón desconocido: {door!r}")
    return doors[door]


def distributable_float_count(count: int, wing_share: float, front_fifth_share: float) -> int:
    """Menor número de boyas ≥ ``count`` que la distribución selectiva del libro admite.

    Flot!G107:H111 divide por (boyas del primer quinto − 1) y por (boyas restantes por ala): con
    pocas boyas (p. ej. 7) alguno de los dos es 0. Desde que ``distribute_floats`` informa esos
    espaciados como NaN, toda cantidad es admisible y esta función devuelve ``count``; se conserva
    por compatibilidad.
    """
    n = max(int(count), 1)
    for cand in range(n, n + 50):
        try:
            rigging.distribute_floats(cand, 200.0, 20.0, 8.0, 4.0, wing_share, front_fifth_share)
        except (ZeroDivisionError, ValueError):
            continue
        return cand
    return n


def speed_grid(v_lo: float, v_hi: float, extra: tuple[float, ...] = ()) -> tuple[float, ...]:
    """Malla fina de velocidades [kn]: de ``min(1, v_lo)`` a ``max(5, v_hi)`` cada 0,05 kn."""
    lo = min(1.0, math.floor(v_lo / GRID_STEP_KN) * GRID_STEP_KN)
    hi = max(5.0, math.ceil(v_hi / GRID_STEP_KN) * GRID_STEP_KN)
    n = int(round((hi - lo) / GRID_STEP_KN))
    pts = {round(lo + i * GRID_STEP_KN, 6) for i in range(n + 1)}
    pts.update(round(float(x), 6) for x in extra)
    return tuple(sorted(x for x in pts if x > 0))


class Evaluator:
    """Evalúa diseños ``(s, v)`` de un caso base con una corrida del motor (cacheada) por escala.

    ``door`` (id del catálogo o :class:`Door`), ``door_angle`` (ángulo de ataque, debe estar en la
    polar) y ``propeller`` reemplazan los del caso; ``compat`` es :attr:`Compat.CORRECTED` por
    defecto. Si ``s_step`` se indica, la escala se redondea a ese paso antes de evaluar (lo usa el
    optimizador para reutilizar corridas).
    """

    def __init__(
        self,
        base_case: DesignCase,
        *,
        door: str | Door | None = None,
        door_angle: float | None = None,
        propeller: PropellerType | str | None = None,
        compat: Compat | str = Compat.CORRECTED,
        limits: Limits | None = None,
        s_step: float | None = None,
    ) -> None:
        """Prepara el caso (portón, ángulo, hélice, modo) y la malla de velocidades."""
        self.limits = limits or Limits()
        self.s_step = s_step
        changes: dict[str, Any] = {
            "door": _resolve_door(door, base_case),
            "compat": Compat(compat),
        }
        if door_angle is not None:
            changes["door_attack_angle_deg"] = float(door_angle)
        if propeller is not None:
            changes["ft_propeller"] = PropellerType(propeller)
        case = dataclasses.replace(base_case, **changes)
        self.book_speeds = case.speeds_kn
        grid = speed_grid(
            self.limits.v_min_kn,
            self.limits.v_max_kn,
            (*case.speeds_kn, case.ballast_min_speed_kn, case.ballast_max_speed_kn),
        )
        # El cable se verifica aquí a cada v; el motor lo selecciona a la menor velocidad de la
        # malla para que una red grande no aborte la corrida (select_warp sin candidatos).
        self.case = dataclasses.replace(case, speeds_kn=grid, warp_design_speed_kn=grid[0])
        self.speeds = np.asarray(grid, dtype=float)
        warps = load_catalogue("warps").items
        self._warps = sorted(
            (
                (str(w["id"]), float(w["diameter_mm"]), float(w["breaking_load_t"]) * 1000.0)
                for w in warps
            ),
            key=lambda t: (t[1], t[2]),
        )
        self._cache: dict[tuple[int, ...], Curves] = {}
        self.runs = 0

    # -- corridas -----------------------------------------------------------------------------

    def quantise(self, s: float) -> float:
        """Escala redondeada a ``s_step`` (si está fijado)."""
        if self.s_step:
            return round(round(s / self.s_step) * self.s_step, 10)
        return float(s)

    def curves(self, s: float) -> Curves:
        """Corre el motor para la red escalada por ``s`` (cacheado por número de mallas)."""
        s = self.quantise(s)
        net = scale_net(self.case.net, s)
        mod = None if self.case.net_modified is None else scale_net(self.case.net_modified, s)
        count = self.case.float_count
        if count is not None:
            count = scale_count(count, s)
        elif net.floats is not None:
            count = net.floats.count
        if count is not None:
            count = distributable_float_count(
                count, self.case.float_wing_share, self.case.float_front_fifth_share
            )
        key = tuple(
            n
            for spec in (net, mod)
            if spec is not None
            for p in spec.panels
            for n in (p.meshes_top, p.meshes_bottom, p.meshes_depth)
        ) + (-1 if count is None else count,)
        hit = self._cache.get(key)
        if hit is not None:
            return dataclasses.replace(hit, s=s, net_id=net.id)
        case = dataclasses.replace(self.case, net=net, net_modified=mod, float_count=count)
        try:
            result = run(case)
        except (ZeroDivisionError, IndexError, FloatingPointError) as exc:
            raise ValueError(f"el motor no puede calcular la red escalada s = {s}: {exc}") from exc
        self.runs += 1
        req = result.doors.required_area_m2
        lo, hi = case.required_area_speed_range_kn
        idx = [int(np.argmin(np.abs(self.speeds - v))) for v in self.book_speeds if lo <= v <= hi]
        # Port!F215: promedio de la superficie requerida en las velocidades del libro (2–4 kn).
        door_req = float(np.mean(req[idx])) / 2.0 if idx else result.doors.required_area.per_door_m2
        dims = result.dimensions.std
        curves = Curves(
            s=s,
            net_id=net.id,
            speeds_kn=self.speeds,
            ah_m=np.asarray(result.spread.fridman.dpa_std_m, dtype=float),
            av_m=np.asarray(result.spread.vertical.fridman.std.av_m, dtype=float),
            demand_kgf=np.asarray(result.warps.total.std, dtype=float),
            available_kgf=np.asarray(result.power.ft_kgf, dtype=float),
            net_drag_kgf=np.asarray(result.drag.rn.std, dtype=float),
            dpa_geometric_m=float(result.spread.dpa_geometric_m),
            dpa_geometric_exact_m=_dpa_geometric_m(result),
            av_max_m=float(result.spread.vertical.prado_m["high_opening"]),
            headrope_m=float(dims.headrope_m),
            footrope_m=float(dims.footrope_m),
            door_required_m2=door_req,
            warp_min_diameter_mm=float(result.warps.diameter_mm),
            result=result,
        )
        self._cache[key] = curves
        return curves

    # -- evaluación ---------------------------------------------------------------------------

    def _warp(self, min_diameter_mm: float, min_breaking_kgf: float) -> tuple[str | None, float]:
        """Cable más delgado que cumple Ø y rotura; mayor rotura disponible con Ø suficiente."""
        ok = [w for w in self._warps if w[1] >= min_diameter_mm - 1e-9]
        best = max((w[2] for w in ok), default=0.0)
        chosen = next((w[0] for w in ok if w[2] >= min_breaking_kgf), None)
        return chosen, best

    def at(self, s: float, v_kn: float) -> Evaluation:
        """Evalúa el diseño ``(s, v)``."""
        c = self.curves(s)
        return self.from_curves(c, v_kn)

    def from_curves(self, c: Curves, v_kn: float) -> Evaluation:
        """Evalúa a la velocidad ``v_kn`` con las curvas ya calculadas de una escala."""
        v = float(v_kn)
        if not self.speeds[0] <= v <= self.speeds[-1]:
            raise ValueError(
                f"v = {v} kn fuera de la malla de velocidades "
                f"[{self.speeds[0]:g}, {self.speeds[-1]:g}] kn"
            )
        lim = self.limits
        case = self.case

        def at(arr: FloatArray) -> float:
            return float(np.interp(v, c.speeds_kn, arr))

        dpa_f, av, rt, ft = at(c.ah_m), at(c.av_m), at(c.demand_kgf), at(c.available_kgf)
        # La DPA de Fridman sale del equilibrio de fuerzas y no satura: con una red chica y el
        # mismo portón supera la apertura que permite la geometría del aparejo (DPA geométrica,
        # Mec!L211). La abertura efectiva es la menor de las dos.
        ah = min(dpa_f, c.dpa_geometric_exact_m)
        # Idem AV de Fridman: con R_N chica (red lenta) el ángulo de la lima tiende a 90°. Tope en
        # la AV máxima de Prado y Dremière (6,5 % de la circunferencia, "mucha AV", Mec!F246).
        av_f = av
        av = min(av_f, c.av_max_m)
        v_ms = v * KNOT_TO_MS
        safety = (
            case.warp_safety_factor if lim.warp_safety_factor is None else lim.warp_safety_factor
        )
        warp_id, best_bl = self._warp(c.warp_min_diameter_mm, safety * rt)
        assert case.door.area_m2 is not None
        door_area = float(case.door.area_m2)
        constraints = (
            _constraint(
                "thrust",
                ft,
                (1.0 + lim.margin) * rt,
                None,
                f"F_T ≥ (1 + {lim.margin:g})·R_T",
            ),
            _constraint(
                "net_open",
                dpa_f,
                lim.open_ratio * c.dpa_geometric_m,
                None,
                f"DPA de Fridman ≥ {lim.open_ratio:g}·DPA geométrica",
            ),
            _constraint(
                "warp",
                best_bl,
                safety * rt,
                None,
                f"rotura de algún cable del catálogo ≥ {safety:g}·R_T",
            ),
            _constraint(
                "door",
                c.door_required_m2,
                None,
                door_area * (1.0 + lim.door_tolerance),
                "superficie requerida por portón (Port!F215) ≤ superficie del portón",
            ),
            _constraint(
                "speed",
                v,
                lim.v_min_kn,
                lim.v_max_kn,
                f"{lim.v_min_kn:g} ≤ v ≤ {lim.v_max_kn:g} kn",
            ),
        )
        penalty = float(sum(k.violation for k in constraints))
        return Evaluation(
            s=c.s,
            v_kn=v,
            net_id=c.net_id,
            vessel_id=case.vessel.id,
            door_id=case.door.id,
            propeller=case.ft_propeller.value,
            ah_m=ah,
            dpa_fridman_m=dpa_f,
            av_m=av,
            av_fridman_m=av_f,
            area_rate_m2_h=ah * v_ms * 3600.0,
            volume_rate_m3_h=ah * av * v_ms * 3600.0,
            demand_kgf=rt,
            available_kgf=ft,
            thrust_margin=ft / rt - 1.0,
            energy_kgf_m_per_m2=rt / ah,
            net_drag_kgf=at(c.net_drag_kgf),
            dpa_geometric_m=c.dpa_geometric_m,
            headrope_m=c.headrope_m,
            footrope_m=c.footrope_m,
            door_area_m2=door_area,
            door_required_m2=c.door_required_m2,
            warp_id=warp_id,
            constraints=constraints,
            feasible=all(k.ok for k in constraints),
            penalty=penalty,
        )


def evaluate(
    base_case: DesignCase,
    s: float,
    v_kn: float,
    *,
    door_id: str | Door | None = None,
    door_angle: float | None = None,
    propeller: PropellerType | str | None = None,
    limits: Limits | None = None,
    compat: Compat | str = Compat.CORRECTED,
) -> Evaluation:
    """Evalúa la red del caso escalada por ``s`` remolcada a ``v_kn`` (ver :class:`Evaluator`)."""
    ev = Evaluator(
        base_case,
        door=door_id,
        door_angle=door_angle,
        propeller=propeller,
        compat=compat,
        limits=limits,
    )
    return ev.at(s, v_kn)


__all__ = [
    "GRID_STEP_KN",
    "OBJECTIVES",
    "OBJECTIVE_ALIASES",
    "Constraint",
    "Curves",
    "Evaluation",
    "Evaluator",
    "Limits",
    "evaluate",
    "speed_grid",
]
