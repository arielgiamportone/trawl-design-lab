"""Economía de la operación: costo, ingreso y margen de una marea (Fase 16).

A partir de un caso de diseño y de los datos de la operación que carga el usuario (precios,
marea, captura, tripulación) calcula, para cada velocidad de arrastre:

* **Combustible y lubricante.** Durante el lance la potencia al freno es
  ``P = R_T · v / η`` (``η`` :data:`TOWING_EFFICIENCY`, tiro × velocidad sobre potencia al
  freno), recortada a la del buque; en la navegación al caladero y de vuelta, una fracción
  :attr:`EconomicInputs.steaming_load` de la potencia del motor; en el calado y virado, una
  fracción :attr:`EconomicInputs.idle_load`. El combustible es ``P · SFC / ρ_gasoil`` y el
  lubricante una proporción del combustible (Parker y Tyedmers 2015).
* **Captura e ingreso.** La captura por hora de arrastre que carga el usuario vale a una
  velocidad de referencia y escala con el área barrida por hora ``AH · v`` (más velocidad o más
  boca, más área barrida; no se modela el escape ni el arreo). El ingreso es captura × precio en
  playa (o el promedio ponderado de las especies).
* **Tripulación.** «A la parte»: un porcentaje del ingreso, descontados antes (si así se reparte)
  el combustible, el lubricante y los gastos de la marea; o un jornal por día por tripulante.
* **Red y aparejo.** El costo del armado (lista de materiales, Fase 13, o el que carga el
  usuario) se amortiza en su vida útil en horas de arrastre, más una reparación anual como
  fracción del costo.
* **Otros.** Gastos por marea (hielo, víveres, carnada, puerto) y anuales (permisos, seguro)
  prorrateados por marea.

No se inventan precios. Sin precio del gasoil no hay costo; sin captura o sin precio de la
captura no hay ingreso ni margen. Los demás rubros sin dato (lubricante, tripulación, red,
gastos de la marea, fijos anuales) quedan fuera del total y se informan en
:attr:`TripEconomics.missing`: el resultado es incompleto (:attr:`TripEconomics.complete`).
Las constantes de ingeniería (consumo específico, rendimiento de remolque, cargas del motor)
tienen valores por defecto A VERIFICAR.
"""

from __future__ import annotations

import dataclasses
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from trawlkit.i18n import N_, t
from trawlkit.sim.core import DIESEL_KG_L, KW_PER_HP, SFC_KG_KWH, TOWING_EFFICIENCY

if TYPE_CHECKING:
    from trawlkit.model import DesignCase
    from trawlkit.optimize.evaluate import Evaluation, Limits

G = 9.80665
KNOT_MS = 1852.0 / 3600.0
CrewMode = Literal["share", "wage", "none"]

#: Velocidades de la curva económica [kn] (dentro del rango operativo del optimizador).
SPEED_STEP_KN = 0.25


@dataclass(frozen=True)
class Species:
    """Especie de la captura: fracción del peso y precio en playa por kg."""

    name: str
    share: float
    price: float | None = None


