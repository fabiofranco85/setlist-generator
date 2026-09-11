"""
Song insertion logic for generated setlists.

The mirror of :mod:`library.remover`. Insertion is purely structural: no
recency recalculation, no energy reordering, no selection algorithm. The
song lands exactly where the caller asks, because a caller naming both the
song and the slot has already made both decisions (the same reasoning that
makes ``replace --with`` skip energy ordering).

One contract:

* ``add_song_to_setlist`` puts a song into ``moment`` at ``position``,
  appending when no position is given. A moment the setlist does not have
  yet is created, mirroring the way ``remove_song_from_setlist`` drops a
  moment whose last song goes.

Returns a new setlist dict (immutable input pattern, matching
``remover.remove_song_from_setlist``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .observability import Observability


def add_song_to_setlist(
    setlist_dict: dict[str, Any],
    moment: str,
    song: str,
    position: int | None = None,
    obs: Observability | None = None,
) -> dict[str, Any]:
    """Insert ``song`` into ``moment``.

    Args:
        setlist_dict: Source setlist (not mutated).
        moment: Moment to insert into. Created when the setlist does not
            have it yet, so a moment removed by mistake can be rebuilt.
        song: Song title. Validation that it exists in the repertoire is
            the caller's job: this module only knows about setlist shape.
        position: Zero-indexed slot the song should occupy, matching
            ``remove_song_from_setlist``. ``None`` appends. Valid values
            run from 0 to the moment's current length (that last one being
            the same as appending).
        obs: Observability container (defaults to noop).

    Returns:
        New setlist dict with the song inserted.

    Raises:
        ValueError: If ``position`` is out of range, or the song is already
            somewhere in this setlist. Errors carry enough context to act on.
    """
    from .observability import Observability as _Obs

    obs = obs or _Obs.noop()

    moments_in_setlist = setlist_dict.get("moments", {})

    # A song may appear only once per setlist: the generator guarantees it,
    # and replacement/selection both rely on it when building exclusion sets.
    for existing_moment, songs_in_moment in moments_in_setlist.items():
        if song in songs_in_moment:
            raise ValueError(
                f"'{song}' is already in this setlist, in moment "
                f"'{existing_moment}'. Remove it first, or use "
                f"'songbook replace' to swap it."
            )

    moment_songs = moments_in_setlist.get(moment, [])
    creates_moment = moment not in moments_in_setlist

    if position is None:
        position = len(moment_songs)
    elif position < 0 or position > len(moment_songs):
        # The upper bound is inclusive: inserting *at* the length appends.
        raise ValueError(
            f"Position {position + 1} out of range. "
            f"Moment '{moment}' has {len(moment_songs)} song(s), so a new "
            f"song can go at 1-{len(moment_songs) + 1}"
        )

    obs.logger.info(
        "Inserting song",
        moment=moment,
        position=position,
        song=song,
        moment_created=creates_moment,
    )

    new_setlist = _shallow_copy_setlist_dict(setlist_dict)
    new_list = list(moment_songs)
    new_list.insert(position, song)
    new_setlist["moments"][moment] = new_list

    obs.metrics.counter("songs_inserted")
    if creates_moment:
        obs.metrics.counter("moments_created_by_insert")

    return new_setlist


def _shallow_copy_setlist_dict(setlist_dict: dict[str, Any]) -> dict[str, Any]:
    """Build a new setlist dict preserving date / label / event_type.

    Moments are copied one level deep so callers can mutate them safely.
    The input's moment order is preserved rather than re-canonicalized, the
    same contract ``remover`` and ``replacer`` document: the caller owns
    moment ordering (an event type's moments_order), not this module.
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
