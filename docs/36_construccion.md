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

# Del diseño al taller: guía de construcción

```{code-cell} ipython3
:tags: [remove-cell]
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.cwd().parent))
sys.path.insert(0, str(pathlib.Path.cwd()))

from IPython.display import Markdown
import _plots_v as PV
from myst_nb import glue
from trawlkit.api import service
from trawlkit.construction import cut_ratio_of, guide
from trawlkit.netting import cut_code_ratio


def num(x: float, nd: int = 2) -> str:
    return f"{x:,.{nd}f}".replace(",", " ").replace(".", ",")


R = service.run_case(service.build_case("fao_a3_standard", "fao_a3_modified"))
G = guide(R)
P = {p.id: p for p in G.pieces}
J = {(j.a, j.b): j for j in G.joins}
H = {(h.rope, h.part): h for h in G.hanging}
```

## Propósito

El cálculo termina en un plano y en una lista de materiales; el redero necesita otra cosa: saber
cuánto paño comprar, cómo cortar cada pieza, en qué orden unirlas y cómo armar la red en las
relingas. Este capítulo describe `trawlkit.construction` (Fase 15), que lleva el diseño al taller
con las reglas clásicas de construcción de redes {cite}`prado1990,klust1982` y las arma para
cualquier red del catálogo ({doc}`33_catalogo_fao`) o de una planilla ({doc}`35_lotes_proyeccion`).

## Cortes: leer un ciclo

Un paño de red se angosta o se ensancha cortando sus costados con un **ciclo** que se repite. Cada
corte de una **punta** (N) baja una malla sin cambiar el ancho; cada **malleta** (B, una pata de
malla) baja media malla y avanza media malla a lo ancho; cada **transversal** (T) avanza una malla a
lo ancho. Un ciclo $n_N\,\mathrm{N}\;n_T\,\mathrm{T}\;n_B\,\mathrm{B}$ cambia el ancho en
$n_T + n_B/2$ mallas por cada $n_N + n_B/2$ de alto:

$$
r = \frac{n_T + n_B/2}{n_N + n_B/2}, \qquad \text{ciclos} = \frac{N}{n_N + n_B/2}.
$$

Así, `1N2B` (una punta y dos malletas) da $r = 1/2$ y `AB` (todo malletas) $r = 1$. La guía expande
cada código en una instrucción de taller («1N2B: 1 punta y 2 malletas por ciclo; repetir 18
veces») y dice por qué borde empezar.

```{code-cell} ipython3
:tags: [remove-input]
PV.md_table(
    ["Paño", "Piezas", "Mallas boca → bolsa × alto", "Cortes", "Desperdicio"],
    [
        [
            p.id,
            str(p.pieces),
            f"{p.meshes_mouth} → {p.meshes_codend} × {p.meshes_depth}",
            "; ".join(f"{s.side}: {s.code}" + (" (inferido)" if s.inferred else "") for s in p.sides),
            f"{num(100 * p.waste, 0)} %",
        ]
        for p in G.pieces
    ],
)
```

**Alas: dos costados distintos.** Un paño central se corta igual en los dos costados. Una pieza de
ala tiene un costado de relinga (en la A-3, `AB`) y uno interior; juntos dan el cambio de ancho
$|T_\text{boca} - T_\text{bolsa}|$, sumando o restando: $|r_1 \pm r_2|\,N$, la misma regla que usa
el validador del catálogo. Cuando el plano trae un solo corte, la guía infiere el otro y lo marca.
Es lo que pasa con el paño F de la A-3: el libro no puede dar su corte (errata
`panel_f_cut_na`, {doc}`erratas`). Con un costado `AB` que gana 40 mallas en 40 de alto y un paño
que sólo crece de 129 a 143, el costado interior debe perder 26 mallas en 40, $r = 0{,}65$: el
corte más cercano de la tabla es `1N4B` ($r = 2/3$), el mismo de la pieza D que le precede.

**Paño a comprar.** Cada pieza sale de un rectángulo de paño. Las piezas centrales salen de un
rectángulo del ancho de su borde mayor; las de ala se cortan **de a pares encastradas**, una el
reflejo de la otra, de un rectángulo de $(T_\text{boca} + T_\text{bolsa}) \times N$ mallas, sin
otro desperdicio que el del corte. La guía suma los rectángulos por calidad (material, mallero e
hilo) y da el peso de paño a comprar con el desperdicio incluido: para la A-3,
{glue:md}`stock_kg` kg frente a {glue:md}`finished_kg` kg de paño cortado.

```{code-cell} ipython3
:tags: [remove-cell]
glue("stock_kg", Markdown(num(sum(s.weight_kg for s in G.stock), 1)), display=False)
glue("finished_kg", Markdown(num(sum(s.finished_kg for s in G.stock), 1)), display=False)
```

## Uniones y tomas

Dos paños se unen borde con borde. Si tienen las mismas mallas, se unen **malla a malla**; si no,
el paño con más mallas se recoge con **tomas** (dos mallas juntas sobre una del otro paño) repartidas
a lo largo de la costura. Las uniones salen del mismo orden que el plano (ver
{doc}`33_catalogo_fao`): los paños centrales de la boca a la bolsa, las alas de la punta al cuerpo,
cada ala sobre una esquina del primer paño central y, al final, las costuras laterales entre el
dorso y el vientre (en las redes de 4 paneles, cada estación del costado con la del dorso y la del
vientre, desde el copo).

