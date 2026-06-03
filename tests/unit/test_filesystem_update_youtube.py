"""Tests for FilesystemSongRepository.update_youtube."""

from __future__ import annotations

import pytest

from library.repositories.filesystem.songs import FilesystemSongRepository


class TestFilesystemUpdateYoutube:
    @pytest.fixture()
    def repo(self, tmp_project):
        return FilesystemSongRepository(tmp_project)

    def test_sets_youtube_url(self, repo):
        repo.update_youtube("Upbeat Song", "https://youtu.be/abc123")
        song = repo.get_by_title("Upbeat Song")
        assert song is not None
        assert song.youtube_url == "https://youtu.be/abc123"

    def test_persists_to_csv(self, repo, tmp_project):
        repo.update_youtube("Upbeat Song", "https://youtu.be/abc123")
        # Reload from disk via a fresh repository — proves persistence,
        # not just cache state.
        fresh = FilesystemSongRepository(tmp_project)
        song = fresh.get_by_title("Upbeat Song")
        assert song is not None
        assert song.youtube_url == "https://youtu.be/abc123"

    def test_invalidates_cache(self, repo):
        first = repo.get_by_title("Upbeat Song")
        assert first is not None and first.youtube_url == ""
        repo.update_youtube("Upbeat Song", "https://youtu.be/xyz")
        updated = repo.get_by_title("Upbeat Song")
        assert updated is not None and updated.youtube_url == "https://youtu.be/xyz"

    def test_empty_string_clears_link(self, repo):
        repo.update_youtube("Upbeat Song", "https://youtu.be/abc123")
        repo.update_youtube("Upbeat Song", "")
        song = repo.get_by_title("Upbeat Song")
        assert song is not None and song.youtube_url == ""

    def test_stores_value_verbatim_without_validation(self, repo):
        # The repository layer is format-agnostic — validation is the CLI's job.
        repo.update_youtube("Upbeat Song", "not-a-url")
        song = repo.get_by_title("Upbeat Song")
        assert song is not None and song.youtube_url == "not-a-url"

    def test_does_not_touch_other_songs(self, repo, tmp_project):
        repo.update_youtube("Upbeat Song", "https://youtu.be/abc123")
        after = (tmp_project / "database.csv").read_text(encoding="utf-8")
        for line in [
            "Moderate Song;2;louvor(3),saudação(4);",
            "Reflective Song;3;louvor(5),ofertório;",
            "Worship Song;4;louvor(4),poslúdio(2);",
        ]:
            assert line in after, f"untouched row was rewritten: {line!r}"

    def test_preserves_tags_and_event_types_columns(self, tmp_path):
        db = tmp_path / "database.csv"
        db.write_text(
            "song;energy;tags;youtube;event_types\n"
            "Youth Anthem;1;louvor(5);https://youtu.be/old;youth\n"
            "Regular;2;louvor(3);;\n",
            encoding="utf-8",
        )
        (tmp_path / "chords").mkdir()

        repo = FilesystemSongRepository(tmp_path)
        repo.update_youtube("Youth Anthem", "https://youtu.be/new")

        song = repo.get_by_title("Youth Anthem")
        assert song is not None
        assert song.youtube_url == "https://youtu.be/new"
        assert song.tags == {"louvor": 5}
        assert song.event_types == ["youth"]

    def test_adds_youtube_column_when_missing(self, tmp_path):
        # A CSV without the optional 'youtube' column should gain it on write.
        db = tmp_path / "database.csv"
        db.write_text(
            "song;energy;tags\n"
            "Bare Song;2;louvor(3)\n",
            encoding="utf-8",
        )
        (tmp_path / "chords").mkdir()

        repo = FilesystemSongRepository(tmp_path)
        repo.update_youtube("Bare Song", "https://youtu.be/abc123")

        after = db.read_text(encoding="utf-8")
        assert "youtube" in after.splitlines()[0]
        song = repo.get_by_title("Bare Song")
        assert song is not None and song.youtube_url == "https://youtu.be/abc123"

    def test_unknown_song_raises_key_error(self, repo):
        with pytest.raises(KeyError, match="Ghost"):
            repo.update_youtube("Ghost", "https://youtu.be/abc123")
