"""Regenera ``web/openapi.json`` desde la app FastAPI (luego ``npm run gen:api`` en ``web/``)."""

import json
from pathlib import Path

from trawlkit.api.app import app

OUT = Path(__file__).resolve().parents[1] / "web" / "openapi.json"


def render() -> str:
    return json.dumps(app.openapi(), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    OUT.write_text(render(), encoding="utf-8")
    print(f"escrito {OUT}")
