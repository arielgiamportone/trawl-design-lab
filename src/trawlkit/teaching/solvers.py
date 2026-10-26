"""Solvers del banco de ejercicios: cada uno calcula las respuestas con funciones del motor.

Un solver recibe los datos del enunciado (``vars``, ya elegidos para la semilla) y devuelve un
diccionario con las respuestas y los valores intermedios que cita la explicación. Algunos tienen
además una función ``derive`` que completa datos que dependen de otros (por ejemplo, el alto de un
paño a partir de la razón de corte elegida), para que los números del enunciado sean «redondos».

No hay fórmulas copiadas: todo sale de :mod:`trawlkit.power`, :mod:`trawlkit.drag`,
:mod:`trawlkit.netting`, :mod:`trawlkit.net`, :mod:`trawlkit.dimensions`,
:mod:`trawlkit.rigging`, :mod:`trawlkit.construction` y :mod:`trawlkit.economics`.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from fractions import Fraction
from functools import cache
from typing import Any

from trawlkit import dimensions, drag, net, netting, power
from trawlkit.construction import cut_cycle
from trawlkit.economics import KNOT_MS
from trawlkit.economics import G as G_ECON
from trawlkit.i18n import N_
from trawlkit.io import PropellerType
from trawlkit.performance import speed_window
from trawlkit.rigging import ballast, doors, floats, spread, warps
from trawlkit.sim.core import DIESEL_KG_L, SFC_KG_KWH, TOWING_EFFICIENCY
from trawlkit.units import KNOT_TO_MS

Values = dict[str, Any]
SolverFn = Callable[[Values], Values]
DeriveFn = Callable[[Values], Values]


@dataclass(frozen=True)
class _Entry:
    fn: SolverFn
    derive: DeriveFn | None = None
    derived: dict[str, tuple[str, str]] = field(default_factory=dict)


_REGISTRY: dict[str, _Entry] = {}


def solver(
    name: str,
    derive: DeriveFn | None = None,
    derived: dict[str, tuple[str, str]] | None = None,
) -> Callable[[SolverFn], SolverFn]:
    """Registra un solver. ``derived`` da etiqueta y unidad a los datos que agrega ``derive``."""

    def wrap(fn: SolverFn) -> SolverFn:
        if name in _REGISTRY:
            raise ValueError(f"solver repetido: {name}")
        _REGISTRY[name] = _Entry(fn, derive, dict(derived or {}))
        return fn

    return wrap


def names() -> list[str]:
    """Solvers registrados."""
    return sorted(_REGISTRY)


def _entry(name: str) -> _Entry:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(f"solver desconocido: {name}") from None


def derive(name: str, values: Values) -> Values:
    """Datos del enunciado completados por el ``derive`` del solver (si tiene)."""
    entry = _entry(name)
    return dict(values) if entry.derive is None else {**values, **entry.derive(dict(values))}


def derived_labels(name: str) -> dict[str, tuple[str, str]]:
    """Etiqueta (en español, marcada con ``N_``) y unidad de los datos que agrega ``derive``."""
    return dict(_entry(name).derived)


def run_solver(name: str, values: Values) -> Values:
    """Respuestas e intermedios del solver ``name``."""
    return {k: _plain(v) for k, v in _entry(name).fn(dict(values)).items()}


def _plain(v: Any) -> Any:
    if isinstance(v, str):
        return v
    return float(v)


def _f(v: Values, key: str) -> float:
    return float(v[key])


PROPELLERS = {
    "PF": PropellerType.FIXED_PITCH,
    "PF+T": PropellerType.FIXED_PITCH_NOZZLE,
    "PV": PropellerType.VARIABLE_PITCH,
    "PV+T": PropellerType.VARIABLE_PITCH_NOZZLE,
}


# =============================================================================================
# 10 · Potencia
# =============================================================================================


@solver("fridman_tiro")
def _fridman_tiro(v: Values) -> Values:
    kf = power.fridman_kf(PROPELLERS[str(v["helice"])])
    ft = power.fridman_towing_force_kgf(_f(v, "bhp"), _f(v, "v"), kf)
    return {"kf": kf, "ft_kgf": ft}


@solver("prado_bollard")
def _prado_bollard(v: Values) -> Values:
    prop = PROPELLERS[str(v["helice"])]
    pct = power.prado_propeller_percent(prop)
    bp = power.bollard_pull_kgf(_f(v, "bhp"), prop)
    return {"pct": pct, "bp_kgf": bp, "bp_t": bp / 1000.0}


@solver("prado_arrastre")
def _prado_arrastre(v: Values) -> Values:
    bhp = _f(v, "bhp")
    prop = PROPELLERS[str(v["helice"])]
    bp = power.bollard_pull_kgf(bhp, prop)
    k_bp = power.prado_k_factor(prop, bhp)
    bp_k_t = power.bollard_pull_k_t(bhp, k_bp)
    bp_avg = power.bollard_pull_avg_kgf(bp, bp_k_t)
    apn = power.apparent_nominal_power_hp(bp_avg)
    p = power.trawling_power_hp(apn, _f(v, "k"))
    bpf = power.bollard_pull_fishing_kgf(p, _f(v, "v"))
    return {
        "bp_kgf": bp,
        "k_bp": k_bp,
        "bp_k_kgf": bp_k_t * 1000.0,
        "bp_avg_kgf": bp_avg,
        "apn_hp": apn,
        "p_hp": p,
        "bpf_kgf": bpf,
    }


@solver("koyama_tiro")
def _koyama_tiro(v: Values) -> Values:
    bhp = _f(v, "bhp")
    k = power.koyama_k(bhp)
    bhp_f = power.koyama_bhp_f_hp(bhp)
    ehp = power.koyama_ehp_hp(bhp_f, k)
    v_ms = _f(v, "v") * KNOT_TO_MS
    pull = power.koyama_pull_kgf(bhp, k, v_ms)
    return {"k": k, "bhp_f": bhp_f, "ehp_hp": ehp, "v_ms": v_ms, "pull_kgf": pull}


# =============================================================================================
# 11 · Paños y cortes
# =============================================================================================


@solver("hilo_y_borde")
def _hilo_y_borde(v: Values) -> Values:
    runnage = netting.runnage_m_per_kg(_f(v, "rtex"))
    edge = netting.stretched_length_m(_f(v, "mallas"), _f(v, "malla"))
    return {"runnage": runnage, "borde_m": edge}


def _derive_corte(v: Values) -> Values:
    t1 = int(_f(v, "t1"))
    h = int(_f(v, "h"))
    code = str(v["codigo"])
    ratio = netting.cut_code_ratio(code)
    n = round(h / ratio)
    return {"t2": t1 - 2 * h, "n": n}


@solver(
    "corte_simetrico",
    derive=_derive_corte,
    derived={
        "t2": (N_("Mallas del borde menor (T2)"), "mallas"),
        "n": (N_("Mallas de alto (N)"), "mallas"),
    },
)
def _corte_simetrico(v: Values) -> Values:
    t1, t2, n = _f(v, "t1"), _f(v, "t2"), _f(v, "n")
    side = netting.symmetric_cut_meshes(t1, t2)
    ratio = netting.taper_ratio(side, n)
    code = netting.cut_code(float(ratio))
    return {"lado": side, "razon": ratio, "codigo_corte": code or "—"}


@solver("angulo_corte")
def _angulo_corte(v: Values) -> Values:
    code = str(v["codigo"])
    u1 = _f(v, "u1")
    width, height = netting.cut_steps(code)
    u2 = netting.vertical_opening_coefficient(u1)
    theta = netting.cut_angle_deg(code, u1)
    return {"a": width, "d": height, "u2": u2, "theta": theta}


@solver("mallas_y_area")
def _mallas_y_area(v: Values) -> Values:
    t1, t2, n, m, u1 = (_f(v, k) for k in ("t1", "t2", "n", "malla", "u1"))
    return {
        "mallas_total": netting.mesh_count(t1, t2, n),
        "u2": netting.vertical_opening_coefficient(u1),
        "area_m2": netting.panel_working_area_m2(u1, t1, t2, n, m),
    }


# =============================================================================================
# 12 · Mecánica de la red
# =============================================================================================


@solver("indice_filtracion")
def _indice_filtracion(v: Values) -> Values:
    d = [_f(v, f"d{i}") for i in (1, 2, 3)]
    m = [_f(v, f"m{i}") for i in (1, 2, 3)]
    fi = net.filtration_index(d, m)
    return {"suma_d": fi.sum_twine_mm, "suma_l": fi.sum_mesh_mm, "dl": fi.value}


@solver("superficie_solida")
def _superficie_solida(v: Values) -> Values:
    d, m, t1, t2, n, c = (_f(v, k) for k in ("d", "malla", "t1", "t2", "n", "paneles"))
    length = net.panel_length_m(n, m)
    return {"largo_m": length, "ss_m2": net.solid_surface_m2(d, m, t1, t2, n, c)}


@solver("solidez")
def _solidez(v: Values) -> Values:
    d, m, t1, t2, n, u1 = (_f(v, k) for k in ("d", "malla", "t1", "t2", "n", "u1"))
    ss = net.solid_surface_m2(d, m, t1, t2, n)
    st = net.working_surface_m2(u1, m, t1, t2, n)
    sol = net.solidity(ss, st)
    return {"ss_m2": ss, "st_m2": st, "solidez": sol, "filtrado": net.filtering_coefficient(sol)}


# =============================================================================================
# 13 · Dimensiones
# =============================================================================================


@solver("lima_por_piezas")
def _lima_por_piezas(v: Values) -> Values:
    wing = dimensions.headrope_wing_piece_m(_f(v, "n_punta"), _f(v, "n_ala"), _f(v, "malla_ala"))
    bosom = dimensions.headrope_bosom_piece_m(
        _f(v, "t_square"), _f(v, "malla_square"), _f(v, "t_ala"), _f(v, "malla_ala")
    )
    wing_c = dimensions.corrected_piece_m(wing, _f(v, "e_ala"))
    bosom_c = dimensions.corrected_piece_m(bosom, _f(v, "e_bocana"))
    return {
        "ala_m": wing,
        "bocana_m": bosom,
        "ala_corr_m": wing_c,
        "bocana_corr_m": bosom_c,
        "lima_m": dimensions.headrope_length_m(wing_c, bosom_c),
    }


@solver("circunferencia")
def _circunferencia(v: Values) -> Values:
    fc = dimensions.fishing_circle_m(_f(v, "t_dorso"), _f(v, "t_vientre"), _f(v, "malla"))
    return {
        "fc_m": fc,
        "av_suzuki_m": spread.vertical_opening_suzuki_m(float(fc)),
        "av_pct_m": spread.vertical_opening_pct_m(float(fc), _f(v, "pct") / 100.0),
    }


# =============================================================================================
# 14 · Resistencia
# =============================================================================================


@solver("rn_aberdeen")
def _rn_aberdeen(v: Values) -> Values:
    t = float(drag.aberdeen_demersal(_f(v, "ss"), _f(v, "v"))[()])
    return {"rn_t": t, "rn_kgf": t * 1000.0}


@solver("rn_tauti")
def _rn_tauti(v: Values) -> Values:
    v_ms = _f(v, "v") * KNOT_TO_MS
    t = float(drag.tauti_nomura_shu(_f(v, "dl"), _f(v, "a"), v_ms)[()])
    return {"v_ms": v_ms, "rn_t": t, "rn_kgf": t * 1000.0}


@solver("rn_comparar")
def _rn_comparar(v: Values) -> Values:
    dl, a, ln, ss, vk = (_f(v, k) for k in ("dl", "a", "l", "ss", "v"))
    k84 = float(drag.koyama_1984(dl, a, ln, vk)[()]) * 1000.0
    ab = float(drag.aberdeen_demersal(ss, vk)[()]) * 1000.0
    return {"koyama_kgf": k84, "aberdeen_kgf": ab, "dif_pct": (k84 / ab - 1.0) * 100.0}


@solver("rn_reid")
def _rn_reid(v: Values) -> Values:
    t = float(drag.reid(_f(v, "ss"), _f(v, "v"))[()])
    return {"rn_t": t, "rn_kgf": t * 1000.0}


@solver("rn_velocidad")
def _rn_velocidad(v: Values) -> Values:
    ss, v1, v2 = _f(v, "ss"), _f(v, "v1"), _f(v, "v2")
    r1 = float(drag.aberdeen_demersal(ss, v1)[()]) * 1000.0
    r2 = float(drag.aberdeen_demersal(ss, v2)[()]) * 1000.0
    return {"r1_kgf": r1, "r2_kgf": r2, "aumento_pct": (r2 / r1 - 1.0) * 100.0}


# =============================================================================================
# 15 · Portones y aparejo
# =============================================================================================


@solver("fuerzas_porton")
def _fuerzas_porton(v: Values) -> Values:
    v_ms = _f(v, "v") * KNOT_TO_MS
    f = doors.door_forces_kgf(_f(v, "area"), _f(v, "cd"), _f(v, "cl"), v_ms)
    return {"v_ms": v_ms, "rd_kgf": float(f.drag_kgf), "ry_kgf": float(f.lift_kgf)}


@solver("separacion_portones")
def _separacion_portones(v: Values) -> Values:
    ds = doors.door_spread_m(_f(v, "pastecas"), _f(v, "por_metro"), _f(v, "cable"))
    half = warps.warp_divergence_deg(ds, _f(v, "pastecas"), _f(v, "cable"))
    return {"ds_m": ds, "medio_phi": half}


@solver("superficie_porton")
def _superficie_porton(v: Values) -> Values:
    kf = power.fridman_kf(PropellerType.FIXED_PITCH)
    ft = float(power.fridman_towing_force_kgf(_f(v, "bhp"), _f(v, "v"), kf))
    rob = float(doors.door_drag_share_kgf(ft, _f(v, "fraccion") / 100.0))
    v_ms = _f(v, "v") * KNOT_TO_MS
    s = float(doors.required_area_m2(rob, _f(v, "cd"), v_ms))
    return {"ft_kgf": ft, "rob_kgf": rob, "s_total_m2": s, "s_porton_m2": s / 2.0}


# =============================================================================================
# 16 · Aberturas
# =============================================================================================


@solver("dpa_triangulos")
def _dpa_triangulos(v: Values) -> Values:
    dpa = warps.dpa_similar_triangles_m(_f(v, "ds"), _f(v, "l_red"), _f(v, "aparejo"))
    return {"dpa_m": dpa, "relacion": dpa / _f(v, "lima")}


@solver("abertura_vertical")
def _abertura_vertical(v: Values) -> Values:
    a = spread.stretched_circumference_m(_f(v, "mallas"), _f(v, "malla"))
    return {
        "a_m": a,
        "suzuki_m": spread.vertical_opening_suzuki_m(a),
        "prado_m": spread.vertical_opening_pct_m(a, _f(v, "pct") / 100.0),
    }


# =============================================================================================
# 17 · Flotación y lastre
# =============================================================================================


@solver("flotacion_empirica")
def _flotacion_empirica(v: Values) -> Values:
    k = floats.flotation_koyama_kgf(_f(v, "lima"))
    p = floats.flotation_prado_kgf(_f(v, "nhp"))
    return {"koyama_kgf": k, "prado_kgf": p, "promedio_kgf": (k + p) / 2.0}


@solver("numero_boyas")
def _numero_boyas(v: Values) -> Values:
    n = float(floats.float_count(_f(v, "flot"), _f(v, "unitaria")))
    return {"boyas": n, "total_kgf": n * _f(v, "unitaria")}


@solver("flotacion_fridman")
def _flotacion_fridman(v: Values) -> Values:
    beta = floats.beta_deg(_f(v, "av"), _f(v, "l_cuerpo"))
    fr = floats.flotation_fridman(
        _f(v, "ft"), _f(v, "rn"), _f(v, "alfa"), beta, _f(v, "w_lima"), rounddown=False
    )
    return {
        "beta": beta,
        "f1_kgf": float(fr.f1_kgf),
        "f2_kgf": float(fr.f2_kgf),
        "f1v_kgf": float(fr.f1_vertical_kgf),
        "f2v_kgf": float(fr.f2_vertical_kgf),
        "f_kgf": float(fr.total_kgf),
    }


@solver("lastre_empirico")
def _lastre_empirico(v: Values) -> Values:
    k = ballast.ballast_koyama_kg(_f(v, "lima"))
    p = ballast.ballast_prado_kg(_f(v, "nhp"))
    chain = ballast.adjust_chain_weight_kg(p)
    return {
        "koyama_kg": k,
        "prado_kg": p,
        "cadena_kg": chain,
        "kg_m": ballast.ballast_even_kg_m(p, chain, _f(v, "burlon")),
    }


# =============================================================================================
# 18 · Cables
# =============================================================================================


@solver("cable_por_profundidad")
def _cable_por_profundidad(v: Values) -> Values:
    depth = _f(v, "prof")
    ls = warps.warp_length_for_depth(depth)
    return {
        "relacion": warps.warp_depth_ratio(depth),
        "cable_m": ls,
        "a_comprar_m": warps.warp_quantity_m(ls),
    }


@solver("angulos_cable")
def _angulos_cable(v: Values) -> Values:
    d1 = warps.warp_declination_deg(_f(v, "prof"), _f(v, "puntal"), _f(v, "cable"))
    d2 = warps.warp_divergence_deg(_f(v, "ds"), _f(v, "pastecas"), _f(v, "cable"))
    return {"delta1": d1, "delta2": d2}


@solver("diametro_cable")
def _diametro_cable(v: Values) -> Values:
    dw = warps.warp_diameter_aguila_mm(_f(v, "nhp"))
    w = warps.warp_weight(round(dw), _f(v, "cable"))
    return {"dw_mm": dw, "dw_redondo": float(round(dw)), "peso_aire_kg": w.total_air_kg}


# =============================================================================================
# 19 · Ventana de velocidad
# =============================================================================================

_SPEEDS = (1.5, 2.0, 2.5, 3.0, 3.5, 4.0)


@solver("ventana_velocidad")
def _ventana_velocidad(v: Values) -> Values:
    kf = power.fridman_kf(PropellerType.FIXED_PITCH)
    bhp, ss, share = _f(v, "bhp"), _f(v, "ss"), _f(v, "aparejo") / 100.0
    ft = [float(power.fridman_towing_force_kgf(bhp, s, kf)) for s in _SPEEDS]
    rn = [float(drag.aberdeen_demersal(ss, s)[()]) * 1000.0 for s in _SPEEDS]
    demand = [r * (1.0 + share) for r in rn]
    w = speed_window(list(_SPEEDS), ft, demand)
    out: Values = {"v_max": w.max_speed_kn if w.max_speed_kn is not None else 0.0}
    for s, f, d in zip(_SPEEDS, ft, demand, strict=True):
        tag = f"{s:.1f}".replace(".", "_")
        out[f"ft_{tag}"] = f
        out[f"rt_{tag}"] = d
    return out


@cache
def _a3_result(vessel: str) -> Any:
    from trawlkit.api import service

    return service.run_case(service.build_case(vessel=vessel))


@solver("caso_a3")
def _caso_a3(v: Values) -> Values:
    s = _a3_result(str(v["buque"])).summary()
    return {
        "v_max": float(s["max_speed_kn"]),
        "rn3_kgf": float(s["rn_std_3kn_kgf"]),
        "lima_m": float(s["headrope_m"]),
    }


# =============================================================================================
# 20 · Optimización
# =============================================================================================


@solver("area_barrida")
def _area_barrida(v: Values) -> Values:
    v1, v2, ah1, ah2 = (_f(v, k) for k in ("v1", "v2", "ah1", "ah2"))
    a1 = ah1 * v1 * 1852.0
    a2 = ah2 * v2 * 1852.0
    return {"a1_m2_h": a1, "a2_m2_h": a2, "ganancia_pct": (a2 / a1 - 1.0) * 100.0}


# =============================================================================================
# 23 · Mar real
# =============================================================================================


@solver("corriente")
def _corriente(v: Values) -> Values:
    vf, c, ss = _f(v, "v_fondo"), _f(v, "corriente"), _f(v, "ss")
    v_agua = vf + c if str(v["sentido"]) == "en contra" else vf - c
    r0 = float(drag.aberdeen_demersal(ss, vf)[()]) * 1000.0
    r1 = float(drag.aberdeen_demersal(ss, v_agua)[()]) * 1000.0
    return {"v_agua": v_agua, "r0_kgf": r0, "r1_kgf": r1, "cambio_pct": (r1 / r0 - 1.0) * 100.0}


# =============================================================================================
# 24 · Selectividad
# =============================================================================================


@solver("retencion_logistica")
def _retencion_logistica(v: Values) -> Values:
    l50 = _f(v, "fs") * _f(v, "malla") / 10.0
    sr = _f(v, "sr")
    talla = _f(v, "talla")
    r = 1.0 / (1.0 + math.exp(-math.log(9.0) * (talla - l50) / sr))
    return {"l50_cm": l50, "l25_cm": l50 - sr / 2.0, "l75_cm": l50 + sr / 2.0, "r_pct": r * 100.0}


# =============================================================================================
# 36 · Construcción
# =============================================================================================


@solver("ciclo_corte")
def _ciclo_corte(v: Values) -> Values:
    code = str(v["codigo"])
    n_pts, t_pts, b_pts = cut_cycle(code)
    ratio = netting.cut_code_ratio(code)
    deep = n_pts + b_pts / 2.0
    cycles = _f(v, "alto") / deep
    return {
        "razon": ratio,
        "alto_ciclo": deep,
        "ciclos": cycles,
        "mallas_ancho": cycles * (t_pts + b_pts / 2.0),
    }


def _derive_embande(v: Values) -> Values:
    stretched = float(netting.stretched_length_m(_f(v, "mallas"), _f(v, "malla")))
    return {"relinga": round(_f(v, "e_obj") * stretched, 1)}


@solver("embande", derive=_derive_embande, derived={"relinga": (N_("Largo de la relinga"), "m")})
def _embande(v: Values) -> Values:
    stretched = netting.stretched_length_m(_f(v, "mallas"), _f(v, "malla"))
    e = _f(v, "relinga") / float(stretched)
    return {
        "estirado_m": stretched,
        "e": e,
        "mallas_m": _f(v, "mallas") / _f(v, "relinga"),
        "cada_50cm": _f(v, "mallas") / _f(v, "relinga") / 2.0,
    }


def _derive_toma(v: Values) -> Values:
    return {"nb": round(_f(v, "na") * _f(v, "razon_b"))}


@solver("toma_union", derive=_derive_toma, derived={"nb": (N_("Mallas del paño B"), "mallas")})
def _toma_union(v: Values) -> Values:
    na, nb = int(_f(v, "na")), int(_f(v, "nb"))
    frac = Fraction(na, nb).limit_denominator(8)
    extra = abs(na - nb)
    small = min(na, nb)
    return {
        "a": float(frac.numerator),
        "b": float(frac.denominator),
        "tomas": float(extra),
        "cada": small / extra if extra else 0.0,
    }


# =============================================================================================
# 37 · Economía
# =============================================================================================


@solver("gasoil_arrastre")
def _gasoil_arrastre(v: Values) -> Values:
    r, vk = _f(v, "r"), _f(v, "v")
    eta = _f(v, "eta") if "eta" in v else TOWING_EFFICIENCY
    p_kw = r * G_ECON * vk * KNOT_MS / eta / 1000.0
    l_h = p_kw * SFC_KG_KWH / DIESEL_KG_L
    return {"p_kw": p_kw, "l_h": l_h, "l_lance": l_h * _f(v, "horas")}


@solver("precio_equilibrio")
def _precio_equilibrio(v: Values) -> Values:
    f, g, c, cap = _f(v, "f"), _f(v, "g"), _f(v, "parte") / 100.0, _f(v, "captura")
    p = (f - c * g) / ((1.0 - c) * cap)
    return {"p": p}


@solver("costo_red_hora")
def _costo_red_hora(v: Values) -> Values:
    cost, life, rep = _f(v, "costo"), _f(v, "vida"), _f(v, "reparacion") / 100.0
    hours_year = _f(v, "horas_marea") * _f(v, "mareas")
    amort = cost / life
    repair = cost * rep / hours_year
    return {"amort_h": amort, "rep_h": repair, "total_h": amort + repair, "horas_anio": hours_year}
