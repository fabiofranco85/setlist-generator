"""Unit tests for generator strict mode (Problem 2).

When a custom moments_config is provided (event type), the generator should
raise ValueError if a moment has zero tagged songs. Default MOMENTS_CONFIG
generation remains lenient (no error for empty moments).
"""

import pytest

from library.generator import SetlistGenerator, generate_setlist
from tests.helpers.factories import make_song


class TestStrictModeRaisesForEmptyMoment:
    """When moments_config is passed (custom event type), strict mode fires."""

    def _make_songs(self):
        return {
            "Song A": make_song(title="Song A", tags={"louvor": 3}),
            "Song B": make_song(title="Song B", tags={"louvor": 4}),
            "Song C": make_song(title="Song C", tags={"louvor": 5}),
        }

    def test_raises_when_no_songs_tagged(self):
        songs = self._make_songs()
        generator = SetlistGenerator(songs, [])

        with pytest.raises(ValueError, match="No songs available for moment 'final'"):
            generator.generate(
                "2026-03-01",
                moments_config={"louvor": 2, "final": 1},
            )

    def test_error_message_includes_moment_name(self):
        songs = self._make_songs()
        generator = SetlistGenerator(songs, [])

        with pytest.raises(ValueError, match="'custom_moment'"):
            generator.generate(
                "2026-03-01",
                moments_config={"louvor": 1, "custom_moment": 1},
            )

    def test_functional_api_also_raises(self):
        songs = self._make_songs()

        with pytest.raises(ValueError, match="No songs available"):
            generate_setlist(
                songs, [], "2026-03-01",
                moments_config={"louvor": 1, "nonexistent": 1},
            )


class TestStrictModeDoesNotFireForDefaults:
    """Default MOMENTS_CONFIG generation stays lenient."""

    def test_no_error_for_empty_moment_without_custom_config(self, sample_songs):
        """sample_songs has no 'crianças'-tagged songs, but default is lenient."""
        generator = SetlistGenerator(sample_songs, [])
        # moments_config=None → uses default config → strict=False
        setlist = generator.generate("2026-03-01")
        # crianças should just be empty, no error
        assert setlist.moments.get("crianças") == []


class TestStrictModeSucceedsWhenSongsExist:
    """Strict mode doesn't fire when there are tagged songs."""

    def test_no_error_when_songs_are_tagged(self):
        songs = {
            "Song A": make_song(title="Song A", tags={"louvor": 3, "final": 2}),
            "Song B": make_song(title="Song B", tags={"louvor": 4}),
        }
        generator = SetlistGenerator(songs, [])
        setlist = generator.generate(
            "2026-03-01",
            moments_config={"louvor": 1, "final": 1},
        )
        assert len(setlist.moments["final"]) == 1

    def test_no_error_when_all_tagged_songs_already_selected(self):
        """If songs ARE tagged but all were already selected for other moments,
        strict mode does NOT raise — it only raises when zero songs have the tag."""
        songs = {
            "Song A": make_song(title="Song A", tags={"louvor": 3, "final": 2}),
        }
        generator = SetlistGenerator(songs, [])
        # louvor selects Song A first, then final has no candidates left,
        # but Song A IS tagged for 'final', so strict doesn't fire
        setlist = generator.generate(
            "2026-03-01",
            moments_config={"louvor": 1, "final": 1},
        )
        # final is empty (Song A already used), but no error
        assert setlist.moments["final"] == []
