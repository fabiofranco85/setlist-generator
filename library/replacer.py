"""
Song replacement logic for generated setlists.

This module provides functions to replace songs in already-generated setlists,
either automatically (using the selection algorithm) or manually (user-specified).
"""

from typing import Any

from .config import ENERGY_ORDERING_ENABLED, ENERGY_ORDERING_RULES, MOMENTS_CONFIG
from .models import Song
from .ordering import apply_energy_ordering
from .selector import calculate_recency_scores, select_songs_for_moment


def find_target_setlist(
    history: list[dict[str, Any]],
    target_date: str | None = None
) -> dict[str, Any]:
    """
    Find the setlist to modify.

    Args:
        history: List of all historical setlists (sorted by date, most recent first)
        target_date: Specific date (YYYY-MM-DD), or None for latest

    Returns:
        Setlist dict: {"date": "...", "moments": {...}}

    Raises:
        ValueError: If date not found or no history exists
    """
    if not history:
        raise ValueError("No setlists found in history")

    if target_date is None:
        return history[0]  # Already sorted by date (most recent first)

    for setlist in history:
        if setlist.get("date") == target_date:
            return setlist

    raise ValueError(f"Setlist for date {target_date} not found")


def validate_replacement_request(
    setlist: dict[str, Any],
    moment: str,
    position: int,
    replacement_song: str | None,
    songs: dict[str, Song]
) -> None:
    """
    Validate the replacement request.

    Args:
        setlist: Target setlist dict
        moment: Service moment
        position: Position to replace (0-indexed)
        replacement_song: Manual replacement song, or None for auto
        songs: All available songs

    Raises:
        ValueError: If validation fails with descriptive message
    """
    # Validate moment exists
    if moment not in MOMENTS_CONFIG:
        valid = ", ".join(MOMENTS_CONFIG.keys())
        raise ValueError(f"Invalid moment '{moment}'. Valid: {valid}")

    # Validate position
    moment_songs = setlist["moments"].get(moment, [])
    if not moment_songs:
        raise ValueError(f"No songs found in moment '{moment}'")

    if position < 0 or position >= len(moment_songs):
        raise ValueError(
            f"Position {position} out of range. "
            f"Moment '{moment}' has {len(moment_songs)} song(s) (0-{len(moment_songs)-1})"
        )

    # Validate manual replacement song exists
    if replacement_song is not None:
        if replacement_song not in songs:
            raise ValueError(f"Song '{replacement_song}' not found in database")

        # Validate song has the required moment tag
        song = songs[replacement_song]
        if not song.has_moment(moment):
            raise ValueError(
                f"Song '{replacement_song}' is not tagged for moment '{moment}'"
            )


def select_replacement_song(
    moment: str,
    setlist: dict[str, Any],
    position: int,
    songs: dict[str, Song],
    history: list[dict[str, Any]],
    manual_replacement: str | None = None
) -> str:
    """
    Select a replacement song (auto or manual mode).

    Args:
        moment: Service moment
        setlist: Current setlist dict
        position: Position being replaced (0-indexed)
        songs: All available songs
        history: Historical setlists for recency calculation
        manual_replacement: User-specified song, or None for auto

    Returns:
        Song title to use as replacement

    Raises:
        ValueError: If no suitable replacement found
    """
    # Manual mode: validate and return
    if manual_replacement is not None:
        validate_replacement_request(
            setlist, moment, position, manual_replacement, songs
        )
        return manual_replacement

    # Auto mode: use selection algorithm

    # Build exclusion set: all songs EXCEPT the one being replaced
    exclusion_set = set()
    moment_songs = setlist["moments"][moment]
    song_to_replace = moment_songs[position]

    for moment_name, song_list in setlist["moments"].items():
        for song in song_list:
            if song != song_to_replace:  # Exclude everything EXCEPT replacement target
                exclusion_set.add(song)

    # Calculate recency scores for the target date
    recency_scores = calculate_recency_scores(
        songs=songs,
        history=history,
        current_date=setlist["date"]
    )

    # Select 1 replacement song
    selected = select_songs_for_moment(
        moment=moment,
        count=1,
        songs=songs,
        recency_scores=recency_scores,
        already_selected=exclusion_set,
        overrides=None
    )

    if not selected:
        raise ValueError(
            f"No available replacement songs for moment '{moment}'. "
            f"All eligible songs may already be in the setlist."
        )

    return selected[0][0]  # Return title (first element of first tuple)


