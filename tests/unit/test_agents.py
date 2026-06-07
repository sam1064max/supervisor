"""Unit tests for the specialist agents."""

from __future__ import annotations

import pytest

from supervisor.agents import (
    make_analytics_agent,
    make_calculator_agent,
    make_research_agent,
    make_reviewer_agent,
    make_writer_agent,
)
from supervisor.decisions import (
    AnalyticsResult,
    DraftReport,
    ResearchResult,
    ReviewResult,
)
from supervisor.providers import FakeProvider


class TestResearchAgent:
    def test_produces_result(self, fake_provider: FakeProvider) -> None:
        fake_provider.queue(ResearchResult(topic="NVIDIA", findings=["revenue up"], confidence=0.8))
        agent = make_research_agent(fake_provider)
        delta = agent({"query": "NVIDIA earnings"})
        assert len(delta["research_results"]) == 1
        assert delta["completed_agents"] == ["research"]

    def test_wrong_type_raises(self, fake_provider: FakeProvider) -> None:
        # Queue a different Pydantic model than the agent expects.
        fake_provider.queue(AnalyticsResult(metric="x", value=1.0))
        agent = make_research_agent(fake_provider)
        with pytest.raises(TypeError):
            agent({"query": "x"})


class TestAnalyticsAgent:
    def test_produces_result(self, fake_provider: FakeProvider) -> None:
        fake_provider.queue(AnalyticsResult(metric="revenue", value=100.0, unit="B"))
        agent = make_analytics_agent(fake_provider)
        delta = agent({"query": "x", "research_results": []})
        assert delta["analytics_results"][0].value == 100.0
        assert delta["completed_agents"] == ["analytics"]


class TestCalculatorAgent:
    def test_evaluates(self, fake_provider: FakeProvider) -> None:
        agent = make_calculator_agent(fake_provider)
        delta = agent({"query": "What is 17 x 32?"})
        assert delta["calculation_results"][0].value == 544.0
        assert delta["completed_agents"] == ["calculator"]

    def test_no_expression_raises(self, fake_provider: FakeProvider) -> None:
        agent = make_calculator_agent(fake_provider)
        with pytest.raises(ValueError, match="no arithmetic expression"):
            agent({"query": "hello world"})


class TestWriterAgent:
    def test_produces_report_and_final_answer(self, fake_provider: FakeProvider) -> None:
        fake_provider.queue(DraftReport(title="T", summary="S", body="B"))
        agent = make_writer_agent(fake_provider)
        delta = agent({"query": "x"})
        assert delta["report"] == "B"
        assert delta["final_answer"] == "B"

    def test_includes_feedback(self, fake_provider: FakeProvider) -> None:
        fake_provider.queue(DraftReport(title="T2", summary="S2", body="B2"))
        agent = make_writer_agent(fake_provider)
        delta = agent({"query": "x", "review_feedback": "add more detail"})
        assert delta["report"] == "B2"


class TestReviewerAgent:
    def test_sufficient(self, fake_provider: FakeProvider) -> None:
        fake_provider.queue(ReviewResult(is_sufficient=True, feedback="ok", confidence=0.9))
        agent = make_reviewer_agent(fake_provider)
        delta = agent({"report": "B", "review_feedback": "", "review_cycle": 0})
        assert delta["review_status"] == "sufficient"
        assert delta["review_cycle"] == 1
        assert delta["review_feedback"] == "ok"

    def test_insufficient(self, fake_provider: FakeProvider) -> None:
        fake_provider.queue(ReviewResult(is_sufficient=False, feedback="add x", confidence=0.4))
        agent = make_reviewer_agent(fake_provider)
        delta = agent({"report": "B", "review_feedback": "", "review_cycle": 0})
        assert delta["review_status"] == "pending"
        assert "add x" in delta["review_feedback"]
