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

# Ventana de velocidad remolcable

## Propósito

Todo el diseño desemboca en una pregunta: **¿puede el buque remolcar esta red a la velocidad que
la especie exige?** El tiro disponible $F_T$ disminuye al aumentar la velocidad (la hélice
convierte en empuje una fracción cada vez menor de su potencia) y la resistencia total $R_T$
aumenta aproximadamente con $v^2$. Las dos curvas se cruzan en la **velocidad máxima remolcable**;
por debajo de ella está la ventana viable.

El Excel pone una tabla al lado de la otra (`'Potencia Disponible Arrastre OK'!L11:O19` y
`'Cables de Remolque'!H118:I126`) y deja la conclusión al lector. `trawlkit.performance` la
formaliza. Este capítulo cierra la cadena de {doc}`motor`: usa el tiro de {doc}`10_potencia`, la
resistencia de la red de {doc}`14_resistencia`, la de los portones de
{doc}`15_portones_aparejo`, la de las boyas de {doc}`17_flotacion_lastre` y la de los cables de
{doc}`18_cables`.

## Teoría

### Oferta: el tiro disponible

El libro adopta como tiro de diseño la recta de {cite:t}`fridman1986`:

$$
F_T(v) = P\,(K_F - 0{,}7\,v) \quad [\text{kgf}], \qquad
K_F = \begin{cases} 10 & \text{hélice de paso fijo (PF)} \\ 15 & \text{paso variable con tobera (PV+T)} \end{cases}
$$ (eq-19-ft)

con $P$ en HP y $v$ en nudos. El coeficiente $K_F$ es el tiro a punto fijo por HP; la pendiente
$0{,}7\,P$ refleja la caída del empuje con la velocidad de avance. Una hélice de paso variable con
tobera entrega 50 % más tiro a punto fijo que una de paso fijo diseñada para navegar, que trabaja
lejos de su punto óptimo a velocidades de arrastre. Los otros métodos de potencia (Prado–Dremière,
Koyama, Nomura, Hamuro) se discuten en {doc}`10_potencia`.

### Demanda: la resistencia total

$$
R_T(v) = R_N(v) + R_B(v) + R_W(v) + R_{OB}(v)
$$ (eq-19-rt)

La red domina (≈ 90–98 % del total); los portones son el segundo término y boyas y cables aportan
pocos puntos porcentuales ({numref}`fig-18-demanda`).

### Ventana viable y velocidad máxima

Una velocidad $v$ es viable cuando el margen $m(v) = F_T(v) - R_T(v)$ es no negativo. Sobre el
vector de velocidades del libro ($v_i$ = 1; 1,5; … 5 kn), la velocidad máxima remolcable es el
primer cruce de $m$ de positivo a negativo, interpolado linealmente entre los dos puntos que lo
rodean:

$$
v^* = v_k + (v_{k+1} - v_k)\,\frac{m_k}{m_k - m_{k+1}}, \qquad m_k \ge 0 > m_{k+1}
$$ (eq-19-vmax)

Si todo el vector es viable, $v^*$ es la última velocidad; si ninguna lo es, no hay ventana. Como
$R_T$ es convexa y $F_T$ lineal, la interpolación lineal entre nodos sobreestima levemente la
demanda en el tramo y $v^*$ queda del lado seguro.

## Coeficientes

| Símbolo | Valor | Unidad | Fuente | Celda |
|---|---|---|---|---|
| $K_F$ paso fijo | 10 | kgf/HP | {cite:t}`fridman1986` | `PotOK!D10` |
| $K_F$ paso variable + tobera | 15 | kgf/HP | {cite:t}`fridman1986` | `PotOK!F10` |
| pendiente | 0,7 | kgf/(HP·kn) | {cite:t}`fridman1986` | `PotOK!E10` |
| $P$ | 150 (180) | HP | Tipo de buques | `PotOK!C10` (`C22`) |
| vector de velocidades | 1–5, paso 0,5 | kn | — | `PotOK!B10:B18` |

## Equivalencia Excel ↔ `trawlkit`

| Celda(s) | Cálculo | Función |
|---|---|---|
| `PotOK!L11:O19` | $F_T$ de Fridman (PF y PV+T, 150 y 180 HP) | `power.summary`, `power.fridman_towing_force_kgf` |
| `Rem!H118:I126` | $R_T$ (estándar y modificada) | `rigging.total_drag_kgf` (errata `warp_total_omits_doors`) |
| — | demanda con cualquier combinación de términos | `performance.total_demand_kgf` |
| — | margen, velocidades viables y $v^*$ | `performance.speed_window` |
| — | ventanas por hélice y red | `model.run` → `result.performance.windows`, `.design` |

