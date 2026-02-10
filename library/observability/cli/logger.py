"""CLI logger — structured key=value output via stdlib logging."""

from __future__ import annotations

import logging
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

_bound_context: ContextVar[dict[str, Any]] = ContextVar("_bound_context", default={})


class _KeyValueFormatter(logging.Formatter):
    """Format log records as: ``LEVEL    message  key1=val1 key2=val2``."""

    def format(self, record: logging.LogRecord) -> str:
        level = record.levelname.ljust(8)
        message = record.getMessage()

        extra_pairs: dict[str, Any] = getattr(record, "structured_context", {})
        if extra_pairs:
            kv = "  ".join(f"{k}={v}" for k, v in extra_pairs.items())
            return f"{level}{message}  {kv}"
        return f"{level}{message}"


class CliLogger:
    """Structured logger backed by stdlib :mod:`logging`.

    Outputs to **stderr** so it never interferes with regular command output.
    """

    def __init__(self, *, level: str = "WARNING", name: str = "songbook") -> None:
        self._logger = logging.getLogger(name)
        self._logger.setLevel(getattr(logging, level.upper(), logging.WARNING))
        self._logger.propagate = False

        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(_KeyValueFormatter())
            self._logger.addHandler(handler)

    def _emit(self, level: int, message: str, **context: Any) -> None:
        if not self._logger.isEnabledFor(level):
            return
        merged = {**_bound_context.get(), **context}
        record = self._logger.makeRecord(
            self._logger.name,
            level,
            "(observability)",
            0,
            message,
            (),
            None,
        )
        record.structured_context = merged  # type: ignore[attr-defined]
        self._logger.handle(record)

    def debug(self, message: str, **context: Any) -> None:
        self._emit(logging.DEBUG, message, **context)

    def info(self, message: str, **context: Any) -> None:
        self._emit(logging.INFO, message, **context)

    def warning(self, message: str, **context: Any) -> None:
        self._emit(logging.WARNING, message, **context)

    def error(self, message: str, **context: Any) -> None:
        self._emit(logging.ERROR, message, **context)

    @contextmanager
    def bind(self, **context: Any) -> Iterator[CliLogger]:
        """Yield a logger with extra context fields merged in."""
        token = _bound_context.set({**_bound_context.get(), **context})
        try:
            yield self
        finally:
            _bound_context.reset(token)
