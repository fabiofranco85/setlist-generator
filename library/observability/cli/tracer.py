"""CLI tracer — logs span events through the LoggerPort."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from ..protocols import LoggerPort


class CliSpan:
    """A span that accumulates attributes and logs them on close."""

    def __init__(self, name: str, attributes: dict[str, Any]) -> None:
        self.name = name
        self.attributes = dict(attributes)

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value


class CliTracer:
    """Traces span start/end events via an injected :class:`LoggerPort`."""

    def __init__(self, logger: LoggerPort) -> None:
        self._logger = logger
        self._depth = 0

    @contextmanager
    def span(self, name: str, **attributes: Any) -> Iterator[CliSpan]:
        s = CliSpan(name, attributes)
        indent = "  " * self._depth
        self._logger.debug(f"{indent}[span:start] {name}", **attributes)
        self._depth += 1
        try:
            yield s
        except Exception as exc:
            s.set_attribute("error", str(exc))
            # Merge attributes manually to avoid kwarg collision
            merged = {**s.attributes, "error": str(exc)}
            self._logger.error(f"{indent}[span:error] {name}", **merged)
            raise
        finally:
            self._depth -= 1
            self._logger.debug(f"{indent}[span:end] {name}", **s.attributes)
