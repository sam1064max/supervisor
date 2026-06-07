"""Failure test: invalid state passed to the graph does not crash."""

from __future__ import annotations

from supervisor.config import Settings
from supervisor.graph import build_graph
from supervisor.providers import FakeProvider


class TestInvalidState:
    def test_missing_query(self, test_settings: Settings) -> None:
        provider = FakeProvider()
        graph = build_graph(provider, test_settings)
        final = graph.invoke({})
        assert final.get("error") == "input_rejected"

    def test_query_as_int(self, test_settings: Settings) -> None:
        provider = FakeProvider()
        graph = build_graph(provider, test_settings)
        final = graph.invoke({"query": 12345})
        assert final.get("error") == "input_rejected"
