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


class TestLabeledGenerationWorkflow:
    """Integration tests for labeled setlists and derivation."""

    @pytest.fixture()
    def repos(self, tmp_project, monkeypatch):
        monkeypatch.delenv("STORAGE_BACKEND", raising=False)
        monkeypatch.delenv("SETLIST_OUTPUT_DIR", raising=False)
        monkeypatch.delenv("SETLIST_HISTORY_DIR", raising=False)
        return get_repositories(base_path=tmp_project)

    def test_generate_primary_then_derive(self, repos, tmp_project):
        """Full workflow: generate primary, derive labeled variant."""
        random.seed(42)
        generator = SetlistGenerator.from_repositories(repos.songs, repos.history)

        # Generate primary (unlabeled)
        primary = generator.generate("2026-03-01")
        repos.history.save(primary)

        assert (tmp_project / "history" / "2026-03-01.json").exists()

        # Derive labeled variant
        from library.models import Setlist
        from library.replacer import derive_setlist

        songs = repos.songs.get_all()
        history = repos.history.get_all()
        base_dict = repos.history.get_by_date("2026-03-01")

        derived_dict = derive_setlist(base_dict, songs, history, replace_count=2)
        derived_dict["label"] = "evening"

        derived_setlist = Setlist(
            date=derived_dict["date"],
            moments=derived_dict["moments"],
            label="evening",
        )
        repos.history.save(derived_setlist)

        # Verify both exist
        assert (tmp_project / "history" / "2026-03-01.json").exists()
        assert (tmp_project / "history" / "2026-03-01_evening.json").exists()

        # Verify get_by_date_all returns both
        all_setlists = repos.history.get_by_date_all("2026-03-01")
        assert len(all_setlists) == 2
        labels = [s.get("label", "") for s in all_setlists]
        assert "" in labels
        assert "evening" in labels

    def test_labeled_setlist_markdown_output(self, repos, tmp_project):
        """Labeled setlists produce files with label in filename."""
        random.seed(42)
        generator = SetlistGenerator.from_repositories(repos.songs, repos.history)
        setlist = generator.generate("2026-03-01", label="morning")
        songs = repos.songs.get_all()

        md_path, _ = repos.output.save_from_setlist(setlist, songs)
        assert md_path.name == "2026-03-01_morning.md"
        content = md_path.read_text()
        assert "# Setlist - 2026-03-01 (morning)" in content

    def test_recency_shared_across_labels(self, repos):
        """Both labeled and unlabeled setlists contribute to recency scores."""
        random.seed(42)
        generator = SetlistGenerator.from_repositories(repos.songs, repos.history)

        # Generate primary
        primary = generator.generate("2026-03-01")
        repos.history.save(primary)

        # Generate labeled
        labeled = generator.generate("2026-03-01", label="evening")
        repos.history.save(labeled)

        # Both should appear in get_all
        all_history = repos.history.get_all()
        dates = [h["date"] for h in all_history]
        assert dates.count("2026-03-01") == 2

        # Recency calculation uses all of them (via date field)
        from library.selector import calculate_recency_scores
        songs = repos.songs.get_all()
        scores = calculate_recency_scores(songs, all_history, "2026-04-01")
        # Songs used on 2026-03-01 should have non-1.0 recency
        for song_title in primary.moments.get("louvor", []):
            assert scores[song_title] < 1.0
