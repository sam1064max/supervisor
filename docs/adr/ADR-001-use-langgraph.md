# ADR-001: Use LangGraph as the Orchestration Framework

- Status: Accepted
- Date: 2026-06-07
- Deciders: Engineering

## Context

The Supervisor pattern requires:

- A graph runtime that supports typed state.
- First-class parallel branches (`Send`).
- Built-in human-in-the-loop (`interrupt`/`resume`).
- A reducer model for state merging across parallel branches.
- Production observability hooks.

## Decision

We adopt [LangGraph](https://langchain-ai.github.io/langgraph/) as the
orchestration runtime.

## Consequences

Positive:

- Aligns the project with the most widely used multi-agent framework in the
  Python ecosystem.
- Reduces the amount of bespoke code we have to maintain.
- Provides a future migration path to LangGraph Platform, LangSmith, and
  LangChain ecosystem tools.

Negative:

- Couples the project to a third-party runtime.
- Public type surface is imperfect; we pin to a specific version.
- Increases transitive dependency surface.

## Alternatives considered

- **Hand-rolled state machine**: too much bespoke code, no observability,
  no `Send` equivalent.
- **Temporal**: production-grade but explicitly LLM-agnostic; we would still
  need to model reflection and routing by hand.
- **Autogen / CrewAI**: weaker parallel / reducer support at the time of
  evaluation.
