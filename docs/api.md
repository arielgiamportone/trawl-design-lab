# API HTTP

La API expone el motor por HTTP. Se levanta con `uv run trawlkit serve` (puerto 8000) y la
documentación interactiva queda en `http://127.0.0.1:8000/docs`. El contrato completo está en
`web/openapi.json`; esta página se genera a partir de él.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Comprobación de vida. |
| GET | `/catalog/nets` | Redes predefinidas. |
| GET | `/catalog/nets/{net_id}` | Especificación completa de una red predefinida (paneles, relingas, boyas). |
| GET | `/catalog/vessels` | Buques del catálogo. |
| GET | `/catalog/doors` | Portones del catálogo con su polar CL/CD. |
| GET | `/params` | Parámetros de diseño sobrescribibles en `DesignRequest.params`. |
| GET | `/errata` | Erratas del libro Excel original. |
| POST | `/design` | Calcula un caso de diseño completo. |
| POST | `/design/plan` | Plano SVG del caso: lámina técnica (`sheet`) o escala real (`scale`). |
| POST | `/optimize` | Optimiza la escala de la red y la velocidad de arrastre (malla + evolución diferencial). |
| POST | `/design/report` | Informe del caso en HTML, PDF o XLSX. |

## Ejemplo

```bash
curl -s -X POST http://127.0.0.1:8000/design \
  -H 'Content-Type: application/json' \
  -d '{"net": "fao_a3_standard", "net_modified": "fao_a3_modified", "vessel": "fao_a3_150hp", "compat": "excel"}'
```

El cuerpo `DesignRequest` acepta redes, buques y portones por id del catálogo o como especificación
completa, el modo de cálculo y `params` con los parámetros de `GET /params`. Los ids se validan
contra el catálogo; los parámetros numéricos deben ser finitos y no negativos.

La variable `TRAWLKIT_CORS_ORIGINS` limita los orígenes permitidos (por defecto `*`).
