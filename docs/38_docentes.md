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

# Guía para docentes

```{code-cell} ipython3
:tags: [remove-cell]
import pathlib
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path.cwd().parent))
sys.path.insert(0, str(pathlib.Path.cwd()))

from IPython.display import Markdown
import _plots_v as PV
from myst_nb import glue
from trawlkit.teaching import bank, load_bank
from trawlkit.teaching.bank import LEVEL_LABELS
from trawlkit.teaching.labs import load_labs

EX = list(load_bank().values())


def title(chapter: str) -> str:
    """Título del capítulo (la primera línea «# …» de su archivo)."""
    text = pathlib.Path(f"{chapter}.md").read_text(encoding="utf-8")
    head = next(line for line in text.splitlines() if line.startswith("# "))
    return f"{chapter.split('_')[0]} · {head[2:].strip()}"


LABS = list(load_labs().values())
glue("n_ex", Markdown(str(len(EX))), display=False)
glue("n_labs", Markdown(str(len(LABS))), display=False)
glue("n_ch", Markdown(str(len({e.chapter for e in EX}))), display=False)
```

## Propósito

El proyecto nació en una cátedra de Ingeniería Pesquera ({doc}`utn`) y vuelve a ella con el modo
**«Aula UTN»** de la app (Fase 17). Está pensado para la tecnicatura y el grado:

- un **banco de {glue:md}`n_ex` ejercicios** de {glue:md}`n_ch` capítulos, en tres niveles, que se
  corrigen solos;
- **{glue:md}`n_labs` laboratorios guiados** que se hacen sobre la app con un caso real;
- un **aula** con cursos, tareas, entregas y planilla de notas.

Los ejercicios no traen números fijos: cada vez que se abren cambian los datos (dentro de rangos
«de pizarrón»), y la respuesta la calcula el mismo motor que usa el resto del libro. La semilla 0
da los datos del libro: son los que aparecen en la sección «Ejercicios» al final de cada capítulo.

## Tres maneras de usarlo en clase

**Práctica libre.** En la app, *Aula UTN → Práctica libre*. No hace falta cuenta ni conexión: los
alumnos eligen capítulo y nivel, resuelven, ven qué respuesta está bien y por qué, y piden otros
datos para volver a intentar. Sirve para la ejercitación de la semana y para estudiar.

**Laboratorios.** Un laboratorio es una secuencia de pasos sobre la app: «cambie el buque», «baje
el hilo del cuerpo», «compare con esta red». Un panel acompaña al alumno, lo lleva a la pestaña de
cada paso y **comprueba con su caso** que lo hizo (el motor calcula los hechos: el buque, la malla
del copo, la velocidad máxima). Las preguntas numéricas se corrigen contra el caso del propio
alumno; las de opción múltiple, contra la respuesta; las abiertas las corrige el docente.

**Aula del curso.** Con el aula habilitada en el servidor ({doc}`despliegue`), el docente crea el
curso y comparte un código; los alumnos se registran con él. Una **tarea** reúne ejercicios y
laboratorios del banco, con fecha de cierre, intentos y política de devolución. Cada alumno
recibe **sus propios datos** en cada ejercicio. La corrección la hace siempre el servidor.

## Qué hay en el banco

```{code-cell} ipython3
:tags: [remove-input]
count = Counter((e.chapter, e.level) for e in EX)
labs_by = Counter(x.chapter for x in LABS)
rows = []
for ch in sorted({e.chapter for e in EX} | set(labs_by)):
    rows.append(
        [
            title(ch),
            str(count.get((ch, "basico"), 0)),
            str(count.get((ch, "intermedio"), 0)),
            str(count.get((ch, "avanzado"), 0)),
            str(labs_by.get(ch, 0)),
        ]
    )
PV.md_table(["Capítulo", "Básicos", "Intermedios", "Avanzados", "Laboratorios"], rows)
```

Los niveles orientan la planificación:

- **Básico**: aplicar una fórmula del capítulo con datos dados (tiro de Fridman, resistencia de
  Aberdeen, flotación de Koyama).
- **Intermedio**: encadenar dos o tres pasos o leer una tabla (potencia de arrastre de Prado,
  código de corte, superficie de portón).
- **Avanzado**: usar el motor completo o un balance (velocidad máxima de la A-3, flotación de
  Fridman).

