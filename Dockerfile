# API trawlkit (FastAPI + WeasyPrint) para el despliegue de vista previa (Render, plan gratuito).
# Ver docs/despliegue.md. Construir y probar localmente:
#   docker build -t trawlkit-api .
#   docker run --rm -p 8000:8000 -e TRAWLKIT_CORS_ORIGINS='*' trawlkit-api
FROM ghcr.io/astral-sh/uv:0.11.32 AS uv

FROM python:3.12-slim

# Pango (y una fuente) para los informes PDF de WeasyPrint.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=/usr/local/bin/python3.12 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# 1) Dependencias (capa cacheada mientras no cambien pyproject.toml/uv.lock).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project \
        --extra api --extra report --extra optimize --extra classroom

# 2) El paquete (código + datos de src/trawlkit/data), instalado como rueda, no editable.
COPY README.md LICENSE ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable \
        --extra api --extra report --extra optimize --extra classroom \
    && rm -rf /root/.cache

RUN useradd --create-home --uid 10001 app
USER app

# Render inyecta PORT; 8000 si se corre a mano.
ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8000\")}/health', timeout=4)"

CMD ["sh", "-c", "exec uvicorn trawlkit.api.app:app --host 0.0.0.0 --port \"${PORT:-8000}\" --proxy-headers --forwarded-allow-ips='*'"]
