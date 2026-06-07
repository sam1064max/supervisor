# Architecture Decision Records

This directory contains the ADRs for the Supervisor project.

| ID | Title | Status |
|---|---|---|
| [ADR-001](ADR-001-use-langgraph.md) | Use LangGraph as the orchestration framework | Accepted |
| [ADR-002](ADR-002-typed-state.md) | Strongly typed state with Pydantic v2 | Accepted |
| [ADR-003](ADR-003-llm-provider-abstraction.md) | Provider-agnostic LLM interface with offline `FakeProvider` | Accepted |
| [ADR-004](ADR-004-dynamic-routing.md) | Dynamic routing via LLM-based planner | Accepted |
| [ADR-005](ADR-005-deployment-surface.md) | CLI + library + Docker deployment surface | Accepted |

ADRs are immutable once accepted. If a decision changes, write a new ADR
that supersedes the old one; do not edit in place.
