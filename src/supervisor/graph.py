"""``StateGraph`` construction. Wires all nodes, edges, and routing logic.

The graph topology is:

    START
      -> input_guardrail
      -> supervisor
      -> (parallel via Send | sequential first hop)
      -> writer
      -> reviewer (loop, bounded)
      -> output_guardrail
      -> human_checkpoint (optional)
      -> END
"""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from supervisor.agents import (
    make_analytics_agent,
    make_calculator_agent,
    make_research_agent,
    make_reviewer_agent,
    make_writer_agent,
)
from supervisor.config import Settings, get_settings
from supervisor.guardrails import input_guardrail, output_guardrail
from supervisor.logging_setup import get_logger
from supervisor.providers import LLMProvider, build_provider
from supervisor.recovery import with_retries
from supervisor.state import AgentState
from supervisor.supervisor import make_supervisor_node

logger = get_logger(__name__)

_UPSTREAM_AGENTS = ("research", "analytics", "calculator")


def build_graph(
    provider: LLMProvider | None = None,
    settings: Settings | None = None,
) -> Any:  # langgraph's StateGraph/CompiledStateGraph generics are imperfect
    """Construct and compile the Supervisor graph."""
    settings = settings or get_settings()
    provider = provider or build_provider(settings)

    builder: Any = StateGraph(AgentState)

    builder.add_node("input_guardrail", input_guardrail)
    builder.add_node("supervisor", make_supervisor_node(provider, settings))
    builder.add_node(
        "research",
        with_retries(
            make_research_agent(provider),
            agent_name="research",
            max_retries=settings.agent_max_retries,
        ),
    )
    builder.add_node(
        "analytics",
        with_retries(
            make_analytics_agent(provider),
            agent_name="analytics",
            max_retries=settings.agent_max_retries,
        ),
    )
    builder.add_node(
        "calculator",
        with_retries(
            make_calculator_agent(provider),
            agent_name="calculator",
            max_retries=settings.agent_max_retries,
        ),
    )
    builder.add_node(
        "writer",
        with_retries(
            make_writer_agent(provider),
            agent_name="writer",
            max_retries=settings.agent_max_retries,
        ),
    )
    builder.add_node(
        "reviewer",
        with_retries(
            make_reviewer_agent(provider),
            agent_name="reviewer",
            max_retries=settings.agent_max_retries,
        ),
    )
    builder.add_node("output_guardrail", output_guardrail)
    builder.add_node("human_checkpoint", _human_checkpoint)

    builder.add_edge(START, "input_guardrail")
    builder.add_conditional_edges(
        "input_guardrail",
        _after_input_guardrail,
        {"supervisor": "supervisor", END: END},
    )
    builder.add_conditional_edges(
        "supervisor",
        _route_supervisor,
        ["research", "analytics", "calculator", "writer", "reviewer"],
    )
    builder.add_edge("research", "writer")
    builder.add_edge("analytics", "writer")
    builder.add_edge("calculator", "writer")
    builder.add_conditional_edges(
        "writer",
        _after_writer,
        {"reviewer": "reviewer", "output_guardrail": "output_guardrail"},
    )
    builder.add_conditional_edges(
        "reviewer",
        _make_after_reviewer(settings),
        {"writer": "writer", "output_guardrail": "output_guardrail"},
    )
    builder.add_conditional_edges(
        "output_guardrail",
        _make_after_output_guardrail(settings),
        {"human_checkpoint": "human_checkpoint", END: END},
    )
    builder.add_conditional_edges(
        "human_checkpoint",
        _after_human,
        {"writer": "writer", END: END},
    )

    return builder.compile()


def _after_input_guardrail(state: dict[str, Any]) -> str:
    if state.get("error") == "input_rejected":
        return END
    return "supervisor"


def _route_supervisor(
    state: dict[str, Any],
) -> list[Send] | list[str]:
    order = list(state.get("execution_order") or [])
    parallel = bool(state.get("requires_parallel_execution", False))
    if not order:
        return ["writer"]
    upstream = [a for a in order if a in _UPSTREAM_AGENTS]
    downstream = [a for a in order if a not in _UPSTREAM_AGENTS]
    if parallel and len(upstream) > 1:
        return [Send(name, state) for name in upstream]
    if upstream:
        return [upstream[0]]
    if downstream:
        return [downstream[0]]
    return ["writer"]


def _after_writer(state: dict[str, Any]) -> Literal["reviewer", "output_guardrail"]:
    if "reviewer" in (state.get("selected_agents") or []):
        return "reviewer"
    return "output_guardrail"


def _make_after_reviewer(settings: Settings) -> Any:
    def _after_reviewer(state: dict[str, Any]) -> str:
        if state.get("error") == "reviewer_failed":
            return "output_guardrail"
        cycle = int(state.get("review_cycle", 0) or 0)
        status = state.get("review_status", "pending")
        if status == "sufficient":
            return "output_guardrail"
        if cycle >= settings.max_review_cycles:
            logger.warning(
                "review.forced_complete",
                cycle=cycle,
                max=settings.max_review_cycles,
            )
            return "output_guardrail"
        return "writer"

    return _after_reviewer


def _make_after_output_guardrail(settings: Settings) -> Any:
    def _after_output_guardrail(state: dict[str, Any]) -> str:
        if state.get("error") == "output_rejected":
            return END
        if settings.human_review_enabled:
            return "human_checkpoint"
        return END

    return _after_output_guardrail


def _after_human(state: dict[str, Any]) -> str:
    decision = state.get("metadata", {}).get("human_decision")
    if decision == "reject":
        return "writer"
    return END


def _human_checkpoint(state: dict[str, Any]) -> dict[str, Any]:
    """Mark the run as awaiting human approval.

    The runner reads ``metadata.awaiting_human`` and surfaces the answer to
    the operator. The graph terminates here until the operator decides.
    """
    meta = dict(state.get("metadata") or {})
    meta["awaiting_human"] = True
    return {"metadata": meta}
