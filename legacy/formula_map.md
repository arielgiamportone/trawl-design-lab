# Mapa de fórmulas: Excel → trawlkit

| Hoja | Módulo destino |
|---|---|
| Especie Blanco, Tipo de buques | `trawlkit.io` (spec YAML: `species`, `vessel`) |
| Potenc disponible para arrastre, Potencia Disponible Arrastre OK | `trawlkit.vessel`, `trawlkit.power` |
| Paños de red y cortes | `trawlkit.netting` |
| Cables Y Cabulleria | `data/ropes.yaml`, `trawlkit.rigging.warps` |
| Mecánica de la Red | `trawlkit.net`, `trawlkit.rigging.spread` |
| Dimensiones de la Red | `trawlkit.dimensions` |
| Resistencia de la RED | `trawlkit.drag` |
| Portones y aparejamiento | `trawlkit.rigging.doors`, `trawlkit.rigging.bridles` |
| Flotación y Lastre | `trawlkit.rigging.floats`, `trawlkit.rigging.ballast` |
| Cables de Remolque | `trawlkit.rigging.warps` |
| Tablas de Referencias | `data/reference/*.csv`, `trawlkit.materials` |

El detalle bloque a bloque se genera en la Fase 1 con `tools/extract_excel.py`.
