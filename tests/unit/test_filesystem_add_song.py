"""Tests for FilesystemSongRepository.add."""

from __future__ import annotations

import pytest

from library.models import Song
from library.repositories.filesystem.songs import FilesystemSongRepository


def _song(title, *, tags=None, energy=2.0, content="", youtube_url="", event_types=None):
    return Song(
        title=title,
        tags=tags if tags is not None else {"louvor": 3},
        energy=energy,
        content=content,
        youtube_url=youtube_url,
        event_types=event_types or [],
    )


class TestFilesystemAddSong:
    @pytest.fixture()
    def repo(self, tmp_project):
        return FilesystemSongRepository(tmp_project)

    def test_adds_song_to_catalogue(self, repo):
        repo.add(_song("Novo Louvor", tags={"louvor": 5}, energy=2))
        song = repo.get_by_title("Novo Louvor")
        assert song is not None
        assert song.tags == {"louvor": 5}
        assert song.energy == 2

    def test_persists_to_csv(self, repo, tmp_project):
        repo.add(_song("Novo Louvor", tags={"louvor": 5}, energy=2))
        # Fresh repo proves the row hit disk, not just the cache.
        fresh = FilesystemSongRepository(tmp_project)
        song = fresh.get_by_title("Novo Louvor")
        assert song is not None
        assert song.tags == {"louvor": 5}

    def test_writes_chord_file_with_content(self, repo, tmp_project):
        repo.add(_song("Novo Louvor", content="### Novo Louvor (G)\n\nG  C\nLyrics\n"))
        chord_file = tmp_project / "chords" / "Novo Louvor.md"
        assert chord_file.exists()
        assert chord_file.read_text(encoding="utf-8") == "### Novo Louvor (G)\n\nG  C\nLyrics\n"
        # And the content round-trips into the Song object.
        fresh = FilesystemSongRepository(tmp_project)
        assert fresh.get_by_title("Novo Louvor").content.startswith("### Novo Louvor (G)")

    def test_persists_youtube_url(self, repo, tmp_project):
        repo.add(_song("Novo Louvor", youtube_url="https://youtu.be/abc123"))
        fresh = FilesystemSongRepository(tmp_project)
        song = fresh.get_by_title("Novo Louvor")
        assert song is not None and song.youtube_url == "https://youtu.be/abc123"

    def test_rejects_duplicate_title(self, repo):
        with pytest.raises(ValueError, match="already exists"):
            repo.add(_song("Upbeat Song"))

    def test_does_not_touch_existing_rows(self, repo, tmp_project):
        repo.add(_song("Novo Louvor", tags={"louvor": 5}, energy=2))
        after = (tmp_project / "database.csv").read_text(encoding="utf-8")
        for line in [
            "Upbeat Song;1;louvor(4),prelúdio;",
            "Moderate Song;2;louvor(3),saudação(4);",
            "Reflective Song;3;louvor(5),ofertório;",
            "Worship Song;4;louvor(4),poslúdio(2);",
        ]:
            assert line in after, f"untouched row was rewritten: {line!r}"

    def test_serializes_tags_and_default_weight(self, repo, tmp_project):
        # Default-weight (3) moments are written bare; others get parentheses.
        repo.add(_song("Novo Louvor", tags={"louvor": 5, "prelúdio": 3}))
        after = (tmp_project / "database.csv").read_text(encoding="utf-8")
        assert "Novo Louvor;2.0;louvor(5),prelúdio;" in after

    def test_persists_event_types(self, repo, tmp_project):
        repo.add(_song("Youth Anthem", event_types=["youth"]))
        # tmp_project's database.csv has no event_types column — add() must
        # introduce it so the binding survives a reload.
        fresh = FilesystemSongRepository(tmp_project)
        song = fresh.get_by_title("Youth Anthem")
        assert song is not None and song.event_types == ["youth"]

    def test_invalidates_cache(self, repo):
        assert repo.get_by_title("Novo Louvor") is None  # primes the cache
        repo.add(_song("Novo Louvor"))
        assert repo.get_by_title("Novo Louvor") is not None
