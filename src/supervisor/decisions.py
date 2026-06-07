"""Structured outputs for the Supervisor and its specialist agents.

Every payload that crosses a graph edge is a Pydantic v2 model. The
``SupervisorDecision`` is produced via ``with_structured_output(...)`` (or
its manual equivalent in the provider layer); we never parse free text.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AgentName = Literal[
    "research",
    "analytics",
    "calculator",
    "writer",
    "reviewer",
]

ALL_AGENT_NAMES: list[str] = [
    "research",
    "analytics",
    "calculator",
    "writer",
    "reviewer",
]


class SupervisorDecision(BaseModel):
    """The output of the Supervisor planner node."""

    selected_agents: list[str] = Field(
        description="Specialist agents that should participate, in any order.",
    )
    execution_order: list[str] = Field(
        description="Ordered list of agents to execute. Empty if no execution required.",
    )
    reasoning: str = Field(
        description="Concise rationale, used for logging and audit.",
    )
    requires_parallel_execution: bool = Field(
        default=False,
        description="True if all upstream agents are independent and may run concurrently.",
    )


class ResearchResult(BaseModel):
    """Output of the Research agent."""

    topic: str
    findings: list[str]
    sources: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class AnalyticsResult(BaseModel):
    """Output of the Analytics agent."""

    metric: str
    value: float
    unit: str = ""
    notes: str = ""


class CalculationResult(BaseModel):
    """Output of the Calculator agent."""

    expression: str
    value: float
    is_exact: bool = True


class DraftReport(BaseModel):
    """Output of the Writer agent."""

    title: str
    summary: str
    body: str
    citations: list[str] = Field(default_factory=list)


class ReviewResult(BaseModel):
    """Output of the Reviewer agent."""

    is_sufficient: bool
    feedback: str
    confidence: float = Field(ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list)


class GuardrailVerdict(BaseModel):
    """Output of the input/output guardrails."""

    allowed: bool
    reason: str = ""
