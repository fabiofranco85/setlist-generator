"""Observability facade — bundles logger, metrics, and tracer.

Mirrors the ``RepositoryContainer`` pattern: a single object that is
threaded through the call-stack so every layer can emit telemetry without
importing concrete backends.
"""

from __future__ import annotations

from dataclasses import dataclass

from .noop import NullLogger, NullMetrics, NullTracer
from .protocols import LoggerPort, MetricsPort, TracerPort


@dataclass
class Observability:
    """Container for all observability ports."""

    logger: LoggerPort
    metrics: MetricsPort
    tracer: TracerPort

    @classmethod
    def noop(cls) -> Observability:
        """Create a silent observability container (for tests and non-instrumented paths)."""
        return cls(
            logger=NullLogger(),
            metrics=NullMetrics(),
            tracer=NullTracer(),
        )

    @classmethod
    def for_cli(cls, level: str = "WARNING") -> Observability:
        """Create a CLI-appropriate observability container.

        Args:
            level: Log level name (e.g. "DEBUG", "WARNING").
        """
        from .cli import CliLogger, CliMetrics, CliTracer

        logger = CliLogger(level=level)
        metrics = CliMetrics()
        tracer = CliTracer(logger=logger)
        return cls(logger=logger, metrics=metrics, tracer=tracer)
