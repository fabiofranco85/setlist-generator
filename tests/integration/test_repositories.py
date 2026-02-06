"""Integration tests for filesystem repositories.

All tests use the ``tmp_project`` fixture (real files on disk).
"""

import json
from pathlib import Path

import pytest

from library.models import Setlist
from library.repositories import get_repositories
from library.repositories.filesystem import (
    FilesystemConfigRepository,
    FilesystemHistoryRepository,
    FilesystemOutputRepository,
    FilesystemSongRepository,
)


# ---------------------------------------------------------------------------
# SongRepository
# ---------------------------------------------------------------------------


class TestFilesystemSongRepository:
    @pytest.fixture()
    def repo(self, tmp_project):
        return FilesystemSongRepository(tmp_project)

    def test_get_all_count(self, repo):
        songs = repo.get_all()
        assert len(songs) == 4

    def test_get_all_keys(self, repo):
        songs = repo.get_all()
        assert "Upbeat Song" in songs
        assert "Moderate Song" in songs
        assert "Reflective Song" in songs
        assert "Worship Song" in songs

    def test_get_by_title_found(self, repo):
        song = repo.get_by_title("Upbeat Song")
        assert song is not None
        assert song.title == "Upbeat Song"
        assert song.energy == 1

    def test_get_by_title_not_found(self, repo):
        assert repo.get_by_title("Ghost") is None

    def test_search_case_insensitive(self, repo):
        results = repo.search("upbeat")
        assert len(results) == 1
        assert results[0].title == "Upbeat Song"

    def test_search_partial_match(self, repo):
        results = repo.search("Song")
        assert len(results) == 4

    def test_update_content(self, repo, tmp_project):
        new_content = "### Upbeat Song (D)\n\nD  A\nNew lyrics"
        repo.update_content("Upbeat Song", new_content)
        song = repo.get_by_title("Upbeat Song")
        assert song.content == new_content
        # Also persisted to disk
        file_content = (tmp_project / "chords" / "Upbeat Song.md").read_text()
        assert file_content == new_content

    def test_update_content_not_found_raises(self, repo):
        with pytest.raises(KeyError, match="not found"):
            repo.update_content("Ghost", "content")

    def test_exists_true(self, repo):
        assert repo.exists("Upbeat Song") is True

    def test_exists_false(self, repo):
        assert repo.exists("Ghost") is False

    def test_tags_parsed_correctly(self, repo):
        song = repo.get_by_title("Upbeat Song")
        assert song.tags == {"louvor": 4, "prelúdio": 3}

    def test_content_loaded_from_chord_file(self, repo):
        song = repo.get_by_title("Upbeat Song")
        assert "### Upbeat Song (C)" in song.content


# ---------------------------------------------------------------------------
# HistoryRepository
# ---------------------------------------------------------------------------


class TestFilesystemHistoryRepository:
    @pytest.fixture()
    def repo(self, tmp_project):
        return FilesystemHistoryRepository(tmp_project / "history")

    def test_get_all_empty(self, repo):
        assert repo.get_all() == []

    def test_save_and_get_all(self, repo):
        setlist = Setlist(date="2026-02-15", moments={"louvor": ["Song A"]})
        repo.save(setlist)
        history = repo.get_all()
        assert len(history) == 1
        assert history[0]["date"] == "2026-02-15"

    def test_save_creates_file(self, repo, tmp_project):
        setlist = Setlist(date="2026-02-15", moments={"louvor": ["Song A"]})
        repo.save(setlist)
        json_file = tmp_project / "history" / "2026-02-15.json"
        assert json_file.exists()
        data = json.loads(json_file.read_text())
        assert data["date"] == "2026-02-15"

    def test_get_by_date_found(self, repo):
        setlist = Setlist(date="2026-02-15", moments={"louvor": ["Song A"]})
        repo.save(setlist)
        result = repo.get_by_date("2026-02-15")
        assert result is not None
        assert result["date"] == "2026-02-15"

    def test_get_by_date_not_found(self, repo):
        assert repo.get_by_date("2099-12-31") is None

    def test_get_latest_empty(self, repo):
        assert repo.get_latest() is None

    def test_get_latest(self, repo):
        repo.save(Setlist(date="2026-01-01", moments={"louvor": ["A"]}))
        repo.save(Setlist(date="2026-02-15", moments={"louvor": ["B"]}))
        latest = repo.get_latest()
        assert latest["date"] == "2026-02-15"

    def test_save_overwrites_existing(self, repo):
        repo.save(Setlist(date="2026-02-15", moments={"louvor": ["A"]}))
        repo.save(Setlist(date="2026-02-15", moments={"louvor": ["B"]}))
        result = repo.get_by_date("2026-02-15")
        assert result["moments"]["louvor"] == ["B"]

    def test_update_existing(self, repo):
        repo.save(Setlist(date="2026-02-15", moments={"louvor": ["A"]}))
        repo.update("2026-02-15", {"date": "2026-02-15", "moments": {"louvor": ["B"]}})
        result = repo.get_by_date("2026-02-15")
        assert result["moments"]["louvor"] == ["B"]

    def test_update_nonexistent_raises(self, repo):
        with pytest.raises(KeyError, match="No setlist found"):
            repo.update("2099-12-31", {"date": "2099-12-31", "moments": {}})

    def test_exists_true(self, repo):
        repo.save(Setlist(date="2026-02-15", moments={"louvor": ["A"]}))
        assert repo.exists("2026-02-15") is True

    def test_exists_false(self, repo):
        assert repo.exists("2099-12-31") is False

    def test_get_all_sorted_most_recent_first(self, repo):
        repo.save(Setlist(date="2026-01-01", moments={"louvor": ["A"]}))
        repo.save(Setlist(date="2026-03-01", moments={"louvor": ["B"]}))
        repo.save(Setlist(date="2026-02-01", moments={"louvor": ["C"]}))
        history = repo.get_all()
        dates = [h["date"] for h in history]
        assert dates == ["2026-03-01", "2026-02-01", "2026-01-01"]