```{code-cell} ipython3
:tags: [remove-input]
PV.md_table(
    ["Laboratorio", "Capítulo", "Nivel", "Pasos", "Qué se aprende"],
    [
        [x.title, title(x.chapter), LEVEL_LABELS[x.level], str(len(x.steps)), x.summary]
        for x in LABS
    ],
)
```

## Cómo se corrige

- **Números**: se aceptan con coma o con punto decimal y con espacios de miles. Cada respuesta
  tiene su tolerancia (por defecto ±2 %; los ángulos, los porcentajes y los códigos, la suya). Si
  la respuesta difiere en un factor de mil, se avisa que revise las unidades.
- **Códigos de corte**: se comparan sin espacios ni mayúsculas (`1n2b` vale como `1N2B`).
- **Laboratorios**: un paso está cumplido cuando se cumplen sus comprobaciones y las preguntas
  cerradas están bien; las abiertas sólo tienen que tener texto. La nota automática es la fracción
  de pasos cumplidos.
- **El docente decide**: en la planilla, cada entrega se abre, se le pone nota (reemplaza a la
  automática) y un comentario que el alumno ve en su tarea. Las celdas con preguntas abiertas sin
  revisar se marcan con ✎.

La política de devolución de cada tarea define qué ve el alumno:

| Devolución | Al entregar | Con intentos agotados o al cierre |
|---|---|---|
| **Al entregar** (práctica, trabajos) | qué respuesta está bien y el puntaje | la respuesta esperada y la explicación |
| **Al cierre** (exámenes) | «entrega recibida» | todo |

## Planificación sugerida (un cuatrimestre)

Una propuesta para una materia de diseño de artes de pesca de 16 semanas, con el libro como texto
y la app como laboratorio. Las semanas de evaluación usan tareas con devolución al cierre.

| Semana | Tema y capítulo | En clase | Tarea en el aula |
|---|---|---|---|
| 1 | La red de arrastre y su nomenclatura ({doc}`01_introduccion`, {doc}`02_nomenclatura`) | Recorrido por la app en modo guiado | — |
| 2 | Potencia disponible ({doc}`10_potencia`) | Fridman y Prado a mano | Ejercicios de potencia (básicos) |
| 3 | Paños, cortes y mallas ({doc}`11_panos_y_cortes`) | Leer un plano FAO | Corte simétrico y ángulo de corte |
| 4 | Mecánica y dimensiones ({doc}`12_mecanica_red`, {doc}`13_dimensiones`) | Lima por piezas | Superficie sólida, solidez, lima |
| 5 | Resistencia de la red ({doc}`14_resistencia`) | Laboratorio «El paño y la resistencia» | Resistencia (básicos e intermedios) |
| 6 | Portones y aparejo ({doc}`15_portones_aparejo`) | Polar del portón | Fuerzas y superficie de portón |
| 7 | Aberturas ({doc}`16_aberturas`) | Laboratorio «Otro portón, otra boca» | DPA y abertura vertical |
| 8 | **Primer parcial** (capítulos 10 a 16) | Examen en el aula | Tarea con datos por alumno, 1 intento, devolución al cierre |
| 9 | Flotación y lastre ({doc}`17_flotacion_lastre`) | Balance de Fridman | Flotación y lastre |
| 10 | Cables ({doc}`18_cables`) | Laboratorio «Pescar más hondo» | Cable por profundidad y ángulos |
| 11 | Ventana de velocidad ({doc}`19_ventana_velocidad`) | Laboratorio «Más potencia, más velocidad» | Velocidad máxima (intermedio y avanzado) |
| 12 | Optimización ({doc}`20_optimizacion`) | Laboratorio «Una red a la medida del buque» | Área barrida |
| 13 | Selectividad y mar real ({doc}`24_malla_selectividad`, {doc}`23_mar_real`) | Rombo frente a T90 en la app | Curva logística y corriente |
| 14 | Del diseño al taller ({doc}`36_construccion`) | Laboratorio «Del plano al taller» | Ciclo de corte, embando y tomas |
| 15 | Economía de la operación ({doc}`37_economia`) | Velocidad más rentable con precios del puerto | Gasoil, red por hora y equilibrio |
| 16 | **Segundo parcial y trabajo final** | Defensa del diseño | Proyecto: la red para un buque de la flota local |

