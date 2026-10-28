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

# Aparejos dobles y de vara

```{code-cell} ipython3
:tags: [remove-cell]
import dataclasses
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.cwd().parent))
sys.path.insert(0, str(pathlib.Path.cwd()))

from IPython.display import SVG, display
import _plots_t1 as P
from trawlkit.catalog import catalog_case
from trawlkit.cost import bill_of_materials
from trawlkit.drawing import rig_plan_svg
from trawlkit.io import load_net
from trawlkit.model import run
from trawlkit.netcheck import check
from trawlkit.rigging import multirig as M
from trawlkit.rigging import shrimp as SH
from trawlkit.sim import simulate

P.setup_style()


def f(x, nd=1):
    return P.fmt(float(x), nd)
```

## Propósito

El libro original calcula **una** red remolcada con su par de portones. Muchas pesquerías no
trabajan así. La flota langostinera argentina remolca **dos redes desde los tangones**, una por
banda, cada una con sus portones (Res. CFP 7/2018, art. 4: los tangoneros «deberán operar con
tangones con redes langostineras» {cite:p}`cfp2018res7`). En el Mar del Norte y en el Atlántico
norte son comunes el **aparejo gemelo**, dos redes lado a lado con un muerto central, y el
**arrastre de vara**, en el que una vara rígida fija la abertura de la red. Este capítulo muestra
cómo `trawlkit` calcula esos tres aparejos (Fase 19.5), de qué fuente sale cada valor y dónde
están los límites del cálculo.

## Tres aparejos

**Tangones** (`rig: outrigger`). Dos redes iguales, una desde la punta de cada tangón. En el golfo
de México los tangones medían «usualmente 24 pies» y pescaban a unos 20° sobre la horizontal, con
las pastecas a 10–12 pies sobre el agua; cada red lleva «un solo cable con una brida» hacia los dos
portones y una red se cala unas 25 brazas más a popa que la otra para que no se enreden
{cite:p}`knake1958`. En el tangonero argentino la brida es la **tijera**: en las simulaciones del
INIDEP, 70 m de cable de acero de 22 mm, con cable de remolque de 24 mm y portones planos de
madera de 540 kg a 3,5 nudos {cite:p}`roth2022ito043`.

**Gemelo** (`rig: twin`). Dos redes lado a lado remolcadas por dos cables: los portones van por
fuera y las puntas de ala interiores se unen a un **muerto** o trineo central sin sustentación
{cite:p}`bullisfloyd1972,arkley1987ir1310`. Cada portón abre una red contra el muerto. Bullis y
Floyd describen un trineo de 6 pies de largo, 32 pulgadas de alto atrás y un patín de acero de
8 pulgadas, y señalan que «dos redes de 35 pies se abren con un solo par de portones de 7 pies;
una red de 70 pies requeriría portones de 10 a 12 pies». Para el peso del muerto la base de datos
de artes de Seafish da una **regla práctica**: alrededor de 1,5 veces el peso de un portón
{cite:p}`seafishtwinrig`. Arkley probó un trineo de 125 kg con portones en V de 6 pies.

**Vara** (`rig: beam`). Una vara apoyada en dos patines fija la abertura horizontal; no hay
portones. La resistencia es la de la red más la de la vara, los patines, el tren y las cadenas
espantadoras (*tickler chains*). Wageningen Marine Research midió las dimensiones de la flota
holandesa y estimó el arrastre de cada componente {cite:p}`rijnsdorp2020c056`: varas de 12 m y
Ø0,24 m en los buques de más de 221 kW y de 4,5 m y Ø0,15 m en los menores; patines de 0,063 y
0,054 m² de área frontal y 0,70 y 0,60 m de alto. El ancho de las varas crece con la potencia
según Eigaard et al. {cite:p}`eigaard2016`, que también observan que lo habitual es remolcar dos
varas, una desde cada tangón, y que las varas de camarón no llevan cadenas espantadoras. Verhoest y
Maton describen la vara doble belga de camarón de 8 m, con los tangones a unos 30° de la
horizontal {cite:p}`verhoest1964`.

## Cómo los calcula el motor

Las etapas del libro siguen calculando **una red** con sus portones (geometría, dimensiones,
resistencia, flotación, lastre y cables). Una etapa nueva, `RigStage` (`result.multirig`), cuenta
las piezas de cada aparejo y arma la resistencia de todo el arte:

