"""Song selection algorithms based on weights, recency, and randomness."""

import random
from typing import Dict, Set

from .config import RECENCY_PENALTY_PERFORMANCES, DEFAULT_ENERGY
from .models import Song


def calculate_recency_scores(
    songs: dict[str, Song],
    history: list[dict]
) -> dict[str, float]:
    """
    Calculate the recency score for each song.
    Higher score = longer since last used = better candidate.

    Returns: {song_title: recency_score}
    """
    scores = {}

    # Initialize all songs with max score (never used)
    for title in songs:
        scores[title] = 1.0

    # Penalize recently used songs
    for i, setlist in enumerate(history[:RECENCY_PENALTY_PERFORMANCES]):
        penalty_factor = 1 - ((RECENCY_PENALTY_PERFORMANCES - i) / RECENCY_PENALTY_PERFORMANCES)

        # Get all songs from this setlist
        for moment, song_list in setlist.get("moments", {}).items():
            for song in song_list:
                if song in scores:
                    # Apply penalty (more recent = lower score)
                    scores[song] = min(scores[song], penalty_factor)

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
