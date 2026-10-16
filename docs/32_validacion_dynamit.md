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

# Validación contra DynamiT

```{code-cell} ipython3
:tags: [remove-cell]
import sys, pathlib, math
sys.path.insert(0, str(pathlib.Path.cwd().parent))
import numpy as np
import matplotlib.pyplot as plt
from tests.golden_utils import golden
from trawlkit import drag
import _plots_v as V
V.setup_style()

C, E = V.run_case(150, "corrected"), V.run_case(150, "excel")
kn = C.case.speeds
```

## Propósito

{doc}`31_validacion_excel` demuestra que `trawlkit` reproduce el libro Excel. Eso no dice nada sobre
si el libro acierta: valida la migración, no el modelo. Para eso hace falta una referencia
**independiente**. El autor del libro simuló la misma red FAO A-3 con DynamiT y pegó los resultados
en el Excel (`Res!S302:S310`) y en dos capturas (`legacy/dynamit_*.png`). Este capítulo compara esos
resultados con los del motor, variable por variable.

## Qué es DynamiT

DynamiT es el programa de Ifremer para simular y optimizar artes de arrastre {cite:p}`dynamit`. A
diferencia del libro, que encadena reglas empíricas independientes entre sí (una fórmula para la
resistencia, otra para la abertura, otra para la separación de portones), DynamiT representa el arte
completo —paños, relingas, bridas, cables y portones— como una estructura flexible y busca la
**forma de equilibrio** bajo las fuerzas hidrodinámicas sobre cada hilo, el peso, la flotación y el
contacto con el fondo. La resistencia, las aberturas y la separación de portones salen de esa misma
forma, de modo que son **coherentes entre sí**.

Eso no lo convierte en la verdad: es un modelo con sus propios coeficientes de arrastre del hilo y
de los portones, y sólo una medición en el mar (sensores de abertura y dinamómetro en los cables)
diría cuál de los dos acierta. Pero es un modelo físico independiente, y donde coincide con el
libro el resultado gana confianza.

## Resultados de DynamiT

La simulación usa la red **estándar**: la captura `legacy/dynamit_resumen_fao_a3.png` lista los
paños con lado de malla 40, 30 y 20 mm (malla estirada 80, 60 y 40 mm) y bolsa J1 de 20 mm de lado,
es decir, la bolsa estándar de 40 mm. Su superficie total es **38,76 m²**, que coincide con la
superficie sólida **corregida** del motor (38,75 m²) y no con la del libro (40,90 m²): una
confirmación independiente de la errata `codend_minor_side_uses_depth` ({doc}`erratas`). El peso
que reporta (32,30 kg) es mayor que el del motor (20,0 kg corregido, 28,3 kg Excel); DynamiT usa
títulos de hilo propios (780 y 1160 m/kg) que no son los del libro.

La tabla de resultados se transcribe de `legacy/dynamit_resultados_fao_a3.png` (red FAO A3,
velocidades 1,0–5,0 kn). La fila de resistencia coincide con la columna pegada en el Excel, lo que
verifica la transcripción:

```{code-cell} ipython3
# Transcripción de legacy/dynamit_resultados_fao_a3.png (DynamiT, Ifremer; red FAO A3 estándar).
# Cada número se verificó contra la imagen ampliada. Unidades de la captura: m y kg (kgf).
DYNAMIT = {
    "v_kn": [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
    "AH_m": [8.9, 11.2, 12.5, 12.9, 13.3, 13.2, 13.3, 13.5, 13.6],  # abertura horizontal
    "AV_m": [6.0, 3.5, 2.4, 1.8, 1.4, 1.2, 1.0, 1.3, 1.6],  # abertura vertical
    "DP_m": [28.5, 40.9, 46.6, 49.3, 51.4, 51.6, 52.3, 53.2, 53.4],  # distancia entre portones
    "RA_kg": [330.6, 476.0, 704.3, 967.3, 1331.3, 1751.9, 2208.7, 2784.5, 3371.8],  # resistencia
}
D = {k: np.array(v) for k, v in DYNAMIT.items()}
assert np.allclose(D["v_kn"], kn)
# La columna DynamiT pegada en 'Resistencia de la RED'!S398:S406 es la misma RA (en kgf).
assert np.allclose(D["RA_kg"], golden("resistencia_de_la_red", "summary_dynamit_std_kgf"), rtol=1e-9)
assert np.allclose(D["RA_kg"] / 1000, golden("resistencia_de_la_red", "summary_dynamit_std_t"), rtol=1e-9)
V.md_table(["Parámetro"] + [V.fmt(v, 1) for v in D["v_kn"]],
           [[lab] + [V.fmt(x, 1) for x in D[k]] for lab, k in
            (("AH [m]", "AH_m"), ("AV [m]", "AV_m"), ("DP [m]", "DP_m"), ("RA [kgf]", "RA_kg"))])
```

