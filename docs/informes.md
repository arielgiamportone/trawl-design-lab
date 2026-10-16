# Informes y planos

`trawlkit` genera, a partir de un caso de diseño, el plano de la red y un informe completo.

## Desde la línea de comandos

```bash
# Informe completo: HTML, PDF, XLSX y láminas SVG
uv run trawlkit report data/fao_a3_standard.yaml --modified data/fao_a3_modified.yaml \
    --vessel fao_a3_150hp --out informe/

# Sólo algunos formatos
uv run trawlkit report data/fao_a3_standard.yaml --format html,xlsx --out informe/

# Plano suelto: lámina técnica (sheet) o escala real (scale), red estándar o modificada
uv run trawlkit plan data/fao_a3_standard.yaml --view sheet --out lamina.svg
uv run trawlkit plan data/fao_a3_standard.yaml --modified data/fao_a3_modified.yaml \
    --view scale --variant mod --out escala_mod.svg
```

El PDF requiere el extra `report` (`pip install "trawlkit[report]"`) y las librerías Pango del
sistema que usa WeasyPrint.

## Desde Python

```python
from trawlkit import DesignCase, run
from trawlkit.drawing import net_scale_svg, net_sheet_svg
from trawlkit.report.build import build_report

result = run(case)  # ver docs/motor.md para armar el caso
svg = net_sheet_svg(result, "std")  # lámina A3
paths = build_report(result, "informe/", formats=("html", "pdf", "xlsx", "svg"))
```

## Qué contiene

| Salida | Contenido |
|---|---|
| `informe.html` | Página autocontenida (sin conexión ni JavaScript), modo claro y oscuro: portada, resumen con indicadores, láminas, escala real, gráficos, tablas, erratas, notas, metodología y créditos. |
| `informe.pdf` | El mismo HTML impreso: A4 vertical, tablas anchas en A4 apaisado y láminas en A3 apaisado. |
| `informe.xlsx` | Una hoja por tabla (resumen, paneles, potencia, resistencia, demanda, aparejo, boyas y lastre, cable, ventana de velocidad, erratas) más "Caso" con todos los parámetros y "Notas". |
| `plano_estandar.svg`, `plano_modificada.svg` | Lámina técnica A3 como los planos de 2014: planos superior e inferior, mallas por borde, códigos de corte, tablas laterales, relingas, superficie y peso por plano, esquema del aparejo y rótulo. |
| `plano_escala_*.svg` | Vista a escala real en metros con grilla de 1 m, cotas por panel, escala gráfica, largos estirados y armados y escalones donde cambia el coeficiente de armado. |

## Gráficos

1. Tiro disponible por método frente a la resistencia total (estándar y modificada), con la ventana
   de velocidad viable sombreada y la velocidad máxima marcada.
2. Resistencia de la red por los 13 métodos, con el método de diseño (Aberdeen demersal) destacado.
3. Composición de la resistencia total a 3.5 nudos: red, boyas, cables y portones.
4. Distancia entre puntas de ala y abertura vertical de Fridman según la velocidad.

## Diferencias con los planos de 2014

Las láminas salen del modelo, no se copian del dibujo. Por eso algunos valores difieren del plano
original: en modo corregido el burlón mide 33,39 m, la superficie sólida 38,75 m², las patentes 25 m,
la flotación 36 kgf y el cable seleccionado es de 13 mm. El dibujo no inventa datos que el modelo no
tiene (por ejemplo, el diámetro de patentes y bridas).

Ejemplos generados: carpeta `examples/fao_a3/` del repositorio.
