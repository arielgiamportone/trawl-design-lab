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
from trawlkit.model import run

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
) -> EnginePoint:
    """El caso de la red con la profundidad, el cable, el portón y las patentes de un lance."""
    spec = _spec(net)
    overrides: dict[str, Any] = {"depth_m": float(depth_m)}
    if warp_m is not None:
        overrides["measured_warp_m"] = float(warp_m)
    if sweeps_m is not None:
        overrides["sweeps_m"] = float(sweeps_m)
    case = catalog_case(spec, **overrides).case
    if door is not None:
        case = dataclasses.replace(case, door=validation_door(spec, door))
    r = run(case)
    v = np.asarray(case.speeds, dtype=float)
    assert case.door.area_m2 is not None
    return EnginePoint(
        depth_m=float(depth_m),
        speed_kn=float(speed_kn),
        warp_m=float(r.rigging.towing.warp_m),
        warp_from_source=warp_m is not None,
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


def reference_point(net: str | NetSpec, ref: Mapping[str, Any]) -> EnginePoint:
    """:func:`engine_point` con las condiciones de una entrada de ``measured`` o ``simulated``."""
    return engine_point(
        net,
        depth_m=float(ref["depth_m"]),
        speed_kn=float(ref["speed_kn"]),
        warp_m=None if ref.get("warp_m") is None else float(ref["warp_m"]),
        door=ref.get("door"),
        sweeps_m=None if ref.get("sweeps_m") is None else float(ref["sweeps_m"]),
    )


def references(net: str | NetSpec, kind: str = "measured") -> list[dict[str, Any]]:
    """Las mediciones (``kind="measured"``) o simulaciones (``"simulated"``) de la red."""
    spec = _spec(net)
    return [dict(x) for x in (spec.model_extra or {}).get(kind) or []]


def deviation(engine: float, reference: float | None) -> float | None:
    """Desvío relativo (motor − referencia) / referencia, o ``None`` sin referencia."""
    if reference is None or not reference:
        return None
    return engine / float(reference) - 1.0


__all__ = [
    "QUANTITIES",
    "TOLERANCES",
    "EnginePoint",
    "deviation",
    "engine_point",
    "reference_point",
    "references",
    "validation_door",
]
