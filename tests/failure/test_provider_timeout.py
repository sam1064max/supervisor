"""Failure test: provider unavailability is handled gracefully."""

from __future__ import annotations

from supervisor.config import Settings
from supervisor.providers import ProviderUnavailable
from supervisor.supervisor import plan_decision


class TestProviderTimeout:
    def test_supervisor_falls_back(self, test_settings: Settings) -> None:
        class TimeoutProvider:
            def complete(self, *args, **kwargs):
                raise ProviderUnavailable("connection timeout")

        decision = plan_decision("What is 17 x 32?", TimeoutProvider(), test_settings)
        # Heuristic kicks in
        assert "calculator" in decision.selected_agents

    def test_keyerror_also_falls_back(self, test_settings: Settings) -> None:
        class WeirdProvider:
            def complete(self, *args, **kwargs):
                raise KeyError("missing")

        decision = plan_decision("What is 17 x 32?", WeirdProvider(), test_settings)
        assert "calculator" in decision.selected_agents