La captura dice "kg": en el contexto de una resistencia es kilogramo-fuerza (1 kgf = 9,81 N), la
misma unidad del libro.

## Qué se compara con qué

DynamiT entrega una sola cifra por variable y velocidad; el libro tiene varias, de naturaleza
distinta. Conviene ser explícito:

| DynamiT | Magnitud del motor (celda del libro) | Naturaleza |
|---|---|---|
| AH, abertura horizontal | **DPA de Fridman**, red estándar (`Mec!P164:P172`) | depende de $v$: equilibrio de portones, cables y red |
| | AH geométrica (`Dim!F61`) | fija: promedio de reglas geométricas |
| AV, abertura vertical | **AV de Fridman**, red estándar (`Mec!O272:O280`) | depende de $v$: ángulo de la brida por flotación y $R_N$ |
| | AV de Suzuki (`Mec!D255`) | fija: fracción de la circunferencia |
| DP, distancia entre portones | **$D_s$ desde la DPA de Fridman** (`Mec!L164:L172`) | depende de $v$: triángulos semejantes |
| | $D_s$ "al metro de cable" (`Port!E13`) | fija: $(2{,}65 - D_6)\,L_s + D_6$ |
| RA, resistencia | **$R_N$ de diseño**, Aberdeen demersal (`Res!N302:N310`) | red sola |
| | $R_T$ total (`Rem!H118:H126`) | red + boyas + cables (+ un portón en modo corregido) |

En `trawlkit` son, en el mismo orden, `spread.fridman.dpa_std_m`, `spread.horizontal_opening_m`,
`spread.vertical.fridman.std.av_m`, `spread.vertical.suzuki_m`,
`spread.table.door_spread_from_dpa_m`, `doors.spread_m`, `drag.rn.std` y `warps.total.std` del
`DesignResult`.

La captura no aclara si RA es la resistencia de la red o la del arte completo. Se la compara con
las dos, pero la lectura natural es la **red**: el autor la pegó en la tabla resumen de resistencia
de la red, junto a los trece métodos (`Res!S302:S310`), y ya es menor que la $R_N$ de la mayoría de
los métodos de superficie sólida; si incluyera dos portones (≈ 320 kgf a 3 kn según el motor) y los
cables, la red de DynamiT quedaría por debajo de todos ellos.

