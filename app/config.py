# app/config.py
from __future__ import annotations
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[1]  # .../ApplyPilot

class Settings(BaseSettings):
    # App
    app_name: str = "ApplyPilot"

    # Storage (relative paths are resolved from project root)
    doc_out_dir: str = "storage/docs"
    template_dir: str = "templates"

    # DB
    database_url: str = "sqlite:///./local.db"

    # .env loader
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Helpers to get absolute Paths
    @property
    def doc_out_path(self) -> Path:
        p = Path(self.doc_out_dir)
        return p if p.is_absolute() else (_PROJECT_ROOT / p)

    @property
    def template_path(self) -> Path:
        p = Path(self.template_dir)
        return p if p.is_absolute() else (_PROJECT_ROOT / p)

settings = Settings()
