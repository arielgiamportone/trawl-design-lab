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

# Caso de estudio: red FAO A-3 en el Canal Beagle

```{code-cell} ipython3
:tags: [remove-cell]
import sys, pathlib, math
sys.path.insert(0, str(pathlib.Path.cwd().parent))
import numpy as np
import matplotlib.pyplot as plt
from tests.golden_utils import golden
import _plots_v as V
V.setup_style()

C150, C180 = V.run_case(150, "corrected"), V.run_case(180, "corrected")
E150, E180 = V.run_case(150, "excel"), V.run_case(180, "excel")
kn = C150.case.speeds
I = {v: C150.case.speed_index(v) for v in (2.0, 2.5, 3.0, 3.5)}
```

## Contexto

El modelo nació para una pesquería concreta: la **langostilla** (*Munida gregaria* /
*M. subrugosa*) del Canal Beagle, un crustáceo pequeño que vive sobre fondos intermedios a unos 40 m
de profundidad, con la flota local de pesqueros de rada o ría de hasta 9 m de eslora y motores de
150–180 BHP {cite:p}`giamportone2024`. La pregunta de diseño es la de {doc}`01_introduccion`: ¿qué red
puede remolcar ese buque, a qué velocidad, con qué aparejo?

La red elegida es la A-3 del catálogo FAO de redes para embarcaciones chicas {cite:p}`faocatalogue`,
una red de fondo de dos caras pensada justamente para 150–180 HP. El libro la evalúa en dos
variantes que este capítulo compara: la **estándar**, con bolsa de 40 mm, y la **modificada para
crustáceos**, con bolsa de 30 mm, que retiene mejor a la langostilla a costa de más hilo en el agua.

Todo el capítulo usa el **modo corregido** (`Compat.CORRECTED`, ver {doc}`erratas`), que es el modo de
diseño; el modo `excel` aparece como columna de comparación y como ancla de validación contra el
libro original.

## Planteo del caso

```{code-cell} ipython3
:tags: [hide-input]
c = C150.case
std, mod = c.net, c.net_modified
cod_std = [p for p in std.panels if p.section.value == "codend"]
cod_mod = [p for p in mod.panels if p.section.value == "codend"]

def codend(ps):
    return " + ".join(f"{p.id}: {V.fmt(p.mesh_mm, 0)} mm, {p.meshes_top}×{p.meshes_depth} mallas"
                      + (f" (×{p.count})" if p.count > 1 else "") for p in ps)

d = c.door
V.md_table(
    ["Entrada", "Valor", "Origen"],
    [
        ["Especie objetivo", f"{std.species.name} (Munida gregaria / M. subrugosa)", "Especie Blanco!C3, H3"],
        ["Profundidad de trabajo", f"{V.fmt(c.working_depth_m, 0)} m, fondo {std.species.bottom_type.lower()}", "Especie Blanco!E5:E6"],
        ["Red estándar: bolsa", codend(cod_std), "Paños!H222:T224"],
        ["Red modificada: bolsa", codend(cod_mod), "Paños!H255:H257"],
        ["Paños del cuerpo y alas", "PA, 80/60/40 mm, Ø 1,13–1,37 mm (iguales en ambas)", "data/fao_a3_*.yaml"],
        ["Buque de diseño", f"{V.fmt(c.vessel.bhp, 0)} BHP, eslora ≤ {V.fmt(c.vessel.length_m, 0)} m, manga {V.fmt(c.vessel.beam_m, 1)} m", "Tipo de buques"],
        ["Buque de la clase", "180 BHP (flotación Ffz promediada, cable dimensionado con 180 HP)", "Mec!O261, Rem!E81"],
        ["Hélice para ROB y flotación", "paso fijo, K_F = 10 kgf/HP (Fridman)", "PotOK!L11"],
        ["Portón", f"plano de madera FAO, {V.fmt(d.length_m, 2)} × {V.fmt(d.height_m, 2)} m, S = {V.fmt(d.area_m2, 3)} m², {V.fmt(d.weight_air_kg, 0)} kg", "Tablas de Referencias!A245"],
        ["Ángulo de ataque del portón", f"{V.fmt(c.door_attack_angle_deg, 0)}° (C_L = 0,93, C_D = 0,71)", "Port!C134"],
        ["Cable filado", f"{V.fmt(C150.rigging.towing.warp_m, 0)} m (5 × profundidad)", "Mec!E177"],
        ["Velocidades", "1 a 5 kn cada 0,5 kn", "PotOK!B10:B18"],
    ],
)
```