```{code-cell} ipython3
:tags: [hide-input]
def quantities(r):
    return {
        "AH": {"DPA Fridman": np.asarray(r.spread.fridman.dpa_std_m),
               "AH geométrica": np.full(9, r.spread.horizontal_opening_m)},
        "AV": {"AV Fridman": np.asarray(r.spread.vertical.fridman.std.av_m),
               "AV Suzuki": np.full(9, r.spread.vertical.suzuki_m)},
        "DP": {"Ds desde DPA Fridman": np.asarray(r.spread.table.door_spread_from_dpa_m),
               "Ds al metro de cable": np.full(9, r.doors.spread_m)},
        "RA": {"Rₙ diseño (Aberdeen)": np.asarray(r.drag.rn.std),
               "Rₜ total": np.asarray(r.warps.total.std)},
    }

QC, QE = quantities(C), quantities(E)
REF = {"AH": D["AH_m"], "AV": D["AV_m"], "DP": D["DP_m"], "RA": D["RA_kg"]}
UNIT = {"AH": "m", "AV": "m", "DP": "m", "RA": "kgf"}
band = (kn >= 2.0) & (kn <= 4.0)  # rango de pesca

rows = []
for var, ref in REF.items():
    for name in QC[var]:
        for mode, Q in (("corregido", QC), ("Excel", QE)):
            x = Q[var][name]
            e = x - ref
            p = e / ref * 100
            rows.append([var, name, mode, V.sfmt(p[band].mean(), 1),
                         f"{V.fmt(np.abs(e[band]).mean(), 1 if var != 'RA' else 0)} {UNIT[var]}",
                         V.fmt(np.abs(p[band]).mean(), 1), V.fmt(np.abs(p).mean(), 1)])
V.md_table(["DynamiT", "Magnitud del motor", "Modo", "Sesgo 2–4 kn [%]", "Error abs. 2–4 kn",
            "Error 2–4 kn [%]", "Error 1–5 kn [%]"], rows)
```

El **sesgo** es el promedio de (motor − DynamiT), con signo: positivo si el motor da más. El **error
medio** es el promedio de su valor absoluto. Los errores se resumen en el rango de pesca, 2–4 kn, y
en todo el rango, 1–5 kn, donde los extremos pesan mucho (a 1 kn la red está mal abierta en ambos
modelos).

## Comparación por velocidad

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      DynamiT (puntos) frente a `trawlkit`. Azul: magnitud dependiente de la velocidad (Fridman o
      Aberdeen); naranja: regla fija o resistencia total. Línea llena: modo corregido; trazos: modo
      Excel. La banda gris marca el rango de pesca, 2–4 kn.
    name: fig-32-dynamit
---
TITLES = {"AH": "Abertura horizontal [m]", "AV": "Abertura vertical [m]",
          "DP": "Distancia entre portones [m]", "RA": "Resistencia [kgf]"}
LEG = {"AH": "lower right", "AV": "upper right", "DP": "lower right", "RA": "upper left"}
fig, axes = plt.subplots(2, 2, figsize=(9.4, 7.2))
for ax, var in zip(axes.flat, REF):
    ax.axvspan(2.0, 4.0, color=V.GRID, alpha=0.45, lw=0, zorder=0)
    ax.plot(kn, REF[var], "o", color=V.INK, ms=5.5, mec=V.SURFACE, mew=1.2, zorder=4,
            label="DynamiT")
    for k, name in enumerate(QC[var]):
        col = V.SERIES[k]
        ax.plot(kn, QC[var][name], color=col, zorder=3, label=name)
        ax.plot(kn, QE[var][name], color=col, lw=1.1, ls=(0, (3, 2)), zorder=2)
    ax.legend(loc=LEG[var], fontsize=8.5, handlelength=1.6)
    ax.set_title(TITLES[var])
    ax.set_xlim(0.85, 5.15)
    ax.set_xticks(np.arange(1, 5.5, 1))
    ax.set_ylim(bottom=0)
for ax in axes[1]:
    ax.set_xlabel("Velocidad de arrastre [kn]")
fig.tight_layout(w_pad=2.0)
plt.show()
```

```{code-cell} ipython3
:tags: [hide-input]
lines = [("AH DynamiT [m]", D["AH_m"], 1), ("DPA Fridman [m]", QC["AH"]["DPA Fridman"], 1),
         ("AV DynamiT [m]", D["AV_m"], 1), ("AV Fridman [m]", QC["AV"]["AV Fridman"], 2),
         ("DP DynamiT [m]", D["DP_m"], 1), ("Ds Fridman [m]", QC["DP"]["Ds desde DPA Fridman"], 1),
         ("RA DynamiT [kgf]", D["RA_kg"], 0), ("Rₙ Aberdeen [kgf]", QC["RA"]["Rₙ diseño (Aberdeen)"], 0)]
