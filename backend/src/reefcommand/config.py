"""Runtime configuration.

Loaded from environment variables, see .env.example at the repository root.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
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

    llm_provider: Literal["anthropic", "deepseek"] = "anthropic"
    llm_model: str = "claude-sonnet-5"
    llm_timeout_seconds: float = Field(default=30.0, gt=0.0)
    llm_max_tokens: int = Field(default=4096, ge=256)
    llm_retry_backoff_seconds: float = Field(default=0.5, ge=0.0)
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com/beta"
    deepseek_trust_env: bool = Field(
        default=False,
        description=(
            "Whether the DeepSeek HTTP client should inherit HTTP(S)_PROXY settings. "
            "Disabled by default so a stale local proxy cannot block the API."
        ),
    )

    external_timeout_seconds: float = 3.0
    force_cache: bool = False
    offline_demo: bool = True


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor. Use this rather than constructing Settings directly."""
    return Settings()
