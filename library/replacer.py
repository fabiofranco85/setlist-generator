"""
Song replacement logic for generated setlists.

This module provides functions to replace songs in already-generated setlists,
either automatically (using the selection algorithm) or manually (user-specified).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .config import ENERGY_ORDERING_ENABLED, ENERGY_ORDERING_RULES, MOMENTS_CONFIG
from .event_type import filter_songs_for_event_type
from .models import Song
from .ordering import apply_energy_ordering
from .selector import calculate_recency_scores, select_songs_for_moment

if TYPE_CHECKING:
    from .observability import Observability


def find_target_setlist(
    history: list[dict[str, Any]],
    target_date: str | None = None,
    target_label: str = "",
    event_type: str = "",
) -> dict[str, Any]:
    """
    Find the setlist to modify.

    Args:
        history: List of all historical setlists (sorted by date, most recent first)
        target_date: Specific date (YYYY-MM-DD), or None for latest
        target_label: Optional label for multiple setlists per date
        event_type: Optional event type slug to filter by

    Returns:
        Setlist dict: {"date": "...", "moments": {...}}

    Raises:
        ValueError: If date/label/event_type not found or no history exists
    """
    if not history:
        raise ValueError("No setlists found in history")

    if target_date is None:
        # Filter by event_type if specified
        if event_type:
            for setlist in history:
                if setlist.get("event_type", "") == event_type:
                    return setlist
            raise ValueError(f"No setlists found for event type '{event_type}'")
        return history[0]  # Already sorted by date (most recent first)

    for setlist in history:
        if (setlist.get("date") == target_date
                and setlist.get("label", "") == target_label
                and setlist.get("event_type", "") == event_type):
            return setlist

    label_suffix = f" (label: {target_label})" if target_label else ""
    type_suffix = f" (event type: {event_type})" if event_type else ""
    raise ValueError(f"Setlist for date {target_date}{label_suffix}{type_suffix} not found")


def validate_replacement_request(
    setlist: dict[str, Any],
    moment: str,
    position: int,
    replacement_song: str | None,
    songs: dict[str, Song],
    moments_config: dict[str, int] | None = None,
) -> None:
    """
    Validate the replacement request.

    Args:
        setlist: Target setlist dict
        moment: Service moment
        position: Position to replace (0-indexed)
        replacement_song: Manual replacement song, or None for auto
        songs: All available songs
        moments_config: Optional moments config (defaults to MOMENTS_CONFIG)

    Raises:
        ValueError: If validation fails with descriptive message
    """
    config = moments_config or MOMENTS_CONFIG
    # Validate moment exists
    if moment not in config:
        valid = ", ".join(config.keys())
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
    reorder_energy: bool = True,
    obs: Observability | None = None,
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
        obs: Observability container (defaults to noop)

    Returns:
        Updated setlist dict (new copy, original unchanged)
    """
    from .observability import Observability as _Obs

    obs = obs or _Obs.noop()
    old_song = setlist_dict["moments"][moment][position]
    obs.logger.info(
        "Replacing song",
        moment=moment,
        position=position,
        old=old_song,
        new=replacement_song,
    )

    # Create a copy to avoid mutating original
    new_setlist = {
        "date": setlist_dict["date"],
        "moments": {},
    }
    if setlist_dict.get("label"):
        new_setlist["label"] = setlist_dict["label"]
    if setlist_dict.get("event_type"):
        new_setlist["event_type"] = setlist_dict["event_type"]

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

    obs.metrics.counter("songs_replaced")
    return new_setlist


def replace_songs_batch(
    setlist_dict: dict[str, Any],
    replacements: list[tuple[str, int, str | None]],
    songs: dict[str, Song],
    history: list[dict[str, Any]],
    obs: Observability | None = None,
) -> dict[str, Any]:
    """
    Replace multiple songs at once.

    Args:
        setlist_dict: Original setlist
        replacements: List of (moment, position, manual_song)
            manual_song can be None for auto-selection
        songs: All available songs
        history: Historical setlists
        obs: Observability container (defaults to noop)

    Returns:
        Updated setlist dict (new copy, original unchanged)

    Raises:
        ValueError: If any replacement is invalid
    """
    from .observability import Observability as _Obs

    obs = obs or _Obs.noop()
    obs.logger.info("Batch replacing songs", count=len(replacements))
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
        "moments": {},
    }
    if setlist_dict.get("label"):
        new_setlist["label"] = setlist_dict["label"]
    if setlist_dict.get("event_type"):
        new_setlist["event_type"] = setlist_dict["event_type"]

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

    obs.metrics.counter("songs_replaced", value=len(replacements))
    return new_setlist


def derive_setlist(
    base_setlist_dict: dict[str, Any],
    songs: dict[str, Song],
    history: list[dict[str, Any]],
    replace_count: int | None = None,
    event_type: str = "",
) -> dict[str, Any]:
    """
    Derive a new setlist by replacing songs from a base setlist.

    Creates a variant of the base setlist by randomly selecting positions
    to replace and using the existing replacement algorithm for auto-selection.

    Args:
        base_setlist_dict: The primary setlist to derive from
        songs: All available songs
        history: Historical setlists for recency
        replace_count: Number of songs to replace.
            None = random (1 to total_songs).
        event_type: Optional event type slug for song filtering

    Returns:
        New setlist dict with replaced songs (caller sets label)
    """
    import random

    # Filter songs by event type if specified
    available = filter_songs_for_event_type(songs, event_type) if event_type else songs

    # Enumerate all (moment, position) pairs
    all_positions = []
    for moment_name, song_list in base_setlist_dict["moments"].items():
        for idx in range(len(song_list)):
            all_positions.append((moment_name, idx))

    total_songs = len(all_positions)
    if total_songs == 0:
        return dict(base_setlist_dict)

    # Determine how many to replace
    if replace_count is None:
        replace_count = random.randint(1, total_songs)
    else:
        replace_count = max(0, min(replace_count, total_songs))

    if replace_count == 0:
        # Copy exactly (no changes)
        new_setlist = {
            "date": base_setlist_dict["date"],
            "moments": {},
        }
        for m, sl in base_setlist_dict["moments"].items():
            new_setlist["moments"][m] = sl.copy()
        return new_setlist

    # Randomly sample positions to replace
    positions_to_replace = random.sample(all_positions, replace_count)

    # Build replacements list (all auto-selection)
    replacements: list[tuple[str, int, str | None]] = [
        (moment, pos, None)
        for moment, pos in positions_to_replace
    ]

    # Use replace_songs_batch for the actual replacement
    return replace_songs_batch(
        setlist_dict=base_setlist_dict,
        replacements=replacements,
        songs=available,
        history=history,
    )
