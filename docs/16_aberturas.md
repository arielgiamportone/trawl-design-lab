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

# Aberturas horizontal y vertical

## Propósito

La boca de la red es la sección que barre el fondo: su ancho, la **distancia entre puntas de ala**
(DPA o abertura horizontal AH), y su alto, la **abertura vertical** AV, fijan el área barrida y,
con ella, la captura por hora de arrastre. Ninguna de las dos es una dimensión de la red: resultan
del equilibrio entre la fuerza de abertura de los portones, la resistencia de la red, la flotación
de la lima y la geometría del aparejo.

El libro estima cada abertura por varios métodos independientes y los compara. Este capítulo
replica los bloques B162:P282 de *Mecánica de la Red* y la celda `Dim!F61`; en `trawlkit` vive en
`trawlkit.rigging.spread`. Usa la resistencia de la red ({doc}`14_resistencia`), las fuerzas del
portón y el aparejo ({doc}`15_portones_aparejo`) y la flotación total
({doc}`17_flotacion_lastre`), y alimenta a su vez el método de Dickson de resistencia y el
dimensionado de los cables ({doc}`18_cables`).

## Teoría

### Geometría de maniobra

El cable filado $L_s$ se elige por profundidad $d$ con la relación tabulada $L_s/d$ (tabla
*profundidad → cable filado*, 6:1 a 20 m, 5:1 a 40 m, ≈ 3:1 a 200 m); la tabla se consulta como el
`LOOKUP` del Excel, con la fila de mayor profundidad no superior a $d$:

$$
L_s = d\cdot\left(\frac{L_s}{d}\right)_{tab}, \qquad L_{sh} = 0{,}95\,L_s
$$ (eq-16-ls)

$L_{sh}$ es la proyección horizontal del cable en aguas someras (0,85·$L_s$ en aguas profundas).
La red trabajando tiene un largo $L_{Rw} = L_R\,U_2$, con $L_R$ el largo sin bolsa y $U_2 = 0{,}87$
el coeficiente de armado vertical de la red abierta.

### DPA de Fridman: coeficientes de expansión

{cite:t}`fridman1986` plantea el equilibrio de medio sistema (un portón, un cable, media red) y
expresa las fuerzas del portón relativas a la media resistencia de la red con dos **coeficientes de
expansión**:

$$
E_{dx} = \frac{R_{OB}}{R_N/2}, \qquad E_{dy} = \frac{F_y}{R_N/2}
$$ (eq-16-edx)

$E_{dy}$ mide cuánto "tira hacia afuera" el portón frente a lo que la red "tira hacia atrás";
$E_{dx}$ mide la resistencia extra que el portón agrega en la línea del cable. Ambos crecen con la
velocidad porque las fuerzas del portón escalan con $v^2$ mientras que $R_N$ crece algo más
lentamente. Con la red trabajando $L_{Rw}$ y las bridas $L_{nc}$ ($=V_s$, brida superior):

$$
DPA = \frac{2\,L_{sh}\,L_{Rw}\,E_{dy}}{L_{sh} + L_{nc}\,(1 + E_{dx})}
$$ (eq-16-dpa-fridman)

La DPA de Fridman es la única que depende de la velocidad: a 1 kn la red se abre apenas 6 m y a
5 kn supera los 15 m.

### DPA geométrica y por ángulo de corte

Por **triángulos semejantes**, si el aparejo (pie de gallo $PG$, alargue $A_{PG}$, patentes
$L_p$, brida $V_s$) y la red (largo $m$) están tensos en línea recta desde cada portón, la abertura
en las puntas de ala es la fracción de $D_s$ que corresponde a la red:

$$
DPA_g = \frac{m\,D_s}{PG + A_{PG} + L_p + V_s + m}
$$ (eq-16-dpa-geom)

El libro la evalúa con el burlón ($m$ = 33,3 m, redondeando hacia abajo) y con la red trabajando
($m = L_{Rw}$, sólo en el numerador y en el término de la red, redondeando hacia arriba). El
tercer método, de {cite:t}`prado1990`, deduce la abertura de la forma de la red: con un largo total
$b$ y el ángulo medio de los cortes $\alpha$ (capítulo {doc}`11_panos_y_cortes`),

