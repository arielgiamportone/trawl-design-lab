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

# Guide for teachers

```{code-cell} ipython3
:tags: [remove-cell]
import sys, pathlib
DOCS = pathlib.Path.cwd().parent
sys.path[:0] = [str(DOCS.parent), str(DOCS)]
import _lang  # English book: number format and engine messages in English
from collections import Counter

from IPython.display import Markdown
import _plots_v as PV
from myst_nb import glue
from trawlkit.teaching import bank, load_bank
from trawlkit.teaching.bank import LEVEL_LABELS, level_label
from trawlkit.teaching.labs import load_labs

EX = list(load_bank().values())


def title(chapter: str) -> str:
    """Title of the chapter (the first “# …” line of its file in this book)."""
    path = pathlib.Path(f"{chapter}.md")
    if not path.exists():  # chapter not yet in the English book: fall back to the Spanish one
        path = DOCS / f"{chapter}.md"
    text = path.read_text(encoding="utf-8")
    head = next(line for line in text.splitlines() if line.startswith("# "))
    return f"{chapter.split('_')[0]} · {head[2:].strip()}"


LABS = list(load_labs().values())
glue("n_ex", Markdown(str(len(EX))), display=False)
glue("n_labs", Markdown(str(len(LABS))), display=False)
glue("n_ch", Markdown(str(len({e.chapter for e in EX}))), display=False)
```

## Purpose

The project was born in a Fisheries Engineering course ({doc}`utn`) and returns to it with the
**“UTN Classroom”** mode of the app (Phase 17). It is designed for the technician programme and
the degree:

- a **bank of {glue:md}`n_ex` exercises** from {glue:md}`n_ch` chapters, at three levels, that
  grade themselves;
- **{glue:md}`n_labs` guided labs** that are done on the app with a real case;
- a **classroom** with courses, assignments, submissions and a gradebook.

The exercises do not come with fixed numbers: every time they are opened the data change (within
“blackboard” ranges), and the answer is computed by the same engine the rest of the book uses.
Seed 0 gives the book's data: they are the ones that appear in the “Exercises” section at the end
of each chapter.

## Three ways to use it in class

**Free practice.** In the app, *UTN Classroom → Free practice*. No account or connection is
needed: students choose chapter and level, solve, see which answer is right and why, and ask for
new data to try again. It serves for the week's practice and for studying.

**Labs.** A lab is a sequence of steps on the app: “change the vessel”, “reduce the twine of the
body”, “compare with this net”. A panel accompanies the student, takes them to the tab of each
step and **checks against their case** that they did it (the engine computes the facts: the
vessel, the codend mesh, the maximum speed). Numerical questions are graded against the
student's own case; multiple-choice ones, against the answer; open ones are graded by the
teacher.

**Course classroom.** With the classroom enabled on the server ({doc}`despliegue`), the teacher
creates the course and shares a code; students sign up with it. An **assignment** brings together
exercises and labs from the bank, with a due date, attempts and a feedback policy. Each student
receives **their own data** in every exercise. Grading is always done by the server.

