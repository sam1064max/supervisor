# ADR-004: Dynamic Routing via LLM-Based Planner, Not Hardcoded

- Status: Accepted
- Date: 2026-06-07
- Deciders: Engineering

## Context

The constitution forbids hardcoded routing:

> "Routing must not be hardcoded. Use LLM-based planning."

The naive approach is to keyword-match the user query and call the matching
agent. This produces brittle systems.

## Decision

The Supervisor node prompts an LLM to produce a `SupervisorDecision`
Pydantic model. The decision is the only signal that drives routing. The
LLM is required to return structured output (no free-text parsing).

If structured output fails twice in a row, we fall back to a deterministic
heuristic router that classifies by intent (e.g. presence of digits and
math operators -> Calculator).

## Consequences

Positive:

- New agent types can be added without rewriting routing code; the planner
  simply learns the new option.
- The decision is auditable: every `SupervisorDecision` is logged in full.

Negative:

- Latency: one extra LLM call per request. Mitigated by the offline
  `FakeProvider` for development.
- The heuristic fallback is necessarily imperfect. It is documented and
  bounded.

## Alternatives considered

- **Pure rules engine**: rejected by the constitution.
- **Fine-tuned router model**: defer to v1.0.0.
