"""Unit tests for the structured logging layer."""

from __future__ import annotations

import json

import pytest

from supervisor.logging_setup import (
    bind_request_context,
    configure_logging,
    get_logger,
    new_trace_id,
    timed,
)


class TestConfigureLogging:
    def test_idempotent(self, test_settings) -> None:
        configure_logging(test_settings)
        configure_logging(test_settings)
        # No error means success.

    def test_json_emits_valid_json(self, test_settings, capsys) -> None:
        test_settings.log_level = "INFO"
        configure_logging(test_settings)
        log = get_logger("test_json")
        log.info("hello", foo="bar")
        captured = capsys.readouterr()
        assert "hello" in captured.err
        for line in captured.err.strip().splitlines():
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("event") == "hello":
                assert rec.get("foo") == "bar"
                return
        pytest.fail("Did not find 'hello' record in JSON output")

    def test_console_format(self, test_settings) -> None:
        test_settings.log_level = "INFO"
        test_settings.log_format = "console"
        configure_logging(test_settings)
        log = get_logger("console_test")
        log.info("console works")


class TestBindRequestContext:
    def test_binds_ids(self) -> None:
        with bind_request_context() as ctx:
            assert ctx["request_id"]
            assert ctx["trace_id"]

    def test_overrides_ids(self) -> None:
        with bind_request_context(request_id="r1", trace_id="t1") as ctx:
            assert ctx["request_id"] == "r1"
            assert ctx["trace_id"] == "t1"

    def test_unbinds_on_exit(self) -> None:
        with bind_request_context(request_id="r1") as ctx:
            assert ctx["request_id"] == "r1"
        with bind_request_context() as ctx2:
            assert ctx2["request_id"] != "r1"


class TestNewTraceId:
    def test_returns_string(self) -> None:
        tid = new_trace_id()
        assert isinstance(tid, str)
        assert len(tid) == 32

    def test_unique(self) -> None:
        assert new_trace_id() != new_trace_id()


class TestTimed:
    def test_emits_duration(self, test_settings) -> None:
        test_settings.log_level = "INFO"
        configure_logging(test_settings)
        log = get_logger("timed_test")
        with timed(log, "test.event", x=1):
            pass

    def test_emits_on_exception(self, test_settings) -> None:
        test_settings.log_level = "INFO"
        configure_logging(test_settings)
        log = get_logger("timed_test_exc")
        with pytest.raises(RuntimeError), timed(log, "exc.event"):
            raise RuntimeError("test")
