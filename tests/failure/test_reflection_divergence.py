"""Failure test: the reflection loop is bounded. The system never loops
forever even if the reviewer never approves."""

from __future__ import annotations

from supervisor.config import Settings
from supervisor.decisions import (
    DraftReport,
    ReviewResult,
    SupervisorDecision,
)
from supervisor.graph import build_graph
from supervisor.providers import FakeProvider


class TestReflectionDivergence:
    def test_forces_complete_after_max_cycles(self, test_settings: Settings) -> None:
        test_settings.max_review_cycles = 2
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=["writer", "reviewer"],
                    execution_order=["writer", "reviewer"],
                    reasoning="needs review",
                ),
                DraftReport(title="T", summary="S", body="B1"),
                ReviewResult(is_sufficient=False, feedback="rev1", confidence=0.2),
                DraftReport(title="T", summary="S", body="B2"),
                ReviewResult(is_sufficient=False, feedback="rev2", confidence=0.2),
                # cycle=2 >= max=2 -> go to output_guardrail
            ]
        )
        graph = build_graph(provider, test_settings)
        final = graph.invoke({"query": "x"})
        # The final body should be B2 (the last writer output)
        assert final["final_answer"] == "B2"
        # The cycle count should be at least 2
        assert final.get("review_cycle", 0) >= 2

    def test_single_cycle_with_approval(self, test_settings: Settings) -> None:
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=["writer", "reviewer"],
                    execution_order=["writer", "reviewer"],
                    reasoning="r",
                ),
                DraftReport(title="T", summary="S", body="B"),
                ReviewResult(is_sufficient=True, feedback="ok", confidence=0.9),
            ]
        )
        graph = build_graph(provider, test_settings)
        final = graph.invoke({"query": "x"})
        assert final["final_answer"] == "B"
        assert final.get("review_cycle") == 1
        assert final.get("review_status") == "sufficient"
