# app/config.py
from __future__ import annotations
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[1]  # .../ApplyPilot

class Settings(BaseSettings):
    # App
    app_name: str = Field(default="ApplyPilot", alias="APP_NAME")

    # Storage (relative paths are resolved from project root)
    doc_out_dir: str = Field(default="storage/docs", alias="DOC_OUT_DIR")
    template_dir: str = "templates"
    resumes_dir: str = Field(default="storage/resumes", alias="RESUMES_DIR")
    playwright_headless: bool = Field(default=False, alias="PLAYWRIGHT_HEADLESS")

    # DB
    database_url: str = Field(default="sqlite:///./local.db", alias="DATABASE_URL")

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
