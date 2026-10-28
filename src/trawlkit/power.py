"""Potencia disponible para el arrastre: Fridman, Prado-Dremiere, Koyama, Nomura y Hamuro.

Reimplementa la hoja ``'Potencia Disponible Arrastre OK'`` del modelo Excel. Cada método estima la
fuerza de tiro (``FT``, kgf) que un buque de ``BHP`` HP en hélice puede ejercer a la velocidad de
arrastre ``v``:

* **Fridman**: ``FT = BHP·(KF − 0.7·v)`` con ``v`` en nudos (``E10:G18``).
* **Prado & Dremiere (FAO)**: bollard pull ``BP = BHP·0.9·pct/100·1000`` (``B60:E63``) y vía factor
  K (``I59:L62``); potencia nominal aparente ``APN = 0.09·BP`` (``B73:C76``); potencia de arrastre
  ``P = 0.75·K·APN`` (``K68:L77``) y bollard pull pescando ``BPF = 150·P/v`` (``C88:L111``).
* **Koyama**: ``EHP = K·0.6·BHP``; ``F = 75·EHP/v`` (``A160:L179``).
* **Nomura**: ``F = 0.8·K1·K2·K3·75·NHP/v`` (``E216:F224``).
* **Hamuro**: ``Ps = K1·K2·K3·NHP``; ``F = 75·Ps/v`` (``F259:L266``, ``E272:H280``).

Convenciones del Excel que se reproducen tal cual (ver docstrings):

* Koyama y Nomura convierten nudos a m/s con **0.514** (``H171``, ``B216``), Hamuro con **0.5144**
  (``B272``).
* El "NHP" de Nomura y Hamuro es ``MID("150 HP",1,3)`` = el BHP del buque (150/180), no los HP
  nominales (199.5/239.4) de ``'Potenc disponible'!C24``.
* El 150 de ``BPF = 150·P/v`` es una constante de conversión (≈ 75/0.5144 kgf·kn por HP) y se usa
  también para el buque de 180 HP (``D88 = 150·L68/A88``). Está en el Workbook (Prado y Dremière
  1990, «Pulling power of trawlers», PDF p. 102) con ``p`` = potencia disponible para el arrastre,
  que es lo que el Excel le pasa (``K68 = 0.75·K·APN``), no el BHP.
* La regla ``BP = BHP·0.9·pct/100`` no es del Workbook: es la regla práctica de remolcadores de
  Zahalka («Bollard Pull», Association of Hanseatic Marine Underwriters), que el libro Excel
  atribuye a Prado.
* Las tablas resumen de ``A295:I370`` son números pegados (estáticos) salvo la columna "Nomura",
  que en tres de las cuatro tablas enlaza a Hamuro (errata ``nomura_column_links_hamuro``).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from typing import Any, Literal

import numpy as np
import numpy.typing as npt
import yaml

from trawlkit.i18n import t
from trawlkit.io.loader import DATA_DIR
from trawlkit.io.schema import PropellerType, Vessel
from trawlkit.units import KNOT_TO_MS

FloatOrArray = float | npt.NDArray[np.float64]
Method = Literal["fridman", "prado", "koyama", "nomura", "hamuro"]

_PF = PropellerType.FIXED_PITCH
_PFT = PropellerType.FIXED_PITCH_NOZZLE
_PV = PropellerType.VARIABLE_PITCH
_PVT = PropellerType.VARIABLE_PITCH_NOZZLE

#: Ruta del YAML de coeficientes extraído del Excel.
POWER_COEFFICIENTS_PATH = DATA_DIR / "reference" / "power_coefficients.yaml"

# ----------------------------------------------------------------------------------------------
# Constantes (copiadas de trawlkit/data/reference/power_coefficients.yaml; test_power verifica
# la igualdad)
# ----------------------------------------------------------------------------------------------

#: Factor nudos → m/s usado por Koyama (``H171 = 0.514``) y Nomura (``B216 = H171``).
KNOT_TO_MS_KOYAMA: float = 0.514
#: 1 HP = 75 kgf·m/s (``L214``, ``C263``).
HP_IN_KGF_M_S: float = 75.0

#: Fridman: coeficiente empírico KF por hélice (``D10 = MID(E3,38,2)``, ``F10 = MID(E4,40,2)``).
FRIDMAN_KF: dict[PropellerType, float] = {
    PropellerType.FIXED_PITCH: 10.0,
    PropellerType.VARIABLE_PITCH_NOZZLE: 15.0,
}
#: Fridman: pendiente de la caída de FT con la velocidad (``0.7·v``).
FRIDMAN_SPEED_SLOPE: float = 0.7

# Fuente (Fase 19.8b): la regla BP = BHP·0.9·{1.10, 1.20, 1.25, 1.40}/100 [t] está transcrita de
# Capt. P. Zahalka (Association of Hanseatic Marine Underwriters), «Bollard Pull» (zahalkabollard):
# «Fixed pitch propeller (freewheeling): BHP x 0,9 x 1,10 / 100 = (t)» … «Controllable pitch
# propeller and kort-nozzle: BHP x 0,9 x 1,40 / 100 = (t)». Es una regla práctica de
# remolcadores, «rough estimates» según el propio autor; el libro Excel (giamportone2024) la
# atribuye a Prado, pero no está en el Fisherman's Workbook (Prado y Dremière 1990, PDF p. 102,
# «Pulling power of trawlers»), que da BP0 = 10-12 kg por BHP con hélice fija y 13-16 kg por HP de
# APN con paso variable o tobera (control cruzado: la regla da 9.9-12.6 kgf/BHP).
# anker2022bollard queda como fuente secundaria. Los números no se cambian: reproducen el libro
# Excel.
#: Regla de Zahalka (atribuida a Prado en el Excel): factor base del bollard pull (``BHP·0.9``).
PRADO_BASE_FACTOR: float = 0.9
#: Zahalka: porcentaje por tipo de hélice (``A49:A55``: 1.10/1.20/1.25/1.40); ver arriba.
PRADO_PROPELLER_PERCENT: dict[PropellerType, float] = {
    PropellerType.FIXED_PITCH: 1.10,
    PropellerType.FIXED_PITCH_NOZZLE: 1.20,
    PropellerType.VARIABLE_PITCH: 1.25,
    PropellerType.VARIABLE_PITCH_NOZZLE: 1.40,
}
#: Prado: factor K "según potencia" (``K52:L55``) por hélice, indexado por BHP tabulado.
PRADO_K_BY_POWER: dict[PropellerType, dict[int, float]] = {
    PropellerType.FIXED_PITCH: {150: 11.23, 180: 11.21},
    PropellerType.FIXED_PITCH_NOZZLE: {150: 13.35, 180: 13.32},
    PropellerType.VARIABLE_PITCH: {150: 11.73, 180: 11.71},
    PropellerType.VARIABLE_PITCH_NOZZLE: {150: 13.73, 180: 13.71},
}
#: Conversión t → HP del bollard pull vía K (``J59 = I59·100/1.36``).
PRADO_T_TO_HP: float = 100.0 / 1.36
#: Prado: ``APN = 0.09·BP`` (``B73``).
PRADO_APN_FACTOR: float = 0.09
#: Prado: fracción de la APN disponible para el arrastre (``K68 = 0.75·K·APN``).
PRADO_AVAILABLE_FRACTION: float = 0.75
#: Prado: constante HP → kgf·kn de ``BPF = 150·P/v`` (``C88``). Transcrita del Workbook (Prado y
#: Dremière 1990, PDF p. 102, imagen AH827E183): «BP (kg) = 150 × p (HP) / trawling speed (knots)»
#: con ``p`` la potencia disponible para el arrastre, ``p = 0.75·k·(BHP o ANP)``.
PRADO_BPF_CONVERSION: float = 150.0


@dataclass(frozen=True)
class PradoRow:
    """Fila de la tabla ``I68:L77`` (potencia disponible para el arrastre, Prado)."""

    key: str
    propeller: PropellerType
    high_rpm: bool | None
    k: float
    cell_150: str
    cell_180: str


#: Las diez filas de ``I68:L77`` en el orden del Excel; ``key`` coincide con los golden.
PRADO_ROWS: tuple[PradoRow, ...] = (
    PradoRow("fixed_high_rpm", _PF, True, 0.20, "K68", "L68"),
    PradoRow("fixed_low_rpm_k25", _PF, False, 0.25, "K69", "L69"),
    PradoRow("fixed_low_rpm_k28", _PF, False, 0.28, "K70", "L70"),
    PradoRow("fixed_nozzle_high_rpm", _PFT, True, 0.20, "K71", "L71"),
    PradoRow("fixed_nozzle_low_rpm_k25", _PFT, False, 0.25, "K72", "L72"),
    PradoRow("fixed_nozzle_low_rpm_k28", _PFT, False, 0.28, "K73", "L73"),
    PradoRow("variable_k28", _PV, None, 0.28, "K74", "L74"),
    PradoRow("variable_k30", _PV, None, 0.30, "K75", "L75"),
    PradoRow("variable_nozzle_k28", _PVT, None, 0.28, "K76", "L76"),
    PradoRow("variable_nozzle_k30", _PVT, None, 0.30, "K77", "L77"),
)
#: Filas promediadas en ``C123`` (paso fijo: las 5 de PF/PF+T de ``C88:K88`` más ``C103``).
PRADO_BPF_AVG_FIXED_KEYS: tuple[str, ...] = tuple(r.key for r in PRADO_ROWS[:6])
#: Filas promediadas en ``E123`` (paso variable: ``E103, G103, I103, K103``).
PRADO_BPF_AVG_VARIABLE_KEYS: tuple[str, ...] = tuple(r.key for r in PRADO_ROWS[6:])

#: Koyama: ``BHP_F = 0.6·BHP`` (``C169 = 150·0.6``).
KOYAMA_BHP_FRACTION: float = 0.6
#: Koyama: K para buques de 15-55 t y < 600 BHP (``M165``); 0.18 para 1200-1500 BHP (``M166:M167``).
KOYAMA_K_SMALL: float = 0.15
KOYAMA_K_LARGE: float = 0.18
KOYAMA_BHP_SMALL_MAX: float = 600.0

#: Nomura: K1 utilización del motor (``L205``), K2 estado del mar (``L206``).
NOMURA_K1: float = 0.85
NOMURA_K2: float = 0.85
#: Nomura: rangos de K3 (eficiencia de propulsión) por tamaño de arrastrero (``L208:L211``).
NOMURA_K3_RANGES: dict[str, tuple[float, ...]] = {
    "small": (0.17, 0.20),
    "medium": (0.20,),
    "large_300_1000_t": (0.24, 0.26),
    "large_over_1000_t": (0.28, 0.29),
}
#: Nomura: K3 usado por el Excel en ``E216`` (``MID(L208,1,4)`` = cota inferior de "pequeños").
NOMURA_K3_EXCEL: float = 0.17
#: Nomura: fracción de la resistencia total atribuida a la red (``L213``).
NOMURA_NET_SHARE: float = 0.8

#: Hamuro: K1 = 82.5 % de NHP (``C254``), K2 estado del mar (``F257``).
HAMURO_K1: float = 0.825
HAMURO_K2: float = 0.85


@dataclass(frozen=True)
class HamuroRow:
    """Columna de la tabla de Hamuro ``F255:L259`` (configuración de hélice y K3)."""

    key: str
    propeller: PropellerType
    high_rpm: bool
    k3: float
    cell_150: str
    cell_180: str


#: Las siete configuraciones de ``F255:L258``; ``key`` coincide con los golden ``hamuro_ps_*``.
HAMURO_ROWS: tuple[HamuroRow, ...] = (
    HamuroRow("fixed_low_rpm", _PF, False, 0.265, "F259", "F266"),
    HamuroRow("fixed_high_rpm", _PF, True, 0.20, "G259", "G266"),
    HamuroRow("fixed_nozzle_high_rpm", _PFT, True, 0.24, "H259", "H266"),
    HamuroRow("fixed_nozzle_low_rpm", _PFT, False, 0.28, "I259", "I266"),
    HamuroRow("variable_high_rpm", _PV, True, 0.25, "J259", "J266"),
    HamuroRow("variable_nozzle_low_rpm", _PVT, False, 0.27, "K259", "K266"),
    HamuroRow("variable_nozzle_high_rpm", _PVT, True, 0.30, "L259", "L266"),
)
#: "Peor caso" de Hamuro: ``G260 = AVERAGE(F259:I259)`` (paso fijo, con y sin tobera).
HAMURO_WORST_KEYS: tuple[str, ...] = tuple(r.key for r in HAMURO_ROWS[:4])
#: "Mejor caso" de Hamuro: ``K260 = AVERAGE(J259:L259)`` (paso variable, con y sin tobera).
HAMURO_BEST_KEYS: tuple[str, ...] = tuple(r.key for r in HAMURO_ROWS[4:])


# ----------------------------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------------------------


@cache
def load_power_coefficients() -> dict[str, Any]:
    """Lee ``trawlkit/data/reference/power_coefficients.yaml`` (coeficientes del Excel)."""
    with POWER_COEFFICIENTS_PATH.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{POWER_COEFFICIENTS_PATH}: expected a mapping at top level")
    return data


def _like(result: npt.NDArray[np.float64], template: FloatOrArray) -> FloatOrArray:
    """Devuelve ``float`` si ``template`` es escalar; si no, el array."""
    if np.ndim(template) == 0:
        return float(result)
    return result


def _check_positive(name: str, value: FloatOrArray) -> None:
    if np.any(np.asarray(value, dtype=float) <= 0):
        raise ValueError(f"{name} must be positive, got {value}")


def _rows_for(
    rows: tuple[PradoRow, ...] | tuple[HamuroRow, ...], propeller: PropellerType, high_rpm: bool
) -> list[Any]:
    out = [
        r
        for r in rows
        if r.propeller == propeller and (r.high_rpm is None or r.high_rpm == high_rpm)
    ]
    if not out:
        rpm = "high" if high_rpm else "low"
        raise ValueError(f"no tabulated coefficient for {propeller.value} at {rpm} RPM")
    return out


# ----------------------------------------------------------------------------------------------
# Fridman
# ----------------------------------------------------------------------------------------------


def fridman_kf(propeller: PropellerType) -> float:
    """KF de Fridman para la hélice (``D10`` → 10 paso fijo; ``F10`` → 15 paso variable + tobera).

    El Excel sólo tabula estas dos configuraciones; para PF+T y PV se lanza ``ValueError``. No se
    halló una fuente publicada con el KF de esas hélices (Fase 19.4: el libro de Fridman de 1986
    no está en línea), así que no se interpola: el caso debe indicar ``fridman_kf``.
    """
    try:
        return FRIDMAN_KF[propeller]
    except KeyError:
        raise ValueError(
            t(
                "KF de Fridman no tabulado para la hélice {prop!r}: el libro sólo da PF (10) y "
                "PV+T (15) y no se halló una fuente publicada para PF+T ni PV; indique "
                "fridman_kf (o el diámetro de la hélice para ver el tiro por la hélice)",
                prop=propeller.value,
            )
        ) from None


def fridman_towing_force_kgf(
    bhp: float, v_kn: FloatOrArray, kf: float, slope: float = FRIDMAN_SPEED_SLOPE
) -> FloatOrArray:
    """Fuerza de tiro disponible según Fridman.

    ``FT = BHP·(KF − 0.7·v)``, con ``v`` en nudos, ``KF`` = 10 (paso fijo) o 15 (paso variable +
    tobera). Unidades: kgf. Autor: Fridman. Celdas ``E10 = C10*(D10-(0.7*B10))`` (PF, 150 HP) y
    ``G10 = C10*(F10-(0.7*B10))`` (PV+T); ``E22``/``G22`` para 180 HP.
    """
    v = np.asarray(v_kn, dtype=float)
    return _like(bhp * (kf - slope * v), v_kn)


# ----------------------------------------------------------------------------------------------
# Prado & Dremiere (FAO)
# ----------------------------------------------------------------------------------------------


def prado_propeller_percent(propeller: PropellerType) -> float:
    """Porcentaje de Prado por hélice (``A49:A55``: 1.10 PF, 1.20 PF+T, 1.25 PV, 1.40 PV+T)."""
    return PRADO_PROPELLER_PERCENT[propeller]


def prado_k_factor(propeller: PropellerType, bhp: float) -> float:
    """Factor K "según potencia" de Prado (``K52:L55``).

    La tabla sólo tiene columnas para 150 y 180 HP; se toma la columna de BHP tabulado más cercano
    (en empate, el menor). Para otras potencias el valor es una aproximación.
    """
    table = PRADO_K_BY_POWER[propeller]
    nearest = min(table, key=lambda p: (abs(p - bhp), p))
    return table[nearest]


def bollard_pull_kgf(
    bhp: float, propeller: PropellerType | float, base_factor: float = PRADO_BASE_FACTOR
) -> float:
    """Bollard pull (tiro a punto fijo) del libro Excel (bloque «Prado & Dremiere»).

    ``BP = BHP·0.9·(pct/100)·1000`` con ``pct`` = 1.10 (PF), 1.20 (PF+T), 1.25 (PV), 1.40 (PV+T).
    La regla es de Zahalka («Bollard Pull», regla práctica de remolcadores, estimación gruesa), no
    del Workbook (ver :data:`PRADO_BASE_FACTOR`). ``propeller`` admite el tipo de hélice o el
    porcentaje directamente. Unidades: kgf. Celda ``B60 = (C10*(0.9)*(1.1/100)*1000)`` (150 HP);
    ``D60 = C22*0.9*(1.1/100)*1000`` (180 HP).
    """
    pct = prado_propeller_percent(propeller) if isinstance(propeller, PropellerType) else propeller
    return bhp * base_factor * (pct / 100.0) * 1000.0


def bollard_pull_t(
    bhp: float, propeller: PropellerType | float, base_factor: float = PRADO_BASE_FACTOR
) -> float:
    """Bollard pull de Prado en toneladas (``C60 = B60/1000``)."""
    return bollard_pull_kgf(bhp, propeller, base_factor) / 1000.0


def bollard_pull_k_t(bhp: float, k: float) -> float:
    """Bollard pull vía factor K: ``BP = K·BHP/1000`` [t] (``I59 = K52*(C10/1000)``)."""
    return k * (bhp / 1000.0)


def bollard_pull_k_hp(bp_k_t: float, t_to_hp: float = PRADO_T_TO_HP) -> float:
    """Equivalente en HP del bollard pull vía K: ``(BP·100)/1.36`` (``J59 = (I59*100)/1.36``)."""
    return bp_k_t * t_to_hp


def bollard_pull_avg_kgf(bp_prado_kgf: float, bp_k_t: float) -> float:
    """Promedio del bollard pull por porcentaje y vía K.

    ``BP_avg = AVERAGE(BP_prado, BP_K·1000)`` en kgf. Celda ``G58 = AVERAGE(B60,(I59*1000))`` para
    150 HP; para 180 HP el Excel promedia en toneladas y multiplica después
    (``G65 = AVERAGE(E60,K59)*1000``), que es lo mismo salvo redondeo de coma flotante.
    """
    return (bp_prado_kgf + bp_k_t * 1000.0) / 2.0


def apparent_nominal_power_hp(bp_avg_kgf: float, factor: float = PRADO_APN_FACTOR) -> float:
    """Potencia nominal aparente de Prado: ``APN = 0.09·BP_avg`` [HP] (``B73 = 0.09*G58``)."""
    return factor * bp_avg_kgf


def trawling_power_hp(
    apn_hp: float, k: float, available_fraction: float = PRADO_AVAILABLE_FRACTION
) -> float:
    """Potencia disponible para el arrastre según Prado.

    ``P = 0.75·K·APN`` con K = 0.20 (PF/PF+T alta RPM), 0.25 y 0.28 (PF/PF+T baja RPM), 0.28 y 0.30
    (PV/PV+T). Unidades: HP. Celdas ``K68 = 0.75*0.2*B73`` … ``K77 = 0.75*0.3*B76`` (150 HP),
    ``L68:L77`` (180 HP).
    """
    return available_fraction * k * apn_hp


def bollard_pull_fishing_kgf(
    power_hp: float, v_kn: FloatOrArray, conversion: float = PRADO_BPF_CONVERSION
) -> FloatOrArray:
    """Bollard pull pescando (BPF) de Prado.

    ``BPF = 150·P/v`` con ``P`` la potencia de arrastre [HP] y ``v`` en nudos. El 150 es una
    constante de conversión HP → kgf·kn (≈ 75 kgf·m/s / 0.5144 m/s por nudo ≈ 145.8, redondeado):
    **no** es el BHP del buque; el Excel usa el mismo 150 para el buque de 180 HP
    (``D88 = 150*L68/A88``). Unidades: kgf. Celda ``C88 = (150*K68)/A88``.

    Fuente: Workbook (Prado y Dremière 1990, PDF p. 102), «BP (kg) = 150 × p (HP) / trawling speed
    (knots)», con ``p = 0.75·k·(BHP o ANP)`` la potencia disponible para el arrastre. El Excel le
    pasa ``P = 0.75·K·APN`` (:func:`trawling_power_hp`), es decir la ``p`` del Workbook y no el BHP;
    usa la APN también en las filas de paso fijo, donde el Workbook admite el BHP (con la regla del
    Excel la APN del buque de 150 HP de paso fijo es ≈ 143 HP, *derivado*).
    """
    v = np.asarray(v_kn, dtype=float)
    _check_positive("v_kn", v)
    return _like(conversion * power_hp / v, v_kn)


def prado_trawling_power_table(bhp: float) -> dict[str, float]:
    """Potencia de arrastre de Prado para las diez filas de ``I68:L77`` (clave → HP).

    Cada fila usa el bollard pull promedio (``G58:G61``) y la APN (``B73:B76``) de su hélice.
    """
    out: dict[str, float] = {}
    for row in PRADO_ROWS:
        bp = bollard_pull_kgf(bhp, row.propeller)
        bp_k = bollard_pull_k_t(bhp, prado_k_factor(row.propeller, bhp))
        apn = apparent_nominal_power_hp(bollard_pull_avg_kgf(bp, bp_k))
        out[row.key] = trawling_power_hp(apn, row.k)
    return out


def prado_bpf_table(bhp: float, speeds_kn: FloatOrArray) -> dict[str, npt.NDArray[np.float64]]:
    """BPF de Prado para las diez filas (clave → array sobre ``speeds_kn``), ``C88:L111``."""
    v = np.atleast_1d(np.asarray(speeds_kn, dtype=float))
    return {
        key: np.asarray(bollard_pull_fishing_kgf(p, v), dtype=float)
        for key, p in prado_trawling_power_table(bhp).items()
    }


def bollard_pull_fishing_avg_kgf(
    bhp: float, speeds_kn: FloatOrArray, propeller_family: Literal["fixed", "variable"]
) -> npt.NDArray[np.float64]:
    """Promedio del BPF por familia de hélice (``C123:F131``).

    * ``"fixed"``: ``C123 = AVERAGE(C88,E88,G88,I88,K88,C103)`` — las seis filas de paso fijo
      (con y sin tobera, alta y baja RPM);
    * ``"variable"``: ``E123 = AVERAGE(E103,G103,I103,K103)`` — las cuatro filas de paso variable.

    ``D123``/``F123`` son las mismas fórmulas para 180 HP. Unidades: kgf.
    """
    keys = PRADO_BPF_AVG_FIXED_KEYS if propeller_family == "fixed" else PRADO_BPF_AVG_VARIABLE_KEYS
    table = prado_bpf_table(bhp, speeds_kn)
    stacked = np.vstack([table[k] for k in keys])
    return np.asarray(stacked.mean(axis=0), dtype=float)


# ----------------------------------------------------------------------------------------------
# Koyama
# ----------------------------------------------------------------------------------------------


def koyama_k(bhp: float) -> float:
    """K de Koyama según la tabla ``J164:M167``: 0.15 para < 600 BHP, 0.18 para 1200-1500 BHP."""
    return KOYAMA_K_SMALL if bhp < KOYAMA_BHP_SMALL_MAX else KOYAMA_K_LARGE


def koyama_bhp_f_hp(bhp: float, fraction: float = KOYAMA_BHP_FRACTION) -> float:
    """``BHP_F = 0.6·BHP`` [HP] (``C169 = 150*0.6``)."""
    return bhp * fraction


def koyama_ehp_hp(bhp_f_hp: float, k: float) -> float:
    """``EHP = K·BHP_F`` [HP] (``C171 = C170*C169``)."""
    return k * bhp_f_hp


def koyama_ehp_kgf_m_s(ehp_hp: float, hp_in_kgf_m_s: float = HP_IN_KGF_M_S) -> float:
    """``EHP·75`` [kgf·m/s] (``C172 = C171*75``)."""
    return ehp_hp * hp_in_kgf_m_s


def koyama_pull_kgf(
    bhp: float,
    k: float,
    v_ms: FloatOrArray,
    bhp_fraction: float = KOYAMA_BHP_FRACTION,
    hp_in_kgf_m_s: float = HP_IN_KGF_M_S,
) -> FloatOrArray:
    """Tiro disponible según Koyama.

    ``F = 75·K·0.6·BHP / v`` con ``v`` en m/s. En el Excel la velocidad es ``v = 0.514·kn``
    (``H171 = 0.514``, ``H172 = (G172*H171)/G171``), no 0.5144; use
    :func:`koyama_pull_series_kgf` para reproducirlo desde nudos. Unidades: kgf. Autor: Koyama.
    Celda ``K171 = C172/H171`` (150 HP), ``L171 = D172/H171`` (180 HP).
    """
    v = np.asarray(v_ms, dtype=float)
    _check_positive("v_ms", v)
    ehp = koyama_ehp_kgf_m_s(koyama_ehp_hp(koyama_bhp_f_hp(bhp, bhp_fraction), k), hp_in_kgf_m_s)
    return _like(ehp / v, v_ms)


def koyama_pull_series_kgf(
    bhp: float,
    speeds_kn: FloatOrArray,
    k: float = KOYAMA_K_SMALL,
    knot_to_ms: float = KNOT_TO_MS_KOYAMA,
) -> FloatOrArray:
    """Tiro de Koyama sobre velocidades en nudos con el factor 0.514 del Excel (``K171:L179``)."""
    v = np.asarray(speeds_kn, dtype=float) * knot_to_ms
    return _like(np.asarray(koyama_pull_kgf(bhp, k, v), dtype=float), speeds_kn)


# ----------------------------------------------------------------------------------------------
# Nomura
# ----------------------------------------------------------------------------------------------


def nomura_k3_average(
    ranges: dict[str, tuple[float, ...]] | None = None,
) -> float:
    """Promedio de todas las cotas de K3 de ``L208:L211`` (``L212``; = 0.2342857)."""
    values = [v for r in (ranges or NOMURA_K3_RANGES).values() for v in r]
    return float(np.mean(values))


def nomura_pull_kgf(
    nhp: float,
    k1: float,
    k2: float,
    k3: float,
    v_ms: FloatOrArray,
    share: float = NOMURA_NET_SHARE,
    hp_in_kgf_m_s: float = HP_IN_KGF_M_S,
) -> FloatOrArray:
    """Tiro disponible para la red según Nomura.

    ``F = 0.8·K1·K2·K3·75·NHP / v`` con K1 = 0.85 (utilización del motor), K2 = 0.85 (estado del
    mar), K3 = eficiencia de propulsión (el Excel usa 0.17, ``MID(L208,1,4)``, cota inferior de
    "arrastreros pequeños"), 0.8 la fracción de la resistencia atribuida a la red y ``v`` en m/s.
    El Excel usa ``NHP = MID("150 HP",1,3)`` = BHP y ``v = 0.514·kn`` (``B216 = H171``).
    Unidades: kgf. Autor: Nomura. Celda
    ``E216 = (L213*L205*L206*MID(L208,1,4)*MID(L214,1,2)*MID(E213,1,3))/B216``.
    """
    v = np.asarray(v_ms, dtype=float)
    _check_positive("v_ms", v)
    return _like(share * k1 * k2 * k3 * hp_in_kgf_m_s * nhp / v, v_ms)


def nomura_pull_series_kgf(
    nhp: float,
    speeds_kn: FloatOrArray,
    k1: float = NOMURA_K1,
    k2: float = NOMURA_K2,
    k3: float = NOMURA_K3_EXCEL,
    share: float = NOMURA_NET_SHARE,
    knot_to_ms: float = KNOT_TO_MS_KOYAMA,
) -> FloatOrArray:
    """Tiro de Nomura sobre velocidades en nudos con el factor 0.514 del Excel (``E216:F224``)."""
    v = np.asarray(speeds_kn, dtype=float) * knot_to_ms
    return _like(np.asarray(nomura_pull_kgf(nhp, k1, k2, k3, v, share), dtype=float), speeds_kn)


# ----------------------------------------------------------------------------------------------
# Hamuro
# ----------------------------------------------------------------------------------------------


def hamuro_k3(propeller: PropellerType, high_rpm: bool) -> float:
    """K3 de Hamuro por hélice y régimen (``F258:L258``); PV a baja RPM no está tabulado."""
    row: HamuroRow = _rows_for(HAMURO_ROWS, propeller, high_rpm)[0]
    return row.k3


def hamuro_ps_hp(nhp: float, k1: float, k2: float, k3: float) -> float:
    """Potencia de arrastre de Hamuro: ``Ps = K1·K2·K3·NHP`` [HP].

    K1 = 0.825 (82.5 % de NHP), K2 = 0.85 (estado del mar), K3 según hélice y RPM (0.265 PF<300 …
    0.30 PV+T>300). El Excel usa ``NHP = MID("150 HP",1,3)`` = BHP. Autor: Hamuro (Tokyo Univ.
    Fisheries). Celda ``F259 = PRODUCT(F256,F257,F258,MID(F254,1,3))``.
    """
    return k1 * k2 * k3 * nhp


def hamuro_ps_table(nhp: float, k1: float = HAMURO_K1, k2: float = HAMURO_K2) -> dict[str, float]:
    """``Ps`` para las siete configuraciones de ``F259:L259`` (clave → HP)."""
    return {row.key: hamuro_ps_hp(nhp, k1, k2, row.k3) for row in HAMURO_ROWS}


def hamuro_ps_average_hp(
    nhp: float, case: Literal["worst", "best"], k1: float = HAMURO_K1, k2: float = HAMURO_K2
) -> float:
    """Promedio de ``Ps`` de Hamuro.

    Peor caso: ``G260 = AVERAGE(F259:I259)`` (paso fijo); mejor caso: ``K260 = AVERAGE(J259:L259)``
    (paso variable). ``G267``/``K267`` para 180 HP. Unidades: HP.
    """
    keys = HAMURO_WORST_KEYS if case == "worst" else HAMURO_BEST_KEYS
    table = hamuro_ps_table(nhp, k1, k2)
    return float(np.mean([table[k] for k in keys]))


def hamuro_pull_kgf(
    ps_hp: float, v_ms: FloatOrArray, hp_in_kgf_m_s: float = HP_IN_KGF_M_S
) -> FloatOrArray:
    """Tiro disponible según Hamuro: ``F = 75·Ps / v`` con ``v`` en m/s.

    El Excel usa ``v = 0.5144·kn`` (``B272``), a diferencia de Koyama/Nomura. Unidades: kgf.
    Celda ``E272 = MID($C$263,1,2)*$F$259/B272`` (PF<300 RPM, 150 HP); ``F272`` usa ``L259``
    (PV+T>300), ``G272``/``H272`` los equivalentes de 180 HP (``F266``/``L266``).
    """
    v = np.asarray(v_ms, dtype=float)
    _check_positive("v_ms", v)
    return _like(hp_in_kgf_m_s * ps_hp / v, v_ms)


def hamuro_pull_series_kgf(
    nhp: float,
    speeds_kn: FloatOrArray,
    k3: float,
    k1: float = HAMURO_K1,
    k2: float = HAMURO_K2,
    knot_to_ms: float = KNOT_TO_MS,
) -> FloatOrArray:
    """Tiro de Hamuro sobre velocidades en nudos (``E272:H280``, factor 0.5144)."""
    v = np.asarray(speeds_kn, dtype=float) * knot_to_ms
    ps = hamuro_ps_hp(nhp, k1, k2, k3)
    return _like(np.asarray(hamuro_pull_kgf(ps, v), dtype=float), speeds_kn)


# ----------------------------------------------------------------------------------------------
# Curvas por buque y resumen
# ----------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class PowerCurves:
    """Fuerza de tiro disponible [kgf] por método, sobre un vector de velocidades [kn].

    ``prado_kgf`` es el promedio de las filas de Prado que coinciden con la hélice y el régimen
    del buque (una fila para PF/PF+T alta RPM, dos para el resto); ``nomura_kgf`` y ``hamuro_kgf``
    usan ``nhp`` (por defecto el BHP, como el Excel).
    """

    bhp: float
    propeller: PropellerType
    high_rpm: bool
    speeds_kn: npt.NDArray[np.float64]
    fridman_kgf: npt.NDArray[np.float64]
    prado_kgf: npt.NDArray[np.float64]
    koyama_kgf: npt.NDArray[np.float64]
    nomura_kgf: npt.NDArray[np.float64]
    hamuro_kgf: npt.NDArray[np.float64]

    def by_method(self, method: Method) -> npt.NDArray[np.float64]:
        """Serie de un método por nombre."""
        return {
            "fridman": self.fridman_kgf,
            "prado": self.prado_kgf,
            "koyama": self.koyama_kgf,
            "nomura": self.nomura_kgf,
            "hamuro": self.hamuro_kgf,
        }[method]

    @property
    def average_kgf(self) -> npt.NDArray[np.float64]:
        """Promedio de los cinco métodos (como ``I300 = AVERAGE(D300:H300)``)."""
        stacked = np.vstack(
            [self.fridman_kgf, self.prado_kgf, self.koyama_kgf, self.nomura_kgf, self.hamuro_kgf]
        )
        return np.asarray(stacked.mean(axis=0), dtype=float)

    def to_dict(self) -> dict[str, Any]:
        """Serializa con las series como listas."""
        return {
            "bhp": self.bhp,
            "propeller": self.propeller.value,
            "high_rpm": self.high_rpm,
            "speeds_kn": self.speeds_kn.tolist(),
            "fridman_kgf": self.fridman_kgf.tolist(),
            "prado_kgf": self.prado_kgf.tolist(),
            "koyama_kgf": self.koyama_kgf.tolist(),
            "nomura_kgf": self.nomura_kgf.tolist(),
            "hamuro_kgf": self.hamuro_kgf.tolist(),
            "average_kgf": self.average_kgf.tolist(),
        }


def power_curves(
    vessel: Vessel,
    speeds_kn: FloatOrArray,
    *,
    kf: float | None = None,
    nhp: float | None = None,
    koyama_k_value: float | None = None,
    nomura_k3: float = NOMURA_K3_EXCEL,
) -> PowerCurves:
    """Curvas de tiro disponible para un buque del catálogo por los cinco métodos.

    * Fridman: ``kf`` por defecto según :func:`fridman_kf` (sólo PF y PV+T tabulados);
    * Prado: promedio de las filas de ``I68:L77`` compatibles con hélice y RPM;
    * Koyama: ``k`` según :func:`koyama_k` (0.15 por debajo de 600 BHP), ``v = 0.514·kn``;
    * Nomura: K1 = K2 = 0.85, K3 = 0.17, ``v = 0.514·kn``;
    * Hamuro: K3 según hélice y RPM, ``v = 0.5144·kn``.

    ``nhp`` por defecto es el BHP (convención del Excel para Nomura y Hamuro).
    """
    v = np.atleast_1d(np.asarray(speeds_kn, dtype=float))
    bhp = vessel.bhp
    nhp_val = bhp if nhp is None else nhp
    kf_val = fridman_kf(vessel.propeller) if kf is None else kf
    k_koyama = koyama_k(bhp) if koyama_k_value is None else koyama_k_value

    fridman = np.asarray(fridman_towing_force_kgf(bhp, v, kf_val), dtype=float)
    table = prado_bpf_table(bhp, v)
    prado_rows: list[PradoRow] = _rows_for(PRADO_ROWS, vessel.propeller, vessel.high_rpm)
    prado = np.asarray(np.vstack([table[r.key] for r in prado_rows]).mean(axis=0), dtype=float)
    koyama = np.asarray(koyama_pull_series_kgf(bhp, v, k_koyama), dtype=float)
    nomura = np.asarray(nomura_pull_series_kgf(nhp_val, v, k3=nomura_k3), dtype=float)
    hamuro = np.asarray(
        hamuro_pull_series_kgf(nhp_val, v, hamuro_k3(vessel.propeller, vessel.high_rpm)),
        dtype=float,
    )
    return PowerCurves(
        bhp=bhp,
        propeller=vessel.propeller,
        high_rpm=vessel.high_rpm,
        speeds_kn=v,
        fridman_kgf=fridman,
        prado_kgf=prado,
        koyama_kgf=koyama,
        nomura_kgf=nomura,
        hamuro_kgf=hamuro,
    )


def available_towing_force_kgf(
    vessel: Vessel, speeds_kn: FloatOrArray, method: Method = "fridman", **kwargs: Any
) -> npt.NDArray[np.float64]:
    """Fuerza de tiro disponible [kgf] de un buque por el método indicado (Fridman por defecto)."""
    return power_curves(vessel, speeds_kn, **kwargs).by_method(method)


@dataclass(frozen=True)
class FridmanSummary:
    """Resumen ``'Potencia OK'!L11:O19``: FT de Fridman para hélice PF y PV+T de un buque.

    Para 150 HP son las columnas ``L`` (``=E10``) y ``M`` (``=G10``); para 180 HP, ``N`` (``=E22``)
    y ``O`` (``=G22``). Las columnas ``J``/``K`` (RN de la red) proceden de
    ``'Resistencia de la RED'`` y viven en :mod:`trawlkit.drag`.
    """

    bhp: float
    speeds_kn: npt.NDArray[np.float64]
    ft_fixed_pitch_kgf: npt.NDArray[np.float64]
    ft_variable_pitch_nozzle_kgf: npt.NDArray[np.float64]

    def to_dict(self) -> dict[str, Any]:
        """Serializa con las series como listas."""
        return {
            "bhp": self.bhp,
            "speeds_kn": self.speeds_kn.tolist(),
            "ft_fixed_pitch_kgf": self.ft_fixed_pitch_kgf.tolist(),
            "ft_variable_pitch_nozzle_kgf": self.ft_variable_pitch_nozzle_kgf.tolist(),
        }


def summary(vessel: Vessel, speeds_kn: FloatOrArray) -> FridmanSummary:
    """Reproduce ``L11:O19``: FT de Fridman (PF y PV+T) del buque sobre ``speeds_kn``."""
    v = np.atleast_1d(np.asarray(speeds_kn, dtype=float))
    return FridmanSummary(
        bhp=vessel.bhp,
        speeds_kn=v,
        ft_fixed_pitch_kgf=np.asarray(
            fridman_towing_force_kgf(vessel.bhp, v, FRIDMAN_KF[PropellerType.FIXED_PITCH]),
            dtype=float,
        ),
        ft_variable_pitch_nozzle_kgf=np.asarray(
            fridman_towing_force_kgf(
                vessel.bhp, v, FRIDMAN_KF[PropellerType.VARIABLE_PITCH_NOZZLE]
            ),
            dtype=float,
        ),
    )
