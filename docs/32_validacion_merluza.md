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

# Validación con redes de merluza

```{code-cell} ipython3
:tags: [remove-cell]
import sys, pathlib
sys.path[:0] = [str(pathlib.Path.cwd().parent), str(pathlib.Path.cwd())]
import numpy as np
import matplotlib.pyplot as plt
import _plots_v as V
import _hake as H
from trawlkit import fieldcheck as F
from trawlkit.io import load_net
from trawlkit.netcheck import check
V.setup_style()
PTS = H.points()  # corre el motor para cada lance y cada simulación (≈ 30 s)
```

## Propósito

{doc}`32_validacion_dynamit` compara el motor con una simulación de la red A-3 y
{doc}`26_aparejos_dobles_y_vara` con las simulaciones de las tangoneras de langostino del INIDEP.
Faltaba lo más importante: **redes de pescado medidas en el mar**. La merluza común
(*Merluccius hubbsi*) es la pesquería de arrastre de fondo más grande de la Argentina y el INIDEP
publica, para sus redes de campaña, el plano, el aparejo, simulaciones DynamiT y lances medidos con
sensores de telemetría (Simrad TV-80, PX, Scanmar): separación de portones (DP), abertura vertical
(AV) y, a veces, abertura entre puntas de ala (AH), con la profundidad, el cable filado y la
velocidad de cada lance.

Este capítulo digitaliza cinco redes de esas fuentes y compara el motor, **sin cambiar sus
métodos**, con 114 lances medidos, una media de campaña y seis simulaciones DynamiT. Los desvíos sistemáticos se describen con
números y se propone una calibración que **no se aplica**: queda para decidir.

## Las redes

```{code-cell} ipython3
:tags: [remove-input]
STATUS = {"published": "publicada", "draft": "borrador"}
rows = []
for nid in H.NETS:
    s = load_net(nid)
    err = sum(i.level == "error" for i in check(s))
    d = s.model_extra["design"]
    rows.append([H.SHORT[nid], STATUS[s.status], s.sources[0].key, len(s.panels),
                 V.fmt(s.headrope.length_m, 2), V.fmt(s.footrope.length_m, 2), str(err),
                 d["vessel_id"]])
V.md_table(["Red", "Estado", "Fuente", "Paños", "Lima [m]", "Burlón [m]", "Errores", "Buque"], rows)
```

- **VA-35,5/45 diseñada** {cite:p}`roth2017angelescu`: red de cuatro caras de PE diseñada por el
  INIDEP para el BIPO Víctor Angelescu (IAT 101/2017, fig. 2, plano vectorial con malleros, Ø del
  hilo, mallas y cortes). Cierra por largo estirado y se publica. DynamiT a 4 nudos, 100 m y 500 m
  de cable con portones Morgère SPF08 de 4,5 m² y 1200 kg (CL 1,00; CD 0,58), bridas de 50 m y
  patentes de 50 m.
- **VA-35,5/45 construida** {cite:p}`bartozzetti2018iat151`: la misma red tal como se armó (IAT
  151/2018, fig. 1): cambian las puntas de ala, el costado, el vientre (Ø4 mm) y el copo (hilo
  doble). La columna de malleros del vientre no está impresa (se suponen los del dorso). Aparejo:
  bridas de 50/48,5 m, patentes de 100 m, 90 boyas de 200 mm y 380 kg de cadena. Se publica. Trae
  tres series medidas y la simulación DynamiT a 400 m de {cite:t}`roth2025iat026`.
- **Engel 35,5 m** (IAT 101/2017, fig. 1): la red de las campañas de evaluación de merluza desde
  1993 (Holmberg, Oca Balda, Angelescu). **Borrador**: el plano conserva la cantidad de mallas al
  cambiar de mallero (194 de 200 mm sobre 194 de 160 mm, 160 de 160 mm sobre 160 de 120 mm),
  empalmes que no cierran por largo estirado (20–25 %), y no da el hilo ni el copo (supuestos:
  nylon de Ø3 mm y copo de 103 mm y 22 m de {cite:t}`pappi2024ic004`). Portones polivalentes de
  1200 kg y 5,58 m² {cite:p}`tringali2012eh0612`. El burlón difiere entre informes: 41,50 m en el
  plano, 50 m en EH 06/12, IC 004/24 e IC 041/25, 40,0 m en IC 019/13 {cite:p}`dato2013global` y
  40,3 m en el Inf. Téc. 66 {cite:p}`casarsa2007inftec66`; se usa el del plano.
