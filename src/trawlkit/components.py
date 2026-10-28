"""Catálogo de componentes del arte: paño, cables, cabos, portones, boyas, cadenas y grilletes.

Fase 13; los grilletes, desde la Fase 19.2.

Cada componente es un ítem con su fuente y la procedencia de cada valor, como las redes del
catálogo FAO (:mod:`trawlkit.provenance`):

* **Genéricos** (``brand = None``): lo que se consigue en cualquier ferretería naval, a tamaños
  estándar, con los valores que dan las tablas de referencia (FAO *Fisherman's Workbook*) por
  material y construcción. Son la base: todo componente de marca dice a qué genérico equivale
  (``generic_of``).
* **De fabricante**: datos puntuales de fichas técnicas públicas, citadas (no se copian tablas
  enteras).
* **Usados en la flota**: lo que informan los estudios de flotas (FAO REBYC, BOBP, el libro Excel
  de la A-3).
* **Aportes de usuarios** (``status = "user"``): cargados en la app, sin verificar.

Los archivos están en ``trawlkit/data/components/<tipo>/<fuente>.yaml`` y los genera
``tools/components/build_components.py``. :func:`load_components` los junta y valida;
:func:`check` revisa la coherencia física de un ítem (peso por metro contra diámetro, carga de
rotura dentro del rango del material, flotación contra volumen, polar del portón plausible).
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from functools import cache
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import Field, TypeAdapter

from trawlkit.i18n import N_, t
from trawlkit.io.loader import DATA_DIR
from trawlkit.io.schema import (
    Door,
    DoorCoefficients,
    NetSpec,
    Provenance,
    ProvenanceKind,
    SourceDocument,
    _Model,
)
from trawlkit.materials import (
    ea_from_breaking_load_n,
    material_table,
    rope_ea_n,
    twine_modulus_pa,
    wire_core,
    wire_rope_ea_n,
)
from trawlkit.netcheck import Issue

#: Carpeta de los catálogos de componentes.
COMPONENTS_DIR = DATA_DIR / "components"

ComponentKind = Literal["twine", "wire", "rope", "door", "float", "chain", "shackle"]
KINDS: tuple[ComponentKind, ...] = (
    "twine",
    "wire",
    "rope",
    "door",
    "float",
    "chain",
    "shackle",
)

#: Nombre de cada tipo en castellano (se traduce con ``t`` al usarlo).
KIND_LABEL: dict[str, str] = {
    "twine": N_("Paño e hilo"),
    "wire": N_("Cable de acero"),
    "rope": N_("Cabo"),
    "door": N_("Portón"),
    "float": N_("Boya"),
    "chain": N_("Cadena"),
    "shackle": N_("Grillete"),
}

Status = Literal["published", "user", "draft"]

#: Regiones (para filtrar lo que se consigue en cada puerto).
REGIONS: tuple[str, ...] = (
    "global",
    "latam",
    "europe",
    "africa",
    "south_asia",
    "southeast_asia",
    "north_america",
)


class Price(_Model):
    """Precio orientativo de un componente: siempre con fecha y fuente."""

    value: float = Field(ge=0)
    currency: str = Field(description="Código ISO 4217 (USD, ARS, EUR…)")
    unit: Literal["kg", "m", "unit"]
    date: str = Field(description="AAAA-MM o AAAA-MM-DD")
    source: str


class ComponentBase(_Model):
    """Campos comunes de todo componente del catálogo."""

    id: str
    kind: ComponentKind
    name: str
    brand: str | None = Field(default=None, description="None = genérico")
    product: str | None = None
    country: str | None = None
    regions: list[str] = Field(default_factory=list)
    generic_of: str | None = Field(default=None, description="Id del genérico equivalente")
    status: Status = "published"
    sources: list[SourceDocument] = Field(default_factory=list)
    provenance: dict[str, Provenance] = Field(default_factory=dict)
    price: Price | None = None
    notes: list[str] = Field(default_factory=list)

    @property
    def is_generic(self) -> bool:
        """Si es un genérico (sin marca; un aporte de usuario nunca lo es)."""
        return self.brand is None and self.status != "user"


class TwineItem(ComponentBase):
    """Hilo de red (paño): material, Rtex, diámetro, rendimiento y carga de rotura."""

    kind: Literal["twine"] = "twine"
    material: str = Field(description="PA, PE, PP, PES, UHMWPE")
    construction: str | None = Field(default=None, description="torcido, trenzado, monofilamento")
    rtex: float | None = Field(default=None, gt=0)
    diameter_mm: float = Field(gt=0)
    runnage_m_per_kg: float | None = Field(default=None, gt=0)
    breaking_load_kgf: float | None = Field(default=None, gt=0, description="Seco, sin nudo")
    knot_breaking_load_kgf: float | None = Field(
        default=None, gt=0, description="Con nudo (mojado si la fuente lo indica)"
    )
    knotted: bool = True
    elongation_pct: float | None = Field(default=None, gt=0, description="Alargamiento de rotura")
    ea_kn: float | None = Field(default=None, gt=0, description="Rigidez axial EA [kN]")


class WireItem(ComponentBase):
    """Cable de acero (de remolque, malletas o patentes)."""

    kind: Literal["wire"] = "wire"
    construction: str = Field(description="6x7, 6x12, 6x19 (12/6/1), 6x19 (9/9/1), 6x24, 6x26")
    core: str | None = Field(default=None, description="FC (fibra), IWRC (acero)")
    diameter_mm: float = Field(gt=0)
    weight_kg_per_m: float = Field(gt=0)
    breaking_load_t: float = Field(gt=0, description="Carga de rotura mínima [t]")
    galvanised: bool = True
    elongation_pct: float | None = Field(default=None, gt=0, description="Alargamiento de rotura")
    ea_kn: float | None = Field(default=None, gt=0, description="Rigidez axial EA [kN]")


class RopeItem(ComponentBase):
    """Cabo de fibra o combinado (relingas, malletas, patentes)."""

    kind: Literal["rope"] = "rope"
    material: str = Field(description="PA, PE, PP, PES, HMPE, combinado (acero + fibra)")
    construction: str | None = None
    diameter_mm: float = Field(gt=0)
    weight_kg_per_m: float = Field(gt=0)
    breaking_load_t: float = Field(gt=0)
    elongation_pct: float | None = Field(default=None, gt=0, description="Alargamiento de rotura")
    ea_kn: float | None = Field(default=None, gt=0, description="Rigidez axial EA [kN]")


class DoorItem(ComponentBase):
    """Portón de arrastre, con su polar CL/CD y el rango de potencia para el que se usa."""

    kind: Literal["door"] = "door"
    type: str = Field(description="flat, flat_wood, v, oval, cambered, suberkrub, shrimp")
    length_m: float = Field(gt=0)
    height_m: float = Field(gt=0)
    area_m2: float = Field(gt=0)
    weight_air_kg: float | None = Field(default=None, gt=0)
    weight_water_kg: float | None = Field(default=None, gt=0)
    hp_range: tuple[float, float] | None = None
    coefficients: list[DoorCoefficients] = Field(default_factory=list)

    def to_door(self) -> Door:
        """Portón del motor (:class:`~trawlkit.io.schema.Door`)."""
        coef = self.model_extra.get("weight_water_coefficient") if self.model_extra else None
        data: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "length_m": self.length_m,
            "height_m": self.height_m,
            "area_m2": self.area_m2,
            "aspect_ratio": self.height_m / self.length_m,
            "weight_air_kg": self.weight_air_kg,
            "weight_water_kg": self.weight_water_kg,
            "coefficients": [c.model_dump() for c in self.coefficients],
        }
        if coef is not None:
            data["weight_water_coefficient"] = coef
        return Door.model_validate(data)


class FloatItem(ComponentBase):
    """Boya de relinga."""

    kind: Literal["float"] = "float"
    material: str = Field(description="plástico, aluminio, vidrio, PVC espumado")
    mount: str | None = Field(default=None, description="agujero central, lateral, orejas")
    diameter_mm: float = Field(gt=0)
    buoyancy_kgf: float = Field(gt=0)
    max_depth_m: float | None = Field(default=None, gt=0)
    volume_l: float | None = Field(default=None, gt=0)


class ChainItem(ComponentBase):
    """Cadena (lastre, reglaje, cadenas de peso)."""

    kind: Literal["chain"] = "chain"
    link: str = Field(description="corto, largo")
    link_diameter_mm: float = Field(gt=0)
    grade: str | None = None
    weight_kg_per_m: float = Field(gt=0)
    breaking_load_t: float | None = Field(default=None, gt=0)


class ShackleItem(ComponentBase):
    """Grillete (unión de cables, cadenas y portones; Fase 19.2).

    ``wll_t`` es la carga de trabajo (WLL) de la ficha; ``breaking_load_t``, la rotura mínima
    (en general ``design_factor`` × WLL); ``size`` es el tamaño nominal tal como lo da el
    fabricante (pulgadas o mm).
    """

    kind: Literal["shackle"] = "shackle"
    type: str = Field(default="bow", description="bow (lira), dee (recto)")
    size: str = Field(description="Tamaño nominal de la ficha (1/2 in, 13 mm)")
    body_diameter_mm: float = Field(gt=0, description="Diámetro del cuerpo (arco)")
    pin_diameter_mm: float | None = Field(default=None, gt=0, description="Diámetro del perno")
    wll_t: float = Field(gt=0, description="Carga de trabajo (WLL) [t]")
    breaking_load_t: float | None = Field(default=None, gt=0, description="Rotura mínima [t]")
    design_factor: float | None = Field(default=None, gt=0, description="Rotura / WLL")
    weight_kg: float = Field(gt=0, description="Peso de una pieza [kg]")
    galvanised: bool = True


Component = Annotated[
    TwineItem | WireItem | RopeItem | DoorItem | FloatItem | ChainItem | ShackleItem,
    Field(discriminator="kind"),
]
_ADAPTER: TypeAdapter[Any] = TypeAdapter(Component)

MODELS: dict[str, type[ComponentBase]] = {
    "twine": TwineItem,
    "wire": WireItem,
    "rope": RopeItem,
    "door": DoorItem,
    "float": FloatItem,
    "chain": ChainItem,
    "shackle": ShackleItem,
}


def parse_component(data: dict[str, Any]) -> ComponentBase:
    """Valida un componente (``kind`` elige el modelo)."""
    item: ComponentBase = _ADAPTER.validate_python(data)
    return item


def component_files(kind: str) -> list[Path]:
    """Archivos YAML de un tipo de componente."""
    return sorted((COMPONENTS_DIR / kind).glob("*.yaml"))


#: Cargador de YAML: el de libyaml si está (el catálogo de portones pasa de 1000 ítems desde la
#: Fase 20.1), si no el de Python puro (Pyodide).
_YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


@cache
def _load_kind(kind: str) -> tuple[ComponentBase, ...]:
    out: list[ComponentBase] = []
    seen: set[str] = set()
    for path in component_files(kind):
        with path.open(encoding="utf-8") as fh:
            raw = yaml.load(fh, Loader=_YAML_LOADER) or {}
        sources = [SourceDocument.model_validate(s) for s in raw.get("sources", [])]
        for rec in raw.get("items", []):
            data = {"kind": kind, **rec}
            if sources and "sources" not in data:
                data["sources"] = [s.model_dump(exclude_none=True) for s in sources]
            item = parse_component(data)
            if item.id in seen:
                raise ValueError(f"id de componente repetido: {kind}/{item.id} ({path.name})")
            seen.add(item.id)
            out.append(item)
    return tuple(out)


#: Aportes de usuario habilitados en el pedido en curso (ver :func:`user_components`).
_USER_ITEMS: ContextVar[tuple[ComponentBase, ...]] = ContextVar("user_components", default=())


@contextmanager
def user_components(
    items: Iterable[ComponentBase | Mapping[str, Any]],
) -> Iterator[tuple[ComponentBase, ...]]:
    """Habilita aportes de usuario (``status: user``) mientras dura el bloque.

    Dentro del bloque, :func:`load_components` y :func:`get_component` los incluyen como si
    estuvieran en el catálogo, con su estado de aporte sin verificar. Lo usa la API para que un
    aporte guardado en el navegador entre en el cálculo sólo en ese pedido.
    """
    parsed = tuple(
        it if isinstance(it, ComponentBase) else parse_component({**it, "status": "user"})
        for it in items
    )
    token = _USER_ITEMS.set(parsed)
    try:
        yield parsed
    finally:
        _USER_ITEMS.reset(token)


def load_components(
    kind: str,
    *,
    brands: Iterable[str] | None = None,
    region: str | None = None,
    generic_only: bool = False,
    statuses: Iterable[str] = ("published",),
    extra: Iterable[ComponentBase] = (),
) -> list[ComponentBase]:
    """Componentes de un tipo, con filtros.

    * ``brands``: marcas permitidas (los genéricos siempre pasan);
    * ``region``: región del puerto (los genéricos y los de región ``global`` siempre pasan);
    * ``generic_only``: sólo genéricos;
    * ``statuses``: estados admitidos (por defecto sólo los publicados);
    * ``extra``: componentes agregados por el usuario (aportes), que pasan los mismos filtros.

    Los aportes habilitados con :func:`user_components` se agregan siempre, con el estado
    ``user`` admitido.
    """
    if kind not in MODELS:
        raise KeyError(
            t(
                "tipo de componente desconocido: {kind!r} (use {kinds})",
                kind=kind,
                kinds=", ".join(KINDS),
            )
        )
    enabled = _USER_ITEMS.get()
    allowed = set(statuses) | ({"user"} if enabled else set())
    extra = (*extra, *enabled)
    wanted = None if brands is None else {b.lower() for b in brands}
    out: list[ComponentBase] = []
    for item in (*_load_kind(kind), *(e for e in extra if e.kind == kind)):
        if item.status not in allowed:
            continue
        if generic_only and not item.is_generic:
            continue
        if wanted is not None and not item.is_generic and (item.brand or "").lower() not in wanted:
            continue
        if (
            region is not None
            and not item.is_generic
            and item.regions
            and region not in item.regions
            and "global" not in item.regions
        ):
            continue
        out.append(item)
    return out


def get_component(kind: str, item_id: str) -> ComponentBase:
    """Componente por id (``KeyError`` si no existe; incluye borradores y aportes)."""
    for item in load_components(kind, statuses=("published", "draft", "user")):
        if item.id == item_id:
            return item
    raise KeyError(t("componente desconocido: {kind}/{id}", kind=kind, id=item_id))


def generic_for(item: ComponentBase) -> ComponentBase | None:
    """Genérico equivalente de un componente (él mismo si ya es genérico)."""
    if item.is_generic:
        return item
    if item.generic_of is None:
        return None
    try:
        return get_component(item.kind, item.generic_of)
    except KeyError:
        return None


# ---------------------------------------------------------------------------------------------
# Validador físico
# ---------------------------------------------------------------------------------------------


def _densities() -> dict[str, float]:
    tab = material_table()
    names = {"PA": "PA", "PE": "PE", "PP": "PP", "PES": "PES", "UHMWPE": "HMPE", "HMPE": "HMPE"}
    out = {k: tab[v].value("density_kg_m3") for k, v in names.items()}
    out["steel"] = tab["steel_wire_rope"].value("density_kg_m3")
    return {k: float(v) for k, v in out.items() if v is not None}


#: Densidad de los materiales [kg/m³], de la tabla de materiales con fuentes
#: (:func:`trawlkit.materials.material_table`, Fase 19.1).
DENSITY_KG_M3: dict[str, float] = _densities()

#: Rangos plausibles de cada verificación (mínimo, máximo).
#: Peso del cable de acero por mm² de diámetro [kg/m/mm²]: 6x12 con almas de fibra en los
#: cordones 0,0024, 6x7 FC 0,0035 … 6x26 IWRC compactado 0,0046 (Workbook, Bridon-Bekaert 2023).
WIRE_WEIGHT_K = (0.0022, 0.0050)
#: Carga de rotura del cable por mm² de diámetro [t/mm²]: 1420–2160 N/mm² de grado.
WIRE_MBL_K = (0.030, 0.100)
#: Fracción de llenado de un cabo de fibra (peso / (área del círculo × densidad)).
ROPE_FILL = (0.40, 1.15)
#: Tenacidad del hilo de red [gf/tex]: PE y PP estándar ≈ 25–45, PA ≈ 50, UHMWPE hasta 200.
TWINE_TENACITY = (10.0, 250.0)
#: Peso de la cadena por mm² de diámetro de eslabón [kg/m/mm²]: largo ≈ 0,018, corto ≈ 0,023.
CHAIN_WEIGHT_K = (0.014, 0.030)
#: Fracción de la flotación de una esfera del mismo diámetro (pared, agujeros, orejas).
FLOAT_FRACTION = (0.30, 1.02)
#: Peso del portón por m² [kg/m²]: madera ≈ 50, acero liviano ≈ 100, pelágico pesado ≈ 700.
DOOR_KG_M2 = (15.0, 800.0)
#: Peso del grillete por mm³ de diámetro del cuerpo [kg/mm³]: 1,2·10⁻⁴ (Crosby G-209 de 2½ in)
#: a 1,6·10⁻⁴ (Green Pin de 13 mm) en las fichas cargadas (Fase 19.2).
SHACKLE_WEIGHT_K = (0.8e-4, 2.5e-4)
#: WLL del grillete por mm² de diámetro del cuerpo [t/mm²]: 0,011–0,014 en las fichas cargadas.
SHACKLE_WLL_K = (0.006, 0.020)
#: Factor de diseño (rotura / WLL) de grilletes: 4:1 a 6:1 en las normas de izaje; 8 de margen.
SHACKLE_DESIGN_FACTOR = (4.0, 8.0)
#: Perno / cuerpo: el perno es igual o algo más grueso que el cuerpo (1,0–1,3 en las fichas).
SHACKLE_PIN_RATIO = (0.9, 1.6)


def _issue(item: ComponentBase, level: str, code: str, msg: str) -> Issue:
    return Issue(level, code, f"{item.kind}/{item.id}: {msg}", (item.id,))  # type: ignore[arg-type]


def _range(
    item: ComponentBase, value: float, rng: tuple[float, float], code: str, what: str
) -> Issue | None:
    lo, hi = rng
    if lo <= value <= hi:
        return None
    return _issue(
        item,
        "warning",
        code,
        t(
            "{what} = {value:.4g} fuera del rango {lo:g}–{hi:g}",
            what=what,
            value=value,
            lo=lo,
            hi=hi,
        ),
    )


def _below(item: ComponentBase, value: float, lo: float, code: str, what: str) -> Issue | None:
    if value >= lo:
        return None
    return _issue(
        item,
        "warning",
        code,
        t("{what} = {value:.4g} por debajo de {lo:g}", what=what, value=value, lo=lo),
    )


#: Margen del validador alrededor de los rangos de la tabla de materiales (tenacidad y
#: alargamiento): los rangos son el mínimo y el máximo de unas pocas tablas (redondeos de la
#: fuente, variación entre fabricantes). Sólo decide cuándo avisar; no es un dato del material.
TABLE_RANGE_MARGIN = 0.10


def _widen(lo: float, hi: float) -> tuple[float, float]:
    return lo * (1.0 - TABLE_RANGE_MARGIN), hi * (1.0 + TABLE_RANGE_MARGIN)


def tenacity_range_gf_tex(material: str, kind: str) -> tuple[float, float] | None:
    """Rango de tenacidad del material [gf/tex] para el validador (``kind``: ``twine`` o ``rope``).

    Hilo: seco sin nudo (Workbook, prado1990); cabo: seco (Workbook; HMPE de mennens_dynice78).
    Es el rango de la tabla ± :data:`TABLE_RANGE_MARGIN`; ``None`` si la tabla no lo trae para
    ese material.
    """
    m = material_table().find(material)
    key = "twine_tenacity_dry_gf_tex" if kind == "twine" else "rope_tenacity_gf_tex"
    v = m.get(key) if m is not None else None
    if v is None:
        return None
    return _widen(*(v.range or (v.value, v.value)))


def elongation_range_pct(material: str) -> tuple[float, float] | None:
    """Alargamientos de la tabla para el material [%]: (mínimo, máximo).

    Junta el alargamiento de rotura (fibra, monofilamento o alambre) y el del cabo al 75 % de la
    rotura (ramos1999), ± :data:`TABLE_RANGE_MARGIN`; con un solo dato (acero) el máximo es
    infinito: el cable se alarga al menos lo que su alambre. ``None`` si la tabla no trae
    alargamientos para el material.
    """
    m = material_table().find(material)
    if m is None:
        return None
    vals: list[float] = []
    for key in ("elongation_break_pct", "rope_elongation_75pct_mbl_pct"):
        v = m.get(key)
        if v is not None:
            vals += [v.value, *(v.range or ())]
    if not vals:
        return None
    lo, hi = _widen(min(vals), max(vals))
    return (lo, hi) if max(vals) > min(vals) else (lo, math.inf)


#: Aceleración de la gravedad para pasar kgf a N.
_G = 9.80665


def _breaking_load_n(item: ComponentBase) -> float | None:
    if isinstance(item, TwineItem):
        return item.breaking_load_kgf * _G if item.breaking_load_kgf else None
    if isinstance(item, WireItem | RopeItem):
        return item.breaking_load_t * 1000.0 * _G
    return None


def axial_stiffness(item: ComponentBase) -> tuple[float, Provenance] | None:
    """Rigidez axial EA [kN] de un hilo, cabo o cable, con su procedencia.

    En orden: ``ea_kn`` del ítem (dato de la ficha); si no, ``EA ≈ rotura / alargamiento de
    rotura`` cuando el ítem trae ``elongation_pct`` (derivada, secante); si no, la relación del
    material de la tabla de materiales (:mod:`trawlkit.materials`): ``EA = k·d²`` de OrcaFlex
    para cabos de PA, PES y PP, del cable 6x19 según el alma, y ``E·π·d²/4`` para el hilo. El
    cabo combinado no tiene relación con fuente: devuelve el supuesto del simulador (1·10⁶ N,
    «A VERIFICAR»). ``None`` para otros tipos o si la tabla no trae relación (cabo PE, HMPE).
    """
    if not isinstance(item, TwineItem | RopeItem | WireItem):
        return None
    if item.ea_kn is not None:
        prov = item.provenance.get("ea_kn") or Provenance(
            kind=ProvenanceKind.TRANSCRIBED, note=t("EA de la ficha del componente")
        )
        return item.ea_kn, prov
    mbl = _breaking_load_n(item)
    if item.elongation_pct is not None and mbl is not None:
        return ea_from_breaking_load_n(mbl, item.elongation_pct) / 1000.0, Provenance(
            kind=ProvenanceKind.DERIVED,
            note=t(
                "EA ≈ rotura / alargamiento de rotura = {mbl:.0f} N / {eps:g} %",
                mbl=mbl,
                eps=item.elongation_pct,
            ),
        )
    tab = material_table()
    if isinstance(item, WireItem):
        core = wire_core(item.core, item.construction)
        sv = tab["steel_wire_rope"].get(
            "ea_iwrc_n_per_mm2" if core == "IWRC" else "ea_fc_n_per_mm2"
        )
        ea = wire_rope_ea_n(item.diameter_mm, core)
    elif isinstance(item, RopeItem):
        m = tab.find(item.material)
        sv = None if m is None else (m.get("rope_ea_n_per_mm2") or m.get("rope_ea_n"))
        ea_n = rope_ea_n(item.material, item.diameter_mm)
        if ea_n is None or sv is None:
            return None
        ea = ea_n
    else:
        m = tab.find(item.material)
        sv = None if m is None else m.get("twine_modulus_gpa")
        if sv is None:
            return None
        ea = twine_modulus_pa(item.material) * math.pi * (item.diameter_mm / 1000.0) ** 2 / 4.0
    assert sv is not None
    kind = ProvenanceKind.ASSUMED if sv.to_verify else ProvenanceKind.DERIVED
    note = (
        t("supuesto de la tabla de materiales (sin fuente), A VERIFICAR")
        if sv.to_verify
        else t("relación del material ({unit}) de la tabla de materiales", unit=sv.unit or "")
    )
    return ea / 1000.0, Provenance(kind=kind, document=sv.source, note=note)


def check(item: ComponentBase) -> list[Issue]:
    """Coherencia física de un componente (lista vacía si todo cierra)."""
    issues: list[Issue | None] = []
    if isinstance(item, WireItem):
        d2 = item.diameter_mm**2
        issues.append(
            _range(item, item.weight_kg_per_m / d2, WIRE_WEIGHT_K, "weight", t("kg/m por mm²"))
        )
        issues.append(_range(item, item.breaking_load_t / d2, WIRE_MBL_K, "mbl", t("t por mm²")))
    elif isinstance(item, RopeItem):
        mat = item.material.upper()
        if mat in DENSITY_KG_M3:
            area = math.pi / 4.0 * (item.diameter_mm / 1000.0) ** 2
            fill = item.weight_kg_per_m / (area * DENSITY_KG_M3[mat])
            issues.append(_range(item, fill, ROPE_FILL, "weight", t("llenado del cabo")))
        rng = tenacity_range_gf_tex(item.material, "rope")
        if rng is not None:
            issues.append(
                _range(
                    item,
                    item.breaking_load_t / item.weight_kg_per_m,
                    rng,
                    "tenacity",
                    t("tenacidad del cabo [gf/tex] según el material"),
                )
            )
    elif isinstance(item, TwineItem):
        if item.rtex and item.runnage_m_per_kg:
            expect = 1e6 / item.rtex
            if abs(item.runnage_m_per_kg - expect) / expect > 0.20:
                issues.append(
                    _issue(
                        item,
                        "warning",
                        "runnage",
                        t(
                            "rendimiento {runnage:g} m/kg y Rtex {rtex:g} no "
                            "concuerdan (10⁶/Rtex = {expect:.0f} m/kg)",
                            runnage=item.runnage_m_per_kg,
                            rtex=item.rtex,
                            expect=expect,
                        ),
                    )
                )
        rtex = item.rtex or (1e6 / item.runnage_m_per_kg if item.runnage_m_per_kg else None)
        if rtex and item.breaking_load_kgf:
            issues.append(
                _range(
                    item,
                    item.breaking_load_kgf * 1000.0 / rtex,
                    TWINE_TENACITY,
                    "tenacity",
                    t("tenacidad [gf/tex]"),
                )
            )
            rng = tenacity_range_gf_tex(item.material, "twine")
            if rng is not None:
                issues.append(
                    _range(
                        item,
                        item.breaking_load_kgf * 1000.0 / rtex,
                        rng,
                        "tenacity_material",
                        t("tenacidad seca sin nudo [gf/tex] según el material"),
                    )
                )
        if (
            item.knot_breaking_load_kgf
            and item.breaking_load_kgf
            and item.knot_breaking_load_kgf > 1.5 * item.breaking_load_kgf
        ):
            issues.append(
                _issue(
                    item,
                    "warning",
                    "knot",
                    t("la rotura con nudo supera en más de 50 % a la rotura sin nudo"),
                )
            )
    elif isinstance(item, ChainItem):
        issues.append(
            _range(
                item,
                item.weight_kg_per_m / item.link_diameter_mm**2,
                CHAIN_WEIGHT_K,
                "weight",
                t("kg/m por mm²"),
            )
        )
    elif isinstance(item, FloatItem):
        sphere = math.pi / 6.0 * (item.diameter_mm / 10.0) ** 3 / 1000.0 * 1.025
        issues.append(
            _range(
                item, item.buoyancy_kgf / sphere, FLOAT_FRACTION, "buoyancy", t("flotación/esfera")
            )
        )
    elif isinstance(item, ShackleItem):
        d = item.body_diameter_mm
        issues.append(
            _range(
                item, item.weight_kg / d**3, SHACKLE_WEIGHT_K, "weight", t("kg por mm³ del cuerpo")
            )
        )
        issues.append(_range(item, item.wll_t / d**2, SHACKLE_WLL_K, "wll", t("WLL [t] por mm²")))
        if item.breaking_load_t is not None:
            if item.breaking_load_t < item.wll_t:
                issues.append(
                    _issue(
                        item,
                        "error",
                        "mbl",
                        t(
                            "rotura {mbl:g} t menor que la carga de trabajo {wll:g} t",
                            mbl=item.breaking_load_t,
                            wll=item.wll_t,
                        ),
                    )
                )
            else:
                issues.append(
                    _range(
                        item,
                        item.breaking_load_t / item.wll_t,
                        SHACKLE_DESIGN_FACTOR,
                        "design_factor",
                        t("rotura / WLL"),
                    )
                )
        if item.pin_diameter_mm is not None:
            issues.append(
                _range(
                    item, item.pin_diameter_mm / d, SHACKLE_PIN_RATIO, "pin", t("perno / cuerpo")
                )
            )
    elif isinstance(item, DoorItem):
        shape = item.area_m2 / (item.length_m * item.height_m)
        if not 0.55 <= shape <= 1.05:
            issues.append(
                _issue(
                    item,
                    "warning",
                    "area",
                    t(
                        "superficie {area:g} m² y medidas {length:g} × {height:g} m no concuerdan",
                        area=item.area_m2,
                        length=item.length_m,
                        height=item.height_m,
                    ),
                )
            )
        if item.weight_air_kg:
            issues.append(
                _range(item, item.weight_air_kg / item.area_m2, DOOR_KG_M2, "weight", "kg/m²")
            )
        elif not item.weight_water_kg:
            # Fase 19.3: hay fabricantes que no publican el peso («sur demande»); no se inventa.
            issues.append(
                _issue(
                    item,
                    "warning",
                    "weight_missing",
                    t("sin peso publicado: no se puede verificar el peso en el agua del portón"),
                )
            )
        usable = [c for c in item.coefficients if c.cl is not None and c.cd is not None]
        if not usable:
            issues.append(_issue(item, "error", "polar", t("sin coeficientes CL/CD")))
        for c in usable:
            assert c.cl is not None and c.cd is not None
            if not (0.0 < c.cl <= 2.6 and 0.0 < c.cd <= 1.6):
                issues.append(
                    _issue(
                        item,
                        "warning",
                        "polar",
                        t(
                            "CL {cl:g} / CD {cd:g} a {angle:g}° fuera de lo plausible",
                            cl=c.cl,
                            cd=c.cd,
                            angle=c.angle_deg,
                        ),
                    )
                )
    if isinstance(item, TwineItem | RopeItem | WireItem) and item.elongation_pct is not None:
        material = "steel" if isinstance(item, WireItem) else item.material
        rng_e = elongation_range_pct(material)
        if rng_e is not None:
            what = t("alargamiento de rotura [%] según el material")
            issues.append(
                _below(item, item.elongation_pct, rng_e[0], "elongation", what)
                if math.isinf(rng_e[1])
                else _range(item, item.elongation_pct, rng_e, "elongation", what)
            )
    if item.generic_of is not None and generic_for(item) is None:
        issues.append(
            _issue(
                item,
                "warning",
                "generic",
                t("genérico equivalente desconocido: {id}", id=item.generic_of),
            )
        )
    return [i for i in issues if i is not None]


def apply_twine(spec: NetSpec, twine: TwineItem, *, codend: bool = False) -> NetSpec:
    """Red con el hilo ``twine`` en todos los paños (salvo el copo, si ``codend`` es falso).

    Reemplaza material, diámetro, Rtex y rendimiento; los paños del copo suelen ir con un hilo
    más grueso y se dejan como estaban. Agrega una nota a la red.
    """
    from trawlkit.io.schema import Section

    runnage = twine.runnage_m_per_kg or (1e6 / twine.rtex if twine.rtex else None)
    panels = []
    for p in spec.panels:
        if p.section is Section.CODEND and not codend:
            panels.append(p)
            continue
        panels.append(
            p.model_copy(
                update={
                    "material": twine.material,
                    "twine_diameter_mm": twine.diameter_mm,
                    "rtex": twine.rtex,
                    "runnage_m_per_kg": runnage,
                }
            )
        )
    note = t("Paño reemplazado por {name} ({id})", name=twine.name, id=twine.id) + (
        "" if codend else t(", salvo el copo")
    )
    return spec.model_copy(update={"panels": panels, "notes": [*spec.notes, note]})


def summary(items: Iterable[ComponentBase]) -> dict[str, Any]:
    """Cantidad de ítems por tipo, marca y estado (para el libro y la API)."""
    out: dict[str, Any] = {"items": 0, "generic": 0, "brands": set(), "statuses": {}}
    for it in items:
        out["items"] += 1
        out["generic"] += it.is_generic
        if it.brand:
            out["brands"].add(it.brand)
        out["statuses"][it.status] = out["statuses"].get(it.status, 0) + 1
    out["brands"] = sorted(out["brands"])
    return out


__all__ = [
    "COMPONENTS_DIR",
    "KINDS",
    "KIND_LABEL",
    "REGIONS",
    "ChainItem",
    "ComponentBase",
    "DoorItem",
    "FloatItem",
    "Price",
    "RopeItem",
    "ShackleItem",
    "TwineItem",
    "WireItem",
    "apply_twine",
    "axial_stiffness",
    "check",
    "elongation_range_pct",
    "generic_for",
    "get_component",
    "load_components",
    "parse_component",
    "summary",
    "tenacity_range_gf_tex",
    "user_components",
]