* **tangones**: por red, RN + boyas + dos portones + un cable + las dos ramas de la tijera; el
  buque remolca dos;
* **gemelo**: por red, RN + boyas + un portón + un cable + medio muerto (arrastre de un trineo de
  área frontal $A$ con $C_D = 1{,}05$, el del patín de la vara); la separación de cada red es la de
  portón a muerto;
* **vara**: por vara, RN + vara ($C_D = 1{,}1$, área $d \cdot L$) + dos patines ($C_D = 1{,}05$)
  + tren y cadenas (arrastre por metro de vara de la tabla 9 de C056/20 escalado con $v^2$); sin
  portones ni boyas (la lima va a la vara).

La demanda frente al tiro del buque es $n_\text{redes}$ veces la de una red más el rozamiento con
el fondo (tren de cada red, portones, muerto o patines). Cada cable se dimensiona con lo que
remolca: una red con tangones y varas; todo el arte en el gemelo, como el libro con sus dos
cables. El **ancho barrido** es, con tangones, de portón exterior a portón exterior: cada red
centrada detrás de la punta de su tangón, que está a $L\cos\theta$ de la crujía.

Los valores por defecto sólo salen de las fuentes; todo lo demás es una entrada del caso:

```{code-cell} ipython3
P.md_table(
    ["Dato", "Valor por defecto", "Fuente"],
    [
        ["Largo del tangón", f"{f(M.BOOM_LENGTH_M, 2)} m (24 pies)", "Knake et al. 1958, p. 3"],
        ["Ángulo del tangón", f"{f(M.BOOM_ANGLE_DEG, 0)}° (vara: {f(M.BEAM_BOOM_ANGLE_DEG, 0)}°)",
         "Knake et al. 1958, p. 5; Verhoest y Maton 1964"],
        ["Tijera", f"{f(M.OUTRIGGER_BRIDLE_M, 0)} m de Ø{f(M.OUTRIGGER_BRIDLE_DIAMETER_MM, 0)} mm",
         "Roth y Rubio 2022 (INIDEP)"],
        ["Muerto del gemelo", f"{f(M.CLUMP_DOOR_RATIO, 1)} × un portón (regla práctica)",
         "Seafish"],
        ["Área frontal del muerto", f"{f(M.SLED_FRONTAL_M2, 3)} m² (32 × 8 pulgadas, supuesto)",
         "Bullis y Floyd 1972, p. 27"],
        ["Portón por pie de relinga", "70–80 pulg²/pie (0,148–0,169 m²/m), abertura 70–75 %",
         "Watson et al. 1984"],
        ["Varas por buque", str(M.BEAMS_PER_VESSEL), "Eigaard et al. 2016, p. i29"],
        ["Ancho de las varas", "1,4812·kW^0,4578 (camarón); 0,6601·kW^0,5078 (peces)",
         "Eigaard et al. 2016, tabla 4"],
        ["Vara, patines y cadenas", "por clase de buque (≤ 221 kW y > 221 kW)",
         "Rijnsdorp et al. 2020, tablas 2, 3, 8 y 9"],
    ],
)
```

El caso los acepta como parámetros (`boom_length_m`, `boom_angle_deg`, `outrigger_bridle_m`,
`clump_weight_kg`, `beam_count`, `beam_length_m`, `beam_ticklers`, `beam_weight_kg`, `opening_method`,
`shrimp_bridle_m`…); en la app,
el selector **Aparejo** del panel del caso y del modo guiado sigue por defecto el de la red y los
parámetros se editan en «Parámetros avanzados».

## Aberturas de las redes camaroneras

El promedio de aberturas del libro (`Dim!F61`) promedia cuatro DPA (por ángulo de corte,
geométrica, geométrica con la red trabajando y la serie de Fridman) y la separación de portones
sale del cable filado: está pensado para redes de pescado remolcadas con patentes largas. En la
red tangonera del INIDEP los dos términos geométricos ya dan los 14 m de DynamiT, pero la DPA por
ángulo de corte ($2 b U_2 \tan\alpha$) da 60 m y la separación de portones crece con el cable. Con
**tijera** eso no pasa: «la separación entre portones no puede ser modificada con la longitud del
cable de arrastre filado» {cite:p}`roth2016iat072`. Por eso, con `opening_method="auto"` (por
defecto), los aparejos de tangones y gemelo usan el **método camaronero**
(`trawlkit.rigging.shrimp`, Fase 19.7b); `opening_method="book"` vuelve al promedio del libro y
`"shrimp"` lo fuerza, por ejemplo en una red camaronera con portones. Las redes con portones (aun
las de crustáceos, como la de langostilla de la A-3), la pareja y la vara no cambian, y tampoco el
modo Excel del libro.

