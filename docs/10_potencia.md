---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# Potencia disponible para el arrastre

```{code-cell} ipython3
:tags: [remove-cell]
import sys, pathlib, math
sys.path.insert(0, str(pathlib.Path.cwd().parent))
import numpy as np
import matplotlib.pyplot as plt
from tests.golden_utils import golden, SPEEDS_KN
import _plots_t1 as P
P.setup_style()
```

## Propósito

Antes de dibujar un solo paño hay que saber **cuánta fuerza puede hacer el buque** a la velocidad de
pesca. Esa fuerza, el tiro disponible $F_T$ (kgf), es el techo de todo el diseño: la resistencia de
la red, de los portones, de las boyas y de los cables debe quedar por debajo de ella en la ventana de
velocidades de trabajo. Es la primera etapa de la cadena (ver {doc}`motor`) y alimenta la resistencia
de los portones (ROB como fracción de $F_T$), la flotación de Fridman y la ventana de velocidad
({doc}`19_ventana_velocidad`).

El libro original estima $F_T$ por cinco caminos independientes —Fridman, Prado y Dremière, Koyama,
Nomura y Hamuro— para los dos buques de la clase (150 y 180 BHP). No son cinco mediciones de lo mismo:
cada autor parte de una hipótesis física distinta, y entender esa hipótesis es lo que permite
elegir y desconfiar con criterio.

## Teoría

### Reparto de la energía del motor (Fridman)

Fridman {cite:p}`fridman1986` propone un balance grosero pero didáctico: de la energía del motor,
alrededor de un tercio se pierde antes de llegar a la hélice (reductora, auxiliares), de modo que

$$
\mathrm{HP_{nom}} = \mathrm{BHP}\,(1 + 0{,}33)
$$ (eq-pot-nominal)

y de la potencia que llega a la hélice (BHP) sólo un tercio se convierte en tiro útil sobre la red:

$$
\mathrm{HP_{tiro}} = 0{,}33\,\mathrm{BHP}.
$$ (eq-pot-tiro)

El resto se reparte entre el giro de la hélice (35 %), la formación de olas (27 %), el rozamiento del
casco (18 %), la estela y turbulencia (17 %) y la resistencia del aire (3 %). La demanda total que el
buque debe cubrir es

$$
P_{\text{total}} = R_N + 2R_W + 2R_{OB} + R_H ,
$$ (eq-pot-demanda)

con $R_N$ la resistencia de la red, $R_W$ la de cada cable, $R_{OB}$ la de cada portón y $R_H$ la del
casco.

### Tiro disponible de Fridman

La fórmula empírica de Fridman relaciona el tiro con la potencia en la hélice $P$ [HP] y la velocidad
$v$ [kn]:

$$
F_T = P\,(K_F - 0{,}7\,v)
$$ (eq-fridman-ft)

$K_F$ [kgf/HP] es el tiro por caballo a punto fijo: 10 para hélice de paso fijo (PF) y 15 para paso
variable con tobera (PV+T). La pendiente $0{,}7\,P$ expresa que, al avanzar, la hélice pierde empuje
porque su ángulo de ataque efectivo disminuye. Es la única de las cinco fórmulas con un **tiro a
punto fijo finito** ($F_T(0) = K_F P$): para 150 BHP y PF, 1500 kgf.

### Prado y Dremière (FAO)

El *Fisherman's Workbook* {cite:p}`prado1990` encadena cuatro reglas prácticas. El tiro a punto fijo
(*bollard pull*) es

$$
BP = \mathrm{BHP}\cdot 0{,}9\cdot \frac{p}{100}\ \ [\mathrm{t}],
$$ (eq-prado-bp)

con $p$ = 1,10 (PF), 1,20 (PF+T), 1,25 (PV) y 1,40 (PV+T), es decir, entre 9,9 y 12,6 kgf por BHP. El
libro lo promedia con una segunda estimación, $BP_K = K\cdot\mathrm{BHP}/1000$ con $K$ tabulado según
potencia y hélice. Del *bollard pull* promedio se obtiene una potencia nominal aparente y, de ella, la
potencia disponible para el arrastre:

$$
\mathrm{APN} = 0{,}09\,BP_{\text{prom}}, \qquad P_a = 0{,}75\,K\,\mathrm{APN},
$$ (eq-prado-apn)

con $K$ = 0,20 (paso fijo, altas RPM) a 0,30 (paso variable con tobera). Finalmente el tiro pescando
(*bollard pull when fishing*) es