El buque de 180 HP no es un caso aparte: el libro calcula los dos buques de la clase lado a lado, y
dos resultados los acoplan (la flotación total de Fridman promedia ambos bloques y el cable se
dimensiona con 180 HP, ver {doc}`motor`). Por eso cada corrida lleva al otro buque en
`class_vessels`, y lo que cambia entre ellas es el **tiro disponible**.

## Resultados principales

```{code-cell} ipython3
:tags: [hide-input]
def row(label, f, nd=2, unit=""):
    a, b = f(C150), f(E150)
    if isinstance(a, str):
        return [label, a, b, "—" if a == b else "cambia"]
    return [label + (f" [{unit}]" if unit else ""), V.fmt(a, nd), V.fmt(b, nd),
            V.pct_s(a, b) if b else "—"]

i3, i35 = I[3.0], I[3.5]
rows = [
    row("Lima (relinga superior)", lambda r: r.dimensions.std.headrope_m, 2, "m"),
    row("Burlón (relinga inferior)", lambda r: r.dimensions.std.footrope_m, 2, "m"),
    row("Superficie sólida Sₛ, estándar", lambda r: r.geometry.std.solid_surface_m2, 2, "m²"),
    row("Superficie sólida Sₛ, modificada", lambda r: r.geometry.mod.solid_surface_m2, 2, "m²"),
    row("Peso de la red estándar en aire", lambda r: r.geometry.std.weight_air_kg, 1, "kg"),
    row("Abertura vertical (Suzuki)", lambda r: r.spread.vertical.suzuki_m, 2, "m"),
    row("Abertura horizontal AH", lambda r: r.spread.horizontal_opening_m, 2, "m"),
    row("Distancia entre portones", lambda r: r.doors.spread_m, 1, "m"),
    row("Rₙ de diseño a 3 kn (Aberdeen)", lambda r: r.drag.rn.std[i3], 0, "kgf"),
    row("Resistencia total a 3,5 kn", lambda r: r.warps.total.std[i35], 0, "kgf"),
    row("Flotación total (redondeada)", lambda r: r.floats.flotation_rounded_kgf, 0, "kgf"),
    row("Boyas", lambda r: f"{r.floats.count}\u00a0×\u00a0{r.floats.diameter_mm:.0f}\u00a0mm"),
    row("Lastre mínimo", lambda r: r.ballast.limits.min_kg, 0, "kg"),
    row("Lastre máximo", lambda r: r.ballast.limits.max_kg, 0, "kg"),
    row("Carga de rotura mínima del cable", lambda r: r.warps.loads.min_breaking_load_kgf / 1000, 2, "t"),
    row("Cable seleccionado", lambda r: f"{r.warps.selection.diameter_mm:.0f}\u00a0mm, "
        f"{V.fmt(r.warps.selection.breaking_load_t, 2)}\u00a0t"),
    row("Velocidad máxima (150 HP, PF, estándar)", lambda r: r.performance.design.max_speed_kn, 2, "kn"),
]
V.md_table(["Resultado (150 BHP)", "Corregido", "Excel", "Δ corregido vs Excel"], rows)
```

La columna `excel` reproduce el libro original. La celda siguiente lo comprueba contra los valores
cacheados del Excel (`tests/golden`) con la misma tolerancia que la suite de tests:

```{code-cell} ipython3
DIM, RES = "dimensiones_de_la_red", "resistencia_de_la_red"
REM, FLOT = "cables_de_remolque", "flotacion_y_lastre"
e = E150  # corrida en modo Excel, 150 BHP
checks = [
    (e.dimensions.std.headrope_m, golden(DIM, "headrope_m")),
    (e.dimensions.std.footrope_m, golden(DIM, "footrope_m")),
    (e.geometry.std.solid_surface_m2, golden(DIM, "solid_surface_std_m2")),
    (e.drag.rn.std / 1000, golden(RES, "aberdeen_demersal_rn_std_t")),
    (e.warps.total.std, golden(REM, "total_drag_std_kgf")),
    (e.warps.selection.diameter_mm, golden(DIM, "warp_diameter_mm")),
    (e.floats.flotation_rounded_kgf, golden(FLOT, "flotation_total_rounded_kgf")),
    (e.ballast.limits.min_kg, golden(FLOT, "ballast_min_150_kg")),
    (e.ballast.limits.max_kg, golden(FLOT, "ballast_max_150_kg")),
]
for got, ref in checks:
    assert np.allclose(got, ref, rtol=1e-6, atol=0)
f"{len(checks)} comprobaciones contra el libro Excel: OK"
```

