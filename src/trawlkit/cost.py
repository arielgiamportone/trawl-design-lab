"""Lista de materiales y costo orientativo de un armado (Fase 13).

A partir de un :class:`~trawlkit.model.DesignResult` arma la lista de lo que hay que comprar para
armar el arte, con cantidades y, si hay precios, el costo:

* **Paño**: peso en aire de la red (``net.analyse``) por material [kg].
* **Relingas**: largo de la lima y del burlón con su cabo [m].
* **Bridas y patentes**: dos juegos de bridas superior e inferior y dos patentes (cable de
  acero), salvo en la pareja, donde no hay patentes [m].
* **Cable de remolque**: cantidad a comprar del cable elegido (``warps.quantity_m``) [m].
* **Boyas** [unidades], **portones** (2; 0 en la pareja) y **cadena** de lastre y reglaje [m].

Cada línea dice qué componente se usa (id del catálogo de componentes cuando lo hay) y su
precio: el del caso (``prices``, cargado por el usuario), el del componente (``price``) o ninguno.
Los totales se dan por moneda, y se dice cuántas líneas quedan sin precio: un precio faltante
nunca se toma como cero.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

from trawlkit.components import ComponentBase, Price, get_component

if TYPE_CHECKING:
    from trawlkit.model import DesignResult

Unit = str


@dataclass(frozen=True)
class BomLine:
    """Una línea de la lista de materiales."""

    key: str
    label: str
    quantity: float
    unit: Unit
    component_id: str | None = None
    component_kind: str | None = None
    component_name: str | None = None
    unit_price: float | None = None
    currency: str | None = None
    price_source: str | None = None
    cost: float | None = None
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return asdict(self)


@dataclass(frozen=True)
class BillOfMaterials:
    """Lista de materiales con totales por moneda."""

    lines: list[BomLine]
    totals: dict[str, float] = field(default_factory=dict)
    missing_prices: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "lines": [ln.to_dict() for ln in self.lines],
            "totals": dict(self.totals),
            "missing_prices": self.missing_prices,
        }


def _component(kind: str, item_id: str | None) -> ComponentBase | None:
    if item_id is None:
        return None
    try:
        return get_component(kind, item_id)
    except KeyError:
        return None


def _price_for(
    item: ComponentBase | None, item_id: str | None, unit: str, prices: Mapping[str, Price]
) -> Price | None:
    if item_id is not None and item_id in prices:
        p = prices[item_id]
    elif item is not None and item.price is not None:
        p = item.price
    else:
        return None
    return p if p.unit == unit else None


def bill_of_materials(
    result: DesignResult,
    prices: Mapping[str, Price | Mapping[str, Any]] | None = None,
    *,
    warp_id: str | None = None,
) -> BillOfMaterials:
    """Lista de materiales del armado del resultado (ver el docstring del módulo).

    ``prices`` mapea id de componente (o clave de línea: ``netting_pa``, ``doors``…) a un precio
    orientativo; si no, se usa el ``price`` del componente. ``warp_id`` reemplaza el cable que
    eligió el motor (el optimizador lo verifica a la velocidad de trabajo).
    """
    case = result.case
    px: dict[str, Price] = {
        k: v if isinstance(v, Price) else Price.model_validate(v) for k, v in (prices or {}).items()
    }
    dims = result.dimensions.std
    lines: list[BomLine] = []

    def add(
        key: str,
        label: str,
        quantity: float,
        unit: str,
        kind: str | None,
        item_id: str | None,
        name: str | None = None,
        note: str | None = None,
    ) -> None:
        item = _component(kind, item_id) if kind else None
        price = _price_for(item, item_id, unit, px) or _price_for(None, key, unit, px)
        cost = None if price is None else price.value * quantity
        lines.append(
            BomLine(
                key=key,
                label=label,
                quantity=round(quantity, 3),
                unit=unit,
                component_id=item_id,
                component_kind=kind,
                component_name=name or (item.name if item else None),
                unit_price=None if price is None else price.value,
                currency=None if price is None else price.currency,
                price_source=None if price is None else price.source,
                cost=None if cost is None else round(cost, 2),
                note=note,
            )
        )

    # Paño: peso en aire por material.
    by_mat: dict[str, float] = {}
    geo = result.geometry.std
    for row in geo.rows:
        w = float(row.weight_air_kg)
        by_mat[row.row.material] = by_mat.get(row.row.material, 0.0) + w
    twine = case.twine_id
    for mat, kg in by_mat.items():
        add(
            f"netting_{mat.lower()}",
            f"Paño de {mat}",
            kg,
            "kg",
            "twine" if twine else None,
            twine,
            name=None if twine else f"Paño {mat} del plano",
        )

    # Relingas.
    head = result.floats.headrope_rope
    foot = result.ballast.footrope_rope
    add("headrope", "Lima (relinga superior)", dims.headrope_m, "m", "rope", head.id)
    add("footrope", "Burlón (relinga inferior)", dims.footrope_m, "m", "rope", foot.id)

    # Bridas y patentes (dos lados).
    br = result.bridles
    wire_id = warp_id or result.warps.selection.id
    bridles_m = 2.0 * (br.lengths.upper_m + br.lengths.lower_m)
    add("bridles", "Malletas (superior e inferior, dos lados)", bridles_m, "m", "wire", wire_id)
    if not case.is_pair and br.sweeps_m > 0:
        add("sweeps", "Patentes (dos)", 2.0 * br.sweeps_m, "m", "wire", wire_id)
    add(
        "warps",
        "Cable de remolque",
        float(result.warps.quantity_m),
        "m",
        "wire",
        wire_id,
        note="2 cables del largo filado más 50 % de reserva (Cab!D12)",
    )

    # Boyas.
    fl = result.floats
    add(
        "floats",
        f"Boyas de {fl.diameter_mm:g} mm",
        float(fl.count),
        "unit",
        "float" if case.float_id else None,
        case.float_id,
        name=None if case.float_id else f"Boya Ø{fl.diameter_mm:g} mm",
    )

    # Portones.
    if not case.is_pair:
        add(
            "doors",
            "Portones (par)",
            2.0,
            "unit",
            "door",
            case.door.id,
            name=case.door.name,
        )

    # Cadena: reglaje y lastre del burlón (a lo sumo, el máximo del libro).
    chain = _component("chain", case.chain_id)
    ballast_kg = float(result.ballast.limits.max_kg)
    if chain is not None:
        kgm = float(chain.weight_kg_per_m)  # type: ignore[attr-defined]
        add(
            "chain",
            "Cadena de lastre y reglaje",
            ballast_kg / kgm,
            "m",
            "chain",
            chain.id,
            note=f"{ballast_kg:.0f} kg de lastre máximo a {kgm:g} kg/m",
        )
    else:
        add(
            "ballast",
            "Lastre (cadena o plomos)",
            ballast_kg,
            "kg",
            None,
            None,
            name="Lastre",
            note="elija una cadena del catálogo para pasarlo a metros",
        )

    totals: dict[str, float] = {}
    for ln in lines:
        if ln.cost is not None and ln.currency:
            totals[ln.currency] = round(totals.get(ln.currency, 0.0) + ln.cost, 2)
    missing = sum(ln.cost is None for ln in lines)
    return BillOfMaterials(lines=lines, totals=totals, missing_prices=missing)


__all__ = ["BillOfMaterials", "BomLine", "bill_of_materials"]