```{code-cell} ipython3
:tags: [remove-input]
PV.md_table(
    ["Paso", "Cara", "Unión", "Mallas", "Cómo"],
    [
        [str(j.step), j.plane, f"{j.a} + {j.b}", f"{j.meshes_a} : {j.meshes_b}", j.rule]
        for j in G.joins
    ],
)
w = J["C", "E"]
glue("wing_meshes", Markdown(str(w.meshes_b)), display=False)
glue("bosom_meshes", Markdown(str(H["lima", "bocana"].meshes)), display=False)
```

El ala C termina en 117 mallas de 80 mm (9,36 m estirados) y se apoya sobre el paño E, de 60 mm:
ocupa {glue:md}`wing_meshes` mallas de su borde de boca en cada esquina (la relación «117/156» que
dibuja la lámina). De las 412 mallas de E quedan libres {glue:md}`bosom_meshes` en el centro: la
**bocana**, que no se cose a otro paño sino que se arma directamente en la lima.

## Montaje en relingas

El paño se arma en la relinga con un **coeficiente de armado** $E$, el cociente entre el largo de
cabo y el largo del paño estirado que se arma en él {cite}`prado1990`:

$$
E = \frac{L_\text{cabo}}{n \cdot m}, \qquad \text{mallas por metro} = \frac{n}{L_\text{cabo}},
$$

con $n$ mallas de mallero $m$. En las alas el paño se arma por su costado cortado, una malla por
cada fila de alto (la misma cuenta que la pieza de ala de la hoja Dimensiones de la Red, $(N_A +
N_C)\cdot m$), y el libro arma a $E = 1{,}05$; en la bocana se arman las mallas libres del borde
de boca.

```{code-cell} ipython3
:tags: [remove-input]
PV.md_table(
    ["Relinga", "Tramo", "Cabo [m]", "Mallas", "E", "Pauta"],
    [
        [h.rope, h.part, num(h.rope_m), str(h.meshes), num(h.hanging), h.schedule]
        for h in G.hanging
    ],
)
glue("e_bosom", Markdown(num(H["lima", "bocana"].hanging, 3)), display=False)
```

La bocana de la A-3 queda en $E =$ {glue:md}`e_bosom`, que es el embando de bocana del libro
(0,83) aplicado a la mitad del borde libre: la hoja calcula la pieza de bocana como la mitad de lo
que el borde de boca excede a las alas. Si el cabo resulta más largo que el paño ($E > 1{,}1$), el
paño no puede ir directo en él: va a una relinga de armado o línea de pesca, y el cabo (por
ejemplo, un burlón con discos o cadena) se une a ella con colgantes. La guía lo avisa; pasa con el
burlón de la red de pareja BOBP/WP/13.

**Boyas y lastre.** La posición de cada boya sigue la regla selectiva del libro (hoja Flotación y
Lastre): 70 % de las boyas en las alas y, de ellas, 60 % en el primer quinto del ala, junto a la
bocana, donde la lima necesita más empuje; el resto se reparte parejo. El lastre se reparte en
tres zonas del burlón (reglaje en el centro, bocana y alas) con sus kg y kg/m para el lastre mínimo
y el máximo.

**Cortes de cabos.** A cada largo terminado (lima, burlón, refuerzos de punta de ala, malletas,
patentes, pies de gallo, cadenas y cables) se le suma un sobrante por gaza o empalme. El valor por
defecto, 0,5 m por gaza, es una regla de taller (A VERIFICAR según el cabo y el tipo de empalme) y
se puede cambiar en la app y en `trawlkit build-guide --eye-allowance`.

## Todo el catálogo

La misma guía sale para cualquier red del catálogo:

```{code-cell} ipython3
:tags: [remove-input]
rows = []
for nid, spec in service.net_presets().items():
    g = guide(service.run_case(service.build_case(nid)))
    inferred = sum(s.inferred for p in g.pieces for s in p.sides)
    warns = sum(bool(h.warning) for h in g.hanging)
    rows.append(
        [
            nid,
            str(sum(p.pieces for p in g.pieces)),
            str(len(g.joins)),
            num(sum(s.weight_kg for s in g.stock), 1),
            str(inferred),
            str(warns),
        ]
    )
PV.md_table(
    ["Red", "Piezas", "Uniones", "Paño a comprar [kg]", "Cortes inferidos", "Avisos de armado"],
    rows,
)
```

## Dónde se usa

- **Web**: pestaña «Construcción» del modo experto, con la hoja de corte, el armado paso a paso
  (el plano resalta los paños de cada unión), el montaje en relingas con la línea de boyas, los
  cortes de cabos y el avance del taller, que queda guardado en el navegador; en el modo guiado,
  «¿Cómo la armo? Guía para el taller» en el resultado ({doc}`web`).
- **Sin conexión**: el motor del teléfono arma la guía y su planilla XLSX; el PDF necesita el
  servidor y, sin red, se imprime la vista HTML.
- **CLI**: `trawlkit build-guide fao_a3_standard -o guia.pdf` (o `.html`, `.xlsx`, `.json`).
- **API**: `POST /design/construction` y `/design/construction/export` ({doc}`api`).
- **Informe del caso**: la sección «Construcción y materiales», con la lista de materiales.

## Supuestos y límites

- Las mallas se cuentan a malla estirada y los largos de cabo incluyen el embando del motor.
- Los cortes inferidos salen del cambio de ancho del paño: hay que verificarlos contra el plano.
- El encastre de las alas de a pares supone piezas espejadas; con alas asimétricas el desperdicio
  real es mayor.
- La posición de las boyas y el reparto del lastre son un punto de partida para la prueba de mar.
- Las costuras laterales se dan como una costura por lado con las mallas de cada cara; los
  refuerzos de costado (cabos de costado, *selvedges*) dependen del plano.
