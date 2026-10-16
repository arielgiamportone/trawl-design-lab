"""Utilidades para reproducir el comportamiento numérico de Excel en los módulos de aparejo.

Los módulos de ``trawlkit.rigging`` replican celdas que usan ``ROUND``, ``ROUNDUP``, ``ROUNDDOWN``,
``INT``, ``EVEN`` y ``LOOKUP``. Estas funciones imitan esa semántica (redondeo *half away from
zero*, truncado hacia cero, búsqueda binaria de ``LOOKUP``) tanto para escalares como para arrays.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import fields, is_dataclass
from typing import Any, TypeAlias

import numpy as np
import numpy.typing as npt

FloatArray: TypeAlias = npt.NDArray[np.float64]
FloatOrArray: TypeAlias = float | FloatArray

#: Tolerancia para absorber el ruido de coma flotante antes de truncar/redondear hacia arriba
#: (Excel trabaja con 15 dígitos significativos; p. ej. ``0.75 - 0.2`` debe tratarse como 0.55).
_EPS_DIGITS = 10


def as_array(x: FloatOrArray | Sequence[float]) -> FloatArray:
    """Convierte un escalar, lista o array a ``np.ndarray`` de ``float64``."""
    return np.asarray(x, dtype=float)


def ret(x: FloatArray, like: object) -> FloatOrArray:
    """Devuelve ``float`` si la entrada era escalar y ``np.ndarray`` en caso contrario."""
    if np.ndim(like) == 0 and isinstance(like, int | float | np.floating | np.integer):
        return float(x)
    return x


def excel_round(x: FloatOrArray, digits: int = 0) -> FloatOrArray:
    """``ROUND(x, digits)`` de Excel: redondeo *half away from zero*.

    ``round()`` de Python redondea al par (``round(0.5) == 0``); Excel devuelve 1.
    """
    a = as_array(x)
    scale = 10.0**digits
    scaled = np.round(np.abs(a) * scale, _EPS_DIGITS)
    out = np.sign(a) * np.floor(scaled + 0.5) / scale
    return ret(out, x)


def excel_roundup(x: FloatOrArray, digits: int = 0) -> FloatOrArray:
    """``ROUNDUP(x, digits)`` de Excel: redondeo alejándose de cero."""
    a = as_array(x)
    scale = 10.0**digits
    scaled = np.round(np.abs(a) * scale, _EPS_DIGITS)
    out = np.sign(a) * np.ceil(scaled) / scale
    return ret(out, x)


def excel_rounddown(x: FloatOrArray, digits: int = 0) -> FloatOrArray:
    """``ROUNDDOWN(x, digits)`` de Excel: truncado hacia cero."""
    a = as_array(x)
    scale = 10.0**digits
    scaled = np.round(np.abs(a) * scale, _EPS_DIGITS)
    out = np.sign(a) * np.floor(scaled) / scale
    return ret(out, x)


def excel_int(x: FloatOrArray) -> FloatOrArray:
    """``INT(x)`` de Excel: redondeo hacia −∞."""
    a = as_array(x)
    return ret(np.floor(np.round(a, _EPS_DIGITS)), x)


def excel_even(x: FloatOrArray) -> FloatOrArray:
    """``EVEN(x)`` de Excel: entero par más cercano alejándose de cero (``EVEN(8.4) == 10``)."""
    a = as_array(x)
    m = np.ceil(np.round(np.abs(a), _EPS_DIGITS))
    m = np.where(m % 2 == 1, m + 1, m)
    return ret(np.sign(a) * m, x)


def excel_lookup_index(value: float, vector: Sequence[float]) -> int:
    """Índice que devolvería ``LOOKUP(value, vector)`` de Excel (búsqueda binaria).

    Excel asume ``vector`` ordenado ascendente y devuelve la posición del mayor valor ≤ ``value``.
    Se reproduce la búsqueda binaria literal para que también coincida sobre vectores desordenados
    (p. ej. ``'Flotación y Lastre'!F92`` busca sobre el número de boyas, que no está ordenado).
    """
    lo, hi = 0, len(vector) - 1
    if hi < 0:
        raise ValueError("LOOKUP sobre vector vacío")
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if vector[mid] <= value:
            lo = mid
        else:
            hi = mid - 1
    if vector[lo] > value:
        raise ValueError(f"LOOKUP: ningún valor ≤ {value!r} en {list(vector)!r}")
    return lo


def dataclass_to_dict(obj: Any) -> dict[str, Any]:
    """``asdict`` que convierte arrays a listas (para serializar resultados)."""
    if not is_dataclass(obj) or isinstance(obj, type):
        raise TypeError("se esperaba una instancia de dataclass")
    out: dict[str, Any] = {}
    for f in fields(obj):
        v = getattr(obj, f.name)
        if isinstance(v, np.ndarray):
            out[f.name] = v.tolist()
        elif is_dataclass(v) and not isinstance(v, type):
            out[f.name] = dataclass_to_dict(v)
        elif isinstance(v, np.generic):
            out[f.name] = v.item()
        else:
            out[f.name] = v
    return out
