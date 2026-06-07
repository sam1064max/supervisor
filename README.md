# Supervisor

> A production-grade reference implementation of the **Supervisor Pattern** for
> multi-agent LLM systems, built on [LangGraph](https://langchain-ai.github.io/langgraph/).

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

## Why this exists

Multi-agent LLM systems fail for predictable reasons:

* The orchestrator drifts into doing work it should be delegating.
* Routing is hardcoded and breaks the moment a request shape changes.
* Failures in one agent take the whole system down.
* There is no observable trace of *why* the system did what it did.

This project is the reference implementation we wished we had: typed state,
structured outputs, parallel fan-out, reflection, human checkpoints, and a
hermetic test story that does not require a network.

## Quick start

```bash
uv sync
cp .env.example .env
uv run supervisor run "What is 17 x 32?"
```

By default the system uses the offline `fake` provider, so the command above
works without an API key.

## Documentation

| Section | File |
|---|---|
| Architecture | [`docs/Architecture.md`](docs/Architecture.md) |
| Data flow | [`docs/Dataflow.md`](docs/Dataflow.md) |
| Sequence diagrams | [`docs/SequenceDiagram.md`](docs/SequenceDiagram.md) |
| Troubleshooting | [`docs/Troubleshooting.md`](docs/Troubleshooting.md) |
| Decisions | [`docs/adr/`](docs/adr) |

## Status

`v0.1.0` - public reference implementation. See [CHANGELOG](CHANGELOG.md) and
[Roadmap](docs/Roadmap.md).

## License

MIT. See [LICENSE](LICENSE).
