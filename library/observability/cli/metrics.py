"""CLI metrics — lightweight in-memory counters, gauges, and timers."""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Iterator


def _make_key(name: str, **labels: Any) -> str:
    """Encode labels into the metric key: ``name[k1=v1,k2=v2]``."""
    if not labels:
        return name
    parts = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
    return f"{name}[{parts}]"


class CliMetrics:
    """In-memory metrics collector for CLI commands."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}
        self._gauges: dict[str, float] = {}
        self._timers: dict[str, list[float]] = {}

    def counter(self, name: str, value: int = 1, **labels: Any) -> None:
        key = _make_key(name, **labels)
        self._counters[key] = self._counters.get(key, 0) + value

    def gauge(self, name: str, value: float, **labels: Any) -> None:
        key = _make_key(name, **labels)
        self._gauges[key] = value

    @contextmanager
    def timer(self, name: str, **labels: Any) -> Iterator[None]:
        key = _make_key(name, **labels)
        start = time.perf_counter()
        try:
            yield None
        finally:
            elapsed = time.perf_counter() - start
            self._timers.setdefault(key, []).append(elapsed)

    def get_summary(self) -> dict[str, Any]:
        """Return a structured summary of all recorded metrics."""
        summary: dict[str, Any] = {}
        if self._counters:
            summary["counters"] = dict(self._counters)
        if self._gauges:
            summary["gauges"] = dict(self._gauges)
        if self._timers:
            summary["timers"] = {}
            for key, durations in self._timers.items():
                total = sum(durations)
                summary["timers"][key] = {
                    "count": len(durations),
                    "total": total,
                    "avg": total / len(durations),
                }
        return summary
