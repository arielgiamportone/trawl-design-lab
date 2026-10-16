"""Extrae valores de referencia (golden values) del libro Excel heredado.

Lee ``legacy/Calculos_Red_FAO_A3.xlsx`` con ``openpyxl`` en modo ``data_only=True`` (valores
cacheados por Excel) y escribe un JSON por hoja en ``tests/golden/``::

    {
      "sheet": "Resistencia de la RED",
      "generated_by": "tools/extract/golden.py",
      "values": {"<key>": {"cell": "N302", "value": 0.42, "label": "...", "unit": "t"}},
      "series": {"<key>": {"x": "speed_kn", "x_values": [...], "cells": "N302:N310",
                            "values": [...], "unit": "t"}}
    }

Las claves son ``snake_case`` en inglés y estables: los tests del motor de cálculo las
referencian. Las celdas vacías o con error (``#N/A``, ``#REF!``…) se omiten y se registran.

Uso: ``uv run python -m tools.extract.golden``.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tools.extract.common import GOLDEN, XLSX, rows, workbook

log = logging.getLogger("tools.extract.golden")

GENERATED_BY = "tools/extract/golden.py"
SOURCE = "legacy/Calculos_Red_FAO_A3.xlsx"

#: Vector de velocidades usado por todas las tablas indexadas por velocidad (nudos).
SPEED_KN: list[float] = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]

_NUMERIC_TEXT = re.compile(r"^\s*-?\d+(\.\d+)?\s*$")


@dataclass(frozen=True)
class V:
    """Un valor escalar a extraer."""

    cell: str
    label: str
    unit: str = ""
    static: bool = False


@dataclass(frozen=True)
class S:
    """Una serie (rango de una columna o fila) a extraer."""

    cells: str
    label: str
    unit: str = ""
    x: str = "speed_kn"
    x_values: list[Any] | None = field(default_factory=lambda: list(SPEED_KN))
    x_cells: str | None = None
    static: bool = False


Spec = tuple[dict[str, V], dict[str, S]]


# --------------------------------------------------------------------------------------
# Helpers para construir especificaciones repetitivas
# --------------------------------------------------------------------------------------


def _col_series(col: str, r0: int, r1: int, label: str, unit: str, **kw: Any) -> S:
    return S(f"{col}{r0}:{col}{r1}", label, unit, **kw)


def _speed(col: str, r0: int, label: str, unit: str = "t", **kw: Any) -> S:
    """Serie de 9 filas (1.0–5.0 kn) que empieza en ``col``+``r0``."""
    return _col_series(col, r0, r0 + 8, label, unit, **kw)


def _panel_series(cells: str, label: str, unit: str, x_cells: str) -> S:
    return S(cells, label, unit, x="panel", x_values=None, x_cells=x_cells)


# --------------------------------------------------------------------------------------
# Especificación por hoja
# --------------------------------------------------------------------------------------

ESPECIE: Spec = (
    {
        "species_common_name": V("C3", "Target species, common name"),
        "species_scientific_name": V("H3", "Target species, scientific name"),
        "species_depth_m": V("E5", "Working depth where the species is found", "m"),
        "species_bottom_type": V("E6", "Bottom type"),
    },
    {},
)

BUQUES: Spec = (
    {
        "vessel_class": V("A1", "Vessel class heading (150–180 BHP)"),
        "vessel_type_description": V("A3", "Vessel type 1 description"),
        "vessel_loa_note": V("B4", "Length overall note"),
        "vessel_beam_m": V("B5", "Beam", "m"),
        "vessel_depth_m": V("B6", "Moulded depth (puntal)", "m"),
    },
    {},
)


def _power_budget(suffix: str, r0: int, h_row: int) -> dict[str, V]:
    names = [
        ("nominal_hp", "Nominal HP = BHP × 1.33"),
        ("bhp", "Brake horsepower at propeller"),
        ("towing_hp", "HP available for towing the net (33 %)"),
        ("propeller_loss_hp", "Loss turning the propeller (35 %)"),
        ("wave_loss_hp", "Wave-making loss (27 %)"),
        ("friction_loss_hp", "Hull friction loss (18 %)"),
        ("wake_loss_hp", "Wake and turbulence loss (17 %)"),
        ("air_loss_hp", "Air resistance loss (3 %)"),
    ]
    out: dict[str, V] = {}
    for i, (k, lab) in enumerate(names):
        out[f"{k}_{suffix}"] = V(f"C{r0 + i}", f"{lab}, {suffix} BHP vessel", "hp")
        kw_key = k.removesuffix("_hp") + "_kw"
        out[f"{kw_key}_{suffix}"] = V(f"E{r0 + i}", f"{lab}, {suffix} BHP vessel", "kW")
    out[f"admiralty_speed_{suffix}"] = V(
        f"H{h_row}", f"Admiralty-formula speed, {suffix} BHP vessel", "kn"
    )
    return out


POTENC: Spec = ({**_power_budget("150", 24, 27), **_power_budget("180", 36, 38)}, {})


def _prado_fishing_cols(r0: int, spec: list[tuple[str, str, str]]) -> dict[str, S]:
    return {
        key: _speed(col, r0, f"Prado/Dremiere bollard pull when fishing, {lab}", "kgf")
        for col, key, lab in spec
    }


_PRADO_A = [
    ("C", "prado_bpf_fixed_high_rpm_150_kgf", "fixed pitch high RPM (K=0.20), 150 HP"),
    ("D", "prado_bpf_fixed_high_rpm_180_kgf", "fixed pitch high RPM (K=0.20), 180 HP"),
    ("E", "prado_bpf_fixed_low_rpm_k25_150_kgf", "fixed pitch low RPM K=0.25, 150 HP"),
    ("F", "prado_bpf_fixed_low_rpm_k25_180_kgf", "fixed pitch low RPM K=0.25, 180 HP"),
    ("G", "prado_bpf_fixed_low_rpm_k28_150_kgf", "fixed pitch low RPM K=0.28, 150 HP"),
    ("H", "prado_bpf_fixed_low_rpm_k28_180_kgf", "fixed pitch low RPM K=0.28, 180 HP"),
    ("I", "prado_bpf_fixed_nozzle_high_rpm_150_kgf", "fixed pitch + nozzle high RPM, 150 HP"),
    ("J", "prado_bpf_fixed_nozzle_high_rpm_180_kgf", "fixed pitch + nozzle high RPM, 180 HP"),
    ("K", "prado_bpf_fixed_nozzle_low_rpm_k25_150_kgf", "fixed + nozzle low RPM K=0.25, 150 HP"),
    ("L", "prado_bpf_fixed_nozzle_low_rpm_k25_180_kgf", "fixed + nozzle low RPM K=0.25, 180 HP"),
]
_PRADO_B = [
    ("C", "prado_bpf_fixed_nozzle_low_rpm_k28_150_kgf", "fixed + nozzle low RPM K=0.28, 150 HP"),
    ("D", "prado_bpf_fixed_nozzle_low_rpm_k28_180_kgf", "fixed + nozzle low RPM K=0.28, 180 HP"),
    ("E", "prado_bpf_variable_k28_150_kgf", "variable pitch K=0.28, 150 HP"),
    ("F", "prado_bpf_variable_k28_180_kgf", "variable pitch K=0.28, 180 HP"),
    ("G", "prado_bpf_variable_k30_150_kgf", "variable pitch K=0.30, 150 HP"),
    ("H", "prado_bpf_variable_k30_180_kgf", "variable pitch K=0.30, 180 HP"),
    ("I", "prado_bpf_variable_nozzle_k28_150_kgf", "variable pitch + nozzle K=0.28, 150 HP"),
    ("J", "prado_bpf_variable_nozzle_k28_180_kgf", "variable pitch + nozzle K=0.28, 180 HP"),
    ("K", "prado_bpf_variable_nozzle_k30_150_kgf", "variable pitch + nozzle K=0.30, 150 HP"),
    ("L", "prado_bpf_variable_nozzle_k30_180_kgf", "variable pitch + nozzle K=0.30, 180 HP"),
]


def _summary_block(tag: str, r0: int, label: str, nomura_note: str) -> dict[str, S]:
    """Tablas resumen de fuerza disponible (filas 300+, 319+, 342+, 362+)."""
    return {
        f"summary_{tag}_fridman_kgf": _speed(
            "D", r0, f"Summary {label}: Fridman FT (pasted static)", "kgf", static=True
        ),
        f"summary_{tag}_prado_kgf": _speed(
            "E", r0, f"Summary {label}: Prado/Dremiere BPF (pasted static)", "kgf", static=True
        ),
        f"summary_{tag}_koyama_kgf": _speed(
            "F", r0, f"Summary {label}: Koyama (pasted static)", "kgf", static=True
        ),
        f"summary_{tag}_nomura_kgf": _speed(
            "G", r0, f"Summary {label}: column headed Nomura ({nomura_note})", "kgf"
        ),
        f"summary_{tag}_hamuro_kgf": _speed(
            "H", r0, f"Summary {label}: Hamuro (pasted static)", "kgf", static=True
        ),
        f"summary_{tag}_average_kgf": _speed(
            "I", r0, f"Summary {label}: average of the five methods", "kgf"
        ),
    }


POTENCIA_OK: Spec = (
    {
        "fridman_kf_fixed_pitch": V(
            "D10", "Fridman empirical KF, fixed-pitch propeller (MID of E3)"
        ),
        "fridman_kf_variable_pitch_nozzle": V(
            "F10", "Fridman empirical KF, variable pitch + nozzle (MID of E4)"
        ),
        "bhp_150": V("C10", "BHP of the 150 HP vessel", "hp"),
        "bhp_180": V("C22", "BHP of the 180 HP vessel", "hp"),
        # Prado / Dremiere bollard pull
        "prado_k_fixed_150": V("K52", "Prado K factor, fixed pitch, 150 HP"),
        "prado_k_fixed_180": V("L52", "Prado K factor, fixed pitch, 180 HP"),
        "prado_k_fixed_nozzle_150": V("K53", "Prado K factor, fixed pitch + nozzle, 150 HP"),
        "prado_k_fixed_nozzle_180": V("L53", "Prado K factor, fixed pitch + nozzle, 180 HP"),
        "prado_k_variable_150": V("K54", "Prado K factor, variable pitch, 150 HP"),
        "prado_k_variable_180": V("L54", "Prado K factor, variable pitch, 180 HP"),
        "prado_k_variable_nozzle_150": V("K55", "Prado K factor, variable pitch + nozzle, 150 HP"),
        "prado_k_variable_nozzle_180": V("L55", "Prado K factor, variable pitch + nozzle, 180 HP"),
        "bollard_pull_fixed_150_kgf": V("B60", "Bollard pull BHP·0.9·1.10/100, 150 HP", "kgf"),
        "bollard_pull_fixed_nozzle_150_kgf": V("B61", "Bollard pull ·1.20, 150 HP", "kgf"),
        "bollard_pull_variable_150_kgf": V("B62", "Bollard pull ·1.25, 150 HP", "kgf"),
        "bollard_pull_variable_nozzle_150_kgf": V("B63", "Bollard pull ·1.40, 150 HP", "kgf"),
        "bollard_pull_fixed_150_t": V("C60", "Bollard pull fixed pitch, 150 HP", "t"),
        "bollard_pull_fixed_nozzle_150_t": V("C61", "Bollard pull fixed + nozzle, 150 HP", "t"),
        "bollard_pull_variable_150_t": V("C62", "Bollard pull variable pitch, 150 HP", "t"),
        "bollard_pull_variable_nozzle_150_t": V(
            "C63", "Bollard pull variable + nozzle, 150 HP", "t"
        ),
        "bollard_pull_fixed_180_kgf": V("D60", "Bollard pull BHP·0.9·1.10/100, 180 HP", "kgf"),
        "bollard_pull_fixed_nozzle_180_kgf": V("D61", "Bollard pull ·1.20, 180 HP", "kgf"),
        "bollard_pull_variable_180_kgf": V("D62", "Bollard pull ·1.25, 180 HP", "kgf"),
        "bollard_pull_variable_nozzle_180_kgf": V("D63", "Bollard pull ·1.40, 180 HP", "kgf"),
        "bollard_pull_fixed_180_t": V("E60", "Bollard pull fixed pitch, 180 HP", "t"),
        "bollard_pull_fixed_nozzle_180_t": V("E61", "Bollard pull fixed + nozzle, 180 HP", "t"),
        "bollard_pull_variable_180_t": V("E62", "Bollard pull variable pitch, 180 HP", "t"),
        "bollard_pull_variable_nozzle_180_t": V(
            "E63", "Bollard pull variable + nozzle, 180 HP", "t"
        ),
        "bollard_pull_k_fixed_150_t": V("I59", "Bollard pull via K factor, fixed, 150 HP", "t"),
        "bollard_pull_k_fixed_nozzle_150_t": V("I60", "Via K factor, fixed + nozzle, 150 HP", "t"),
        "bollard_pull_k_variable_150_t": V("I61", "Via K factor, variable, 150 HP", "t"),
        "bollard_pull_k_variable_nozzle_150_t": V("I62", "Via K, variable + nozzle, 150 HP", "t"),
        "bollard_pull_k_fixed_180_t": V("K59", "Bollard pull via K factor, fixed, 180 HP", "t"),
        "bollard_pull_k_fixed_nozzle_180_t": V("K60", "Via K factor, fixed + nozzle, 180 HP", "t"),
        "bollard_pull_k_variable_180_t": V("K61", "Via K factor, variable, 180 HP", "t"),
        "bollard_pull_k_variable_nozzle_180_t": V("K62", "Via K, variable + nozzle, 180 HP", "t"),
        "bollard_pull_avg_fixed_150_kgf": V("G58", "Average bollard pull, fixed, 150 HP", "kgf"),
        "bollard_pull_avg_fixed_nozzle_150_kgf": V("G59", "Average, fixed + nozzle, 150 HP", "kgf"),
        "bollard_pull_avg_variable_150_kgf": V("G60", "Average, variable, 150 HP", "kgf"),
        "bollard_pull_avg_variable_nozzle_150_kgf": V(
            "G61", "Average, variable + nozzle, 150 HP", "kgf"
        ),
        "bollard_pull_avg_fixed_180_kgf": V("G65", "Average bollard pull, fixed, 180 HP", "kgf"),
        "bollard_pull_avg_fixed_nozzle_180_kgf": V("G66", "Average, fixed + nozzle, 180 HP", "kgf"),
        "bollard_pull_avg_variable_180_kgf": V("G67", "Average, variable, 180 HP", "kgf"),
        "bollard_pull_avg_variable_nozzle_180_kgf": V(
            "G68", "Average, variable + nozzle, 180 HP", "kgf"
        ),
        "apn_fixed_150_hp": V("B73", "Apparent nominal power = 0.09·BP, fixed, 150 HP", "hp"),
        "apn_fixed_nozzle_150_hp": V("B74", "APN, fixed + nozzle, 150 HP", "hp"),
        "apn_variable_150_hp": V("B75", "APN, variable, 150 HP", "hp"),
        "apn_variable_nozzle_150_hp": V("B76", "APN, variable + nozzle, 150 HP", "hp"),
        "apn_fixed_180_hp": V("C73", "Apparent nominal power = 0.09·BP, fixed, 180 HP", "hp"),
        "apn_fixed_nozzle_180_hp": V("C74", "APN, fixed + nozzle, 180 HP", "hp"),
        "apn_variable_180_hp": V("C75", "APN, variable, 180 HP", "hp"),
        "apn_variable_nozzle_180_hp": V("C76", "APN, variable + nozzle, 180 HP", "hp"),
        "trawling_power_fixed_high_rpm_150_hp": V("K68", "0.75·0.20·APN, fixed high RPM", "hp"),
        "trawling_power_fixed_low_rpm_k25_150_hp": V("K69", "0.75·0.25·APN, fixed low RPM", "hp"),
        "trawling_power_fixed_low_rpm_k28_150_hp": V("K70", "0.75·0.28·APN, fixed low RPM", "hp"),
        "trawling_power_fixed_nozzle_high_rpm_150_hp": V(
            "K71", "0.75·0.20·APN, fixed+nozzle", "hp"
        ),
        "trawling_power_fixed_nozzle_low_rpm_k25_150_hp": V("K72", "0.75·0.25·APN", "hp"),
        "trawling_power_fixed_nozzle_low_rpm_k28_150_hp": V("K73", "0.75·0.28·APN", "hp"),
        "trawling_power_variable_k28_150_hp": V("K74", "0.75·0.28·APN, variable", "hp"),
        "trawling_power_variable_k30_150_hp": V("K75", "0.75·0.30·APN, variable", "hp"),
        "trawling_power_variable_nozzle_k28_150_hp": V("K76", "0.75·0.28·APN, var+nozzle", "hp"),
        "trawling_power_variable_nozzle_k30_150_hp": V("K77", "0.75·0.30·APN, var+nozzle", "hp"),
        "trawling_power_fixed_high_rpm_180_hp": V("L68", "0.75·0.20·APN, fixed high RPM", "hp"),
        "trawling_power_fixed_low_rpm_k25_180_hp": V("L69", "0.75·0.25·APN, fixed low RPM", "hp"),
        "trawling_power_fixed_low_rpm_k28_180_hp": V("L70", "0.75·0.28·APN, fixed low RPM", "hp"),
        "trawling_power_fixed_nozzle_high_rpm_180_hp": V(
            "L71", "0.75·0.20·APN, fixed+nozzle", "hp"
        ),
        "trawling_power_fixed_nozzle_low_rpm_k25_180_hp": V("L72", "0.75·0.25·APN", "hp"),
        "trawling_power_fixed_nozzle_low_rpm_k28_180_hp": V("L73", "0.75·0.28·APN", "hp"),
        "trawling_power_variable_k28_180_hp": V("L74", "0.75·0.28·APN, variable", "hp"),
        "trawling_power_variable_k30_180_hp": V("L75", "0.75·0.30·APN, variable", "hp"),
        "trawling_power_variable_nozzle_k28_180_hp": V("L76", "0.75·0.28·APN, var+nozzle", "hp"),
        "trawling_power_variable_nozzle_k30_180_hp": V("L77", "0.75·0.30·APN, var+nozzle", "hp"),
        # Koyama
        "koyama_bhp_f_150_hp": V("C169", "Koyama BHP_F = 60 % BHP, 150 HP", "hp"),
        "koyama_bhp_f_180_hp": V("D169", "Koyama BHP_F = 60 % BHP, 180 HP", "hp"),
        "koyama_k": V("C170", "Koyama K constant (15–55 t, <600 BHP)"),
        "koyama_ehp_150_hp": V("C171", "Koyama EHP = K·BHP_F, 150 HP", "hp"),
        "koyama_ehp_180_hp": V("D171", "Koyama EHP = K·BHP_F, 180 HP", "hp"),
        "koyama_ehp_150_kgf_m_s": V("C172", "Koyama EHP ·75, 150 HP", "kgf·m/s"),
        "koyama_ehp_180_kgf_m_s": V("D172", "Koyama EHP ·75, 180 HP", "kgf·m/s"),
        # Nomura
        "nomura_k1_engine_use": V("L205", "Nomura K1 main-engine utilisation"),
        "nomura_k2_sea_state": V("L206", "Nomura K2 sea state"),
        "nomura_k3_medium_trawlers": V("L209", "Nomura K3 propulsion efficiency, medium trawlers"),
        "nomura_k3_average": V("L212", "Nomura K3 average over vessel classes"),
        "nomura_net_drag_share": V("L213", "Nomura net drag share of total (estimated)"),
        # Hamuro
        "hamuro_k1": V("C254", "Hamuro K1 (82.5 % of NHP)"),
        "hamuro_ps_fixed_low_rpm_150_hp": V("F259", "Hamuro Ps, PF RPM<300, 150 HP", "hp"),
        "hamuro_ps_fixed_high_rpm_150_hp": V("G259", "Hamuro Ps, PF RPM>300, 150 HP", "hp"),
        "hamuro_ps_fixed_nozzle_high_rpm_150_hp": V("H259", "Hamuro Ps, PF+T RPM>300, 150", "hp"),
        "hamuro_ps_fixed_nozzle_low_rpm_150_hp": V("I259", "Hamuro Ps, PF+T RPM<300, 150", "hp"),
        "hamuro_ps_variable_high_rpm_150_hp": V("J259", "Hamuro Ps, PV RPM>300, 150 HP", "hp"),
        "hamuro_ps_variable_nozzle_low_rpm_150_hp": V("K259", "Hamuro Ps, PV+T RPM<300, 150", "hp"),
        "hamuro_ps_variable_nozzle_high_rpm_150_hp": V(
            "L259", "Hamuro Ps, PV+T RPM>300, 150", "hp"
        ),
        "hamuro_ps_worst_avg_150_hp": V("G260", "Hamuro Ps worst-case average, 150 HP", "hp"),
        "hamuro_ps_best_avg_150_hp": V("K260", "Hamuro Ps best-case average, 150 HP", "hp"),
        "hamuro_ps_fixed_low_rpm_180_hp": V("F266", "Hamuro Ps, PF RPM<300, 180 HP", "hp"),
        "hamuro_ps_fixed_high_rpm_180_hp": V("G266", "Hamuro Ps, PF RPM>300, 180 HP", "hp"),
        "hamuro_ps_fixed_nozzle_high_rpm_180_hp": V("H266", "Hamuro Ps, PF+T RPM>300, 180", "hp"),
        "hamuro_ps_fixed_nozzle_low_rpm_180_hp": V("I266", "Hamuro Ps, PF+T RPM<300, 180", "hp"),
        "hamuro_ps_variable_high_rpm_180_hp": V("J266", "Hamuro Ps, PV RPM>300, 180 HP", "hp"),
        "hamuro_ps_variable_nozzle_low_rpm_180_hp": V("K266", "Hamuro Ps, PV+T RPM<300, 180", "hp"),
        "hamuro_ps_variable_nozzle_high_rpm_180_hp": V(
            "L266", "Hamuro Ps, PV+T RPM>300, 180", "hp"
        ),
        "hamuro_ps_worst_avg_180_hp": V("G267", "Hamuro Ps worst-case average, 180 HP", "hp"),
        "hamuro_ps_best_avg_180_hp": V("K267", "Hamuro Ps best-case average, 180 HP", "hp"),
    },
    {
        "speed_ms": S("H171:H179", "Speed in m/s (Koyama block)", "m/s"),
        "fridman_ft_fixed_pitch_150_kgf": _speed(
            "E", 10, "Fridman FT = HP·(KF − 0.7·v), fixed pitch, 150 HP", "kgf"
        ),
        "fridman_ft_variable_pitch_nozzle_150_kgf": _speed(
            "G", 10, "Fridman FT, variable pitch + nozzle, 150 HP", "kgf"
        ),
        "fridman_ft_fixed_pitch_180_kgf": _speed(
            "E", 22, "Fridman FT = HP·(KF − 0.7·v), fixed pitch, 180 HP", "kgf"
        ),
        "fridman_ft_variable_pitch_nozzle_180_kgf": _speed(
            "G", 22, "Fridman FT, variable pitch + nozzle, 180 HP", "kgf"
        ),
        "rn_std_kgf": _speed("J", 11, "RN FAO A3 standard net (Aberdeen demersal) ×1000", "kgf"),
        "rn_mod_kgf": _speed("K", 11, "RN FAO A3 modified net (Aberdeen demersal) ×1000", "kgf"),
        "fridman_summary_fixed_150_kgf": _speed("L", 11, "Summary FT(PF) 150 HP (=E10:E18)", "kgf"),
        "fridman_summary_variable_nozzle_150_kgf": _speed(
            "M", 11, "Summary FT(PV+T) 150 HP (=G10:G18)", "kgf"
        ),
        "fridman_summary_fixed_180_kgf": _speed("N", 11, "Summary FT(PF) 180 HP (=E22:E30)", "kgf"),
        "fridman_summary_variable_nozzle_180_kgf": _speed(
            "O", 11, "Summary FT(PV+T) 180 HP (=G22:G30)", "kgf"
        ),
        **_prado_fishing_cols(88, _PRADO_A),
        **_prado_fishing_cols(103, _PRADO_B),
        "prado_bpf_avg_fixed_150_kgf": _speed(
            "C", 123, "Prado BPF average, fixed pitch variants, 150 HP", "kgf"
        ),
        "prado_bpf_avg_fixed_180_kgf": _speed(
            "D", 123, "Prado BPF average, fixed pitch variants, 180 HP", "kgf"
        ),
        "prado_bpf_avg_variable_150_kgf": _speed(
            "E", 123, "Prado BPF average, variable pitch variants, 150 HP", "kgf"
        ),
        "prado_bpf_avg_variable_180_kgf": _speed(
            "F", 123, "Prado BPF average, variable pitch variants, 180 HP", "kgf"
        ),
        "koyama_pull_150_kgf": _speed(
            "K", 171, "Koyama pull = EHP[kgf·m/s] / v[m/s], 150 HP", "kgf"
        ),
        "koyama_pull_180_kgf": _speed(
            "L", 171, "Koyama pull = EHP[kgf·m/s] / v[m/s], 180 HP", "kgf"
        ),
        "nomura_pull_150_kgf": _speed(
            "E", 216, "Nomura pull = 0.8·K1·K2·K3·75·NHP / v, 150 HP", "kgf"
        ),
        "nomura_pull_180_kgf": _speed(
            "F", 216, "Nomura pull = 0.8·K1·K2·K3·75·NHP / v, 180 HP", "kgf"
        ),
        "hamuro_pull_fixed_150_kgf": _speed("E", 272, "Hamuro pull = 75·Ps / v, PF, 150 HP", "kgf"),
        "hamuro_pull_variable_nozzle_150_kgf": _speed(
            "F", 272, "Hamuro pull = 75·Ps / v, PV+T, 150 HP", "kgf"
        ),
        "hamuro_pull_fixed_180_kgf": _speed("G", 272, "Hamuro pull = 75·Ps / v, PF, 180 HP", "kgf"),
        "hamuro_pull_variable_nozzle_180_kgf": _speed(
            "H", 272, "Hamuro pull = 75·Ps / v, PV+T, 180 HP", "kgf"
        ),
        **_summary_block("worst_150", 300, "worst case 150 HP", "=E216 Nomura 150"),
        **_summary_block("best_150", 319, "best case 150 HP", "=F272 Hamuro PV+T 150, mislinked"),
        **_summary_block("worst_180", 342, "worst case 180 HP", "=G272 Hamuro PF 180, mislinked"),
        **_summary_block("best_180", 362, "best case 180 HP", "=H272 Hamuro PV+T 180, mislinked"),
    },
)


def _netting_spec(
    name: str,
    r0: int,
    side: str,
    area: str,
    meshes: str,
    cuts: list[tuple[str, str, str, str]],
    count: str | None,
) -> dict[str, V]:
    """Bloque de un paño: largos estirados, área, nº de mallas, cortes y cantidad.

    ``side`` = "L" para la mitad izquierda de la hoja (cols A–L) o "R" (cols M–X).
    """
    len_col = "I" if side == "L" else "U"
    rows_t2, rows_t1, rows_n = (r0, r0 + 1, r0 + 2)
    out = {
        f"{name}_stretched_t2_m": V(f"{len_col}{rows_t2}", f"{name}: stretched length b (T2)", "m"),
        f"{name}_stretched_t1_m": V(f"{len_col}{rows_t1}", f"{name}: stretched length a (T1)", "m"),
        f"{name}_stretched_n_m": V(f"{len_col}{rows_n}", f"{name}: stretched depth h (N)", "m"),
        f"{name}_working_area_m2": V(area, f"{name}: working area U1·U2·((T1+T2)/2)·N·mL²", "m²"),
        f"{name}_mesh_count": V(meshes, f"{name}: number of meshes ((T1+T2−1)·(N−0.5))+0.5"),
    }
    for tag, mcell, rcell, ccell in cuts:
        out[f"{name}_cut_{tag}_meshes"] = V(mcell, f"{name}: cut {tag} meshes to add/remove")
        out[f"{name}_cut_{tag}_ratio"] = V(rcell, f"{name}: cut {tag} ratio (RC)")
        out[f"{name}_cut_{tag}_code"] = V(ccell, f"{name}: cut {tag} code (VLOOKUP)")
    if count:
        out[f"{name}_panel_count"] = V(count, f"{name}: number of panels (COUNTIF)")
    return out


def _twine_density_key(name: str, cell: str) -> dict[str, V]:
    return {f"{name}_twine_density_kg_m3": V(cell, f"{name}: twine density (L55-style)", "kg/m³")}


# Panel A rows 55-57 use the wrong T1/T2 order in the Excel: I55 is the 'b (T2)' row.
PANOS: Spec = (
    {
        "netting_80mm_twine_mm": V("C5", "Twine diameter, 80 mm mesh netting", "mm"),
        "netting_80mm_mesh_mm": V("C6", "Stretched mesh size, wings", "mm"),
        "netting_80mm_rtex": V("C7", "Rtex, 80 mm netting", "tex"),
        "netting_80mm_t_meshes": V("C3", "Meshes per unit length T (mallas en T)"),
        "netting_80mm_n_meshes": V("C4", "Meshes per unit depth N"),
        "netting_60mm_twine_mm": V("C15", "Twine diameter, 60 mm netting", "mm"),
        "netting_60mm_mesh_mm": V("C16", "Stretched mesh size, square/body", "mm"),
        "netting_60mm_rtex": V("C17", "Rtex, 60 mm netting", "tex"),
        "netting_40mm_body_twine_mm": V("O5", "Twine diameter, 40 mm body netting", "mm"),
        "netting_40mm_body_mesh_mm": V("O6", "Stretched mesh size, 40 mm body netting", "mm"),
        "netting_40mm_body_rtex": V("O7", "Rtex, 40 mm body netting", "tex"),
        "netting_40mm_bag_twine_mm": V("O21", "Twine diameter, 40 mm codend", "mm"),
        "netting_40mm_bag_mesh_mm": V("O22", "Stretched mesh size, standard codend", "mm"),
        "netting_40mm_bag_rtex": V("O23", "Rtex, standard codend", "tex"),
        "netting_30mm_twine_mm": V("C26", "Twine diameter, 30 mm crustacean codend", "mm"),
        "netting_30mm_mesh_mm": V("C27", "Stretched mesh size, modified codend", "mm"),
        "netting_30mm_rtex": V("C28", "Rtex, modified codend", "tex"),
        "panel_a_runnage_m_kg": V("A55", "Panel A: runnage 1e6/Rtex", "m/kg"),
        **_twine_density_key("panel_a", "L55"),
        **_netting_spec(
            "panel_a",
            55,
            "L",
            "A61",
            "A64",
            [("x1", "G63", "H63", "I63"), ("x2", "G64", "H64", "I64")],
            "N62",
        ),
        **_netting_spec(
            "panel_b",
            54,
            "R",
            "M60",
            "M63",
            [("x1", "R62", "S62", "T62"), ("x2", "R63", "S63", "T63")],
            None,
        ),
        **_netting_spec(
            "panel_c",
            90,
            "L",
            "A96",
            "A99",
            [("x1", "F97", "G97", "H97"), ("x2", "F98", "G98", "H98")],
            "B97",
        ),
        **_netting_spec(
            "panel_d",
            89,
            "R",
            "M95",
            "M98",
            [("x1", "R97", "S97", "T97"), ("x2", "R98", "S98", "T98")],
            "N97",
        ),
        **_netting_spec(
            "panel_e", 120, "L", "A126", "A129", [("x1", "F127", "G127", "H127")], "B127"
        ),
        **_netting_spec(
            "panel_f",
            114,
            "R",
            "M120",
            "M123",
            [("x1", "R122", "S122", "T122"), ("x2", "R123", "S123", "T123")],
            "N122",
        ),
        **_netting_spec(
            "panel_g_back", 156, "L", "A162", "A165", [("x1", "F163", "G163", "H163")], None
        ),
        **_netting_spec(
            "panel_g_belly", 156, "R", "M162", "M165", [("x1", "R163", "S163", "T163")], "N163"
        ),
        **_netting_spec(
            "panel_h_back", 189, "L", "A195", "A198", [("x1", "F196", "G196", "H196")], None
        ),
        **_netting_spec(
            "panel_h_belly", 189, "R", "M195", "M198", [("x1", "R196", "S196", "T196")], "N196"
        ),
        **_netting_spec(
            "panel_i_bag_top",
            222,
            "L",
            "A228",
            "A231",
            [("n", "F229", "G229", "H229"), ("t", "F230", "G230", "H230")],
            "B229",
        ),
        **_netting_spec(
            "panel_j_bag_bottom",
            222,
            "R",
            "M228",
            "M231",
            [("n", "R229", "S229", "T229"), ("t", "R230", "S230", "T230")],
            "N229",
        ),
        **_netting_spec(
            "panel_i_mod_bag_top",
            255,
            "L",
            "A261",
            "A264",
            [("n", "F262", "G262", "H262"), ("t", "F263", "G263", "H263")],
            None,
        ),
        **_netting_spec(
            "panel_i_mod_bag_bottom",
            255,
            "R",
            "M261",
            "M264",
            [("n", "R262", "S262", "T262"), ("t", "R263", "S263", "T263")],
            "O262",
        ),
        "mod_bag_join_ratio": V("J240", "Join ratio modified bag / panel H (I256/I190)"),
        "mod_bag_join_offset_m": V("B243", "Half difference of widths at the join", "m"),
        "cut_angle_average_deg": V("K278", "Average horizontal attack angle of the cuts", "°"),
        "cut_ratio_first_panel": V("G273", "Cut code of the first panel (used by all rows)"),
    },
    {
        "cut_u1_horizontal": _panel_series(
            "E273:E277", "Horizontal opening coef. U1", "", "B273:B277"
        ),
        "cut_u2_vertical": _panel_series("F273:F277", "Vertical opening coef. U2", "", "B273:B277"),
        "cut_codes": _panel_series("G273:G277", "Cut code per panel", "", "B273:B277"),
        "cut_width_meshes": _panel_series(
            "H273:H277", "Meshes (a) in width per cut (all rows use $G$273)", "", "B273:B277"
        ),
        "cut_height_meshes": _panel_series(
            "I273:I277", "Meshes (d) in height per cut (all rows use $G$273)", "", "B273:B277"
        ),
        "cut_tan_theta": _panel_series("J273:J277", "tan θ = (a·U1)/(d·U2)", "", "B273:B277"),
        "cut_angle_deg": _panel_series("K273:K277", "θ = DEGREES(ATAN(tan θ))", "°", "B273:B277"),
        "summary_top_mesh_mm": _panel_series(
            "Q271:Q279", "Summary upper plan: mesh size", "mm", "N271:N279"
        ),
        "summary_top_n_meshes": _panel_series(
            "R271:R279", "Summary upper plan: N meshes", "", "N271:N279"
        ),
        "summary_top_t_meshes": _panel_series(
            "S271:S279", "Summary upper plan: T meshes", "", "N271:N279"
        ),
        "summary_top_rtex": _panel_series(
            "U271:U279", "Summary upper plan: Rtex", "tex", "N271:N279"
        ),
        "summary_top_twine_mm": _panel_series(
            "V271:V279", "Summary upper plan: twine Ø", "mm", "N271:N279"
        ),
        "summary_top_u1": _panel_series("W271:W279", "Summary upper plan: U1", "", "N271:N279"),
        "summary_bottom_mesh_mm": _panel_series(
            "Q282:Q291", "Summary lower plan: mesh size", "mm", "N282:N291"
        ),
        "summary_bottom_n_meshes": _panel_series(
            "R282:R291", "Summary lower plan: N meshes", "", "N282:N291"
        ),
        "summary_bottom_t_meshes": _panel_series(
            "S282:S291", "Summary lower plan: T meshes", "", "N282:N291"
        ),
        "summary_bottom_rtex": _panel_series(
            "U282:U291", "Summary lower plan: Rtex", "tex", "N282:N291"
        ),
        "summary_bottom_twine_mm": _panel_series(
            "V282:V291", "Summary lower plan: twine Ø", "mm", "N282:N291"
        ),
        "summary_bottom_u1": _panel_series("W282:W291", "Summary lower plan: U1", "", "N282:N291"),
    },
)

CABLES_CABULLERIA: Spec = (
    {
        "headrope_rope": V("D3", "Headrope rope (combination 12 mm, steel 6x24+7)"),
        "headrope_rope_kg_per_m": V("G3", "Headrope rope mass per metre", "kg/m"),
        "headrope_rope_strength_t": V("H3", "Headrope rope breaking strength", "t"),
        "headrope_rope_diameter_mm": V("I3", "Headrope rope diameter", "mm"),
        "headrope_rope_length_m": V("J3", "Headrope rope length (=Lima)", "m"),
        "footrope_rope": V("D4", "Footrope rope (combination 14 mm, steel 6x24+7)"),
        "footrope_rope_kg_per_m": V("G4", "Footrope rope mass per metre", "kg/m"),
        "footrope_rope_strength_t": V("H4", "Footrope rope breaking strength", "t"),
        "footrope_rope_diameter_mm": V("I4", "Footrope rope diameter", "mm"),
        "footrope_rope_length_m": V("J4", "Footrope rope length (=Burlon)", "m"),
        "wingtip_reinforcement_m": V("J5", "Wing-tip reinforcement rope ROUNDUP(4·C155, 1)", "m"),
        "warp_selected": V("D11", "Selected towing warp construction"),
        "warp_diameter_mm": V("G11", "Selected warp diameter", "mm"),
        "warp_kg_per_m": V("H11", "Selected warp mass per metre", "kg/m"),
        "warp_strength_t": V("I11", "Selected warp breaking strength", "t"),
        "warp_quantity_m": V("D12", "Warp to buy = 2·Ls + 0.5·Ls", "m"),
    },
    {},
)


MECANICA: Spec = (
    {
        "filtration_sum_twine_mm_std": V("I15", "Σ twine Ø, standard net", "mm"),
        "filtration_sum_mesh_mm_std": V("J15", "Σ mesh size, standard net", "mm"),
        "filtration_sum_panels_std": V("H15", "Σ panel count, standard net"),
        "filtration_index_std": V("K15", "Filtration index d/l (Σd / Σl), standard net"),
        "filtration_sum_twine_mm_mod": V("I17", "Σ twine Ø, modified net", "mm"),
        "filtration_sum_mesh_mm_mod": V(
            "J17", "Σ mesh size, modified net (J16 counted twice)", "mm"
        ),
        "filtration_sum_panels_mod": V("H17", "Σ panel count, modified net"),
        "filtration_index_mod": V("K17", "Filtration index d/l, modified net"),
        "solid_surface_std_m2": V("N38", "Solid surface Ss = Σ panels, standard net", "m²"),
        "solid_surface_mod_bag_m2": V("N39", "Solid surface of the modified codend (I')", "m²"),
        "solid_surface_mod_m2": V("N40", "Solid surface Ss, modified net", "m²"),
        "solid_surface_lower_mod_m2": V("O30", "Ss lower plan, modified (includes N39)", "m²"),
        "solid_surface_upper_mod_m2": V("O32", "Ss upper plan, modified (includes N39)", "m²"),
        "solid_surface_lower_std_m2": V("O35", "Ss lower plan, standard (includes N37)", "m²"),
        "solid_surface_upper_std_m2": V("O37", "Ss upper plan, standard (includes N36)", "m²"),
        "working_surface_std_m2": V("M65", "Working surface St = Σ panels, standard net", "m²"),
        "working_surface_mod_bag_m2": V("M66", "Working surface of the modified codend", "m²"),
        "working_surface_mod_m2": V("M67", "Working surface St, modified net", "m²"),
        "solidity_std": V("E75", "Solidity coefficient Ss/St, standard"),
        "solidity_mod": V("E76", "Solidity coefficient Ss/St, modified"),
        "filtering_coef_std": V("M78", "Filtering coefficient 1 − solidity, standard"),
        "filtering_coef_mod": V("M79", "Filtering coefficient 1 − solidity, modified"),
        "net_weight_air_std_kg": V("O107", "Net weight in air, standard (sum of panels)", "kg"),
        "net_weight_water_std_kg": V("P107", "Net weight in water, standard", "kg"),
        "net_weight_air_mod_kg": V("O109", "Net weight in air, modified", "kg"),
        "net_weight_water_mod_kg": V("P109", "Net weight in water, modified", "kg"),
        "mod_bag_twine_weight_kg": V("N108", "Modified codend: twine weight SN", "kg"),
        "mod_bag_weight_air_kg": V("O108", "Modified codend: weight in air", "kg"),
        "mod_bag_weight_water_kg": V("P108", "Modified codend: weight in water", "kg"),
        "lower_plan_weight_std_kg": V("I110", "Weight lower plan, standard", "kg"),
        "upper_plan_weight_std_kg": V("I111", "Weight upper plan, standard", "kg"),
        "lower_plan_weight_mod_kg": V("I112", "Weight lower plan, modified", "kg"),
        "upper_plan_weight_mod_kg": V("I113", "Weight upper plan, modified", "kg"),
        "seawater_density_kg_m3": V("O127", "Sea-water density", "kg/m³"),
        "freshwater_density_kg_m3": V("O128", "Fresh-water density", "kg/m³"),
        "gravity_m_s2": V("O129", "Gravity", "m/s²"),
        "door_attack_angle_deg": V("D164", "Door attack angle (=Portones!C134)", "°"),
        "door_area_m2": V("E164", "Door projected area (=Portones!D122)", "m²"),
        "door_cd": V("F164", "Door CD at the selected angle"),
        "door_cl": V("G164", "Door CL at the selected angle"),
        "depth_m": V("E176", "Working depth d", "m"),
        "warp_length_m": V("E177", "Warp paid out Ls = d · ratio", "m"),
        "warp_depth_ratio": V("J178", "Warp/depth ratio (LOOKUP in Tablas A354:C383)"),
        "warp_horizontal_shallow_m": V("F179", "Lsh = 0.95·Ls (shallow)", "m"),
        "warp_horizontal_deep_m": V("F180", "Lsh = 0.85·Ls (deep)", "m"),
        "net_length_no_bag_m": V("E182", "Net length without codend LR", "m"),
        "u1": V("E183", "Horizontal opening coefficient U1"),
        "u2": V("E184", "Vertical opening coefficient U2"),
        "net_length_working_m": V("E185", "LR working = LR·U2", "m"),
        "bridle_length_m": V("E186", "Bridle length Lnc (=Dimensiones!F68)", "m"),
        "footrope_m": V("E209", "Footrope (Burlon)", "m"),
        "door_spread_m": V("E210", "Door spread Ds (=Portones!E13)", "m"),
        "sweeps_m": V("E213", "Sweeps (patentes)", "m"),
        "crowfoot_m": V("E211", "Crowfoot (pie de gallo)", "m"),
        "crowfoot_extension_m": V("E212", "Crowfoot extension", "m"),
        "upper_bridle_m": V("E214", "Upper bridle", "m"),
        "dpa_geometric_std_m": V("L211", "DPA geometric ROUNDDOWN(Burlon·Ds / Σ rigging)", "m"),
        "dpa_geometric_working_m": V(
            "L225", "DPA ROUNDUP(Ds·LR_working / (LR_working + rigging))", "m"
        ),
        "dpa_from_cut_angle_m": V("L233", "DPA = 2·b·U2·tan(α)", "m"),
        "net_length_total_std_m": V("E233", "Total length incl. codend, standard", "m"),
        "net_length_total_mod_m": V("F233", "Total length incl. codend, modified", "m"),
        "cut_angle_deg": V("E235", "Average cut angle α", "°"),
        "circumference_m": V("F243", "Maximum stretched circumference a", "m"),
        "av_izzo_4_35pct_m": V("K242", "AV Izzo 4.35 % of circumference", "m"),
        "av_izzo_5pct_m": V("K243", "AV Izzo 5 %", "m"),
        "av_izzo_6pct_m": V("K244", "AV Izzo 6 %", "m"),
        "av_izzo_7pct_m": V("K245", "AV Izzo 7 %", "m"),
        "av_prado_low_opening_m": V(
            "F245", "AV Prado/Dremiere bottom trawl low opening 5.5 %", "m"
        ),
        "av_prado_high_opening_m": V(
            "F246", "AV Prado/Dremiere bottom trawl high opening 6.5 %", "m"
        ),
        "av_prado_shellfish_m": V("F247", "AV Prado/Dremiere shellfish trawl 6.5 %", "m"),
        "vertical_opening_m": V("D255", "AV Suzuki (JICA 1982) = 4/90 · a", "m"),
        "av_martini_m": V("E272", "AV Martini level 2 = (DV − MR·mL)·0.05", "m"),
        "av_martini_dv_m": V("E269", "DV: stretched circumference of first back/belly panel", "m"),
        "av_martini_mr_meshes": V("E270", "MR: meshes on the rope edges (3·4)"),
        "flotation_total_kgf": V("O261", "Total flotation Ffz (average of 4 methods)", "kgf"),
        "dan_leno_m": V("O262", "Dan leno height", "m"),
        "dpa_over_l": V("O265", "DPA / L"),
        "dpa_over_l_rounded": V("P265", "DPA / L rounded"),
        "catenary_ratio": V("O266", "Catenary fL/L"),
        "headrope_sag_m": V("O267", "Headrope sag fL = 0.216·L", "m"),
        "av_fridman_avg_std_m": V("O282", "AV Fridman average, standard", "m"),
        "av_fridman_avg_mod_m": V("P282", "AV Fridman average, modified", "m"),
        "av_summary_prado_low_m": V("U246", "AV summary: Prado low opening (static)", "m", True),
        "av_summary_prado_high_m": V("W246", "AV summary: Prado high opening (static)", "m", True),
        "av_summary_izzo_4_35_m": V("U248", "AV summary: Izzo 4.35 % (static)", "m", True),
        "av_summary_izzo_5_m": V("V248", "AV summary: Izzo 5 % (static)", "m", True),
        "av_summary_izzo_6_m": V("W248", "AV summary: Izzo 6 % (static)", "m", True),
        "av_summary_izzo_7_m": V("X248", "AV summary: Izzo 7 % (static)", "m", True),
        "av_summary_suzuki_m": V("U250", "AV summary: Suzuki (static)", "m", True),
        "av_summary_martini_m": V("U252", "AV summary: Martini (static)", "m", True),
        "av_summary_fridman_avg_std_m": V(
            "T266", "AV summary: Fridman avg std (static)", "m", True
        ),
        "av_summary_fridman_avg_mod_m": V(
            "U266", "AV summary: Fridman avg mod (static)", "m", True
        ),
    },
    {
        "filtration_per_panel": _panel_series(
            "K6:K14", "d/l · panel count per panel group", "", "D6:D14"
        ),
        "solid_surface_per_panel_m2": _panel_series(
            "N29:N37", "Solid surface per panel group", "m²", "C29:C37"
        ),
        "panel_length_m": _panel_series("M29:M37", "Panel length mL·N/1000", "m", "C29:C37"),
        "panel_u1": _panel_series("K56:K64", "U1 per panel group", "", "A56:A64"),
        "panel_u2": _panel_series("L56:L64", "U2 = sqrt(1 − U1²)", "", "A56:A64"),
        "working_surface_per_panel_m2": _panel_series(
            "M56:M64", "Working surface per panel group", "m²", "A56:A64"
        ),
        "twine_weight_per_panel_kg": _panel_series(
            "N98:N106", "SN twine weight per panel group", "kg", "A98:A106"
        ),
        "weight_air_per_panel_kg": _panel_series(
            "O98:O106", "Weight in air per panel group", "kg", "A98:A106"
        ),
        "weight_water_per_panel_kg": _panel_series(
            "P98:P106", "Weight in water per panel group", "kg", "A98:A106"
        ),
        "speed_ms": _speed("C", 164, "Speed in m/s", "m/s"),
        "door_drag_rd_kgf": _speed("H", 164, "Door drag Rd = ½ρ/g·v²·S·CD", "kgf"),
        "door_lift_fdy_kgf": _speed("I", 164, "Door spreading force Fdy = ½ρ/g·v²·S·CL", "kgf"),
        "rn_std_kgf": _speed("J", 164, "RN standard (Aberdeen demersal) ×1000", "kgf"),
        "rn_mod_kgf": _speed("K", 164, "RN modified (Aberdeen demersal) ×1000", "kgf"),
        "edx_std": _speed("L", 164, "Edx = Rd / (RN/2), standard", ""),
        "edx_mod": _speed("M", 164, "Edx = Rd / (RN/2), modified", ""),
        "edy_std": _speed("N", 164, "Edy = Fdy / (RN/2), standard", ""),
        "edy_mod": _speed("O", 164, "Edy = Fdy / (RN/2), modified", ""),
        "dpa_fridman_std_m": _speed(
            "P", 164, "DPA Fridman = 2·Lsh·LRw·Edy / (Lsh + Lnc·(1+Edx)), standard", "m"
        ),
        "dpa_fridman_mod_m": _speed("Q", 164, "DPA Fridman, modified", "m"),
        "yn_std_m": _speed("I", 193, "Yn = DPA/2, standard", "m"),
        "yn_mod_m": _speed("J", 193, "Yn = DPA/2, modified", "m"),
        "dpa_fridman_2yn_std_m": _speed("K", 193, "2·Yn, standard", "m"),
        "dpa_fridman_2yn_mod_m": _speed("L", 193, "2·Yn, modified", "m"),
        "door_spread_from_dpa_m": _speed("M", 193, "Door spread from DPA (modified)", "m"),
        "rn_std_kgf_av": _speed("K", 272, "RN standard ×1000 for AV Fridman", "kgf"),
        "rn_mod_kgf_av": _speed("L", 272, "RN modified ×1000 for AV Fridman", "kgf"),
        "alpha_fridman_std_deg": _speed("M", 272, "α = atan(2·Ffz / RN), standard", "°"),
        "alpha_fridman_mod_deg": _speed("N", 272, "α = atan(2·Ffz / RN), modified", "°"),
        "av_fridman_std_m": _speed(
            "O", 272, "AV Fridman = dan leno + (fL + Vs)·sin α, standard", "m"
        ),
        "av_fridman_mod_m": _speed("P", 272, "AV Fridman, modified", "m"),
        "av_fridman_summary_std_m": _speed(
            "T", 256, "AV Fridman summary (pasted static), standard", "m", static=True
        ),
        "av_fridman_summary_mod_m": _speed(
            "U", 256, "AV Fridman summary (pasted static), modified", "m", static=True
        ),
    },
)

DIMENSIONES: Spec = (
    {
        "headrope_m": V("F45", "Headrope (Lima) = 2·L_ala_corr + L_bocana_corr", "m"),
        "footrope_m": V("F46", "Footrope (Burlon) = 2·m_ala_corr + m_bocana_corr", "m"),
        "total_length_belly_std_m": V("F47", "Total length (belly) incl. codend, standard", "m"),
        "total_length_belly_mod_m": V("G47", "Total length (belly) incl. codend, modified", "m"),
        "total_length_back_no_bag_std_m": V("F48", "Total length (back) without codend", "m"),
        "total_length_back_no_bag_mod_m": V("G48", "Total length without codend, modified", "m"),
        "circumference_m": V("F49", "Maximum stretched circumference a", "m"),
        "upper_wing_m": V("F50", "Upper wing c", "m"),
        "lower_wing_m": V("F51", "Lower wing d", "m"),
        "back_belly_m": V("F52", "Back or belly e", "m"),
        "bag_m": V("F53", "Codend f", "m"),
        "square_m": V("F54", "Square d − c", "m"),
        "cut_angle_deg": V("F55", "Horizontal attack angle α", "°"),
        "filtration_index_std": V("F56", "Filtration index d/l, standard"),
        "filtration_index_mod": V("G56", "Filtration index d/l, modified"),
        "solid_surface_std_m2": V("F57", "Solid surface Ss, standard", "m²"),
        "solid_surface_mod_m2": V("G57", "Solid surface Ss, modified", "m²"),
        "working_surface_std_m2": V("F58", "Working surface St, standard", "m²"),
        "working_surface_mod_m2": V("G58", "Working surface St, modified", "m²"),
        "net_weight_std_kg": V("F59", "Net weight unrigged, standard", "kg"),
        "net_weight_mod_kg": V("G59", "Net weight unrigged, modified", "kg"),
        "vertical_opening_m": V("F60", "Vertical opening AV", "m"),
        "horizontal_opening_m": V("F61", "Horizontal opening AH (average of 4 DPA estimates)", "m"),
        "working_depth_m": V("F62", "Working depth", "m"),
        "flotation_total_kgf": V("F63", "Total flotation Ft", "kgf"),
        "dan_leno_m": V("F64", "Dan leno / triangle height", "m"),
        "sweeps_m": V("F65", "Sweeps (patentes)", "m"),
        "sweeps_range_note": V("H65", "Sweeps allowed range note"),
        "crowfoot_m": V("F66", "Crowfoot (pie de gallo)", "m"),
        "crowfoot_extension_m": V("F67", "Crowfoot extension", "m"),
        "upper_bridle_std_m": V("F68", "Upper bridle Vs, standard", "m"),
        "upper_bridle_mod_m": V("G68", "Upper bridle Vs, modified", "m"),
        "lower_bridle_std_m": V("F69", "Lower bridle Vi, standard", "m"),
        "lower_bridle_mod_m": V("G69", "Lower bridle Vi, modified", "m"),
        "warp_diameter_mm": V("F70", "Towing warp diameter", "mm"),
        "warp_length_m": V("F71", "Warp paid out per side", "m"),
        "square_depth_meshes": V("F85", "Meshes in depth of the square"),
        "square_mesh_mm": V("F86", "Square mesh size", "mm"),
        "length_factor": V("D89", "Fujiishi length factor FL = (L + 2·square)/m"),
        "fishing_circle_m": V("D97", "Fishing circle FC", "m"),
        "body_length_m": V("D103", "Body length L_cuerpo", "m"),
        "fc_body_ratio": V("D109", "FC / L_cuerpo"),
        "headrope_wing_m": V("C140", "Headrope wing piece L_ala", "m"),
        "headrope_bosom_m": V("F140", "Headrope bosom piece L_bocana", "m"),
        "headrope_wing_hanging": V("C142", "Hanging ratio (embando) wing"),
        "headrope_bosom_hanging": V("G142", "Hanging ratio (embando) bosom"),
        "headrope_wing_corrected_m": V("C143", "Headrope wing corrected", "m"),
        "headrope_bosom_corrected_m": V("G143", "Headrope bosom corrected", "m"),
        "footrope_wing_m": V("C148", "Footrope wing piece m_ala", "m"),
        "footrope_bosom_m": V("F148", "Footrope bosom piece m_bocana", "m"),
        "footrope_wing_hanging": V("C150", "Hanging ratio wing (footrope)"),
        "footrope_bosom_hanging": V("G150", "Hanging ratio bosom (footrope)"),
        "footrope_wing_corrected_m": V("C151", "Footrope wing corrected", "m"),
        "footrope_bosom_corrected_m": V("G151", "Footrope bosom corrected", "m"),
        "wingtip_reinforcement_m": V("C155", "Wing-tip reinforcement m_punta", "m"),
        "wingtip_hanging": V("C157", "Hanging ratio wing tip"),
    },
    {
        "nomura_ratio_fao_a3": S(
            "C124:C132",
            "Nomura proportions of FAO A3",
            "",
            x="ratio",
            x_values=None,
            x_cells="B124:B132",
        ),
        "nomura_ratio_reference": S(
            "E124:E132",
            "Nomura reference proportions, bottom trawl 2 panels",
            "",
            x="ratio",
            x_values=None,
            x_cells="B124:B132",
        ),
    },
)


def _drag_pair(
    key: str, col_std: str, col_mod: str, r0: int, label: str, unit: str = "t"
) -> dict[str, S]:
    return {
        f"{key}_std_{unit}": _speed(col_std, r0, f"{label}, standard net", unit),
        f"{key}_mod_{unit}": _speed(col_mod, r0, f"{label}, modified net", unit),
    }


_SUMMARY_COLS = [
    ("C", "tauti_nomura_shu", "Tauti–Nomura–Shu"),
    ("D", "tauti_headrope", "Tauti (headrope)"),
    ("E", "tauti_footrope", "Tauti (footrope)"),
    ("F", "koyama_1974", "Koyama 1974"),
    ("G", "koyama_1984", "Koyama 1984"),
    ("H", "hamuro", "Hamuro"),
    ("I", "nomura_150", "Nomura NHP 150"),
    ("J", "nomura_180", "Nomura NHP 180"),
    ("K", "reid", "Reid"),
    ("L", "robertson", "Robertson"),
    ("M", "maclennan", "MacLennan"),
    ("N", "aberdeen_demersal", "Aberdeen demersal"),
    ("O", "aberdeen_pelagic", "Aberdeen pelagic"),
    ("P", "fridman", "Fridman"),
    ("Q", "dickson", "Dickson"),
    ("R", "average", "Average of methods"),
    ("S", "dynamit", "DynamiT (static)"),
]


def _summary_series(prefix: str, r0: int, net: str, unit: str) -> dict[str, S]:
    out: dict[str, S] = {}
    for col, key, lab in _SUMMARY_COLS:
        out[f"{prefix}_{key}_{net}_{unit}"] = _speed(
            col, r0, f"Summary {lab}, {net} net", unit, static=(key == "dynamit")
        )
    return out


RESISTENCIA: Spec = (
    {
        "filtration_index_std": V("E4", "Filtration index d/l, standard"),
        "filtration_index_mod": V("E5", "Filtration index d/l, modified"),
        "circumference_m": V("E6", "Stretched circumference a (=Dimensiones!D97)", "m"),
        "headrope_m": V("I25", "Headrope rs", "m"),
        "footrope_m": V("I26", "Footrope ri", "m"),
        "koyama74_length_std_m": V("E69", "Koyama 1974 total length incl. codend, standard", "m"),
        "koyama74_length_mod_m": V("E70", "Koyama 1974 total length incl. codend, modified", "m"),
        "koyama84_length_std_m": V("D86", "Koyama 1984 length without codend, standard", "m"),
        "koyama84_length_mod_m": V("D87", "Koyama 1984 length without codend, modified", "m"),
        "hamuro_st_std_m2": V("D110", "Hamuro working surface, standard", "m²"),
        "hamuro_st_mod_m2": V("D111", "Hamuro working surface, modified", "m²"),
        "hamuro_alpha_deg": V("D112", "Hamuro attack angle α", "°"),
        "hamuro_sin_alpha": V("D113", "ABS(SIN(DEGREES(α))) — errata hamuro_sin_degrees"),
        "reid_ss_std_m2": V("F149", "Reid solid surface, standard", "m²"),
        "reid_ss_mod_m2": V("F150", "Reid solid surface, modified", "m²"),
        "dickson_m2_to_ft2": V("F275", "Dickson m² → ft² factor"),
        "dickson_st_std_ft2": V("F276", "Dickson working surface, standard", "ft²"),
        "dickson_st_mod_ft2": V("F277", "Dickson working surface, modified", "ft²"),
        "summary_dynamit_1kn_std_t": V(
            "S302", "DynamiT RN at 1 kn, standard (=330.6/1000)", "t", True
        ),
    },
    {
        "speed_kn": _speed("B", 11, "Speed vector", "kn"),
        "speed_ms": _speed("C", 11, "Speed vector", "m/s"),
        **_drag_pair(
            "tauti_nomura_shu_rn", "D", "E", 11, "Tauti–Nomura–Shu RN = 27·d/l·a²·v^1.45/1000"
        ),
        **_drag_pair("tauti_headrope_rn", "D", "E", 30, "Tauti RN = 25·d/l·rs²·v²/1000"),
        **_drag_pair("tauti_footrope_rn", "L", "M", 30, "Tauti RN = 25·d/l·ri²·v²/1000"),
        **_drag_pair("koyama_1974_rn", "D", "E", 74, "Koyama 1974 RN = 16·d/l·a·b·v²/1000"),
        **_drag_pair("koyama_1984_rn", "C", "D", 91, "Koyama 1984 RN = 8·d/l·a·L·v_kn²/1000"),
        **_drag_pair("hamuro_rn", "D", "E", 117, "Hamuro RN = 191·d/l·v²·St·sin α/1000"),
        "nomura_rn_150_t": _speed("D", 132, "Nomura RN = 7.2·NHP / v /1000, 150 HP", "t"),
        "nomura_rn_180_t": _speed("E", 132, "Nomura RN = 7.2·NHP / v /1000, 180 HP", "t"),
        **_drag_pair("reid_rn", "C", "D", 154, "Reid RN = v²·Ss / (54.72·v₁ + 115.2)"),
        **_drag_pair("robertson_rn", "C", "D", 174, "Robertson RN = v²·Ss / (66.18·v + 41.5)"),
        **_drag_pair(
            "maclennan_rn", "C", "D", 196, "MacLennan RN = Ss·(61.2+46.6·v²)/(1+0.0641·v)/9807"
        ),
        **_drag_pair(
            "aberdeen_demersal_rn",
            "C",
            "D",
            214,
            "Aberdeen demersal RN = Ss·(0.00624+0.00475·v²)/(1+0.0641·v)",
        ),
        **_drag_pair(
            "aberdeen_pelagic_rn",
            "C",
            "D",
            237,
            "Aberdeen pelagic RN = Ss·0.00868·v²/(1+0.00475·v)",
        ),
        **_drag_pair("fridman_rn", "D", "E", 258, "Fridman RN = (1.8+2α·(d/l−0.01))·St·v²/1000"),
        "dickson_ah_m": _speed("C", 282, "Dickson input AH (=Mecánica!P164:P172)", "m"),
        "dickson_av_m": _speed("D", 282, "Dickson input AV (=Mecánica!O272:O280)", "m"),
        **_drag_pair(
            "dickson_rn", "E", "F", 282, "Dickson RN = 1/125·St_ft²·d/l·(1+13.2·AH·AV)/St"
        ),
        **_summary_series("summary", 302, "std", "t"),
        **_summary_series("summary", 317, "mod", "t"),
        **_summary_series("summary", 398, "std", "kgf"),
        **_summary_series("summary", 413, "mod", "kgf"),
        "summary_method_average_mod_t": S(
            "C326:S326",
            "Per-method mean over speeds, modified net",
            "t",
            x="method",
            x_values=[k for _, k, _ in _SUMMARY_COLS],
        ),
        "summary_method_average_mod_kgf": S(
            "C422:S422",
            "Per-method mean over speeds, modified net",
            "kgf",
            x="method",
            x_values=[k for _, k, _ in _SUMMARY_COLS],
        ),
    },
)


def _rob_share(tag: str, r0: int, hp: str) -> dict[str, S]:
    return {
        f"fridman_ft_fixed_{tag}_kgf": _speed("D", r0, f"Fridman FT fixed pitch, {hp}", "kgf"),
        f"rob_15pct_{tag}_kgf": _speed("E", r0, f"ROB = 15 % of FT, {hp}", "kgf"),
        f"rob_20pct_{tag}_kgf": _speed("F", r0, f"ROB = 20 % of FT, {hp}", "kgf"),
        f"rob_25pct_{tag}_kgf": _speed("G", r0, f"ROB = 25 % of FT, {hp}", "kgf"),
        f"rob_30pct_{tag}_kgf": _speed("H", r0, f"ROB = 30 % of FT, {hp}", "kgf"),
    }


PORTONES: Spec = (
    {
        "gallows_spacing_m": V("D6", "Distance between gallows (=vessel beam)", "m"),
        "spread_per_metre_m": V("D7", "Door spread at 1 m of warp", "m"),
        "working_depth_m": V("D8", "Working depth", "m"),
        "warp_length_m": V("D9", "Warp paid out", "m"),
        "door_spread_m": V("E13", "Door spread Ds = (D7 − D6)·Ls + D6", "m"),
        "warp_half_divergence_deg": V("D21", "½φ = asin(0.5·(Ds − gallows)/Ls)", "°"),
        "spread_correction_factor": V("D28", "Correction factor for door spread"),
        "door_spread_corrected_m": V("F30", "Corrected door spread = 1.15·2·Ls·sin(½φ)", "m"),
        "vertical_opening_std_m": V("F37", "AV standard (=Mecánica!D255)", "m"),
        "headrope_sag_m": V("F38", "Headrope sag fL", "m"),
        "bridle_angle_deg": V("F39", "Angle between upper and lower bridle α", "°"),
        "upper_bridle_std_m": V("D44", "Upper bridle Vs = ROUND(E52)", "m"),
        "upper_bridle_mod_m": V("E44", "Upper bridle Vs, modified", "m"),
        "lower_bridle_std_m": V("D45", "Lower bridle Vi = ROUNDUP(Vs − Cr)", "m"),
        "lower_bridle_mod_m": V("E45", "Lower bridle Vi, modified", "m"),
        "adjust_chain_std_m": V("D46", "Adjustment chain Cr = 0.095·Vs", "m"),
        "adjust_chain_mod_m": V("E46", "Adjustment chain, modified", "m"),
        "bridle_length_no_triangle_std_m": V("E52", "Bridle length = ROUND(AV/sin α − fL)", "m"),
        "bridle_length_no_triangle_mod_m": V("F52", "Bridle length, modified", "m"),
        "dan_leno_height_m": V("F56", "Dan leno / triangle height", "m"),
        "bridle_length_triangle_std_m": V(
            "E60", "Bridle length with triangle = ROUND((AV − h)/sin α)", "m"
        ),
        "bridle_length_triangle_mod_m": V("F60", "Bridle length with triangle, modified", "m"),
        "dremiere_ratio": V("B68", "Dremiere ratio warp/sweep"),
        "sweeps_dremiere_m": V("C71", "Sweep length Dremiere = Ls / ratio", "m"),
        "sweeps_martini_delta_deg": V("H65", "δ for Martini sweeps", "°"),
        "sweeps_martini_m": V("G71", "Sweep length Martini (Ds/2 − DPA/2 / DEGREES(SIN(δ)))", "m"),
        "sweeps_dpa_m": V("E78", "DPA used for sweeps (=Mecánica!L211)", "m"),
        "sweeps_bridle_m": V("E79", "Bridle used for sweeps", "m"),
        "sweeps_net_length_m": V("E80", "Net length used for sweeps (=Largototal)", "m"),
        "sweeps_bridle_triangle_m": V("E81", "Bridle with triangle used for sweeps", "m"),
        "sweeps_no_triangle_m": V("C83", "LPST = ((Ds·LR/DPA) − (Vs + LR))·1.1", "m"),
        "sweeps_triangle_m": V("C87", "LPCT with triangle", "m"),
        "door_length_for_crowfoot_m": V("D95", "Door length (for crowfoot)", "m"),
        "crowfoot_m": V("E97", "Crowfoot PG = ROUND(1.2·door length, 1)", "m"),
        "crowfoot_upper_m": V("G98", "Upper crowfoot = PG − 0.05", "m"),
        "crowfoot_extension_m": V("E99", "Crowfoot extension", "m"),
        "bridle_attack_angle_deg": V("D110", "δ = asin(((Ds − DPA)/2)/(PG + LPST + bridle))", "°"),
        "door_name": V("B117", "Selected door"),
        "door_length_m": V("D120", "Door length", "m"),
        "door_height_m": V("D121", "Door height", "m"),
        "door_area_m2": V("D122", "Door projected area", "m²"),
        "door_aspect_ratio": V("D123", "Door aspect ratio"),
        "door_area_ratio": V("D124", "Door area ratio"),
        "door_weight_air_kg": V("D125", "Door weight in air", "kg"),
        "door_weight_coef": V("D126", "Door weight multiplier (in water)"),
        "door_weight_water_kg": V("D127", "Door weight in water", "kg"),
        "door_angle_selected_deg": V("C134", "Selected door attack angle", "°"),
        "door_cl_selected": V("D134", "CL at selected angle"),
        "door_cd_selected": V("E134", "CD at selected angle"),
        "door_cl_cd_selected": V("F134", "CL/CD at selected angle"),
        "rob_cd": V("D185", "Door CD (ROB block)"),
        "rob_cl": V("D186", "Door CL (ROB block)"),
        "rob_area_m2": V("D184", "Door area (ROB block)", "m²"),
        "required_door_area_avg_150_m2": V(
            "F212", "Average required door area (2.0–4.0 kn), 150 HP", "m²"
        ),
        "required_door_area_each_150_m2": V("F215", "Required area per door, 150 HP", "m²"),
        "required_door_area_avg_180_m2": V("F225", "Average required door area, 180 HP", "m²"),
        "required_door_area_each_180_m2": V("F229", "Required area per door, 180 HP", "m²"),
        "required_door_area_overall_m2": V("F220", "Overall average required area per door", "m²"),
        "force_angle_deg": V("E240", "Optimum attack angle (force block)", "°"),
        "centre_of_pressure_m": V("C266", "Centre of pressure d = ¾·cos φ/(4 + π sin φ)·L", "m"),
        "ha_m": V("C269", "hA = 0.8·L/4", "m"),
        "hb_m": V("C270", "hB = L/4", "m"),
        "sweep_lever_m": V("E277", "d_patente lever for moment balance", "m"),
    },
    {
        "door_polar_angle_deg": S(
            "C132:C137",
            "Door polar: attack angle",
            "°",
            x="angle_deg",
            x_values=None,
            x_cells="C132:C137",
        ),
        "door_polar_cl": S(
            "D132:D137", "Door polar: CL", "", x="angle_deg", x_values=None, x_cells="C132:C137"
        ),
        "door_polar_cd": S(
            "E132:E137", "Door polar: CD", "", x="angle_deg", x_values=None, x_cells="C132:C137"
        ),
        "door_polar_cl_cd": S(
            "F132:F137", "Door polar: CL/CD", "", x="angle_deg", x_values=None, x_cells="C132:C137"
        ),
        "rn_std_kgf": _speed("B", 146, "RN standard ×1000", "kgf"),
        "rn_mod_kgf": _speed("C", 146, "RN modified ×1000", "kgf"),
        **_rob_share("150", 146, "150 HP"),
        **_rob_share("180", 160, "180 HP"),
        "speed_ms": _speed("C", 190, "Speed in m/s", "m/s"),
        "rob_kgf": _speed("D", 190, "ROB = ½ρ/g·CD·S·v² (both doors)", "kgf"),
        "door_spreading_force_kgf": _speed("E", 190, "Fy = ½ρ/g·CL·S·v²", "kgf"),
        "rob_20pct_input_150_kgf": _speed("D", 210, "ROB 20 % input, 150 HP", "kgf"),
        "required_door_area_150_m2": _speed(
            "E", 210, "Required area S = 2·ROB/(ρ/g·CD·v²), 150 HP", "m²"
        ),
        "rob_20pct_input_180_kgf": _speed("D", 223, "ROB 20 % input, 180 HP", "kgf"),
        "required_door_area_180_m2": _speed("E", 223, "Required area S, 180 HP", "m²"),
        "door_force_kgf": _speed(
            "D",
            252,
            "Pφ = ½·ρ_s·(ρ/g)·v²·S·2 sin(φ)/(1+sin²φ) — errata door_force_mixed_angles",
            "kgf",
        ),
        "door_moment_kgf_cm": _speed("G", 281, "Moment Pφ · d·100", "kgf·cm"),
        "sweep_moment_kgf_cm": _speed("H", 281, "½·RN·d_patente", "kgf·m"),
    },
)


def _fridman_float_rows(tag: str, r0: int, hp: str) -> dict[str, S]:
    return {
        f"fridman_ft_{tag}_kgf": _speed("E", r0, f"Fridman FT (PF), {hp}", "kgf"),
        f"float_f1_{tag}_kgf": _speed("F", r0, f"F1 = 0.8·FT/4, {hp}", "kgf"),
        f"float_f2_std_{tag}_kgf": _speed("G", r0, f"F2 = RN/4, standard, {hp}", "kgf"),
        f"float_f2_mod_{tag}_kgf": _speed("H", r0, f"F2 = RN/4, modified, {hp}", "kgf"),
        f"float_f1_vertical_{tag}_kgf": _speed("I", r0, f"F1' = F1·sin(bridle α), {hp}", "kgf"),
        f"float_f2_vertical_std_{tag}_kgf": _speed(
            "J", r0, f"F2' = F2·sin β, standard, {hp}", "kgf"
        ),
        f"float_f2_vertical_mod_{tag}_kgf": _speed(
            "K", r0, f"F2' = F2·sin β, modified, {hp}", "kgf"
        ),
        f"flotation_total_std_{tag}_kgf": _speed(
            "L", r0, f"F total = F1'+F2'+W_lima, standard, {hp}", "kgf"
        ),
        f"flotation_total_mod_{tag}_kgf": _speed("M", r0, f"F total, modified, {hp}", "kgf"),
    }


FLOTACION: Spec = (
    {
        "headrope_m": V("H4", "Headrope L", "m"),
        "flotation_koyama_kgf": V("F6", "Koyama flotation = 1.11·L − 6.81", "kgf"),
        "prado_k": V("I14", "Prado K (50–600 NHP)"),
        "flotation_prado_150_kgf": V("F17", "Prado flotation = K·NHP, 150 HP", "kgf"),
        "flotation_prado_180_kgf": V("G17", "Prado flotation = K·NHP, 180 HP", "kgf"),
        "bridle_angle_deg": V("F22", "Bridle angle α (=Portones!F39)", "°"),
        "beta_deg": V("F23", "β = atan((AV/2)/L_cuerpo)", "°"),
        "vertical_opening_m": V("F24", "AV", "m"),
        "body_length_m": V("F25", "Body length", "m"),
        "net_length_no_bag_m": V("F26", "Net length without codend", "m"),
        "headrope_wing_m": V("F27", "Headrope wing piece", "m"),
        "headrope_diameter_mm": V("F32", "Headrope rope diameter", "mm"),
        "headrope_material": V("F33", "Headrope rope material"),
        "headrope_kg_per_m": V("F35", "Headrope rope kg/m", "kg/m"),
        "headrope_weight_air_kg": V("F36", "Headrope weight in air", "kg"),
        "headrope_weight_water_kgf": V("F37", "Headrope weight in water = 0.087·W_air", "kgf"),
        "flotation_fridman_avg_150_kgf": V(
            "N43", "Fridman flotation average 1–3 kn, 150 HP", "kgf"
        ),
        "flotation_fridman_avg_180_kgf": V(
            "N55", "Fridman flotation average 1–3 kn, 180 HP", "kgf"
        ),
        "flotation_design_150_kgf": V("F70", "Total flotation used for float count, 150 HP", "kgf"),
        "flotation_design_180_kgf": V("G70", "Total flotation used for float count, 180 HP", "kgf"),
        "float_count": V("F84", "Number of floats chosen"),
        "float_count_total": V("F91", "Total floats"),
        "float_diameter_mm": V("F92", "Float diameter (LOOKUP by count)", "mm"),
        "flotation_total_rounded_kgf": V("F90", "Total flotation rounded", "kgf"),
        "headrope_wing_corrected_m": V("F87", "Headrope wing corrected", "m"),
        "headrope_bosom_corrected_m": V("F89", "Headrope bosom corrected", "m"),
        "float_spacing_even_m": V("F94", "Even spacing = L / n", "m"),
        "floats_per_wing_even": V("F95", "Floats per wing (even)"),
        "floats_bosom_even": V("F96", "Floats on bosom (even)"),
        "float_wing_share": V("F103", "Share of flotation on wings"),
        "floats_on_wings": V("G103", "Floats on wings = EVEN(n·share)"),
        "floats_per_wing": V("H103", "Floats per wing"),
        "floats_on_bosom": V("G104", "Floats on bosom"),
        "wing_front_fifth_share": V("G106", "Share of wing floats on the first fifth"),
        "floats_front_fifth": V("G107", "Floats on the first fifth of each wing"),
        "float_spacing_front_fifth_m": V("H110", "Spacing on the first fifth", "m"),
        "wing_remaining_length_m": V("C111", "Remaining wing length", "m"),
        "floats_remaining": V("F111", "Floats on the remaining wing"),
        "float_spacing_remaining_m": V("H111", "Spacing on the remaining wing", "m"),
        "wing_free_end_m": V("E112", "Free distance to the wing-tip eye", "m"),
        "float_spacing_bosom_m": V("K112", "Spacing on the bosom = bosom/3", "m"),
        "float_diameter_m": V("H128", "Float diameter", "m"),
        "float_cd_hoerner": V("H129", "Float CD (Hoerner 1975)"),
        "kinematic_viscosity_0c": V("H130", "ν sea water 0 °C", "m²/s"),
        "kinematic_viscosity_20c": V("H131", "ν sea water 20 °C", "m²/s"),
        "kinematic_viscosity_avg": V("H132", "ν average", "m²/s"),
        "ballast_koyama_kg": V("G159", "Koyama ballast = 1.81·L − 4.54", "kg"),
        "ballast_prado_k_150": V("G168", "Prado K for ballast, 150 HP"),
        "ballast_prado_150_kg": V("I173", "Prado ballast = K·NHP, 150 HP", "kg"),
        "ballast_prado_k_180": V("G176", "Prado K for ballast, 180 HP"),
        "ballast_prado_180_kg": V("I180", "Prado ballast = K·NHP, 180 HP", "kg"),
        "footrope_m": V("G184", "Footrope length", "m"),
        "footrope_diameter_mm": V("G185", "Footrope diameter", "mm"),
        "footrope_kg_per_m": V("G187", "Footrope kg/m", "kg/m"),
        "footrope_weight_air_kg": V("G188", "Footrope weight in air", "kg"),
        "coef_nylon": V("G189", "Coefficient nylon (in water)"),
        "coef_steel": V("G190", "Coefficient steel (in water)"),
        "footrope_weight_water_kgf": V("G191", "Footrope weight in water = W·0.87/10", "kgf"),
        "ballast_min_150_kg": V("F225", "Minimum ballast = ROUNDDOWN(M197), 150 HP", "kg"),
        "ballast_max_150_kg": V("F226", "Maximum ballast = ROUNDUP(L201), 150 HP", "kg"),
        "bottom_type": V("F227", "Bottom type"),
        "adjust_chain_m": V("F224", "Adjustment chain length", "m"),
        "adjust_chain_weight_kg": V("H224", "Adjustment chain weight", "kg"),
        "ballast_even_kg_m": V("E233", "Even ballast distribution", "kg/m"),
        "ballast_min_adjust_kg": V("G236", "Min ballast: adjustment chain share", "kg"),
        "ballast_min_bosom_kg": V("G237", "Min ballast: bosom share", "kg"),
        "ballast_min_wings_kg": V("G238", "Min ballast: wings share", "kg"),
        "ballast_min_adjust_kg_m": V("I236", "Min ballast: adjustment chain kg/m", "kg/m"),
        "ballast_min_bosom_kg_m": V("I237", "Min ballast: bosom kg/m", "kg/m"),
        "ballast_min_wings_kg_m": V("I238", "Min ballast: wings kg/m", "kg/m"),
        "ballast_max_adjust_kg": V("G243", "Max ballast: adjustment chain share", "kg"),
        "ballast_max_bosom_kg": V("G244", "Max ballast: bosom share", "kg"),
        "ballast_max_wings_kg": V("G245", "Max ballast: wings share", "kg"),
        "ballast_max_adjust_kg_m": V("I243", "Max ballast: adjustment chain kg/m", "kg/m"),
        "ballast_max_bosom_kg_m": V("I244", "Max ballast: bosom kg/m", "kg/m"),
        "ballast_max_wings_kg_m": V("I245", "Max ballast: wings kg/m", "kg/m"),
    },
    {
        "rn_std_kgf": _speed("C", 42, "RN standard ×1000", "kgf"),
        "rn_mod_kgf": _speed("D", 42, "RN modified ×1000", "kgf"),
        **_fridman_float_rows("150", 42, "150 HP"),
        **_fridman_float_rows("180", 55, "180 HP"),
        "float_diameter_mm": S(
            "D72:D82", "Float catalogue diameter", "mm", x="float_index", x_values=list(range(11))
        ),
        "float_unit_buoyancy_kgf": S(
            "E72:E82", "Float unit buoyancy", "kgf", x="float_index", x_values=list(range(11))
        ),
        "float_count_150": S(
            "F72:F82",
            "Floats needed = ROUND(F/unit), 150 HP",
            "",
            x="float_index",
            x_values=list(range(11)),
        ),
        "float_count_180": S(
            "G72:G82", "Floats needed, 180 HP", "", x="float_index", x_values=list(range(11))
        ),
        "speed_ms": _speed("E", 138, "Speed in m/s", "m/s"),
        "float_reynolds": _speed("H", 138, "Re = π·D²·v/ν — errata float_reynolds", ""),
        "float_cd": _speed("I", 138, "Float CD", ""),
        "float_drag_kgf": _speed("J", 138, "Float drag RB = ½·ρ·CD·(ρ/g)·πD²/4·v²·n", "kgf"),
        "ballast_std_150_kg": _speed(
            "L", 197, "Ballast = F1'+F2' − W_burlon, standard, 150 HP", "kg"
        ),
        "ballast_mod_150_kg": _speed("M", 197, "Ballast, modified, 150 HP", "kg"),
        "ballast_std_180_kg": _speed("L", 210, "Ballast, standard, 180 HP", "kg"),
        "ballast_mod_180_kg": _speed("M", 210, "Ballast, modified, 180 HP", "kg"),
    },
)

REMOLQUE: Spec = (
    {
        "footrope_m": V("F6", "Footrope", "m"),
        "door_spread_m": V("F7", "Door spread Ds", "m"),
        "sweeps_plus_bridle_m": V("F8", "Sweeps + upper bridle", "m"),
        "warp_length_m": V("F9", "Warp paid out", "m"),
        "net_length_no_bag_m": V("F10", "Net length without codend", "m"),
        "gallows_spacing_m": V("F11", "Distance between gallows", "m"),
        "dpa_a_m": V("F17", "DPA (A) = Ds·m / (sweeps+bridle + m)", "m"),
        "dpa_b_m": V("F19", "DPA (B) = Ds·L / (L + sweeps+bridle)", "m"),
        "warp_divergence_deg": V("E25", "δ2 = asin(0.5·(Ds − gallows)/Ls)", "°"),
        "bridle_divergence_deg": V("E29", "δ3 = asin(0.5·(Ds − DPA)/(sweeps+bridle))", "°"),
        "warp_declination_deg": V("E33", "δ1 = asin((depth + vessel depth)/Ls)", "°"),
        "ehp_150_hp": V("E70", "EHP 150 HP (Koyama)", "hp"),
        "ehp_180_hp": V("E71", "EHP 180 HP (Koyama)", "hp"),
        "warp_diameter_ehp_150_mm": V("F73", "Dw = 18 + 0.0034·EHP, 150 HP", "mm"),
        "warp_diameter_ehp_180_mm": V("F74", "Dw = 18 + 0.0034·EHP, 180 HP", "mm"),
        "warp_diameter_aguila_150_mm": V("E80", "Dw = 5.6822·ln(NHP) − 17.225, 150 HP", "mm"),
        "warp_diameter_aguila_180_mm": V("E81", "Dw = 5.6822·ln(NHP) − 17.225, 180 HP", "mm"),
        "warp_attack_angle_deg": V("E103", "Warp attack angle (=δ2)", "°"),
        "effective_depth_m": V("E105", "Effective depth", "m"),
        "warp_cd": V("E106", "Warp CD (nearest α in Nomura–Yamazaki table)"),
        "warp_diameter_mm": V("E110", "Warp diameter used (=E81)", "mm"),
        "warp_diameter_m": V("E111", "Warp diameter", "m"),
        "warp_length_used_m": V("E112", "Warp length used", "m"),
        "kinematic_viscosity_avg": V("F161", "ν average", "m²/s"),
        "warp_weight_air_kg_m": V(
            "E248", "Warp unit weight in air (avg 0.00368/0.00417·D²)", "kg/m"
        ),
        "warp_weight_water_a_kg_m": V("F250", "Warp unit weight in water 0.00305·D²", "kg/m"),
        "warp_weight_water_b_kg_m": V("F252", "Warp unit weight in water 0.87·W_air", "kg/m"),
        "effective_depth_used_m": V("F254", "Effective depth", "m"),
        "warp_length_m_sel": V("F255", "Warp paid out (selection block)", "m"),
        "warp_total_weight_air_kg": V("F256", "Total warp weight in air", "kg"),
        "warp_total_weight_water_kg": V("F257", "Total warp weight in water", "kg"),
        "warp_min_diameter_mm": V("E264", "Minimum warp diameter", "mm"),
        "warp_min_weight_air_kg_m": V("E265", "Minimum warp weight in air", "kg/m"),
        "warp_min_weight_water_kg_m": V("E266", "Minimum warp weight in water", "kg/m"),
        "warp_working_load_kgf": V("E267", "Working load = total drag at 3.5 kn (H123)", "kgf"),
        "warp_safety_factor": V("D271", "Safety factor"),
        "warp_min_breaking_load_kgf": V("E272", "Minimum breaking load = 4·working load", "kgf"),
    },
    {
        "speed_ms": _speed("C", 118, "Speed in m/s", "m/s"),
        "rn_std_kgf": _speed("D", 118, "RN standard ×1000", "kgf"),
        "rn_mod_kgf": _speed("E", 118, "RN modified ×1000", "kgf"),
        "float_drag_kgf": _speed("F", 118, "Float drag RB", "kgf"),
        "warp_drag_2_kgf": _speed("G", 118, "RW two warps = ½·CD·ρ/g·D·L·v²·2", "kgf"),
        "total_drag_std_kgf": _speed(
            "H", 118, "Total = RW + RB + RN std — errata warp_total_omits_doors", "kgf"
        ),
        "total_drag_mod_kgf": _speed("I", 118, "Total = RW + RB + RN mod", "kgf"),
        "warp_reynolds": _speed("D", 167, "Re = D·v/ν", ""),
        "warp_cd_cylinder": _speed("E", 167, "Cylinder CD (1.1 / 1.2)", ""),
        "warp_drag_cylinder_kgf": _speed("F", 167, "RW cylinder = ½·CD·ρ/g·D·L·v²", "kgf"),
        "warp_drag_cylinder_2_kgf": _speed("G", 167, "RW cylinder, two warps", "kgf"),
        "fridman_ft_fixed_150_kgf": _speed("C", 191, "FT fixed pitch 150 HP", "kgf"),
        "fridman_ft_variable_nozzle_150_kgf": _speed("D", 191, "FT variable+nozzle 150 HP", "kgf"),
        "warp_drag_5pct_fixed_kgf": _speed("E", 191, "RW = 5 % FT (PF)", "kgf"),
        "warp_drag_5pct_variable_kgf": _speed("F", 191, "RW = 5 % FT (PV+T)", "kgf"),
        "warp_drag_10pct_fixed_kgf": _speed("G", 191, "RW = 10 % FT (PF)", "kgf"),
        "warp_drag_10pct_variable_kgf": _speed("H", 191, "RW = 10 % FT (PV+T)", "kgf"),
        "warp_cd_maclennan": _speed("D", 227, "MacLennan CD = 2.11 − 12.24·v·Dw", ""),
    },
)

_NOMURA_ROWS = [
    (16, "bottom_2_panels"),
    (17, "bottom_2_panels_b"),
    (18, "bottom_4_8_panels"),
    (19, "pelagic_2_panels"),
    (20, "pelagic_4_8_panels"),
    (21, "bottom_small"),
    (22, "pair_trawl"),
    (23, "shrimp_single"),
    (24, "shrimp_twin"),
    (25, "pelagic_pair"),
]
_RATIO_NAMES = ["l/m", "l/b", "m/b", "a/b", "c/b", "d/b", "e/b", "f/b", "(d-c)/b"]

TABLAS: Spec = (
    {
        "kf_fixed_pitch": V("B6", "Fridman KF, fixed pitch"),
        "kf_variable_pitch_nozzle": V("B7", "Fridman KF, variable pitch + nozzle"),
        "pa_density_kg_m3": V("B36", "PA (nylon) density", "kg/m³"),
        "pa_1280_runnage_m_kg": V("C36", "Runnage of PA Rtex 1280", "m/kg"),
        "pa_1280_rtex": V("E36", "Rtex", "tex"),
        "pa_1280_twine_mm": V("F36", "Twine diameter PA 1280", "mm"),
        "pa_coef_seawater": V("G36", "Weight multiplier in sea water"),
        "pa_coef_freshwater": V("I36", "Weight multiplier in fresh water"),
        "pa_950_runnage_m_kg": V("C37", "Runnage of PA Rtex 950", "m/kg"),
        "pa_950_rtex": V("E37", "Rtex", "tex"),
        "pa_950_twine_mm": V("F37", "Twine diameter PA 950", "mm"),
        "door_fao_length_m": V("C247", "FAO flat wooden door: length", "m"),
        "door_fao_height_m": V("C248", "FAO flat wooden door: height", "m"),
        "door_fao_area_m2": V("C249", "FAO flat wooden door: projected area", "m²"),
        "door_fao_aspect_ratio": V("C250", "FAO door aspect ratio"),
        "door_fao_area_ratio": V("C251", "FAO door area ratio"),
        "door_fao_weight_air_kg": V("C252", "FAO door weight in air", "kg"),
        "door_fao_weight_coef": V("C253", "FAO door weight multiplier"),
        "door_fao_weight_water_kg": V("C254", "FAO door weight in water", "kg"),
        "chain_short_7mm_kg_m": V("C316", "Trawlex short-link 7 mm grade 80 chain", "kg/m"),
        "chain_long_19mm_kg_m": V("C317", "Trawlex long-link 19 mm grade 80 chain", "kg/m"),
    },
    {
        **{
            f"nomura_ratio_{name}": S(
                f"D{r}:L{r}",
                f"Nomura proportions: {name}",
                "",
                x="ratio",
                x_values=list(_RATIO_NAMES),
            )
            for r, name in _NOMURA_ROWS
        },
        "cut_ratio": S(
            "A49:A68", "Cut table: ratio", "", x="cut_code", x_values=None, x_cells="C49:C68"
        ),
        "cut_width_meshes": S(
            "E49:E68",
            "Cut table: meshes in width (a)",
            "",
            x="cut_code",
            x_values=None,
            x_cells="C49:C68",
        ),
        "cut_height_meshes": S(
            "F49:F68",
            "Cut table: meshes in height (d)",
            "",
            x="cut_code",
            x_values=None,
            x_cells="C49:C68",
        ),
        "sweep_delta_deg": S("A177:A197", "Sweep angle δ", "°", x="row", x_values=list(range(21))),
        "sweep_dremiere_ratio": S(
            "B177:B182", "Dremiere warp/sweep ratio", "", x="row", x_values=list(range(6))
        ),
        "sweep_length_allowed_m": S(
            "C177:C187", "Allowed sweep lengths", "m", x="row", x_values=list(range(11))
        ),
        "useful_percentages": S(
            "F177:F196", "Useful percentages", "", x="row", x_values=list(range(20))
        ),
        "nhp_possible": S(
            "H177:H216", "Possible NHP values", "hp", x="row", x_values=list(range(40))
        ),
        "dan_leno_height_m": S(
            "B202:B221",
            "Dan leno arm height by depth",
            "m",
            x="depth_m",
            x_values=None,
            x_cells="A202:A221",
        ),
        "door_fao_polar_cl": S(
            "C259:C264", "FAO door CL", "", x="angle_deg", x_values=None, x_cells="B259:B264"
        ),
        "door_fao_polar_cd": S(
            "D259:D264", "FAO door CD", "", x="angle_deg", x_values=None, x_cells="B259:B264"
        ),
        "door_morgere_polar_cl": S(
            "C281:C286",
            "Morgère oval door CL",
            "",
            x="angle_deg",
            x_values=None,
            x_cells="B281:B286",
        ),
        "door_morgere_polar_cd": S(
            "D281:D286",
            "Morgère oval door CD",
            "",
            x="angle_deg",
            x_values=None,
            x_cells="B281:B286",
        ),
        "rope_diameter_mm": S(
            "C293:C296",
            "Rope catalogue: diameter",
            "mm",
            x="rope",
            x_values=None,
            x_cells="B293:B296",
        ),
        "rope_kg_per_m": S(
            "E293:E296",
            "Rope catalogue: kg/m",
            "kg/m",
            x="rope",
            x_values=None,
            x_cells="B293:B296",
        ),
        "rope_strength_t": S(
            "F293:F296",
            "Rope catalogue: breaking strength",
            "t",
            x="rope",
            x_values=None,
            x_cells="B293:B296",
        ),
        "warp_catalogue_kg_per_m": S(
            "E338:E343",
            "Warp catalogue 6x19+1 Seale: kg/m",
            "kg/m",
            x="diameter_mm",
            x_values=None,
            x_cells="B338:B343",
        ),
        "warp_catalogue_strength_t": S(
            "F338:F343",
            "Warp catalogue 6x19+1 Seale: breaking strength",
            "t",
            x="diameter_mm",
            x_values=None,
            x_cells="B338:B343",
        ),
        "warp_by_depth_m": S(
            "B354:B383",
            "Warp to pay out by depth",
            "m",
            x="depth_m",
            x_values=None,
            x_cells="A354:A383",
        ),
        "warp_depth_ratio": S(
            "C354:C383", "Warp/depth ratio", "", x="depth_m", x_values=None, x_cells="A354:A383"
        ),
    },
)

SHEETS: dict[str, Spec] = {
    "Especie Blanco": ESPECIE,
    "Tipo de buques": BUQUES,
    "Potenc disponible para arrastre": POTENC,
    "Potencia Disponible Arrastre OK": POTENCIA_OK,
    "Paños de red y cortes": PANOS,
    "Cables Y Cabulleria": CABLES_CABULLERIA,
    "Mecánica de la Red": MECANICA,
    "Dimensiones de la Red": DIMENSIONES,
    "Resistencia de la RED": RESISTENCIA,
    "Portones y aparejamiento": PORTONES,
    "Flotación y Lastre": FLOTACION,
    "Cables de Remolque": REMOLQUE,
    "Tablas de Referencias": TABLAS,
}


# --------------------------------------------------------------------------------------
# Extracción
# --------------------------------------------------------------------------------------


def slug(name: str) -> str:
    """``"Resistencia de la RED"`` → ``"resistencia_de_la_red"`` (sin acentos ni ñ)."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")


