"""Specialist agents. Each is a LangGraph node: ``(state) -> dict``.

The Calculator agent is the only specialist that does not call the LLM by
default - arithmetic is deterministic and the LLM adds latency and error
surface. The other agents are wrapped in :func:`make_*_agent` factories so
the LLM provider can be injected at graph-build time.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from supervisor.decisions import (
    AnalyticsResult,
    CalculationResult,
    DraftReport,
    ResearchResult,
    ReviewResult,
)
from supervisor.logging_setup import get_logger
from supervisor.providers import LLMProvider
from supervisor.supervisor import extract_expression
from supervisor.tools import safe_eval

logger = get_logger(__name__)

AgentFn = Callable[[dict[str, Any]], dict[str, Any]]


def make_research_agent(provider: LLMProvider) -> AgentFn:
    """Return a research node bound to the given provider."""

    def agent(state: dict[str, Any]) -> dict[str, Any]:
        query = state.get("query", "")
        messages = [
            {"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]
        result = provider.complete(messages, response_model=ResearchResult)
        if not isinstance(result, ResearchResult):
            raise TypeError(f"research agent expected ResearchResult, got {type(result).__name__}")
        logger.info(
            "agent.research.completed",
            findings=len(result.findings),
            confidence=result.confidence,
        )
        return {
            "research_results": [result],
            "completed_agents": ["research"],
        }

    return agent


def make_analytics_agent(provider: LLMProvider) -> AgentFn:
    """Return an analytics node bound to the given provider."""

    def agent(state: dict[str, Any]) -> dict[str, Any]:
        research = state.get("research_results", [])
        query = state.get("query", "")
        context = "\n".join(f"- {f}" for r in research for f in r.findings)
        messages = [
            {"role": "system", "content": ANALYTICS_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Query: {query}\nContext: {context or '(none)'}",
            },
        ]
        result = provider.complete(messages, response_model=AnalyticsResult)
        if not isinstance(result, AnalyticsResult):
            raise TypeError(
                f"analytics agent expected AnalyticsResult, got {type(result).__name__}"
            )
        logger.info(
            "agent.analytics.completed",
            metric=result.metric,
            value=result.value,
        )
        return {
            "analytics_results": [result],
            "completed_agents": ["analytics"],
        }

    return agent


def make_calculator_agent(provider: LLMProvider) -> AgentFn:
    """Return a calculator node. The provider is unused but accepted for
    uniformity with the other factories.
    """

    def agent(state: dict[str, Any]) -> dict[str, Any]:
        _ = provider  # arithmetic is deterministic; provider not used
        query = state.get("query", "")
        expression = extract_expression(query)
        if expression is None:
            raise ValueError("calculator: no arithmetic expression found in query")
        value = safe_eval(expression)
        result = CalculationResult(expression=expression, value=float(value))
        logger.info("agent.calculator.completed", expression=expression, value=value)
        return {
            "calculation_results": [result],
            "completed_agents": ["calculator"],
        }

    return agent


def make_writer_agent(provider: LLMProvider) -> AgentFn:
    """Return a writer node bound to the given provider."""

    def agent(state: dict[str, Any]) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": WRITER_SYSTEM_PROMPT},
            {"role": "user", "content": _format_writer_input(state)},
        ]
        result = provider.complete(messages, response_model=DraftReport)
        if not isinstance(result, DraftReport):
            raise TypeError(f"writer agent expected DraftReport, got {type(result).__name__}")
        logger.info(
            "agent.writer.completed",
            title=result.title,
            body_length=len(result.body),
            cycle=state.get("review_cycle", 0),
        )
        return {
            "report": result.body,
            "final_answer": result.body,
            "completed_agents": ["writer"],
            "metadata": {"last_draft_title": result.title},
        }

    return agent


def make_reviewer_agent(provider: LLMProvider) -> AgentFn:
    """Return a reviewer node bound to the given provider."""

    def agent(state: dict[str, Any]) -> dict[str, Any]:
        report = state.get("report", "")
        feedback = state.get("review_feedback", "")
        cycle = int(state.get("review_cycle", 0) or 0)
        messages = [
            {"role": "system", "content": REVIEWER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Review cycle: {cycle}\n"
                    f"Report to review:\n{report}\n"
                    f"Previous feedback: {feedback or '(none)'}"
                ),
            },
        ]
        result = provider.complete(messages, response_model=ReviewResult)
        if not isinstance(result, ReviewResult):
            raise TypeError(f"reviewer agent expected ReviewResult, got {type(result).__name__}")
        new_cycle = cycle + 1
        status: str = "sufficient" if result.is_sufficient else "pending"
        logger.info(
            "agent.reviewer.completed",
            is_sufficient=result.is_sufficient,
            confidence=result.confidence,
            cycle=new_cycle,
        )
        return {
            "review_feedback": result.feedback,
            "review_result": result,
            "review_cycle": new_cycle,
            "review_status": status,
            "completed_agents": ["reviewer"],
        }

    return agent


# ----------------------------------------------------------------------
# Prompts
# ----------------------------------------------------------------------

RESEARCH_SYSTEM_PROMPT = (
    "You are a research specialist. Gather facts, sources, and findings. "
    "Return a ResearchResult JSON object with topic, findings (list of strings), "
    "sources (list of strings), and confidence (0..1)."
)

ANALYTICS_SYSTEM_PROMPT = (
    "You are an analytics specialist. Compute a single key metric from the "
    "provided context. Return an AnalyticsResult JSON object with metric, value, "
    "unit, and notes."
)

WRITER_SYSTEM_PROMPT = (
    "You are a writer specialist. Produce a clear, well-structured report. "
    "Return a DraftReport JSON object with title, summary, body, and citations."
)

REVIEWER_SYSTEM_PROMPT = (
    "You are a reviewer specialist. Evaluate the report for completeness, "
    "consistency, and confidence. If the report is sufficient, set "
    "is_sufficient=true. Otherwise, set is_sufficient=false and provide "
    "actionable feedback. Return a ReviewResult JSON object."
)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _format_writer_input(state: dict[str, Any]) -> str:
    parts: list[str] = [f"Original query: {state.get('query', '')}"]
    research = state.get("research_results") or []
    if research:
        parts.append("Research findings:")
        for r in research:
            topic = getattr(r, "topic", "<unknown>")
            findings = getattr(r, "findings", [])
            parts.append(f"  Topic: {topic}")
            for f in findings:
                parts.append(f"    - {f}")
    analytics = state.get("analytics_results") or []
    if analytics:
        parts.append("Analytics results:")
        for a in analytics:
            parts.append(
                f"  - {getattr(a, 'metric', '?')}: "
                f"{getattr(a, 'value', '?')} {getattr(a, 'unit', '')}".rstrip()
            )
    calcs = state.get("calculation_results") or []
    if calcs:
        parts.append("Calculation results:")
        for c in calcs:
            parts.append(f"  - {getattr(c, 'expression', '?')} = {getattr(c, 'value', '?')}")
    if state.get("review_feedback"):
        parts.append(f"Reviewer feedback to address: {state['review_feedback']}")
    return "\n".join(parts)