## Supuestos y límites

- **Un único método de tiro.** La ventana usa la recta de Fridman; los otros métodos del capítulo
  {doc}`10_potencia` dan $F_T$ distintos y, por lo tanto, ventanas distintas. Es una comparación
  de proyecto, no una predicción de la velocidad real, que depende del estado de la hélice, del
  casco y del mar.
- **Errata `warp_total_omits_doors`** (`Rem!H118`). La resistencia total del Excel es
  `G118+F118+D118` = $R_W + R_B + R_N$: omite los portones. En modo `CORRECTED` `trawlkit` suma
  $R_{OB}$, lo que baja la velocidad máxima ({doc}`erratas`).
- **Un portón o dos.** La hoja calcula la resistencia de **un** portón de 1,805 m² (`Port!D190`,
  {doc}`15_portones_aparejo`). El modo corregido suma la de los **dos** portones del arte
  (`trawlkit.model.DOORS_PER_RIG = 2`); la tabla de sensibilidad muestra ambos casos.
- **Malla de velocidades.** $v^*$ se interpola sobre la malla de 0,5 kn del libro;
  `DesignCase.speeds_kn` admite una malla más fina.

## Ejemplo ejecutable

```{code-cell} ipython3
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.cwd().parent))
sys.path.insert(0, str(pathlib.Path.cwd()))

import numpy as np
from IPython.display import Markdown

from tests.golden_utils import golden
from trawlkit.performance import speed_window, total_demand_kgf
import _plots_t2 as P

REM = "cables_de_remolque"
r = P.fao_result(150, "excel")
win = r.performance.design  # paso fijo, red estándar


def close(actual, key, sheet=REM):
    """Compara con el valor del Excel (escalar o serie) a rtol = 1e-6."""
    got, exp = np.atleast_1d(actual), np.atleast_1d(golden(sheet, key))
    return all(math.isclose(a, b, rel_tol=1e-6) for a, b in zip(got, exp))


pvt_win = r.performance.windows["variable_pitch_nozzle_std"]
assert close(win.available_kgf, "fridman_ft_fixed_150_kgf")
assert close(win.demand_kgf, "total_drag_std_kgf")
assert close(pvt_win.available_kgf, "fridman_ft_variable_nozzle_150_kgf")

# v* recalculada a mano con los valores del Excel (ecuación de v*)
ft = np.array(golden(REM, "fridman_ft_fixed_150_kgf"))
rt = np.array(golden(REM, "total_drag_std_kgf"))
m = ft - rt
k = int(np.argmax(m < 0)) - 1
v_hand = r.case.speeds[k] + 0.5 * m[k] / (m[k] - m[k + 1])
assert math.isclose(win.max_speed_kn, v_hand, rel_tol=1e-9)

for key, w in r.performance.windows.items():
    print(f"{key:<26} v* = {w.max_speed_kn:.2f} kn, viables {w.feasible_speeds_kn}")
```

La ventana de diseño (hélice de paso fijo, red estándar) se cierra a 2,44 kn en el Excel. Con los
portones incluidos, y con las demás erratas corregidas, el cruce se adelanta
({numref}`fig-19-ventana`).

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Ventana de velocidad del buque de 150 HP con la red FAO A-3 estándar. Tiro de Fridman con
      hélice de paso fijo (PF) y de paso variable con tobera (PV+T) frente a la resistencia total
      del Excel ($R_N + R_B + R_W$) y del modo corregido (que suma $R_{OB}$). La zona sombreada es la
      ventana viable de diseño (PF, Excel); los anillos marcan $v^*$.
    name: fig-19-ventana
---
P.setup()
rc = P.fao_result(150, "corrected")
kn = r.case.speeds
fig, ax = P.plt.subplots(figsize=(7.2, 4.6))
pf, pvt = win.available_kgf, r.performance.windows["variable_pitch_nozzle_std"].available_kgf

# ventana viable: entre R_T y F_T hasta v*
vv = np.linspace(kn[0], win.max_speed_kn, 60)
ax.fill_between(vv, np.interp(vv, kn, win.demand_kgf), np.interp(vv, kn, pf),
                color=P.GOOD, alpha=0.12, lw=0)
ax.annotate("ventana viable\n(PF, Excel)", (1.45, 1050), color=P.INK_2, fontsize=9, ha="center")