@dataclass(frozen=True)
class EconomicInputs:
    """Datos de la operación. Los precios y montos en ``None`` son «sin dato»."""

    currency: str = "USD"
    # Combustible y lubricante
    fuel_price_l: float | None = None
    lube_price_l: float | None = None
    lube_ratio: float = 0.01
    """L de lubricante por L de gasoil (A VERIFICAR: 0,5–2 % según el motor)."""
    sfc_kg_kwh: float = SFC_KG_KWH
    towing_efficiency: float = TOWING_EFFICIENCY
    steaming_load: float = 0.8
    """Fracción de la potencia del motor en navegación (A VERIFICAR)."""
    idle_load: float = 0.2
    """Fracción de la potencia en calado y virado (A VERIFICAR)."""
    # Marea
    steaming_hours: float = 4.0
    """Navegación ida y vuelta al caladero por marea [h]."""
    hauls_per_trip: int = 4
    haul_hours: float = 2.0
    handling_hours: float = 0.5
    """Calado y virado por lance [h]."""
    trip_days: float = 1.0
    trips_per_year: float = 150.0
    # Captura e ingreso
    catch_kg_h: float | None = None
    """Captura por hora de arrastre a ``reference_speed_kn`` [kg/h]."""
    reference_speed_kn: float = 3.0
    price_kg: float | None = None
    species: tuple[Species, ...] = ()
    # Tripulación
    crew_mode: CrewMode = "share"
    crew_share: float | None = None
    """Fracción para la tripulación «a la parte» (0–1)."""
    share_after_costs: bool = True
    crew_size: int | None = None
    wage_day: float | None = None
    # Red y aparejo
    gear_cost: float | None = None
    gear_life_hours: float = 2000.0
    """Vida útil del armado en horas de arrastre (A VERIFICAR)."""
    gear_repair_year: float = 0.1
    """Reparación anual como fracción del costo del armado."""
    # Otros gastos
    trip_costs: float | None = None
    """Hielo, víveres, carnada y puerto por marea."""
    annual_costs: float | None = None
    """Permisos, seguro y otros fijos por año."""

    def __post_init__(self) -> None:
        """Valida rangos."""
        checks = [
            (self.hauls_per_trip >= 1, "hauls_per_trip ≥ 1"),
            (self.haul_hours > 0, "haul_hours > 0"),
            (self.trips_per_year > 0, "trips_per_year > 0"),
            (self.reference_speed_kn > 0, "reference_speed_kn > 0"),
            (0 < self.towing_efficiency <= 1, N_("towing_efficiency en (0, 1]")),
            (self.gear_life_hours > 0, "gear_life_hours > 0"),
            (self.crew_share is None or 0 <= self.crew_share <= 1, N_("crew_share en [0, 1]")),
            (
                min(self.steaming_hours, self.handling_hours, self.trip_days) >= 0,
                N_("tiempos ≥ 0"),
            ),
        ]
        for ok, msg in checks:
            if not ok:
                raise ValueError(t(msg))

    @property
    def mean_price(self) -> float | None:
        """Precio medio por kg: el de las especies ponderado por su fracción, o ``price_kg``."""
        priced = [s for s in self.species if s.share > 0]
        if priced:
            if any(s.price is None for s in priced):
                return None
            total = sum(s.share for s in priced)
            return sum(s.share * (s.price or 0.0) for s in priced) / total
        return self.price_kg

    @property
    def towing_hours(self) -> float:
        """Horas de arrastre por marea."""
        return self.hauls_per_trip * self.haul_hours

    @property
    def sea_hours(self) -> float:
        """Horas en el mar por marea (navegación, lances y maniobras)."""
        return self.steaming_hours + self.towing_hours + self.hauls_per_trip * self.handling_hours

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        d = asdict(self)
        d["species"] = [asdict(s) for s in self.species]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EconomicInputs:
        """Desde un diccionario (las claves desconocidas dan ``ValueError``)."""
        names = {f.name for f in dataclasses.fields(cls)}
        unknown = set(data) - names
        if unknown:
            raise ValueError(t("datos desconocidos: {names}", names=", ".join(sorted(unknown))))
        d = dict(data)
        d["species"] = tuple(
            s if isinstance(s, Species) else Species(**s) for s in d.get("species", ())
        )
        return cls(**d)


@dataclass(frozen=True)
class TripEconomics:
    """Una marea a una velocidad: consumos, captura, costos, ingreso y margen."""

    speed_kn: float
    feasible: bool
    towing_power_kw: float
    power_limited: bool
    fuel_l_tow: float
    fuel_l_steam: float
    fuel_l_handling: float
    fuel_l: float
    fuel_l_h_tow: float
    area_rate_m2_h: float
    catch_kg: float | None
    fuel_l_per_kg: float | None
    revenue: float | None
    costs: dict[str, float | None]
    total_cost: float | None
    margin: float | None
    cost_per_kg: float | None
    margin_per_sea_hour: float | None
    breakeven_price: float | None
    missing: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        """Si el costo y el margen incluyen todos los rubros (no falta ningún dato)."""
        return not self.missing

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        d = asdict(self)
        d["missing"] = list(self.missing)
        d["warnings"] = list(self.warnings)
        d["complete"] = self.complete
        return d


COST_LABELS: dict[str, str] = {
    "fuel": N_("Combustible"),
    "lube": N_("Lubricante"),
    "crew": N_("Tripulación"),
    "gear": N_("Red y aparejo"),
    "trip": N_("Gastos de la marea"),
    "annual": N_("Fijos anuales (por marea)"),
}


