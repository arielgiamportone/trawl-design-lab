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

# Validación contra el libro Excel

```{code-cell} ipython3
:tags: [remove-cell]
import sys, pathlib, math, json
sys.path.insert(0, str(pathlib.Path.cwd().parent))
import numpy as np
import matplotlib.pyplot as plt
from tests.golden_utils import golden, golden_entry, RTOL_EXACT
import _plots_v as V
V.setup_style()
```

## Propósito

`trawlkit` es una **migración**: antes de corregir o extender el modelo hay que demostrar que,
con las mismas entradas, devuelve los mismos números que el libro `Calculos_Red_FAO_A3.xlsx`. Este
capítulo describe cómo se hizo esa demostración, mide cuánto del libro cubre y la repite aquí mismo
sobre el caso completo. Las diferencias *intencionales* con el libro (las erratas) se tratan en
{doc}`erratas`; la comparación con un simulador independiente, en {doc}`32_validacion_dynamit`.

## Método

1. **Valores de referencia.** `tools/extract/golden.py` abre el libro con `openpyxl` en modo
   `data_only`, es decir, lee el **último valor que Excel calculó y guardó** en cada celda, no la
   fórmula. Así la referencia es el número que vio el autor, erratas incluidas. Los valores se
   guardan en `tests/golden/<hoja>.json`, uno por hoja, con claves `snake_case` estables: escalares en
   `values` (celda, valor, etiqueta, unidad) y vectores por velocidad en `series` (rango de celdas,
   eje $x$, valores).
2. **Marcas.** Las celdas que el libro tiene **pegadas a mano** en lugar de calculadas llevan
   `"static": true`: son resúmenes copiados de otras hojas o de otro programa (DynamiT) y no se
   pueden reproducir con fórmulas, de modo que **no cuentan como validación**. Los coeficientes que
   el libro extrae de etiquetas de texto con `MID()` llevan `"coerced_from_text": true`, porque su
   valor depende del separador decimal del sistema.
3. **Modo `Compat.EXCEL`.** Toda comparación se hace con el motor en modo Excel, que reproduce las
   erratas del libro (ver {doc}`motor`).
4. **Tolerancia.** Relativa $\mathrm{rtol} = 10^{-6}$ (`tests/golden_utils.RTOL_EXACT`): es más
   estricta que cualquier redondeo de ingeniería, y deja pasar sólo diferencias de punto flotante
   (orden de sumas, `0.5144` frente a `0.514`, potencias). No hizo falta la tolerancia
   `RTOL_TRUNCATED = 1e-3` prevista para los valores truncados por `MID()`: el motor reproduce el
   truncado exacto.
5. **Tres niveles de test.** Por función (cada bloque de fórmulas alimentado con las entradas golden
   de sus celdas precedentes), extremo a extremo (`tests/test_case_fao_a3.py`: el caso completo, sin
   entradas intermedias, para 150 y 180 BHP) y modo corregido (`tests/test_corrected_mode.py`).
   La suite completa son unos 1 200 tests y corre en ≈ 15 s.

## Cobertura por hoja

¿Cuántos de los valores golden están efectivamente verificados por algún test? La celda siguiente
lo mide leyendo los JSON y buscando cada clave en el código de los tests (`tests/test_*.py`, sin
`test_golden.py`, que sólo valida la estructura de los JSON). Una clave cuenta como verificada si
aparece como texto literal o si coincide con una plantilla de un test parametrizado, por ejemplo
`f"summary_{column}_{variant}_t"` o `"fridman_summary_fixed_{hp}_kgf"`; para no inflar la cuenta,
la plantilla debe tener al menos cinco letras fijas.

