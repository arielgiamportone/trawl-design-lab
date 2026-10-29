"""Biblioteca de polares de portones (Fase 19.3): coeficientes CL/CD medidos y polar por tipo.

Los datos están en ``trawlkit/data/door_polars.yaml``:

* las 26 hojas de datos del Apéndice IV de Seafish/IFREMER/DIFTA (1993) (``sfia1993``), modelos
  ensayados en tanque de flujo a 25–45°, con medidas, relación de aspecto, peso y CL máximo;
* las Tablas 2 y 3 de Mellibovsky et al. (2018) (``mellibovsky2018``): portones pelágicos de alta
  relación de aspecto Thyborøn 15 VF y Grilli Fly, en tanque de flujo y en túnel de viento.

Las polares del portón plano y del oval del libro Excel de la A-3 (``doors.yaml``) son, número
por número, las hojas «Flat Wooden» y «Morgère Polyvalent Ovale» de Seafish (1993).

:func:`polar_for_type` da una polar representativa por tipo de portón con la regla de
:data:`TYPE_POLARS`: una hoja tal cual (*transcripta*), la media de varias hojas a los ángulos
que todas ensayaron (*derivada*; Seafish 1993, sección 3-16, recomienda promediar los tres
portones en V) o un ajuste de los puntos medidos (*derivada*). :data:`ATTACK_ANGLES` da el
rango de ángulo de ataque recomendado por tipo, con su fuente.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache
from typing import Any, Literal

import numpy as np
from pydantic import Field

from trawlkit.compat import Compat
from trawlkit.i18n import N_, t
from trawlkit.io import DATA_DIR
from trawlkit.io.schema import Door, DoorCoefficients, Provenance, ProvenanceKind, _Model

#: Archivo de la biblioteca.
POLARS_FILE = DATA_DIR / "door_polars.yaml"

#: Tipos de portón con polar representativa.
DoorType = Literal["flat", "v", "oval", "cambered", "multifoil", "high_aspect"]
DOOR_TYPES: tuple[str, ...] = ("flat", "v", "oval", "cambered", "multifoil", "high_aspect")

#: Rótulo de cada tipo (se traduce con ``t`` al usarlo).
DOOR_TYPE_LABEL: dict[str, str] = {
    "flat": N_("Plano rectangular"),
    "v": N_("En V"),
    "oval": N_("Oval cambado"),
    "cambered": N_("Cambado (con ranura)"),
    "multifoil": N_("Multiperfil"),
    "high_aspect": N_("Pelágico de alta relación de aspecto (Süberkrüb)"),
}

#: Tipos del catálogo de componentes y del libro que usan la polar de otro tipo.
TYPE_ALIASES: dict[str, str] = {
    "flat_wood": "flat",
    "flat_wood_iron_frame": "flat",
    "shrimp": "flat",
    "oval_polyvalent": "oval",
    "polyvalent": "oval",
    "suberkrub": "high_aspect",
    "pelagic": "high_aspect",
    "slotted": "cambered",
}


class PolarPoint(DoorCoefficients):
    """Un punto de la polar medida; ``beta_deg`` es el ángulo de deriva (Mellibovsky 2018)."""

    beta_deg: float | None = None


class PolarSource(_Model):
    """Documento, página y figura de una polar."""

    document: str
    page: str | None = None
    figure: str | None = None


class PolarConditions(_Model):
    """Condiciones de ensayo de un conjunto de polares."""

    document: str
    facility: str
    speed_ms: float | None = None
    reynolds: float | None = None
    page: str | None = None
    note: str | None = None


class MeasuredPolar(_Model):
    """Polar medida de un modelo de portón, con su fuente y el modelo ensayado."""

    id: str
    name: str
    type: str = Field(description="flat, v, oval, cambered, multifoil, high_aspect, other")
    description: str | None = None
    source: PolarSource
    conditions: str
    model: dict[str, float] = Field(default_factory=dict)
    max_cl: DoorCoefficients | None = None
    coefficients: list[PolarPoint]

    def usable(self, *, with_max: bool = False) -> list[PolarPoint]:
        """Puntos con CL y CD (sin los ángulos no ensayados), ordenados por ángulo.

        Con ``with_max`` se agrega la fila «Maximum CL at» de la hoja (si su ángulo no está),
        como hace el libro Excel de la A-3 con el 32° del portón plano.
        """
        pts = [c for c in self.coefficients if c.cl is not None and c.cd is not None]
        m = self.max_cl
        if with_max and m is not None and m.angle_deg not in {c.angle_deg for c in pts}:
            pts.append(PolarPoint(angle_deg=m.angle_deg, cl=m.cl, cd=m.cd))
        return sorted(pts, key=lambda c: c.angle_deg)


class PolarLibrary(_Model):
    """La biblioteca: condiciones de ensayo y polares."""

    conditions: dict[str, PolarConditions]
    polars: list[MeasuredPolar]


@cache
def load_door_polars() -> PolarLibrary:
    """Lee y valida ``door_polars.yaml`` (con caché)."""
    import yaml

    with POLARS_FILE.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    lib = PolarLibrary.model_validate(raw)
    ids = [p.id for p in lib.polars]
    if len(ids) != len(set(ids)):
        raise ValueError("id de polar repetido en door_polars.yaml")
    for p in lib.polars:
        if p.conditions not in lib.conditions:
            raise ValueError(f"{p.id}: condiciones de ensayo desconocidas {p.conditions!r}")
    return lib


def get_polar(polar_id: str) -> MeasuredPolar:
    """Polar medida por ``id`` (``KeyError`` si no existe)."""
    for p in load_door_polars().polars:
        if p.id == polar_id:
            return p
    raise KeyError(t("polar de portón desconocida: {id!r}", id=polar_id))


# --- Polar representativa por tipo -----------------------------------------------------------

#: Regla de cada tipo: ``("single", [id])`` usa la hoja tal cual (con su fila de CL máximo);
#: ``("mean", ids)`` promedia CL
#: y CD a los ángulos que ensayaron todas; ``("fit", [id])`` ajusta CL lineal y CD cuadrático en
#: α a los puntos medidos (Mellibovsky et al. 2018: «CL casi lineal», «CD compatible con una
#: polar parabólica») y los evalúa a :data:`FIT_ANGLES`.
TYPE_POLARS: dict[str, tuple[str, tuple[str, ...], str]] = {
    "flat": (
        "single",
        ("sfia1993_flat_wooden",),
        N_("hoja «Flat Wooden» de Seafish (1993), la misma polar del libro Excel de la A-3"),
    ),
    "v": (
        "mean",
        ("sfia1993_reference_vee", "sfia1993_blooe_tech", "sfia1993_munkebo"),
        N_(
            "media de los tres portones en V sin camber ensayados por Seafish (Reference Vee, "
            "Blooe Tech y Munkebo): la sección 3-16 recomienda promediarlos"
        ),
    ),
    "oval": (
        "single",
        ("sfia1993_morgere_polyvalent_ovale",),
        N_("hoja «Morgère Polyvalent Ovale» de Seafish (1993), la del libro Excel de la A-3"),
    ),
    "cambered": (
        "mean",
        ("sfia1993_net_tec", "sfia1993_perfect_patent_b", "sfia1993_thyboron_type2_125"),
        N_(
            "media de los portones en V cambados que Seafish cita como de CL máximo 1,4–1,5 "
            '(Net Tec, Perfect Patent B y Thyborøn Type 2 de 125"; sección 3-14)'
        ),
    ),
    "multifoil": (
        "mean",
        (
            "sfia1993_bison_3_slots",
            "sfia1993_hydrofin_multifoil",
            "sfia1993_morgere_polyfoil",
            "sfia1993_fjortoft_multi_foil",
        ),
        N_(
            "media de los cuatro portones multiperfil de Seafish (Bison 3 Slots, Hydrofin, "
            "Morgère Polyfoil y Fjørtoft) a los ángulos que ensayaron todos (30–45°)"
        ),
    ),
    "high_aspect": (
        "fit",
        ("mellibovsky2018_thyboron_15vf_ft",),
        N_(
            "Thyborøn 15 VF (AR 2,5) en tanque de flujo (Mellibovsky et al. 2018, Tabla 2): CL "
            "lineal y CD cuadrático ajustados a los 11 puntos medidos (13,6–35,6°). El túnel de "
            "viento da 20–30 % más; los autores lo atribuyen a un error de la velocidad del "
            "tanque"
        ),
    ),
}

#: Ángulos a los que se evalúa el ajuste de la polar ``fit`` (dentro del rango medido).
FIT_ANGLES: tuple[float, ...] = (15.0, 20.0, 25.0, 30.0, 35.0)


@dataclass(frozen=True)
class AttackAngleRange:
    """Rango de ángulo de ataque recomendado para un tipo de portón, con su fuente."""

    min_deg: float
    max_deg: float
    document: str
    page: str
    note: str
    kind: str = "transcribed"

    @property
    def design_deg(self) -> float:
        """Ángulo de diseño del tipo: el centro del rango."""
        return 0.5 * (self.min_deg + self.max_deg)

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable (nota traducida)."""
        return {
            "min_deg": self.min_deg,
            "max_deg": self.max_deg,
            "document": self.document,
            "page": self.page,
            "kind": self.kind,
            "note": t(self.note),
        }


