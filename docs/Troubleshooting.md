# Troubleshooting

## "All my tests are skipped"

`pytest` collects only the test files matching the configured pattern. If you
ran `pytest` from the repo root with no arguments, every test should be
collected. If not, check:

```bash
uv run pytest --collect-only
```

You should see > 50 tests. If you see zero, your `pyproject.toml`
`[tool.pytest.ini_options]` is being shadowed by an older `setup.cfg` or
`pytest.ini` - delete those.

## "ModuleNotFoundError: langgraph"

You are probably using global Python. Always use `uv`:

```bash
uv sync
uv run pytest
uv run supervisor run "..."
```

## "Supervisor decided to use no agents"

This is usually a malformed `SupervisorDecision`. Enable DEBUG logging:

```bash
SUPERVISOR_LOG_LEVEL=DEBUG uv run supervisor run "..."
```

Look for `supervisor.decision_failed` and the `error_class` field. The most
common cause is the provider emitting prose that fails Pydantic validation.
The system retries once, then falls back to a heuristic router.

## "Parallel execution is sequential"

The graph uses `Send`. If your state reducer is not `Annotated[list[T],
operator.add]`, LangGraph falls back to last-write-wins. Check the
`AgentState` definition.

## "Human checkpoint never resumes"

`interrupt` requires a thread id and a checkpointer. The default
`MemorySaver` is process-local. For production, configure a persistent
checkpointer (e.g. `Postgres` or `Redis`) and pass the same `thread_id` on
resume.

## "Coverage dropped below 80%"

Run the coverage report and locate uncovered lines:

```bash
uv run pytest --cov=src --cov-report=term-missing
```

Add a test for the uncovered branch. Every new branch needs a test.

## "Mypy complains about langgraph types"

LangGraph's public types are imperfect. We pin to a known-good version in
`pyproject.toml`. If you upgrade, expect to update `mypy` ignores in
`src/supervisor/typing.py`.

## "Docker image is huge"

We use a multi-stage build with `python:3.11-slim` and a `uv` install stage.
The final image should be < 250 MB. If it grows, check for stray `pip
install` calls and remove them.

## "JSON logs are interleaved with text"

`structlog` is configured to emit JSON to stderr. If you see mixed output,
something is calling `print()` directly. Replace it with `logger.info(...)`.
