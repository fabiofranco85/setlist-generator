"""Data loading utilities for songs and history."""

import csv
import json
import re
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
    Load songs from tags.csv and their content from chords/*.md files.
    Returns: {song_title: Song}
    """
    songs = {}
    tags_file = base_path / "tags.csv"
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

            songs[title] = Song(
                title=title,
                tags=tags,
                energy=energy,
                content=content
            )

    return songs


def load_history(setlists_path: Path) -> list[dict]:
    """
    Load setlist history from JSON files.

    Args:
        setlists_path: Path to history directory (e.g., Path("./history"))

    Returns:
        List of historical setlists sorted by date (most recent first)
    """
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
