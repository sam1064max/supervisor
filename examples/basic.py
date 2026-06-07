"""End-to-end examples for the Supervisor library API.

Run with:
    uv run python examples/basic.py

The default `FakeProvider` is used so the examples are hermetic.
"""

from __future__ import annotations

import json

from supervisor import Supervisor, SupervisorResult, run_supervisor
from supervisor.decisions import (
    CalculationResult,
    DraftReport,
    ReviewResult,
    SupervisorDecision,
)
from supervisor.providers import FakeProvider


def example_one_shot() -> None:
    """The simplest possible call."""
    print("=" * 70)
    print("Example 1: one-shot run_supervisor()")
    print("=" * 70)
    result: SupervisorResult = run_supervisor("What is 17 x 32?")
    print(f"final_answer: {result.final_answer}")
    print(f"trace_id={result.trace_id}  duration_ms={result.duration_ms:.1f}")
    print()


def example_reuse_graph() -> None:
    """Reuse the ``run_supervisor`` convenience for many queries.

    Each call builds a fresh ``Supervisor`` (and fresh ``FakeProvider``)
    because the graph captures the provider at build time. In production
    with a real provider, you'd build the ``Supervisor`` once and reuse
    it across requests - the underlying ``httpx`` client pools connections.
    """
    print("=" * 70)
    print("Example 2: many queries via run_supervisor()")
    print("=" * 70)
    for q in ["What is 6 * 7?", "Compute 100 / 4", "Research solar vs wind"]:
        r = run_supervisor(q)
        print(f"  Q: {q}")
        print(f"  A: {r.final_answer[:80]}...")
    print()


def example_custom_provider() -> None:
    """Pre-queue a FakeProvider with deterministic responses."""
    print("=" * 70)
    print("Example 3: hand-rolled deterministic provider")
    print("=" * 70)

    fake = FakeProvider()
    fake.queue(
        SupervisorDecision(
            selected_agents=["calculator", "writer"],
            execution_order=["calculator", "writer"],
            requires_parallel_execution=False,
            reasoning="forced for demo",
        )
    )
    fake.queue(CalculationResult(expression="2 ** 10", value=1024.0, unit=None))
    fake.queue(
        DraftReport(
            title="2^10",
            summary="Two to the tenth is 1024.",
            body="2^10 = 1024. This matches the well-known 1-KiB boundary.",
            citations=[],
        )
    )
    fake.queue(ReviewResult(is_sufficient=True, feedback="ok", confidence=0.99, issues=[]))

    sup = Supervisor(provider=fake)
    result = sup.run("What is 2^10?")
    print(f"  {result.final_answer}")
    print()


def example_json_output() -> None:
    """Emit a JSON envelope for log/queue pipelines."""
    print("=" * 70)
    print("Example 4: JSON envelope")
    print("=" * 70)
    result = run_supervisor("Hello")
    envelope = {
        "final_answer": result.final_answer,
        "trace_id": result.trace_id,
        "request_id": result.request_id,
        "duration_ms": result.duration_ms,
        "error": result.error,
    }
    print(json.dumps(envelope, indent=2))
    print()


if __name__ == "__main__":
    example_one_shot()
    example_reuse_graph()
    example_custom_provider()
    example_json_output()