**Separación de portones con tijera.** Equilibrio plano de un portón colgado de una rama de la
tijera {cite:p}`roth2016iat072` (ecs. 13–17, con la proyección corregida):

$$
\beta = \arcsin\!\left(\frac{L_C}{L_R}\sin\alpha\right),\qquad
T\cos\alpha = F_{CD} + \tfrac{R}{2}\cos\beta,\qquad
F_{CL} = T\sin\alpha + \tfrac{R}{2}\sin\beta,\qquad
DP = 2\,L_C\sin\alpha
$$

$F_{CL}$ y $F_{CD}$ son la sustentación y la resistencia de un portón (polar del caso), $R$ la RN
de diseño de la red a la velocidad de diseño (3,5 nudos, la de las simulaciones del INIDEP),
$L_C$ la rama de la tijera (`outrigger_bridle_m`: 70 m por defecto; 55–73 m en los informes del
INIDEP) y $L_R$ el tramo del portón al punto donde converge la red: cañas + pie de gallo + 0,90 ×
el largo estirado de la red sin copo (punta de ala → copo). El 0,90 es la forma de malla de
referencia de DynamiT a lo largo (derivada de la columna «Length ratio» de sus tablas de cabos,
ver el caso argentino). Las **cañas** valen 3 m por defecto (IAT 85/2024 {cite:p}`roth2024iat085`
e ITO 61/2022 {cite:p}`roth2022ito061`; 2,5–4 m en los demás aparejos del INIDEP, supuesto) y se
cambian con `shrimp_bridle_m`. α se busca por bisección.

**Corrección de la ec. (12) de Roth.** La ecuación impresa es
$F_{CL} - (F_{CD} + R/2)\sin 2\alpha + (R/2)\sin 2\beta = 0$: proyecta dos veces las componentes
de las ecs. 5–8 y da $2\sin\alpha\cos\alpha$ donde va $\sin\alpha$. Con los datos de ITO 043/2022
(4,08 m², $C_L/C_D$ = 0,93/0,71, $R$ = 3777 − 2·$F_{CD}$, $L_C$ = 70 m) la forma impresa da
separaciones que ningún tangonero tiene; la corregida encierra los 16,2 m de DynamiT:

```{code-cell} ipython3
import math
from trawlkit.rigging.doors import door_forces_kgf
from trawlkit.units import KNOT_TO_MS

fz = door_forces_kgf(4.08, 0.71, 0.93, 3.5 * KNOT_TO_MS)
FL, FD = float(fz.lift_kgf), float(fz.drag_kgf)
RN = 3777.2 - 2 * FD


def printed_eq12(lc, lr):
    """DP con la ec. (12) impresa (raíz por barrido de α)."""
    amax = math.asin(min(1.0, lr / lc))
    g = lambda a: FL - (FD + RN / 2) * math.sin(2 * a) + (RN / 2) * math.sin(
        2 * math.asin(min(1.0, lc / lr * math.sin(a))))
    xs = [amax * k / 4000 for k in range(1, 4000)]
    for a, b in zip(xs, xs[1:]):
        if g(a) * g(b) < 0:
            return 2 * lc * math.sin(0.5 * (a + b))
    return float("nan")


P.md_table(
    ["L_R [m]", "DP, ec. (12) impresa [m]", "DP, equilibrio corregido [m]", "DynamiT [m]"],
    [[f(lr, 0), f(printed_eq12(70.0, lr)), f(SH.tijera_balance(FL, FD, RN, 70.0, lr).spread_m),
      "16,2"] for lr in (20.0, 25.0, 30.0, 35.0)],
)
```

Roth informa un acuerdo de 0,6 m con DynamiT para su ejemplo de 22 m (tabla 1), pero no imprime
$L_C$ ni los datos del portón, así que ese resultado no se pudo reproducir.

