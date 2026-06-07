"""Typer CLI. Subcommands: ``run``, ``plan``, ``agents``.

The CLI is a thin shell over the library API. There is no test-mode branch
in the application code; the offline ``FakeProvider`` is the default.
"""

from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from supervisor.config import get_settings
from supervisor.decisions import ALL_AGENT_NAMES
from supervisor.logging_setup import configure_logging, get_logger
from supervisor.providers import build_provider
from supervisor.runner import Supervisor
from supervisor.supervisor import plan_decision

app = typer.Typer(
    name="supervisor",
    help="Supervisor agent CLI.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()
logger = get_logger(__name__)


_RESPONSIBILITIES: dict[str, str] = {
    "research": "Information gathering, retrieval, fact collection",
    "analytics": "KPI calculations, aggregations, metrics",
    "calculator": "Safe mathematical evaluation (AST-based, no eval())",
    "writer": "Draft reports and final prose",
    "reviewer": "Quality validation and reflection",
}


@app.command()
def run(
    query: str = typer.Argument(..., help="The user request to route and execute."),
    json_output: bool = typer.Option(False, "--json", help="Emit the result as JSON."),
) -> None:
    """Run the Supervisor end-to-end on a single query."""
    settings = get_settings()
    configure_logging(settings)
    sup = Supervisor(settings=settings)
    result = sup.run(query)
    if json_output:
        typer.echo(
            json.dumps(
                {
                    "final_answer": result.final_answer,
                    "trace_id": result.trace_id,
                    "request_id": result.request_id,
                    "duration_ms": result.duration_ms,
                    "error": result.error,
                    "rejection_reason": result.rejection_reason,
                    "awaiting_human": result.awaiting_human,
                },
                indent=2,
            )
        )
        return
    if result.error:
        console.print(
            Panel(
                f"[red]Error:[/red] {result.error}\n"
                f"[yellow]Reason:[/yellow] {result.rejection_reason or '-'}",
                title="Supervisor",
            )
        )
        raise typer.Exit(code=1)
    console.print(Panel(result.final_answer, title="Answer", border_style="green"))
    console.print(
        f"[dim]trace_id={result.trace_id}  request_id={result.request_id}  "
        f"duration_ms={result.duration_ms:.1f}[/dim]"
    )


@app.command()
def plan(
    query: str = typer.Argument(..., help="The query to plan (no execution)."),
) -> None:
    """Show the Supervisor's plan for a query without running the agents."""
    settings = get_settings()
    configure_logging(settings)
    provider = build_provider(settings)
    decision = plan_decision(query, provider, settings)
    table = Table(title="Supervisor Plan")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Selected agents", ", ".join(decision.selected_agents))
    table.add_row("Execution order", " -> ".join(decision.execution_order) or "(none)")
    table.add_row("Parallel?", "yes" if decision.requires_parallel_execution else "no")
    table.add_row("Reasoning", decision.reasoning)
    console.print(table)


@app.command()
def agents() -> None:
    """List the available specialist agents."""
    table = Table(title="Specialist Agents")
    table.add_column("Name", style="cyan")
    table.add_column("Responsibility", style="white")
    for name in ALL_AGENT_NAMES:
        table.add_row(name, _RESPONSIBILITIES.get(name, ""))
    console.print(table)


if __name__ == "__main__":  # pragma: no cover
    app()
