"""Structured JSON logging via ``structlog``.

Every log record carries a ``trace_id`` and ``request_id`` when bound via
:func:`bind_request_context`. The :func:`timed` context manager emits a
single record with ``duration_ms`` when the block exits.
"""

from __future__ import annotations

import logging
import sys
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import structlog

from supervisor.config import Settings, get_settings

_LOGGING_CONFIGURED = False


def configure_logging(settings: Settings | None = None) -> None:
    """Configure structlog + stdlib logging. Idempotent."""
    global _LOGGING_CONFIGURED
    settings = settings or get_settings()

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.log_format == "json":
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level, logging.INFO),
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=getattr(logging, settings.log_level, logging.INFO),
    )
    _LOGGING_CONFIGURED = True


def get_logger(name: str | None = None) -> Any:
    """Return a structlog logger. Configure logging on first use."""
    if not _LOGGING_CONFIGURED:
        configure_logging()
    return structlog.get_logger(name)


@contextmanager
def bind_request_context(
    request_id: str | None = None,
    trace_id: str | None = None,
    **extra: Any,
) -> Iterator[dict[str, str]]:
    """Bind ``request_id`` and ``trace_id`` to the current logging context."""
    request_id = request_id or str(uuid.uuid4())
    trace_id = trace_id or uuid.uuid4().hex
    keys = ["request_id", "trace_id", *extra.keys()]
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        trace_id=trace_id,
        **extra,
    )
    try:
        yield {"request_id": request_id, "trace_id": trace_id}
    finally:
        structlog.contextvars.unbind_contextvars(*keys)


def new_trace_id() -> str:
    """Mint a fresh trace id."""
    return uuid.uuid4().hex


@contextmanager
def timed(logger: Any, event: str, **fields: Any) -> Iterator[None]:
    """Emit ``event`` with ``duration_ms`` when the block exits."""
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(event, duration_ms=round(duration_ms, 3), **fields)
