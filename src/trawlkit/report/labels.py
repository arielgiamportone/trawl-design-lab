"""Etiquetas en español, unidades y formato de números para informes y CLI."""

from __future__ import annotations

#: Etiquetas en español y unidades de las claves de ``DesignResult.summary()``.
SUMMARY_LABELS: dict[str, tuple[str, str]] = {
    "net_id": ("Red", ""),
    "vessel_id": ("Buque", ""),
    "door_id": ("Portón", ""),
    "compat": ("Modo de compatibilidad", ""),
    "headrope_m": ("Lima", "m"),
    "footrope_m": ("Burlón", "m"),
    "cut_angle_deg": ("Ángulo de ataque de los cortes (α)", "°"),
    "filtration_index": ("Índice de filtración (d/l)", ""),
    "solid_surface_m2": ("Superficie sólida (Ss)", "m²"),
    "working_surface_m2": ("Superficie de trabajo (St)", "m²"),
    "net_weight_kg": ("Peso de la red", "kg"),
    "vertical_opening_m": ("Abertura vertical (AV)", "m"),
    "horizontal_opening_m": ("Abertura horizontal (AH)", "m"),
    "working_depth_m": ("Profundidad de trabajo", "m"),
    "flotation_total_kgf": ("Flotación total", "kgf"),
    "dan_leno_m": ("Dan leno", "m"),
    "sweeps_m": ("Patentes", "m"),
    "crowfoot_m": ("Pies de gallo", "m"),
    "crowfoot_extension_m": ("Alargue de pies de gallo", "m"),
    "upper_bridle_m": ("Brida superior", "m"),
    "lower_bridle_m": ("Brida inferior", "m"),
    "warp_diameter_mm": ("Ø cable de remolque", "mm"),
    "warp_length_m": ("Cable filado", "m"),
    "float_count": ("Boyas", "u"),
    "float_diameter_mm": ("Ø boya", "mm"),
    "ballast_min_kg": ("Lastre mínimo", "kg"),
    "ballast_max_kg": ("Lastre máximo", "kg"),
    "warp_selected": ("Cable seleccionado", ""),
    "warp_breaking_load_t": ("Rotura del cable seleccionado", "t"),
    "warp_min_breaking_load_kgf": ("Rotura mínima requerida", "kgf"),
    "warp_quantity_m": ("Cable a comprar", "m"),
    "max_speed_kn": ("Velocidad máxima remolcable", "kn"),
}


def label(key: str) -> tuple[str, str]:
    """Etiqueta en español y unidad de una clave de ``DesignResult.summary()``."""
    if key in SUMMARY_LABELS:
        return SUMMARY_LABELS[key]
    if key.startswith("rn_std_"):
        return (f"RN estándar a {key[7:-4].replace('_', '.')}", "kgf")
    if key.startswith("rob_"):
        return (f"ROB a {key[4:-4].replace('_', '.')}", "kgf")
    return (key, "")


def fmt(value: float | str | None) -> str:
    """Formatea un valor con 4-5 cifras significativas (enteros sin decimales, None → —)."""
    if value is None:
        return "—"
    if isinstance(value, str):
        return value
    if float(value).is_integer():
        return f"{int(value)}"
    return f"{value:.4g}" if abs(value) < 1 else f"{value:.5g}"


def summary_markdown(summary: dict[str, float | str | None]) -> str:
    """Tabla Markdown (etiquetas en español, unidades) de ``DesignResult.summary()``."""
    lines = ["| Magnitud | Valor | Unidad |", "|---|---|---|"]
    for key, value in summary.items():
        name, unit = label(key)
        lines.append(f"| {name} | {fmt(value)} | {unit} |")
    return "\n".join(lines)