- **Baldino «Beagle I» 46,4 m** {cite:p}`roth2019iat045`: red comercial de un arrastrero de Mar
  del Plata, redibujada por el INIDEP (original, fig. 2) y corregida (fig. 3). Las dos quedan como
  **borrador**: la original por las secciones que no empalman que señala el propio informe (134
  mallas de 140 mm sobre 100 de 120 mm, 36 %); la modificada porque su costado pasa de 30 a 45
  mallas de 200 mm entre dos secciones (33 %), como se lee la figura. El informe no da el buque,
  las malletas ni la superficie de los portones Mercury de 2300 kg (7,5 m² por la tabla de Polar,
  derivado).

Cada valor lleva su procedencia (transcripto, derivado o supuesto, con la página y la cita); lo
que viene de otro informe de la misma red (aparejo, mediciones) cita ese informe. El registro
detallado está en {doc}`catalogo_fuentes`.

## Qué se compara y con qué tolerancia

El motor corre el caso de cada red (`trawlkit.catalog.catalog_case`, modo corregido) con las
condiciones de cada lance o simulación (`trawlkit.fieldcheck.engine_point`):

- **profundidad** del lance y, cuando la fuente lo publica, su **cable filado**: el caso lo toma en
  `DesignCase.measured_warp_m` en lugar de la tabla cable/profundidad del libro (Mec!E177). Es una
  entrada, no un método nuevo: con `None`, el motor da lo mismo que antes;
- el **portón de la serie**, con su superficie y peso publicados y la polar publicada (CL y CD de
  IAT 101/2017 y de IAT 026/25) o, para los polivalentes, la hoja «Morgère Polyvalent Ovale» de
  Seafish (supuesta);
- las **patentes** de la serie cuando las da.

Las magnitudes son las del libro para redes de pescado, sin cambios: **DP** de la DPA de Fridman
promediada entre 2 y 4 kn y llevada a los portones (la regla de todo caso del catálogo); **AH**
del libro (`Dim!F61`, promedio de cuatro reglas); **AV** de Suzuki (`Mec!D255`, fija); y la
**resistencia total** (`Rem!H118` + dos portones) a la velocidad del lance, interpolada entre las
velocidades de cálculo. Las **tolerancias** declaradas son:

```{code-cell} ipython3
:tags: [remove-input]
NAMES = {"door_spread_m": "Separación de portones (DP)", "wing_spread_m": "Abertura entre alas (AH)",
         "vertical_opening_m": "Abertura vertical (AV)", "drag_kgf": "Resistencia total (R)"}
V.md_table(["Magnitud", "Tolerancia"],
           [[NAMES[k], f"± {V.fmt(100 * F.TOLERANCES[k], 0)} %"] for k in NAMES])
```

Son tolerancias de diseño: la DP y la AV medidas varían 8–9 % de lance a lance con el mismo
aparejo (coeficientes de variación de 0,081 y 0,087 en la tabla 1 de IAT 151/2018) y varios
portones no publican su polar. Los casos fuera de tolerancia van **en negrita** en las tablas.

## Frente a DynamiT

Cada celda es «motor / DynamiT (desvío)»:

```{code-cell} ipython3
:tags: [remove-input]
V.md_table(["Red", "Prof., cable, v", "DP [m]", "AH [m]", "AV [m]", "R [kgf]"], H.simulated_rows())
```

- **VA-35,5/45 a 100 m**: la AH (+3 %) y la AV (+7 %) caen dentro de la tolerancia; la DP queda un
  24 % por debajo y la resistencia total un 26 % por encima (la de la red sola, Aberdeen, da
  6072 kgf: −3 %; la diferencia son los portones y los cables que suma el libro, y DynamiT no
  aclara qué incluye su «resistencia total al avance»).
- **VA-35,5/45 a 400 m y 1200 m de cable** (portones SPF 08,5): la resistencia coincide (−2 %) y la
  AH queda dentro (−14 %), pero la DP es un 42 % menor y la AV de Suzuki, fija en 4,21 m, no baja a
  los 2,4 m de la simulación. El informe muestra que con esos portones la red se abre de más a
  gran profundidad (AH = 80 % de la lima): justo el régimen donde el motor menos se mueve.
- **Baldino 46,4 m**: el motor da una DP un 36–39 % menor que DynamiT, pero el informe no publica las
  malletas y el caso usa las 25 m del libro (`Dim!F65`). La DP del motor es proporcional al aparejo
  (DPA · (LRw + aparejo)/LRw): con 100 m de malletas daría 194 m, la de DynamiT. Sin el dato, no
  se puede decidir. La AH del libro (43 m, 0,93 de la lima) supera en 50–63 % a la de DynamiT: la
  DPA de Fridman con un portón de 7,5 m² supera a la lima (54 m a 4 kn), algo que la geometría de
  la red no permite y que ya se vio en {doc}`32_validacion_dynamit` por encima de 4 kn. La
  resistencia total queda 12–13 % por debajo.

