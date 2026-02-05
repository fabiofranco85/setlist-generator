"""Data loading utilities for songs and history.

.. deprecated::
    The functions in this module are deprecated. Use the repository pattern instead:

    >>> from library import get_repositories
    >>> repos = get_repositories()
    >>> songs = repos.songs.get_all()
    >>> history = repos.history.get_all()

The ``parse_tags()`` function is NOT deprecated as it remains useful for parsing
tag strings in various contexts.
"""

import csv
import json
import re
import warnings
from pathlib import Path
from typing import Dict

from .config import DEFAULT_WEIGHT, DEFAULT_ENERGY
from .models import Song


def parse_tags(tags_str: str) -> dict[str, int]:
    """
    Parse tags string into dict of {moment: weight}.
    Supports formats: 'louvor', 'louvor(5)', 'louvor,prelúdio(3)'
    """
    if not tags_str.strip():
        return {}

    tags = {}
    for tag in tags_str.split(","):
        tag = tag.strip()
        if not tag:
            continue

        # Check for weight in parentheses: tag(weight)
        match = re.match(r"^(.+?)\((\d+)\)$", tag)
        if match:
            moment = match.group(1).strip()
            weight = int(match.group(2))
        else:
            moment = tag
            weight = DEFAULT_WEIGHT

        tags[moment] = weight

    return tags


def load_songs(base_path: Path) -> dict[str, Song]:
    """
    Load songs from database.csv and their content from chords/*.md files.

    .. deprecated::
        Use ``get_repositories().songs.get_all()`` instead:

        >>> from library import get_repositories
        >>> repos = get_repositories(base_path=base_path)
        >>> songs = repos.songs.get_all()

    Args:
        base_path: Project root directory

    Returns:
        Dictionary mapping song titles to Song objects
    """
    warnings.warn(
        "load_songs() is deprecated. Use get_repositories().songs.get_all() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    songs = {}
    tags_file = base_path / "database.csv"
    chords_path = base_path / "chords"

    with open(tags_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            title = row["song"]

            # Parse energy (default if missing or invalid)
            energy_str = row.get("energy", "").strip()
            try:
                energy = float(energy_str) if energy_str else DEFAULT_ENERGY
            except ValueError:
                energy = DEFAULT_ENERGY

            # Parse tags
            tags = parse_tags(row["tags"])

            # Load song content from chords folder
            song_file = chords_path / f"{title}.md"
            content = ""
            if song_file.exists():
                with open(song_file, "r", encoding="utf-8") as sf:
                    content = sf.read()

            # Parse YouTube URL (optional column)
            youtube_url = (row.get("youtube") or "").strip()

            songs[title] = Song(
                title=title,
                tags=tags,
                energy=energy,
                content=content,
                youtube_url=youtube_url,
            )

    return songs


def load_history(setlists_path: Path) -> list[dict]:
    """
    Load setlist history from JSON files.

    .. deprecated::
        Use ``get_repositories().history.get_all()`` instead:

        >>> from library import get_repositories
        >>> repos = get_repositories(history_dir=setlists_path)
        >>> history = repos.history.get_all()

    Args:
        setlists_path: Path to history directory (e.g., Path("./history"))

    Returns:
        List of historical setlists sorted by date (most recent first)
    """
    warnings.warn(
        "load_history() is deprecated. Use get_repositories().history.get_all() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    history = []

    if not setlists_path.exists():
        return history

    for file in setlists_path.glob("*.json"):
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            history.append(data)

    # Sort by date, most recent first
    history.sort(key=lambda x: x.get("date", ""), reverse=True)
    return history
