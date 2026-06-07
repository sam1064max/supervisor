"""Edge case: the human-in-the-loop checkpoint is engaged when configured."""

from __future__ import annotations

from supervisor.config import Settings
from supervisor.decisions import (
    DraftReport,
    SupervisorDecision,
)
from supervisor.graph import build_graph
from supervisor.providers import FakeProvider


class TestHumanReview:
    def test_hitl_disabled_by_default(self, test_settings: Settings) -> None:
        assert test_settings.human_review_enabled is False
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=["writer"],
                    execution_order=["writer"],
                    reasoning="r",
                ),
                DraftReport(title="T", summary="S", body="Final"),
            ]
        )
        graph = build_graph(provider, test_settings)
        final = graph.invoke({"query": "x"})
        # No awaiting_human flag
        assert not final.get("metadata", {}).get("awaiting_human")

    def test_hitl_enabled_marks_awaiting(self, test_settings: Settings) -> None:
        test_settings.human_review_enabled = True
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=["writer"],
                    execution_order=["writer"],
                    reasoning="r",
                ),
                DraftReport(title="T", summary="S", body="Final"),
            ]
        )
        graph = build_graph(provider, test_settings)
        final = graph.invoke({"query": "x"})
        assert final.get("metadata", {}).get("awaiting_human") is True
        # The answer is still set
        assert final["final_answer"] == "Final"
