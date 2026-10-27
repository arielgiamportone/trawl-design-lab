# Datos

Todo lo que hay aquí se genera con `uv run python tools/extract_excel.py` a partir de
`legacy/Calculos_Red_FAO_A3.xlsx`; cada valor lleva la celda de origen (`source`/`source_cells`).
No editar a mano: corregir el extractor y regenerar.

La carpeta forma parte del paquete (`trawlkit/data`, `trawlkit.io.DATA_DIR`) y se instala con la
rueda: los presets (`fao_a3_standard`, `fao_a3_modified`, …) funcionan fuera del checkout.

| Archivo | Contenido | Modelo |
|---|---|---|
| `fao_a3_standard.yaml` | Red FAO A-3 estándar (bolsa 40 mm): especie, 10 paneles A..J, relingas, boyas, lastre | `NetSpec` |
| `fao_a3_modified.yaml` | Variante para crustáceos (bolsa 30 mm, panel I') | `NetSpec` |
| `vessels.yaml` | Buques de 150 y 180 BHP | `VesselCatalogue` |
| `vessels/*.yaml` | Flota argentina (Fase 19.4): tipos de buque con las medias publicadas (INIDEP, FAO, CFP) y buques con características publicadas, con fuente y procedencia por campo (no salen del Excel) | `VesselCatalogue` |
| `reference/kartha1966_trawlers.yaml` | Hélices y tiro medido de ocho arrastreros de la India (Kartha y Roy Choudhury 1966), para validar el tiro por la hélice | YAML |
| `doors.yaml` | Portón plano FAO de madera y Morgère polivalente oval, con CL/CD por ángulo | `DoorCatalogue` |
| `floats.yaml`, `ropes.yaml`, `chains.yaml`, `warps.yaml`, `materials.yaml` | Catálogos | `Catalogue` |
| `reference/*.csv` | Proporciones de Nomura, razones de corte, factor K de nudos, catenaria, ángulos útiles, altura de brazo dan leno, profundidad→cable filado | CSV |
| `reference/power_coefficients.yaml` | Coeficientes empíricos de potencia disponible (Fridman, Prado-Dremière, Koyama, Nomura, Hamuro) | YAML |

Convención de paneles: `meshes_top` es el borde más cercano a la boca de la red y `meshes_bottom`
el más cercano a la bolsa (como en los planos); `meshes_a`/`meshes_b` conservan el T1/T2
(mayor/menor) del Excel.

Licencia: CC BY 4.0 (ver `LICENSE-docs`).
