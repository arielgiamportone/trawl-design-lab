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

# Paños de red y cortes

```{code-cell} ipython3
:tags: [remove-cell]
import sys, pathlib, math
sys.path.insert(0, str(pathlib.Path.cwd().parent))
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from tests.golden_utils import golden
import _plots_t1 as P
P.setup_style()
```

## Propósito

Una red de arrastre es un conjunto de **paños** trapezoidales cosidos entre sí. Cada paño queda
definido por su compostura (material, diámetro y título del hilo, tamaño de malla), por su número de
mallas en los dos bordes y en el alto, y por la forma en que se corta y se arma sobre las relingas.
Esta etapa traduce el plano de la red FAO A-3 {cite:p}`faocatalogue` en magnitudes geométricas: largos
estirados, superficie de trabajo, número de mallas y ángulo de los cortes. Todo lo que sigue
—superficies sólidas ({doc}`12_mecanica_red`), relingas ({doc}`13_dimensiones`) y resistencia
({doc}`14_resistencia`)— se construye sobre estos números.

## Teoría

### El hilo y la malla

La malla se mide **estirada**: $m_L$ es la distancia entre los centros de dos nudos opuestos con la
malla tirante (80, 60, 40 y 30 mm en la A-3). Cada malla tiene cuatro **patas** (barras) de largo
$m_L/2$. El hilo se caracteriza por su diámetro $d$ y por su título en **Rtex** (gramos por kilómetro
de hilo terminado); su inversa es el **rendimiento**

$$
r = \frac{10^6}{\mathrm{Rtex}}\quad [\mathrm{m/kg}],
$$ (eq-runnage)

781,25 m/kg para la poliamida (PA) R1280tex de 1,37 mm y 1052,6 m/kg para la R950tex de 1,16 mm.

### Geometría del paño

Con la convención del libro, $T_1$ y $T_2$ son las mallas de los dos bordes del paño y $N$ las mallas
de alto. El paño estirado es un trapecio cuyos lados miden

$$
L_{T} = \frac{T\,c_X\,m_L}{1000}, \qquad L_N = \frac{N\,c_Y\,m_L}{1000}\quad[\mathrm{m}],
$$ (eq-largo-estirado)

donde $c_X = 0{,}5$ y $c_Y = 1$ son los coeficientes "en el plano" con los que la hoja dibuja los
paños (bordes con la malla semiabierta, alto a malla estirada).

Al armar la red, la malla no trabaja estirada sino abierta. El **coeficiente de armado horizontal**
$U_1$ (*hanging ratio*) es la fracción del largo estirado que ocupa la malla a lo ancho; como las
patas no cambian de largo, la abertura vertical queda fijada por

$$
U_2 = \sqrt{1 - U_1^2}.
$$ (eq-u2)

La A-3 usa $U_1 = 0{,}38$ en alas, square y primer cuerpo, y $U_1 = 0{,}23$ en el segundo cuerpo y la
bolsa: la red se cierra hacia atrás para que la captura no escape. Con esos coeficientes, la
**superficie de trabajo** del paño armado (Prado) es la de un trapecio de mallas romboidales:

$$
S_t = U_1 U_2\,\frac{T_1 + T_2}{2}\,N\,\left(\frac{m_L}{1000}\right)^2\quad[\mathrm{m^2}].
$$ (eq-st-pano)

El producto $U_1U_2$ es máximo (0,5) con $U_1 = 0{,}707$, la malla cuadrada; con 0,38 vale 0,35 y con
0,23 vale 0,22. El **número de mallas** del paño, que sirve para presupuestar el paño, es

$$
n = (T_1 + T_2 - 1)(N - 0{,}5) + 0{,}5 .
$$ (eq-n-mallas)

### Cortes

Para pasar de un borde de $T_1$ mallas a otro de $T_2$ en $N$ mallas de alto hay que cortar el paño en
diagonal. Los cortes se combinan a partir de tres elementos: **N** (punto o nudo: avanza una malla en
alto sin cambiar el ancho), **T** (malla transversal: reduce una malla de ancho sin avanzar) y **B**
(barra o pata: avanza media malla en alto y reduce media malla de ancho). Un código como 1N2B (un
punto, dos barras, repetido) avanza $1 + 2\cdot\tfrac12 = 2$ mallas en alto y reduce
$2\cdot\tfrac12 = 1$ malla de ancho por ciclo, de modo que su **razón de corte** es

