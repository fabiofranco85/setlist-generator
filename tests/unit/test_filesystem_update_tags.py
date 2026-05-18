"""Tests for FilesystemSongRepository.update_tags and serialize_tags."""

from __future__ import annotations

import pytest

from library.repositories.filesystem.songs import (
    FilesystemSongRepository,
    serialize_tags,
)


# ---------------------------------------------------------------------------
# serialize_tags — pure helper
# ---------------------------------------------------------------------------


class TestSerializeTags:
    def test_default_weight_emits_bare_moment(self):
        # DEFAULT_WEIGHT is 3 — bare form is shorter and matches the existing
        # convention used throughout database.csv.
        assert serialize_tags({"louvor": 3}) == "louvor"

    def test_non_default_weight_uses_parens(self):
        assert serialize_tags({"louvor": 5}) == "louvor(5)"

    def test_multiple_tags_preserve_insertion_order(self):
        result = serialize_tags({"louvor": 5, "prelúdio": 3, "poslúdio": 2})
        assert result == "louvor(5),prelúdio,poslúdio(2)"

    def test_empty_dict_returns_empty_string(self):
        assert serialize_tags({}) == ""

    def test_round_trips_with_parse_tags(self):
        from library.loader import parse_tags

        original = {"louvor": 5, "prelúdio": 3, "poslúdio": 7}
        round_tripped = parse_tags(serialize_tags(original))
        assert round_tripped == original

    def test_round_trip_handles_all_default_weights(self):
        from library.loader import parse_tags

        original = {"louvor": 3, "prelúdio": 3}
        assert parse_tags(serialize_tags(original)) == original


# ---------------------------------------------------------------------------
# FilesystemSongRepository.update_tags — full read/modify/write cycle
# ---------------------------------------------------------------------------


class TestFilesystemUpdateTags:
    @pytest.fixture()
    def repo(self, tmp_project):
        return FilesystemSongRepository(tmp_project)

    def test_updates_existing_weight(self, repo):
        repo.update_tags("Upbeat Song", {"louvor": 7, "prelúdio": 3})
        song = repo.get_by_title("Upbeat Song")
        assert song is not None
        assert song.tags == {"louvor": 7, "prelúdio": 3}

    def test_persists_to_csv(self, repo, tmp_project):
        repo.update_tags("Upbeat Song", {"louvor": 7, "prelúdio": 3})
        # Reload from disk via a fresh repository — proves persistence,
        # not just cache state.
        fresh = FilesystemSongRepository(tmp_project)
        song = fresh.get_by_title("Upbeat Song")
        assert song is not None
        assert song.tags["louvor"] == 7

    def test_invalidates_cache(self, repo):
        # Load → cache populated → update → next read reflects the change
        first = repo.get_by_title("Upbeat Song")
        assert first is not None and first.tags["louvor"] == 4
        repo.update_tags("Upbeat Song", {"louvor": 9, "prelúdio": 3})
        updated = repo.get_by_title("Upbeat Song")
        assert updated is not None and updated.tags["louvor"] == 9

    def test_does_not_touch_other_songs(self, repo, tmp_project):
        # The CSV writer should leave every other row unchanged.
        before = (tmp_project / "database.csv").read_text(encoding="utf-8")
        repo.update_tags("Upbeat Song", {"louvor": 8, "prelúdio": 3})
        after = (tmp_project / "database.csv").read_text(encoding="utf-8")
        # Other rows should appear verbatim in both strings.
        for line in [
            "Moderate Song;2;louvor(3),saudação(4)",
            "Reflective Song;3;louvor(5),ofertório",
            "Worship Song;4;louvor(4),poslúdio(2)",
        ]:
            assert line in before, f"setup precondition failed for {line!r}"
            assert line in after, f"untouched row was rewritten: {line!r}"

    def test_preserves_optional_columns(self, tmp_path):
        # Build a project with the 5th event_types column populated to make
        # sure update_tags doesn't drop it on rewrite.
        db = tmp_path / "database.csv"
        db.write_text(
            "song;energy;tags;youtube;event_types\n"
            "Youth Anthem;1;louvor(5);https://youtu.be/abc;youth\n"
            "Regular;2;louvor(3);;\n",
            encoding="utf-8",
        )
        (tmp_path / "chords").mkdir()

        repo = FilesystemSongRepository(tmp_path)
        repo.update_tags("Youth Anthem", {"louvor": 9})

        after = db.read_text(encoding="utf-8")
        # The youtube and event_types columns should survive intact.
        assert "https://youtu.be/abc" in after
        assert "youth" in after

    def test_unknown_song_raises_key_error(self, repo):
        with pytest.raises(KeyError, match="Ghost"):
            repo.update_tags("Ghost", {"louvor": 5})

    def test_invalid_weight_raises_value_error(self, repo):
        with pytest.raises(ValueError, match="positive integers"):
            repo.update_tags("Upbeat Song", {"louvor": 0})

    def test_negative_weight_raises_value_error(self, repo):
        with pytest.raises(ValueError, match="positive integers"):
            repo.update_tags("Upbeat Song", {"louvor": -1})

    def test_non_integer_weight_raises_value_error(self, repo):
        with pytest.raises(ValueError, match="positive integers"):
            repo.update_tags("Upbeat Song", {"louvor": "5"})  # type: ignore[dict-item]

    def test_empty_dict_clears_tags(self, repo):
        repo.update_tags("Upbeat Song", {})
        assert repo.get_by_title("Upbeat Song").tags == {}

    def test_default_weight_writes_bare_form_in_csv(self, repo, tmp_project):
        # Sanity check: a weight that matches DEFAULT_WEIGHT should hit disk
        # without parentheses (preserves minimal diffs against the existing CSV).
        repo.update_tags("Upbeat Song", {"louvor": 3})
        line = next(
            ln for ln in (tmp_project / "database.csv").read_text().splitlines()
            if ln.startswith("Upbeat Song;")
        )
        assert ";louvor;" in line or line.endswith(";louvor;")
