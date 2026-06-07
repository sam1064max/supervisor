"""Strongly typed ``AgentState`` for the Supervisor graph.

Fields with the ``Annotated[list[T], operator.add]`` shape are merged by
concatenation when parallel branches return partial updates, which is the
LangGraph idiom for fan-in.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

from supervisor.decisions import (
    AnalyticsResult,
    CalculationResult,
    ResearchResult,
    ReviewResult,
)

ReviewStatus = Literal["pending", "sufficient", "forced_complete"]


class AgentState(TypedDict, total=False):
    """Mutable state passed through the graph.

    ``total=False`` makes every field optional; nodes must tolerate missing
    keys on first invocation. The graph is the single source of truth at
    runtime.
    """

    # Identity
    query: str
    request_id: str
    trace_id: str

    # Supervisor plan
    selected_agents: list[str]
    execution_order: list[str]
    requires_parallel_execution: bool
    supervisor_reasoning: str

    # Execution results (parallel-safe via reducer)
    completed_agents: Annotated[list[str], operator.add]
    research_results: Annotated[list[ResearchResult], operator.add]
    analytics_results: Annotated[list[AnalyticsResult], operator.add]
    calculation_results: Annotated[list[CalculationResult], operator.add]

    # Reflection
    report: str
    review_feedback: str
    review_result: ReviewResult | None
    review_cycle: int
    review_status: ReviewStatus

    # Output
    final_answer: str
    rejection_reason: str | None

    # Telemetry
    started_at: float
    completed_at: float
    metadata: dict[str, Any]
    error: str | None
