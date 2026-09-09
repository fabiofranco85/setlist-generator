"""Projection of a setlist's moments onto another event type's moment shape.

Backs the cross-event-type re-use in ``songbook setlists`` (the ``r`` action).
Copying a setlist to a different event type is never a straight copy: the
target type has its own moments, its own song counts, and its own song pool
(songs bound to another type are simply not eligible).

This module answers one question, as pure data: given the source's moments and
the target's shape, what carries over, what has to be dropped, and how many
empty slots are left? Filling those slots is the caller's job. The CLI prompts
for them and auto-selects whatever the user leaves blank, so the same plan
serves both the interactive summary and the selection step.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import Song


@dataclass
class MomentPlan:
    """One target moment: what carried over, and how much room is left."""

    moment: str
    carried: list[str] = field(default_factory=list)
    slots: int = 0


@dataclass
class ReconcilePlan:
    """The full projection, plus everything that could not come along."""

    moments: list[MomentPlan] = field(default_factory=list)
    # Moments the target event type does not have, mapped to their orphaned songs.
    dropped_moments: dict[str, list[str]] = field(default_factory=dict)
    # (moment, song) pairs dropped because the target moment ran out of room.
    overflow: list[tuple[str, str]] = field(default_factory=list)
    # (moment, song) pairs dropped because the song is not in the target's pool.
    unavailable: list[tuple[str, str]] = field(default_factory=list)

    @property
    def total_slots(self) -> int:
        """Number of songs still to be chosen across all moments."""
        return sum(mp.slots for mp in self.moments)


def plan_reconciliation(
    source_moments: dict[str, list[str]],
    target_moments: dict[str, int],
    available_songs: dict[str, Song],
) -> ReconcilePlan:
    """Project ``source_moments`` onto the ``target_moments`` shape.

    Args:
        source_moments: The setlist being copied, ``{moment: [song titles]}``.
        target_moments: The target event type's shape, ``{moment: count}``,
            already in the order its output should follow (an EventType's
            ``ordered_moments``).
        available_songs: The song pool for the *target* event type, i.e. the
            result of :func:`library.event_type.filter_songs_for_event_type`.
            Songs outside it cannot legally appear in the new setlist.

    Returns:
        A :class:`ReconcilePlan`. Nothing is mutated; the carried lists are
        fresh copies the caller is free to fill in place.
    """
    plan = ReconcilePlan()

    for moment, count in target_moments.items():
        from_source = source_moments.get(moment, [])

        # Availability is filtered before the count is applied. A song bound
        # to another event type must not consume one of the target's slots on
        # its way out, or a legal song further down the list gets dropped in
        # favour of a hole.
        eligible = []
        for title in from_source:
            if title in available_songs:
                eligible.append(title)
            else:
                plan.unavailable.append((moment, title))

        carried = eligible[:count]
        for title in eligible[count:]:
            plan.overflow.append((moment, title))

        plan.moments.append(
            MomentPlan(moment=moment, carried=carried, slots=count - len(carried))
        )

    for moment, songs in source_moments.items():
        if moment not in target_moments:
            plan.dropped_moments[moment] = list(songs)

    return plan
