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

# Resistencia de la red

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

La resistencia hidrodinámica de la red, $R_N$, es el término dominante de la demanda de tiro
({eq}`eq-pot-demanda` en {doc}`10_potencia`) y el número del que dependen casi todas las etapas
siguientes: la resistencia de los portones se fija como fracción del tiro, la abertura horizontal de
Fridman y su flotación usan $R_N$, el cable se dimensiona con la resistencia total y la ventana de
velocidad compara $R_N(v)$ con el tiro disponible ({doc}`19_ventana_velocidad`).

No hay una fórmula universal. Cada autor ajustó coeficientes sobre un tipo de red —de fondo o
pelágica, de dos o de cuatro caras, de poliamida (PA) o de polietileno (PE)— y con una variable de
tamaño distinta: la circunferencia de la boca, una relinga, la superficie sólida $S_s$ o la de
trabajo $S_t$. El libro evalúa trece métodos para las dos variantes de la red, de 1 a 5 nudos, y
adopta uno, **Aberdeen demersal**, como $R_N$ de diseño. Este capítulo presenta los trece, su dominio
y por qué esa elección es razonable.

## Teoría

En todas las fórmulas $R_N$ está en toneladas-fuerza; $v$ en m/s salvo donde se indica $v_{kn}$ (nudos,
con 1 kn = 0,5144 m/s). Las variables geométricas vienen de {doc}`12_mecanica_red` y
{doc}`13_dimensiones`: $d/l$, $S_s$, $S_t$, circunferencia de pesca $a$, largo con bolsa $b$ y sin
bolsa $L$, lima, burlón y ángulo de ataque $\alpha$.

### Escuela japonesa: tamaño de la red y $d/l$

La ley de semejanza de Tauti establece que la resistencia de redes geométricamente semejantes es
proporcional a $d/l$, al cuadrado de una dimensión lineal y al cuadrado de la velocidad. Tauti, Nomura
y Shu {cite:p}`tauti1974` la ajustaron para redes de arrastre de dos caras con la circunferencia de la
boca y un exponente de velocidad menor que 2 (la red se deforma y se alinea con el flujo al acelerar):

$$
R_N = \frac{27\,(d/l)\,a^2\,v^{1{,}45}}{1000}.
$$ (eq-rn-tns)

La forma original de Tauti usa una relinga $\ell$ (lima o burlón) como dimensión de referencia:

$$
R_N = \frac{25\,(d/l)\,\ell^2\,v^2}{1000}.
$$ (eq-rn-tauti)

Koyama {cite:p}`koyama1974` reemplaza el cuadrado de una dimensión por el producto circunferencia ×
largo con bolsa, y en una versión posterior {cite:p}`koyama1984` por circunferencia × largo sin bolsa,
con la velocidad en nudos:

$$
R_N^{(1974)} = \frac{16\,(d/l)\,a\,b\,v^2}{1000}, \qquad
R_N^{(1984)} = \frac{8\,(d/l)\,a\,L\,v_{kn}^2}{1000}.
$$ (eq-rn-koyama)

Hamuro {cite:p}`hamuro` parte de la resistencia de un paño plano inclinado un ángulo $\alpha$ respecto
del flujo:

$$
R_N = \frac{191\,(d/l)\,v^2\,S_t\,\lvert\sin\alpha\rvert}{1000}.
$$ (eq-rn-hamuro)

La columna "Nomura" de la hoja, $T = 7{,}2\,\mathrm{NHP}/v$ {cite:p}`nomura1981`, **no es una
resistencia** sino el tiro disponible de un buque de 150 o 180 NHP; se muestra en la tabla del libro
pero se excluye de la comparación.

### Escuela europea: superficie sólida

Los laboratorios escoceses midieron redes a escala real y encontraron que la superficie sólida del
hilo $S_s$ explica mejor la resistencia que cualquier dimensión de la boca. Reid {cite:p}`reid1977`
para redes pelágicas y Robertson {cite:p}`robertson1981` para semipelágicas proponen formas
racionales en nudos:

$$
R_N^{\text{Reid}} = \frac{v_{kn}^2\,S_s}{54{,}72\,v_{kn} + 115{,}2}, \qquad
R_N^{\text{Rob}} = \frac{v_{kn}^2\,S_s}{66{,}18\,v_{kn} + 41{,}5}.
$$ (eq-rn-reid)

