"""Retry and fallback helpers for specialist agents.

The :func:`with_retries` decorator wraps a node function with bounded retry
and exponential backoff. After exhaustion, the wrapped function returns a
partial state update that includes ``error`` and the last exception.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from supervisor.logging_setup import get_logger

logger = get_logger(__name__)

NodeFn = Callable[[dict[str, Any]], dict[str, Any]]


def with_retries(
    fn: NodeFn,
    *,
    agent_name: str,
    max_retries: int,
) -> NodeFn:
    """Wrap a node function with bounded retry + exponential backoff."""

    def wrapper(state: dict[str, Any]) -> dict[str, Any]:
        attempt = 0
        last_exc: Exception | None = None
        while attempt <= max_retries:
            try:
                delta = fn(state)
                if attempt > 0:
                    logger.info("agent.recovered", agent=agent_name, attempt=attempt)
                meta = dict(delta.get("metadata") or {})
                retries = dict(meta.get("retries") or {})
                retries[agent_name] = attempt
                meta["retries"] = retries
                return {**delta, "metadata": meta}
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "agent.retry",
                    agent=agent_name,
                    attempt=attempt,
                    max_retries=max_retries,
                    error_class=type(exc).__name__,
                    error=str(exc),
                )
                attempt += 1
                if attempt <= max_retries:
                    time.sleep(min(0.05 * (2 ** (attempt - 1)), 1.0))
        assert last_exc is not None
        return {
            "error": f"{agent_name}_failed",
            "metadata": {
                "retries": {agent_name: attempt},
                "last_error": str(last_exc),
            },
        }

    return wrapper
