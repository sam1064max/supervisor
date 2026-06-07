# Supervisor

> A production-grade reference implementation of the **Supervisor Pattern** for
> multi-agent LLM systems, built on [LangGraph](https://langchain-ai.github.io/langgraph/).

[![CI](https://github.com/sam1064max/supervisor/actions/workflows/ci.yml/badge.svg)](https://github.com/sam1064max/supervisor/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Coverage 96%](https://img.shields.io/badge/coverage-96%25-brightgreen.svg)](pyproject.toml)

The Supervisor coordinates specialist agents. It does not answer user questions.
It routes, orders, parallelises, retries, reflects, and approves. Like an
engineering manager, not a doer.

```text
                +-----------------------+
user request -->|   Input Guardrail     |
                +----------+------------+
                           v
                +----------+------------+
                |     Supervisor        |  <-- dynamic routing
                +----------+------------+
                           v
        +------------------+------------------+
        v                  v                  v
   Research           Analytics         Calculator
        \                  |                  /
         \                 |                 /
          +-------+--------+--------+-------+
                  v                 v
                Writer <-------> Reviewer   <-- reflection loop
                  |
                  v
                Output Guardrail
                  |
                  v
            (optional HITL) --> Final Answer
```

---

## Why this exists

Multi-agent LLM systems fail for predictable reasons:

- The orchestrator drifts into doing work it should be delegating.
- Routing is hardcoded and breaks the moment a request shape changes.
- Failures in one agent take the whole system down.
- There is no observable trace of *why* the system did what it did.

This project is the reference implementation we wished we had: typed state,
structured outputs, parallel fan-out, reflection, human checkpoints, and a
hermetic test story that does not require a network.

## Features

- **Typed state** (`TypedDict` + `Annotated` reducers) and structured `Pydantic` outputs.
- **Dynamic routing** - the supervisor LLM chooses which agents to run, in what order, and whether to parallelise.
- **Parallel fan-out** via LangGraph's `Send` primitive for independent upstream work.
- **Bounded reflection loop** between `Writer` and `Reviewer` with a configurable cap.
- **Guardrails** at the boundary (length, prompt-injection, output sanitation).
- **Optional human-in-the-loop** checkpoint before delivery.
- **Pluggable LLM provider** - `fake` (offline), `openai`, `anthropic` - via `httpx` (no vendor SDK lock-in).
- **Structured JSON logging** with `trace_id` / `request_id` / `duration_ms` correlation.
- **Retries with exponential backoff** for transient provider failures.
- **Hermetic tests** - 177 tests, 96% branch coverage, no network.
- **Multi-stage Docker image** (non-root, `tini` init, healthcheck).
- **CI** - ruff, black, mypy strict, pytest with coverage threshold, Docker build on every push.

---

## Quick start

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
# 1. Install deps
uv sync --all-extras --dev

# 2. Copy and edit env (defaults work offline)
cp .env.example .env

# 3. Run a query (uses fake provider by default)
uv run supervisor run "What is 17 x 32?"

# 4. Or call as a library
uv run python -c "from supervisor import run_supervisor; print(run_supervisor('What is 17 x 32?').final_answer)"
```

To use a real model, set the provider and API key:

```bash
export SUPERVISOR_LLM_PROVIDER=openai
export SUPERVISOR_OPENAI_API_KEY=sk-...
uv run supervisor run "Summarise the latest on vector DBs"
```

See [`config/settings.example.yaml`](config/settings.example.yaml) for the full
list of options, or browse the source: `src/supervisor/config.py`.

---

## Architecture

The full architecture, including a Mermaid component diagram, lives in
[`docs/Architecture.md`](docs/Architecture.md). The short version:

- **`input_guardrail`** rejects empty/over-long/injection-laden inputs.
- **`supervisor`** uses the LLM to emit a `SupervisorDecision` (which agents, in what order, parallel or serial).
- **`_route_supervisor`** dispatches upstream work via `Send` (parallel) or a single hop (serial).
- **`writer`** synthesises a draft, **`reviewer`** decides `sufficient | needs_revision`. The loop is bounded by `max_review_cycles`.
- **`output_guardrail`** validates the final draft.
- **`human_checkpoint`** (optional) hands off to a human reviewer.

A sequence diagram for a typical run is in
[`docs/SequenceDiagram.md`](docs/SequenceDiagram.md).

## Library API

```python
from supervisor import run_supervisor, Supervisor, SupervisorResult

# One-shot
result: SupervisorResult = run_supervisor("Compare 2^10 and 1024.")
print(result.final_answer)
print(result.state["completed_agents"])

# Reuse the compiled graph
agent = Supervisor()
r1 = agent.invoke("What is 12 * 8?")
r2 = agent.invoke("Now divide it by 4.")
```

## CLI

```text
Usage: supervisor [OPTIONS] COMMAND [ARGS]...

Commands:
  run     Run a single query end-to-end.
  plan    Print the routing plan the supervisor would emit.
  agents  List the specialist agents.
```

```bash
# Inspect the routing plan without running agents
uv run supervisor plan "Research solar vs wind and compute 5*5"

# List agents
uv run supervisor agents
```

## Examples

| Query | What happens |
|---|---|
| `What is 17 x 32?` | Calculator only, then writer (no reviewer). |
| `Research solar vs wind and compute 5*5` | Parallel `research` + `calculator`, writer, reviewer. |
| `What's 1024 / 8?` | Calculator + writer; reviewer skipped (trivial). |
| `Explain transformers` | Research + analytics + writer + reviewer. |

See [`tests/regression/`](tests/regression) for end-to-end expected behaviour.

---

## Configuration

All settings come from environment variables (or a YAML file) and are typed via
`pydantic-settings`. The full list is in
[`config/settings.example.yaml`](config/settings.example.yaml).

| Variable | Default | Purpose |
|---|---|---|
| `SUPERVISOR_LLM_PROVIDER` | `fake` | `fake` / `openai` / `anthropic` |
| `SUPERVISOR_LLM_MODEL` | `fake-default` | Model name passed to provider |
| `SUPERVISOR_OPENAI_API_KEY` | - | OpenAI key (when provider=openai) |
| `SUPERVISOR_ANTHROPIC_API_KEY` | - | Anthropic key (when provider=anthropic) |
| `SUPERVISOR_MAX_REVIEW_CYCLES` | `2` | Bound the writer<->reviewer loop |
| `SUPERVISOR_HUMAN_REVIEW_ENABLED` | `false` | Toggle HITL checkpoint |
| `SUPERVISOR_LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `SUPERVISOR_LOG_FORMAT` | `json` | `json` (machine) or `console` (human) |
| `SUPERVISOR_MAX_INPUT_LENGTH` | `4000` | Reject longer inputs |

---

## Testing

```bash
uv run pytest                  # fast
uv run pytest --cov=src        # with coverage
make test-cov                  # gate (fails below 80%)
```

The test suite is fully hermetic - it uses the `fake` provider, so CI does not
require any API keys. 177 tests cover unit, integration, failure, regression,
and edge cases.

## Docker

```bash
docker build -t supervisor:dev .
docker run --rm -e SUPERVISOR_LLM_PROVIDER=fake supervisor:dev \
  supervisor run "What is 12 * 9?"
```

Or with Compose:

```bash
docker compose run --rm supervisor run "Hello"
```

The image is multi-stage, runs as a non-root `supervisor` user, and uses
`tini` as PID 1 for clean signal handling.

## CI

GitHub Actions runs on every push:

1. **Lint** - `ruff check .`
2. **Format** - `black --check .`
3. **Types** - `mypy src tests` (strict)
4. **Tests** - pytest on Python 3.10 / 3.11 / 3.12 with coverage gate
5. **Docker build** - smoke build of the image

See [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

---

## Troubleshooting

See [`docs/Troubleshooting.md`](docs/Troubleshooting.md) for the full FAQ.
Common ones:

- **`ProviderUnavailable: openai ...`** - set `SUPERVISOR_OPENAI_API_KEY` or switch to `fake`.
- **Mypy errors in tests only** - the test tree is configured with a relaxed mypy override in `pyproject.toml`; the same `disallow_untyped_defs` rules do not apply.
- **Tests are slow** - `uv run pytest -n auto` (requires `pytest-xdist`) or run a single file.

## FAQ

**Why not use `langchain-openai` / `langchain-anthropic`?**
We deliberately keep the dependency surface small. `httpx` is enough to call
both OpenAI and Anthropic's structured-output endpoints, and lets us stub the
network in tests with `respx`.

**Why does the supervisor always run the writer and reviewer?**
The supervisor picks the *upstream* agents (research / analytics / calculator).
The writer and (when the answer is substantial) reviewer are appended by the
supervisor wrapper to guarantee a complete answer; without them, the user gets
raw data instead of a finished report.

**How do I add a new agent?**
Implement a `make_my_agent(provider, settings)` factory in `src/supervisor/agents.py`,
add its result model to `decisions.py`, wire it into `graph.py` and the
`routing_plan` heuristic in `supervisor.py`. Then add unit + integration tests.

**Can I run this in production?**
v0.1.0 is a reference implementation. The hooks for persistence (checkpoint
store), streaming, and async execution are in place, but you should add
observability (OpenTelemetry), a real secret store, and rate limiting before
shipping.

---

## Benchmarks

```text
$ uv run python examples/benchmark.py
'What is 17 x 32?'                             reported=   8.37ms  wall=  50.20ms
'Compute 100 / 4'                              reported=   5.15ms  wall=  43.08ms
'Research solar vs wind'                       reported= 156.13ms  wall= 183.78ms
'Explain transformer attention'                reported= 157.63ms  wall= 185.97ms
'What is 2 to the power of 10?'                reported= 156.45ms  wall= 186.52ms
median=183.8ms  p95=186.0ms  max=186.5ms
```

Real-model latencies are dominated by the LLM. With a 1k-token draft, expect
~2-4s end-to-end on GPT-4o-mini or Claude Haiku.

---

## Roadmap

See [`docs/Roadmap.md`](docs/Roadmap.md). Highlights:

- v0.2 - streaming, async, OpenTelemetry, persistent checkpoint store.
- v0.3 - tool-use agents (web search, code execution).
- v0.4 - multi-tenant quotas, rate limiting.
- v0.5 - production hardening (auth, audit log, secrets backend).

---

## Contributing

1. Fork and branch.
2. `uv sync --all-extras --dev`
3. Make your change.
4. `make ci` - runs ruff, black, mypy, pytest with coverage gate.
5. PR with a conventional-commit title.

## Security

Do not commit secrets. Use a `.env` file (gitignored) for local development and
your CI/secret store for shared environments.

## Status

`v0.2.0` - public reference implementation. See
[`CHANGELOG.md`](CHANGELOG.md) and [`docs/Roadmap.md`](docs/Roadmap.md).

## License

MIT. See [`LICENSE`](LICENSE).