$$
RC = \frac{\Delta T}{\Delta N} = \frac{T + B/2}{N + B/2} = \frac12 .
$$ (eq-razon-corte)

El corte AB (todas barras) da 1/1; 1N1B, 1/3; 3N2B, 1/4; 1T2B, 2/1. La tabla de cortes del libro
(`data/reference/cut_ratios.csv`) cubre las razones 1/1 a 1/20 y algunas $2/x$.

En las alas, el libro descompone el borde cortado en dos tramos: $X_2 = N$ mallas en AB y el resto,
$X_1 = \lvert N - \lvert T_1 - T_2\rvert\rvert$, con razón

$$
RC_{X_1} = \frac{\lvert X_1 - N\rvert}{2X_1},
$$ (eq-rc-ala)

que se busca en la tabla para obtener el código (paño A: $X_1 = 18$, $RC = 0{,}5$ → 1N2B).

### Ángulo de ataque de los cortes

Una vez armado, el borde cortado forma con el eje de la red un ángulo que depende del código y del
armado. Si el código reduce $a$ mallas de ancho cada $d$ mallas de alto (Prado),

$$
\tan\theta = \frac{a\,U_1}{d\,U_2}.
$$ (eq-angulo-corte)

Para 1N2B ($a = 1$, $d = 2$) con $U_1 = 0{,}38$, $\theta = 11{,}6°$; con $U_1 = 0{,}23$, $6{,}7°$. El
libro promedia los ángulos de los paños del plan alto (A, C, E, G, H) y obtiene $\alpha = 10{,}63°$,
el **ángulo de ataque** que usan los métodos de resistencia de Hamuro y Fridman y la DPA por ángulo
de corte. Cuanto menor el ángulo, más alineado está el paño con el flujo y menor su resistencia de
forma; ángulos de 5–15° son típicos en el cuerpo de una red de fondo.

## Coeficientes y tablas

| Magnitud | Valor | Unidad | Fuente | Celda del Excel |
|---|---|---|---|---|
| Compostura 80 mm (alas) | PA, Ø 1,37, R1280tex | mm, g/km | plano FAO A-3 | `P!C3:C7` |
| Compostura 60 mm (square, cuerpo 1) | PA, Ø 1,16, R950tex | mm, g/km | plano | `P!C13:C17` |
| Compostura 40 mm (cuerpo 2 / bolsa) | Ø 1,16 R950tex / Ø 1,37 R1280tex | mm | plano | `P!O3:O7`, `O19:O23` |
| Compostura 30 mm (bolsa modificada) | PA, Ø 1,37, R1280tex | mm | plano | `P!C24:C28` |
| Coeficientes en el plano $c_X$, $c_Y$ | 0,5 / 1 | — | hoja | `P!D55`, `F57` |
| $U_1$ alas, square, cuerpo 1 | 0,38 | — | plano | `P!W271:W282` |
| $U_1$ cuerpo 2, bolsa | 0,23 | — | plano | `P!W276:W279` |
| Tabla de cortes | 1/1 … 1/20, 2/x | — | FAO | `Tab!A49:F88` |

## Equivalencia Excel ↔ `trawlkit`

| Celda(s) | Contenido | Función |
|---|---|---|
| `P!A55` | Rendimiento | `trawlkit.netting.runnage_m_per_kg` |
| `P!I55:I57` | Largos estirados | `trawlkit.netting.stretched_length_m` |
| `P!L55` | Densidad del hilo | `trawlkit.materials.twine_density_kg_m3` |
| `P!A61` | Superficie de trabajo del paño | `trawlkit.netting.panel_working_area_m2` |
| `P!A64` | Número de mallas | `trawlkit.netting.mesh_count` |
| `P!G63:G64` | Mallas de los cortes $X_1$, $X_2$ | `cut_meshes`, `cut_meshes_x2` |
| `P!H63`, `G127` | Razón de corte | `trawlkit.netting.cut_ratio`, `taper_ratio` |
| `P!I63` | Código de corte | `trawlkit.netting.cut_code` |
| `P!H273:K273` | Ángulo del corte | `trawlkit.netting.cut_angle_deg` |
| `P!K278` | Ángulo medio | `trawlkit.netting.mean_cut_angle_deg` |
| `P!J240`, `B243` | Pegadura de la bolsa modificada | `join_ratio`, `join_offset_m` |
| `P!N269:W291` | Resumen de paños | spec YAML `data/fao_a3_standard.yaml` |

## Supuestos y límites