_WB_ANGLES = "Workbook, «Otter boards: proportions, angles of attack» (PDF p. 95)"

#: Ángulo de ataque recomendado por tipo (FAO *Fisherman's Workbook*; para los cambados y los
#: multiperfil, que el Workbook no trae, el ángulo de CL máximo de las hojas de Seafish 1993).
ATTACK_ANGLES: dict[str, AttackAngleRange] = {
    "flat": AttackAngleRange(
        35.0, 40.0, "prado1990", _WB_ANGLES, N_("portón rectangular plano: 35–40°")
    ),
    "v": AttackAngleRange(
        35.0,
        35.0,
        "prado1990",
        _WB_ANGLES,
        N_("portón rectangular en V: 35°; Seafish (sección 3-14): trabajo «alrededor de 35°»"),
    ),
    "oval": AttackAngleRange(35.0, 35.0, "prado1990", _WB_ANGLES, N_("portón oval: 35°")),
    "cambered": AttackAngleRange(
        34.0,
        37.0,
        "sfia1993",
        "Appendix IV-22, IV-24 a IV-26 (PDF pp. 153-157)",
        N_(
            "ángulo de CL máximo de Net Tec, Perfect Patent B y Thyborøn Type 2 (34–37°); en el "
            "mar el portón toma unos 4° menos que lo calculado (App. III-11)"
        ),
        "derived",
    ),
    "multifoil": AttackAngleRange(
        40.0,
        45.0,
        "sfia1993",
        "Section 3-15 (PDF p. 60); Appendix IV-5, IV-12, IV-16",
        N_(
            "los multiperfil tienen el CL máximo a ángulos altos (sección 3-15): 42–43° en las "
            "hojas de Bison 3 Slots, Hydrofin y Morgère Polyfoil"
        ),
        "derived",
    ),
    "high_aspect": AttackAngleRange(
        15.0,
        15.0,
        "prado1990",
        _WB_ANGLES,
        N_(
            "portón rectangular cambado (Süberkrüb): 15°; el Thyborøn 15 VF tiene su mejor "
            "CL/CD hacia 15° (Mellibovsky et al. 2015)"
        ),
    ),
}

