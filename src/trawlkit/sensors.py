"""Importador genérico de registros de sensores de pesca (CSV).

Los sistemas de monitoreo del arte (sensores de separación de portones, de altura de la relinga,
tensiómetros de los cables, GPS) exportan tablas con columnas y unidades distintas según el
fabricante. :func:`parse_log` lee un CSV cualquiera y reconoce las columnas por su nombre:

* separador ``,``, ``;`` o tabulador (detectado), coma decimal si el separador es ``;``;
* líneas que empiezan con ``#`` = comentarios;
* nombres en español o inglés, con la unidad como sufijo o entre paréntesis/corchetes
  (``speed_kn``, ``SOG (m/s)``, ``Tension babor [t]``…); ver :data:`ALIASES` y :data:`UNITS`;
* las tensiones de babor y estribor se promedian (tensión de un cable).

:func:`windows` agrupa las filas en tramos estacionarios (por velocidad o por tiempo) y resume
cada uno con la mediana; :func:`to_observations` convierte los tramos en observaciones para
:func:`trawlkit.sim.calibration.calibrate`.
"""

from __future__ import annotations

import csv
import io
import math
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

#: Magnitud → (nombres reconocidos, unidad interna). Los nombres se comparan sin acentos, en
#: minúsculas y con espacios/guiones como ``_``.
ALIASES: dict[str, tuple[tuple[str, ...], str]] = {
    "time": (("time", "timestamp", "datetime", "fecha_hora", "hora", "fecha", "t", "tiempo"), "s"),
    "speed": (
        ("speed", "sog", "stw", "velocidad", "vel", "speed_over_ground", "velocidad_fondo"),
        "kn",
    ),
    "door_spread": (
        (
            "door_spread",
            "doorspread",
            "dp",
            "separacion_portones",
            "separacion_de_portones",
            "door_distance",
            "ds",
        ),
        "m",
    ),
    "wing_spread": (
        ("wing_spread", "wingspread", "ah", "abertura_horizontal", "net_width", "ancho_red"),
        "m",
    ),
    "headrope_height": (
        (
            "headrope_height",
            "headline_height",
            "headline",
            "av",
            "abertura_vertical",
            "altura_relinga",
            "net_opening",
            "opening",
            "altura_red",
        ),
        "m",
    ),
    "warp_tension": (
        ("warp_tension", "tension", "tension_cable", "tension_cables", "warp_load", "load"),
        "kgf",
    ),
    "warp_tension_port": (
        ("warp_tension_port", "tension_port", "port_tension", "tension_babor", "babor", "port"),
        "kgf",
    ),
    "warp_tension_stbd": (
        (
            "warp_tension_stbd",
            "tension_stbd",
            "stbd_tension",
            "starboard_tension",
            "tension_estribor",
            "estribor",
            "stbd",
            "starboard",
        ),
        "kgf",
    ),
    "depth": (("depth", "profundidad", "prof", "bottom_depth", "door_depth"), "m"),
    "catch": (("catch", "catch_kg", "captura", "captura_kg", "catch_estimate"), "kg"),
}

#: Factores a la unidad interna, por unidad escrita en el encabezado.
UNITS: dict[str, dict[str, float]] = {
    "kn": {
        "kn": 1.0,
        "kt": 1.0,
        "kts": 1.0,
        "knots": 1.0,
        "nudos": 1.0,
        "ms": 1.9438445,
        "m_s": 1.9438445,
        "kmh": 0.5399568,
        "km_h": 0.5399568,
    },
    "m": {"m": 1.0, "cm": 0.01, "ft": 0.3048, "fm": 1.8288, "fathom": 1.8288, "brazas": 1.8288},
    "kgf": {
        "kgf": 1.0,
        "kg": 1.0,
        "t": 1000.0,
        "tf": 1000.0,
        "ton": 1000.0,
        "kn": 101.97162,
        "kn_force": 101.97162,
        "n": 0.10197162,
        "lbf": 0.45359237,
        "lb": 0.45359237,
    },
    "kg": {"kg": 1.0, "t": 1000.0, "ton": 1000.0},
    "s": {"s": 1.0},
}


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower().strip()
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")


def _split_unit(header: str) -> tuple[str, str | None]:
    """``"SOG (m/s)"`` → ``("sog", "m_s")``; ``"speed_kn"`` → ``("speed_kn", None)``."""
    m = re.match(r"^(.*?)[\s]*[\(\[]([^\)\]]+)[\)\]]\s*$", header)
    if m:
        return _norm(m.group(1)), _norm(m.group(2))
    return _norm(header), None


