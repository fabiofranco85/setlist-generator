"""Unit tests for CLI observability backends."""

import logging
import time

from library.observability import Observability, LoggerPort, MetricsPort, TracerPort, Span
from library.observability.cli import CliLogger, CliMetrics, CliTracer
from library.observability.cli.tracer import CliSpan


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------


class TestCliProtocolCompliance:
    def test_cli_logger_satisfies_logger_port(self):
        assert isinstance(CliLogger(level="DEBUG"), LoggerPort)

    def test_cli_metrics_satisfies_metrics_port(self):
        assert isinstance(CliMetrics(), MetricsPort)

    def test_cli_tracer_satisfies_tracer_port(self):
        logger = CliLogger(level="DEBUG")
        assert isinstance(CliTracer(logger=logger), TracerPort)

    def test_cli_span_satisfies_span(self):
        assert isinstance(CliSpan("test", {}), Span)


# ---------------------------------------------------------------------------
# CliLogger
# ---------------------------------------------------------------------------


class TestCliLogger:
    def test_debug_message_format(self, capsys):
        logger = CliLogger(level="DEBUG", name="test_debug_fmt")
        logger.debug("hello world", key="val")
        captured = capsys.readouterr()
        assert "DEBUG" in captured.err
        assert "hello world" in captured.err
        assert "key=val" in captured.err

    def test_level_filtering(self, capsys):
        logger = CliLogger(level="WARNING", name="test_level_filter")
        logger.debug("should not appear")
        logger.info("should not appear")
        logger.warning("should appear")
        captured = capsys.readouterr()
        assert "should not appear" not in captured.err
        assert "should appear" in captured.err

    def test_bind_adds_context(self, capsys):
        logger = CliLogger(level="DEBUG", name="test_bind")
        with logger.bind(request_id="abc"):
            logger.debug("bound message")
        captured = capsys.readouterr()
        assert "request_id=abc" in captured.err
        assert "bound message" in captured.err

    def test_bind_context_is_scoped(self, capsys):
        logger = CliLogger(level="DEBUG", name="test_bind_scope")
        with logger.bind(ctx="inner"):
            pass
        logger.debug("after bind")
        captured = capsys.readouterr()
        assert "ctx=inner" not in captured.err.split("after bind")[-1]

    def test_no_stdout_pollution(self, capsys):
        logger = CliLogger(level="DEBUG", name="test_no_stdout")
        logger.info("test message", foo="bar")
        captured = capsys.readouterr()
        assert captured.out == ""


# ---------------------------------------------------------------------------
# CliMetrics
# ---------------------------------------------------------------------------


class TestCliMetrics:
    def test_counter_increments(self):
        m = CliMetrics()
        m.counter("requests")
        m.counter("requests")
        m.counter("requests", value=3)
        summary = m.get_summary()
        assert summary["counters"]["requests"] == 5

    def test_counter_with_labels(self):
        m = CliMetrics()
        m.counter("http", method="GET")
        m.counter("http", method="POST")
        m.counter("http", method="GET")
        summary = m.get_summary()
        assert summary["counters"]["http[method=GET]"] == 2
        assert summary["counters"]["http[method=POST]"] == 1

    def test_gauge_records_latest(self):
        m = CliMetrics()
        m.gauge("temperature", 20.0)
        m.gauge("temperature", 25.5)
        summary = m.get_summary()
        assert summary["gauges"]["temperature"] == 25.5

    def test_timer_records_duration(self):
        m = CliMetrics()
        with m.timer("op"):
            time.sleep(0.01)
        summary = m.get_summary()
        timer_data = summary["timers"]["op"]
        assert timer_data["count"] == 1
        assert timer_data["total"] >= 0.005  # at least ~5ms
        assert timer_data["avg"] == timer_data["total"]

    def test_multiple_timers_accumulate(self):
        m = CliMetrics()
        with m.timer("op"):
            pass
        with m.timer("op"):
            pass
        summary = m.get_summary()
        assert summary["timers"]["op"]["count"] == 2

    def test_empty_summary(self):
        m = CliMetrics()
        assert m.get_summary() == {}


# ---------------------------------------------------------------------------
# CliTracer
# ---------------------------------------------------------------------------


class TestCliTracer:
    def test_span_yields_cli_span(self):
        logger = CliLogger(level="DEBUG", name="test_tracer_span")
        tracer = CliTracer(logger=logger)
        with tracer.span("operation", key="val") as s:
            assert isinstance(s, CliSpan)
            assert s.name == "operation"
            assert s.attributes["key"] == "val"

    def test_span_set_attribute(self):
        logger = CliLogger(level="DEBUG", name="test_tracer_attr")
        tracer = CliTracer(logger=logger)
        with tracer.span("op") as s:
            s.set_attribute("result", 42)
            assert s.attributes["result"] == 42

    def test_span_logs_start_and_end(self, capsys):
        logger = CliLogger(level="DEBUG", name="test_tracer_log")
        tracer = CliTracer(logger=logger)
        with tracer.span("my_operation"):
            pass
        captured = capsys.readouterr()
        assert "[span:start] my_operation" in captured.err
        assert "[span:end] my_operation" in captured.err

    def test_span_logs_error_on_exception(self, capsys):
        logger = CliLogger(level="DEBUG", name="test_tracer_err")
        tracer = CliTracer(logger=logger)
        try:
            with tracer.span("failing_op"):
                raise ValueError("boom")
        except ValueError:
            pass
        captured = capsys.readouterr()
        assert "[span:error] failing_op" in captured.err
        assert "boom" in captured.err

    def test_nested_spans_track_depth(self, capsys):
        logger = CliLogger(level="DEBUG", name="test_tracer_depth")
        tracer = CliTracer(logger=logger)
        with tracer.span("outer"):
            with tracer.span("inner"):
                pass
        captured = capsys.readouterr()
        # Inner span should be indented relative to outer
        assert "  [span:start] inner" in captured.err


# ---------------------------------------------------------------------------
# Observability.for_cli() factory
# ---------------------------------------------------------------------------


class TestObservabilityForCli:
    def test_returns_container_with_cli_implementations(self):
        obs = Observability.for_cli(level="DEBUG")
        assert isinstance(obs.logger, CliLogger)
        assert isinstance(obs.metrics, CliMetrics)
        assert isinstance(obs.tracer, CliTracer)

    def test_default_level_is_warning(self, capsys):
        obs = Observability.for_cli()  # default level
        obs.logger.debug("should not show")
        obs.logger.info("should not show")
        captured = capsys.readouterr()
        assert captured.err == ""