**Abertura horizontal.** $AH = DP \cdot L_{Rw} / (L_{Rw} + \text{pie de gallo} + \text{cañas})$: la
razón de triángulos semejantes del libro (Mec!L225, sin el redondeo) con las cañas cortas en lugar
de las patentes de 25 m. Se controla $AH/DP$ contra 0,72–0,88, el rango de las simulaciones
DynamiT del INIDEP con tijera (ITO 043, IAT 85, 104 y 111; derivado de sus tablas). La DPA por
ángulo de corte y la serie de Fridman salen del promedio.

**Respaldo sin tijera** (gemelo, portones, o si el equilibrio no tiene solución):
$AH = k \cdot \text{lima}$ con la DP del libro y $k$ por familia:

```{code-cell} ipython3
fam = {"inidep_dynamit": "Tangonera argentina de baja abertura (DynamiT)",
       "us_conventional": "Camaronera convencional de EE. UU., sin boyas (medida)",
       "tongue": "Red de lengüeta, Mongoose, Cobra (medida)"}
P.md_table(
    ["Familia", "k", "Rango", "Fuente"],
    [[fam[h.key], f(h.k, 2), f"{f(h.low, 2)}–{f(h.high, 2)}", h.source]
     for h in SH.HEADROPE_K.values()],
)
```

Las fuentes no coinciden y el motor lo dice en las notas de cada corrida. Las simulaciones DynamiT
de tangoneras argentinas dan $AH/\text{lima}$ = 0,36–0,50; la separación de portones **medida**
con sensores Simrad en la red Iberconsa de 25,4 m es 18,8–19,5 m, 0,74–0,77 × la lima
{cite:p}`roth2024iat094`, y el propio INIDEP considera que su AH simulada queda «muy por debajo del
valor recomendado (aproximadamente 70 %)» {cite:p}`roth2024iat085`. Las mediciones con buzos de
Watson et al. {cite:p}`watson1984` y Harrington et al. {cite:p}`harrington1988` dan 0,62–0,78 en
las camaroneras convencionales de EE. UU. DynamiT puede estar sesgado hacia abajo: la única
comparación medida/simulada (Iberconsa) no usa los mismos portones (Bison de 400 kg con doble
tobera en el mar; planos de 500 kg y 4,5 m² en el simulador).

**Abertura vertical.** $AV = 0{,}04 \cdot \text{lima}$ (0,03–0,07) en redes de baja abertura con
pocas boyas o ninguna: 0,026–0,049 en DynamiT y 0,029–0,080 en las mediciones de Watson et al. y
Harrington et al. No se corrige por boyas: la tabla 3 de Watson et al. muestra que 10–20 boyas
multiplican la AV por 1,75–2,9, pero no da una relación continua, y la cantidad de boyas del motor
es la que calcula el libro, no la de la red. La AV de Suzuki (4/90 de la circunferencia) da 3,2 m
en la red del INIDEP, 2,5 veces la de DynamiT. El límite de 1,5 m de la Res. CFP 7/2018 se controla
con esta AV.

**Profundidad de diseño.** La flota langostinera pesca a 71–87 m (IC 68/2022
{cite:p}`rubio2022ic068`) y a 86–106 m (IAT 94/2024); las simulaciones DynamiT de tangoneras del
INIDEP usan 100 m. Las redes de langostino cuya fuente no da la profundidad toman 90 m (rango
70–110 m, `trawlkit.catalog.LANGOSTINO_DEPTH_M`; valor elegido dentro de ese rango); las demás
redes de fondo siguen con 30 m. Con tijera la profundidad cambia el cable y su tensión, no la DP.

### Validación

El motor completo con las dos redes de ITO 043/2022 del catálogo (antes: promedio del libro;
después: método camaronero) frente a DynamiT, y el equilibrio aislado con los datos publicados de
cada simulación del INIDEP ($R$ = tensión − 2·$F_{CD}$; $L_R$ del plano digitalizado o estimado,
A VERIFICAR):