def is_error(value: Any) -> bool:
    """Excel guarda los errores como texto ``#N/A``, ``#REF!``, ``#DIV/0!``…"""
    return isinstance(value, str) and value.startswith("#")


def clean(value: Any) -> Any:
    """Normaliza un valor cacheado: bool → bool, texto numérico → float, texto → strip."""
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        text = value.strip()
        if _NUMERIC_TEXT.match(text):
            return float(text)
        return text
    return str(value)


def _flat(sheet: str, ref: str) -> list[Any]:
    if ":" not in ref:
        return [workbook()[sheet][ref].value]
    return [v for row in rows(sheet, ref) for v in row]


def extract_sheet(sheet: str, spec: Spec) -> tuple[dict[str, Any], list[str]]:
    """Devuelve (documento JSON, lista de celdas omitidas) de una hoja."""
    values_spec, series_spec = spec
    skipped: list[str] = []
    values: dict[str, Any] = {}
    for key, v in values_spec.items():
        raw = workbook()[sheet][v.cell].value
        if raw is None or is_error(raw):
            skipped.append(f"{sheet}!{v.cell} ({key}): {raw!r}")
            continue
        entry: dict[str, Any] = {
            "cell": v.cell,
            "value": clean(raw),
            "label": v.label,
            "unit": v.unit,
        }
        if isinstance(raw, str) and isinstance(entry["value"], float):
            entry["coerced_from_text"] = True
        if v.static:
            entry["static"] = True
        values[key] = entry

    series: dict[str, Any] = {}
    for key, s in series_spec.items():
        raw_vals = _flat(sheet, s.cells)
        x_values = s.x_values if s.x_cells is None else [clean(v) for v in _flat(sheet, s.x_cells)]
        if x_values is None or len(x_values) != len(raw_vals):
            raise ValueError(f"{sheet}!{s.cells} ({key}): x_values no coincide con el rango")
        missing = [
            f"{s.cells.split(':')[0]}+{i}"
            for i, v in enumerate(raw_vals)
            if v is None or is_error(v)
        ]
        if len(missing) == len(raw_vals):
            skipped.append(f"{sheet}!{s.cells} ({key}): serie completamente vacía")
            continue
        cleaned = [None if v is None or is_error(v) else clean(v) for v in raw_vals]
        entry = {
            "x": s.x,
            "x_values": x_values,
            "cells": s.cells,
            "values": cleaned,
            "label": s.label,
            "unit": s.unit,
        }
        if s.static:
            entry["static"] = True
        if missing:
            entry["missing"] = missing
            for i, v in enumerate(raw_vals):
                if v is None or is_error(v):
                    skipped.append(f"{sheet}!{s.cells} ({key}) índice {i}: {v!r}")
        series[key] = entry

    doc = {
        "sheet": sheet,
        "generated_by": GENERATED_BY,
        "source": SOURCE,
        "values": values,
        "series": series,
    }
    return doc, skipped


def run(out_dir: Path = GOLDEN) -> list[Path]:
    """Extrae todas las hojas y escribe un JSON por hoja. Devuelve las rutas escritas."""
    if not XLSX.exists():
        raise FileNotFoundError(XLSX)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for sheet, spec in SHEETS.items():
        doc, skipped = extract_sheet(sheet, spec)
        for item in skipped:
            log.warning("omitido: %s", item)
        path = out_dir / f"{slug(sheet)}.json"
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        log.info(
            "%s → %s (%d valores, %d series, %d omitidos)",
            sheet,
            path.relative_to(out_dir.parent.parent),
            len(doc["values"]),
            len(doc["series"]),
            len(skipped),
        )
        written.append(path)
    return written


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    paths = run()
    print(f"{len(paths)} archivos escritos en {GOLDEN}")


if __name__ == "__main__":
    main()