$$
DPA_\alpha = 2\,b\,U_2\,\tan\alpha
$$ (eq-16-dpa-corte)

La **abertura horizontal** de diseño es el promedio de los cuatro métodos, contando la serie de
Fridman (estándar, 1–5 kn) como un solo término:

$$
AH = \tfrac14\left(DPA_\alpha + DPA_{g,L_{Rw}} + DPA_{g,m} + \overline{DPA_{F}}\right)
$$ (eq-16-ah)

### Abertura vertical

Los métodos empíricos expresan AV como fracción de la circunferencia de la boca a malla estirada
$a$:

- {cite:t}`prado1990`: $AV = 0{,}055\,a$ en redes de poca abertura y $0{,}065\,a$ en redes de
  mucha abertura o marisqueras;
- {cite:t}`izzo` (INIDEP): 4,35; 5; 6 y 7 % de $a$;
- {cite:t}`suzuki1982`: $AV = \tfrac{4}{90}\,a$ (4,4 %), el valor que el libro adopta como AV de
  diseño (`Dim!F60`).

{cite:t}`martini` parte en cambio de la circunferencia estirada del primer paño de dorso más
vientre, $D_V$, descontadas las $M_R$ mallas relingadas en las uniones:

$$
AV_M = \left(D_V - \frac{M_R\,m_L}{1000}\right)\cdot 0{,}05
$$ (eq-16-av-martini)

### AV de Baranov–Fridman: la lima como catenaria

El método físico considera la lima como un cable flexible cargado por la flotación total
$F_{fz}$ y tirado hacia atrás por la red. El ángulo con que la lima y la brida suben respecto del
fondo resulta del cociente entre la flotación y la resistencia {cite:p}`fridman1986`:

$$
\alpha_v = \arctan\!\left(\frac{2\,F_{fz}}{R_N}\right), \qquad
AV = h_{dl} + (f_L + V_s)\,\sin\alpha_v
$$ (eq-16-av-fridman)

donde $h_{dl}$ es la altura del triángulo o dan leno (0,6 m) y $f_L$ la flecha de la lima. La flecha
se obtiene de la tabla de la catenaria, que da $f_L/L$ en función de la relación $DPA/L$ entre la
abertura y el largo de la lima: cuanto más cerrada está la red (DPA/L pequeño), más "cuelga" la
lima. Como $R_N$ crece con $v^2$ y $F_{fz}$ es fija, **la AV de Fridman cae con la velocidad**:
la red se aplana al acelerar, el comportamiento que se observa en el mar.

## Coeficientes

| Símbolo | Valor | Unidad | Fuente | Celda |
|---|---|---|---|---|
| $L_s/d$ a 40 m | 5 | — | tabla profundidad → cable | `Mec!J178` |
| $L_{sh}/L_s$ | 0,95 (somero), 0,85 (profundo) | — | {cite:t}`fridman1986` | `Mec!F179:F180` |
| $U_2$ red trabajando | 0,87 | — | — | `Mec!E184` |
| AV Prado | 5,5 %; 6,5 % de $a$ | — | {cite:t}`prado1990` | `Mec!H245:H247` |
| AV Izzo | 4,35; 5; 6; 7 % de $a$ | — | {cite:t}`izzo` | `Mec!J242:J245` |
| AV Suzuki | 4/90 de $a$ | — | {cite:t}`suzuki1982` | `Mec!D255` |
| $M_R$, factor de Martini | 12 mallas; 0,05 | — | {cite:t}`martini` | `Mec!E270`, `E272` |
| $h_{dl}$ (dan leno) | 0,6 | m | — | `Mec!O262` |
| $f_L/L$ | 0,216 (fijo) | — | tabla de la catenaria | `Mec!O266` |

## Equivalencia Excel ↔ `trawlkit`

