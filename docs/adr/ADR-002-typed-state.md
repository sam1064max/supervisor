# ADR-002: Strongly Typed State with Pydantic v2 and TypedDict Reducers

- Status: Accepted
- Date: 2026-06-07
- Deciders: Engineering

## Context

Multi-agent systems are notorious for silent state corruption: one branch
overwrites another, optional fields appear and disappear, and untyped
dicts accumulate.

## Decision

- `AgentState` is a `TypedDict` with explicit fields and `Annotated`
  reducers.
- All inter-agent payloads are Pydantic v2 `BaseModel` subclasses.
- The Supervisor decision is a Pydantic `BaseModel` and is produced via
  `with_structured_output(...)` so we never parse free text.
- All settings are Pydantic `BaseSettings` loaded from environment / `.env`.

## Consequences

Positive:

- The mypy strictness catches drift at PR time.
- The graph contract is enforceable in tests via fixture factories.
- Pydantic v2 is the same library used by LangGraph internally, so we
  share a single validation model.

Negative:

- Some LangGraph internals are not type-clean; we isolate them in
  `src/supervisor/typing.py`.
- Adding a new field requires a Pydantic migration; that is the price of
  safety.

## Alternatives considered

- **dataclasses only**: no reducer support, no validation.
- **attrs**: similar to dataclasses, weaker ecosystem.
- **msgspec**: faster but less ecosystem support.
