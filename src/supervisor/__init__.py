"""Supervisor - production-grade multi-agent orchestration reference implementation.

Public API:
    Supervisor          - high-level façade, construct once and reuse
    SupervisorResult    - result of a single run
    run_supervisor      - module-level convenience wrapper
"""

from __future__ import annotations

from supervisor._version import __version__
from supervisor.runner import Supervisor, SupervisorResult, run_supervisor

__all__ = [
    "__version__",
    "Supervisor",
    "SupervisorResult",
    "run_supervisor",
]