## Frente a lo medido

Por serie: desvío medio del motor [mínimo; máximo] y fracción de lances dentro de la tolerancia.
Un asterisco en el cable indica que la fuente no lo publica y el motor usa el de su tabla:

```{code-cell} ipython3
:tags: [remove-input]
V.md_table(["Red", "Serie", "Lances", "Prof. [m]", "Cable [m]", "DP", "AH", "AV"], H.series_rows())
```

```{code-cell} ipython3
---
tags: [remove-input]
mystnb:
  figure:
    caption: |
      Separación de portones de la VA-35,5/45 contra el cable filado. Puntos: lances medidos
      (IAT 151/18 con polivalentes; IC 029/18 e IC 012/21 con SPF08) y la simulación DynamiT de
      IAT 026/25 (rombo). Cruces: el motor en las mismas condiciones (profundidad, cable,
      velocidad y portón de cada lance).
    name: fig-32m-dp-cable
---
fig, ax = plt.subplots(figsize=(8.6, 5.0))
for k, ser in enumerate(("iat151", "ic012", "ic029")):
    hv = H.hauls(ser)
    w = [p.warp_m for _, p in hv]
    ax.plot(w, [r["door_spread_m"] for r, _ in hv], "o", color=V.SERIES[k], ms=5, alpha=0.85,
            mec=V.SURFACE, mew=0.6, label=H.SERIES[ser][0] + " (medido)")
    ax.plot(w, [p.door_spread_m for _, p in hv], "x", color=V.SERIES[k], ms=5, alpha=0.9,
            label=H.SERIES[ser][0] + " (motor)")
sim = [(r, p) for nid, k, r, p in PTS if k == "simulated" and nid == "inidep_iat151_va355_construida"]
for r, p in sim:
    ax.plot(r["warp_m"], r["door_spread_m"], "D", color=V.INK, ms=7, label="DynamiT, IAT 026/25")
    ax.plot(p.warp_m, p.door_spread_m, "x", color=V.INK, ms=8, mew=2, label="motor, IAT 026/25")
ax.set_xlabel("Cable filado [m]")
ax.set_ylabel("Separación de portones [m]")
ax.set_ylim(bottom=0)
ax.legend(fontsize=8, ncol=2, loc="lower right")
fig.tight_layout()
plt.show()
```

### La red Engel, lance por lance

Los lances 17–28 de la campaña VA-05/2024 {cite:p}`rubio2024calibracion` son los únicos con AH
medida por sensores en las puntas de ala, a 21–24 m y a 105–117 m, con portones SPF 08,5 de 4,8 m²
(cada celda: motor / medido):

```{code-cell} ipython3
:tags: [remove-input]
V.md_table(["Lance", "Prof. [m]", "Cable [m]", "v [kn]", "DP [m]", "AH [m]", "AV [m]"],
           H.haul_rows("ic016"))
```

La AH del libro queda dentro de ±20 % en ocho de los nueve lances con sensores de ala (−5 % a
+13 %). El lance 18 da +20 %: es aquel en que el informe anota que «la distancia entre puntas de
alas, promedió los 15 m de abertura horizontal y por plano debería ser de 21 m» y cambia el
enganche de los portones (p. 12). La DP muestra el
mismo patrón que la VA: el motor la sobrestima con poco cable (+23 % a +47 % con 104–160 m, aunque
en los lances 17–19 el portón estaba enganchado para la «menor fuerza de expansión», pp. 11–12) y
la subestima con 351–403 m (−12 % a −16 %).

## Desvíos sistemáticos

**1. La separación de portones crece con el cable la mitad de rápido que la medida.** Con la
profundidad, el cable y el portón de cada lance, la pendiente de la DP del motor contra el cable
es una fracción de la medida en las tres series con cable publicado:

```{code-cell} ipython3
:tags: [remove-input]
V.md_table(["Red", "Serie", "Lances", "dDP/dcable medida", "dDP/dcable motor",
            "n medido (DP ∝ cableⁿ)", "n motor", "medido / motor"], H.warp_fit_rows())
FITS = H.warp_fits()
DN = float(np.mean([f["exp_measured"] - f["exp_engine"] for f in FITS]))
print(f"Δn medio = {DN:.2f}".replace(".", ","))
```

