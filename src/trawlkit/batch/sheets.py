"""Lectura de planillas (CSV o XLSX) de flotas, redes y casos (Fase 14).

Las planillas que llegan del puerto o de la escuela no siguen un formato fijo. :func:`read_book`
lee un CSV o un XLSX y :func:`parse_sheet` reconoce las columnas por su nombre, como el
importador de sensores (:mod:`trawlkit.sensors`):

* separador ``,``, ``;`` o tabulador (detectado); coma decimal si el separador es ``;`` o si el
  número no tiene punto (``27,5``);
* líneas que empiezan con ``#`` = comentarios; filas vacías ignoradas;
* nombres en español o inglés, sin importar acentos ni mayúsculas, con la unidad como sufijo o
  entre paréntesis o corchetes (``Potencia (kW)``, ``eslora_ft``, ``Mallero [mm]``);
* las unidades se convierten a las del motor (hp, m, mm, kn, kg, kgf).

Un error en una fila o una columna se informa con su ubicación (:class:`RowIssue`) y nunca
aborta la lectura del resto.
"""

from __future__ import annotations

import csv
import io
import math
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

ColKind = Literal["float", "int", "str", "enum"]

#: Unidad base → (sufijo normalizado → factor a la base).
UNITS: dict[str, dict[str, float]] = {
    "hp": {"hp": 1.0, "bhp": 1.0, "cv": 1.0, "ps": 1.0, "kw": 1.0 / 0.7355},
    "m": {"m": 1.0, "cm": 0.01, "mm": 0.001, "ft": 0.3048, "pie": 0.3048, "pies": 0.3048},
    "mm": {"mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4, "pulg": 25.4},
    "kn": {"kn": 1.0, "nudos": 1.0, "nudo": 1.0, "kt": 1.0, "m_s": 1.0 / 0.5144},
    "kg": {"kg": 1.0, "t": 1000.0},
    "kgf": {"kgf": 1.0, "kg": 1.0, "t": 1000.0, "n": 1.0 / 9.80665, "kn": 1000.0 / 9.80665},
    "tex": {"tex": 1.0, "rtex": 1.0},
    "": {"": 1.0},
}


@dataclass(frozen=True)
class Col:
    """Columna reconocida: clave, nombres admitidos, tipo, unidad base y ayuda."""

    key: str
    aliases: tuple[str, ...]
    kind: ColKind = "float"
    unit: str = ""
    required: bool = False
    help: str = ""
    example: str = ""
    #: Para ``enum``: valor normalizado → valor del motor.
    choices: tuple[tuple[str, str], ...] = ()
    low: float | None = None
    high: float | None = None


@dataclass(frozen=True)
class RowIssue:
    """Observación de la lectura: nivel, código, mensaje, fila (1 = primera de datos) y columna."""

    level: Literal["error", "warning"]
    code: str
    message: str
    row: int | None = None
    column: str | None = None
    sheet: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return asdict(self)


@dataclass
class Sheet:
    """Hoja leída: nombre, encabezados y filas crudas (texto o número)."""

    name: str
    headers: list[str]
    rows: list[list[Any]]
    decimal_comma: bool = False


@dataclass
class Parsed:
    """Filas interpretadas de una hoja y sus observaciones."""

    records: list[dict[str, Any]]
    columns: dict[str, str]
    """Encabezado de la planilla → clave reconocida."""
    ignored: list[str]
    issues: list[RowIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "records": self.records,
            "columns": self.columns,
            "ignored": self.ignored,
            "issues": [i.to_dict() for i in self.issues],
        }


def norm(text: str) -> str:
    """Nombre normalizado: sin acentos, minúsculas, ``_`` entre palabras."""
    t = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")


def split_unit(header: str) -> tuple[str, str | None]:
    """``"Potencia (kW)"`` → ``("potencia", "kw")``; ``"eslora_m"`` → ``("eslora_m", None)``."""
    m = re.match(r"^(.*?)\s*[\(\[]([^\)\]]+)[\)\]]\s*$", str(header))
    if m:
        return norm(m.group(1)), norm(m.group(2))
    return norm(header), None


def match(header: str, cols: Sequence[Col]) -> tuple[Col, float] | None:
    """Columna y factor de conversión a la unidad base, o ``None`` si no se reconoce."""
    name, unit = split_unit(header)
    for col in cols:
        table = UNITS[col.unit]
        if name in col.aliases or name == col.key:
            if unit is None:
                return col, 1.0
            return (col, table[unit]) if unit in table else None
        for alias in (col.key, *col.aliases):
            if name.startswith(alias + "_"):
                suffix = name[len(alias) + 1 :]
                if suffix in table:
                    return col, table[suffix]
    return None


# -- lectura de archivos -----------------------------------------------------------------------


def _sniff(text: str) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")][:5]
    sample = "\n".join(lines)
    counts = {d: sample.count(d) for d in (";", "\t", ",")}
    return max(counts, key=lambda d: counts[d]) if any(counts.values()) else ","


def read_csv(text: str, name: str = "planilla") -> Sheet:
    """Hoja de un CSV (separador detectado, comentarios ``#``, filas vacías fuera)."""
    text = text.lstrip("﻿")
    delim = _sniff(text)
    reader = csv.reader(
        (ln for ln in io.StringIO(text) if ln.strip() and not ln.lstrip().startswith("#")),
        delimiter=delim,
    )
    rows = [r for r in reader if any(c.strip() for c in r)]
    if not rows:
        return Sheet(name, [], [], delim == ";")
    return Sheet(name, [h.strip() for h in rows[0]], rows[1:], delim == ";")


def read_xlsx(data: bytes) -> list[Sheet]:
    """Hojas de un libro XLSX (necesita openpyxl: extra ``excel``)."""
    try:
        import openpyxl
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise RuntimeError('leer XLSX necesita openpyxl: pip install "trawlkit[excel]"') from exc
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    out: list[Sheet] = []
    for ws in wb.worksheets:
        rows = [
            ["" if c is None else c for c in r]
            for r in ws.iter_rows(values_only=True)
            if r and any(c not in (None, "") for c in r)
        ]
        rows = [r for r in rows if not str(r[0]).lstrip().startswith("#")]
        if not rows:
            continue
        out.append(Sheet(ws.title, [str(h).strip() for h in rows[0]], [list(r) for r in rows[1:]]))
    wb.close()
    return out


def read_book(data: bytes | str, filename: str = "planilla.csv") -> list[Sheet]:
    """Hojas de un CSV (una) o de un XLSX (todas las que tengan datos)."""
    suffix = Path(filename).suffix.lower()
    if suffix in (".xlsx", ".xlsm"):
        if isinstance(data, str):
            raise ValueError("un XLSX se lee como bytes")
        return read_xlsx(data)
    text = data.decode("utf-8-sig", errors="replace") if isinstance(data, bytes) else data
    return [read_csv(text, Path(filename).stem or "planilla")]


# -- interpretación ----------------------------------------------------------------------------


def number(value: Any, decimal_comma: bool = False) -> float:
    """Número de una celda: admite coma decimal y separador de miles."""
    if isinstance(value, bool):
        raise ValueError("no es un número")
    if isinstance(value, (int, float)):
        return float(value)
    t = str(value).strip().replace(" ", "").replace(" ", "")
    if not t:
        raise ValueError("vacío")
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".") if decimal_comma else t.replace(",", "")
    elif "," in t:
        t = t.replace(",", ".")
    x = float(t)
    if not math.isfinite(x):
        raise ValueError("no es finito")
    return x