Para la **tecnicatura** conviene quedarse en los niveles básico e intermedio y dar más peso a los
laboratorios y a la guía de construcción; para el **grado**, sumar los avanzados, la simulación
({doc}`21_simulacion`) y la incertidumbre ({doc}`25_incertidumbre_calibracion`).

**Unidad optativa: langostino con tangones** ({doc}`26_aparejos_dobles_y_vara`, Fase 20.3). Para
una cátedra patagónica, una o dos semanas después de cables y ventana de velocidad. El banco suma
cinco ejercicios sobre la red tangonera del INIDEP: la abertura horizontal por triángulos
semejantes con las cañas cortas, la separación de portones por el equilibrio de la tijera de Roth
(2016) con la proyección corregida (sen α en lugar de sen 2α), la abertura vertical contra el
límite de 1,5 m de la Res. CFP 7/2018, el largo del tangón que evita que las redes se superpongan y
el cable de remolque según la carga de rotura requerida. El laboratorio «Red langostinera de
tangones» calcula la red del INIDEP con el tangonero típico, cambia la velocidad y la profundidad y
compara la separación de portones y las aberturas con las de DynamiT.

## Ejemplos de evaluación

**Parcial con datos por alumno.** Una tarea con 6 a 8 ejercicios de los capítulos evaluados, un
intento, devolución al cierre y cierre al final del turno. Para tomarlo en papel, la planilla de
la tarea descarga **un enunciado por alumno con sus propios datos** (PDF) y la **clave** de cada
uno: no hay dos exámenes iguales y la corrección es directa.

**Trabajo práctico con laboratorio.** Dos o tres ejercicios y un laboratorio, varios intentos,
devolución al entregar. El docente revisa las respuestas abiertas del laboratorio con esta
rúbrica orientativa:

| Criterio | 0 | 1 | 2 |
|---|---|---|---|
| Usa los números de su caso | No cita valores | Cita valores sin compararlos | Compara antes y después con unidades |
| Explica la causa física | No explica | Explica en general | Relaciona con la teoría del capítulo (superficie sólida, tiro, ángulos) |
| Reconoce límites | — | Menciona una limitación | Dice qué supuesto del modelo podría cambiar la conclusión |

**Proyecto final.** El alumno elige un buque real de la flota local, diseña o adapta la red con
la app (catálogo, optimización, componentes), entrega el informe PDF del caso, la guía de
construcción y la economía de la marea con precios relevados en el puerto, y lo defiende.

```{note}
Los ejercicios son «a libro abierto» por naturaleza: el motor que los corrige es el mismo que el
alumno tiene en la app. Los datos por alumno evitan la copia directa entre compañeros, pero para
evaluar el cálculo a mano conviene tomar el parcial en papel con el PDF por alumno.
```

## Privacidad

El aula guarda lo mínimo: usuario, nombre para mostrar (nombre o legajo) y la contraseña con hash;
no pide correo. Si un alumno olvida la contraseña, el docente le pone una nueva desde la lista de
alumnos del curso. Cada usuario puede borrar su cuenta con sus entregas. Las semillas de los datos
se derivan con un secreto guardado en la base, así los datos de un alumno no se pueden adivinar
desde afuera.

## Sumar ejercicios y laboratorios

El banco está en `src/trawlkit/data/teaching/` y es abierto: cada ejercicio es una entrada YAML con
el enunciado, los datos (fijos, en una grilla o en una lista), las respuestas con su tolerancia y
el nombre de un *solver* de `trawlkit.teaching.solvers` que calcula las respuestas con funciones
del motor. Un laboratorio es una lista de pasos con comprobaciones del tipo
`{fact: summary.max_speed_kn, op: ">", baseline_factor: 1.2}` sobre hechos que calcula el motor.
Las pruebas (`tests/test_teaching.py`) corren cada ejercicio con veinte semillas y verifican que
la respuesta correcta saque el puntaje completo. Las propuestas de ejercicios de otras cátedras
son bienvenidas en el repositorio.

Desde la línea de comandos:

```bash
trawlkit exercises list --chapter 14_resistencia
trawlkit exercises show resistencia.aberdeen --seed 7
trawlkit exercises sheet --chapter 14_resistencia --key -o clave.pdf
```