| Celda(s) | Cálculo | Función |
|---|---|---|
| `Mec!E176:E186` | $L_s$, $L_{sh}$, $L_{Rw}$, $L_{nc}$ | `rigging.towing_geometry`, `rigging.warp_depth_ratio` |
| `Mec!H164:O172` | $R_d$, $F_{dy}$, $E_{dx}$, $E_{dy}$ | `rigging.door_forces_kgf`, `rigging.expansion_coefficients` |
| `Mec!P164:Q172` | DPA de Fridman | `rigging.dpa_fridman_m`, `rigging.fridman_spread` (errata `dpa_std_uses_mod_edy`) |
| `Mec!I193:M201` | tabla 2·Yn y $D_s$ desde la DPA | `rigging.dpa_fridman_table` |
| `Mec!L211` | DPA geométrica (burlón) | `rigging.dpa_geometric_m` |
| `Mec!L225` | DPA con la red trabajando | `rigging.dpa_geometric_working_m` |
| `Mec!L233` | DPA por ángulo de corte | `rigging.dpa_from_cut_angle_m` |
| `Dim!F61` | AH promedio | `rigging.horizontal_opening_m` |
| `Mec!F245:F247`, `K242:K245` | AV Prado, Izzo | `rigging.vertical_opening_pct_m` |
| `Mec!D255` | AV Suzuki | `rigging.vertical_opening_suzuki_m` |
| `Mec!E269:E272` | AV Martini | `rigging.vertical_opening_martini_m` |
| `Mec!O261` | $F_{fz}$ | `rigging.fridman_flotation_total_kgf` |
| `Mec!O265:O267` | $DPA/L$, $f_L/L$, $f_L$ | `rigging.catenary_ratio`, `rigging.headrope_sag_m` |
| `Mec!M272:O282` | AV Baranov–Fridman | `rigging.vertical_opening_fridman` |
| bloque completo | etapa `spread` | `model.run` → `result.spread` |

## Supuestos y límites

- **Equilibrio estático.** {eq}`eq-16-dpa-fridman` supone cables rectos en planta, portones a
  ángulo de ataque constante y red simétrica; no considera la corriente ni el giro del buque.
- **AV de diseño empírica.** Los porcentajes de la circunferencia condensan la experiencia con
  redes de dos caras y fondo blando; no dependen de la velocidad ni de la flotación. El libro
  adopta Suzuki (1,98 m) como AV de diseño; Baranov–Fridman da 2,09 m en promedio, pero 4,6 m a
  1 kn y 1,0 m a 5 kn.
- **Errata `dpa_std_uses_mod_edy`** (`Mec!P164`). La DPA de la red estándar se calcula con
  `$O164`, el $E_{dy}$ de la red **modificada**, en vez de `$N164`. Como la modificada tiene algo
  menos de resistencia, su $E_{dy}$ es mayor en el cociente $R_{N,std}/R_{N,mod}$ (≈ 2,2 % a
  todas las velocidades) y la DPA estándar sale sobreestimada en la misma proporción. `Compat.CORRECTED` usa el $E_{dy}$ estándar ({doc}`erratas`).
- **Errata `catenary_ratio_hardcoded`** (`Mec!O266`): la circularidad. La flecha $f_L$ entra en
  el largo de la brida ({eq}`eq-15-bridas`, $V_s = AV/\sin\alpha_b - f_L$); la brida entra en las
  DPA ({eq}`eq-16-dpa-fridman` y {eq}`eq-16-dpa-geom`); y la DPA define $DPA/L$, que es la entrada
  de la tabla de la catenaria que da $f_L$. El cálculo es un **lazo**:
  $f_L \to V_s \to DPA \to DPA/L \to f_L$. El Excel lo corta escribiendo a mano $f_L/L = 0{,}216$,
  el valor tabulado para $DPA/L = 0{,}87$, aunque la propia hoja calcula $DPA/L = 0{,}45$ en
  `O265`. Ese valor está además fuera de la tabla (que llega hasta 0,56, $f_L/L = 0{,}378$). El
  modelo conserva 0,216 en ambos modos para no cambiar la geometría de diseño (`DesignCase.catenary_ratio`)
  y anota la discrepancia en `result.notes`; el ejemplo de abajo resuelve el lazo.

## Ejemplo ejecutable

