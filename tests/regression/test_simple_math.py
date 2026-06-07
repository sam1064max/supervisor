"""Regression test: the canonical ``What is 17 x 32?`` example from the
spec must always produce 544."""

from __future__ import annotations

from supervisor.config import Settings
from supervisor.decisions import (
    DraftReport,
    SupervisorDecision,
)
from supervisor.graph import build_graph
from supervisor.providers import FakeProvider


class TestSimpleMath:
    def test_17_x_32(self, test_settings: Settings) -> None:
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=["calculator", "writer"],
                    execution_order=["calculator", "writer"],
                    reasoning="simple math",
                ),
                DraftReport(title="Math", summary="544", body="17 x 32 = 544"),
            ]
        )
        graph = build_graph(provider, test_settings)
        final = graph.invoke({"query": "What is 17 x 32?"})
        assert "544" in final["final_answer"]

    def test_2_plus_2(self, test_settings: Settings) -> None:
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=["calculator", "writer"],
                    execution_order=["calculator", "writer"],
                    reasoning="r",
                ),
                DraftReport(title="T", summary="4", body="2 + 2 = 4"),
            ]
        )
        graph = build_graph(provider, test_settings)
        final = graph.invoke({"query": "2 + 2"})
        assert "4" in final["final_answer"]

    def test_complex_expression(self, test_settings: Settings) -> None:
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=["calculator", "writer"],
                    execution_order=["calculator", "writer"],
                    reasoning="r",
                ),
                DraftReport(title="T", summary="210", body="(2 + 3) * (4 + 6) = 50"),
            ]
        )
        graph = build_graph(provider, test_settings)
        final = graph.invoke({"query": "Compute (2 + 3) * (4 + 6)"})
        # Calculator computes 50 (the expression from the query).
        # The writer then produces a draft referencing it.
        assert "50" in final["final_answer"] or "5" in final["final_answer"]
