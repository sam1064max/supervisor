"""Externalized configuration via Pydantic Settings.

All runtime configuration is read from environment variables prefixed with
``SUPERVISOR_`` and optionally from a ``.env`` file. No values are hardcoded
in the application code; see ``.env.example`` for the full schema.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
ProviderName = Literal["fake", "openai", "anthropic"]
EnvironmentName = Literal["development", "testing", "production"]
LogFormat = Literal["json", "console"]


class Settings(BaseSettings):
    """Process-wide settings. Construct via :func:`get_settings`."""

    model_config = SettingsConfigDict(
        env_prefix="SUPERVISOR_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    env: EnvironmentName = "development"
    log_level: LogLevel = "INFO"
    log_format: LogFormat = "json"

    llm_provider: ProviderName = "fake"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_timeout_s: int = Field(default=30, ge=1, le=600)
    llm_max_retries: int = Field(default=2, ge=0, le=10)

    max_review_cycles: int = Field(default=3, ge=1, le=10)
    agent_max_retries: int = Field(default=2, ge=0, le=5)
    human_review_enabled: bool = False
    max_parallel_agents: int = Field(default=4, ge=1, le=16)

    trace_enabled: bool = True
    otlp_endpoint: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached process-wide settings instance."""
    return Settings()


def reset_settings_cache() -> None:
    """Clear the settings cache. Useful in tests."""
    get_settings.cache_clear()
