"""Test data builders and factories.

Use these helpers to construct domain objects with sensible defaults.
Override only the fields relevant to each test case.
"""

from library.models import Song


def make_song(**overrides) -> Song:
    """Build a Song with sensible defaults.

    Example::

        song = make_song(title="Oceanos", energy=2)
        song = make_song(tags={"louvor": 5, "prelúdio": 3})
    """
    defaults = {
        "title": "Factory Song",
        "tags": {"louvor": 3},
        "energy": 2,
        "content": "### Factory Song (G)\n\nG  D\nLyrics...",
        "youtube_url": "",
    }
    defaults.update(overrides)
    return Song(**defaults)


def make_history_entry(date: str = "2026-01-15", **moment_songs) -> dict:
    """Build a history entry dict.

    Example::

        entry = make_history_entry("2026-01-15", louvor=["Song A", "Song B"])
        entry = make_history_entry()  # uses defaults
    """
    moments = moment_songs or {"louvor": ["Factory Song"]}
    return {"date": date, "moments": moments}
