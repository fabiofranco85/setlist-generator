"""Observability protocol definitions (ports).

Defines the abstract interfaces for logging, metrics, and tracing.
Implementations live in subpackages (cli/, noop.py). Using Protocol
enables structural subtyping — any class that implements the required
methods satisfies the protocol without explicit inheritance.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Span(Protocol):
    """A tracing span that can accumulate attributes."""

    def set_attribute(self, key: str, value: Any) -> None: ...


@runtime_checkable
class LoggerPort(Protocol):
    """Structured logger with contextual binding."""

    def debug(self, message: str, **context: Any) -> None: ...
    def info(self, message: str, **context: Any) -> None: ...
    def warning(self, message: str, **context: Any) -> None: ...
    def error(self, message: str, **context: Any) -> None: ...
    def bind(self, **context: Any) -> AbstractContextManager[LoggerPort]: ...


@runtime_checkable
class MetricsPort(Protocol):
    """Metrics collection with counters, gauges, and timers."""

    def counter(self, name: str, value: int = 1, **labels: Any) -> None: ...
    def gauge(self, name: str, value: float, **labels: Any) -> None: ...
    def timer(self, name: str, **labels: Any) -> AbstractContextManager[None]: ...
    def get_summary(self) -> dict[str, Any]: ...


@runtime_checkable
class TracerPort(Protocol):
    """Distributed-tracing-style span creation."""

    def span(self, name: str, **attributes: Any) -> AbstractContextManager[Span]: ...
