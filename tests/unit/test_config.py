"""Unit tests for the configuration layer."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from supervisor.config import Settings, get_settings, reset_settings_cache


class TestSettings:
    def test_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for key in (
            "SUPERVISOR_ENV",
            "SUPERVISOR_LLM_PROVIDER",
            "SUPERVISOR_LOG_LEVEL",
            "SUPERVISOR_MAX_REVIEW_CYCLES",
            "SUPERVISOR_AGENT_MAX_RETRIES",
            "SUPERVISOR_HUMAN_REVIEW_ENABLED",
        ):
            monkeypatch.delenv(key, raising=False)
        reset_settings_cache()
        s = Settings()
        assert s.env == "development"
        assert s.llm_provider == "fake"
        assert s.log_level == "INFO"
        assert s.max_review_cycles == 3
        assert s.agent_max_retries == 2
        assert s.human_review_enabled is False

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SUPERVISOR_LLM_PROVIDER", "openai")
        monkeypatch.setenv("SUPERVISOR_LLM_API_KEY", "sk-test")
        monkeypatch.setenv("SUPERVISOR_HUMAN_REVIEW_ENABLED", "true")
        reset_settings_cache()
        s = Settings()
        assert s.llm_provider == "openai"
        assert s.llm_api_key == "sk-test"
        assert s.human_review_enabled is True

    def test_max_review_cycles_bounds(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SUPERVISOR_MAX_REVIEW_CYCLES", "20")
        reset_settings_cache()
        with pytest.raises(ValidationError):
            Settings()

    def test_max_review_cycles_lower_bound(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SUPERVISOR_MAX_REVIEW_CYCLES", "0")
        reset_settings_cache()
        with pytest.raises(ValidationError):
            Settings()

    def test_get_settings_is_cached(self) -> None:
        reset_settings_cache()
        a = get_settings()
        b = get_settings()
        assert a is b

    def test_reset_cache_creates_new(self) -> None:
        reset_settings_cache()
        a = get_settings()
        reset_settings_cache()
        b = get_settings()
        assert a is not b

    def test_log_format_default(self, test_settings: Settings) -> None:
        assert test_settings.log_format == "json"

    def test_max_parallel_agents_default(self, test_settings: Settings) -> None:
        assert test_settings.max_parallel_agents == 4
