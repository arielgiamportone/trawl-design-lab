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

# La flota argentina

```{code-cell} ipython3
:tags: [remove-cell]
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.cwd().parent))
sys.path.insert(0, str(pathlib.Path.cwd()))

import numpy as np
import matplotlib.pyplot as plt
import _plots_t1 as P
from trawlkit import propulsion as pr
from trawlkit.api import service
from trawlkit.model import run
from trawlkit.power import bollard_pull_t

P.setup_style()
TIPOS = {
    "rada_ria": "Rada o ría",
    "costero": "Costero",
    "fresquero": "Fresquero",
    "congelador": "Congelador",
    "tangonero": "Tangonero",
    "investigacion": "Investigación",
    None: "Libro (A-3)",
}
VESSELS = service.vessel_list()
```

## Propósito

El libro original calcula la red para dos buques de rada o ría de 150 y 180 BHP. Este capítulo
describe el catálogo de buques que la Fase 19.4 agregó a `trawlkit`: **tipos de buque** de la flota
argentina armados con los valores medios publicados por el INIDEP y la FAO, y **buques con
características publicadas** (los de investigación del INIDEP y dos de fuente secundaria). Cada
valor cita su tabla y su página; lo calculado lleva la fórmula; lo que la fuente no da queda vacío
y marcado «A VERIFICAR». No hay medidas inventadas: cuando un caso necesita una manga o un puntal
que la fuente no publica, el motor los escala del buque de la A-3 y lo anota.

## La flota por segmentos

La clasificación oficial {cite:p}`fao2005argentina` separa la flota **costera** (de rada o ría y
costera) de la **de altura** (arrastreros fresqueros y congeladores, tangoneros, surimeros y de
vieira; palangreros; poteros). Las esloras y los buques registrados en 2005 (transcriptos de las
pp. 14–16 del PDF):

| Segmento | Eslora | Registrados 2005 |
|---|---|---|
| Rada o ría | «eslora promedio de 10 a 15 metros» | 144 |
| Costera | «entre 15 y 25 metros de eslora» | 120 |
| Arrastreros fresqueros de altura | «eslora de 25 a 63 metros» | 140 |
| Arrastreros congeladores | «entre 30 y 100 m (mayor frecuencia entre 60 y 80 m)» | 62 |
| Tangoneros | «eslora de entre 26 y 39 metros» | 76 |
| Surimeros | «más de 100 m de eslora» | 3 |

Las potencias salen de los trabajos del INIDEP de 2001: la flota industrial de 1998
{cite:p}`bertolotti2001flota`, los estratos de fresqueros {cite:p}`bertolotti2001fresqueros` y de
congeladores {cite:p}`bertolotti2001congeladores`, la flota costera {cite:p}`lasta2001costera` y la
flota de pequeña escala de Mar del Plata {cite:p}`errazti2001costera`. En todos la potencia se
correlaciona fuerte con la eslora ($r$ = 0,88 en fresqueros y 0,89 en congeladores). Los
tangoneros están acotados por la Res. CFP 7/2018 {cite:p}`cfp2018res7`: hasta 40 m de eslora de
arqueo y 2000 hp, con portones y abertura vertical de la red de hasta 150 cm.

En Tierra del Fuego, el caso de este libro, operan entre 5 y 7 costeros por año desde Ushuaia, de
9 a 24 m de eslora y 70 a 600 HP, en el Canal Beagle (Lasta et al. 2001, p. 105). El estrato I de la
flota de pequeña escala de Mar del Plata (13 m, 134 ± 92 HP) es el análogo publicado más cercano
a los buques de 150–180 BHP de la A-3.

## El catálogo de `trawlkit`

Los buques viven en `src/trawlkit/data/vessels/*.yaml` (los dos de la A-3 siguen en
`data/vessels.yaml`, primeros y sin cambios) y se piden con `GET /catalog/vessels`, que filtra por
tipo (`?type=tangonero`), región y estado. Los **tipos** (`typical: true`) son medias de un estrato,
no buques reales; los marcados *provisorio* vienen de una enciclopedia o de la prensa.

```{code-cell} ipython3
rows = []
for v in VESSELS:
    src = v.sources[0].key if v.sources else "giamportone2024"
    estado = "provisorio" if v.status == "draft" else ("típico" if v.typical else "publicado")
    rows.append([
        v.id,
        TIPOS[v.vessel_type.value if v.vessel_type else None],
        P.fmt(v.bhp, 0),
        P.fmt(v.length_m, 2) if v.length_m else "—",
        P.fmt(v.beam_m, 2) if v.beam_m else "A VERIFICAR",
        estado,
        src,
    ])
P.md_table(["Id", "Tipo", "BHP", "Eslora [m]", "Manga [m]", "Estado", "Fuente"], rows)
```