## What is in the bank

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
PV.md_table(["Chapter", "Basic", "Intermediate", "Advanced", "Labs"], rows)
```

The levels guide the planning:

- **Basic**: apply a formula of the chapter with given data (Fridman pull, Aberdeen drag, Koyama
  buoyancy).
- **Intermediate**: chain two or three steps or read a table (Prado towing power, cut code,
  otter board area).
- **Advanced**: use the full engine or a balance (maximum speed of the A-3, Fridman buoyancy).

```{code-cell} ipython3
:tags: [remove-input]
PV.md_table(
    ["Lab", "Chapter", "Level", "Steps", "What is learned"],
    [
        [x.title, title(x.chapter), level_label(x.level), str(len(x.steps)), x.summary]
        for x in LABS
    ],
)
```

## How it is graded

- **Numbers**: accepted with a decimal comma or point and with thousands spaces. Each answer has
  its tolerance (±2 % by default; angles, percentages and codes have their own). If the answer
  differs by a factor of a thousand, the student is told to check the units.
- **Cut codes**: compared without spaces or capitals (`1n2b` counts as `1N2B`).
- **Labs**: a step is completed when its checks are met and the closed questions are right; the
  open ones only need to have text. The automatic grade is the fraction of steps completed.
- **The teacher decides**: in the gradebook, each submission is opened and given a grade (which
  replaces the automatic one) and a comment that the student sees in their assignment. Cells with
  open questions not yet reviewed are marked with ✎.

The feedback policy of each assignment defines what the student sees:

| Feedback | On submission | When attempts run out or after the due date |
|---|---|---|
| **On submission** (practice, coursework) | which answer is right and the score | the expected answer and the explanation |
| **After the due date** (exams) | “Submission received” | everything |

## Suggested plan (one semester)

A proposal for a 16-week fishing gear design course, with the book as the textbook and the app as
the laboratory. The assessment weeks use assignments with feedback after the due date.

| Week | Topic and chapter | In class | Assignment in the classroom |
|---|---|---|---|
| 1 | The trawl and its nomenclature ({doc}`01_introduccion`, {doc}`02_nomenclatura`) | Tour of the app in Guided mode | — |
| 2 | Available power ({doc}`10_potencia`) | Fridman and Prado by hand | Power exercises (basic) |
| 3 | Netting panels, cuts and meshes ({doc}`11_panos_y_cortes`) | Reading an FAO plan | Symmetrical cut and cutting angle |
| 4 | Mechanics and dimensions ({doc}`12_mecanica_red`, {doc}`13_dimensiones`) | Headrope by pieces | Solid area, solidity, headrope |
| 5 | Net drag ({doc}`14_resistencia`) | Lab “Netting and drag” | Drag (basic and intermediate) |
| 6 | Otter boards and rigging ({doc}`15_portones_aparejo`) | Otter board polar | Forces and otter board area |
| 7 | Openings ({doc}`16_aberturas`) | Lab “Another otter board, another mouth” | DPA and vertical opening |
| 8 | **First midterm exam** (chapters 10 to 16) | Exam in the classroom | Assignment with data per student, 1 attempt, feedback after the due date |
| 9 | Buoyancy and ballast ({doc}`17_flotacion_lastre`) | Fridman balance | Buoyancy and ballast |
| 10 | Warps ({doc}`18_cables`) | Lab “Fishing deeper” | Warp by depth and angles |
| 11 | Speed window ({doc}`19_ventana_velocidad`) | Lab “More power, more speed” | Maximum speed (intermediate and advanced) |
| 12 | Optimization ({doc}`20_optimizacion`) | Lab “A net sized for the vessel” | Swept area |
| 13 | Selectivity and real sea ({doc}`24_malla_selectividad`, {doc}`23_mar_real`) | Diamond versus T90 in the app | Logistic curve and current |
| 14 | From design to net loft ({doc}`36_construccion`) | Lab “From the plan to the net loft” | Cutting cycle, hanging ratio and take-ups |
| 15 | Economics of the operation ({doc}`37_economia`) | Most profitable speed with port prices | Diesel, net per hour and break-even |
| 16 | **Second midterm exam and final project** | Defence of the design | Project: the net for a vessel of the local fleet |

For the **technician programme** it is best to stay at the basic and intermediate levels and to
give more weight to the labs and to the construction guide; for the **degree**, add the advanced
ones, simulation ({doc}`21_simulacion`) and uncertainty ({doc}`25_incertidumbre_calibracion`).

## Assessment examples

**Midterm exam with data per student.** An assignment with 6 to 8 exercises from the chapters
assessed, one attempt, feedback after the due date and the due date at the end of the class
session. To give it on paper, the assignment's gradebook downloads **one statement per student
with their own data** (PDF) and the **answer key** for each one: no two exams are the same and
grading is straightforward.

**Practical assignment with a lab.** Two or three exercises and a lab, several attempts, feedback
on submission. The teacher reviews the open answers of the lab with this indicative rubric:

| Criterion | 0 | 1 | 2 |
|---|---|---|---|
| Uses the numbers of their case | Quotes no values | Quotes values without comparing them | Compares before and after, with units |
| Explains the physical cause | Does not explain | Explains in general | Relates it to the theory of the chapter (solid area, pull, angles) |
| Recognizes limits | — | Mentions a limitation | Says which assumption of the model could change the conclusion |

**Final project.** The student chooses a real vessel of the local fleet, designs or adapts the
net with the app (catalogue, optimization, components), hands in the PDF report of the case, the
construction guide and the trip economics with prices surveyed at the port, and defends it.

```{note}
The exercises are “open book” by nature: the engine that grades them is the same one the student
has in the app. Data per student prevent direct copying between classmates, but to assess the
calculation by hand it is best to give the midterm on paper with the PDF per student.
```

## Privacy

The classroom stores the minimum: username, display name (name or student ID) and the hashed
password; it does not ask for an email. If a student forgets the password, the teacher sets a
new one from the course's list of students. Each user can delete their account along with their
submissions. The seeds of the data are derived with a secret stored in the database, so a
student's data cannot be guessed from outside.

## Adding exercises and labs

The bank is in `src/trawlkit/data/teaching/` and is open: each exercise is a YAML entry with the
statement, the data (fixed, on a grid or in a list), the answers with their tolerance and the name
of a *solver* in `trawlkit.teaching.solvers` that computes the answers with engine functions. A
lab is a list of steps with checks of the type
`{fact: summary.max_speed_kn, op: ">", baseline_factor: 1.2}` on facts the engine computes.
The tests (`tests/test_teaching.py`) run each exercise with twenty seeds and check that the
correct answer gets the full score. Proposals of exercises from other courses are welcome in the
repository.

From the command line:

```bash
trawlkit exercises list --chapter 14_resistencia
trawlkit exercises show resistencia.aberdeen --seed 7
trawlkit exercises sheet --chapter 14_resistencia --key -o clave.pdf
```