$$
BPF = \frac{150\,P_a}{v}\quad [\mathrm{kgf}],\ v\ \text{en kn},
$$ (eq-prado-bpf)

donde 150 es una constante de conversión ($\approx 75/0{,}5144$ kgf·kn por HP), **no** el BHP.

### Koyama, Nomura y Hamuro: potencia constante

Las tres escuelas japonesas parten de una potencia efectiva de remolque $P_e$ [HP] y suponen que se
mantiene constante, de modo que el tiro es potencia sobre velocidad:

$$
F = \frac{75\,P_e}{v}\quad [\mathrm{kgf}],\ v\ \text{en m/s}.
$$ (eq-potencia-constante)

Lo que cambia es cómo se estima $P_e$:

* **Koyama** {cite:p}`koyama1974`: $P_e = \mathrm{EHP} = K\cdot 0{,}6\,\mathrm{BHP}$, con 0,6 la carga del
  motor durante la pesca y $K$ = 0,15 para buques de menos de 600 BHP (0,18 para 1200–1500 BHP).
* **Nomura** {cite:p}`nomura1981`: $P_e = 0{,}8\,K_1K_2K_3\,\mathrm{NHP}$, con $K_1 = 0{,}85$ (uso del
  motor), $K_2 = 0{,}85$ (estado del mar), $K_3$ = 0,17–0,29 (eficiencia propulsiva según tamaño del
  arrastrero; el libro usa 0,17) y 0,8 la fracción de la demanda atribuida a la red.
* **Hamuro** {cite:p}`hamuro`: $P_e = P_s = K_1K_2K_3\,\mathrm{NHP}$, con $K_1 = 0{,}825$, $K_2 = 0{,}85$ y
  $K_3$ entre 0,20 (PF, altas RPM) y 0,30 (PV+T, altas RPM).

La forma {eq}`eq-potencia-constante` diverge cuando $v \to 0$: a 1 kn predice tiros de 2 a 4 t para un
buque cuyo *bollard pull* es 1,5–1,9 t, lo que es físicamente imposible. Estas fórmulas sólo tienen
sentido en el rango de arrastre (≈ 2,5–4,5 kn), donde la hélice trabaja cerca de su punto de diseño.
Por eso, aunque el libro promedia los cinco métodos, el que alimenta el resto del diseño es el de
Fridman: es lineal, acotado y conservador a baja velocidad.

## Coeficientes

| Coeficiente | Valor | Unidad | Fuente | Celda del Excel |
|---|---|---|---|---|
| $K_F$ paso fijo / PV+T | 10 / 15 | kgf/HP | Fridman | `PotOK!D10`, `F10` |
| Pendiente de Fridman | 0,7 | kgf/(HP·kn) | Fridman | `PotOK!E10` |
| Fracciones del BHP (nominal, tiro) | 0,33 / 0,33 | — | Fridman | `Pot!C24`, `C26` |
| Pérdidas (hélice, olas, rozamiento, estela, aire) | 0,35 / 0,27 / 0,18 / 0,17 / 0,03 | — | Fridman | `Pot!C27:C31` |
| $p$ del *bollard pull* (PF, PF+T, PV, PV+T) | 1,10 / 1,20 / 1,25 / 1,40 | % | Prado | `PotOK!A49:A55` |
| $K$ del *bollard pull* (150 HP, PF) | 11,23 | t/1000 HP | Prado | `PotOK!K52:L55` |
| APN / fracción disponible | 0,09 / 0,75 | — | Prado | `PotOK!B73`, `K68` |
| $K$ de arrastre | 0,20–0,30 | — | Prado | `PotOK!K68:L77` |
| Koyama $K$ / carga | 0,15 / 0,6 | — | Koyama | `PotOK!M165`, `C169` |
| Nomura $K_1$, $K_2$, $K_3$, fracción red | 0,85 / 0,85 / 0,17 / 0,8 | — | Nomura | `PotOK!L205:L213` |
| Hamuro $K_1$, $K_2$, $K_3$ | 0,825 / 0,85 / 0,20–0,30 | — | Hamuro | `PotOK!C254`, `F257:L258` |

Los valores están en `src/trawlkit/data/reference/power_coefficients.yaml`, generado desde el libro.

## Equivalencia Excel ↔ `trawlkit`

