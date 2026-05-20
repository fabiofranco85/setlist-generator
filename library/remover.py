"""
Song and moment removal logic for generated setlists.

This module provides functions to remove songs or entire moments from
already-generated setlists. Removal is purely structural — no recency
recalculation, no energy reordering, no selection algorithm. Two
contracts:

* ``remove_song_from_setlist`` drops one song at ``(moment, position)``.
  If that song was the *only* one in its moment, the moment itself is
  dropped from the setlist — empty moments are not allowed in stored
  setlists (they round-trip oddly through JSONB and clutter outputs).
* ``remove_moment_from_setlist`` drops every song in a moment plus the
  moment key.

Both functions return a new setlist dict (immutable input pattern,
matching ``replacer.replace_song_in_setlist``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .observability import Observability


def remove_song_from_setlist(
    setlist_dict: dict[str, Any],
    moment: str,
    position: int,
    obs: Observability | None = None,
) -> dict[str, Any]:
    """Remove the song at ``(moment, position)``.

    If the removed song was the last one in its moment, the moment is
    also dropped from the returned setlist — empty moments are not a
    valid stored state.

    Args:
        setlist_dict: Source setlist (not mutated)
        moment: Moment to remove the song from. Must exist in the
            setlist's ``moments`` dict — validation is against the
            setlist contents, not against any moments_config, because the
            user is operating on what's actually there.
        position: Zero-indexed position to remove. Must be in range for
            the moment's current song list.
        obs: Observability container (defaults to noop).

    Returns:
        New setlist dict with the song removed (and the moment dropped
        if it became empty).

    Raises:
        ValueError: If ``moment`` is not in the setlist or ``position``
            is out of range. Errors include enough context to action.
    """
    from .observability import Observability as _Obs

    obs = obs or _Obs.noop()

    moments_in_setlist = setlist_dict.get("moments", {})
    if moment not in moments_in_setlist:
        available = ", ".join(moments_in_setlist.keys()) or "(none)"
        raise ValueError(
            f"Moment '{moment}' is not in this setlist. "
            f"Available moments: {available}"
        )

    moment_songs = moments_in_setlist[moment]
    if position < 0 or position >= len(moment_songs):
        raise ValueError(
            f"Position {position + 1} out of range. "
            f"Moment '{moment}' has {len(moment_songs)} song(s) "
            f"(1-{len(moment_songs)})"
        )

    removed_song = moment_songs[position]
    moment_emptied = len(moment_songs) == 1

    obs.logger.info(
        "Removing song",
        moment=moment,
        position=position,
        song=removed_song,
        moment_emptied=moment_emptied,
    )

    new_setlist = _shallow_copy_setlist_dict(setlist_dict)

    if moment_emptied:
        # Drop the moment entirely — stored setlists don't carry empty
        # moments, matching how the generator never produces them.
        del new_setlist["moments"][moment]
    else:
        new_list = list(moment_songs)
        del new_list[position]
        new_setlist["moments"][moment] = new_list

    obs.metrics.counter("songs_removed")
    if moment_emptied:
        obs.metrics.counter("moments_dropped_after_last_song_removed")

    return new_setlist


def remove_moment_from_setlist(
    setlist_dict: dict[str, Any],
    moment: str,
    obs: Observability | None = None,
) -> dict[str, Any]:
    """Remove an entire moment (all its songs + the moment key itself).

    Args:
        setlist_dict: Source setlist (not mutated)
        moment: Moment slug to remove. Must exist in the setlist.
        obs: Observability container (defaults to noop).

    Returns:
        New setlist dict with the moment removed.

    Raises:
        ValueError: If the moment is not present in the setlist.
    """
    from .observability import Observability as _Obs

    obs = obs or _Obs.noop()

    moments_in_setlist = setlist_dict.get("moments", {})
    if moment not in moments_in_setlist:
        available = ", ".join(moments_in_setlist.keys()) or "(none)"
        raise ValueError(
            f"Moment '{moment}' is not in this setlist. "
            f"Available moments: {available}"
        )

    song_count = len(moments_in_setlist[moment])
    obs.logger.info("Removing moment", moment=moment, song_count=song_count)

    new_setlist = _shallow_copy_setlist_dict(setlist_dict)
    del new_setlist["moments"][moment]

    obs.metrics.counter("moments_removed")
    obs.metrics.counter("songs_removed", value=song_count)

    return new_setlist


def _shallow_copy_setlist_dict(setlist_dict: dict[str, Any]) -> dict[str, Any]:
    """Build a new setlist dict preserving date / label / event_type.

    Moments are copied one level deep (the dict is fresh, each song-list
    inside it is a fresh list) so callers can mutate them safely. The
    moment iteration order from the input is preserved — re-canonicalizing
    here would silently overwrite the event type's user-defined order
    (matches the contract documented in
    ``replacer.replace_song_in_setlist``).
    """
    new_setlist: dict[str, Any] = {
        "date": setlist_dict["date"],
        "moments": {m: list(songs) for m, songs in setlist_dict["moments"].items()},
    }
    if setlist_dict.get("label"):
        new_setlist["label"] = setlist_dict["label"]
    if setlist_dict.get("event_type"):
        new_setlist["event_type"] = setlist_dict["event_type"]
    return new_setlist
