"""Regression test: comprehensive NVIDIA-style report with parallel agents."""

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


class TestComplexReport:
    def test_nvidia_earnings(self, test_settings: Settings) -> None:
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=[
                        "research",
                        "analytics",
                        "writer",
                        "reviewer",
                    ],
                    execution_order=[
                        "research",
                        "analytics",
                        "writer",
                        "reviewer",
                    ],
                    reasoning="comprehensive",
                    requires_parallel_execution=True,
                ),
                ResearchResult(topic="NVIDIA", findings=["revenue up 20%", "EPS beat"]),
                AnalyticsResult(metric="YoY growth", value=20.0, unit="%"),
                DraftReport(
                    title="NVIDIA Earnings",
                    summary="Growth 20%",
                    body="NVIDIA beat expectations with 20% YoY growth.",
                ),
                ReviewResult(is_sufficient=True, feedback="ok", confidence=0.9),
            ]
        )
        graph = build_graph(provider, test_settings)
        final = graph.invoke({"query": "Analyze NVIDIA earnings and generate a report."})
        assert "NVIDIA" in final["final_answer"]
        assert "20%" in final["final_answer"] or "20" in final["final_answer"]
        completed = final.get("completed_agents", [])
        assert "research" in completed
        assert "analytics" in completed
        assert "writer" in completed
        assert "reviewer" in completed