P.line(ax, kn, pf, 1, "$F_T$ paso fijo (PF)")
P.line(ax, kn, pvt, 7, "$F_T$ paso variable + tobera (PV+T)")
P.line(ax, kn, win.demand_kgf, 2, "$R_T$ Excel ($R_N+R_B+R_W$)")
P.line(ax, kn, rc.performance.design.demand_kgf, 4, "$R_T$ corregido ($+R_{OB}$)")

marks = ((win, "$v^*$ PF, Excel", (2.8, 850)),
         (r.performance.windows["variable_pitch_nozzle_std"], "$v^*$ PV+T, Excel", (2.05, 2700)),
         (rc.performance.design, "$v^*$ PF, corregido", (2.8, 550)))
for w, lab, xy in marks:
    vs = w.max_speed_kn
    y = float(np.interp(vs, kn, w.available_kgf))
    ax.plot([vs], [y], "o", ms=13, mfc="none", mec=P.INK_2, mew=1.2)
    ax.annotate(f"{lab}: {vs:.2f} kn".replace(".", ","), (vs, y), xytext=xy, textcoords="data",
                color=P.INK_2, fontsize=9, va="center",
                arrowprops={"arrowstyle": "-", "color": P.MUTED, "lw": 0.8, "shrinkB": 7})
ax.set_ylabel("Fuerza [kgf]")
ax.set_ylim(0, 4200)
P.speed_axis(ax)
P.legend(ax, loc="upper left")
P.finish(fig)
```

### Sensibilidad

La tabla varía un factor por vez sobre el caso de diseño (150 HP, PF, red estándar, modo Excel).

```{code-cell} ipython3
---
mystnb:
  markdown_format: myst
---
r180 = P.fao_result(180, "excel")
rn, rb, rw = r.drag.rn.std, r.floats.drag_kgf, r.warps.drag_kgf
rob = np.asarray(r.doors.forces.drag_kgf)
pvt = r.performance.windows["variable_pitch_nozzle_std"].available_kgf


def vmax(ft, *terms):
    return speed_window(kn, ft, total_demand_kgf(*terms)).max_speed_kn


base = vmax(pf, rn, rb, rw)
assert math.isclose(base, win.max_speed_kn, rel_tol=1e-12)
rows = [
    ("Caso de diseño (Excel: $R_N+R_B+R_W$)", base),
    ("$R_N$ − 10 %", vmax(pf, 0.9 * rn, rb, rw)),
    ("$R_N$ + 10 %", vmax(pf, 1.1 * rn, rb, rw)),
    ("+ $R_{OB}$ de un portón", vmax(pf, rn, rb, rw, rob)),
    ("+ $R_{OB}$ de los dos portones (modo corregido)", vmax(pf, rn, rb, rw, 2 * rob)),
    ("Red modificada", r.performance.windows["fixed_pitch_mod"].max_speed_kn),
    ("Hélice PV+T", vmax(pvt, rn, rb, rw)),
    ("Buque de 180 HP (PF)", r180.performance.design.max_speed_kn),
    ("Buque de 180 HP (PV+T)",
     r180.performance.windows["variable_pitch_nozzle_std"].max_speed_kn),
    ("Modo corregido completo (PF)", rc.performance.design.max_speed_kn),
]
lines = ["| Variante | $v^*$ [kn] | Δ [kn] |", "|---|---|---|"]
for name, v in rows:
    lines.append(f"| {name} | {v:.2f} | {v - base:+.2f} |".replace(".", ","))
Markdown("\n".join(lines))
```

Tres lecturas:

1. **La hélice pesa más que la potencia.** Pasar de paso fijo a paso variable con tobera (mismo
   motor) gana ≈ 0,8 kn; pasar de 150 a 180 HP con paso fijo gana menos de 0,3 kn. Para arrastrar a 2,5–3 kn, velocidades habituales en arrastre de fondo, el
   buque de 150 HP necesita una hélice de paso variable o una red más chica.
2. **Los portones no son despreciables.** Con un portón la ventana pierde ≈ 0,1 kn; con los dos,
   que es la configuración real, ≈ 0,2 kn. Omitirlos (errata `warp_total_omits_doors`) da una
   ventana optimista.
3. **La incertidumbre de $R_N$ domina.** Un ±10 % en la resistencia de la red, que es menor que la
   dispersión entre métodos de {doc}`14_resistencia`, mueve $v^*$ ≈ ±0,15 kn, tanto como los
   portones. Por eso el modo corregido completo baja $v^*$ menos de lo que sugieren los portones: las correcciones
   de la red (superficie sólida, burlón) reducen $R_N$ ≈ 5 % y compensan buena parte del portón
   que se agrega. Las redes estándar y modificada son casi equivalentes (la bolsa de 30 mm resiste un
   poco menos en modo Excel).
