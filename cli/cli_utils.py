"""
Shared CLI utilities for songbook commands.

Provides reusable Click decorators and helper functions.
"""

import click
from functools import wraps
from pathlib import Path


def path_options(f):
    """Add --output-dir and --history-dir options to a command."""
    @click.option("--output-dir", help="Custom markdown output directory")
    @click.option("--history-dir", help="Custom history directory")
    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper


def date_option(required=False, help_text="Target date (YYYY-MM-DD)"):
    """Add --date option to a command."""
    def decorator(f):
        return click.option(
            "--date",
            required=required,
            help=help_text
        )(f)
    return decorator


def resolve_paths(output_dir, history_dir):
    """
    Resolve output paths from CLI options.

    Args:
        output_dir: Optional custom output directory
        history_dir: Optional custom history directory

    Returns:
        OutputPaths object with resolved paths
    """
    from library import get_output_paths
    return get_output_paths(
        Path("."),
        cli_output_dir=output_dir,
        cli_history_dir=history_dir
    )


def handle_error(error, exit_code=1):
    """
    Standard error handling for CLI commands.

    Args:
        error: Exception or error message
        exit_code: Exit code (default: 1)
    """
    click.secho(f"Error: {error}", fg="red", err=True)
    raise SystemExit(exit_code)


def print_metrics_summary(summary):
    """
    Print observability metrics summary to stderr.

    Args:
        summary: Dict returned by MetricsPort.get_summary()
    """
    import sys

    parts = []
    for name, value in summary.get("counters", {}).items():
        parts.append(f"{name}={value}")
    for name, data in summary.get("timers", {}).items():
        parts.append(f"{name}={data['total']:.2f}s")
    if parts:
        print(f"\n[stats] {', '.join(parts)}", file=sys.stderr)
