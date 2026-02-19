"""Application settings — loads from .env + YAML config files."""

from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

_CONFIG_DIR = Path(__file__).parent
_PROJECT_ROOT = Path(__file__).resolve().parents[4]  # src/istari/config/ -> project root


def _load_yaml(filename: str) -> dict:
    path = _CONFIG_DIR / filename
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    # Database
    database_url: str = "postgresql+asyncpg://istari:changeme@localhost:5432/istari"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # LLM keys
    anthropic_api_key: str = ""
    google_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    # Gmail OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    gmail_token_path: str = "gmail_token.json"
    gmail_max_results: int = 20

    # Worker
    quiet_hours_start: int = 21
    quiet_hours_end: int = 7
    stale_todo_days: int = 3

    # Logging
    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def llm_routing(self) -> dict:
        return _load_yaml("llm_routing.yml")

    @property
    def schedules(self) -> dict:
        return _load_yaml("schedules.yml")


settings = Settings()