* **Etiquetas invertidas.** En el bloque del paño A la hoja rotula `b (T2)` y `a (T1)` al revés que
  en los demás; los golden conservan el orden de la hoja y las funciones son simétricas en $T_1$,
  $T_2$.
* **$U_1$ del plano en `P!A61`.** La superficie de trabajo de la hoja de paños usa $c_X = 0{,}5$ como
  si fuera $U_1$ (2,99 m² para A), mientras que la de {doc}`12_mecanica_red` usa el $U_1$ real del paño
  (0,38). Sólo la segunda alimenta la resistencia.
* **Erratas** (ver {doc}`erratas`):
  `cut_ratio_first_panel` (todas las filas del ángulo usan el código del primer paño; en la A-3 todos
  son 1N2B y no cambia el resultado), `panel_f_cut_na` (la razón del paño F, 0,2692, no está en la
  tabla y la celda da `#N/A`; en modo corregido se toma la más cercana, 3N2B),
  `panel_b_cut_uses_plan_coef` (la razón del paño B usa $c_X$ en vez de $N$: 0,486 en lugar de 0,5),
  `panel_b_cut_code_lookup_a` y `twine_density_units` (la "densidad" de `P!L55` no tiene unidades de
  densidad: 1152 kg/m³ en el libro frente a 868 kg/m³ dimensionalmente correctos para el hilo
  trenzado, y 1140 kg/m³ para el polímero).
* La geometría supone paños planos y mallas romboidales perfectas; ignora el tamaño del nudo y el
  estiramiento del hilo bajo carga.

## Ejemplo ejecutable

Compostura y magnitudes del paño A (punta de ala superior), comparadas con la hoja:

```{code-cell} ipython3
from trawlkit import Compat
from trawlkit import netting
from trawlkit.materials import twine_density_kg_m3

G = "panos_de_red_y_cortes"
r = netting.runnage_m_per_kg(1280)
checks = {
    "panel_a_runnage_m_kg": r,
    "panel_a_stretched_t1_m": netting.stretched_length_m(57, 80, 0.5),
    "panel_a_stretched_n_m": netting.stretched_length_m(36, 80, 1.0),
    "panel_a_working_area_m2": netting.panel_working_area_m2(0.5, 57, 3, 36, 80),
    "panel_a_mesh_count": netting.mesh_count(57, 3, 36),
    "panel_a_cut_x1_meshes": netting.cut_meshes(57, 3, 36),
    "panel_a_cut_x1_ratio": netting.cut_ratio(netting.cut_meshes(57, 3, 36), 36),
    "panel_a_twine_density_kg_m3": twine_density_kg_m3(1.37, 80, r, Compat.EXCEL),
}
for key, value in checks.items():
    assert math.isclose(value, golden(G, key), rel_tol=1e-6), key
assert netting.cut_code(0.5) == golden(G, "panel_a_cut_x1_code") == "1N2B"
rc_f = golden(G, "panel_f_cut_x1_ratio")  # 0.2692: no está en la tabla
assert netting.cut_code(rc_f, compat=Compat.EXCEL) is None  # el #N/A del libro
assert netting.cut_code(rc_f) == "3N2B"  # modo corregido: razón más cercana
P.md_table(["Magnitud (paño A)", "trawlkit", "Excel"],
           [[k, P.fmt(v, 4), P.fmt(golden(G, k), 4)] for k, v in checks.items()])
```

Ángulo de ataque de los cortes del plan alto y su promedio (`P!K273:K278`):

```{code-cell} ipython3
codes = golden(G, "cut_codes")
u1 = golden(G, "cut_u1_horizontal")
angles = [netting.cut_angle_deg(c, u) for c, u in zip(codes, u1)]
for a, b in zip(angles, golden(G, "cut_angle_deg")):
    assert math.isclose(a, b, rel_tol=1e-6)
alpha = netting.mean_cut_angle_deg(codes, u1, compat=Compat.EXCEL)
assert math.isclose(alpha, golden(G, "cut_angle_average_deg"), rel_tol=1e-6)
P.md_table(["Paño", "Código", "U₁", "U₂", "θ [°]"],
           [[p, c, P.fmt(u, 2), P.fmt(math.sqrt(1 - u * u), 4), P.fmt(a, 2)]
            for p, c, u, a in zip("ACEGH", codes, u1, angles)]
           + [["**Promedio α**", "", "", "", f"**{P.fmt(alpha, 2)}**"]])
```

Primeras filas de la tabla de cortes:

```{code-cell} ipython3
:tags: [hide-input]
rows = netting.load_cut_table()
P.md_table(["Razón", "Código", "Mallas en ancho", "Mallas en alto"],
           [[r.label, r.cut_code, r.mesh_increase_width or "—", r.mesh_increase_height or "—"]
            for r in rows[:8]] + [[r.label, r.cut_code, "—", "—"] for r in rows[20:]])
```

Resumen por paño de la red estándar —A/B puntas de ala superior e inferior, C/D alas, E square,
F segunda sección del ala inferior, G/H cuerpos (dorso y vientre iguales), I/J bolsas— con el largo
a malla estirada, la superficie de trabajo con el $U_1$ de cada paño y el número de mallas, por
panel:

```{code-cell} ipython3
:tags: [hide-input]
from trawlkit.io import load_net
from trawlkit.net import working_surface_m2

std = load_net("fao_a3_standard")
rows = []
for p in std.panels:
    rows.append([p.id, P.fmt(p.mesh_mm, 0), P.fmt(p.twine_diameter_mm, 2),
                 f"{p.meshes_top}/{p.meshes_bottom}", p.meshes_depth, P.fmt(p.hanging_ratio, 2),
                 p.count, P.fmt(netting.stretched_length_m(p.meshes_depth, p.mesh_mm), 2),
                 P.fmt(working_surface_m2(p.hanging_ratio, p.mesh_mm, p.meshes_top,
                                          p.meshes_bottom, p.meshes_depth), 2),
                 f"{netting.mesh_count(p.meshes_top, p.meshes_bottom, p.meshes_depth):,.0f}"
                 .replace(",", "\u202f"),
                 p.cut_code or "—"])
P.md_table(["Paño", "mL [mm]", "d [mm]", "T boca/bolsa", "N", "U₁",
            "Cant.", "Largo N [m]", "Sₜ c/u [m²]", "Mallas c/u", "Corte"], rows)
```

```{code-cell} ipython3
:tags: [hide-input]
from trawlkit.drawing.layout import layout_net

lay = layout_net(std, mode="schematic")
colours = {0.38: P.SERIES[0], 0.23: P.SERIES[1]}
fig, axes = plt.subplots(1, 2, figsize=(9.2, 6.4), sharey=True)
titles = {"upper": "Plan alto (dorso)", "lower": "Plan bajo (vientre)"}
for ax, plane in zip(axes, lay.planes):
    for s in lay.shapes[plane]:
        c = colours[s.hanging_ratio]
        ax.add_patch(Polygon(s.points, closed=True, facecolor=c, alpha=0.16, lw=0))
        ax.add_patch(Polygon(s.points, closed=True, fill=False, edgecolor=c, lw=1.2))
        if s.side != "left":
            cx, cy = s.centroid
            label = s.id if s.cut_code is None else f"{s.id}\n{s.cut_code}"
            if s.section.value == "wing_tip":  # triángulo pequeño: etiqueta al costado
                ax.annotate(label, xy=(cx, cy), xytext=(cx - 7.5, cy - 0.3), fontsize=8.5,
                            ha="center", va="center", color=P.INK, linespacing=1.1,
                            arrowprops=dict(arrowstyle="-", color=P.MUTED, lw=0.8))
            else:
                ax.text(cx, cy, label, ha="center", va="center", fontsize=8.5, color=P.INK,
                        linespacing=1.1)
    ax.set_title(titles[plane])
    ax.set_xlim(-19.5, 19.5)
    ax.set_xlabel("Ancho a malla estirada [m]")
    ax.grid(False)
axes[0].set_ylim(43.5, -1)
axes[0].set_ylabel("Distancia desde la boca a malla estirada [m]")
from matplotlib.patches import Patch
fig.legend(handles=[Patch(facecolor=colours[u], alpha=0.35, edgecolor=colours[u], label=f"$U_1$ = {P.fmt(u, 2)}")
                    for u in colours], loc="lower center", ncol=2)
fig.tight_layout(rect=(0, 0.05, 1, 1))
plt.show()
```

El esquema dibuja la red estándar a malla estirada, con el código de corte de cada paño. Se ve la
lógica del diseño: alas de 80 mm con cortes 1N2B (en el vientre, el ala D usa 1N4B, más abierto, y la
segunda sección F completa la bocana del burlón), square y primer cuerpo de 60 mm que se cierran con
el mismo corte, y un segundo cuerpo y bolsa de 40 mm armados más cerrados ($U_1 = 0{,}23$), que es lo
que reduce el ángulo de ataque de 11,6° a 6,7° en esa zona.
