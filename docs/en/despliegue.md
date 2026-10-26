# Online deployment (preview)

The application can be tried online without installing anything. The preview uses two free
services:

| Piece | Where | URL |
|---|---|---|
| Book (this documentation) | GitHub Pages | <https://arielgiamportone.github.io/trawl-design-lab/> (Spanish) and <https://arielgiamportone.github.io/trawl-design-lab/en/> (English) |
| Web application (React) | GitHub Pages, next to the book | <https://arielgiamportone.github.io/trawl-design-lab/app/> |
| API (FastAPI + `trawlkit` engine) | Render, free plan (Docker) | <https://trawl-design-lab-api.onrender.com> (interactive documentation at `/docs`) |

## Architecture

```
browser ──► GitHub Pages ──► /trawl-design-lab/        book (Jupyter Book), Spanish
                         ├─► /trawl-design-lab/en/     book, English edition (docs/en)
                         └─► /trawl-design-lab/app/    static web app (web/dist)
        │
        ├── fetch (CORS) ──► Render: trawl-design-lab-api (Docker container)
        │                    uvicorn trawlkit.api.app:app, GET /health, POST /design, …
        └── no network ────► Web Worker with Pyodide: the trawlkit wheel (app/py/)
                             trawlkit.api.offline, the same routes without a server
```

- **Book and app** are built in the same GitHub Actions workflow (`.github/workflows/docs.yml`):
  first the book (`jupyter-book build docs -W`), then the English edition
  (`jupyter-book build docs/en -W`, copied to `docs/_build/html/en/` and so published under
  `/trawl-design-lab/en/`), then the app with `VITE_BASE=/trawl-design-lab/app/` and the API URL,
  and `web/dist` is copied to `docs/_build/html/app/`. A single Pages artefact is published on
  each push to `main`.
- **Offline engine**: the same workflow builds the `trawlkit` *wheel* and packages it with
  `tools/offline_bundle.py` into `web/public/py/` (with `manifest.json`, the contract fingerprint
  and the pure wheels it needs in Pyodide, such as openpyxl for XLSX batches). The app downloads
  it when the user chooses “Prepare offline use” and runs it in a *Web Worker* ({doc}`web`). The
  CI tests that this wheel gives in Pyodide the same answers as CPython
  (`web/scripts/pyodide-parity.mjs`, relative tolerance 1e-9).
- **API**: `Dockerfile` at the root (Python 3.12, Pango for the WeasyPrint PDFs, dependencies
  pinned by `uv.lock` with the `api`, `report` and `optimize` extras, unprivileged user, port
  `$PORT`). `render.yaml` is the *Blueprint* that describes the service. Render rebuilds the image
  on each commit to `main` that passes CI and touches `src/`, `pyproject.toml`, `uv.lock` or the
  `Dockerfile`.
- The CI (`.github/workflows/ci.yml`, job `docker`) builds the same image, starts it and tests
  `/health`, `POST /design`, the PDF report and the CORS header for GitHub Pages.

## Steps to publish it

The repository already contains everything needed; three steps remain that only the owner of the
accounts can do:

1. **Enable GitHub Pages.** On GitHub: *Settings → Pages → Build and deployment → Source:*
   **GitHub Actions**. Then re-run the “Docs” workflow (*Actions → Docs → Run workflow*) or push
   to `main`. The book is at `/trawl-design-lab/` (English edition at `/trawl-design-lab/en/`)
   and the app at `/trawl-design-lab/app/`.
2. **Create the API on Render.** At <https://dashboard.render.com>: *New → Blueprint*, connect
   the GitHub account, choose the `trawl-design-lab` repository and press **Apply** (Render reads
   `render.yaml`; nothing needs to be filled in). The first build takes a few minutes. When it
   finishes, check `https://trawl-design-lab-api.onrender.com/health`.
3. **Only if the Render URL is different** (for example, if the name `trawl-design-lab-api` was
   already taken and Render added a suffix): on GitHub, *Settings → Secrets and variables →
   Actions → Variables → New repository variable*, name `TRAWLKIT_API_URL`, value the URL of the
   service (without a trailing slash, e.g. `https://trawl-design-lab-api-x1y2.onrender.com`), and
   re-run “Docs”. The app is rebuilt pointing at that URL; no code needs to be touched.

