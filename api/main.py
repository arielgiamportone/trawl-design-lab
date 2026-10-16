"""API HTTP de trawlkit (FastAPI). Se completa en la Fase 4."""

from __future__ import annotations

from fastapi import FastAPI

from trawlkit import __version__

app = FastAPI(title="trawlkit API", version=__version__)


@app.get("/health")
def health() -> dict[str, str]:
    """Comprobación de vida."""
    return {"status": "ok", "version": __version__}
