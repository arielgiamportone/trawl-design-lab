# Despliegue en línea (vista previa)

La aplicación puede probarse en línea sin instalar nada. La vista previa usa dos servicios
gratuitos:

| Pieza | Dónde | URL |
|---|---|---|
| Libro (esta documentación) | GitHub Pages | <https://arielgiamportone.github.io/trawl-design-lab/> |
| Aplicación web (React) | GitHub Pages, junto al libro | <https://arielgiamportone.github.io/trawl-design-lab/app/> |
| API (FastAPI + motor `trawlkit`) | Render, plan gratuito (Docker) | <https://trawl-design-lab-api.onrender.com> (documentación interactiva en `/docs`) |

## Arquitectura

```
navegador ──► GitHub Pages ──► /trawl-design-lab/        libro (Jupyter Book)
                           └─► /trawl-design-lab/app/    app web estática (web/dist)
          │
          ├── fetch (CORS) ──► Render: trawl-design-lab-api (contenedor Docker)
          │                    uvicorn trawlkit.api.app:app, GET /health, POST /design, …
          └── sin red ───────► Web Worker con Pyodide: la wheel de trawlkit (app/py/)
                               trawlkit.api.offline, las mismas rutas sin servidor
```

- **Libro y app** se construyen en el mismo flujo de GitHub Actions (`.github/workflows/docs.yml`):
  primero el libro (`jupyter-book build docs -W`), después la app con
  `VITE_BASE=/trawl-design-lab/app/` y la URL de la API, y se copia `web/dist` a
  `docs/_build/html/app/`. Se publica un único artefacto de Pages en cada push a `main`.
- **Motor sin conexión**: el mismo flujo construye la *wheel* de `trawlkit` y la empaqueta con
  `tools/offline_bundle.py` en `web/public/py/` (con `manifest.json`, la huella del contrato y las
  ruedas puras que necesita en Pyodide, como openpyxl para los lotes en XLSX). La app la descarga
  cuando el usuario elige «Preparar uso sin conexión» y la corre en un *Web Worker*
  ({doc}`web`). La CI prueba que esa rueda dé en Pyodide las mismas respuestas que CPython
  (`web/scripts/pyodide-parity.mjs`, tolerancia relativa 1e-9).
- **API**: `Dockerfile` en la raíz (Python 3.12, Pango para los PDF de WeasyPrint, dependencias
  fijadas por `uv.lock` con los extras `api`, `report` y `optimize`, usuario sin privilegios,
  puerto `$PORT`). `render.yaml` es el *Blueprint* que describe el servicio. Render reconstruye la
  imagen en cada commit de `main` que pasa la CI y que toca `src/`, `pyproject.toml`, `uv.lock` o
  el `Dockerfile`.
- La CI (`.github/workflows/ci.yml`, job `docker`) construye la misma imagen, la arranca y prueba
  `/health`, `POST /design`, el informe PDF y la cabecera CORS para GitHub Pages.

## Pasos para publicarla

El repositorio ya contiene todo lo necesario; faltan tres pasos que sólo puede hacer el dueño de
las cuentas:

1. **Activar GitHub Pages.** En GitHub: *Settings → Pages → Build and deployment → Source:*
   **GitHub Actions**. Luego relanzar el flujo «Docs» (*Actions → Docs → Run workflow*) o hacer un
   push a `main`. El libro queda en `/trawl-design-lab/` y la app en `/trawl-design-lab/app/`.
2. **Crear la API en Render.** En <https://dashboard.render.com>: *New → Blueprint*, conectar la
   cuenta de GitHub, elegir el repositorio `trawl-design-lab` y pulsar **Apply** (Render lee
   `render.yaml`; no hace falta completar nada). La primera construcción tarda unos minutos.
   Cuando termine, comprobar `https://trawl-design-lab-api.onrender.com/health`.
3. **Sólo si la URL de Render es distinta** (por ejemplo, si el nombre `trawl-design-lab-api` ya
   estaba tomado y Render agregó un sufijo): en GitHub, *Settings → Secrets and variables →
   Actions → Variables → New repository variable*, nombre `TRAWLKIT_API_URL`, valor la URL del
   servicio (sin barra final, p. ej. `https://trawl-design-lab-api-x1y2.onrender.com`), y relanzar
   «Docs». La app se recompila apuntando a esa URL; no hay que tocar código.

## Limitaciones del plan gratuito

