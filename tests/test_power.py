"""trawlkit.power contra 'Potencia Disponible Arrastre OK' (tests/golden)."""

from __future__ import annotations

import numpy as np
import pytest

from tests.golden_utils import SPEEDS_KN, assert_close, golden, golden_entry, is_static
from trawlkit import power as p
from trawlkit.compat import ERRATA_BY_KEY
from trawlkit.io import PropellerType, Vessel, load_vessels
from trawlkit.units import KNOT_TO_MS

SHEET = "potencia_disponible_arrastre_ok"
BHPS = [150.0, 180.0]
SPEEDS = np.array(SPEEDS_KN)
PROPELLERS = {
    "fixed": PropellerType.FIXED_PITCH,
    "fixed_nozzle": PropellerType.FIXED_PITCH_NOZZLE,
    "variable": PropellerType.VARIABLE_PITCH,
    "variable_nozzle": PropellerType.VARIABLE_PITCH_NOZZLE,
}


def cell(key: str) -> str:
    entry = golden_entry(SHEET, key)
    return entry["cell"] if "cell" in entry else entry["cells"]


def gid(key: str) -> str:
    return f"{key}[{cell(key)}]"


def vessel(bhp: float) -> Vessel:
    return next(v for v in load_vessels().vessels if v.bhp == bhp)


def tag(bhp: float) -> str:
    return str(int(bhp))


# ---------------------------------------------------------------------------------------------
# Constantes: módulo == YAML == golden
# ---------------------------------------------------------------------------------------------


def test_constants_match_yaml() -> None:
    coef = p.load_power_coefficients()
    assert p.FRIDMAN_KF[PropellerType.FIXED_PITCH] == coef["fridman"]["kf"]["fixed_pitch"]
    assert (
        p.FRIDMAN_KF[PropellerType.VARIABLE_PITCH_NOZZLE]
        == coef["fridman"]["kf"]["variable_pitch_nozzle"]
    )
    for prop in PropellerType:
        pct = coef["prado"]["bollard_pull_percent"][prop.value]
        assert p.PRADO_PROPELLER_PERCENT[prop] == pct["propeller_factor"]
        assert p.PRADO_BASE_FACTOR == pct["base_factor"]
        assert pct["divisor"] == 100
        kbp = coef["bollard_pull_k"]["by_propeller"][prop.value]
        assert p.PRADO_K_BY_POWER[prop] == {150: kbp["k_150hp"], 180: kbp["k_180hp"]}
    assert p.PRADO_APN_FACTOR == coef["prado"]["apn_factor_of_bollard_pull"]
    assert p.PRADO_AVAILABLE_FRACTION == coef["prado"]["available_fraction_of_apn"]
    yaml_rows = coef["prado"]["k_by_propeller_rpm"]
    assert len(yaml_rows) == len(p.PRADO_ROWS) == 10
    for row, yrow in zip(p.PRADO_ROWS, yaml_rows, strict=True):
        assert row.propeller.value == yrow["propeller"]
        assert row.k == yrow["k"]
        assert row.high_rpm == {"high": True, "low": False, None: None}[yrow["rpm"]]
        assert yrow["source"].endswith(f"I{row.cell_150[1:]}:{row.cell_150}")
    assert p.KOYAMA_BHP_FRACTION == coef["koyama"]["bhp_fraction"]
    assert p.KOYAMA_K_SMALL == coef["koyama"]["k_table"][0]["k"]
    assert p.KOYAMA_K_LARGE == coef["koyama"]["k_table"][1]["k"]
    assert p.KOYAMA_BHP_SMALL_MAX == coef["koyama"]["k_table"][0]["bhp"]["max"]
    nom = coef["nomura"]
    assert p.NOMURA_K1 == nom["k1_engine_utilisation"]
    assert p.NOMURA_K2 == nom["k2_sea_state"]
    assert p.NOMURA_NET_SHARE == nom["net_resistance_fraction"]
    assert p.HP_IN_KGF_M_S == nom["hp_in_kgf_m_s"] == coef["hamuro"]["hp_in_kgf_m_s"]
    for name, rng in p.NOMURA_K3_RANGES.items():
        assert list(rng) == nom["k3_propulsion_efficiency"][name]["range"], name
    assert_close(p.nomura_k3_average(), nom["k3_average"])
    assert p.NOMURA_K3_EXCEL == p.NOMURA_K3_RANGES["small"][0]
    ham = coef["hamuro"]
    assert p.HAMURO_K1 == ham["k1_fraction_of_nhp"]
    assert p.HAMURO_K2 == ham["k2_sea_state"]
    assert len(ham["k3_by_propeller_rpm"]) == len(p.HAMURO_ROWS) == 7
    for row, yrow in zip(p.HAMURO_ROWS, ham["k3_by_propeller_rpm"], strict=True):
        assert row.propeller.value == yrow["propeller"]
        assert row.k3 == yrow["k3"]
        assert row.high_rpm == (yrow["rpm"] == "high")
        assert yrow["source"].startswith(f"Potencia Disponible Arrastre OK!{row.cell_150[0]}255")


