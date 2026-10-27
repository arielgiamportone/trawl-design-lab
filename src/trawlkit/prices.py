"""Lista de precios del usuario: leer y escribir CSV o XLSX (Fase 19.2).

El catálogo de componentes no trae precios (cambian con el puerto, la fecha y el proveedor). El
usuario arma su lista de precios y la usa en la lista de materiales, el costo del armado y la
economía de la operación (``prices`` en :func:`trawlkit.cost.bill_of_materials` y
:func:`trawlkit.economics.economics`). Este módulo la pasa de planilla a ese mapa y vuelta:

* una fila por precio, con la **clave**: el id de un componente del catálogo
  (``crosby_g209_5_8in``) o la clave de una línea de la lista de materiales (``netting_pa``,
  ``doors``, ``floats``…);
* **precio**, **moneda** (ISO 4217), **unidad** (``kg``, ``m`` o ``unit``: la de la línea),
  **fecha** (AAAA-MM o AAAA-MM-DD) y **fuente**;
* columnas en español o en inglés, separador y coma decimal detectados, como las planillas de
  los lotes (:mod:`trawlkit.batch.sheets`).

Un error en una fila se informa con su número y no aborta el resto; un precio faltante nunca se
toma como cero.
"""

from __future__ import annotations

import datetime as _dt
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from trawlkit.batch.sheets import RowIssue, norm, read_book
from trawlkit.i18n import N_, get_lang, t

#: Columnas reconocidas: clave → nombres admitidos (normalizados con :func:`norm`).
COLUMNS: dict[str, tuple[str, ...]] = {
    "key": ("key", "clave", "id", "componente", "component", "component_id", "linea", "line"),
    "label": ("label", "descripcion", "description", "item", "nombre", "name", "detalle"),
    "value": ("value", "price", "precio", "valor", "unit_price", "precio_unitario"),
    "currency": ("currency", "moneda", "divisa"),
    "unit": ("unit", "unidad", "por"),
    "date": ("date", "fecha"),
    "source": ("source", "fuente", "proveedor", "supplier"),
}

#: Unidad escrita en la planilla → unidad de la lista de materiales.
UNITS: dict[str, str] = {
    "kg": "kg",
    "kilo": "kg",
    "kilogramo": "kg",
    "m": "m",
    "metro": "m",
    "metre": "m",
    "meter": "m",
    "unit": "unit",
    "u": "unit",
    "un": "unit",
    "unidad": "unit",
    "pieza": "unit",
    "pza": "unit",
    "pc": "unit",
    "pcs": "unit",
    "piece": "unit",
    "ud": "unit",
}

#: Encabezados de la planilla exportada (se traducen con ``t`` al escribirla).
HEADERS: tuple[tuple[str, str], ...] = (
    ("key", N_("clave")),
    ("label", N_("descripción")),
    ("value", N_("precio")),
    ("currency", N_("moneda")),
    ("unit", N_("unidad")),
    ("date", N_("fecha")),
    ("source", N_("fuente")),
)

#: Máximo de filas de una lista de precios (guarda de costo del servidor).
MAX_ROWS = 5000

_DATE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")


@dataclass
class PriceList:
    """Precios leídos de una planilla, observaciones y columnas que no se reconocieron."""

    prices: dict[str, dict[str, Any]]
    rows: int
    issues: list[RowIssue] = field(default_factory=list)
    ignored: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "prices": self.prices,
            "rows": self.rows,
            "issues": [i.to_dict() for i in self.issues],
            "ignored": self.ignored,
        }


def _column(header: str) -> str | None:
    name = norm(re.sub(r"[\(\[].*?[\)\]]", "", str(header)))
    for key, aliases in COLUMNS.items():
        if name in aliases:
            return key
    return None


def _number(cell: Any, decimal_comma: bool) -> float | None:
    if isinstance(cell, bool):
        return None
    if isinstance(cell, int | float):
        return float(cell)
    text = str(cell).strip().replace(" ", "").replace(" ", "")
    text = re.sub(r"^[^\d\-]+|[^\d]+$", "", text)  # símbolos de moneda alrededor
    if not text:
        return None
    if decimal_comma or ("," in text and "." not in text):
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


def _date(cell: Any) -> str | None:
    if isinstance(cell, _dt.datetime | _dt.date):
        return cell.strftime("%Y-%m-%d")
    text = str(cell).strip()
    return text if _DATE.match(text) else None