```{code-cell} ipython3
rows = []
for nid, sim in (("inidep_ito043_tangonera_inidep", "ito043_sim3"),
                 ("inidep_ito043_tangonera_empresa", "ito043_sim2")):
    case = catalog_case(nid).case
    before = run(dataclasses.replace(case, opening_method="book"))
    after = run(case)
    dc = next(c for c in SH.DYNAMIT_CASES if c.key == sim)
    rows.append([
        f"`{nid}` (motor)",
        f"{f(before.doors.spread_m)} / {f(before.spread.horizontal_opening_m)} / "
        f"{f(before.spread.vertical_opening_m, 2)}",
        f"{f(after.doors.spread_m)} / {f(after.spread.horizontal_opening_m)} / "
        f"{f(after.spread.vertical_opening_m, 2)}",
        f"{f(dc.dynamit_spread_m)} / {f(dc.dynamit_ah_m)} / "
        + ("1,3" if sim == "ito043_sim3" else "1,5"),
        f"{f(100 * (after.doors.spread_m / dc.dynamit_spread_m - 1), 0)} %",
        "—",
    ])
for dc in SH.DYNAMIT_CASES:
    b = SH.dynamit_case_balance(dc)
    rows.append([
        f"{dc.label} (equilibrio, L_R {f(dc.net_leg_m)} m"
        + (", estimado" if dc.net_leg_kind == "assumed" else "") + ")",
        "—",
        f(b.spread_m),
        f(dc.dynamit_spread_m),
        f"{f(100 * (b.spread_m / dc.dynamit_spread_m - 1), 0)} %",
        "18,8–19,5 (IAT 94/2024)" if dc.key == "iat085_iberconsa" else "—",
    ])
P.md_table(
    ["Caso", "Antes: DP / AH / AV [m]", "Método camaronero", "DynamiT", "DP − DynamiT",
     "DP medida [m]"],
    rows,
)
```

El motor completo queda dentro del 15 % de la DP y del 10 % de la AH de DynamiT en las dos redes;
antes, la DP salía de 3,6 a 3,9 veces mayor. El equilibrio aislado queda dentro de ±20 % en los
cuatro casos del informe de la fase (ITO 043 sims. 1 y 3, IAT 85 Iberconsa, IAT 111 Morales), la
tolerancia que fijan los tests mientras $L_R$ no salga de un plano digitalizado; la sim. 2 con el
equilibrio aislado (menos tensión con casi la misma $L_R$) da +26 %. La DP medida de la red Iberconsa
(18,8–19,5 m, otros portones y tijera de 60 m) queda por encima de DynamiT y del equilibrio:
coherente con el sesgo de DynamiT señalado arriba.

## Caso argentino: la red tangonera del INIDEP

El INIDEP evaluó en DynamiT una red tangonera propuesta por la empresa Pesquera Deseado y una red
propia {cite:p}`roth2022ito043`. Sus figuras 5 (red del INIDEP) y 4 (red de la empresa con hilo de
3 mm) están en el catálogo como `inidep_ito043_tangonera_inidep` y
`inidep_ito043_tangonera_empresa`, digitalizadas con la procedencia de cada valor, y están
**publicadas** desde la Fase 19.7c. La relectura de los planos mostró que el copo de dos caras
(2 × 100 mallas de 60 mm = 12,0 m) coincide con la suma de los bordes de bolsa del dorso y del
vientre (4,80 + 7,32 = 12,12 m en la fig. 5; 4,80 + 7,42 = 12,22 m en la fig. 4) y que cada
costado termina antes del copo, fruncido en un cabo de 0,50 m (N en la fig. 5, L en la fig. 4) que
cierra en las costuras. La columna «Length ratio» de la tabla de cabos de DynamiT lo confirma
(regla derivada: largo del cabo sobre el borde del paño a la forma de malla de referencia, 0,90 a
lo largo y 0,436 a lo ancho; para N, 0,50 / (17 × 0,14 × 0,436) = 0,48, lo impreso). El
validador compara entonces la circunferencia y no cara por cara (aviso `codend_join`): cara por
cara la unión no es 1:1 y el plano no dice cómo se reparte la diferencia. Quedan como avisos tres
rótulos de corte que no dan el cambio de ancho de su paño (se transcriben como se leen) y los
costados, que el motor reparte por largo estirado.

```{code-cell} ipython3
spec = load_net("inidep_ito043_tangonera_inidep")
P.md_table(
    ["Nivel", "Código", "Problema"],
    [[i.level, i.code, i.message] for i in check(spec)],
)
```