MacLennan {cite:p}`maclennan1981` ajustó redes demersales de PE, con una parte independiente de la
velocidad (el rozamiento de las partes que arrastran sobre el fondo) y otra cuadrática:

$$
R_N^{\text{MacL}} = \frac{S_s\,(61{,}2 + 46{,}6\,v_{kn}^2)}{(1 + 0{,}0641\,v_{kn})\,9807}.
$$ (eq-rn-maclennan)

Las fórmulas del Marine Laboratory de Aberdeen {cite:p}`aberdeen` para redes demersales (PE) y
pelágicas (nylon) son

$$
R_N^{\text{Ab,dem}} = S_s\,\frac{0{,}00624 + 0{,}00475\,v_{kn}^2}{1 + 0{,}0641\,v_{kn}}, \qquad
R_N^{\text{Ab,pel}} = S_s\,\frac{0{,}00868\,v_{kn}^2}{1 + 0{,}00475\,v_{kn}}.
$$ (eq-rn-aberdeen)

Nótese que $61{,}2/9807 = 0{,}00624$ y $46{,}6/9807 = 0{,}00475$: **Aberdeen demersal y MacLennan son
la misma fórmula**, una en newtons y otra en toneladas, y sólo difieren por el redondeo de los
coeficientes (0,02 %).

### Fridman y Dickson: superficie de trabajo y boca

Fridman {cite:p}`fridman1973` corrige el coeficiente de arrastre de un paño por el ángulo de ataque y
por el índice de filtración (el término $d/l - 0{,}01$ crece con paños más tupidos):

$$
R_N = \frac{\left[1{,}8 + 2\alpha\,(d/l - 0{,}01)\right] S_t\,v^2}{1000},
$$ (eq-rn-fridman)

con $\alpha$ en grados, tal como lo usa la hoja. Dickson {cite:p}`dickson` expresa la resistencia en
función del área de la boca, abertura horizontal (AH) por vertical (AV), con $S_t$ en pies cuadrados:

$$
R_N = \frac{1}{125}\,S_t^{\,\mathrm{ft^2}}\,(d/l)\,\frac{1 + 2\cdot 6{,}6\,\mathrm{AH}\,\mathrm{AV}}{S_t^{\,\mathrm{m^2}}}.
$$ (eq-rn-dickson)

Dickson no contiene la velocidad explícitamente; depende de ella sólo a través de AH y AV, que el
libro toma de Fridman ({doc}`16_aberturas`). Como la AV de Fridman disminuye al acelerar más rápido de
lo que crece la AH, Dickson da una resistencia **decreciente** con la velocidad por encima de 1,5 kn:
no es aplicable fuera del punto de diseño para el que se calcularon las aberturas.

### Dominio de validez

| Método | Variable | Tipo de red de origen | Material | $v$ |
|---|---|---|---|---|
| Tauti–Nomura–Shu | $d/l$, $a$ | arrastre de fondo, 2 caras | PA | m/s |
| Tauti (lima/burlón) | $d/l$, relinga | redes semejantes en general | — | m/s |
| Koyama 1974 / 1984 | $d/l$, $a$, $b$ o $L$ | arrastre de fondo | PA | m/s / kn |
| Hamuro | $d/l$, $S_t$, $\alpha$ | paño plano inclinado | — | m/s |
| Reid | $S_s$ | pelágica | nylon | kn |
| Robertson | $S_s$ | semipelágica | — | kn |
| MacLennan | $S_s$ | fondo, 4 caras | PE | kn |
| Aberdeen demersal | $S_s$ | fondo (demersal) | PE | kn |
| Aberdeen pelágica | $S_s$ | pelágica | nylon | kn |
| Fridman | $d/l$, $S_t$, $\alpha$ | arrastre en general | — | m/s |
| Dickson | $d/l$, $S_t$, AH, AV | arrastre en general | — | (vía aberturas) |

### Por qué Aberdeen demersal es la $R_N$ de diseño

1. **Tipo de red.** La A-3 es una red de fondo; de las fórmulas basadas en $S_s$ —las que mejor
   representan la cantidad de hilo, incluido el de la bolsa—, Aberdeen demersal y MacLennan son las
   únicas ajustadas sobre redes demersales medidas a escala real. Reid, Robertson y Aberdeen pelágica
   provienen de redes que no tocan el fondo y carecen del término independiente de la velocidad.