La procedencia de cada valor está en el propio archivo. Por ejemplo, la del tangonero típico:

```{code-cell} ipython3
tang = next(v for v in VESSELS if v.id == "ar_tangonero_1998")
P.md_table(
    ["Campo", "Tipo", "Documento", "Página", "Nota"],
    [[k, p.kind.value, p.document or "—", p.page or "—", p.note or ""]
     for k, p in tang.provenance.items()],
)
```

## Buques con características publicadas

* **BIP Dr. Eduardo L. Holmberg** (INIDEP, Hitachi Zosen 1980): 61,95 m, 11 m de manga, 2100 hp
  {cite:p}`giorgini2023poder`; motor Yanmar de 2100 PS a 680 rpm, hélice de cuatro palas de paso
  variable y guinche Kawasaki con dos tambores de 2000 m de cable de 24 mm {cite:p}`inidepholmberg`.
* **BIP Capitán Cánepa** (dado de baja): 39,17 m, 7,35 m, 760 hp {cite:p}`giorgini2023poder`.
* **BIPO Víctor Angelescu** (2017): 52,8 m, 12,8 × 5,0 m, calado 4,8 m, dos motores eléctricos de
  1050 kW {cite:p}`inidepangelescu`.
* **BIPO Mar Argentino** (2020): 36,0 m, 8,5 × 4,0 m, calado 3,40 m, 253 TRB, 550 kW
  {cite:p}`inidepmarargentino`.
* **BIP Capitán Oca Balda** (provisorio): medidas de una enciclopedia sin referencias
  {cite:p}`wikipediaocabalda`; construcción de {cite:p}`argentinaocabalda`.
* **B/P San Severo** (provisorio): tangonero multipropósito de Contessi, 20,95 × 7,50 × 3,30 m y 926 HP
  según la prensa {cite:p}`pescare2026sansevero,argenports2026sansevero`.

Las potencias en kW se pasan a hp métrico (0,7355 kW/hp) y quedan como *derivadas*.

## Lo que no se encontró

* **Diámetro, paso y RPM de la hélice, y tiro a punto fijo medido**: ningún buque pesquero argentino
  los tiene publicados. Por eso ningún buque del catálogo usa todavía el tiro por la hélice
  ({doc}`10_potencia`).
* **Distribución de tipos de hélice** (fija o de paso variable, con o sin tobera) por segmento: no
  hallada. Los tipos quedan con el valor por defecto del esquema (paso fijo), marcado como supuesto.
* **Manga, puntal y calado por segmento**: las tablas del INIDEP dan eslora, TRB, HP, bodega y
  tripulación, no las formas del casco.
* **El KF de Fridman para PF+T y PV**: el Holmberg y el Oca Balda, de paso variable sin dato de tobera,
  piden `fridman_kf` para calcular un caso.

## Tiro por la hélice en los tipos de la flota

Sin diámetros publicados, el modelo de la hélice se puede usar al revés: ¿qué diámetro haría falta
para que la fórmula de Wärtsilä {eq}`eq-wartsila` dé los 10–12 kgf/BHP que el *Fisherman's
Workbook* {cite:p}`prado1990` indica para hélice fija? La inversa es
$D = (BP\cdot 9{,}81/k_1)^{3/2}/P_D$, con $P_D = 0{,}9\,\mathrm{BHP}$ (todo *derivado*):

```{code-cell} ipython3
rows = []
for v in VESSELS:
    if not v.typical:
        continue
    pd = pr.delivered_power_kw(v.bhp)
    d10 = pr.diameter_for_bollard_pull_m(10 * v.bhp / 1000, pd)
    d12 = pr.diameter_for_bollard_pull_m(12 * v.bhp / 1000, pd)
    rows.append([
        v.name,
        P.fmt(v.bhp, 0),
        P.fmt(pd, 0),
        f"{P.fmt(10 * v.bhp / 1000, 1)}–{P.fmt(12 * v.bhp / 1000, 1)}",
        P.fmt(bollard_pull_t(v.bhp, v.propeller), 1),
        f"{P.fmt(d10, 2)}–{P.fmt(d12, 2)}",
    ])
P.md_table(
    ["Tipo", "BHP", "P_D [kW]", "BP Workbook [t]", "BP libro (A VERIFICAR) [t]",
     "D equivalente [m]"],
    rows,
)
```

