---
paths:
  - "library/observability/**/*.py"
---

# Observability Layer

Structured logging, metrics, and tracing for the setlist generator.

## Architecture

Follows the same **ports-and-adapters** pattern as `library/repositories/`:

- **Ports** (`protocols.py`): `LoggerPort`, `MetricsPort`, `TracerPort`, `Span`
- **Noop adapter** (`noop.py`): Zero-cost null objects for tests and non-instrumented paths
- **CLI adapter** (`cli/`): Human-readable stderr output for terminal use
- **Container** (`container.py`): `Observability` dataclass bundles all three ports

## Key Conventions

### Always use noop defaults
Every function/class that accepts `obs` must default to `Observability.noop()`:
```python
def my_function(data, obs=None):
    from library.observability import Observability as _Obs
    obs = obs or _Obs.noop()
```

### Instrument at boundaries, not in pure functions
- Instrument orchestrators (`generator.py`, `replacer.py`) and CLI commands
- Leave pure algorithms (`selector.py`, `ordering.py`, `transposer.py`) uninstrumented
- Callers log the context; callees stay pure

### Structured kwargs for context
```python
obs.logger.info("Generating setlist", date=date, songs=len(songs))
obs.metrics.counter("setlists_generated")
with obs.metrics.timer("generate_duration"):
    ...
with obs.tracer.span("generate_setlist", date=date):
    ...
```

### Log levels
- **DEBUG**: Detailed step-by-step (moment generated, span start/end)
- **INFO**: Key lifecycle events (generation started/completed, replacement done)
- **WARNING**: Recoverable issues
- **ERROR**: Failures

## Adding a New Backend

1. Create a new subpackage (e.g., `library/observability/otel/`)
2. Implement `LoggerPort`, `MetricsPort`, `TracerPort` protocols
3. Add a factory method to `Observability` (e.g., `for_otel()`)
4. Wire it from the CLI or application entry point

## CLI Integration

- `--verbose` / `-v` flag on the CLI group switches log level from WARNING to DEBUG
- Verbose flag is passed from `cli/main.py` → command `run()` functions
- Metrics summary printed to stderr at end of command when verbose
