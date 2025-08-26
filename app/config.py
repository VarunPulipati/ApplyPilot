"""
Centralized config using pydantic-settings.

- Loads values from environment variables and a local .env file.
- Keeps sane defaults for quick local development.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Basic app info
    app_name: str = "ApplyPilot"
    app_env: str = "dev"  # dev | staging | prod
    log_level: str = "INFO"

    # Data & storage
    # SQLite for dev; swap to Postgres later: postgres://user:pass@host:5432/db
    database_url: str = "sqlite:///./local.db"
    doc_out_dir: str = "./storage/docs"
    file_store: str = "local"  # or "s3", "azure" in the future

    # Optional integrations (leave blank until you wire these)
    openai_api_key: str | None = None
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_token_path: str = "./secrets/google_token.json"

    class Config:
        env_file = ".env"  # allow overrides via a local .env


# Single importable instance everywhere:
settings = Settings()