def test_load_power_coefficients_is_cached() -> None:
    assert p.load_power_coefficients() is p.load_power_coefficients()
    assert p.POWER_COEFFICIENTS_PATH.name == "power_coefficients.yaml"


@pytest.mark.parametrize(
    ("key", "prop"),
    [
        ("fridman_kf_fixed_pitch", PropellerType.FIXED_PITCH),
        ("fridman_kf_variable_pitch_nozzle", PropellerType.VARIABLE_PITCH_NOZZLE),
    ],
    ids=[gid("fridman_kf_fixed_pitch"), gid("fridman_kf_variable_pitch_nozzle")],
)
def test_fridman_kf_golden(key: str, prop: PropellerType) -> None:
    assert p.fridman_kf(prop) == golden(SHEET, key)


@pytest.mark.parametrize("prop", [PropellerType.FIXED_PITCH_NOZZLE, PropellerType.VARIABLE_PITCH])
def test_fridman_kf_untabulated(prop: PropellerType) -> None:
    with pytest.raises(ValueError, match="no tabulado"):
        p.fridman_kf(prop)


@pytest.mark.parametrize("bhp", BHPS, ids=[gid("bhp_150"), gid("bhp_180")])
def test_bhp_golden(bhp: float) -> None:
    assert vessel(bhp).bhp == golden(SHEET, f"bhp_{tag(bhp)}")


@pytest.mark.parametrize(
    ("name", "bhp"),
    [(n, b) for n in PROPELLERS for b in BHPS],
    ids=[gid(f"prado_k_{n}_{tag(b)}") for n in PROPELLERS for b in BHPS],
)
def test_prado_k_golden(name: str, bhp: float) -> None:
    assert p.prado_k_factor(PROPELLERS[name], bhp) == golden(SHEET, f"prado_k_{name}_{tag(bhp)}")


def test_prado_k_nearest_power() -> None:
    pf = PropellerType.FIXED_PITCH
    assert p.prado_k_factor(pf, 100.0) == p.PRADO_K_BY_POWER[pf][150]
    assert p.prado_k_factor(pf, 165.0) == p.PRADO_K_BY_POWER[pf][150]  # empate → menor
    assert p.prado_k_factor(pf, 170.0) == p.PRADO_K_BY_POWER[pf][180]
    assert p.prado_k_factor(pf, 500.0) == p.PRADO_K_BY_POWER[pf][180]


# ---------------------------------------------------------------------------------------------
# Fridman
# ---------------------------------------------------------------------------------------------

FRIDMAN_SERIES = [
    ("fridman_ft_fixed_pitch_150_kgf", 150.0, PropellerType.FIXED_PITCH),
    ("fridman_ft_variable_pitch_nozzle_150_kgf", 150.0, PropellerType.VARIABLE_PITCH_NOZZLE),
    ("fridman_ft_fixed_pitch_180_kgf", 180.0, PropellerType.FIXED_PITCH),
    ("fridman_ft_variable_pitch_nozzle_180_kgf", 180.0, PropellerType.VARIABLE_PITCH_NOZZLE),
]


@pytest.mark.parametrize(
    ("key", "bhp", "prop"), FRIDMAN_SERIES, ids=[gid(k) for k, _, _ in FRIDMAN_SERIES]
)
def test_fridman_towing_force_golden(key: str, bhp: float, prop: PropellerType) -> None:
    ft = p.fridman_towing_force_kgf(bhp, SPEEDS, p.fridman_kf(prop))
    assert_close(ft, golden(SHEET, key), where=key)
    # Escalar a escalar.
    one = p.fridman_towing_force_kgf(bhp, SPEEDS_KN[2], p.fridman_kf(prop))
    assert isinstance(one, float)
    assert_close(one, golden(SHEET, key)[2])


