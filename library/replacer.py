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
    from .config import GenerationConfig
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
    config: GenerationConfig | None = None,
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
    effective_moments = (
        config.moments_config if config is not None
        else moments_config if moments_config is not None
        else MOMENTS_CONFIG
    )
    # Validate moment exists
    if moment not in effective_moments:
        valid = ", ".join(effective_moments.keys())
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
    config: GenerationConfig | None = None,
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

    # Copy all moments preserving the input dict's order. The caller is the
    # source of truth for moment ordering (an event type's moments_order,
    # generate's MOMENTS_CONFIG iteration, etc.) — re-canonicalizing here
    # silently overwrites that contract.
    for m, songs_in_moment in setlist_dict["moments"].items():
        new_setlist["moments"][m] = songs_in_moment.copy()

    # Replace the song at the specified position
    moment_songs = new_setlist["moments"][moment]
    moment_songs[position] = replacement_song

    # Optionally reorder by energy
    if reorder_energy:
        eo_enabled = config.energy_ordering_enabled if config else ENERGY_ORDERING_ENABLED
        eo_rules = config.energy_ordering_rules if config else ENERGY_ORDERING_RULES
        if eo_enabled and moment in eo_rules:
            # Reconstruct (title, energy) tuples
            selected_with_energy = [
                (title, songs[title].energy)
                for title in moment_songs
            ]

            # Reorder (treat all as auto-selected, no overrides)
            ordered_songs = apply_energy_ordering(
                moment=moment,
                selected_songs=selected_with_energy,
                override_count=0,
                energy_ordering_enabled=eo_enabled,
                energy_ordering_rules=eo_rules,
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
    config: GenerationConfig | None = None,
    reorder_energy: bool = True,
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
        reorder_energy: When True (default), reapply energy ordering to each
            affected moment after replacement. Set to False to keep each new
            song at the exact requested position.

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

    # Preserve input dict's moment order — same reasoning as
    # replace_song_in_setlist: do not silently re-canonicalize.
    for m, songs_in_moment in setlist_dict["moments"].items():
        new_setlist["moments"][m] = songs_in_moment.copy()

    for moment, position, replacement in final_replacements:
        new_setlist["moments"][moment][position] = replacement

    # Reorder each affected moment by energy (skip when caller asked us to
    # keep replacements at their requested positions).
    affected_moments = {moment for moment, _, _ in replacements}

    eo_enabled = (
        reorder_energy
        and (config.energy_ordering_enabled if config else ENERGY_ORDERING_ENABLED)
    )
    eo_rules = config.energy_ordering_rules if config else ENERGY_ORDERING_RULES
    for moment in affected_moments:
        if eo_enabled and moment in eo_rules:
            moment_songs = new_setlist["moments"][moment]
            selected_with_energy = [
                (title, songs[title].energy)
                for title in moment_songs
            ]
            ordered = apply_energy_ordering(
                moment=moment,
                selected_songs=selected_with_energy,
                override_count=0,
                energy_ordering_enabled=eo_enabled,
                energy_ordering_rules=eo_rules,
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
    config: GenerationConfig | None = None,
    target_moments: dict[str, int] | None = None,
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
        config: Generation config
        target_moments: Optional target moments config ({moment: count}). When
            provided, the derived setlist's moments are projected onto this
            shape — overlapping moments carry songs from the base, missing
            moments are freshly selected, and base moments not in target are
            dropped. Output moment order follows ``target_moments.keys()``.
            This is the recommended path for the CLI/API to avoid
            cross-event-type contamination if the wrong base is picked up.

    Returns:
        New setlist dict with replaced songs (caller sets label)
    """
    import random

    # Filter songs by event type if specified
    available = filter_songs_for_event_type(songs, event_type) if event_type else songs

    base_moments = base_setlist_dict.get("moments", {})

    # Build the scaffold (moment -> list of songs) in the target's order. If
    # no target shape was supplied, fall back to the base's shape — preserves
    # backward compatibility for callers that don't yet pass target_moments.
    scaffold: dict[str, list[str]] = {}
    already_selected: set[str] = set()
    needs_fresh_fill = False

    if target_moments is not None:
        for moment, count in target_moments.items():
            from_base = base_moments.get(moment, [])
            carried = [s for s in from_base[:count] if s in available]
            already_selected.update(carried)
            scaffold[moment] = list(carried)
            if len(carried) < count:
                needs_fresh_fill = True
    else:
        for moment, song_list in base_moments.items():
            scaffold[moment] = list(song_list)

    # Fresh-fill any gaps where the scaffold has fewer songs than target wants
    # (e.g., target adds a moment the base doesn't have, or asks for more
    # songs than base supplies). Recency is calculated lazily — only if we
    # actually need to select fresh songs.
    if needs_fresh_fill:
        # needs_fresh_fill is only ever set to True inside the
        # `if target_moments is not None` branch above, so this is safe —
        # the assert exists only to satisfy static analyzers (Pyright).
        assert target_moments is not None
        decay = config.recency_decay_days if config else None
        kw = {"recency_decay_days": decay} if decay is not None else {}
        recency_scores = calculate_recency_scores(
            songs=available, history=history,
            current_date=base_setlist_dict["date"], **kw,
        )
        eo_enabled = config.energy_ordering_enabled if config else ENERGY_ORDERING_ENABLED
        eo_rules = config.energy_ordering_rules if config else ENERGY_ORDERING_RULES
        for moment, count in target_moments.items():
            needed = count - len(scaffold[moment])
            if needed <= 0:
                continue
            selected = select_songs_for_moment(
                moment, needed, available, recency_scores,
                already_selected, overrides=None,
            )
            for title, _energy in selected:
                scaffold[moment].append(title)
                already_selected.add(title)
            # Re-apply energy ordering to this moment after fresh-fill
            if eo_enabled and moment in eo_rules and scaffold[moment]:
                with_energy = [
                    (t, available[t].energy)
                    for t in scaffold[moment]
                    if t in available
                ]
                scaffold[moment] = apply_energy_ordering(
                    moment=moment,
                    selected_songs=with_energy,
                    override_count=0,
                    energy_ordering_enabled=eo_enabled,
                    energy_ordering_rules=eo_rules,
                )

    # Enumerate all (moment, position) pairs in the scaffold
    all_positions: list[tuple[str, int]] = []
    for moment_name, song_list in scaffold.items():
        for idx in range(len(song_list)):
            all_positions.append((moment_name, idx))

    total_songs = len(all_positions)
    if total_songs == 0:
        return {"date": base_setlist_dict["date"], "moments": scaffold}

    # Determine how many to replace
    if replace_count is None:
        replace_count = random.randint(1, total_songs)
    else:
        replace_count = max(0, min(replace_count, total_songs))

    if replace_count == 0:
        return {"date": base_setlist_dict["date"], "moments": scaffold}

    # Randomly sample positions to replace
    positions_to_replace = random.sample(all_positions, replace_count)
    replacements: list[tuple[str, int, str | None]] = [
        (moment, pos, None) for moment, pos in positions_to_replace
    ]

    # Hand off to replace_songs_batch for the actual replacement + energy
    # reorder. Pass the scaffold (not the raw base) so alien moments are
    # already gone and the target order is preserved.
    return replace_songs_batch(
        setlist_dict={"date": base_setlist_dict["date"], "moments": scaffold},
        replacements=replacements,
        songs=available,
        history=history,
        config=config,
    )