La red dice con qué buque y portón se calcula: el **tangonero típico** de la flota (media de
1998, {doc}`39_flota_argentina`), porque el informe no publica la eslora ni la potencia del
B/P *Atlántico 1*, y un portón plano de 4,08 m², el área de los portones de 530 kg del mismo
aparejo de la empresa en IAT 75/2023 {cite:p}`roth2023iat075`, con la proporción del portón plano
genérico del catálogo (2,86 × 1,43 m; supuesto, ITO 043 no publica las medidas). La profundidad
tampoco está en el informe: 90 m, la de la flota langostinera. Todo queda en las notas del caso.

```{code-cell} ipython3
cc = catalog_case(spec)
r = run(cc.case)
r_book = run(dataclasses.replace(cc.case, opening_method="book"))
mr = r.multirig
i = r.case.speed_index(3.5)
P.md_table(
    ["Resultado a 3,5 nudos", "Libro", "Método camaronero", "DynamiT (INIDEP, sim. 3)"],
    [
        ["Abertura horizontal AH [m]", f(r_book.spread.horizontal_opening_m),
         f(r.spread.horizontal_opening_m), "14,0"],
        ["Separación de portones de una red [m]", f(r_book.doors.spread_m), f(r.doors.spread_m),
         "16,2"],
        ["Abertura vertical AV [m]", f(r_book.spread.vertical_opening_m, 2),
         f(r.spread.vertical_opening_m, 2), "1,3"],
        ["Una red con su aparejo [kgf]", f(r_book.multirig.per_net.std[i], 0),
         f(mr.per_net.std[i], 0), "3777 (tensión del cable)"],
        ["Las dos redes y el rozamiento [kgf]", f(r_book.multirig.demand.std[i], 0),
         f(mr.demand.std[i], 0), "—"],
        ["Ancho barrido [m]", f(r_book.multirig.swept_width_m), f(mr.swept_width_m), "—"],
    ],
)
```

La resistencia de una red con su aparejo no depende del método de aberturas y queda a menos de un
20 % de la tensión del cable de DynamiT (el motor la calcula a 90 m, con más cable). Las notas de la corrida
dicen qué método se usó, con qué datos y en qué rango quedan las aberturas; el límite de la
Res. CFP 7/2018 para la abertura vertical (1,5 m) se controla con la AV del método:

```{code-cell} ipython3
for n in r.notes:
    if n.startswith(("shrimp_opening", "cfp_res7_2018", "multirig_overlap", "watson_door_area")):
        print(n)
```

Con los tangones de 24 pies de la fuente norteamericana las dos redes de esta separación se
superponen: la nota dice qué largo de tangón haría falta o, como en el golfo de México, que hay que
desfasar las redes. El largo de los tangones argentinos no está publicado; se cambia con
`boom_length_m`:

```{code-cell} ipython3
need = M.boom_length_without_overlap_m(r.doors.spread_m, M.BOOM_ANGLE_DEG)
r_long = run(dataclasses.replace(cc.case, boom_length_m=round(need + 1.0, 1)))
lay = r_long.multirig.layout
print(f"tangón de {f(r_long.case.boom_length_m)} m: punta a {f(lay.tip_offset_m)} m de la crujía, "
      f"huelgo entre redes {f(lay.gap_m)} m, ancho barrido {f(lay.swept_width_m)} m")
display(SVG(rig_plan_svg(r_long)))
```

La lista de materiales cuenta dos redes, cuatro portones, dos tijeras y dos cables:

```{code-cell} ipython3
bom = bill_of_materials(r)
P.md_table(
    ["Línea", "Cantidad", "Unidad"],
    [[ln.label, f(ln.quantity, 1), ln.unit] for ln in bom.lines],
)
```

## Caso gemelo

La red de arrastre de fondo de 2 paneles del Fisherman's Workbook (50–70 hp) en aparejo gemelo:
dos redes iguales, los portones del plano (1,30 × 0,65 m, 50 kg) afuera y un muerto de 75 kg
(1,5 portones) en el medio.

