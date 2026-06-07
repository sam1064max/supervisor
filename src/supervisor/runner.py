"""Top-level entry point. Wraps graph invocation with logging and tracing.

The :class:`Supervisor` is the only public façade. Construct it once and
reuse it across requests. Each :meth:`Supervisor.run` call mints a fresh
``request_id`` and ``trace_id`` and binds them to the logging context.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from supervisor.config import Settings, get_settings
from supervisor.graph import build_graph
from supervisor.logging_setup import (
    bind_request_context,
    configure_logging,
    get_logger,
    new_trace_id,
    timed,
)
from supervisor.providers import LLMProvider, build_provider
from supervisor.state import AgentState

logger = get_logger(__name__)


@dataclass
class SupervisorResult:
    """Result of a single Supervisor run."""

    final_answer: str
    state: dict[str, Any] = field(default_factory=dict)
    trace_id: str = ""
    request_id: str = ""
    duration_ms: float = 0.0
    error: str | None = None
    rejection_reason: str | None = None
    awaiting_human: bool = False


class Supervisor:
    """High-level façade. Construct once, invoke many times."""

    def __init__(
        self,
        settings: Settings | None = None,
        provider: LLMProvider | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        configure_logging(self._settings)
        self._provider = provider or build_provider(self._settings)
        self._graph = build_graph(self._provider, self._settings)

    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def provider(self) -> LLMProvider:
        return self._provider

    def run(
        self,
        query: str,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> SupervisorResult:
        """Run the Supervisor end-to-end on a single query."""
        request_id = request_id or str(uuid.uuid4())
        trace_id = trace_id or new_trace_id()
        with bind_request_context(request_id=request_id, trace_id=trace_id):
            return self._run_inner(query, request_id, trace_id)

    def _run_inner(
        self, query: str, request_id: str, trace_id: str
    ) -> SupervisorResult:
        started = time.perf_counter()
        initial: dict[str, Any] = {
            "query": query,
            "request_id": request_id,
            "trace_id": trace_id,
            "started_at": started,
            "completed_at": 0.0,
            "review_cycle": 0,
            "review_status": "pending",
            "completed_agents": [],
            "selected_agents": [],
            "execution_order": [],
            "research_results": [],
            "analytics_results": [],
            "calculation_results": [],
            "metadata": {},
        }
        with timed(logger, "supervisor.run", query_length=len(query)):
            try:
                final_state: dict[str, Any] = self._graph.invoke(initial)  # type: ignore[assignment]
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "supervisor.crashed",
                    error_class=type(exc).__name__,
                    error=str(exc),
                )
                return SupervisorResult(
                    final_answer=f"Supervisor crashed: {exc}",
                    state={},
                    trace_id=trace_id,
                    request_id=request_id,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    error="runner_crashed",
                )
        completed = time.perf_counter()
        final_state["completed_at"] = completed
        meta = dict(final_state.get("metadata") or {})
        return SupervisorResult(
            final_answer=str(final_state.get("final_answer", "")),
            state=dict(final_state),
            trace_id=trace_id,
            request_id=request_id,
            duration_ms=(completed - started) * 1000,
            error=final_state.get("error"),
            rejection_reason=final_state.get("rejection_reason"),
            awaiting_human=bool(meta.get("awaiting_human", False)),
        )


def run_supervisor(
    query: str,
    *,
    settings: Settings | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
) -> SupervisorResult:
    """Module-level convenience wrapper around :class:`Supervisor`."""
    sup = Supervisor(settings=settings)
    return sup.run(query, request_id=request_id, trace_id=trace_id)
