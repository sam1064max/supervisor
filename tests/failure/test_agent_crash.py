"""Failure test: an agent raising is caught by the retry wrapper and the
graph continues. The system never crashes."""

from __future__ import annotations

from supervisor.config import Settings
from supervisor.decisions import (
    DraftReport,
    SupervisorDecision,
)
from supervisor.graph import build_graph
from supervisor.providers import FakeProvider


class TestCalculatorCrash:
    def test_calculator_failure_recorded(self, test_settings: Settings) -> None:
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=["calculator", "writer"],
                    execution_order=["calculator", "writer"],
                    reasoning="r",
                ),
                DraftReport(title="T", summary="S", body="Fallback body"),
            ]
        )
        graph = build_graph(provider, test_settings)
        final = graph.invoke({"query": "this query has no arithmetic"})
        # Calculator failed, but the graph continued
        assert final["final_answer"]
        assert final.get("error") == "calculator_failed"


class TestProviderCrashesInWriter:
    def test_writer_retries_then_escalates(self, test_settings: Settings) -> None:
        # Queue only the supervisor response. Writer will fail (no queued response).
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=["writer"],
                    execution_order=["writer"],
                    reasoning="r",
                )
                # no more responses: writer will raise after retries
            ]
        )
        graph = build_graph(provider, test_settings)
        final = graph.invoke({"query": "x"})
        # System should not crash; final state has error
        assert "error" in final


class TestProviderCrashesInReviewer:
    def test_reviewer_failure_does_not_crash(self, test_settings: Settings) -> None:
        test_settings.max_review_cycles = 2
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=["writer", "reviewer"],
                    execution_order=["writer", "reviewer"],
                    reasoning="r",
                ),
                DraftReport(title="T", summary="S", body="B"),
                # No more responses: reviewer fails
            ]
        )
        graph = build_graph(provider, test_settings)
        final = graph.invoke({"query": "x"})
        # The retry wrapper should catch the error
        assert "error" in final