```{code-cell} ipython3
single = run(catalog_case("fao_wb_bt2p_60hp").case)
twin = run(catalog_case("fao_wb_bt2p_60hp", rig="twin").case)
j = twin.case.speed_index(3.0)
mt = twin.multirig
P.md_table(
    ["A 3 nudos", "Una red con portones", "Gemelo (dos redes)"],
    [
        ["Resistencia total [kgf]", f(single.performance.demand.std[j], 0), f(mt.demand.std[j], 0)],
        ["Ancho barrido [m]", f(single.doors.spread_m), f(mt.swept_width_m)],
        ["Portones", "2", str(mt.n_doors)],
        ["Muerto [kg]", "—", f(mt.clump_weight_kg, 0)],
        ["Arrastre del muerto [kgf]", "—", f(mt.clump_drag_kgf[j], 1)],
        ["Velocidad máxima [kn]", f(single.performance.design.max_speed_kn, 2),
         f(twin.performance.design.max_speed_kn, 2)],
    ],
)
```

Con dos redes del mismo tamaño el buque arrastra casi el doble y barre el doble de ancho; el par de
portones es el mismo. Por eso el gemelo se usa con redes más chicas que la que el buque llevaría
sola (Bullis y Floyd: dos de 35 pies en vez de una de 70).

## Caso de vara

La red de vara para camarón n.º 03 del catálogo tailandés de la SEAFDEC {cite:p}`seafdec2016thai`
(17 m, 235 hp) está en el catálogo como borrador: el copo de 32 mm se une 1:1 al cuerpo de 51 mm,
como dibuja el plano, y ese empalme no cierra en largo estirado. El plano no da la vara ni los
patines: el caso toma el ancho de Eigaard et al. para 175 kW (camarón, dos varas) y la vara y los
patines de los buques chicos de C056/20.

```{code-cell} ipython3
rb = run(catalog_case("seafdec_03_beam_shrimp").case)
mb = rb.multirig
k = rb.case.speed_index(3.0)
bd = mb.beam
P.md_table(
    ["Componente (una vara, 3 nudos)", "kgf"],
    [
        ["Red (RN de diseño)", f(rb.drag.rn.std[k], 1)],
        ["Red por la ec. 10 de C056/20 (comparación)", f(bd.net_c056_kgf[k], 1)],
        ["Vara", f(bd.beam_kgf[k], 1)],
        ["Patines", f(bd.shoes_kgf[k], 1)],
        ["Tren", f(bd.ground_gear_kgf[k], 1)],
        ["Cadenas espantadoras", f(bd.ticklers_kgf[k], 1)],
        ["Una vara con su red y su cable", f(mb.per_net.std[k], 1)],
        ["Las dos varas", f(mb.demand.std[k], 1)],
    ],
)
print(f"vara de {f(bd.beam_length_m, 2)} m, abertura vertical {f(mb.vertical_opening_m, 2)} m, "
      f"ancho barrido {f(mb.swept_width_m)} m")
```

**Contraste con una medición.** Depestele et al. {cite:p}`depestele2016` estimaron la resistencia
de una vara de tickler de 4,4 m a 4,4 nudos (paños inferiores, cadenas y patines). Con los datos
por metro de C056/20 para la clase chica escalados a ese ancho y esa velocidad:

```{code-cell} ipython3
chk = M.depestele_check("small")
P.md_table(
    ["Componente", "C056/20 escalado [N]", "Depestele et al. 2016 [N]", "Cociente"],
    [
        ["Paños inferiores", f(chk.netting_n, 0), f(chk.measured["lower_netting_n"], 0),
         f(chk.ratio("netting"), 2)],
        ["Cadenas (tickler y tren)", f(chk.chains_n, 0), f(chk.measured["chains_n"], 0),
         f(chk.ratio("chains"), 2)],
        ["Patines", f(chk.shoes_n, 0), f(chk.measured["shoes_n"], 0), f(chk.ratio("shoes"), 2)],
        ["Total", f(chk.total_n, 0), f(chk.measured["total_n"], 0), f(chk.ratio("total"), 2)],
    ],
)
```

Las cadenas coinciden dentro del 1 % y el total dentro del 20 %; los paños de Depestele son de hilo
más fino («much lower hydrodynamic drag») y sus patines, de 0,72 m² de suela, más grandes que los
de la tabla 2 de C056/20. Los tests del paquete fijan estas tolerancias (cadenas ±10 %, total
±25 %). Ambas son estimaciones de modelo, no tiros medidos con dinamómetro: no se encontró una
medición publicada de la tensión del cable de una vara.

## Simulación