Las diferencias entre columnas son las erratas del libro ({doc}`erratas`): el corregido mide el burlón
completo (33,39 m en vez del truncado 33,3), no infla la superficie sólida de la bolsa estándar
(38,75 m² en vez de 40,90), suma la resistencia de los portones a la demanda total y, con ella,
pide un cable de 13 mm porque el de 12 mm (8,55 t) no alcanza la carga de rotura mínima. Lo demás
(relingas, aberturas geométricas, flotación, boyas) coincide entre modos.

## Láminas de la red

Las láminas se dibujan desde el resultado corregido con `trawlkit.drawing.net_sheet_svg` (ver
{doc}`informes`). Sólo cambia la bolsa: la estándar tiene dos paños de 40 mm (I superior de 200
mallas de alto y J inferior de 250), la modificada un único paño I′ de 30 mm, 139 × 300 mallas,
repetido arriba y abajo.

```{code-cell} ipython3
---
tags: [hide-input, full-width]
mystnb:
  figure:
    caption: Lámina A3 de la red FAO A-3 estándar (bolsa de 40 mm), modo corregido.
    name: fig-30-lamina-std
---
V.sheet_svg(C150, "std")
```

```{code-cell} ipython3
---
tags: [hide-input, full-width]
mystnb:
  figure:
    caption: Lámina A3 de la red FAO A-3 modificada para crustáceos (bolsa de 30 mm), modo corregido.
    name: fig-30-lamina-mod
---
V.sheet_svg(C150, "mod")
```

## Tiro disponible y demanda: 150 frente a 180 HP

La ventana de velocidad ({doc}`19_ventana_velocidad`) es el intervalo en el que el tiro de Fridman
$F_T(v)$ supera la resistencia total $R_T(v) = R_N + R_B + R_W + R_{OB}$. La demanda no depende del
buque; el tiro sí, y depende tanto de la potencia como de la hélice: paso fijo (PF, $K_F = 10$) o
paso variable con tobera (PV+T, $K_F = 15$).

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Tiro de Fridman (PF y PV+T) frente a la resistencia total de la red estándar y la
      modificada, modo corregido. La zona sombreada es la ventana viable con hélice de paso fijo y
      red estándar; los anillos marcan la velocidad máxima remolcable $v^*$ de cada combinación.
    name: fig-30-ventana
---
fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.2), sharey=True)
for ax, r, bhp in zip(axes, (C150, C180), (150, 180)):
    W = r.performance.windows
    pf, pvt = W["fixed_pitch_std"].available_kgf, W["variable_pitch_nozzle_std"].available_kgf
    dstd, dmod = r.performance.demand.std, r.performance.demand.mod
    vs = W["fixed_pitch_std"].max_speed_kn
    vv = np.linspace(kn[0], vs, 60)
    ax.fill_between(vv, np.interp(vv, kn, dstd), np.interp(vv, kn, pf), color=V.BLUE_150,
                    alpha=0.45, lw=0, zorder=1)
    ax.plot(kn, pf, color=V.SERIES[0], zorder=3)
    ax.plot(kn, pvt, color=V.SERIES[1], zorder=3)
    ax.plot(kn, dstd, color=V.INK, lw=1.8, zorder=3, label="Rₜ red estándar")
    ax.plot(kn, dmod, color=V.INK_2, lw=1.4, ls=(0, (4, 2)), zorder=3, label="Rₜ red modificada")
    for key in ("fixed_pitch_std", "variable_pitch_nozzle_std"):
        w = W[key]
        y = float(np.interp(w.max_speed_kn, kn, w.available_kgf))
        ax.plot([w.max_speed_kn], [y], "o", ms=11, mfc="none", mec=V.INK_2, mew=1.2, zorder=4)
        ax.annotate(f"v* = {V.fmt(w.max_speed_kn, 2)} kn", (w.max_speed_kn, y), xytext=(8, -14),
                    textcoords="offset points", fontsize=8.5, color=V.INK_2)
    V.end_label(ax, 5.0, pf[-1], "Fₜ PF", dy=-2)
    V.end_label(ax, 5.0, pvt[-1], "Fₜ PV+T")
    ax.set_title(f"{bhp} BHP")
    ax.set_xlabel("Velocidad de arrastre [kn]")
    ax.set_xlim(1, 5)
    ax.set_ylim(0, 4400)
