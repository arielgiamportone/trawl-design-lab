"""Selectividad del copo por tamaño a partir de la forma simulada de cada malla.

Modelo geométrico de paso (tipo FISHSELECT, Herrmann et al. 2009): un pez de talla ``L`` escapa
por una malla si la elipse de su sección transversal más resistente, de semiejes
``A = c·h·L/2`` (alto) y ``B = c·w·L/2`` (ancho), entra en la luz de la malla girándola a su
favor. La malla deformada es un paralelogramo de lados ``e_i``, ``e_j`` (ver
:mod:`trawlkit.sim.meshstate`); entra si, para algún giro ``θ`` de la elipse, su semiancho en la
dirección normal a cada par de lados no supera la mitad de la luz entre esos lados::

    σ_k(θ) = √(A²(n_k·u)² + B²(n_k·v)²) ≤ h_k'/2,   k = i, j

con ``u = (cos θ, sen θ)``, ``v = (−sen θ, cos θ)``. Como ``A`` y ``B`` son proporcionales a
``L``, cada malla tiene una **talla máxima de paso** ``L_m`` cerrada.

Curva de retención del copo: las mallas candidatas son las del copo y la extensión en una franja
de ``zone_length_m`` justo delante de la captura (o del extremo del copo vacío), donde los peces
se acumulan y buscan salir (Herrmann 2005), ponderadas por su cantidad y sin la parte tapada por
la captura. Con la
variabilidad morfológica ``cv`` (individuos de la misma talla con secciones distintas)::

    r(L) = 1 − C · Σ_m w_m Φ((L_m/L − 1)/cv) / Σ_m w_m

``C`` es la probabilidad de contacto con una malla (1 = todos los peces la prueban). De la curva
salen ``L50``, ``L25``, ``L75``, el rango de selección ``SR = L75 − L25`` y el factor de selección
``SF = L50 / mallero``.

Supuestos (A VERIFICAR): escape sólo geométrico (sin comportamiento del pez), contacto ``C``
constante, sección elíptica escalada con la talla y coeficientes de ``data/species.yaml``.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from typing import Any

import numpy as np
import numpy.typing as npt
import yaml

from trawlkit.io.loader import DATA_DIR
from trawlkit.io.schema import MeshOrientation, NetSpec, Panel, Section
from trawlkit.netting import orientation_coefficients
from trawlkit.sim.meshstate import MeshState

FloatArray = npt.NDArray[np.float64]

#: Secciones de la red donde se evalúa el escape.
ESCAPE_SECTIONS = ("codend", "extension")
#: Largo de la franja de escape delante de la captura [m] (A VERIFICAR).
ESCAPE_ZONE_M = 3.0
#: Giros de la elipse que se prueban (la elipse es simétrica cada 180°).
_THETA = np.linspace(0.0, math.pi, 91)


@dataclass(frozen=True)
class FishShape:
    """Sección transversal de una especie (ver ``data/species.yaml``)."""

    id: str
    name: str
    scientific_name: str
    group: str
    measure: str  # TL o CL
    unit: str  # cm o mm
    length_min: float
    length_max: float
    height: float
    width: float
    compression: float
    cv: float
    notes: str

    @property
    def mm_per_unit(self) -> float:
        """Milímetros por unidad de talla."""
        return 10.0 if self.unit == "cm" else 1.0

    def lengths(self, n: int = 141) -> FloatArray:
        """Tallas por defecto de la curva: de un cuarto de la talla mínima a la máxima."""
        return np.linspace(0.25 * self.length_min, self.length_max, n)

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable."""
        return {
            "id": self.id,
            "name": self.name,
            "scientific_name": self.scientific_name,
            "group": self.group,
            "measure": self.measure,
            "unit": self.unit,
            "length_min": self.length_min,
            "length_max": self.length_max,
            "height": self.height,
            "width": self.width,
            "compression": self.compression,
            "cv": self.cv,
            "notes": self.notes,
        }


@cache
def _raw() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load((DATA_DIR / "species.yaml").read_text(encoding="utf-8"))
    return data


