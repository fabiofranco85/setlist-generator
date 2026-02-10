"""Observability layer — structured logging, metrics, and tracing.

Public API:
    Observability          Facade container (logger + metrics + tracer)
    LoggerPort             Logger protocol (port)
    MetricsPort            Metrics protocol (port)
    TracerPort             Tracer protocol (port)
    Span                   Tracing span protocol
    NullLogger / …         Noop implementations (for tests)
"""

from .container import Observability
from .noop import NullLogger, NullMetrics, NullSpan, NullTracer
from .protocols import LoggerPort, MetricsPort, Span, TracerPort

__all__ = [
    "Observability",
    # Protocols (ports)
    "LoggerPort",
    "MetricsPort",
    "TracerPort",
    "Span",
    # Noop implementations
    "NullLogger",
    "NullMetrics",
    "NullTracer",
    "NullSpan",
]