#: Largo de cada pata de la pata de gallo (backstrop) en largos de portón: no menos que el largo
#: del portón y hasta 1,5 veces (Seafish 1993, sección 2.2.3, PDF p. 37; el Workbook da
#: a ≈ L × 1–2).
BACKSTROP_RATIO: tuple[float, float] = (1.0, 1.5)

#: Margen de seguridad sobre la superficie equivalente al pasar a un portón de más CL (Seafish
#: 1993, sección 3-16, PDF p. 61).
EQUIVALENT_AREA_MARGIN = 0.10


# --- CL efectivo calibrado (Fase 20.5) --------------------------------------------------------

#: Tipo de portón de las fuentes sin polar publicada al que se aplica el CL efectivo calibrado
#: (``door_type: polyvalent`` en ``design`` o en ``validation_doors`` de una red). Su polar es la
#: del tipo (hoja «Morgère Polyvalent Ovale» de Seafish 1993), supuesta.
CALIBRATED_DOOR_TYPE = "polyvalent"

#: Factor de CL efectivo del portón polivalente sin polar publicada (Fase 20.5, sólo modo
#: corregido): ``CL_ef = factor · CL`` de la hoja del tipo. Ajustado para que la DP media de los
#: 52 lances de IAT 151/18 (92,2 m) coincida con la del motor, con el factor de cable vigente
#: (1: la corrección de cable no se aplica; :func:`trawlkit.fieldcheck.polyvalent_cl_fit`).
POLYVALENT_CL_EFFECTIVE_FACTOR: float = 0.80

