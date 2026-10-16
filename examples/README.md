# Ejemplos generados

Informe completo del caso de estudio: red FAO A-3 estándar y modificada, buque de 150 BHP
(con el de 180 BHP como buque de la clase, como en el Excel original) y portón plano FAO.

| Carpeta | Modo | Qué muestra |
|---|---|---|
| `fao_a3/corregido/` | `Compat.CORRECTED` | Fórmulas corregidas (modo por defecto para diseño real). |
| `fao_a3/excel/` | `Compat.EXCEL` | Reproduce los números del libro Excel original, erratas incluidas. |

Cada carpeta contiene `informe.html` (abre en cualquier navegador, sin conexión), `informe.pdf`,
`informe.xlsx` y las láminas `plano_*.svg`.

Para regenerarlos:

```bash
uv run trawlkit report fao_a3_standard --modified fao_a3_modified \
    --vessel fao_a3_150hp --out examples/fao_a3/corregido
uv run trawlkit report fao_a3_standard --modified fao_a3_modified \
    --vessel fao_a3_150hp --compat excel --out examples/fao_a3/excel
```
