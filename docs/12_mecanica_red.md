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

# Mecánica de la red

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

La resistencia hidrodinámica de una red depende, ante todo, de **cuánto hilo** enfrenta al agua y de
**cuánta superficie** ocupa el paño una vez armado. Esta etapa resume la red en cuatro magnitudes: el
índice de filtración $d/l$, la superficie sólida $S_s$, la superficie de trabajo $S_t$ y su cociente,
la solidez. Añade el peso de la red en aire y en agua, que interviene en el lastre. Son las entradas
directas de los trece métodos de resistencia ({doc}`14_resistencia`) y se calculan para las dos
variantes de la red: la **estándar** (bolsa de 40 mm) y la **modificada** para crustáceos (bolsa
I' de 30 mm, superior e inferior).

La hoja no trabaja con paneles individuales sino con **filas de paño**: una por letra (A+B, C, E, G,
H, D, F, I, J o I'), con la cantidad de paneles iguales de cada fila.

## Teoría

### Índice de filtración

El cociente entre el diámetro del hilo y el tamaño de malla mide qué fracción de la malla está
ocupada por hilo. Para la red completa el libro usa la razón de sumas sobre las filas de paño

$$
\frac{d}{l} = \frac{\sum_i d_i}{\sum_i m_{L,i}} ,
$$ (eq-dl)

sin ponderar por superficie ni por cantidad de paneles. En la A-3 estándar vale
$11{,}49/540 = 0{,}0213$; las filas varían entre 0,017 (alas de 80 mm) y 0,034 (bolsa de 40 mm). Es
la variable de las fórmulas japonesas de resistencia (Tauti, Koyama, Hamuro): a igual tamaño de red,
la resistencia crece casi proporcionalmente a $d/l$.

### Superficie sólida

La superficie que el hilo proyecta es el producto de su largo total por su diámetro. Un paño de
$N$ mallas de alto y bordes $T_1$, $T_2$ tiene, a malla estirada, un largo $L = N\,m_L/1000$ [m] y
contiene $\approx (T_1+T_2)\,N$ patas de $m_L/2$ en cada sentido, de donde

$$
S_s = \frac{L\,d\,(T_1 + T_2)}{1000}\,n_p\quad[\mathrm{m^2}],
$$ (eq-ss)

con $d$ en mm y $n_p$ la cantidad de paneles iguales (FAO). Es equivalente a $S_s = 2\,d\,m_L\,n$
con $n$ el número de mallas: cada malla aporta dos veces su largo estirado de hilo. No incluye los
nudos. $S_s$ es la variable de las fórmulas europeas (Reid, Robertson, MacLennan, Aberdeen).

### Superficie de trabajo y solidez

La superficie de trabajo es la del paño armado ({eq}`eq-st-pano` en {doc}`11_panos_y_cortes`):

$$
S_t = \tfrac12\,U_1 U_2\,m_L^2\,(T_1+T_2)\,N\,n_p\quad[\mathrm{m^2}],\ m_L\ \text{en m}.
$$ (eq-st)

El cociente

$$
\sigma = \frac{S_s}{S_t} = \frac{2\,(d/m_L)}{U_1U_2}
$$ (eq-solidez)

es la **solidez** (Pérez Águila {cite:p}`perezaguila2010`): la fracción del área armada tapada por
hilo; $1-\sigma$ es el coeficiente de filtrado. Para $d/m_L \approx 0{,}02$ y $U_1U_2 = 0{,}35$,
$\sigma \approx 0{,}12$; un paño más cerrado ($U_1$ pequeño) o de hilo más grueso es más sólido, filtra
peor y forma más presión delante de la bolsa.

### Peso de la red

El libro pesa el hilo en dos pasos (métodos A y B). Primero el peso de un paño de referencia de
$T = 500$ por $N = 100$ mallas:

$$
S_N = \left(T\,\frac{m_L}{1000}\,2N\right)\pi\left(\frac{d}{2000}\right)^2\rho\quad[\mathrm{kg}],
$$ (eq-peso-ref)

largo de hilo por sección por densidad. Después se escala al paño real por la relación de mallas,
$W = \frac{(T_1+T_2)/2}{T}\cdot\frac{N_p}{N}\cdot S_N$, y el peso en agua es
$W_a = W\,(1 - \rho_w/\rho)$ con $\rho_w = 1025$ kg/m³. Para poliamida ($\rho = 1140$ kg/m³) el
peso en agua es apenas el 10 % del peso en aire.

## Coeficientes

| Magnitud | Valor | Unidad | Fuente | Celda del Excel |
|---|---|---|---|---|
| Densidad del agua de mar (fuerzas) | 1024 | kg/m³ | — | `Mec!O127` |
| Densidad del agua (pesos) | 1025 | kg/m³ | — | `Mec!P98` |
| Paño de referencia $T \times N$ | 500 × 100 | mallas | — | `Mec!L98:M98` |
| π en las fórmulas de peso | 3,1416 | — | — | `Mec!N98`, `P!L55` |
| Densidad del polímero PA | 1140 | kg/m³ | catálogo | `Tab!A35:I37` |
| $U_1$ por fila | 0,38 / 0,23 | — | plano | `Mec!K56:K64` |

## Equivalencia Excel ↔ `trawlkit`

| Celda(s) | Contenido | Función |
|---|---|---|
| `Mec!K6:K14` | $d/m_L$ por fila | `trawlkit.net.filtration_per_row` |
| `Mec!K15`, `K17` | $d/l$ de la red | `trawlkit.net.filtration_index` |
| `Mec!M29:N37` | Largo y $S_s$ por fila | `panel_length_m`, `solid_surface_m2` |
| `Mec!N38`, `N40`, `O30:O37` | $S_s$ total y por plano | `trawlkit.net.analyse`, `split_by_plane` |
| `Mec!K56:M64`, `M65`, `M67` | $U_1$, $U_2$, $S_t$ | `trawlkit.net.working_surface_m2` |
| `Mec!E75:M79` | Solidez y filtrado | `trawlkit.net.solidity`, `filtering_coefficient` |
| `Mec!N98:P109` | Pesos (métodos A y B) | `reference_twine_weight_kg`, `panel_weight_air_kg`, `weight_in_water_kg` |
| `Mec!I110:I113` | Peso por plano | `trawlkit.net.split_by_plane` |
| hoja completa | — | `trawlkit.net.analyse(spec, compat)` |

## Supuestos y límites

* **Bolsa estándar con el lado equivocado** (`codend_minor_side_uses_depth`, `Mec!K36:K37`). La
  celda del lado menor de la bolsa superior I apunta al alto $N = 200$ en vez de al borde $T_2 = 113$,
  y la bolsa inferior J la copia. Así las bolsas cuentan $(113 + 200)$ mallas de borde en lugar de
  $(113 + 113)$ y la superficie sólida de la red estándar sube de **38,75 a 40,90 m²** (+5,5 %); también
  aumentan su $S_t$ y su peso. Como la RN de diseño (Aberdeen) es proporcional a $S_s$, el libro
  sobreestima la resistencia de la red estándar en ese mismo 5,5 %. La bolsa modificada I' está bien
  referenciada.
* **Doble conteo en $d/l$ modificado** (`filtration_double_count`, `Mec!J17`). La suma de malleros de
  la red modificada incluye dos veces los 30 mm de la bolsa I': $\sum m_L = 520$ en vez de 490 y
  $d/l = 0{,}01946$ en lugar de 0,02065 (−5,8 %). Afecta a todos los métodos de resistencia basados
  en $d/l$ para la variante modificada.
* **Densidad del hilo** (`twine_density_units`). Los pesos usan la "densidad" de `P!L55`
  (≈1152 kg/m³), que no tiene unidades de densidad; el coeficiente de peso en agua resultante (0,11)
  es parecido por casualidad al 0,10 de la poliamida.
* **Pesos sin cantidad de paneles** (`net_weight_ignores_panel_count`, `Mec!O107`, `O109`). El peso
  total suma las filas sin multiplicar por los paneles de cada una (alas izquierda y derecha, planos
  alto y bajo): con la densidad del libro, multiplicar cada fila por su cantidad llevaría los 28,3 kg
  a 45,4 kg (+60 %). El modo corregido multiplica cada fila por su cantidad (en aire, en agua y en el
  reparto por plano), igual que ya hacen $S_s$ y $S_t$; el modo Excel lo reproduce.
* $d/l$ global como cociente de sumas da el mismo peso a una fila de dos paneles pequeños que al
  cuerpo; una media ponderada por $S_t$ sería más representativa, pero los coeficientes de las
  fórmulas de resistencia se ajustaron con la definición del libro.

## Ejemplo ejecutable

```{code-cell} ipython3
from trawlkit import Compat
from trawlkit.io import load_net
from trawlkit.net import analyse

G = "mecanica_de_la_red"
std_x = analyse(load_net("fao_a3_standard"), Compat.EXCEL)
mod_x = analyse(load_net("fao_a3_modified"), Compat.EXCEL)
std_c = analyse(load_net("fao_a3_standard"), Compat.CORRECTED)
mod_c = analyse(load_net("fao_a3_modified"), Compat.CORRECTED)

checks = {
    "filtration_index_std": std_x.filtration_index,
    "filtration_index_mod": mod_x.filtration_index,
    "solid_surface_std_m2": std_x.solid_surface_m2,
    "solid_surface_mod_m2": mod_x.solid_surface_m2,
    "working_surface_std_m2": std_x.working_surface_m2,
    "solidity_std": std_x.solidity,
    "net_weight_air_std_kg": std_x.weight_air_kg,
    "net_weight_water_std_kg": std_x.weight_water_kg,
}
for key, value in checks.items():
    assert math.isclose(value, golden(G, key), rel_tol=1e-6), key
for row, ref in zip(std_x.rows, golden(G, "solid_surface_per_panel_m2")):
    assert math.isclose(row.solid_surface_m2, ref, rel_tol=1e-6), row.row.id

cases = (std_x, std_c, mod_x, mod_c)
show = [("d/l", "filtration_index", 5), ("Sₛ [m²]", "solid_surface_m2", 2),
        ("Sₜ [m²]", "working_surface_m2", 1), ("Solidez Sₛ/Sₜ", "solidity", 4),
        ("Peso en aire [kg]", "weight_air_kg", 2),
        ("Peso en agua [kg]", "weight_water_kg", 2)]
P.md_table(["Magnitud", "Estándar (Excel)", "Estándar (corregido)",
            "Modificada (Excel)", "Modificada (corregido)"],
           [[lab, *(P.fmt(getattr(g, attr), nd) for g in cases)]
            for lab, attr, nd in show])
```

Las erratas se ven en la tabla: entre "Excel" y "corregido", la red estándar cambia en $S_s$ y
$S_t$ (bolsas I/J) y la modificada en $d/l$ (doble conteo). Los pesos cambian en las dos por dos
causas que van en sentido contrario: por panel son un 20–30 % menores porque usan la densidad
aparente correcta del hilo trenzado (≈868 kg/m³ en lugar de 1152; con ella el peso del paño de
referencia es exactamente su largo de hilo dividido por el rendimiento), pero el total cuenta todos
los paneles de cada fila (`net_weight_ignores_panel_count`). El resultado neto es un peso corregido
de unos 33 kg en aire para la red estándar y 35 kg para la modificada, frente a los 28 y 23 kg del
libro.

```{code-cell} ipython3
:tags: [hide-input]
ids = [g.row.id for g in std_x.rows]
y = np.arange(len(ids))
h = 0.36
fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.4), sharey=True)
for ax, attr, title, unit in (
    (axes[0], "solid_surface_m2", "Superficie sólida $S_s$", "[m²]"),
    (axes[1], "working_surface_m2", "Superficie de trabajo $S_t$", "[m²]"),
):
    vc = [getattr(g, attr) for g in std_c.rows]
    vx = [getattr(g, attr) for g in std_x.rows]
    ax.barh(y - h / 2 - 0.02, vc, height=h, color=P.SERIES[0], label="Corregido")
    ax.barh(y + h / 2 + 0.02, vx, height=h, color=P.SERIES[1], label="Excel")
    for k, (a, b) in enumerate(zip(vc, vx)):
        if abs(a - b) > 1e-9:
            ax.annotate(f"{P.fmt(a, 2)} → {P.fmt(b, 2)}", xy=(b, k + h / 2), xytext=(5, 0),
                        textcoords="offset points", va="center", fontsize=8, color=P.INK_2)
    ax.set_title(title)
    ax.set_xlabel(f"Superficie por fila de paño {unit}")
    ax.grid(axis="y", visible=False)
    ax.margins(x=0.22)
axes[0].set_yticks(y, ids)
axes[0].invert_yaxis()
axes[0].set_ylabel("Fila de paño (red estándar)")
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", ncol=2)
fig.tight_layout(rect=(0, 0.06, 1, 1))
plt.show()
```

Por fila de paño, el cuerpo G concentra el 38 % de la superficie sólida y el 45 % de la de trabajo:
es la pieza que más pesa en la resistencia. Las únicas filas que cambian entre modos son las bolsas
I y J (errata `codend_minor_side_uses_depth`); en ellas el libro suma 2,15 m² de hilo que no existen.
Por su $U_1 = 0{,}23$, las bolsas tienen poca superficie de trabajo para su superficie sólida, es
decir, la mayor solidez de la red (≈0,31 contra ≈0,10 de las alas).

## Ejercicios

Del banco del modo docente, con los datos del libro. Con la CLI (`trawlkit exercises`) se generan
con otros datos y se corrigen.

```{code-cell} ipython3
:tags: [remove-input]
import pathlib as _pl, sys as _sys
_sys.path.insert(0, str(_pl.Path.cwd()))
import _exercises
_exercises.section("12_mecanica_red")
```
