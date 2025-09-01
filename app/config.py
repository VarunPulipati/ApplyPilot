# app/config.py
from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # App basics
    app_name: str = "ApplyPilot"
    database_url: str = "sqlite:///./local.db"
    doc_out_dir: str = "storage/docs"

    # AI key: read from env variable GEMINI_API_KEY
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")

    # Load from .env and ignore any extra keys so migrations don't fail
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",   # <-- important: prevents "extra inputs" ValidationError
    )

# Singleton
settings = Settings()