2. **Posición en el abanico.** A 3 kn queda algo por encima de la mediana de los trece métodos (≈ 9 %),
   del lado conservador sin ser un extremo como Aberdeen pelágica o Koyama 1984.
3. **Contraste con la simulación.** Frente a la simulación DynamiT {cite:p}`dynamit` de la misma red
   ({doc}`32_validacion_dynamit`), Aberdeen demersal es entre un 15 y un 33 % mayor (más a baja velocidad);
   para dimensionar portones y cables es preferible ese sesgo a uno optimista.
4. **Límite reconocido.** Sus coeficientes son para PE; la A-3 es de PA, de hilo más fino a igual
   resistencia y con menor $S_s$. Aplicarla a PA es una extrapolación que el libro acepta porque el
   término dominante, $S_s$, ya contiene el diámetro real del hilo.

## Coeficientes

| Método | Coeficientes | Celda del Excel |
|---|---|---|
| Tauti–Nomura–Shu | 27; exponente 1,45 | `Res!D11:E19` |
| Tauti (lima / burlón) | 25 | `Res!D30:E38`, `L30:M38` |
| Koyama 1974 / 1984 | 16 / 8 | `Res!D74:E82`, `C91:D99` |
| Hamuro | 191 | `Res!D117:E125` |
| Nomura (tiro) | 7,2 | `Res!D132:E140` |
| Reid | 54,72; 115,2 | `Res!C154:D162` |
| Robertson | 66,18; 41,5 | `Res!C174:D182` |
| MacLennan | 61,2; 46,6; 0,0641; 9807 | `Res!C196:D204` |
| Aberdeen demersal | 0,00624; 0,00475; 0,0641 | `Res!C214:D222` |
| Aberdeen pelágica | 0,00868; 0,00475 | `Res!C237:D245` |
| Fridman | 1,8; 2; 0,01 | `Res!D258:E266` |
| Dickson | 1/125; 6,6; 10,76 ft²/m² | `Res!E282:F290` |

## Equivalencia Excel ↔ `trawlkit`

| Celda(s) | Contenido | Función |
|---|---|---|
| `Res!E4:E6`, `I25:I26`, … | Entradas | `trawlkit.drag.DragInputs` |
| `Res!D11` | Tauti–Nomura–Shu | `trawlkit.drag.tauti_nomura_shu` |
| `Res!D30`, `L30` | Tauti | `trawlkit.drag.tauti_rope` |
| `Res!D74`, `C91` | Koyama | `koyama_1974`, `koyama_1984` |
| `Res!D113`, `D117` | Hamuro | `hamuro_sin_alpha`, `hamuro` |
| `Res!D132` | Nomura (tiro) | `trawlkit.drag.nomura` |
| `Res!C154`, `C174`, `C196` | Reid, Robertson, MacLennan | `reid`, `robertson`, `maclennan` |
| `Res!C214`, `C237` | Aberdeen | `aberdeen_demersal`, `aberdeen_pelagic` |
| `Res!D258`, `E282` | Fridman, Dickson | `fridman`, `dickson` |
| `Res!A298:S326`, `A394:S422` | Resumen en t y kgf | `trawlkit.drag.drag_table`, `DragTable.kgf` |
| `Res!R302:R325`, `C326` | Promedios | `trawlkit.drag.average`, `method_average` |
| `Res!N302:N310` | $R_N$ de diseño | `DragTable.design_rn`, `DesignResult.drag.rn` |

## Supuestos y límites

* **Hamuro con el seno de grados** (`hamuro_sin_degrees`, `Res!D113`). La hoja calcula
  `ABS(SIN(DEGREES(α)))`: convierte 10,63 a "grados" (609,3) y evalúa el seno en radianes. Por pura
  casualidad el resultado (0,1891) está cerca del correcto $\sin 10{,}63° = 0{,}1845$ (+2,5 %).
  Además la variante modificada usa el $d/l$ de la estándar (`hamuro_mod_uses_std_dl`).
* **Reid con denominador fijo** (`reid_fixed_denominator`, `Res!C154:C162`). El denominador usa
  siempre la velocidad de la primera fila (1 kn): $54{,}72\cdot 1 + 115{,}2$. La curva resultante es
  una parábola pura que a 5 kn más que duplica a la fórmula correcta (6,0 t frente a 2,5 t).
