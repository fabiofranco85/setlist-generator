"""Shell completion functions for songbook CLI.

This module provides completion functions for Click's built-in shell completion system.
Completions are dynamically generated from:
- Song names (database.csv)
- Moment names (config.MOMENTS_CONFIG)
- Available dates (history/*.json files)
- Musical key names (for transposition commands)

All functions gracefully handle errors by returning empty lists rather than raising exceptions.
"""

from pathlib import Path
from typing import List
import click
from click.shell_completion import CompletionItem


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
    """Complete dates from history/*.json files.

    Args:
        ctx: Click context object
        param: Click parameter object
        incomplete: Partial input from user

    Returns:
        List of CompletionItem objects matching the incomplete input.
        Dates are sorted in descending order (most recent first).
        Returns empty list on errors (e.g., missing history directory).

    Example:
        Input: "2025-" -> Returns: ["2025-12-25", "2025-12-18", ...]
        Input: "2025-12" -> Returns: ["2025-12-25", "2025-12-18", ...]
    """
    try:
        # Get history-dir from context if available
        history_dir = None
        output_dir = None
        if ctx and ctx.params:
            history_dir = ctx.params.get('history_dir')
            output_dir = ctx.params.get('output_dir')

        # Resolve using CLI utilities (respects --history-dir and env vars)
        from cli.cli_utils import resolve_paths
        paths = resolve_paths(output_dir, history_dir)
        history_path = paths.history_dir

        # Find all JSON files in history directory
        if not history_path.exists():
            return []

        json_files = list(history_path.glob("*.json"))

        # Extract YYYY-MM-DD from filenames
        dates = []
        for json_file in json_files:
            # Expected format: YYYY-MM-DD.json
            date_str = json_file.stem
            # Basic validation: should be 10 characters (YYYY-MM-DD)
            if len(date_str) == 10 and date_str.count('-') == 2:
                dates.append(date_str)

        # Sort descending (most recent first)
        dates.sort(reverse=True)

        # Filter by incomplete input
        matching_dates = [
            date for date in dates
            if date.startswith(incomplete)
        ]

        # Return as CompletionItem objects
        return [CompletionItem(date) for date in matching_dates]

    except Exception:
        # Gracefully return empty list on any error
        # (e.g., missing history directory, permission errors)
        return []
