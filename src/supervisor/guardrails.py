"""Input and output guardrails.

Guardrails run before and after the rest of the graph. They populate
``rejection_reason`` and ``error`` rather than raising, so the graph can
short-circuit cleanly.
"""

from __future__ import annotations

import re
from typing import Any

from supervisor.decisions import GuardrailVerdict
from supervisor.logging_setup import get_logger

logger = get_logger(__name__)

MAX_QUERY_LENGTH = 8000
MIN_QUERY_LENGTH = 1
MAX_ANSWER_LENGTH = 50_000

_UNSAFE_PATTERNS = [
    re.compile(r"ignore (the )?previous instructions", re.IGNORECASE),
    re.compile(r"disregard (the )?system prompt", re.IGNORECASE),
    re.compile(r"reveal (your|the) (system|hidden) prompt", re.IGNORECASE),
]


def input_guardrail(state: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input. Returns a partial state update."""
    query = state.get("query", "")
    verdict = _evaluate_input(query)
    if not verdict.allowed:
        logger.warning("guardrail.input.rejected", reason=verdict.reason)
        return {
            "rejection_reason": verdict.reason,
            "error": "input_rejected",
            "final_answer": f"Request rejected: {verdict.reason}",
        }
    return {}


def _evaluate_input(query: Any) -> GuardrailVerdict:
    if query is None:
        return GuardrailVerdict(allowed=False, reason="query is None")
    if not isinstance(query, str):
        return GuardrailVerdict(allowed=False, reason="query is not a string")
    stripped = query.strip()
    if len(stripped) < MIN_QUERY_LENGTH:
        return GuardrailVerdict(allowed=False, reason="query is empty")
    if len(stripped) > MAX_QUERY_LENGTH:
        return GuardrailVerdict(
            allowed=False, reason=f"query exceeds {MAX_QUERY_LENGTH} characters"
        )
    for pat in _UNSAFE_PATTERNS:
        if pat.search(stripped):
            return GuardrailVerdict(
                allowed=False, reason="query matches a prompt-injection pattern"
            )
    return GuardrailVerdict(allowed=True, reason="ok")


def output_guardrail(state: dict[str, Any]) -> dict[str, Any]:
    """Validate the final answer before returning it."""
    answer = state.get("final_answer", "")
    verdict = _evaluate_output(answer)
    if not verdict.allowed:
        logger.warning("guardrail.output.rejected", reason=verdict.reason)
        return {
            "rejection_reason": verdict.reason,
            "error": "output_rejected",
            "final_answer": f"Output rejected: {verdict.reason}",
        }
    return {}


def _evaluate_output(answer: Any) -> GuardrailVerdict:
    if not isinstance(answer, str) or not answer.strip():
        return GuardrailVerdict(allowed=False, reason="empty final answer")
    if len(answer) > MAX_ANSWER_LENGTH:
        return GuardrailVerdict(
            allowed=False, reason="final answer exceeds length limit"
        )
    return GuardrailVerdict(allowed=True, reason="ok")