```{code-cell} ipython3
:tags: [hide-input]
cov = V.golden_coverage()  # una fila por JSON de tests/golden
rows = []
for r in cov:
    p = r["tested"] / r["computed"] * 100
    rows.append([r["sheet"], r["keys"], r["series"], r["static"], r["computed"],
                 r["tested_literal"], r["tested"], V.fmt(p, 0) + " %"])
tot = {k: sum(r[k] for r in cov) for k in ("keys", "series", "static", "computed",
                                            "tested_literal", "tested")}
p_tot = tot["tested"] / tot["computed"] * 100
p_lit = tot["tested_literal"] / tot["computed"] * 100
rows.append(["**Total**", f"**{tot['keys']}**", f"**{tot['series']}**", f"**{tot['static']}**",
             f"**{tot['computed']}**", f"**{tot['tested_literal']}**", f"**{tot['tested']}**",
             f"**{V.fmt(p_tot, 1)} %**"])
V.md_table(["Hoja", "Claves", "de ellas series", "Estáticas", "Calculadas",
            "En tests (literal)", "En tests (con plantillas)", "Cobertura"], rows)
```

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Cobertura de los valores golden calculados por los tests del motor, por hoja del libro.
      Azul: clave nombrada literalmente en un test; celeste: cubierta por un test parametrizado
      (plantilla); gris: no referenciada. Las celdas estáticas (pegadas a mano) se excluyen.
    name: fig-31-cobertura
---
order = sorted(cov, key=lambda r: r["tested"] / r["computed"])
y = np.arange(len(order))
lit = np.array([r["tested_literal"] / r["computed"] for r in order]) * 100
tpl = np.array([(r["tested"] - r["tested_literal"]) / r["computed"] for r in order]) * 100
rest = 100 - lit - tpl
fig, ax = plt.subplots(figsize=(8.2, 4.6))
ax.barh(y, lit, color=V.BLUE_450, height=0.68, label="literal", zorder=3)
ax.barh(y, tpl, left=lit, color=V.BLUE_150, height=0.68, label="plantilla", zorder=3)
ax.barh(y, rest, left=lit + tpl, color=V.GRID, height=0.68, label="sin test", zorder=3)
for yi, r in zip(y, order):
    ax.annotate(f"{r['tested']}/{r['computed']}", (100, yi), xytext=(6, 0),
                textcoords="offset points", va="center", fontsize=8.5, color=V.INK_2,
                annotation_clip=False)
ax.set_yticks(y, [r["sheet"] for r in order])
ax.set_xlim(0, 100)
ax.set_xlabel("Claves golden calculadas [%]")
ax.grid(axis="y", visible=False)
ax.legend(loc="lower center", bbox_to_anchor=(0.45, 1.0), ncol=3)
fig.tight_layout()
plt.show()
```

```{code-cell} ipython3
:tags: [hide-input]
def kind(slug, k):
    v = golden(slug, k)
    return "texto" if isinstance(v, str) else "número"

miss = [(r["slug"], k) for r in cov for k in r["untested_keys"]]
n_txt = sum(kind(s, k) == "texto" for s, k in miss)
by_sheet = {}
for s, k in miss:
    by_sheet.setdefault(V.SHEET_NAMES[s], []).append(k)
V.md_table(["Hoja", "Claves sin test", "Ejemplos"],
           [[h, len(ks), ", ".join(ks[:4]) + (" …" if len(ks) > 4 else "")]
            for h, ks in sorted(by_sheet.items(), key=lambda t: -len(t[1]))])
