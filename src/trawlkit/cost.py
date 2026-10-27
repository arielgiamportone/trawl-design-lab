"""Lista de materiales y costo orientativo de un armado (Fase 13).

A partir de un :class:`~trawlkit.model.DesignResult` arma la lista de lo que hay que comprar para
armar el arte, con cantidades y, si hay precios, el costo:

* **Paño**: peso en aire de la red (``net.analyse``) por material [kg].
* **Relingas**: largo de la lima y del burlón con su cabo [m].
* **Bridas y patentes**: dos juegos de bridas superior e inferior y dos patentes (cable de
  acero), salvo en la pareja, donde no hay patentes [m].
* **Cable de remolque**: cantidad a comprar del cable elegido (``warps.quantity_m``) [m].
* **Boyas** [unidades], **portones** (2; 0 en la pareja) y **cadena** de lastre y reglaje [m]
  (los metros de la etapa de lastre, ``ballast.chain``, si el caso eligió una cadena).
* **Grilletes** [unidades] (Fase 19.2): cantidad supuesta por armado (:data:`SHACKLES_PER_SIDE`)
  y el grillete más chico del catálogo de componentes con carga de trabajo (WLL) no menor que la
  carga de trabajo del arte (Rem!E267).
* **Tangones, gemelo y vara** (Fase 19.5): paño, relingas, bridas, patentes, boyas y lastre se
  multiplican por las redes del aparejo; los portones son dos por red con tangones y dos en el
  gemelo (más el muerto central); con tangones se agregan las tijeras y en la vara las varas, los
  patines y las cadenas espantadoras (sin portones, boyas, bridas ni lastre).

Cada línea dice qué componente se usa (id del catálogo de componentes cuando lo hay) y su
precio: el del caso (``prices``, cargado por el usuario), el del componente (``price``) o ninguno.
Los totales se dan por moneda, y se dice cuántas líneas quedan sin precio: un precio faltante
nunca se toma como cero.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

from trawlkit.components import ComponentBase, Price, ShackleItem, get_component
from trawlkit.i18n import t

if TYPE_CHECKING:
    from trawlkit.model import DesignResult

Unit = str

#: Grilletes por banda (supuesto de la lista de materiales, Fase 19.2; no hay fuente que dé la
#: cantidad): con portones, cable–portón, portón–patente, patente–malletas y las dos malletas a
#: la punta del ala (relinga superior e inferior) = 5; en la pareja, sin portones ni patentes,
#: cable–malletas y las dos malletas al ala = 3. Las uniones de la red (copo, paños) no cuentan.
SHACKLES_PER_SIDE: dict[str, int] = {"otter": 5, "pair": 3, "outrigger": 5, "twin": 5, "beam": 3}


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
    #: Línea de cantidad supuesta (grilletes): suma al total si tiene precio, pero sin precio no
    #: deja incompleta la lista (no cuenta en ``missing_prices``).
    optional: bool = False

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


def select_shackle(load_t: float, case: Any = None) -> ShackleItem | None:
    """Grillete más chico del catálogo con WLL ≥ ``load_t`` [t] (a igual WLL, el más liviano).

    Con un caso, respeta sus filtros de componentes (marca, región, genéricos); ``None`` si
    ningún grillete alcanza la carga.
    """
    from trawlkit.components import load_components
    from trawlkit.model import component_filters

    flt = component_filters(case) if case is not None else None
    items = [s for s in load_components("shackle", **(flt or {})) if isinstance(s, ShackleItem)]
    ok = [s for s in items if s.wll_t >= load_t]
    if not ok:
        return None
    return min(ok, key=lambda s: (s.wll_t, s.weight_kg, s.id))


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
    mr = result.multirig
    nets = 1 if mr is None else mr.n_nets
    beam = mr is not None and mr.kind == "beam"
    per = "" if nets == 1 else t(" ({n} redes)", n=nets)

    def add(
        key: str,
        label: str,
        quantity: float,
        unit: str,
        kind: str | None,
        item_id: str | None,
        name: str | None = None,
        note: str | None = None,
        optional: bool = False,
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
                optional=optional,
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
            t("Paño de {material}", material=mat) + per,
            nets * kg,
            "kg",
            "twine" if twine else None,
            twine,
            name=None if twine else t("Paño {material} del plano", material=mat),
        )

    # Relingas.
    head = result.floats.headrope_rope
    foot = result.ballast.footrope_rope
    add(
        "headrope", t("Lima (relinga superior)") + per, nets * dims.headrope_m, "m", "rope", head.id
    )
    add(
        "footrope",
        t("Burlón (relinga inferior)") + per,
        nets * dims.footrope_m,
        "m",
        "rope",
        foot.id,
    )

    # Bridas y patentes (dos lados de cada red; la vara no las lleva).
    br = result.bridles
    wire_id = warp_id or result.warps.selection.id
    bridles_m = 2.0 * (br.lengths.upper_m + br.lengths.lower_m)
    if not beam:
        add(
            "bridles",
            t("Malletas (superior e inferior, dos lados)") + per,
            nets * bridles_m,
            "m",
            "wire",
            wire_id,
        )
    if not case.is_pair and not beam and br.sweeps_m > 0:
        add("sweeps", t("Patentes (dos)") + per, nets * 2.0 * br.sweeps_m, "m", "wire", wire_id)
    if mr is not None and mr.bridle_m is not None:
        add(
            "outrigger_bridles",
            t("Tijeras (dos ramas por red)"),
            nets * 2.0 * mr.bridle_m,
            "m",
            None,
            None,
            name=t("Cable de acero Ø{d:g} mm", d=mr.bridle_diameter_mm or 0.0),
        )
    add(
        "warps",
        t("Cable de remolque"),
        float(result.warps.quantity_m),
        "m",
        "wire",
        wire_id,
        note=t("2 cables del largo filado más 50 % de reserva (Cab!D12)")
        if mr is None
        else t(
            "{n} cables del largo filado más {pct:.0f} % de reserva",
            n=mr.n_warps,
            pct=100 * case.warp_spare_fraction,
        ),
    )

    # Boyas.
    fl = result.floats
    if not beam:  # en la vara la lima va a la vara
        add(
            "floats",
            t("Boyas de {d:g} mm", d=fl.diameter_mm) + per,
            float(nets * fl.count),
            "unit",
            "float" if case.float_id else None,
            case.float_id,
            name=None if case.float_id else t("Boya Ø{d:g} mm", d=fl.diameter_mm),
        )

    # Portones.
    n_doors = 2 if mr is None else mr.n_doors
    if not case.is_pair and n_doors > 0:
        add(
            "doors",
            t("Portones (par)") if n_doors == 2 else t("Portones ({n})", n=n_doors),
            float(n_doors),
            "unit",
            "door",
            case.door.id,
            name=case.door.name,
        )
    if mr is not None and mr.kind == "twin":
        add(
            "clump",
            t("Muerto central (trineo)"),
            1.0,
            "unit",
            None,
            None,
            name=t("Muerto central"),
            note=None
            if mr.clump_weight_kg is None
            else t("{kg:.0f} kg en aire", kg=mr.clump_weight_kg),
        )
    if beam and mr is not None and mr.beam is not None:
        b = mr.beam
        add(
            "beams",
            t("Varas de {m:.2f} m", m=b.beam_length_m),
            float(nets),
            "unit",
            None,
            None,
            name=t("Vara Ø{d:g} m", d=b.beam_diameter_m),
        )
        add(
            "beam_shoes",
            t("Patines de la vara"),
            float(2 * nets),
            "unit",
            None,
            None,
            name=t("Patín de {h:.2f} m", h=b.shoe_height_m),
        )
        if b.ticklers:
            from trawlkit.rigging.multirig import BEAM_CLASSES

            data = BEAM_CLASSES[b.beam_class]
            n_tick = round(data.shoe_ticklers) + round(data.net_ticklers)
            add(
                "ticklers",
                t("Cadenas espantadoras"),
                float(nets * n_tick),
                "unit",
                None,
                None,
                name=t("Cadena espantadora"),
                note=t(
                    "{shoe:g} de patín y {net:g} de red por vara (medianas de C056/20, tabla 3; "
                    "A VERIFICAR)",
                    shoe=data.shoe_ticklers,
                    net=data.net_ticklers,
                ),
                optional=True,
            )

    # Cadena: reglaje y lastre del burlón (a lo sumo, el máximo del libro).
    bc = result.ballast.chain
    ballast_kg = float(nets * result.ballast.limits.max_kg)
    if beam:
        pass  # el tren de la vara son las cadenas: no hay lastre de Fridman
    elif bc is not None:
        add(
            "chain",
            t("Cadena de lastre y reglaje") + per,
            nets * bc.max_m,
            "m",
            "chain",
            bc.id,
            note=t(
                "{kg:.0f} kg de lastre máximo a {kgm:g} kg/m ({water:.0f} kgf en el agua)",
                kg=ballast_kg,
                kgm=bc.weight_kg_per_m,
                water=bc.water_weight_max_kgf,
            ),
        )
    else:
        add(
            "ballast",
            t("Lastre (cadena o plomos)") + per,
            ballast_kg,
            "kg",
            None,
            None,
            name=t("Lastre"),
            note=t("elija una cadena del catálogo para pasarlo a metros"),
        )

    # Grilletes de las uniones del aparejo (cantidad supuesta; ver SHACKLES_PER_SIDE).
    load_t = float(result.warps.loads.working_load_kgf) / 1000.0
    shackle = select_shackle(load_t, case)
    n = 2 * SHACKLES_PER_SIDE[case.rig_kind] * nets
    add(
        "shackles",
        t("Grilletes de las uniones del aparejo"),
        float(n),
        "unit",
        "shackle" if shackle else None,
        shackle.id if shackle else None,
        name=None if shackle else t("Grillete de WLL ≥ {load:.2g} t", load=load_t),
        note=t(
            "{n} grilletes ({per} por banda, supuesto) con WLL ≥ {load:.2g} t, la carga de "
            "trabajo del arte (Rem!E267)",
            n=n,
            per=n // (2 * nets),
            load=load_t,
        ),
        optional=True,
    )

    totals: dict[str, float] = {}
    for ln in lines:
        if ln.cost is not None and ln.currency:
            totals[ln.currency] = round(totals.get(ln.currency, 0.0) + ln.cost, 2)
    missing = sum(ln.cost is None and not ln.optional for ln in lines)
    return BillOfMaterials(lines=lines, totals=totals, missing_prices=missing)


__all__ = [
    "SHACKLES_PER_SIDE",
    "BillOfMaterials",
    "BomLine",
    "bill_of_materials",
    "select_shackle",
]