SUMMARY_SERIES = [
    ("fridman_summary_fixed_150_kgf", 150.0, "ft_fixed_pitch_kgf"),
    ("fridman_summary_variable_nozzle_150_kgf", 150.0, "ft_variable_pitch_nozzle_kgf"),
    ("fridman_summary_fixed_180_kgf", 180.0, "ft_fixed_pitch_kgf"),
    ("fridman_summary_variable_nozzle_180_kgf", 180.0, "ft_variable_pitch_nozzle_kgf"),
]


@pytest.mark.parametrize(
    ("key", "bhp", "attr"), SUMMARY_SERIES, ids=[gid(k) for k, _, _ in SUMMARY_SERIES]
)
def test_summary_golden(key: str, bhp: float, attr: str) -> None:
    s = p.summary(vessel(bhp), SPEEDS_KN)
    assert_close(getattr(s, attr), golden(SHEET, key), where=key)
    assert s.to_dict()[attr] == getattr(s, attr).tolist()
    assert s.bhp == bhp and s.speeds_kn.tolist() == SPEEDS_KN


# ---------------------------------------------------------------------------------------------
# Prado & Dremiere: bollard pull, APN, potencia de arrastre
# ---------------------------------------------------------------------------------------------

BP_CASES = [(n, b) for n in PROPELLERS for b in BHPS]
BP_IDS = [f"{n}_{tag(b)}" for n, b in BP_CASES]


@pytest.mark.parametrize(
    ("name", "bhp"),
    BP_CASES,
    ids=[gid(f"bollard_pull_{i}_kgf") + "+" + cell(f"bollard_pull_{i}_t") for i in BP_IDS],
)
def test_bollard_pull_golden(name: str, bhp: float) -> None:
    prop = PROPELLERS[name]
    key = f"bollard_pull_{name}_{tag(bhp)}"
    assert_close(p.bollard_pull_kgf(bhp, prop), golden(SHEET, f"{key}_kgf"), where=key)
    assert_close(p.bollard_pull_t(bhp, prop), golden(SHEET, f"{key}_t"), where=key)
    # El porcentaje también puede pasarse como número.
    assert p.bollard_pull_kgf(bhp, p.prado_propeller_percent(prop)) == p.bollard_pull_kgf(bhp, prop)


@pytest.mark.parametrize(
    ("name", "bhp"), BP_CASES, ids=[gid(f"bollard_pull_k_{i}_t") for i in BP_IDS]
)
def test_bollard_pull_k_golden(name: str, bhp: float) -> None:
    prop = PROPELLERS[name]
    bp_k = p.bollard_pull_k_t(bhp, p.prado_k_factor(prop, bhp))
    assert_close(bp_k, golden(SHEET, f"bollard_pull_k_{name}_{tag(bhp)}_t"))


def test_bollard_pull_k_hp() -> None:
    # J59 = (I59*100)/1.36 con I59 = 1.6845 t.
    assert_close(p.bollard_pull_k_hp(1.6845), 1.6845 * 100 / 1.36)


@pytest.mark.parametrize(
    ("name", "bhp"), BP_CASES, ids=[gid(f"bollard_pull_avg_{i}_kgf") for i in BP_IDS]
)
def test_bollard_pull_avg_golden(name: str, bhp: float) -> None:
    prop = PROPELLERS[name]
    avg = p.bollard_pull_avg_kgf(
        p.bollard_pull_kgf(bhp, prop), p.bollard_pull_k_t(bhp, p.prado_k_factor(prop, bhp))
    )
    assert_close(avg, golden(SHEET, f"bollard_pull_avg_{name}_{tag(bhp)}_kgf"))


@pytest.mark.parametrize(("name", "bhp"), BP_CASES, ids=[gid(f"apn_{i}_hp") for i in BP_IDS])
def test_apparent_nominal_power_golden(name: str, bhp: float) -> None:
    prop = PROPELLERS[name]
    apn = p.apparent_nominal_power_hp(
        golden(SHEET, f"bollard_pull_avg_{name}_{tag(bhp)}_kgf"),
    )
    assert_close(apn, golden(SHEET, f"apn_{name}_{tag(bhp)}_hp"))
    assert prop in p.PRADO_PROPELLER_PERCENT


