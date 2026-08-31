"""Production container entrypoint: calculation API under /api plus the built SPA.

Run (container, PYTHONPATH=/srv/src:/srv/apps/api):
    python -m uvicorn serve:serve --host 0.0.0.0 --port 8080
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import app as api_app
from security import StaticSecurityMiddleware

ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = ROOT / "apps" / "observatory" / "dist"

serve = FastAPI(title="Fortune Observatory", docs_url=None, redoc_url=None, openapi_url=None)
serve.add_middleware(StaticSecurityMiddleware)
serve.mount("/api", api_app.app)
serve.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="spa")