| Celda(s) | Contenido | Función |
|---|---|---|
| `Pot!C24:E31` | Reparto de energía | `trawlkit.vessel.power_budget` |
| `Pot!H27`, `H38` | Velocidad de Almirantazgo | `trawlkit.vessel.admiralty_speed_kn` |
| `PotOK!E10:G30` | $F_T$ de Fridman | `trawlkit.power.fridman_towing_force_kgf` |
| `PotOK!B60:E63` | *Bollard pull* | `trawlkit.power.bollard_pull_kgf` |
| `PotOK!I59:L62`, `G58:G68` | BP vía $K$ y promedio | `bollard_pull_k_t`, `bollard_pull_avg_kgf` |
| `PotOK!B73:C76` | APN | `trawlkit.power.apparent_nominal_power_hp` |
| `PotOK!K68:L77` | Potencia de arrastre | `trawlkit.power.trawling_power_hp` |
| `PotOK!C88:L111`, `C123:F131` | BPF y promedios | `bollard_pull_fishing_kgf`, `bollard_pull_fishing_avg_kgf` |
| `PotOK!K171:L179` | Koyama | `trawlkit.power.koyama_pull_series_kgf` |
| `PotOK!E216:F224` | Nomura | `trawlkit.power.nomura_pull_series_kgf` |
| `PotOK!F259:L266`, `E272:H280` | Hamuro | `hamuro_ps_table`, `hamuro_pull_series_kgf` |
| `PotOK!L11:O19` | Resumen de Fridman (PF y PV+T) | `trawlkit.power.summary` |
| — | Las cinco curvas para un buque | `trawlkit.power.power_curves` |

## Supuestos y límites

* **Velocidad en m/s.** Koyama y Nomura convierten nudos con **0,514** (`PotOK!H171`); Hamuro y el resto
  del libro con **0,5144** (`PotOK!B272`). `trawlkit` reproduce ambos factores; la diferencia es de
  0,08 %.
* **NHP = BHP.** Nomura y Hamuro piden la potencia nominal, pero el libro toma `MID("150 HP",1,3)`,
  es decir el BHP (150/180), y no los HP nominales de {eq}`eq-pot-nominal` (199,5/239,4). Usar los
  nominales elevaría estas dos curvas un 33 %.
* **El 150 de BPF** es una constante de unidades y se usa también para el buque de 180 HP.
* **Tablas resumen estáticas.** Los resúmenes "peor/mejor caso" (`PotOK!A295:I370`) son números pegados
  que no siempre coinciden con las fórmulas (Koyama pegado 2382 kgf a 1 kn frente a 1970 kgf de la
  fórmula) y su columna "Nomura" enlaza a Hamuro en tres de las cuatro tablas (errata
  `nomura_column_links_hamuro`, ver {doc}`erratas`). `trawlkit` calcula Nomura de verdad.
* **Dominio.** Las fórmulas de potencia constante sólo valen en el rango de arrastre; ninguna considera
  el estado de la hélice, el calado ni el ensuciamiento del casco. Los rangos de $K_3$ de Nomura y
  Hamuro dan una idea honesta de la incertidumbre: ±20 % sobre $F_T$.

## Ejemplo ejecutable

Reparto de energía de los dos buques de la clase:

```{code-cell} ipython3
from trawlkit.vessel import power_budget

G0 = "potenc_disponible_para_arrastre"
rows = []
for bhp in (150, 180):
    b = power_budget(bhp)
    ref = golden(G0, f"towing_hp_{bhp}")
    assert math.isclose(b.towing_hp, ref, rel_tol=1e-6)
    hp = (b.nominal_hp, b.towing_hp, b.propeller_loss_hp, b.wave_loss_hp,
          b.friction_loss_hp, b.wake_loss_hp, b.air_loss_hp)
    rows.append([f"{bhp:.0f}", *(P.fmt(x, 1) for x in hp)])
P.md_table(["BHP", "HP nominales", "Tiro de red", "Hélice", "Olas",
            "Rozamiento", "Estela", "Aire"], rows)
```

Las cinco curvas de tiro con la configuración de **paso fijo** que el libro usa como peor caso
(Prado: promedio de las seis filas de paso fijo, `C123`; Hamuro: PF a bajas RPM, `E272`), verificadas
contra los valores del Excel:

```{code-cell} ipython3
from trawlkit import power
from trawlkit.io.schema import PropellerType

v = np.array(SPEEDS_KN)
G = "potencia_disponible_arrastre_ok"

PF = PropellerType.FIXED_PITCH
K3_PF_LOW_RPM = power.hamuro_k3(PF, high_rpm=False)  # 0.265, columna E272

def curves(bhp):
    return {
        "Fridman": power.fridman_towing_force_kgf(bhp, v, power.FRIDMAN_KF[PF]),
        "Prado": power.bollard_pull_fishing_avg_kgf(bhp, v, "fixed"),
        "Koyama": power.koyama_pull_series_kgf(bhp, v),
        "Nomura": power.nomura_pull_series_kgf(bhp, v),
        "Hamuro": power.hamuro_pull_series_kgf(bhp, v, k3=K3_PF_LOW_RPM),
    }

ft = {bhp: curves(bhp) for bhp in (150, 180)}
keys = {"Fridman": "fridman_ft_fixed_pitch_{}_kgf",
        "Prado": "prado_bpf_avg_fixed_{}_kgf",
        "Koyama": "koyama_pull_{}_kgf",
        "Nomura": "nomura_pull_{}_kgf",
        "Hamuro": "hamuro_pull_fixed_{}_kgf"}
for bhp, c in ft.items():
    for name, key in keys.items():
        ref = golden(G, key.format(bhp))
        ok = all(math.isclose(a, b, rel_tol=1e-6) for a, b in zip(c[name], ref))
        assert ok, (bhp, name)

i3 = SPEEDS_KN.index(3.0)
P.md_table(["Método", "150 BHP a 3 kn [kgf]", "180 BHP a 3 kn [kgf]"],
           [[n, P.fmt(ft[150][n][i3], 0), P.fmt(ft[180][n][i3], 0)] for n in keys])
```

```{code-cell} ipython3
:tags: [hide-input]
from trawlkit.drag import aberdeen_demersal

rn = aberdeen_demersal(golden("mecanica_de_la_red", "solid_surface_std_m2"), v) * 1000
order = ["Fridman", "Prado", "Koyama", "Nomura", "Hamuro"]
fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0), sharey=True)
for ax, bhp in zip(axes, (150, 180)):
    for k, name in enumerate(order):
        y = ft[bhp][name]
        mk = dict(marker="o", ms=5, mec=P.SURFACE, mew=1.5) if name == "Hamuro" else {}
        ax.plot(v, y, color=P.SERIES[k], label=name, zorder=3, **mk)
    ax.plot(v, rn, color=P.INK_2, lw=1.2, label="RN de diseño (Aberdeen)", zorder=2)
    bp = power.bollard_pull_kgf(bhp, PF)
    ax.axhline(bp, color=P.MUTED, lw=1, zorder=1)
    ax.annotate(f"bollard pull PF = {P.fmt(bp, 0)} kgf", xy=(5.0, bp), xytext=(0, 4),
                textcoords="offset points", ha="right", fontsize=8, color=P.INK_2)
    ax.set_title(f"{bhp} BHP, hélice de paso fijo")
    ax.set_xlabel("Velocidad de arrastre [kn]")
    ax.set_xlim(1, 5)
    ax.set_ylim(0, 5200)
    ax.set_xticks(np.arange(1, 5.5, 0.5))
axes[0].set_ylabel("Tiro disponible $F_T$ [kgf]")
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", ncol=6, bbox_to_anchor=(0.5, -0.02))
fig.tight_layout(rect=(0, 0.07, 1, 1))
plt.show()
```

La figura resume la discusión teórica. Fridman (azul) es una recta acotada por el *bollard pull*; las
otras cuatro son hipérbolas que lo superan por debajo de 2 kn. En el rango de pesca (2,5–3,5 kn) los
métodos se ordenan con una dispersión de casi 2:1: Prado y Hamuro son los más optimistas, Koyama y
Nomura los más prudentes y Fridman queda en el medio a 3 kn. La línea gris es la resistencia de
diseño de la red sola ({doc}`14_resistencia`). Con hélice de paso fijo, la red sola ya iguala el tiro
de Fridman hacia 2,5 kn en el buque de 150 BHP y hacia 2,7 kn en el de 180 BHP; con paso variable y
tobera ($K_F = 15$) esos cruces suben a 3,25 y 3,6 kn. Según Koyama o Nomura el cruce baja a
2,1–2,3 kn. El margen real, una vez sumados portones, cables y boyas, se analiza en
{doc}`19_ventana_velocidad`.