TP_CASES = [(row, b) for row in p.PRADO_ROWS for b in BHPS]


@pytest.mark.parametrize(
    ("row", "bhp"),
    TP_CASES,
    ids=[gid(f"trawling_power_{r.key}_{tag(b)}_hp") for r, b in TP_CASES],
)
def test_trawling_power_golden(row: p.PradoRow, bhp: float) -> None:
    key = f"trawling_power_{row.key}_{tag(bhp)}_hp"
    assert cell(key) == (row.cell_150 if bhp == 150 else row.cell_180)
    family = {
        PropellerType.FIXED_PITCH: "fixed",
        PropellerType.FIXED_PITCH_NOZZLE: "fixed_nozzle",
        PropellerType.VARIABLE_PITCH: "variable",
        PropellerType.VARIABLE_PITCH_NOZZLE: "variable_nozzle",
    }[row.propeller]
    apn = golden(SHEET, f"apn_{family}_{tag(bhp)}_hp")
    assert_close(p.trawling_power_hp(apn, row.k), golden(SHEET, key), where=key)
    assert_close(p.prado_trawling_power_table(bhp)[row.key], golden(SHEET, key), where=key)


# ---------------------------------------------------------------------------------------------
# Prado & Dremiere: BPF
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("row", "bhp"), TP_CASES, ids=[gid(f"prado_bpf_{r.key}_{tag(b)}_kgf") for r, b in TP_CASES]
)
def test_bollard_pull_fishing_golden(row: p.PradoRow, bhp: float) -> None:
    key = f"prado_bpf_{row.key}_{tag(bhp)}_kgf"
    power_hp = golden(SHEET, f"trawling_power_{row.key}_{tag(bhp)}_hp")
    # El 150 es una constante de conversión, también para el buque de 180 HP (D88).
    assert_close(p.bollard_pull_fishing_kgf(power_hp, SPEEDS), golden(SHEET, key), where=key)
    assert_close(p.prado_bpf_table(bhp, SPEEDS)[row.key], golden(SHEET, key), where=key)


BPF_AVG = [
    ("prado_bpf_avg_fixed_150_kgf", 150.0, "fixed"),
    ("prado_bpf_avg_fixed_180_kgf", 180.0, "fixed"),
    ("prado_bpf_avg_variable_150_kgf", 150.0, "variable"),
    ("prado_bpf_avg_variable_180_kgf", 180.0, "variable"),
]


@pytest.mark.parametrize(("key", "bhp", "family"), BPF_AVG, ids=[gid(k) for k, _, _ in BPF_AVG])
def test_bollard_pull_fishing_avg_golden(key: str, bhp: float, family: str) -> None:
    avg = p.bollard_pull_fishing_avg_kgf(bhp, SPEEDS, family)  # type: ignore[arg-type]
    assert_close(avg, golden(SHEET, key), where=key)


def test_bollard_pull_fishing_rejects_zero_speed() -> None:
    with pytest.raises(ValueError):
        p.bollard_pull_fishing_kgf(20.0, 0.0)


# ---------------------------------------------------------------------------------------------
# Koyama
# ---------------------------------------------------------------------------------------------


def test_speed_ms_series_uses_0_514() -> None:
    key = "speed_ms"
    assert_close(SPEEDS * p.KNOT_TO_MS_KOYAMA, golden(SHEET, key), where=cell(key))
    assert p.KNOT_TO_MS_KOYAMA != KNOT_TO_MS


@pytest.mark.parametrize("bhp", BHPS, ids=[gid("koyama_bhp_f_150_hp"), gid("koyama_bhp_f_180_hp")])
def test_koyama_steps_golden(bhp: float) -> None:
    t = tag(bhp)
    k = p.koyama_k(bhp)
    assert k == golden(SHEET, "koyama_k")
    bhp_f = p.koyama_bhp_f_hp(bhp)
    assert_close(bhp_f, golden(SHEET, f"koyama_bhp_f_{t}_hp"))
    ehp = p.koyama_ehp_hp(bhp_f, k)
    assert_close(ehp, golden(SHEET, f"koyama_ehp_{t}_hp"))
    assert_close(p.koyama_ehp_kgf_m_s(ehp), golden(SHEET, f"koyama_ehp_{t}_kgf_m_s"))


