# Roadmap

`v0.1.0` is a complete, hermetic reference implementation. The following items
are deliberately deferred.

## v0.2.0 - Persistent state

* Postgres checkpointer.
* Resume from `thread_id` across processes.
* Run history API.

## v0.3.0 - Provider expansion

* Bedrock provider.
* Azure OpenAI provider.
* Local Ollama provider.

## v0.4.0 - Streaming

* Token streaming from the Writer.
* Server-sent events over an optional HTTP adapter.

## v0.5.0 - Tooling

* Pluggable research tool (Tavily, SerpAPI).
* Code interpreter sandbox for the Analytics agent.

## v1.0.0 - Hardening

* Property-based tests for the planner.
* Fuzz tests for the calculator.
* Load tests with `locust`.
* OpenTelemetry export.
* Multi-tenant isolation.
