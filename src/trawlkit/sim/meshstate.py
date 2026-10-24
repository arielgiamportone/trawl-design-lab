"""Estado de cada malla de la red simulada (zoom por malla).

Dentro de un elemento triangular de Priour (ver :mod:`trawlkit.sim.mesh`) los vectores de pata
``e_i = ∂x/∂i`` y ``e_j = ∂x/∂j`` son constantes, así que todas las mallas del triángulo tienen la
misma forma: un paralelogramo de lados ``e_i`` y ``e_j``. De ahí salen:

* el **ángulo de apertura** ``β = acos(e_i·e_j / |e_i||e_j|)`` entre las dos familias de hilos
  (rombo: β → 0 con la malla cerrada a lo largo de la red; 90° con la malla abierta en cuadrado);
* las **alturas** del paralelogramo, ``h_i = |e_j| sen β`` (entre los lados paralelos a ``e_i``)
  y ``h_j = |e_i| sen β``, y la **luz de malla** descontando el diámetro del hilo,
  ``h' = h − d``: es el hueco por donde un pez puede pasar;
* el **área libre** ``h_i' h_j' / sen β`` y la **fracción abierta** ``|e_i × e_j| / a²`` (1 = malla
  abierta en cuadrado, 0 = cerrada).

La reconstrucción de las mallas de un triángulo es exacta (el campo es lineal en el elemento):
:func:`mesh_patch` dibuja un parche de ``n × n`` mallas en el plano local del triángulo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import numpy.typing as npt

from trawlkit.sim.mesh import NetModel

FloatArray = npt.NDArray[np.float64]


@dataclass(frozen=True, eq=False)
class MeshState:
    """Forma de la malla de cada triángulo (arrays de largo ``nt``; largos en mm)."""

    orientation: tuple[str, ...]
    section: tuple[str, ...]
    meshes: FloatArray  # mallas del triángulo
    leg_mm: FloatArray  # pata nominal (mallero / 2)
    twine_mm: FloatArray
    leg_i_mm: FloatArray  # pata deformada de cada familia
    leg_j_mm: FloatArray
    opening_deg: FloatArray  # ángulo β entre las dos familias de hilos
    clear_i_mm: FloatArray  # luz entre los hilos paralelos a e_i (h_i − d)
    clear_j_mm: FloatArray  # luz entre los hilos paralelos a e_j (h_j − d)
    catch_fill: FloatArray  # fracción del triángulo tapada por la captura (0–1)
    x_m: FloatArray = field(default_factory=lambda: np.zeros(0))  # centroide a lo largo [m]

    @property
    def open_fraction(self) -> FloatArray:
        """Área de la malla respecto de la malla abierta en cuadrado (0 = cerrada)."""
        beta = np.radians(self.opening_deg)
        return np.asarray(
            self.leg_i_mm * self.leg_j_mm * np.sin(beta) / np.maximum(self.leg_mm, 1e-9) ** 2,
            dtype=float,
        )

    @property
    def clear_area_mm2(self) -> FloatArray:
        """Área libre de cada malla [mm²] (paralelogramo interior, descontado el hilo)."""
        sb = np.maximum(np.sin(np.radians(self.opening_deg)), 1e-6)
        ci = np.maximum(self.clear_i_mm, 0.0)
        cj = np.maximum(self.clear_j_mm, 0.0)
        return np.asarray(ci * cj / sb, dtype=float)

    def zone(self, sections: tuple[str, ...] = ("codend", "extension")) -> npt.NDArray[np.bool_]:
        """Triángulos de las secciones dadas."""
        return np.array([s in sections for s in self.section], dtype=bool)

    def summary(self, sections: tuple[str, ...] = ("codend", "extension")) -> dict[str, float]:
        """Ángulo y área libre medios (ponderados por mallas) de una zona de la red."""
        sel = self.zone(sections)
        w = self.meshes * sel
        if w.sum() <= 0:
            return {}
        return {
            "opening_deg": float(np.average(self.opening_deg, weights=w)),
            "open_fraction": float(np.average(self.open_fraction, weights=w)),
            "clear_area_mm2": float(np.average(self.clear_area_mm2, weights=w)),
            "meshes": float(w.sum()),
        }

    def to_dict(self) -> dict[str, Any]:
        """Representación serializable (redondeada)."""
        return {
            "orientation": list(self.orientation),
            "section": list(self.section),
            "meshes": np.round(self.meshes, 1).tolist(),
            "leg_mm": np.round(self.leg_mm, 2).tolist(),
            "twine_mm": np.round(self.twine_mm, 3).tolist(),
            "leg_i_mm": np.round(self.leg_i_mm, 2).tolist(),
            "leg_j_mm": np.round(self.leg_j_mm, 2).tolist(),
            "opening_deg": np.round(self.opening_deg, 1).tolist(),
            "clear_i_mm": np.round(self.clear_i_mm, 2).tolist(),
            "clear_j_mm": np.round(self.clear_j_mm, 2).tolist(),
            "catch_fill": np.round(self.catch_fill, 3).tolist(),
        }


def leg_vectors(model: NetModel, nodes: FloatArray) -> tuple[FloatArray, FloatArray]:
    """Vectores de pata ``(e_i, e_j)`` de cada triángulo [m], (nt, 3) cada uno."""
    xs = nodes[model.tri]  # (nt, 3, 3)
    ei = np.einsum("tk,tkc->tc", model.tri_gi, xs)
    ej = np.einsum("tk,tkc->tc", model.tri_gj, xs)
    return ei, ej


def mesh_state(
    model: NetModel, nodes: FloatArray, catch_fill: FloatArray | None = None
) -> MeshState:
    """Estado de la malla de cada triángulo con las posiciones ``nodes``."""
    ei, ej = leg_vectors(model, nodes)
    si = np.linalg.norm(ei, axis=1)
    sj = np.linalg.norm(ej, axis=1)
    c = np.clip(np.einsum("ij,ij->i", ei, ej) / np.maximum(si * sj, 1e-15), -1.0, 1.0)
    beta = np.arccos(c)
    sb = np.sin(beta)
    d = model.tri_d
    nt = int(model.tri.shape[0])
    orient = model.tri_orientation or ("diamond",) * nt
    fill = np.zeros(nt) if catch_fill is None or catch_fill.size != nt else catch_fill
    return MeshState(
        orientation=tuple(orient),
        section=tuple(model.tri_section or ("",) * nt),
        meshes=model.tri_area.copy(),
        leg_mm=model.tri_a * 1000.0,
        twine_mm=d * 1000.0,
        leg_i_mm=si * 1000.0,
        leg_j_mm=sj * 1000.0,
        opening_deg=np.degrees(beta),
        clear_i_mm=(sj * sb - d) * 1000.0,
        clear_j_mm=(si * sb - d) * 1000.0,
        catch_fill=np.asarray(fill, dtype=float).copy(),
        x_m=nodes[model.tri, 0].mean(axis=1),
    )


def mesh_patch(state: MeshState, tri: int, n: int = 5) -> dict[str, Any]:
    """Parche de ``n × n`` mallas del triángulo ``tri`` en su plano local [mm].

    ``e_i`` va sobre el eje x local y ``e_j`` forma el ángulo β con él. Devuelve los nudos
    (``(n+1)²`` puntos), los hilos de cada familia como pares de índices de nudo y los datos de la
    malla (ángulo, patas, luz y área libre).
    """
    if not 0 <= tri < state.meshes.size:
        raise IndexError(f"triángulo fuera de rango: {tri}")
    if not 1 <= n <= 20:
        raise ValueError("n debe estar entre 1 y 20")
    li = float(state.leg_i_mm[tri])
    lj = float(state.leg_j_mm[tri])
    beta = float(np.radians(state.opening_deg[tri]))
    e1 = np.array([li, 0.0])
    e2 = np.array([lj * np.cos(beta), lj * np.sin(beta)])
    knots = [(a * e1 + b * e2).tolist() for a in range(n + 1) for b in range(n + 1)]

    def k(a: int, b: int) -> int:
        return a * (n + 1) + b

    twines_i = [[k(a, b), k(a + 1, b)] for a in range(n) for b in range(n + 1)]
    twines_j = [[k(a, b), k(a, b + 1)] for a in range(n + 1) for b in range(n)]
    return {
        "triangle": tri,
        "n": n,
        "knots": knots,
        "twines_i": twines_i,
        "twines_j": twines_j,
        "orientation": state.orientation[tri],
        "section": state.section[tri],
        "opening_deg": float(state.opening_deg[tri]),
        "leg_i_mm": li,
        "leg_j_mm": lj,
        "twine_mm": float(state.twine_mm[tri]),
        "clear_i_mm": float(state.clear_i_mm[tri]),
        "clear_j_mm": float(state.clear_j_mm[tri]),
        "clear_area_mm2": float(state.clear_area_mm2[tri]),
        "open_fraction": float(state.open_fraction[tri]),
    }
