"""Shared test fixtures.

Every test gets a hermetic :class:`Settings` instance with the offline
``fake`` provider, the ``testing`` environment, and a cleared settings
cache. No test depends on the network.
"""

from __future__ import annotations

import pytest

from supervisor.config import Settings, reset_settings_cache
from supervisor.providers import FakeProvider


@pytest.fixture(autouse=True)
def _isolate_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    """Quiet the logs to WARNING so test output stays readable."""
    monkeypatch.setenv("SUPERVISOR_LOG_LEVEL", "WARNING")
    monkeypatch.setenv("SUPERVISOR_LOG_FORMAT", "json")
    reset_settings_cache()


@pytest.fixture
def test_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Return a hermetic Settings instance for the test."""
    monkeypatch.setenv("SUPERVISOR_ENV", "testing")
    monkeypatch.setenv("SUPERVISOR_LLM_PROVIDER", "fake")
    monkeypatch.setenv("SUPERVISOR_LOG_LEVEL", "WARNING")
    monkeypatch.setenv("SUPERVISOR_LOG_FORMAT", "json")
    monkeypatch.setenv("SUPERVISOR_HUMAN_REVIEW_ENABLED", "false")
    monkeypatch.setenv("SUPERVISOR_MAX_REVIEW_CYCLES", "3")
    monkeypatch.setenv("SUPERVISOR_AGENT_MAX_RETRIES", "2")
    reset_settings_cache()
    return Settings()


@pytest.fixture
def fake_provider(test_settings: Settings) -> FakeProvider:
    """Return an empty FakeProvider."""
    return FakeProvider()