## Limitations of the free plan

- **Suspension after inactivity.** Render puts the service to sleep after about 15 minutes
  without traffic. The first request after that takes **30–60 s** while the container starts. The
  app handles it: the indicator in the header shows “Connecting…”, then “Waking up the API (this
  may take up to a minute)…”, retries `/health` with increasing waits for ~90 s and only then
  loads the catalogues and computes. If it does not respond, it shows “API unavailable” with a
  “Retry” button.
- **Slow CPU (0.1 CPU, 512 MB).** Computing a case takes somewhat longer than locally, and the
  heavy tools much longer:
  - **Simulation**: use the **fast** resolution; the API rejects requests with an estimated cost
    greater than `TRAWLKIT_MAX_SIM_SECONDS` (20 s on Render).
  - **Optimization**: use the default grid and **no refinement**; the grid is limited to
    `TRAWLKIT_MAX_OPT_GRID` × `TRAWLKIT_MAX_OPT_GRID` (15 × 15 on Render).
- **Free hours**: the free plan has a monthly quota of instance hours; while the app is open it
  checks `/health` every minute, which keeps the service awake.

The results are the same as locally: the engine and the data are identical.

## Environment variables

| Variable | Where | Default | In the preview | Use |
|---|---|---|---|---|
| `TRAWLKIT_CORS_ORIGINS` | API | `*` | `https://arielgiamportone.github.io` | Allowed origins, comma-separated (no path or trailing slash). |
| `TRAWLKIT_MAX_SIM_SECONDS` | API | `30` | `20` | Maximum estimated cost of `POST /simulate` [s]. |
| `TRAWLKIT_MAX_BATCH_SECONDS` | API | `120` | `90` | Maximum estimated cost of `POST /simulate/uncertainty` and `POST /simulate/calibrate` [s]. |
| `TRAWLKIT_MAX_OPT_GRID` | API | `25` | `15` | Maximum side of the `POST /optimize` grid (2–25). |
| `TRAWLKIT_ALLOW_REFINE` | API | allowed | allowed | `0`/`false` rejects `refine: true` in `POST /optimize`. |
| `DATABASE_URL` | API | no classroom | Neon Postgres (secret) | Database of the UTN Classroom (accounts, courses, assignments and submissions). Without it, `/classroom` responds 503 and everything else works the same. |
| `PORT` | API (Docker) | `8000` | set by Render | Listening port of uvicorn. |
| `VITE_API_URL` | app (build) | `http://127.0.0.1:8000` | repo variable `TRAWLKIT_API_URL` or `https://trawl-design-lab-api.onrender.com` | Base URL of the API. |
| `VITE_BASE` | app (build) | `/` | `/trawl-design-lab/app/` | Public path of the app. |
| `VITE_DOCS_URL` | app (build) | no link | `../` | “Documentation” link in the header (to the book). |

The API variables are changed on Render (*service → Environment*) or in `render.yaml`.

## UTN Classroom: database on Neon

The classroom (courses, students, assignments, submissions and grades) needs a database that
survives deployments; the disk of Render's free plan is wiped on each one. Postgres on
[Neon](https://neon.tech) is used, whose free plan does not expire (0.5 GB is enough for many
courses).

1. **Create the database.** On Neon, *New project* (region close to Render's, e.g. US West for
   `oregon`). In *Connection details*, copy the connection string
   (`postgresql://user:password@ep-….neon.tech/neondb?sslmode=require`). It is a secret: it is not
   pasted into the repository or into issues.
2. **Load it into Render.** *trawl-design-lab-api → Environment → Add environment variable*:
   `DATABASE_URL` with that string (`render.yaml` declares it with `sync: false`, so Render asks
   for it and does not version it). Saving redeploys the API; the tables are created by themselves
   on the first request to the classroom.