- **Suspensión por inactividad.** Render duerme el servicio tras unos 15 minutos sin tráfico. El
  primer pedido después de eso tarda **30–60 s** mientras el contenedor arranca. La app lo maneja:
  el indicador de la cabecera muestra «Conectando…», luego «Despertando la API (puede tardar hasta
  un minuto)…», reintenta `/health` con esperas crecientes durante ~90 s y sólo entonces carga los
  catálogos y calcula. Si no responde, muestra «API no disponible» con un botón «Reintentar».
- **CPU lenta (0,1 CPU, 512 MB).** El cálculo de un caso tarda algo más que en local, y las
  herramientas pesadas mucho más:
  - **Simulación**: usar la resolución **rápida**; la API rechaza pedidos con un costo estimado
    mayor que `TRAWLKIT_MAX_SIM_SECONDS` (20 s en Render).
  - **Optimización**: usar la malla por defecto y **sin refinado**; la malla se limita a
    `TRAWLKIT_MAX_OPT_GRID` × `TRAWLKIT_MAX_OPT_GRID` (15 × 15 en Render).
- **Horas gratuitas**: el plan gratuito tiene un cupo mensual de horas de instancia; mientras la
  app está abierta comprueba `/health` cada minuto, lo que mantiene el servicio despierto.

Los resultados son los mismos que en local: el motor y los datos son idénticos.

## Variables de entorno

| Variable | Dónde | Por defecto | En la vista previa | Uso |
|---|---|---|---|---|
| `TRAWLKIT_CORS_ORIGINS` | API | `*` | `https://arielgiamportone.github.io` | Orígenes permitidos, separados por comas (sin ruta ni barra final). |
| `TRAWLKIT_MAX_SIM_SECONDS` | API | `30` | `20` | Costo estimado máximo de `POST /simulate` [s]. |
| `TRAWLKIT_MAX_BATCH_SECONDS` | API | `120` | `90` | Costo estimado máximo de `POST /simulate/uncertainty` y `POST /simulate/calibrate` [s]. |
| `TRAWLKIT_MAX_OPT_GRID` | API | `25` | `15` | Lado máximo de la malla de `POST /optimize` (2–25). |
| `TRAWLKIT_ALLOW_REFINE` | API | permitido | permitido | `0`/`false` rechaza `refine: true` en `POST /optimize`. |
| `DATABASE_URL` | API | sin aula | Postgres de Neon (secreto) | Base del Aula UTN (cuentas, cursos, tareas y entregas). Sin ella, `/classroom` responde 503 y lo demás funciona igual. |
| `PORT` | API (Docker) | `8000` | lo fija Render | Puerto de escucha de uvicorn. |
| `VITE_API_URL` | app (compilación) | `http://127.0.0.1:8000` | variable del repo `TRAWLKIT_API_URL` o `https://trawl-design-lab-api.onrender.com` | URL base de la API. |
| `VITE_BASE` | app (compilación) | `/` | `/trawl-design-lab/app/` | Ruta pública de la app. |
| `VITE_DOCS_URL` | app (compilación) | sin enlace | `../` | Enlace «Documentación» de la cabecera (al libro). |

Las variables de la API se cambian en Render (*servicio → Environment*) o en `render.yaml`.

## Aula UTN: base de datos en Neon

