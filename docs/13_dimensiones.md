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

# Dimensiones de la red

```{code-cell} ipython3
:tags: [remove-cell]
import sys, pathlib, math
sys.path.insert(0, str(pathlib.Path.cwd().parent))
import numpy as np
import matplotlib.pyplot as plt
from tests.golden_utils import golden
import _plots_t1 as P
P.setup_style()
```

## Propósito

Las dimensiones principales —largo de la **lima** (relinga superior) y del **burlón** (relinga
inferior), largo total, circunferencia de la boca— son las que el armador reconoce y las que usan los
métodos de resistencia, las aberturas y el aparejo. Esta etapa las deriva de los paños
({doc}`11_panos_y_cortes`): primero arma las relingas pieza por pieza (Martini {cite:p}`martini`),
después mide largos y circunferencias, y por último compara las proporciones de la red con las de
redes de referencia (Nomura {cite:p}`nomura1981`) y con el factor de largo de Fujiishi
{cite:p}`fujiishi`.

## Teoría

### Relingas por piezas (Martini)

Cada relinga se compone de dos piezas de ala iguales y una pieza central, la **bocana**. La pieza de
ala de la lima es el borde cortado de la punta de ala y del ala superior, que en los cortes de ala
mide aproximadamente su alto a malla estirada:

$$
\ell_{\text{ala}} = \frac{(N_A + N_C)\,m_L}{1000},
$$ (eq-lima-ala)

y la bocana es la mitad de lo que el borde de boca del square excede a los dos bordes de pegadura de
las alas:

$$
\ell_{\text{boc}} = \frac{T_E\,m_{L,E} - 2\,T_C\,m_{L,C}}{2000}.
$$ (eq-lima-bocana)

En el burlón, la pieza de ala suma además la segunda sección del ala inferior (F) y la bocana se mide
sobre el primer cuerpo del vientre. Cada pieza se corrige por un **embando** $E$ —la relación entre
el largo del cabo y el del paño que se arma sobre él— y la relinga es

$$
L_{\text{relinga}} = 2\,E_{\text{ala}}\,\ell_{\text{ala}} + E_{\text{boc}}\,\ell_{\text{boc}},
$$ (eq-relinga)

con $E_{\text{ala}} = 1{,}05$ (el cabo es un 5 % más largo que el borde en patas, que trabaja tenso y en
diagonal) y $E_{\text{boc}} = 0{,}83$ (el borde de mallas de la bocana se arma recogido sobre el cabo).
Para la A-3: lima $= 2\cdot 13{,}104 + 2{,}49 = 28{,}70$ m y burlón $= 2\cdot 15{,}624 + 2{,}14 =
33{,}39$ m. El burlón es más largo que la lima: la lima avanza sobre el burlón (el square forma una
visera) para que el pez que se levanta al paso del burlón no escape por arriba.

### Largos y circunferencias

El **largo total** $b$ es la suma de los altos estirados de los paños del vientre, bolsa incluida
(42,68 m en la estándar, 41,68 m en la modificada); el largo sin bolsa $L$ (32,68 m) es la del dorso.
La **circunferencia de pesca** es el perímetro estirado de la boca del cuerpo, dorso más vientre:

$$
a = FC = \frac{(T_{D1} + T_{V1})\,m_L}{1000} = \frac{(372 + 372)\cdot 60}{1000} = 44{,}64\ \text{m}.
$$ (eq-fc)

Es la medida de tamaño que usan las fórmulas japonesas de resistencia y las de abertura vertical por
porcentaje. Su cociente con el largo del cuerpo (2,51 en la A-3) indica si la red es "corta y
ancha" o "larga y estrecha".

### Factor de largo (Fujiishi)

Fujiishi propone controlar la coherencia entre lima, burlón y square con

$$
F_L = \frac{L_{\text{lima}} + 2\,N_E\,m_{L,E}/1000}{L_{\text{burlón}}} ,
$$ (eq-fujiishi)

es decir, la lima más dos veces el alto del square (la visera, ida y vuelta) frente al burlón.
$F_L \approx 1$ indica que la visera compensa exactamente la diferencia de largo entre relingas; la
A-3 da 1,006.

### Proporciones de Nomura

Nomura tabula, para distintos tipos de red, las relaciones adimensionales entre lima $l$, burlón $m$,
largo total $b$, circunferencia $a$, ala superior $c$, ala inferior $d$, dorso $e$ y bolsa $f$:

$$
\frac{l}{m},\ \frac{l}{b},\ \frac{m}{b},\ \frac{a}{b},\ \frac{c}{b},\ \frac{d}{b},\ \frac{e}{b},\
\frac{f}{b},\ \frac{d-c}{b}.
$$ (eq-nomura-prop)

Compararlas con las de redes probadas del mismo tipo (aquí, "red de fondo, 2 caras") es un control
rápido de diseño: una proporción muy alejada señala una pieza desproporcionada.

## Coeficientes