@pytest.mark.parametrize("bhp", BHPS, ids=[gid("koyama_pull_150_kgf"), gid("koyama_pull_180_kgf")])
def test_koyama_pull_golden(bhp: float) -> None:
    key = f"koyama_pull_{tag(bhp)}_kgf"
    v_ms = SPEEDS * p.KNOT_TO_MS_KOYAMA
    assert_close(p.koyama_pull_kgf(bhp, p.KOYAMA_K_SMALL, v_ms), golden(SHEET, key), where=key)
    assert_close(p.koyama_pull_series_kgf(bhp, SPEEDS), golden(SHEET, key), where=key)
    one = p.koyama_pull_series_kgf(bhp, 1.0)
    assert isinstance(one, float)
    assert_close(one, golden(SHEET, key)[0])


def test_koyama_k_lookup() -> None:
    assert p.koyama_k(599.0) == 0.15
    assert p.koyama_k(1200.0) == 0.18


# ---------------------------------------------------------------------------------------------
# Nomura
# ---------------------------------------------------------------------------------------------


def test_nomura_constants_golden() -> None:
    assert p.NOMURA_K1 == golden(SHEET, "nomura_k1_engine_use")
    assert p.NOMURA_K2 == golden(SHEET, "nomura_k2_sea_state")
    assert p.NOMURA_K3_RANGES["medium"] == (golden(SHEET, "nomura_k3_medium_trawlers"),)
    assert_close(p.nomura_k3_average(), golden(SHEET, "nomura_k3_average"))
    assert p.NOMURA_NET_SHARE == golden(SHEET, "nomura_net_drag_share")


@pytest.mark.parametrize("bhp", BHPS, ids=[gid("nomura_pull_150_kgf"), gid("nomura_pull_180_kgf")])
def test_nomura_pull_golden(bhp: float) -> None:
    key = f"nomura_pull_{tag(bhp)}_kgf"
    v_ms = SPEEDS * p.KNOT_TO_MS_KOYAMA  # B216 = H171 = 0.514
    # NHP = MID("150 HP",1,3): el Excel usa el BHP como NHP.
    pull = p.nomura_pull_kgf(bhp, p.NOMURA_K1, p.NOMURA_K2, p.NOMURA_K3_EXCEL, v_ms)
    assert_close(pull, golden(SHEET, key), where=key)
    assert_close(p.nomura_pull_series_kgf(bhp, SPEEDS), golden(SHEET, key), where=key)


def test_nomura_pull_uses_lower_bound_k3_not_average() -> None:
    v_ms = SPEEDS * p.KNOT_TO_MS_KOYAMA
    with_avg = p.nomura_pull_kgf(150.0, 0.85, 0.85, p.nomura_k3_average(), v_ms)
    assert not np.allclose(with_avg, golden(SHEET, "nomura_pull_150_kgf"))


# ---------------------------------------------------------------------------------------------
# Hamuro
# ---------------------------------------------------------------------------------------------

HAM_CASES = [(row, b) for row in p.HAMURO_ROWS for b in BHPS]


def test_hamuro_k1_golden() -> None:
    assert p.HAMURO_K1 == golden(SHEET, "hamuro_k1")


@pytest.mark.parametrize(
    ("row", "bhp"), HAM_CASES, ids=[gid(f"hamuro_ps_{r.key}_{tag(b)}_hp") for r, b in HAM_CASES]
)
def test_hamuro_ps_golden(row: p.HamuroRow, bhp: float) -> None:
    key = f"hamuro_ps_{row.key}_{tag(bhp)}_hp"
    assert cell(key) == (row.cell_150 if bhp == 150 else row.cell_180)
    assert p.hamuro_k3(row.propeller, row.high_rpm) == row.k3
    ps = p.hamuro_ps_hp(bhp, p.HAMURO_K1, p.HAMURO_K2, row.k3)
    assert_close(ps, golden(SHEET, key), where=key)
    assert_close(p.hamuro_ps_table(bhp)[row.key], golden(SHEET, key), where=key)


@pytest.mark.parametrize(
    ("bhp", "case"),
    [(b, c) for b in BHPS for c in ("worst", "best")],
    ids=[gid(f"hamuro_ps_{c}_avg_{tag(b)}_hp") for b in BHPS for c in ("worst", "best")],
)
def test_hamuro_ps_average_golden(bhp: float, case: str) -> None:
    key = f"hamuro_ps_{case}_avg_{tag(bhp)}_hp"
    avg = p.hamuro_ps_average_hp(bhp, case)  # type: ignore[arg-type]
    assert_close(avg, golden(SHEET, key), where=key)


