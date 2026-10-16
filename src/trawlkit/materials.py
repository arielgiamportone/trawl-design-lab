"""Materiales de los paños: densidad del hilo y coeficientes de peso en el agua.

Reproduce la columna *Densidad* de la hoja ``'Paños de red y cortes'`` (L55, X54, …) y expone el
catálogo ``trawlkit/data/materials.yaml`` (``'Tablas de Referencias'!A35:I37``) como objetos
:class:`Material`.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import numpy.typing as npt

from trawlkit.compat import Compat
from trawlkit.io.schema import Catalogue
from trawlkit.units import RHO_SEAWATER

#: Valor de π incrustado en las fórmulas del Excel (``3.1416`` en P!L55 y Mec!N98).
EXCEL_PI: float = 3.1416

Number = float | npt.NDArray[np.float64]


def _out(a: npt.NDArray[np.float64]) -> Number:
    """Devuelve un ``float`` para entradas escalares y un array en caso contrario."""
    return float(a) if a.ndim == 0 else a


@dataclass(frozen=True)
class Material:
    """Hilo de red del catálogo ``trawlkit/data/materials.yaml``.

    ``density_kg_m3`` es la densidad del polímero (PA 1140 kg/m³) y los coeficientes
    ``weight_in_water_coefficient_*`` el cociente peso en agua / peso en aire
    (``1 - ρ_agua/ρ_material``) tal como figuran en ``'Tablas de Referencias'!G36`` e ``I36``.
    """

    id: str
    material: str
    density_kg_m3: float
    runnage_m_per_kg: float | None = None
    rtex: float | None = None
    diameter_mm: float | None = None
    weight_in_water_coefficient_seawater: float | None = None
    weight_in_water_coefficient_freshwater: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return asdict(self)


def materials_from_catalogue(catalogue: Catalogue) -> tuple[Material, ...]:
    """Convierte el catálogo genérico (``load_catalogue("materials")``) en :class:`Material`."""
    fields = {f for f in Material.__dataclass_fields__}
    out: list[Material] = []
    for item in catalogue.items:
        kwargs = {k: v for k, v in item.items() if k in fields}
        out.append(Material(**kwargs))
    return tuple(out)


def find_material(
    materials: tuple[Material, ...] | list[Material],
    material: str = "PA",
    rtex: float | None = None,
    diameter_mm: float | None = None,
) -> Material:
    """Busca el hilo del catálogo por material y, opcionalmente, Rtex o diámetro.

    Si se indica ``rtex`` (o ``diameter_mm``) se devuelve la entrada más cercana entre las del
    mismo material; si no, la primera del material. Lanza ``KeyError`` si el material no existe.
    """
    candidates = [m for m in materials if m.material.upper() == material.upper()]
    if not candidates:
        raise KeyError(f"material desconocido en el catálogo: {material!r}")
    if rtex is not None:
        with_rtex = [m for m in candidates if m.rtex is not None]
        if with_rtex:
            return min(with_rtex, key=lambda m: abs(float(m.rtex or 0.0) - rtex))
    if diameter_mm is not None:
        with_d = [m for m in candidates if m.diameter_mm is not None]
        if with_d:
            return min(with_d, key=lambda m: abs(float(m.diameter_mm or 0.0) - diameter_mm))
    return candidates[0]


def twine_density_kg_m3(
    twine_diameter_mm: Number,
    mesh_mm: Number,
    runnage_m_per_kg: Number,
    compat: Compat = Compat.CORRECTED,
) -> Number:
    """Densidad aparente del hilo a partir del diámetro y el rendimiento [kg/m³].

    Celda representativa: ``'Paños de red y cortes'!L55``::

        =((3.1416*((J55/2)^2)*(B55/2)/1000))*(A55/((B55/2)/1000))

    con J55 = Ø hilo [mm], B55 = mallero [mm] y A55 = rendimiento [m/kg]. El término
    ``(B55/2)/1000`` aparece en numerador y denominador y se cancela, de modo que la celda
    calcula ``π·(d/2)²[mm²] · runnage[m/kg]``, que **no** tiene unidades de densidad
    (mm²·m/kg = 1e-6 m³/kg, el inverso de una densidad y con un factor 1e-6 de por medio).

    Errata ``twine_density_units`` (P!L55):

    * :attr:`Compat.EXCEL` reproduce la celda tal cual (≈ 1151.65 kg/m³ para Ø 1.37 mm,
      R1280tex); el número coincide por casualidad con el orden de magnitud de la densidad del
      nylon (1140 kg/m³).
    * :attr:`Compat.CORRECTED` devuelve la densidad aparente dimensionalmente correcta
      ``ρ = 1 / (A[m²] · runnage[m/kg])`` con ``A = π·(d[m]/2)²`` (≈ 868.3 kg/m³), es decir,
      la masa del hilo por unidad de volumen del cilindro envolvente (incluye los huecos del
      trenzado, por eso es menor que la densidad del polímero).

    ``mesh_mm`` sólo interviene en el modo EXCEL (se cancela algebraicamente, pero se conserva
    para dejar constancia de la celda original).
    """
    d = np.asarray(twine_diameter_mm, dtype=float)
    m_l = np.asarray(mesh_mm, dtype=float)
    r = np.asarray(runnage_m_per_kg, dtype=float)
    if compat is Compat.EXCEL:
        half_mesh_m = (m_l / 2.0) / 1000.0
        return _out((EXCEL_PI * (d / 2.0) ** 2 * half_mesh_m) * (r / half_mesh_m))
    area_m2 = math.pi * (d / 2.0 / 1000.0) ** 2
    return _out(1.0 / (area_m2 * r))


def weight_in_water_coefficient(density_kg_m3: Number, rho_water: float = RHO_SEAWATER) -> Number:
    """Cociente peso en agua / peso en aire: ``1 - ρ_agua / ρ_material``.

    Para PA (1140 kg/m³) en agua de mar da ≈ 0.10, el valor tabulado en
    ``'Tablas de Referencias'!G36``. ``'Mecánica de la Red'!P98`` usa ρ_agua = 1025 kg/m³
    (ver :func:`trawlkit.net.weight_in_water_kg`).
    """
    rho = np.asarray(density_kg_m3, dtype=float)
    return _out(1.0 - rho_water / rho)
