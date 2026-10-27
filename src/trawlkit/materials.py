"""Materiales de los paños: densidad del hilo y coeficientes de peso en el agua.

Reproduce la columna *Densidad* de la hoja ``'Paños de red y cortes'`` (L55, X54, …) y expone el
catálogo ``trawlkit/data/materials.yaml`` (``'Tablas de Referencias'!A35:I37``) como objetos
:class:`Material`.

Fase 19.1: el mismo archivo trae una **tabla de materiales con fuentes** (PA, PES, PE, PP, HMPE,
cable de acero, cabo combinado acero + PP y cadena), que :func:`material_table` devuelve como
:class:`MaterialTable`: densidad, factor de peso en el agua, tenacidad, relaciones mojado/seco y
con nudo/sin nudo, alargamiento de rotura, módulo de la fibra y del hilo, y relaciones de rigidez
axial ``EA = k·d²`` de cabos y cables. Cada valor dice de dónde sale (clave bibliográfica) y cómo
(transcripto, derivado o supuesto «A VERIFICAR»). Las funciones :func:`polymer_density`,
:func:`twine_modulus_pa`, :func:`rope_ea_n` y :func:`wire_rope_ea_n` son las que usan el
simulador y el validador de componentes.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from functools import cache
from typing import Any, Literal

import numpy as np
import numpy.typing as npt
from pydantic import Field

from trawlkit.compat import Compat
from trawlkit.io.schema import Catalogue, ProvenanceKind, _Model
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


# ---------------------------------------------------------------------------------------------
# Tabla de materiales con fuentes (Fase 19.1)
# ---------------------------------------------------------------------------------------------


class SourcedValue(_Model):
    """Un valor de la tabla de materiales con su procedencia.

    ``kind`` es ``transcribed`` (copiado de ``source``), ``derived`` (calculado; la fórmula va en
    ``note``) o ``assumed`` (no se encontró fuente y se conserva el valor del motor, «A VERIFICAR»).
    ``basis`` dice sobre qué se mide (fibra, hilo, cabo; área nominal o metálica).
    """

    value: float
    range: tuple[float, float] | None = None
    unit: str | None = None
    basis: str | None = None
    kind: ProvenanceKind
    source: str | None = Field(default=None, description="Clave bibliográfica")
    page: str | None = None
    note: str | None = None

    @property
    def to_verify(self) -> bool:
        """Si el valor es un supuesto «A VERIFICAR»."""
        return self.kind is ProvenanceKind.ASSUMED


MaterialFamily = Literal["fibre", "steel", "combination"]


class MaterialProperties(_Model):
    """Propiedades de un material (claves de ``properties`` en ``materials.yaml``)."""

    id: str
    name: str
    family: MaterialFamily
    aliases: list[str] = Field(default_factory=list)
    values: dict[str, SourcedValue] = Field(default_factory=dict)
    pending: list[str] = Field(default_factory=list, description="Datos no encontrados")

    def get(self, key: str) -> SourcedValue | None:
        """Valor con fuente de la propiedad ``key`` (``None`` si la tabla no lo trae)."""
        return self.values.get(key)

    def value(self, key: str, default: float | None = None) -> float | None:
        """Número de la propiedad ``key`` (``default`` si la tabla no lo trae)."""
        v = self.values.get(key)
        return default if v is None else float(v.value)


class Reference(_Model):
    """Documento citado por la tabla de materiales."""

    title: str
    url: str | None = None
    accessed: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class MaterialTable:
    """Tabla de materiales con fuentes (:func:`material_table`)."""

    materials: dict[str, MaterialProperties]
    references: dict[str, Reference]
    notes: tuple[str, ...] = ()

    def find(self, name: str | None) -> MaterialProperties | None:
        """Material por id o alias, sin distinguir mayúsculas (``None`` si no está).

        ``"combinado (PP + acero)"`` y cualquier nombre que empiece con ``combinado`` devuelven
        el cabo combinado; ``"acero"`` o ``"steel"``, el cable de acero.
        """
        if not name:
            return None
        key = name.strip().upper()
        for m in self.materials.values():
            if key == m.id.upper() or key in (a.upper() for a in m.aliases):
                return m
        if key.startswith(("COMBINADO", "COMBINATION")):
            return self.materials.get("combination_steel_pp")
        return None

    def __getitem__(self, name: str) -> MaterialProperties:
        """Material por id o alias (``KeyError`` si no está)."""
        m = self.find(name)
        if m is None:
            raise KeyError(f"material desconocido en la tabla: {name!r}")
        return m

    def sources(self) -> set[str]:
        """Claves bibliográficas citadas por algún valor."""
        return {v.source for m in self.materials.values() for v in m.values.values() if v.source}

    def to_verify(self) -> list[str]:
        """Valores supuestos y datos no encontrados («A VERIFICAR»), como texto."""
        out = [
            f"{m.id}.{k}: {v.note or ''}".strip()
            for m in self.materials.values()
            for k, v in m.values.items()
            if v.to_verify
        ]
        out += [f"{m.id}: {p}" for m in self.materials.values() for p in m.pending]
        return out


_META_KEYS = {"name", "family", "aliases", "pending"}


def material_table_from_catalogue(catalogue: Catalogue) -> MaterialTable:
    """Arma la :class:`MaterialTable` a partir del catálogo ``materials`` ya cargado."""
    extra = catalogue.model_extra or {}
    raw: dict[str, Any] = extra.get("properties") or {}
    mats: dict[str, MaterialProperties] = {}
    for mid, rec in raw.items():
        values = {k: SourcedValue.model_validate(v) for k, v in rec.items() if k not in _META_KEYS}
        mats[mid] = MaterialProperties(
            id=mid,
            name=rec["name"],
            family=rec["family"],
            aliases=[str(a) for a in rec.get("aliases", [])],
            values=values,
            pending=list(rec.get("pending", [])),
        )
    refs = {k: Reference.model_validate(v) for k, v in (extra.get("references") or {}).items()}
    return MaterialTable(mats, refs, tuple(extra.get("properties_notes") or ()))


@cache
def material_table() -> MaterialTable:
    """Tabla de materiales con fuentes de ``trawlkit/data/materials.yaml`` (en caché)."""
    from trawlkit.io.loader import load_catalogue

    return material_table_from_catalogue(load_catalogue("materials"))


#: Material por defecto del paño cuando la spec no lo dice o no está en la tabla.
DEFAULT_TWINE_MATERIAL = "PA"
#: Rigidez axial de las relingas combinadas cuando no hay dato [N] (supuesto «A VERIFICAR» de la
#: tabla: ``combination_steel_pp.rope_ea_n``).
DEFAULT_ROPE_EA_N = 1.0e6


def polymer_density(material: str | None, default: str = DEFAULT_TWINE_MATERIAL) -> float:
    """Densidad del material [kg/m³] de la tabla; si no está, la de ``default`` (PA)."""
    tab = material_table()
    m = tab.find(material) or tab[default]
    rho = m.value("density_kg_m3")
    if rho is None:
        rho = tab[default].value("density_kg_m3")
    assert rho is not None
    return rho


def twine_modulus_pa(material: str | None, default: str = DEFAULT_TWINE_MATERIAL) -> float:
    """Módulo del hilo de red sobre ``π·d²/4`` [Pa] según el material (PA si no está).

    PA: 2 GPa (supuesto del simulador, del orden que dan la fibra de bexco2004 y el cociente
    hilo/fibra de legue2025); PE: 0,60 GPa (legue2025, hilo HDPE trenzado); PES, PP y HMPE: el de
    PA escalado por el cociente de módulos de fibra de bexco2004 (ver ``materials.yaml``).
    """
    tab = material_table()
    m = tab.find(material)
    gpa = m.value("twine_modulus_gpa") if m is not None else None
    if gpa is None:
        gpa = tab[default].value("twine_modulus_gpa")
    assert gpa is not None
    return gpa * 1e9


def rope_ea_n(material: str | None, diameter_mm: float) -> float | None:
    """EA de un cabo de fibra por la relación ``EA = k·d²`` de la tabla [N] (OrcaFlex).

    Para el cabo combinado devuelve el supuesto ``rope_ea_n`` (1·10⁶ N, «A VERIFICAR»); ``None``
    si la tabla no trae relación para el material (PE, HMPE) o el material no está.
    """
    m = material_table().find(material)
    if m is None:
        return None
    k = m.value("rope_ea_n_per_mm2")
    if k is not None:
        return k * diameter_mm**2
    return m.value("rope_ea_n")


def wire_core(core: str | None, construction: str | None = None) -> Literal["FC", "IWRC"]:
    """Alma del cable: ``IWRC`` si lo dice ``core`` (o la construcción), si no ``FC``.

    Sin dato se toma alma de fibra (módulo menor, del lado conservador para el estiramiento).
    """
    text = f"{core or ''} {construction or ''}".upper()
    return "IWRC" if "IWRC" in text and "FC O IWRC" not in text else "FC"


def wire_rope_ea_n(diameter_mm: float, core: str | None = "FC") -> float:
    """EA del cable de acero 6x19 sobre el diámetro nominal [N]: ``EA = k·d²`` (OrcaFlex/HER).

    ``k`` = 36 700 N/mm² con alma de fibra y 40 400 N/mm² con alma de acero, es decir un módulo
    efectivo de 46,9 o 51,4 GPa sobre ``π·d²/4`` (103 o 113 GPa sobre el área metálica, 0,455 de
    la nominal).
    """
    sw = material_table()["steel_wire_rope"]
    key = "ea_iwrc_n_per_mm2" if wire_core(core) == "IWRC" else "ea_fc_n_per_mm2"
    k = sw.value(key)
    assert k is not None
    return k * diameter_mm**2


def wire_rope_modulus_pa(core: str | None = "FC") -> float:
    """Módulo efectivo del cable de acero 6x19 sobre el área nominal [Pa] (46,9 o 51,4 GPa)."""
    sw = material_table()["steel_wire_rope"]
    key = "effective_modulus_iwrc_gpa" if wire_core(core) == "IWRC" else "effective_modulus_fc_gpa"
    gpa = sw.value(key)
    assert gpa is not None
    return gpa * 1e9


def ea_from_breaking_load_n(breaking_load_n: float, elongation_pct: float) -> float:
    """EA secante ≈ carga de rotura / alargamiento de rotura [N] (derivado, cota inferior).

    Un cabo o hilo se pone más rígido cerca de la rotura que al comienzo; la secante entre cero y
    la rotura subestima la rigidez a la carga de trabajo de un cable de acero y la sobrestima en
    un cabo de fibra trabajado. Sirve cuando no hay otro dato.
    """
    if elongation_pct <= 0:
        raise ValueError("el alargamiento de rotura debe ser > 0")
    return breaking_load_n / (elongation_pct / 100.0)


def _polymer_densities() -> dict[str, float]:
    """Densidades de los polímeros que el libro no trae, desde la tabla de materiales."""
    tab = material_table()
    out: dict[str, float] = {}
    for name in ("PE", "PP", "PES", "UHMWPE"):
        m = tab.find(name)
        rho = m.value("density_kg_m3") if m is not None else None
        if rho is not None:
            out[name] = rho
    return out


#: Polímeros que el libro Excel no trae (sólo tiene PA): densidad usual [kg/m³] para las redes
#: del catálogo FAO (Fase 12), tomada de la tabla de materiales con fuentes (Fase 19.1). PE:
#: polietileno; PP: polipropileno; PES: poliéster; UHMWPE: HMPE (Dyneema).
POLYMER_DENSITY_KG_M3: dict[str, float] = _polymer_densities()


def materials_from_catalogue(catalogue: Catalogue) -> tuple[Material, ...]:
    """Convierte el catálogo genérico (``load_catalogue("materials")``) en :class:`Material`.

    Agrega una entrada genérica (sólo densidad) por cada polímero de
    :data:`POLYMER_DENSITY_KG_M3` que el catálogo no tenga.
    """
    fields = {f for f in Material.__dataclass_fields__}
    out: list[Material] = []
    for item in catalogue.items:
        kwargs = {k: v for k, v in item.items() if k in fields}
        out.append(Material(**kwargs))
    present = {m.material.upper() for m in out}
    for name, rho in POLYMER_DENSITY_KG_M3.items():
        if name not in present:
            out.append(Material(id=f"{name.lower()}_generic", material=name, density_kg_m3=rho))
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
        # Alias de la tabla de materiales (HMPE = UHMWPE, nylon = PA, …).
        tab = material_table()
        wanted = tab.find(material)
        if wanted is not None:
            candidates = [m for m in materials if tab.find(m.material) is wanted]
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
