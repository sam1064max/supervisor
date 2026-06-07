# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-06-07

### Added
- Initial public release of the Supervisor Agent reference implementation.
- LangGraph-based multi-agent orchestration with dynamic routing.
- Specialist agents: Research, Analytics, Calculator, Writer, Reviewer.
- Parallel specialist execution via `Send`.
- Reflection loop (Writer -> Reviewer -> Writer) with bounded cycles.
- Optional Human-in-the-Loop checkpoint (`interrupt`/`resume`).
- Input and output guardrails.
- Failure recovery: configurable retries with per-agent fallback.
- Strongly typed `AgentState` (TypedDict) and `SupervisorDecision` (Pydantic).
- LLM provider abstraction with offline `FakeProvider` for hermetic tests.
- Structured JSON logging with `trace_id`, `request_id`, `duration_ms`.
- CLI: `supervisor run`, `supervisor plan`, `supervisor agents`.
- Library API: `Supervisor.run()`.
- Multi-stage Dockerfile and `docker-compose.yml`.
- CI workflow (install, ruff, black, mypy, pytest, docker build).
- ADRs 001-005, Architecture.md, Dataflow.md, SequenceDiagram.md,
  Troubleshooting.md.