def species_catalogue() -> tuple[FishShape, ...]:
    """Especies del catálogo ``data/species.yaml``."""
    out = []
    for it in _raw()["items"]:
        ln = it["length"]
        out.append(
            FishShape(
                id=str(it["id"]),
                name=str(it["name"]),
                scientific_name=str(it["scientific_name"]),
                group=str(it["group"]),
                measure=str(ln["measure"]),
                unit=str(ln["unit"]),
                length_min=float(ln["min"]),
                length_max=float(ln["max"]),
                height=float(it["height"]),
                width=float(it["width"]),
                compression=float(it.get("compression", 1.0)),
                cv=float(it.get("cv", 0.05)),
                notes=str(it.get("notes", "")),
            )
        )
    return tuple(out)


def species(key: str) -> FishShape:
    """Especie del catálogo por ``id``."""
    for s in species_catalogue():
        if s.id == key:
            return s
    raise KeyError(f"especie desconocida: {key!r}")


def species_source() -> str:
    """Fuente de los coeficientes del catálogo."""
    return str(_raw().get("source", ""))


# ---------------------------------------------------------------------------------------------
# Prueba de paso
# ---------------------------------------------------------------------------------------------


def max_passing_length(
    opening_deg: FloatArray,
    clear_i_mm: FloatArray,
    clear_j_mm: FloatArray,
    shape: FishShape,
) -> FloatArray:
    """Talla máxima que pasa por cada malla, en la unidad de talla de la especie.

    ``clear_i_mm`` es la luz entre los hilos paralelos a ``e_i`` y ``clear_j_mm`` entre los
    paralelos a ``e_j``; ``opening_deg`` el ángulo entre ``e_i`` y ``e_j``. Mallas cerradas (luz
    ≤ 0) dan 0.
    """
    beta = np.radians(np.asarray(opening_deg, dtype=float))[:, None]
    hi = np.maximum(np.asarray(clear_i_mm, dtype=float), 0.0)[:, None] / 2.0
    hj = np.maximum(np.asarray(clear_j_mm, dtype=float), 0.0)[:, None] / 2.0
    th = _THETA[None, :]
    a = shape.compression * shape.height * shape.mm_per_unit / 2.0  # por unidad de talla
    b = shape.compression * shape.width * shape.mm_per_unit / 2.0
    # Marco local: e_i sobre x. Normal a los lados paralelos a e_i: (0, 1); a e_j: (sen β, −cos β).
    ni = (0.0, 1.0)
    nj_x, nj_y = np.sin(beta), -np.cos(beta)
    cu, su = np.cos(th), np.sin(th)

    def sigma(nx: Any, ny: Any) -> FloatArray:
        nu = nx * cu + ny * su
        nv = -nx * su + ny * cu
        return np.asarray(np.sqrt((a * nu) ** 2 + (b * nv) ** 2), dtype=float)

    li = hi / np.maximum(sigma(*ni), 1e-12)
    lj = hj / np.maximum(sigma(nj_x, nj_y), 1e-12)
    return np.asarray(np.minimum(li, lj).max(axis=1), dtype=float)


def _phi(z: FloatArray) -> FloatArray:
    from math import erf

    return np.asarray(0.5 * (1.0 + np.vectorize(erf)(z / math.sqrt(2.0))), dtype=float)


def _crossing(lengths: FloatArray, r: FloatArray, level: float) -> float:
    """Primera talla donde la retención (creciente) alcanza ``level`` (NaN si no la alcanza)."""
    above = np.flatnonzero(r >= level)
    if above.size == 0:
        return float("nan")
    k = int(above[0])
    if k == 0:
        return float("nan")  # retenido ya en la talla más chica: por debajo del rango
    r0, r1 = r[k - 1], r[k]
    f = (level - r0) / (r1 - r0) if r1 != r0 else 0.0
    return float(lengths[k - 1] + f * (lengths[k] - lengths[k - 1]))


