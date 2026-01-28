"""Core setlist generation logic."""

from typing import Dict

from .config import MOMENTS_CONFIG
from .models import Song, Setlist
from .ordering import apply_energy_ordering
from .selector import calculate_recency_scores, select_songs_for_moment


def generate_setlist(
    songs: dict[str, Song],
    history: list[dict],
    date: str,
    overrides: dict[str, list[str]] | None = None
) -> Setlist:
    """
    Generate a complete setlist for all moments.

    Args:
        songs: Dictionary of available songs
        history: List of historical setlists
        date: Date for this setlist
        overrides: Optional manual song overrides per moment

    Returns:
        Setlist object with selected songs
    """
    recency_scores = calculate_recency_scores(songs, history)
    already_selected = set()
    moments = {}

    for moment, count in MOMENTS_CONFIG.items():
        moment_overrides = overrides.get(moment) if overrides else None
        override_count = len(moment_overrides) if moment_overrides else 0

        selected_with_energy = select_songs_for_moment(
            moment, count, songs, recency_scores, already_selected, moment_overrides
        )

        # Apply energy-based ordering (preserves override order)
        ordered_songs = apply_energy_ordering(moment, selected_with_energy, override_count)
        moments[moment] = ordered_songs

    return Setlist(date=date, moments=moments)