#: Procedencia de :data:`POLYVALENT_CL_EFFECTIVE_FACTOR`.
POLYVALENT_CL_PROVENANCE = Provenance(
    kind=ProvenanceKind.CALIBRATED,
    document="bartozzetti2018iat151",
    page="tabla 1 (52 lances)",
    note=N_(
        "CL efectivo de los portones polivalentes de 5,58 m² del INIDEP ajustado a la DP media "
        "medida de IAT 151/18 (sin corrección de cable); verificado con el Inf. Téc. 66 "
        "(casarsa2007inftec66) e IC 041/25 (alvarezcolombo2025ic041)"
    ),
)


def polar_published(door: Door) -> bool:
    """Indica si el portón tiene polar publicada (Fase 20.5); por defecto, sí.

    :func:`trawlkit.catalog.door_from_params` marca ``polar_published`` en el portón: ``True``
    con CL y CD de la fuente, ``False`` con la hoja de la biblioteca de su tipo.
    """
    return bool((door.model_extra or {}).get("polar_published", True))


def cl_effective_factor(door: Door, compat: Compat = Compat.CORRECTED) -> float:
    """Factor de CL efectivo del portón (Fase 20.5): :data:`POLYVALENT_CL_EFFECTIVE_FACTOR`.

    Sólo en modo :attr:`Compat.CORRECTED` y para un portón de tipo
    :data:`CALIBRATED_DOOR_TYPE` sin polar publicada; si no, 1.
    """
    if compat is Compat.EXCEL or door.type != CALIBRATED_DOOR_TYPE or polar_published(door):
        return 1.0
    return POLYVALENT_CL_EFFECTIVE_FACTOR


def canonical_type(door_type: str | None) -> str | None:
    """Tipo de :data:`DOOR_TYPES` de un tipo del catálogo (``flat_wood`` → ``flat``) o ``None``."""
    if door_type is None:
        return None
    key = door_type.strip().lower()
    key = TYPE_ALIASES.get(key, key)
    return key if key in DOOR_TYPES else None


@dataclass(frozen=True)
class TypePolar:
    """Polar representativa de un tipo de portón y cómo se obtuvo."""

    type: str
    coefficients: tuple[DoorCoefficients, ...]
    method: str  # single, mean, fit
    polar_ids: tuple[str, ...]
    documents: tuple[str, ...]
    pages: tuple[str, ...]
    note: str
    angles: AttackAngleRange = field(repr=False)

    @property
    def kind(self) -> ProvenanceKind:
        """Procedencia: *transcripta* si es una hoja tal cual; si no, *derivada*."""
        return ProvenanceKind.TRANSCRIBED if self.method == "single" else ProvenanceKind.DERIVED

    def provenance(self, *, applied_to: str | None = None) -> Provenance:
        """Procedencia de la polar; ``applied_to`` la marca como supuesta para otro portón."""
        note = t(self.note)
        if applied_to:
            note = t(
                "{applied}: el fabricante no publica la polar; se usa la del tipo ({note})",
                applied=applied_to,
                note=note,
            )
        return Provenance(
            kind=ProvenanceKind.ASSUMED if applied_to else self.kind,
            document=self.documents[0],
            page="; ".join(self.pages),
            note=note,
        )

    def coefficient_dicts(self) -> list[dict[str, float]]:
        """Coeficientes como dicts ``{angle_deg, cl, cd}`` (para el catálogo de componentes)."""
        out = []
        for c in self.coefficients:
            assert c.cl is not None and c.cd is not None
            out.append({"angle_deg": c.angle_deg, "cl": c.cl, "cd": c.cd})
        return out

    def at(self, angle_deg: float) -> tuple[float, float]:
        """(CL, CD) interpolados linealmente (recortado al rango de la polar)."""
        a = np.array([c.angle_deg for c in self.coefficients])
        cl = np.array([c.cl for c in self.coefficients], dtype=float)
        cd = np.array([c.cd for c in self.coefficients], dtype=float)
        return float(np.interp(angle_deg, a, cl)), float(np.interp(angle_deg, a, cd))

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "type": self.type,
            "label": t(DOOR_TYPE_LABEL[self.type]),
            "method": self.method,
            "kind": self.kind.value,
            "polar_ids": list(self.polar_ids),
            "documents": list(self.documents),
            "pages": list(self.pages),
            "note": t(self.note),
            "coefficients": self.coefficient_dicts(),
            "attack_angle": self.angles.to_dict(),
        }


