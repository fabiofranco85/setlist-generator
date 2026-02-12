"""
Shared CLI utilities for songbook commands.

Provides reusable Click decorators and helper functions.
"""

import re

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


_LABEL_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def validate_label(label: str) -> str:
    """Validate and normalize a setlist label.

    Labels must be lowercase alphanumeric with hyphens/underscores,
    starting with a letter or digit, max 30 characters.

    Args:
        label: Label string to validate

    Returns:
        Validated label string

    Raises:
        SystemExit: If label is invalid
    """
    if not label:
        return ""

    label = label.strip().lower()

    if len(label) > 30:
        handle_error("Label must be at most 30 characters")

    if not _LABEL_PATTERN.match(label):
        handle_error(
            f"Invalid label '{label}'. "
            "Labels must start with a letter or digit and contain only "
            "lowercase letters, digits, hyphens, and underscores."
        )

    return label


def find_setlist_or_fail(repos, date, label=""):
    """Find a setlist by date and label, or exit with error.

    Provides helpful error messages listing available dates/labels.

    Args:
        repos: RepositoryContainer with history access
        date: Target date (YYYY-MM-DD) or None for latest
        label: Optional label for multiple setlists per date

    Returns:
        Setlist dictionary

    Raises:
        SystemExit: If setlist not found
    """
    if date:
        setlist = repos.history.get_by_date(date, label=label)
        if setlist:
            return setlist

        # Not found — provide helpful message
        all_for_date = repos.history.get_by_date_all(date)
        if all_for_date and label:
            available_labels = [s.get("label", "") or "(unlabeled)" for s in all_for_date]
            handle_error(
                f"No setlist found for {date} with label '{label}'.\n"
                f"Available labels for {date}: {', '.join(available_labels)}"
            )
        elif not all_for_date:
            history = repos.history.get_all()
            dates = [s["date"] for s in history[:10]]
            handle_error(
                f"No setlist found for date: {date}\n"
                f"Available dates: {', '.join(dates) if dates else '(none)'}"
            )
        else:
            # Found unlabeled but user asked for label
            handle_error(
                f"No setlist found for {date} with label '{label}'.\n"
                f"An unlabeled setlist exists for {date}."
            )
    else:
        # Latest
        history = repos.history.get_all()
        if not history:
            handle_error("No setlists found in history")
        # If label specified, filter
        if label:
            for entry in history:
                if entry.get("label", "") == label:
                    return entry
            handle_error(f"No setlist found with label '{label}'")
        return history[0]
