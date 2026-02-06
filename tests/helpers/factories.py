"""Test data builders and factories.

Use these helpers to construct domain objects with sensible defaults.
Override only the fields relevant to each test case.

Example patterns
----------------

Simple builder function::

    def make_song(**overrides) -> Song:
        defaults = {
            "title": "Factory Song",
            "tags": {"louvor": 3},
            "energy": 2,
            "content": "### Factory Song (G)\\n\\nG  D\\nLyrics...",
            "youtube_url": "",
        }
        defaults.update(overrides)
        return Song(**defaults)

History entry builder::

    def make_history_entry(date: str = "2026-01-15", **moment_songs) -> dict:
        moments = moment_songs or {"louvor": ["Song A", "Song B"]}
        return {"date": date, "moments": moments}
"""
