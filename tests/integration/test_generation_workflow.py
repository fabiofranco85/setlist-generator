"""Integration tests for end-to-end generation workflows.

These tests exercise the full pipeline: repositories → generator → output.
"""

import json
import random

import pytest

from library.formatter import format_setlist_markdown
from library.generator import SetlistGenerator
from library.repositories import get_repositories


class TestGenerationWorkflow:
    @pytest.fixture()
    def repos(self, tmp_project, monkeypatch):
        monkeypatch.delenv("STORAGE_BACKEND", raising=False)
        monkeypatch.delenv("SETLIST_OUTPUT_DIR", raising=False)
        monkeypatch.delenv("SETLIST_HISTORY_DIR", raising=False)
        return get_repositories(base_path=tmp_project)

    def test_generate_and_save_history(self, repos, tmp_project):
        random.seed(42)
        generator = SetlistGenerator.from_repositories(repos.songs, repos.history)
        setlist = generator.generate("2026-02-15")
        repos.history.save(setlist)

        json_file = tmp_project / "history" / "2026-02-15.json"
        assert json_file.exists()
        data = json.loads(json_file.read_text())
        assert data["date"] == "2026-02-15"
        assert "louvor" in data["moments"]

    def test_generate_and_save_markdown(self, repos, tmp_project):
        random.seed(42)
        generator = SetlistGenerator.from_repositories(repos.songs, repos.history)
        setlist = generator.generate("2026-02-15")
        songs = repos.songs.get_all()

        md_content = format_setlist_markdown(setlist, songs)
        md_path = repos.output.save_markdown(setlist.date, md_content)

        assert md_path.exists()
        content = md_path.read_text()
        assert "# Setlist - 2026-02-15" in content

    def test_generate_replace_and_save(self, repos, tmp_project):
        random.seed(42)
        generator = SetlistGenerator.from_repositories(repos.songs, repos.history)
        setlist = generator.generate("2026-02-15")
        repos.history.save(setlist)

        from library.replacer import replace_song_in_setlist

        songs = repos.songs.get_all()
        setlist_dict = repos.history.get_by_date("2026-02-15")

        if setlist_dict["moments"].get("louvor"):
            original_song = setlist_dict["moments"]["louvor"][0]
            # Find a replacement candidate
            available = [
                t for t in songs
                if t != original_song and songs[t].has_moment("louvor")
                and t not in setlist_dict["moments"]["louvor"]
            ]
            if available:
                replacement = available[0]
                new_setlist = replace_song_in_setlist(
                    setlist_dict, "louvor", 0, replacement, songs
                )
                repos.history.update("2026-02-15", new_setlist)
                updated = repos.history.get_by_date("2026-02-15")
                assert replacement in updated["moments"]["louvor"]

    def test_from_repositories_pipeline(self, repos):
        random.seed(42)
        generator = SetlistGenerator.from_repositories(repos.songs, repos.history)
        setlist = generator.generate("2026-02-15")
        assert setlist.date == "2026-02-15"
        # Should have songs for louvor (the largest moment)
        assert len(setlist.moments["louvor"]) > 0