def _mul(a: float | None, b: float) -> float | None:
    return None if a is None else a * b


def trip(
    inp: EconomicInputs,
    *,
    speed_kn: float,
    demand_kgf: float,
    area_rate_m2_h: float,
    reference_area_rate_m2_h: float,
    vessel_hp: float,
    feasible: bool = True,
    warnings: tuple[str, ...] = (),
) -> TripEconomics:
    """Economía de una marea a ``speed_kn`` con la resistencia y el área barrida del motor.

    ``reference_area_rate_m2_h`` es el área barrida por hora a la velocidad de referencia de la
    captura (:attr:`EconomicInputs.reference_speed_kn`).
    """
    max_kw = vessel_hp * KW_PER_HP
    tow_kw = demand_kgf * G * speed_kn * KNOT_MS / inp.towing_efficiency / 1000.0
    used = min(tow_kw, max_kw)
    l_per_kwh = inp.sfc_kg_kwh / DIESEL_KG_L
    fuel_tow_h = used * l_per_kwh
    fuel_tow = fuel_tow_h * inp.towing_hours
    fuel_steam = max_kw * inp.steaming_load * l_per_kwh * inp.steaming_hours
    fuel_hand = max_kw * inp.idle_load * l_per_kwh * inp.hauls_per_trip * inp.handling_hours
    fuel = fuel_tow + fuel_steam + fuel_hand

    missing: list[str] = []
    catch = None
    if inp.catch_kg_h is None:
        missing.append(t("captura por hora"))
    elif reference_area_rate_m2_h > 0:
        catch = inp.catch_kg_h * area_rate_m2_h / reference_area_rate_m2_h * inp.towing_hours
    price = inp.mean_price
    if price is None:
        missing.append(t("precio de la captura"))
    revenue = None if catch is None or price is None else catch * price

    if inp.fuel_price_l is None:
        missing.append(t("precio del gasoil"))
    if inp.lube_price_l is None:
        missing.append(t("precio del lubricante"))
    fuel_cost = _mul(inp.fuel_price_l, fuel)
    lube_cost = _mul(inp.lube_price_l, fuel * inp.lube_ratio)

    hours_year = inp.towing_hours * inp.trips_per_year
    if inp.gear_cost is None:
        missing.append(t("costo de la red y el aparejo"))
        gear = None
    else:
        per_hour = inp.gear_cost / inp.gear_life_hours + (
            inp.gear_cost * inp.gear_repair_year / hours_year
        )
        gear = per_hour * inp.towing_hours
    if inp.trip_costs is None:
        missing.append(t("gastos de la marea"))
    if inp.annual_costs is None:
        missing.append(t("costos fijos anuales"))
    annual = _mul(inp.annual_costs, 1.0 / inp.trips_per_year)

    # Los costos que se reparten antes de la parte: los que hay (el gasoil es obligatorio).
    shared = None if fuel_cost is None else fuel_cost + (lube_cost or 0.0) + (inp.trip_costs or 0.0)
    crew: float | None
    crew_rate = 0.0
    if inp.crew_mode == "none":
        crew = 0.0
    elif inp.crew_mode == "wage":
        if inp.wage_day is None or inp.crew_size is None:
            missing.append(t("jornal y cantidad de tripulantes"))
            crew = None
        else:
            crew = inp.wage_day * inp.crew_size * inp.trip_days
    else:
        if inp.crew_share is None:
            missing.append(t("parte de la tripulación"))
            crew = None
        else:
            crew_rate = inp.crew_share
            base = revenue
            if inp.share_after_costs and revenue is not None:
                base = None if shared is None else revenue - shared
            crew = None if base is None else inp.crew_share * max(base, 0.0)

    costs: dict[str, float | None] = {
        "fuel": fuel_cost,
        "lube": lube_cost,
        "crew": crew,
        "gear": gear,
        "trip": inp.trip_costs,
        "annual": annual,
    }
    # El total necesita el gasoil; los demás costos sin dato quedan fuera y se avisa (``missing``).
    total = None if fuel_cost is None else sum(v for v in costs.values() if v is not None)
    margin = None if total is None or revenue is None else revenue - total
    cost_kg = None if total is None or not catch else total / catch

    # Precio de equilibrio: el margen es lineal en el precio (la parte de la tripulación también).
    breakeven = None
    if total is not None and catch:
        fixed = total - (crew or 0.0)
        if inp.crew_mode == "share" and crew_rate > 0:
            if inp.share_after_costs and shared is not None:
                # m = R − fixed − c·(R − shared) = 0 → R = (fixed − c·shared)/(1 − c)
                need = (fixed - crew_rate * shared) / (1.0 - crew_rate)
                need = max(need, shared)  # por debajo de shared la tripulación no cobra
            else:
                need = fixed / (1.0 - crew_rate)
        else:
            need = fixed + (crew or 0.0)
        breakeven = need / catch if crew_rate < 1.0 else None
    return TripEconomics(
        speed_kn=speed_kn,
        feasible=feasible,
        towing_power_kw=tow_kw,
        power_limited=tow_kw > max_kw,
        fuel_l_tow=fuel_tow,
        fuel_l_steam=fuel_steam,
        fuel_l_handling=fuel_hand,
        fuel_l=fuel,
        fuel_l_h_tow=fuel_tow_h,
        area_rate_m2_h=area_rate_m2_h,
        catch_kg=catch,
        fuel_l_per_kg=fuel / catch if catch else None,
        revenue=revenue,
        costs=costs,
        total_cost=total,
        margin=margin,
        cost_per_kg=cost_kg,
        margin_per_sea_hour=None if margin is None else margin / inp.sea_hours,
        breakeven_price=breakeven,
        missing=tuple(missing),
        warnings=warnings,
    )


