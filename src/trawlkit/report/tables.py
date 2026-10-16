"""Tablas neutrales del informe, compartidas por las salidas HTML y XLSX.

Una :class:`Table` es independiente del formato: título, columnas con unidad y filas de valores
crudos (``float``, ``int``, ``str`` o ``None``). El HTML formatea con
:func:`trawlkit.report.labels.fmt` y el XLSX escribe los números tal cual con formato de celda.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

Cell = float | int | str | None


@dataclass(frozen=True)
class Column:
    """Columna de una tabla: clave estable, encabezado en español y unidad."""

    key: str
    header: str
    unit: str = ""

    @property
    def heading(self) -> str:
        """Encabezado con la unidad entre corchetes (``"Velocidad [kn]"``)."""
        return f"{self.header} [{self.unit}]" if self.unit else self.header


@dataclass(frozen=True)
class Table:
    """Tabla del informe."""

    key: str
    """Identificador estable (nombre de hoja XLSX, ancla HTML)."""
    title: str
    columns: tuple[Column, ...]
    rows: tuple[tuple[Cell, ...], ...]
    note: str = ""
    source: str = ""
    """Celdas del Excel original que reproduce (``'Resistencia de la RED'!N302:N310``)."""
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Valida que todas las filas tengan tantas celdas como columnas."""
        n = len(self.columns)
        for i, row in enumerate(self.rows):
            if len(row) != n:
                raise ValueError(f"{self.key}: fila {i} tiene {len(row)} celdas, se esperaban {n}")

    def column(self, key: str) -> list[Cell]:
        """Valores de una columna por clave."""
        idx = [c.key for c in self.columns].index(key)
        return [row[idx] for row in self.rows]

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "key": self.key,
            "title": self.title,
            "columns": [{"key": c.key, "header": c.header, "unit": c.unit} for c in self.columns],
            "rows": [list(r) for r in self.rows],
            "note": self.note,
            "source": self.source,
        }