print(f"{len(miss)} claves calculadas sin test ({n_txt} son textos).")
print(f"Cobertura total {V.fmt(p_tot, 1)} % ({V.fmt(p_lit, 1)} % sólo con nombres literales).")
```

La cobertura es completa o casi completa en las hojas de cálculo propiamente dichas —potencia,
resistencia, mecánica de la red, dimensiones, portones, flotación y cables—, que son las que
definen el diseño. Los huecos se concentran en tres grupos que **no son resultados del modelo**:

* **Entradas y catálogos.** *Tablas de Referencias*, las tablas de paños de *Paños de red y cortes*
  (`netting_80mm_*`, …), *Especie Blanco* y *Tipo de buques* son datos. Se validan por otra vía:
  `tools/extract` los vuelca a `src/trawlkit/data/*.yaml` y `src/trawlkit/data/reference/*.csv`, y `tests/test_data_*.py`
  comprueba esos archivos contra el libro, no contra el JSON golden.
* **Conversiones y textos.** Las potencias en kW de *Potenc disponible* (`nominal_kw_150`, …), las
  etiquetas (`bottom_type`, `headrope_material`) y constantes físicas repetidas (`gravity_m_s2`).
* **Valores intermedios por panel** de *Paños de red y cortes* (largos estirados, superficie y
  número de mallas por paño) que el motor calcula pero que los tests verifican a través de los
  totales y de la superficie sólida.

## Comprobación extremo a extremo

La prueba más exigente es correr el caso completo —red estándar y modificada, buque de 150 BHP con
el de 180 BHP en la clase, portón FAO— sin ninguna entrada intermedia, y comparar los resultados
finales de cada hoja con el libro. Es lo que hace `tests/test_case_fao_a3.py` con unas 120 claves;
aquí se repite con una selección de trece.

```{code-cell} ipython3
r = V.run_case(150, "excel")
DIM, MEC = "dimensiones_de_la_red", "mecanica_de_la_red"
RES, PORT = "resistencia_de_la_red", "portones_y_aparejamiento"
FLOT, REM = "flotacion_y_lastre", "cables_de_remolque"
POT = "potencia_disponible_arrastre_ok"
checks = [
    (DIM, "footrope_m", r.dimensions.std.footrope_m),
    (DIM, "solid_surface_std_m2", r.geometry.std.solid_surface_m2),
    (DIM, "horizontal_opening_m", r.spread.horizontal_opening_m),
    (POT, "fridman_summary_fixed_150_kgf", r.power.fridman.ft_fixed_pitch_kgf),
    (RES, "aberdeen_demersal_rn_std_t", r.drag.table.design_rn("std")),
    (RES, "dickson_rn_std_t", r.drag.table.std["dickson"]),
    (MEC, "dpa_fridman_std_m", r.spread.fridman.dpa_std_m),
    (MEC, "av_fridman_std_m", r.spread.vertical.fridman.std.av_m),
    (PORT, "door_spread_m", r.doors.spread_m),
    (FLOT, "flotation_total_rounded_kgf", r.floats.flotation_rounded_kgf),
    (FLOT, "ballast_std_150_kg", r.ballast.fridman.std),
    (REM, "total_drag_std_kgf", r.warps.total.std),
    (REM, "warp_min_breaking_load_kgf", r.warps.loads.min_breaking_load_kgf),
]
SUP = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")
PREFIX = {DIM: "Dim", MEC: "Mec", RES: "Res", PORT: "Port", FLOT: "Flot", REM: "Rem",
          POT: "PotOK"}
rows = []
for slug, key, got in checks:
    ref = np.asarray(golden(slug, key), dtype=float)
    got = np.asarray(got, dtype=float)
    assert np.allclose(got, ref, rtol=RTOL_EXACT, atol=0), (slug, key)
    err = np.max(np.abs(got - ref) / np.maximum(np.abs(ref), 1e-300))
    e = golden_entry(slug, key)
    cell = e.get("cell", e.get("cells"))
    pick = (lambda a: float(a)) if got.ndim == 0 else (lambda a: float(a[4]))  # serie: 3 kn
    m, ex = f"{err:.0e}".split("e")
    err_s = "0" if err == 0 else f"{m}·10{str(int(ex)).translate(SUP)}"
    rows.append([f"{PREFIX[slug]}!{cell}", key, V.fmt(pick(got), 3), V.fmt(pick(ref), 3), err_s])
V.md_table(["Celda(s)", "Clave golden", "trawlkit", "Excel", "Error rel."], rows)
```

Las series se muestran a 3 kn, pero se comparan en las nueve velocidades. Las trece comparaciones
pasan con errores relativos de cero o del orden de $10^{-16}$, es decir, en el último bit de la
mantisa: el motor reproduce el libro a la **precisión de la máquina**, no sólo a la precisión de
ingeniería.

## Lo que esta validación no demuestra

* **Que el libro esté bien.** Se validó contra los números del libro, erratas incluidas; las
  diferencias corregidas están en {doc}`erratas`.
* **Los valores estáticos.** Las 33 claves pegadas a mano (resúmenes "peor/mejor caso" de potencia,
  resumen de aberturas verticales, columna de DynamiT en la resistencia) no se pueden recalcular.
  Los tests las mencionan sólo para documentar que no coinciden con las fórmulas o para exponerlas
  como referencia externa (DynamiT, {doc}`32_validacion_dynamit`).
* **Otros casos.** La validación es para la red FAO A-3 con los dos buques del libro. Que el motor
  funcione para otras redes y buques se apoya en que reproduce fórmula a fórmula, no un ajuste:
  cambiar una entrada recorre exactamente el mismo camino que en el libro.