# ---------------------------------------------------------------------------
# ConfigRepository
# ---------------------------------------------------------------------------


class TestFilesystemConfigRepository:
    @pytest.fixture()
    def repo(self):
        return FilesystemConfigRepository()

    def test_moments(self, repo):
        moments = repo.get_moments_config()
        assert "louvor" in moments
        assert moments["louvor"] == 4

    def test_recency_decay(self, repo):
        assert repo.get_recency_decay_days() == 45

    def test_default_weight(self, repo):
        assert repo.get_default_weight() == 3

    def test_energy_ordering(self, repo):
        assert repo.is_energy_ordering_enabled() is True
        rules = repo.get_energy_ordering_rules()
        assert rules.get("louvor") == "ascending"

    def test_default_energy(self, repo):
        assert repo.get_default_energy() == 2.5


# ---------------------------------------------------------------------------
# OutputRepository
# ---------------------------------------------------------------------------


class TestFilesystemOutputRepository:
    @pytest.fixture()
    def repo(self, tmp_project):
        return FilesystemOutputRepository(tmp_project / "output")

    def test_save_markdown(self, repo, tmp_project):
        path = repo.save_markdown("2026-02-15", "# Test content")
        assert path.exists()
        assert path.read_text() == "# Test content"

    def test_get_markdown_path(self, repo, tmp_project):
        path = repo.get_markdown_path("2026-02-15")
        assert path == tmp_project / "output" / "2026-02-15.md"

    def test_get_pdf_path(self, repo, tmp_project):
        path = repo.get_pdf_path("2026-02-15")
        assert path == tmp_project / "output" / "2026-02-15.pdf"

    def test_save_from_setlist_markdown_only(self, repo, tmp_project):
        songs_repo = FilesystemSongRepository(tmp_project)
        songs = songs_repo.get_all()
        setlist = Setlist(
            date="2026-02-15",
            moments={"louvor": ["Upbeat Song", "Moderate Song"]},
        )
        md_path, pdf_path = repo.save_from_setlist(setlist, songs, include_pdf=False)
        assert md_path.exists()
        assert pdf_path is None
        content = md_path.read_text()
        assert "# Setlist - 2026-02-15" in content


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class TestGetRepositories:
    def test_default_filesystem(self, tmp_project, monkeypatch):
        monkeypatch.delenv("STORAGE_BACKEND", raising=False)
        monkeypatch.delenv("SETLIST_OUTPUT_DIR", raising=False)
        monkeypatch.delenv("SETLIST_HISTORY_DIR", raising=False)
        repos = get_repositories(base_path=tmp_project)
        songs = repos.songs.get_all()
        assert len(songs) == 4

    def test_unknown_backend_raises(self, tmp_project):
        with pytest.raises(ValueError, match="Unknown storage backend"):
            get_repositories(backend="unknown_db", base_path=tmp_project)