```{code-cell} ipython3
:tags: [hide-input]
d = np.linspace(0.4, 4.0, 200)
fig, ax = plt.subplots(figsize=(8.6, 4.2))
pick = ["ar_rada_ria_mdp_e1", "ar_fresquero_e1", "ar_tangonero_1998", "ar_congelador_e2"]
for k, vid in enumerate(pick):
    v = next(x for x in VESSELS if x.id == vid)
    pd = pr.delivered_power_kw(v.bhp)
    kgf = [1000 * pr.bollard_pull_wartsila_t(x, pd) / v.bhp for x in d]
    ax.plot(d, kgf, color=P.SERIES[k], label=f"{v.name} ({v.bhp:.0f} BHP)", zorder=3)
ax.axhspan(10, 12, color=P.MUTED, alpha=0.18, zorder=1)
ax.annotate("Workbook, hélice fija: 10–12 kgf/BHP", xy=(4.0, 11), ha="right", va="center",
            fontsize=8, color=P.INK_2)
ax.axhline(9.9, color=P.MUTED, lw=1, ls="--", zorder=2)
ax.annotate("libro: BHP·0,9·1,10/100 (A VERIFICAR)", xy=(4.0, 9.9), xytext=(0, -10),
            textcoords="offset points", ha="right", fontsize=8, color=P.INK_2)
ax.set_xlabel("Diámetro de la hélice D [m]")
ax.set_ylabel("Tiro a punto fijo por BHP [kgf/BHP]")
ax.set_xlim(0.4, 4.0)
ax.set_ylim(0, 30)
ax.legend(loc="upper left", fontsize=8)
fig.tight_layout()
plt.show()
```

Con hélice abierta, la fórmula de Wärtsilä llega a los 10–12 kgf/BHP del Workbook con diámetros de
0,6–0,8 m en el buque de rada o ría y de 1,7–2,2 m en el tangonero típico. Cuanto mayor y más lenta
la hélice, más tiro por caballo: con el doble de diámetro el tiro sube un 59 % ($2^{2/3}$). El FAO
FTP 383 {cite:p}`wilson1999` cita un caso en que una hélice un 50 % mayor dio un 27 % más de tiro a
punto fijo. Ésa es la información que el BHP solo no tiene y que la fórmula del libro no puede ver.

## Calcular un caso con un buque del catálogo

Un tipo de la flota se usa como cualquier buque del catálogo. La manga y el puntal que la fuente no
da se escalan del buque de la A-3 con la razón de esloras y quedan en las notas; con un buque
distinto del de la A-3 la separación de portones sale de la DPA de Fridman
(`door_spread_rule = "fridman"`), porque la regla «al metro» del libro está calibrada para la A-3.

```{code-cell} ipython3
case = service.build_case(
    vessel="ar_rada_ria_mdp_e1",
    net_modified="fao_a3_modified",
    params={"door_spread_rule": "fridman"},
)
r = run(case)
print("\n".join(n for n in r.notes if n.startswith("catalog")))
s = r.summary()
P.md_table(
    ["Magnitud", "Valor"],
    [
        ["Buque", case.vessel.name],
        ["BHP", P.fmt(case.vessel.bhp, 2)],
        ["Eslora × manga × puntal [m]",
         f"{P.fmt(case.vessel.length_m, 2)} × {P.fmt(case.vessel.beam_m, 2)} × "
         f"{P.fmt(case.vessel.depth_m, 2)}"],
        ["Velocidad máxima con la red A-3 [kn]", P.fmt(s["max_speed_kn"], 2)],
    ],
)
```

En la app, el paso «Buque» del modo guiado filtra el catálogo por tipo y región, y la casilla
**Usar mi buque** (también en el panel del caso del modo experto) abre un formulario con la potencia,
la eslora, la manga, el puntal, el tipo de hélice, la tobera, el diámetro de la hélice, la capacidad
del tambor y la región. Los datos se guardan con el caso y el proyecto y viajan a la API como un
buque en línea, siempre en métrico (las unidades imperiales sólo cambian lo que se muestra). Con el
diámetro, el resultado suma el tiro por la hélice; con la capacidad del tambor, el motor controla que
el cable filado más la reserva del libro entren en cada tambor y que el tiro del guinche alcance el
80 % del tiro a punto fijo sin pasar de 1/3 de la rotura del cable {cite:p}`prado1990`.

## Supuestos y límites

* Los tipos son **medias** de estratos de 1997–1998: la flota cambió desde entonces (el informe del
  variado costero de 2021 {cite:p}`magyp2021variado` ya estratifica por menos de 19 m, 19–28,25 m y
  28,26–38,95 m). Los desvíos estándar de la potencia son del 15 al 70 % de la media.
* «HP» del registro se toma como BHP. TRB (arqueo bruto de registro) se guarda como `gross_tonnage`.
* La manga y el puntal escalados de la A-3 son un supuesto geométrico (buques semejantes) para poder
  calcular, no un dato.
* El tiro por la hélice es una cota optimista (≈ +25 % frente a la medición de Kartha y Roy
  Choudhury {cite:p}`kartha1966`, ver {doc}`10_potencia`) y sólo se calcula con un diámetro real.