def _mean_polar(polars: list[MeasuredPolar]) -> list[DoorCoefficients]:
    sets = [{c.angle_deg: c for c in p.usable()} for p in polars]
    common = sorted(set.intersection(*(set(s) for s in sets)))
    out = []
    for a in common:
        cl = float(np.mean([s[a].cl for s in sets]))
        cd = float(np.mean([s[a].cd for s in sets]))
        out.append(DoorCoefficients(angle_deg=a, cl=round(cl, 3), cd=round(cd, 3)))
    return out


def _fit_polar(polar: MeasuredPolar) -> list[DoorCoefficients]:
    pts = polar.usable()
    a = np.array([c.angle_deg for c in pts])
    pl = np.polyfit(a, np.array([c.cl for c in pts], dtype=float), 1)
    pd = np.polyfit(a, np.array([c.cd for c in pts], dtype=float), 2)
    lo, hi = float(a.min()), float(a.max())
    return [
        DoorCoefficients(
            angle_deg=x,
            cl=round(float(np.polyval(pl, x)), 3),
            cd=round(float(np.polyval(pd, x)), 3),
        )
        for x in FIT_ANGLES
        if lo <= x <= hi
    ]


def polar_for_type(door_type: str) -> TypePolar:
    """Polar representativa de un tipo de portón (``KeyError`` si el tipo no tiene polar).

    Tipos: ``flat``, ``v``, ``oval``, ``cambered``, ``multifoil`` y ``high_aspect``, y los alias
    del catálogo (``flat_wood``, ``suberkrub``…).
    """
    key = canonical_type(door_type)
    if key is None:
        raise KeyError(t("tipo de portón sin polar representativa: {type!r}", type=door_type))
    return _type_polar(key)


@cache
def _type_polar(key: str) -> TypePolar:
    method, ids, note = TYPE_POLARS[key]
    polars = [get_polar(i) for i in ids]
    if method == "single":
        coefs = [
            DoorCoefficients(angle_deg=c.angle_deg, cl=c.cl, cd=c.cd)
            for c in polars[0].usable(with_max=True)
        ]
    elif method == "mean":
        coefs = _mean_polar(polars)
    else:
        coefs = _fit_polar(polars[0])
    return TypePolar(
        type=key,
        coefficients=tuple(coefs),
        method=method,
        polar_ids=tuple(ids),
        documents=tuple(dict.fromkeys(p.source.document for p in polars)),
        pages=tuple(f"{p.source.page}" for p in polars),
        note=note,
        angles=ATTACK_ANGLES[key],
    )


def attack_angle_range(door_type: str | None) -> AttackAngleRange | None:
    """Rango de ángulo de ataque recomendado del tipo (``None`` si no se conoce)."""
    key = canonical_type(door_type)
    return None if key is None else ATTACK_ANGLES[key]


__all__ = [
    "ATTACK_ANGLES",
    "BACKSTROP_RATIO",
    "CALIBRATED_DOOR_TYPE",
    "POLYVALENT_CL_EFFECTIVE_FACTOR",
    "POLYVALENT_CL_PROVENANCE",
    "DOOR_TYPES",
    "DOOR_TYPE_LABEL",
    "EQUIVALENT_AREA_MARGIN",
    "TYPE_POLARS",
    "AttackAngleRange",
    "MeasuredPolar",
    "PolarLibrary",
    "TypePolar",
    "attack_angle_range",
    "canonical_type",
    "cl_effective_factor",
    "get_polar",
    "load_door_polars",
    "polar_for_type",
    "polar_published",
]