HAM_PULL = [
    ("hamuro_pull_fixed_150_kgf", 150.0, "fixed_low_rpm"),
    ("hamuro_pull_variable_nozzle_150_kgf", 150.0, "variable_nozzle_high_rpm"),
    ("hamuro_pull_fixed_180_kgf", 180.0, "fixed_low_rpm"),
    ("hamuro_pull_variable_nozzle_180_kgf", 180.0, "variable_nozzle_high_rpm"),
]


@pytest.mark.parametrize(("key", "bhp", "row_key"), HAM_PULL, ids=[gid(k) for k, _, _ in HAM_PULL])
def test_hamuro_pull_golden(key: str, bhp: float, row_key: str) -> None:
    row = next(r for r in p.HAMURO_ROWS if r.key == row_key)
    ps = golden(SHEET, f"hamuro_ps_{row_key}_{tag(bhp)}_hp")
    v_ms = SPEEDS * KNOT_TO_MS  # B272 = 0.5144
    assert_close(p.hamuro_pull_kgf(ps, v_ms), golden(SHEET, key), where=key)
    assert_close(p.hamuro_pull_series_kgf(bhp, SPEEDS, row.k3), golden(SHEET, key), where=key)


def test_hamuro_k3_untabulated() -> None:
    with pytest.raises(ValueError, match="no tabulated"):
        p.hamuro_k3(PropellerType.VARIABLE_PITCH, high_rpm=False)


# ---------------------------------------------------------------------------------------------
# Curvas por buque
# ---------------------------------------------------------------------------------------------


def test_power_curves_150_fixed_high_rpm() -> None:
    v = vessel(150.0)
    assert v.propeller is PropellerType.FIXED_PITCH and v.high_rpm
    curves = p.power_curves(v, SPEEDS_KN)
    assert_close(curves.fridman_kgf, golden(SHEET, "fridman_ft_fixed_pitch_150_kgf"))
    assert_close(curves.prado_kgf, golden(SHEET, "prado_bpf_fixed_high_rpm_150_kgf"))
    assert_close(curves.koyama_kgf, golden(SHEET, "koyama_pull_150_kgf"))
    assert_close(curves.nomura_kgf, golden(SHEET, "nomura_pull_150_kgf"))
    # Hamuro PF > 300 RPM (G259) no tiene serie en el Excel: 75·Ps/(0.5144·v).
    ps = golden(SHEET, "hamuro_ps_fixed_high_rpm_150_hp")
    assert_close(curves.hamuro_kgf, 75.0 * ps / (SPEEDS * KNOT_TO_MS))
    assert_close(
        curves.average_kgf,
        np.mean(
            [
                curves.fridman_kgf,
                curves.prado_kgf,
                curves.koyama_kgf,
                curves.nomura_kgf,
                curves.hamuro_kgf,
            ],
            axis=0,
        ),
    )
    d = curves.to_dict()
    assert d["propeller"] == "fixed_pitch" and d["high_rpm"] is True and d["bhp"] == 150.0
    assert d["speeds_kn"] == SPEEDS_KN and len(d["average_kgf"]) == len(SPEEDS_KN)
    for method in ("fridman", "prado", "koyama", "nomura", "hamuro"):
        assert_close(
            p.available_towing_force_kgf(v, SPEEDS_KN, method),  # type: ignore[arg-type]
            curves.by_method(method),  # type: ignore[arg-type]
        )
    assert_close(p.available_towing_force_kgf(v, SPEEDS_KN), curves.fridman_kgf)


def test_power_curves_180_variable_nozzle() -> None:
    v = vessel(180.0).model_copy(update={"propeller": PropellerType.VARIABLE_PITCH_NOZZLE})
    curves = p.power_curves(v, SPEEDS)
    assert_close(curves.fridman_kgf, golden(SHEET, "fridman_ft_variable_pitch_nozzle_180_kgf"))
    expected_prado = np.mean(
        [
            golden(SHEET, "prado_bpf_variable_nozzle_k28_180_kgf"),
            golden(SHEET, "prado_bpf_variable_nozzle_k30_180_kgf"),
        ],
        axis=0,
    )
    assert_close(curves.prado_kgf, expected_prado)
    assert_close(curves.koyama_kgf, golden(SHEET, "koyama_pull_180_kgf"))
    assert_close(curves.nomura_kgf, golden(SHEET, "nomura_pull_180_kgf"))
    assert_close(curves.hamuro_kgf, golden(SHEET, "hamuro_pull_variable_nozzle_180_kgf"))


