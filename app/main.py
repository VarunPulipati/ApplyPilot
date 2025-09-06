# app/main.py
from __future__ import annotations
import sys, asyncio

# Windows: Playwright needs the *Selector* loop for subprocesses
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

from pathlib import Path
from fastapi import FastAPI
from .config import settings

app = FastAPI(title=settings.app_name)

# Ensure folders exist
Path(settings.doc_out_dir).mkdir(parents=True, exist_ok=True)
Path(settings.resumes_dir).mkdir(parents=True, exist_ok=True)

# --- imports AFTER policy is set ---
from .routes import profiles as profiles_routes
from .routes import packages as packages_routes
from .routes import jobs as jobs_routes
from .routes import autopilot as autopilot_routes
from .routes import apply as apply_routes
from .routes import sources as sources_routes

app.include_router(profiles_routes.router)
app.include_router(packages_routes.router)
app.include_router(jobs_routes.router)
app.include_router(autopilot_routes.router)
app.include_router(apply_routes.router)
app.include_router(sources_routes.router)

@app.get("/health")
def health():
    return {"ok": True, "app": settings.app_name}
