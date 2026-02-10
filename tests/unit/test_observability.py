"""Unit tests for noop observability implementations and protocol compliance."""

from library.observability import (
    Observability,
    NullLogger,
    NullMetrics,
    NullTracer,
    NullSpan,
    LoggerPort,
    MetricsPort,
    TracerPort,
    Span,
)


# ---------------------------------------------------------------------------
# Protocol compliance (isinstance checks on @runtime_checkable protocols)
# ---------------------------------------------------------------------------


class TestProtocolCompliance:
    def test_null_logger_satisfies_logger_port(self):
        assert isinstance(NullLogger(), LoggerPort)

    def test_null_metrics_satisfies_metrics_port(self):
        assert isinstance(NullMetrics(), MetricsPort)

    def test_null_tracer_satisfies_tracer_port(self):
        assert isinstance(NullTracer(), TracerPort)

    def test_null_span_satisfies_span(self):
        assert isinstance(NullSpan(), Span)


# ---------------------------------------------------------------------------
# NullLogger
# ---------------------------------------------------------------------------


class TestNullLogger:
    def test_all_levels_are_noop(self):
        logger = NullLogger()
        # Should not raise
        logger.debug("msg", key="val")
        logger.info("msg", key="val")
        logger.warning("msg", key="val")
        logger.error("msg", key="val")

    def test_bind_yields_self(self):
        logger = NullLogger()
        with logger.bind(request_id="abc") as bound:
            assert bound is logger


# ---------------------------------------------------------------------------
# NullMetrics
# ---------------------------------------------------------------------------


class TestNullMetrics:
    def test_counter_is_noop(self):
        m = NullMetrics()
        m.counter("test", 5, label="x")

    def test_gauge_is_noop(self):
        m = NullMetrics()
        m.gauge("test", 1.5, label="x")

    def test_timer_context_manager(self):
        m = NullMetrics()
        with m.timer("test") as t:
            assert t is None

    def test_get_summary_returns_empty(self):
        m = NullMetrics()
        m.counter("x")
        assert m.get_summary() == {}


# ---------------------------------------------------------------------------
# NullTracer
# ---------------------------------------------------------------------------


class TestNullTracer:
    def test_span_yields_null_span(self):
        tracer = NullTracer()
        with tracer.span("op", key="val") as s:
            assert isinstance(s, NullSpan)
            s.set_attribute("foo", "bar")  # should not raise


# ---------------------------------------------------------------------------
# Observability.noop() factory
# ---------------------------------------------------------------------------


class TestObservabilityNoop:
    def test_noop_returns_container_with_null_implementations(self):
        obs = Observability.noop()
        assert isinstance(obs.logger, NullLogger)
        assert isinstance(obs.metrics, NullMetrics)
        assert isinstance(obs.tracer, NullTracer)

    def test_noop_is_fully_usable(self):
        """Verify a full instrumentation sequence works with noop."""
        obs = Observability.noop()
        obs.logger.info("Starting", date="2026-01-01")
        obs.metrics.counter("things")
        with obs.metrics.timer("duration"):
            with obs.tracer.span("work") as s:
                s.set_attribute("result", 42)
        summary = obs.metrics.get_summary()
        assert summary == {}
