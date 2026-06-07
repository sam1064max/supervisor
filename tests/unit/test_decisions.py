"""Unit tests for the Pydantic models in decisions.py."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from supervisor.decisions import (
    ALL_AGENT_NAMES,
    AnalyticsResult,
    CalculationResult,
    DraftReport,
    GuardrailVerdict,
    ResearchResult,
    ReviewResult,
    SupervisorDecision,
)


class TestSupervisorDecision:
    def test_valid(self) -> None:
        d = SupervisorDecision(
            selected_agents=["research", "writer"],
            execution_order=["research", "writer"],
            reasoning="ok",
        )
        assert d.selected_agents == ["research", "writer"]
        assert d.requires_parallel_execution is False

    def test_empty(self) -> None:
        d = SupervisorDecision(
            selected_agents=[],
            execution_order=[],
            reasoning="nothing needed",
        )
        assert d.selected_agents == []

    def test_parallel_flag(self) -> None:
        d = SupervisorDecision(
            selected_agents=["a", "b"],
            execution_order=["a", "b"],
            reasoning="r",
            requires_parallel_execution=True,
        )
        assert d.requires_parallel_execution is True


class TestResearchResult:
    def test_valid(self) -> None:
        r = ResearchResult(topic="x", findings=["a", "b"], confidence=0.9)
        assert r.topic == "x"
        assert r.findings == ["a", "b"]
        assert r.sources == []

    def test_confidence_bounds(self) -> None:
        with pytest.raises(ValidationError):
            ResearchResult(topic="x", findings=[], confidence=1.5)
        with pytest.raises(ValidationError):
            ResearchResult(topic="x", findings=[], confidence=-0.1)


class TestAnalyticsResult:
    def test_valid(self) -> None:
        a = AnalyticsResult(metric="x", value=42.0, unit="USD")
        assert a.value == 42.0
        assert a.notes == ""


class TestCalculationResult:
    def test_valid(self) -> None:
        c = CalculationResult(expression="2+2", value=4.0)
        assert c.is_exact is True


class TestDraftReport:
    def test_valid(self) -> None:
        r = DraftReport(title="t", summary="s", body="b")
        assert r.citations == []


class TestReviewResult:
    def test_valid(self) -> None:
        r = ReviewResult(is_sufficient=True, feedback="ok", confidence=0.95)
        assert r.issues == []


class TestGuardrailVerdict:
    def test_allowed(self) -> None:
        v = GuardrailVerdict(allowed=True, reason="ok")
        assert v.allowed is True


class TestAgentNames:
    @pytest.mark.parametrize("name", ["research", "analytics", "calculator", "writer", "reviewer"])
    def test_all_agents_listed(self, name: str) -> None:
        assert name in ALL_AGENT_NAMES