| Magnitud | Valor | Unidad | Fuente | Celda del Excel |
|---|---|---|---|---|
| Embando de las alas | 1,05 | — | Martini | `Dim!C142`, `C150` |
| Embando de la bocana | 0,83 | — | Martini | `Dim!G142`, `G150` |
| Embando de la punta de ala (refuerzo) | 1 | — | — | `Dim!C157` |
| Alto y mallero del square | 40 / 60 | mallas / mm | plano | `Dim!F85:F86` |
| Proporciones de referencia | fila "Red de Fondo, 2 caras" | — | Nomura | `Tab!A16:L16` |

## Equivalencia Excel ↔ `trawlkit`

| Celda(s) | Contenido | Función |
|---|---|---|
| `Dim!C140`, `F140` | Piezas de la lima | `headrope_wing_piece_m`, `headrope_bosom_piece_m` |
| `Dim!C148`, `F148` | Piezas del burlón | `footrope_wing_piece_m`, `footrope_bosom_piece_m` |
| `Dim!C143`, `G143`, `C151`, `G151` | Piezas corregidas | `trawlkit.dimensions.corrected_piece_m` |
| `Dim!F45` | Lima | `trawlkit.dimensions.headrope_length_m` |
| `Dim!F46` | Burlón | `trawlkit.dimensions.footrope_length_m` |
| `Dim!F47:F54` | Largos por plan y pieza | `trawlkit.dimensions.compute` |
| `Dim!F49`, `D97` | Circunferencia máxima y de pesca | `max_circumference_m`, `fishing_circle_m` |
| `Dim!D89` | Factor de largo | `trawlkit.dimensions.length_factor` |
| `Dim!D103`, `D109` | Largo del cuerpo, FC/cuerpo | `trawlkit.dimensions.fc_body_ratio` |
| `Dim!C124:E132` | Proporciones de Nomura | `nomura_ratios`, `load_nomura_reference` |
| `Dim!C155`, `Cab!J5` | Refuerzo de puntas de ala | `wingtip_reinforcement_m`, `wingtip_reinforcement_rope_m` |

## Supuestos y límites

* **Burlón truncado** (`footrope_mid_truncation`, `Dim!F46`). La fórmula aplica `MID()` a números:
  15,624 → "15.6" y 2,1414 → "2.1", de modo que el libro usa **33,3 m** en lugar de **33,389 m**. La
  diferencia (−0,27 %) se propaga a todo lo que usa el nombre `Burlon`: el factor de Fujiishi, las
  proporciones de Nomura, Tauti (burlón), la DPA geométrica y el lastre. Además depende de la
  configuración regional: con coma decimal `MID` devolvería otra cosa.
* **Largo modificado** (`mod_length_wrong_rows`, `Dim!G48`). La columna de la red modificada suma
  filas del plan inferior en vez del dorso; en la A-3 ambos planos miden 32,68 m y no cambia el número.
* **Errata de referencia** (`nomura_ratio_typo`). En la tabla de Nomura, dos filas tienen $a/b = 10{,}6$
  donde corresponde 1,06; no afecta a la fila usada aquí.
* Las relingas por piezas suponen alas con borde en patas y bocana en mallas; los embandos 1,05 y 0,83
  son valores prácticos, no resultado de un equilibrio de fuerzas. Las proporciones de Nomura son un
  control estadístico, no un criterio de optimalidad.

## Ejemplo ejecutable

```{code-cell} ipython3
from trawlkit import Compat
from trawlkit.io import load_net
from trawlkit.dimensions import compute

G = "dimensiones_de_la_red"
dx = compute(load_net("fao_a3_standard"), compat=Compat.EXCEL, modified=False)
dc = compute(load_net("fao_a3_standard"), compat=Compat.CORRECTED, modified=False)

checks = {
    "headrope_m": dx.headrope_m,
    "footrope_m": dx.footrope_m,
    "headrope_wing_corrected_m": dx.headrope.wing_corrected_m,
    "footrope_bosom_corrected_m": dx.footrope.bosom_corrected_m,
    "total_length_belly_std_m": dx.total_length_m,
    "fishing_circle_m": dx.fishing_circle_m,
    "body_length_m": dx.body_length_m,
    "length_factor": dx.length_factor,
    "fc_body_ratio": dx.fc_body_ratio,
}
for key, value in checks.items():
    assert math.isclose(value, golden(G, key), rel_tol=1e-6), key
for a, b in zip(dx.nomura_ratios.values(), golden(G, "nomura_ratio_fao_a3")):
    assert math.isclose(a, b, rel_tol=1e-6)

labels = {"headrope_m": "Lima [m]", "footrope_m": "Burlón [m]",
          "total_length_m": "Largo total con bolsa b [m]",
          "body_length_no_bag_m": "Largo sin bolsa L [m]",
          "fishing_circle_m": "Circunferencia de pesca a [m]",
          "length_factor": "Factor de largo (Fujiishi)",
          "fc_body_ratio": "FC / largo del cuerpo"}
P.md_table(["Magnitud", "Excel", "Corregido"],
           [[lab, P.fmt(getattr(dx, k), 4), P.fmt(getattr(dc, k), 4)]
            for k, lab in labels.items()])
```