axes[0].set_ylabel("Fuerza [kgf]")
axes[0].legend(loc="upper left")
fig.tight_layout()
plt.show()
```

```{code-cell} ipython3
:tags: [hide-input]
combos = [("fixed_pitch", "PF"), ("variable_pitch_nozzle", "PV+T")]
rows = []
for bhp, rc, re_ in ((150, C150, E150), (180, C180, E180)):
    for key, lab in combos:
        a, b = rc.performance.windows, re_.performance.windows
        rows.append([f"{bhp} BHP, {lab}",
                     V.fmt(a[f"{key}_std"].max_speed_kn, 2), V.fmt(a[f"{key}_mod"].max_speed_kn, 2),
                     V.fmt(b[f"{key}_std"].max_speed_kn, 2), V.fmt(b[f"{key}_mod"].max_speed_kn, 2)])
V.md_table(["Buque y hélice", "v* estándar, corregido [kn]", "v* modificada, corregido [kn]",
            "v* estándar, Excel [kn]", "v* modificada, Excel [kn]"], rows)
```

Tres lecturas:

* **La hélice pesa más que los 30 HP.** Con paso fijo, el buque de 150 HP sólo remolca la red hasta
  2,28 kn, y el de 180 HP hasta 2,54 kn. Cambiar a paso variable con tobera, sin tocar el motor,
  lleva el límite a 2,99 kn (150 HP) y 3,29 kn (180 HP): +0,71 y +0,75 kn, frente a los +0,26 kn
  que aportan 30 HP más con paso fijo.
* **El margen es estrecho.** La red sola ya consume casi todo el tiro: a 2,5 kn la resistencia de la
  red estándar es el 90 % de la demanda total y equivale al 97 % del tiro PF del buque de 150 HP.
* **El modo corregido es más exigente**: suma a la demanda la resistencia de los dos portones y
  corrige la bolsa estándar, que en el Excel aparecía más pesada que la modificada (las diferencias
  de velocidad se calculan en la tabla de arriba).

## Red estándar frente a modificada: lo que cuesta la bolsa de 30 mm

La bolsa modificada tiene malla más chica y más mallas (139 × 300 frente a 113 × 200/250): más
hilo en el agua por metro cuadrado de paño, más superficie sólida y por lo tanto más resistencia en
cualquier método basado en $S_s$.

```{code-cell} ipython3
:tags: [hide-input]
rows = []
for v in (2.0, 2.5, 3.0, 3.5):
    i = I[v]
    rs, rm = C150.drag.rn.std[i], C150.drag.rn.mod[i]
    es, em = E150.drag.rn.std[i], E150.drag.rn.mod[i]
    rows.append([V.fmt(v, 1), V.fmt(rs, 0), V.fmt(rm, 0),
                 f"{V.sfmt(rm - rs, 0)} ({V.pct_s(rm, rs)}\u00a0%)",
                 f"{V.sfmt(em - es, 0)} ({V.pct_s(em, es)}\u00a0%)"])
gs, gm = C150.geometry.std.solid_surface_m2, C150.geometry.mod.solid_surface_m2
V.md_table(["v [kn]", "Rₙ estándar [kgf]", "Rₙ modificada [kgf]",
            "Δ Rₙ corregido [kgf]", "Δ Rₙ Excel [kgf]"], rows)
print(f"Sₛ estándar = {V.fmt(gs)} m², Sₛ modificada = {V.fmt(gm)} m² ({V.pct_s(gm, gs)} %)")
```

```{code-cell} ipython3
---
tags: [hide-input]
mystnb:
  figure:
    caption: |
      Diferencia de resistencia de la red (modificada − estándar) según la velocidad. En el modo
      corregido la bolsa de 30 mm cuesta un 3,3 % más; en el Excel, la errata de la bolsa
      estándar (`codend_minor_side_uses_depth`) invierte el signo y la modificada parece más liviana.
    name: fig-30-bolsa