El simulador resuelve **una** red con sus puntos de remolque fijos y la vista 3D la replica: con
tangones, centrada detrás de cada punta; en el gemelo, a cada lado del muerto (los puntos de
remolque de la red simulada son el portón y el muerto; la red queda simétrica respecto de su eje y
el muerto, en el fondo, no tiene sustentación); en la vara, las puntas de la lima quedan fijas en
los extremos de la vara a la altura del patín y las del burlón en los patines. Los portones
acoplados (cable hasta el buque) no se usan con estos aparejos.

```{code-cell} ipython3
sim = simulate(rb, 3.0, resolution=3)
print(f"vara simulada: converge {sim.converged}, AH {f(sim.ah_m, 2)} m, "
      f"red {f(sim.drag_kgf, 0)} kgf × {sim.rig['n_nets']} = {f(sim.rig['drag_kgf'], 0)} kgf")
```

## Límites

* Las aberturas de las redes camaroneras salen del método de la Fase 19.7b, calibrado con
  simulaciones DynamiT del INIDEP y contrastado con una sola serie medida (separación de portones,
  IAT 94/2024); no hay una AH medida de una tangonera argentina publicada. Su validez: tijera de
  55–73 m, portones planos o Bison de 300–600 kg, lima de 11–40 m, 2,5–4 nudos y 30–110 m. El
  largo $L_R$ y las cañas son derivados o supuestos; la tolerancia es ±20 % en la DP.
* Con tangones el resto de la geometría de cada red (cable, flecha, bridas del libro) se calcula
  como la de un arrastre con portones del libro; la tijera suma su arrastre y fija la DP. Las redes se suponen centradas
  detrás de la punta de su tangón; no se modela el desfase a popa.
* El muerto del gemelo es una regla práctica (1,5 portones) y su arrastre, el de un trineo de las
  medidas de Bullis y Floyd: no hay una fórmula de diseño publicada.
* La vara toma el tren y las cadenas por metro de la flota holandesa (C056/20); no hay datos de las
  varas tailandesas ni argentinas. Sin el peso de la vara (`beam_weight_kg`) no hay rozamiento de
  los patines.
* No se encontraron publicados el largo ni el ángulo de los tangones argentinos, ni la potencia del
  B/P *Atlántico 1*.

## Redes digitalizadas

| Red | Fuente | Aparejo | Estado |
|---|---|---|---|
| `inidep_ito043_tangonera_inidep` | INIDEP ITO 043/2022, fig. 5 {cite:p}`roth2022ito043` | tangones | publicada |
| `inidep_ito043_tangonera_empresa` | INIDEP ITO 043/2022, fig. 4 | tangones | publicada |
| `seafdec_03_beam_shrimp` | SEAFDEC 2016, plano 03 {cite:p}`seafdec2016thai` | vara | borrador |
| `seafdec_31_outrigger_shrimp` | SEAFDEC 2016, plano 31 (14 m, 75 hp) | tangones | publicada |
| `seafdec_33_outrigger_shrimp` | SEAFDEC 2016, plano 33 (20 m, 90 hp) | tangones | publicada |
| `seafdec_38_outrigger_shrimp` | SEAFDEC 2016, plano 38 (13,5 m, 100 hp) | tangones | publicada |
| `seafdec_39_outrigger_shrimp` | SEAFDEC 2016, plano 39 (16 m, 150 hp) | tangones | publicada |
| `seafdec_35_outrigger_shrimp` | SEAFDEC 2016, plano 35 (15 m, 112 hp) | tangones | borrador |
| `seafdec_30_beam_shrimp` | SEAFDEC 2016, plano 30 (11 m, 165 hp) | vara | publicada |

Las redes tailandesas de la Fase 19.6 fueron las primeras redes de tangones y de vara **publicadas**
del catálogo: sus planos dan la red y el buque, pero no los tangones, los portones ni la vara, así que
su caso usa los valores por defecto de este capítulo (que no son los de la flota tailandesa).

El plano gemelo de Seafish de 380 × 70 mm {cite:p}`arkley1987ir1310` no se digitalizó: es un
escaneo con notación británica (filas de media malla, cortes S, SB y SK, conteos de medio paño)
que no se puede verificar en la imagen con la precisión del resto del catálogo. Los planos
tipeados de IAT 27/2019 (red Solimeno, original y modificada) e IAT 75/2023 (red tradicional de
Pesquera Deseado, versión legible de la fig. 2 de ITO 043) quedan para una fase siguiente. Las
fuentes consultadas están en {doc}`catalogo_fuentes`.