rows = [[lab] + [V.fmt(x, nd) for x in arr] for lab, arr, nd in lines]
rows.append(["Δ Rₙ [%]"] + [V.pct_s(a, b) for a, b in zip(QC["RA"]["Rₙ diseño (Aberdeen)"], D["RA_kg"])])
V.md_table(["v [kn]"] + [V.fmt(v, 1) for v in kn], rows)
```

## ¿Qué método de resistencia se parece más a DynamiT?

La $R_N$ de diseño del libro es la de Aberdeen demersal, pero hay doce más ({doc}`14_resistencia`).
Con DynamiT como referencia se pueden ordenar:

```{code-cell} ipython3
:tags: [hide-input]
NAMES = {"tauti_nomura_shu": "Tauti, Nomura y Shu", "tauti_headrope": "Tauti (lima)",
         "tauti_footrope": "Tauti (burlón)", "koyama_1974": "Koyama 1974",
         "koyama_1984": "Koyama 1984", "hamuro": "Hamuro", "reid": "Reid",
         "robertson": "Robertson", "maclennan": "MacLennan",
         "aberdeen_demersal": "Aberdeen demersal (diseño)", "aberdeen_pelagic": "Aberdeen pelágica",
         "fridman": "Fridman", "dickson": "Dickson"}
ra = D["RA_kg"]
def score(r, m):
    x = np.asarray(r.drag.table.std[m]) * 1000
    p = (x - ra) / ra * 100
    return p.mean(), np.abs(p).mean(), np.abs(p[band]).mean()
sc = {m: (score(C, m), score(E, m)) for m in NAMES}
order = sorted(NAMES, key=lambda m: sc[m][0][1])
# exponente de velocidad de DynamiT: RA ∝ v^n
n_dyn = np.polyfit(np.log(kn), np.log(ra), 1)[0]
rows = []
for m in order:
    (bc, ac, gc), (be, ae, ge) = sc[m]
    name = f"**{NAMES[m]}**" if m == drag.DESIGN_METHOD else NAMES[m]
    rows.append([name, V.sfmt(bc, 1), V.fmt(ac, 1), V.fmt(gc, 1), V.fmt(ae, 1)])
V.md_table(["Método (red estándar)", "Sesgo corregido [%]", "Error medio corregido 1–5 kn [%]",
            "Error medio corregido 2–4 kn [%]", "Error medio Excel 1–5 kn [%]"], rows)