```{code-cell} ipython3
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.cwd().parent))
sys.path.insert(0, str(pathlib.Path.cwd()))

import numpy as np

from tests.golden_utils import golden
from trawlkit import Compat, rigging
import _plots_t2 as P

MEC = "mecanica_de_la_red"
r = P.fao_result(150, "excel")
s, tow = r.spread, r.rigging.towing


def close(actual, key, sheet=MEC):
    """Compara con el valor del Excel (escalar o serie) a rtol = 1e-6."""
    got, exp = np.atleast_1d(actual), np.atleast_1d(golden(sheet, key))
    return all(math.isclose(a, b, rel_tol=1e-6) for a, b in zip(got, exp))


assert close(tow.net_length_working_m, "net_length_working_m")
assert close(s.fridman.edy_mod, "edy_mod")
assert close(s.fridman.dpa_std_m, "dpa_fridman_std_m")  # con la errata de Edy
assert close(s.dpa_cut_angle_m, "dpa_from_cut_angle_m")
DIM = "dimensiones_de_la_red"
assert close(s.horizontal_opening_m, "horizontal_opening_m", DIM)
assert close(s.vertical.martini_m, "av_martini_m")
assert close(s.vertical.flotation_total_kgf, "flotation_total_kgf")
assert close(s.vertical.fridman.std.av_average_m, "av_fridman_avg_std_m")

v = s.vertical
print(f"Ls = {tow.warp_m:g} m, Lsh = {tow.warp_horizontal_shallow_m:g} m, "
      f"LRw = {tow.net_length_working_m:.2f} m, Lnc = {tow.bridle_m:g} m")
print(f"DPA geométrica: burlón {s.dpa_geometric_m:g} m, LRw {s.dpa_working_m:g} m")
print(f"DPA por corte {s.dpa_cut_angle_m:.2f} m; "
      f"Fridman (media 1–5 kn) {np.mean(s.fridman.dpa_std_m):.2f} m")
print(f"AH = {s.horizontal_opening_m:.2f} m")
pr = v.prado_m
print(f"AV Suzuki {v.suzuki_m:.2f} m; Prado {pr['low_opening']:.2f} / "
      f"{pr['high_opening']:.2f} m; Izzo {v.izzo_m[0]:.2f}–{v.izzo_m[-1]:.2f} m")
print(f"AV Martini {v.martini_m:.2f} m; "
      f"Fridman (media) {v.fridman.std.av_average_m:.2f} m "
      f"con Ffz = {v.flotation_total_kgf:.1f} kgf")
```

La errata de $E_{dy}$, aislada: las mismas entradas, en los dos modos.

```{code-cell} ipython3
d = r.doors
args = (d.door.area_m2, d.polar.cd, d.polar.cl, r.case.speeds_ms,
        r.drag.rn.std, r.drag.rn.mod, tow.warp_horizontal_shallow_m,
        tow.net_length_working_m, tow.bridle_m)
fx = rigging.fridman_spread(*args, compat=Compat.EXCEL)
fc = rigging.fridman_spread(*args, compat=Compat.CORRECTED)
assert close(fx.dpa_std_m, "dpa_fridman_std_m")
diff = 100 * (np.asarray(fx.dpa_std_m) / np.asarray(fc.dpa_std_m) - 1)
print(f"DPA estándar a 3 kn: Excel {fx.dpa_std_m[4]:.3f} m, "
      f"corregida {fc.dpa_std_m[4]:.3f} m")
print(f"sobreestimación del Excel: {diff.min():.2f} % a {diff.max():.2f} %")
```

Y la circularidad de la catenaria: partiendo del 0,216 del Excel, recorremos el lazo
$f_L \to V_s \to DPA_{g,L_{Rw}} \to DPA/L \to f_L/L$ hasta que se repite.

```{code-cell} ipython3
dims, case = r.dimensions.std, r.case
pg = r.rigging.crowfoot.length_m
ratio, seen = case.catenary_ratio, []
for _ in range(10):
    sag = rigging.headrope_sag_m(dims.headrope_m, ratio)
    vs = rigging.bridle_lengths(
        v.suzuki_m, sag, case.bridle_angle_deg, case.dan_leno_m
    ).upper_m
    dpa = rigging.dpa_geometric_working_m(
        d.spread_m, tow.net_length_working_m, pg, 0.0, case.sweeps_m, vs
    )
    seen.append((ratio, sag, vs, dpa, dpa / dims.headrope_m))
    new = rigging.catenary_ratio(dpa / dims.headrope_m)
    if new == ratio:
        break
    ratio = new
assert math.isclose(seen[0][4], golden(MEC, "dpa_over_l"), rel_tol=1e-6)
for i, (q, sag, vs, dpa, dl) in enumerate(seen):
    print(f"{i}: fL/L = {q:.3f} → fL = {sag:5.2f} m → Vs = {vs:g} m "
          f"→ DPA = {dpa:g} m → DPA/L = {dl:.3f}")
```

