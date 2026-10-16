"""Tablas neutrales del informe, compartidas por las salidas HTML y XLSX.

Una :class:`Table` es independiente del formato: título, columnas con unidad y filas de valores
crudos (``float``, ``int``, ``str`` o ``None``). El HTML formatea con
:func:`trawlkit.report.labels.fmt` y el XLSX escribe los números tal cual con formato de celda.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

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


# ---------------------------------------------------------------------------------------------
# Constructores de tablas a partir de un DesignResult
# ---------------------------------------------------------------------------------------------

if TYPE_CHECKING:
    from trawlkit.model import DesignResult

#: Nombres en español de las columnas de 'Resistencia de la RED' (``drag.SUMMARY_COLUMNS``).
METHOD_LABELS: dict[str, str] = {
    "tauti_nomura_shu": "Tauti–Nomura–Shu (1974)",
    "tauti_headrope": "Tauti (lima)",
    "tauti_footrope": "Tauti (burlón)",
    "koyama_1974": "Koyama (1974)",
    "koyama_1984": "Koyama (1984)",
    "hamuro": "Hamuro",
    "nomura_150": "Nomura 150 HP (tiro)",
    "nomura_180": "Nomura 180 HP (tiro)",
    "reid": "Reid (1977)",
    "robertson": "Robertson (1981)",
    "maclennan": "MacLennan (1981)",
    "aberdeen_demersal": "Aberdeen demersal",
    "aberdeen_pelagic": "Aberdeen pelágica",
    "fridman": "Fridman (1973)",
    "dickson": "Dickson",
}

#: Métodos de tiro disponible de ``PowerCurves`` (atributo, etiqueta).
PULL_METHODS: tuple[tuple[str, str], ...] = (
    ("fridman_kgf", "Fridman"),
    ("prado_kgf", "Prado–Dremière"),
    ("koyama_kgf", "Koyama"),
    ("nomura_kgf", "Nomura"),
    ("hamuro_kgf", "Hamuro"),
)

VARIANT_LABELS: dict[str, str] = {"std": "estándar", "mod": "modificada"}

PROPELLER_LABELS: dict[str, str] = {
    "fixed_pitch": "Paso fijo (PF)",
    "fixed_pitch_nozzle": "Paso fijo con tobera (PF+T)",
    "variable_pitch": "Paso variable (PV)",
    "variable_pitch_nozzle": "Paso variable con tobera (PV+T)",
}

PLANE_LABELS: dict[str, str] = {"upper": "superior", "lower": "inferior", "side": "lateral"}
SECTION_LABELS: dict[str, str] = {
    "wing_tip": "punta de ala",
    "wing": "ala",
    "square": "square",
    "belly": "vientre",
    "body": "cuerpo",
    "extension": "extensión",
    "codend": "bolsa",
}

#: Erratas cuyo tratamiento no depende del modo (ver ``docs/erratas.md``).
ERRATA_FIXED_TREATMENT: dict[str, tuple[str, str]] = {
    "nomura_column_links_hamuro": (
        "documentada",
        "Sin conmutador: Nomura se calcula de verdad; el enlace del libro sólo se documenta.",
    ),
    "nomura_ratio_typo": ("reproducida", "Tabla de referencia copiada tal cual en ambos modos."),
    "panel_f_cut_na": ("corregida", "El código de corte se calcula en ambos modos."),
    "panel_b_cut_uses_plan_coef": ("corregida", "La razón de corte usa N en ambos modos."),
    "panel_b_cut_code_lookup_a": ("corregida", "Cada paño busca con su propia razón."),
    "catenary_ratio_hardcoded": (
        "reproducida",
        "fL/L = 0.216 en ambos modos; el valor de tabla se anota en las notas.",
    ),
}


def _f(value: Any) -> float | None:
    """Número de Python (``None`` para NaN o ``None``)."""
    if value is None:
        return None
    x = float(value)
    return None if math.isnan(x) else x


def _at(values: Any, i: int) -> float | None:
    """Elemento ``i`` de una serie (escalar o array) como ``float``."""
    return _f(np.asarray(values, dtype=float)[i])


def _speeds(result: DesignResult) -> list[float]:
    return [float(v) for v in result.case.speeds_kn]


def _kv_columns() -> tuple[Column, ...]:
    return (
        Column("group", "Grupo"),
        Column("name", "Magnitud"),
        Column("value", "Valor"),
        Column("unit", "Unidad"),
    )


def _kv(group: str, name: str, value: Any, unit: str = "") -> tuple[Cell, ...]:
    v: Cell = value if isinstance(value, str) or value is None else _f(value)
    return (group, name, v, unit)


def has_modified(result: DesignResult) -> bool:
    """Indica si el caso trae una red modificada (columna G del libro)."""
    return result.case.net_modified is not None


def summary_table(result: DesignResult) -> Table:
    """Resumen del caso (``DesignResult.summary()``) con etiquetas en español."""
    from trawlkit.report.labels import label

    rows = []
    for key, value in result.summary().items():
        name, unit = label(key)
        rows.append(
            (key, name, value if isinstance(value, str) or value is None else _f(value), unit)
        )
    return Table(
        key="resumen",
        title="Resumen del diseño",
        columns=(
            Column("key", "Clave"),
            Column("name", "Magnitud"),
            Column("value", "Valor"),
            Column("unit", "Unidad"),
        ),
        rows=tuple(rows),
        source="'Dimensiones de la Red'!F45:F71; 'Resistencia de la RED'!N302:N310; "
        "'Portones y aparejamiento'!D190:D198; 'Cables Y Cabulleria'!D11:D12",
    )


def panels_table(result: DesignResult, variant: str = "std") -> Table:
    """Paños de la red (estándar o modificada) con Ss y peso de su fila de 'Mecánica de la Red'.

    Ss y peso se reparten entre los paneles de una fila según su cantidad (los paneles de una
    fila tienen compostura idéntica).
    """
    spec = result.case.net if variant == "std" else (result.case.net_modified or result.case.net)
    geom = result.geometry.variant(variant)
    share: dict[str, tuple[float, float]] = {}
    by_id = {p.id: p for p in spec.panels}
    for rg in geom.rows:
        total = sum(by_id[pid].count for pid in rg.row.panel_ids if pid in by_id) or 1
        for pid in rg.row.panel_ids:
            n = by_id[pid].count if pid in by_id else 0
            share[pid] = (rg.solid_surface_m2 * n / total, rg.weight_air_kg * n / total)
    rows = []
    for p in spec.panels:
        ss, w = share.get(p.id, (None, None))
        runnage = p.runnage_m_per_kg
        if runnage is None and p.rtex:
            runnage = 1_000_000.0 / p.rtex
        rows.append(
            (
                p.id,
                PLANE_LABELS.get(p.plane.value, p.plane.value),
                SECTION_LABELS.get(p.section.value, p.section.value),
                p.material,
                float(p.mesh_mm),
                float(p.twine_diameter_mm),
                _f(p.rtex),
                _f(runnage),
                int(p.meshes_top),
                int(p.meshes_bottom),
                int(p.meshes_depth),
                _f(p.hanging_ratio),
                int(p.count),
                p.cut_code or "—",
                _f(ss),
                _f(w),
            )
        )
    return Table(
        key=f"panos_{variant}",
        title=f"Paños de la red {VARIANT_LABELS[variant]} ({spec.id})",
        columns=(
            Column("id", "Paño"),
            Column("plane", "Plano"),
            Column("section", "Sección"),
            Column("material", "Material"),
            Column("mesh_mm", "Mallero", "mm"),
            Column("twine_mm", "Ø hilo", "mm"),
            Column("rtex", "Rtex", "tex"),
            Column("runnage", "Runnage", "m/kg"),
            Column("meshes_top", "Mallas boca"),
            Column("meshes_bottom", "Mallas bolsa"),
            Column("meshes_depth", "Mallas alto"),
            Column("u1", "U1"),
            Column("count", "Cant."),
            Column("cut", "Corte"),
            Column("ss_m2", "Ss", "m²"),
            Column("weight_kg", "Peso", "kg"),
        ),
        rows=tuple(rows),
        note="Ss y peso de la fila de 'Mecánica de la Red' repartidos por cantidad de paneles.",
        source="'Paños de red y cortes'!N269:W291; 'Mecánica de la Red'!C29:L37, N29, O107",
        meta={"variant": variant},
    )


def power_table(result: DesignResult) -> Table:
    """Tiro disponible por método y velocidad; FT de Fridman PF y PV+T de la clase."""
    curves = result.power.curves
    bhp = f"{result.case.vessel.bhp:g} HP"
    cols = [Column("speed_kn", "Velocidad", "kn")]
    cols += [Column(attr, f"{name} {bhp}", "kgf") for attr, name in PULL_METHODS]
    series: list[Any] = [getattr(curves, attr) for attr, _ in PULL_METHODS]
    for vid, s in result.power.class_fridman.items():
        tag = f"{s.bhp:g} HP"
        cols.append(Column(f"ft_pf_{vid}", f"FT Fridman PF {tag}", "kgf"))
        cols.append(Column(f"ft_pvt_{vid}", f"FT Fridman PV+T {tag}", "kgf"))
        series += [s.ft_fixed_pitch_kgf, s.ft_variable_pitch_nozzle_kgf]
    rows = tuple((v, *(_f(s[i]) for s in series)) for i, v in enumerate(_speeds(result)))
    return Table(
        key="potencia",
        title=f"Tiro disponible por método ({result.case.vessel.id}) y FT de Fridman de la clase",
        columns=tuple(cols),
        rows=rows,
        source="'Potencia Disponible Arrastre OK'!L11:O19, B10:G30, A160:L280",
    )


def drag_table(result: DesignResult, variant: str = "std") -> Table:
    """Resistencia de la red por método y velocidad [kgf] (13 métodos, Nomura y promedio)."""
    from trawlkit.drag import average

    table = result.drag.table.kgf
    cols_data = table.variant(variant)
    avg = average(table, result.case.compat)
    avg_v = avg.std if variant == "std" else avg.mod
    cols = [Column("speed_kn", "Velocidad", "kn")]
    cols += [Column(c, METHOD_LABELS.get(c, c), "kgf") for c in table.columns]
    cols.append(Column("average", "Promedio", "kgf"))
    rows = tuple(
        (float(v), *(_f(cols_data[c][i]) for c in table.columns), _f(avg_v[i]))
        for i, v in enumerate(table.speed_kn)
    )
    first, last = ("A398", "S406") if variant == "std" else ("A413", "S421")
    return Table(
        key=f"resistencia_{variant}",
        title=f"Resistencia de la red {VARIANT_LABELS[variant]} por método",
        columns=tuple(cols),
        rows=rows,
        note=f"RN de diseño: {METHOD_LABELS[result.drag.design_method]}. Las columnas de Nomura "
        "son tiro disponible, no resistencia.",
        source=f"'Resistencia de la RED'!{first}:{last}",
        meta={"variant": variant},
    )


def rigging_table(result: DesignResult) -> Table:
    """Portones, bridas, patentes, pies de gallo y aberturas (DPA, AH, AV) por método."""
    d = result.doors
    b = result.bridles
    s = result.spread
    case = result.case
    rows: list[tuple[Cell, ...]] = [
        _kv("Portones", "Portón", case.door.name),
        _kv("Portones", "Superficie del portón", case.door.area_m2, "m²"),
        _kv("Portones", "Distancia entre portones (Ds)", d.spread_m, "m"),
        _kv("Portones", "Semiángulo de divergencia (½φ)", d.half_divergence_deg, "°"),
        _kv("Portones", "Distancia corregida", d.spread_corrected_m, "m"),
        _kv("Portones", "Ángulo de ataque de la polar", d.polar.angle_deg, "°"),
        _kv("Portones", "CL", d.polar.cl),
        _kv("Portones", "CD", d.polar.cd),
        _kv("Portones", "CL/CD", d.polar.cl_cd),
    ]
    speeds = case.report_speeds_kn
    for share, arr in d.rob_shares_kgf.items():
        pct = share.replace("pct", " %")
        for v in speeds:
            i = case.speed_index(v)
            rows.append(_kv("Portones", f"ROB = {pct} de FT a {v:g} kn", arr[i], "kgf"))
    for v in speeds:
        i = case.speed_index(v)
        rows.append(
            _kv(
                "Portones",
                f"ROB hidrodinámica de un portón a {v:g} kn",
                _at(d.forces.drag_kgf, i),
                "kgf",
            )
        )
    rows += [
        _kv(
            "Portones",
            "Superficie requerida (promedio 2–4 kn)",
            d.required_area.average_total_m2,
            "m²",
        ),
        _kv("Portones", "Superficie requerida por portón", d.required_area.per_door_m2, "m²"),
        _kv(
            "Portones",
            "Superficie requerida por portón (clase)",
            d.required_area_per_door_class_m2,
            "m²",
        ),
        _kv("Bridas", "Brida superior", b.lengths.upper_m, "m"),
        _kv("Bridas", "Brida inferior", b.lengths.lower_m, "m"),
        _kv("Bridas", "Cadena de ajuste", b.lengths.adjust_chain_m, "m"),
        _kv("Bridas", "Brida sin triángulo", b.lengths.no_triangle_m, "m"),
        _kv("Bridas", "Brida con triángulo", b.lengths.triangle_m, "m"),
        _kv("Patentes", "Patentes de diseño", b.sweeps_m, "m"),
        _kv("Patentes", "Patentes + brida", b.sweeps_plus_bridle_m, "m"),
        _kv("Patentes", "Patentes (Dremière)", b.sweeps_dremiere_m, "m"),
        _kv("Patentes", "Patentes (Martini)", b.sweeps_martini_m, "m"),
        _kv("Patentes", "Patentes sin triángulo", b.sweeps_no_triangle_m, "m"),
        _kv("Patentes", "Patentes con triángulo", b.sweeps_triangle_m, "m"),
        _kv("Pies de gallo", "Pies de gallo", b.crowfoot.length_m, "m"),
        _kv("Pies de gallo", "Pie de gallo superior", b.crowfoot.upper_m, "m"),
        _kv("Pies de gallo", "Alargue", b.crowfoot.extension_m, "m"),
        _kv("Pies de gallo", "Ángulo de ataque de bridas (δ)", b.attack_angle_deg, "°"),
    ]
    for v in speeds:
        i = case.speed_index(v)
        rows.append(
            _kv("DPA", f"DPA Fridman estándar a {v:g} kn", _at(s.fridman.dpa_std_m, i), "m")
        )
        rows.append(
            _kv("DPA", f"DPA Fridman modificada a {v:g} kn", _at(s.fridman.dpa_mod_m, i), "m")
        )
    rows += [
        _kv("DPA", "DPA geométrica", s.dpa_geometric_m, "m"),
        _kv("DPA", "DPA geométrica con la red trabajando", s.dpa_working_m, "m"),
        _kv("DPA", "DPA por ángulo de corte", s.dpa_cut_angle_m, "m"),
        _kv("AH", "Abertura horizontal (AH)", s.horizontal_opening_m, "m"),
        _kv("AV", "AV Suzuki", s.vertical.suzuki_m, "m"),
    ]
    prado_names = {
        "low_opening": "baja abertura",
        "high_opening": "alta abertura",
        "shellfish": "mariscos",
    }
    for k, v in s.vertical.prado_m.items():
        rows.append(_kv("AV", f"AV Prado–Dremière ({prado_names.get(k, k)})", v, "m"))
    for j, v in enumerate(s.vertical.izzo_m, 1):
        rows.append(_kv("AV", f"AV Izzo ({j})", v, "m"))
    rows += [
        _kv("AV", "AV Martini", s.vertical.martini_m, "m"),
        _kv(
            "AV", "AV Baranov–Fridman estándar (promedio)", s.vertical.fridman.std.av_average_m, "m"
        ),
        _kv(
            "AV",
            "AV Baranov–Fridman modificada (promedio)",
            s.vertical.fridman.mod.av_average_m,
            "m",
        ),
    ]
    return Table(
        key="aparejo",
        title="Portones, bridas, patentes y aberturas",
        columns=_kv_columns(),
        rows=tuple(rows),
        source="'Portones y aparejamiento'!A1:H289; 'Mecánica de la Red'!B162:P282; "
        "'Dimensiones de la Red'!F60:F61",
    )


def floats_ballast_table(result: DesignResult) -> Table:
    """Flotación de la lima, boyas y lastre del burlón."""
    f = result.floats
    bl = result.ballast
    dist = f.distribution
    rows: list[tuple[Cell, ...]] = [
        _kv("Flotación", "Koyama", f.koyama_kgf, "kgf"),
        _kv("Flotación", "Prado–Dremière", f.prado_kgf, "kgf"),
        _kv("Flotación", "Fridman (promedio 1–3 kn)", f.fridman_average_kgf, "kgf"),
    ]
    for vid, v in f.class_fridman_average_kgf.items():
        rows.append(_kv("Flotación", f"Fridman {vid}", v, "kgf"))
    rows += [
        _kv("Flotación", "Flotación total de la clase (Ffz)", f.flotation_total_kgf, "kgf"),
        _kv("Flotación", "Flotación de diseño (redondeada)", f.flotation_rounded_kgf, "kgf"),
        _kv("Flotación", "Cabo de la lima", f.headrope_rope.id),
        _kv("Flotación", "Peso de la lima en el agua", f.headrope_weight_water_kgf, "kgf"),
        _kv("Boyas", "Cantidad de boyas", f.count, "u"),
        _kv("Boyas", "Diámetro de boya", f.diameter_mm, "mm"),
        _kv("Boyas", "Separación uniforme", dist.spacing_even_m, "m"),
        _kv("Boyas", "Boyas en alas", dist.on_wings, "u"),
        _kv("Boyas", "Boyas en el centro (bosom)", dist.on_bosom, "u"),
        _kv("Boyas", "Separación en el centro", dist.spacing_bosom_m, "m"),
    ]
    for v in result.case.report_speeds_kn:
        i = result.case.speed_index(v)
        rows.append(_kv("Boyas", f"Resistencia de las boyas (RB) a {v:g} kn", f.drag_kgf[i], "kgf"))
    rows += [
        _kv("Lastre", "Koyama", bl.koyama_kg, "kg"),
        _kv("Lastre", "Prado–Dremière", bl.prado_kg, "kg"),
        _kv("Lastre", "Cabo del burlón", bl.footrope_rope.id),
        _kv("Lastre", "Peso del burlón en el agua", bl.footrope_weight_water_kgf, "kgf"),
        _kv("Lastre", "Lastre mínimo", bl.limits.min_kg, "kg"),
        _kv("Lastre", "Lastre máximo", bl.limits.max_kg, "kg"),
        _kv("Lastre", "Cadena de ajuste", bl.adjust_chain_weight_kg, "kg"),
        _kv("Lastre", "Reparto uniforme", bl.even_kg_m, "kg/m"),
        _kv("Lastre", "Mínimo: centro (bosom)", bl.distribution_min.bosom_kg, "kg"),
        _kv("Lastre", "Mínimo: alas", bl.distribution_min.wings_kg, "kg"),
        _kv("Lastre", "Máximo: centro (bosom)", bl.distribution_max.bosom_kg, "kg"),
        _kv("Lastre", "Máximo: alas", bl.distribution_max.wings_kg, "kg"),
    ]
    return Table(
        key="flotacion_lastre",
        title="Flotación, boyas y lastre",
        columns=_kv_columns(),
        rows=tuple(rows),
        source="'Flotación y Lastre'!E2:J146, D153:I245",
    )


def warp_table(result: DesignResult) -> Table:
    """Cable de remolque: ángulos, diámetro por método, CD, cargas y selección."""
    w = result.warps
    sel = w.selection
    rows: list[tuple[Cell, ...]] = [
        _kv("Geometría", "Cable filado (Ls)", w.warp_m, "m"),
        _kv("Geometría", "Patentes + brida", w.sweeps_plus_bridle_m, "m"),
        _kv("Geometría", "DPA (A, triángulos semejantes)", w.dpa_a_m, "m"),
        _kv("Geometría", "DPA (B, triángulos semejantes)", w.dpa_b_m, "m"),
        _kv("Ángulos", "Declinación (δ1)", w.angles.declination_deg, "°"),
        _kv("Ángulos", "Divergencia (δ2)", w.angles.divergence_deg, "°"),
        _kv("Ángulos", "Divergencia de bridas (δ3)", w.angles.bridle_divergence_deg, "°"),
        _kv("Diámetro", "Ø por EHP (regla práctica)", w.diameter_ehp_mm, "mm"),
        _kv("Diámetro", "Ø Pérez Águila (buque de diseño)", w.diameter_aguila_mm, "mm"),
        _kv("Diámetro", "NHP de dimensionamiento", w.sizing_nhp_hp, "HP"),
        _kv("Diámetro", "Ø de diseño", w.diameter_mm, "mm"),
        _kv("Hidrodinámica", "CD del cable (Nomura–Yamazaki)", w.cd),
        _kv("Peso", "Peso en aire", w.weight.air_kg_m, "kg/m"),
        _kv("Peso", "Peso total en aire", w.weight.total_air_kg, "kg"),
        _kv("Peso", "Peso total en agua", w.weight.total_water_kg, "kg"),
        _kv("Cargas", "Carga de trabajo", w.loads.working_load_kgf, "kgf"),
        _kv("Cargas", "Factor de seguridad", w.loads.safety_factor),
        _kv("Cargas", "Rotura mínima requerida", w.loads.min_breaking_load_kgf, "kgf"),
        _kv("Selección", "Cable seleccionado", sel.id),
        _kv("Selección", "Construcción", sel.construction),
        _kv("Selección", "Ø seleccionado", sel.diameter_mm, "mm"),
        _kv("Selección", "Rotura del cable", sel.breaking_load_t, "t"),
        _kv("Selección", "Cumple la rotura mínima", "sí" if sel.satisfies_breaking_load else "no"),
        _kv("Selección", "Cable a comprar", w.quantity_m, "m"),
    ]
    return Table(
        key="cable",
        title="Cable de remolque",
        columns=_kv_columns(),
        rows=tuple(rows),
        source="'Cables de Remolque'!A1:H272; 'Cables Y Cabulleria'!D11:D12",
    )


def demand_table(result: DesignResult) -> Table:
    """Resistencia total a remolcar por velocidad: RN, RB, Rw, ROB y total (estándar/modificada)."""
    w = result.warps
    rows = tuple(
        (
            v,
            _f(result.drag.rn.std[i]),
            _f(result.drag.rn.mod[i]),
            _f(result.floats.drag_kgf[i]),
            _f(w.drag_kgf[i]),
            _at(result.doors.rig_drag_kgf, i),
            _f(w.total.std[i]),
            _f(w.total.mod[i]),
            _f(result.power.ft_kgf[i]),
        )
        for i, v in enumerate(_speeds(result))
    )
    rob_note = (
        "La resistencia total incluye ROB (modo corregido)."
        if result.case.compat.value == "corrected"
        else "Modo EXCEL: la resistencia total omite ROB (errata warp_total_omits_doors)."
    )
    return Table(
        key="demanda",
        title="Resistencia total a remolcar por velocidad",
        columns=(
            Column("speed_kn", "Velocidad", "kn"),
            Column("rn_std", "RN estándar", "kgf"),
            Column("rn_mod", "RN modificada", "kgf"),
            Column("rb", "RB boyas", "kgf"),
            Column("rw", "Rw cables", "kgf"),
            Column("rob", "ROB par de portones", "kgf"),
            Column("total_std", "Total estándar", "kgf"),
            Column("total_mod", "Total modificada", "kgf"),
            Column("ft", "FT disponible", "kgf"),
        ),
        rows=rows,
        note=rob_note,
        source="'Cables de Remolque'!G118:I126; 'Portones y aparejamiento'!D190:D198",
    )


def speed_window_table(result: DesignResult) -> Table:
    """Velocidad máxima y velocidades viables por propulsor y variante."""
    rows = []
    for key, win in result.performance.windows.items():
        prop, variant = key.rsplit("_", 1)
        feas = win.feasible_speeds_kn
        rows.append(
            (
                PROPELLER_LABELS.get(prop, prop),
                VARIANT_LABELS.get(variant, variant),
                _f(win.max_speed_kn),
                ", ".join(f"{v:g}" for v in feas) if feas else "ninguna",
                "sí" if key == result.performance.design_key else "",
            )
        )
    return Table(
        key="ventana_velocidad",
        title="Ventana de velocidad remolcable FT(v) ≥ R(v)",
        columns=(
            Column("propeller", "Propulsor"),
            Column("variant", "Red"),
            Column("max_speed_kn", "Velocidad máxima", "kn"),
            Column("feasible", "Velocidades viables", "kn"),
            Column("design", "Diseño"),
        ),
        rows=tuple(rows),
        note="Velocidad máxima: cruce FT = R interpolado linealmente.",
        source="'Potencia Disponible Arrastre OK'!L11:O19 frente a 'Cables de Remolque'!H118:I126",
    )


def errata_table(result: DesignResult) -> Table:
    """Erratas del libro original y su tratamiento en el modo de compatibilidad del caso."""
    from trawlkit.compat import ERRATA, Compat

    excel = result.case.compat is Compat.EXCEL
    rows = []
    for e in ERRATA:
        if e.key in ERRATA_FIXED_TREATMENT:
            status, how = ERRATA_FIXED_TREATMENT[e.key]
        elif excel:
            status, how = "reproducida", "Reproducida (EXCEL)."
        else:
            status, how = "corregida", "Corregida (CORRECTED)."
        rows.append((e.key, e.sheet, e.cell, e.description, status, how))
    return Table(
        key="erratas",
        title=f"Erratas del libro original (modo {result.case.compat.value})",
        columns=(
            Column("key", "Clave"),
            Column("sheet", "Hoja"),
            Column("cell", "Celda"),
            Column("description", "Descripción"),
            Column("status", "Estado"),
            Column("treatment", "Tratamiento"),
        ),
        rows=tuple(rows),
        source="trawlkit.compat.ERRATA; docs/erratas.md",
    )


def notes_table(result: DesignResult) -> Table:
    """Notas de la corrida (``DesignResult.notes``)."""
    return Table(
        key="notas",
        title="Notas de la corrida",
        columns=(Column("n", "N.º"), Column("note", "Nota")),
        rows=tuple((i, n) for i, n in enumerate(result.notes, 1)),
    )


def all_tables(result: DesignResult) -> list[Table]:
    """Todas las tablas del informe en orden (las de la red modificada sólo si existe)."""
    variants = ("std", "mod") if has_modified(result) else ("std",)
    out = [summary_table(result)]
    out += [panels_table(result, v) for v in variants]
    out.append(power_table(result))
    out += [drag_table(result, v) for v in variants]
    out += [
        demand_table(result),
        rigging_table(result),
        floats_ballast_table(result),
        warp_table(result),
        speed_window_table(result),
        errata_table(result),
        notes_table(result),
    ]
    return out