def test_power_curves_low_rpm_fixed_averages_two_prado_rows() -> None:
    v = vessel(150.0).model_copy(update={"high_rpm": False})
    curves = p.power_curves(v, SPEEDS)
    expected = np.mean(
        [
            golden(SHEET, "prado_bpf_fixed_low_rpm_k25_150_kgf"),
            golden(SHEET, "prado_bpf_fixed_low_rpm_k28_150_kgf"),
        ],
        axis=0,
    )
    assert_close(curves.prado_kgf, expected)
    assert_close(curves.hamuro_kgf, golden(SHEET, "hamuro_pull_fixed_150_kgf"))


def test_power_curves_overrides() -> None:
    v = vessel(150.0).model_copy(update={"propeller": PropellerType.FIXED_PITCH_NOZZLE})
    with pytest.raises(ValueError, match="no tabulado"):
        p.power_curves(v, SPEEDS)
    curves = p.power_curves(v, SPEEDS, kf=12.0, nhp=199.5, koyama_k_value=0.18, nomura_k3=0.2)
    assert_close(curves.fridman_kgf, p.fridman_towing_force_kgf(150.0, SPEEDS, 12.0))
    assert_close(curves.koyama_kgf, p.koyama_pull_series_kgf(150.0, SPEEDS, 0.18))
    assert_close(curves.nomura_kgf, p.nomura_pull_series_kgf(199.5, SPEEDS, k3=0.2))
    assert_close(curves.hamuro_kgf, p.hamuro_pull_series_kgf(199.5, SPEEDS, 0.24))
    assert_close(curves.prado_kgf, golden(SHEET, "prado_bpf_fixed_nozzle_high_rpm_150_kgf"))


# ---------------------------------------------------------------------------------------------
# Tablas resumen A295:I370 (valores pegados + errata de la columna Nomura)
# ---------------------------------------------------------------------------------------------

CASES = ["worst_150", "best_150", "worst_180", "best_180"]


@pytest.mark.parametrize("case", CASES)
def test_summary_tables_static_flags(case: str) -> None:
    for method in ("fridman", "prado", "koyama", "hamuro"):
        assert is_static(SHEET, f"summary_{case}_{method}_kgf"), (case, method)
    assert not is_static(SHEET, f"summary_{case}_nomura_kgf")
    assert not is_static(SHEET, f"summary_{case}_average_kgf")


@pytest.mark.parametrize("case", CASES)
def test_summary_tables_average_is_mean_of_columns(case: str) -> None:
    # I300 = AVERAGE(D300:H300): promedio de las cinco columnas (cuatro pegadas + Nomura).
    cols = [
        golden(SHEET, f"summary_{case}_{m}_kgf")
        for m in ("fridman", "prado", "koyama", "nomura", "hamuro")
    ]
    assert_close(np.mean(cols, axis=0), golden(SHEET, f"summary_{case}_average_kgf"))


def test_summary_nomura_column_links_hamuro_erratum() -> None:
    erratum = ERRATA_BY_KEY["nomura_column_links_hamuro"]
    assert erratum.cell == "G319,G342,G362"
    # G300 = E216 (Nomura de verdad, 150 HP).
    assert_close(
        golden(SHEET, "summary_worst_150_nomura_kgf"), golden(SHEET, "nomura_pull_150_kgf")
    )
    # G319 = F272, G342 = G272, G362 = H272: la columna "Nomura" repite la de Hamuro.
    for case, ham in (
        ("best_150", "hamuro_pull_variable_nozzle_150_kgf"),
        ("worst_180", "hamuro_pull_fixed_180_kgf"),
        ("best_180", "hamuro_pull_variable_nozzle_180_kgf"),
    ):
        assert_close(golden(SHEET, f"summary_{case}_nomura_kgf"), golden(SHEET, ham), where=case)
        assert_close(
            golden(SHEET, f"summary_{case}_nomura_kgf"), golden(SHEET, f"summary_{case}_hamuro_kgf")
        )
