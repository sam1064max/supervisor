"""Integration tests for the Supervisor runner."""

from __future__ import annotations

import pytest

from supervisor.config import Settings
from supervisor.decisions import (
    DraftReport,
    SupervisorDecision,
)
from supervisor.providers import FakeProvider
from supervisor.runner import Supervisor, SupervisorResult, run_supervisor


class TestSupervisorRunner:
    def test_run_returns_result(self, test_settings: Settings) -> None:
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=["calculator", "writer"],
                    execution_order=["calculator", "writer"],
                    reasoning="math",
                ),
                DraftReport(title="T", summary="544", body="17 x 32 = 544"),
            ]
        )
        sup = Supervisor(settings=test_settings, provider=provider)
        result = sup.run("What is 17 x 32?")
        assert isinstance(result, SupervisorResult)
        assert "544" in result.final_answer
        assert result.trace_id
        assert result.request_id
        assert result.duration_ms > 0
        assert result.error is None

    def test_run_with_explicit_ids(self, test_settings: Settings) -> None:
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=["writer"],
                    execution_order=["writer"],
                    reasoning="r",
                ),
                DraftReport(title="T", summary="S", body="Hello"),
            ]
        )
        sup = Supervisor(settings=test_settings, provider=provider)
        result = sup.run("hello", request_id="r1", trace_id="t1")
        assert result.request_id == "r1"
        assert result.trace_id == "t1"

    def test_module_level_wrapper(
        self, test_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=["writer"],
                    execution_order=["writer"],
                    reasoning="r",
                ),
                DraftReport(title="T", summary="S", body="World"),
            ]
        )
        monkeypatch.setattr("supervisor.runner.build_provider", lambda s: provider)
        result = run_supervisor("hello world", settings=test_settings)
        assert "World" in result.final_answer

    def test_settings_property(self, test_settings: Settings) -> None:
        sup = Supervisor(settings=test_settings)
        assert sup.settings is test_settings

    def test_provider_property(self, test_settings: Settings) -> None:
        provider = FakeProvider()
        sup = Supervisor(settings=test_settings, provider=provider)
        assert sup.provider is provider

    def test_empty_query_returns_rejection(self, test_settings: Settings) -> None:
        sup = Supervisor(settings=test_settings)
        result = sup.run("")
        assert result.error == "input_rejected"
        assert "rejected" in result.final_answer.lower()


class TestRunnerObservation:
    def test_duration_is_recorded(self, test_settings: Settings) -> None:
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=["writer"],
                    execution_order=["writer"],
                    reasoning="r",
                ),
                DraftReport(title="T", summary="S", body="x"),
            ]
        )
        sup = Supervisor(settings=test_settings, provider=provider)
        result = sup.run("x")
        assert result.duration_ms >= 0
