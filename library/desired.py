"""Placement of user-requested ("desired") songs into service moments.

Backs ``songbook generate --desired "Song A, Song B"``. The user names songs
without saying where they go; this module decides the moment for each one and
guarantees every named song lands somewhere — or refuses the whole request.

Unlike ``--override``, which pins songs to a moment at a position the user
chose, a desired song only gets a *moment*. Its position inside that moment is
left to the energy ordering in :mod:`library.ordering`, so the emotional arc of
the moment survives.
"""

from __future__ import annotations

from difflib import get_close_matches

from .models import Song


def parse_desired(raw: str | None) -> list[str]:
    """Split a comma-separated ``--desired`` value into cleaned song titles.

    Blank entries are dropped and repeats are collapsed (case-insensitively) —
    a song named twice would otherwise compete with itself for a slot.
    """
    if not raw:
        return []

    titles: list[str] = []
    seen: set[str] = set()
    for chunk in raw.split(","):
        title = chunk.strip()
        if not title or title.casefold() in seen:
            continue
        seen.add(title.casefold())
        titles.append(title)

    return titles


def resolve_desired_songs(names: list[str], songs: dict[str, Song]) -> dict[str, Song]:
    """Look up desired song titles in the available pool, case-insensitively.

    Returns a dict keyed by the *canonical* database title, so downstream code
    never has to care about how the user capitalized things.

    Raises:
        ValueError: If any name is unknown. Every unmatched name is reported in
            one message (with close-match suggestions) so a user with two typos
            fixes both in one run instead of discovering them one per attempt.
    """
    by_folded = {title.casefold(): title for title in songs}

    resolved: dict[str, Song] = {}
    missing: list[str] = []

    for name in names:
        canonical = by_folded.get(name.strip().casefold())
        if canonical is None:
            missing.append(name)
        else:
            resolved[canonical] = songs[canonical]

    if missing:
        raise ValueError(_missing_songs_message(missing, songs))

    return resolved


def assign_desired_to_moments(
    desired: dict[str, Song],
    capacities: dict[str, int],
) -> dict[str, list[str]]:
    """Assign each desired song to one of the moments it is tagged for.

    Each song prefers the moment where it carries the highest weight; ties go to
    whichever moment comes first in ``capacities`` (i.e. service order). A song
    is only bumped to a lower-preference moment when that is what lets the whole
    set fit.

    Args:
        desired: Canonical title -> Song, the songs that must be placed.
        capacities: Moment -> number of free slots, in service order.

    Returns:
        Moment -> list of assigned titles (in the order the user named them).

    Raises:
        ValueError: If no assignment places every desired song.
    """
    preferences = {
        title: _rank_moments(song, capacities) for title, song in desired.items()
    }

    unplaceable = [title for title, moments in preferences.items() if not moments]
    if unplaceable:
        raise ValueError(_unplaceable_message(unplaceable, desired, capacities))

    assignment: dict[str, list[str]] = {moment: [] for moment in capacities}

    unplaced = []
    for title in desired:
        if not _seat(title, preferences, capacities, assignment, visited=set()):
            unplaced.append(title)

    if unplaced:
        raise ValueError(_no_room_message(unplaced, preferences, capacities))

    return {moment: titles for moment, titles in assignment.items() if titles}


def plan_desired_songs(
    names: list[str],
    songs: dict[str, Song],
    moments_config: dict[str, int],
    overrides: dict[str, list[str]] | None = None,
) -> dict[str, list[str]]:
    """Resolve desired song names and assign them to moments.

    The single entry point used by :class:`~library.generator.SetlistGenerator`.
    ``songs`` must already be filtered for the target event type, so a song bound
    to another event type simply reads as "not found".

    Overrides are honored first: they consume slots in their moment (shrinking
    what is left for desired songs) and a song named in both is dropped from the
    desired set, since the override already guarantees it.
    """
    overrides = overrides or {}

    resolved = resolve_desired_songs(names, songs)

    already_pinned = {title for titles in overrides.values() for title in titles}
    resolved = {
        title: song for title, song in resolved.items() if title not in already_pinned
    }
    if not resolved:
        return {}

    capacities = {
        moment: max(0, count - len(overrides.get(moment, [])))
        for moment, count in moments_config.items()
    }

    return assign_desired_to_moments(resolved, capacities)


# --------------------------------------------------------------------------
# Internals
# --------------------------------------------------------------------------


def _rank_moments(song: Song, capacities: dict[str, int]) -> list[str]:
    """Moments this song can go in, best first.

    Ordered by tag weight descending, ties broken by service order. Moments the
    song isn't tagged for — and moments with no free slots — are excluded.
    """
    service_order = list(capacities)
    candidates = [
        moment
        for moment in service_order
        if song.has_moment(moment) and capacities[moment] > 0
    ]
    return sorted(
        candidates,
        key=lambda moment: (-song.get_weight(moment), service_order.index(moment)),
    )


def _seat(
    title: str,
    preferences: dict[str, list[str]],
    capacities: dict[str, int],
    assignment: dict[str, list[str]],
    visited: set[str],
) -> bool:
    """Seat one song, relocating already-seated songs if that is what it takes.

    This is Kuhn's augmenting-path step for bipartite matching. Walking the
    song's moments in preference order means it takes its favorite moment
    whenever that moment has room; the recursive branch only fires when the
    moment is full, and it asks a current occupant to move rather than giving up.

    Plain greedy assignment fails here: two songs that both prefer a one-slot
    prelúdio would strand the second, even when poslúdio sits empty and the
    first song is tagged for it too. ``visited`` guards against cycling between
    moments while looking for that rearrangement.
    """
    for moment in preferences[title]:
        if moment in visited:
            continue
        visited.add(moment)

        if len(assignment[moment]) < capacities[moment]:
            assignment[moment].append(title)
            return True

        for occupant in list(assignment[moment]):
            assignment[moment].remove(occupant)
            if _seat(occupant, preferences, capacities, assignment, visited):
                assignment[moment].append(title)
                return True
            assignment[moment].append(occupant)

    return False


def _missing_songs_message(missing: list[str], songs: dict[str, Song]) -> str:
    lines = [
        f"{len(missing)} desired song(s) not found in the song database:"
        if len(missing) > 1
        else "Desired song not found in the song database:"
    ]
    for name in missing:
        suggestions = get_close_matches(name, list(songs), n=3, cutoff=0.6)
        hint = f" — did you mean: {', '.join(suggestions)}?" if suggestions else ""
        lines.append(f"  - {name!r}{hint}")
    return "\n".join(lines)


def _unplaceable_message(
    unplaceable: list[str],
    desired: dict[str, Song],
    capacities: dict[str, int],
) -> str:
    moments = ", ".join(capacities) or "(none)"
    lines = ["Desired song(s) cannot be placed in any moment of this setlist:"]
    for title in unplaceable:
        tags = ", ".join(desired[title].tags) or "(untagged)"
        lines.append(f"  - {title!r} is tagged for: {tags}")
    lines.append(f"Moments available for this setlist: {moments}")
    return "\n".join(lines)


def _no_room_message(
    unplaced: list[str],
    preferences: dict[str, list[str]],
    capacities: dict[str, int],
) -> str:
    contested = sorted({moment for title in unplaced for moment in preferences[title]})
    lines = ["Not enough room for every desired song."]
    for title in unplaced:
        lines.append(f"  - {title!r} could not be placed")
    for moment in contested:
        lines.append(f"Moment {moment!r} has room for only {capacities[moment]} song(s).")
    lines.append("Ask for fewer songs, or free up slots by dropping an --override.")
    return "\n".join(lines)
