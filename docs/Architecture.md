# Architecture

## Purpose

This document describes the architecture of the **Supervisor Agent**, a
production-grade reference implementation of the *Supervisor Pattern* for
multi-agent LLM systems.

The Supervisor is an orchestrator. It does not perform business logic. It
determines:

1. Which specialist agents should participate.
2. In what order they should execute.
3. Whether execution can be parallelised.
4. Whether additional work is required.
5. Whether the final answer is sufficient.

## High-level topology

```mermaid
flowchart TD
    A[User Request] --> B[Input Guardrail]
    B -->|safe| C[Supervisor Planner]
    B -->|unsafe| Z[Reject + Log]
    C -->|decision| D{Parallel fan-out}
    D -->|branch 1| E1[Research Agent]
    D -->|branch 2| E2[Analytics Agent]
    D -->|branch 3| E3[Calculator Agent]
    E1 --> F[Reducer]
    E2 --> F
    E3 --> F
    F --> G[Writer Agent]
    G --> H[Reviewer Agent]
    H -->|insufficient| G
    H -->|sufficient| I{HITL enabled?}
    I -->|no| J[Output Guardrail]
    I -->|yes| K[Human Checkpoint]
    K -->|approve| J
    K -->|reject| G
    J -->|safe| L[Final Answer]
    J -->|unsafe| Z
```

## Components

| Component | Responsibility | Owns state? |
|---|---|---|
| `Input Guardrail` | Validate user input. Reject empty, oversized, or unsafe prompts. Emits structured reject reason. | No |
| `Supervisor` | Decide which agents run, in what order, in parallel or sequence. Produce `SupervisorDecision`. | Reads only |
| `Research Agent` | Information gathering, retrieval, search, fact collection. | Appends to `research_results` |
| `Analytics Agent` | KPI calculations, aggregations, metrics. | Appends to `analytics_results` |
| `Calculator Agent` | Mathematical evaluation via a safe AST-based tool. Never uses `eval()`. | Appends to `calculation_results` |
| `Writer Agent` | Produce draft report from upstream results. | Writes `report` |
| `Reviewer Agent` | Evaluate quality, completeness, consistency. Bounded reflection loop. | Writes `review_feedback`, increments `review_cycle` |
| `Output Guardrail` | Validate final answer length, content, structure before returning. | No |
| `Human Checkpoint` | Optional `interrupt`/`resume` for HITL approval. | Reads context, awaits command |
| `Recovery` | Per-agent retry, exponential backoff, fallback, escalation. | Counts `retries` |

## Layered view

```mermaid
flowchart LR
    subgraph Edge
        CLI[CLI - typer]
        LIB[Library API]
    end
    subgraph Application
        RUN[run_supervisor]
        GRAPH[StateGraph]
    end
    subgraph Domain
        STATE[AgentState]
        DEC[SupervisorDecision]
        AGENTS[Specialist Agents]
    end
    subgraph Infrastructure
        LLM[LLM Provider]
        LOG[Structured Logger]
        CONF[Settings]
    end
    CLI --> RUN
    LIB --> RUN
    RUN --> GRAPH
    GRAPH --> STATE
    GRAPH --> AGENTS
    GRAPH --> DEC
    AGENTS --> LLM
    GRAPH --> LOG
    RUN --> CONF
```

## Dependencies

Production:

| Package | Purpose | Justification |
|---|---|---|
| `langgraph` | Graph runtime, `Send`, `interrupt` | Project-defining dependency. No equivalent stdlib alternative. |
| `pydantic` >=2 | Typed state, structured outputs, settings | Industry standard. Used by LangGraph itself. |
| `pydantic-settings` | Externalised configuration | First-party companion to `pydantic`. |
| `httpx` | OpenAI / Anthropic HTTP calls | Already a transitive dependency of LangChain. |
| `typer` | CLI | Built on `click`, type-annotated, low ceremony. |
| `rich` | Pretty console output for CLI | Stdlib `print` is insufficient for tabular agent output. |
| `structlog` | Structured JSON logging | De-facto standard for JSON logs in Python. |
| `python-dotenv` | `.env` loading for local dev | Tiny, ubiquitous, no replacement. |

Test-only:

| Package | Purpose | Justification |
|---|---|---|
| `pytest` | Test runner | Standard. |
| `pytest-asyncio` | Async graph execution | Required for LangGraph async API. |
| `pytest-cov` | Coverage reporting | Standard. |
| `respx` | Mock `httpx` for provider tests | Lighter than spinning up a wiremock server. |
| `freezegun` | Deterministic time in reflection tests | Tiny. |

Lint / type:

| Package | Purpose |
|---|---|
| `ruff` | Linter + formatter |
| `black` | Formatter (kept for compatibility with ecosystem) |
| `mypy` | Static type checker |

## State transitions

`AgentState` is a `TypedDict` with reducer functions. The graph mutates a
single instance throughout execution; LangGraph persists it via the configured
checkpointer.

```mermaid
stateDiagram-v2
    [*] --> InputGuardrail
    InputGuardrail --> Rejected: invalid
    InputGuardrail --> Planned: valid
    Planned --> Research
    Planned --> Analytics
    Planned --> Calculator
    Planned --> DirectWrite: simple math
    Research --> Writer
    Analytics --> Writer
    Calculator --> Writer
    DirectWrite --> Reviewer
    Writer --> Reviewer
    Reviewer --> Writer: insufficient
    Reviewer --> HumanCheckpoint: sufficient + HITL
    Reviewer --> OutputGuardrail: sufficient + no HITL
    HumanCheckpoint --> Writer: rejected
    HumanCheckpoint --> OutputGuardrail: approved
    OutputGuardrail --> [*]
    Rejected --> [*]
```

## Failure modes

| Mode | Detection | Recovery |
|---|---|---|
| Invalid input | Input guardrail regex/length check | Return `Rejected` with reason. No graph crash. |
| Specialist exception | Node try/except wrapper | Retry up to `agent_max_retries`. Fallback agent if configured. Escalate to safe error message. |
| Provider timeout | `httpx` `TimeoutException` | Exponential backoff. If exhausted, raise `ProviderUnavailable` and fall back to the `fake` provider if `allow_degradation=true`. |
| Malformed structured output | Pydantic `ValidationError` on `SupervisorDecision` | One re-prompt. On second failure, use a deterministic heuristic router. |
| Reflection divergence | `review_cycle > max_review_cycles` | Accept current draft, mark with `review_status=forced_complete`, log warning. |
| Human never responds | Checkpoint timeout | Configurable; default = 30 minutes. After timeout, fall back to non-HITL path. |

## Recovery strategies

* **Retry with backoff** at the agent level.
* **Degradation** by falling back from a paid provider to the offline `fake`
  provider when configured.
* **Bounded reflection** prevents infinite Writer/Reviewer loops.
* **Hard guardrails** at input and output keep the system from emitting unsafe
  or unbounded content.
* **Observability**: every failure emits a structured log record with
  `trace_id`, `request_id`, `agent`, `attempt`, `duration_ms`, `error_class`.

## Out of scope (v0.1.0)

* Persistent checkpoints across processes (MemorySaver only).
* Web search tools (Research agent operates on a static corpus for the
  reference implementation; pluggable interface defined).
* Multi-tenant isolation.
* Streaming token output (final answer only).

See [`docs/Roadmap.md`](Roadmap.md) for the next-step plan.
