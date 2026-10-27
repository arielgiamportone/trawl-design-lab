"""Aparejos de dos redes (tangones y gemelo) y arrastre de vara (Fase 19.5).

El motor del libro calcula **una** red con su par de portones. Este módulo reúne los datos y las
fórmulas, con su fuente, para los aparejos en los que el buque remolca más de una red o en los
que la abertura horizontal la fija una vara:

* **Tangones** (``outrigger``): el buque remolca dos redes iguales, una desde cada tangón, cada
  una con su par de portones y un solo cable desde la punta del tangón que se abre en una tijera
  hacia los dos portones (Knake, Murdock y Cating 1958, FL 470, p. 6: «each trawl has but a
  single warp with bridle»). Es el aparejo de la flota langostinera argentina (Res. CFP 7/2018,
  art. 4: «tangones con redes langostineras»).
* **Gemelo** (``twin``): dos redes lado a lado con dos cables; los portones van afuera y las
  puntas de ala interiores se unen a un muerto o trineo central (Bullis y Floyd 1972; Arkley
  1987). Cada portón abre una red contra el muerto, que no tiene sustentación.
* **Vara** (``beam``): una vara rígida apoyada en dos patines fija la abertura horizontal; no hay
  portones. La resistencia es la de la red más la de la vara, los patines, el tren y las cadenas
  espantadoras (*tickler chains*), con los datos por componente de Rijnsdorp et al. (2020,
  WMR C056/20). Lo habitual es remolcar dos varas desde dos tangones (Eigaard et al. 2016,
  p. i29; Verhoest y Maton 1964).

Valores por defecto: sólo los que dan las fuentes (cada constante cita la suya); el resto son
entradas explícitas del caso. Las reglas prácticas (muerto = 1,5 portones, Seafish) se marcan
como tales.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, fields
from typing import Any

import numpy as np
from numpy.typing import NDArray

from trawlkit.units import RHO_SEAWATER, G

FloatArray = NDArray[np.float64]

#: Pie y pulgada [m].
FT_M = 0.3048
INCH_M = 0.0254

#: Aparejos que el motor sabe calcular.
RIGS: tuple[str, ...] = ("otter", "pair", "outrigger", "twin", "beam")
#: Aparejos de esta fase (más de una red o vara): los resuelve :class:`~trawlkit.model.RigStage`.
MULTI_RIGS: tuple[str, ...] = ("outrigger", "twin", "beam")

# ---------------------------------------------------------------------------------------------
# Tangones
# ---------------------------------------------------------------------------------------------

#: Largo del tangón: «usually 24-feet long» (Knake, Murdock y Cating 1958, FL 470, p. 3).
BOOM_LENGTH_M = 24.0 * FT_M
#: Ángulo de pesca del tangón sobre la horizontal: «an angle of 20° above horizontal»
#: (FL 470, p. 5).
BOOM_ANGLE_DEG = 20.0
#: Distancia del pie del tangón a la crujía: «mounted on the mast pad eyes or ... fitted to a
#: gooseneck» (FL 470, p. 3): al pie del palo, sobre la crujía.
BOOM_HEEL_OFFSET_M = 0.0
#: Tangones de la vara doble a ≈ 30° de la horizontal pescando (Verhoest y Maton 1964, p. 210).
BEAM_BOOM_ANGLE_DEG = 30.0
#: Tijera del tangonero argentino: 70 m de cable de acero de 22 mm (Roth y Rubio 2022, INIDEP ITO
#: 043/22, pp. 1 y 5; aparejo de las simulaciones DynamiT).
OUTRIGGER_BRIDLE_M = 70.0
OUTRIGGER_BRIDLE_DIAMETER_MM = 22.0

# ---------------------------------------------------------------------------------------------
# Gemelo
# ---------------------------------------------------------------------------------------------

#: Peso del muerto central ≈ 1,5 veces el de un portón (Seafish, base de datos de artes, «twin
#: rig trawl»: regla práctica, no una fórmula de diseño).
CLUMP_DOOR_RATIO = 1.5
#: Trineo del gemelo del golfo de México: 6 pies de largo, 32 pulgadas de alto atrás y un patín de
#: acero de 8 pulgadas de ancho (Bullis y Floyd 1972, p. 27).
SLED_LENGTH_M = 6.0 * FT_M
SLED_HEIGHT_M = 32.0 * INCH_M
SLED_SHOE_WIDTH_M = 8.0 * INCH_M
#: Área frontal del trineo [m²] (derivada: alto × ancho del patín; supuesto «A VERIFICAR», el
#: trineo no es una placa llena).
SLED_FRONTAL_M2 = SLED_HEIGHT_M * SLED_SHOE_WIDTH_M
#: Coeficiente de arrastre del trineo: el del patín de la vara (C056/20, tabla 1), objeto de forma
#: parecida (supuesto).
CD_SLED = 1.05

# ---------------------------------------------------------------------------------------------
# Portón por pie de relinga (Watson et al. 1984)
# ---------------------------------------------------------------------------------------------

#: Área de un portón por pie de relinga superior en las redes camaroneras convencionales:
#: 70–80 pulg²/pie, con una abertura de 70–75 % de la relinga (Watson, Workman, Taylor y Serra
#: 1984, NOAA TR NMFS 3, p. 1 y figs. 9–10).
WATSON_DOOR_AREA_IN2_PER_FT: tuple[float, float] = (70.0, 80.0)
WATSON_SPREAD_RATIO: tuple[float, float] = (0.70, 0.75)
#: 1 pulg²/pie = 6,4516·10⁻⁴ m² / 0,3048 m = 2,117·10⁻³ m²/m.
IN2_PER_FT_TO_M2_PER_M = INCH_M**2 / FT_M

# ---------------------------------------------------------------------------------------------
# Vara (Rijnsdorp et al. 2020, WMR C056/20; Eigaard et al. 2016)
# ---------------------------------------------------------------------------------------------

#: Coeficientes de arrastre de la vara y de los patines (C056/20, tabla 1; ec. 1).
CD_BEAM = 1.1
CD_SHOE = 1.05
#: Límite entre buques chicos y grandes (C056/20: ≤ 221 kW y > 221 kW).
BEAM_CLASS_KW = 221.0
#: Patines por vara.
SHOES_PER_BEAM = 2
#: Varas por buque: «Typically, two TBBs are towed by each vessel» (Eigaard et al. 2016, p. i29).
BEAMS_PER_VESSEL = 2
#: Ancho total de las varas en función de la potencia, a·kW^b (Eigaard et al. 2016, tabla 4,
#: p. i38): TBB_CRU (camarón) y TBB_DMF (peces demersales). Es el ancho **total** del arte (fig. 8:
#: «total gear width»); se reparte entre las varas.
EIGAARD_BEAM_WIDTH: dict[str, tuple[float, float]] = {
    "CRU": (1.4812, 0.4578),
    "DMF": (0.6601, 0.5078),
}


@dataclass(frozen=True)
class BeamClass:
    """Datos de una clase de buque de vara (C056/20, tablas 2, 3, 8 y 9; arrastre en kN/m)."""

    beam_length_m: float
    beam_diameter_m: float
    shoe_area_m2: float
    shoe_height_m: float
    speed_ms: float
    beam_kn_m: float
    net_top_kn_m: float
    net_bottom_kn_m: float
    ground_gear_kn_m: float
    ticklers_kn_m: float
    shoes_kn_m: float
    total_kn_m: float
    shoe_ticklers: float
    net_ticklers: float


#: Varas de tickler con red en V del Mar del Norte (C056/20): tabla 2 (vara y patines), tabla 3
#: (cadenas), tabla 8 (velocidad de arrastre) y tabla 9 (arrastre por metro de vara, «Tckl_V-net»).
BEAM_CLASSES: dict[str, BeamClass] = {
    "small": BeamClass(
        beam_length_m=4.5,
        beam_diameter_m=0.15,
        shoe_area_m2=0.054,
        shoe_height_m=0.60,
        speed_ms=2.66,
        beam_kn_m=0.83,
        net_top_kn_m=1.99,
        net_bottom_kn_m=2.34,
        ground_gear_kn_m=0.38,
        ticklers_kn_m=0.69,
        shoes_kn_m=0.03,
        total_kn_m=6.3,
        shoe_ticklers=6.5,
        net_ticklers=5.0,
    ),
    "large": BeamClass(
        beam_length_m=12.0,
        beam_diameter_m=0.24,
        shoe_area_m2=0.063,
        shoe_height_m=0.70,
        speed_ms=3.29,
        beam_kn_m=1.43,
        net_top_kn_m=3.25,
        net_bottom_kn_m=3.13,
        ground_gear_kn_m=0.77,
        ticklers_kn_m=2.26,
        shoes_kn_m=0.04,
        total_kn_m=10.9,
        shoe_ticklers=8.8,
        net_ticklers=10.9,
    ),
}

#: Vara de 4 m con tickler medida/estimada por Depestele et al. (2016, ICES JMS 73(S1), versión
#: advance access, pp. 2–3 y tabla 2): ancho 4,4 m, 4,4 nudos; arrastre de los paños inferiores,
#: de las cadenas (tickler y tren) y de los patines, en N.
DEPESTELE_2016: dict[str, float] = {
    "beam_width_m": 4.4,
    "speed_kn": 4.4,
    "weight_air_kg": 1065.0,
    "beam_shoes_kg": 595.0,
    "lower_netting_n": 4150.0,
    "chains_n": 3440.0,
    "shoes_n": 1770.0,
    "total_n": 9360.0,
}

#: Palabras que señalan una red de crustáceos (vara TBB_CRU, sin cadenas espantadoras).
_CRUSTACEAN_WORDS = (
    "camar",
    "langost",
    "crust",
    "gamba",
    "shrimp",
    "prawn",
    "crangon",
    "pleoticus",
    "penae",
)


def _q(v_ms: FloatArray | float) -> FloatArray:
    """Presión dinámica ½·ρ·v² [Pa]."""
    v = np.asarray(v_ms, dtype=float)
    return 0.5 * RHO_SEAWATER * v**2


def drag_kgf(cd: float, frontal_m2: float, v_ms: FloatArray | float) -> FloatArray:
    """Arrastre de un cuerpo ``D = ½·ρ·A·v²·C_D`` (C056/20, ec. 1) [kgf]."""
    return np.asarray(_q(v_ms) * frontal_m2 * cd / G, dtype=float)


# ---------------------------------------------------------------------------------------------
# Geometría
# ---------------------------------------------------------------------------------------------


def boom_tip_offset_m(length_m: float, angle_deg: float, heel_offset_m: float = 0.0) -> float:
    """Distancia horizontal de la punta del tangón a la crujía [m]: pie + L·cos θ."""
    return float(heel_offset_m + length_m * math.cos(math.radians(angle_deg)))


def boom_tip_rise_m(length_m: float, angle_deg: float) -> float:
    """Altura de la punta del tangón sobre su pie [m]: L·sin θ.

    Con los 24 pies a 20° de FL 470 sube 2,5 m (8,2 pies); con el pie en la cubierta la punta
    queda a 10–12 pies sobre el agua, como dice la fuente (p. 5).
    """
    return float(length_m * math.sin(math.radians(angle_deg)))


@dataclass(frozen=True)
class OutriggerLayout:
    """Planta de dos redes remolcadas desde los tangones (o dos varas)."""

    tip_offset_m: float
    tip_rise_m: float
    net_spread_m: float
    gap_m: float
    swept_width_m: float

    @property
    def overlap(self) -> bool:
        """Si las dos redes se superponen en planta (huelgo negativo)."""
        return self.gap_m < 0.0


def outrigger_layout(
    net_spread_m: float, length_m: float, angle_deg: float, heel_offset_m: float = 0.0
) -> OutriggerLayout:
    """Planta de las dos redes, cada una centrada detrás de la punta de su tangón.

    El huelgo entre redes es ``2·y_punta − DP`` y el ancho barrido ``2·DP + huelgo`` (de portón
    exterior a portón exterior; FL 470, fig. 4: redes de 40 pies con tangones de 24 pies, media
    abertura ≈ 20 pies y un huelgo entre redes). Supuesto: cada red sigue la punta de su tangón.
    """
    tip = boom_tip_offset_m(length_m, angle_deg, heel_offset_m)
    gap = 2.0 * tip - net_spread_m
    return OutriggerLayout(
        tip_offset_m=tip,
        tip_rise_m=boom_tip_rise_m(length_m, angle_deg),
        net_spread_m=net_spread_m,
        gap_m=gap,
        swept_width_m=2.0 * net_spread_m + gap,
    )


def boom_length_without_overlap_m(
    net_spread_m: float, angle_deg: float, heel_offset_m: float = 0.0
) -> float:
    """Largo mínimo del tangón para que las dos redes no se superpongan [m] (huelgo = 0)."""
    return float((0.5 * net_spread_m - heel_offset_m) / math.cos(math.radians(angle_deg)))


# ---------------------------------------------------------------------------------------------
# Portones (Watson et al. 1984) y muerto central
# ---------------------------------------------------------------------------------------------


def watson_door_area_m2(headrope_m: float) -> tuple[float, float]:
    """Área de un portón para una relinga de ``headrope_m`` según Watson et al. (1984) [m²]."""
    lo, hi = WATSON_DOOR_AREA_IN2_PER_FT
    k = IN2_PER_FT_TO_M2_PER_M
    return (lo * k * headrope_m, hi * k * headrope_m)


def watson_spread_m(headrope_m: float) -> tuple[float, float]:
    """Abertura entre puntas de ala de 70–75 % de la relinga (Watson et al. 1984) [m]."""
    lo, hi = WATSON_SPREAD_RATIO
    return (lo * headrope_m, hi * headrope_m)


def clump_weight_kg(door_weight_air_kg: float) -> float:
    """Muerto central = 1,5 × el peso de un portón (Seafish, regla práctica) [kg]."""
    return CLUMP_DOOR_RATIO * door_weight_air_kg


def steel_in_water(weight_air_kg: float) -> float:
    """Peso en el agua de una pieza de acero [kgf] (1 − ρ_agua/ρ_acero)."""
    return weight_air_kg * (1.0 - 1024.0 / 7850.0)


# ---------------------------------------------------------------------------------------------
# Vara
# ---------------------------------------------------------------------------------------------


def beam_class(power_kw: float) -> str:
    """Clase de buque de C056/20: ``small`` (≤ 221 kW) o ``large``."""
    return "small" if power_kw <= BEAM_CLASS_KW else "large"


def is_crustacean(*texts: str | None) -> bool:
    """Si alguno de los textos (especie, nombre científico) es de un crustáceo."""
    hay = " ".join(t for t in texts if t).lower()
    return any(w in hay for w in _CRUSTACEAN_WORDS)


def beam_width_total_m(power_kw: float, metier: str) -> float:
    """Ancho total de las varas de un buque de ``power_kw`` (Eigaard et al. 2016, tabla 4) [m]."""
    a, b = EIGAARD_BEAM_WIDTH[metier]
    return float(a * power_kw**b)


@dataclass(frozen=True)
class BeamDrag:
    """Resistencia de los componentes de una vara (sin la red) [kgf, una vara].

    ``beam`` y ``shoes`` con la ec. 1 de C056/20 (vara cilíndrica de diámetro ``d``, C_D = 1,1;
    patines de área frontal ``A``, C_D = 1,05); ``ground_gear`` y ``ticklers`` con el arrastre por
    metro de vara de la tabla 9 (red en V) escalado con v² desde la velocidad de la tabla 8.
    ``net_c056`` es la red por la ec. 10 (MacLennan 1981) con la superficie de hilo, sólo para
    comparar con la RN de diseño.
    """

    metier: str
    beam_class: str
    beam_length_m: float
    beam_diameter_m: float
    shoe_area_m2: float
    shoe_height_m: float
    ticklers: bool
    beam_kgf: FloatArray
    shoes_kgf: FloatArray
    ground_gear_kgf: FloatArray
    ticklers_kgf: FloatArray
    total_kgf: FloatArray
    net_c056_kgf: FloatArray = field(default_factory=lambda: np.zeros(0))

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        out: dict[str, Any] = {}
        for f in fields(self):
            v = getattr(self, f.name)
            out[f.name] = v.tolist() if isinstance(v, np.ndarray) else v
        return out


def per_metre_kgf(kn_m: float, ref_speed_ms: float, v_ms: FloatArray | float) -> FloatArray:
    """Arrastre por metro de vara [kgf/m] escalado con v² desde la velocidad de referencia."""
    v = np.asarray(v_ms, dtype=float)
    return np.asarray(kn_m * 1000.0 * (v / ref_speed_ms) ** 2 / G, dtype=float)


def net_drag_c056_kgf(twine_area_m2: float, v_ms: FloatArray | float) -> FloatArray:
    """Red por la ec. 10 de C056/20 (MacLennan 1981): ½ρU²·A·0,352/(1 + 0,125·U) [kgf]."""
    v = np.asarray(v_ms, dtype=float)
    return np.asarray(_q(v) * twine_area_m2 * 0.352 / (1.0 + 0.125 * v) / G, dtype=float)


def beam_drag(
    v_ms: FloatArray,
    *,
    length_m: float,
    diameter_m: float,
    shoe_area_m2: float,
    shoe_height_m: float,
    cls: str,
    ticklers: bool,
    metier: str,
    twine_area_m2: float | None = None,
) -> BeamDrag:
    """Resistencia de los componentes de una vara a las velocidades ``v_ms`` (ver :class:`BeamDrag`)."""
    data = BEAM_CLASSES[cls]
    v = np.asarray(v_ms, dtype=float)
    beam = drag_kgf(CD_BEAM, diameter_m * length_m, v)
    shoes = SHOES_PER_BEAM * drag_kgf(CD_SHOE, shoe_area_m2, v)
    ground = per_metre_kgf(data.ground_gear_kn_m, data.speed_ms, v) * length_m
    tick = (
        per_metre_kgf(data.ticklers_kn_m, data.speed_ms, v) * length_m
        if ticklers
        else np.zeros_like(v)
    )
    return BeamDrag(
        metier=metier,
        beam_class=cls,
        beam_length_m=float(length_m),
        beam_diameter_m=float(diameter_m),
        shoe_area_m2=float(shoe_area_m2),
        shoe_height_m=float(shoe_height_m),
        ticklers=bool(ticklers),
        beam_kgf=beam,
        shoes_kgf=shoes,
        ground_gear_kgf=ground,
        ticklers_kgf=tick,
        total_kgf=beam + shoes + ground + tick,
        net_c056_kgf=np.zeros(0)
        if twine_area_m2 is None
        else net_drag_c056_kgf(twine_area_m2, v),
    )


@dataclass(frozen=True)
class DepesteleCheck:
    """Comparación de C056/20 (clase chica, escalada) con la vara de Depestele et al. (2016) [N]."""

    netting_n: float
    chains_n: float
    shoes_n: float
    total_n: float
    measured: dict[str, float]

    def ratio(self, key: str) -> float:
        """Cociente modelo/medición de un componente (``netting``, ``chains``, ``shoes``, ``total``)."""
        ref = {
            "netting": self.measured["lower_netting_n"],
            "chains": self.measured["chains_n"],
            "shoes": self.measured["shoes_n"],
            "total": self.measured["total_n"],
        }[key]
        return float(getattr(self, f"{key}_n") / ref)

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "netting_n": self.netting_n,
            "chains_n": self.chains_n,
            "shoes_n": self.shoes_n,
            "total_n": self.total_n,
            "measured": dict(self.measured),
        }


def depestele_check(cls: str = "small") -> DepesteleCheck:
    """Paños inferiores, cadenas y patines de C056/20 para la vara de Depestele et al. (2016).

    Ancho de la vara y velocidad de Depestele (4,4 m, 4,4 nudos); paños inferiores, tren y
    cadenas por metro de la tabla 9 de C056/20 escalados con v²; dos patines con el área frontal
    de la tabla 2 y la ec. 1. Depestele et al. estiman sus valores con Reid (1977), Xu y Huang
    (2014) y Hoerner (1965): ambos son estimaciones de modelo, no tiros medidos.
    """
    from trawlkit.units import KNOT_TO_MS

    data = BEAM_CLASSES[cls]
    d = DEPESTELE_2016
    v = d["speed_kn"] * KNOT_TO_MS
    width = d["beam_width_m"]
    k = (v / data.speed_ms) ** 2
    netting = data.net_bottom_kn_m * 1000.0 * k * width
    chains = (data.ground_gear_kn_m + data.ticklers_kn_m) * 1000.0 * k * width
    shoes = float(SHOES_PER_BEAM * drag_kgf(CD_SHOE, data.shoe_area_m2, v) * G)
    return DepesteleCheck(
        netting_n=netting,
        chains_n=chains,
        shoes_n=shoes,
        total_n=netting + chains + shoes,
        measured=dict(d),
    )


__all__ = [
    "BEAMS_PER_VESSEL",
    "BEAM_BOOM_ANGLE_DEG",
    "BEAM_CLASSES",
    "BEAM_CLASS_KW",
    "BOOM_ANGLE_DEG",
    "BOOM_HEEL_OFFSET_M",
    "BOOM_LENGTH_M",
    "CD_BEAM",
    "CD_SHOE",
    "CD_SLED",
    "CLUMP_DOOR_RATIO",
    "DEPESTELE_2016",
    "EIGAARD_BEAM_WIDTH",
    "MULTI_RIGS",
    "OUTRIGGER_BRIDLE_DIAMETER_MM",
    "OUTRIGGER_BRIDLE_M",
    "RIGS",
    "SHOES_PER_BEAM",
    "SLED_FRONTAL_M2",
    "SLED_HEIGHT_M",
    "SLED_LENGTH_M",
    "SLED_SHOE_WIDTH_M",
    "WATSON_DOOR_AREA_IN2_PER_FT",
    "WATSON_SPREAD_RATIO",
    "BeamClass",
    "BeamDrag",
    "DepesteleCheck",
    "OutriggerLayout",
    "beam_class",
    "beam_drag",
    "beam_width_total_m",
    "boom_length_without_overlap_m",
    "boom_tip_offset_m",
    "boom_tip_rise_m",
    "clump_weight_kg",
    "depestele_check",
    "drag_kgf",
    "is_crustacean",
    "net_drag_c056_kgf",
    "outrigger_layout",
    "per_metre_kgf",
    "steel_in_water",
    "watson_door_area_m2",
    "watson_spread_m",
]