def replace_song_in_setlist(
    setlist_dict: dict[str, Any],
    moment: str,
    position: int,
    replacement_song: str,
    songs: dict[str, Song],
    reorder_energy: bool = True
) -> dict[str, Any]:
    """
    Replace a song and optionally reorder by energy.

    Args:
        setlist_dict: Original setlist dict
        moment: Service moment
        position: Position to replace (0-indexed)
        replacement_song: New song title
        songs: All available songs
        reorder_energy: Whether to reapply energy ordering

    Returns:
        Updated setlist dict (new copy, original unchanged)
    """
    # Create a copy to avoid mutating original
    new_setlist = {
        "date": setlist_dict["date"],
        "moments": {}
    }

    # Copy all moments
    for m, song_list in setlist_dict["moments"].items():
        new_setlist["moments"][m] = song_list.copy()

    # Replace the song at the specified position
    moment_songs = new_setlist["moments"][moment]
    moment_songs[position] = replacement_song

    # Optionally reorder by energy
    if reorder_energy:
        if ENERGY_ORDERING_ENABLED and moment in ENERGY_ORDERING_RULES:
            # Reconstruct (title, energy) tuples
            selected_with_energy = [
                (title, songs[title].energy)
                for title in moment_songs
            ]

            # Reorder (treat all as auto-selected, no overrides)
            ordered_songs = apply_energy_ordering(
                moment=moment,
                selected_songs=selected_with_energy,
                override_count=0
            )

            new_setlist["moments"][moment] = ordered_songs

    return new_setlist


def replace_songs_batch(
    setlist_dict: dict[str, Any],
    replacements: list[tuple[str, int, str | None]],
    songs: dict[str, Song],
    history: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Replace multiple songs at once.

    Args:
        setlist_dict: Original setlist
        replacements: List of (moment, position, manual_song)
            manual_song can be None for auto-selection
        songs: All available songs
        history: Historical setlists

    Returns:
        Updated setlist dict (new copy, original unchanged)

    Raises:
        ValueError: If any replacement is invalid
    """
    # Validate all replacements first
    for moment, position, manual_song in replacements:
        validate_replacement_request(
            setlist_dict, moment, position, manual_song, songs
        )

    # Build exclusion set for auto-selections
    # Start with all songs in setlist EXCEPT those being replaced
    exclusion_set = set()
    replacement_positions = {
        (moment, position) for moment, position, _ in replacements
    }

    for moment_name, song_list in setlist_dict["moments"].items():
        for idx, song in enumerate(song_list):
            if (moment_name, idx) not in replacement_positions:
                exclusion_set.add(song)

    # Select replacements for each position
    final_replacements = []
    recency_scores = None  # Calculate once, reuse

    for moment, position, manual_song in replacements:
        if manual_song is not None:
            # Manual mode
            replacement = manual_song
        else:
            # Auto mode
            if recency_scores is None:
                recency_scores = calculate_recency_scores(
                    songs=songs,
                    history=history,
                    current_date=setlist_dict["date"]
                )

            selected = select_songs_for_moment(
                moment=moment,
                count=1,
                songs=songs,
                recency_scores=recency_scores,
                already_selected=exclusion_set.copy(),
                overrides=None
            )

            if not selected:
                raise ValueError(f"No replacement found for {moment} position {position}")

            replacement = selected[0][0]
            exclusion_set.add(replacement)  # Prevent reuse in batch

        final_replacements.append((moment, position, replacement))

    # Apply all replacements
    new_setlist = {
        "date": setlist_dict["date"],
        "moments": {}
    }

    for m, song_list in setlist_dict["moments"].items():
        new_setlist["moments"][m] = song_list.copy()

    for moment, position, replacement in final_replacements:
        new_setlist["moments"][moment][position] = replacement

    # Reorder each affected moment by energy
    affected_moments = {moment for moment, _, _ in replacements}

    for moment in affected_moments:
        if ENERGY_ORDERING_ENABLED and moment in ENERGY_ORDERING_RULES:
            moment_songs = new_setlist["moments"][moment]
            selected_with_energy = [
                (title, songs[title].energy)
                for title in moment_songs
            ]
            ordered = apply_energy_ordering(
                moment=moment,
                selected_songs=selected_with_energy,
                override_count=0
            )
            new_setlist["moments"][moment] = ordered

    return new_setlist