@dataclass(frozen=True, eq=False)
class SelectivityCurve:
    """Curva de retención del copo para una especie."""

    species: FishShape
    lengths: FloatArray
    retention: FloatArray
    l25: float
    l50: float
    l75: float
    sr: float
    sf: float  # L50 / mallero (en la misma unidad)
    mesh_mm: float  # mallero medio de la zona de escape
    contact: float
    fit_tri: FloatArray  # talla máxima de paso por triángulo (NaN fuera de la zona)
    escape_meshes: float  # mallas candidatas (sin las tapadas por la captura)

    def to_dict(self, *, per_triangle: bool = True) -> dict[str, Any]:
        """Representación serializable."""
        out: dict[str, Any] = {
            "species": self.species.id,
            "name": self.species.name,
            "measure": self.species.measure,
            "unit": self.species.unit,
            "lengths": np.round(self.lengths, 2).tolist(),
            "retention": np.round(self.retention, 4).tolist(),
            "l25": _num(self.l25),
            "l50": _num(self.l50),
            "l75": _num(self.l75),
            "sr": _num(self.sr),
            "sf": _num(self.sf),
            "mesh_mm": self.mesh_mm,
            "contact": self.contact,
            "escape_meshes": self.escape_meshes,
            "range": _range_flag(self.retention),
        }
        if per_triangle:
            out["fit_tri"] = [None if math.isnan(v) else round(float(v), 2) for v in self.fit_tri]
        return out


def _range_flag(r: FloatArray) -> str:
    """Fuera de rango: ``below`` (retiene ya en la talla mínima), ``above`` (nunca llega) o ""."""
    if r[0] >= 0.5:
        return "below"
    if float(np.max(r)) < 0.5:
        return "above"
    return ""


def _num(v: float) -> float | None:
    return None if math.isnan(v) else round(float(v), 3)


def escape_zone(
    state: MeshState,
    sections: tuple[str, ...] = ESCAPE_SECTIONS,
    zone_length_m: float | None = ESCAPE_ZONE_M,
) -> npt.NDArray[np.bool_]:
    """Triángulos de la franja de escape: ``zone_length_m`` delante del frente de la captura.

    El frente es el centroide más adelantado de los triángulos con captura; sin captura, el
    extremo del copo. ``None`` usa toda la sección.
    """
    zone = state.zone(sections)
    if zone_length_m is None or state.x_m.size != zone.size or not zone.any():
        return zone
    filled = zone & (state.catch_fill > 0)
    front = float(np.min(state.x_m[filled])) if filled.any() else float(np.max(state.x_m[zone]))
    band = zone & (state.x_m >= front - zone_length_m)
    return band if band.any() else zone


def retention_curve(
    state: MeshState,
    shape: FishShape | str,
    lengths: Sequence[float] | FloatArray | None = None,
    *,
    contact: float = 1.0,
    sections: tuple[str, ...] = ESCAPE_SECTIONS,
    zone_length_m: float | None = ESCAPE_ZONE_M,
) -> SelectivityCurve:
    """Curva de retención de ``shape`` con la forma de malla ``state`` (ver el módulo)."""
    sp = species(shape) if isinstance(shape, str) else shape
    if not 0.0 <= contact <= 1.0:
        raise ValueError("contact debe estar entre 0 y 1")
    ls = sp.lengths() if lengths is None else np.asarray(lengths, dtype=float)
    if ls.size < 2 or np.any(ls <= 0) or np.any(np.diff(ls) <= 0):
        raise ValueError("las tallas deben ser positivas y crecientes")
    zone = escape_zone(state, sections, zone_length_m)
    w = state.meshes * zone * (1.0 - np.clip(state.catch_fill, 0.0, 1.0))
    fit = np.full(state.meshes.size, np.nan)
    if zone.any():
        fit[zone] = max_passing_length(
            state.opening_deg[zone], state.clear_i_mm[zone], state.clear_j_mm[zone], sp
        )
    total = float(w.sum())
    if total <= 0:
        retention = np.ones(ls.size)
    else:
        sel = w > 0
        ratio = fit[sel][None, :] / ls[:, None]
        p_pass = _phi((ratio - 1.0) / max(sp.cv, 1e-6))
        retention = 1.0 - contact * (p_pass * w[sel][None, :]).sum(axis=1) / total
    l25, l50, l75 = (_crossing(ls, retention, q) for q in (0.25, 0.5, 0.75))
    mesh_mm = (
        float(np.average(2.0 * state.leg_mm, weights=state.meshes * zone)) if zone.any() else 0.0
    )
    sf = l50 * sp.mm_per_unit / mesh_mm if mesh_mm > 0 and not math.isnan(l50) else float("nan")
    return SelectivityCurve(
        species=sp,
        lengths=ls,
        retention=np.asarray(retention, dtype=float),
        l25=l25,
        l50=l50,
        l75=l75,
        sr=l75 - l25,
        sf=sf,
        mesh_mm=mesh_mm,
        contact=contact,
        fit_tri=fit,
        escape_meshes=total,
    )


