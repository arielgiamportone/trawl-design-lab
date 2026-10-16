"""Fuerzas sobre el modelo discreto y relajación dinámica hasta el equilibrio.

Cargas
------
* **Paño** (elemento triangular, ver :mod:`trawlkit.sim.mesh`): tensión de cada familia de hilos
  ``T = EA · max(s/a − 1, 0)`` (sólo tracción); hidrodinámica de Morison sobre cada familia como
  un cilindro de diámetro ``d`` y largo natural ``L = A_ij · a`` (de modo que ``Σ d·L = Ss``)::

      F_n = ½ ρ C_N d L |u_n| u_n,     F_t = ½ ρ C_T d L |u_t| u_t,

  con ``u = v x̂`` la velocidad del agua relativa a la red (la red avanza hacia −x) y ``u_n``,
  ``u_t`` sus componentes normal y tangencial al hilo (Morison et al. 1950, *Petroleum Trans.
  AIME* 189:149; para redes: Lee, Lee, Lee y Kim 2005, *Ocean Eng.* 32:331–347; Priour 2013,
  *A Finite Element Method for Netting*, Springer). Rangos usuales del hilo de red:
  C_N ≈ 1,0–1,6 y C_T ≈ 0,01–0,1 (Takagi, Shimizu, Suzuki, Hiraishi y Yamamoto 2004,
  *Ocean Eng.* 31:1281–1300; Lee et al. 2005; Priour 2013). El peso sumergido del hilo es
  ``(1 − ρ_agua/ρ_PA) g / runnage`` y se reparte 1/3 por vértice.
* **Relingas**: barras sólo a tracción con su EA, Morison con su diámetro y peso sumergido
  (mitad a cada extremo); **bridas y patentes**: barras sólo a tracción sin carga hidrodinámica.
* **Boyas**: empuje y arrastre de esfera ``½ ρ C_D (π D²/4) v²`` en los nodos de la lima.
* **Nudos** (opcional, apagado por defecto): esferas de diámetro ``k·d`` (``knot_factor``), dos
  por malla, con arrastre ``½ ρ C_D (π (k d)²/4) v²`` en +x. No forman parte del modelo pedido
  (hilos de Morison); sirven para medir cuánto del arrastre de una red real se debe a los nudos.
* **Fondo** (``z = 0``): restricción unilateral. Un nodo apoyado recibe la reacción
  ``R = max(0, −F_z)`` y el rozamiento cinético ``μ R`` en +x: en el arrastre estacionario todo
  punto apoyado desliza sobre el fondo con velocidad −v x̂, así que la dirección es exacta.

Twines y barras se evalúan juntos como "segmentos": un segmento tiene tres nodos, coeficientes
``g`` con los que su vector es ``Σ g_k x_k`` (un hilo del triángulo: ``∂x/∂i``; una barra:
``x₁ − x₀``), una multiplicidad ``A`` (hilos en paralelo), largo natural, EA, ``½ρ d L`` y peso.

Solver
------
Relajación dinámica (Day 1965; Underwood 1983, *Computational Methods for Transient Analysis*
cap. 5; Barnes 1999, *Int. J. Space Struct.* 14:89) con masas ficticias iguales a una cota de
Gershgorin de la rigidez axial de cada nodo, de modo que el paso unitario es estable, integrada
con el esquema FIRE (Bitzek, Koskinen, Gähler, Moseler y Gumbsch 2006, *Phys. Rev. Lett.*
97:170201): ``M a = F``, con amortiguamiento adaptativo que mezcla la velocidad con la dirección
de la fuerza y la anula cuando la potencia ``F·v`` se vuelve negativa, y paso de tiempo
adaptativo. La red es simétrica respecto del plano ``y = 0``: las fuerzas se proyectan sobre el
subespacio simétrico (equivale a simular media red), lo que suprime el modo de balanceo lateral.
Todo está vectorizado con numpy (``np.bincount`` para ensamblar): no hay bucles de Python sobre
hilos ni barras.

Se exploró también un Newton implícito con jacobiano analítico: la transición flojo/tenso de
hilos casi inextensibles (EA/T ≈ 10³) arruina la linealización y el Newton se estanca, mientras
que la relajación explícita converge de forma robusta.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from trawlkit.sim.mesh import NetModel

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.int64]

RHO_SEAWATER = 1024.0
G = 9.80665


@dataclass(frozen=True)
class Params:
    """Parámetros físicos de una corrida."""

    speed_ms: float
    cn: float = 1.4
    ct: float = 0.08
    mu: float = 0.5
    float_cd: float = 0.5
    knot_factor: float = 0.0
    knot_cd: float = 1.0
    rho: float = RHO_SEAWATER


@dataclass(frozen=True)
class Forces:
    """Fuerzas nodales y desglose (N)."""

    total: FloatArray  # (n, 3) resultante, con reacción del fondo y rozamiento
    hydro_x: FloatArray  # (n,) componente x de las fuerzas hidrodinámicas
    reaction: FloatArray  # (n,) reacción normal del fondo
    twine_tension: FloatArray  # (nt, 2) tensión de cada familia de hilos [N por hilo]
    bar_tension: FloatArray  # (nb,) tensión de cada barra [N]
    contact: npt.NDArray[np.bool_]


class ForceField:
    """Evaluador vectorizado de las fuerzas nodales de un :class:`NetModel` a una velocidad."""

    def __init__(self, model: NetModel, p: Params) -> None:
        """Precalcula los segmentos (hilos y barras) y las cargas constantes."""
        self.model = model
        self.p = p
        n = int(model.x0.shape[0])
        self.n = n
        nt = int(model.tri.shape[0])
        nb = int(model.bar.shape[0])
        self.nt, self.nb = nt, nb
        b = model.bar
        bar_nodes = np.stack([b[:, 0], b[:, 1], b[:, 1]], axis=1)
        bar_g = np.tile(np.array([-1.0, 1.0, 0.0]), (nb, 1))
        self.nodes = np.concatenate([model.tri, model.tri, bar_nodes])  # (ns, 3)
        self.g = np.concatenate([model.tri_gi, model.tri_gj, bar_g])
        self.mult = np.concatenate([model.tri_area, model.tri_area, np.ones(nb)])
        self.l0 = np.concatenate([model.tri_a, model.tri_a, model.bar_l0])
        self.ea = np.concatenate([model.tri_ea, model.tri_ea, model.bar_ea])
        length = np.concatenate([model.tri_area * model.tri_a] * 2 + [model.bar_l0])
        diam = np.concatenate([model.tri_d, model.tri_d, model.bar_d])
        self.k = 0.5 * p.rho * diam * length  # ½ ρ d L
        self.w = np.concatenate(
            [model.tri_w * model.tri_area * model.tri_a] * 2 + [model.bar_w * model.bar_l0]
        )
        self.h = np.concatenate(
            [np.full((2 * nt, 3), 1.0 / 3.0), np.tile(np.array([0.5, 0.5, 0.0]), (nb, 1))]
        )
        self.idx = ((3 * self.nodes)[:, :, None] + np.arange(3)).ravel()
        drag_float = np.zeros(n)
        buoy = np.zeros(n)
        if model.float_nodes.size:
            q = 0.5 * p.rho * p.float_cd * model.float_area_m2 * p.speed_ms**2
            np.add.at(drag_float, model.float_nodes, model.float_weights * q)
            np.add.at(buoy, model.float_nodes, model.float_weights * model.float_buoyancy_n)
        if p.knot_factor > 0.0:
            # Nudos: esferas de diámetro knot_factor·d, uno por unidad de área en coordenadas
            # de hilo (2 nudos por malla), con arrastre ½ρ C_D A v² en +x (1/3 por vértice).
            area_k = np.pi / 4.0 * (p.knot_factor * model.tri_d) ** 2
            fk = 0.5 * p.rho * p.knot_cd * area_k * model.tri_area * p.speed_ms**2 / 3.0
            np.add.at(drag_float, model.tri.ravel(), np.repeat(fk, 3))
        const = model.point_load.copy()
        const[:, 0] += drag_float
        const[:, 2] += buoy
        self.const = const.ravel()
        self.point_drag = drag_float
        self.free = np.ones(n, dtype=bool)
        self.free[model.fixed] = False

    def tensions(self, x: FloatArray) -> FloatArray:
        """Tensión de cada segmento [N] en la configuración ``x``."""
        vec = np.einsum("sk,skc->sc", self.g, x[self.nodes])
        s = np.sqrt(np.einsum("ij,ij->i", vec, vec))
        return np.asarray(self.ea * np.maximum(s / self.l0 - 1.0, 0.0), dtype=float)

    def evaluate(self, x: FloatArray, full: bool = False) -> tuple[FloatArray, Forces | None]:
        """Fuerza nodal resultante (n, 3); con ``full`` también el desglose :class:`Forces`."""
        p = self.p
        vel = p.speed_ms
        xs = x[self.nodes]
        vec = np.einsum("sk,skc->sc", self.g, xs)
        s = np.maximum(np.sqrt(np.einsum("ij,ij->i", vec, vec)), 1e-12)
        e = vec / s[:, None]
        t = self.ea * np.maximum(s / self.l0 - 1.0, 0.0)
        # Morison con agua v x̂: componente tangencial ue (con signo) y normal un.
        ue = vel * e[:, 0]
        un = -ue[:, None] * e
        un[:, 0] += vel
        un_mag = np.sqrt(np.maximum(vel * vel - ue * ue, 0.0))
        fh = self.k[:, None] * (p.cn * un_mag[:, None] * un + (p.ct * np.abs(ue) * ue)[:, None] * e)
        hx = fh[:, 0].copy() if full else None
        fh[:, 2] -= self.w
        fv = self.h[:, :, None] * fh[:, None, :] - (self.mult * t)[:, None, None] * (
            self.g[:, :, None] * e[:, None, :]
        )
        total = np.bincount(self.idx, weights=fv.ravel(), minlength=3 * self.n) + self.const
        total = total.reshape(-1, 3)
        contact = x[:, 2] <= 1e-9
        reaction = np.where(contact, np.maximum(-total[:, 2], 0.0), 0.0)
        total[:, 2] += reaction
        total[:, 0] += p.mu * reaction
        total[~self.free] = 0.0
        if not full:
            return total, None
        assert hx is not None
        hydro_x = (
            np.bincount(
                self.nodes.ravel(), weights=(self.h * hx[:, None]).ravel(), minlength=self.n
            )
            + self.point_drag
        )
        nt = self.nt
        tens = np.stack([t[:nt], t[nt : 2 * nt]], axis=1)
        return total, Forces(total, hydro_x, reaction, tens, t[2 * nt :], contact)

    def drag(self, forces: Forces, nodes: npt.NDArray[np.bool_] | None = None) -> float:
        """Arrastre [N]: fuerzas hidrodinámicas en x más rozamiento con el fondo."""
        sel = slice(None) if nodes is None else nodes
        return float(forces.hydro_x[sel].sum() + self.p.mu * forces.reaction[sel].sum())


def compute_forces(model: NetModel, x: FloatArray, p: Params) -> Forces:
    """Fuerzas nodales en la configuración ``x`` (n, 3), con desglose."""
    forces = ForceField(model, p).evaluate(x, full=True)[1]
    assert forces is not None
    return forces


@dataclass(frozen=True)
class RelaxResult:
    """Resultado de la relajación."""

    x: FloatArray
    forces: Forces
    converged: bool
    iterations: int
    residual: float  # ‖R‖₂ / |arrastre total|
    force_balance: float  # |Σ R_x| / |arrastre total|
    drag_mean: float  # arrastre medio en la última ventana [N]
    drag_std: float  # desvío del arrastre en la última ventana [N]


def nodal_stiffness(model: NetModel) -> FloatArray:
    """Cota de Gershgorin de la rigidez axial nodal [N/m] (todos los hilos y barras tensos).

    Para el vértice ``k`` de un triángulo suma ``A·EA/a·|g_k|·Σ_l|g_l|`` por familia de hilos, y
    ``2·EA/L`` por barra en cada extremo; con masas ficticias iguales a esta cota el paso
    explícito ``Δt = 1`` es estable (Underwood 1983).
    """
    n = model.x0.shape[0]
    base = (model.tri_area * model.tri_ea / model.tri_a)[:, None]
    k_tri = base * (
        np.abs(model.tri_gi) * np.abs(model.tri_gi).sum(axis=1, keepdims=True)
        + np.abs(model.tri_gj) * np.abs(model.tri_gj).sum(axis=1, keepdims=True)
    )
    k = np.bincount(model.tri.ravel(), weights=k_tri.ravel(), minlength=n)
    kb = 2.0 * model.bar_ea / model.bar_l0
    k += np.bincount(model.bar[:, 0], weights=kb, minlength=n)
    k += np.bincount(model.bar[:, 1], weights=kb, minlength=n)
    return np.maximum(k, 1e-6 * float(k.max()))


def quantities(model: NetModel, x: FloatArray, ff: ForceField, forces: Forces) -> FloatArray:
    """(AH, AV, arrastre de la red) de la configuración: lo que vigila el criterio de parada."""
    tu = model.wing_tips_upper
    ah = float(np.linalg.norm(x[tu[0]] - x[tu[1]]))
    av = float(x[model.headrope_centre, 2] - x[model.footrope_centre, 2])
    return np.array([ah, av, ff.drag(forces, net_mask(model))])


def net_mask(model: NetModel) -> npt.NDArray[np.bool_]:
    """Nodos de la red (sin los nodos de unión de bridas ni los portones)."""
    mask = np.ones(model.x0.shape[0], dtype=bool)
    mask[[*model.junctions, *model.doors]] = False
    return mask


def relax(
    model: NetModel,
    p: Params,
    x_init: FloatArray | None = None,
    *,
    tol: float = 1e-2,
    qoi_tol: float = 3e-3,
    window: int = 1000,
    max_iter: int = 40_000,
    symmetric: bool = True,
    mass_factor: float = 0.5,
    check_every: int = 100,
    history: list[tuple[float, ...]] | None = None,
) -> RelaxResult:
    """Busca el equilibrio estático con FIRE y masas ficticias (ver docstring del módulo).

    Cada ``check_every`` iteraciones se miden el residuo ``‖R‖₂/|D|``, el desbalance global
    ``|Σ R_x|/|D|`` (``R`` fuerzas residuales de los nodos libres, ``D`` arrastre de la red: agua
    en x más rozamiento con el fondo) y las magnitudes AH, AV y ``D``. Se detiene cuando, en la
    última ventana de ``window`` iteraciones, el residuo y el desbalance medios son menores que
    ``tol`` y la media de AH, AV y ``D`` cambió menos que ``qoi_tol`` (relativo) respecto de la
    ventana anterior.

    El residuo no baja mucho de ~10⁻³: la bolsa inferior J (250 mallas) va cosida a la superior
    I (200 mallas) y su exceso de largo forma un bolsón flojo, de rigidez casi nula, que sigue
    derivando lentamente (y hace oscilar el arrastre ±1 %) sin afectar a la boca.
    """
    ff = ForceField(model, p)
    free = ff.free
    x = (model.x0 if x_init is None else x_init).copy()
    x[:, 2] = np.maximum(x[:, 2], 0.0)
    mirror = model.mirror
    flip = np.array([1.0, -1.0, 1.0])
    if symmetric:
        x = 0.5 * (x + x[mirror] * flip)
    inv_m = np.where(free, 1.0 / (mass_factor * nodal_stiffness(model)), 0.0)[:, None]
    v = np.zeros_like(x)
    dt, dt_max = 0.1, 1.0
    alpha0 = alpha = 0.1
    n_pos = 0
    it = 0
    samples: list[FloatArray] = []  # (res, bal, AH, AV, D) en cada control
    span = max(2, window // check_every)
    converged = False
    for it in range(1, max_iter + 1):
        check = it % check_every == 0
        f, full = ff.evaluate(x, full=check)
        if symmetric:
            f = 0.5 * (f + f[mirror] * flip)
        if full is not None:
            drag = max(abs(ff.drag(full)), 1e-9)
            res = float(np.linalg.norm(f[free])) / drag
            bal = abs(float(f[free, 0].sum())) / drag
            q = quantities(model, x, ff, full)
            samples.append(np.array([res, bal, *q.tolist()]))
            if history is not None:
                history.append((it, res, bal, *q.tolist()))
            if len(samples) >= 2 * span:
                last = np.mean(samples[-span:], axis=0)
                prev = np.mean(samples[-2 * span : -span], axis=0)
                change = float(
                    np.max(np.abs(last[2:] - prev[2:]) / np.maximum(np.abs(last[2:]), 1e-6))
                )
                if last[0] < tol and last[1] < tol and change < qoi_tol:
                    converged = True
                    break
        acc = f * inv_m
        power = float(np.einsum("ij,ij->", f, v))
        if power > 0.0:
            vn = float(np.sqrt(np.einsum("ij,ij->", v, v)))
            an = float(np.sqrt(np.einsum("ij,ij->", acc, acc)))
            if an > 0.0:
                v = (1.0 - alpha) * v + (alpha * vn / an) * acc
            n_pos += 1
            if n_pos > 5:
                dt = min(dt * 1.1, dt_max)
                alpha *= 0.99
        else:
            v[:] = 0.0
            dt *= 0.5
            alpha = alpha0
            n_pos = 0
        v += dt * acc
        x += dt * v
        # Fondo: proyección z ≥ 0 sin velocidad entrante.
        below = x[:, 2] < 0.0
        x[below, 2] = 0.0
        v[below, 2] = np.maximum(v[below, 2], 0.0)
    f, final = ff.evaluate(x, full=True)
    assert final is not None
    if symmetric:
        f = 0.5 * (f + f[mirror] * flip)
    drag = max(abs(ff.drag(final)), 1e-9)
    res = float(np.linalg.norm(f[free])) / drag
    bal = abs(float(f[free, 0].sum())) / drag
    tail = np.array(samples[-span:]) if samples else np.zeros((1, 5))
    return RelaxResult(
        x, final, converged, it, res, bal, float(tail[:, 4].mean()), float(tail[:, 4].std())
    )