print(f"DynamiT: RA ∝ v^{n_dyn:.2f}".replace(".", ","))
```

## Discusión

**Resistencia.** La $R_N$ de diseño (Aberdeen demersal) queda **por encima** de DynamiT en todas
las velocidades: +18 % de promedio en modo corregido y +25 % en modo Excel. La diferencia es máxima
entre 1,5 y 2,5 kn (+23 a +26 % en modo corregido), donde el término constante de Aberdeen (el
rozamiento de las partes que arrastran por el fondo) todavía pesa, y baja a +9 % a 5 kn. Corregir
la superficie sólida de la bolsa acerca el libro a DynamiT en 6–7 puntos. Los métodos más cercanos a
la simulación son Reid en modo corregido, Robertson y Tauti con el burlón (errores medios de
14–17 % en 1–5 kn, 7–13 % en el rango de pesca); Reid sólo lo es una vez corregido el denominador
fijo (`reid_fixed_denominator`), que en el Excel le da un error medio del 55 %. La forma de la curva también dice
algo: DynamiT crece como $v^{1{,}48}$, muy cerca del exponente 1,45 de Tauti, Nomura y Shu y lejos
del $v^2$ de las fórmulas cuadráticas puras: la red se deforma y se alinea con el flujo al acelerar,
y un simulador de forma lo captura sin que nadie lo ajuste. Para el diseño, la elección de Aberdeen
es **conservadora**: ≈ 18 % más de resistencia equivale, en la ventana de {doc}`30_caso_beagle`, a
velocidades máximas algo menores que las que daría DynamiT.

**Abertura horizontal.** Es la variable en la que más coinciden. La AH geométrica del libro
(13,1 m) cae justo en la meseta que alcanza DynamiT a partir de 2,5 kn (12,9–13,6 m): error medio
del 2 % en el rango de pesca. La DPA de Fridman cruza a DynamiT a 3 kn, con sesgo medio menor al 1 %
y error medio del 7 % entre 2 y 4 kn, pero con otra pendiente: subestima a 2 kn (−12 %) y
sobrestima a 4 kn (+12 %). Fuera del rango las curvas se separan. Por debajo de 2 kn Fridman cierra
la red mucho más rápido que la simulación (6,0 frente a 8,9 m a 1 kn): su modelo supone portones,
cables y red alineados y tensos, y a baja velocidad la fuerza de los portones, que crece con $v^2$,
no alcanza para tensarlos. Por encima de 4 kn la DPA de Fridman sigue creciendo (16,1 m a 5 kn)
mientras DynamiT se estabiliza en 13,5 m: en la simulación las relingas y el paño, de largo fijo,
limitan la abertura; en la fórmula de Fridman nada la limita.

**Abertura vertical.** Ambos modelos coinciden en la tendencia —la red "se aplasta" al acelerar
porque la resistencia crece más rápido que la flotación— y en el orden de magnitud en el rango de
pesca (1,0–2,6 m). La AV de Fridman sobrestima 14–17 % entre 2 y 4 kn y no reproduce dos rasgos de
DynamiT: la gran abertura a 1 kn (6 m), donde la red casi no tiene tensión, y el **repunte** por
encima de 4 kn (1,0 → 1,6 m). Ese repunte es un efecto de forma que una fórmula de un ángulo de
brida no puede tener: con más velocidad cambia el reparto de tensiones entre la lima, las alas y las
bridas, o el burlón empieza a despegarse del fondo. La AV de Suzuki (1,98 m, error medio del 47 %)
es sólo un número de referencia para el plano.

**Distancia entre portones.** Es la mayor discrepancia. DynamiT separa los portones 47–52 m en el
rango de pesca; el libro, 32,5 m con la regla "al metro de cable" (−35 % de promedio) y 25–34 m con
la derivada de la DPA de Fridman (−40 %). Hay dos razones. La primera es de método: las dos reglas del libro
son geométricas o empíricas (cuánto se abre un portón genérico por metro de cable; triángulos
semejantes desde la DPA), mientras que DynamiT calcula la fuerza de abertura de **este** portón con
su polar. La segunda es de datos: no conocemos el cable filado ni la longitud de patentes de la
simulación, y la separación de portones es muy sensible a ambos. Es la variable en la que el
diseño final debería apoyarse en simulación o medición. Por suerte es también la que menos influye
en las demás etapas del libro, que usan $D_s$ sólo a través de los ángulos de los cables.

**Por qué discrepan.** El libro es una cadena de reglas empíricas, cada una ajustada sobre otras
redes y otros barcos, y evaluadas de forma independiente: la resistencia no "sabe" cuánto se abrió
la red ni la abertura cuánto se separaron los portones. DynamiT impone que todas las magnitudes
salgan de la misma forma de equilibrio. Donde el libro usa una fórmula basada en el mecanismo físico
dominante (la superficie sólida para la resistencia, el equilibrio de fuerzas de Fridman para la
DPA, el ángulo de la brida para la AV) las dos herramientas coinciden dentro del 2–20 % en el rango
de pesca; donde usa una regla práctica (separación de portones al metro de cable, AV como fracción
de la circunferencia), la discrepancia llega al 35–47 %.

**Limitaciones de esta comparación.** Una sola simulación, de autor y fecha no documentados en el
repositorio, sin los parámetros de aparejo (cable filado, patentes, portón, ángulo de ataque, tipo
de fondo) ni la versión de DynamiT; una sola red y una sola profundidad. Ninguno de los dos modelos
se comparó con mediciones en el mar.