El lazo converge en dos pasos a $f_L/L = 0{,}378$ (el extremo de la tabla), con una brida de
13 m en vez de 18 m. Que la tabla se agote indica que, con este aparejo, la red trabaja más cerrada
de lo que la tabla de la catenaria contempla (DPA ≈ 0,45–0,49 veces la lima).

{numref}`fig-16-aberturas` compara todos los métodos. Los métodos geométricos y empíricos son
constantes; sólo los de Fridman responden a la velocidad, en sentidos opuestos: la red se abre en
horizontal y se aplana en vertical al acelerar.

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Abertura horizontal (arriba) y vertical (abajo) de la red FAO A-3 estándar con el
      buque de 150 HP, por método. Las curvas son los métodos de Fridman (modo Excel); las rectas,
      los métodos que no dependen de la velocidad. La banda gris es el rango de Izzo (4,35–7 % de
      la circunferencia).
    name: fig-16-aberturas
---
P.setup()
kn = r.case.speeds
fig, (a1, a2) = P.plt.subplots(2, 1, figsize=(7, 8.4))

P.line(a1, kn, s.fridman.dpa_std_m, 1, "Fridman, estándar")
P.line(a1, kn, fc.dpa_std_m, 1, "Fridman, estándar corregida", marker=False, ls=(0, (4, 3)), lw=1.6)
flat = [(s.dpa_geometric_m, 2, "Geométrica (burlón y $L_{Rw}$)"),
        (s.dpa_cut_angle_m, 3, "Por ángulo de corte"),
        (s.horizontal_opening_m, 7, "AH de diseño (promedio)")]
for val, slot, lab in flat:
    style = {"ls": (0, (1.5, 2)), "lw": 2.4} if slot == 7 else {"lw": 2}
    a1.plot([1, 5], [val, val], color=P.color(slot), label=lab, **style)
a1.annotate("geométricas = 13 m ≈ AH = 13,01 m", (3.2, 12.5), color=P.INK_2, fontsize=9, va="top")
a1.set_title("Distancia entre puntas de ala")
a1.set_ylabel("DPA [m]")
a1.set_ylim(0, 18)
P.speed_axis(a1)
P.legend(a1, loc="lower right")

a2.fill_between([1, 5], v.izzo_m[0], v.izzo_m[-1], color=P.NEUTRAL_WASH, lw=0, label="Izzo 4,35–7 %")
P.line(a2, kn, v.fridman.std.av_m, 1, "Baranov–Fridman, estándar")
for val, slot, lab in ((v.suzuki_m, 2, "Suzuki (diseño)"),
                       (v.prado_m["low_opening"], 3, "Prado 5,5 %"),
                       (v.prado_m["high_opening"], 4, "Prado 6,5 %"),
                       (v.martini_m, 5, "Martini")):
    a2.plot([1, 5], [val, val], color=P.color(slot), lw=2, label=lab)
a2.set_title("Abertura vertical")
a2.set_ylabel("AV [m]")
a2.set_ylim(0, 5)
P.speed_axis(a2)
P.legend(a2, loc="upper right")
P.finish(fig)
```

| v [kn] | 1,0 | 2,0 | 2,5 | 3,0 | 4,0 | 5,0 |
|---|---|---|---|---|---|---|
| $E_{dx}$ estándar | 0,084 | 0,155 | 0,175 | 0,190 | 0,212 | 0,229 |
| $E_{dy}$ estándar | 0,110 | 0,203 | 0,229 | 0,248 | 0,277 | 0,300 |
| DPA Fridman estándar (Excel) [m] | 5,78 | 10,61 | 11,96 | 12,96 | 14,44 | 15,58 |
| AV Baranov–Fridman estándar [m] | 4,61 | 2,47 | 1,95 | 1,62 | 1,24 | 1,04 |

A la velocidad de pesca (2,5 kn) las dos estimaciones físicas coinciden con las de diseño: DPA de
Fridman ≈ 12 m frente a AH = 13,0 m, y AV de Fridman ≈ 1,95 m frente a 1,98 m de Suzuki.
