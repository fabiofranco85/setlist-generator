"""Shell completion functions for songbook CLI.

This module provides completion functions for Click's built-in shell completion system.
Completions are dynamically generated from:
- Song names (the active storage backend)
- Moment names (config.MOMENTS_CONFIG)
- Available dates and labels (setlist history in the active storage backend)
- Event type slugs (the active storage backend)
- Musical key names (for transposition commands)

Everything data-driven goes through the repository layer rather than reading files
directly, so completion follows STORAGE_BACKEND like the commands themselves do.

All functions gracefully handle errors by returning empty lists rather than raising
exceptions.
"""

from typing import List
from click.shell_completion import CompletionItem


def _get_repositories(ctx):
    """Build a repository container for a completion callback.

    Honors ``--history-dir`` / ``--output-dir`` when they are already parsed on
    the context, so completion looks at the same data the command would.
    Imports are deferred to keep the TAB round-trip cheap.

    Args:
        ctx: Click context object (may be None)

    Returns:
        RepositoryContainer for the active storage backend.
    """
    from cli.cli_utils import resolve_paths
    from library import get_repositories

    history_dir = None
    output_dir = None
    if ctx is not None and ctx.params:
        history_dir = ctx.params.get("history_dir")
        output_dir = ctx.params.get("output_dir")

    paths = resolve_paths(output_dir, history_dir)
    return get_repositories(history_dir=paths.history_dir, output_dir=paths.output_dir)


def complete_song_names(ctx, param, incomplete: str) -> List[CompletionItem]:
    """Complete song names from database.csv (case-insensitive).

    Args:
        ctx: Click context object
        param: Click parameter object
        incomplete: Partial input from user

    Returns:
        List of CompletionItem objects matching the incomplete input.
        Returns empty list on errors (e.g., missing database.csv).

    Example:
        Input: "oce" -> Returns: ["Oceanos"]
        Input: "OU" -> Returns: ["Ousado Amor"]
    """
    try:
        from library import get_repositories

        # Load songs via repository
        repos = get_repositories()
        songs = repos.songs.get_all()

        # Filter by incomplete input (case-insensitive)
        # songs is a dict where keys are song titles
        incomplete_lower = incomplete.lower()
        matching_songs = [
            title for title in songs.keys()
            if incomplete_lower in title.lower()
        ]

        # Sort alphabetically for consistent ordering
        matching_songs.sort()

        # Return as CompletionItem objects
        return [CompletionItem(song) for song in matching_songs]

    except Exception:
        # Gracefully return empty list on any error
        # (e.g., missing database.csv, parsing errors)
        return []


def complete_moment_names(ctx, param, incomplete: str) -> List[CompletionItem]:
    """Complete moment names from config.MOMENTS_CONFIG.

    Args:
        ctx: Click context object
        param: Click parameter object
        incomplete: Partial input from user

    Returns:
        List of CompletionItem objects matching the incomplete input.
        Returns empty list on errors.

    Example:
        Input: "lou" -> Returns: ["louvor"]
        Input: "pre" -> Returns: ["prelúdio"]
    """
    try:
        from library.config import MOMENTS_CONFIG

        # Get all moment names from config
        all_moments = list(MOMENTS_CONFIG.keys())

        # Filter by incomplete input (case-insensitive)
        incomplete_lower = incomplete.lower()
        matching_moments = [
            moment for moment in all_moments
            if incomplete_lower in moment.lower()
        ]

        # Return as CompletionItem objects
        return [CompletionItem(moment) for moment in matching_moments]

    except Exception:
        # Gracefully return empty list on any error
        return []


# All valid musical keys for transposition tab-completion
_ALL_KEYS = [
    "C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B",
    "Cm", "C#m", "Dm", "D#m", "Ebm", "Em", "Fm", "F#m", "Gm", "G#m", "Am", "A#m", "Bbm", "Bm",
]


def complete_key_names(ctx, param, incomplete: str) -> List[CompletionItem]:
    """Complete musical key names for transposition.

    Args:
        ctx: Click context object
        param: Click parameter object
        incomplete: Partial input from user

    Returns:
        List of CompletionItem objects matching the incomplete input.

    Example:
        Input: "B" -> Returns: ["B", "Bb", "Bm", "Bbm"]
        Input: "F#" -> Returns: ["F#", "F#m"]
    """
    incomplete_lower = incomplete.lower()
    matching = [k for k in _ALL_KEYS if k.lower().startswith(incomplete_lower)]
    return [CompletionItem(k) for k in matching]


def complete_history_dates(ctx, param, incomplete: str) -> List[CompletionItem]:
    """Complete dates of stored setlists.

    Reads the setlist history through the repository layer, so it works on every
    backend. Dates of labeled setlists are offered too (the date portion only) —
    ``--label`` completes separately.

    Args:
        ctx: Click context object
        param: Click parameter object
        incomplete: Partial input from user

    Returns:
        List of CompletionItem objects matching the incomplete input.
        Dates are sorted in descending order (most recent first).
        Returns empty list on errors (e.g., unreachable database).

    Example:
        Input: "2026-" -> Returns: ["2026-03-01", "2026-02-15", ...]
        Input: "2026-02" -> Returns: ["2026-02-15", ...]
    """
    try:
        repos = _get_repositories(ctx)

        dates = {
            entry["date"]
            for entry in repos.history.get_all()
            if entry.get("date")
        }

        # Most recent first — the date you want is nearly always a recent one
        matching = sorted(
            (date for date in dates if date.startswith(incomplete)),
            reverse=True,
        )

        return [CompletionItem(date) for date in matching]

    except Exception:
        # Gracefully return empty list on any error
        # (e.g., unreachable backend, missing DATABASE_URL)
        return []


def complete_history_labels(ctx, param, incomplete: str) -> List[CompletionItem]:
    """Complete labels of stored setlists.

    Args:
        ctx: Click context object
        param: Click parameter object
        incomplete: Partial input from user

    Returns:
        List of CompletionItem objects for known labels, alphabetically sorted.
        Returns empty list on errors.
    """
    try:
        repos = _get_repositories(ctx)

        labels = {
            entry["label"]
            for entry in repos.history.get_all()
            if entry.get("label")
        }

        matching = sorted(
            label for label in labels
            if label.startswith(incomplete.lower())
        )

        return [CompletionItem(label) for label in matching]

    except Exception:
        return []


def complete_event_type_slugs(ctx, param, incomplete: str) -> List[CompletionItem]:
    """Complete event type slugs, described by their display name.

    Args:
        ctx: Click context object
        param: Click parameter object
        incomplete: Partial input from user

    Returns:
        List of CompletionItem objects, alphabetically sorted by slug.
        Returns empty list on errors.

    Example:
        Input: "y" -> Returns: ["youth"] (described as "Youth Service")
    """
    try:
        repos = _get_repositories(ctx)

        event_types = repos.event_types.get_all()

        return [
            CompletionItem(slug, help=event_types[slug].name)
            for slug in sorted(event_types)
            if slug.startswith(incomplete.lower())
        ]

    except Exception:
        return []
