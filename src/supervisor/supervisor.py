"""The Supervisor node. LLM-based dynamic planning with structured output.

The Supervisor never performs business logic. It produces a
:class:`SupervisorDecision` that tells the graph which agents to run, in
what order, and whether parallel execution is safe.
"""

from __future__ import annotations

import re
from typing import Any

from supervisor.config import Settings, get_settings
from supervisor.decisions import (
    ALL_AGENT_NAMES,
    SupervisorDecision,
)
from supervisor.logging_setup import get_logger
from supervisor.providers import LLMProvider

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are the Supervisor of a multi-agent system.

You NEVER answer the user's question directly.
You decide which specialist agents should participate, in what order,
and whether they can run in parallel.

Available agents:
- "research"  : information gathering, search, fact collection
- "analytics" : KPI calculations, aggregations, metrics
- "calculator": safe mathematical evaluation
- "writer"    : produce a draft report or final prose answer
- "reviewer"  : validate quality, completeness, consistency

Rules:
- Always include "writer" unless the answer is a one-line numeric result.
- Include "reviewer" for any non-trivial answer or when the stakes matter.
- If only arithmetic is needed, "calculator" + "writer" is sufficient.
- execution_order is the ordered list of agents you would actually invoke.
- Set requires_parallel_execution=true ONLY when all selected agents are
  independent of each other and their order does not matter.

Return a SupervisorDecision JSON object."""


def make_supervisor_node(provider: LLMProvider, settings: Settings | None = None) -> Any:
    """Build the Supervisor node function for the graph."""
    settings = settings or get_settings()

    def supervisor_node(state: dict[str, Any]) -> dict[str, Any]:
        query = state.get("query", "")
        logger.info("supervisor.start", query_length=len(query))
        decision = plan_decision(query, provider, settings)
        if "writer" not in decision.selected_agents:
            decision.selected_agents.append("writer")
        if decision.execution_order and "writer" not in decision.execution_order:
            decision.execution_order.append("writer")
        if (
            decision.selected_agents
            and "reviewer" not in decision.selected_agents
            and _looks_substantial(query, decision)
        ):
            decision.selected_agents.append("reviewer")
            decision.execution_order.append("reviewer")
        return {
            "selected_agents": decision.selected_agents,
            "execution_order": decision.execution_order,
            "requires_parallel_execution": decision.requires_parallel_execution,
            "supervisor_reasoning": decision.reasoning,
        }

    return supervisor_node


def plan_decision(query: str, provider: LLMProvider, settings: Settings) -> SupervisorDecision:
    """Produce a :class:`SupervisorDecision` for the given query.

    Falls back to a deterministic heuristic router if the provider fails.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query},
    ]
    try:
        result = provider.complete(messages, response_model=SupervisorDecision)
    except Exception as exc:
        logger.warning(
            "supervisor.provider_error",
            error_class=type(exc).__name__,
            error=str(exc),
        )
        result = _heuristic_plan(query)
    if not isinstance(result, SupervisorDecision):
        result = SupervisorDecision.model_validate(result)
    _validate_decision(result, settings)
    logger.info(
        "supervisor.decision",
        selected=result.selected_agents,
        order=result.execution_order,
        parallel=result.requires_parallel_execution,
        reasoning=result.reasoning,
    )
    return result


def _validate_decision(decision: SupervisorDecision, settings: Settings) -> None:
    valid = set(ALL_AGENT_NAMES)
    for name in decision.selected_agents:
        if name not in valid:
            raise ValueError(f"unknown agent in selected_agents: {name}")
    for name in decision.execution_order:
        if name not in valid:
            raise ValueError(f"unknown agent in execution_order: {name}")
    parallel_count = len(decision.selected_agents)
    if parallel_count > settings.max_parallel_agents:
        logger.warning(
            "supervisor.parallel_capped",
            requested=parallel_count,
            max=settings.max_parallel_agents,
        )


def _heuristic_plan(query: str) -> SupervisorDecision:
    """Deterministic fallback when the provider is unavailable or invalid."""
    q = query.lower()
    has_math = (
        any(ch in q for ch in "+-*/%^")
        or any(tok in q.split() for tok in ("x", "×", "into", "times", "multiplied"))
    ) and any(ch.isdigit() for ch in q)
    is_simple_math = has_math and len(q.split()) < 12
    is_complex = len(q.split()) > 20 or any(
        kw in q for kw in ("report", "analyze", "analysis", "earnings", "comprehensive")
    )
    if is_simple_math:
        return SupervisorDecision(
            selected_agents=["calculator", "writer"],
            execution_order=["calculator", "writer"],
            reasoning="heuristic: short query with arithmetic operators",
            requires_parallel_execution=False,
        )
    if is_complex:
        return SupervisorDecision(
            selected_agents=["research", "analytics", "writer", "reviewer"],
            execution_order=["research", "analytics", "writer", "reviewer"],
            reasoning="heuristic: long query or analysis keywords detected",
            requires_parallel_execution=True,
        )
    return SupervisorDecision(
        selected_agents=["writer"],
        execution_order=["writer"],
        reasoning="heuristic: default single-agent path",
        requires_parallel_execution=False,
    )


def _looks_substantial(query: str, decision: SupervisorDecision) -> bool:
    return len(query.split()) > 8 or any(
        a in decision.selected_agents for a in ("research", "analytics")
    )


# Matches the first arithmetic expression in a natural-language query.
# Requires at least one digit, one operator, and one more digit.
_EXPRESSION_RE = re.compile(r"\d+(?:\s*(?:\*\*|[+\-*/%^x×])\s*\d+)+")


def extract_expression(query: str) -> str | None:
    """Extract the first plausible arithmetic expression from a query.

    Recognises the operators ``+``, ``-``, ``*``, ``/``, ``%``, ``^``,
    ``x`` and the unicode multiplication sign, as well as Python's ``**``
    power operator.  # noqa: RUF002

    The ``x`` and unicode forms are normalised to ``*`` and ``^`` to ``**``
    so the result is valid Python and can be passed to :func:`safe_eval`.
    # noqa: RUF002

    Returns the matched substring stripped, or ``None`` if no plausible
    expression is present.
    """
    match = _EXPRESSION_RE.search(query)
    if not match:
        return None
    expr = match.group(0).strip().replace("×", "*").replace("^", "**")
    return re.sub(r"\s+x\s+", " * ", expr)