def match_column(header: str) -> tuple[str, float] | None:
    """Magnitud y factor de conversión de una columna, o ``None`` si no se reconoce."""
    name, unit = _split_unit(header)
    for qty, (names, base) in ALIASES.items():
        table = UNITS[base]
        if name in names:
            if unit is None:
                return qty, 1.0
            if unit in table:
                return qty, table[unit]
            return None
        for alias in names:
            if name.startswith(alias + "_"):
                suffix = name[len(alias) + 1 :]
                if suffix in table:
                    return qty, table[suffix]
    return None


@dataclass(frozen=True, eq=False)
class SensorLog:
    """Registro leído: columnas reconocidas (unidad interna) y avisos."""

    columns: dict[str, list[float]]  # magnitud → valores (NaN si falta)
    mapping: dict[str, str]  # encabezado original → magnitud
    ignored: tuple[str, ...]
    rows: int
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Resumen serializable (sin los valores)."""
        return {
            "mapping": dict(self.mapping),
            "ignored": list(self.ignored),
            "rows": self.rows,
            "quantities": sorted(self.columns),
            "warnings": list(self.warnings),
        }


def _number(text: str, decimal_comma: bool) -> float:
    t = text.strip()
    if not t:
        return math.nan
    if decimal_comma:
        t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return math.nan


def _time(text: str, decimal_comma: bool) -> float:
    v = _number(text, decimal_comma)
    if math.isfinite(v):
        return v
    t = text.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y %H:%M:%S", "%H:%M:%S", "%H:%M"):
        try:
            d = datetime.strptime(t, fmt)
        except ValueError:
            continue
        return (
            d.hour * 3600
            + d.minute * 60
            + d.second
            + (d.toordinal() * 86400 if d.year > 1900 else 0)
        )
    try:
        return datetime.fromisoformat(t).timestamp()
    except ValueError:
        return math.nan


def parse_log(text: str, *, max_rows: int = 200_000) -> SensorLog:
    """Lee un CSV de sensores (ver el docstring del módulo)."""
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if len(lines) < 2:
        raise ValueError("el archivo no tiene encabezado y datos")
    head = lines[0]
    delim = max((";", "\t", ","), key=head.count)
    if head.count(delim) == 0:
        delim = ","  # una sola columna
    decimal_comma = delim != "," and any(re.search(r"\d,\d", ln) for ln in lines[1:20])
    reader = csv.reader(io.StringIO("\n".join(lines)), delimiter=delim)
    headers = next(reader)
    mapping: dict[str, str] = {}
    factors: dict[int, tuple[str, float]] = {}
    ignored: list[str] = []
    for k, h in enumerate(headers):
        m = match_column(h)
        if m is None or m[0] in mapping.values():
            ignored.append(h)
            continue
        mapping[h] = m[0]
        factors[k] = m
    if not factors:
        raise ValueError("ninguna columna reconocida (ver los nombres admitidos en la ayuda)")
    cols: dict[str, list[float]] = {q: [] for q, _ in factors.values()}
    n = 0
    for row in reader:
        if n >= max_rows:
            break
        n += 1
        for k, (q, f) in factors.items():
            cell = row[k] if k < len(row) else ""
            v = _time(cell, decimal_comma) if q == "time" else _number(cell, decimal_comma) * f
            cols[q].append(v)
    warnings: list[str] = []
    if "warp_tension_port" in cols or "warp_tension_stbd" in cols:
        port = cols.pop("warp_tension_port", None)
        stbd = cols.pop("warp_tension_stbd", None)
        pairs = zip(port or [math.nan] * n, stbd or [math.nan] * n, strict=True)
        mean = [
            (a + b) / 2 if math.isfinite(a) and math.isfinite(b) else (a if math.isfinite(a) else b)
            for a, b in pairs
        ]
        if "warp_tension" not in cols:
            cols["warp_tension"] = mean
            warnings.append("tensión de un cable = promedio de babor y estribor")
    if "speed" not in cols:
        warnings.append("sin columna de velocidad: los tramos se arman por tiempo")
    return SensorLog(cols, mapping, tuple(ignored), n, tuple(warnings))


#: Magnitud del registro → magnitud observable del simulador.
TO_QUANTITY = {
    "door_spread": "door_spread_m",
    "wing_spread": "ah_m",
    "headrope_height": "headrope_height_m",
    "warp_tension": "warp_tension_kgf",
}


@dataclass(frozen=True)
class Window:
    """Tramo estacionario del registro: medianas y cantidad de filas."""

    speed_kn: float
    catch_kg: float
    n: int
    values: dict[str, float]
    spread: dict[str, float] = field(default_factory=dict)  # desvío intercuartil por magnitud
    t_start: float | None = None
    t_end: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "speed_kn": self.speed_kn,
            "catch_kg": self.catch_kg,
            "n": self.n,
            "values": dict(self.values),
            "spread": dict(self.spread),
            "t_start": self.t_start,
            "t_end": self.t_end,
        }


def _median(xs: Sequence[float]) -> float:
    v = sorted(x for x in xs if math.isfinite(x))
    if not v:
        return math.nan
    m = len(v) // 2
    return v[m] if len(v) % 2 else (v[m - 1] + v[m]) / 2


def _iqr(xs: Sequence[float]) -> float:
    v = sorted(x for x in xs if math.isfinite(x))
    if len(v) < 4:
        return math.nan
    return v[(3 * len(v)) // 4] - v[len(v) // 4]


def windows(
    log: SensorLog,
    *,
    by: str = "speed",
    width: float = 0.25,
    min_rows: int = 5,
    speed_kn: float | None = None,
) -> list[Window]:
    """Tramos estacionarios: por velocidad (``width`` en kn) o por tiempo (``width`` en min).

    Por tiempo hace falta una columna de tiempo y la velocidad sale de la columna de velocidad o
    de ``speed_kn``. Se descartan tramos con menos de ``min_rows`` filas.
    """
    if width <= 0:
        raise ValueError("width debe ser positivo")
    n = log.rows
    speed = log.columns.get("speed")
    catch = log.columns.get("catch", [0.0] * n)
    tcol = log.columns.get("time")
    keys: list[float | None] = []
    if by == "speed":
        if speed is None:
            raise ValueError("para agrupar por velocidad hace falta una columna de velocidad")
        keys = [round(v / width) * width if math.isfinite(v) and v > 0.3 else None for v in speed]
    elif by == "time":
        if tcol is None:
            raise ValueError("para agrupar por tiempo hace falta una columna de tiempo")
        t0 = min((t for t in tcol if math.isfinite(t)), default=0.0)
        keys = [math.floor((t - t0) / (60 * width)) if math.isfinite(t) else None for t in tcol]
    else:
        raise ValueError("by debe ser 'speed' o 'time'")
    groups: dict[float, list[int]] = {}
    for i, k in enumerate(keys):
        if k is not None:
            groups.setdefault(k, []).append(i)
    out = []
    for _, idx in sorted(groups.items()):
        if len(idx) < min_rows:
            continue
        sp = _median([speed[i] for i in idx]) if speed is not None else (speed_kn or math.nan)
        if not math.isfinite(sp):
            continue
        vals: dict[str, float] = {}
        spread: dict[str, float] = {}
        for q, col in log.columns.items():
            if q not in TO_QUANTITY:
                continue
            m = _median([col[i] for i in idx])
            if math.isfinite(m) and m > 0:
                vals[TO_QUANTITY[q]] = m
                iqr = _iqr([col[i] for i in idx])
                if math.isfinite(iqr):
                    spread[TO_QUANTITY[q]] = iqr
        if not vals:
            continue
        ts = [tcol[i] for i in idx if tcol is not None and math.isfinite(tcol[i])] if tcol else []
        out.append(
            Window(
                speed_kn=round(sp, 2),
                catch_kg=max(0.0, _median([catch[i] for i in idx]) if catch else 0.0) or 0.0,
                n=len(idx),
                values=vals,
                spread=spread,
                t_start=min(ts) if ts else None,
                t_end=max(ts) if ts else None,
            )
        )
    return out


def to_observations(ws: Sequence[Window], quantities: Sequence[str] | None = None) -> list[Any]:
    """Observaciones para la calibración (una por tramo y magnitud), con peso ∝ √filas."""
    from trawlkit.sim.calibration import Observation

    out = []
    for w in ws:
        for q, v in w.values.items():
            if quantities is not None and q not in quantities:
                continue
            if not 0.3 <= w.speed_kn <= 6.0:
                continue
            out.append(
                Observation(
                    q,
                    v,
                    w.speed_kn,
                    catch_kg=round(w.catch_kg, 0),
                    weight=min(3.0, math.sqrt(w.n / 10.0)) if w.n else 1.0,
                    source="sensores",
                )
            )
    return out


def example_log() -> str:
    """Registro de ejemplo (sintético) incluido en el paquete: ``data/examples/sensor_log.csv``."""
    from trawlkit.io.loader import DATA_DIR

    return (DATA_DIR / "examples" / "sensor_log.csv").read_text(encoding="utf-8")
