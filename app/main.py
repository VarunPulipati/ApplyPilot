# app/main.py
"""
FastAPI entrypoint: wires settings, routers, and prepares output folders.
"""
from pathlib import Path
from fastapi import FastAPI
from .config import settings

# Import routers
from .routes import profiles as profiles_routes
from .routes import packages as packages_routes
from .routes import jobs as jobs_routes
from .routes import sources as sources_routes
from .routes import apply as apply_routes
from dotenv import load_dotenv
load_dotenv() 
# Create app first
app = FastAPI(title=settings.app_name)

# Ensure the output directory exists (so PDF writes don't fail)
Path(settings.doc_out_dir).mkdir(parents=True, exist_ok=True)

# Register endpoints
app.include_router(profiles_routes.router)
app.include_router(packages_routes.router)
app.include_router(jobs_routes.router)
app.include_router(sources_routes.router)
app.include_router(apply_routes.router)

@app.get("/health")
def health():
    return {"ok": True, "app": settings.app_name}
