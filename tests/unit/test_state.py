"""Unit tests for the AgentState TypedDict."""

from __future__ import annotations

from supervisor.state import AgentState


class TestAgentState:
    def test_minimal_construction(self) -> None:
        state: AgentState = {
            "query": "x",
            "request_id": "r",
            "trace_id": "t",
            "selected_agents": [],
            "execution_order": [],
            "completed_agents": [],
            "research_results": [],
            "analytics_results": [],
            "calculation_results": [],
            "review_cycle": 0,
            "metadata": {},
        }
        assert state["query"] == "x"
        assert state["review_cycle"] == 0
