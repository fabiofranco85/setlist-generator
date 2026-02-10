"""Noop (null-object) implementations of the observability ports.

These are zero-cost placeholders used when no observability backend is
configured. Every method is a no-op so instrumented code can call
``obs.logger.info(...)`` without guards.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator


class NullSpan:
    """A span that silently discards attributes."""

    def set_attribute(self, key: str, value: Any) -> None:
        pass


class NullLogger:
    """A logger that silently discards all messages."""

    def debug(self, message: str, **context: Any) -> None:
        pass

    def info(self, message: str, **context: Any) -> None:
        pass

    def warning(self, message: str, **context: Any) -> None:
        pass

    def error(self, message: str, **context: Any) -> None:
        pass

    @contextmanager
    def bind(self, **context: Any) -> Iterator[NullLogger]:
        yield self


class NullMetrics:
    """A metrics collector that silently discards all data."""

    def counter(self, name: str, value: int = 1, **labels: Any) -> None:
        pass

    def gauge(self, name: str, value: float, **labels: Any) -> None:
        pass

    @contextmanager
    def timer(self, name: str, **labels: Any) -> Iterator[None]:
        yield None

    def get_summary(self) -> dict[str, Any]:
        return {}


class NullTracer:
    """A tracer that silently discards all spans."""

    @contextmanager
    def span(self, name: str, **attributes: Any) -> Iterator[NullSpan]:
        yield NullSpan()
