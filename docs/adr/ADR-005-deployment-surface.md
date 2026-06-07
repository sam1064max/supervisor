# ADR-005: CLI + Library + Docker Deployment Surface

- Status: Accepted
- Date: 2026-06-07
- Deciders: Engineering

## Context

The constitution requires that the project be:

- Reproducible from scratch.
- CI-runnable.
- Inspectable in a Staff Engineer portfolio review.
- Reachable both as a binary and as an importable library.

## Decision

We ship three surfaces:

1. **CLI** (`supervisor run`, `supervisor plan`, `supervisor agents`) via
   `typer`. The CLI is a thin shell over the library API.
2. **Library** (`from supervisor import Supervisor`) so the system can be
   embedded in any Python application.
3. **Container** (multi-stage Dockerfile + `docker-compose.yml`) so the
   system can be deployed without local Python.

All three call the same `run_supervisor(query, settings)` function. There
is no "test mode" code path; the offline `FakeProvider` is the default in
all three surfaces.

## Consequences

Positive:

- One code path, three consumption models.
- The container is the only thing the CI needs to test, simplifying the
  pipeline.
- The library API is sufficient for unit tests; no subprocess invocation
  required.

Negative:

- More surface to document. The README, the `supervisor --help` output, and
  the Sphinx-style docstrings must stay in sync.
- Typer / Click adds ~15 transitive packages; we accept this for the UX.

## Alternatives considered

- **CLI only**: rejected; the library surface is required for embedding
  the system in larger applications.
- **HTTP service only**: rejected; the system is fundamentally synchronous
  and a CLI is a more honest interface.