def read_prices(
    data: bytes | str,
    filename: str = "precios.csv",
    *,
    currency: str | None = None,
    today: _dt.date | None = None,
) -> PriceList:
    """Lee una lista de precios (CSV o XLSX; de un XLSX, la primera hoja con datos).

    ``currency`` es la moneda de las filas que no la traen; sin ella, esas filas son un error.
    Sin fecha, se usa el mes de ``today`` (hoy) y se avisa; sin fuente, el nombre del archivo.
    Una clave repetida: vale la última fila y se avisa.
    """
    sheets = read_book(data, filename)
    issues: list[RowIssue] = []
    if not sheets or not sheets[0].headers:
        return PriceList({}, 0, [RowIssue("error", "empty", t("la planilla está vacía"))])
    sheet = sheets[0]
    cols: dict[int, str] = {}
    ignored: list[str] = []
    for j, h in enumerate(sheet.headers):
        key = _column(h)
        if key is None or key in cols.values():
            if str(h).strip():
                ignored.append(str(h))
            continue
        cols[j] = key
    missing = [k for k in ("key", "value", "unit") if k not in cols.values()]
    if missing:
        return PriceList(
            {},
            0,
            [
                RowIssue(
                    "error",
                    "columns",
                    t(
                        "faltan columnas: {cols} (se esperan clave, precio, moneda, unidad, fecha "
                        "y fuente)",
                        cols=", ".join(missing),
                    ),
                )
            ],
            ignored,
        )
    if len(sheet.rows) > MAX_ROWS:
        issues.append(
            RowIssue(
                "error",
                "too_many",
                t("demasiadas filas: {n} (máximo {max})", n=len(sheet.rows), max=MAX_ROWS),
            )
        )
        return PriceList({}, len(sheet.rows), issues, ignored)
    month = (today or _dt.date.today()).strftime("%Y-%m")
    default_source = t("lista de precios {file}", file=filename)
    prices: dict[str, dict[str, Any]] = {}
    for i, raw in enumerate(sheet.rows, start=1):
        rec = {key: (raw[j] if j < len(raw) else "") for j, key in cols.items()}
        key = str(rec.get("key") or "").strip()
        if not key:
            continue
        value = _number(rec.get("value", ""), sheet.decimal_comma)
        if value is None or value < 0:
            if str(rec.get("value", "")).strip():
                issues.append(
                    RowIssue(
                        "error",
                        "value",
                        t("precio inválido: {v!r}", v=str(rec.get("value"))),
                        i,
                        "value",
                    )
                )
            continue
        unit = UNITS.get(norm(str(rec.get("unit") or "")))
        if unit is None:
            issues.append(
                RowIssue(
                    "error",
                    "unit",
                    t("unidad inválida: {u!r} (use kg, m o unidad)", u=str(rec.get("unit"))),
                    i,
                    "unit",
                )
            )
            continue
        cur = str(rec.get("currency") or currency or "").strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", cur):
            issues.append(
                RowIssue(
                    "error",
                    "currency",
                    t("moneda inválida: {c!r} (código ISO de 3 letras)", c=cur),
                    i,
                    "currency",
                )
            )
            continue
        date = _date(rec.get("date") or "")
        if date is None:
            if str(rec.get("date") or "").strip():
                issues.append(
                    RowIssue(
                        "warning",
                        "date",
                        t("fecha inválida {d!r}: se usa {month}", d=str(rec["date"]), month=month),
                        i,
                        "date",
                    )
                )
            date = month
        source = str(rec.get("source") or "").strip() or default_source
        if key in prices:
            issues.append(
                RowIssue(
                    "warning",
                    "duplicate",
                    t("clave repetida {key!r}: vale esta fila", key=key),
                    i,
                    "key",
                )
            )
        prices[key] = {
            "value": value,
            "currency": cur,
            "unit": unit,
            "date": date,
            "source": source,
        }
    return PriceList(prices, len(sheet.rows), issues, ignored)


def price_rows(
    prices: Mapping[str, Mapping[str, Any]],
    lines: Iterable[Mapping[str, Any]] = (),
) -> list[list[Any]]:
    """Filas de la planilla: un precio por fila, y las líneas sin precio como plantilla.

    ``lines`` son líneas de la lista de materiales (``key``, ``label``, ``unit`` y, si lo hay,
    ``component_id``): dan la descripción y agregan, vacías, las que todavía no tienen precio.
    """
    labels: dict[str, tuple[str, str]] = {}
    order: list[str] = []
    for ln in lines:
        key = str(ln.get("component_id") or ln.get("key") or "")
        if key and key not in labels:
            labels[key] = (str(ln.get("label") or ""), str(ln.get("unit") or ""))
            order.append(key)
    for key in prices:
        if key not in labels:
            order.append(key)
    rows: list[list[Any]] = []
    for key in order:
        p = prices.get(key)
        label, unit = labels.get(key, ("", ""))
        if p is None:
            rows.append([key, label, "", "", unit, "", ""])
        else:
            rows.append(
                [
                    key,
                    label,
                    float(p["value"]),
                    p["currency"],
                    p["unit"],
                    p.get("date", ""),
                    p.get("source", ""),
                ]
            )
    return rows


def write_prices(
    prices: Mapping[str, Mapping[str, Any]],
    fmt: str = "csv",
    lines: Sequence[Mapping[str, Any]] = (),
) -> bytes:
    """Lista de precios en CSV (``;``, coma decimal en español) o XLSX; se vuelve a leer igual."""
    head = [t(h) for _, h in HEADERS]
    rows = price_rows(prices, lines)
    if fmt == "csv":
        import csv
        import io

        buf = io.StringIO()
        es = get_lang() == "es"
        w = csv.writer(buf, delimiter=";" if es else ",", lineterminator="\n")
        w.writerow(head)
        for row in rows:
            w.writerow(
                [
                    (f"{v:g}".replace(".", ",") if es else f"{v:g}") if isinstance(v, float) else v
                    for v in row
                ]
            )
        return buf.getvalue().encode("utf-8")
    if fmt == "xlsx":
        from trawlkit.batch.export import to_xlsx

        return to_xlsx([(t("Precios"), head, rows)])
    raise ValueError(t("formato: csv o xlsx"))


__all__ = ["COLUMNS", "HEADERS", "PriceList", "price_rows", "read_prices", "write_prices"]
