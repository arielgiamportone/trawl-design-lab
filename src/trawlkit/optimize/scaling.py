"""Escalado geométrico de una red: mismas mallas y materiales, más (o menos) mallas por panel.

La familia de redes ``scale_net(spec, s)`` conserva el mallero, el hilo, los materiales, los cortes
y los coeficientes de armado, y multiplica por ``s`` el número de mallas de cada borde y de alto de
cada panel. Es la manera habitual de "agrandar" o "achicar" un diseño probado para otro buque: las
dimensiones lineales (relingas, largos, circunferencias) escalan ≈ ``s`` y las superficies de
paño ≈ ``s²``.
"""

from __future__ import annotations

import math
from typing import Any

from trawlkit.io.schema import Door, NetSpec, Panel

#: Extras de un panel que son números de mallas (T1/T2 del Excel) y se escalan con los bordes.
_MESH_EXTRAS = ("meshes_a", "meshes_b")


def scale_count(n: int | float, s: float) -> int:
    """Número de mallas ``n`` escalado por ``s``, redondeado hacia arriba en .5 y al menos 1.

    Es una función del número de origen: dos bordes que compartían el mismo número de mallas
    siguen compartiéndolo después del escalado. ``0`` (borde en punta) se conserva.
    """
    if n == 0:
        return 0
    return max(1, math.floor(float(n) * s + 0.5))


def _scale_panel(panel: Panel, s: float) -> Panel:
    data: dict[str, Any] = panel.model_dump()
    for key in ("meshes_top", "meshes_bottom", "meshes_depth", *_MESH_EXTRAS):
        if data.get(key) is not None:
            data[key] = scale_count(data[key], s)
    return Panel.model_validate(data)


def scale_net(spec: NetSpec, s: float) -> NetSpec:
    """Red escalada geométricamente por ``s`` (``s = 1`` devuelve la misma red con otro ``id``).

    * Cada panel multiplica ``meshes_top``, ``meshes_bottom``, ``meshes_depth`` y los extras
      ``meshes_a``/``meshes_b`` (T1/T2) por ``s`` con :func:`scale_count`; el mallero, el hilo, el
      material, los cortes y ``hanging_ratio`` no cambian. Como el redondeo depende sólo del número
      de origen, los bordes que se unen (iguales en la red original) siguen iguales.
    * ``headrope``/``footrope.length_m`` (informativos: el motor recalcula las relingas a partir de
      las mallas, ver :mod:`trawlkit.dimensions`) se multiplican por ``s``.
    * ``floats.count`` (que el motor usa como número de boyas) escala con la lima y se redondea;
      ``total_buoyancy_kgf`` escala en la misma proporción que el número de boyas.
    * ``ballast_kg`` escala con el burlón.
    * ``id`` lleva el sufijo ``_s{s:.2f}``.
    """
    if not math.isfinite(s) or s <= 0:
        raise ValueError(f"el factor de escala debe ser positivo y finito (s = {s!r})")
    data: dict[str, Any] = spec.model_dump()
    data["panels"] = [_scale_panel(p, s).model_dump() for p in spec.panels]
    for rope in ("headrope", "footrope"):
        r = data.get(rope)
        if r is not None and r.get("length_m") is not None:
            r["length_m"] = float(r["length_m"]) * s
    fl = data.get("floats")
    if fl is not None:
        old = int(fl["count"])
        fl["count"] = scale_count(old, s)
        if fl.get("total_buoyancy_kgf") is not None and old > 0:
            fl["total_buoyancy_kgf"] = float(fl["total_buoyancy_kgf"]) * fl["count"] / old
    if data.get("ballast_kg") is not None:
        data["ballast_kg"] = float(data["ballast_kg"]) * s
    data["id"] = f"{spec.id}_s{s:.2f}"
    return NetSpec.model_validate(data)


def scale_door(door: Door, area_m2: float) -> Door:
    """Portón geométricamente semejante a ``door`` con superficie ``area_m2``.

    Largo y alto escalan con ``sqrt(area_m2 / area)``, los pesos con ``(area_m2 / area)^1.5`` y la
    polar CL/CD (adimensional) se conserva. Sirve para dimensionar el portón con la regla del libro
    (Port!F215) cuando el del catálogo queda chico para el buque.
    """
    if door.area_m2 is None or door.area_m2 <= 0:
        raise ValueError(f"el portón {door.id!r} no tiene superficie")
    if not math.isfinite(area_m2) or area_m2 <= 0:
        raise ValueError("area_m2 debe ser positiva")
    k = area_m2 / float(door.area_m2)
    lin = math.sqrt(k)
    data: dict[str, Any] = door.model_dump()
    data["area_m2"] = float(area_m2)
    for key in ("length_m", "height_m"):
        if data.get(key) is not None:
            data[key] = float(data[key]) * lin
    for key in ("weight_air_kg", "weight_water_kg"):
        if data.get(key) is not None:
            data[key] = float(data[key]) * k**1.5
    data["id"] = f"{door.id}_{area_m2:.2f}m2"
    return Door.model_validate(data)


__all__ = ["scale_count", "scale_door", "scale_net"]
