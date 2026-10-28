"""Aberturas de las redes camaroneras y langostineras con tangones o gemelo (Fase 19.7b).

El promedio de cuatro DPA del libro (``Dim!F61``: por ángulo de corte, geométrica, geométrica con
la red trabajando y la serie de Fridman) y la separación de portones «al metro» de cable están
pensados para un arrastre de peces con portones a popa y patentes largas. En un tangonero cada red
cuelga de una **tijera**: un solo cable que se abre en dos ramas de 60–73 m hacia los portones,
que van unidos a las alas con cañas cortas (2,5–4 m). La separación entre portones no depende del
cable filado: «la separación entre portones no puede ser modificada con la longitud del cable de
arrastre filado» (Roth 2016, INIDEP IAT 72/2016, p. 9). Este módulo reúne el método propuesto para
esos aparejos, con la fuente de cada número:

* **Separación de portones (DP)**: equilibrio plano portón–tijera–red (Roth 2016, ecs. 13–17) con
  la proyección corregida (ver :func:`tijera_balance`).
* **Abertura horizontal (AH)**: DP por la razón de triángulos semejantes del motor (Mec!L225, sin
  el redondeo) con las cañas cortas en lugar de las patentes de 25 m; se contrasta con AH/DP =
  0,72–0,88 de las simulaciones DynamiT del INIDEP.
* **Respaldo** (sin tijera, o sin solución del equilibrio): AH = k·lima con k por familia.
* **Abertura vertical (AV)**: 0,04·lima (0,03–0,07) en redes de baja abertura con pocas o ninguna
  boya; límite de 1,5 m de la Res. CFP 7/2018 (art. 4).

Fuera del rango de validez (tijera de 55–73 m, portones planos o Bison de 300–600 kg, lima de
11–40 m, 2,5–4 nudos, 30–110 m de profundidad) el método da un orden de magnitud, no un diseño.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, fields
from typing import Any

from trawlkit.i18n import t

#: Métodos de aberturas de :class:`~trawlkit.model.DesignCase` (``opening_method``): ``auto``
#: (camaronero con tangones o gemelo, o con una red sólo de crustáceos), ``book`` (el promedio
#: del libro) o ``shrimp`` (forzado).
OPENING_METHODS: tuple[str, ...] = ("auto", "book", "shrimp")

#: Cañas portón–ala por defecto [m]: 3,0 m en las simulaciones del INIDEP de redes de Pesquera
#: Deseado e Iberconsa (Roth, Rubio y García 2024, IAT 85/2024, p. 5) y en la tangonera de ITO
#: 61/2022 (p. 3). Supuesto: ITO 043/2022 no da el largo de las cañas.
SHRIMP_BRIDLE_M = 3.0
#: Rango de las cañas en los aparejos del INIDEP [m]: 2,5 m (IAT 111/2022) a 4 m (IAT 27/2019,
#: ITO 34/2020, IAT 104/2023).
SHRIMP_BRIDLE_RANGE_M: tuple[float, float] = (2.5, 4.0)
#: Factor de largo del cuerpo trabajando para L_R: referencia longitudinal E_N = 0,90 de la
#: columna «Length ratio» de los planos DynamiT (derivado: cabos rectos D, K, L y M de ITO
#: 043/2022, fig. 5; largo del cabo / (filas × mallero × 0,90) = 1,04–1,14 como el impreso).
TIJERA_NET_LENGTH_FACTOR = 0.90
#: AH/DP de las simulaciones DynamiT del INIDEP con tijera y cañas cortas (derivado de ITO
#: 043/2022, IAT 85/2024, IAT 104/2023 e IAT 111/2022: 0,72–0,88).
AH_OVER_DP_RANGE: tuple[float, float] = (0.72, 0.88)
#: AH/lima de las simulaciones DynamiT de tangoneras argentinas (ITO 043/2022, IAT 27/2019, IAT
#: 75/2023, IAT 85/2024, IAT 111/2022; derivado de sus tablas): 0,36–0,50.
DYNAMIT_AH_RANGE: tuple[float, float] = (0.36, 0.50)
#: DP/lima medida con sensores Simrad PX en la red Iberconsa de 25,4 m (Roth, Pisano y Di Leva
#: 2024, IAT 94/2024, tabla 1: 18,8–19,5 m): 0,74–0,77.
MEASURED_DP_RANGE: tuple[float, float] = (0.74, 0.77)
#: AV/lima en redes de baja abertura con pocas o ninguna boya: 0,04 (0,03–0,07). DynamiT del
#: INIDEP 0,026–0,049; Watson et al. (1984, tablas 1–5) y Harrington et al. (1988, tabla 1)
#: medidos 0,029–0,080.
AV_HEADROPE_RATIO = 0.04
AV_HEADROPE_RANGE: tuple[float, float] = (0.03, 0.07)
#: Límite de abertura vertical de la flota langostinera (Res. CFP 7/2018, art. 4) [m].
CFP_AV_LIMIT_M = 1.5


@dataclass(frozen=True)
class HeadropeK:
    """Coeficiente k de AH = k·lima de una familia de redes, con su rango y su fuente."""

    key: str
    k: float
    low: float
    high: float
    source: str


#: AH = k·lima por familia (informe de la Fase 19.7b, sección 5.3).
HEADROPE_K: dict[str, HeadropeK] = {
    # Tangonera argentina de baja abertura, calibrada con DynamiT (tablas de ITO 043/2022, IAT
    # 27/2019, 75/2023, 85/2024 y 111/2022).
    "inidep_dynamit": HeadropeK("inidep_dynamit", 0.43, 0.36, 0.50, "DynamiT, INIDEP"),
    # Redes camaroneras convencionales de EE. UU. sin boyas, medidas con buzos (Watson et al.
    # 1984, tablas 1–5; Harrington et al. 1988, tablas 1 y 4).
    "us_conventional": HeadropeK(
        "us_conventional", 0.70, 0.62, 0.78, "Watson et al. 1984; Harrington et al. 1988"
    ),
    # Redes de lengüeta (tongue), Mongoose y Cobra (las mismas fuentes).
    "tongue": HeadropeK("tongue", 0.80, 0.72, 0.89, "Watson et al. 1984; Harrington et al. 1988"),
}

#: Palabras que señalan al langostino patagónico (red argentina).
_LANGOSTINO_WORDS = ("langostino", "pleoticus")
#: Palabras que señalan una red de lengüeta.
_TONGUE_WORDS = ("tongue", "lengüeta", "lengueta", "mongoose", "cobra")
#: Palabras que señalan peces en la especie objetivo (red mixta: no es sólo camaronera).
_FISH_WORDS = ("pez", "peces", "pescado", "fish", "merluza", "hake")


def _hay(*texts: str | None) -> str:
    return " ".join(t for t in texts if t).lower()


def is_langostino(*texts: str | None) -> bool:
    """Si alguno de los textos (especie, nombre científico) es el langostino patagónico."""
    hay = _hay(*texts)
    return any(w in hay for w in _LANGOSTINO_WORDS)


def has_fish(*texts: str | None) -> bool:
    """Si la especie objetivo nombra peces (red mixta de peces y camarón)."""
    hay = _hay(*texts)
    return any(w in hay for w in _FISH_WORDS)


def headrope_k(*texts: str | None) -> HeadropeK:
    """k de respaldo por familia: langostino argentino, lengüeta o camaronera convencional."""
    if is_langostino(*texts):
        return HEADROPE_K["inidep_dynamit"]
    hay = _hay(*texts)
    if any(w in hay for w in _TONGUE_WORDS):
        return HEADROPE_K["tongue"]
    return HEADROPE_K["us_conventional"]


@dataclass(frozen=True)
class TijeraBalance:
    """Equilibrio plano de un portón colgado de una rama de la tijera (una velocidad).

    ``alpha_deg`` es el ángulo de la rama de la tijera con el eje de arrastre y ``beta_deg`` el
    de la red (cañas + cuerpo) con el eje; ``tension_kgf`` la tensión de la rama. ``converged``
    es falso si la sustentación del portón supera lo que puede equilibrar la geometría (β llega a
    90°): entonces ``spread_m`` es la máxima geométrica, 2·L_R, y no es un resultado.
    """

    alpha_deg: float
    beta_deg: float
    tension_kgf: float
    spread_m: float
    converged: bool


def tijera_balance(
    lift_kgf: float,
    drag_kgf: float,
    net_drag_kgf: float,
    leg_m: float,
    net_leg_m: float,
    *,
    iterations: int = 200,
) -> TijeraBalance:
    """Separación de portones de un aparejo con tijera por el equilibrio plano (Roth 2016).

    Geometría (Roth 2016, IAT 72/2016, ecs. 16–17): la rama de la tijera ``L_C`` va del punto de
    unión, sobre el eje, al portón; ``L_R`` (cañas + red) va del portón al punto donde converge
    la red, también sobre el eje. Con la misma separación lateral ``a = L_C·sin α = L_R·sin β``::

        β  = arcsin((L_C / L_R)·sin α)
        T·cos α = F_CD + (R/2)·cos β          (a lo largo del arrastre)
        F_CL    = T·sin α + (R/2)·sin β       (a lo ancho)
        DP = 2·L_C·sin α

    con ``F_CL``/``F_CD`` la sustentación y la resistencia de un portón y ``R`` la resistencia de
    la red (la mitad por banda). α se busca por bisección en (0, arcsin(L_R/L_C)).

    **Corrección**: la ec. (12) impresa de Roth es ``F_CL − (F_CD + R/2)·sin 2α + (R/2)·sin 2β =
    0``: proyecta dos veces las componentes «tangencial» y «de corte» (ecs. 5–8) y da 2·sin α·cos
    α donde va sin α. Con los datos de ITO 043/2022 (S = 4,08 m², C_L/C_D = 0,93/0,71, R = 3777 −
    2·F_CD, L_C = 70 m, L_R = 20–35 m) la forma impresa da DP = 40–65 m y la de arriba 13–22 m,
    que encierra los 16,2 m de DynamiT (informe de la Fase 19.7b, sección 5.1).
    """
    if lift_kgf <= 0 or leg_m <= 0 or net_leg_m <= 0:
        raise ValueError(t("tijera_balance: sustentación y largos deben ser positivos"))
    half = 0.5 * net_drag_kgf
    ratio = leg_m / net_leg_m

    def parts(alpha: float) -> tuple[float, float, float]:
        beta = math.asin(min(1.0, ratio * math.sin(alpha)))
        tension = (drag_kgf + half * math.cos(beta)) / math.cos(alpha)
        return beta, tension, tension * math.sin(alpha) + half * math.sin(beta) - lift_kgf

    a_max = math.asin(min(1.0, net_leg_m / leg_m))
    # Con L_R ≥ L_C, α no puede pasar de 90° (la rama quedaría de costado).
    a_max = min(a_max, math.radians(89.9))
    beta, tension, residual = parts(a_max)
    if residual < 0.0:
        return TijeraBalance(
            alpha_deg=math.degrees(a_max),
            beta_deg=math.degrees(beta),
            tension_kgf=tension,
            spread_m=2.0 * leg_m * math.sin(a_max),
            converged=False,
        )
    lo, hi = 0.0, a_max
    for _ in range(iterations):
        mid = 0.5 * (lo + hi)
        if parts(mid)[2] > 0.0:
            hi = mid
        else:
            lo = mid
    alpha = 0.5 * (lo + hi)
    beta, tension, _ = parts(alpha)
    return TijeraBalance(
        alpha_deg=math.degrees(alpha),
        beta_deg=math.degrees(beta),
        tension_kgf=tension,
        spread_m=2.0 * leg_m * math.sin(alpha),
        converged=True,
    )


def net_leg_m(bridle_m: float, crowfoot_m: float, body_stretched_m: float) -> float:
    """L_R = cañas + pie de gallo + 0,90 × largo estirado del cuerpo (punta de ala → copo) [m]."""
    return bridle_m + crowfoot_m + TIJERA_NET_LENGTH_FACTOR * body_stretched_m


def wing_spread_m(door_spread_m: float, net_length_working_m: float, rigging_m: float) -> float:
    """AH = DP·LRw/(LRw + aparejo) [m]: triángulos semejantes de Mec!L225 sin el redondeo.

    ``rigging_m`` es el largo portón → punta de ala (pie de gallo + cañas).
    """
    return door_spread_m * net_length_working_m / (net_length_working_m + rigging_m)


@dataclass(frozen=True)
class ShrimpOpening:
    """Aberturas por el método camaronero (ver el docstring del módulo).

    ``method`` es ``tijera`` (equilibrio portón–tijera–red y triángulos semejantes) o
    ``headrope_k`` (AH = k·lima; DP la del libro). ``book_*`` son los valores que daba el
    promedio del libro, para comparar.
    """

    method: str
    door_spread_m: float
    horizontal_opening_m: float
    vertical_opening_m: float
    headrope_m: float
    ah_over_dp: float
    ah_over_headrope: float
    k: HeadropeK
    book_door_spread_m: float
    book_horizontal_opening_m: float
    bridle_m: float | None = None
    leg_m: float | None = None
    net_leg_m: float | None = None
    body_stretched_m: float | None = None
    speed_kn: float | None = None
    balance: TijeraBalance | None = None

    @property
    def ah_over_dp_in_range(self) -> bool:
        """Si AH/DP cae en el rango de DynamiT (0,72–0,88)."""
        lo, hi = AH_OVER_DP_RANGE
        return lo <= self.ah_over_dp <= hi

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        out: dict[str, Any] = {}
        for f in fields(self):
            v = getattr(self, f.name)
            if isinstance(v, HeadropeK | TijeraBalance):
                v = {g.name: getattr(v, g.name) for g in fields(v)}
            out[f.name] = v
        out["ah_over_dp_in_range"] = self.ah_over_dp_in_range
        return out


def vertical_opening_m(headrope_m: float) -> float:
    """AV = 0,04·lima [m] (redes de baja abertura con pocas o ninguna boya)."""
    return AV_HEADROPE_RATIO * headrope_m


__all__ = [
    "AH_OVER_DP_RANGE",
    "AV_HEADROPE_RANGE",
    "AV_HEADROPE_RATIO",
    "CFP_AV_LIMIT_M",
    "DYNAMIT_AH_RANGE",
    "HEADROPE_K",
    "MEASURED_DP_RANGE",
    "OPENING_METHODS",
    "SHRIMP_BRIDLE_M",
    "SHRIMP_BRIDLE_RANGE_M",
    "TIJERA_NET_LENGTH_FACTOR",
    "HeadropeK",
    "ShrimpOpening",
    "TijeraBalance",
    "has_fish",
    "headrope_k",
    "is_langostino",
    "net_leg_m",
    "tijera_balance",
    "vertical_opening_m",
    "wing_spread_m",
]