El aula (cursos, alumnos, tareas, entregas y notas) necesita una base que sobreviva a los
despliegues; el disco del plan gratuito de Render se borra en cada uno. Se usa Postgres en
[Neon](https://neon.tech), cuyo plan gratuito no vence (0,5 GB alcanzan para muchos cursos).

1. **Crear la base.** En Neon, *New project* (región cercana a la de Render, p. ej. US West para
   `oregon`). En *Connection details*, copiar la cadena de conexión
   (`postgresql://usuario:clave@ep-….neon.tech/neondb?sslmode=require`). Es un secreto: no se
   pega en el repositorio ni en issues.
2. **Cargarla en Render.** *trawl-design-lab-api → Environment → Add environment variable*:
   `DATABASE_URL` con esa cadena (el `render.yaml` la declara con `sync: false`, así que Render la
   pide y no la versiona). Guardar redespliega la API; las tablas se crean solas en el primer
   pedido al aula.
3. **Crear el administrador**, una sola vez, desde una computadora con el repositorio (el plan
   gratuito de Render no tiene consola):

   ```bash
   uv sync --extra classroom
   export DATABASE_URL='postgresql://…neon.tech/neondb?sslmode=require'
   uv run trawlkit classroom migrate
   uv run trawlkit classroom create-admin --username ariel   # pide la contraseña
   ```
4. **Invitar a los docentes.** Con la cuenta de administrador, en la app (modo «Aula UTN» →
   *Invitaciones*) o con `uv run trawlkit classroom invite --username ariel --count 3`. Cada
   docente se registra con su código y crea sus cursos; los alumnos se registran con el código del
   curso.

`GET /classroom/status` dice si el aula está habilitada en el servidor. Para probar en local sin
Neon: `DATABASE_URL=sqlite:///aula.db uv run trawlkit serve`.

Datos personales: sólo usuario, nombre para mostrar (nombre o legajo) y la contraseña con hash
(scrypt); no hay correo. El docente resetea contraseñas de sus alumnos y cada usuario puede borrar
su cuenta con sus entregas.

## Probar el despliegue en local

Con Docker:

```bash
docker build -t trawlkit-api .
docker run --rm -p 8000:8000 -e TRAWLKIT_CORS_ORIGINS='*' trawlkit-api
curl http://127.0.0.1:8000/health
```

La app tal como se publica en Pages (bajo una sub-ruta):

```bash
cd web
VITE_BASE=/trawl-design-lab/app/ VITE_API_URL=http://127.0.0.1:8000 VITE_DOCS_URL=../ npm run build
mkdir -p /tmp/sitio/trawl-design-lab && cp -r dist /tmp/sitio/trawl-design-lab/app
python -m http.server 8080 --directory /tmp/sitio
# http://127.0.0.1:8080/trawl-design-lab/app/
```

Sin Docker, la API se levanta con `uv run trawlkit serve` (ver {doc}`web`).

## Problemas frecuentes

- **«API no disponible» al abrir la app.** Lo más común es que la API esté dormida y tardó más
  de lo esperado: pulsar «Reintentar». Si persiste, abrir la URL de la API + `/health` en el
  navegador; si no responde, revisar los *Logs* del servicio en Render (una construcción fallida
  deja el servicio sin desplegar).
- **Error de CORS en la consola** (`No 'Access-Control-Allow-Origin' header`): el origen de la app
  no está en `TRAWLKIT_CORS_ORIGINS`. El origen es sólo esquema y dominio
  (`https://arielgiamportone.github.io`), sin `/trawl-design-lab`. Si la app se publica en otro
  dominio, agregarlo separado por comas. Durante un arranque en frío Render puede responder con un
  error sin cabeceras CORS; el navegador lo informa como error de CORS pero se resuelve solo al
  terminar de arrancar.
- **La app apunta a otra URL.** La URL de la API queda fija al compilar: tras cambiar la variable
  `TRAWLKIT_API_URL` hay que relanzar el flujo «Docs».
- **«simulación demasiado costosa» o «malla de optimización demasiado grande».** Son las guardas
  de costo del servidor gratuito: bajar la resolución o la cantidad de velocidades, o el tamaño de
  la malla.
- **«Error 404: Not Found» en una función nueva, o «API desactualizada» en la cabecera.** La app
  de GitHub Pages es de una versión más nueva que la API de Render: la app llama a una ruta que la
  API todavía no tiene. `GET /health` informa `contract` (huella de las rutas de la API) y `commit`
  (el commit desplegado, `RENDER_GIT_COMMIT`); la app compara esa huella con la de su build y, si
  difieren, la cabecera muestra «API desactualizada» y los 404 de ruta explican la causa. Render
  redespliega solo cada commit de `main` con la CI en verde (unos minutos después). Si no pasa:
  Render → servicio `trawl-design-lab-api` → **Manual Deploy → Deploy latest commit**. El flujo
  «Docs» termina con el job `api-check`, que espera hasta 20 minutos a que la API sirva el mismo
  contrato que la app y deja un aviso en el resumen si no lo consigue
  (`python tools/check_api_contract.py URL_API` lo comprueba desde una terminal). Antes, el
  Blueprint tenía un `buildFilter` por rutas: si el último commit de un push no tocaba `src/`, la
  API no se redesplegaba aunque los anteriores sí la cambiaran. Se quitó; si el servicio se creó
  con el filtro, Render lo quita al sincronizar el Blueprint (o en *Settings → Build Filters*).
- **404 en `/trawl-design-lab/app/`.** Pages no está activado con fuente *GitHub Actions* o el
  flujo «Docs» todavía no corrió en `main`.
