"""Run the Supervisor on a small benchmark and print timings.

Default: offline `FakeProvider`, 5 queries, sequential.
"""

from __future__ import annotations

import statistics
import time

from supervisor import run_supervisor

QUERIES: list[str] = [
    "What is 17 x 32?",
    "Compute 100 / 4",
    "Research solar vs wind",
    "Explain transformer attention",
    "What is 2 to the power of 10?",
]


def main() -> None:
    durations: list[float] = []
    for q in QUERIES:
        start = time.perf_counter()
        result = run_supervisor(q)
        wall = (time.perf_counter() - start) * 1000
        durations.append(wall)
        print(
            f"{q!r:45s}  "
            f"reported={result.duration_ms:7.2f}ms  "
            f"wall={wall:7.2f}ms  "
            f"len={len(result.final_answer)}  "
            f"err={result.error or '-'}"
        )
    print("-" * 70)
    print(
        f"median={statistics.median(durations):.1f}ms  "
        f"p95={sorted(durations)[int(len(durations) * 0.95) - 1]:.1f}ms  "
        f"max={max(durations):.1f}ms"
    )


if __name__ == "__main__":
    main()
