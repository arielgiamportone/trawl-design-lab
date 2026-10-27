"""Etiquetas en español, unidades y formato de números para informes y CLI."""

from __future__ import annotations

from trawlkit.i18n import N_, t

#: Etiquetas en español y unidades de las claves de ``DesignResult.summary()``.
SUMMARY_LABELS: dict[str, tuple[str, str]] = {
    "net_id": (N_("Red"), ""),
    "vessel_id": (N_("Buque"), ""),
    "door_id": (N_("Portón"), ""),
    "compat": (N_("Modo de compatibilidad"), ""),
    "headrope_m": (N_("Lima"), "m"),
    "footrope_m": (N_("Burlón"), "m"),
    "cut_angle_deg": (N_("Ángulo de ataque de los cortes (α)"), "°"),
    "filtration_index": (N_("Índice de filtración (d/l)"), ""),
    "solid_surface_m2": (N_("Superficie sólida (Ss)"), "m²"),
    "working_surface_m2": (N_("Superficie de trabajo (St)"), "m²"),
    "net_weight_kg": (N_("Peso de la red"), "kg"),
    "vertical_opening_m": (N_("Abertura vertical (AV)"), "m"),
    "horizontal_opening_m": (N_("Abertura horizontal (AH)"), "m"),
    "working_depth_m": (N_("Profundidad de trabajo"), "m"),
    "flotation_total_kgf": (N_("Flotación total"), "kgf"),
    "dan_leno_m": (N_("Dan leno"), "m"),
    "sweeps_m": (N_("Patentes"), "m"),
    "crowfoot_m": (N_("Pies de gallo"), "m"),
    "crowfoot_extension_m": (N_("Alargue de pies de gallo"), "m"),
    "upper_bridle_m": (N_("Brida superior"), "m"),
    "lower_bridle_m": (N_("Brida inferior"), "m"),
    "warp_diameter_mm": (N_("Ø cable de remolque"), "mm"),
    "warp_length_m": (N_("Cable filado"), "m"),
    "float_count": (N_("Boyas"), "u"),
    "float_diameter_mm": (N_("Ø boya"), "mm"),
    "ballast_min_kg": (N_("Lastre mínimo"), "kg"),
    "ballast_max_kg": (N_("Lastre máximo"), "kg"),
    "warp_selected": (N_("Cable seleccionado"), ""),
    "warp_breaking_load_t": (N_("Rotura del cable seleccionado"), "t"),
    "warp_min_breaking_load_kgf": (N_("Rotura mínima requerida"), "kgf"),
    "warp_quantity_m": (N_("Cable a comprar"), "m"),
    "max_speed_kn": (N_("Velocidad máxima remolcable"), "kn"),
    "warp_tension_kgf": (N_("Tensión de cada cable a la velocidad de diseño"), "kgf"),
    "warp_stretch_m": (N_("Estiramiento elástico del cable"), "m"),
    "warp_safety_factor": (N_("Coeficiente de seguridad del cable"), ""),
    # Fase 19.5: tangones, gemelo y vara.
    "rig": (N_("Aparejo"), ""),
    "n_nets": (N_("Redes del aparejo"), "u"),
    "net_spread_m": (N_("Separación de los puntos de remolque de cada red"), "m"),
    "door_spread_total_m": (N_("Separación entre portones exteriores"), "m"),
    "swept_width_m": (N_("Ancho barrido total"), "m"),
    "beam_length_m": (N_("Largo de cada vara"), "m"),
    "boom_tip_offset_m": (N_("Punta del tangón desde la crujía"), "m"),
    "nets_gap_m": (N_("Huelgo entre las redes"), "m"),
    "clump_weight_kg": (N_("Peso del muerto central"), "kg"),
}


def label(key: str) -> tuple[str, str]:
    """Etiqueta (en el idioma activo) y unidad de una clave de ``DesignResult.summary()``."""
    if key in SUMMARY_LABELS:
        name, unit = SUMMARY_LABELS[key]
        return (t(name), unit)
    if key.startswith("rn_std_"):
        return (t("RN estándar a {speed}", speed=key[7:-4].replace("_", ".")), "kgf")
    if key.startswith("rob_"):
        return (t("ROB a {speed}", speed=key[4:-4].replace("_", ".")), "kgf")
    if key.startswith("net_total_"):
        speed = key[10:-4].replace("_", ".")
        return (t("Una red con su aparejo a {speed}", speed=speed), "kgf")
    if key.startswith("total_drag_"):
        speed = key[11:-4].replace("_", ".")
        return (t("Resistencia de todo el arte a {speed}", speed=speed), "kgf")
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
    lines = [f"| {t('Magnitud')} | {t('Valor')} | {t('Unidad')} |", "|---|---|---|"]
    for key, value in summary.items():
        name, unit = label(key)
        lines.append(f"| {name} | {fmt(value)} | {unit} |")
    return "\n".join(lines)
