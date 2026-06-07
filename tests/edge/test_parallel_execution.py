"""Edge case: parallel execution via LangGraph's ``Send`` works correctly."""

from __future__ import annotations

from supervisor.config import Settings
from supervisor.decisions import (
    AnalyticsResult,
    DraftReport,
    ResearchResult,
    ReviewResult,
    SupervisorDecision,
)
from supervisor.graph import build_graph
from supervisor.providers import FakeProvider


class TestParallelExecution:
    def test_three_agents_run_in_parallel(self, test_settings: Settings) -> None:
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=[
                        "research",
                        "analytics",
                        "calculator",
                        "writer",
                        "reviewer",
                    ],
                    execution_order=[
                        "research",
                        "analytics",
                        "calculator",
                        "writer",
                        "reviewer",
                    ],
                    reasoning="comprehensive",
                    requires_parallel_execution=True,
                ),
                ResearchResult(topic="X", findings=["a"]),
                AnalyticsResult(metric="y", value=1.0),
                # Calculator does not call LLM
                DraftReport(
                    title="T",
                    summary="S",
                    body="parallel body",
                ),
                ReviewResult(is_sufficient=True, feedback="ok", confidence=0.9),
            ]
        )
        graph = build_graph(provider, test_settings)
        # Query includes arithmetic so the calculator can succeed.
        final = graph.invoke({"query": "comprehensive report on revenue, compute 100 + 200"})
        assert "parallel body" in final["final_answer"]
        completed = final.get("completed_agents", [])
        assert "research" in completed
        assert "analytics" in completed
        assert "calculator" in completed

    def test_two_agents_run_in_parallel(self, test_settings: Settings) -> None:
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=["research", "analytics", "writer"],
                    execution_order=["research", "analytics", "writer"],
                    reasoning="r",
                    requires_parallel_execution=True,
                ),
                ResearchResult(topic="X", findings=["a"]),
                AnalyticsResult(metric="y", value=1.0),
                DraftReport(title="T", summary="S", body="two parallel body"),
                # Reviewer is added by the wrapper because the decision
                # includes research; make it approve immediately.
                ReviewResult(is_sufficient=True, feedback="ok", confidence=0.9),
            ]
        )
        graph = build_graph(provider, test_settings)
        final = graph.invoke({"query": "do research and analytics"})
        assert "two parallel body" in final["final_answer"]
        assert "research" in final.get("completed_agents", [])
        assert "analytics" in final.get("completed_agents", [])

    def test_sequential_uses_first_hop(self, test_settings: Settings) -> None:
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=["research", "writer"],
                    execution_order=["research", "writer"],
                    reasoning="r",
                    requires_parallel_execution=False,
                ),
                ResearchResult(topic="X", findings=["a"]),
                DraftReport(title="T", summary="S", body="sequential body"),
                # Reviewer is added by the wrapper because the decision
                # includes research; make it approve immediately.
                ReviewResult(is_sufficient=True, feedback="ok", confidence=0.9),
            ]
        )
        graph = build_graph(provider, test_settings)
        final = graph.invoke({"query": "research then write"})
        assert "sequential body" in final["final_answer"]
        assert "research" in final.get("completed_agents", [])