```{code-cell} ipython3
:tags: [hide-input]
fig, ax = plt.subplots(figsize=(9.2, 2.6))
for k, (name, rope) in enumerate((("Lima", dc.headrope), ("Burlón", dc.footrope))):
    w, b = rope.wing_corrected_m, rope.bosom_corrected_m
    left = 0.0
    for part, length, colour in (("ala", w, P.SERIES[0]), ("bocana", b, P.SERIES[1]),
                                 ("ala", w, P.SERIES[0])):
        ax.barh(k, length - 0.06, left=left + 0.03, height=0.5, color=colour)
        ax.text(left + length / 2, k, P.fmt(length, 2), ha="center", va="center", fontsize=8.5,
                color="white" if colour == P.SERIES[0] else P.INK)
        left += length
    ax.annotate(f"{P.fmt(left, 3)} m", xy=(left, k), xytext=(6, 0), textcoords="offset points",
                va="center", fontsize=9, color=P.INK)
ax.set_yticks([0, 1], ["Lima", "Burlón"])
ax.invert_yaxis()
ax.set_xlim(0, 37)
ax.set_xlabel("Largo de la relinga, piezas corregidas por el embando [m]")
ax.grid(axis="y", visible=False)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=P.SERIES[0], label="Ala (embando 1,05)"),
                   Patch(color=P.SERIES[1], label="Bocana (embando 0,83)")],
          loc="lower right", ncol=2, bbox_to_anchor=(1, 1.0))
fig.tight_layout()
plt.show()
```

Composición de las relingas (valores corregidos, sin el truncado de `MID`). Las alas son casi todo el
largo; la bocana del burlón es más corta que la de la lima porque el vientre es más estrecho en la
boca que el square.

```{code-cell} ipython3
:tags: [hide-input]
import csv
from trawlkit.io.loader import DATA_DIR
from trawlkit.dimensions import NOMURA_LABELS

with open(DATA_DIR / "reference" / "nomura_proportions.csv", encoding="utf-8") as fh:
    ref_rows = [r for r in csv.DictReader(fh) if r["net_type"] == "Red de Fondo, 2 caras"]
labels = [lab for lab, _ in NOMURA_LABELS]
lo = [min(float(r[col]) for r in ref_rows) for _, col in NOMURA_LABELS]
hi = [max(float(r[col]) for r in ref_rows) for _, col in NOMURA_LABELS]
a3 = [dc.nomura_ratios[lab] for lab in labels]

fig, ax = plt.subplots(figsize=(9.2, 4.0))
y = np.arange(len(labels))
for k in y:
    ax.plot([lo[k], hi[k]], [k, k], color=P.BLUE_150, lw=9, solid_capstyle="round", zorder=1)
ax.scatter(lo + hi, list(y) * 2, s=28, color=P.BLUE_300, zorder=2,
           label="Referencia Nomura (red de fondo, 2 caras)")
ax.scatter(a3, y, s=64, color=P.SERIES[1], edgecolor=P.SURFACE, linewidth=2, zorder=3,
           label="FAO A-3 estándar")
for k, val in enumerate(a3):
    ax.annotate(P.fmt(val, 2), xy=(val, k), xytext=(0, 9), textcoords="offset points",
                ha="center", fontsize=8, color=P.INK_2)
ax.set_yticks(y, [f"${lab}$" if lab != "(d-c)/b" else "$(d-c)/b$" for lab in labels])
ax.invert_yaxis()
ax.set_xlabel("Proporción (adimensional)")
ax.grid(axis="y", visible=False)
ax.legend(loc="lower right")
fig.tight_layout()
plt.show()
```

Frente a las dos redes de fondo de dos caras de la tabla de Nomura (banda azul), casi todas las
proporciones de la A-3 caen fuera del rango, y lo hacen de forma coherente: la lima es larga
($l/m = 0{,}86$ contra 0,71–0,74; $l/b$ y $c/b$ por encima) y el burlón y el ala inferior cortos
($m/b$, $d/b$ por debajo), de modo que la diferencia de alas $(d-c)/b = 0{,}06$ es la mitad de la de
referencia. Es una red de visera corta, con poco avance de la lima sobre el burlón; el dorso y la
bolsa también son relativamente cortos. La circunferencia relativa $a/b$ (1,05) queda apenas por
debajo de lo habitual. Nada de esto es un error —la A-3 es un diseño FAO probado para buques
pequeños—, pero explica por qué conviene vigilar su abertura vertical y el escape por encima de la
lima ({doc}`16_aberturas`).

## Ejercicios

Del banco del modo docente, con los datos del libro. En la app, el modo «Aula UTN» los genera con
otros datos y los corrige ({doc}`38_docentes`).

```{code-cell} ipython3
:tags: [remove-input]
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path.cwd()))
import _exercises
_exercises.section("13_dimensiones")
```
