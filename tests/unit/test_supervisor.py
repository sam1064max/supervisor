"""Unit tests for the Supervisor planner."""

from __future__ import annotations

import pytest

from supervisor.config import Settings
from supervisor.decisions import SupervisorDecision
from supervisor.providers import FakeProvider, LLMError
from supervisor.supervisor import (
    _heuristic_plan,
    extract_expression,
    make_supervisor_node,
    plan_decision,
)


class TestPlanDecision:
    def test_uses_provider(self, test_settings: Settings) -> None:
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=["calculator", "writer"],
                    execution_order=["calculator", "writer"],
                    reasoning="math detected",
                )
            ]
        )
        decision = plan_decision("What is 17 x 32?", provider, test_settings)
        assert "calculator" in decision.selected_agents

    def test_provider_failure_falls_back(self, test_settings: Settings) -> None:
        class BrokenProvider:
            def complete(self, *args, **kwargs):
                raise LLMError("nope")

        decision = plan_decision("What is 17 x 32?", BrokenProvider(), test_settings)
        assert "calculator" in decision.selected_agents

    def test_provider_value_error_falls_back(self, test_settings: Settings) -> None:
        class ValueErrorProvider:
            def complete(self, *args, **kwargs):
                raise ValueError("nope")

        decision = plan_decision("What is 17 x 32?", ValueErrorProvider(), test_settings)
        assert "calculator" in decision.selected_agents

    def test_invalid_agent_rejected(self, test_settings: Settings) -> None:
        provider = FakeProvider(
            responses=[
                {
                    "selected_agents": ["bogus"],
                    "execution_order": ["bogus"],
                    "reasoning": "r",
                }
            ]
        )
        with pytest.raises(ValueError, match="unknown agent"):
            plan_decision("x", provider, test_settings)

    def test_response_is_typed(self, test_settings: Settings) -> None:
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=["writer"],
                    execution_order=["writer"],
                    reasoning="r",
                )
            ]
        )
        decision = plan_decision("hello", provider, test_settings)
        assert isinstance(decision, SupervisorDecision)


class TestSupervisorNode:
    def test_forces_writer(self, test_settings: Settings) -> None:
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=["calculator"],
                    execution_order=["calculator"],
                    reasoning="r",
                )
            ]
        )
        node = make_supervisor_node(provider, test_settings)
        delta = node({"query": "What is 1+1?"})
        assert "writer" in delta["selected_agents"]
        assert "writer" in delta["execution_order"]

    def test_adds_reviewer_for_substantial(self, test_settings: Settings) -> None:
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=["research", "writer"],
                    execution_order=["research", "writer"],
                    reasoning="r",
                )
            ]
        )
        node = make_supervisor_node(provider, test_settings)
        long_query = (
            "Please write a comprehensive analysis of the latest trends in "
            "the semiconductor industry and the impact on global supply chains"
        )
        delta = node({"query": long_query})
        assert "reviewer" in delta["selected_agents"]

    def test_skips_reviewer_for_short(self, test_settings: Settings) -> None:
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=["calculator", "writer"],
                    execution_order=["calculator", "writer"],
                    reasoning="r",
                )
            ]
        )
        node = make_supervisor_node(provider, test_settings)
        delta = node({"query": "What is 2+2?"})
        assert "reviewer" not in delta["selected_agents"]


class TestHeuristicPlan:
    def test_simple_math(self) -> None:
        d = _heuristic_plan("What is 17 x 32?")
        assert "calculator" in d.selected_agents
        assert d.requires_parallel_execution is False

    def test_complex(self) -> None:
        d = _heuristic_plan(
            "Please write a comprehensive analysis of the latest trends in the market"
        )
        assert "research" in d.selected_agents
        assert d.requires_parallel_execution is True

    def test_default(self) -> None:
        d = _heuristic_plan("hello there friend")
        assert d.selected_agents == ["writer"]

    def test_earnings_keyword(self) -> None:
        d = _heuristic_plan("give me the Q3 earnings report")
        assert "research" in d.selected_agents


class TestExtractExpression:
    def test_basic(self) -> None:
        # "x" is normalised to "*" so the result is valid Python
        assert extract_expression("What is 17 x 32?") == "17 * 32"

    def test_unicode_multiplication(self) -> None:
        assert extract_expression("What is 17 × 32?") == "17 * 32"

    def test_with_parens(self) -> None:
        assert extract_expression("Compute (2+3) * 4") is not None

    def test_no_math(self) -> None:
        assert extract_expression("hello world") is None

    def test_operators_only_no_digits(self) -> None:
        assert extract_expression("+ +") is None