En la DPA de Fridman el cable entra arriba y abajo de la fracción
(`2·Lsh·LRw·Edy / (Lsh + Lnc·(1 + Edx))`), así que con cables largos la DP casi no cambia. En el
mar la DP sigue creciendo: 75 → 103 m entre 180 y 450 m de cable (IAT 151/18), 129 → 158 m entre
500 y 930 m (IC 029/18) y 162 m a 1200 m en DynamiT (IAT 026/25). Por eso el motor queda por
debajo con cable largo (−33 % en IC 029/18, −42 % frente a IAT 026/25) y por encima con cable corto
(Engel a 21 m: hasta +47 %).

**2. El nivel de la DP depende del portón, y la polar de los polivalentes no se publica.** Con
los SPF08 de superficie publicada (IC 012/21, 240–470 m de cable) el desvío medio es nulo y los
40 lances caen dentro de ±20 %. Con los polivalentes de 1200–1260 kg (superficie de 5,58 m² y polar
Morgère Polyvalent Ovale supuestas) el motor sobrestima: +26 % en IAT 151/18, +39 % en el Inf. Téc.
66 y +51 % frente a la media de IC 041/25 (estas dos sin cable publicado). Un CL de 1,18 a 32° es
más de lo que esos portones parecen dar en el mar.

**3. La abertura vertical de Suzuki es fija.** Es una fracción de la circunferencia de la red:
4,21 m en la VA construida y 3,76 m en la Engel, sin velocidad, boyas ni profundidad. Lo medido en
la VA baja de 4,9 m (35 m de profundidad) a 2,3 m (125–135 m): +14 % de promedio en IAT 151/18
(98 % de los lances dentro de ±30 %), +38 % en IC 012/21 y +62 % en IC 029/18. En la Engel, con
el doble de flotación por metro de lima, el motor queda por debajo (−13 % con sensores, −40 % con
el sonar de red de 2000). La AV de Fridman del libro, que sí depende de la velocidad, da 7–10 m y
no sirve de alternativa.

**4. La AH del libro acierta en la Engel con sensores y se pasa en la red grande.** +5 % de
promedio en IC 016/24 (ocho de nueve lances dentro de ±20 %) y +3 % frente a DynamiT en la VA a
100 m; +61 % frente al sonar del Inf. Téc. 66, donde también la DP sale +39 % por el portón
supuesto; +50 a +63 % en la red de 46,4 m, donde la DPA de Fridman supera la lima.

**5. Resistencia.** Sólo hay simulaciones: +26 % (VA, 100 m), −2 % (VA, 400 m) y −12 a −13 %
(Baldino). No se publicó ninguna tensión de cable medida para estas redes.

## Propuesta de calibración (no aplicada)

El motor no se cambió: los métodos del libro y los valores dorados quedan como están. Para que el
usuario decida, la calibración que sugieren estos datos es:

1. **Sensibilidad de la DP al cable**, sólo en modo corregido y para redes de pescado:
   $DP_{cal} = DP_{motor} \cdot (L_s / L_{s,ref})^{\Delta n}$, con $L_{s,ref}$ el cable de la tabla
   del libro para la profundidad del caso y $\Delta n$ la diferencia de exponentes de la tabla de
   arriba (0,10 a 0,37 según la serie; el promedio se imprime arriba). Con el cable de la tabla el
   factor vale 1 y el caso de diseño no cambia; sólo cambia la respuesta a un cable distinto.
2. **Portones polivalentes**: un CL efectivo menor que el de la hoja de Seafish a 32°, ajustado a
   los 52 lances de IAT 151/18 (con la hoja, lo medido es 0,80 veces lo que da el motor), o publicar la polar
   que use el INIDEP. Mientras tanto la superficie (5,58 m²) y la polar quedan como supuestos.
3. **AV**: ninguna regla del libro reproduce la caída con la profundidad; una corrección por la
   flotación (las boyas de la Engel y de la VA) necesita más series que las de este capítulo.

## Limitaciones

- Las mediciones no traen la velocidad de cada lance en IAT 151/18 (se usa la media de 3,8 kn), ni
  el cable en el Inf. Téc. 66 y en IC 041/25 (se usa la tabla del libro), ni la tensión de los
  cables en ningún caso.
- Los portones polivalentes del INIDEP no tienen superficie ni polar publicadas para todas las
  campañas; los SPF tienen CL y CD publicados para un ángulo y se suponen constantes.
- Los lances de IC 012/21 llevan dispositivos de selectividad (malla cuadrada, T90, grilla) y los
  de IC 016/24 cambian de enganche de portón entre lances.
- La Engel y las dos redes de Baldino son borradores: el motor las calcula, pero su resultado
  depende de las lecturas y los supuestos anotados.
