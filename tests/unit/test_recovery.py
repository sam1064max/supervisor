"""Unit tests for the retry wrapper."""

from __future__ import annotations

from supervisor.recovery import with_retries


def test_succeeds_first_try() -> None:
    calls = {"n": 0}

    def node(state):
        calls["n"] += 1
        return {"metadata": {"x": 1}}

    wrapped = with_retries(node, agent_name="x", max_retries=2)
    delta = wrapped({})
    assert calls["n"] == 1
    assert delta["metadata"]["x"] == 1
    assert delta["metadata"]["retries"]["x"] == 0


def test_succeeds_after_retry() -> None:
    calls = {"n": 0}

    def node(state):
        calls["n"] += 1
        if calls["n"] < 2:
            raise ValueError("boom")
        return {"metadata": {"x": 2}}

    wrapped = with_retries(node, agent_name="x", max_retries=2)
    delta = wrapped({})
    assert calls["n"] == 2
    assert delta["metadata"]["retries"]["x"] == 1


def test_exhausts_retries() -> None:
    def node(state):
        raise RuntimeError("always fails")

    wrapped = with_retries(node, agent_name="x", max_retries=1)
    delta = wrapped({})
    assert delta["error"] == "x_failed"
    assert "always fails" in delta["metadata"]["last_error"]


def test_zero_retries_fails_immediately() -> None:
    def node(state):
        raise ValueError("nope")

    wrapped = with_retries(node, agent_name="x", max_retries=0)
    delta = wrapped({})
    assert delta["error"] == "x_failed"
    assert delta["metadata"]["retries"]["x"] == 1


def test_preserves_existing_metadata() -> None:
    def node(state):
        return {"metadata": {"foo": "bar"}}

    wrapped = with_retries(node, agent_name="x", max_retries=0)
    delta = wrapped({})
    assert delta["metadata"]["foo"] == "bar"
    assert delta["metadata"]["retries"]["x"] == 0


def test_existing_metadata_wins_over_retries() -> None:
    """When the node returns a metadata dict, the wrapper augments it with
    the retry count but preserves all other keys."""

    def node(state):
        return {"metadata": {"retries": {"preexisting": 99}}}

    wrapped = with_retries(node, agent_name="x", max_retries=0)
    delta = wrapped({})
    assert delta["metadata"]["retries"]["preexisting"] == 99
    assert delta["metadata"]["retries"]["x"] == 0
