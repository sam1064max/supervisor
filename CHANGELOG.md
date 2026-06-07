# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-06-07

### Added
- `Supervisor` and `run_supervisor` now auto-seed a `FakeProvider` for the
  offline experience, so `uv run supervisor run "..."` works without any
  API key or test fixture.
- `^` is now recognised and normalised to `**` in the calculator (power
  notation), and `**` is accepted as a single operator in
  `extract_expression`.
- `examples/basic.py` - end-to-end library walkthrough.
- `examples/benchmark.py` - quick latency benchmark.
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`.
- `.github/ISSUE_TEMPLATE/{bug,feature,question}.yml`.
- `.github/PULL_REQUEST_TEMPLATE.md`.
- CI + coverage + license badges in the README.

### Fixed
- `_resolve_provider` preserves the `build_provider` monkeypatch seam
  used by tests while still seeding the offline fake.
- `examples/basic.py` example 3 used a calculator expression (`2^10`) that
  the previous regex did not extract.

## [0.1.1] - 2026-06-07

### Fixed
- Removed unused `CompiledStateGraph` import (`graph.py`).
- Migrated `Callable` import to `collections.abc` (`tools.py`).
- Normalised line-wrapping in `tools.py` to satisfy black.

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