* **Promedio contaminado** (`drag_average_pollution`, `Res!R302:R310`). La columna "promedio" incluye
  las dos columnas de Nomura, que son tiro disponible y no resistencia, y en la primera fila también la
  velocidad en m/s. A 1 kn el promedio del libro (554 kgf) duplica la media de los trece métodos de
  resistencia (264 kgf). `trawlkit.drag.average` en modo corregido promedia sólo `RN_METHODS`.
* **Arrastre de erratas previas.** Todos los métodos basados en $S_s$ heredan el +5,5 % de la bolsa
  estándar (`codend_minor_side_uses_depth`); Tauti (burlón) hereda el truncado del burlón y los de
  $d/l$ en la variante modificada, el doble conteo (ver {doc}`12_mecanica_red`).
* Ningún método modela la captura en la bolsa, el contacto del burlón con el fondo de forma explícita
  ni la deformación de la red a alta velocidad; todos son correlaciones empíricas válidas cerca de su
  base de datos.

## Ejemplo ejecutable

El caso completo en modo `Compat.EXCEL` (necesario para Dickson, que usa las aberturas de Fridman)
reproduce el resumen del libro método por método:

```{code-cell} ipython3
from trawlkit import Compat, DesignCase, run, drag
from trawlkit.io import load_doors, load_net, load_vessels

vessels = {v.id: v for v in load_vessels().vessels}

def case(compat):
    return run(DesignCase(
        net=load_net("fao_a3_standard"),
        net_modified=load_net("fao_a3_modified"),
        vessel=vessels["fao_a3_150hp"],
        class_vessels=(vessels["fao_a3_180hp"],),
        door=load_doors().doors[0],
        compat=compat,
    ))

def same(xs, ys):
    return all(math.isclose(a, b, rel_tol=1e-6) for a, b in zip(xs, ys, strict=True))

res_x, res_c = case(Compat.EXCEL), case(Compat.CORRECTED)
tx, tc = res_x.drag.table, res_c.drag.table
G = "resistencia_de_la_red"
for col in drag.SUMMARY_COLUMNS:
    for variant in ("std", "mod"):
        ref = golden(G, f"summary_{col}_{variant}_t")
        got = tx.variant(variant)[col]
        assert same(got, ref), (col, variant)
# promedio del libro (con la errata drag_average_pollution) y RN de diseño en kgf
assert same(res_x.drag.average.std, golden(G, "summary_average_std_t"))
assert same(res_x.drag.rn.std, golden(G, "summary_aberdeen_demersal_std_kgf"))
```

```{code-cell} ipython3
:tags: [hide-input]
NAMES = {"tauti_nomura_shu": "Tauti–Nomura–Shu", "tauti_headrope": "Tauti (lima)",
         "tauti_footrope": "Tauti (burlón)", "koyama_1974": "Koyama 1974",
         "koyama_1984": "Koyama 1984", "hamuro": "Hamuro", "reid": "Reid",
         "robertson": "Robertson", "maclennan": "MacLennan",
         "aberdeen_demersal": "Aberdeen demersal (diseño)",
         "aberdeen_pelagic": "Aberdeen pelágica", "fridman": "Fridman", "dickson": "Dickson"}
v = np.array(SPEEDS_KN)
kx, kc = tx.kgf, tc.kgf
dyn = golden(G, "summary_dynamit_std_kgf")
rows = []
for col in drag.RN_METHODS:
    x = kx.std[col]
    rows.append([NAMES[col], *(P.fmt(x[SPEEDS_KN.index(s)], 0) for s in (2.0, 3.0, 4.0)),
                 P.fmt(kc.std[col][SPEEDS_KN.index(3.0)], 0)])
rows.append(["*Promedio (Excel con Nomura; corregido sólo RN)*",
             *(P.fmt(res_x.drag.average.std[SPEEDS_KN.index(s)] * 1000, 0) for s in (2.0, 3.0, 4.0)),
             P.fmt(res_c.drag.average.std[SPEEDS_KN.index(3.0)] * 1000, 0)])
rows.append(["*DynamiT (simulación)*", *(P.fmt(dyn[SPEEDS_KN.index(s)], 0) for s in (2.0, 3.0, 4.0)), "—"])
P.md_table(["Método (red estándar)", "2 kn [kgf]", "3 kn [kgf]", "4 kn [kgf]", "3 kn corregido [kgf]"],
           rows)
```

