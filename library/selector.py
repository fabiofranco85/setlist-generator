"""Song selection algorithms based on weights, recency, and randomness."""

import random
from datetime import datetime, date
from math import exp
from typing import Dict, Set

from .config import RECENCY_DECAY_DAYS, DEFAULT_ENERGY
from .models import Song


def calculate_recency_scores(
    songs: dict[str, Song],
    history: list[dict],
    current_date: str | None = None
) -> dict[str, float]:
    """
    Calculate recency scores using time-based exponential decay.

    Songs get higher scores the longer it's been since they were last used.
    Score formula: 1.0 - exp(-days_since_last_use / DECAY_CONSTANT)

    Args:
        songs: Dictionary of all available songs
        history: List of historical setlists (sorted by date, most recent first)
        current_date: Current date for calculation (defaults to today, format: YYYY-MM-DD)

    Returns:
        Dictionary mapping song titles to recency scores (0.0-1.0)
    """
    # Parse current date
    if current_date is None:
        today = date.today()
    else:
        today = datetime.strptime(current_date, "%Y-%m-%d").date()

    # Initialize all songs with maximum score (never used)
    scores = {title: 1.0 for title in songs}

    # Track last use date for each song
    last_used = {}  # {song_title: date_object}

    # Scan all history files to find last use of each song
    for setlist in history:  # Already sorted by date (most recent first)
        setlist_date_str = setlist.get("date")
        if not setlist_date_str:
            continue

        try:
            setlist_date = datetime.strptime(setlist_date_str, "%Y-%m-%d").date()
        except ValueError:
            continue  # Skip malformed dates

        # Collect songs from this setlist
        for moment, song_list in setlist.get("moments", {}).items():
            for song in song_list:
                if song in scores and song not in last_used:
                    # Record first (most recent) occurrence
                    last_used[song] = setlist_date

    # Calculate decay-based scores
    for song, last_date in last_used.items():
        days_since = (today - last_date).days

        # Exponential decay formula
        # Score approaches 1.0 as days_since increases
        # RECENCY_DECAY_DAYS controls the decay rate
        if days_since <= 0:
            # Same day or future date (shouldn't happen, but handle gracefully)
            scores[song] = 0.0
        else:
            decay_factor = exp(-days_since / RECENCY_DECAY_DAYS)
            scores[song] = 1.0 - decay_factor

    return scores


def select_songs_for_moment(
    moment: str,
    count: int,
    songs: dict[str, Song],
    recency_scores: dict[str, float],
    already_selected: Set[str],
    overrides: list[str] | None = None
) -> list[tuple[str, float]]:
    """
    Select songs for a specific moment.
    Returns list of (title, energy) tuples.
    """
    selected = []

    # Handle overrides first
    if overrides:
        for song in overrides:
            if song in songs and song not in already_selected:
                energy = songs[song].energy
                selected.append((song, energy))
                already_selected.add(song)

        if len(selected) >= count:
            return selected[:count]

    # Get candidate songs for this moment
    candidates = []
    for title, song in songs.items():
        if title in already_selected:
            continue
        if not song.has_moment(moment):
            continue

        weight = song.get_weight(moment)
        recency = recency_scores.get(title, 1.0)

        # Combined score: weight * recency
        # This prioritizes high-weight songs that haven't been used recently
        score = weight * (recency + 0.1)  # +0.1 to avoid zero scores
        candidates.append((title, score))

    # Sort by score (descending) with some randomization
    # Add small random factor to avoid always picking the same songs
    candidates.sort(key=lambda x: x[1] + random.uniform(0, 0.5), reverse=True)

    # Select remaining needed songs
    for title, _ in candidates:
        if len(selected) >= count:
            break
        energy = songs[title].energy
        selected.append((title, energy))
        already_selected.add(title)

    return selected