---
fig, ax = plt.subplots(figsize=(7.4, 3.4))
w = 0.18
dc = C150.drag.rn.mod - C150.drag.rn.std
de = E150.drag.rn.mod - E150.drag.rn.std
ax.bar(kn - w / 2, dc, width=w * 0.95, color=V.SERIES[0], label="Corregido", zorder=3)
ax.bar(kn + w / 2, de, width=w * 0.95, color=V.MUTED, label="Excel (con errata)", zorder=3)
ax.axhline(0, color=V.INK_2, lw=0.8, zorder=4)
for x, y in zip(kn[::2], dc[::2]):
    ax.annotate(V.fmt(y, 0), (x - w / 2, y), xytext=(0, 3), textcoords="offset points",
                ha="center", fontsize=8, color=V.INK_2)
ax.set_xticks(kn)
ax.set_xlabel("Velocidad de arrastre [kn]")
ax.set_ylabel("Rₙ modificada − Rₙ estándar [kgf]")
ax.legend(loc="lower left", ncol=2)
fig.tight_layout()
plt.show()
```

En modo corregido la bolsa de 30 mm agrega 1,28 m² de superficie sólida (+3,3 %) y, como la
resistencia de diseño de Aberdeen es proporcional a $S_s$, el mismo +3,3 % de $R_N$: ≈ 40 kgf a
2,5 kn y ≈ 68 kgf a 3,5 kn. Sobre la ventana el efecto es chico, entre −0,04 y −0,06 kn de
velocidad máxima según buque y hélice. Es decir: **la retención de langostilla con la bolsa de 30 mm
cuesta poco en tiro**; el factor limitante sigue siendo el buque y su hélice. El libro original
llegaba a la conclusión contraria (la modificada "resiste menos") por la errata de la bolsa
estándar, que contaba 200 mallas como lado menor en vez de 113.

## Recomendaciones de diseño

Las recomendaciones siguientes son **salidas del modelo** con los supuestos de este capítulo (modo
corregido, Fridman para el tiro, Aberdeen demersal para la red, cable de 200 m a 40 m de
profundidad). No reemplazan la prueba en el mar; {doc}`32_validacion_dynamit` muestra que la
resistencia empírica de diseño queda ≈ 18 % por encima de la que simula DynamiT, de modo que son
recomendaciones del lado conservador.

```{code-cell} ipython3
:tags: [hide-input]
# Velocidad mínima: la DPA de Fridman (que crece con v) alcanza el 85 % de la AH geométrica.
ah = C150.spread.horizontal_opening_m
dpa = np.asarray(C150.spread.fridman.dpa_std_m)
v_min = float(np.interp(0.85 * ah, dpa, kn))
fl = C150.floats
unit = fl.catalogue_buoyancy_kgf[fl.catalogue_diameters_mm.index(fl.diameter_mm)]
ws = C150.warps
V.md_table(
    ["Elemento", "Recomendación (salida del modelo)", "Criterio"],
    [
        ["Velocidad mínima", f"≈ {V.fmt(v_min, 1)} kn",
         f"DPA de Fridman ≥ 85 % de AH = {V.fmt(ah, 1)} m"],
        ["Velocidad máxima, 150 HP", f"PF: {V.fmt(C150.performance.windows['fixed_pitch_mod'].max_speed_kn, 2)} kn · PV+T: "
         f"{V.fmt(C150.performance.windows['variable_pitch_nozzle_mod'].max_speed_kn, 2)} kn", "Fₜ ≥ Rₜ, red modificada"],
        ["Velocidad máxima, 180 HP", f"PF: {V.fmt(C180.performance.windows['fixed_pitch_mod'].max_speed_kn, 2)} kn · PV+T: "
         f"{V.fmt(C180.performance.windows['variable_pitch_nozzle_mod'].max_speed_kn, 2)} kn", "Fₜ ≥ Rₜ, red modificada"],
        ["Cable de remolque", f"Ø {ws.selection.diameter_mm:.0f} mm ({ws.selection.construction}), "
         f"rotura {V.fmt(ws.selection.breaking_load_t, 2)} t; {V.fmt(ws.warp_m, 0)} m filados, "
         f"{V.fmt(ws.quantity_m, 0)} m a comprar (2 cables + {V.fmt(ws.quantity_m - 2 * ws.warp_m, 0)} m de reserva)",
         f"rotura mínima {V.fmt(ws.loads.min_breaking_load_kgf / 1000, 2)} t (4 × Rₜ a 3,5 kn)"],
        ["Flotación", f"{fl.count} boyas de {fl.diameter_mm:.0f} mm (≈ {V.fmt(fl.count * unit, 0)} kgf), "
         f"{fl.distribution.per_wing} por ala y {fl.distribution.on_bosom} en el centro",
         f"Fridman, promedio 1–3 kn: {V.fmt(fl.flotation_rounded_kgf, 0)} kgf"],
        ["Lastre del burlón", f"{V.fmt(C150.ballast.limits.min_kg, 0)}–{V.fmt(C150.ballast.limits.max_kg, 0)} kg",
         "Fridman: modificada a 1 kn / estándar a 3 kn"],
        ["Portones", f"FAO plano {V.fmt(C150.case.door.area_m2, 3)} m² a 32° (requerido ≈ "
         f"{V.fmt(C150.doors.required_area_per_door_class_m2, 2)} m² por portón)", "ROB = 20 % de Fₜ, promedio 2–4 kn"],
    ],
)
```

En palabras:

1. **Velocidad de arrastre.** Por debajo de ≈ 2,1 kn la red no termina de abrirse horizontalmente
   según Fridman (la DPA no llega al 85 % de la abertura geométrica); por encima de $v^*$ el buque no
   la remolca. Con **150 HP y paso fijo la ventana de la red modificada es de apenas 2,1–2,25 kn**:
   operable, pero sin reserva para corriente, mar o captura en la bolsa. Con **paso variable y
   tobera** el rango útil pasa a 2,1–2,9 kn (150 HP) o 2,1–3,2 kn (180 HP), y es la configuración
   recomendada para la red modificada.
2. **Cable.** 13 mm de acero 6 × 19 Seale (10,3 t de rotura). El de 12 mm que eligió el libro queda
   por debajo de la rotura mínima (8,55 t < 10,1 t) una vez que la demanda incluye los portones.
3. **Flotación.** 12 boyas de 200 mm, cinco por ala y dos en el centro de la lima.
4. **Lastre.** Entre 27 y 41 kg de cadena repartida en el burlón: 27 kg bastan para mantener el
   burlón en el fondo a 1 kn con la red modificada y 41 kg lo mantienen a 3 kn con la estándar; más
   lastre sólo aumenta el rozamiento y hace que el burlón "are" el fondo.
5. **Portones.** El portón FAO de 1,805 m² está en el orden de la superficie requerida
   (≈ 1,8 m² por portón): adecuado, pero sin margen si se quisiera más abertura.

## Limitaciones

* **Métodos empíricos.** La resistencia de la red sale de una sola fórmula (Aberdeen demersal) de
  las trece de {doc}`14_resistencia`, cuya dispersión supera ±50 %. La comparación con DynamiT
  ({doc}`32_validacion_dynamit`) sugiere que Aberdeen sobrestima la resistencia de esta red en
  ≈ 18 %, de modo que las velocidades máximas de este capítulo son conservadoras.
* **Tiro de Fridman.** Es una recta acotada, sin curva de hélice real ni estado del casco; las otras
  cuatro escuelas de {doc}`10_potencia` dan tiros hasta 2:1 distintos a 3 kn.
* **Portones en la demanda.** El modo corregido suma a $R_T$ la resistencia de los dos portones
  (≈ 434 kgf a 3,5 kn); el Excel no los suma (errata `warp_total_omits_doors`, ver la sensibilidad
  de {doc}`19_ventana_velocidad`).
* **Casco y estado del mar.** La demanda no incluye la resistencia del casco $R_H$ ni la de la captura
  en la bolsa; ambas reducen la ventana.
* **Geometría fija.** La flecha de la lima usa $f_L/L = 0{,}216$ fijo (errata
  `catenary_ratio_hardcoded`), la separación de portones es una regla por metro de cable y el cable
  filado es 5 × la profundidad: el modelo no resuelve el equilibrio del arte, que es lo que hace un
  simulador como DynamiT.
* **Una sola red y un solo fondo.** Los resultados valen para la A-3 a 40 m. Otra profundidad cambia
  el cable filado, la separación de portones y las aberturas; hay que volver a correr el caso.
