"""Tests for library/labeler.py — relabel_setlist()."""

import pytest

from library.labeler import relabel_setlist
from library.models import Setlist


class TestRelabelSetlist:
    """Core relabel_setlist() function tests."""

    @pytest.fixture()
    def base_dict(self):
        return {
            "date": "2026-03-01",
            "moments": {
                "louvor": ["Song A", "Song B", "Song C", "Song D"],
                "prelúdio": ["Song E"],
            },
        }

    @pytest.fixture()
    def labeled_dict(self):
        return {
            "date": "2026-03-01",
            "label": "evening",
            "moments": {
                "louvor": ["Song A", "Song B"],
                "prelúdio": ["Song C"],
            },
        }

    # --- Add label ---

    def test_add_label(self, base_dict):
        result = relabel_setlist(base_dict, "evening")
        assert result.label == "evening"
        assert result.date == "2026-03-01"
        assert result.setlist_id == "2026-03-01_evening"

    def test_add_label_preserves_moments(self, base_dict):
        result = relabel_setlist(base_dict, "evening")
        assert result.moments == base_dict["moments"]

    # --- Rename label ---

    def test_rename_label(self, labeled_dict):
        result = relabel_setlist(labeled_dict, "night")
        assert result.label == "night"
        assert result.setlist_id == "2026-03-01_night"

    # --- Remove label ---

    def test_remove_label(self, labeled_dict):
        result = relabel_setlist(labeled_dict, "")
        assert result.label == ""
        assert result.setlist_id == "2026-03-01"

    # --- Returns Setlist ---

    def test_returns_setlist_instance(self, base_dict):
        result = relabel_setlist(base_dict, "evening")
        assert isinstance(result, Setlist)

    # --- Deep copy ---

    def test_moments_deep_copied(self, base_dict):
        result = relabel_setlist(base_dict, "evening")
        # Mutating the result should not affect the source
        result.moments["louvor"].append("Extra")
        assert "Extra" not in base_dict["moments"]["louvor"]

    def test_source_not_mutated(self, base_dict):
        original_moments = {k: list(v) for k, v in base_dict["moments"].items()}
        relabel_setlist(base_dict, "evening")
        assert base_dict["moments"] == original_moments

    # --- to_dict roundtrip ---

    def test_to_dict_with_label(self, base_dict):
        result = relabel_setlist(base_dict, "evening")
        d = result.to_dict()
        assert d["label"] == "evening"
        assert d["date"] == "2026-03-01"

    def test_to_dict_without_label(self, labeled_dict):
        result = relabel_setlist(labeled_dict, "")
        d = result.to_dict()
        assert "label" not in d


class TestHistoryRepositoryDelete:
    """Tests for HistoryRepository.delete()."""

    @pytest.fixture()
    def history_repo(self, tmp_path):
        from library.repositories.filesystem.history import FilesystemHistoryRepository
        return FilesystemHistoryRepository(tmp_path / "history")

    def test_delete_unlabeled(self, history_repo, tmp_path):
        s = Setlist(date="2026-01-01", moments={"louvor": ["A"]})
        history_repo.save(s)
        assert history_repo.exists("2026-01-01")

        history_repo.delete("2026-01-01")
        assert not history_repo.exists("2026-01-01")

    def test_delete_labeled(self, history_repo, tmp_path):
        s = Setlist(date="2026-01-01", moments={"louvor": ["A"]}, label="evening")
        history_repo.save(s)
        assert history_repo.exists("2026-01-01", label="evening")

        history_repo.delete("2026-01-01", label="evening")
        assert not history_repo.exists("2026-01-01", label="evening")

    def test_delete_raises_if_not_found(self, history_repo):
        with pytest.raises(KeyError, match="No setlist found"):
            history_repo.delete("9999-01-01")

    def test_delete_invalidates_cache(self, history_repo):
        s = Setlist(date="2026-01-01", moments={"louvor": ["A"]})
        history_repo.save(s)
        # Populate cache
        assert len(history_repo.get_all()) == 1

        history_repo.delete("2026-01-01")
        # Cache should be invalidated — get_all should return empty
        assert len(history_repo.get_all()) == 0

    def test_delete_file_removed(self, history_repo, tmp_path):
        s = Setlist(date="2026-01-01", moments={"louvor": ["A"]}, label="evening")
        history_repo.save(s)
        json_path = tmp_path / "history" / "2026-01-01_evening.json"
        assert json_path.exists()

        history_repo.delete("2026-01-01", label="evening")
        assert not json_path.exists()


class TestOutputRepositoryDeleteOutputs:
    """Tests for OutputRepository.delete_outputs()."""

    @pytest.fixture()
    def output_repo(self, tmp_path):
        from library.repositories.filesystem.output import FilesystemOutputRepository
        return FilesystemOutputRepository(tmp_path / "output")

    def test_delete_md_only(self, output_repo, tmp_path):
        output_repo.save_markdown("2026-01-01", "# Test", label="evening")
        deleted = output_repo.delete_outputs("2026-01-01", label="evening")
        assert len(deleted) == 1
        assert deleted[0].suffix == ".md"
        assert not deleted[0].exists()

    def test_delete_md_and_pdf(self, output_repo, tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir(exist_ok=True)
        output_repo.save_markdown("2026-01-01", "# Test")
        # Create a fake PDF
        (output_dir / "2026-01-01.pdf").write_text("fake pdf")

        deleted = output_repo.delete_outputs("2026-01-01")
        assert len(deleted) == 2
        suffixes = {p.suffix for p in deleted}
        assert suffixes == {".md", ".pdf"}

    def test_delete_returns_empty_when_no_files(self, output_repo):
        deleted = output_repo.delete_outputs("9999-01-01")
        assert deleted == []

    def test_delete_with_label(self, output_repo, tmp_path):
        output_repo.save_markdown("2026-01-01", "# Test", label="evening")
        deleted = output_repo.delete_outputs("2026-01-01", label="evening")
        assert len(deleted) == 1
        assert "evening" in deleted[0].name

    def test_delete_does_not_affect_other_labels(self, output_repo, tmp_path):
        output_repo.save_markdown("2026-01-01", "# Unlabeled")
        output_repo.save_markdown("2026-01-01", "# Evening", label="evening")

        output_repo.delete_outputs("2026-01-01", label="evening")
        # Unlabeled should still exist
        assert output_repo.get_markdown_path("2026-01-01").exists()