3. **Create the administrator**, only once, from a computer with the repository (Render's free
   plan has no console):

   ```bash
   uv sync --extra classroom
   export DATABASE_URL='postgresql://…neon.tech/neondb?sslmode=require'
   uv run trawlkit classroom migrate
   uv run trawlkit classroom create-admin --username ariel   # asks for the password
   ```
4. **Invite the teachers.** With the administrator account, in the app (“UTN Classroom” mode →
   *Teacher invitations*) or with `uv run trawlkit classroom invite --username ariel --count 3`.
   Each teacher signs up with their code and creates their courses; the students sign up with the
   course code.

`GET /classroom/status` says whether the classroom is enabled on the server. To test locally
without Neon: `DATABASE_URL=sqlite:///aula.db uv run trawlkit serve`.

Personal data: only the username, a display name (name or student number) and the hashed
password (scrypt); there is no e-mail. The teacher resets the passwords of their students and
each user can delete their account with their submissions.

## Testing the deployment locally

With Docker:

```bash
docker build -t trawlkit-api .
docker run --rm -p 8000:8000 -e TRAWLKIT_CORS_ORIGINS='*' trawlkit-api
curl http://127.0.0.1:8000/health
```

The app as it is published on Pages (under a sub-path):

```bash
cd web
VITE_BASE=/trawl-design-lab/app/ VITE_API_URL=http://127.0.0.1:8000 VITE_DOCS_URL=../ npm run build
mkdir -p /tmp/sitio/trawl-design-lab && cp -r dist /tmp/sitio/trawl-design-lab/app
python -m http.server 8080 --directory /tmp/sitio
# http://127.0.0.1:8080/trawl-design-lab/app/
```

Without Docker, the API is started with `uv run trawlkit serve` (see {doc}`web`).

## Common problems

- **“API unavailable” when opening the app.** The most common cause is that the API is asleep
  and took longer than expected: press “Retry”. If it persists, open the API URL + `/health` in
  the browser; if it does not respond, check the service *Logs* on Render (a failed build leaves
  the service undeployed).
- **CORS error in the console** (`No 'Access-Control-Allow-Origin' header`): the origin of the app
  is not in `TRAWLKIT_CORS_ORIGINS`. The origin is only scheme and domain
  (`https://arielgiamportone.github.io`), without `/trawl-design-lab`. If the app is published on
  another domain, add it, comma-separated. During a cold start Render may respond with an error
  without CORS headers; the browser reports it as a CORS error but it resolves itself once the
  start-up finishes.
- **The app points to another URL.** The API URL is fixed at build time: after changing the
  `TRAWLKIT_API_URL` variable the “Docs” workflow must be re-run.
- **“simulation too costly” or “optimisation grid too large”.** These are the cost guards of the
  free server: lower the resolution or the number of speeds, or the size of the grid.
- **“Error 404: Not Found” in a new feature, or “API out of date” in the header.** The GitHub
  Pages app is from a newer version than the Render API: the app calls a route that the API does
  not have yet. `GET /health` reports `contract` (fingerprint of the API routes) and `commit` (the
  deployed commit, `RENDER_GIT_COMMIT`); the app compares that fingerprint with that of its build
  and, if they differ, the header shows “API out of date” and the route 404s explain the cause.
  Render redeploys each commit to `main` with green CI by itself (a few minutes later). If that
  does not happen: Render → service `trawl-design-lab-api` → **Manual Deploy → Deploy latest
  commit**. The “Docs” workflow ends with the `api-check` job, which waits up to 20 minutes for
  the API to serve the same contract as the app and leaves a warning in the summary if it does not
  (`python tools/check_api_contract.py URL_API` checks it from a terminal). Previously, the
  Blueprint had a `buildFilter` by paths: if the last commit of a push did not touch `src/`, the
  API was not redeployed even if the earlier ones did change it. It was removed; if the service was
  created with the filter, Render removes it when syncing the Blueprint (or in *Settings → Build
  Filters*).
- **404 at `/trawl-design-lab/app/`.** Pages is not enabled with the *GitHub Actions* source or
  the “Docs” workflow has not yet run on `main`.
