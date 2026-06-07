# ADR-003: Provider-Agnostic LLM Interface with Offline FakeProvider

- Status: Accepted
- Date: 2026-06-07
- Deciders: Engineering

## Context

The constitution requires:

- "No test should depend on internet access."
- "Mock all external services."
- "Document dependency rationale."

LangChain ships an `init_chat_model` helper that supports OpenAI, Anthropic,
and others, but the reference implementation must remain runnable in CI
without API keys.

## Decision

We define a minimal `LLMProvider` protocol with two production
implementations (`OpenAIProvider`, `AnthropicProvider`) and one offline
implementation (`FakeProvider`) that returns deterministic, scripted
responses.

- The CLI default is `fake`. Real providers require explicit opt-in.
- `FakeProvider` is the source of the deterministic behaviour exercised by
  the test suite.
- All HTTP calls in real providers are wrapped in `httpx` so we can mock
  them with `respx` in tests.

## Consequences

Positive:

- Tests are hermetic and run in < 5 seconds.
- The same code path executes in dev and CI; we never branch on "is this a
  test?".
- Provider outages degrade to a clear error, not a hang.

Negative:

- We maintain a small provider layer; the long-term plan is to delegate it
  to `langchain` adapters. We will do that when the test ergonomics allow.
- The `FakeProvider` is a maintenance burden if the agent contracts drift.

## Alternatives considered

- **Always require OpenAI**: violates the no-internet rule.
- **Use `vcrpy` cassettes**: works but adds a binary asset to the repo and
  makes the system harder to reason about.