#: Restricciones del optimizador que deciden si el buque puede trabajar a esa velocidad; las
#: demás (apertura de la red, portón, rango) se informan como avisos.
TOWING_CONSTRAINTS = ("thrust", "warp")
CONSTRAINT_WARNINGS = {
    "net_open": N_("la red queda poco abierta a esta velocidad"),
    "door": N_("el portón queda chico"),
    "speed": N_("fuera del rango operativo"),
}


# ---------------------------------------------------------------------------------------------
# Curva por velocidad, comparación y ahorro
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class EconomicsResult:
    """Curva económica de un caso: una marea por velocidad, la mejor y el año."""

    net_id: str
    vessel_id: str
    currency: str
    gear_cost: float | None
    gear_cost_source: str
    trips: tuple[TripEconomics, ...]
    best_margin_kn: float | None
    best_cost_kg_kn: float | None
    least_fuel_kg_kn: float | None
    year: dict[str, float | None]
    inputs: EconomicInputs
    notes: tuple[str, ...] = field(default_factory=tuple)

    def at(self, speed_kn: float) -> TripEconomics:
        """La marea a la velocidad de la curva más cercana a ``speed_kn``."""
        return min(self.trips, key=lambda t: abs(t.speed_kn - speed_kn))

    @property
    def best(self) -> TripEconomics | None:
        """La marea de mayor margen (o, sin precios, la de menos combustible por kg)."""
        for kn in (self.best_margin_kn, self.least_fuel_kg_kn):
            if kn is not None:
                return self.at(kn)
        return None

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "net_id": self.net_id,
            "vessel_id": self.vessel_id,
            "currency": self.currency,
            "gear_cost": self.gear_cost,
            "gear_cost_source": self.gear_cost_source,
            "trips": [t.to_dict() for t in self.trips],
            "best_margin_kn": self.best_margin_kn,
            "best_cost_kg_kn": self.best_cost_kg_kn,
            "least_fuel_kg_kn": self.least_fuel_kg_kn,
            "year": dict(self.year),
            "inputs": self.inputs.to_dict(),
            "notes": list(self.notes),
        }


def _argbest(trips: list[TripEconomics], key: str, maximise: bool) -> float | None:
    cands = [t for t in trips if t.feasible and getattr(t, key) is not None]
    if not cands:
        return None
    pick = (max if maximise else min)(cands, key=lambda t: getattr(t, key))
    return pick.speed_kn


def bom_gear_cost(case: DesignCase, prices: dict[str, Any] | None, currency: str) -> float | None:
    """Costo del armado según la lista de materiales, si todas las líneas tienen precio."""
    from trawlkit.cost import bill_of_materials
    from trawlkit.model import run

    bom = bill_of_materials(run(case), prices)
    if bom.missing_prices:
        return None
    return bom.totals.get(currency)


