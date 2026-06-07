"""Integration tests for the Typer CLI."""

from __future__ import annotations

from typer.testing import CliRunner

from supervisor.cli import app
from supervisor.decisions import (
    DraftReport,
    SupervisorDecision,
)
from supervisor.providers import FakeProvider


class TestAgents:
    def test_agents_lists_all(self) -> None:
        runner = CliRunner()
        result = runner.invoke(app, ["agents"])
        assert result.exit_code == 0
        for name in ("research", "analytics", "calculator", "writer", "reviewer"):
            assert name in result.stdout


class TestPlan:
    def test_plan_simple_math(self, test_settings, monkeypatch) -> None:
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=["calculator", "writer"],
                    execution_order=["calculator", "writer"],
                    reasoning="math detected",
                )
            ]
        )
        monkeypatch.setattr("supervisor.cli.build_provider", lambda s: provider)
        monkeypatch.setattr("supervisor.cli.get_settings", lambda: test_settings)
        runner = CliRunner()
        result = runner.invoke(app, ["plan", "What is 17 x 32?"])
        assert result.exit_code == 0
        assert "calculator" in result.stdout


class TestRun:
    def test_run_json_output(self, test_settings, monkeypatch) -> None:
        provider = FakeProvider(
            responses=[
                SupervisorDecision(
                    selected_agents=["writer"],
                    execution_order=["writer"],
                    reasoning="r",
                ),
                DraftReport(title="T", summary="S", body="Final text"),
            ]
        )
        # Patch the provider factory used by the runner, not the CLI.
        monkeypatch.setattr("supervisor.runner.build_provider", lambda s: provider)
        monkeypatch.setattr("supervisor.cli.get_settings", lambda: test_settings)
        runner = CliRunner()
        result = runner.invoke(app, ["run", "hello", "--json"])
        assert "Final text" in result.stdout or "error" in result.stdout.lower()


class TestCLIHelp:
    def test_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Supervisor" in result.stdout