```{code-cell} ipython3
:tags: [hide-input]
families = [
    ("Dimensiones y $d/l$", ["tauti_nomura_shu", "tauti_headrope", "tauti_footrope",
                             "koyama_1974", "koyama_1984"]),
    ("Superficie sólida $S_s$", ["reid", "robertson", "maclennan", "aberdeen_pelagic"]),
    ("Superficie de trabajo y boca", ["hamuro", "fridman", "dickson"]),
]
fig, axes = plt.subplots(1, 3, figsize=(10.5, 5.4), sharey=True)
design = kx.std["aberdeen_demersal"]
for ax, (title, cols) in zip(axes, families):
    for k, col in enumerate(cols, start=1):
        ls = (0, (4, 2)) if col == "maclennan" else "-"
        ax.plot(v, kx.std[col], color=P.SERIES[k], lw=1.8, ls=ls, label=NAMES[col], zorder=2)
    ax.plot(v, design, color=P.SERIES[0], lw=3, label="Aberdeen demersal (diseño)", zorder=3)
    ax.set_title(title)
    ax.set_xlabel("Velocidad [kn]")
    ax.set_xlim(1, 5)
    ax.set_ylim(0, 9000)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), fontsize=8.5, handlelength=1.8)
axes[0].set_ylabel("Resistencia de la red $R_N$ [kgf]")
fig.tight_layout()
plt.show()
```

Los trece métodos agrupados por la variable que usan, con la $R_N$ de diseño (azul, trazo grueso) como
referencia en cada panel. MacLennan (trazo discontinuo) queda exactamente bajo Aberdeen demersal. La
curva de Reid es la del libro, con el denominador fijo; la corregida queda por debajo de Robertson a
alta velocidad.

```{code-cell} ipython3
:tags: [hide-input]
i3 = SPEEDS_KN.index(3.0)
vals = sorted(((kx.std[c][i3], c) for c in drag.RN_METHODS), reverse=False)
fig, ax = plt.subplots(figsize=(9.2, 4.6))
y = np.arange(len(vals))
for k, (val, col) in enumerate(vals):
    is_design = col == "aberdeen_demersal"
    ax.plot([0, val], [k, k], color=P.GRID, lw=1, zorder=1)
    ax.scatter(val, k, s=80 if is_design else 46, color=P.SERIES[0] if is_design else P.BLUE_300,
               edgecolor=P.SURFACE, linewidth=2, zorder=3)
    ax.annotate(P.fmt(val, 0), xy=(val, k), xytext=(8, 0), textcoords="offset points",
                va="center", fontsize=8.5, color=P.INK if is_design else P.INK_2,
                fontweight="bold" if is_design else "normal")
med = float(np.median([val for val, _ in vals]))
for x0, lab, dx, ha in ((dyn[i3], "DynamiT", -4, "right"), (med, "mediana", 4, "left")):
    ax.axvline(x0, color=P.INK_2, lw=1, zorder=0)
    ax.annotate(lab, xy=(x0, len(vals) - 0.4), xytext=(dx, 0), textcoords="offset points",
                fontsize=8.5, color=P.INK_2, va="center", ha=ha)
ax.set_yticks(y, [NAMES[c] for _, c in vals])
ax.set_xlim(0, 3600)
ax.set_ylim(-0.7, len(vals) - 0.1)
ax.set_xlabel("$R_N$ a 3 kn, red estándar [kgf]")
ax.grid(axis="y", visible=False)
fig.tight_layout()
plt.show()
```

A la velocidad de diseño (3 kn) los métodos se extienden de 510 kgf (Dickson) a 3150 kgf (Aberdeen
pelágica), un factor de 6. Si se dejan de lado los que están fuera de su dominio —Dickson, Hamuro
(paño plano, sin bolsa), Aberdeen pelágica y Reid (pelágicas)—, el abanico se reduce a
1040–2240 kgf, un factor de 2, que es la incertidumbre honesta de una estimación empírica de
resistencia. La $R_N$ de diseño (1680 kgf) queda en el centro de ese abanico, algo por encima de su
mediana (1545 kgf), y un 26 % por encima de la simulación DynamiT (1331 kgf).

## Ejercicios

Del banco del modo docente, con los datos del libro. Con la CLI (`trawlkit exercises`) se generan
con otros datos y se corrigen.

```{code-cell} ipython3
:tags: [remove-input]
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path.cwd()))
import _exercises
_exercises.section("14_resistencia")
```