def economics(
    case: DesignCase,
    inputs: EconomicInputs,
    *,
    speeds: tuple[float, ...] | None = None,
    limits: Limits | None = None,
    prices: dict[str, Any] | None = None,
    reference_area_rate_m2_h: float | None = None,
) -> EconomicsResult:
    """Curva económica del caso entre ``limits.v_min_kn`` y ``v_max_kn``.

    Si ``inputs.gear_cost`` falta y ``prices`` completa la lista de materiales en la moneda de
    ``inputs``, el costo del armado sale de ella. ``reference_area_rate_m2_h`` fija el área
    barrida por hora a la que corresponde ``inputs.catch_kg_h`` (por defecto, la de este caso a
    la velocidad de referencia); :func:`compare` le pasa la de la red base.
    """
    from trawlkit.optimize.evaluate import Evaluator, Limits

    lim = limits or Limits()
    ev = Evaluator(case, limits=lim)
    curves = ev.curves(1.0)
    lo, hi = float(ev.speeds[0]), float(ev.speeds[-1])
    if speeds is None:
        n = int(round((lim.v_max_kn - lim.v_min_kn) / SPEED_STEP_KN))
        speeds = tuple(round(lim.v_min_kn + i * SPEED_STEP_KN, 6) for i in range(n + 1))
    speeds = tuple(sorted({min(max(float(v), lo), hi) for v in speeds}))
    gear_source = t("usuario")
    if inputs.gear_cost is None and prices:
        cost = bom_gear_cost(ev.case, prices, inputs.currency)
        if cost is not None:
            inputs = dataclasses.replace(inputs, gear_cost=cost)
            gear_source = t("lista de materiales")
    if inputs.gear_cost is None:
        gear_source = t("sin dato")
    ref_v = min(max(inputs.reference_speed_kn, lo), hi)
    ref: Evaluation = ev.from_curves(curves, ref_v)
    ref_area = ref.area_rate_m2_h if reference_area_rate_m2_h is None else reference_area_rate_m2_h
    trips: list[TripEconomics] = []
    for v in speeds:
        e = ev.from_curves(curves, v)
        ok = all(c.ok for c in e.constraints if c.name in TOWING_CONSTRAINTS)
        warns = tuple(
            t(CONSTRAINT_WARNINGS.get(c.name, c.name))
            for c in e.constraints
            if not c.ok and c.name not in TOWING_CONSTRAINTS
        )
        trips.append(
            trip(
                inputs,
                speed_kn=v,
                demand_kgf=e.demand_kgf,
                area_rate_m2_h=e.area_rate_m2_h,
                reference_area_rate_m2_h=ref_area,
                vessel_hp=case.vessel.bhp,
                feasible=ok,
                warnings=warns,
            )
        )
    best_margin = _argbest(trips, "margin", True)
    best_cost = _argbest(trips, "cost_per_kg", False)
    least_fuel = _argbest(trips, "fuel_l_per_kg", False)
    pick_kn = best_margin if best_margin is not None else least_fuel
    pick = next((t for t in trips if t.speed_kn == pick_kn), None)
    year: dict[str, float | None] = {}
    if pick is not None:
        per = inputs.trips_per_year
        year = {
            "speed_kn": pick.speed_kn,
            "fuel_l": pick.fuel_l * per,
            "catch_kg": _mul(pick.catch_kg, per),
            "revenue": _mul(pick.revenue, per),
            "total_cost": _mul(pick.total_cost, per),
            "margin": _mul(pick.margin, per),
        }
    notes = [
        t(
            "Captura proporcional al área barrida por hora (AH·v) desde la velocidad de "
            "referencia; no se modela el escape ni el arreo."
        ),
        t(
            "Consumo específico {sfc:g} kg/kWh, rendimiento de remolque "
            "{eff:g}, carga en navegación {steam:g} y en maniobras {idle:g} (A VERIFICAR).",
            sfc=inputs.sfc_kg_kwh,
            eff=inputs.towing_efficiency,
            steam=inputs.steaming_load,
            idle=inputs.idle_load,
        ),
    ]
    if not any(tr_.feasible for tr_ in trips):
        notes.append(
            t(
                "A ninguna velocidad del rango el buque tiene tiro con reserva para esta red (o "
                "el cable no alcanza)."
            )
        )
    return EconomicsResult(
        net_id=case.net.id,
        vessel_id=case.vessel.id,
        currency=inputs.currency,
        gear_cost=inputs.gear_cost,
        gear_cost_source=gear_source,
        trips=tuple(trips),
        best_margin_kn=best_margin,
        best_cost_kg_kn=best_cost,
        least_fuel_kg_kn=least_fuel,
        year=year,
        inputs=inputs,
        notes=tuple(notes),
    )


