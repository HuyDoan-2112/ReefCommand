"""Runtime configuration.

Loaded from environment variables, see .env.example at the repository root.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

DATA_DIR = Path(__file__).parent / "data"
CACHE_DIR = DATA_DIR / "cache"


class Settings(BaseSettings):
    """Application settings.

    `force_cache` exists because live external APIs are a demo liability.
    With it set, no live external call is attempted at all.
    """

    model_config = SettingsConfigDict(env_prefix="REEFCOMMAND_", env_file=".env", extra="ignore")

    env: str = "development"
    log_level: str = "INFO"
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    llm_model: str = "claude-sonnet-4-5"
    llm_timeout_seconds: float = 30.0

    external_timeout_seconds: float = 3.0
    force_cache: bool = False
    offline_demo: bool = True


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor. Use this rather than constructing Settings directly."""
    return Settings()