def selectivity(
    result: Any,
    species_ids: Sequence[str] | str,
    lengths: Sequence[float] | None = None,
    *,
    contact: float = 1.0,
) -> list[SelectivityCurve]:
    """Curvas de retención de un :class:`~trawlkit.sim.SimResult` para varias especies."""
    state = result.mesh
    if state is None:
        raise ValueError("el resultado no tiene estado de malla")
    ids = [species_ids] if isinstance(species_ids, str) else list(species_ids)
    return [retention_curve(state, s, lengths, contact=contact) for s in ids]


# ---------------------------------------------------------------------------------------------
# Variantes de copo
# ---------------------------------------------------------------------------------------------

#: Ángulo de reposo de la malla T90 en el plano del panel [°]: la diagonal larga a lo ancho.
T90_HANGING = 0.80
#: Secciones que cambia :func:`codend_variant`.
VARIANT_SECTIONS = (Section.CODEND, Section.EXTENSION)


def _scaled(panel: Panel, fx: float, fy: float, **update: Any) -> Panel:
    """Panel con las mallas a lo ancho multiplicadas por ``fx`` y a lo alto por ``fy``."""
    data = panel.model_dump()
    data["meshes_top"] = max(1, round(panel.meshes_top * fx))
    data["meshes_bottom"] = max(1, round(panel.meshes_bottom * fx))
    data["meshes_depth"] = max(1, round(panel.meshes_depth * fy))
    for key in ("meshes_a", "meshes_b"):
        if data.get(key) is not None:
            data[key] = max(1, round(float(data[key]) * fx))
    data.update(update)
    return Panel.model_validate(data)


def codend_variant(
    spec: NetSpec,
    orientation: MeshOrientation | str,
    *,
    mesh_mm: float | None = None,
    hanging_ratio: float | None = None,
) -> NetSpec:
    """Red con el copo (y la extensión) en otra orientación de malla o con otro mallero.

    Se conservan el ancho y el largo relingados de cada paño: el número de mallas se recalcula con
    los coeficientes de la orientación nueva (:func:`trawlkit.netting.orientation_coefficients`).
    En T90 el U1 por defecto es :data:`T90_HANGING` (malla abierta a lo ancho); en malla cuadrada,
    0,5 (lado = una pata).
    """
    o = MeshOrientation(str(orientation))
    panels = []
    for p in spec.panels:
        if p.section not in VARIANT_SECTIONS:
            panels.append(p)
            continue
        u_old = float(p.hanging_ratio or 0.5)
        cx0, cy0 = orientation_coefficients(p.mesh_orientation, u_old)
        m_new = float(mesh_mm or p.mesh_mm)
        if o is MeshOrientation.SQUARE:
            u_new = 0.5
        elif o is MeshOrientation.T90:
            u_new = float(hanging_ratio or T90_HANGING)
        else:
            u_new = float(hanging_ratio or (u_old if p.mesh_orientation == o else 0.23))
        cx1, cy1 = orientation_coefficients(o, u_new)
        fx = (cx0 * p.mesh_mm) / (cx1 * m_new)
        fy = (cy0 * p.mesh_mm) / (cy1 * m_new)
        panels.append(_scaled(p, fx, fy, mesh_orientation=o, mesh_mm=m_new, hanging_ratio=u_new))
    suffix = f"{o.value}" + (f"_{mesh_mm:g}" if mesh_mm else "")
    return spec.model_copy(update={"panels": panels, "id": f"{spec.id}_{suffix}"})