@dataclass(frozen=True)
class Comparison:
    """Un caso en la comparación: su marea a la velocidad elegida y el ahorro frente a la base."""

    label: str
    result: EconomicsResult
    trip: TripEconomics | None
    annual_margin: float | None
    annual_fuel_l: float | None
    savings_year: float | None
    fuel_savings_l_year: float | None
    payback_years: float | None

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "label": self.label,
            "net_id": self.result.net_id,
            "vessel_id": self.result.vessel_id,
            "gear_cost": self.result.gear_cost,
            "trip": None if self.trip is None else self.trip.to_dict(),
            "annual_margin": self.annual_margin,
            "annual_fuel_l": self.annual_fuel_l,
            "savings_year": self.savings_year,
            "fuel_savings_l_year": self.fuel_savings_l_year,
            "payback_years": self.payback_years,
        }


def compare(
    cases: list[tuple[str, DesignCase, float | None]],
    inputs: EconomicInputs,
    *,
    speed_kn: float | None = None,
    limits: Limits | None = None,
    prices: dict[str, Any] | None = None,
) -> list[Comparison]:
    """Compara casos con los mismos datos de operación; el primero es la base.

    Cada caso va como ``(rótulo, caso, costo del armado o None)``. Sin ``speed_kn`` cada uno
    trabaja a su velocidad de mayor margen (o de menos combustible por kg). La captura por hora
    de ``inputs`` vale para la red base a la velocidad de referencia; las otras pescan en
    proporción a su área barrida por hora (una red más chica, menos captura). El **ahorro** es la
    diferencia de margen anual frente a la base (o, sin precios de captura, de costo anual) y el
    **repago** el costo del armado nuevo dividido por ese ahorro.
    """
    from trawlkit.optimize.evaluate import Evaluator

    out: list[Comparison] = []
    base: Comparison | None = None
    n = inputs.trips_per_year
    ref_area: float | None = None
    if cases:
        ev = Evaluator(cases[0][1], limits=limits)
        lo, hi = float(ev.speeds[0]), float(ev.speeds[-1])
        ref_area = ev.at(1.0, min(max(inputs.reference_speed_kn, lo), hi)).area_rate_m2_h
    for label, case, gear in cases:
        inp = inputs if gear is None else dataclasses.replace(inputs, gear_cost=gear)
        res = economics(case, inp, limits=limits, prices=prices, reference_area_rate_m2_h=ref_area)
        t = res.at(speed_kn) if speed_kn is not None else res.best
        margin = None if t is None or t.margin is None else t.margin * n
        cost = None if t is None or t.total_cost is None else t.total_cost * n
        fuel = None if t is None else t.fuel_l * n
        savings: float | None = None
        fuel_savings: float | None = None
        payback: float | None = None
        if base is not None and t is not None and base.trip is not None:
            if margin is not None and base.annual_margin is not None:
                savings = margin - base.annual_margin
            elif cost is not None and base.trip.total_cost is not None:
                savings = base.trip.total_cost * n - cost
            if fuel is not None and base.annual_fuel_l is not None:
                fuel_savings = base.annual_fuel_l - fuel
            if savings is not None and savings > 0 and res.gear_cost is not None:
                payback = res.gear_cost / savings
        comp = Comparison(label, res, t, margin, fuel, savings, fuel_savings, payback)
        if base is None:
            base = comp
        out.append(comp)
    return out


__all__ = [
    "COST_LABELS",
    "Comparison",
    "EconomicInputs",
    "EconomicsResult",
    "Species",
    "TripEconomics",
    "bom_gear_cost",
    "compare",
    "economics",
    "trip",
]