def parse_sheet(sheet: Sheet, cols: Sequence[Col]) -> Parsed:
    """Interpreta las filas de una hoja con las columnas ``cols``."""
    issues: list[RowIssue] = []
    mapping: dict[int, tuple[Col, float]] = {}
    columns: dict[str, str] = {}
    ignored: list[str] = []
    seen: dict[str, str] = {}
    for i, h in enumerate(sheet.headers):
        if not str(h).strip():
            continue
        hit = match(h, cols)
        if hit is None:
            ignored.append(h)
            continue
        col, factor = hit
        if col.key in seen:
            issues.append(
                RowIssue(
                    "warning",
                    "duplicate_column",
                    f"«{h}» repite «{seen[col.key]}»: se usa la primera",
                    column=h,
                    sheet=sheet.name,
                )
            )
            continue
        seen[col.key] = h
        mapping[i] = (col, factor)
        columns[h] = col.key
    for col in cols:
        if col.required and col.key not in seen:
            issues.append(
                RowIssue(
                    "error",
                    "missing_column",
                    f"falta la columna «{col.key}» ({col.help})",
                    column=col.key,
                    sheet=sheet.name,
                )
            )
    records: list[dict[str, Any]] = []
    for r, raw in enumerate(sheet.rows, start=1):
        rec: dict[str, Any] = {}
        for i, (col, factor) in mapping.items():
            cell = raw[i] if i < len(raw) else ""
            if cell is None or str(cell).strip() == "":
                continue
            header = sheet.headers[i]
            try:
                rec[col.key] = _value(col, cell, factor, sheet.decimal_comma)
            except ValueError as exc:
                issues.append(
                    RowIssue(
                        "error",
                        "bad_value",
                        f"«{cell}» no vale para {col.key}: {exc}",
                        row=r,
                        column=header,
                        sheet=sheet.name,
                    )
                )
                continue
            v = rec[col.key]
            if isinstance(v, float) and (
                (col.low is not None and v < col.low) or (col.high is not None and v > col.high)
            ):
                issues.append(
                    RowIssue(
                        "warning",
                        "out_of_range",
                        f"{col.key} = {v:g} fuera del rango habitual ({col.low:g}–{col.high:g})",
                        row=r,
                        column=header,
                        sheet=sheet.name,
                    )
                )
        if not rec:
            continue
        missing = [c.key for c in cols if c.required and c.key not in rec and c.key in seen]
        for key in missing:
            issues.append(
                RowIssue(
                    "error",
                    "missing_value",
                    f"falta {key}",
                    row=r,
                    column=seen[key],
                    sheet=sheet.name,
                )
            )
        rec["_row"] = r
        records.append(rec)
    return Parsed(records=records, columns=columns, ignored=ignored, issues=issues)


def _value(col: Col, cell: Any, factor: float, decimal_comma: bool) -> Any:
    if col.kind == "str":
        return str(cell).strip()
    if col.kind == "enum":
        key = norm(str(cell))
        for name, value in col.choices:
            if key == name:
                return value
        options = sorted({v for _, v in col.choices})
        raise ValueError(f"opción desconocida (use {', '.join(options)})")
    if isinstance(cell, str):
        m = re.match(r"^\s*([-+]?[\d.,\u202f ]+?)\s*([A-Za-z/]+)\s*$", cell)
        if m and col.unit:
            unit = norm(m.group(2))
            table = UNITS[col.unit]
            if unit not in table:
                raise ValueError(f"unidad «{m.group(2)}» desconocida para {col.unit}")
            factor = table[unit]
            cell = m.group(1)
    x = number(cell, decimal_comma) * factor
    if col.kind == "int":
        if abs(x - round(x)) > 1e-6:
            raise ValueError("se espera un entero")
        return int(round(x))
    return x


__all__ = [
    "UNITS",
    "Col",
    "Parsed",
    "RowIssue",
    "Sheet",
    "match",
    "norm",
    "number",
    "parse_sheet",
    "read_book",
    "read_csv",
    "read_xlsx",
    "split_unit",
]
